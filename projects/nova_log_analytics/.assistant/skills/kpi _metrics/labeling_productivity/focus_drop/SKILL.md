# Focus Drop KPI Monitoring Skill

> Labeler 작업 집중도 저하(Focus Drop)를 KPI로서 지속 모니터링하고, 생산성 산출 시 idle 시간을 차감할 수 있도록 연계하는 통합 운영 가이드

---

## 1. 개요

### 1.1 목적

Labeler의 작업 세션에서 **작업 집중도 저하 신호**를 분포 기반으로 탐지하고, 일일 KPI로 집계하여 지속적으로 모니터링한다. 추가로, 생산성 분석 시 Focus Drop에서 판정된 idle 시간을 Task 순소요시간(net working time) 계산에 연결할 수 있도록 한다.

### 1.2 핵심 원칙

- **집중도 측정이 아닌 저하 탐지**: 심리적 몰입 상태를 측정하지 않고, 정상 분포 대비 이탈 신호를 탐지한다
- **분포 기반 percentile 체계**: 절대 임계값이 아닌 Labeler 정상군 분포에서 경계를 산출한다
- **기준선 안정성**: 판정 기준(2차 percentile)은 당일 데이터가 아닌 안정 구간(rolling window)에서 사전 산출하여 고정한다
- **반복성 중심 판정**: 개별 gap 하나가 아닌, 긴 gap의 반복 발생 패턴으로 판정한다
- **3단계 심각도 (배타적)**: light → heavy → idle 단계로 구분하며, 최고 레벨 우선 적용한다
- **생산성 연계 가능성**: idle gap의 발생 횟수뿐 아니라 지속 시간(`idle_gap_duration_sec`)을 저장하여 Task 순소요시간에서 차감 가능하도록 설계한다

### 1.3 적용 대상

- **기본 모드**: Labeler (Reviewer/Manager 제외 — KPI 기준선 보호)
- **확장 모드**: Reviewer 전용 또는 Labeler + Reviewer 통합 모드 지원 가능 (§16 참조)
- **Feature**: OD, LD, RMD (통합 기준, 필요 시 feature별 분리)
- **분석 단위**: 개별 gap → 세션 → 사용자 일 단위 → Task idle rollup

### 1.4 관련 문서

| 문서 | 역할 |
|------|------|
| `labeler_focus_drop_concept_design.md` | v1.0 개념 설계 |
| `labeler_focus_drop_metric_design.md` | v1.0 메트릭 구조 |
| `productivity_concept_design.md` | 생산성 지표 및 Task 순소요시간 연계 |

---

## 2. 데이터 소스

### 2.1 원시 테이블

```
sv_nova_dev_an2_catalog.raw.raw_labelit__workspace_command       -- 이벤트 로그 (핵심)
sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_tasks               -- task 메타
sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_assignments         -- assignment 메타 (role 식별)
sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_annotation_policies -- feature 식별
sv_nova_dev_an2_catalog.raw.raw_labelit__company                 -- 회사 필터
```

> Focus Drop 파이프라인은 staging layer를 거치지 않고 raw 테이블을 직접 참조한다 (CDC dedup 패턴 §2.5 적용). 이벤트 시계열 분석 특성상 staging 집계가 불필요하기 때문이다.

### 2.2 핵심 필드 파싱

```sql
-- workspace_command에서 추출
c.`_raw`:userId::STRING       AS user_id,
c.`_raw`:sessionId::STRING    AS session_id,
c.`_raw`:taskId::STRING       AS task_id,
c.`_raw`:createdAt::TIMESTAMP AS event_time,
c.`_raw`:commandType::STRING  AS command_type

-- gen2_assignments에서 추출 (role 필터용)
LOWER(a.`_raw`:role::STRING)  AS user_role
```

### 2.3 조인 관계

```
command._raw:taskId → task._id
task._raw:assignmentId → assignment._id        (★ role 식별 경로)
task._raw:policyId → annotation_policy._id     (feature 식별)
task._raw:companyId → company._id
```

### 2.4 주의사항

- `_is_deleted = false` 인 레코드만 분석 대상
- `object_id`는 task 간 중복 가능 → 반드시 `task_id`와 함께 사용
- `diff_sec <= 0` (타임스탬프 역전) 제외
- **기본 KPI 파이프라인에서는 role 필터를 선행 적용해야 함** — 미적용 시 기준선 오염
- 단, **생산성 연계용 idle rollup**은 Labeler 전용/Reviewer 전용/통합(all_roles) 모드로 별도 운용 가능 (§16)

### 2.5 CDC dedup 패턴 (필수)

raw 테이블은 CDC 적재 구조로 동일 `_id`에 여러 버전 레코드가 존재할 수 있다. 모든 raw 참조는 `_ingested_at` 기준 최신 레코드만 선택하는 dedup CTE를 거쳐야 한다.

```sql
WITH latest_commands AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__workspace_command`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
)
```

세 raw 테이블(`workspace_command`, `gen2_tasks`, `gen2_assignments`) 모두 동일 패턴을 적용한다. dedup 미적용 시 동일 이벤트가 여러 번 카운트되어 percentile/세션 메트릭이 왜곡된다.

### 2.6 시간 기준 — KST 일자 변환

`createdAt`은 UTC TIMESTAMP로 저장된다. 분석 단위가 KST 영업일이므로 다음 변환을 거친 후 `analysis_date`/`rolling_days` 필터에 적용한다.

```sql
CAST(
  CONVERT_TIMEZONE('UTC', 'Asia/Seoul', c.`_raw`:createdAt::TIMESTAMP) AS DATE
) = DATE '${analysis_date}'
```

미적용 시 KST 자정 인접 이벤트(UTC 15시–24시 = KST 0시–9시)가 잘못된 일자로 분류되어 세션이 분절될 수 있다.

---

## 3. 세션 정의

### 3.1 세션 키

```
session_key = (user_id, session_id, task_id)
```

### 3.2 세션 유효성 조건

분석 대상 세션은 다음 **3개 조건을 모두** 충족해야 한다.

| 파라미터 | 권장 초기값 | 설명 | SQL 적용 위치 |
|----------|-----------|------|--------------|
| `min_event_count` | 10 | 세션 내 최소 이벤트 수 | HAVING (gap 수 + 1 ≥ 값) |
| `min_session_duration_sec` | 60 | 세션 최소 지속 시간(초) | HAVING (MAX - MIN ≥ 값) |
| `min_gap_count` | 5 | 분석 대상 최소 gap 수 (zero-inflation 방지) | HAVING COUNT(*) ≥ 값 |

### 3.3 diff_sec 산출

```sql
UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
  LAG(event_time) OVER (
    PARTITION BY user_id, session_id, task_id
    ORDER BY event_time
  )
) AS diff_sec
```

---

## 4. 메트릭 체계

### 4.1 지표 계층 흐름

```
[1차 percentile]  gap_p75 / gap_p90 / gap_p95 (gap_p99: 참고 진단용)
        ↓ 각 gap을 severity 구간으로 분류 (idle ≥ 180s 고정)
[세션 지표]       light_gap_count / heavy_gap_count / idle_gap_count
                  light_gap_ratio / heavy_gap_ratio / idle_gap_ratio
                  idle_gap_duration_sec
        ↓ 기준선 테이블(rolling baseline)에서 2차 percentile 조회
[세션 판정]       is_light_session / is_heavy_session / is_idle_session
                  → focus_drop_level (배타적: idle > heavy > light > normal)
        ↓ 사용자 일 단위 집계 + Task 단위 rollup
[사용자 KPI]      light_session_count / heavy_session_count / idle_gap_total
[Task rollup]     idle_gap_total / idle_gap_duration_sec / contributing_sessions
        ↓ 생산성 지표와 조인
[생산성 연계]     gross_task_hours - task_total_idle_sec = net_task_hours
```

### 4.2 gap 구간 정의

| 구간 | 조건 | 용도 |
|------|------|------|
| 정상 | `diff_sec <= gap_p75` | 정상 작업 흐름 |
| observation | `gap_p75 < diff_sec <= gap_p90` | 추세 관찰 보조 (판정 미사용) |
| light | `gap_p90 < diff_sec <= gap_p95` | light_gap_count 산출 |
| heavy | `gap_p95 < diff_sec < 180` | heavy_gap_count 산출 |
| idle | `diff_sec >= 180` | idle_gap_count 및 idle_gap_duration_sec 산출 (고정 임계값 3분) |

### 4.3 세션 핵심 메트릭

| 메트릭 | 역할 | 비고 |
|--------|------|------|
| `light_gap_count` | 핵심 판정 | count 중심 |
| `heavy_gap_count` | 핵심 판정 | count 중심 |
| `idle_gap_count` | 핵심 판정 | count 중심 |
| `idle_gap_duration_sec` | 생산성 연계 | `SUM(diff_sec WHERE gap_severity='idle')`, 판정 미사용 |
| `light_gap_ratio` | 보조 보정 | 세션 길이 차이 보정 |
| `heavy_gap_ratio` | 보조 보정 | 세션 길이 차이 보정 |
| `idle_gap_ratio` | 보조 보정 | 세션 길이 차이 보정 |
| `observation_gap_count` | 추세 관찰 | 판정 미사용 |
| `session_avg_gap` | 참고 진단 | 판정 미사용 |

### 4.4 사용자 일 단위 메트릭

| 메트릭 | 역할 | 집계 범위 |
|--------|------|----------|
| `light_session_count` | 핵심 반복성 | `is_light_session = TRUE` 세션 수 |
| `heavy_session_count` | 핵심 반복성 | `is_heavy_session = TRUE` 세션 수 |
| `idle_gap_total` | 핵심 누적량 | **모든 세션**의 idle_gap_count 합산 (세션 판정 무관) |
| `idle_gap_duration_total_sec` | 생산성 보조 | **모든 세션**의 idle_gap_duration_sec 합산 (선택 집계) |

> **설계 의도 — `idle_gap_total`**: 세션 레벨 판정(`is_idle_session`)과 무관하게, 하루 전체에 걸쳐 발생한 idle gap(≥ 3분)의 절대 누적량을 측정한다. 이는 개별 세션에서는 session_idle_count_p99를 초과하지 못하더라도, 다수 세션에 걸쳐 이탈이 산재하는 패턴을 포착하기 위함이다.

> **설계 의도 — `idle_gap_duration_total_sec`**: 생산성 지표와 연결할 때는 idle gap의 **발생 횟수**보다 **실제 차감 시간(초)** 이 더 중요하다. 따라서 KPI 본체는 count 중심으로 유지하되, 별도 rollup에서 duration 합산값을 보조적으로 유지한다.

---

## 5. 판정 기준

### 5.1 세션 판정

| 레벨 | 주판정 | 보조판정 (오탐 시 전환) | 최소 조건 | 상태 |
|------|--------|---------|----------|------|
| light | `light_gap_count > session_light_count_p90` | `light_gap_ratio > session_light_ratio_p90` | `light_gap_count > 0` | ratio 현재 비활성 (§7.4 주석). 오탐률 > 20% 시 AND 활성화 |
| heavy | `heavy_gap_count > session_heavy_count_p95` | `heavy_gap_ratio > session_heavy_ratio_p95` | `heavy_gap_count > 0` | 동일 |
| idle | `idle_gap_count > session_idle_count_p99` | `idle_gap_ratio > session_idle_ratio_p99` | `idle_gap_count > 0` | 동일 |

### 5.2 배타성 규칙

판정 레벨은 **최고 심각도 우선** 원칙으로 배타적으로 적용한다.

```
focus_drop_level = CASE
  WHEN is_idle_session  THEN 'idle'
  WHEN is_heavy_session THEN 'heavy'
  WHEN is_light_session THEN 'light'
  ELSE 'normal'
END
```

- 한 세션/유저는 **단일 focus_drop_level**만 가짐
- 대시보드 집계 시 중복 카운트 방지
- 알림은 최고 레벨 기준으로만 발송

### 5.3 사용자 일 단위 판정

| 레벨 | 조건 | 최소 조건 |
|------|------|----------|
| light 후보 | `light_session_count > user_light_session_count_p90` | `> 0` |
| heavy 후보 | `heavy_session_count > user_heavy_session_count_p95` | `> 0` |
| idle 후보 | `idle_gap_total > user_idle_gap_total_p99` | `> 0` |

사용자 레벨에도 동일한 배타성 규칙을 적용한다 (`user_focus_drop_level`).

> **차원 구분**: `heavy`은 세션 반복성(heavy 세션 수) 기준이고, `idle`은 gap 누적량(idle gap 절대 합산) 기준이다. 두 지표는 서로 다른 차원을 측정하므로, heavy이 낮더라도 idle이 높을 수 있고 그 반대도 가능하다.

### 5.4 기준선 산출 원칙

> **중요**: 세션/유저 판정에 사용하는 2차 percentile 기준은 **당일 데이터에서 산출하지 않는다**.

| 기준선 | 산출 방법 | 갱신 주기 |
|--------|----------|----------|
| gap percentile (1차) | Labeler 직전 90일 로그의 diff_sec 분포 (최소 10,000 gap 표본 필수) | 분기 1회 또는 드리프트 시 |
| session threshold (2차) | 직전 30일 세션 메트릭의 percentile | 주 1회 rolling |
| user threshold (2차) | 직전 30일 유저 KPI의 percentile | 주 1회 rolling |

### 5.5 판정 제외 지표

- `session_avg_gap`, `user_day_avg_gap` — 참고용 진단만
- `idle_gap_duration_sec` — 생산성 차감용, focus_drop 판정에는 직접 미사용
- 단일 gap 1회 발생만으로의 판정
- 절대 count 고정값만을 사용한 판정

---

## 6. 파이프라인 구조

### 6.1 실행 순서

```
[기준선 산출 — 분기/주 단위]

focus_drop__gap_percentiles.sql          → analytics.focus_drop_gap_thresholds
                                            (1차 percentile: gap 구간 경계)

[일 단위 배치 — 매일 04:00 UTC]

focus_drop__session_metrics.sql          → analytics.focus_drop_session_metrics
        ↓                                   (세션별 count/ratio/duration 산출)
focus_drop__task_idle_rollup.sql         → analytics.focus_drop_task_idle_rollup
        ↓                                   (Task별 idle 누적 횟수/초수 산출)
focus_drop__session_tags.sql             → analytics.focus_drop_session_tags
        ↓                                   (기준선 참조 → 세션 판정)
focus_drop__user_day_kpi.sql             → analytics.focus_drop_user_day_kpi
                                            (기준선 참조 → 유저 판정)

[기준선 갱신 — 주 1회 월요일 03:00 UTC, session_metrics/user_day_kpi 누적 결과를 입력으로 사용]

focus_drop__session_thresholds.sql       → analytics.focus_drop_session_thresholds
                                            (직전 30일 session_metrics 기반)
focus_drop__user_thresholds.sql          → analytics.focus_drop_user_thresholds
                                            (직전 30일 user_day_kpi 기반)
```

> **의존성 방향**: session_thresholds / user_thresholds는 session_metrics / user_day_kpi의 **누적 산출물**(직전 30일분)을 입력으로 사용한다. 반대로 session_tags / user_day_kpi는 session_thresholds / user_thresholds의 **최신 기준선**을 참조한다. `task_idle_rollup`은 session_metrics의 당일 산출물을 입력으로 사용하며 기준선에는 의존하지 않는다. 따라서 정상 운영 시 실행 순서는 `session_metrics → task_idle_rollup → session_tags → user_day_kpi` (일 배치) / `session_thresholds → user_thresholds` (주 배치, session_metrics / user_day_kpi 결과 반영)이다.

### 6.2 실행 스케줄

| 노트북 | 실행 주기 | 트리거 조건 |
|--------|----------|------------|
| `gap_percentiles` | 분기 1회 또는 분포 변화 시 | 기준값 드리프트 ±20% 감지 |
| `session_thresholds`, `user_thresholds` | 주 1회 (월요일 03:00 UTC) | 직전 30일 rolling window 갱신 |
| `session_metrics` → `task_idle_rollup` → `session_tags` → `user_day_kpi` | 일 단위 배치 | 매일 04:00 UTC (전일 데이터 대상) |

### 6.3 Delta 테이블

> 초기 생성 DDL: `.sql/focus_drop__ddl.sql` (7개 테이블, `PARTITIONED BY (analysis_date)` + `columnMapping.mode = 'name'` 포함)

| 테이블 | 스키마 | 갱신 전략 |
|--------|--------|----------|
| `analytics.focus_drop_gap_thresholds` | `version INT, computed_at TIMESTAMP, feature_scope STRING, sample_count BIGINT, gap_p50 DOUBLE, gap_p75 DOUBLE, gap_p90 DOUBLE, gap_p95 DOUBLE, gap_p99 DOUBLE` (gap_p99는 참고 진단용) | 버전업 시 INSERT |
| `analytics.focus_drop_session_thresholds` | `version INT, computed_at TIMESTAMP, is_bootstrap BOOLEAN, window_start DATE, window_end DATE, session_light_count_p90 DOUBLE, session_heavy_count_p95 DOUBLE, session_idle_count_p99 DOUBLE, session_light_ratio_p90 DOUBLE, session_heavy_ratio_p95 DOUBLE, session_idle_ratio_p99 DOUBLE` | 주 1회 INSERT |
| `analytics.focus_drop_user_thresholds` | `version INT, computed_at TIMESTAMP, is_bootstrap BOOLEAN, window_start DATE, window_end DATE, user_light_session_count_p90 DOUBLE, user_heavy_session_count_p95 DOUBLE, user_idle_gap_total_p99 DOUBLE` | 주 1회 INSERT |
| `analytics.focus_drop_session_metrics` | `analysis_date DATE, user_id STRING, session_id STRING, task_id STRING, total_gaps INT, observation_gap_count INT, light_gap_count INT, heavy_gap_count INT, idle_gap_count INT, idle_gap_duration_sec DOUBLE, light_gap_ratio DOUBLE, heavy_gap_ratio DOUBLE, idle_gap_ratio DOUBLE, session_avg_gap DOUBLE` | INSERT INTO ... REPLACE WHERE analysis_date |
| `analytics.focus_drop_task_idle_rollup` | `analysis_date DATE, task_id STRING, role_scope STRING, role_group STRING, contributing_sessions INT, contributing_users INT, idle_gap_total INT, idle_gap_duration_sec DOUBLE` | INSERT INTO ... REPLACE WHERE analysis_date |
| `analytics.focus_drop_session_tags` | `analysis_date DATE, user_id STRING, session_id STRING, task_id STRING, light_gap_count INT, heavy_gap_count INT, idle_gap_count INT, is_light_session BOOLEAN, is_heavy_session BOOLEAN, is_idle_session BOOLEAN, focus_drop_level STRING` | INSERT INTO ... REPLACE WHERE analysis_date |
| `analytics.focus_drop_user_day_kpi` | `analysis_date DATE, user_id STRING, light_session_count INT, heavy_session_count INT, idle_gap_total INT, total_sessions INT, is_light_user BOOLEAN, is_heavy_user BOOLEAN, is_idle_user BOOLEAN, user_focus_drop_level STRING` | INSERT INTO ... REPLACE WHERE analysis_date |

### 6.4 Databricks Job 구성

파이프라인은 **배포 단계(Phase)** 에 따라 Job 구성이 달라진다.

#### Phase A Job — Warm-up 전용 일 배치 (Day 1~6)

기준선 테이블이 없으므로 `session_metrics`와 `task_idle_rollup`만 실행. `session_tags` / `user_day_kpi`는 포함하지 않는다.

```yaml
# Job: focus_drop_warmup_daily  (Phase A 전용 — Day 7 이후 아래 steady-state job으로 교체)
# Schedule: 0 0 4 * * ?  (매일 04:00 UTC)
tasks:
  - task_key: session_metrics
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__session_metrics
      base_parameters:
        analysis_date: "{{ds}}"       # Databricks 날짜 변수: 전일 기준

  - task_key: task_idle_rollup
    depends_on:
      - task_key: session_metrics
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__task_idle_rollup
      base_parameters:
        analysis_date: "{{ds}}"
```

#### Phase B 수동 실행 순서 (Day 7 — 1회성)

Job이 아닌 수동 순차 실행. §12.4 Bootstrap 절차 참조.

```
1. session_thresholds   rolling_window_days=7, is_bootstrap=TRUE
2. zero-inflation 보정  (§12.1 UPDATE SQL)
3. task_idle_rollup     analysis_date=(누락일 전체 소급)
4. session_tags         analysis_date=(누락일 전체 소급)
5. user_thresholds      수동 INSERT (§12.4 Bootstrap INSERT 참조)
6. user_day_kpi         analysis_date=(누락일 전체 소급)
7. focus_drop_daily Job 활성화 (steady-state 일 배치 진입)
```

#### Steady-state Job — 일 배치 (Day 7+)

Phase A Job을 폐기하고 아래 Job으로 교체.

```yaml
# Job: focus_drop_daily
# Schedule: 0 0 4 * * ?  (매일 04:00 UTC)
tasks:
  - task_key: session_metrics
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__session_metrics
      base_parameters:
        analysis_date: "{{ds}}"

  - task_key: task_idle_rollup
    depends_on:
      - task_key: session_metrics
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__task_idle_rollup
      base_parameters:
        analysis_date: "{{ds}}"

  - task_key: session_tags
    depends_on:
      - task_key: session_metrics
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__session_tags
      base_parameters:
        analysis_date: "{{ds}}"

  - task_key: user_day_kpi
    depends_on:
      - task_key: session_tags
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__user_day_kpi
      base_parameters:
        analysis_date: "{{ds}}"
```

#### Steady-state Job — 주 배치 (매주 월요일)

`session_thresholds`와 `user_thresholds`는 소스 테이블이 달라 독립 실행 가능 → 병렬 실행.

```yaml
# Job: focus_drop_weekly
# Schedule: 0 0 3 ? * MON  (매주 월요일 03:00 UTC — 일 배치 완료 후)
tasks:
  - task_key: session_thresholds      # focus_drop_session_metrics 참조
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__session_thresholds
      base_parameters:
        rolling_window_days: "30"
        is_bootstrap: "false"

  - task_key: user_thresholds         # focus_drop_user_day_kpi 참조 (session_thresholds 불필요)
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__user_thresholds
      base_parameters:
        rolling_window_days: "30"
        is_bootstrap: "false"
```

#### Quarterly Job — gap_percentiles (분기 1회)

분포 드리프트 여부와 무관하게 분기 정기 실행. 드리프트 감지 시 §9.2 SOP에 따라 수동 재실행 추가 가능.

```yaml
# Job: focus_drop_quarterly
# Schedule: 0 0 2 1 1,4,7,10 ?  (1월·4월·7월·10월 1일 02:00 UTC)
tasks:
  - task_key: gap_percentiles
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__gap_percentiles
      base_parameters:
        rolling_days: "90"
```

---

## 7. SQL 레퍼런스

### 7.1 gap percentile 산출 (Labeler role 필터 포함)

```sql
-- focus_drop__gap_percentiles.sql
-- 시간 기준: rolling_days는 KST 기준 영업일 (createdAt UTC → KST 변환 후 비교)
-- 표본 10,000 미달 시 HAVING으로 자동 스킵 → 기존 기준선 유지

CREATE WIDGET TEXT rolling_days DEFAULT "90";

INSERT INTO analytics.focus_drop_gap_thresholds
WITH latest_assignments AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_assignments`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
latest_tasks AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_tasks`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
latest_commands AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__workspace_command`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
labeler_commands AS (
  SELECT
    c.`_raw`:userId::STRING       AS user_id,
    c.`_raw`:sessionId::STRING    AS session_id,
    c.`_raw`:taskId::STRING       AS task_id,
    c.`_raw`:createdAt::TIMESTAMP AS event_time
  FROM latest_commands c
  INNER JOIN latest_tasks       t ON c.`_raw`:taskId::STRING = t.`_id`
  INNER JOIN latest_assignments a ON t.`_raw`:assignmentId::STRING = a.`_id`
  WHERE LOWER(a.`_raw`:role::STRING) = 'labeler'
    AND CAST(
      CONVERT_TIMEZONE('UTC', 'Asia/Seoul', c.`_raw`:createdAt::TIMESTAMP) AS DATE
    ) >= DATE_SUB(CURRENT_DATE(), ${rolling_days})
),
with_diff AS (
  SELECT *,
    UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
      LAG(event_time) OVER (PARTITION BY user_id, session_id, task_id ORDER BY event_time)
    ) AS diff_sec
  FROM labeler_commands
)
SELECT
  COALESCE((SELECT MAX(version) FROM analytics.focus_drop_gap_thresholds), 0) + 1 AS version,
  CURRENT_TIMESTAMP()        AS computed_at,
  'all_features'             AS feature_scope,
  COUNT(*)                   AS sample_count,
  PERCENTILE(diff_sec, 0.50) AS gap_p50,
  PERCENTILE(diff_sec, 0.75) AS gap_p75,
  PERCENTILE(diff_sec, 0.90) AS gap_p90,
  PERCENTILE(diff_sec, 0.95) AS gap_p95,
  PERCENTILE(diff_sec, 0.99) AS gap_p99
FROM with_diff
WHERE diff_sec IS NOT NULL AND diff_sec > 0
  AND diff_sec < 180  -- ★ Idle gap 제외: idle 구간(≥ 180s)은 고정 임계값으로 처리, percentile 분포 오염 방지
HAVING COUNT(*) >= 10000;  -- ★ §5.4 최소 표본 요건 강제 (미달 시 0행 INSERT → 기존 기준선 유지)
```

### 7.2 세션 메트릭 산출 (유효성 3조건 완전 구현)

```sql
-- focus_drop__session_metrics.sql
-- 의존성: focus_drop_gap_thresholds (gap 구간 경계 — 테이블에서 자동 로드)
-- 갱신 전략: INSERT INTO ... REPLACE WHERE analysis_date
-- 시간 기준: analysis_date는 KST 일자 (createdAt UTC → KST 변환 후 비교)

CREATE WIDGET TEXT analysis_date            DEFAULT "";
CREATE WIDGET TEXT min_gap_count            DEFAULT "5";
CREATE WIDGET TEXT min_event_count          DEFAULT "10";
CREATE WIDGET TEXT min_session_duration_sec DEFAULT "60";

INSERT INTO analytics.focus_drop_session_metrics
REPLACE WHERE analysis_date = '${analysis_date}'
WITH thresholds AS (
  -- gap 구간 경계: 위젯 없이 최신 버전 자동 참조 (gap_p99 제거: idle 경계는 고정 180s)
  SELECT gap_p75, gap_p90, gap_p95
  FROM analytics.focus_drop_gap_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_gap_thresholds)
),
latest_assignments AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_assignments`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
latest_tasks AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_tasks`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
latest_commands AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__workspace_command`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
labeler_commands AS (
  SELECT
    c.`_raw`:userId::STRING       AS user_id,
    c.`_raw`:sessionId::STRING    AS session_id,
    c.`_raw`:taskId::STRING       AS task_id,
    c.`_raw`:createdAt::TIMESTAMP AS event_time
  FROM latest_commands c
  INNER JOIN latest_tasks       t ON c.`_raw`:taskId::STRING = t.`_id`
  INNER JOIN latest_assignments a ON t.`_raw`:assignmentId::STRING = a.`_id`
  WHERE LOWER(a.`_raw`:role::STRING) = 'labeler'
    AND CAST(
      CONVERT_TIMEZONE('UTC', 'Asia/Seoul', c.`_raw`:createdAt::TIMESTAMP) AS DATE
    ) = DATE '${analysis_date}'
),
with_diff AS (
  SELECT *,
    UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
      LAG(event_time) OVER (PARTITION BY user_id, session_id, task_id ORDER BY event_time)
    ) AS diff_sec,
    UNIX_TIMESTAMP(event_time) AS event_ts_unix
  FROM labeler_commands
),
gap_classified AS (
  SELECT
    g.user_id, g.session_id, g.task_id, g.diff_sec, g.event_ts_unix,
    CASE
      WHEN g.diff_sec >= 180        THEN 'idle'       -- ★ 고정 임계값 3분
      WHEN g.diff_sec <= t.gap_p75 THEN 'normal'
      WHEN g.diff_sec <= t.gap_p90 THEN 'observation'
      WHEN g.diff_sec <= t.gap_p95 THEN 'light'
      ELSE 'heavy'                                     -- gap_p95 < diff_sec < 180
    END AS gap_severity
  FROM with_diff g
  CROSS JOIN thresholds t
  WHERE g.diff_sec IS NOT NULL AND g.diff_sec > 0
)
SELECT
  DATE '${analysis_date}'                                         AS analysis_date,
  user_id, session_id, task_id,
  COUNT(*)                                                        AS total_gaps,
  SUM(CASE WHEN gap_severity = 'observation' THEN 1 ELSE 0 END)  AS observation_gap_count,
  SUM(CASE WHEN gap_severity = 'light'       THEN 1 ELSE 0 END)  AS light_gap_count,
  SUM(CASE WHEN gap_severity = 'heavy'       THEN 1 ELSE 0 END)  AS heavy_gap_count,
  SUM(CASE WHEN gap_severity = 'idle'        THEN 1 ELSE 0 END)  AS idle_gap_count,
  SUM(CASE WHEN gap_severity = 'idle'        THEN diff_sec ELSE 0 END) AS idle_gap_duration_sec,
  ROUND(SUM(CASE WHEN gap_severity = 'light'     THEN 1 ELSE 0 END) / COUNT(*), 4) AS light_gap_ratio,
  ROUND(SUM(CASE WHEN gap_severity = 'heavy'     THEN 1 ELSE 0 END) / COUNT(*), 4) AS heavy_gap_ratio,
  ROUND(SUM(CASE WHEN gap_severity = 'idle'      THEN 1 ELSE 0 END) / COUNT(*), 4) AS idle_gap_ratio,
  AVG(diff_sec)                                                   AS session_avg_gap
FROM gap_classified
GROUP BY user_id, session_id, task_id
HAVING COUNT(*) >= ${min_gap_count}
   AND COUNT(*) + 1 >= ${min_event_count}
   AND (MAX(event_ts_unix) - MIN(event_ts_unix)) >= ${min_session_duration_sec};
```

> **gap_p75/p90/p95 자동 로드**: session_metrics SQL은 위젯 파라미터 대신 `analytics.focus_drop_gap_thresholds`의 최신 버전을 CTE로 직접 참조한다. percentile 갱신 시 별도 위젯 동기화 불필요.

### 7.3 세션 기준선 산출 (rolling 30일)

```sql
-- focus_drop__session_thresholds.sql
INSERT INTO analytics.focus_drop_session_thresholds
SELECT
  COALESCE((SELECT MAX(version) FROM analytics.focus_drop_session_thresholds), 0) + 1  AS version,
  CURRENT_TIMESTAMP()                              AS computed_at,
  FALSE                                            AS is_bootstrap,
  DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AS window_start,
  DATE_SUB(CURRENT_DATE(), 1)                      AS window_end,
  PERCENTILE(light_gap_count,   0.90)              AS session_light_count_p90,
  PERCENTILE(heavy_gap_count,   0.95)              AS session_heavy_count_p95,
  PERCENTILE(idle_gap_count,    0.99)              AS session_idle_count_p99,
  PERCENTILE(light_gap_ratio,   0.90)              AS session_light_ratio_p90,
  PERCENTILE(heavy_gap_ratio,   0.95)              AS session_heavy_ratio_p95,
  PERCENTILE(idle_gap_ratio,    0.99)              AS session_idle_ratio_p99
FROM analytics.focus_drop_session_metrics
WHERE analysis_date BETWEEN DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AND DATE_SUB(CURRENT_DATE(), 1);
-- ★ 기준 산출 기간과 판정 대상 기간이 분리됨 (당일 데이터 미포함)
```

### 7.4 세션 판정 (사전 산출 기준선 참조)

```sql
-- focus_drop__session_tags.sql
WITH thresholds AS (
  -- ★ 사전 산출된 rolling baseline 테이블에서 조회 (count + ratio 모두)
  SELECT
    session_light_count_p90, session_heavy_count_p95, session_idle_count_p99,
    session_light_ratio_p90, session_heavy_ratio_p95, session_idle_ratio_p99
  FROM analytics.focus_drop_session_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds)
)
INSERT INTO analytics.focus_drop_session_tags
REPLACE WHERE analysis_date = ${analysis_date}
SELECT
  m.analysis_date,
  m.user_id, m.session_id, m.task_id,
  m.light_gap_count, m.heavy_gap_count, m.idle_gap_count,
  -- 개별 레벨 판정 (count 단독; light 오탐률 > 20% 확인 시 ratio AND 조건 활성화)
  CASE WHEN m.light_gap_count > 0
        AND m.light_gap_count > t.session_light_count_p90
       THEN TRUE ELSE FALSE END AS is_light_session,
  CASE WHEN m.heavy_gap_count > 0
        AND m.heavy_gap_count > t.session_heavy_count_p95
       THEN TRUE ELSE FALSE END AS is_heavy_session,
  CASE WHEN m.idle_gap_count > 0
        AND m.idle_gap_count > t.session_idle_count_p99
       THEN TRUE ELSE FALSE END AS is_idle_session,
  -- ★ 배타적 최종 레벨 (idle > heavy > light > normal)
  CASE
    WHEN m.idle_gap_count > 0
         AND m.idle_gap_count > t.session_idle_count_p99    THEN 'idle'
    WHEN m.heavy_gap_count > 0
         AND m.heavy_gap_count > t.session_heavy_count_p95  THEN 'heavy'
    WHEN m.light_gap_count > 0
         AND m.light_gap_count > t.session_light_count_p90  THEN 'light'
    ELSE 'normal'
  END AS focus_drop_level
FROM analytics.focus_drop_session_metrics m
CROSS JOIN thresholds t
WHERE m.analysis_date = ${analysis_date};
-- ★ ratio 보조판정 활용: 오탐 의심 시 아래 추가 조건으로 필터링 가능
-- AND m.light_gap_ratio > t.session_light_ratio_p90
```

### 7.5 사용자 일 KPI (사전 산출 기준선 참조)

```sql
-- focus_drop__user_day_kpi.sql
WITH user_daily AS (
  SELECT
    user_id,
    analysis_date,
    SUM(CASE WHEN is_light_session THEN 1 ELSE 0 END) AS light_session_count,
    SUM(CASE WHEN is_heavy_session THEN 1 ELSE 0 END) AS heavy_session_count,
    -- ★ idle_gap_total: 세션 판정 무관, 모든 세션의 idle gap(≥ 3분) 누적 절대량
    SUM(idle_gap_count)                               AS idle_gap_total,
    COUNT(*)                                          AS total_sessions
  FROM analytics.focus_drop_session_tags
  WHERE analysis_date = ${analysis_date}
  GROUP BY user_id, analysis_date
),
user_thresholds AS (
  -- ★ 사전 산출된 rolling baseline에서 조회
  SELECT user_light_session_count_p90, user_heavy_session_count_p95, user_idle_gap_total_p99
  FROM analytics.focus_drop_user_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_user_thresholds)
)
INSERT INTO analytics.focus_drop_user_day_kpi
REPLACE WHERE analysis_date = ${analysis_date}
SELECT
  d.analysis_date,
  d.user_id,
  d.light_session_count,
  d.heavy_session_count,
  d.idle_gap_total,
  d.total_sessions,
  -- 개별 레벨 플래그
  CASE WHEN d.light_session_count > 0
        AND d.light_session_count > t.user_light_session_count_p90
       THEN TRUE ELSE FALSE END AS is_light_user,
  CASE WHEN d.heavy_session_count > 0
        AND d.heavy_session_count > t.user_heavy_session_count_p95
       THEN TRUE ELSE FALSE END AS is_heavy_user,
  CASE WHEN d.idle_gap_total > 0
        AND d.idle_gap_total > t.user_idle_gap_total_p99
       THEN TRUE ELSE FALSE END AS is_idle_user,
  -- ★ 배타적 최종 레벨 (idle > heavy > light > normal)
  CASE
    WHEN d.idle_gap_total > 0
         AND d.idle_gap_total > t.user_idle_gap_total_p99        THEN 'idle'
    WHEN d.heavy_session_count > 0
         AND d.heavy_session_count > t.user_heavy_session_count_p95 THEN 'heavy'
    WHEN d.light_session_count > 0
         AND d.light_session_count > t.user_light_session_count_p90  THEN 'light'
    ELSE 'normal'
  END AS user_focus_drop_level
FROM user_daily d
CROSS JOIN user_thresholds t;
```

### 7.6 유저 기준선 산출 (rolling 30일)

```sql
-- focus_drop__user_thresholds.sql
INSERT INTO analytics.focus_drop_user_thresholds
SELECT
  COALESCE((SELECT MAX(version) FROM analytics.focus_drop_user_thresholds), 0) + 1  AS version,
  CURRENT_TIMESTAMP()                              AS computed_at,
  FALSE                                            AS is_bootstrap,
  DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AS window_start,
  DATE_SUB(CURRENT_DATE(), 1)                      AS window_end,
  PERCENTILE(light_session_count,  0.90)          AS user_light_session_count_p90,
  PERCENTILE(heavy_session_count, 0.95)           AS user_heavy_session_count_p95,
  PERCENTILE(idle_gap_total,      0.99)           AS user_idle_gap_total_p99
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date BETWEEN DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AND DATE_SUB(CURRENT_DATE(), 1);
```

### 7.7 Task idle rollup (생산성 연계용)

```sql
-- focus_drop__task_idle_rollup.sql
INSERT INTO analytics.focus_drop_task_idle_rollup
REPLACE WHERE analysis_date = ${analysis_date}
SELECT
  analysis_date,
  task_id,
  'labeler'                        AS role_scope,
  'labeler'                        AS role_group,
  COUNT(*)                         AS contributing_sessions,
  COUNT(DISTINCT user_id)          AS contributing_users,
  SUM(idle_gap_count)              AS idle_gap_total,
  SUM(idle_gap_duration_sec)       AS idle_gap_duration_sec
FROM analytics.focus_drop_session_metrics
WHERE analysis_date = ${analysis_date}
GROUP BY analysis_date, task_id;
```

> 생산성 SQL에서는 동일 Task가 여러 날짜에 걸쳐 진행될 수 있으므로, `focus_drop_task_idle_rollup`을 `task_id` 기준으로 다시 합산하여 `task_total_idle_sec`를 산출한 후 `deliver_actionAt - start_actionAt`에서 차감한다. 상세 산식은 §16.1 참조.

---

## 8. 모니터링 대시보드

### 8.1 일일 요약 뷰

```sql
-- 일일 KPI 현황 조회 (배타적 레벨 기준 — 중복 카운트 없음)
SELECT
  analysis_date,
  COUNT(*) AS total_labelers,
  SUM(CASE WHEN user_focus_drop_level = 'light' THEN 1 ELSE 0 END) AS light_users,
  SUM(CASE WHEN user_focus_drop_level = 'heavy' THEN 1 ELSE 0 END) AS heavy_users,
  SUM(CASE WHEN user_focus_drop_level = 'idle'  THEN 1 ELSE 0 END) AS idle_users,
  ROUND(SUM(CASE WHEN user_focus_drop_level = 'light' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS light_pct,
  ROUND(SUM(CASE WHEN user_focus_drop_level = 'heavy' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS heavy_pct,
  ROUND(SUM(CASE WHEN user_focus_drop_level = 'idle'  THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS idle_pct
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date >= DATE_SUB(CURRENT_DATE(), 30)
GROUP BY analysis_date
ORDER BY analysis_date DESC;
```

### 8.2 사용자별 상세 조회

```sql
-- 특정 사용자의 최근 세션별 판정 현황
SELECT
  s.analysis_date,
  s.user_id,
  s.session_id,
  s.task_id,
  s.light_gap_count,
  s.heavy_gap_count,
  s.idle_gap_count,
  s.focus_drop_level
FROM analytics.focus_drop_session_tags s
WHERE s.user_id = ${target_user_id}
  AND s.analysis_date >= DATE_SUB(CURRENT_DATE(), 7)
ORDER BY s.analysis_date DESC, s.session_id;
```

### 8.3 추세 모니터링

```sql
-- 주간 추세: 배타적 레벨(user_focus_drop_level) 기준 사용자 비율 변화
SELECT
  DATE_TRUNC('week', analysis_date) AS week_start,
  COUNT(DISTINCT user_id) AS total_labelers,
  COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'light' THEN user_id END) AS light_users,
  COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'heavy' THEN user_id END) AS heavy_users,
  COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'idle'  THEN user_id END) AS idle_users,
  ROUND(COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'light' THEN user_id END) / COUNT(DISTINCT user_id) * 100, 1) AS light_pct,
  ROUND(COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'heavy' THEN user_id END) / COUNT(DISTINCT user_id) * 100, 1) AS heavy_pct,
  ROUND(COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'idle'  THEN user_id END) / COUNT(DISTINCT user_id) * 100, 1) AS idle_pct
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date >= DATE_SUB(CURRENT_DATE(), 90)
GROUP BY DATE_TRUNC('week', analysis_date)
ORDER BY week_start DESC;
```

---

## 9. 알림 기준

### 9.1 알림 레벨

| 레벨 | 조건 | 행동 |
|------|------|------|
| **INFO** | 당일 `user_focus_drop_level = 'light'` 존재 | 일일 리포트에 포함 |
| **WARNING** | `user_focus_drop_level = 'heavy'` 1명 이상 | 팀 리드 Slack 알림 |
| **CRITICAL** | `user_focus_drop_level = 'idle'` 존재 | 즉시 검토 요청 |
| **DRIFT** | `gap_p90/p95` 기존 대비 ±20% 변동 | percentile 재산출 트리거 |

> 배타적 레벨 적용으로, 한 유저에게 중복 알림이 발생하지 않는다.

**DRIFT 대응 SOP** (`drift_status = 'RECALCULATE'` 감지 시):

1. **담당자**: 데이터 엔지니어 (파이프라인 소유자)
2. **확인**: §9.2 드리프트 쿼리 수동 실행 → 원인 파악 (온보딩? UX 변경? 계절성?)
3. **실행**: 정상적 분포 변화로 판단되면 `gap_percentiles` 수동 재실행 → 신규 gap_thresholds INSERT
4. **후속**: `session_thresholds` / `user_thresholds`를 다음 주 배치 전에 임시 재실행하여 2차 기준선도 갱신
5. **기록**: §13 버전업 원칙에 따라 변경 사유 기록

> §9.2의 7일 윈도우는 **급격한 분포 변화의 조기 경보**를 목적으로 한다. 완만한 drift(4~5주)는 session_thresholds / user_thresholds의 주간 rolling 갱신 + 분기 정기 검토가 커버한다.

### 9.2 기준선 드리프트 감지

```sql
-- 현재 분포 vs 기준 비교 (최근 7일 — 급격한 shift 조기 경보용; 완만한 drift는 session/user_thresholds rolling이 커버)
-- ★ §7.1과 동일한 CDC dedup + KST 변환 구조
WITH latest_assignments AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_assignments`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
latest_tasks AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_tasks`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
latest_commands AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__workspace_command`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
recent_labeler_diffs AS (
  SELECT
    UNIX_TIMESTAMP(c.`_raw`:createdAt::TIMESTAMP) - UNIX_TIMESTAMP(
      LAG(c.`_raw`:createdAt::TIMESTAMP) OVER (
        PARTITION BY c.`_raw`:userId::STRING, c.`_raw`:sessionId::STRING, c.`_raw`:taskId::STRING
        ORDER BY c.`_raw`:createdAt::TIMESTAMP
      )
    ) AS diff_sec
  FROM latest_commands c
  INNER JOIN latest_tasks       t ON c.`_raw`:taskId::STRING = t.`_id`
  INNER JOIN latest_assignments a ON t.`_raw`:assignmentId::STRING = a.`_id`
  WHERE LOWER(a.`_raw`:role::STRING) = 'labeler'
    AND CAST(
      CONVERT_TIMEZONE('UTC', 'Asia/Seoul', c.`_raw`:createdAt::TIMESTAMP) AS DATE
    ) >= DATE_SUB(CURRENT_DATE(), 7)
),
current_dist AS (
  SELECT
    PERCENTILE(diff_sec, 0.90) AS current_p90,
    PERCENTILE(diff_sec, 0.95) AS current_p95,
    PERCENTILE(diff_sec, 0.99) AS current_p99
  FROM recent_labeler_diffs
  WHERE diff_sec IS NOT NULL AND diff_sec > 0
),
baseline AS (
  SELECT gap_p90, gap_p95, gap_p99
  FROM analytics.focus_drop_gap_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_gap_thresholds)
)
SELECT
  ABS(c.current_p90 - b.gap_p90) / b.gap_p90 * 100 AS drift_p90_pct,
  ABS(c.current_p95 - b.gap_p95) / b.gap_p95 * 100 AS drift_p95_pct,
  ABS(c.current_p99 - b.gap_p99) / b.gap_p99 * 100 AS drift_p99_pct,
  CASE WHEN ABS(c.current_p90 - b.gap_p90) / b.gap_p90 > 0.20
         OR ABS(c.current_p95 - b.gap_p95) / b.gap_p95 > 0.20
         OR ABS(c.current_p99 - b.gap_p99) / b.gap_p99 > 0.20
       THEN 'RECALCULATE' ELSE 'STABLE' END AS drift_status
FROM current_dist c CROSS JOIN baseline b;
```

---

## 10. 운영 해석 원칙

### 10.1 판정 ≠ 확정

- `light`/`heavy` 판정은 **검토 필요 신호**이며, 저성과 확정이 아님
- 실제 해석 시 작업 맥락, task 특성, 운영 이슈를 함께 고려

### 10.2 도메인 특성 고려

- 3D point cloud annotation에서는 시점 탐색/회전/확인 시간이 command 로그에 반영되지 않음
- 따라서 개별 long gap 하나보다 **반복 패턴**을 우선 해석
- 생산성 연계 시에도 idle 차감은 **순작업시간 근사치**이지 완전한 근태 시간 대체값이 아님

### 10.3 feature별 해석

- OD: 객체 밀도 높음 → 짧은 gap이 정상
- LD: 연속 라인 작업 → 리듬성 갭 패턴
- RMD: 넓은 영역 탐색 → 상대적으로 긴 gap 허용 가능

---

## 11. 파라미터 관리

### 11.1 튜닝 가능 파라미터

| 파라미터 | 현재값 | 설명 |
|----------|--------|------|
| `min_event_count` | 10 | 세션 최소 이벤트 수 |
| `min_session_duration_sec` | 60 | 세션 최소 지속 시간 |
| `min_gap_count` | 5 | 분석 최소 gap 수 |
| `idle_threshold_sec` | 180 | idle 고정 임계값(초) |
| `drift_threshold_pct` | 20 | 기준선 드리프트 알림 임계(%) |
| `feature_scope` | `all_features` | 기준 산출 범위 (feature별 분리 시 변경) |
| `rolling_window_days` | 30 | 세션/유저 기준선 산출 rolling 윈도우 |
| `role_scope` | `labeler_only` | 기본 KPI 모드. 확장 시 `reviewer_only`, `all_roles` 가능 (§16) |

### 11.2 feature별 분리 판단 기준

- feature 간 `gap_p90` 차이가 ±30% 이상 → 분리 산출
- `task._raw:policyId` → `annotation_policy._raw:feature` 조인으로 식별

---

## 12. 트러블슈팅

### 12.1 zero-inflation 문제

**증상**: `session_*_count_p90/p95/p99 = 0` → 해당 레벨의 gap이 1개만 있어도 전부 판정됨

> 예: `session_idle_count_p99 = 0`인 경우, `idle_gap_count > 0 AND > 0` = TRUE → idle gap 1개만으로 idle 세션 판정. Bootstrap 초기(7일 데이터) 또는 idle gap이 매우 드문 정상 구간에서 발생.

**해결** (light / heavy / idle 공통):
1. `min_gap_count` 파라미터 상향 (5 → 10)으로 짧은 세션 제거
2. `해당_gap_count > 0` 최소 조건은 이미 적용됨 (§7.4)
3. rolling window 기간 확대하여 기준선 재산출
4. **bootstrap 시 보수적 최솟값 적용**: `session_idle_count_p99 = 0`이면 최솟값 1로 대체

```sql
-- session_thresholds 실행 후 zero-inflation 보정 (선택적 후처리)
UPDATE analytics.focus_drop_session_thresholds
SET session_idle_count_p99  = GREATEST(session_idle_count_p99, 1),
    session_heavy_count_p95 = GREATEST(session_heavy_count_p95, 1),
    session_light_count_p90 = GREATEST(session_light_count_p90, 1)
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds)
  AND (session_idle_count_p99 = 0 OR session_heavy_count_p95 = 0 OR session_light_count_p90 = 0);
```

> 이 보정은 "threshold = 0이면 최솟값 1로 올린다"는 단순 규칙으로, `gap_count > 0 AND gap_count > 1` = `gap_count >= 2`가 되어 단일 gap 오탐을 방지한다.

### 12.2 오탐률 과다

**증상**: light 판정 비율이 30% 이상

**해결**:
1. Labeler role 필터 정확성 확인 (gen2_assignments 조인 검증)
2. `gap_p90` 기준값이 너무 낮은지 확인 (2초 이하이면 비정상)
3. 특정 company/project의 UX 특성이 gap 분포를 왜곡하는지 확인

### 12.3 기준값 급변

**증상**: 신규 산출 percentile이 기존 대비 50% 이상 변동

**원인 후보**:
1. 신규 대량 Labeler 온보딩 (미숙련 패턴 유입)
2. 툴 UX 변경 (새 기능 추가로 gap 패턴 변화)
3. policy 변경으로 작업 방식 변화

### 12.4 기준선 테이블 부재 (초기 배포 시)

**증상**: `focus_drop_session_thresholds` 또는 `focus_drop_user_thresholds`에 데이터 없음 → session_tags / user_day_kpi 노트북 실행 시 CROSS JOIN 결과가 빈 행

**근본 원인**: 파이프라인 의존성 순환 구조

```
gap_percentiles    ← workspace_command 90일분 + 표본 10,000 gap 필요
session_thresholds ← session_metrics 30일분 필요
user_thresholds    ← user_day_kpi 30일분 필요
session_tags       ← session_thresholds + gap_percentiles 필요
user_day_kpi       ← user_thresholds 필요  ← 자기 자신 30일분 필요 (순환)
```

**단계적 해결 — 4 Phase 초기 배포**:

#### Phase 0: 인프라 준비 (Day 0)

테이블이 존재하지 않는 상태에서 시작한다.

1. **DDL 적용**: `.sql/focus_drop__ddl.sql` 실행 → 7개 Delta 테이블 생성
   - `focus_drop_gap_thresholds`, `focus_drop_session_thresholds`, `focus_drop_user_thresholds`
   - `focus_drop_session_metrics`, `focus_drop_task_idle_rollup`, `focus_drop_session_tags`, `focus_drop_user_day_kpi`
2. **존재 확인 쿼리**:
   ```sql
   SHOW TABLES IN analytics LIKE 'focus_drop_*';
   ```
3. **gap_percentiles 1회 실행 시도**: 표본 부족 시 `HAVING COUNT(*) >= 10000` 가드로 0행 INSERT → Phase A에서 재시도

#### Phase A: Warm-up (Day 1~6)

- **실행**: `session_metrics` → `task_idle_rollup` 일 단위 배치 (gap_percentiles는 표본 누적 후 별도 트리거)
- **gap_percentiles**: workspace_command 누적 표본이 10,000 gap 이상 도달하면 수동 실행 → `focus_drop_gap_thresholds` 첫 버전 생성
  - 표본 부족 상태에서 session_metrics는 `thresholds` CTE가 0행 → CROSS JOIN 결과 0행 → 적재 스킵 (silent skip)
  - Phase A 진입 전제: gap_percentiles 1행 이상 적재 확인
- **session_tags / user_day_kpi**: 실행하지 않음 (2차 기준선 미생성)
- **최소 요건**: Labeler 유효 세션 100개 이상 축적 확인

#### Phase B: Bootstrap (Day 7)

- **조건**: session_metrics에 최소 7일분 데이터 적재 + gap_percentiles 1행 이상 존재 확인
- **실행 순서** (순환 의존성 해소):
  1. `session_thresholds`를 `rolling_window_days = 7`로 임시 실행 (`is_bootstrap = TRUE`) → 세션 기준선 생성
  2. zero-inflation 보정 SQL 실행 (§12.1) → `session_idle_count_p99 = 0` 등을 최솟값 1로 대체
  3. `task_idle_rollup`을 7일 소급 실행 → 생산성 연계 데이터 준비
  4. `session_tags`를 7일 소급 실행 (session_thresholds 기준선 참조) → session_tags 생성
  5. **`user_thresholds`를 임시 기준값으로 수동 INSERT** → 유저 기준선 부트스트랩 (★ user_day_kpi보다 먼저)
     ```sql
     INSERT INTO analytics.focus_drop_user_thresholds VALUES (
       1, CURRENT_TIMESTAMP(), TRUE,
       DATE_SUB(CURRENT_DATE(), 7), DATE_SUB(CURRENT_DATE(), 1),
       1.0, 1.0, 3.0
       -- 근거: threshold=1 → count>1 필요 → light/heavy 세션 2회 이상,
       --       idle gap 4개 이상이어야 판정. 과탐지 방지 우선, Phase C에서 실데이터 대체.
     );
     ```
  6. `user_day_kpi`를 7일 소급 실행 (user_thresholds 부트스트랩 기준선 참조) → user_day_kpi 생성
  7. 이후 일 배치 Job(`focus_drop_daily`)을 steady-state 구성으로 활성화
- **주의**: Bootstrap 기준선은 `is_bootstrap = TRUE`로 마킹하여 정식 기준선과 구분

#### Phase C: Steady-state (Day 30+)

- **전환 조건**: session_metrics 30일분 + user_day_kpi 30일분 축적
- **실행**: `session_thresholds` / `user_thresholds`를 정식 30일 rolling window로 재실행 → Bootstrap 기준선 대체 (`is_bootstrap = FALSE` 신규 버전)
- **gap_percentiles**: workspace_command 90일분 누적 시점에서 정식 분기 스케줄(§6.4 Quarterly Job)로 편입
- **이후**: 정상 스케줄 (`session_thresholds` / `user_thresholds` 주 1회, `session_metrics` / `task_idle_rollup` / `session_tags` / `user_day_kpi` 일 1회) 전환

**폴백 동작 (session_tags / user_day_kpi)**:

```sql
-- session_tags / user_day_kpi에서 기준선 테이블이 비어있을 때의 방어 로직
WITH thresholds AS (
  SELECT session_light_count_p90, session_heavy_count_p95, session_idle_count_p99
  FROM analytics.focus_drop_session_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds)
)
-- thresholds CTE가 0행이면 CROSS JOIN 결과도 0행 → 판정 자체가 생략됨
-- 이 경우 session_tags 테이블에 당일 데이터가 적재되지 않으므로 알림 미발생 (safe fail)
-- ★ Silent failure 방지: 아래 모니터링 쿼리를 일 배치 마지막에 실행
```

**Bootstrap silent failure 감지 쿼리** (일 배치 마지막에 실행):

```sql
-- 기준선 부재로 인한 0행 적재 감지 → 운영자 알림 트리거
SELECT
  CASE
    WHEN (SELECT COUNT(*) FROM analytics.focus_drop_session_tags WHERE analysis_date = ${analysis_date}) = 0
     AND (SELECT COUNT(*) FROM analytics.focus_drop_session_metrics WHERE analysis_date = ${analysis_date}) > 0
    THEN 'ALERT: session_tags 0행 — 기준선 테이블(session_thresholds) 비어있음'
    WHEN (SELECT COUNT(*) FROM analytics.focus_drop_user_day_kpi WHERE analysis_date = ${analysis_date}) = 0
     AND (SELECT COUNT(*) FROM analytics.focus_drop_session_tags WHERE analysis_date = ${analysis_date}) > 0
    THEN 'ALERT: user_day_kpi 0행 — 기준선 테이블(user_thresholds) 비어있음'
    ELSE 'OK'
  END AS pipeline_health_status;
```

**Bootstrap 최소 요건 체크 쿼리**:

```sql
-- Phase B 진입 가능 여부 확인
SELECT
  COUNT(DISTINCT analysis_date) AS available_days,
  COUNT(*) AS total_sessions,
  CASE WHEN COUNT(DISTINCT analysis_date) >= 7 AND COUNT(*) >= 100
       THEN 'READY_FOR_BOOTSTRAP' ELSE 'WAIT' END AS bootstrap_status
FROM analytics.focus_drop_session_metrics;
```

### 12.5 Idle Bootstrap 거동 — Phase B 민감도 관리

Phase B(7일 데이터) 기준선에서 idle 관련 threshold는 구조적으로 민감도가 높아진다.

#### Phase B 상황

| threshold | 7일 데이터 예상값 | zero-inflation 보정 후 | 실제 판정 조건 |
|-----------|--------------|---------------------|--------------|
| `session_idle_count_p99` | 0 (idle 이벤트 희귀) | 1 | `idle_gap_count >= 2` → is_idle_session |
| `user_idle_gap_total_p99` | 수동 3.0 (Bootstrap INSERT) | — | `idle_gap_total >= 4` → is_idle_user |

**`user_idle_gap_total_p99 = 3.0` 근거**: 하루 전체 세션에서 idle gap 누적이 4회 이상인 사용자만 `is_idle_user = TRUE`로 판정하여 초기 과탐지를 억제. 이 값은 Phase C(30일 데이터 축적 후) `user_thresholds` 재산출 시 실데이터 기반으로 자동 대체된다.

#### Phase B 기간 운영 지침

1. **출력 마킹**: `is_bootstrap = TRUE`인 기간(session_thresholds, user_thresholds 버전 확인)의 session_tags / user_day_kpi 집계는 리포팅에서 별도 구분
2. **idle 세션 비율 수동 모니터링**: Phase B에서 idle 세션 비율이 5% 초과 시 threshold 재검토 신호
3. **`session_idle_count_p99 = 1` 상태 허용**: 단일 idle gap 오탐이 우려되면 `session_thresholds`에서 최솟값을 1 → 2로 수동 조정 가능 (zero-inflation 보정 SQL의 `GREATEST(..., 1)` → `GREATEST(..., 2)`)
4. **Phase C 전환 확인 쿼리**:

```sql
-- idle threshold가 실데이터 기반으로 갱신되었는지 확인
SELECT version, is_bootstrap, window_start, window_end,
       session_idle_count_p99, user_idle_gap_total_p99
FROM analytics.focus_drop_session_thresholds st
JOIN analytics.focus_drop_user_thresholds ut ON ut.version = (
  SELECT MAX(version) FROM analytics.focus_drop_user_thresholds WHERE is_bootstrap = FALSE
)
WHERE st.version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds WHERE is_bootstrap = FALSE);
```

#### gap_p99 와 idle 180s 임계값 공존 원칙

`gap_p99`는 분류 경계가 아닌 **임계값 안전 마진 모니터링 지표**로 유지한다.

- `gap_p99` 산출 범위: `diff_sec < 180` 모집단 → "idle 제외 작업 리듬의 통계적 상한"
- 해석: `(180 - gap_p99)` = idle 고정 임계값과 정상 작업 분포 사이의 마진
- Phase B~C에서 gap_p99가 지속적으로 상승하면 180s 임계값 재협의 신호

```sql
-- 분기별 gap_p99 추이 — 안전 마진 모니터링
SELECT version, computed_at, gap_p95, gap_p99,
       ROUND(180 - gap_p99, 1) AS idle_safety_margin_sec
FROM analytics.focus_drop_gap_thresholds
ORDER BY version DESC
LIMIT 4;
```

---

## 13. 버전업 원칙

다음 조건 중 하나 이상 확인 시 기준 재검토 및 percentile 재산출:

- Labeler 표본이 기존 대비 50% 이상 증가
- 툴 UX 또는 작업 방식 변경
- `drift_status = 'RECALCULATE'` 연속 2주 감지
- 특정 feature에서 오탐/미탐 반복 보고
- 분기 정기 검토 시점
- 생산성 연계 시 `task_total_idle_sec / gross_task_sec` 분포가 급격히 변동

---

## 14. 트리거 키워드

다음 키워드가 요청에 포함되면 본 skill을 참조:

- "집중도", "focus drop", "집중도 저하", "focus"
- "gap 분석", "gap percentile", "긴 공백"
- "light session", "heavy session", "idle session"
- "작업 이탈", "idle 탐지", "3분 기준", "180초"
- "KPI 모니터링", "일일 리포트"
- "idle 차감", "순소요시간", "net working time", "task idle"

---

## 15. 빠른 참조

### 15.1 현황 확인 쿼리

```sql
-- 오늘의 focus drop KPI 요약 (배타적 레벨)
SELECT user_id, user_focus_drop_level, light_session_count, heavy_session_count, idle_gap_total
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date = CURRENT_DATE() - 1
  AND user_focus_drop_level != 'normal'
ORDER BY
  CASE user_focus_drop_level WHEN 'idle' THEN 1 WHEN 'heavy' THEN 2 WHEN 'light' THEN 3 END;
```

### 15.2 기준값 확인

```sql
-- 현재 적용 중인 gap threshold
SELECT * FROM analytics.focus_drop_gap_thresholds
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_gap_thresholds);

-- 현재 적용 중인 세션 기준선
SELECT * FROM analytics.focus_drop_session_thresholds
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds);

-- 현재 적용 중인 유저 기준선
SELECT * FROM analytics.focus_drop_user_thresholds
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_user_thresholds);
```

### 15.3 세션 상세 드릴다운

```sql
-- 특정 사용자의 세션별 gap severity 분포
SELECT
  session_id, task_id,
  total_gaps,
  light_gap_count, heavy_gap_count, idle_gap_count,
  focus_drop_level
FROM analytics.focus_drop_session_tags
WHERE user_id = :user_id
  AND analysis_date = :date
ORDER BY
  CASE focus_drop_level WHEN 'idle' THEN 1 WHEN 'heavy' THEN 2 WHEN 'light' THEN 3 ELSE 4 END;
```

### 15.4 Task idle rollup 확인

```sql
-- 생산성 연계용 task idle 누적 초수 확인
SELECT
  analysis_date,
  task_id,
  role_scope,
  role_group,
  contributing_sessions,
  contributing_users,
  idle_gap_total,
  idle_gap_duration_sec
FROM analytics.focus_drop_task_idle_rollup
WHERE analysis_date >= DATE_SUB(CURRENT_DATE(), 7)
ORDER BY analysis_date DESC, idle_gap_duration_sec DESC;
```

### 15.5 초기 배포 단계별 진입 확인 쿼리

Phase 0 → A → B → C 전환 시 다음 SELECT 묶음으로 다음 단계 진입 가능 여부를 미리 검증한다. 모든 쿼리는 read-only이며 실행 결과로 OK/PENDING을 판정한다.

#### Phase 0 → Phase A (DDL 적재 완료 확인)

```sql
-- 7개 focus_drop 테이블 존재 여부
SHOW TABLES IN analytics LIKE 'focus_drop_*';
-- 기대: 7행 (gap_thresholds, session_metrics, session_thresholds, session_tags,
--        user_thresholds, user_day_kpi, task_idle_rollup)

-- 각 테이블 빈 상태 확인 (Phase 0 직후엔 모두 0행이어야 정상)
SELECT 'gap_thresholds'   AS tbl, COUNT(*) AS rows FROM analytics.focus_drop_gap_thresholds
UNION ALL SELECT 'session_metrics',   COUNT(*) FROM analytics.focus_drop_session_metrics
UNION ALL SELECT 'session_thresholds',COUNT(*) FROM analytics.focus_drop_session_thresholds
UNION ALL SELECT 'session_tags',      COUNT(*) FROM analytics.focus_drop_session_tags
UNION ALL SELECT 'user_thresholds',   COUNT(*) FROM analytics.focus_drop_user_thresholds
UNION ALL SELECT 'user_day_kpi',      COUNT(*) FROM analytics.focus_drop_user_day_kpi
UNION ALL SELECT 'task_idle_rollup',  COUNT(*) FROM analytics.focus_drop_task_idle_rollup;
```

#### Phase A → Phase B (gap_percentiles + session_metrics 누적 충분)

```sql
-- gap_thresholds 최신 버전 존재 확인
SELECT version, gap_p75, gap_p90, gap_p95, sample_size, computed_at
FROM analytics.focus_drop_gap_thresholds
ORDER BY version DESC
LIMIT 1;
-- 기대: 1행, sample_size > 10000 권장

-- session_metrics 7일+ 누적 + 세션 100개 이상 (Bootstrap 기준)
SELECT
  COUNT(DISTINCT analysis_date)              AS days_loaded,
  COUNT(*)                                   AS total_sessions,
  COUNT(DISTINCT user_id)                    AS distinct_users,
  MIN(analysis_date)                         AS first_date,
  MAX(analysis_date)                         AS last_date
FROM analytics.focus_drop_session_metrics;
-- Phase B 진입 기준: days_loaded >= 7 AND total_sessions >= 100
```

#### Phase B → Phase C (기준선 부트스트랩 + 7일 KPI 적재)

```sql
-- session_thresholds 부트스트랩 버전 존재
SELECT version, role_scope, role_group, rolling_window_days, is_bootstrap, computed_at
FROM analytics.focus_drop_session_thresholds
WHERE is_bootstrap = TRUE
ORDER BY version DESC;
-- 기대: 1행 이상 (Phase B step 1 결과)

-- user_thresholds 부트스트랩 INSERT 확인
SELECT version, role_scope, role_group, rolling_window_days, is_bootstrap, computed_at
FROM analytics.focus_drop_user_thresholds
WHERE is_bootstrap = TRUE
ORDER BY version DESC;
-- 기대: 1행 이상 (Phase B step 5 수동 INSERT 결과)

-- session_tags + user_day_kpi 7일 적재 확인
SELECT 'session_tags' AS tbl, COUNT(DISTINCT analysis_date) AS days, COUNT(*) AS rows
FROM analytics.focus_drop_session_tags
UNION ALL
SELECT 'user_day_kpi', COUNT(DISTINCT analysis_date), COUNT(*)
FROM analytics.focus_drop_user_day_kpi;
-- Phase C 진입 기준: 두 테이블 모두 days >= 7
```

#### Phase C → 정상 운영 (30일 누적 + is_bootstrap=FALSE 신규 버전)

```sql
-- session_metrics 30일 누적 확인
SELECT
  COUNT(DISTINCT analysis_date) AS days_loaded,
  MIN(analysis_date)            AS first_date,
  MAX(analysis_date)            AS last_date
FROM analytics.focus_drop_session_metrics;
-- 기대: days_loaded >= 30

-- session_thresholds + user_thresholds is_bootstrap=FALSE 신규 버전 존재
SELECT 'session_thresholds' AS tbl, MAX(version) AS latest_version,
       MAX(CASE WHEN is_bootstrap = FALSE THEN version END) AS latest_steady_version
FROM analytics.focus_drop_session_thresholds
UNION ALL
SELECT 'user_thresholds', MAX(version),
       MAX(CASE WHEN is_bootstrap = FALSE THEN version END)
FROM analytics.focus_drop_user_thresholds;
-- 기대: 두 테이블 모두 latest_steady_version IS NOT NULL
```

---

## 16. 생산성 연계 및 Reviewer 확장

### 16.1 Task 순소요시간 차감 원칙

생산성 분석에서 Task 평균 소요시간은 다음 두 값을 모두 유지한다.

| 지표 | 산식 | 의미 |
|------|------|------|
| `gross_task_hours` | `(deliver_actionAt - start_actionAt) / 3600` | 전환 이력 기준 총 경과 시간 |
| `net_task_hours` | `GREATEST(gross_task_sec - task_total_idle_sec, 0) / 3600` | Focus Drop idle 차감 후 순작업시간 |

여기서:

```sql
gross_task_sec      = UNIX_TIMESTAMP(deliver_at) - UNIX_TIMESTAMP(start_at)
task_total_idle_sec = SUM(idle_gap_duration_sec)  -- 동일 task의 복수 session / 복수 일자 합산
net_task_hours      = GREATEST(gross_task_sec - task_total_idle_sec, 0) / 3600.0
```

> `task_total_idle_sec`는 `analytics.focus_drop_task_idle_rollup`을 `task_id` 기준으로 재합산하여 만든다. 동일 Task가 여러 날짜·세션에 걸쳐 진행될 수 있으므로 반드시 누적 합산이 필요하다.

### 16.2 생산성 SQL 연계 예시

```sql
WITH task_idle AS (
  SELECT
    task_id,
    SUM(idle_gap_duration_sec) AS task_total_idle_sec
  FROM analytics.focus_drop_task_idle_rollup
  WHERE role_scope = 'all_roles'  -- 초기에는 'labeler' fallback 가능
  GROUP BY task_id
)
SELECT
  d.task_id,
  s.start_at,
  d.deliver_at,
  ROUND((UNIX_TIMESTAMP(d.deliver_at) - UNIX_TIMESTAMP(s.start_at)) / 3600.0, 2) AS gross_task_hours,
  ROUND(COALESCE(i.task_total_idle_sec, 0) / 3600.0, 2) AS idle_hours,
  ROUND(
    GREATEST(
      UNIX_TIMESTAMP(d.deliver_at) - UNIX_TIMESTAMP(s.start_at) - COALESCE(i.task_total_idle_sec, 0),
      0
    ) / 3600.0,
    2
  ) AS net_task_hours
FROM deliver_events d
JOIN start_events s ON d.task_id = s.task_id
LEFT JOIN task_idle i ON d.task_id = i.task_id;
```

### 16.3 Reviewer 확장 모드

생산성 지표의 분모는 **Labeler + Reviewer 합산**이므로, Focus Drop idle도 최종적으로는 Reviewer까지 확장하는 것이 정합성이 높다.

권장 확장 방식은 **role 필터 제거**가 아니라, **role을 dimension으로 유지한 통합 파이프라인**이다.

| 모드 | 설명 | 사용처 |
|------|------|------|
| `labeler_only` | 기존 KPI 기준선 유지 | Focus Drop KPI 본체 |
| `reviewer_only` | Reviewer 패턴 단독 분석 | Reviewer 운영 진단 |
| `all_roles` | Labeler + Reviewer 통합 rollup | 생산성 순소요시간 차감 |

### 16.4 통합 role 파이프라인 SQL 패턴

```sql
-- 공통 소스 CTE 예시: role 차원을 보존
WITH worker_commands AS (
  SELECT
    c._raw:userId::STRING       AS user_id,
    c._raw:sessionId::STRING    AS session_id,
    c._raw:taskId::STRING       AS task_id,
    c._raw:createdAt::TIMESTAMP AS event_time,
    LOWER(a._raw:role::STRING)  AS role_group
  FROM sv_nova_dev_an2_catalog.raw.raw_labelit__workspace_command c
  INNER JOIN sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_tasks t
    ON c._raw:taskId::STRING = t._id
  INNER JOIN sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_assignments a
    ON t._raw:assignmentId::STRING = a._id
  WHERE c._is_deleted = false
    AND LOWER(a._raw:role::STRING) IN ('labeler', 'reviewer')
    AND (
      ${role_scope} = 'all_roles'
      OR LOWER(a._raw:role::STRING) = ${role_scope}
    )
)
```

이 패턴을 사용하면 `focus_drop_task_idle_rollup` 적재 시 다음 두 컬럼을 유지할 수 있다.

- `role_scope`: 실행 모드 (`labeler`, `reviewer`, `all_roles`)
- `role_group`: 실제 작업 역할 (`labeler`, `reviewer`)

### 16.5 운영 권고안

1. **즉시 적용**: Labeler 파이프라인에 `idle_gap_duration_sec`와 `task_idle_rollup` 추가
2. **중간 단계**: 생산성 SQL에서 `labeler` idle 차감 버전과 `gross_task_hours`를 병행 보고
3. **최종 단계**: Reviewer 확장 후 `role_scope = 'all_roles'` 기준을 기본값으로 전환
4. **대시보드 표기**: `gross_task_hours`, `idle_hours`, `net_task_hours` 3개를 동시에 노출하여 해석 가능성 확보
5. **Phase A/B 기간 주의**: 부트스트랩 7일 동안은 gap 기준선 미생성으로 `idle_gap_duration_sec = 0`이 될 수 있음 → 이 기간 `net_task_hours = gross_task_hours` 전체. 첫 주 생산성 리포트에 "idle 차감 미적용(부트스트랩 기간)" 주석 권고

### 16.6 해석상 주의점

- idle 차감은 **근사치**이며, 검토/인지/시야 탐색 같은 비명령 시간 전체를 완전하게 설명하지 않는다
- idle 차감 후 `net_task_hours`가 0에 가까운 Task는 로그 수집 이상 또는 세션 분절 이슈를 우선 점검해야 한다
- Reviewer 확장 시 Reviewer의 작업 리듬은 Labeler와 다를 수 있으므로, KPI 기준선과 생산성 차감 로직을 동일 테이블에 혼합하지 않는 것이 안전하다
