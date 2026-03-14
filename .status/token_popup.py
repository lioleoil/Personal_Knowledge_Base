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


def show_popup(data):
    used     = data.get('used', 0)
    limit    = data.get('window_limit', data.get('daily_limit', 44000))
    plan     = data.get('plan', 'Pro')
    period   = data.get('date', '')
    sessions = data.get('sessions', [])
    pct      = min(used / limit * 100, 100) if limit > 0 else 0
    color    = get_bar_color(pct)

    warn_text  = None
    warn_color = RED
    if pct >= 90:
        warn_text  = '!  한도 90% 초과 — 속도 제한 임박'
        warn_color = RED
    elif pct >= 75:
        warn_text  = f'!  한도 75% 도달 — 잔여 {fmt(limit - used)} 토큰'
        warn_color = YELLOW

    recent = sessions[-2:] if sessions else []

    W = 420
    H = 138 + (22 if warn_text else 0) + len(recent) * 19

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

    # ── 진행 바 ───────────────────────────────
    bar_canvas = tk.Canvas(root, bg=BG2, height=13,
                           highlightthickness=0, relief='flat')
    bar_canvas.pack(fill='x', padx=pad, pady=(0, 3))

    def draw_bar(event=None):
        bar_canvas.update_idletasks()
        w = bar_canvas.winfo_width()
        filled = max(1, int(w * pct / 100))
        bar_canvas.delete('all')
        bar_canvas.create_rectangle(0, 0, w, 13, fill=BG2, outline='')
        bar_canvas.create_rectangle(0, 0, filled, 13, fill=color, outline='')

    bar_canvas.bind('<Configure>', draw_bar)

    # ── 수치 ──────────────────────────────────
    num = tk.Frame(root, bg=BG)
    num.pack(fill='x', padx=pad)
    tk.Label(num, text=f'{fmt(used)}  /  {fmt(limit)}', bg=BG, fg=color,
             font=('Consolas', 10, 'bold')).pack(side='left')
    tk.Label(num, text=f'{pct:.1f}%', bg=BG, fg=color,
             font=('Consolas', 10, 'bold')).pack(side='right')

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
    data = {'used': 0, 'window_limit': 44000, 'plan': 'Pro', 'date': '', 'sessions': []}
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            pass
    show_popup(data)
