#!/usr/bin/env python3
"""
Slack 채널의 캔버스를 마크다운 포맷으로 export하는 스크립트
"""
import os
import sys
from dotenv import load_dotenv
from slack_sdk.web import WebClient
import ssl
import json
from datetime import datetime

# .env 로드
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
_scripts_env = os.path.join(os.path.dirname(__file__), "..", ".scripts", ".env")
if os.path.exists(_scripts_env):
    load_dotenv(dotenv_path=_scripts_env, override=False)

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

client = WebClient(token=os.environ["SLACK_BOT_TOKEN"], ssl=ssl_context)


def get_channel_canvases(channel_id: str):
    """채널의 모든 캔버스 목록 가져오기"""
    try:
        # 채널의 메시지에서 캔버스를 찾기
        result = client.conversations_history(channel=channel_id, limit=1000)
        canvases = []

        for message in result.get("messages", []):
            # 파일이 첨부된 메시지 중 캔버스 찾기
            if "files" in message:
                for file in message["files"]:
                    if file.get("subtype") == "slack_canvas" or file.get("mimetype") == "application/vnd.slack-docs":
                        canvases.append({
                            "id": file.get("id"),
                            "name": file.get("name", file.get("title", "Untitled Canvas")),
                            "created": file.get("created", 0),
                            "file": file
                        })

        return canvases
    except Exception as e:
        print(f"Error fetching canvases: {e}")
        return []


def get_canvas_content(canvas_id: str):
    """캔버스 내용 가져오기"""
    try:
        # canvases.access.* API 또는 files.info 사용
        result = client.files_info(file=canvas_id)

        if result["ok"]:
            file_info = result["file"]

            # 캔버스 내용 추출
            # canvas_sections가 있으면 사용, 없으면 plain_text 사용
            if "canvas" in file_info:
                canvas_data = file_info["canvas"]
                return canvas_data
            elif "plain_text" in file_info:
                return {"content": file_info["plain_text"]}
            elif "preview" in file_info:
                return {"content": file_info["preview"]}
            else:
                # URL에서 다운로드
                if "url_private_download" in file_info:
                    import requests
                    headers = {"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}
                    response = requests.get(file_info["url_private_download"], headers=headers, verify=False)
                    if response.ok:
                        return {"content": response.text}

                return {"content": "내용을 가져올 수 없습니다."}
    except Exception as e:
        print(f"Error fetching canvas content {canvas_id}: {e}")
        return {"content": f"Error: {e}"}


def canvas_to_markdown(canvas_name: str, canvas_content):
    """캔버스 내용을 마크다운으로 변환"""
    md = f"# {canvas_name}\n\n"
    md += f"_Exported at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n"
    md += "---\n\n"

    if isinstance(canvas_content, dict):
        if "content" in canvas_content:
            md += canvas_content["content"]
        else:
            # JSON 형태로 저장된 경우
            md += "```json\n"
            md += json.dumps(canvas_content, indent=2, ensure_ascii=False)
            md += "\n```\n"
    else:
        md += str(canvas_content)

    return md


def main():
    channel_id = "C08C2M08X7Z"

    if len(sys.argv) > 1:
        channel_id = sys.argv[1]

    print(f"Fetching canvases from channel: {channel_id}")

    # 채널 정보 가져오기
    try:
        channel_info = client.conversations_info(channel=channel_id)
        channel_name = channel_info["channel"]["name"]
        print(f"Channel name: {channel_name}")
    except Exception as e:
        print(f"Warning: Could not get channel name: {e}")
        channel_name = channel_id

    # 캔버스 목록 가져오기
    canvases = get_channel_canvases(channel_id)
    print(f"Found {len(canvases)} canvases")

    if not canvases:
        print("No canvases found in this channel.")
        return

    # 출력 디렉터리 생성
    output_dir = os.path.join(os.path.dirname(__file__), "canvas_exports", channel_name)
    os.makedirs(output_dir, exist_ok=True)

    # 각 캔버스를 마크다운으로 변환하여 저장
    for i, canvas in enumerate(canvases, 1):
        print(f"\n[{i}/{len(canvases)}] Processing: {canvas['name']}")

        # 캔버스 내용 가져오기
        content = get_canvas_content(canvas['id'])

        # 마크다운 변환
        markdown = canvas_to_markdown(canvas['name'], content)

        # 파일명 생성 (안전한 파일명으로 변환)
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in canvas['name'])
        safe_name = safe_name.strip()
        filename = f"{i:02d}_{safe_name}.md"

        # 파일 저장
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)

        print(f"  ✓ Saved to: {output_path}")

    print(f"\n✅ All canvases exported to: {output_dir}")

    # 인덱스 파일 생성
    index_path = os.path.join(output_dir, "00_INDEX.md")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(f"# Canvas Export Index - {channel_name}\n\n")
        f.write(f"Channel ID: `{channel_id}`\n\n")
        f.write(f"Exported at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Total canvases: {len(canvases)}\n\n")
        f.write("---\n\n")
        f.write("## Canvases\n\n")

        for i, canvas in enumerate(canvases, 1):
            safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in canvas['name'])
            safe_name = safe_name.strip()
            filename = f"{i:02d}_{safe_name}.md"
            created_date = datetime.fromtimestamp(canvas['created']).strftime('%Y-%m-%d')
            f.write(f"{i}. [{canvas['name']}](./{filename}) - Created: {created_date}\n")

    print(f"📋 Index file created: {index_path}")


if __name__ == "__main__":
    main()
