"""
Claude Agent 대시보드 모니터
실행: python .status/monitor.py

- 프로젝트 전체에서 .agents/ 디렉토리를 자동 탐색
- 각 에이전트의 실행 기록을 카드로 표시
- 2초마다 자동 갱신
"""
import tkinter as tk
from tkinter import ttk
import json, os, threading, time
from datetime import datetime

PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
)
STATUS_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 색상 팔레트 ────────────────────────────────────────────────
BG_DARK   = '#12121E'
BG_CARD   = '#1E1E2E'
BG_INNER  = '#2A2A3E'
BG_LOG    = '#1A1A2E'
FG_HEAD   = '#FFFFFF'
FG_MAIN   = '#CCCCDD'
FG_DIM    = '#666688'
FG_DIMMER = '#444466'
C_BLUE    = '#4A90D9'
C_GREEN   = '#27AE60'
C_ORANGE  = '#E67E22'
C_RED     = '#E74C3C'
C_YELLOW  = '#F1C40F'

FOLDER_COLORS = {
    'Nova':              '#4A90D9',
    'ODD':               '#9B59B6',
    'OpenLABEL':         '#1ABC9C',
    'DQA':               '#E74C3C',
    'Gen1_Gen2_Labeling':'#E67E22',
    'Gen2_Policy':       '#E91E8C',
    'Career':            '#F39C12',
    'Python_Scripts':    '#27AE60',
    'Strategy_Business': '#3498DB',
    'projects/02_Profile': '#8E44AD',
    'Misc':              '#7F8C8D',
    # Agent Ecosystem 역할
    'execution':         '#4A90D9',
    'validation':        '#27AE60',
    'advisor':           '#E67E22',
    'reporter':          '#9B59B6',
    'orchestrator':      '#1ABC9C',
}

STATUS_MAP = {
    'waiting':   ('대기 중', FG_DIM),
    'running':   ('진행 중', C_BLUE),
    'completed': ('완료',    C_GREEN),
    'error':     ('오류',    C_RED),
}

POLL_INTERVAL = 2   # 초


# ── 데이터 로딩 ───────────────────────────────────────────────

def discover_agents() -> list[dict]:
    """프로젝트 전체에서 .agents/*.json 파일을 탐색, 최신순 정렬.
    .agents/bus/ 의 task 파일도 카드로 포함."""
    results = []
    skip = {'.git', '__pycache__', 'node_modules', '.claude'}
    for dirpath, dirnames, _ in os.walk(PROJECT_ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip]
        if '.agents' in dirnames:
            agents_dir = os.path.join(dirpath, '.agents')
            for subname in os.listdir(agents_dir):
                subpath = os.path.join(agents_dir, subname)
                # bus/ 디렉터리: task 요약 카드 생성
                if subname == 'bus' and os.path.isdir(subpath):
                    results.extend(_discover_bus_tasks(subpath))
                    continue
                if not os.path.isdir(subpath):
                    continue
                for fname in os.listdir(subpath):
                    if not fname.endswith('.json'):
                        continue
                    fpath = os.path.join(subpath, fname)
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        data['_path']  = fpath
                        data['_mtime'] = os.path.getmtime(fpath)
                        results.append(data)
                    except Exception:
                        continue
    STATUS_ORDER = {'running': 0, 'error': 1, 'waiting': 2, 'completed': 3}
    results.sort(key=lambda d: (
        STATUS_ORDER.get(d.get('status', 'waiting'), 2),
        -d['_mtime']
    ))
    return results


_BUS_FTYPES = [
    'user_decision', 'advisor_plan', 'validation', 'requirement',
    'manifest', 'result', 'advice', 'report', 'evaluation', 'learning',
]

def _parse_bus_fname(fname: str):
    """파일명에서 (task_id, ftype) 추출. task_id에 '_'가 포함된 경우도 처리."""
    stem = fname[:-5]  # .json 제거
    for ftype in _BUS_FTYPES:
        suffix = '_' + ftype
        if stem.endswith(suffix):
            return stem[:-len(suffix)], ftype
    return None, None


def _discover_bus_tasks(bus_dir: str) -> list[dict]:
    """bus/ 디렉터리에서 task_id별로 가장 최신 파일을 읽어 요약 카드 생성."""
    task_files: dict[str, list[str]] = {}
    for fname in os.listdir(bus_dir):
        if not fname.endswith('.json'):
            continue
        tid, ftype = _parse_bus_fname(fname)
        if tid is None:
            continue
        task_files.setdefault(tid, []).append(fname)

    cards = []
    for tid, fnames in task_files.items():
        # 가장 최신 파일로 상태 추론
        latest_path = None
        latest_mtime = 0
        domain = '?'
        verdict = None
        bus_status = 'running'
        file_types = []

        for fname in fnames:
            fpath = os.path.join(bus_dir, fname)
            mtime = os.path.getmtime(fpath)
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest_path = fpath
            _, ftype = _parse_bus_fname(fname)
            if ftype:
                file_types.append(ftype)

            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if ftype == 'manifest':
                    domain = data.get('domain', '?')
                elif ftype == 'validation':
                    verdict = data.get('verdict')
                    if verdict == 'PASS':
                        bus_status = 'completed' if 'report' in file_types else 'running'
                    elif verdict == 'FAIL':
                        bus_status = 'error'
                elif ftype == 'report':
                    bus_status = 'completed'
            except Exception:
                pass

        verdict_label = f' [{verdict}]' if verdict else ''

        # manifest만 있고 1시간 이상 경과 → stale (포기된 태스크)
        if file_types == ['manifest'] and (time.time() - latest_mtime) > 3600:
            bus_status = 'completed'

        card = {
            '_path':      latest_path or os.path.join(bus_dir, f'{tid}_manifest.json'),
            '_mtime':     latest_mtime,
            'agent_id':   tid,
            'title':      f'Bus Task: {domain}{verdict_label}',
            'agent_type': 'bus',
            'folder':     _infer_role_from_files(file_types),
            'status':     bus_status,
            'progress':   0,
            'message':    f'단계: {", ".join(file_types)}',
            'log':        [f'task_id: {tid}', f'domain: {domain}', f'verdict: {verdict or "-"}'],
            'started_at': None,
            'completed_at': None,
        }
        cards.append(card)
    return cards


def _infer_role_from_files(file_types: list[str]) -> str:
    """버스 파일 유형으로 현재 활성 에이전트 역할 추론."""
    if 'report' in file_types:
        return 'reporter'
    if 'advice' in file_types:
        return 'advisor'
    if 'validation' in file_types:
        return 'validation'
    if 'result' in file_types:
        return 'execution'
    return 'orchestrator'


def fmt(n: int) -> str:
    if n >= 1_000_000: return f'{n/1_000_000:.2f}M'
    if n >= 1_000:     return f'{n/1_000:.1f}k'
    return str(n)


def folder_color(folder: str) -> str:
    for key, color in FOLDER_COLORS.items():
        if key in folder:
            return color
    return C_BLUE


# ── 에이전트 카드 위젯 ─────────────────────────────────────────

class AgentCard(tk.Frame):
    def __init__(self, parent, data: dict):
        super().__init__(parent, bg=BG_CARD, bd=0)
        self._color = folder_color(data.get('folder', ''))
        self._build()
        self.refresh(data)

    def _build(self):
        tk.Frame(self, bg=self._color, height=3).pack(fill='x')

        inner = tk.Frame(self, bg=BG_INNER, padx=14, pady=10)
        inner.pack(fill='both', expand=True, padx=0, pady=0)

        # 헤더 행: 제목 + 폴더 태그
        hdr = tk.Frame(inner, bg=BG_INNER)
        hdr.pack(fill='x')
        self._title_lbl = tk.Label(hdr, text='', font=('', 11, 'bold'),
                                   bg=BG_INNER, fg=FG_HEAD, anchor='w')
        self._title_lbl.pack(side='left')
        self._folder_lbl = tk.Label(hdr, text='', font=('Consolas', 8),
                                    bg=self._color, fg=FG_HEAD, padx=6, pady=1)
        self._folder_lbl.pack(side='right')

        # 상태 배지 + 진행률
        row2 = tk.Frame(inner, bg=BG_INNER)
        row2.pack(fill='x', pady=(6, 0))
        self._status_lbl = tk.Label(row2, text='', font=('Consolas', 9, 'bold'),
                                    bg=BG_INNER, fg=FG_DIM, anchor='w')
        self._status_lbl.pack(side='left')
        self._time_lbl = tk.Label(row2, text='', font=('Consolas', 8),
                                  bg=BG_INNER, fg=FG_DIMMER)
        self._time_lbl.pack(side='right')

        # 최근 로그
        tk.Label(inner, text='최근 로그', font=('', 8),
                 bg=BG_INNER, fg=FG_DIM, anchor='w').pack(fill='x', pady=(6, 1))
        self._log_lbl = tk.Label(inner, text='—', font=('Consolas', 8),
                                 bg=BG_LOG, fg='#AAAACC', anchor='w',
                                 justify='left', wraplength=440,
                                 padx=6, pady=4)
        self._log_lbl.pack(fill='x')

    def refresh(self, data: dict):
        title   = data.get('title', data.get('agent_id', '알 수 없음'))
        folder  = data.get('folder', '')
        status  = data.get('status', 'waiting')
        logs    = data.get('log', [])
        message = data.get('message', '')

        label, fg = STATUS_MAP.get(status, ('알 수 없음', FG_DIM))

        # 시간 표시 (완료/오류면 completed_at, 진행 중이면 started_at)
        ts = data.get('completed_at') or data.get('started_at') or ''
        ts_short = ts[11:16] if len(ts) >= 16 else ts[:10]   # HH:MM or date

        self._title_lbl.config(text=title)
        self._folder_lbl.config(text=folder or '—')
        self._status_lbl.config(text=label, fg=fg)
        self._time_lbl.config(text=ts_short)

        recent = logs[-3:] if logs else ([message] if message else [])
        self._log_lbl.config(text='\n'.join(recent) or '—')


# ── 메인 앱 ───────────────────────────────────────────────────

C_GREEN2 = '#2ECC71'  # OpenAI 라인용 (C_GREEN과 구분)

class TokenLineGraph(tk.Frame):
    """
    token_usage.json + openai_usage.json 기반 라인 그래프.
    Claude(파랑), Claude SDK(오렌지), OpenAI(녹색) 3개 시리즈.
    """
    PAD_L, PAD_R, PAD_T, PAD_B = 44, 36, 10, 36

    def __init__(self, parent):
        super().__init__(parent, bg=BG_CARD, pady=4)
        tk.Label(self, text='토큰 사용량 (7일)', font=('Consolas', 9, 'bold'),
                 bg=BG_CARD, fg=FG_DIM).pack(anchor='w', padx=10)
        self._canvas = tk.Canvas(self, bg=BG_CARD, highlightthickness=0)
        self._canvas.pack(fill='both', expand=True, padx=8, pady=(0, 4))
        self._canvas.bind('<Configure>', lambda _: self._draw())
        self._canvas.bind('<Motion>', self._on_hover)
        self._canvas.bind('<Leave>', self._on_leave)
        self._token_file = os.path.join(STATUS_DIR, 'token_usage.json')
        self._oai_file   = os.path.join(STATUS_DIR, 'openai_usage.json')
        self._points: list = []   # [(px, py, bucket), ...]

    def refresh(self):
        self._draw()

    def _load_buckets(self) -> list[dict]:
        """Claude hourly_buckets에 OpenAI 토큰을 oai_tokens 필드로 병합."""
        buckets: dict[str, dict] = {}

        # Claude 토큰
        if os.path.exists(self._token_file):
            try:
                with open(self._token_file, encoding='utf-8') as f:
                    data = json.load(f)
                for b in data.get('hourly_buckets', []):
                    key = b.get('hour', '')
                    if key:
                        entry = dict(b)
                        entry.setdefault('oai_tokens', 0)
                        buckets[key] = entry
            except Exception:
                pass

        # OpenAI 토큰 — 전체 모델 시간대별 합산
        if os.path.exists(self._oai_file):
            try:
                with open(self._oai_file, encoding='utf-8') as f:
                    oai = json.load(f)
                for model_data in oai.get('models', {}).values():
                    for b in model_data.get('hourly_buckets', []):
                        key = b.get('hour', '')
                        if not key:
                            continue
                        tok = b.get('input_tokens', 0) + b.get('output_tokens', 0)
                        if key in buckets:
                            buckets[key]['oai_tokens'] = buckets[key].get('oai_tokens', 0) + tok
                        else:
                            buckets[key] = {'hour': key, 'tokens': 0, 'sdk_tokens': 0,
                                            'oai_tokens': tok}
            except Exception:
                pass

        return sorted(buckets.values(), key=lambda b: b.get('hour', ''))

    def _draw(self):
        c = self._canvas
        c.delete('all')
        self._points = []
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 10 or h < 20:
            return

        buckets = self._load_buckets()
        pl, pr, pt, pb = self.PAD_L, self.PAD_R, self.PAD_T, self.PAD_B
        gw = w - pl - pr
        gh = h - pt - pb

        # 축
        c.create_line(pl, pt, pl, pt + gh, fill=FG_DIMMER, width=1)
        c.create_line(pl, pt + gh, pl + gw, pt + gh, fill=FG_DIMMER, width=1)

        if not buckets:
            c.create_text(pl + gw // 2, pt + gh // 2,
                          text='데이터 없음', fill=FG_DIM, font=('Consolas', 9, 'bold'))
            return

        max_tok = max(
            max((b.get('tokens', 0) for b in buckets), default=0),
            max((b.get('oai_tokens', 0) for b in buckets), default=0),
        ) or 1

        # Y축 레이블
        for frac, lbl in [(0, '0'), (0.5, fmt(max_tok // 2)), (1.0, fmt(max_tok))]:
            y = pt + gh - int(frac * gh)
            c.create_line(pl - 3, y, pl, y, fill=FG_DIMMER)
            c.create_text(pl - 4, y, text=lbl, anchor='e',
                          fill=FG_DIM, font=('Consolas', 8, 'bold'))

        # 좌표 계산
        n = len(buckets)
        step = gw / max(n - 1, 1)
        raw_points = []
        sdk_points = []
        oai_points = []
        for i, b in enumerate(buckets):
            x = pl + int(i * step)
            ratio = b.get('tokens', 0) / max_tok
            y = pt + gh - int(ratio * gh)
            raw_points.append((x, y))
            self._points.append((x, y, b))

            sdk_tok = b.get('sdk_tokens', 0)
            sdk_points.append((x, pt + gh - int(sdk_tok / max_tok * gh)) if sdk_tok else None)

            oai_tok = b.get('oai_tokens', 0)
            oai_points.append((x, pt + gh - int(oai_tok / max_tok * gh)) if oai_tok else None)

        # 면적 채우기 (Claude 전체)
        if len(raw_points) >= 2:
            poly = [pl, pt + gh]
            for x, y in raw_points:
                poly += [x, y]
            poly += [raw_points[-1][0], pt + gh]
            c.create_polygon(poly, fill='#1A2A3E', outline='')

        # Claude 전체 라인 (파랑)
        if len(raw_points) >= 2:
            flat = [coord for px, py in raw_points for coord in (px, py)]
            c.create_line(flat, fill=C_BLUE, width=1.5, smooth=False)

        # Claude SDK 라인 (오렌지)
        sdk_valid = [(x, y) for x, y in zip(
            [p[0] for p in raw_points], [p[1] if p else None for p in sdk_points]
        ) if y is not None]
        if len(sdk_valid) >= 2:
            c.create_line([c for px, py in sdk_valid for c in (px, py)],
                          fill=C_ORANGE, width=2, smooth=False)
        for px, py in sdk_valid:
            c.create_oval(px-3, py-3, px+3, py+3, fill=C_ORANGE, outline=BG_CARD)

        # OpenAI 라인 (녹색)
        oai_valid = [(x, y) for x, y in zip(
            [p[0] for p in raw_points], [p[1] if p else None for p in oai_points]
        ) if y is not None]
        if len(oai_valid) >= 2:
            c.create_line([c for px, py in oai_valid for c in (px, py)],
                          fill=C_GREEN2, width=2, smooth=False)
        for px, py in oai_valid:
            c.create_oval(px-3, py-3, px+3, py+3, fill=C_GREEN2, outline=BG_CARD)

        # 범례
        has_sdk = bool(sdk_valid)
        has_oai = bool(oai_valid)
        lx = pl + gw - 2
        legend_y = pt + 6
        if has_sdk or has_oai:
            c.create_line(lx-18, legend_y, lx, legend_y, fill=C_BLUE, width=2)
            c.create_text(lx-20, legend_y, text='Claude', fill=C_BLUE,
                          font=('Consolas', 7, 'bold'), anchor='e')
            legend_y += 10
        if has_sdk:
            c.create_line(lx-18, legend_y, lx, legend_y, fill=C_ORANGE, width=2)
            c.create_text(lx-20, legend_y, text='SDK', fill=C_ORANGE,
                          font=('Consolas', 7, 'bold'), anchor='e')
            legend_y += 10
        if has_oai:
            c.create_line(lx-18, legend_y, lx, legend_y, fill=C_GREEN2, width=2)
            c.create_text(lx-20, legend_y, text='OpenAI', fill=C_GREEN2,
                          font=('Consolas', 7, 'bold'), anchor='e')

        # 포인트 + X축 레이블
        label_step = max(1, n // 7)
        prev_date = None
        for i, (x, y) in enumerate(raw_points):
            c.create_oval(x-3, y-3, x+3, y+3, fill=C_BLUE, outline=BG_CARD)
            if i % label_step == 0 or i == n - 1:
                hour_str  = buckets[i].get('hour', '')
                date_part = hour_str[5:10]
                time_part = hour_str[-5:]
                if date_part != prev_date:
                    lbl_text = f'{date_part}\n{time_part}'
                    prev_date = date_part
                else:
                    lbl_text = time_part
                c.create_text(x, pt + gh + 4, text=lbl_text,
                              fill=FG_DIM, font=('Consolas', 8, 'bold'), anchor='n')

    # ── 툴팁 ──────────────────────────────────────────────────────
    def _on_hover(self, event):
        if not self._points:
            return
        nearest = min(self._points, key=lambda p: abs(p[0] - event.x))
        px, py, bucket = nearest
        if abs(event.x - px) > 28:
            self._canvas.delete('tip')
            return
        hour   = bucket.get('hour', '')
        tokens = bucket.get('tokens', 0)
        sdk    = bucket.get('sdk_tokens', 0)
        oai    = bucket.get('oai_tokens', 0)
        tip    = f'{hour}  Claude {fmt(tokens)}'
        if sdk:
            tip += f'  SDK {fmt(sdk)}'
        if oai:
            tip += f'  OpenAI {fmt(oai)}'
        self._show_tip(px, py, tip)

    def _show_tip(self, px, py, text):
        c = self._canvas
        c.delete('tip')
        cw  = c.winfo_width()
        tx  = min(max(px, 55), cw - 55)
        ty  = max(py - 6, 14)
        pad = 4
        t   = c.create_text(tx, ty, text=text, fill=FG_HEAD,
                             font=('Consolas', 8, 'bold'), anchor='s', tags='tip')
        bb  = c.bbox(t)
        if bb:
            c.create_rectangle(bb[0]-pad, bb[1]-pad, bb[2]+pad, bb[3]+pad,
                                fill=BG_INNER, outline=FG_DIMMER, tags='tip')
            c.tag_raise(t)
        # 수직 가이드 선 + 강조 점
        pt_pad = self.PAD_T
        gh     = c.winfo_height() - pt_pad - self.PAD_B
        c.create_line(px, pt_pad, px, pt_pad + gh,
                      fill=FG_DIMMER, dash=(2, 3), tags='tip')
        c.create_oval(px-4, py-4, px+4, py+4,
                      fill=C_BLUE, outline=FG_HEAD, width=1, tags='tip')

    def _on_leave(self, _):
        self._canvas.delete('tip')


def fmt(n: int) -> str:
    if n >= 1000:
        return f'{n/1000:.1f}k'
    return str(n)


def fmt_cost(v: float) -> str:
    if v >= 1.0:   return f'${v:.3f}'
    if v >= 0.001: return f'${v:.4f}'
    return f'${v:.6f}'


class OpenAICostPanel(tk.Frame):
    """
    openai_usage.json 기반 모델별 비용 패널.
    파일이 없으면 표시하지 않고 높이 0으로 유지.
    """
    USAGE_FILE = os.path.join(STATUS_DIR, 'openai_usage.json')

    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self._inner: tk.Frame | None = None
        self.refresh()

    def refresh(self):
        data = self._load()
        if not data or not data.get('models'):
            if self._inner:
                self._inner.destroy()
            self._inner = tk.Frame(self, bg=BG_CARD, padx=12, pady=6)
            self._inner.pack(fill='x', padx=16, pady=(0, 4))
            hdr = tk.Frame(self._inner, bg=BG_CARD)
            hdr.pack(fill='x')
            tk.Label(hdr, text='OpenAI API 비용', font=('Consolas', 8, 'bold'),
                     bg=BG_CARD, fg='#BB86FC').pack(side='left')
            tk.Label(hdr, text='기록 없음', font=('Consolas', 8),
                     bg=BG_CARD, fg=FG_DIMMER).pack(side='left', padx=8)
            return
        self._rebuild(data)

    def _load(self) -> dict | None:
        if not os.path.exists(self.USAGE_FILE):
            return None
        try:
            with open(self.USAGE_FILE, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def _rebuild(self, data: dict):
        if self._inner:
            self._inner.destroy()
        self._inner = tk.Frame(self, bg=BG_CARD, padx=12, pady=8)
        self._inner.pack(fill='x', padx=16, pady=(0, 4))

        # 헤더
        hdr = tk.Frame(self._inner, bg=BG_CARD)
        hdr.pack(fill='x')
        tk.Label(hdr, text='OpenAI API 비용', font=('Consolas', 8, 'bold'),
                 bg=BG_CARD, fg='#BB86FC').pack(side='left')
        total = data.get('total_cost_usd', 0.0)
        updated = data.get('updated_at', '')
        tk.Label(hdr, text=f'누적 {fmt_cost(total)}   {updated}',
                 font=('Consolas', 8), bg=BG_CARD, fg=FG_DIM).pack(side='right')

        # 모델별 행
        models = data.get('models', {})
        all_costs = [md.get('cost_usd', 0) for md in models.values()] or [1]
        max_cost = max(all_costs) or 1

        for model, md in sorted(models.items(), key=lambda x: -x[1].get('cost_usd', 0)):
            cost    = md.get('cost_usd', 0.0)
            calls   = md.get('calls', 0)
            in_tok  = md.get('input_tokens', 0)
            out_tok = md.get('output_tokens', 0)
            pct     = cost / max_cost * 100

            row = tk.Frame(self._inner, bg=BG_CARD)
            row.pack(fill='x', pady=1)

            tk.Label(row, text=model, font=('Consolas', 8),
                     bg=BG_CARD, fg='#79DCFF', width=22, anchor='w').pack(side='left')

            bar_w = 120
            filled_w = max(2, int(bar_w * pct / 100))
            bar_frame = tk.Frame(row, bg=BG_INNER, width=bar_w, height=10)
            bar_frame.pack(side='left', padx=4)
            bar_frame.pack_propagate(False)
            color = C_GREEN if pct < 33 else C_YELLOW if pct < 66 else C_ORANGE if pct < 85 else C_RED
            tk.Frame(bar_frame, bg=color, width=filled_w, height=10).pack(side='left')

            summary = f'{fmt_cost(cost)}  {calls}회  in {fmt(in_tok)} out {fmt(out_tok)}'
            tk.Label(row, text=summary, font=('Consolas', 8),
                     bg=BG_CARD, fg=FG_MAIN).pack(side='left', padx=6)


class TokenWindow(tk.Toplevel):
    """토큰 사용량 그래프 독립 창."""

    def __init__(self, master):
        super().__init__(master)
        self.title('Token Usage')
        self.configure(bg=BG_DARK)
        self.resizable(True, True)
        self.minsize(400, 120)
        self._graph = TokenLineGraph(self)
        self._graph.pack(fill='both', expand=True, padx=16, pady=12)
        self._center()
        self._start_polling()

    def _start_polling(self):
        threading.Thread(target=self._poll, daemon=True).start()

    def _poll(self):
        while True:
            self.after(0, self._graph.refresh)
            time.sleep(POLL_INTERVAL)

    def _center(self):
        w, h = 560, 158
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f'{w}x{h}+{sw - w - 40}+{sh // 2 + 370}')


class MonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        ttk.Style(self).theme_use('clam')
        self.title('Claude Agent Monitor')
        self.configure(bg=BG_DARK)
        self.resizable(True, True)

        self._cards: dict[str, AgentCard] = {}   # path → card
        self._last_agents: list = []
        self._dismissed_paths: set[str] = set()  # 수동 제거된 에이전트 경로
        self._build_ui()
        self._center()
        self._start_polling()

    def _build_ui(self):
        # 헤더
        hdr = tk.Frame(self, bg=BG_DARK, padx=20, pady=12)
        hdr.pack(fill='x')
        tk.Label(hdr, text='Claude Agent Monitor', font=('', 14, 'bold'),
                 bg=BG_DARK, fg=FG_HEAD).pack(side='left')
        tk.Label(hdr, text='실행 중인 에이전트', font=('Consolas', 9),
                 bg=BG_DARK, fg=FG_DIM).pack(side='left', padx=(10, 0))

        self._clock = tk.Label(hdr, text='', font=('Consolas', 9),
                               bg=BG_DARK, fg=FG_DIM)
        self._clock.pack(side='right')

        self._cleanup_btn = tk.Label(hdr, text='버스 정리',
                                     font=('Consolas', 9), bg=BG_DARK,
                                     fg=FG_DIM, cursor='hand2', padx=8)
        self._cleanup_btn.pack(side='right')
        self._cleanup_btn.bind('<Button-1>', self._cleanup_bus)

        self._refresh_btn = tk.Label(hdr, text='새로고침',
                                     font=('Consolas', 9), bg=BG_DARK,
                                     fg=FG_DIM, cursor='hand2', padx=8)
        self._refresh_btn.pack(side='right')
        self._refresh_btn.bind('<Button-1>', self._immediate_refresh)

        # 스크롤 가능한 카드 영역
        scroll_outer = tk.Frame(self, bg=BG_DARK)
        scroll_outer.pack(fill='both', expand=True, padx=16, pady=8)

        self._canvas = tk.Canvas(scroll_outer, bg=BG_DARK,
                                 highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_outer, orient='vertical',
                                  command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self._canvas.pack(side='left', fill='both', expand=True)

        self._card_frame = tk.Frame(self._canvas, bg=BG_DARK)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._card_frame, anchor='nw')

        self._empty_lbl = tk.Label(self._card_frame,
                                   text='실행 중인 에이전트 없음',
                                   font=('Consolas', 12), bg=BG_DARK,
                                   fg=FG_DIM, pady=40)

        self._card_frame.bind('<Configure>', self._on_frame_resize)
        self._canvas.bind('<Configure>', self._on_canvas_resize)
        self._canvas.bind_all('<MouseWheel>', self._on_mousewheel)

        # 토큰 라인 그래프 (Claude)
        self._token_graph = TokenLineGraph(self)
        self._token_graph.pack(fill='x', padx=16, pady=(0, 4))

        # OpenAI 비용 패널
        self._openai_panel = OpenAICostPanel(self)
        self._openai_panel.pack(fill='x')


        # 푸터
        ftr = tk.Frame(self, bg=BG_DARK, padx=20, pady=6)
        ftr.pack(fill='x')
        self._summary = tk.Label(ftr, text='탐색 중...', font=('', 8),
                                 bg=BG_DARK, fg=FG_DIM)
        self._summary.pack(side='left')

    def _on_frame_resize(self, _):
        self._canvas.configure(scrollregion=self._canvas.bbox('all'))

    def _on_canvas_resize(self, e):
        self._canvas.itemconfig(self._canvas_window, width=e.width)

    def _on_mousewheel(self, e):
        self._canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units')

    def _poll(self):
        while True:
            now    = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            agents = discover_agents()
            self.after(0, lambda n=now, a=agents: self._refresh_ui(n, a))
            time.sleep(POLL_INTERVAL)

    def _repack_cards(self, agents: list):
        """실행 중인 에이전트 카드만 배치. 없으면 빈 상태 메시지 표시."""
        for card in self._cards.values():
            card.pack_forget()
        self._empty_lbl.pack_forget()

        any_running = False
        for data in agents:
            path   = data['_path']
            status = data.get('status', 'waiting')
            if status != 'running':
                continue
            if path in self._cards:
                self._cards[path].pack(fill='x', pady=(0, 8))
                any_running = True

        if not any_running:
            self._empty_lbl.pack(pady=40)

    def _refresh_ui(self, now: str, agents: list):
        self._clock.config(text=now)
        # dismissed 경로 제외
        agents = [d for d in agents if d['_path'] not in self._dismissed_paths]
        # stale running 자동 제외: completed_at 없고 1시간 이상 경과한 running 항목
        stale_cutoff = time.time() - 3600
        agents = [
            d for d in agents
            if not (
                d.get('status') == 'running'
                and d.get('completed_at') is None
                and d.get('_mtime', 0) < stale_cutoff
            )
        ]
        self._last_agents = agents

        running_paths = {d['_path'] for d in agents if d.get('status') == 'running'}

        # 더 이상 running이 아닌 카드 제거
        for path in list(self._cards):
            if path not in running_paths:
                self._cards[path].destroy()
                del self._cards[path]

        # running 에이전트 카드만 생성/갱신 (pack은 _repack_cards 에서 처리)
        for data in agents:
            if data.get('status') != 'running':
                continue
            path = data['_path']
            if path not in self._cards:
                self._cards[path] = AgentCard(self._card_frame, data)
            else:
                self._cards[path].refresh(data)

        self._repack_cards(agents)
        self._token_graph.refresh()
        self._openai_panel.refresh()

        # 상태 요약 — 최근 24시간 기준 (로그 내 타임스탬프 우선, fallback _mtime)
        cutoff_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cutoff_ts_24h = (datetime.now() - __import__('datetime').timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        def _is_recent(d: dict) -> bool:
            ts = d.get('completed_at') or d.get('started_at') or ''
            if ts:
                return ts >= cutoff_ts_24h
            return d.get('_mtime', 0) >= time.time() - 86400
        recent  = [d for d in agents if _is_recent(d)]
        running = sum(1 for d in agents if d.get('status') == 'running')
        done    = sum(1 for d in recent if d.get('status') == 'completed')
        error   = sum(1 for d in recent if d.get('status') == 'error')
        self._summary.config(
            text=f'실행 중 {running}개  |  최근 24h: 완료 {done}  오류 {error}')

    def _immediate_refresh(self, _=None):
        now    = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        agents = discover_agents()
        self._refresh_ui(now, agents)

    def _cleanup_bus(self, _=None):
        """버스 정리: stale bus task 파일 삭제.

        (1) manifest-only + 1시간 경과 (stale)
        (2) evaluation 또는 user_decision 존재 (완료 태스크)

        에이전트 로그 파일(.agents/<subtype>/*.json)은 건드리지 않음.
        stale running 항목은 _refresh_ui 자동 필터가 처리.
        """
        from tkinter import messagebox

        bus_dir = os.path.join(PROJECT_ROOT, '.agents', 'bus')
        if not os.path.exists(bus_dir):
            messagebox.showinfo('버스 정리', '정리할 항목 없음')
            return

        task_files: dict[str, list[str]] = {}
        for fname in os.listdir(bus_dir):
            if not fname.endswith('.json'):
                continue
            tid, ftype = _parse_bus_fname(fname)
            if tid:
                task_files.setdefault(tid, []).append(fname)

        to_del: list[str] = []
        for tid, fnames in task_files.items():
            ftypes = set()
            for f in fnames:
                _, ft = _parse_bus_fname(f)
                if ft:
                    ftypes.add(ft)
            mtimes = [os.path.getmtime(os.path.join(bus_dir, f)) for f in fnames]
            age = time.time() - max(mtimes)
            is_stale = (ftypes == {'manifest'} and age > 3600)
            is_done  = bool(ftypes & {'evaluation', 'user_decision'})
            if is_stale or is_done:
                to_del.extend(fnames)

        if not to_del:
            messagebox.showinfo('버스 정리', '정리할 항목 없음')
            return

        preview = '\n'.join(to_del[:10])
        if len(to_del) > 10:
            preview += f'\n... 외 {len(to_del)-10}개'
        if messagebox.askyesno('버스 정리', f'{len(to_del)}개 파일 삭제하시겠습니까?\n\n{preview}'):
            deleted = 0
            for fname in to_del:
                try:
                    os.remove(os.path.join(bus_dir, fname))
                    deleted += 1
                except Exception:
                    pass
            messagebox.showinfo('버스 정리', f'{deleted}개 파일 삭제 완료')
            self._immediate_refresh()

    def _start_polling(self):
        threading.Thread(target=self._poll, daemon=True).start()

    def _center(self):
        w, h = 560, 820
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f'{w}x{h}+{sw - w - 40}+{(sh - h) // 2}')


if __name__ == '__main__':
    # Windows: 중복 실행 방지 — 기존 인스턴스 종료 후 재시작
    import ctypes, signal
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, True, 'ClaudeAgentMonitor')
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        # 기존 창 찾아 종료
        hwnd = ctypes.windll.user32.FindWindowW(None, 'Claude Agent Monitor')
        if hwnd:
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            h = ctypes.windll.kernel32.OpenProcess(1, False, pid.value)
            ctypes.windll.kernel32.TerminateProcess(h, 0)
            ctypes.windll.kernel32.CloseHandle(h)
        time.sleep(0.4)
        # 새 mutex 획득
        ctypes.windll.kernel32.CloseHandle(_mutex)
        _mutex = ctypes.windll.kernel32.CreateMutexW(None, True, 'ClaudeAgentMonitor')

    app = MonitorApp()
    app.mainloop()
