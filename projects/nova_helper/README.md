# Nova Helper — Slack Bot

Nova 워크스페이스 Slack 봇. Slack Bolt(Socket Mode) 기반 플러그인 아키텍처로 구동되며, Confluence 연동 및 PM 스킬 파이프라인을 지원한다.

## 구조

```
nova_helper/
├── nova_helper.py       # 앱 진입점 — Slack Bolt 초기화 + 플러그인 자동 로더
├── nova_okr.py          # /nova_okr 슬래시 커맨드 — OKR 브레인스토밍 모달 + 파이프라인
├── confluence_plugin.py # Confluence REST API — 페이지 생성·PPTX 첨부
├── pm_pipeline.py       # OKR 파이프라인 오케스트레이터 (Claude → Gemini → Confluence)
└── requirements.txt     # 패키지 의존성
```

## 플러그인 아키텍처

`nova_helper.py`는 같은 디렉터리의 `nova_*.py` 파일을 자동 탐색하여 `register(app)` 함수가 있으면 등록한다.

```python
# 새 기능 추가 방법:
# 1. nova_xxx.py 파일 생성
# 2. register(app) 함수 구현
def register(app):
    @app.command("/nova_xxx")
    def handle(ack, body, client):
        ack()
        ...
```

## 슬래시 커맨드

| 커맨드 | 설명 |
|--------|------|
| `/nova_help` | Nova Help Center 포털 링크 버튼 |
| `/nova_jira` | Nova Jira Structure 보드 링크 버튼 |
| `/nova_okr` | OKR 브레인스토밍 모달 실행 → Claude AI 생성 → Confluence 업로드 |

## OKR 파이프라인 흐름

```
/nova_okr 실행
    │
    ▼
모달 입력 (컨텍스트 / 분기 / 전략 키워드 / 옵션)
    │
    ▼
[Step 1] Claude API → OKR 마크다운 생성 (3세트 A/B/C)
    │
    ▼ (Confluence 업로드 선택 시)
[Step 2] Confluence → 페이지 생성 (TE 스페이스)
    │
    ▼
Slack DM으로 진행 상황 실시간 업데이트
```

산출물은 `projects/personal_knowledge_base/05_PM_Outputs/` 에 `.md` 형식으로 저장된다.

## 환경 설정

`.env` 파일 (nova_helper/ 내부 또는 Workspace/.scripts/.env 공용):

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
CLAUDE_API_KEY=sk-ant-...
CONFLUENCE_URL=https://stradvision.atlassian.net/wiki
CONFLUENCE_USERNAME=your@email.com
CONFLUENCE_API_TOKEN=...
CONFLUENCE_SPACE_KEY=TE
```

## 실행

```bash
cd projects/nova_helper
python nova_helper.py
```

venv 환경이 있으면 자동 활성화됨 (`[venv] nova_helper 활성화됨` 출력 확인).

## 의존성

```
slack-bolt
slack-sdk
python-dotenv
requests
anthropic
google-genai
python-pptx
markdown
urllib3
```

## 관련 프로젝트

- `personal_knowledge_base/pm_ppt_generator.py` — pm_pipeline.py가 import하는 Gemini PPT 생성 모듈
- `Workspace/.scripts/doc_gen.py` — Confluence 문서 생성 GUI (별도 독립 도구)
