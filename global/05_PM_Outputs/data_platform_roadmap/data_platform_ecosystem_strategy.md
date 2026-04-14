# AI Agent 기반 데이터 플랫폼 생태계 전략

> **핵심 철학**: 플랫폼 자체가 AI Agent 기반으로 설계된다.
> Data Platform Engineer는 Agent들이 안정적으로 동작하는 **생태계(플랫폼 인프라)** 를 책임지고,
> AI DataOps Engineer는 사용자의 실제 문제를 해결하는 **개별 Agent** 를 개발한다.
> PM Lead는 생태계 전략과 Agent 개발 우선순위를 조율한다.

---

## 전체 아키텍처

```
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 4: 사용자                                                      │
│                                                                       │
│   팀 A                팀 B                팀 C                        │
│  "성과 분석"          "이상 감지"          "리포트 생성"               │
└──────────┬───────────────┬───────────────────┬───────────────────────┘
           │               │                   │
┌──────────▼───────────────▼───────────────────▼───────────────────────┐
│  LAYER 3: 개별 AI Agent  ← AI DataOps Engineer가 개발·운영              │
│                                                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │
│  │ Performance     │  │ Anomaly         │  │ Report          │      │
│  │ Analysis Agent  │  │ Detection Agent │  │ Generator Agent │      │
│  │                 │  │                 │  │                 │      │
│  │ instruction.md  │  │ instruction.md  │  │ instruction.md  │      │
│  │ (도메인 분석룰)  │  │ (이상 탐지 룰)  │  │ (리포트 형식)   │      │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘      │
└───────────┼────────────────────┼────────────────────┼───────────────┘
            │                    │                    │
            │   공유 플랫폼 인터페이스 (Tool 라이브러리)  │
┌───────────▼────────────────────▼────────────────────▼───────────────┐
│  LAYER 2: AI Agent 플랫폼  ← Data Platform Engineer가 구축·관리               │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Shared Tool Library (Agent가 공통으로 사용하는 도구)          │   │
│  │  ├── Data Discovery Tool   (Unity Catalog 탐색)               │   │
│  │  ├── SQL Execution Tool    (Databricks SQL Warehouse 실행)    │   │
│  │  ├── Contract Lookup Tool  (Data Contract·품질기준 조회)       │   │
│  │  └── Lineage Tracer Tool   (데이터 혈통 추적)                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Agent Registry  │  │ instruction.md   │  │ Agent Observ-    │  │
│  │  · 등록된 Agent  │  │ Management       │  │ ability          │  │
│  │  · 버전 관리     │  │ · 도메인별 관리   │  │ · 응답 품질 모니터│  │
│  │  · 접근 권한     │  │ · 버전 관리      │  │ · 사용 로그 분석 │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  CI/CD Pipeline  │  │  Cost Governance │  │  Access Control  │  │
│  │  · Agent 배포    │  │  · 쿼리 비용 추적 │  │  · Agent별 권한  │  │
│  │  · 자동 테스트   │  │  · 사용량 리포트  │  │  · 사용자 권한   │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│  LAYER 1: 데이터 플랫폼 (Databricks)  ← Data Platform Engineer가 책임         │
│                                                                       │
│  Unity Catalog           Delta Lake              Workflows            │
│  · 거버넌스               Raw / Stg / Int / Mart  · 파이프라인 실행    │
│  · 접근 제어              · Data Contract         · 스케줄링           │
│  · 메타데이터             · 품질 테스트             · 실패 알람         │
│  · Lineage 추적          · Observability                              │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│  LAYER 0: 데이터 소스  (이관 완료)                                     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## R&R 정의

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

#### 한 줄 정의
> "데이터가 제때, 정확하게, 안정적으로 흐르는 환경을 만들고 유지한다."

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

#### 한 줄 정의
> "데이터 자산이 올바르게 정의되고, 안전하게 접근되며, Agent가 신뢰하는 구조 위에서 동작하도록 한다."

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

#### 한 줄 정의
> "도메인 지식을 Agent에 녹여내고, 사용자가 스스로 분석하는 환경을 만든다."

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

## 전체 로드맵 (18주)

| Phase | 내용 | 기간 | 주 담당자 | 누적 |
|-------|------|------|---------|------|
| Phase 1 | 플랫폼 기반 · Agent 생태계 인프라 | 4주 | Data Platform Engineer | 4주 |
| Phase 2 | Agent가 활용할 데이터 환경 완비 | 3주 | Data Platform Engineer | 7주 |
| Phase 3 | 첫 번째 Agent 개발 · 파일럿 | 4주 | AI DataOps Engineer | 11주 |
| Phase 4 | 플랫폼 강화 · Agent 확장 | 4주 | 양쪽 병렬 | 15주 |
| Phase 5 | 생태계 안정화 · 운영 체계 | 3주 | 전체 | 18주 |

---

## Phase 1 — 플랫폼 기반 & Agent 생태계 인프라 (4주)

> Data Platform Engineer가 생태계의 기초를 완성하는 단계.
> AI DataOps Engineer는 이 기간에 첫 번째 Agent 요구사항을 수집·기획한다.

### Data Platform Engineer

#### Unity Catalog 거버넌스
- [ ] 데이터 접근 주체 4계층 설계 및 적용
  ```
  platform_admin      → 전체 권한
  data_engineer       → Raw~Mart 읽기·쓰기
  agent_service_{name}→ 특정 스키마 읽기 전용 (Agent별 Service Principal)
  business_user_{team}→ Mart 지정 테이블 읽기
  ```
- [ ] PII 컬럼 태그 기반 마스킹 자동 적용
- [ ] Agent 전용 Service Principal 발급 체계 구성

#### Shared Tool Library v1 (Agent 공통 도구)
- [ ] **Data Discovery Tool**: Unity Catalog 탐색, 테이블·컬럼 검색
  ```python
  def search_tables(keyword: str, domain: str = None) -> list[TableInfo]:
      """키워드로 테이블 탐색. 테이블명·description·grain·owner 반환"""

  def get_schema(table_name: str) -> SchemaInfo:
      """컬럼 목록, 타입, description, PII 여부, Data Contract 링크 반환"""
  ```
- [ ] **SQL Execution Tool**: 안전 가드레일 포함 쿼리 실행
  ```python
  def execute_sql(query: str, agent_id: str) -> QueryResult:
      """SELECT만 허용, 최대 스캔 행 제한, 타임아웃 설정, 실행 로그 기록"""
  ```
- [ ] **Contract Lookup Tool**: Data Contract·SLA·품질기준 조회
- [ ] Tool 응답 스펙 표준화 (Agent가 파싱하기 쉬운 JSON 구조)

#### instruction.md 관리 시스템
- [ ] 저장소 구조 확정
  ```
  instructions/
  ├── _template.md          # AI DataOps Engineer가 참조할 작성 가이드
  ├── _global.md            # 모든 Agent에 공통 적용되는 규칙
  └── domains/
      ├── labelit/
      │   └── instruction.md
      └── workload/
          └── instruction.md
  ```
- [ ] `_global.md` 초안 작성 (출처 명시 규칙, PII 처리 규칙, 응답 형식 등)
- [ ] instruction.md → Agent 컨텍스트 주입 메커니즘 구현

#### CI/CD & 배포 인프라
- [ ] Agent 코드 Git 저장소 구조 정의
  ```
  agents/
  ├── shared/tools/         # Shared Tool Library
  ├── performance_agent/    # 개별 Agent (AI DataOps Engineer 소유)
  └── anomaly_agent/
  ```
- [ ] Agent 배포 파이프라인 구성 (PR 머지 → 자동 테스트 → 배포)
- [ ] Agent 실행 환경 구성 (Databricks Apps 또는 외부 API 서버)

#### Agent Observability 기반
- [ ] Agent 사용 로그 수집 테이블 설계
  ```sql
  agent_logs (
    log_id, agent_name, agent_version,
    user_team, query_text, sql_generated,
    response_latency_ms, success, error_type,
    logged_at
  )
  ```
- [ ] 기본 모니터링 대시보드 초안 (성공률, 지연시간, 사용 빈도)

### AI DataOps Engineer (이 기간)
- [ ] 첫 번째 Agent 대상 사용자 팀 인터뷰 (3~5회)
- [ ] Agent 요구사항 문서 작성 (어떤 질문을 하는지, 어떤 답을 기대하는지)
- [ ] 해당 도메인 instruction.md 초안 작성 시작

### 완료 기준
- [ ] Service Principal로 Mart 테이블 읽기 테스트 통과
- [ ] Shared Tool Library 3종 동작 확인
- [ ] CI/CD: PR 머지 → Agent 자동 배포 성공
- [ ] 첫 번째 Agent 요구사항 문서 확정

---

## Phase 2 — Agent가 활용할 데이터 환경 완비 (3주)

> Agent의 응답 품질은 메타데이터와 Data Contract 품질에 비례한다.
> Data Platform Engineer가 Agent의 "이해력"을 높이는 작업에 집중한다.

### Data Platform Engineer

#### Data Contract 전면 적용
- [ ] Contract YAML 필수 필드 정의 (Agent가 참조하는 필드 강조)
  ```yaml
  dataset:
    description: "이 테이블이 무엇을 나타내는지 한 문장"   # Agent 필수 참조
    grain: "레코드 1개의 의미"                              # Agent 필수 참조
    update_frequency: hourly
    sla:
      freshness_minutes: 30
  schema:
    - name: field_name
      description: "비즈니스 의미"                          # Agent 필수 참조
      business_term: "공식 비즈니스 용어"                   # Agent 필수 참조
      pii: false
  ```
- [ ] 전체 마트 테이블 Contract 작성 완료 (grain + description 100%)
- [ ] `COMMENT ON TABLE / COLUMN` 구문으로 Unity Catalog에 직접 비즈니스 기술 적용

#### Data Lineage 수집
- [ ] Lineage 수집 활성화 (Unity Catalog 내장 또는 OpenLineage)
- [ ] Lineage Tracer Tool 개발 (Agent가 "이 컬럼 어디서 왔어?"를 물을 수 있게)
- [ ] 컬럼 수준 Lineage 커버리지: 핵심 마트 테이블 100%

#### 데이터 품질 검증 표준화 (Databricks 네이티브)
- [ ] Delta Live Tables Expectations 레이어별 기준 정의 및 적용
  | 레이어 | 필수 Expectation |
  |--------|----------------|
  | Raw | NOT NULL (PK), 중복 없음 (PK) |
  | Staging | NOT NULL (핵심 컬럼), 허용 값 범위 |
  | Mart | NOT NULL, 집계 합산 검증 (Reconciliation 노트북) |
- [ ] Expectation 실패 → Slack 알람 + Agent Observability 로그 연동
- [ ] 검증 실패 레코드 자동 격리: DLT quarantine 테이블 활용

#### Observability 고도화
- [ ] 5축 모니터링 가동 (Freshness / Volume / Schema / Distribution / Pipeline)
- [ ] 플랫폼 헬스 대시보드 완성

### AI DataOps Engineer
- [ ] 첫 번째 Agent instruction.md 완성 (사용자 팀 검수 포함)
- [ ] Agent 응답 시나리오 20개 이상 작성 (예상 Q&A 매핑)
- [ ] Shared Tool Library 사용법 숙지 및 Agent 설계 문서 작성

### 완료 기준
- [ ] 전체 마트 테이블 description + grain 100% 완성
- [ ] Data Discovery Tool로 비즈니스 용어 검색 동작 확인
- [ ] DLT Expectations 커버리지 마트 테이블 100%
- [ ] 첫 번째 Agent instruction.md 사용자 팀 검수 완료

---

## Phase 3 — 첫 번째 Agent 개발 · 파일럿 (4주)

> AI DataOps Engineer가 주도하고 Data Platform Engineer가 플랫폼으로 지원하는 단계.
> 첫 Agent를 실제 사용자와 함께 검증하며 개발-피드백 루프를 확립한다.

### AI DataOps Engineer (주도)

#### Agent 개발
- [ ] Agent 기본 구조 구현
  ```python
  class PerformanceAnalysisAgent:
      """
      사용 도구: Data Discovery, SQL Execution, Contract Lookup
      instruction: instructions/domains/labelit/instruction.md
      대상 사용자: Labelit 라벨러 성과 분석팀
      """
      def run(self, user_query: str) -> AgentResponse:
          # 1. instruction.md 컨텍스트 로드
          # 2. Data Discovery로 관련 테이블 탐색
          # 3. Contract Lookup으로 비즈니스 정의 확인
          # 4. SQL 생성 및 실행
          # 5. 결과 포맷 + 출처 표시
  ```
- [ ] 도메인 특화 추가 도구 필요 시 Data Platform Engineer와 협업하여 개발
- [ ] 응답 형식 정의: 분석 결과 + 데이터 출처 + 신뢰도 + 주의사항

#### 파일럿 운영 (2주)
- [ ] 대상 사용자 팀 3~5명 선정
- [ ] 실제 질문 20개 이상 수집 → Agent로 답변 → 사용자 정확도 평가
- [ ] 오답 케이스 분류: instruction.md 문제 / 메타데이터 문제 / Tool 문제
- [ ] 분류 결과에 따라 각 담당자에게 피드백 전달

#### instruction.md 개선 루프
```
사용자 질문
    ↓
Agent 응답
    ↓
사용자 평가 (정확 / 부정확 / 불완전)
    ↓
오답 원인 분류
    ├── instruction.md 규칙 누락 → AI DataOps Engineer 수정
    ├── 메타데이터 불완전 → Data Platform Engineer 보강
    └── Tool 기능 부족 → Data Platform Engineer + AI DataOps Engineer 협업
```

### Data Platform Engineer (지원)
- [ ] 파일럿 중 발견된 메타데이터 누락 항목 긴급 보강
- [ ] Tool 오류 또는 성능 이슈 수정
- [ ] Agent 사용 로그 분석: 어떤 쿼리 패턴이 많은지 파악
- [ ] 필요 시 파일럿 전용 도메인 추가 도구 개발

### PM Lead
- [ ] 파일럿 참여 사용자 조율 및 피드백 수집 프로세스 운영
- [ ] 파일럿 결과 기반 2번째 Agent 개발 우선순위 결정

### 완료 기준
- [ ] 첫 번째 Agent 실사용자 대상 파일럿 2주 완료
- [ ] 응답 정확도 ≥ 85% (사용자 평가 기준)
- [ ] 오답 원인 분류 및 개선 항목 정리 완료
- [ ] instruction.md 개선 루프 1사이클 이상 완료

---

## Phase 4 — 플랫폼 강화 · Agent 확장 (4주)

> Data Platform Engineer는 플랫폼을 고도화하고, AI DataOps Engineer는 두 번째 Agent를 개발한다.
> 두 트랙이 병렬로 진행되며 협업 접점에서 속도를 맞춘다.

### Data Platform Engineer 트랙

#### Shared Tool Library v2
- [ ] **Visualization Tool**: 쿼리 결과 → 차트/테이블 자동 생성
- [ ] **Anomaly Detection Tool**: 시계열 이상값 탐지 (통계 기반)
- [ ] **Report Template Tool**: 정기 리포트 포맷 자동화
- [ ] Tool 버전 관리 및 하위 호환성 정책 수립

#### Agent Observability 고도화
- [ ] Agent별 응답 품질 스코어 자동 추적
- [ ] 사용 패턴 분석: 자주 묻는 질문 유형 자동 분류
- [ ] 비용 추적: Agent별 쿼리 DBU 비용 집계

#### 플랫폼 보안 강화
- [ ] Agent 쿼리 감사 로그 완전 활성화
- [ ] 비정상 쿼리 패턴 탐지 (대용량 스캔, 반복 실패 등) → 자동 차단

### AI DataOps Engineer 트랙

#### 두 번째 Agent 개발
- [ ] Phase 3 파일럿 결과 + PM Lead 우선순위 기반으로 대상 선정
- [ ] 동일한 개발 프로세스 적용 (요구사항 → instruction.md → 개발 → 파일럿)
- [ ] 첫 번째 Agent에서 얻은 패턴을 재사용해 개발 속도 향상

#### 첫 번째 Agent 정식 운영 전환
- [ ] 파일럿 피드백 반영 후 프로덕션 배포
- [ ] 사용자 팀 전체 롤아웃 (온보딩 가이드 포함)
- [ ] 정기 품질 리뷰 일정 확정 (월 1회)

### 완료 기준
- [ ] Shared Tool Library v2 (Visualization 포함) 배포
- [ ] 첫 번째 Agent 프로덕션 롤아웃 완료
- [ ] 두 번째 Agent 파일럿 시작

---

## Phase 5 — 생태계 안정화 · 운영 체계 (3주)

> 플랫폼이 "운영되는" 상태로 전환. 이후는 반복 확장 사이클로 진행.

### Data Platform Engineer

- [ ] 플랫폼 운영 런북(Runbook) 작성
  - 파이프라인 장애 대응 절차
  - Tool 오류 대응 절차
  - Agent 응답 품질 급락 시 대응 절차
- [ ] 월간 플랫폼 헬스 리포트 자동화
- [ ] 신규 Agent 추가 시 플랫폼 체크리스트 정립
  ```
  신규 Agent 배포 체크리스트:
  ✅ Service Principal 최소 권한 설정
  ✅ instruction.md 작성 및 _global.md 상속 확인
  ✅ Agent Registry 등록
  ✅ 응답 로그 수집 연결
  ✅ CI/CD 파이프라인 연결
  ```

### AI DataOps Engineer

- [ ] Agent 개발 표준 프로세스 문서화 (다음 Agent부터 독립적으로 진행 가능하도록)
  ```
  1. 사용자 인터뷰 → 요구사항 문서
  2. instruction.md 초안 → 도메인 사용자 검수
  3. Agent 구현 (Shared Tool 활용)
  4. 시나리오 테스트 (20개 이상)
  5. 파일럿 (2주) → 정확도 ≥ 85% 확인
  6. Data Platform Engineer 배포 요청 (체크리스트 첨부)
  7. 프로덕션 롤아웃 → 사용자 온보딩
  8. 월 1회 품질 리뷰
  ```
- [ ] instruction.md 업데이트 주기 및 책임자 명확화

### PM Lead

- [ ] 전체 생태계 현황 리포트 작성 (Agent 수, 사용자 수, KPI 현황)
- [ ] 다음 분기 Agent 개발 로드맵 확정
- [ ] 플랫폼 성숙도 레벨 평가 및 다음 목표 설정

### 완료 기준
- [ ] 운영 런북 작성 완료
- [ ] Agent 개발 표준 프로세스 문서화 완료
- [ ] 활성 Agent 2개 이상 프로덕션 운영 중
- [ ] 월간 플랫폼 헬스 리포트 1회 자동 생성

---

## 반복 확장 사이클 (Phase 5 이후)

Phase 5 완료 후부터는 아래 사이클을 반복하며 생태계를 확장한다.

```
        ┌─────────────────────────────────────────────┐
        │           생태계 확장 반복 사이클              │
        │                                             │
        │  신규 도메인/니즈 발굴 (PM Lead)              │
        │          ↓                                  │
        │  요구사항 수집 (AI DataOps Engineer)             │
        │          ↓                                  │
        │  플랫폼 지원 확인 (Data Platform Engineer)             │
        │  (Tool 추가 필요? 데이터 없음? 권한 설정?)    │
        │          ↓                                  │
        │  Agent 개발 · 파일럿 (AI DataOps Engineer)      │
        │          ↓                                  │
        │  배포 · 롤아웃 (Data Platform Engineer + AI DataOps Engineer) │
        │          ↓                                  │
        │  품질 모니터링 · 개선 (양쪽 공동)             │
        │          ↓                                  │
        │     다음 사이클 ←──────────────────────┐    │
        └─────────────────────────────────────────┘   │
```

---

## KPI 체계

### Data Platform Engineer 책임 (플랫폼 안정성)

| 지표 | Phase 3 목표 | Phase 5 목표 |
|------|------------|------------|
| 파이프라인 성공률 (7일) | ≥ 97% | ≥ 99% |
| Freshness SLA 준수율 | ≥ 90% | ≥ 95% |
| 데이터 품질 테스트 통과율 | ≥ 95% | ≥ 99% |
| Shared Tool 가용성 | ≥ 99% | ≥ 99.9% |
| 메타데이터 완성도 (마트) | ≥ 80% | 100% |

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
| "데이터 팀에 직접 문의" 건수 | 분기 -30% |

---

## 요약: 역할 한눈에 보기

```
┌────────────────────────────────────────────────────────────────────┐
│  PM Lead                                                           │
│  What: 생태계 전략 · Agent 개발 우선순위 · 두 팀 조율             │
│  Output: 로드맵, KPI 리포트, 분기별 확장 계획                      │
├────────────────────────────────────────────────────────────────────┤
│  Data Platform Engineer                                                     │
│  What: 플랫폼이 작동하는 생태계 전체 (LAYER 0~2)                  │
│  Output: 안정적인 데이터, 신뢰할 수 있는 Tool, 배포 인프라          │
│  핵심 질문: "Agent가 믿을 수 있는 환경에서 동작하는가?"            │
├────────────────────────────────────────────────────────────────────┤
│  AI DataOps Engineer                                                  │
│  What: 사용자 문제를 해결하는 개별 Agent (LAYER 3)                │
│  Output: 동작하는 Agent, instruction.md, 사용자 만족도             │
│  핵심 질문: "Agent가 사용자의 질문에 정확하게 답하는가?"           │
└────────────────────────────────────────────────────────────────────┘
```
