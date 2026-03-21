#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PM Skill Launcher
사용법: python pm_skill.py
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stdin  = io.TextIOWrapper(sys.stdin.buffer,  encoding="utf-8", errors="replace")

# ── Claude 스킬 매칭용 내부 데이터 (터미널에 직접 노출 안 됨) ────────────────
SKILLS = {
    "create-prd":               {"call": "/pm-execution:create-prd",                       "desc": "PRD 문서 작성"},
    "user-stories":             {"call": "/pm-execution:user-stories",                     "desc": "유저 스토리 작성"},
    "job-stories":              {"call": "/pm-execution:job-stories",                      "desc": "Job Story 작성"},
    "wwas":                     {"call": "/pm-execution:wwas",                             "desc": "Why-What-Acceptance 백로그"},
    "sprint-plan":              {"call": "/pm-execution:sprint-plan",                      "desc": "스프린트 계획 수립"},
    "retro":                    {"call": "/pm-execution:retro",                            "desc": "스프린트 회고"},
    "release-notes":            {"call": "/pm-execution:release-notes",                    "desc": "릴리즈 노트 생성"},
    "summarize-meeting":        {"call": "/pm-execution:summarize-meeting",                "desc": "회의록 요약"},
    "pre-mortem":               {"call": "/pm-execution:pre-mortem",                       "desc": "출시 전 리스크 분석"},
    "brainstorm-okrs":          {"call": "/pm-execution:brainstorm-okrs",                  "desc": "OKR 브레인스토밍"},
    "test-scenarios":           {"call": "/pm-execution:test-scenarios",                   "desc": "테스트 시나리오 생성"},
    "outcome-roadmap":          {"call": "/pm-execution:outcome-roadmap",                  "desc": "Output → Outcome 로드맵 전환"},
    "dummy-dataset":            {"call": "/pm-execution:dummy-dataset",                    "desc": "더미 데이터셋 생성"},
    "stakeholder-map":          {"call": "/pm-execution:stakeholder-map",                  "desc": "이해관계자 맵핑"},
    "brainstorm-ideas":         {"call": "/pm-product-discovery:brainstorm-ideas-existing","desc": "아이디어 발산 (기존 제품)"},
    "identify-assumptions":     {"call": "/pm-product-discovery:identify-assumptions-existing", "desc": "리스크 가정 식별"},
    "prioritize-features":      {"call": "/pm-product-discovery:prioritize-features",      "desc": "피처 우선순위 결정"},
    "interview-script":         {"call": "/pm-product-discovery:interview-script",         "desc": "고객 인터뷰 스크립트"},
    "summarize-interview":      {"call": "/pm-product-discovery:summarize-interview",      "desc": "인터뷰 내용 구조화"},
    "opportunity-solution-tree":{"call": "/pm-product-discovery:opportunity-solution-tree","desc": "Opportunity Solution Tree"},
    "metrics-dashboard":        {"call": "/pm-product-discovery:metrics-dashboard",        "desc": "제품 메트릭 대시보드 설계"},
    "analyze-feature-requests": {"call": "/pm-product-discovery:analyze-feature-requests", "desc": "피처 요청 분석·우선순위"},
    "product-strategy":         {"call": "/pm-product-strategy:product-strategy",          "desc": "9섹션 전략 캔버스"},
    "product-vision":           {"call": "/pm-product-strategy:product-vision",            "desc": "제품 비전 수립"},
    "value-proposition":        {"call": "/pm-product-strategy:value-proposition",         "desc": "JTBD 기반 가치 제안"},
    "swot-analysis":            {"call": "/pm-product-strategy:swot-analysis",             "desc": "SWOT 분석"},
    "lean-canvas":              {"call": "/pm-product-strategy:lean-canvas",               "desc": "린 캔버스"},
    "business-model":           {"call": "/pm-product-strategy:business-model",            "desc": "비즈니스 모델 캔버스"},
    "pricing-strategy":         {"call": "/pm-product-strategy:pricing-strategy",          "desc": "가격 전략"},
    "competitor-analysis":      {"call": "/pm-market-research:competitor-analysis",        "desc": "경쟁사 분석"},
    "market-sizing":            {"call": "/pm-market-research:market-sizing",              "desc": "TAM/SAM/SOM 시장 규모"},
    "customer-journey-map":     {"call": "/pm-market-research:customer-journey-map",       "desc": "고객 여정 맵"},
    "user-personas":            {"call": "/pm-market-research:user-personas",              "desc": "유저 페르소나"},
    "sentiment-analysis":       {"call": "/pm-market-research:sentiment-analysis",         "desc": "피드백 감성 분석"},
    "ab-test-analysis":         {"call": "/pm-data-analytics:ab-test-analysis",            "desc": "A/B 테스트 결과 분석"},
    "cohort-analysis":          {"call": "/pm-data-analytics:cohort-analysis",             "desc": "코호트 분석"},
    "sql-queries":              {"call": "/pm-data-analytics:sql-queries",                 "desc": "자연어 → SQL 변환"},
    "gtm-strategy":             {"call": "/pm-go-to-market:gtm-strategy",                  "desc": "GTM 전략 전체 수립"},
    "beachhead-segment":        {"call": "/pm-go-to-market:beachhead-segment",             "desc": "첫 번째 타겟 세그먼트 선정"},
    "ideal-customer-profile":   {"call": "/pm-go-to-market:ideal-customer-profile",        "desc": "ICP 정의"},
    "growth-loops":             {"call": "/pm-go-to-market:growth-loops",                  "desc": "성장 루프 설계"},
    "competitive-battlecard":   {"call": "/pm-go-to-market:competitive-battlecard",        "desc": "경쟁사 배틀카드"},
    "north-star-metric":        {"call": "/pm-marketing-growth:north-star-metric",         "desc": "North Star 메트릭 정의"},
    "marketing-ideas":          {"call": "/pm-marketing-growth:marketing-ideas",           "desc": "마케팅 아이디어 발산"},
    "positioning-ideas":        {"call": "/pm-marketing-growth:positioning-ideas",         "desc": "포지셔닝 아이디어"},
    "grammar-check":            {"call": "/pm-toolkit:grammar-check",                      "desc": "문법·논리·흐름 교정"},
    "review-resume":            {"call": "/pm-toolkit:review-resume",                      "desc": "PM 이력서 리뷰"},
    "draft-nda":                {"call": "/pm-toolkit:draft-nda",                          "desc": "NDA 초안"},
    "privacy-policy":           {"call": "/pm-toolkit:privacy-policy",                     "desc": "개인정보처리방침 초안"},
}

# ── 터미널 표시용 카테고리 개요 ───────────────────────────────────────────────
CATEGORY_OVERVIEW = [
    ("📋 실행",       "PRD · 유저스토리 · 스프린트 · 회고 · 회의록 · OKR · 릴리즈노트"),
    ("🔍 제품 발견",  "아이디어 발산 · 가정 식별 · OST · 인터뷰 분석 · 피처 우선순위"),
    ("🎯 제품 전략",  "전략캔버스 · 가치제안 · 비전 · SWOT · 린캔버스 · 비즈모델"),
    ("📊 시장 조사",  "경쟁사 분석 · 시장규모(TAM/SAM) · 고객여정맵 · 페르소나"),
    ("📈 데이터 분석","A/B 테스트 · 코호트 분석 · SQL 생성"),
    ("🚀 GTM",        "GTM전략 · ICP · 배틀카드 · 성장루프 · 비치헤드 세그먼트"),
    ("📣 마케팅·성장","North Star 메트릭 · 포지셔닝 · 마케팅 아이디어"),
    ("🛠  툴킷",       "문법교정 · 이력서 리뷰 · NDA · 개인정보처리방침"),
]


def show_toolkit():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║              PM Skill Toolkit                    ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    for cat, keywords in CATEGORY_OVERVIEW:
        print(f"  {cat:<14}  {keywords}")
    print()
    print("──────────────────────────────────────────────────")
    print("  원하는 작업을 설명하면 최적 스킬을 찾아드립니다.")
    print("──────────────────────────────────────────────────")
    print()


def collect_input() -> dict:
    print("[1/3] 목적 — 이 작업으로 달성하려는 것은?")
    purpose = input("  > ").strip()
    print()
    print("[2/3] 컨텍스트 — 제품명 / 상황 / 타겟 유저 / 관련 정보")
    context = input("  > ").strip()
    print()
    print("[3/3] 원하는 산출물 형태 — 문서 / 표 / 요약 / 한국어 등")
    deliverable = input("  > ").strip()
    print()
    return {"purpose": purpose, "context": context, "deliverable": deliverable}


def output_request(data: dict):
    print("━" * 52)
    print("[PM_SKILL_REQUEST]")
    print(f"목적: {data['purpose']}")
    print(f"컨텍스트: {data['context']}")
    print(f"산출물: {data['deliverable']}")
    print("[/PM_SKILL_REQUEST]")
    print("━" * 52)
    print("Claude가 위 요청을 분석합니다...")
    print()


def main():
    show_toolkit()

    # CLI 인자가 있으면 non-interactive 모드 (Claude Code 환경용)
    if len(sys.argv) == 4:
        data = {
            "purpose":     sys.argv[1],
            "context":     sys.argv[2],
            "deliverable": sys.argv[3],
        }
    elif len(sys.argv) > 1:
        print("사용법: pm_skill.py [목적] [컨텍스트] [산출물]")
        sys.exit(1)
    else:
        data = collect_input()  # 터미널 직접 실행 시 기존 interactive 방식

    output_request(data)


if __name__ == "__main__":
    main()
