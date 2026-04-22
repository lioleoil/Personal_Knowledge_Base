"""
OpenAI API 비용 추적기
- run_openai_agent() 호출 후 자동으로 track_usage() 실행
- 데이터: .status/openai_usage.json (모델별 토큰·비용·hourly_buckets)
- 수동 표시: python .status/openai_cost_tracker.py
"""
import json, os
from datetime import datetime, timedelta

STATUS_DIR = os.path.dirname(os.path.abspath(__file__))
USAGE_FILE = os.path.join(STATUS_DIR, 'openai_usage.json')

# USD per 1M tokens — model_config.json의 값이 우선 (track_usage의 model_costs 인자)
_DEFAULT_COSTS: dict[str, dict] = {
    'gpt-4.1':           {'input': 2.0,  'output': 8.0},
    'gpt-4.1-mini':      {'input': 0.40, 'output': 1.60},
    'codex-1':           {'input': 5.0,  'output': 20.0},
    'claude-sonnet-4-6': {'input': 3.0,  'output': 15.0},
    'claude-opus-4-6':   {'input': 15.0, 'output': 75.0},
    'claude-opus-4-7':   {'input': 5.0,  'output': 25.0},
}

# ANSI
R = '\033[0m'; BOLD = '\033[1m'
GREEN = '\033[92m'; YELLOW = '\033[93m'; ORANGE = '\033[38;5;208m'
RED = '\033[91m'; CYAN = '\033[96m'; GRAY = '\033[90m'; WHITE = '\033[97m'
MAGENTA = '\033[95m'


# ── 저장·로드 ──────────────────────────────────────────────────────

def _load() -> dict:
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'updated_at': '', 'models': {}, 'total_cost_usd': 0.0, 'sessions': []}


def _save(data: dict) -> None:
    with open(USAGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── hourly bucket ─────────────────────────────────────────────────

def _update_bucket(model_data: dict, input_tokens: int, output_tokens: int,
                   cost: float) -> None:
    """4시간 버킷 집계 (auto_track.py와 동일한 4h 구간 키 방식)."""
    now = datetime.now()
    bucket_h = (now.hour // 4) * 4
    bucket_key = now.strftime(f'%Y-%m-%d {bucket_h:02d}:00')
    buckets = model_data.setdefault('hourly_buckets', [])
    for b in buckets:
        if b['hour'] == bucket_key:
            b['input_tokens']  += input_tokens
            b['output_tokens'] += output_tokens
            b['cost_usd']      += cost
            return
    buckets.append({
        'hour': bucket_key,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'cost_usd': cost,
    })
    model_data['hourly_buckets'] = buckets[-42:]  # 7일치 유지


# ── 공개 API ───────────────────────────────────────────────────────

def track_usage(model: str, input_tokens: int, output_tokens: int,
                task_name: str, model_costs: dict | None = None) -> None:
    """호출 1회 분 토큰·비용을 openai_usage.json에 누적."""
    costs = {**_DEFAULT_COSTS, **(model_costs or {})}
    rate  = costs.get(model, {'input': 0.0, 'output': 0.0})
    cost  = (input_tokens * rate['input'] + output_tokens * rate['output']) / 1_000_000

    data = _load()
    md   = data['models'].setdefault(model, {
        'input_tokens': 0, 'output_tokens': 0, 'calls': 0,
        'cost_usd': 0.0, 'hourly_buckets': [],
    })
    md['input_tokens']  += input_tokens
    md['output_tokens'] += output_tokens
    md['calls']         += 1
    md['cost_usd']       = round(md['cost_usd'] + cost, 6)

    _update_bucket(md, input_tokens, output_tokens, cost)

    data['total_cost_usd'] = round(
        sum(m['cost_usd'] for m in data['models'].values()), 6
    )
    data['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data.setdefault('sessions', []).append({
        'model': model, 'task': task_name,
        'input_tokens': input_tokens, 'output_tokens': output_tokens,
        'cost_usd': round(cost, 6),
        'time': datetime.now().strftime('%H:%M:%S'),
    })
    # 세션 로그 최근 200개만 유지
    data['sessions'] = data['sessions'][-200:]
    _save(data)


def get_4h_cost(data: dict) -> float:
    """최근 4시간 OpenAI 누적 비용."""
    cutoff = (datetime.now() - timedelta(hours=4)).strftime('%Y-%m-%dT%H')
    total = 0.0
    for md in data.get('models', {}).values():
        for b in md.get('hourly_buckets', []):
            if b.get('hour', '') >= cutoff:
                total += b.get('cost_usd', 0.0)
    return total


def fmt_cost(v: float) -> str:
    if v >= 1.0:   return f'${v:.3f}'
    if v >= 0.001: return f'${v:.4f}'
    return f'${v:.6f}'


def fmt_tok(n: int) -> str:
    if n >= 1_000_000: return f'{n/1_000_000:.2f}M'
    if n >= 1_000:     return f'{n/1_000:.1f}k'
    return str(n)


def bar(pct: float, width: int = 30) -> str:
    filled = int(width * pct / 100)
    empty  = width - filled
    color  = GREEN if pct < 33 else YELLOW if pct < 66 else ORANGE if pct < 85 else RED
    return f'{color}{"#" * filled}{GRAY}{"-" * empty}{R}'


# ── 터미널 표시 ──────────────────────────────────────────────────

def display(data: dict | None = None) -> None:
    data = data or _load()
    models = data.get('models', {})
    if not models:
        print(f'\n  {GRAY}[ OpenAI 사용 기록 없음 ]{R}\n')
        return

    total_cost = data.get('total_cost_usd', 0.0)
    cost_4h    = get_4h_cost(data)
    updated    = data.get('updated_at', '-')
    sessions   = data.get('sessions', [])

    print()
    print(f'{BOLD}{WHITE}  [ OpenAI API 비용 현황 ]  {GRAY}[최종: {updated}]{R}')
    print(f'  {GRAY}4h 누적  {MAGENTA}{BOLD}{fmt_cost(cost_4h)}{R}   '
          f'{GRAY}전체 누적  {RED}{BOLD}{fmt_cost(total_cost)}{R}')
    print(f'  {GRAY}{"─"*48}{R}')

    # 모델별 테이블
    all_costs = [md['cost_usd'] for md in models.values()]
    max_cost  = max(all_costs) if all_costs else 1.0

    for model, md in sorted(models.items(), key=lambda x: -x[1]['cost_usd']):
        calls    = md['calls']
        in_tok   = md['input_tokens']
        out_tok  = md['output_tokens']
        cost     = md['cost_usd']
        pct      = (cost / max_cost * 100) if max_cost > 0 else 0
        b        = bar(pct, width=20)

        print(f'  {CYAN}{model:<22}{R}  {b}  '
              f'{YELLOW}{BOLD}{fmt_cost(cost)}{R}')
        print(f'  {GRAY}  호출 {calls}회  in {fmt_tok(in_tok)}  out {fmt_tok(out_tok)}{R}')

    # 최근 세션 로그
    if sessions:
        print(f'  {GRAY}{"─"*48}{R}')
        for s in sessions[-4:]:
            t     = s.get('time', '')
            name  = s.get('task', '')[:22]
            mdl   = s.get('model', '')[:16]
            cost  = fmt_cost(s.get('cost_usd', 0))
            print(f'  {GRAY}{t}  {CYAN}{mdl:<16}{R}  {GRAY}{name:<22}{R}  {YELLOW}+{cost}{R}')
    print()


# ── CLI ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    import io, sys
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    display()
