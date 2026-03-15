"""
Daily Scrap Collector — news.hada.io(GeekNews) 기사 수집·선택
요약/파일 작성은 Claude Code Agent(CronCreate)가 담당.
실행 결과: 04_WorkLog/Daily_Scrap/.staging.json 생성
"""
import sys, re, time, json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from agent_log import AgentLog, PROJECT_ROOT

import requests
from bs4 import BeautifulSoup

# ── 상수 ──────────────────────────────────────────────────────────────────────
HADA_BASE = "https://news.hada.io"
MAX_PAGES  = 5
TOP_N      = 3
OUTPUT_MD  = Path(PROJECT_ROOT) / "04_WorkLog/Daily_Scrap/Daily_Scrap.md"
STAGING    = Path(PROJECT_ROOT) / "04_WorkLog/Daily_Scrap/.staging.json"

TOPICS = {
    "AI/LLM": [
        "ai", "llm", "gpt", "claude", "openai", "anthropic",
        "gemini", "인공지능", "언어모델", "생성형", "머신러닝",
        "딥러닝", "파인튜닝", "rag", "transformer",
    ],
    "자율주행/로보틱스": [
        "자율주행", "autonomous", "robotics", "로봇", "lidar",
        "waymo", "tesla autopilot", "드론", "perception",
    ],
    "개발/오픈소스": [
        "오픈소스", "open source", "github", "release", "framework",
        "library", "sdk", "rust", "python", "typescript",
        "linux", "kubernetes", "docker",
    ],
    "비즈니스/스타트업": [
        "스타트업", "startup", "투자", "funding", "series",
        "ipo", "인수", "acquisition", "billion", "million",
        "유니콘", "revenue",
    ],
}


# ── 중복 방지 ─────────────────────────────────────────────────────────────────
def load_seen_urls() -> set[str]:
    if not OUTPUT_MD.exists():
        return set()
    text = OUTPUT_MD.read_text(encoding="utf-8")
    return set(re.findall(r'\]\((https?://[^\)]+)\)', text))


# ── 스크래핑 ──────────────────────────────────────────────────────────────────
def scrape_articles(max_pages: int = MAX_PAGES) -> list[dict]:
    articles = []
    headers = {"User-Agent": "Mozilla/5.0"}

    for page in range(1, max_pages + 1):
        url = f"{HADA_BASE}/?page={page}"
        try:
            resp = requests.get(url, timeout=10, headers=headers)
            resp.raise_for_status()
        except Exception as e:
            print(f"[WARN] page {page} fetch error: {e}", flush=True)
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".topic_row")

        for item in items:
            title_tag = item.select_one(".topictitle a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)

            desc_tag = item.select_one(".topicdesc a")
            if not desc_tag:
                continue
            topic_href = desc_tag.get("href", "")
            if not topic_href.startswith("topic?id="):
                continue
            full_url = HADA_BASE + "/" + topic_href.split("&")[0]
            description = desc_tag.get_text(strip=True)

            articles.append({"title": title, "url": full_url, "description": description})

        if len(articles) >= 50:
            break
        time.sleep(1)

    return articles


# ── 분류·스코어링 ─────────────────────────────────────────────────────────────
def classify_article(article: dict) -> tuple[str | None, int]:
    raw = (article["title"] + " " + article["description"]).lower()
    best_topic, best_score = None, 0
    for topic, keywords in TOPICS.items():
        score = sum(1 for kw in keywords if kw in raw)
        if score > best_score:
            best_topic, best_score = topic, score
    return best_topic, best_score


def select_top_articles(articles: list[dict], seen_urls: set[str]) -> list[dict]:
    scored = []
    for a in articles:
        if a["url"] in seen_urls:
            continue
        topic, score = classify_article(a)
        if score > 0:
            scored.append((score, topic, a))

    scored.sort(key=lambda x: -x[0])

    selected: list[dict] = []
    used_topics: set[str] = set()

    for _, topic, a in scored:
        if topic not in used_topics:
            selected.append({**a, "topic": topic})
            used_topics.add(topic)
        if len(selected) >= TOP_N:
            break

    if len(selected) < TOP_N:
        for _, topic, a in scored:
            if any(a["url"] == s["url"] for s in selected):
                continue
            selected.append({**a, "topic": topic})
            if len(selected) >= TOP_N:
                break

    return selected[:TOP_N]


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    STAGING.parent.mkdir(parents=True, exist_ok=True)

    log = AgentLog(
        agent_id=f"DailyScrap_{date_str}",
        title="Daily Scrap — GeekNews 수집",
        agent_type="daily_scrap",
    )

    try:
        log.update(progress=5, message="기존 URL 로딩")
        seen_urls = load_seen_urls()
        log.add(f"기존 수집 URL: {len(seen_urls)}개")

        log.update(progress=20, message="GeekNews 스크래핑 중")
        articles = scrape_articles(MAX_PAGES)
        log.add(f"수집 기사: {len(articles)}개")

        if not articles:
            log.error("기사 수집 실패 — 페이지 구조 확인 필요")
            return

        log.update(progress=70, message="기사 선택 중")
        selected = select_top_articles(articles, seen_urls)
        log.add(f"선택 기사: {len(selected)}개")

        staging_data = {"date": date_str, "articles": selected}
        STAGING.write_text(json.dumps(staging_data, ensure_ascii=False, indent=2), encoding="utf-8")

        log.done(f"스테이징 저장 완료 → {STAGING}")
        print(f"[OK] staging: {STAGING}", flush=True)
        print(json.dumps(staging_data, ensure_ascii=False, indent=2), flush=True)

    except Exception as e:
        log.error(str(e))
        raise


if __name__ == "__main__":
    main()
