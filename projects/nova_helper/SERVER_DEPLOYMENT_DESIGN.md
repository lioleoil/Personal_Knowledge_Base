# Nova Helper — 서버 배포 설계

> 현재 운영: **Socket Mode** (로컬 PC, Task Scheduler 자동 시작)  
> 이 문서: 향후 HTTP Mode 클라우드 배포 시 참고용 설계 가이드

---

## 1. 현재 아키텍처 한계 (Socket Mode 로컬)

| 항목 | 현황 | 한계 |
|------|------|------|
| 실행 환경 | 로컬 PC | PC 종료 시 봇 다운 |
| 터널 | 불필요 | — |
| 배포 자동화 | Task Scheduler | 수동 관리 |
| 확장성 | 단일 인스턴스 | 고가용성 불가 |
| 로그 | `nova_helper.log` 로컬 파일 | 중앙 수집 불가 |

---

## 2. HTTP Mode 서버 아키텍처

```
Slack ──POST /slack/events──► [Cloud Server: Flask + slack_bolt]
                                        │
                          ┌─────────────┼─────────────┐
                          ▼             ▼             ▼
                     nova_okr      nova_helper    pm_pipeline
                     (플러그인)    (코어 핸들러)   (OKR 파이프라인)
```

### 필수 환경변수

| 변수 | 용도 |
|------|------|
| `SLACK_BOT_TOKEN` | Slack Bot OAuth Token |
| `SLACK_SIGNING_SECRET` | 요청 검증 (HTTP Mode 필수) |
| `NOVA_MODE` | `server` 로 설정 |
| `NOVA_PORT` | Flask 포트 (기본: 3000) |
| `SLACK_ESCALATION_CHANNEL` | 에스컬레이션 알림 채널 ID |
| `CLAUDE_API_KEY` | OKR 생성 API |
| `GEMINI_API_KEY` | PPT 생성 API |
| `CONFLUENCE_*` | Confluence 연동 (선택) |

---

## 3. Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY projects/nova_helper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY projects/nova_helper/ ./nova_helper/
COPY .scripts/ ./.scripts/
COPY global/ ./global/

ENV NOVA_MODE=server
ENV NOVA_PORT=3000

EXPOSE 3000

CMD ["python", "-u", "nova_helper/nova_helper.py"]
```

### requirements.txt (HTTP Mode용)

```
slack-bolt>=1.27.0
slack-sdk>=3.41.0
flask>=3.0.0
python-dotenv>=1.0.0
anthropic>=0.20.0
google-generativeai>=0.5.0
python-pptx>=0.6.23
requests>=2.31.0
```

---

## 4. 배포 플랫폼 비교

| 플랫폼 | 비용 | 난이도 | 장점 | 단점 |
|--------|------|--------|------|------|
| **Railway.app** | $5/월 | ⭐ 쉬움 | GitHub 연동, 자동 배포 | 소규모 |
| **Render.com** | $7/월 | ⭐ 쉬움 | 안정적, 무료 tier | 슬립 있음 |
| **Fly.io** | ~$5/월 | ⭐⭐ 보통 | 글로벌 엣지 | 설정 복잡 |
| **AWS EC2 t3.micro** | ~$8/월 | ⭐⭐⭐ 복잡 | 완전 제어 | 관리 부담 |
| **GCP Cloud Run** | 종량제 (~$1 이하) | ⭐⭐ 보통 | 사용량 기반 저렴 | Cold start |

**추천: Railway.app** — GitHub push → 자동 배포, 환경변수 UI 설정, $5 크레딧 포함

---

## 5. Socket Mode → HTTP Mode 마이그레이션 가이드

1. **Slack App 설정**
   - [api.slack.com/apps/A0ALTDQEQBW/socket-mode](https://api.slack.com/apps/A0ALTDQEQBW/socket-mode) → Socket Mode **OFF**
   - Event Subscriptions → Request URL 등록
   - Slash Commands → 각 커맨드 Request URL 등록

2. **환경변수 변경**
   ```
   NOVA_MODE=server
   SLACK_SIGNING_SECRET=<서명 시크릿>
   ```

3. **로컬 파일 의존성 제거**
   - `OUTPUT_DIR` 경로를 환경변수로 추출 또는 클라우드 스토리지 연동
   - `pm_pipeline.py`의 `_BASE` 경로 확인

4. **배포**
   ```bash
   # Railway
   railway init
   railway up
   ```

5. **URL 등록** — 배포 후 생성된 URL을 Slack App 설정에 등록

---

## 6. 프로세스 관리 (로컬 서버 운영 시)

```bash
# PM2 (Node.js 생태계)
pm2 start "python -u nova_helper.py" --name nova-helper
pm2 startup
pm2 save

# 또는 systemd (Linux)
# /etc/systemd/system/nova-helper.service 작성 후
systemctl enable nova-helper
systemctl start nova-helper
```

---

## 7. 마이그레이션 체크리스트

- [ ] 클라우드 플랫폼 계정 생성 (Railway 권장)
- [ ] `requirements.txt` 최신화
- [ ] 환경변수 플랫폼에 등록
- [ ] `Dockerfile` 빌드 테스트 (`docker build -t nova-helper .`)
- [ ] 로컬 파일 의존성 제거 또는 마운트 설정
- [ ] Slack App Socket Mode OFF
- [ ] Request URL 등록 (모든 슬래시 커맨드 + Event Subscriptions)
- [ ] `/health` 엔드포인트 응답 확인
- [ ] 슬래시 커맨드 동작 테스트
