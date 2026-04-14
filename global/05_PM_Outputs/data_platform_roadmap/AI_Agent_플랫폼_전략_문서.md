# AI Agent 기반 데이터 플랫폼 전략

**문서 버전**: v1.0
**작성일**: 2026-04-09
**작성 팀**: Nova Platform Team (PM Lead / Data Platform Engineer / AI DataOps Engineer)

---

## 1. 전략 전환의 배경

### 1-1. 파편화된 데이터 스택의 한계

기존 데이터 조직은 구조적 병목을 안고 운영되어 왔다.

- **데이터 엔지니어**는 복잡한 파이프라인 구축과 유지보수에 매몰되어 비즈니스 가치 창출에 집중하지 못했다.
- **데이터 분석가**는 반복적인 추출 요청과 지표 설명 업무라는 병목에 갇혀, 실질적인 인사이트 생산 시간이 부족했다.
- **비즈니스 사용자**는 데이터 접근 자체에 높은 허들이 있어 의사결정이 지연되었다.

이 분절은 단순한 비효율이 아니라, **데이터 자산이 비즈니스 가치로 이어지는 E2E 생명주기를 단절**시키는 근본적 문제였다.

### 1-2. Databricks AI Day Seoul이 제시한 전환점

> *"Databricks를 도입한다는 것은 단순히 툴 하나를 더 쓰는 것이 아니라,*
> *데이터 자산을 더 빨리 만들고, 더 쉽게 보여주고, 더 넓게 쓰이게 하는 방식으로 바꾸는 일에 가깝습니다."*
> — Databricks AI Day Seoul, Jumi

Databricks AI Day Seoul에서 확인된 4가지 혁신 코드는 우리 팀의 전략 전환에 결정적인 방향을 제시했다.

---

#### 혁신 코드 1 — 운영 패러다임 전환: dbt → Databricks 네이티브

기존 dbt 모델, SQL 스크립트, 별도 스케줄러(Airflow)로 파편화된 운영 체계는
**Databricks Workflows + Delta Live Tables(DLT)** 중심으로 재편되어야 한다.

- Bronze → Silver → Gold(Raw → Staging → Mart)로 이어지는 파이프라인의 전 과정이 단일 플랫폼에서 투명하게 관리된다.
- 적재, 품질 체크, 모니터링이 하나의 화면에서 통합되어 데이터 팀의 운영 가시성이 획기적으로 향상된다.
- Databricks Apps + Git 기반 배포를 통해 운영 환경에 영향 없이 개발 환경을 격리할 수 있다.

> **우리 팀의 결정**: dbt를 제거하고 DLT + Databricks Workflows로 전환 완료.
> 이는 기술 트렌드가 아니라 **운영 가능한 형태로의 진화**다.

---

#### 혁신 코드 2 — 데이터 민주화: 대시보드를 넘어 '대화형 지능'으로

정적 대시보드가 소비의 끝이었던 시대는 끝났다.
비즈니스 사용자는 이제 **Natural Language UI**를 통해 데이터와 직접 대화한다.

실제 사례:
- **무신사(MUSINSA)**: Genie Agent 심층 해석 + Genie Chat Ad-hoc 질의를 결합, 현업이 직접 인사이트를 도출하는 셀프서비스 체계 완성
- **TMAP**: 셀프서비스 도입 후 단순 추출 요청 **68% 감소**, 전 직원 **71%**가 데이터에 직접 접근

단, AI가 신뢰할 수 있는 답을 내놓으려면 **준비된 데이터 자산**이 선행되어야 한다.
핵심 테이블 선정, 시맨틱 정리, 비즈니스 용어 정의 같은 메타데이터 등록이 전제 조건이다.

> **우리 팀의 결정**: Analytics Engineer가 개별 분석 요청을 처리하는 구조 대신,
> **AI Agent가 사용자 접점을 담당**하는 구조로 전환.
> Analytics Engineer 역할을 별도로 두지 않는 배경이 여기에 있다.

---

#### 혁신 코드 3 — 에이전틱 AI: '역할을 가진 Agent'들의 협업 체계

> *"2026년까지 기업의 74%가 에이전틱 AI를 도입할 것으로 전망된다."*
> — Databricks AI Day Seoul

- SQL만으로 AI 함수를 호출해 텍스트의 감성·맥락을 추출하는 **Vibe Analytics**가 분석가의 역할을 증강시킨다.
- 단순 상관관계를 넘어 **"왜(Why)" 인과관계 파이프라인**이 데이터의 실질적 활용도를 높인다.
- 정산 확인, 딜리버리 모니터링처럼 **특정 도메인 지식을 가진 Agent**들이 분석가의 반복 업무를 구조적으로 대신한다.

> **우리 팀의 결정**: 도메인 특화 Agent를 **전담 개발하는 역할(AI DataOps Engineer)** 을 신설.
> 이는 에이전틱 AI 시대에 가장 직접적으로 비즈니스 가치를 창출하는 포지션이다.

---

#### 혁신 코드 4 — AI-Readable 거버넌스: Unity Catalog 기반 아키텍처 신뢰

> *"AI 성능의 임계점은 모델이 아니라 데이터의 구조와 컨텍스트 품질에 의해 결정된다."*
> — Databricks AI Day Seoul

- **Unity Catalog** 기반 체계적 구조화로 AI가 데이터 간 관계를 정확히 파악할 수 있어야 한다.
- 조인 복잡도를 줄이는 **One Big Table(OBT)** 방식의 설계는 LLM 문맥 파악을 도와 분석 정확도를 최대 95%까지 향상시킨다.
- **AI Gateway**를 통한 모델 라우팅·가드레일 통합 관리로 보안을 강화하고 벤더 종속성(Vendor Lock-in)을 방지한다.
- 기술 도입보다 어려운 것은 **기존 워크플로우를 플랫폼으로 옮기는 '운영 전환'** 이다.

> **우리 팀의 결정**: 'AI-Readable' 데이터 환경 구축을 **AI DataOps Engineer의 핵심 책임**으로 정의.
> Genie 정확도가 Phase별 거버넌스 정교화를 통해 45% → 95%로 높아지듯,
> 메타데이터 품질과 Unity Catalog 거버넌스에 지속적으로 투자한다.

---

## 2. 전략 방향: AI Agent 기반 데이터 플랫폼 생태계

### 핵심 철학

> 데이터 팀이 분석을 대신 해주는 구조가 아니라,
> 사용자가 AI Agent를 통해 스스로 데이터를 활용할 수 있는 **생태계**를 구축한다.
> 플랫폼 팀의 역할은 "분석 수행"이 아닌 "생태계 운영과 확장"이다.

### 전체 아키텍처

```
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 4: 사용자 (비즈니스 팀)                                        │
│                                                                       │
│   팀 A                팀 B                팀 C                        │
│  "성과 분석"          "이상 감지"          "리포트 생성"               │
│    자연어 질의          자연어 질의          자연어 질의                │
└──────────┬───────────────┬───────────────────┬───────────────────────┘
           │               │                   │
           │       Natural Language Interface   │
┌──────────▼───────────────▼───────────────────▼───────────────────────┐
│  LAYER 3: 개별 AI Agent  ← AI DataOps Engineer가 개발·운영       │
│                                                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │
│  │ Performance     │  │ Anomaly         │  │ Report          │      │
│  │ Analysis Agent  │  │ Detection Agent │  │ Generator Agent │      │
│  │                 │  │                 │  │                 │      │
│  │ instruction.md  │  │ instruction.md  │  │ instruction.md  │      │
│  │ (도메인 분석룰)  │  │ (이상 탐지 룰)  │  │ (리포트 형식)   │      │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘      │
└───────────┼────────────────────┼────────────────────┼───────────────┘
            │     공유 플랫폼 인터페이스 (Shared Tool Library)           │
┌───────────▼────────────────────▼────────────────────▼───────────────┐
│  LAYER 2: AI Agent 플랫폼  ← Data Platform Engineer가 구축·관리      │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Shared Tool Library                                         │   │
│  │  ├── Data Discovery Tool  (Unity Catalog 탐색)               │   │
│  │  ├── SQL Execution Tool   (Databricks SQL Warehouse 실행)    │   │
│  │  ├── Contract Lookup Tool (Data Contract·품질기준 조회)       │   │
│  │  └── Lineage Tracer Tool  (데이터 혈통 추적)                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  Agent Registry │ instruction.md 관리 │ Agent Observability          │
│  AI Gateway     │ CI/CD Pipeline      │ Cost Governance              │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│  LAYER 1: 데이터 플랫폼 (Databricks)  ← Data Platform Engineer 책임  │
│                                                                       │
│  Unity Catalog (AI-Readable 거버넌스)                                 │
│  · OBT 설계 원칙 적용 (LLM 문맥 파악 최적화)                          │
│  · 메타데이터 완성도 100% 목표 (description, grain, business_term)     │
│  · PII 마스킹, 접근 제어, Lineage 자동 수집                           │
│                                                                       │
│  Delta Lake (DLT 파이프라인)      Databricks Workflows                │
│  Raw → Staging → Mart             · 스케줄링 · 실패 알람              │
│  · DLT Expectations (품질 보증)   · Agent 배포 CI/CD                  │
│  · Data Contract 적용             · 비용 모니터링                     │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│  LAYER 0: 데이터 소스  (Databricks 이관 완료)                         │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. R&R 정의

### 역할 재정립 배경

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

### Data Platform Engineer

**핵심 정체성**: 데이터가 안정적으로 흐르고 신뢰할 수 있는 플랫폼 인프라를 책임진다

#### 현재 책임 영역

| 영역 | 구체적 책임 |
|------|-----------|
| **데이터 파이프라인** | DLT 파이프라인 구축·운영 (Raw → Staging → Mart) |
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

> **한 줄 정의**: "데이터가 제때, 정확하게, 안정적으로 흐르는 환경을 만들고 유지한다."
>
> *Genie 정확도가 Phase 1(45%) → Phase 5(95%)로 올라가는 것은 AI DataOps Engineer의 메타데이터·거버넌스 투자에 직결된다.*

---

### AI DataOps Engineer

**핵심 정체성**: 데이터 자산이 신뢰받고 올바르게 쓰일 수 있도록 거버넌스와 구조를 책임지며, Agent 생태계의 기반을 운영한다

> 역할 범위가 기존 Agent 개발 중심에서 **DataOps 전반으로 확장**됨.
> 데이터 거버넌스·컨트랙트·CI/CD·AI-Readable 구조가 핵심 책임이 되며,
> Agent 생태계 구축은 Data Platform Engineer와 함께 협업한다.

#### DataOps 책임 영역 (핵심)

| 영역 | 구체적 책임 |
|------|-----------|
| **데이터 거버넌스** | Unity Catalog 접근 제어 정책, 역할별 권한 매트릭스, PII 마스킹 자동화 |
| **Data Contract** | 스키마·SLA·품질 기준 정의, Contract YAML 작성·버전 관리, 변경 정책 운영 |
| **CI/CD** | 파이프라인·Agent 코드 배포 자동화, 브랜치 전략, 환경 격리 (dev/prod) |
| **AI-Readable 구조** | 메타데이터 완성도 관리, OBT 설계, 비즈니스 용어 사전, Databricks 네이티브 Comment 적용 |
| **태그·분류 체계** | domain · owner · data_class · sla_tier 태그 표준화 및 관리 |

#### Agent 생태계 책임 영역

| 영역 | 구체적 책임 |
|------|-----------|
| **Agent Registry** | Agent 등록·버전 관리·접근 권한 체계 |
| **AI Gateway** | 모델 라우팅, 가드레일 통합, 벤더 Lock-in 방지 |
| **Agent CI/CD** | Agent 코드 PR → 자동 테스트 → 배포 파이프라인 |
| **Agent Observability** | 응답 품질 스코어 추적, 사용 로그 수집·분석, 이상 알람 |
| **Shared Tool Library** | Data Platform Engineer와 협업하여 Agent 공통 도구 설계·검증 |

> **한 줄 정의**: "데이터 자산이 올바르게 정의되고, 안전하게 접근되며, Agent가 신뢰하는 구조 위에서 동작하도록 한다."

---

### PM Lead & Analyst

**핵심 정체성**: 도메인 지식을 데이터와 연결하여 사용자가 AI Agent를 통해 스스로 분석할 수 있는 환경을 구축한다

> 기존 PM Lead의 전략·조율 역할에 더해,
> **도메인 전문 분석가로서 AI Agent에 지식을 학습시키고**
> **사용자 주도 분석 환경과 자동화 워크플로우를 직접 설계·운영**하는 역할을 맡는다.

#### 도메인 지식 → Agent 구현

| 영역 | 구체적 책임 |
|------|-----------|
| **도메인 지식 학습** | 앱 로그 기반 사용자 행동 패턴 분석, 비즈니스 규칙 추출 |
| **LLM 도메인 튜닝** | instruction.md 작성 (분석 규칙·비즈니스 용어·인과관계 정의), 프롬프트 최적화 |
| **분석 템플릿 설계** | 균일한 품질의 결과 보고서 템플릿 개발, 출력 형식 표준화 |
| **Agent 구현** | 도메인 특화 Agent 설계·테스트, 사용자 검수 조율 |

#### 사용자 주도 분석 환경 구축

| 영역 | 구체적 책임 |
|------|-----------|
| **분석 워크플로우** | AI Agent 기반 자동화 분석 파이프라인 설계·운영 |
| **사용자 환경** | 사용자가 LLM 기반 분석을 직접 수행할 수 있는 인터페이스 구성 |
| **온보딩** | 사용자 팀 교육, Agent 활용 가이드, 피드백 수집 |
| **보고서 자동화** | 정기 리포트 자동 생성 파이프라인, 보고서 품질 일관성 유지 |

#### 전략·조율 (기존 PM 역할 유지)

| 영역 | 구체적 책임 |
|------|-----------|
| **로드맵** | 분기별 플랫폼 생태계 전략 수립 및 우선순위 결정 |
| **조율** | Data Platform Engineer ↔ AI DataOps Engineer 협업 경계 관리 |
| **KPI** | 플랫폼 성숙도 측정, 분기별 리뷰 |
| **확장 전략** | 신규 도메인·사용자 팀 온보딩 계획 |

> **한 줄 정의**: "도메인 지식을 Agent에 녹여내고, 사용자가 스스로 분석하는 환경을 만든다."

---

### 역할 분담 요약

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

### 협업 경계 (RACI)

#### DataOps / 인프라 영역

| 활동 | PM Lead & Analyst | Data Platform Engineer | AI DataOps Engineer |
|------|:---:|:---:|:---:|
| 파이프라인 설계·운영 | I | **R/A** | C |
| DB 통합·소스 연결 | I | **R/A** | I |
| Observability 구축 | I | **R/A** | C |
| Data Contract 정의 | C | C | **R/A** |
| 거버넌스·접근 제어 | I | C | **R/A** |
| AI-Readable 구조 설계 | C | C | **R/A** |
| CI/CD 파이프라인 | I | C | **R/A** |
| 비용 최적화 | A | **R** | C |

#### Agent 생태계 영역

| 활동 | PM Lead & Analyst | Data Platform Engineer | AI DataOps Engineer |
|------|:---:|:---:|:---:|
| Shared Tool Library | I | C | **R/A** |
| Agent Registry 운영 | I | I | **R/A** |
| AI Gateway 운영 | I | C | **R/A** |
| Agent 요구사항 정의 | **R/A** | I | C |
| instruction.md 작성 | **R/A** | I | C |
| Agent 구현 | **R/A** | I | C |
| Agent Observability | C | I | **R/A** |
| 사용자 온보딩 | **R/A** | I | C |

*R=Responsible, A=Accountable, C=Consulted, I=Informed*

---

## 4. 구축 로드맵 (18주)

| Phase | 내용 | 기간 | 주 담당자 | 누적 |
|-------|------|------|---------|------|
| **Phase 1** | 플랫폼 기반 & AI Agent 생태계 인프라 | 4주 | Data Platform Engineer | 4주 |
| **Phase 2** | AI-Readable 데이터 환경 완비 | 3주 | Data Platform Engineer | 7주 |
| **Phase 3** | 첫 번째 Agent 개발 · 파일럿 | 4주 | AI DataOps Engineer | 11주 |
| **Phase 4** | 플랫폼 강화 · Agent 확장 | 4주 | 병렬 진행 | 15주 |
| **Phase 5** | 생태계 안정화 · 운영 체계 수립 | 3주 | 전체 | 18주 |

---

### Phase 1 — 플랫폼 기반 & Agent 생태계 인프라 (4주)

> AI-Readable 거버넌스 구조를 완비하고 Agent가 동작할 수 있는 인프라를 구성한다.
> *"철저한 운영 설계와 거버넌스 없이는 아무리 훌륭한 도구도 그 가치를 발휘할 수 없다." — Databricks AI Day Seoul*

**Data Platform Engineer**
- [ ] Unity Catalog 접근 계층 설계 및 적용
  ```
  platform_admin          → 전체 권한
  data_platform_engineer  → Raw~Mart 읽기·쓰기
  agent_service_{name}    → Mart 읽기 전용 (Agent별 Service Principal)
  business_user_{team}    → Mart 지정 테이블 읽기
  ```
- [ ] PII 컬럼 태그 기반 마스킹 자동 적용
- [ ] AI Gateway 설정: 모델 라우팅, 가드레일 통합, 벤더 Lock-in 방지
- [ ] Shared Tool Library v1 구축
  - Data Discovery Tool (Unity Catalog 탐색)
  - SQL Execution Tool (SELECT 전용, 가드레일 포함)
  - Contract Lookup Tool (비즈니스 정의·SLA 조회)
- [ ] instruction.md 저장소 구조 확정 및 `_global.md` 작성
- [ ] Agent CI/CD 파이프라인 구성 (PR → 자동 테스트 → 배포)
- [ ] Agent 사용 로그 수집 테이블 설계 및 기본 모니터링 대시보드 구성

**AI DataOps Engineer (이 기간)**
- [ ] 첫 번째 Agent 대상 사용자 팀 인터뷰 (3~5회)
- [ ] Agent 요구사항 문서 작성 (질문 유형, 기대 응답, 인과관계 분석 니즈)
- [ ] 도메인 instruction.md 초안 작성 시작

**완료 기준**
- [ ] Service Principal로 Mart 테이블 읽기 테스트 통과
- [ ] Shared Tool Library 3종 동작 확인
- [ ] AI Gateway 연결 및 기본 가드레일 동작 확인
- [ ] 첫 번째 Agent 요구사항 문서 확정

---

### Phase 2 — AI-Readable 데이터 환경 완비 (3주)

> Genie 정확도 로드맵(Phase 1: 45% → Phase 5: 95%)이 증명하듯,
> AI Agent 응답 품질은 메타데이터와 거버넌스 품질에 직결된다.

**Data Platform Engineer**

**AI-Readable 메타데이터 완성**
- [ ] 전체 마트 테이블 Unity Catalog 메타데이터 완성
  ```sql
  -- AI가 반드시 읽어야 하는 3가지 필드
  COMMENT ON TABLE mart.orders IS
    '결제 완료된 주문 데이터. 1 row = 1 주문 건. 매시 30분 이내 갱신.';

  ALTER TABLE mart.orders ALTER COLUMN customer_id
    COMMENT '주문한 고객 ID. business_term: 고객. PII: hash 처리됨.';
  ```
- [ ] OBT(One Big Table) 설계 원칙 적용 검토
  - 조인 복잡도 높은 마트 테이블 식별 → 사전 조인 뷰 또는 OBT로 재설계
  - LLM이 단순 SELECT로 원하는 데이터를 얻을 수 있는 구조

**Data Contract 전면 적용**
- [ ] Contract YAML Agent 참조 필드 포함 작성
  ```yaml
  dataset:
    description: "이 테이블이 무엇을 나타내는지 한 문장"  # Agent 필수
    grain: "레코드 1개의 의미"                            # Agent 필수
    update_frequency: hourly
    sla:
      freshness_minutes: 30
  schema:
    - name: field_name
      description: "비즈니스 의미"
      business_term: "공식 비즈니스 용어"                 # Agent 필수
      pii: false
  ```
- [ ] 전체 마트 테이블 Contract 작성 완료

**Lineage 수집 및 품질 검증**
- [ ] Unity Catalog 내장 Lineage 활성화 (컬럼 수준)
- [ ] DLT Expectations 레이어별 기준 정의 및 적용
  | 레이어 | 필수 Expectation |
  |--------|----------------|
  | Raw | NOT NULL (PK), 중복 없음 |
  | Staging | NOT NULL (핵심 컬럼), 허용 값 범위 |
  | Mart | NOT NULL, 집계 합산 검증 |
- [ ] Expectation 실패 → Slack 알람 + Agent Observability 로그 연동
- [ ] 검증 실패 레코드 자동 격리 (DLT quarantine 테이블)

**AI DataOps Engineer**
- [ ] 첫 번째 Agent instruction.md 완성 (사용자 팀 검수 포함)
  - 비즈니스 용어 정의, 분석 규칙, 인과관계(Why) 분석 기준 포함
- [ ] Agent 응답 시나리오 20개 이상 작성

**완료 기준**
- [ ] 전체 마트 테이블 description + grain + business_term 100%
- [ ] Data Discovery Tool 키워드 검색 동작 확인
- [ ] DLT Expectations 커버리지 마트 테이블 100%
- [ ] OBT 재설계 대상 테이블 식별 완료

---

### Phase 3 — 첫 번째 Agent 개발 · 파일럿 (4주)

> AI DataOps Engineer가 주도하고 Data Platform Engineer가 플랫폼으로 지원.
> 개발-피드백 루프를 확립하는 단계.

**AI DataOps Engineer (주도)**

- [ ] Agent 구현 (Shared Tool 활용)
  ```python
  class PerformanceAnalysisAgent:
      """
      도구: Data Discovery, SQL Execution, Contract Lookup
      instruction: instructions/domains/{domain}/instruction.md
      핵심 기능: 성과 분석 + 인과관계(Why) 추론
      """
      def run(self, user_query: str) -> AgentResponse:
          # 1. instruction.md 로드
          # 2. Data Discovery → 관련 테이블 탐색
          # 3. Contract Lookup → 비즈니스 정의·품질 기준 확인
          # 4. SQL 실행 (Vibe Analytics 포함)
          # 5. 결과 + 출처 + 신뢰도 포함 응답
  ```
- [ ] 파일럿 운영 (2주): 사용자 팀 3~5명 대상 실사용 검증
- [ ] 오답 원인 분류 및 피드백 루프 운영
  ```
  오답 원인 분류
  ├── instruction.md 규칙 누락  → AI DataOps Engineer 수정
  ├── 메타데이터 불완전         → Data Platform Engineer 보강
  └── Tool 기능 부족            → 양쪽 협업으로 해결
  ```

**Data Platform Engineer (지원)**
- [ ] 파일럿 중 발견된 메타데이터 누락 긴급 보강
- [ ] Tool 오류·성능 이슈 수정
- [ ] Agent 쿼리 로그 분석 (패턴 파악)

**완료 기준**
- [ ] 첫 번째 Agent 파일럿 2주 완료
- [ ] 응답 정확도 ≥ 85% (사용자 평가 기준)
- [ ] instruction.md 개선 루프 1사이클 이상 완료

---

### Phase 4 — 플랫폼 강화 · Agent 확장 (4주)

두 트랙이 병렬로 진행된다.

**Data Platform Engineer 트랙**
- [ ] Shared Tool Library v2: Visualization Tool, Anomaly Detection Tool, Report Template Tool
- [ ] Agent Observability 고도화: 응답 품질 스코어 자동 추적, 비용 집계
- [ ] AI Gateway 고도화: 비정상 쿼리 패턴 탐지 및 자동 차단
- [ ] 플랫폼 보안 강화: Agent 쿼리 감사 로그 완전 활성화

**AI DataOps Engineer 트랙**
- [ ] 두 번째 Agent 개발 (Phase 3 결과 + PM Lead 우선순위 기반)
- [ ] 첫 번째 Agent 프로덕션 배포 및 전체 사용자 롤아웃
- [ ] 정기 품질 리뷰 일정 확정 (월 1회)

**완료 기준**
- [ ] Shared Tool Library v2 배포
- [ ] 첫 번째 Agent 프로덕션 롤아웃 완료
- [ ] 두 번째 Agent 파일럿 시작

---

### Phase 5 — 생태계 안정화 · 운영 체계 수립 (3주)

**Data Platform Engineer**
- [ ] 플랫폼 운영 런북 작성 (파이프라인 장애, Tool 오류, Agent 품질 급락 대응)
- [ ] 신규 Agent 배포 체크리스트 정립
- [ ] 월간 플랫폼 헬스 리포트 자동화

**AI DataOps Engineer**
- [ ] Agent 개발 표준 프로세스 문서화
  ```
  1. 사용자 인터뷰 → 요구사항 문서
  2. instruction.md 초안 → 도메인 사용자 검수
  3. Agent 구현 (Shared Tool + Vibe Analytics 활용)
  4. 시나리오 테스트 20개 이상
  5. 파일럿 (2주) → 정확도 ≥ 85%
  6. Data Platform Engineer 배포 요청 (체크리스트 첨부)
  7. 프로덕션 롤아웃 → 사용자 온보딩
  8. 월 1회 품질 리뷰
  ```

**완료 기준**
- [ ] 활성 Agent 2개 이상 프로덕션 운영 중
- [ ] 운영 런북 + 개발 표준 프로세스 문서화 완료
- [ ] 월간 헬스 리포트 1회 자동 생성

---

## 5. KPI 체계

### Data Platform Engineer 책임 (플랫폼 안정성 & AI-Readiness)

| 지표 | Phase 3 목표 | Phase 5 목표 |
|------|------------|------------|
| 파이프라인 성공률 (7일) | ≥ 97% | ≥ 99% |
| Freshness SLA 준수율 | ≥ 90% | ≥ 95% |
| DLT Expectations 커버리지 (마트) | 100% | 100% |
| 메타데이터 완성도 (마트 테이블) | ≥ 80% | 100% |
| Shared Tool 가용성 | ≥ 99% | ≥ 99.9% |

### AI DataOps Engineer 책임 (Agent 품질)

| 지표 | 첫 Agent 기준 | 누적 목표 |
|------|-------------|---------|
| Agent 응답 정확도 | ≥ 85% | ≥ 90% |
| SQL 실행 성공률 | ≥ 90% | ≥ 95% |
| 응답 내 출처 포함률 | 100% | 100% |
| 파일럿 → 정식 배포 전환율 | - | ≥ 80% |

### PM Lead 책임 (생태계 성숙도)

| 지표 | 목표 |
|------|------|
| 활성 Agent 수 | 분기 +1~2개 |
| 활성 사용자 팀 수 | 분기 +1~2팀 |
| 단순 데이터 추출 요청 건수 | 분기 -30% (TMAP 사례: -68% 장기 목표) |
| 데이터 직접 접근 사용자 비율 | 분기 +10%p (TMAP 사례: 71% 장기 목표) |

---

## 6. 반복 확장 사이클

Phase 5 완료 이후 아래 사이클을 반복하며 생태계를 확장한다.

```
신규 도메인/니즈 발굴 (PM Lead)
        ↓
요구사항 수집 (AI DataOps Engineer)
        ↓
플랫폼 지원 확인 (Data Platform Engineer)
(Tool 추가 필요? 메타데이터 보강? 권한 설정?)
        ↓
Agent 개발 · 파일럿 (AI DataOps Engineer)
        ↓
배포 · 롤아웃 (Data Platform Engineer + AI DataOps Engineer)
        ↓
품질 모니터링 · 개선 (양쪽 공동)
        ↓
다음 사이클
```

---

## 7. 결론

> *"데이터 경쟁력은 이제 자산의 소유가 아닌, 자산의 운영 능력에서 결정될 것이다."*
> — Databricks AI Day Seoul

우리 팀의 전략 전환은 기술 트렌드를 따르는 것이 아니다.
Databricks AI Day Seoul에서 확인한 4가지 혁신 코드는 이미 시장에서 검증된 방향성이며,
우리가 직면한 파편화된 스택의 한계를 돌파할 수 있는 실질적 경로다.

**3인 팀이 18주 안에 달성할 것:**

| 역할 | 핵심 산출물 |
|------|-----------|
| **Data Platform Engineer** | AI-Readable Unity Catalog, DLT 파이프라인, Shared Tool Library, AI Gateway |
| **AI DataOps Engineer** | 도메인 특화 Agent 2개+, instruction.md 프레임워크, 사용자 온보딩 |
| **PM Lead** | 생태계 로드맵, KPI 추적, 분기별 확장 계획 |

이 플랫폼이 완성되면, 비즈니스 사용자는 데이터 팀에 추출을 요청하는 대신
Agent와 직접 대화하며 인사이트를 얻는다.
분석 조직의 병목은 사라지고, 데이터 자산은 더 빨리 만들어지고, 더 쉽게 보여지고, 더 넓게 쓰인다.

---

*참고: Databricks AI Day Seoul — 데이터 플랫폼의 미래: 4가지 혁신 코드 (수진, 주미, 성환)*
