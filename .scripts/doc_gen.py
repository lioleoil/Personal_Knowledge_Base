"""
doc_gen.py — Gemini → Confluence 문서 생성

사용법:
    python .scripts/doc_gen.py            # GUI 모드
    python .scripts/doc_gen.py "<prompt>" # CLI 모드
"""
import sys
import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

GEMINI_API_KEY       = os.getenv('GEMINI_API_KEY')
CONFLUENCE_URL       = os.getenv('CONFLUENCE_URL', 'https://stradvision.atlassian.net/wiki')
CONFLUENCE_USERNAME  = os.getenv('CONFLUENCE_USERNAME')
CONFLUENCE_API_TOKEN = os.getenv('CONFLUENCE_API_TOKEN')
CONFLUENCE_SPACE_KEY = os.getenv('CONFLUENCE_SPACE_KEY', 'TE')
PERPLEXITY_API_KEY   = os.getenv('PERPLEXITY_API_KEY', '')
PERPLEXITY_MODEL     = os.getenv('PERPLEXITY_MODEL', 'sonar')
CLAUDE_API_KEY       = os.getenv('CLAUDE_API_KEY', '')

WORKLOG_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'projects', '04_WorkLog')
)

USER_CONTEXT = """\
이름: 박성환 | 직책: PO/PM — 자율주행 데이터 어노테이션팀 (Team Data Quality Assurance)
회사: StradVision | 스페이스: TE(DQA), DIC, DPP
도메인: 자율주행 데이터 어노테이션, 데이터 품질 관리, Nova 플랫폼
역량: Python, 데이터 파이프라인, AI/ML 데이터 운영, 프로젝트 기획·관리
성향: ESTP, 자기완결적 본질주의자
"""

SPACES = [
    ('TE',  'Team Data Quality Assurance'),
    ('DIC', 'Data Innovation Center'),
    ('DPP', 'Data Policy Part'),
]

DOC_TEMPLATES = {
    '일반 문서':    '',
    '기술 스펙':    (
        '기술 명세서 형식으로 작성하세요. '
        '목적, 범위, 기술 요구사항, 아키텍처, API 명세, 제약사항 섹션을 포함하세요.'
    ),
    '가이드라인':   (
        '가이드라인/지침 문서 형식으로 작성하세요. '
        '개요, 적용 범위, 상세 지침, 예외사항, FAQ 섹션을 포함하세요.'
    ),
    '회의록':       (
        '회의록 형식으로 작성하세요. '
        '일시·장소·참석자, 안건, 논의 내용, 결정사항, Action Items 섹션을 포함하세요.'
    ),
    '분석 보고서':  (
        '분석 보고서 형식으로 작성하세요. '
        '요약, 배경, 분석 방법, 결과, 인사이트, 권고사항 섹션을 포함하세요.'
    ),
    '온보딩 문서':  (
        '온보딩 가이드 형식으로 작성하세요. '
        '목적, 사전 준비, 단계별 절차, 주의사항, 참고 자료 섹션을 포함하세요.'
    ),
    '기획안':       (
        '기획안 형식으로 작성하세요. '
        '배경 및 목적, 현황 분석, 제안 내용, 기대 효과, 일정 및 리소스, 리스크 섹션을 포함하세요.'
    ),
    '데이터 품질 보고서': (
        '데이터 품질 보고서 형식으로 작성하세요. '
        '대상 데이터셋, 품질 지표 정의, 측정 결과, 이슈 목록, 개선 조치 섹션을 포함하세요.'
    ),
}


IMAGE_EXTS = {'.png': 'image/png', '.jpg': 'image/jpeg',
              '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
TEXT_EXTS  = {'.md', '.txt'}


def search_worklog_context(prompt: str, max_chars: int = 2000) -> str:
    """로컬 04_WorkLog에서 관련 대화 내용 추출"""
    keywords = [w.lower() for w in prompt.split() if len(w) > 1]
    if not keywords:
        return ""
    ranked = []
    try:
        for root_dir, _, files in os.walk(WORKLOG_DIR):
            for fname in files:
                if not fname.endswith('.md') or fname in ('INDEX.md',):
                    continue
                path = os.path.join(root_dir, fname)
                try:
                    text = open(path, encoding='utf-8').read()
                except Exception:
                    continue
                hits = sum(text.lower().count(kw) for kw in keywords)
                if hits > 0:
                    ranked.append((hits, fname, text))
    except Exception:
        return ""
    ranked.sort(reverse=True)
    snippets, total = [], 0
    for _, fname, text in ranked[:3]:
        chunk = text[:800]
        snippets.append(f"[{fname}]\n{chunk}")
        total += len(chunk)
        if total >= max_chars:
            break
    return "\n\n".join(snippets)


def enrich_with_claude(prompt: str, template_key: str, space_key: str) -> tuple[str, str]:
    """Claude API로 프롬프트 맥락 재구성 → (enriched_context, search_query)"""
    space_name = next((n for k, n in SPACES if k == space_key), space_key)

    worklog = search_worklog_context(prompt)
    worklog_section = f"\n[WorkLog 관련 대화]\n{worklog}" if worklog else ""

    system_prompt = (
        "당신은 자율주행 데이터 어노테이션 도메인의 PO/PM 보조 AI입니다. "
        "사용자의 프롬프트가 어떤 배경·의도·맥락에서 나왔는지 재구성하고, "
        "이를 바탕으로 (1) 풍부한 배경 설명(enriched context)과 "
        "(2) 웹 검색에 최적화된 검색 쿼리를 생성하세요.\n\n"
        "반드시 아래 형식으로만 응답하세요:\n"
        "[CONTEXT]\n<재구성된 배경 및 의도 설명>\n"
        "---QUERY---\n<검색 쿼리>"
    )
    user_content = (
        f"[사용자 프로필]\n{USER_CONTEXT}\n"
        f"[문서 유형] {template_key} | [팀] {space_name}"
        f"{worklog_section}\n\n"
        f"[요청]\n{prompt}"
    )

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}],
        },
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Claude API 오류 {resp.status_code}: {resp.text[:300]}")

    text = resp.json()["content"][0]["text"]
    if "---QUERY---" in text:
        ctx_part, _, query_part = text.partition("---QUERY---")
        enriched = ctx_part.replace("[CONTEXT]", "").strip()
        query    = query_part.strip()
    else:
        enriched = text.strip()
        query    = prompt

    return enriched, query


def call_perplexity(prompt: str) -> tuple[str, list[str]]:
    """Perplexity API 호출 → (content, citations[])"""
    payload = {
        "model": PERPLEXITY_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                 "Content-Type": "application/json"},
        json=payload, timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Perplexity 오류 {resp.status_code}: {resp.text[:300]}")
    data      = resp.json()
    content   = data["choices"][0]["message"]["content"]
    citations = data.get("citations", [])
    return content, citations


def call_gemini(prompt: str, template_key: str = '일반 문서',
                attachments: list[str] | None = None,
                perplexity_context: tuple[str, list[str]] | None = None,
                enriched_context: str | None = None) -> tuple[str, str]:
    """Gemini API 호출 → (title, markdown_body)"""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)

    template_instruction = DOC_TEMPLATES.get(template_key, '')
    format_suffix = f'\n\n문서 형식 지침: {template_instruction}' if template_instruction else ''
    web_search_suffix = (
        '\n\n제공된 [배경 맥락]과 [웹 검색 결과]를 참고하여 충분한 본문을 직접 작성하고, '
        '본문 마지막에 ## 참고 출처 섹션을 추가하세요.'
        if (perplexity_context or enriched_context) else ''
    )

    system_instruction = (
        "당신은 기술 문서 작성 전문가입니다. "
        "사용자의 [요청]을 바탕으로 Confluence에 올릴 완전한 문서를 직접 작성하세요. "
        "[배경 맥락]과 [웹 검색 결과]는 참고 자료이며, 그 내용을 그대로 복붙하지 마세요.\n\n"
        "반드시 아래 형식으로만 응답하세요:\n"
        "TITLE: [문서 제목]\n"
        "---\n"
        "[마크다운 본문]\n\n"
        f"본문은 명확하고 구조적인 마크다운 형식으로 작성하세요. "
        f"비교·목록·속성·단계·결과 등 표로 표현할 수 있는 내용은 반드시 마크다운 표(| 형식)로 작성하세요. "
        f"각 섹션 헤딩(## 등)에는 내용에 어울리는 이모지를 앞에 붙여 가독성을 높이세요. "
        f"수치 분석에서 증가·상승을 나타내는 수치는 <span style=\"color:#e53e3e;\">값</span>, "
        f"감소·하락을 나타내는 수치는 <span style=\"color:#3182ce;\">값</span> 형식의 HTML 태그로 감싸세요.{format_suffix}{web_search_suffix}"
    )

    parts = []
    if perplexity_context or enriched_context:
        content, citations = perplexity_context or ("", [])
        ref_text = "\n".join(f"[{i+1}] {u}" for i, u in enumerate(citations))
        ctx_block = f"[배경 맥락 - 참고용]\n{enriched_context}\n\n" if enriched_context else ""
        web_block = f"[웹 검색 결과 - 참고용]\n{content}\n\n[인용 출처]\n{ref_text}\n" if content else ""
        parts.insert(0, types.Part(text=ctx_block + web_block))
    for path in (attachments or []):
        ext  = os.path.splitext(path)[1].lower()
        name = os.path.basename(path)
        if ext in IMAGE_EXTS:
            with open(path, 'rb') as f:
                parts.append(types.Part(
                    inline_data=types.Blob(mime_type=IMAGE_EXTS[ext], data=f.read())
                ))
        elif ext in TEXT_EXTS:
            with open(path, encoding='utf-8') as f:
                parts.append(types.Part(text=f"[첨부: {name}]\n{f.read()}\n"))
    parts.append(types.Part(text=f"요청: {prompt}"))

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=parts,
        config=types.GenerateContentConfig(system_instruction=system_instruction),
    )
    text = response.text.strip()

    if 'TITLE:' not in text or '---' not in text:
        raise ValueError(f"Gemini 응답 형식 오류:\n{text[:300]}")

    title_line, _, body = text.partition('---')
    title = title_line.replace('TITLE:', '').strip()
    body  = body.strip()

    return title, body


def markdown_to_storage(md: str) -> str:
    """마크다운 → Confluence Storage Format(HTML)"""
    import markdown as md_lib
    html = md_lib.markdown(md, extensions=['fenced_code', 'tables'])
    return html


def _make_auth_header() -> dict:
    token = base64.b64encode(
        f"{CONFLUENCE_USERNAME}:{CONFLUENCE_API_TOKEN}".encode()
    ).decode()
    return {
        'Authorization': f'Basic {token}',
        'Content-Type':  'application/json',
        'Accept':        'application/json',
    }


def create_confluence_page(title: str, body_html: str, space_key: str) -> str:
    """Confluence REST API로 페이지 생성 → 페이지 URL 반환"""
    headers = _make_auth_header()

    payload = {
        'type':  'page',
        'title': title,
        'space': {'key': space_key},
        'body':  {
            'storage': {
                'value':          body_html,
                'representation': 'storage',
            }
        },
    }

    resp = requests.post(
        f"{CONFLUENCE_URL}/rest/api/content",
        json=payload,
        headers=headers,
        timeout=30,
    )

    if not resp.ok:
        raise RuntimeError(
            f"Confluence API 오류 {resp.status_code}: {resp.text[:500]}"
        )

    data  = resp.json()
    links = data.get('_links', {})
    base  = links.get('base', CONFLUENCE_URL)
    tiny  = links.get('tinyui') or f"/pages/{data['id']}"
    return base + tiny


# ──────────────────────────────────────────
# GUI 모드
# ──────────────────────────────────────────

def launch_gui():
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox, filedialog
    import threading
    import webbrowser

    root = tk.Tk()
    root.title("Nova Doc Generator")
    root.resizable(False, False)

    PAD  = dict(padx=14, pady=7)
    PADR = dict(padx=14, pady=2)

    # ── 스페이스 선택 ──
    tk.Label(root, text="스페이스", anchor='w').grid(row=0, column=0, sticky='w', **PAD)
    space_combo = ttk.Combobox(root, values=[f"{k}  —  {n}" for k, n in SPACES],
                               width=38, state='readonly')
    default_idx = next((i for i, (k, _) in enumerate(SPACES) if k == CONFLUENCE_SPACE_KEY), 0)
    space_combo.current(default_idx)
    space_combo.grid(row=0, column=1, sticky='ew', **PAD)

    # ── 문서 템플릿 선택 ──
    tk.Label(root, text="문서 템플릿", anchor='w').grid(row=1, column=0, sticky='w', **PAD)
    template_combo = ttk.Combobox(root, values=list(DOC_TEMPLATES.keys()),
                                  width=38, state='readonly')
    template_combo.current(0)
    template_combo.grid(row=1, column=1, sticky='ew', **PAD)

    # ── 프롬프트 ──
    tk.Label(root, text="프롬프트", anchor='nw').grid(row=2, column=0, sticky='nw', **PAD)
    prompt_box = scrolledtext.ScrolledText(root, width=54, height=8, wrap='word')
    prompt_box.grid(row=2, column=1, sticky='ew', **PAD)

    # ── 파일 첨부 ──
    tk.Label(root, text="파일 첨부", anchor='nw').grid(row=3, column=0, sticky='nw', **PADR)
    attach_outer = tk.Frame(root)
    attach_outer.grid(row=3, column=1, sticky='ew', **PADR)

    attached: list[str] = []
    tag_frame = tk.Frame(attach_outer)
    tag_frame.pack(side='top', fill='x')

    def refresh_tags():
        for w in tag_frame.winfo_children():
            w.destroy()
        for path in attached:
            name = os.path.basename(path)
            cell = tk.Frame(tag_frame, relief='groove', bd=1)
            cell.pack(side='left', padx=2, pady=2)
            tk.Label(cell, text=name, font=('', 8)).pack(side='left', padx=4)
            tk.Button(cell, text='×', font=('', 8), bd=0, fg='red',
                      command=lambda p=path: (attached.remove(p), refresh_tags())).pack(side='left')

    def pick_files():
        paths = filedialog.askopenfilenames(
            title="첨부 파일 선택",
            filetypes=[
                ("지원 파일", "*.md *.txt *.png *.jpg *.jpeg *.webp"),
                ("마크다운/텍스트", "*.md *.txt"),
                ("이미지", "*.png *.jpg *.jpeg *.webp"),
            ]
        )
        for p in paths:
            if p not in attached:
                attached.append(p)
        refresh_tags()

    ttk.Button(attach_outer, text="파일 선택", command=pick_files).pack(side='top', anchor='w')

    # ── 웹 검색 토글 ──
    web_search_var = tk.BooleanVar(value=False)
    tk.Checkbutton(root, text="웹 검색 사용 (Perplexity)",
                   variable=web_search_var).grid(row=4, column=1, sticky='w', **PADR)

    # ── 생성 버튼 ──
    btn = ttk.Button(root, text="문서 생성")
    btn.grid(row=5, column=1, sticky='e', **PAD)

    # ── 상태 표시 ──
    status_var = tk.StringVar(value="")
    status_lbl = tk.Label(root, textvariable=status_var, anchor='w',
                          fg='gray', wraplength=440, justify='left')
    status_lbl.grid(row=6, column=0, columnspan=2, sticky='w', **PAD)

    def on_generate():
        prompt = prompt_box.get('1.0', 'end').strip()
        if not prompt:
            messagebox.showwarning("입력 필요", "프롬프트를 입력하세요.")
            return

        if web_search_var.get() and not PERPLEXITY_API_KEY:
            messagebox.showwarning("설정 필요", "PERPLEXITY_API_KEY를 .env에 설정하세요.")
            return

        if web_search_var.get() and not CLAUDE_API_KEY:
            messagebox.showwarning("설정 필요", "CLAUDE_API_KEY를 .env에 설정하세요.")
            return

        space_key    = SPACES[space_combo.current()][0]
        template_key = template_combo.get()
        files        = list(attached)

        btn.state(['disabled'])
        status_lbl.config(fg='gray', cursor='arrow')
        status_lbl.unbind('<Button-1>')
        status_var.set("Gemini로 문서 생성 중...")

        def run():
            try:
                enriched_ctx, search_q, perplexity_ctx = None, None, None
                if web_search_var.get():
                    root.after(0, lambda: status_var.set("[1/3] 맥락 재구성 중 (Claude)..."))
                    enriched_ctx, search_q = enrich_with_claude(prompt, template_key, space_key)
                    root.after(0, lambda: status_var.set("[2/3] 웹 검색 중 (Perplexity)..."))
                    perplexity_ctx = call_perplexity(search_q)
                root.after(0, lambda: status_var.set(
                    "[3/3] 문서 생성 중 (Gemini)..." if web_search_var.get() else "문서 생성 중 (Gemini)..."
                ))
                title, body_md = call_gemini(prompt, template_key, files, perplexity_ctx, enriched_ctx)
                root.after(0, lambda: status_var.set(f"Confluence 업로드 중... (제목: {title})"))
                body_html = markdown_to_storage(body_md)
                url = create_confluence_page(title, body_html, space_key)
                root.after(0, lambda: on_success(url))
            except Exception as e:
                msg = str(e)
                root.after(0, lambda: on_error(msg))

        threading.Thread(target=run, daemon=True).start()

    def on_success(url):
        status_var.set(f"완료  →  {url}")
        status_lbl.config(fg='#0066cc', cursor='hand2')
        status_lbl.bind('<Button-1>', lambda _: webbrowser.open(url))
        btn.state(['!disabled'])

    def on_error(msg):
        status_var.set(f"오류: {msg[:120]}")
        status_lbl.config(fg='red', cursor='arrow')
        btn.state(['!disabled'])
        messagebox.showerror("오류", msg)

    btn.config(command=on_generate)
    root.mainloop()


# ──────────────────────────────────────────
# CLI 모드
# ──────────────────────────────────────────

def main():
    missing = [v for v in ['GEMINI_API_KEY', 'CONFLUENCE_USERNAME', 'CONFLUENCE_API_TOKEN']
               if not os.getenv(v)]
    if missing:
        print(f"오류: .scripts/.env에 다음 값을 설정하세요: {', '.join(missing)}")
        sys.exit(1)

    if len(sys.argv) < 2:
        launch_gui()
        return

    prompt = ' '.join(sys.argv[1:])

    print("\n[스페이스 선택]")
    for i, (key, name) in enumerate(SPACES, 1):
        print(f"  {i}. {key}  —  {name}")
    print(f"선택 (기본값 {CONFLUENCE_SPACE_KEY}): ", end='', flush=True)
    raw = input().strip()
    if raw.isdigit() and 1 <= int(raw) <= len(SPACES):
        space_key = SPACES[int(raw) - 1][0]
    else:
        space_key = CONFLUENCE_SPACE_KEY

    template_names = list(DOC_TEMPLATES.keys())
    print("\n[문서 템플릿 선택]")
    for i, name in enumerate(template_names, 1):
        print(f"  {i}. {name}")
    print("선택 (기본값 1): ", end='', flush=True)
    raw = input().strip()
    if raw.isdigit() and 1 <= int(raw) <= len(template_names):
        template_key = template_names[int(raw) - 1]
    else:
        template_key = template_names[0]

    print("\n[1/3] Gemini로 문서 생성 중...")
    title, body_md = call_gemini(prompt, template_key)
    print(f"      제목: {title}")

    print("[2/3] Confluence 페이지 생성 중...")
    body_html = markdown_to_storage(body_md)
    page_url  = create_confluence_page(title, body_html, space_key)

    print(f"[완료] {page_url}")


if __name__ == '__main__':
    main()
