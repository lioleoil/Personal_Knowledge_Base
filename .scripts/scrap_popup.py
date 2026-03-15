"""
Daily Scrap 완료 팝업 — 우하단, 8초 자동 닫힘
daily_scrap_runner.py 완료 후 백그라운드 서브프로세스로 호출됨
직접 실행: python .scripts/scrap_popup.py
"""
import tkinter as tk
import json
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
RESULT_FILE  = PROJECT_ROOT / "04_WorkLog/Daily_Scrap/.scrap_result.json"

# 다크 테마 (token_popup.py 동일 팔레트)
BG     = '#1e1e1e'
BG2    = '#2a2a2a'
FG     = '#d4d4d4'
GREEN  = '#4ec994'
YELLOW = '#e5c07b'
BLUE   = '#61afef'
GRAY   = '#5c6370'
WHITE  = '#ffffff'

TOPIC_COLOR = {
    "AI/LLM":           GREEN,
    "자율주행/로보틱스": BLUE,
    "개발/오픈소스":    YELLOW,
    "비즈니스/스타트업": '#d19a66',
}

import webbrowser


def show_popup(data: dict):
    date     = data.get("date", "")
    count    = data.get("count", 0)
    articles = data.get("articles", [])

    W = 420
    H = 108 + len(articles) * 24

    root = tk.Tk()
    root.title("Daily Scrap")
    root.overrideredirect(True)        # 타이틀바 제거
    root.attributes("-topmost", True)  # 항상 위
    root.configure(bg=BG)
    root.resizable(False, False)

    # 화면 우하단 배치 (작업표시줄 여백 포함)
    root.withdraw()  # 위치 계산 전 숨김
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x  = 16
    y  = 16
    root.geometry(f"{W}x{H}+{x}+{y}")
    root.deiconify()  # 표시

    pad = 14

    # ── 헤더 ──────────────────────────────────
    hdr = tk.Frame(root, bg=BG)
    hdr.pack(fill="x", padx=pad, pady=(11, 3))
    tk.Label(
        hdr, text="Daily Scrap 완료", bg=BG, fg=WHITE,
        font=("Consolas", 11, "bold")
    ).pack(side="left")
    tk.Label(
        hdr, text=date, bg=BG, fg=GRAY,
        font=("Consolas", 9)
    ).pack(side="right", padx=(0, 2))

    # ── 구분선 ────────────────────────────────
    tk.Frame(root, bg="#3a3a3a", height=1).pack(fill="x", padx=pad, pady=(4, 6))

    # ── 기사 목록 (클릭 → 브라우저) ──────────
    for a in articles:
        url   = a.get("url", "")
        topic = a.get("topic", "")
        color = TOPIC_COLOR.get(topic, FG)

        row = tk.Frame(root, bg=BG, cursor="hand2")
        row.pack(fill="x", padx=pad, pady=2)

        topic_lbl = tk.Label(
            row, text=f"[{topic}]", bg=BG, fg=color,
            font=("Consolas", 8, "bold"), width=16, anchor="w", cursor="hand2"
        )
        topic_lbl.pack(side="left")

        title = a.get("title", "")
        short = title[:24] + ("…" if len(title) > 24 else "")
        title_lbl = tk.Label(
            row, text=short, bg=BG, fg=BLUE,
            font=("Consolas", 9, "underline"), anchor="w", cursor="hand2"
        )
        title_lbl.pack(side="left")

        def open_url(e, u=url):
            webbrowser.open(u)

        for widget in (row, topic_lbl, title_lbl):
            widget.bind("<Button-1>", open_url)
            widget.bind("<Enter>", lambda e, w=title_lbl: w.config(fg=WHITE))
            widget.bind("<Leave>", lambda e, w=title_lbl: w.config(fg=BLUE))

    # ── 하단 바 ───────────────────────────────
    footer = tk.Frame(root, bg=BG2)
    footer.pack(fill="x", side="bottom")
    tk.Label(
        footer,
        text=f"  GeekNews {count}개 기사 수집  ",
        bg=BG2, fg=GRAY, font=("Consolas", 8)
    ).pack(side="left", pady=3)

    close_btn = tk.Label(
        footer, text="  닫기  ",
        bg=BG2, fg=GRAY, font=("Consolas", 8), cursor="hand2"
    )
    close_btn.pack(side="right", padx=6, pady=3)

    def close(e=None):
        root.destroy()

    close_btn.bind("<Button-1>", close)

    root.mainloop()


if __name__ == "__main__":
    data = {"date": "", "count": 0, "articles": []}
    if RESULT_FILE.exists():
        try:
            data = json.loads(RESULT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    show_popup(data)
