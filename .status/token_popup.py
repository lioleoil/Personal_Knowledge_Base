"""
토큰 사용량 GUI 팝업 — Stop 훅 후 자동 표시 (우하단, 6초 후 자동 닫힘)
auto_track.py에서 백그라운드 서브프로세스로 호출됨
직접 실행: python .status/token_popup.py
"""
import tkinter as tk
import json, os

STATUS_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(STATUS_DIR, 'token_usage.json')

# 다크 테마 색상
BG      = '#1e1e1e'
BG2     = '#2a2a2a'
FG      = '#d4d4d4'
GREEN   = '#4ec994'
YELLOW  = '#e5c07b'
ORANGE  = '#d19a66'
RED     = '#e06c75'
GRAY    = '#5c6370'
WHITE   = '#ffffff'
BLUE    = '#61afef'

AUTO_CLOSE_MS = 6000  # 6초 후 자동 닫기
CHART_H = 72          # 라인 그래프 높이 (px)


def get_bar_color(pct):
    if pct < 50: return GREEN
    if pct < 75: return YELLOW
    if pct < 90: return ORANGE
    return RED


def fmt(n):
    if n >= 1_000_000:
        return f'{n / 1_000_000:.2f}M'
    if n >= 1_000:
        return f'{n / 1_000:.1f}k'
    return str(n)


def draw_line_chart(parent, buckets: list):
    """최근 hourly_buckets(4시간 단위)를 Line 그래프로 그린다.
    최근 12버킷(최대 2일치)을 표시한다.
    """
    label = tk.Label(parent, text='4h 사용량 추이', bg=BG, fg=GRAY,
                     font=('Consolas', 8))
    label.pack(anchor='w', padx=14, pady=(6, 1))

    canvas = tk.Canvas(parent, bg=BG2, height=CHART_H, highlightthickness=0)
    canvas.pack(fill='x', padx=14, pady=(0, 4))

    recent = buckets[-12:] if buckets else []

    def _draw(event=None):
        canvas.delete('all')
        w = canvas.winfo_width()
        if not recent or w < 10:
            canvas.create_text(w // 2, CHART_H // 2, text='데이터 없음',
                               fill=GRAY, font=('Consolas', 8))
            return
        vals = [b['tokens'] for b in recent]
        max_v = max(vals) if vals else 1
        n = len(vals)
        pad_x, pad_y = 6, 8
        step = (w - pad_x * 2) / max(n - 1, 1)
        points = [
            (pad_x + i * step,
             CHART_H - pad_y - int((v / max_v) * (CHART_H - pad_y * 2)))
            for i, v in enumerate(vals)
        ]
        # 그라디언트 영역 (폴리곤)
        poly_pts = [pad_x, CHART_H]
        for x, y in points:
            poly_pts += [x, y]
        poly_pts += [pad_x + (n - 1) * step, CHART_H]
        canvas.create_polygon(poly_pts, fill='#1a2a3a', outline='')
        # 라인
        for i in range(len(points) - 1):
            canvas.create_line(*points[i], *points[i + 1],
                               fill=BLUE, width=2, smooth=True)
        # 점
        for x, y in points:
            canvas.create_oval(x - 3, y - 3, x + 3, y + 3,
                               fill=BLUE, outline=BG, width=1)
        # 최대값 라벨
        canvas.create_text(w - 4, 4, text=fmt(max_v),
                           anchor='ne', fill=GRAY, font=('Consolas', 7))
        # 최신 버킷 시각 라벨
        if recent:
            last_label = recent[-1].get('hour', '')[-5:]  # HH:00
            canvas.create_text(w - 4, CHART_H - 4, text=last_label,
                               anchor='se', fill=GRAY, font=('Consolas', 7))

    canvas.bind('<Configure>', _draw)


def show_popup(data):
    used     = data.get('used', 0)
    limit    = data.get('window_limit', data.get('daily_limit', 44000))
    plan     = data.get('plan', 'Pro')
    period   = data.get('date', '')
    sessions = data.get('sessions', [])
    buckets  = data.get('hourly_buckets', [])
    pct      = min(used / limit * 100, 100) if limit > 0 else 0
    color    = get_bar_color(pct)

    weekly_used  = data.get('weekly_used', 0)
    weekly_limit = data.get('weekly_limit', 500000)
    week_start   = data.get('week_start', '')
    wpct         = min(weekly_used / weekly_limit * 100, 100) if weekly_limit > 0 else 0
    wcolor       = get_bar_color(wpct)

    warn_text  = None
    warn_color = RED
    if pct >= 90:
        warn_text  = '!  윈도우 90% 초과 — 속도 제한 임박'
        warn_color = RED
    elif pct >= 75:
        warn_text  = f'!  윈도우 75% 도달 — 잔여 {fmt(limit - used)} 토큰'
        warn_color = YELLOW
    elif wpct >= 80:
        warn_text  = f'!  주간 80% 초과 — 상위 5% 헤비유저 구간'
        warn_color = ORANGE

    recent = sessions[-2:] if sessions else []
    has_chart = len(buckets) >= 2  # 데이터 2개 이상일 때만 차트 표시

    W = 420
    H = 170 + (22 if warn_text else 0) + len(recent) * 19 + (CHART_H + 28 if has_chart else 0)

    root = tk.Tk()
    root.title('Token Usage')
    root.overrideredirect(True)       # 타이틀바 제거
    root.attributes('-topmost', True) # 항상 위
    root.configure(bg=BG)
    root.resizable(False, False)

    # 화면 우하단 배치
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f'{W}x{H}+{sw - W - 20}+{sh - H - 60}')

    pad = 14

    # ── 헤더 ──────────────────────────────────
    hdr = tk.Frame(root, bg=BG)
    hdr.pack(fill='x', padx=pad, pady=(11, 3))
    tk.Label(hdr, text='Claude Token Usage', bg=BG, fg=WHITE,
             font=('Consolas', 11, 'bold')).pack(side='left')
    tk.Label(hdr, text=f'{plan}  |  {period}~', bg=BG, fg=GRAY,
             font=('Consolas', 9)).pack(side='right', padx=(0, 2))

    # ── 5시간 윈도우 바 ───────────────────────
    tk.Label(root, text='5h 윈도우', bg=BG, fg=GRAY,
             font=('Consolas', 8)).pack(anchor='w', padx=pad, pady=(0, 1))
    bar_canvas = tk.Canvas(root, bg=BG2, height=11,
                           highlightthickness=0, relief='flat')
    bar_canvas.pack(fill='x', padx=pad, pady=(0, 2))

    def draw_bar(event=None):
        bar_canvas.update_idletasks()
        w = bar_canvas.winfo_width()
        filled = max(1, int(w * pct / 100))
        bar_canvas.delete('all')
        bar_canvas.create_rectangle(0, 0, w, 11, fill=BG2, outline='')
        bar_canvas.create_rectangle(0, 0, filled, 11, fill=color, outline='')

    bar_canvas.bind('<Configure>', draw_bar)

    num = tk.Frame(root, bg=BG)
    num.pack(fill='x', padx=pad)
    tk.Label(num, text=f'{fmt(used)} / {fmt(limit)}', bg=BG, fg=color,
             font=('Consolas', 9, 'bold')).pack(side='left')
    tk.Label(num, text=f'{pct:.1f}%', bg=BG, fg=color,
             font=('Consolas', 9, 'bold')).pack(side='right')

    # ── 주간 바 ───────────────────────────────
    tk.Label(root, text=f'주간 ({week_start}~)', bg=BG, fg=GRAY,
             font=('Consolas', 8)).pack(anchor='w', padx=pad, pady=(5, 1))
    wbar_canvas = tk.Canvas(root, bg=BG2, height=11,
                            highlightthickness=0, relief='flat')
    wbar_canvas.pack(fill='x', padx=pad, pady=(0, 2))

    def draw_wbar(event=None):
        wbar_canvas.update_idletasks()
        w = wbar_canvas.winfo_width()
        filled = max(1, int(w * wpct / 100))
        wbar_canvas.delete('all')
        wbar_canvas.create_rectangle(0, 0, w, 11, fill=BG2, outline='')
        wbar_canvas.create_rectangle(0, 0, filled, 11, fill=wcolor, outline='')

    wbar_canvas.bind('<Configure>', draw_wbar)

    wnum = tk.Frame(root, bg=BG)
    wnum.pack(fill='x', padx=pad)
    tk.Label(wnum, text=f'{fmt(weekly_used)} / {fmt(weekly_limit)}', bg=BG, fg=wcolor,
             font=('Consolas', 9, 'bold')).pack(side='left')
    tk.Label(wnum, text=f'{wpct:.1f}%', bg=BG, fg=wcolor,
             font=('Consolas', 9, 'bold')).pack(side='right')

    # ── 경고 ──────────────────────────────────
    if warn_text:
        tk.Label(root, text=warn_text, bg=BG, fg=warn_color,
                 font=('Consolas', 9, 'bold')).pack(anchor='w', padx=pad, pady=(4, 0))

    # ── 최근 세션 ─────────────────────────────
    if recent:
        tk.Frame(root, bg=GRAY, height=1).pack(fill='x', padx=pad, pady=(8, 2))
        for s in recent:
            row = tk.Frame(root, bg=BG)
            row.pack(fill='x', padx=pad)
            tk.Label(row, text=s.get('time', '')[:8], bg=BG, fg=GRAY,
                     font=('Consolas', 8)).pack(side='left')
            tk.Label(row, text=s.get('task', '')[:28], bg=BG, fg=BLUE,
                     font=('Consolas', 8)).pack(side='left', padx=6)
            tk.Label(row, text=f'+{fmt(s.get("tokens", 0))}', bg=BG, fg=YELLOW,
                     font=('Consolas', 8)).pack(side='right')

    # ── 4시간 단위 사용량 추이 그래프 ────────
    if has_chart:
        draw_line_chart(root, buckets)

    # ── 하단 바 (열기 버튼) ───────────────────
    footer = tk.Frame(root, bg=BG2)
    footer.pack(fill='x', side='bottom')
    open_btn = tk.Label(footer, text='  열기  ', bg=BG2, fg=GRAY,
                        font=('Consolas', 8), cursor='hand2')
    open_btn.pack(side='right', padx=6, pady=3)

    def open_file(e):
        import subprocess as sp
        sp.Popen(['explorer', TOKEN_FILE], shell=True)

    def close_all(e):
        # 열기 버튼 위 클릭은 닫기 무시 (open_file이 처리)
        if e.widget is open_btn:
            return
        root.destroy()

    open_btn.bind('<Button-1>', open_file)
    root.bind('<Button-1>', close_all)

    # 경고 상태이면 자동 닫힘 없음 — 직접 클릭해서 닫아야 함
    if not warn_text:
        root.after(AUTO_CLOSE_MS, root.destroy)

    root.mainloop()


if __name__ == '__main__':
    data = {
        'used': 0, 'window_limit': 72000, 'plan': 'Pro',
        'date': '', 'sessions': [], 'hourly_buckets': [],
    }
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            pass
    show_popup(data)
