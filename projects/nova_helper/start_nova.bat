@echo off
REM Nova Helper 자동 시작 (Socket Mode)
REM Windows Task Scheduler에서 로그인 시 자동 실행

cd /d "C:\Users\psh93\OneDrive\Desktop\Workspace\projects\nova_helper"

set PYTHON=C:\Users\psh93\AppData\Local\Programs\Python\Python313\python.exe
if not exist "%PYTHON%" set PYTHON=python.exe

set PYTHONUNBUFFERED=1
"%PYTHON%" -u nova_helper.py >> nova_helper.log 2>&1
