"""
Nova Helper HTTP Mode 실행 스크립트
- Flask 서버 + pyngrok 터널을 동시에 시작
- 실행: python run_http_server.py

ngrok 인증 토큰 설정 (선택, 안정적 URL 원할 때):
  python -c "from pyngrok import ngrok; ngrok.set_auth_token('YOUR_TOKEN')"

Slack App에 Request URL 등록 필요:
  https://api.slack.com/apps/A0ALTDQEQBW/slash-commands
  각 슬래시 커맨드 Request URL → <ngrok_url>/slack/events
"""
import os
import sys
import threading

# .env 로드
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from pyngrok import ngrok
from flask import Flask, request as flask_request

# nova_helper의 app, SlackRequestHandler import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nova_helper as nh
from slack_bolt.adapter.flask import SlackRequestHandler

port = int(os.environ.get("NOVA_PORT", 3000))

# Flask 앱 생성
flask_app = Flask(__name__)
handler = SlackRequestHandler(nh.app)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(flask_request)


@flask_app.route("/health", methods=["GET"])
def health():
    return "ok", 200


if __name__ == "__main__":
    # ngrok 터널 시작
    tunnel = ngrok.connect(port, "http")
    public_url = tunnel.public_url.replace("http://", "https://")

    print("=" * 60)
    print(f"  Nova Helper — HTTP Mode")
    print(f"  Local:  http://127.0.0.1:{port}/slack/events")
    print(f"  Public: {public_url}/slack/events")
    print("=" * 60)
    print()
    print("  Slack App 설정 페이지에서 Request URL을 아래로 등록:")
    print(f"  {public_url}/slack/events")
    print()
    print("  등록 위치:")
    print("  https://api.slack.com/apps/A0ALTDQEQBW/slash-commands")
    print("  (각 슬래시 커맨드 → Request URL 수정)")
    print()
    print("  CTRL+C로 종료")
    print("=" * 60)

    # Flask 서버 실행 (블로킹)
    flask_app.run(host="0.0.0.0", port=port)
