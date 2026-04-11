#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pm_pipeline.py
Slack 입력값 → 마크다운 생성 → Gemini PPT → Confluence 업로드 → Slack 알림
nova_helper.py가 import해서 백그라운드 스레드로 실행한다.
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime

_BASE    = Path(__file__).parent.parent
_SCRIPTS = _BASE / ".scripts"
sys.path.insert(0, str(_SCRIPTS))

from pm_ppt_generator import call_gemini, build_pptx, update_index
from confluence_plugin import create_pm_page, upload_pptx_attachment, CONFLUENCE_SPACE_KEY

OUTPUT_DIR = _BASE / "global" / "05_PM_Outputs"

ICON = {"done": "✅", "running": "⏳", "pending": "○", "error": "❌"}


# ── 진행 상황 트래커 ──────────────────────────────────────────────────────────

class ProgressTracker:
    """
    Slack 메시지 하나를 고정으로 올리고 단계마다 chat_update로 갱신한다.

    steps: [{"label": "...", "detail": ""}]  ← 순서대로 정의
    """

    def __init__(self, client, channel_id: str, user_id: str,
                 context: str, quarter: str, steps: list[dict]):
        self.client     = client
        self.channel_id = channel_id
        self.user_id    = user_id
        self.context    = context
        self.quarter    = quarter
        self.steps      = [dict(s, state="pending", detail="") for s in steps]
        self.ts         = None  # 메시지 timestamp
        self._post_initial()

    def _build_blocks(self, header: str) -> list:
        step_lines = []
        for i, s in enumerate(self.steps):
            icon   = ICON[s["state"]]
            label  = s["label"]
            detail = f"  _({s['detail']})_" if s.get("detail") else ""
            step_lines.append(f"{icon}  *{i+1}.* {label}{detail}")

        return [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f":robot_face: *{header}*"},
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(step_lines)},
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn",
                     "text": f"컨텍스트: *{self.context}* / {self.quarter}"}
                ],
            },
        ]

    def _post_initial(self):
        resp = self.client.chat_postMessage(
            channel=self.channel_id,
            text="OKR 파이프라인 시작",
            blocks=self._build_blocks("OKR 파이프라인 시작"),
        )
        self.ts = resp["ts"]
        self.channel_id = resp["channel"]  # DM 실제 채널 ID(D...) 로 교체

    def start(self, step_idx: int):
        """step_idx 단계를 실행 중으로 표시."""
        self.steps[step_idx]["state"] = "running"
        self.steps[step_idx]["detail"] = ""
        self._update(f"Step {step_idx + 1} 진행 중...")

    def done(self, step_idx: int, detail: str = ""):
        """step_idx 단계를 완료로 표시."""
        self.steps[step_idx]["state"] = "done"
        self.steps[step_idx]["detail"] = detail
        self._update(f"Step {step_idx + 1} 완료")

    def error(self, step_idx: int, msg: str):
        """step_idx 단계를 오류로 표시."""
        self.steps[step_idx]["state"] = "error"
        self.steps[step_idx]["detail"] = msg
        self._update(f"오류 발생")

    def finish(self, page_url: str, pptx_name: str,
               slide_count: int, md_filename: str):
        """최종 완료 메시지로 업데이트 + Confluence 버튼 추가."""
        blocks = self._build_blocks("OKR 파이프라인 완료 ✅")
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*마크다운*\n`{md_filename}`"},
                {"type": "mrkdwn", "text": f"*PPT*\n`{pptx_name}` ({slide_count}장)"},
            ],
        })
        if page_url and page_url != "업로드 미선택":
            blocks.append({
                "type": "actions",
                "elements": [{
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Confluence에서 열기"},
                    "style": "primary",
                    "url": page_url,
                    "action_id": "open_confluence_page",
                }],
            })
        self.client.chat_update(
            channel=self.channel_id,
            ts=self.ts,
            text="OKR 파이프라인 완료",
            blocks=blocks,
        )

    def fail(self, error_msg: str):
        """전체 실패 메시지로 업데이트."""
        blocks = self._build_blocks("OKR 파이프라인 오류 ❌")
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"```{error_msg[:400]}```"},
        })
        self.client.chat_update(
            channel=self.channel_id,
            ts=self.ts,
            text="파이프라인 오류",
            blocks=blocks,
        )

    def _update(self, header: str):
        self.client.chat_update(
            channel=self.channel_id,
            ts=self.ts,
            text=header,
            blocks=self._build_blocks(f"OKR 파이프라인 — {header}"),
        )


# ── Claude API로 OKR 마크다운 생성 ───────────────────────────────────────────

def _generate_okr_markdown(context: str, quarter: str, keywords: str) -> str:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic 패키지 필요: pip install anthropic")

    api_key = os.environ.get("CLAUDE_API_KEY", "")
    if not api_key:
        raise RuntimeError("CLAUDE_API_KEY 미설정")

    ac = anthropic.Anthropic(api_key=api_key)
    prompt = f"""당신은 경험 많은 PM입니다. 아래 정보를 바탕으로 {quarter} OKR 브레인스토밍 문서를 작성하세요.


제품/컨텍스트: {context}
핵심 전략 키워드: {keywords}

아래 형식으로 한국어 마크다운 문서를 작성하세요:

## 전략 맥락
| 전략 축 | 핵심 과제 | 비즈니스 임팩트 |
...

## OKR Set A — [전략 이름]
> 슬로건

| 구분 | 내용 |
| **Objective** | ... |
| **KR 1** | ... |
| **KR 2** | ... |
| **KR 3** | ... |

**전략적 근거:** ...

## OKR Set B — [전략 이름]
(동일 구조)

## OKR Set C — [전략 이름]
(동일 구조)

## 권장 선택 가이드
| 팀 상황 | 추천 OKR |
...

최대한 구체적이고 실행 가능한 수치와 근거를 포함하세요."""

    import time
    last_err = None
    for attempt in range(4):          # 최대 4회 시도
        try:
            msg = ac.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except Exception as e:
            last_err = e
            if "overloaded" in str(e).lower() or "529" in str(e):
                wait = 10 * (attempt + 1)   # 10s → 20s → 30s → 40s
                print(f"[pipeline] Claude API 과부하, {wait}초 후 재시도 ({attempt+1}/4)")
                time.sleep(wait)
            else:
                raise                       # 다른 오류는 즉시 raise
    raise RuntimeError(f"Claude API 4회 재시도 실패: {last_err}")


# ── 마크다운 저장 ─────────────────────────────────────────────────────────────

def _save_markdown(md_body: str, skill: str, context: str, date_str: str) -> Path:
    ctx_slug = re.sub(r"[^\w가-힣]", "-", context)[:30].strip("-").lower()
    filename = f"{skill}_{ctx_slug}_{date_str}.md"
    path = OUTPUT_DIR / filename
    frontmatter = f"---\nskill: {skill}\ncontext: {context}\ndate: {date_str}\n---\n\n"
    path.write_text(frontmatter + md_body, encoding="utf-8")
    return path


# ── 메인 파이프라인 ───────────────────────────────────────────────────────────

def run_okr_pipeline(
    context: str,
    quarter: str,
    keywords: str,
    do_ppt: bool,
    do_confluence: bool,
    parent_page_id: str,
    user_id: str,
    channel_id: str,
    slack_client,
) -> None:
    date_str = datetime.today().strftime("%Y-%m-%d")
    skill    = "brainstorm-okrs"

    # 단계 목록 (옵션에 따라 동적 구성)
    steps = [{"label": "Claude AI — OKR 마크다운 생성"}]
    if do_ppt:
        steps.append({"label": "Gemini AI — 슬라이드 구조화 + PPT 생성"})
    if do_confluence:
        steps.append({"label": "Confluence — 페이지 생성 + PPT 첨부"})

    tracker = ProgressTracker(
        slack_client, channel_id, user_id,
        context, quarter, steps,
    )

    try:
        # ── Step 0: 마크다운 생성 ────────────────────────────────────────────
        tracker.start(0)
        md_body = _generate_okr_markdown(context, quarter, keywords)
        md_path = _save_markdown(md_body, skill, context, date_str)
        tracker.done(0, md_path.name)

        pptx_path   = None
        slide_count = 0
        step_idx    = 1

        # ── Step 1: PPT 생성 (선택) ──────────────────────────────────────────
        if do_ppt:
            tracker.start(step_idx)
            md_text   = md_path.read_text(encoding="utf-8")
            slides    = call_gemini(md_text, skill)
            meta      = {"skill": skill, "context": context, "date": date_str}
            pptx_path = OUTPUT_DIR / f"{md_path.stem}.pptx"
            build_pptx(slides, pptx_path, meta)
            slide_count = len(slides) + 2
            update_index(OUTPUT_DIR)
            tracker.done(step_idx, f"{pptx_path.name} ({slide_count}장)")
            step_idx += 1

        # ── Step 2: Confluence 업로드 (선택) ─────────────────────────────────
        page_url = ""
        if do_confluence:
            tracker.start(step_idx)
            title = f"[OKR] {context} ({date_str})"
            page_id, page_url = create_pm_page(
                title, md_body,
                space_key=CONFLUENCE_SPACE_KEY,
                parent_page_id=parent_page_id,
            )
            if do_ppt and pptx_path and pptx_path.exists():
                upload_pptx_attachment(page_id, pptx_path)
            tracker.done(step_idx, "업로드 완료")

        # ── 완료 ─────────────────────────────────────────────────────────────
        tracker.finish(
            page_url=page_url or "업로드 미선택",
            pptx_name=pptx_path.name if pptx_path else "미생성",
            slide_count=slide_count,
            md_filename=md_path.name,
        )

    except Exception as e:
        print(f"[pipeline] 오류: {e}")
        tracker.fail(str(e))
