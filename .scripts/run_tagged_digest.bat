@echo off
REM 태그된 스레드 다이제스트 — Windows Task Scheduler 진입점
REM 월-금 08/12/16/20시 실행 (setup_tagged_digest_schedule.py 로 등록)

cd /d "C:\Users\psh93\OneDrive\Desktop\Workspace"

set PYTHON=C:\Users\psh93\AppData\Local\Programs\Python\Python313\python.exe
if not exist "%PYTHON%" set PYTHON=python.exe

set PYTHONUNBUFFERED=1
"%PYTHON%" -u .scripts\tagged_thread_digest.py >> .scripts\tagged_digest.log 2>&1
