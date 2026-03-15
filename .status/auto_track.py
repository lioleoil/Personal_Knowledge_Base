"""
Claude Code Stop 훅 — transcript usage 필드 기반 정확한 토큰 추적
transcript의 각 assistant 메시지에 포함된 usage 데이터를 읽어 정확히 집계한다.
"""
import json, os, subprocess, sys
from datetime import datetime

STATUS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, STATUS_DIR)
import show_tokens

MIN_NEW_TOKENS = 100  # 이 미만은 노이즈로 간주하여 기록 생략
POPUP_SCRIPT   = os.path.join(STATUS_DIR, 'token_popup.py')


def launch_popup():
    """GUI 팝업을 백그라운드 서브프로세스로 실행 (훅 블로킹 없음)."""
    if sys.platform == 'win32':
        # pythonw.exe: 콘솔 창 없이 GUI만 표시 (Windows GUI 앱 표준 실행 방식)
        pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
        interpreter = pythonw if os.path.exists(pythonw) else sys.executable
        subprocess.Popen(
            [interpreter, POPUP_SCRIPT],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        subprocess.Popen([sys.executable, POPUP_SCRIPT])


def count_tokens_from_transcript(transcript_path):
    """transcript JSONL의 assistant usage 필드를 합산하여 토큰 수 반환.
    input + output 만 집계 (cache_read/cache_creation은 누적 왜곡되므로 제외).
    """
    if not os.path.exists(transcript_path):
        return 0
    total = 0
    try:
        with open(transcript_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get('type') != 'assistant':
                        continue
                    usage = obj.get('message', {}).get('usage', {})
                    total += usage.get('input_tokens', 0)
                    total += usage.get('output_tokens', 0)
                except Exception:
                    continue
    except Exception:
        return 0
    return total


def main():
    # stdin에서 Stop 훅 페이로드 읽기
    payload = {}
    try:
        raw = sys.stdin.read()
        if raw.strip():
            payload = json.loads(raw)
    except Exception:
        pass

    # stop_hook_active 체크 — 무한루프 방지
    if payload.get('stop_hook_active'):
        launch_popup()
        return

    transcript_path = payload.get('transcript_path', '')

    if not transcript_path:
        launch_popup()
        return

    total_tokens = count_tokens_from_transcript(transcript_path)
    data = show_tokens.load()
    transcripts = data.setdefault('transcripts', {})
    already_counted = transcripts.get(transcript_path, 0)
    new_tokens = total_tokens - already_counted

    if new_tokens >= MIN_NEW_TOKENS:
        transcripts[transcript_path] = total_tokens
        data['used']        = data.get('used', 0)        + new_tokens
        data['weekly_used'] = data.get('weekly_used', 0) + new_tokens
        data.setdefault('sessions', []).append({
            'task': '자동 추적',
            'tokens': new_tokens,
            'time': datetime.now().strftime('%H:%M:%S'),
        })
        show_tokens.save(data)

    launch_popup()


if __name__ == '__main__':
    main()
