#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nova Helper 자동 시작 스크립트
1. Flask 서버 (HTTP mode) 실행
2. cloudflared quick tunnel 시작 → URL 획득
3. Slack App 슬래시 커맨드 Request URL 자동 업데이트

실행: python startup.py
자동 시작 등록: python setup_autostart.py
"""
import os
import sys
import re
import time
import subprocess
import threading
from pathlib import Path

NOVA_DIR = Path(__file__).parent
ENV_PATH = NOVA_DIR / ".env"
APP_ID = "A0ALTDQEQBW"
EVENTS_PATH = "/slack/events"

# slack_bolt가 설치된 Python을 우선 탐색
def _find_python() -> str:
    candidates = [
        sys.executable,
        r"C:\Users\psh93\AppData\Local\Programs\Python\Python313\python.exe",
        "python3", "python",
    ]
    for py in candidates:
        try:
            r = subprocess.run([py, "-c", "import slack_bolt"], capture_output=True)
            if r.returncode == 0:
                return py
        except FileNotFoundError:
            continue
    return sys.executable  # fallback

PYTHON_EXE = _find_python()


# ── .env 로드 (stdlib only) ───────────────────────────────────────────────────

def _load_env():
    if ENV_PATH.exists():
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()
PORT = int(os.environ.get("NOVA_PORT", 3000))


# ── Flask 서버 시작 ───────────────────────────────────────────────────────────

def _start_flask() -> subprocess.Popen:
    env = {**os.environ, "NOVA_MODE": "server"}
    log = open(NOVA_DIR / "flask.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [PYTHON_EXE, str(NOVA_DIR / "nova_helper.py")],
        env=env,
        cwd=str(NOVA_DIR),
        stdout=log,
        stderr=log,
    )
    print(f"  [Flask] PID {proc.pid} 시작 (로그: flask.log)")
    return proc


# ── cloudflared 터널 시작 ─────────────────────────────────────────────────────

_CLOUDFLARED_CANDIDATES = [
    "cloudflared",
    r"C:\Users\psh93\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe",
    r"C:\Program Files\cloudflared\cloudflared.exe",
    r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
]

def _find_cloudflared() -> str:
    for candidate in _CLOUDFLARED_CANDIDATES:
        try:
            r = subprocess.run([candidate, "--version"], capture_output=True)
            if r.returncode == 0:
                return candidate
        except FileNotFoundError:
            continue
    return "cloudflared"  # fallback (에러 메시지용)

def _start_cloudflared(result: dict) -> None:
    """cloudflared 실행 후 result['url'] 에 public URL 저장, result['proc'] 에 프로세스 저장."""
    url_re = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
    cloudflared_exe = _find_cloudflared()
    try:
        proc = subprocess.Popen(
            [cloudflared_exe, "tunnel", "--url", f"http://localhost:{PORT}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        result["proc"] = proc

        for line in proc.stdout:
            m = url_re.search(line)
            if m:
                result["url"] = m.group(0)
                break

        # URL 획득 후에도 stdout 계속 소비 (버퍼 블로킹 방지)
        threading.Thread(
            target=lambda: [_ for _ in proc.stdout],
            daemon=True,
        ).start()

    except FileNotFoundError:
        result["error"] = (
            "cloudflared 를 찾을 수 없습니다.\n"
            "설치 명령: winget install cloudflare.cloudflared"
        )


# ── Slack 슬래시 커맨드 URL 업데이트 ─────────────────────────────────────────

def _fallback(events_url: str) -> None:
    """자동 업데이트 실패 시 브라우저 오픈 + 클립보드 복사."""
    import webbrowser
    dashboard_url = f"https://api.slack.com/apps/{APP_ID}/slash-commands"
    print(f"\n  ┌─ Slack 슬래시 커맨드 수동 등록 필요 ──────────────────────")
    print(f"  │  Request URL: {events_url}")
    print(f"  │  (클립보드에 복사됨)")
    print(f"  └────────────────────────────────────────────────────────────")
    # 클립보드 복사 (Windows)
    try:
        subprocess.run(["clip"], input=events_url.encode(), check=True)
    except Exception:
        pass
    # Slack 대시보드 자동 오픈
    webbrowser.open(dashboard_url)


def _update_slack_urls(tunnel_url: str) -> None:
    """
    slack_sdk WebClient → apps_manifest_get/update 로 슬래시 커맨드 URL 일괄 교체.
    SLACK_APP_CONFIG_TOKEN: api.slack.com → Basic Information → App-Level Tokens
                            (scope: apps:write) 에서 발급한 xapp-... 토큰.
    실패 시 클립보드 복사 + 브라우저 자동 오픈 fallback.
    """
    events_url = f"{tunnel_url}{EVENTS_PATH}"
    config_token = os.environ.get("SLACK_APP_CONFIG_TOKEN", "")

    if not config_token:
        _fallback(events_url)
        return

    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
    except ImportError:
        print("  [Slack] slack_sdk 미설치")
        _fallback(events_url)
        return

    client = WebClient(token=config_token)

    try:
        resp = client.apps_manifest_get(app_id=APP_ID)
        manifest = resp["manifest"]

        count = 0
        for cmd in manifest.get("slash_commands", []):
            cmd["url"] = events_url
            count += 1

        if count == 0:
            print("  [Slack] 매니페스트에 슬래시 커맨드 없음")
            return

        client.apps_manifest_update(app_id=APP_ID, manifest=manifest)
        print(f"  [Slack] {count}개 슬래시 커맨드 URL 자동 업데이트 완료")
        print(f"          → {events_url}")

    except SlackApiError as e:
        err = e.response.get("error", str(e))
        print(f"  [Slack] API 오류: {err}")
        if err in ("unknown_method", "not_allowed_token_type"):
            print("  [Slack] 현재 xapp- 토큰은 manifest API 미지원")
            print("  [Slack] → Slack CLI 발급 토큰(xoxe.xp-)이 필요합니다")
        _fallback(events_url)
    except Exception as e:
        print(f"  [Slack] 예외: {e}")
        _fallback(events_url)


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace") if hasattr(sys.stdout, "reconfigure") else None
    print("  Nova Helper - Startup")
    print("=" * 60)

    # 1. Flask 서버 시작
    print("\n  [1/3] Flask 서버 시작...")
    flask_proc = _start_flask()
    time.sleep(2)  # 초기화 대기

    if flask_proc.poll() is not None:
        print("  [Flask] 프로세스가 즉시 종료됨 — flask.log 확인")
        sys.exit(1)

    # 2. cloudflared 터널 시작 (별도 스레드)
    print("  [2/3] cloudflared 터널 시작...")
    cf = {}
    t = threading.Thread(target=_start_cloudflared, args=(cf,), daemon=True)
    t.start()

    # URL 대기 (최대 30초)
    deadline = time.time() + 30
    while time.time() < deadline:
        if "url" in cf or "error" in cf:
            break
        time.sleep(0.5)

    if "error" in cf:
        print(f"\n  오류: {cf['error']}")
        flask_proc.terminate()
        sys.exit(1)

    tunnel_url = cf.get("url")
    if not tunnel_url:
        print("\n  오류: cloudflared URL 획득 타임아웃 (30초)")
        flask_proc.terminate()
        sys.exit(1)

    print(f"\n  터널 URL: {tunnel_url}")

    # URL을 파일에 저장 (다른 스크립트에서 참조 가능)
    (NOVA_DIR / ".current_tunnel_url").write_text(tunnel_url, encoding="utf-8")

    # 3. Slack URL 업데이트
    print("  [3/3] Slack 슬래시 커맨드 URL 업데이트...")
    _update_slack_urls(tunnel_url)

    print("\n" + "=" * 60)
    print("  Nova Helper 실행 중 (CTRL+C로 종료)")
    print("=" * 60)

    try:
        flask_proc.wait()
    except KeyboardInterrupt:
        print("\n  종료 중...")
    finally:
        flask_proc.terminate()
        if cf.get("proc"):
            cf["proc"].terminate()
        url_file = NOVA_DIR / ".current_tunnel_url"
        if url_file.exists():
            url_file.unlink()


if __name__ == "__main__":
    main()
