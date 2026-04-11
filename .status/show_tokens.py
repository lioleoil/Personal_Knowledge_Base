"""
터미널 토큰 사용량 바 — Claude Code Stop 훅에 의해 자동 실행
수동 실행: python .status/show_tokens.py [추가_토큰수] ["작업명"]
리셋 기준: 5시간 롤링 윈도우 / 주간 한도 별도 추적 (월~일)
Claude Pro 정책: 5시간당 ~45메시지(짧은기준), 주간 한도는 극소수만 도달
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
    """현재 시각 기준 5시간 윈도우의 시작 시각을 반환.
    알려진 기준점(2026-03-15 07:57, 웹 실측)에서 5시간 단위로 계산."""
    now = datetime.now()
    anchor = datetime(2026, 3, 15, 8, 0, 0)
    delta_h = (now - anchor).total_seconds() / 3600
    window_idx = int(delta_h // 5)
    period_start = anchor + timedelta(hours=5 * window_idx)
    return period_start.strftime('%Y-%m-%d %H:%M')


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
            # 새 5시간 윈도우 — 윈도우 데이터 리셋, 주간/버킷 데이터 유지
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
    print(f'{BOLD}{WHITE}  [ Claude Token Usage ]  {GRAY}[{plan} | 기준: {period}~]{R}')
    print(f'  {GRAY}5h 윈도우{R}  {b}  {color}{BOLD}{pct:.1f}%{R}')
    print(f'  {GRAY}사용: {color}{BOLD}{fmt(used)}{R}{GRAY} / {fmt(limit)}  남은: {WHITE}{fmt(limit - used)}{R}')

    if pct >= 90:
        print(f'  {RED}{BOLD}[!] 윈도우 90% 초과 — 속도 제한 임박{R}')
    elif pct >= 75:
        print(f'  {YELLOW}[!] 윈도우 75% 도달 — 잔여 {fmt(limit - used)}{R}')

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
