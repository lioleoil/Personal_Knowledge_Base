---
description: PM Skill Toolkit — 목적을 입력하면 최적 스킬을 찾아줍니다
---

아래 PM Skill Toolkit을 보여주고, 사용자에게 어떤 작업을 원하는지 한 가지 질문만 해줘.

## 노출할 스킬 목록

설치된 스킬 카테고리와 스킬 목록을 다음 형식으로 출력해:

```
╔══════════════════════════════════════════════════╗
║              PM Skill Toolkit                    ║
╚══════════════════════════════════════════════════╝

  📋 실행          PRD · 유저스토리 · 스프린트 · 회고 · 회의록 · OKR · 릴리즈노트
  🔍 제품 발견     아이디어 발산 · 가정 식별 · OST · 인터뷰 분석 · 피처 우선순위
  🎯 제품 전략     전략캔버스 · 가치제안 · 비전 · SWOT · 린캔버스 · 비즈모델
  📊 시장 조사     경쟁사 분석 · 시장규모(TAM/SAM) · 고객여정맵 · 페르소나
  📈 데이터 분석   A/B 테스트 · 코호트 분석 · SQL 생성
  🚀 GTM           GTM전략 · ICP · 배틀카드 · 성장루프 · 비치헤드 세그먼트
  📣 마케팅·성장   North Star 메트릭 · 포지셔닝 · 마케팅 아이디어
  🛠  툴킷          문법교정 · 이력서 리뷰 · NDA · 개인정보처리방침

──────────────────────────────────────────────────
```

그 다음 딱 한 가지만 물어봐:

> **어떤 작업을 도와드릴까요?** (예: "Q2 OKR 만들고 싶어", "경쟁사 분석 필요해", "스프린트 계획 짜야 해")

사용자가 답하면, 아래 기준으로 **가장 적합한 스킬 1~3개**를 추천해줘:

- 스킬명 (슬래시 커맨드 형식)
- 한 줄 설명
- 추천 이유

추천 후 "실행할 스킬을 선택하면 바로 시작합니다." 라고 안내해줘.

## 전체 스킬 참조 목록 (매칭용)

| 스킬 | 슬래시 커맨드 |
|------|--------------|
| PRD 작성 | /pm-execution:create-prd |
| 유저 스토리 | /pm-execution:user-stories |
| Job Story | /pm-execution:job-stories |
| WWA 백로그 | /pm-execution:wwas |
| 스프린트 계획 | /pm-execution:sprint-plan |
| 스프린트 회고 | /pm-execution:retro |
| 릴리즈 노트 | /pm-execution:release-notes |
| 회의록 요약 | /pm-execution:summarize-meeting |
| 출시 전 리스크 | /pm-execution:pre-mortem |
| OKR 브레인스토밍 | /pm-execution:brainstorm-okrs |
| 테스트 시나리오 | /pm-execution:test-scenarios |
| Outcome 로드맵 | /pm-execution:outcome-roadmap |
| 더미 데이터셋 | /pm-execution:dummy-dataset |
| 이해관계자 맵 | /pm-execution:stakeholder-map |
| 아이디어 발산 | /pm-product-discovery:brainstorm-ideas-existing |
| 리스크 가정 식별 | /pm-product-discovery:identify-assumptions-existing |
| 피처 우선순위 | /pm-product-discovery:prioritize-features |
| 인터뷰 스크립트 | /pm-product-discovery:interview-script |
| 인터뷰 요약 | /pm-product-discovery:summarize-interview |
| OST | /pm-product-discovery:opportunity-solution-tree |
| 메트릭 대시보드 | /pm-product-discovery:metrics-dashboard |
| 피처 요청 분석 | /pm-product-discovery:analyze-feature-requests |
| 제품 전략 캔버스 | /pm-product-strategy:product-strategy |
| 제품 비전 | /pm-product-strategy:product-vision |
| 가치 제안 | /pm-product-strategy:value-proposition |
| SWOT 분석 | /pm-product-strategy:swot-analysis |
| 린 캔버스 | /pm-product-strategy:lean-canvas |
| 비즈니스 모델 | /pm-product-strategy:business-model |
| 가격 전략 | /pm-product-strategy:pricing-strategy |
| 경쟁사 분석 | /pm-market-research:competitor-analysis |
| 시장 규모 | /pm-market-research:market-sizing |
| 고객 여정 맵 | /pm-market-research:customer-journey-map |
| 유저 페르소나 | /pm-market-research:user-personas |
| 감성 분석 | /pm-market-research:sentiment-analysis |
| A/B 테스트 분석 | /pm-data-analytics:ab-test-analysis |
| 코호트 분석 | /pm-data-analytics:cohort-analysis |
| SQL 생성 | /pm-data-analytics:sql-queries |
| GTM 전략 | /pm-go-to-market:gtm-strategy |
| 비치헤드 세그먼트 | /pm-go-to-market:beachhead-segment |
| ICP 정의 | /pm-go-to-market:ideal-customer-profile |
| 성장 루프 | /pm-go-to-market:growth-loops |
| 경쟁 배틀카드 | /pm-go-to-market:competitive-battlecard |
| North Star 메트릭 | /pm-marketing-growth:north-star-metric |
| 마케팅 아이디어 | /pm-marketing-growth:marketing-ideas |
| 포지셔닝 아이디어 | /pm-marketing-growth:positioning-ideas |
| 문법 교정 | /pm-toolkit:grammar-check |
| 이력서 리뷰 | /pm-toolkit:review-resume |
| NDA 초안 | /pm-toolkit:draft-nda |
| 개인정보처리방침 | /pm-toolkit:privacy-policy |
