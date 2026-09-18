#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_tagged_digest_schedule.py
──────────────────────────────────────────────────────────────────────────────
태그된 스레드 다이제스트를 Windows Task Scheduler에 등록/제거합니다.
(nova_helper 봇을 상시 구동하지 않는 환경용 폴백 — 봇 상시 구동 시엔
 nova_tagged_digest.py 의 인프로세스 APScheduler가 처리합니다.)

스케줄: 월–금 08:00 / 12:00 / 16:00 / 20:00 (4개 작업)

등록:   python .scripts/setup_tagged_digest_schedule.py
제거:   python .scripts/setup_tagged_digest_schedule.py remove
상태:   python .scripts/setup_tagged_digest_schedule.py status
미리보기: python .scripts/setup_tagged_digest_schedule.py --dry-run
          python .scripts/setup_tagged_digest_schedule.py remove --dry-run
"""
import os
import sys
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.resolve()
BAT_FILE = SCRIPTS_DIR / "run_tagged_digest.bat"

# (작업 이름 접미사, HH:mm)
TIMES = [
    ("0800", "08:00"),
    ("1200", "12:00"),
    ("1600", "16:00"),
    ("2000", "20:00"),
]
TASK_PREFIX = "NovaTaggedDigest_"
WEEKDAYS = "MON,TUE,WED,THU,FRI"


def _task_name(suffix: str) -> str:
    return f"{TASK_PREFIX}{suffix}"


def _create_cmd(suffix: str, hhmm: str) -> list[str]:
    return [
        "schtasks", "/create",
        "/tn", _task_name(suffix),
        "/tr", str(BAT_FILE),
        "/sc", "WEEKLY",
        "/d", WEEKDAYS,
        "/st", hhmm,
        "/ru", os.environ.get("USERNAME", ""),
        "/rl", "HIGHEST",
        "/f",   # 동일 이름 작업 덮어쓰기
    ]


def _delete_cmd(suffix: str) -> list[str]:
    return ["schtasks", "/delete", "/tn", _task_name(suffix), "/f"]


def register(dry_run: bool = False):
    """4개 평일 작업(08/12/16/20시)을 등록한다."""
    for suffix, hhmm in TIMES:
        cmd = _create_cmd(suffix, hhmm)
        if dry_run:
            print("[dry-run] " + " ".join(cmd))
            continue
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ 등록 완료: '{_task_name(suffix)}' (월–금 {hhmm})")
        else:
            print(f"✗ 등록 실패: '{_task_name(suffix)}' — {result.stderr.strip()}")
            if "Access is denied" in result.stderr or "액세스가 거부" in result.stderr:
                print("  관리자 권한이 필요합니다. 터미널을 '관리자 권한으로 실행' 후 다시 시도하세요.")
    if not dry_run:
        print()
        print(f"  배치 파일: {BAT_FILE}")
        print("  월–금 08/12/16/20시에 태그된 스레드 다이제스트가 실행됩니다.")


def remove(dry_run: bool = False):
    """등록된 4개 작업을 제거한다."""
    for suffix, _ in TIMES:
        cmd = _delete_cmd(suffix)
        if dry_run:
            print("[dry-run] " + " ".join(cmd))
            continue
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ 제거 완료: '{_task_name(suffix)}'")
        else:
            print(f"✗ 제거 실패: '{_task_name(suffix)}' — {result.stderr.strip()}")


def status(dry_run: bool = False):
    """등록 여부 및 상태를 확인한다."""
    for suffix, hhmm in TIMES:
        result = subprocess.run(
            ["schtasks", "/query", "/tn", _task_name(suffix), "/fo", "LIST"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"✓ '{_task_name(suffix)}' 등록됨 (월–금 {hhmm})")
        else:
            print(f"✗ '{_task_name(suffix)}' 미등록")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    action = args[0] if args else "register"
    {"register": register, "remove": remove, "status": status}.get(action, register)(dry_run=dry)
