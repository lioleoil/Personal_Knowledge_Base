import os
import ssl
from dotenv import load_dotenv
from slack_sdk.web import WebClient
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

client = WebClient(token=os.environ["SLACK_BOT_TOKEN"], ssl=ssl_context)
app = App(client=client)

NOVA_HELP_URL = "https://stradvision.atlassian.net/servicedesk/customer/portal/45"


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


if __name__ == "__main__":
    print("Nova Helper bot starting...")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
