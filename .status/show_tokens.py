"""
터미널 토큰 사용량 바 — Claude Code Stop 훅에 의해 자동 실행
수동 실행: python .status/show_tokens.py [추가_토큰수] ["작업명"]
리셋 기준: 매일 14:00 (Claude Code 5시간 윈도우 관측값)
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
    알려진 기준점(2026-03-14 14:00)에서 5시간 단위로 계산."""
    now = datetime.now()
    anchor = datetime(2026, 3, 14, 14, 0, 0)
    delta_h = (now - anchor).total_seconds() / 3600
    window_idx = int(delta_h // 5)
    period_start = anchor + timedelta(hours=5 * window_idx)
    return period_start.strftime('%Y-%m-%d %H:%M')


def load():
    period = get_period_key()
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get('date') == period:
            return data
    return {'date': period, 'used': 0, 'window_limit': 72000, 'plan': 'Pro', 'sessions': [], 'transcripts': {}}


def save(data):
    with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_session(tokens, task_name):
    data = load()
    data['used'] = data.get('used', 0) + tokens
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

    print()
    print(f'{BOLD}{WHITE}  [ Claude Token Usage ]  {GRAY}[{plan} | 기준: {period}~]{R}')
    print(f'  {b}  {color}{BOLD}{pct:.1f}%{R}')
    print(f'  {GRAY}사용: {color}{BOLD}{fmt(used)}{R}{GRAY} / 윈도우: {WHITE}{fmt(limit)}{R}  '
          f'{GRAY}남은 토큰: {WHITE}{fmt(limit - used)}{R}')

    if pct >= 90:
        print(f'  {RED}{BOLD}[!] 한도 90% 초과 — 곧 속도 제한될 수 있음. 다음 리셋까지 사용 주의{R}')
    elif pct >= 75:
        print(f'  {YELLOW}[!] 한도 75% 도달 — 잔여 {fmt(limit - used)} 토큰{R}')

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
