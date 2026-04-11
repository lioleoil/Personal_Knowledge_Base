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


def _discover_bus_tasks(bus_dir: str) -> list[dict]:
    """bus/ 디렉터리에서 task_id별로 가장 최신 파일을 읽어 요약 카드 생성."""
    task_files: dict[str, list[str]] = {}
    for fname in os.listdir(bus_dir):
        if not fname.endswith('.json'):
            continue
        parts = fname[:-5].split('_', 1)
        if len(parts) != 2:
            continue
        tid, ftype = parts
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
            ftype = fname[:-5].split('_', 1)[1] if '_' in fname[:-5] else ''
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

        progress_map = {
            'manifest':   20,
            'result':     50,
            'validation': 70,
            'advice':     80,
            'report':     100,
        }
        progress = max((progress_map.get(ft, 0) for ft in file_types), default=0)
        verdict_label = f' [{verdict}]' if verdict else ''

        card = {
            '_path':      latest_path or os.path.join(bus_dir, f'{tid}_manifest.json'),
            '_mtime':     latest_mtime,
            'agent_id':   tid,
            'title':      f'Bus Task: {domain}{verdict_label}',
            'agent_type': 'bus',
            'folder':     _infer_role_from_files(file_types),
            'status':     bus_status,
            'progress':   progress,
            'message':    f'파일: {", ".join(file_types)}',
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

        # 진행 바
        style_key = id(self)
        s = ttk.Style()
        s.configure(f'{style_key}.H.TProgressbar',
                    troughcolor='#3A3A50', background=self._color,
                    thickness=7, borderwidth=0)
        self._prog_var = tk.IntVar(value=0)
        ttk.Progressbar(inner, variable=self._prog_var, maximum=100,
                        style=f'{style_key}.H.TProgressbar').pack(
            fill='x', pady=(4, 2))
        self._pct_lbl = tk.Label(inner, text='0%', font=('Consolas', 8),
                                 bg=BG_INNER, fg=self._color, anchor='e')
        self._pct_lbl.pack(fill='x')

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
        prog    = int(data.get('progress', 0))
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
        self._prog_var.set(prog)
        self._pct_lbl.config(text=f'{prog}%', fg=fg)

        recent = logs[-3:] if logs else ([message] if message else [])
        self._log_lbl.config(text='\n'.join(recent) or '—')


# ── 메인 앱 ───────────────────────────────────────────────────

class MonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Claude Agent Monitor')
        self.configure(bg=BG_DARK)
        self.resizable(True, True)

        self._cards: dict[str, AgentCard] = {}   # path → card
        self._hide_completed = False
        self._last_agents: list = []
        self._build_ui()
        self._center()
        self._start_polling()

    def _build_ui(self):
        # 헤더
        hdr = tk.Frame(self, bg=BG_DARK, padx=20, pady=12)
        hdr.pack(fill='x')
        tk.Label(hdr, text='Claude Agent Monitor', font=('', 14, 'bold'),
                 bg=BG_DARK, fg=FG_HEAD).pack(side='left')

        self._clock = tk.Label(hdr, text='', font=('Consolas', 9),
                               bg=BG_DARK, fg=FG_DIM)
        self._clock.pack(side='right')

        self._toggle_btn = tk.Label(hdr, text='완료 숨기기',
                                    font=('Consolas', 9), bg=BG_DARK,
                                    fg=FG_DIM, cursor='hand2', padx=8)
        self._toggle_btn.pack(side='right')
        self._toggle_btn.bind('<Button-1>', self._toggle_completed)

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

        self._card_frame.bind('<Configure>', self._on_frame_resize)
        self._canvas.bind('<Configure>', self._on_canvas_resize)
        self._canvas.bind_all('<MouseWheel>', self._on_mousewheel)

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

    def _toggle_completed(self, _=None):
        self._hide_completed = not self._hide_completed
        self._toggle_btn.config(
            text='완료 보기' if self._hide_completed else '완료 숨기기',
            fg=C_BLUE if self._hide_completed else FG_DIM,
        )
        self._repack_cards(self._last_agents)

    def _repack_cards(self, agents: list):
        """현재 숨기기 설정에 따라 카드를 순서대로 다시 배치."""
        for card in self._cards.values():
            card.pack_forget()
        for data in agents:
            path   = data['_path']
            status = data.get('status', 'waiting')
            if self._hide_completed and status == 'completed':
                continue
            if path in self._cards:
                self._cards[path].pack(fill='x', pady=(0, 8))

    def _refresh_ui(self, now: str, agents: list):
        self._clock.config(text=now)
        self._last_agents = agents

        current_paths = {d['_path'] for d in agents}

        # 사라진 카드 제거
        for path in list(self._cards):
            if path not in current_paths:
                self._cards[path].destroy()
                del self._cards[path]

        # 카드 생성/갱신 (pack은 _repack_cards 에서 처리)
        for data in agents:
            path = data['_path']
            if path not in self._cards:
                self._cards[path] = AgentCard(self._card_frame, data)
            else:
                self._cards[path].refresh(data)

        self._repack_cards(agents)

        # 상태 요약
        total   = len(agents)
        running = sum(1 for d in agents if d.get('status') == 'running')
        done    = sum(1 for d in agents if d.get('status') == 'completed')
        error   = sum(1 for d in agents if d.get('status') == 'error')
        hidden  = done if self._hide_completed else 0
        suffix  = f'  |  {hidden}개 숨김' if hidden else ''
        self._summary.config(
            text=f'에이전트 {total}개  |  진행 중 {running}  |  완료 {done}  |  오류 {error}{suffix}')

    def _start_polling(self):
        threading.Thread(target=self._poll, daemon=True).start()

    def _center(self):
        w, h = 560, 700
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f'{w}x{h}+{sw - w - 40}+{(sh - h) // 2}')


if __name__ == '__main__':
    ttk.Style().theme_use('clam')
    MonitorApp().mainloop()
