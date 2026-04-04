# Nova Helper Slack Bot — Implementation Plan

## Context
Nova_helper는 팀 Slack에서 슬래시 커맨드로 유용한 기능을 제공하는 내부 봇이다.
현재 목표: `/nova_help` (서비스 데스크 URL 제공) + `/nova_jira` (추후 구체화) 커맨드 구현.
Socket Mode로 동작하므로 공개 서버 URL 불필요. 로컬 PC에서 상시 실행.

---

## 파일 구조

```
C:\Users\psh93\OneDrive\Desktop\Claude\
└── nova_helper\
    ├── .env               # 토큰 (git 제외)
    ├── .gitignore
    ├── requirements.txt
    └── nova_helper.py     # 메인 봇 코드
```

---

## 구현 내용

### `.env`
```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
JIRA_API_TOKEN=ATATT3x...
JIRA_EMAIL=본인이메일@stradvision.ai
JIRA_BASE_URL=https://stradvision.atlassian.net
```

### `requirements.txt`
```
slack-bolt
python-dotenv
requests
```

### `nova_helper.py`
- `App(token=SLACK_BOT_TOKEN)` 초기화
- `/nova_help` → 서비스 데스크 URL 버튼 메시지 응답
- `/nova_jira` → "🚧 준비 중입니다" placeholder 응답
- `SocketModeHandler(app, SLACK_APP_TOKEN).start()`

---

## Slack 앱 설정 (api.slack.com/apps)

1. **Socket Mode**: ON
2. **Slash Commands** 추가:
   - `/nova_help` — Nova Help Portal 열기
   - `/nova_jira` — Jira 티켓 조회 (준비 중)
3. **OAuth Scopes** (Bot Token):
   - `commands`
   - `chat:write`

---

## 실행
```bash
cd nova_helper
pip install -r requirements.txt
python nova_helper.py
```

---

## 검증
1. Slack에서 `/nova_help` 입력 → 서비스 데스크 URL 버튼 메시지 표시 확인
2. `/nova_jira` 입력 → placeholder 메시지 확인
3. 프로세스 종료 시 봇 미응답 확인 (상시 실행 필요 확인)

---

## 보안 주의사항
- `.env`를 `.gitignore`에 추가
- **채팅에 노출된 토큰 재발급 필요** (구현 완료 후)
