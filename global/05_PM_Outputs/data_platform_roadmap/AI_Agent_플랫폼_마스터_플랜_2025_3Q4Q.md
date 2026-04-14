# AI Agent 기반 데이터 플랫폼 마스터 플랜 (2025 3Q–4Q)

**문서 버전**: v2.0
**작성일**: 2026-04-09
**팀 구성**: Data Platform Engineer / AI DataOps Engineer / PM Lead & Analyst
**기간**: 2025년 7월 — 12월 (6개월)

---

## 1. 전략 배경

### 1-1. 파편화된 데이터 스택의 한계

기존 데이터 조직이 직면한 구조적 문제:

- **파이프라인**은 복잡성과 파편화로 인해 장애 감지와 대응이 느리다
- **데이터 거버넌스**는 암묵적 규칙에 의존하여 스키마 변경·접근 제어가 일관되지 않는다
- **분석가**는 반복적인 추출 요청에 매몰되어 도메인 지식 기반의 실질적 인사이트 생산에 집중하지 못한다
- **비즈니스 사용자**는 데이터 접근 허들이 높아 의사결정이 지연된다

이 분절은 단순한 비효율이 아니라, **데이터 자산이 비즈니스 가치로 이어지는 E2E 생명주기를 단절**시키는 근본적 문제다.

### 1-2. Databricks AI Day Seoul이 제시한 방향

*참고: "데이터 플랫폼의 미래: 4가지 혁신 코드" (수진, 주미, 성환)*

| 혁신 코드 | 핵심 메시지 | 우리의 결정 |
|----------|-----------|-----------|
| **코드 1** 운영 패러다임 전환 | dbt + 파편화 스케줄러 → Databricks Workflows + DLT | dbt 제거, DLT + Workflows 완전 전환 |
| **코드 2** 대화형 지능 | 거버넌스 정교화가 선행되어야 AI 정확도가 올라간다 (Genie 45%→95%) | **3Q에 AI-Readable 환경 완비** |
| **코드 3** 에이전틱 AI | 역할을 가진 Agent들이 반복 분석 업무를 구조적으로 대신한다 | **4Q에 Agent 기반 분석 자동화** |
| **코드 4** AI-Readable 거버넌스 | AI 성능의 임계점은 모델이 아니라 데이터 구조와 컨텍스트 품질 | Unity Catalog + OBT 설계를 핵심 투자 |

---

## 2. 팀 구조 및 R&R 재정립

### 2-1. 역할 재정립 배경

개인 면담 결과를 반영하여 각 담당자의 역할을 실제 역량과 희망 방향에 맞게 재조정한다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  기존                          →  변경 후                               │
│                                                                         │
│  Data Platform Engineer           Data Platform Engineer                │
│  (인프라 전반)                    (파이프라인 · 운영 · Observability     │
│                                    · MLOps 연결)                        │
│                                                                         │
│  AI DataOps Engineer    →    AI DataOps Engineer              │
│  (Agent 개발)                     (DataOps: 거버넌스 · Contract ·       │
│                                    CI/CD · AI-Readable + Agent 생태계)  │
│                                                                         │
│  PM Lead                     →    PM Lead & Analyst                    │
│                                    (도메인 지식 → Agent 구현,            │
│                                    사용자 주도 분석 환경, 자동화 워크플로우)│
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 2-2. Data Platform Engineer

**핵심 정체성**: 데이터가 안정적으로 흐르고 신뢰할 수 있는 플랫폼 인프라를 책임진다

#### 현재 책임 영역

| 영역 | 구체적 업무 |
|------|-----------|
| **데이터 파이프라인** | DLT 파이프라인 설계·구축·운영 (Raw → Staging → Mart) |
| **DB 통합** | 소스 시스템 연결, 증분 적재(CDC), 스키마 진화 대응 |
| **Data Observability** | 5축 모니터링 (Freshness · Volume · Schema · Distribution · Pipeline), 헬스 대시보드 |
| **Data Lineage** | Column-level Lineage 수집·유지, 상·하류 영향 분석 |
| **Data Freshness** | SLA 기준 적시성 보장, 지연 감지 및 알람 |
| **Data Quality** | DLT Expectations 레이어별 표준화, 품질 검증 자동화 |
| **시스템 장애 대응** | 파이프라인 장애 감지·원인 분석·복구, 런북 운영 |
| **비용 관리** | DBU 비용 추적, 클러스터 최적화, 쿼리 효율화 |

#### 미래 확장 영역 (4Q 이후)

| 영역 | 방향 |
|------|------|
| **MLOps 파이프라인 연결** | Feature Store 구축, 모델 학습 파이프라인 연동, 모델 성능 모니터링 |

> **한 줄 정의**: "데이터가 제때, 정확하게, 안정적으로 흐르는 환경을 만들고 유지한다.
> 추후 ML 모델이 이 파이프라인 위에서 동작할 수 있도록 확장한다."

---

### 2-3. AI DataOps Engineer

**핵심 정체성**: 데이터 자산이 신뢰받고 올바르게 쓰일 수 있도록 거버넌스와 구조를 책임지며, Agent 생태계의 기반을 운영한다

> 역할 범위가 기존 Agent 개발 중심에서 **DataOps 전반으로 확장**됨.
> 데이터 거버넌스·컨트랙트·CI/CD·AI-Readable 구조가 핵심 책임이 되며,
> Agent 생태계 구축은 Data Platform Engineer와 함께 공동으로 유지한다.

#### DataOps 책임 영역 (신규 핵심)

| 영역 | 구체적 업무 |
|------|-----------|
| **데이터 거버넌스** | Unity Catalog 접근 제어 정책, 역할별 권한 매트릭스, PII 마스킹 자동화 |
| **Data Contract** | 스키마·SLA·품질 기준 정의, Contract YAML 작성·버전 관리, 변경 정책 운영 |
| **CI/CD** | 파이프라인·Agent 코드 배포 자동화, 브랜치 전략, 환경 격리 (dev/prod) |
| **AI-Readable 구조** | 메타데이터 완성도 관리, OBT 설계, 비즈니스 용어 사전, Databricks 네이티브 Comment 적용 |
| **태그·분류 체계** | domain · owner · data_class · sla_tier 태그 표준화 및 관리 |

#### Agent 생태계 책임 영역 (기존 유지)

| 영역 | 구체적 업무 |
|------|-----------|
| **Agent Registry** | Agent 등록·버전 관리·접근 권한 체계 |
| **AI Gateway** | 모델 라우팅, 가드레일 통합, 벤더 Lock-in 방지 |
| **Agent CI/CD** | Agent 코드 PR → 자동 테스트 → 배포 파이프라인 |
| **Agent Observability** | 응답 품질 스코어 추적, 사용 로그 수집·분석, 이상 알람 |
| **Shared Tool Library** | Data Platform Engineer와 협업하여 Agent 공통 도구 설계·검증 |

> **한 줄 정의**: "데이터 자산이 올바르게 정의되고, 안전하게 접근되며, Agent가 신뢰하는 구조 위에서 동작하도록 한다."

---

### 2-4. PM Lead & Analyst

**핵심 정체성**: 도메인 지식을 데이터와 연결하여 사용자가 AI Agent를 통해 스스로 분석할 수 있는 환경을 구축한다

> 기존 PM Lead의 전략·조율 역할에 더해,
> **도메인 전문 분석가로서 AI Agent에 지식을 학습시키고**
> **사용자 주도 분석 환경과 자동화 워크플로우를 직접 설계·운영**하는 역할을 맡는다.

#### 도메인 지식 → Agent 구현

| 영역 | 구체적 업무 |
|------|-----------|
| **도메인 지식 학습** | 앱 로그 기반 사용자 행동 패턴 분석, 비즈니스 규칙 추출 |
| **LLM 도메인 튜닝** | instruction.md 작성 (분석 규칙·비즈니스 용어·인과관계 정의), 프롬프트 최적화 |
| **분석 템플릿 설계** | 균일한 품질의 결과 보고서 템플릿 개발, 출력 형식 표준화 |
| **Agent 구현** | 도메인 특화 Agent 설계·테스트, 사용자 검수 조율 |

#### 사용자 주도 분석 환경 구축

| 영역 | 구체적 업무 |
|------|-----------|
| **분석 워크플로우** | AI Agent 기반 자동화 분석 파이프라인 설계·운영 |
| **사용자 환경** | 사용자가 LLM 기반 분석을 직접 수행할 수 있는 인터페이스 구성 |
| **온보딩** | 사용자 팀 교육, Agent 활용 가이드, 피드백 수집 |
| **보고서 자동화** | 정기 리포트 자동 생성 파이프라인, 보고서 품질 일관성 유지 |

#### 전략·조율 (기존 PM 역할 유지)

| 영역 | 구체적 업무 |
|------|-----------|
| **로드맵** | 분기별 플랫폼 생태계 전략 수립 및 우선순위 결정 |
| **조율** | Data Platform Engineer ↔ AI DataOps Engineer 협업 경계 관리 |
| **KPI** | 플랫폼 성숙도 측정, 분기별 리뷰 |
| **확장 전략** | 신규 도메인·사용자 팀 온보딩 계획 |

> **한 줄 정의**: "도메인 지식을 Agent에 녹여내고, 사용자가 스스로 분석하는 환경을 만든다."

---

### 2-5. 역할 분담 요약

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Data Platform Engineer                                                  │
│                                                                          │
│  "데이터가 제때, 정확하게, 안정적으로 흐른다"                             │
│                                                                          │
│  파이프라인 · DB 통합 · Observability · Lineage                          │
│  Freshness · Quality · 장애 대응 · [미래] MLOps                          │
├──────────────────────────────────────────────────────────────────────────┤
│  AI DataOps Engineer                                                │
│                                                                          │
│  "데이터 자산이 올바르게 정의되고, 안전하게 쓰이며, Agent가 신뢰한다"    │
│                                                                          │
│  [DataOps] 거버넌스 · Data Contract · CI/CD · AI-Readable 구조          │
│  [Agent]   Registry · AI Gateway · Observability · Tool Library         │
├──────────────────────────────────────────────────────────────────────────┤
│  PM Lead & Analyst                                                       │
│                                                                          │
│  "도메인 지식을 Agent에 담아 사용자가 스스로 분석하게 한다"              │
│                                                                          │
│  [도메인] 로그 분석 · instruction.md · LLM 튜닝 · Agent 구현            │
│  [환경]   분석 워크플로우 · 보고서 자동화 · 사용자 온보딩                │
│  [전략]   로드맵 · 우선순위 · KPI · 팀 조율                             │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 2-6. 협업 경계 (RACI)

#### DataOps / 인프라 영역

| 활동 | PM Lead & Analyst | Data Platform Engineer | AI DataOps Engineer |
|------|:---:|:---:|:---:|
| 파이프라인 설계·운영 | I | **R/A** | C |
| DB 통합·소스 연결 | I | **R/A** | I |
| Observability 구축 | I | **R/A** | C |
| Lineage 수집 | I | **R/A** | C |
| 거버넌스·접근 제어 | I | C | **R/A** |
| Data Contract 관리 | C | I | **R/A** |
| CI/CD 파이프라인 | I | C | **R/A** |
| AI-Readable 구조 | C | C | **R/A** |
| 비즈니스 용어 사전 | **R** | I | A |

#### Agent 생태계 영역

| 활동 | PM Lead & Analyst | Data Platform Engineer | AI DataOps Engineer |
|------|:---:|:---:|:---:|
| Shared Tool Library | I | **R** | A |
| Agent Registry | I | C | **R/A** |
| AI Gateway | I | C | **R/A** |
| Agent CI/CD | I | C | **R/A** |
| Agent Observability | C | C | **R/A** |
| instruction.md 작성 | **R/A** | I | C |
| Agent 개발·테스트 | **R/A** | I | C |
| 사용자 온보딩 | **R/A** | I | I |
| 분석 워크플로우 | **R/A** | I | C |

*R=Responsible, A=Accountable, C=Consulted, I=Informed*

---

## 3. 전체 아키텍처

```
┌──────────────────────────────────────────────────────────────────────────┐
│  LAYER 4: 사용자 (비즈니스 팀)                                            │
│  자연어 질문 → Agent 응답 → 인사이트 도출                                  │
│  정기 리포트 자동 수신                                                     │
└──────────┬───────────────┬───────────────────┬───────────────────────────┘
           │               │                   │
┌──────────▼───────────────▼───────────────────▼───────────────────────────┐
│  LAYER 3: 도메인 AI Agent  ← PM Lead & Analyst가 설계·구현                │
│                                                                           │
│  Performance Agent    Anomaly Agent    Report Agent    ...               │
│  (instruction.md)     (instruction.md) (보고서 템플릿)                   │
│  앱 로그 기반 도메인 지식 탑재, 분석 워크플로우 자동화                    │
│                                                                           │
│  ← 4Q에 구현                                                              │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │  Shared Tool Library
┌──────────────────────────▼───────────────────────────────────────────────┐
│  LAYER 2: AI Agent 플랫폼  ← AI DataOps Engineer 운영               │
│                                                                           │
│  Shared Tool Library   Agent Registry   Agent Observability              │
│  AI Gateway            Agent CI/CD      접근 제어 정책                   │
│                                                                           │
│  ← 4Q에 구축                                                              │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────────────┐
│  LAYER 1: 데이터 플랫폼 (Databricks)                                      │
│                                                                           │
│  ★ AI-Readable Unity Catalog  ← AI DataOps Engineer 책임            │
│    · 메타데이터 완성도 100%  · OBT 설계  · Data Contract                 │
│    · 비즈니스 용어 사전      · 태그 체계  · 접근 제어                     │
│                                                                           │
│  ★ 데이터 파이프라인  ← Data Platform Engineer 책임                       │
│    · DLT 파이프라인 (Raw→Staging→Mart)                                    │
│    · DLT Expectations (품질 보증)                                         │
│    · Observability (5축 모니터링)                                         │
│    · Lineage · Freshness · 장애 대응                                      │
│    · [미래] MLOps 파이프라인 연결                                         │
│                                                                           │
│  ← 3Q에 완비  (4Q Agent 성능의 기반)                                      │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────────────┐
│  LAYER 0: 데이터 소스  (Databricks 이관 완료)                              │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 분기별 로드맵

### 전체 일정

```
       7월                 8월                 9월
──────────────────────────────────────────────────────▶ 3Q
  [3Q-M1]               [3Q-M2]              [3Q-M3]
  현황 진단              메타데이터 완성       품질 체계 완성
  기반 설계              OBT 설계             AI-Readiness 검증
  거버넌스 설계           Contract 전면 적용   LLM 튜닝 시작
  앱 로그 분석 시작       instruction.md 초안  4Q 준비

       10월                11월                12월
──────────────────────────────────────────────────────▶ 4Q
  [4Q-M1]               [4Q-M2]              [4Q-M3]
  Agent 플랫폼 인프라     첫 번째 Agent 개발   Agent 확장
  Shared Tool Library    파일럿 운영           보고서 자동화
  AI Gateway             분석 워크플로우 v1    안정화·운영 체계
```

---

## 5. 3Q 상세 계획 — AI-Readable 환경 전환 / LLM 튜닝

> **목표**: Databricks에 구축된 카탈로그·스키마를 AI가 정확하게 이해하고 활용할 수 있는 상태로 완비한다.
> LLM이 올바른 테이블을 찾고, 정확한 SQL을 생성하며, 신뢰할 수 있는 답을 내기 위한 전제 조건을 완성한다.

---

### 3Q-M1 (7월): 현황 진단 & 기반 설계

#### Data Platform Engineer
- [ ] **현황 감사**: 파이프라인 목록·실행 주기·장애 이력·MTTD/MTTR 기준선 측정
- [ ] **Observability 설계**: 5축 모니터링 기준 정의 (Freshness · Volume · Schema · Distribution · Pipeline)
- [ ] **Lineage 활성화 준비**: Unity Catalog 내장 Lineage 설정 검토
- [ ] **DLT Expectations 기준 초안**: 레이어별 품질 규칙 정의 (Raw · Staging · Mart)
- [ ] **장애 대응 프로세스 초안**: 알람 → 원인 분석 → 복구 → 재발 방지 절차

#### AI DataOps Engineer
- [ ] **AI-Readiness 현황 감사**
  ```sql
  -- 메타데이터 누락 테이블 파악
  SELECT table_schema, table_name, comment
  FROM system.information_schema.tables
  WHERE table_catalog = '{catalog}'
    AND comment IS NULL
  ORDER BY table_schema, table_name;
  ```
- [ ] **AI-Readiness 점수 기준 정의**
  ```
  테이블당 100점 만점
  · description 작성     20점
  · grain 정의           20점
  · 핵심 컬럼 description 20점
  · business_term 연결   20점
  · Data Contract 적용   20점
  ```
- [ ] **거버넌스 계층 설계**
  ```
  platform_admin           → 전체 권한
  data_platform_engineer   → Raw~Mart 읽기·쓰기
  agent_service_{name}     → Mart 읽기 전용 (Agent별 Service Principal)
  business_user_{team}     → Mart 지정 테이블 읽기
  ```
- [ ] **Data Contract 템플릿 확정**
  ```yaml
  dataset:
    description: "이 테이블이 무엇을 나타내는지 한 문장"   # LLM 필수
    grain: "레코드 1개의 의미"                             # LLM 필수
    update_frequency: hourly
    sla:
      freshness_minutes: 30
  schema:
    - name: field_name
      description: "비즈니스 의미"                         # LLM 필수
      business_term: "공식 비즈니스 용어"                  # LLM 필수
      pii: false
  ```
- [ ] **OBT 전환 후보 테이블 식별** (3-way 이상 조인 필요 테이블 목록화)
- [ ] **CI/CD 브랜치 전략 및 환경 분리 설계** (dev / prod)
- [ ] **태그 체계 표준화**: domain · owner · data_class · sla_tier

#### PM Lead & Analyst
- [ ] **앱 로그 분석 시작**: 사용자 행동 패턴 파악, 자주 요청되는 분석 유형 분류
- [ ] **도메인 지식 추출**: 현재 수동으로 수행 중인 분석 업무 목록화
- [ ] **사용자 팀 인터뷰**: "어떤 질문에 답이 필요한가?" 3~5회 인터뷰
- [ ] **분석 템플릿 초안**: 보고서 출력 형식·구조 설계 시작

#### 3Q-M1 완료 기준
- [ ] AI-Readiness 현황 점수 측정 완료 (기준선 확보)
- [ ] 전체 테이블 메타데이터 누락 현황 목록화
- [ ] 거버넌스 계층 설계 확정
- [ ] Data Contract 템플릿 확정
- [ ] OBT 전환 후보 목록 확정
- [ ] 앱 로그 기반 분석 니즈 목록 초안 완성

---

### 3Q-M2 (8월): 메타데이터 완성 & OBT 설계 & Contract 전면 적용

#### Data Platform Engineer
- [ ] **Observability 구축**
  | 축 | 구현 방법 |
  |----|---------|
  | Freshness | 마지막 업데이트 시각 vs SLA 기준 자동 비교 |
  | Volume | ±3σ 이상 변동 시 자동 알람 |
  | Schema | 컬럼 추가·삭제·타입 변경 감지 → Contract 담당자(AI DataOps Engineer) 알람 |
  | Distribution | NULL 비율·핵심 컬럼 분포 변화 |
  | Pipeline | Workflows Job 성공률·소요 시간 추이 |
- [ ] **Lineage 수집 활성화**: Unity Catalog Column-level Lineage 핵심 마트 테이블 100%
- [ ] **DLT Expectations 1차 적용**: Raw · Staging 레이어부터 적용 시작
- [ ] **장애 대응 런북 v1**: 알람 → 원인 분석 → 복구 절차 문서화

#### AI DataOps Engineer
- [ ] **Unity Catalog 메타데이터 전면 완성**
  ```sql
  -- 직접 적용 (dbt 없이 Databricks 네이티브)
  COMMENT ON TABLE {catalog}.mart.orders IS
    '결제 완료된 주문 데이터.
     grain: 1 row = 1 주문 건.
     갱신 주기: 매시 30분 이내.
     upstream: staging.stg_orders.
     owner: data-platform-team.';

  ALTER TABLE {catalog}.mart.orders
    ALTER COLUMN customer_id
    COMMENT '주문한 고객 ID. business_term: 고객. PII: SHA-256 해시.';
  ```
- [ ] **전체 마트 테이블 Data Contract 적용 완료**
- [ ] **OBT 재설계 및 적용**
  ```
  Before: LLM이 orders + customers + products 3-way 조인 필요
  After:  mart.orders_enriched (사전 조인, LLM이 단순 SELECT로 완결)
  ```
- [ ] **비즈니스 용어 사전 완성**: 도메인별 공식 용어 → Unity Catalog 컬럼 연결
- [ ] **CI/CD 파이프라인 구성**: Git 브랜치 → 자동 테스트 → dev 배포

#### PM Lead & Analyst
- [ ] **instruction.md 초안 완성** (우선 도메인 1~2개)
  ```markdown
  # {도메인명} 분석 가이드

  ## 비즈니스 용어 정의
  - 실제 작업량: is_reverted = false인 effective_changes만 집계
  - 생산성 지표: objects_per_hour = 총 객체 수 / 순수 작업 시간

  ## 분석 규칙
  - 항상 feature_gen 기준으로 분리 집계
  - 기간 비교는 동일 요일 기준 전주 대비
  - 이상값: 전주 대비 ±20% 이상 변동 시 플래그

  ## 인과관계(Why) 분석 기준
  - 이상값 발생 시 → 1) 데이터 수집 오류 확인 → 2) 비즈니스 이벤트 확인

  ## 참조 금지 테이블
  - raw_*, stg_*: Agent 직접 참조 금지
  ```
- [ ] **사용자 팀과 instruction.md 검수 세션**
- [ ] **LLM 튜닝 1차**: 도메인 용어·규칙 기반 프롬프트 최적화 테스트

#### 3Q-M2 완료 기준
- [ ] 전체 마트 테이블 description + grain + business_term **100%**
- [ ] Data Contract 전체 마트 테이블 적용 완료
- [ ] OBT 재설계 적용 완료
- [ ] Observability 5축 모니터링 가동
- [ ] CI/CD dev 환경 자동 배포 성공
- [ ] 첫 번째 도메인 instruction.md 검수 완료

---

### 3Q-M3 (9월): 품질 체계 완성 & AI-Readiness 검증 & LLM 튜닝 & 4Q 준비

#### Data Platform Engineer
- [ ] **DLT Expectations 전면 적용** (Mart 레이어 포함)
  | 레이어 | 필수 Expectation |
  |--------|----------------|
  | Raw | NOT NULL (PK), 중복 없음 |
  | Staging | NOT NULL (핵심 컬럼), 허용 값 범위 |
  | Mart | NOT NULL, 집계 합산 검증 |
- [ ] **Expectation 실패 → Slack 알람 + 자동 격리** (DLT quarantine 테이블)
- [ ] **플랫폼 헬스 대시보드 완성** (Databricks SQL Dashboard)
- [ ] **4Q Shared Tool Library 설계 검토** (AI DataOps Engineer와 협업)
- [ ] **MLOps 연결 사전 조사**: Feature Store 구조 검토 시작

#### AI DataOps Engineer
- [ ] **AI-Readiness 최종 검증 및 목표 달성**
  - AI-Readiness 평균 점수 **≥ 80점**
- [ ] **Agent 전용 Service Principal 발급 및 권한 설정**
- [ ] **AI Gateway 설정 준비** (모델 라우팅·가드레일 구성 계획)
- [ ] **Agent 저장소 구조 확정**
  ```
  agents/
  ├── shared/tools/            # Shared Tool Library (4Q 구현)
  ├── instructions/
  │   ├── _global.md           # 모든 Agent 공통 규칙
  │   └── domains/{domain}/instruction.md
  └── {domain}_agent/          # 개별 Agent (PM Lead & Analyst 소유)
  ```
- [ ] **`_global.md` 초안 작성** (출처 명시·PII 처리·응답 형식 등)
- [ ] **prod CI/CD 파이프라인 완성** (dev → prod 배포 자동화)

#### PM Lead & Analyst
- [ ] **AI-Readiness 검증 테스트** (LLM 직접 호출)
  ```python
  # 20개 이상의 검증 질문으로 메타데이터 품질 확인
  test_questions = [
      "지난 주 팀별 작업량 요약해줘",
      "이번 달 이상 감지된 케이스는 몇 건이야?",
      "Gen1 vs Gen2 성과 비교해줘"
  ]
  # → LLM이 올바른 테이블을 찾고 정확한 SQL을 생성하는지 확인
  # → 오답 → 메타데이터 보강 요청 (AI DataOps Engineer)
  ```
- [ ] **LLM 튜닝 최종**: 검증 테스트 결과 기반 instruction.md 반복 개선
- [ ] **전체 도메인 instruction.md 완성**
- [ ] **분석 워크플로우 설계 완성**: 4Q에 구현할 자동화 파이프라인 상세 스펙
- [ ] **보고서 템플릿 확정**: 출력 형식·품질 기준·자동화 방식

#### 3Q AI-Readiness Gate (4Q 진입 조건)

> **아래 기준을 모두 충족한 후 4Q를 시작한다**

| 기준 | 목표치 | 담당 |
|------|-------|------|
| AI-Readiness 평균 점수 | **≥ 80점** | AI DataOps Engineer |
| 메타데이터 완성도 | **100%** | AI DataOps Engineer |
| Data Contract 적용률 (마트) | **100%** | AI DataOps Engineer |
| Lineage 커버리지 (핵심 마트) | **100%** | Data Platform Engineer |
| DLT Expectations 커버리지 | **100%** | Data Platform Engineer |
| LLM 직접 테스트 SQL 정확도 | **≥ 70%** | PM Lead & Analyst |
| instruction.md 도메인 커버리지 | **100%** | PM Lead & Analyst |
| Agent Service Principal 권한 설정 | **완료** | AI DataOps Engineer |

---

## 6. 4Q 상세 계획 — AI Agent 기반 플랫폼 자동화

> **전제**: 3Q AI-Readiness Gate 통과 후 시작
> **목표**: 사용자가 AI Agent를 통해 스스로 분석하는 환경을 구축하고,
> 자동화된 분석 워크플로우로 보고서 생성까지 완전 자동화한다

---

### 4Q-M1 (10월): Agent 플랫폼 인프라 구축

#### Data Platform Engineer
- [ ] **Shared Tool Library v1 구현**
  ```python
  # Data Discovery Tool (3Q 메타데이터 기반)
  def search_tables(keyword: str, domain: str = None) -> list[TableInfo]:
      """description · grain · business_term 포함 반환"""

  # SQL Execution Tool (안전 가드레일 포함)
  def execute_sql(query: str, agent_id: str) -> QueryResult:
      """SELECT만 허용. 스캔 행 제한. 타임아웃. 실행 로그 기록"""

  # Contract Lookup Tool
  def get_contract(table_name: str) -> ContractInfo:
      """SLA · 품질 기준 · 비즈니스 정의 반환"""
  ```
- [ ] **Agent 실행 환경 구성** (Databricks Apps 또는 API 서버)
- [ ] **Agent 사용 로그 수집 테이블 활성화**
- [ ] **MLOps 파이프라인 연결 설계 시작** (Feature Store 구조 확정)

#### AI DataOps Engineer
- [ ] **AI Gateway 구성**: 모델 라우팅, 가드레일, 벤더 Lock-in 방지
- [ ] **Agent Registry 구성**: 등록·버전 관리·접근 권한
- [ ] **Agent CI/CD 파이프라인 완성**: PR → 자동 테스트 → 배포
- [ ] **Agent Observability 기반**: 기본 모니터링 대시보드

#### PM Lead & Analyst
- [ ] **첫 번째 Agent 구현 시작** (도메인 지식 기반)
  ```python
  class DomainAnalysisAgent:
      """
      도구: Data Discovery + SQL Execution + Contract Lookup
      instruction: _global.md + domains/{domain}/instruction.md
      특징: 앱 로그 기반 도메인 지식 탑재, 인과관계 분석 포함
      """
  ```
- [ ] **분석 워크플로우 v1 구현**: 자동 데이터 수집 → LLM 분석 → 보고서 생성

#### 4Q-M1 완료 기준
- [ ] Shared Tool Library 3종 동작 확인
- [ ] AI Gateway 연결 및 가드레일 동작 확인
- [ ] Agent CI/CD: PR → 자동 배포 성공
- [ ] 첫 번째 Agent 기본 동작 확인

---

### 4Q-M2 (11월): 첫 번째 Agent 파일럿 & 분석 워크플로우 검증

#### Data Platform Engineer
- [ ] **Shared Tool Library v2**: Visualization Tool, Anomaly Detection Tool
- [ ] **파이프라인 장애 대응 자동화** 강화
- [ ] **MLOps Feature Store 초기 구축**

#### AI DataOps Engineer
- [ ] **Agent Observability 고도화**: 응답 품질 스코어 자동 추적, DBU 비용 집계
- [ ] **신규 Agent 배포 체크리스트 정립**
  ```
  ✅ Service Principal 최소 권한 설정
  ✅ instruction.md 및 _global.md 상속 확인
  ✅ Agent Registry 등록
  ✅ 응답 로그 수집 연결
  ✅ CI/CD 파이프라인 연결
  ✅ 해당 도메인 AI-Readiness 점수 ≥ 80점 확인
  ```

#### PM Lead & Analyst
- [ ] **파일럿 운영** (2주): 사용자 팀 3~5명 대상
  - 실제 질문 20개 이상 수집 → Agent 응답 → 사용자 정확도 평가
  - 오답 원인 분류
    ```
    instruction.md 규칙 누락  → PM Lead & Analyst 수정
    메타데이터 불완전         → AI DataOps Engineer 보강
    Tool 기능 부족            → Data Platform Engineer 지원
    ```
- [ ] **보고서 자동화 v1 런칭**: 정기 리포트 자동 생성 파이프라인 가동
- [ ] **사용자 주도 분석 환경 베타 오픈**

#### 4Q-M2 완료 기준
- [ ] 첫 번째 Agent 파일럿 완료
- [ ] 응답 정확도 **≥ 85%** (사용자 평가)
- [ ] 보고서 자동화 v1 가동
- [ ] instruction.md 개선 루프 1사이클 완료

---

### 4Q-M3 (12월): 확장 & 안정화 & 운영 체계 수립

#### Data Platform Engineer
- [ ] 플랫폼 운영 런북 최종 완성
- [ ] MLOps 파이프라인 연결 1차 완료
- [ ] 월간 플랫폼 헬스 리포트 자동화

#### AI DataOps Engineer
- [ ] 두 번째 Agent 도메인 거버넌스 정비 (메타데이터·Contract 확인)
- [ ] Agent 생태계 운영 표준 프로세스 문서화
- [ ] 신규 도메인 추가 시 체크리스트 검증

#### PM Lead & Analyst
- [ ] 첫 번째 Agent 프로덕션 전체 롤아웃
- [ ] 두 번째 Agent 개발 시작
- [ ] 분석 워크플로우 v2: 사용자 피드백 반영 개선
- [ ] 2026년 생태계 확장 로드맵 수립

#### 4Q 최종 완료 기준
- [ ] 활성 Agent **≥ 2개** 프로덕션 운영
- [ ] Agent 응답 정확도 **≥ 85%**
- [ ] 보고서 자동화 파이프라인 안정 운영
- [ ] 단순 데이터 추출 요청 **-30%** 이상
- [ ] MLOps 파이프라인 1차 연결 완료

---

## 7. KPI 체계

### 3Q KPI — AI-Readiness

| 지표 | 담당 | 7월 말 | 8월 말 | 9월 말 (Gate) |
|------|------|-------|-------|-------------|
| AI-Readiness 평균 점수 | AI DataOps Engineer | 기준선 | ≥ 60점 | **≥ 80점** |
| 메타데이터 완성도 | AI DataOps Engineer | 현황 | ≥ 70% | **100%** |
| Data Contract 적용률 | AI DataOps Engineer | 현황 | ≥ 70% | **100%** |
| Lineage 커버리지 | Data Platform Engineer | 현황 | ≥ 70% | **100%** |
| DLT Expectations 커버리지 | Data Platform Engineer | 현황 | ≥ 70% | **100%** |
| LLM 직접 테스트 정확도 | PM Lead & Analyst | - | 측정 | **≥ 70%** |
| instruction.md 도메인 커버리지 | PM Lead & Analyst | - | 50% | **100%** |

### 4Q KPI — Agent 플랫폼 & 분석 자동화

| 지표 | 담당 | 10월 말 | 11월 말 | 12월 말 |
|------|------|--------|--------|--------|
| Shared Tool 가용성 | Data Platform Engineer | ≥ 99% | ≥ 99% | ≥ 99.9% |
| 파이프라인 성공률 | Data Platform Engineer | ≥ 97% | ≥ 99% | ≥ 99% |
| Agent 응답 정확도 | PM Lead & Analyst | - | **≥ 85%** | ≥ 85% |
| 활성 Agent 수 | PM Lead & Analyst | 0 | 1 (파일럿) | **≥ 2** |
| 보고서 자동화 가동 | PM Lead & Analyst | - | ✅ | 안정 운영 |
| 단순 추출 요청 변화 | 전체 | 기준선 | 측정 | **-30%** |

---

## 8. 반복 확장 사이클 (2026년~)

```
PM Lead & Analyst: 신규 도메인 니즈 발굴
        ↓
AI DataOps Engineer: AI-Readiness 확인
(해당 도메인 테이블 점수 ≥ 80점? 아니면 메타데이터 보강 먼저)
        ↓
PM Lead & Analyst: instruction.md 작성 + Agent 개발
        ↓
Data Platform Engineer: Shared Tool 지원
AI DataOps Engineer: 배포 · CI/CD · 권한 설정
        ↓
PM Lead & Analyst: 파일럿 → 프로덕션 롤아웃 → 사용자 온보딩
        ↓
전체: 품질 모니터링 + 개선 루프
        ↓
다음 사이클 →
```

> **장기 벤치마크** (TMAP 사례)
> - 단순 추출 요청 **-68%**
> - 전 직원 데이터 직접 접근 **71%**
> - Genie 정확도 **Phase 5: 95%** (거버넌스 정교화 누적 결과)

---

## 9. 역할 한눈에 보기

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Data Platform Engineer                                                  │
│  What: 데이터가 안정적으로 흐르는 파이프라인과 인프라                     │
│  3Q: DLT 품질 체계 · Observability · Lineage · 장애 대응                │
│  4Q: Shared Tool Library · MLOps 파이프라인 연결                        │
│  미래: ML Feature Store · 모델 파이프라인 운영                           │
├──────────────────────────────────────────────────────────────────────────┤
│  AI DataOps Engineer (DataOps + Agent 생태계)                       │
│  What: 데이터 자산이 올바르게 정의되고 Agent가 신뢰하는 구조              │
│  3Q: 거버넌스 · Data Contract · AI-Readable 구조 · CI/CD                │
│  4Q: Agent Registry · AI Gateway · Agent CI/CD · Observability          │
├──────────────────────────────────────────────────────────────────────────┤
│  PM Lead & Analyst                                                       │
│  What: 도메인 지식을 Agent에 담아 사용자가 스스로 분석하게 한다           │
│  3Q: 앱 로그 분석 · instruction.md · LLM 튜닝 · 워크플로우 설계         │
│  4Q: Agent 개발 · 파일럿 · 보고서 자동화 · 사용자 분석 환경 런칭        │
└──────────────────────────────────────────────────────────────────────────┘
```

*참고: Databricks AI Day Seoul — "데이터 플랫폼의 미래: 4가지 혁신 코드" (수진, 주미, 성환)*
