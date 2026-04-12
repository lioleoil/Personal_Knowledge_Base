"""
터미널 토큰 사용량 바 — Claude Code Stop 훅에 의해 자동 실행
수동 실행: python .status/show_tokens.py [추가_토큰수] ["작업명"]
리셋 기준: 4시간 롤링 윈도우 / 주간 한도 별도 추적 (월~일)
Claude Pro 정책: 5시간당 72,000 토큰, 주간 한도는 극소수만 도달
"""
import json, os, sys
from datetime import datetime, timedelta

STATUS_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(STATUS_DIR, 'token_usage.json')

# ANSI 색상
R = '\033[0m'
BOLD = '\033[1m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
ORANGE = '\033[38;5;208m'
RED = '\033[91m'
CYAN = '\033[96m'
GRAY = '\033[90m'
WHITE = '\033[97m'


def get_period_key():
    """현재 시각 기준 4시간 윈도우의 시작 시각을 반환.
    하루를 6개 구간(00-04, 04-08, 08-12, 12-16, 16-20, 20-24)으로 분할."""
    now = datetime.now()
    block = (now.hour // 4) * 4
    period_start = now.replace(hour=block, minute=0, second=0, microsecond=0)
    return period_start.strftime('%Y-%m-%d %H:%M')


def get_4h_window_usage(data):
    """hourly_buckets에서 최근 4시간 합산. 버킷 없으면 data['used'] 반환."""
    buckets = data.get('hourly_buckets', [])
    if not buckets:
        return data.get('used', 0)
    cutoff = (datetime.now() - timedelta(hours=4)).strftime('%Y-%m-%dT%H')
    return sum(b.get('tokens', 0) for b in buckets if b.get('hour', '') >= cutoff)


def get_week_start():
    """이번 주 월요일 날짜를 반환 (주간 한도 리셋 기준)."""
    now = datetime.now()
    monday = now - timedelta(days=now.weekday())
    return monday.strftime('%Y-%m-%d')


def load():
    period = get_period_key()
    week_start = get_week_start()

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 주간 데이터 보존 (5시간 윈도우 리셋과 무관하게 주 단위 유지)
        saved_week = data.get('week_start', week_start)
        if saved_week != week_start:
            # 새 주 시작 — 주간 카운터 리셋
            weekly_used = 0
            saved_week = week_start
        else:
            weekly_used = data.get('weekly_used', 0)
        weekly_limit = data.get('weekly_limit', 500000)

        if data.get('date') == period:
            data['week_start'] = saved_week
            data['weekly_used'] = weekly_used
            data['weekly_limit'] = weekly_limit
            data.setdefault('hourly_buckets', [])
            return data
        else:
            # 새 4시간 윈도우 — 윈도우 데이터 리셋, 주간/버킷 데이터 유지
            return {
                'date': period, 'used': 0, 'window_limit': 72000,
                'plan': 'Pro', 'sessions': [], 'transcripts': {},
                'week_start': saved_week,
                'weekly_used': weekly_used,
                'weekly_limit': weekly_limit,
                'hourly_buckets': data.get('hourly_buckets', []),
            }

    return {
        'date': period, 'used': 0, 'window_limit': 72000,
        'plan': 'Pro', 'sessions': [], 'transcripts': {},
        'week_start': week_start, 'weekly_used': 0, 'weekly_limit': 500000,
        'hourly_buckets': [],
    }


def save(data):
    with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_session(tokens, task_name):
    data = load()
    data['used'] = data.get('used', 0) + tokens
    data['weekly_used'] = data.get('weekly_used', 0) + tokens
    data.setdefault('sessions', []).append({
        'task': task_name,
        'tokens': tokens,
        'time': datetime.now().strftime('%H:%M:%S'),
    })
    save(data)
    return data


def _update_hourly_bucket(data: dict, tokens: int, source: str = 'cli') -> None:
    """4시간 단위 버킷에 토큰 수를 집계. 최근 42개(7일치) 유지.
    source='agent_sdk' 이면 버킷의 sdk_tokens 필드에도 추가 집계.
    """
    now = datetime.now()
    bucket_h = (now.hour // 4) * 4
    bucket_key = now.strftime(f'%Y-%m-%d {bucket_h:02d}:00')
    buckets = data.setdefault('hourly_buckets', [])
    for b in buckets:
        if b['hour'] == bucket_key:
            b['tokens'] += tokens
            if source == 'agent_sdk':
                b['sdk_tokens'] = b.get('sdk_tokens', 0) + tokens
            return
    new_b: dict = {'hour': bucket_key, 'tokens': tokens}
    if source == 'agent_sdk':
        new_b['sdk_tokens'] = tokens
    buckets.append(new_b)
    data['hourly_buckets'] = buckets[-42:]


def add_agent_tokens(input_tokens: int, output_tokens: int,
                     task_name: str, model: str = '') -> None:
    """Anthropic SDK 에이전트 호출 토큰을 token_usage.json에 집계.
    hourly_buckets까지 업데이트하여 monitor.py 그래프에 반영된다.
    """
    total = input_tokens + output_tokens
    if total <= 0:
        return
    data = load()
    data['used'] = data.get('used', 0) + total
    data['weekly_used'] = data.get('weekly_used', 0) + total

    session: dict = {
        'task': task_name,
        'tokens': total,
        'time': datetime.now().strftime('%H:%M:%S'),
        'source': 'agent_sdk',
    }
    if model:
        session['model'] = model
    if input_tokens:
        session['input_tokens'] = input_tokens
    if output_tokens:
        session['output_tokens'] = output_tokens
    data.setdefault('sessions', []).append(session)

    _update_hourly_bucket(data, total, source='agent_sdk')
    save(data)


def bar(pct, width=40):
    filled = int(width * pct / 100)
    empty = width - filled
    if pct < 50:
        color = GREEN
    elif pct < 75:
        color = YELLOW
    elif pct < 90:
        color = ORANGE
    else:
        color = RED
    return f'{color}{"#" * filled}{GRAY}{"-" * empty}{R}', color


def fmt(n):
    if n >= 1_000_000:
        return f'{n/1_000_000:.2f}M'
    if n >= 1_000:
        return f'{n/1_000:.1f}k'
    return str(n)


def display(data):
    used = data.get('used', 0)
    limit = data.get('window_limit', data.get('daily_limit', 44000))
    plan = data.get('plan', 'Pro')
    sessions = data.get('sessions', [])
    period = data.get('date', '')
    pct = min(used / limit * 100, 100) if limit > 0 else 0
    b, color = bar(pct)

    weekly_used = data.get('weekly_used', 0)
    weekly_limit = data.get('weekly_limit', 500000)
    week_start = data.get('week_start', '')
    wpct = min(weekly_used / weekly_limit * 100, 100) if weekly_limit > 0 else 0
    wb, wcolor = bar(wpct, width=40)

    print()
    print(f'{BOLD}{WHITE}  [ Claude Token Usage ]  {GRAY}[{plan} | 윈도우: {period}~]{R}')
    print(f'  {GRAY}주간({week_start}~){R}  {wb}  {wcolor}{BOLD}{wpct:.1f}%{R}')
    print(f'  {GRAY}주간: {wcolor}{BOLD}{fmt(weekly_used)}{R}{GRAY} / {fmt(weekly_limit)}  남은: {WHITE}{fmt(weekly_limit - weekly_used)}{R}')

    if wpct >= 80:
        print(f'  {RED}{BOLD}[!] 주간 80% 초과 — 상위 5% 헤비유저 구간{R}')
    elif wpct >= 60:
        print(f'  {YELLOW}[!] 주간 60% 도달{R}')

    if sessions:
        recent = sessions[-3:]
        print(f'  {GRAY}─────────────────────────────────────────{R}')
        for s in recent:
            t = s.get('time', '')
            name = s.get('task', '작업')[:30]
            tok = fmt(s.get('tokens', 0))
            print(f'  {GRAY}{t}  {CYAN}{name:<30}{R}  {YELLOW}+{tok}{R}')
    print()


def display_openai_summary() -> None:
    """OpenAI 비용 요약 — openai_cost_tracker가 있을 때만 출력."""
    try:
        import importlib.util
        tracker_path = os.path.join(STATUS_DIR, 'openai_cost_tracker.py')
        if not os.path.exists(tracker_path):
            return
        spec = importlib.util.spec_from_file_location('openai_cost_tracker', tracker_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.display()
    except Exception:
        pass


if __name__ == '__main__':
    # UTF-8 출력 설정 (Windows 터미널 대응)
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    # 인수: [토큰수] [작업명]
    if len(sys.argv) >= 2:
        try:
            tokens = int(sys.argv[1])
            task = sys.argv[2] if len(sys.argv) >= 3 else '작업'
            data = add_session(tokens, task)
        except ValueError:
            data = load()
    else:
        data = load()
    display(data)
    display_openai_summary()
