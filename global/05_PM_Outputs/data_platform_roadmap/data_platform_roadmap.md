# 데이터 통합 플랫폼 운영 개선 로드맵

## 개요

Data Contract → Data Lineage → Data Observability 조합을 핵심 축으로,
점진적으로 거버넌스와 운영 성숙도를 높여나가는 단계별 로드맵.

각 Phase는 이전 Phase의 결과물 위에 쌓이는 구조로 설계되어
되돌아가지 않고 확장만 하면 되도록 순서를 배치하였다.

---

## Phase 0 — 현황 진단 (Before Start)

> 아무것도 세팅하기 전에 현재 상태를 정량적으로 파악한다.
> 이 단계를 건너뛰면 나중에 "얼마나 개선되었는가"를 측정할 수 없다.

### 목표
- 플랫폼의 현재 상태를 객관적으로 기록
- 가장 큰 고통 지점(Pain Point) 식별
- Phase별 우선순위 근거 확보

### 체크리스트

#### 데이터 흐름 파악
- [ ] 현재 운영 중인 파이프라인 목록 작성 (소스 → 목적지)
- [ ] 각 파이프라인의 실행 주기, 담당자, SLA 유무 확인
- [ ] 파이프라인 간 의존성 수작업으로 도식화

#### 장애 이력 분석
- [ ] 최근 3~6개월 데이터 관련 인시던트 수집
- [ ] 원인 유형 분류: 스키마 변경 / 데이터 품질 / 지연 / 인프라
- [ ] 평균 감지 시간(MTTD), 평균 복구 시간(MTTR) 계산

#### 현재 도구 스택 정리
- [ ] 사용 중인 오케스트레이터, 스토리지, 변환 도구 목록화
- [ ] 메타데이터가 저장·공유되는 방식 (문서? Wiki? 구전?)
- [ ] 데이터 품질 검증이 있다면 어디서 어떻게 하는지 기록

### 산출물
- 현황 진단 보고서 (파이프라인 목록, 인시던트 분석, 도구 스택)
- 개선 우선순위 매트릭스 (영향도 × 구현 난이도)

---

## Phase 1 — Data Contract 수립 (기반 다지기)

> **기간 목표: 2~4주**
>
> "데이터를 누가, 어떤 형태로, 어떤 조건으로 제공하는가"를 명문화한다.
> 이후 모든 품질 검증과 Lineage 추적의 기준이 되는 단계.

### 핵심 개념

Data Contract는 **데이터 생산자(Producer)와 소비자(Consumer) 사이의 계약서**다.
포함 요소:
- 스키마 정의 (필드명, 타입, Nullable 여부)
- 비즈니스 의미 (각 필드가 뜻하는 것)
- SLA (언제까지 데이터가 준비되어야 하는가)
- 품질 기대치 (Null 허용 비율, 범위 등)
- 변경 프로세스 (스키마 변경 시 사전 공지 방법)

### Step 1-1: 템플릿 설계

조직에 맞는 Contract 템플릿을 먼저 만든다.
YAML 또는 JSON 형식을 권장 (코드 리뷰 프로세스에 포함 가능).

```yaml
# data_contract_example.yaml
contract:
  id: orders_v1
  version: 1.0.0
  owner: data-platform-team
  domain: commerce

  dataset:
    name: orders
    description: "결제 완료된 주문 데이터"
    update_frequency: hourly
    sla:
      freshness_minutes: 30  # 매 시각 30분 이내 적재 완료

  schema:
    - name: order_id
      type: STRING
      nullable: false
      description: "주문 고유 식별자"
      pii: false

    - name: customer_id
      type: STRING
      nullable: false
      description: "주문한 고객 ID"
      pii: true
      masking: hash

    - name: total_amount
      type: DECIMAL(18,2)
      nullable: false
      description: "주문 총액 (KRW)"
      constraints:
        min: 0

  quality_rules:
    - rule: no_duplicate_order_id
      type: uniqueness
      column: order_id
    - rule: amount_not_negative
      type: range
      column: total_amount
      min: 0

  change_policy:
    backward_compatible_changes: "즉시 적용 가능"
    breaking_changes: "소비자 팀에 최소 2주 전 사전 공지 필수"
```

### Step 1-2: 파일럿 파이프라인 선정

- 전체 파이프라인 중 **가장 많이 소비되는 데이터셋 3~5개** 선정
- 해당 데이터셋의 생산자 팀과 소비자 팀을 한 자리에 모아 Contract 초안 작성
- "현재 암묵적으로 알고 있던 것"을 문서화하는 것이 핵심

### Step 1-3: 저장소 구성

```
data-contracts/
├── README.md               # Contract 작성 가이드
├── templates/
│   └── contract_template.yaml
├── domains/
│   ├── commerce/
│   │   ├── orders_v1.yaml
│   │   └── products_v1.yaml
│   └── marketing/
│       └── events_v1.yaml
└── CHANGELOG.md            # Contract 변경 이력
```

- Git 저장소로 관리 (버전 관리 + PR 리뷰 프로세스 자연스럽게 적용)
- Contract 변경 시 PR → 생산자·소비자 팀 리뷰 → 머지 프로세스 정립

### Step 1-4: 자동 검증 연결 (가볍게)

파이프라인 실행 시 Contract의 스키마와 실제 데이터를 자동 비교하는 최소한의 검증 추가.

```python
# 예: Great Expectations 또는 커스텀 검증
def validate_against_contract(df, contract_path):
    contract = load_yaml(contract_path)
    for field in contract['schema']:
        assert field['name'] in df.columns, f"Missing column: {field['name']}"
        if not field['nullable']:
            assert df[field['name']].notnull().all(), f"Null found in {field['name']}"
```

### 완료 기준 (Definition of Done)
- [ ] Contract 템플릿 확정 및 저장소 생성
- [ ] 파일럿 데이터셋 3개 이상 Contract 작성 완료
- [ ] Contract 변경 시 PR 리뷰 프로세스 운영 시작
- [ ] 파이프라인 실행 시 스키마 자동 검증 1개 이상 연결

---

## Phase 2 — Data Lineage 구축 (가시성 확보)

> **기간 목표: 3~5주**
>
> "데이터가 어디서 와서 어디로 흘러가는가"를 자동으로 추적한다.
> Phase 1에서 정의한 Contract를 Lineage 그래프의 노드 메타데이터로 활용한다.

### 핵심 개념

Lineage는 **데이터의 혈통(血統)** 이다. 이를 통해:
- 특정 필드의 원천 시스템 역추적 가능
- 상류(Upstream) 장애가 하류(Downstream)에 미치는 영향 범위 즉시 파악
- 스키마 변경 전 영향받는 소비자 사전 식별

### Step 2-1: Lineage 수집 방식 결정

| 방식 | 장점 | 단점 | 적합한 상황 |
|------|------|------|------------|
| **파이프라인 코드 파싱** | 정확도 높음 | 구현 비용 높음 | dbt 등 선언적 변환 사용 시 |
| **런타임 훅 삽입** | 실제 실행 기준 수집 | 오케스트레이터 의존 | Airflow, Prefect 등 사용 시 |
| **OpenLineage 표준 채택** | 벤더 중립, 생태계 넓음 | 초기 세팅 필요 | 장기적으로 권장 |
| **수동 메타데이터 입력** | 빠른 시작 | 유지보수 어려움 | 파일럿 단계에서만 |

**권장: OpenLineage + Marquez(오픈소스) 또는 DataHub 조합**

### Step 2-2: Lineage 수집 연결

#### Airflow 사용 시
```python
# OpenLineage Airflow Provider 설치
pip install openlineage-airflow

# airflow.cfg 또는 환경변수 설정
OPENLINEAGE_URL=http://marquez:5000
OPENLINEAGE_NAMESPACE=production
```

#### dbt 사용 시
```yaml
# profiles.yml에 OpenLineage 설정
# dbt run 시 자동으로 Lineage 이벤트 발송
```

#### 커스텀 파이프라인 (Python)
```python
from openlineage.client import OpenLineageClient
from openlineage.client.run import RunEvent, RunState, Run, Job

client = OpenLineageClient(url="http://marquez:5000")

# 파이프라인 시작 시
client.emit(RunEvent(
    eventType=RunState.START,
    run=Run(runId="..."),
    job=Job(namespace="commerce", name="orders_etl"),
    inputs=[Dataset(namespace="mysql", name="raw_orders")],
    outputs=[Dataset(namespace="bigquery", name="orders_silver")]
))
```

### Step 2-3: Lineage 그래프 보강

자동 수집만으로는 부족한 영역을 보완한다.

- **Contract 메타데이터 연결**: Phase 1에서 작성한 Contract의 owner, SLA, 품질 규칙을 Lineage 노드에 첨부
- **컬럼 수준 Lineage**: 가능한 경우 테이블 수준에서 컬럼 수준으로 심화
- **외부 시스템 포함**: BI 도구(Looker, Tableau), ML 모델 등 최종 소비 지점까지 포함

### Step 2-4: 영향 분석 프로세스 정립

```
스키마 변경 요청 발생
        ↓
Lineage 그래프에서 해당 테이블의 Downstream 조회
        ↓
영향받는 파이프라인 / 대시보드 / 모델 목록 추출
        ↓
각 소비자 팀에 사전 공지 (Contract의 change_policy 기준)
        ↓
변경 적용 → Lineage 자동 업데이트 확인
```

### 완료 기준 (Definition of Done)
- [ ] Lineage 수집 도구 선정 및 운영 환경 배포
- [ ] 핵심 파이프라인 80% 이상 Lineage 자동 수집
- [ ] Contract 메타데이터와 Lineage 노드 연결
- [ ] 스키마 변경 시 영향 분석 프로세스 1회 이상 실제 적용

---

## Phase 3 — Data Observability 구축 (이상 감지 자동화)

> **기간 목표: 4~6주**
>
> "데이터에 문제가 생겼을 때 사람보다 먼저 알아챈다"를 목표로 한다.
> Phase 1의 Contract가 기대값 기준이 되고, Phase 2의 Lineage가 영향 범위 파악에 쓰인다.

### 핵심 개념

Observability는 **외부 증상만 보고 내부 상태를 추론할 수 있는 능력**이다.
데이터 관점에서는 5가지 축으로 측정한다:

| 축 | 의미 | 예시 지표 |
|----|------|----------|
| **Freshness** | 데이터가 얼마나 최신인가 | 마지막 업데이트 시각 |
| **Volume** | 데이터 양이 정상 범위인가 | 일별 레코드 수 이상 감지 |
| **Schema** | 스키마가 변경되었는가 | 컬럼 추가/삭제/타입 변경 |
| **Distribution** | 값의 분포가 정상인가 | Null 비율, 평균값 급변 |
| **Lineage** | 상류 데이터가 정상적으로 흘러오는가 | 상류 파이프라인 지연 감지 |

### Step 3-1: 기본 메트릭 수집 파이프라인 구성

```python
# 예: 매 파이프라인 실행 후 메트릭 수집
class DataMetricsCollector:

    def collect(self, df, table_name: str, run_time: datetime):
        return {
            "table": table_name,
            "run_time": run_time,
            "row_count": len(df),
            "null_rates": {
                col: df[col].isnull().mean()
                for col in df.columns
            },
            "schema": {
                col: str(dtype)
                for col, dtype in df.dtypes.items()
            }
        }
```

수집된 메트릭은 전용 테이블(metrics store)에 시계열로 저장한다.

### Step 3-2: 이상 감지 규칙 구성

#### 정적 규칙 (Contract 기반)
Phase 1에서 정의한 품질 규칙을 모니터링 형태로 전환.

```yaml
# contract의 quality_rules를 모니터링 알람으로 변환
monitors:
  - name: orders_null_check
    table: orders
    column: order_id
    type: null_rate
    threshold: 0.0        # 허용 Null 비율 0%
    alert_channel: "#data-alerts"

  - name: orders_freshness
    table: orders
    type: freshness
    max_delay_minutes: 30  # SLA에서 가져온 값
    alert_channel: "#data-alerts"
```

#### 동적 규칙 (통계 기반 이상 감지)
과거 데이터를 학습해 정상 범위를 자동 설정.

```python
def detect_volume_anomaly(current_count, historical_counts):
    mean = statistics.mean(historical_counts[-30:])  # 최근 30일 평균
    std  = statistics.stdev(historical_counts[-30:])
    z_score = (current_count - mean) / std

    if abs(z_score) > 3:  # 3 시그마 이상 벗어나면 이상
        return Alert(
            severity="WARNING",
            message=f"Volume anomaly: {current_count} (expected ~{mean:.0f})"
        )
```

### Step 3-3: 알람 및 인시던트 연동

```
이상 감지 발생
      ↓
심각도 분류 (INFO / WARNING / CRITICAL)
      ↓
Slack / PagerDuty 알람 발송
      ↓
알람 메시지에 Lineage 링크 포함 (Phase 2 활용)
      ↓
    ┌─────────────────────────────┐
    │ 어떤 테이블에서 이상 발생    │
    │ 상류 파이프라인: orders_etl │
    │ 영향 받는 하류: 3개 대시보드 │
    │ Contract SLA: 30분          │
    │ 현재 지연: 47분             │
    └─────────────────────────────┘
```

알람은 **진단에 필요한 컨텍스트를 한 메시지에** 담아야 한다.
"orders 테이블에 문제"만 알리는 알람은 쓸모없다.

### Step 3-4: 대시보드 구성

운영팀이 데이터 플랫폼 상태를 한눈에 볼 수 있는 대시보드.

```
┌────────────────────────────────────────────────────┐
│           Data Platform Health Dashboard            │
├──────────────┬──────────────┬──────────────────────┤
│  Freshness   │   Volume     │   Quality Score       │
│  ✅ 92%      │  ⚠️  1 Alert │   📊 98.3%            │
├──────────────┴──────────────┴──────────────────────┤
│  Pipeline Status (Last 24h)                         │
│  orders_etl      ████████████████░░  95% success   │
│  products_sync   ████████████████████ 100% success  │
│  events_load     ███████████████░░░░  78% success   │
├─────────────────────────────────────────────────────┤
│  Active Alerts                                      │
│  🔴 events_load: Null rate 12% (threshold: 5%)      │
│     → Lineage: upstream kafka_consumer 지연 감지    │
└─────────────────────────────────────────────────────┘
```

### 완료 기준 (Definition of Done)
- [ ] 핵심 테이블 전체 Freshness / Volume 모니터링 가동
- [ ] Contract 품질 규칙 100% 모니터링 전환 완료
- [ ] 알람 → Lineage 링크 포함 자동 발송 연동
- [ ] 운영 대시보드 구성 및 팀 공유
- [ ] MTTD 측정값이 Phase 0 대비 50% 이상 감소

---

## Phase 4 — 거버넌스 레이어 추가 (확장)

> **기간 목표: 4~8주**
>
> 앞선 3개 Phase의 결과물(Contract, Lineage, Observability)을 기반으로
> 조직 수준의 거버넌스 체계를 세운다.

### Step 4-1: Data Catalog 도입

Lineage와 Contract 정보를 검색 가능한 카탈로그로 통합.

- **오픈소스**: DataHub, OpenMetadata
- **상용**: Atlan, Alation, Collibra

카탈로그가 있으면:
- 개발자가 "주문 데이터 어디 있어요?" 를 스스로 찾을 수 있다
- 새 파이프라인 개발 전 기존 데이터셋 재사용 가능성 확인
- 데이터 자산 전체 현황 파악 가능

### Step 4-2: 접근 제어 강화

Contract에 정의된 PII 필드를 기반으로 컬럼 수준 접근 제어 적용.

```sql
-- BigQuery 예시: 역할별 컬럼 마스킹 정책
CREATE ROW ACCESS POLICY orders_pii_policy
ON orders
GRANT TO ("group:data-engineers@company.com")
FILTER USING (TRUE);  -- 전체 접근

-- 일반 분석가는 customer_id 마스킹 적용
```

### Step 4-3: Data Product화

자주 사용되는 데이터셋을 **독립적으로 배포·버전 관리 가능한 Data Product**로 격상.

```
Data Product: orders_daily_summary
├── Contract (v2.1.0)
├── Quality SLA: 99.5% 이상
├── 소유팀: Data Platform
├── 소비자: 5개 팀, 12개 파이프라인
├── 변경 이력: CHANGELOG.md
└── 배포: 매일 06:00 KST
```

### Step 4-4: 비용 거버넌스

- 파이프라인별 쿼리 비용 태깅 및 추적
- 비효율 쿼리 자동 감지 (풀스캔, 파티션 미사용 등)
- 월별 비용 리포트 자동 생성 → 팀별 배분

### 완료 기준 (Definition of Done)
- [ ] Data Catalog 운영 시작, 핵심 데이터셋 등록
- [ ] PII 필드 컬럼 수준 접근 제어 적용
- [ ] 고사용 데이터셋 3개 이상 Data Product로 전환
- [ ] 파이프라인별 비용 대시보드 운영

---

## Phase 5 — 성숙도 고도화 (지속 개선)

> **기간 목표: 지속 운영**
>
> 플랫폼이 스스로 개선 방향을 제시할 수 있는 수준으로 끌어올린다.

### 주요 이니셔티브

#### Self-serve 분석 환경
- 데이터 팀 없이도 비즈니스 팀이 안전하게 데이터를 탐색할 수 있는 환경
- Semantic Layer 도입으로 SQL 없이도 올바른 지표 조회 가능

#### 자동화된 영향 분석
- Contract 변경 PR이 올라오면 자동으로 Lineage를 조회해 영향 범위를 PR 코멘트로 첨부

#### ML 기반 이상 감지 고도화
- 계절성, 비즈니스 이벤트(세일 기간 등)를 고려한 정교한 이상 탐지 모델 도입

#### 플랫폼 성숙도 정기 측정
- 분기별 Data Management Maturity 평가
- Phase 0에서 수집한 기준값 대비 개선 추이 보고

---

## 성공 지표 (KPI) 요약

| 지표 | Phase 0 (기준) | Phase 3 목표 | Phase 5 목표 |
|------|---------------|-------------|-------------|
| 평균 장애 감지 시간 (MTTD) | 측정 | -50% | -80% |
| 데이터 품질 스코어 | 측정 | 95% 이상 | 99% 이상 |
| Contract 적용 파이프라인 비율 | 0% | 50% | 90% |
| Lineage 커버리지 | 0% | 80% | 95% |
| "데이터 어디 있어요?" 문의 건수 | 측정 | -30% | -70% |

---

## 도구 선택 참고

| 영역 | 오픈소스 (비용 절약) | 상용 (빠른 도입) |
|------|-------------------|-----------------|
| Contract 관리 | Git + 커스텀 | Atlan, Soda |
| Lineage | OpenLineage + Marquez | DataHub, Atlan |
| Observability | Great Expectations | Monte Carlo, Acceldata |
| Catalog | DataHub, OpenMetadata | Atlan, Collibra |
| Orchestration | Airflow, Prefect | Astronomer, Dagster Cloud |

---

## 핵심 원칙

1. **Contract First** — 파이프라인 코드보다 Contract를 먼저 작성한다
2. **자동화 우선** — 수동으로 유지보수해야 하는 것은 결국 낡는다
3. **알람은 맥락과 함께** — 무엇이 문제인지 + 왜 중요한지 + 어디를 보면 되는지를 한 번에
4. **점진적 적용** — 완벽한 설계를 기다리지 말고, 파일럿 → 확장 패턴을 반복
5. **측정이 없으면 개선도 없다** — Phase 0의 기준값을 반드시 수집한다
