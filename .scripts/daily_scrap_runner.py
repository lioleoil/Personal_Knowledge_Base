"""
Daily Scrap 전체 파이프라인 실행자
Task Scheduler 또는 CronCreate Agent 에서 호출

흐름: 수집(daily_scrap.py) → claude -p 요약 → Daily_Scrap.md 저장 → 팝업 알림
"""
import sys, json, subprocess, re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))
from agent_log import AgentLog, PROJECT_ROOT

PROJECT    = Path(PROJECT_ROOT)
STAGING    = PROJECT / "projects/04_WorkLog/Daily_Scrap/.staging.json"
OUTPUT_MD  = PROJECT / "projects/04_WorkLog/Daily_Scrap/Daily_Scrap.md"
RESULT_JSON= PROJECT / "projects/04_WorkLog/Daily_Scrap/.scrap_result.json"
COLLECTOR  = PROJECT / ".scripts/daily_scrap.py"
POPUP      = PROJECT / ".scripts/scrap_popup.py"

HEADER = (
    "# Daily Scrap — GeekNews 자동 수집\n"
    "> 매일 09:00 자동 업데이트 | 출처: https://news.hada.io\n\n"
    "---\n\n"
)


# ── 중복 방지 ─────────────────────────────────────────────────────────────────
def already_done_today(date_str: str) -> bool:
    if not OUTPUT_MD.exists():
        return False
    return f"## {date_str}" in OUTPUT_MD.read_text(encoding="utf-8")


# ── 요약 (claude -p) ──────────────────────────────────────────────────────────
def summarize_via_claude(title: str, description: str, topic: str) -> str:
    prompt = (
        f"다음 기사를 한국어 3줄로 요약해줘. "
        f"각 줄은 '- '로 시작. 세 줄만 출력.\n\n"
        f"제목: {title}\n"
        f"설명: {description[:400]}\n"
        f"토픽: {topic}"
    )
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True,
            timeout=90, encoding="utf-8", errors="replace"
        )
        if result.returncode == 0:
            text = result.stdout.strip()
            if text:
                return text
    except FileNotFoundError:
        pass  # claude CLI 미설치
    except subprocess.TimeoutExpired:
        pass

    # 폴백: 설명 텍스트를 정리해서 반환
    raw_lines = [l.strip().lstrip("- ").strip() for l in description.split("\n") if l.strip()]
    return "\n".join(f"- {l}" for l in raw_lines[:3]) or f"- {description[:200]}"


# ── 마크다운 포맷 ─────────────────────────────────────────────────────────────
def format_entry(article: dict, summary: str) -> str:
    source = urlparse(article["url"]).netloc
    return "\n".join([
        f"### [{article['title']}]({article['url']})",
        f"**토픽:** {article['topic']} | **출처:** {source}",
        "",
        summary,
        "",
        "---",
        "",
    ])


# ── 파일 저장 ─────────────────────────────────────────────────────────────────
def append_to_scrap(date_str: str, entries: list[str]) -> None:
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    date_section = f"## {date_str}\n\n" + "\n".join(entries)

    if not OUTPUT_MD.exists():
        OUTPUT_MD.write_text(HEADER + date_section, encoding="utf-8")
        return

    existing = OUTPUT_MD.read_text(encoding="utf-8")
    header_end = existing.find("\n## ")
    if header_end == -1:
        OUTPUT_MD.write_text(existing.rstrip() + "\n\n" + date_section, encoding="utf-8")
        return

    file_header = existing[:header_end + 1]
    body = existing[header_end + 1:]
    date_marker = f"## {date_str}"

    if date_marker in body:
        # 날짜 섹션 이미 존재 → 섹션 끝에 추가
        idx = body.index(date_marker)
        next_sec = body.find("\n## ", idx + 1)
        if next_sec == -1:
            new_body = body.rstrip() + "\n\n" + "\n".join(entries)
        else:
            new_body = body[:next_sec] + "\n" + "\n".join(entries) + body[next_sec:]
    else:
        # 최신 날짜를 맨 위에 prepend
        new_body = date_section + "\n" + body

    OUTPUT_MD.write_text(file_header + new_body, encoding="utf-8")


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    date_str = datetime.now().strftime("%Y-%m-%d")

    # 중복 실행 방지
    if already_done_today(date_str):
        print(f"[SKIP] {date_str} 이미 처리됨", flush=True)
        return

    log = AgentLog(
        agent_id=f"DailyScrapRunner_{date_str}",
        title="Daily Scrap 전체 실행",
        agent_type="daily_scrap",
    )

    try:
        # 1. 수집
        log.update(progress=10, message="기사 수집 중")
        result = subprocess.run(
            [sys.executable, str(COLLECTOR)],
            capture_output=True, text=True,
            timeout=120, encoding="utf-8", errors="replace"
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or '')[:500]
            log.error(f"수집 실패: {detail}")
            return

        # 2. 스테이징 읽기
        if not STAGING.exists():
            log.done("새 기사 없음 (중복 또는 미수집)")
            return

        data     = json.loads(STAGING.read_text(encoding="utf-8"))
        articles = data.get("articles", [])
        if not articles:
            log.done("선택된 기사 없음")
            return
        log.add(f"선택 기사: {len(articles)}개")

        # 3. 요약 + 포맷
        entries = []
        for i, article in enumerate(articles, 1):
            log.update(progress=20 + i * 20, message=f"요약 중 ({i}/{len(articles)})")
            log.add(f"요약: {article['title'][:40]}")
            summary = summarize_via_claude(
                article["title"],
                article.get("description", ""),
                article["topic"],
            )
            entries.append(format_entry(article, summary))

        # 4. Daily_Scrap.md 저장
        log.update(progress=90, message="파일 저장 중")
        append_to_scrap(date_str, entries)
        log.add(f"저장: {OUTPUT_MD}")

        # 5. 팝업용 결과 JSON 저장
        RESULT_JSON.write_text(
            json.dumps({
                "date":     date_str,
                "count":    len(articles),
                "articles": [{"title": a["title"], "topic": a["topic"], "url": a["url"]} for a in articles],
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 6. 스테이징 삭제
        STAGING.unlink(missing_ok=True)

        # 7. 팝업 알림 (비블로킹)
        if POPUP.exists():
            subprocess.Popen([sys.executable, str(POPUP)])

        log.done(f"{len(articles)}개 기사 스크랩 완료")
        print(f"[OK] {OUTPUT_MD}", flush=True)

    except Exception as e:
        log.error(str(e))
        raise


if __name__ == "__main__":
    main()
