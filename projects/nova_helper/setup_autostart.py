#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows Task Scheduler에 Nova Helper 자동 시작 작업을 등록/제거합니다.

등록: python setup_autostart.py
제거: python setup_autostart.py remove
상태: python setup_autostart.py status
"""
import os
import sys
import subprocess
from pathlib import Path

NOVA_DIR = Path(__file__).parent.resolve()
TASK_NAME = "NovaHelperAutostart"
BAT_FILE = NOVA_DIR / "start_nova.bat"


def register():
    """Task Scheduler에 로그인 트리거 작업 등록."""
    cmd = [
        "schtasks", "/create",
        "/tn", TASK_NAME,
        "/tr", str(BAT_FILE),
        "/sc", "ONLOGON",
        "/ru", os.environ.get("USERNAME", ""),
        "/rl", "HIGHEST",
        "/f",           # 기존 동일 이름 작업 덮어쓰기
        "/delay", "0001:00",  # 로그인 후 1분 지연 (네트워크 준비 대기)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✓ Task Scheduler 등록 완료: '{TASK_NAME}'")
        print(f"  배치 파일: {BAT_FILE}")
        print(f"  로그 파일: {NOVA_DIR / 'startup.log'}")
        print()
        print("  다음 로그인 시 Nova Helper가 자동으로 시작됩니다.")
        print("  지금 바로 테스트하려면: python startup.py")
    else:
        print(f"✗ 등록 실패: {result.stderr.strip()}")
        if "Access is denied" in result.stderr or "액세스가 거부" in result.stderr:
            print()
            print("  관리자 권한이 필요합니다.")
            print("  터미널을 '관리자 권한으로 실행' 후 다시 시도하세요.")


def remove():
    """등록된 Task Scheduler 작업 제거."""
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"✓ 작업 제거 완료: '{TASK_NAME}'")
    else:
        print(f"✗ 제거 실패: {result.stderr.strip()}")


def status():
    """등록 여부 및 현재 상태 확인."""
    result = subprocess.run(
        ["schtasks", "/query", "/tn", TASK_NAME, "/fo", "LIST"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"✓ '{TASK_NAME}' 등록됨\n")
        print(result.stdout)
    else:
        print(f"✗ '{TASK_NAME}' 미등록")

    # 현재 실행 중인 터널 URL 확인
    url_file = NOVA_DIR / ".current_tunnel_url"
    if url_file.exists():
        url = url_file.read_text(encoding="utf-8").strip()
        print(f"\n  현재 터널 URL: {url}")
    else:
        print("\n  Nova Helper 현재 미실행 상태")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "register"
    {"register": register, "remove": remove, "status": status}.get(action, register)()
