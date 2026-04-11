import os
import ssl
from dotenv import load_dotenv
from slack_sdk.web import WebClient
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import glob
import importlib
import sys

# .env 로드 (로컬 → 상위 .scripts/.env 순)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
_scripts_env = os.path.join(os.path.dirname(__file__), "..", ".scripts", ".env")
if os.path.exists(_scripts_env):
    load_dotenv(dotenv_path=_scripts_env, override=False)

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

client = WebClient(token=os.environ["SLACK_BOT_TOKEN"], ssl=ssl_context)
app = App(client=client)

NOVA_HELP_URL = "https://stradvision.atlassian.net/servicedesk/customer/portal/45"


def notify_advisor_escalation(operation: str, context: str, channel: str = None):
    """Advisor 에이전트가 사용자 에스컬레이션 시 Slack으로 알림 전송.
    NOVA_ESCALATION_CHANNEL 환경변수 또는 channel 인자로 대상 채널 지정.
    """
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
                    "text": (
                        f":warning: *Advisor 에스컬레이션*\n"
                        f"*작업*: `{operation}`\n"
                        f"*사유*: {context}\n"
                        f"사용자 승인이 필요합니다."
                    ),
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "승인"},
                        "style": "primary",
                        "action_id": "advisor_approve",
                        "value": operation,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "거부"},
                        "style": "danger",
                        "action_id": "advisor_deny",
                        "value": operation,
                    },
                ],
            },
        ],
    )


@app.command("/nova_help")
def handle_nova_help(ack, respond):
    ack()
    respond({
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":sv2: *Nova Help Center*\nNova 관련 문의 및 요청은 Help Center에서 접수해주세요."
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "포털 열기"},
                    "style": "primary",
                    "url": NOVA_HELP_URL,
                    "action_id": "open_nova_help"
                }
            }
        ]
    })


@app.command("/nova_jira")
def handle_nova_jira(ack, respond):
    ack()
    respond({
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":clipboard: *Nova Structure*\nNova Structure에서 티켓을 확인하세요."
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Structure 열기"},
                    "style": "primary",
                    "url": "https://stradvision.atlassian.net/jira/apps/94d5de1a-112d-4549-bd03-5f910d5fd27b/880424a7-af14-4c77-b446-5ef9feee797a/structure/board/6464",
                    "action_id": "open_nova_jira"
                }
            }
        ]
    })


@app.command("/nova_dashboard#1")
def handle_nova_dashboard(ack, respond):
    ack()
    respond({
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":bar_chart: *Nova Dashboard*\nNova 데이터 대시보드를 확인하세요."
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "대시보드 열기"},
                    "style": "primary",
                    "url": "http://superset.stradvision.com/superset/welcome/",
                    "action_id": "open_nova_dashboard"
                }
            }
        ]
    })


# ── 플러그인 자동 디스커버리 ──────────────────────────────────────────────────
# nova_*.py 파일에 register(app) 함수가 있으면 자동으로 로드됩니다.
# 새 기능 추가: nova_xxx.py 파일을 만들고 register(app) 함수를 구현하세요.
_plugin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _plugin_dir)

for _path in sorted(glob.glob(os.path.join(_plugin_dir, "nova_*.py"))):
    _name = os.path.splitext(os.path.basename(_path))[0]
    if _name == "nova_helper":
        continue
    try:
        _mod = importlib.import_module(_name)
        if hasattr(_mod, "register"):
            _mod.register(app)
            print(f"[plugin] {_name} registered")
    except Exception as _e:
        print(f"[plugin] {_name} load failed: {_e}")


if __name__ == "__main__":
    if os.environ.get("NOVA_MODE") == "server":
        # HTTP 서버 모드 — 서버/컨테이너 환경에서 실행
        # 필요 패키지: pip install aiohttp slack-bolt[async]
        import asyncio
        from aiohttp import web
        from slack_bolt.adapter.aiohttp import AioHTTPAdapter

        signing_secret = os.environ["SLACK_SIGNING_SECRET"]
        http_app = App(
            token=os.environ["SLACK_BOT_TOKEN"],
            signing_secret=signing_secret,
        )
        adapter = AioHTTPAdapter(http_app)

        async def handle_slack(request):
            return await adapter.handle(request)

        async def handle_health(request):
            return web.Response(text="ok")

        web_app = web.Application()
        web_app.router.add_post("/slack/events", handle_slack)
        web_app.router.add_get("/health", handle_health)

        port = int(os.environ.get("NOVA_PORT", 3000))
        print(f"Nova Helper bot starting (HTTP mode) on port {port}...")
        web.run_app(web_app, host="0.0.0.0", port=port)
    else:
        # 로컬 Socket 모드 (기본 동작 — SLACK_APP_TOKEN 필요)
        print("Nova Helper bot starting (Socket mode)...")
        SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
