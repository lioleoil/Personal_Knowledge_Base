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
| `/nova_digest` | 나(박성환)를 @-태그한 스레드 수집·요약 리포트 전달 (`/nova_digest dry` = 게시 없이 미리보기) |

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

## 태그된 스레드 다이제스트 (`/nova_digest`)

나(박성환 / Seonghwan Park)가 @-태그된 **모든 스레드 메시지**를 마지막 실행 이후 구간에서
수집 → 요약 → **한국어 리포트**로 전달하는 잡. 핵심 로직은 `.scripts/tagged_thread_digest.py`,
Slack 커맨드 + 인프로세스 스케줄러는 `nova_tagged_digest.py`.

### 스케줄

**월–금 08:00~20:00, 4시간 간격 (08 / 12 / 16 / 20시, Asia/Seoul)**

### 슬래시 커맨드

| 커맨드 | 동작 |
|--------|------|
| `/nova_digest` | 즉시 수집·요약 후 채널/DM으로 리포트 게시(백그라운드) |
| `/nova_digest dry` | 게시·상태갱신 없이 요약만 생성해 ephemeral 로 미리보기 |

### 필요 환경변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `SLACK_USER_TOKEN` | ✅ | 유저 토큰(xoxp) — `search:read` 스코프 필수. `search.messages` 는 **봇 토큰으로 호출 불가**, 유저 토큰 전용 |
| `SLACK_BOT_TOKEN` | 권장 | 리포트 게시용(xoxb). 없으면 유저 토큰으로 게시 |
| `SLACK_TARGET_USER_ID` | 선택 | 대상 유저 ID. 미설정 시 유저 토큰 `auth.test` 결과 사용 |
| `TAGGED_DIGEST_CHANNEL` | 선택 | 리포트 게시 채널. 미설정 시 대상 유저 DM |
| `CLAUDE_API_KEY` / `ANTHROPIC_API_KEY` | 선택 | 요약용 Anthropic 키. 없으면 비-LLM 원문 목록 리포트로 자동 폴백 |

리포트는 항상 `.status/tagged_digest/tagged_digest_{YYYYMMDD_HHMM}.md` 로도 저장되며,
마지막 성공 실행 시각은 `.status/tagged_digest_state.json` 에 기록된다.

### 배포 옵션

- **옵션 A — nova_helper 상시 구동**: 봇을 계속 실행하면 `nova_tagged_digest.py` 의
  APScheduler(`BackgroundScheduler`, `Asia/Seoul`)가 월–금 08/12/16/20시에 자동 실행한다.
- **옵션 B — Windows Task Scheduler 폴백** (봇을 상시 구동하지 않을 때):
  ```bash
  python .scripts/setup_tagged_digest_schedule.py            # 4개 평일 작업 등록
  python .scripts/setup_tagged_digest_schedule.py remove     # 제거
  python .scripts/setup_tagged_digest_schedule.py --dry-run  # 명령 미리보기
  ```
  `NovaTaggedDigest_0800` … `_2000` 4개 작업이 등록되며 `run_tagged_digest.bat` 를 실행한다.

- **Linux cron 등가 라인** (월–금 08/12/16/20시):
  ```cron
  0 8,12,16,20 * * 1-5  cd /path/to/Workspace && python .scripts/tagged_thread_digest.py
  ```
- **Claude Code 예약 트리거**도 또 다른 실행 옵션이다.

### 수동 실행

```bash
python .scripts/tagged_thread_digest.py --dry-run            # 게시 없이 리포트 출력
python .scripts/tagged_thread_digest.py --window-hours 24    # 최근 24시간 강제 조회
```

## 관련 프로젝트

- `personal_knowledge_base/pm_ppt_generator.py` — pm_pipeline.py가 import하는 Gemini PPT 생성 모듈
- `Workspace/.scripts/doc_gen.py` — Confluence 문서 생성 GUI (별도 독립 도구)
