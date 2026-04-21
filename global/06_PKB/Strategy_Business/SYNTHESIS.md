---
tags:
  - strategy
  - business
  - okr
  - kpi
  - data-engineering
  - pkb
  - synthesis
aliases:
  - Strategy_Business 합성
  - 전략·비즈니스
category: Strategy_Business
source: "[[Strategy_Business_대화_학습_정리]]"
updated: 2026-04-22
---

# Strategy_Business 지식 합성

> 마지막 갱신: 2026-04-22 07:58 | 기반 항목 수: 30

---

# Strategy_Business 위키 합성 문서

## 핵심 지식

1. **KPI는 달성 여부를 판별할 수 있는 수치여야 한다** — "단순 수치화를 위한 숫자"가 아닌, Goal과 직접 연결되어 의미 있는 변화를 측정하는 지표로 설계해야 한다. (예: 데이터 업데이트 주기 D+1 → 실시간, MongoDB 정합성 95% → 99.9%)

2. **OKR Key Result는 KPI에서 역으로 도출한다** — 개발팀 KPI(인프라 개선·자동화)를 기반으로 Key Result를 구성할 때, KPI 수치가 명확할수록 Key Result의 측정 가능성이 높아진다. KPI → Key Result 방향의 전환 로직을 반드시 확인해야 한다.

3. **데이터 거버넌스는 기술이 아닌 의사결정 체계다** — 데이터의 정의·관리·통제·활용 기준을 결정하는 원칙·역할·프로세스·책임의 프레임이다. Nova Lakehouse의 ODD 데이터 규명·정의 작업은 "ODD 데이터 거버넌스"로 명명 가능하다.

4. **정책 문서의 구조적 자산 전환은 Git Markdown 기반으로 측정한다** — MVGen2 Annotation Policy의 Governance 전환률은 "전체 Policy 버전 중 Git Markdown 구조 전환 비율"로 수치화하며, Version & Traceability 확보가 핵심 기준이다.

5. **Nova의 전략적 전환 방향은 데이터 이동 → 의미(Meaning) 관리다** — AI가 파이프라인 생성을 자동화하는 환경에서, 데이터 엔지니어링의 핵심 가치는 단순 적재가 아니라 데이터의 의미·맥락·품질을 구조화하는 것으로 이동하고 있다.

6. **기술 용어의 정확한 영어 표현은 문서·로드맵 맥락에 따라 결정된다** — 예: 쿼리 엔진 전환 → "Databricks Query Engine Migration" (문서·로드맵 표준), workload 대체 → 측정 중심이면 "throughput / task volume", 성과 중심이면 "output / delivery capacity"

---

## 반복 등장 패턴

- **KPI/OKR 설계 반복 요청**: 2026-01-12, 2026-02-20, 2026-02-25 세 차례에 걸쳐 KPI 구체성 검토, Key Result 도출, KPI 항목 완성 요청이 반복됨 → KPI 설계 기준 자체를 문서화할 필요가 있음
- **Nova Lakehouse 관련 개념 정리**: ODD 데이터 거버넌스(01-26), 데이터 레이크하우스 정의(01-29), Ingestion 정의(02-13), Nova 전략 전환(02-25) 등 Nova 플랫폼 관련 개념이 지속적으로 등장
- **업무 영어 표현 요청**: 프로젝트 투입(02-06), 쿼리 엔진 전환(01-06), workload 대체(01-06), 추이/투입 현황(02-25) 등 실무 커뮤니케이션용 영어 표현 요청이 반복됨
- **정책·구조 문서화 작업**: KPI 문서 완성, Annotation Policy Git 전환, 피어 평가 작성 등 기존 내용을 구조화된 문서로 전환하는 요청이 다수

---

## 미해결 질문

- **KPI Goal의 "의미 있는 수치" 판별 기준이 명확하지 않음** — 어떤 수치가 진짜 비즈니스 임팩트를 반영하는지, 단순 운영 지표와 전략 지표를 구분하는 기준이 아직 체계화되지 않음
- **Nova 전략 전환의 실행 로드맵이 미완성** — 전략 방향(의미 관리 중심)은 도출됐으나, 이를 구체적 에픽·스프린트 단위로 분해한 실행 계획이 대화 로그 내에 없음
- **OKR과 KPI의 조직 내 연결 구조** — 개발팀 KPI가 Nova 전체 OKR과 어떻게 계층적으로 연결되는지 명시적 정의가 없음

---

## 관련 카테고리

- **Data_Engineering** — Nova Lakehouse, Ingestion, Databricks, CDC 파이프라인, 데이터 거버넌스
- **Tech_Vocabulary** — 실무 영어 표현, 기술 용어 정의 (Ingestion, ODD, ASPICE 등)
- **Automotive_AD** — IMU, MCIP/MTBF, NCAP, ASPICE Pre-Assessment, ODD
- **Personal_Productivity** — 피어 평가 작성, Git 세팅, 로컬 환경 관리

---

## 연결 노드 (Obsidian Graph)

> PKB 내 직접 연결 문서

- 📄 소스: [[Strategy_Business_대화_학습_정리|Strategy_Business 대화 로그 (30건)]]
- 🔗 [[Nova/SYNTHESIS|Nova]] — Nova 서비스 전략, Databricks 플랫폼 전환 맥락
- 🔗 [[Career/SYNTHESIS|Career]] — 커리어 포지셔닝과 비즈니스 전략 연계
- 🔗 [[AgentEcosystem/SYNTHESIS|AgentEcosystem]] — Multi-Agent 설계 → KPI/OKR 실행 연계
