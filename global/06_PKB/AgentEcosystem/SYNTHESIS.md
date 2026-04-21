---
tags:
  - agent-ecosystem
  - orchestrator
  - multi-agent
  - claude-code
  - pkb
  - synthesis
aliases:
  - AgentEcosystem 합성
  - 에이전트 생태계
category: AgentEcosystem
source: "[[AgentEcosystem_대화_학습_정리]]"
updated: 2026-04-22
---

# AgentEcosystem 지식 합성

> 마지막 갱신: 2026-04-22 07:52 | 기반 항목 수: 20

---

# AgentEcosystem 위키 합성 문서

## 핵심 지식

1. **Multi-Agent 역할 분리 구조가 확립되어 있다**
   - `User Interface Agent` (사용자 대화 진입점), `Advisor Agent / PM` (계획·검토), `Execution Agent + Domain Agent` (실제 작업 수행) 3계층으로 분리 운영 중
   - 각 에이전트는 `role_rules__*.json` 파일로 역할 규칙을 명시적으로 주입받음
   - 경로: `C:/Users/psh93/OneDrive/Desktop/Workspace/global/04_AgentEcosystem/agents/`

2. **Orchestrator → Bus → Execution 파이프라인이 실제 운용 중이다**
   - Task는 `.agents/bus/{task_id}_report.json` 형식으로 결과를 저장
   - 실제 사례: task ID `9dea7c73`, "Waza 도입 및 활용 전략 리포트"가 full pipeline으로 완료됨 (2026-04-14 00:33)
   - 실행 스크립트: `python .scripts/orchestrator.py`

3. **Advisor Agent의 역할이 반응형→능동형으로 전환되는 설계 변경이 승인되었다 (v2.0)**
   - 기존: Advisor가 Validation 요청이 들어올 때만 반응
   - 변경: Advisor가 선제적으로 계획을 수립하고 Execution에 위임하는 PM 역할로 격상
   - 승인된 구현 계획 파일: `af4e849c-d889-4d9d-8aab-49f594cc90d9.jsonl`

4. **비용 최적화를 위한 Haiku 모델 분리 적용 전략이 수립되어 있다**
   - 적용 도메인: `daily_scrap`, `pkb_worklog` → `cost_optimized` 프리셋 자동 적용
   - 고비용 모델은 Advisor/설계 단계에만, 저비용 Haiku는 Execution 단계에 할당하는 구조
   - 토큰 비용 추적이 설계 요소로 포함되어 있음

5. **Daily Scrap 자동화 트리거가 설정 누락 이력이 있다**
   - 2026-04-08 기준, "매일 오전 9시 실행" 지시에도 불구하고 트리거가 미등록 상태였음
   - 마지막 실행: 2026-04-04 → 4일 공백 발생
   - 이후 트리거 설정이 완료되었으나, 설정 지속성 검증 필요

6. **Multi-Agent 설계 초기 플랜(v1.0)은 2026-04-11에 수립되었다**
   - PKB(Personal Knowledge Base)를 도메인별 프로젝트로 구분하고 에이전트를 도메인에 묶는 구조
   - 경로 기준: `nova_he*` 등 도메인 프로젝트가 기반
   - 설계 플랜 파일: `c5083451-dedf-4422-8aa1-06b40ba4ad88.jsonl`

---

## 반복 등장 패턴

- **User Interface Agent 세션이 압도적으로 많다 (20개 중 7개)**
  → 사용자 진입점이 가장 자주 초기화되며, 세션 단절이 잦음을 시사함. 상태 지속성 문제 가능성

- **`role_rules__*.json` 파일 경로를 매 세션마다 명시적으로 주입**
  → 에이전트가 스스로 역할을 기억하지 못하므로, 매 대화마다 시스템 프롬프트로 규칙 파일을 재로딩하는 구조

- **Execution Agent가 `pkb_worklog` 도메인과 함께 묶여 등장**
  → `pkb_worklog`가 Execution 작업의 주요 타겟 도메인임. 작업 로그 기록이 Execution Agent의 핵심 임무 중 하나

- **local command 실행 중 "DO NOT respond" caveat 패턴 반복 (로그 15, 17)**
  → 로컬 스크립트 실행 시 Claude가 불필요하게 응답하는 문제가 있어 caveat를 삽입하는 방어적 패턴 형성

- **계획 승인 후 구현 플랜을 대화 시작 시 주입하는 패턴**
  → `"Here is the approved implementation plan:"` 접두어로 시작하는 세션이 2회 등장. 승인된 플랜을 컨텍스트로 붙여넣는 표준 운용 방식으로 굳어짐

---

## 미해결 질문

- **Daily Scrap 트리거 설정의 지속성이 검증되었는가?**
  → 2026-04-08 이후 설정했다고 나오지만, 이후 정상 실행 여부가 로그에서 확인되지 않음

- **Execution Agent 세션이 종료된 후 결과가 Bus에 정상 기록되는지 감시하는 구조가 있는가?**
  → `bus/{task_id}_report.json`이 생성되는 것은 확인되었으나, 실패 케이스 처리(retry, alert) 로직이 로그에 명시되지 않음

- **v2.0 Advisor Agent(PM 역할)의 능동형 계획 수립이 실제로 구현·검증되었는가?**
  → 승인된 계획(2026-04-12)은 있으나, 실제 능동형 작동 사례가 이후 로그에서 확인되지 않음

- **User Interface Agent 세션이 자주 재시작되는 근본 원인은 무엇인가?**
  → 세션 단절인지, 의도적 분리인지, 아니면 컨텍스트 한계로 인한 재시작인지 불명확

- **Haiku 비용 최적화 프리셋이 실제 적용되어 비용 절감 효과가 측정되었는가?**
  → "예상 효과 보고서 Q1"(2026-04-12)이 존재하나, 실측 결과 데이터가 로그에 없음

---

## 관련 카테고리

- **`pkb_worklog`** — Execution Agent의 주요 작업 도메인, 작업 기록 저장소
- **`daily_scrap`** — 자동화 트리거 관리, 비용 최적화 적용 대상 도메인
- **`nova_he*` (PKB 도메인 프로젝트)** — Multi-Agent 설계의 기반이 되는 지식 도메인 구조
- **`cost_optimization / token_tracking`** — Haiku 분리 전략, 모델별 비용 추적 설계
- **`Claude Code 웹 예약 실행`** — 클라우드 기반 백그라운드 실행 기능, 로컬 트리거 대안으로 검토됨 (2026-04-11 스크랩)
- **`Orchestrator 스크립트 (.scripts/orchestrator.py)`** — 파이프라인 실행 진입점, 별도 관리 필요

---

## 연결 노드 (Obsidian Graph)

> PKB 내 직접 연결 문서

- 📄 소스: [[AgentEcosystem_대화_학습_정리|AgentEcosystem 대화 로그 (20건)]]
- 🔗 [[Nova/SYNTHESIS|Nova]] — nova_helper Slack 봇, orchestrator 파이프라인 연동
- 🔗 [[Python_Scripts/SYNTHESIS|Python_Scripts]] — orchestrator.py, 자동화 스크립트 패턴
- 🔗 [[Strategy_Business/SYNTHESIS|Strategy_Business]] — Multi-Agent 설계 → KPI/OKR 실행 연계
