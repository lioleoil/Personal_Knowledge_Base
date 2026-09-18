#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nova_tagged_digest.py
──────────────────────────────────────────────────────────────────────────────
/nova_digest 슬래시 커맨드 + 인프로세스 스케줄러.

- /nova_digest        : 지금 즉시 다이제스트 실행(백그라운드) → 완료 시 채널/DM 게시
- /nova_digest dry     : dry-run 실행 → 요약 텍스트를 ephemeral 로 반환(게시 X)

APScheduler(BackgroundScheduler, Asia/Seoul)로 월–금 08/12/16/20시에 자동 실행한다.
apscheduler 미설치 시 인프로세스 스케줄러는 건너뛰고, OS 스케줄러 폴백
(setup_tagged_digest_schedule.py) 사용을 안내한다.

nova_helper.py 가 app 인스턴스를 주입해 register(app) 을 호출한다.
"""

import os
import sys
import threading
from pathlib import Path

# .scripts 디렉터리를 sys.path 에 안전하게 추가(이 파일 기준 상대 경로)
_SCRIPTS_DIR = (Path(__file__).resolve().parent / ".." / ".." / ".scripts").resolve()
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# 스케줄러 중복 기동 방지 플래그(register 가 여러 번 호출돼도 1회만 시작)
_scheduler_started = False


def _run_digest_bg(dry_run: bool = False):
    """백그라운드 스레드에서 run_digest 를 호출한다(임포트는 호출 시점에)."""
    from tagged_thread_digest import run_digest
    return run_digest(dry_run=dry_run)


def _start_scheduler():
    """월–금 08/12/16/20시(Asia/Seoul) 크론 잡을 1회만 등록한다."""
    global _scheduler_started
    if _scheduler_started:
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        print("[nova_digest] apscheduler 미설치 — 인프로세스 스케줄러를 건너뜁니다. "
              "OS 스케줄러 폴백(.scripts/setup_tagged_digest_schedule.py)을 사용하세요.")
        return

    def _job():
        try:
            _run_digest_bg(dry_run=False)
        except Exception as e:
            print(f"[nova_digest] 스케줄 실행 오류: {e}")

    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_job(
        _job,
        trigger=CronTrigger(day_of_week="mon-fri", hour="8,12,16,20", minute=0),
        id="nova_tagged_digest",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler_started = True
    print("[nova_digest] 스케줄러 등록 완료 — 월–금 08/12/16/20시 (Asia/Seoul)")


def register(app):
    """nova_helper.py 에서 app 인스턴스를 받아 커맨드·스케줄러를 등록한다."""

    @app.command("/nova_digest")
    def handle_digest(ack, body, respond):
        ack()
        text = (body.get("text") or "").strip().lower()

        # dry-run: 요약을 즉시 생성해 ephemeral 로 반환(게시하지 않음)
        if text in ("dry", "dry-run", "dryrun"):
            respond("다이제스트 dry-run 실행 중... 잠시 후 결과를 표시합니다. (게시하지 않음)")

            def _dry():
                try:
                    report = _run_digest_bg(dry_run=True)
                    respond(f"*[dry-run] 태그된 스레드 다이제스트*\n{report[:2900]}")
                except Exception as e:
                    respond(f"다이제스트 dry-run 실패: {e}")

            threading.Thread(target=_dry, daemon=True).start()
            return

        # 일반 실행: 백그라운드에서 수집·요약·게시
        respond("태그된 스레드 다이제스트를 실행합니다. 완료되면 채널/DM으로 리포트를 전달합니다.")

        def _run():
            try:
                _run_digest_bg(dry_run=False)
            except Exception as e:
                respond(f"다이제스트 실행 실패: {e}")

        threading.Thread(target=_run, daemon=True).start()

    # 인프로세스 스케줄러 기동
    _start_scheduler()
