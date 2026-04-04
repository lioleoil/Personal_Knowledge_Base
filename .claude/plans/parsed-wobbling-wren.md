# Daily Scrap Agent — 구현 계획

## Context
news.hada.io(GeekNews)에서 매일 오전 9시에 AI/LLM·자율주행·개발·비즈니스 관련 뉴스 3개를 자동 수집·요약하여 `Daily_Scrap.md`에 날짜별로 정리하는 백그라운드 잡 에이전트를 구축한다.

---

## 생성할 파일

| 경로 | 설명 |
|------|------|
| `scripts/daily_scrap.py` | 스크래퍼·요약·저장 로직 전체 |
| `04_WorkLog/Daily_Scrap/Daily_Scrap.md` | 날짜별 뉴스 스크랩 결과 (자동 생성) |

수정할 파일: 없음 (AgentLog 등 기존 유틸 그대로 import)

---

## `scripts/daily_scrap.py` 설계

### 상수 및 토픽 키워드

```python
HADA_BASE = "https://news.hada.io"
MAX_PAGES = 5       # 최대 페이지 탐색 수 (~150개 후보)
TOP_N     = 3       # 선택할 기사 수
OUTPUT    = PROJECT_ROOT / "04_WorkLog/Daily_Scrap/Daily_Scrap.md"

TOPICS = {
    "AI/LLM":          ["ai", "llm", "gpt", "claude", "openai", "anthropic",
                        "gemini", "인공지능", "언어모델", "생성형", "머신러닝",
                        "딥러닝", "파인튜닝", "rag", "transformer"],
    "자율주행/로보틱스": ["자율주행", "autonomous", "robotics", "로봇", "lidar",
                        "waymo", "tesla autopilot", "드론", "perception"],
    "개발/오픈소스":    ["오픈소스", "open source", "github", "release", "framework",
                        "library", "sdk", "rust", "python", "typescript",
                        "linux", "kubernetes", "docker"],
    "비즈니스/스타트업":["스타트업", "startup", "투자", "funding", "series",
                        "ipo", "인수", "acquisition", "billion", "million",
                        "유니콘", "revenue"],
}
```

### 함수 흐름

```
main()
  ├── AgentLog 초기화
  ├── load_seen_urls()       → Daily_Scrap.md에서 기존 URL 추출 (중복 방지)
  ├── scrape_articles()      → /?page=1~5 순차 fetch, BeautifulSoup 파싱
  │     · 각 기사: {title, url, description}
  │     · 페이지 간 1초 딜레이
  ├── select_top_articles()  → 키워드 스코어링, 토픽 다양성 우선, 중복 제외
  ├── for each article:
  │     summarize_article()  → Claude API (claude-haiku-4-5) 3줄 한국어 요약
  │     format_entry()       → 마크다운 블록 생성
  └── append_to_scrap()      → Daily_Scrap.md 상단에 날짜 섹션 prepend
```

### 핵심 함수 명세

**`scrape_articles(max_pages) → list[dict]`**
- `requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})`
- BeautifulSoup html.parser로 파싱
- 기사 제목 `<a>` 태그 → title, href → `HADA_BASE + href`
- 설명 텍스트 → description
- 50개 이상 수집 시 조기 종료

**`classify_article(article) → (topic, score)`**
- `raw_text = (title + " " + description).lower()`
- 토픽별 키워드 카운트 합산 → 최고 점수 토픽 반환
- 점수 0이면 (None, 0) 반환

**`select_top_articles(articles, seen_urls) → list[(topic, article)]`**
- 스코어 정렬 후 토픽 다양성 우선 선택 (토픽당 1개 먼저)
- TOP_N 미달 시 동일 토픽 중복 허용으로 채움

**`summarize_article(article, topic) → str`**
```python
client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수
client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=300,
    messages=[{"role": "user", "content": prompt}]
)
```
- 프롬프트: 제목+설명 → 3줄 한국어 요약 ("- "로 시작)

**`append_to_scrap(date_str, entries)`**
- `OUTPUT.parent.mkdir(parents=True, exist_ok=True)`
- 기존 파일 읽기 → 날짜 헤더 없으면 상단에 prepend (최신 날짜가 파일 맨 위)
- 날짜 헤더 이미 존재하면 해당 섹션 뒤에 append (재실행 복구)

---

## `Daily_Scrap.md` 출력 형식

```markdown
# Daily Scrap — GeekNews 자동 수집
> 매일 09:00 자동 업데이트 | 출처: https://news.hada.io

---

## 2026-03-15

### [기사 제목](https://news.hada.io/topic?id=XXXXX)
**토픽:** AI/LLM | **출처:** example.com

- 요약 첫 번째 줄
- 요약 두 번째 줄
- 요약 세 번째 줄

---
```

---

## 스케줄링

### 1단계 — Claude Code CronCreate (즉시)
구현 완료 후 현재 세션에서 바로 등록:
```
CronCreate(
  cron="3 9 * * *",
  prompt="Run daily news scraper: Bash로 python C:/Users/psh93/OneDrive/Desktop/Claude/scripts/daily_scrap.py 실행. 완료 후 생성된 로그 경로 보고."
)
```

### 2단계 — Windows Task Scheduler (영구 등록)
Claude Code가 꺼져 있어도 동작하도록 1회 수동 실행:
```
schtasks /create /tn "Claude_DailyScrap" /tr "python C:\Users\psh93\OneDrive\Desktop\Claude\scripts\daily_scrap.py" /sc DAILY /st 09:03 /f
```
- `ANTHROPIC_API_KEY`는 시스템 환경변수에 등록 필요

---

## 의존성 설치

```bash
pip install requests beautifulsoup4 anthropic
```

- `anthropic`이 이미 설치되어 있을 수 있음: `python -c "import anthropic; print(anthropic.__version__)"` 확인

---

## 검증

1. **즉시 테스트**: `python scripts/daily_scrap.py` 직접 실행
2. **출력 확인**: `04_WorkLog/Daily_Scrap/Daily_Scrap.md` 생성 및 형식 검증
3. **로그 확인**: `04_WorkLog/Daily_Scrap/.agents/` 에 JSON 로그 생성 확인
4. **중복 방지 확인**: 동일 스크립트 재실행 시 동일 날짜 기사 재추가 안 됨 확인
5. **monitor.py 확인**: 실행 중 `python .status/monitor.py`로 진행 상태 모니터링 가능

---

## 참조 파일

- `scripts/agent_log.py` — AgentLog 클래스 (그대로 import)
- `04_WorkLog/Daily_Scrap/Daily_Scrap.md` — 출력 대상 (스크립트가 자동 생성)
