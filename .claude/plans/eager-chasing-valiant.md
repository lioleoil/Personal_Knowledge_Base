# Plan: doc_gen.py — Claude-중심 3단계 파이프라인

## Context
사용자 raw 프롬프트를 Gemini에 직접 넘기는 대신,
**Claude API**가 먼저 받아서 로컬 WorkLog 검색 + 사용자 프로필 참조로 맥락을 재구성한 뒤
Perplexity → Gemini 순으로 전달하는 3단계 파이프라인 구축.
Confluence는 최종 문서 업로드 엔드포인트로만 사용.

---

## 실행 흐름

```
사용자 raw 프롬프트 (+ 첨부파일)
    ↓
[Stage 0] Claude API — 맥락 재구성  ← 웹 검색 ON 시만
    ← 로컬 04_WorkLog 키워드 검색 결과 (관련 대화 발췌)
    ← USER_CONTEXT (사용자 프로필·도메인·역할)
    ← template_key + space_key
    → enriched_context (재구성된 배경·의도)
    → search_query (Perplexity 최적화 검색어)
    ↓
[Stage 1] Perplexity — 웹 검색  ← 웹 검색 ON 시만
    ← search_query
    → web_content, citations[]
    ↓
[Stage 2] Gemini — 문서 생성
    ← original_prompt + enriched_context + web_content + 첨부파일 + 템플릿
    → title + markdown_body (## 참고 출처 포함)
    ↓
[Stage 3] Confluence 업로드
```

---

## 수정 파일
- **`.scripts/doc_gen.py`** — 상수 추가, 신규 함수 2개, 기존 함수 수정
- **`.scripts/.env`** — `PERPLEXITY_API_KEY` 값 기입 + `CLAUDE_API_KEY` 추가
- **의존성 추가 없음** — Claude API는 `requests`로 직접 호출 (이미 사용 중), WorkLog는 로컬 파일 `os.walk`

---

## 구현 상세

### 1. `.env` 수정
```
PERPLEXITY_API_KEY=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
CLAUDE_API_KEY=<사용자 입력>
```

### 2. 상수 추가
```python
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')

USER_CONTEXT = """\
이름: 박성환 | 직책: PO/PM — 자율주행 데이터 어노테이션팀 (Team Data Quality Assurance)
회사: StradVision | 스페이스: TE(DQA), DIC, DPP
도메인: 자율주행 데이터 어노테이션, 데이터 품질 관리, Nova 플랫폼
역량: Python, 데이터 파이프라인, AI/ML 데이터 운영, 프로젝트 기획·관리
성향: ESTP, 자기완결적 본질주의자
"""
```

### 3. `search_worklog_context(prompt)` 신규 함수
- `04_WorkLog/` 폴더(스크립트 기준 `../04_WorkLog`) 내 `*_대화_학습_정리.md` 및 `*.md` 파일을 전수 탐색
- 프롬프트 단어들을 키워드로 삼아 파일 본문에서 hit count 계산 → 상위 3개 파일 선택
- 각 파일에서 최대 800자 발췌, 합산 2000자 이내로 반환
- 실패 시 빈 문자열 반환 (파이프라인 중단 없음)

```python
WORKLOG_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '04_WorkLog')
)

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
```

### 4. `enrich_with_claude(prompt, template_key, space_key)` 신규 함수
- Claude API (`claude-sonnet-4-6`)를 `requests`로 직접 호출
- 입력: raw_prompt + USER_CONTEXT + 로컬 WorkLog 검색 결과
- 출력: `(enriched_context: str, search_query: str)` — 구분자 `---QUERY---` 로 분리

```python
def enrich_with_claude(prompt: str, template_key: str, space_key: str) -> tuple[str, str]:
    """Claude API로 프롬프트 맥락 재구성 → (enriched_context, search_query)"""
    space_name = next((n for k, n in SPACES if k == space_key), space_key)

    # 로컬 WorkLog 검색
    worklog    = search_worklog_context(prompt)
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
        query    = prompt  # fallback

    return enriched, query
```

### 5. `call_perplexity()` — 파라미터만 변경
- 기존 `prompt: str` 유지, 호출 시 `search_query` 전달 (함수 내부 변경 없음)

### 6. `call_gemini()` 수정
- 파라미터 추가: `enriched_context: str | None = None`
- perplexity_context 주입 블록에 enriched_context도 포함:
```python
if perplexity_context or enriched_context:
    content, citations = perplexity_context or ("", [])
    ref_text = "\n".join(f"[{i+1}] {u}" for i, u in enumerate(citations))
    ctx_block = f"[재구성된 요청 맥락]\n{enriched_context}\n\n" if enriched_context else ""
    web_block = f"[웹 검색 결과]\n{content}\n\n[출처]\n{ref_text}\n" if content else ""
    parts.insert(0, types.Part(text=ctx_block + web_block))
```

### 7. `run()` 스레드 수정 (GUI)
```python
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
        ...
```

### 8. GUI 검증 추가 (on_generate)
```python
if web_search_var.get() and not CLAUDE_API_KEY:
    messagebox.showwarning("설정 필요", "CLAUDE_API_KEY를 .env에 설정하세요.")
    return
```

---

## 변경 범위 요약
| 항목 | 변경 내용 |
|------|----------|
| `.env` | `PERPLEXITY_API_KEY` 값 기입, `CLAUDE_API_KEY` 키 추가 |
| 상수 | `CLAUDE_API_KEY`, `USER_CONTEXT` 추가 |
| 신규 함수 | `search_worklog_context()`, `enrich_with_claude()` |
| `call_gemini()` | `enriched_context` 파라미터 추가 |
| `run()` | 3단계 상태 메시지, Claude/Perplexity 순차 호출 |
| `on_generate()` | `CLAUDE_API_KEY` 미설정 경고 추가 |

---

## Verification
1. `.env`에 `CLAUDE_API_KEY` 설정 후 GUI 실행
2. "웹 검색 사용" 체크 → 짧은 프롬프트 입력
3. 상태 메시지 순서 확인: `[1/3] 맥락 재구성 중 (Claude)...` → `[2/3] 웹 검색 중 (Perplexity)...` → `[3/3] 문서 생성 중 (Gemini)...`
4. 생성 문서에 재구성된 배경 맥락 반영 여부 + `## 참고 출처` 섹션 확인
5. 체크 해제 시 Gemini 단독 동작 확인
6. `CLAUDE_API_KEY` 미설정 + 체크 시 경고 팝업 확인
