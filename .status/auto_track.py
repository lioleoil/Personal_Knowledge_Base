"""
Claude Code Stop 훅 — transcript usage 필드 기반 정확한 토큰 추적
transcript의 각 assistant 메시지에 포함된 usage 데이터를 읽어 정확히 집계한다.
집계 결과는 token_usage.json의 hourly_buckets에 저장 → Claude Agent Monitor에서 시각화.
"""
import json, os, sys
from datetime import datetime

STATUS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, STATUS_DIR)
import show_tokens

MIN_NEW_TOKENS = 100  # 이 미만은 노이즈로 간주하여 기록 생략


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
        return

    transcript_path = payload.get('transcript_path', '')
    if not transcript_path:
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
        show_tokens._update_hourly_bucket(data, new_tokens)
        show_tokens.save(data)


if __name__ == '__main__':
    main()
