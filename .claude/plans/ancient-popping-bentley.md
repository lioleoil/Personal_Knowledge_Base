# Plan: Nova Helper PM Skill Pipeline (Slack → Markdown → PPT → Confluence)

## Context
사용자가 Slack을 UI로, 로컬 머신을 서버로 사용하는 PM 스킬 자동화 파이프라인을 요청했다.
- `/nova_pm` Slack 명령어 → 모달 폼 → OKR 입력 → 마크다운 생성 → Gemini PPT → Confluence 업로드 → Slack 알림

## 기존 재사용 가능한 자산

| 자산 | 경로 | 재사용 함수 |
|---|---|---|
| Slack Bolt 봇 | `nova_helper/nova_helper.py` | 커맨드 핸들러 패턴 |
| PPT 생성기 | `pm_ppt_generator.py` | `parse_frontmatter`, `call_gemini`, `build_pptx`, `update_index` |
| Confluence 업로드 | `.scripts/doc_gen.py` | `create_confluence_page`, `markdown_to_storage` |
| 환경변수 | `.scripts/.env` | `CONFLUENCE_*`, `SLACK_*`, `GEMINI_API_KEY` |

## 아키텍처

```
[Slack User]
    │ /nova_pm → 모달 열기
    ▼
[nova_helper.py — Socket Mode]
    │ view_submission 수신
    ├─ ① 마크다운 생성 (Claude 스킬 결과 → 파일로 저장)
    ├─ ② Gemini PPT 생성 (pm_ppt_generator.call_gemini + build_pptx)
    ├─ ③ Confluence 페이지 생성 + PPTX 첨부 (doc_gen.create_confluence_page + 첨부 API)
    └─ ④ Slack DM 알림 (완료 + Confluence 링크)
[05_PM_Outputs/] ← 로컬 파일 저장
[Confluence TE 스페이스] ← 업로드 완료
```

## 구현 계획

### Step 1: `nova_helper/confluence_plugin.py` 신규 생성
`doc_gen.py`의 Confluence 함수를 가져와 pm skill 전용으로 래핑

```python
# 재사용: doc_gen.py의 _make_auth_header(), markdown_to_storage()
# 신규: upload_pptx_attachment(page_id, pptx_path) — REST API /child/attachment
def create_pm_page(title, md_text, space_key) -> str:  # returns page URL
def upload_pptx_attachment(page_id, pptx_path) -> str:  # returns attachment URL
```

### Step 2: `nova_helper/pm_pipeline.py` 신규 생성
전체 파이프라인을 하나의 함수로 래핑 (nova_helper가 import해서 쓸 모듈)

```python
import sys; sys.path.insert(0, ...)
from pm_ppt_generator import call_gemini, build_pptx, parse_frontmatter, update_index
from confluence_plugin import create_pm_page, upload_pptx_attachment

def run_okr_pipeline(context: str, quarter: str, keywords: str, user_id: str, channel_id: str, slack_client) -> None:
    # 1. 마크다운 생성 (OKR 템플릿 기반)
    # 2. call_gemini + build_pptx
    # 3. Confluence 페이지 생성 + PPTX 첨부
    # 4. Slack 완료 알림
```

### Step 3: `nova_helper/nova_helper.py` 수정
기존 파일에 `/nova_pm` 커맨드 + `view_submission` 핸들러 추가

```python
@app.command("/nova_pm")
def handle_nova_pm(ack, body, client):
    ack()
    client.views_open(trigger_id=body["trigger_id"], view=OKR_MODAL)

@app.view("nova_pm_modal")
def handle_submission(ack, body, client, view):
    ack()
    values = view["state"]["values"]
    # 입력값 추출 → threading.Thread(target=run_okr_pipeline, ...).start()
```

### Slack 모달 필드 구성 (`OKR_MODAL`)
```
1. PM 스킬 선택    — static_select (OKR / PRD / 회고 / 회의록)
2. 컨텍스트        — plain_text_input (예: Nova Platform Q2)
3. 전략 키워드     — plain_text_input (예: 유저 활성화 / 아키텍처 전환)
4. 산출물 옵션     — checkboxes (마크다운 저장 / PPT 생성 / Confluence 업로드)
5. Confluence 페이지 ID (optional) — plain_text_input (비워두면 신규 생성)
```

### Confluence 업로드 플로우
1. `create_pm_page(title, md_text, CONFLUENCE_SPACE_KEY)` → `page_id`, `page_url` 반환
2. `upload_pptx_attachment(page_id, pptx_path)` → 첨부 API `POST /rest/api/content/{id}/child/attachment`

### Slack 완료 알림 Block Kit
```json
{
  "blocks": [
    {"type": "section", "text": "✅ PM 산출물 생성 완료"},
    {"type": "section", "text": "📄 Confluence: {page_url}"},
    {"type": "section", "text": "📊 슬라이드: {slides}장 생성됨"}
  ]
}
```

## 수정 파일 목록

| 파일 | 작업 |
|---|---|
| `nova_helper/confluence_plugin.py` | 신규 생성 — Confluence 업로드 래퍼 |
| `nova_helper/pm_pipeline.py` | 신규 생성 — 전체 파이프라인 오케스트레이터 |
| `nova_helper/nova_helper.py` | 수정 — `/nova_pm` 커맨드 + 모달 핸들러 추가 |
| `nova_helper/requirements.txt` | 수정 — `markdown`, `requests` 추가 확인 |

## 검증 방법
1. `python nova_helper/nova_helper.py` 실행
2. Slack에서 `/nova_pm` 입력 → 모달 확인
3. 폼 제출 → 로컬 `05_PM_Outputs/`에 .md + .pptx 생성 확인
4. Confluence TE 스페이스에 페이지 + 첨부파일 생성 확인
5. Slack DM에 완료 알림 + 링크 수신 확인
