# Nova Helper — 서버 환경 재설계안

> 작성일: 2026-04-11  
> 목적: 로컬 머신 의존 Socket Mode → 서버 독립 HTTP Mode 전환

---

## 1. 현재 아키텍처 분석

### 현재 구조 (Socket Mode)

```
로컬 머신
  └─ nova_helper.py
       └─ SocketModeHandler(app, SLACK_APP_TOKEN)
            └─ Slack과 WebSocket 연결 유지 (상시 프로세스 필요)
```

**한계점:**
| 문제 | 영향 |
|------|------|
| 로컬 머신 상시 구동 필요 | 머신 재부팅/절전 시 봇 중단 |
| SLACK_APP_TOKEN (WebSocket 전용) 의존 | 서버 배포 불가 |
| 단일 프로세스 | 수평 확장 불가 |
| 포트 노출 불필요 | 방화벽/VPN 환경에서만 동작 |

---

## 2. 목표 아키텍처 (HTTP Mode)

### 설계 원칙

- **Bolt HTTP Mode** + `aiohttp` 비동기 서버
- Slack → HTTPS POST → `/slack/events` 엔드포인트
- `SLACK_SIGNING_SECRET`으로 요청 검증 (SLACK_APP_TOKEN 불필요)
- Docker 컨테이너로 패키징 → 어느 서버/클라우드에서도 실행

### 아키텍처 다이어그램

```
[Slack Workspace]
      │  HTTPS POST (slash command / event)
      ▼
[Public Endpoint: https://your-server.com/slack/events]
      │
      ▼
[nova_helper (aiohttp + Bolt HTTP Adapter)]
      │
      ├─ /nova_help      → Help Center 링크 응답
      ├─ /nova_jira      → Jira Structure 링크 응답
      ├─ /nova_okr       → OKR 파이프라인 실행 (백그라운드 스레드)
      └─ nova_*.py 플러그인 자동 로드
```

### 환경 변수 변경

| 변수 | 기존 (Socket) | 신규 (HTTP) |
|------|--------------|------------|
| `SLACK_BOT_TOKEN` | 필요 (xoxb-) | 필요 (xoxb-) |
| `SLACK_APP_TOKEN` | 필요 (xapp-) | **제거** |
| `SLACK_SIGNING_SECRET` | 불필요 | **추가 필요** |
| `NOVA_MODE` | 없음 | `server` 설정 시 HTTP 모드 |
| `NOVA_PORT` | 없음 | 서버 포트 (기본 3000) |
| `NOVA_ESCALATION_CHANNEL` | 없음 | Slack 알림 채널 ID |

---

## 3. 코드 변경 사항

### nova_helper.py 수정 내용

기존 `SocketModeHandler` 코드는 유지하고 `NOVA_MODE=server` 환경변수로 HTTP 모드 분기:

```python
if __name__ == "__main__":
    if os.environ.get("NOVA_MODE") == "server":
        # HTTP 서버 모드
        import asyncio
        from aiohttp import web
        from slack_bolt.adapter.aiohttp import AioHTTPAdapter

        signing_secret = os.environ["SLACK_SIGNING_SECRET"]
        bolt_app = App(token=os.environ["SLACK_BOT_TOKEN"],
                       signing_secret=signing_secret)
        # 플러그인 등록 (기존 로직 재사용)
        adapter = AioHTTPAdapter(bolt_app)

        async def handle_slack(request):
            return await adapter.handle(request)

        web_app = web.Application()
        web_app.router.add_post("/slack/events", handle_slack)

        port = int(os.environ.get("NOVA_PORT", 3000))
        print(f"Nova Helper bot starting (HTTP mode) on port {port}...")
        web.run_app(web_app, host="0.0.0.0", port=port)
    else:
        # 로컬 Socket 모드 (기존 동작 유지)
        print("Nova Helper bot starting (Socket mode)...")
        SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
```

### Advisor 에스컬레이션 Slack 알림 함수

```python
def notify_advisor_escalation(operation: str, context: str, channel: str = None):
    """Advisor 에이전트가 사용자 에스컬레이션 시 Slack으로 알림 전송"""
    target = channel or os.environ.get("NOVA_ESCALATION_CHANNEL", "")
    if not target:
        return
    client.chat_postMessage(
        channel=target,
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":warning: *Advisor 에스컬레이션*\n*작업*: `{operation}`\n*사유*: {context}\n사용자 승인이 필요합니다."
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "승인"},
                        "style": "primary",
                        "action_id": "advisor_approve",
                        "value": operation
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "거부"},
                        "style": "danger",
                        "action_id": "advisor_deny",
                        "value": operation
                    }
                ]
            }
        ]
    )
```

---

## 4. 배포 방안

### Docker 구성

**`Dockerfile`**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt aiohttp slack-bolt[async]
COPY . .
ENV NOVA_MODE=server
ENV NOVA_PORT=3000
EXPOSE 3000
CMD ["python", "nova_helper.py"]
```

**`docker-compose.yml`**:
```yaml
version: "3.9"
services:
  nova-helper:
    build: .
    ports:
      - "3000:3000"
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Slack App 설정 변경 필요 사항

1. **Slack App 관리 콘솔** → `Event Subscriptions` 활성화
2. Request URL: `https://your-server.com/slack/events`
3. `Interactivity & Shortcuts` → Request URL 동일하게 설정
4. Socket Mode **비활성화**

### 배포 옵션

| 환경 | 방법 | 비용 |
|------|------|------|
| VPS (AWS EC2, GCP Compute, Hetzner 등) | Docker + nginx reverse proxy | 저비용 |
| Fly.io | `fly deploy` | 무료 티어 가능 |
| Railway | Git push 자동 배포 | 무료 티어 가능 |
| AWS Lambda | Serverless (Mangum adapter) | 사용량 기반 |

---

## 5. 마이그레이션 체크리스트

- [ ] `.env`에 `SLACK_SIGNING_SECRET` 추가 (Slack App 기본 정보 페이지에서 확인)
- [ ] `.env`에 `NOVA_MODE=server` 설정
- [ ] `.env`에 `NOVA_ESCALATION_CHANNEL=` 설정 (DM ID 또는 채널 ID)
- [ ] `requirements.txt`에 `aiohttp` 추가
- [ ] Slack App 콘솔에서 Socket Mode 비활성화
- [ ] Slack App 콘솔에서 Event Subscriptions URL 등록
- [ ] 서버 포트 3000 방화벽 인바운드 허용 또는 nginx 리버스 프록시 설정
- [ ] `python nova_helper.py` → Docker 또는 서비스 등록으로 전환

---

## 6. 로컬 개발 환경 유지

`NOVA_MODE` 환경변수를 설정하지 않으면 기존 Socket Mode로 동작한다.  
개발 시 로컬에서 `SLACK_APP_TOKEN`으로 바로 테스트 가능.

```bash
# 로컬 개발 (기존 방식)
python nova_helper.py

# 서버 모드 테스트 (ngrok 사용)
ngrok http 3000 &
NOVA_MODE=server python nova_helper.py
```
