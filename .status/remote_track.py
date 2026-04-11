"""
원격 에이전트 토큰 추적 — PostToolUse 훅 (TaskOutput)
원격 태스크 .output 파일의 modelUsage를 파싱해 token_usage.json에 반영한다.

실행 방식:
  1. 훅 자동 실행 (PostToolUse → TaskOutput):
     stdin으로 JSON payload 수신 → tool_response에서 modelUsage 추출

  2. 수동 실행:
     python .status/remote_track.py --file <path/to/task.output>
     python .status/remote_track.py --file <path> --task "원격 에이전트: DailyScrap"
"""
import json
import os
import re
import sys

STATUS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, STATUS_DIR)
import show_tokens


def extract_model_usage_from_jsonl(text: str) -> dict[str, dict]:
    """JSONL 텍스트에서 type=result 라인의 modelUsage를 추출."""
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if obj.get('type') == 'result':
                usage = obj.get('modelUsage', {})
                if usage:
                    return usage
        except Exception:
            continue
    return {}


def extract_model_usage_from_file(file_path: str) -> dict[str, dict]:
    """output 파일에서 직접 modelUsage 추출."""
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        return extract_model_usage_from_jsonl(content)
    except Exception:
        return {}


def sum_tokens(model_usage: dict[str, dict]) -> tuple[int, float]:
    """modelUsage → (총 토큰 수, 비용 USD) 계산.
    inputTokens + outputTokens 합산 (cache 제외 — auto_track.py 일관성 유지).
    """
    total_tokens = 0
    total_cost = 0.0
    for model_name, usage in model_usage.items():
        total_tokens += usage.get('inputTokens', 0)
        total_tokens += usage.get('outputTokens', 0)
        total_cost += usage.get('costUSD', 0.0)
    return total_tokens, total_cost


def find_output_file_from_task_id(task_id: str) -> str | None:
    """task_id로 AppData/Local/Temp/claude 내 output 파일 탐색."""
    base = os.path.expandvars(r'%LOCALAPPDATA%\Temp\claude')
    if not os.path.exists(base):
        return None
    target = f'{task_id}.output'
    for root, dirs, files in os.walk(base):
        if target in files:
            return os.path.join(root, target)
    return None


def record_usage(tokens: int, cost_usd: float, task_label: str):
    """token_usage.json에 기록. 100 토큰 미만 노이즈는 건너뜀."""
    if tokens < 100:
        return False
    data = show_tokens.add_session(tokens, task_label)
    print(f'[remote_track] 기록 완료: +{tokens:,} tokens (${cost_usd:.4f})'
          f' → 누적 {data.get("used", 0):,} / {data.get("window_limit", 72000):,}',
          file=sys.stderr)
    return True


def run_from_stdin():
    """PostToolUse 훅 모드: stdin에서 JSON payload 읽기."""
    raw = sys.stdin.read().strip()
    if not raw:
        return

    try:
        payload = json.loads(raw)
    except Exception:
        return

    tool_name = payload.get('tool_name', '')
    if tool_name not in ('TaskOutput', 'RemoteTrigger'):
        return  # 관계없는 툴 무시

    model_usage = {}
    task_label = 'Remote Agent'

    # 1. tool_response에서 직접 파싱 (파일 내용이 짧은 경우)
    tool_response = payload.get('tool_response', '')
    if isinstance(tool_response, str) and tool_response:
        model_usage = extract_model_usage_from_jsonl(tool_response)

    # 2. tool_response에 없으면 task_id로 파일 탐색
    if not model_usage:
        task_id = payload.get('tool_input', {}).get('task_id', '')
        if task_id:
            task_label = f'Remote Agent: {task_id}'
            output_file = find_output_file_from_task_id(task_id)
            if output_file:
                model_usage = extract_model_usage_from_file(output_file)

    if not model_usage:
        return

    tokens, cost = sum_tokens(model_usage)
    record_usage(tokens, cost, task_label)


def run_from_file(file_path: str, task_label: str | None = None):
    """수동 모드: output 파일 경로를 직접 지정."""
    model_usage = extract_model_usage_from_file(file_path)
    if not model_usage:
        print(f'[remote_track] modelUsage 없음: {file_path}', file=sys.stderr)
        return

    label = task_label or f'Remote Agent: {os.path.basename(file_path)}'
    tokens, cost = sum_tokens(model_usage)
    print(f'[remote_track] 파일: {file_path}', file=sys.stderr)
    print(f'[remote_track] 모델: {list(model_usage.keys())}', file=sys.stderr)
    record_usage(tokens, cost, label)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='원격 에이전트 토큰 추적')
    parser.add_argument('--file', type=str, help='output 파일 경로 (수동 모드)')
    parser.add_argument('--task', type=str, help='작업 레이블 (수동 모드, 선택)')
    args = parser.parse_args()

    if args.file:
        run_from_file(args.file, args.task)
    else:
        run_from_stdin()
