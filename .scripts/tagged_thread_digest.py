#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tagged_thread_digest.py
──────────────────────────────────────────────────────────────────────────────
저장소 소유자(박성환 / Seonghwan Park)가 @-태그된 모든 스레드 메시지를
마지막 실행 이후 구간에서 수집 → 요약 → 한국어 리포트로 전달하는 잡(Job).

- 단독 실행: python .scripts/tagged_thread_digest.py [--dry-run] [--window-hours N]
- 임포트 사용: from tagged_thread_digest import run_digest; run_digest()

스케줄: 월–금 08:00~20:00, 4시간 간격 (08/12/16/20시, Asia/Seoul)
        → 인프로세스 스케줄러(nova_tagged_digest.py) 또는 Windows Task Scheduler
          (setup_tagged_digest_schedule.py)에서 호출.

필수 토큰:
- SLACK_USER_TOKEN (xoxp, search:read 스코프) — search.messages 는 유저 토큰 전용.
- SLACK_BOT_TOKEN (xoxb) — 리포트 게시용(없으면 유저 토큰으로 게시).

선택 환경변수:
- SLACK_TARGET_USER_ID   — 대상 유저 ID(미설정 시 유저 토큰의 auth.test 결과 사용).
- TAGGED_DIGEST_CHANNEL  — 리포트 게시 채널(미설정 시 대상 유저 DM).
- CLAUDE_API_KEY / ANTHROPIC_API_KEY — 요약용 Anthropic 키(없으면 비-LLM 폴백).
"""

import os
import ssl
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone

# ── 경로 상수 ─────────────────────────────────────────────────────────────────
_THIS_DIR   = Path(__file__).resolve().parent           # .../.scripts
_BASE       = _THIS_DIR.parent                          # workspace root
_NOVA_ENV   = _BASE / "projects" / "nova_helper" / ".env"
_SCRIPTS_ENV = _THIS_DIR / ".env"
_MODEL_CONFIG = _THIS_DIR / "model_config.json"

_STATUS_DIR = _BASE / ".status"
_STATE_FILE = _STATUS_DIR / "tagged_digest_state.json"
_OUT_DIR    = _STATUS_DIR / "tagged_digest"

# Asia/Seoul (KST, UTC+9). zoneinfo가 없어도 동작하도록 고정 오프셋 사용.
KST = timezone(timedelta(hours=9))

DEFAULT_WINDOW_HOURS = 4
SEARCH_PAGE_LIMIT    = 100    # search.messages 페이지당 결과 수
SEARCH_MAX_PAGES     = 10     # 페이지네이션 상한(과도한 호출 방지)
MODEL_FALLBACK       = "claude-sonnet-5"


# ── 환경변수 로드 (nova_helper 패턴: nova_helper/.env → .scripts/.env) ─────────
def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("[digest] python-dotenv 미설치 — OS 환경변수만 사용합니다.")
        return
    if _NOVA_ENV.exists():
        load_dotenv(dotenv_path=str(_NOVA_ENV))
    if _SCRIPTS_ENV.exists():
        load_dotenv(dotenv_path=str(_SCRIPTS_ENV), override=False)


# ── SSL 검증 비활성화 WebClient (nova_helper.py 방식 — 사내 프록시 우회) ──────
def _build_client(token: str):
    from slack_sdk.web import WebClient
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return WebClient(token=token, ssl=ssl_context)


# ── 모델 문자열 해석 (model_config.json default 프리셋 재사용) ────────────────
def _resolve_model() -> str:
    try:
        cfg = json.loads(_MODEL_CONFIG.read_text(encoding="utf-8"))
        model = cfg.get("presets", {}).get("default", {}).get("execution_model")
        if model:
            return model
    except Exception:
        pass
    return MODEL_FALLBACK


def _anthropic_key() -> str:
    return os.environ.get("CLAUDE_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")


# ── 상태 파일 R/W ─────────────────────────────────────────────────────────────
def _read_last_run_ts() -> float | None:
    if not _STATE_FILE.exists():
        return None
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        ts = data.get("last_run_ts")
        return float(ts) if ts is not None else None
    except Exception as e:
        print(f"[digest] 상태 파일 읽기 실패(무시): {e}")
        return None


def _write_last_run_ts(ts: float) -> None:
    _STATUS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_run_ts": ts,
        "last_run_iso": datetime.fromtimestamp(ts, KST).isoformat(),
    }
    _STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Slack: 대상 유저 ID 해석 ─────────────────────────────────────────────────
def _resolve_target_user_id(user_client) -> str:
    env_uid = os.environ.get("SLACK_TARGET_USER_ID", "").strip()
    if env_uid:
        return env_uid
    resp = user_client.auth_test()
    uid = resp.get("user_id")
    if not uid:
        raise RuntimeError("auth.test 로 대상 유저 ID를 확인하지 못했습니다. SLACK_TARGET_USER_ID 를 설정하세요.")
    return uid


# ── Slack: search.messages 로 멘션 검색 (유저 토큰 전용) ──────────────────────
def _search_mentions(user_client, user_id: str, window_start: float, window_end: float) -> list[dict]:
    """
    <@USERID> 를 포함하는 메시지를 검색한다. search after: 는 날짜 단위이므로
    검색 후 클라이언트 측에서 [window_start, window_end] ts 범위로 재필터링한다.
    """
    from slack_sdk.errors import SlackApiError

    # after: 는 '해당 날짜 이후' 이므로 하루 여유를 두고 넓게 조회 후 ts로 정밀 필터.
    after_date = datetime.fromtimestamp(window_start, KST).date() - timedelta(days=1)
    query = f"<@{user_id}> after:{after_date.isoformat()}"

    matches: list[dict] = []
    for page in range(1, SEARCH_MAX_PAGES + 1):
        try:
            resp = user_client.search_messages(
                query=query,
                count=SEARCH_PAGE_LIMIT,
                page=page,
                sort="timestamp",
                sort_dir="desc",
            )
        except SlackApiError as e:
            err = e.response.get("error", "") if getattr(e, "response", None) else str(e)
            if err == "missing_scope":
                raise RuntimeError(
                    "Slack search.messages 호출에 search:read 스코프가 필요합니다. "
                    "search:read 권한이 부여된 유저 토큰(xoxp)을 SLACK_USER_TOKEN 에 설정하세요."
                )
            raise RuntimeError(f"search.messages 실패: {err}")

        page_matches = resp.get("messages", {}).get("matches", [])
        matches.extend(page_matches)

        paging = resp.get("messages", {}).get("paging", {})
        if page >= paging.get("pages", 1) or not page_matches:
            break

    # ts 정밀 필터 + 멘션 실제 포함 여부 확인(with: 류 오탐 방지)
    mention_token = f"<@{user_id}>"
    filtered = []
    for m in matches:
        try:
            ts = float(m.get("ts", "0"))
        except (TypeError, ValueError):
            continue
        if not (window_start <= ts <= window_end):
            continue
        if mention_token not in (m.get("text") or ""):
            continue
        filtered.append(m)
    return filtered


# ── Slack: 스레드 수집 + 중복 제거 + 멘션 재확인 ─────────────────────────────
def _collect_threads(user_client, matches: list[dict], user_id: str,
                     window_start: float, window_end: float) -> list[dict]:
    """
    각 검색 히트에서 (channel, thread_ts) 를 뽑아 conversations.replies 로
    스레드 전체를 가져온다. (channel, thread_ts) 기준 중복 제거하고,
    윈도우 내에서 실제로 <@USERID> 를 포함한 메시지가 있는 스레드만 유지한다.
    """
    from slack_sdk.errors import SlackApiError

    mention_token = f"<@{user_id}>"
    seen: set[tuple[str, str]] = set()
    threads: list[dict] = []

    for m in matches:
        channel = (m.get("channel") or {}).get("id") or m.get("channel")
        if isinstance(channel, dict):
            channel = channel.get("id")
        if not channel:
            continue
        # 스레드 루트 ts: thread_ts 가 있으면 그것, 없으면 메시지 ts(스레드 시작).
        thread_ts = m.get("thread_ts") or m.get("ts")
        if not thread_ts:
            continue
        key = (channel, thread_ts)
        if key in seen:
            continue
        seen.add(key)

        try:
            replies = user_client.conversations_replies(
                channel=channel, ts=thread_ts, limit=200,
            )
        except SlackApiError as e:
            err = e.response.get("error", "") if getattr(e, "response", None) else str(e)
            print(f"[digest] conversations.replies 실패({channel}/{thread_ts}): {err}")
            continue

        msgs = replies.get("messages", [])
        if not msgs:
            continue

        # 윈도우 내에서 실제로 유저를 태그한 메시지가 있는지 확인
        tagging_msgs = []
        for msg in msgs:
            try:
                mts = float(msg.get("ts", "0"))
            except (TypeError, ValueError):
                continue
            if window_start <= mts <= window_end and mention_token in (msg.get("text") or ""):
                tagging_msgs.append(msg)
        if not tagging_msgs:
            continue

        threads.append({
            "channel": channel,
            "thread_ts": thread_ts,
            "messages": msgs,
            "tagging_messages": tagging_msgs,
        })

    return threads


# ── Slack 부가 정보: 채널명 / 유저명 / permalink ─────────────────────────────
def _channel_name(user_client, channel: str, cache: dict) -> str:
    if channel in cache:
        return cache[channel]
    name = channel
    try:
        info = user_client.conversations_info(channel=channel)
        ch = info.get("channel", {})
        name = ch.get("name") or ("DM" if ch.get("is_im") else channel)
    except Exception:
        pass
    cache[channel] = name
    return name


def _user_name(user_client, uid: str, cache: dict) -> str:
    if not uid:
        return "알 수 없음"
    if uid in cache:
        return cache[uid]
    name = uid
    try:
        info = user_client.users_info(user=uid)
        u = info.get("user", {})
        prof = u.get("profile", {})
        name = prof.get("display_name") or prof.get("real_name") or u.get("name") or uid
    except Exception:
        pass
    cache[uid] = name
    return name


def _permalink(user_client, channel: str, ts: str) -> str:
    try:
        resp = user_client.chat_getPermalink(channel=channel, message_ts=ts)
        return resp.get("permalink", "")
    except Exception:
        return ""


# ── 스레드 → 요약 입력용 구조화 ──────────────────────────────────────────────
def _build_thread_context(user_client, threads: list[dict], user_id: str) -> list[dict]:
    ch_cache: dict = {}
    user_cache: dict = {}
    contexts = []
    for t in threads:
        channel = t["channel"]
        thread_ts = t["thread_ts"]
        ch_name = _channel_name(user_client, channel, ch_cache)
        permalink = _permalink(user_client, channel, thread_ts)

        taggers = []
        for tm in t["tagging_messages"]:
            taggers.append(_user_name(user_client, tm.get("user", ""), user_cache))
        taggers = sorted(set(taggers))

        transcript = []
        for msg in t["messages"]:
            speaker = _user_name(user_client, msg.get("user", ""), user_cache)
            text = (msg.get("text") or "").strip()
            if not text:
                continue
            transcript.append(f"{speaker}: {text}")

        contexts.append({
            "channel_name": ch_name,
            "permalink": permalink,
            "taggers": taggers,
            "transcript": transcript,
        })
    return contexts


# ── 리포트 생성 (LLM) ────────────────────────────────────────────────────────
def _summarize_with_llm(contexts: list[dict], model: str, api_key: str,
                        window_start: float, window_end: float) -> str:
    import anthropic

    ws = datetime.fromtimestamp(window_start, KST).strftime("%Y-%m-%d %H:%M")
    we = datetime.fromtimestamp(window_end, KST).strftime("%Y-%m-%d %H:%M")

    blocks = []
    for i, c in enumerate(contexts, 1):
        transcript = "\n".join(c["transcript"])[:4000]
        blocks.append(
            f"### 스레드 {i}\n"
            f"- 채널: {c['channel_name']}\n"
            f"- 나를 태그한 사람: {', '.join(c['taggers']) or '알 수 없음'}\n"
            f"- 링크: {c['permalink'] or '(링크 없음)'}\n"
            f"- 대화 내용:\n{transcript}"
        )
    joined = "\n\n".join(blocks)

    prompt = f"""당신은 유능한 비서입니다. 아래는 Slack에서 '나'(박성환)가 @-태그된 스레드들의 대화입니다.
수집 구간: {ws} ~ {we} (Asia/Seoul)

각 스레드마다 아래 항목을 한국어로 정리하세요:
- 채널
- 스레드 주제
- 나를 태그한 사람
- 핵심 내용/맥락
- 나에게 요구되는 액션아이템 (없으면 '없음')
- 링크

모든 스레드 정리가 끝나면, 마지막에 '## 우선순위 요약' 섹션을 추가하여
가장 먼저 처리해야 할 항목부터 순서대로 나열하세요.

간결하고 실무적으로, 마크다운으로 작성하세요.

---
{joined}
"""

    ac = anthropic.Anthropic(api_key=api_key)
    last_err = None
    for attempt in range(4):
        try:
            msg = ac.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except Exception as e:
            last_err = e
            if "overloaded" in str(e).lower() or "529" in str(e):
                wait = 10 * (attempt + 1)
                print(f"[digest] Anthropic 과부하, {wait}초 후 재시도 ({attempt+1}/4)")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Anthropic 4회 재시도 실패: {last_err}")


# ── 리포트 생성 (비-LLM 폴백) ────────────────────────────────────────────────
def _plaintext_report(contexts: list[dict], window_start: float, window_end: float) -> str:
    ws = datetime.fromtimestamp(window_start, KST).strftime("%Y-%m-%d %H:%M")
    we = datetime.fromtimestamp(window_end, KST).strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# 태그된 스레드 다이제스트 (요약 없음)",
        f"수집 구간: {ws} ~ {we} (Asia/Seoul)",
        f"총 {len(contexts)}개 스레드",
        "",
        "> Anthropic 키가 없어 LLM 요약을 건너뛰고 원문 목록만 제공합니다.",
        "",
    ]
    for i, c in enumerate(contexts, 1):
        excerpt = " / ".join(c["transcript"][:3])[:500]
        lines.extend([
            f"## 스레드 {i} — {c['channel_name']}",
            f"- 나를 태그한 사람: {', '.join(c['taggers']) or '알 수 없음'}",
            f"- 링크: {c['permalink'] or '(링크 없음)'}",
            f"- 발췌: {excerpt}",
            "",
        ])
    return "\n".join(lines)


# ── 리포트 저장 ───────────────────────────────────────────────────────────────
def _save_report(report: str) -> Path:
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"tagged_digest_{datetime.now(KST).strftime('%Y%m%d_%H%M')}.md"
    path = _OUT_DIR / fname
    path.write_text(report, encoding="utf-8")
    return path


# ── Slack 게시 (긴 리포트는 청크 분할) ───────────────────────────────────────
def _chunk_text(text: str, size: int = 2900) -> list[str]:
    chunks = []
    remaining = text
    while remaining:
        if len(remaining) <= size:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", 0, size)
        if cut <= 0:
            cut = size
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    return chunks


def _post_report(post_client, channel: str, report: str) -> None:
    from slack_sdk.errors import SlackApiError
    chunks = _chunk_text(report)
    for idx, chunk in enumerate(chunks):
        prefix = "" if idx == 0 else f"(이어서 {idx+1}/{len(chunks)})\n"
        try:
            post_client.chat_postMessage(
                channel=channel,
                text=f"태그된 스레드 다이제스트\n{chunk}"[:3900],
                blocks=[{
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"{prefix}{chunk}"[:2990]},
                }],
            )
        except SlackApiError as e:
            err = e.response.get("error", "") if getattr(e, "response", None) else str(e)
            raise RuntimeError(f"chat.postMessage 실패: {err}")


# ── 메인 진입점 ───────────────────────────────────────────────────────────────
def run_digest(dry_run: bool = False, window_hours: int | None = None) -> str:
    """
    태그된 스레드를 수집·요약해 한국어 리포트를 생성/게시하고 리포트 텍스트를 반환한다.
    dry_run=True 이면 Slack 게시와 상태 파일 갱신을 건너뛰고 리포트만 반환한다.
    """
    _load_env()

    user_token = os.environ.get("SLACK_USER_TOKEN", "").strip()
    if not user_token:
        raise RuntimeError(
            "SLACK_USER_TOKEN 이 필요합니다. search.messages 는 유저 토큰(xoxp) 전용이며 "
            "search:read 스코프가 있어야 합니다. 봇 토큰으로는 검색할 수 없습니다."
        )

    user_client = _build_client(user_token)

    # 게시용 클라이언트: 봇 토큰 우선, 없으면 유저 토큰.
    bot_token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    post_client = _build_client(bot_token) if bot_token else user_client

    user_id = _resolve_target_user_id(user_client)
    print(f"[digest] 대상 유저 ID: {user_id}")

    # ── 시간 윈도우 ──────────────────────────────────────────────────────────
    now_ts = datetime.now(KST).timestamp()
    if window_hours is not None:
        window_start = now_ts - window_hours * 3600
    else:
        last = _read_last_run_ts()
        window_start = last if last is not None else now_ts - DEFAULT_WINDOW_HOURS * 3600
    window_end = now_ts

    ws_str = datetime.fromtimestamp(window_start, KST).strftime("%Y-%m-%d %H:%M")
    we_str = datetime.fromtimestamp(window_end, KST).strftime("%Y-%m-%d %H:%M")
    print(f"[digest] 수집 구간: {ws_str} ~ {we_str} (KST)")

    # ── 수집 ──────────────────────────────────────────────────────────────────
    matches = _search_mentions(user_client, user_id, window_start, window_end)
    print(f"[digest] 검색 히트(윈도우 필터 후): {len(matches)}건")

    threads = _collect_threads(user_client, matches, user_id, window_start, window_end)
    print(f"[digest] 유효 스레드(중복 제거 후): {len(threads)}개")

    if not threads:
        report = (
            f"# 태그된 스레드 다이제스트\n"
            f"수집 구간: {ws_str} ~ {we_str} (Asia/Seoul)\n\n"
            f"이 구간에 나를 @-태그한 새 스레드가 없습니다."
        )
    else:
        contexts = _build_thread_context(user_client, threads, user_id)
        api_key = _anthropic_key()
        if api_key:
            model = _resolve_model()
            print(f"[digest] 요약 모델: {model}")
            try:
                report = _summarize_with_llm(contexts, model, api_key, window_start, window_end)
            except Exception as e:
                print(f"[digest] LLM 요약 실패, 폴백 리포트로 전환: {e}")
                report = _plaintext_report(contexts, window_start, window_end)
        else:
            print("[digest] Anthropic 키 없음 — 비-LLM 폴백 리포트 생성")
            report = _plaintext_report(contexts, window_start, window_end)

    # ── 저장 (항상) ────────────────────────────────────────────────────────────
    saved = _save_report(report)
    print(f"[digest] 리포트 저장: {saved}")

    if dry_run:
        print("[digest] --dry-run: Slack 게시 및 상태 갱신 생략")
        print("\n" + "=" * 60)
        print(report)
        print("=" * 60)
        return report

    # ── 게시 ──────────────────────────────────────────────────────────────────
    channel = os.environ.get("TAGGED_DIGEST_CHANNEL", "").strip() or user_id
    try:
        _post_report(post_client, channel, report)
        print(f"[digest] Slack 게시 완료 → {channel}")
    except Exception as e:
        print(f"[digest] Slack 게시 실패(파일은 저장됨): {e}")
        # 게시 실패해도 스케줄러를 죽이지 않는다. 상태는 갱신하지 않음(다음 실행 재시도).
        return report

    # ── 상태 갱신 (게시 성공 시에만) ──────────────────────────────────────────
    _write_last_run_ts(window_end)
    print(f"[digest] 상태 갱신 완료 (last_run_ts={window_end})")

    return report


# ── CLI ───────────────────────────────────────────────────────────────────────
def _main() -> int:
    parser = argparse.ArgumentParser(
        description="태그된 Slack 스레드 다이제스트 수집·요약·전달"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="게시/상태갱신 없이 리포트만 생성·출력")
    parser.add_argument("--window-hours", type=int, default=None,
                        help="수집 구간을 지금부터 N시간 전으로 강제(상태 파일 무시)")
    args = parser.parse_args()

    try:
        run_digest(dry_run=args.dry_run, window_hours=args.window_hours)
        return 0
    except Exception as e:
        print(f"[digest] 오류: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(_main())
