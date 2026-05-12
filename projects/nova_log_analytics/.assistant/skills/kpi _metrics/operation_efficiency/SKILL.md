# Operation Analytics Skill

Stage별 소요 시간(Stage Duration)과 산출물 변화(Object Delta) 산출을 위한 가이드.

## 트리거 키워드

"Stage 소요 시간", "Cycle Time", "병목", "stage duration", "object delta", "산출물 변화", "객체 증감", "반려율", "review reject", "ops", "운영 지표", "TAT", "Turn-Around Time" 중 하나라도 포함되면 이 스킬을 로드할 것.

---

## 1. 데이터 소스

> **운영 SQL 원칙**: staging layer를 우선 소스로 사용한다.
> - Stage Duration: `stg_task_transition_events` (이벤트 쌍 기반)
> - Object Delta: `stg_object_counts_by_task` (stage_key별 COUNT PIVOT 기반)
> - raw 메타(`company`, `gen2_annotation_policies`)만 직접 참조한다.

> 전체 카탈로그 prefix: `sv_nova_dev_an2_catalog.raw.raw_labelit__`

### 1.0 운영 소스 (Staging)

| Staging 테이블 | grain | 출처 | 용도 |
| --- | --- | --- | --- |
| `analytics.stg_task_transition_events` | task_id × event row | `raw_labelit__gen2_tasks` transitionHistory flatten | Stage 시작/종료 이벤트 추출 |
| `analytics.stg_object_counts_by_task` | task_id × table_name × stage_key | 10개 객체 테이블 CDC dedup + COUNT | Stage별 객체 수 비교 |

### 1.1 raw 메타 직접 참조 (staging에 없음)

| 항목 | 테이블 | 용도 |
| --- | --- | --- |
| 업체 메타 | `raw_labelit__company` | companyId → company name |
| Annotation Policy | `raw_labelit__gen2_annotation_policies` | policyId → feature name |

### 1.2 stg_task_transition_events 컬럼

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `task_id` | STRING | gen2_tasks._id |
| `company_id` | STRING | gen2_tasks._raw.companyId |
| `policy_id` | STRING | gen2_tasks._raw.policyId |
| `from_state` | STRING | transitionHistory[].fromState |
| `to_state` | STRING | transitionHistory[].toState |
| `trigger` | STRING | transitionHistory[].trigger (start / submit / reject / reassign / auto) |
| `action_by` | STRING | transitionHistory[].actionBy |
| `action_at` | TIMESTAMP | transitionHistory[].actionAt (UTC) |
| `reason` | STRING | transitionHistory[].reason (반려 사유 등) |
| `event_week` | DATE | DATE_TRUNC('WEEK', action_at KST) — 파티션 키 |

> staging은 snake_case — raw `_raw` JSON의 camelCase (`fromState`, `toState`)와 구분.

### 1.3 stg_object_counts_by_task 컬럼

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `task_id` | STRING | 연결 Task ID |
| `table_name` | STRING | 객체 테이블 이름 (gen2_lines 등) |
| `stage_key` | STRING | labeling / review / inspection / final_qa |
| `object_count` | BIGINT | CDC dedup 후 해당 (task_id, table_name, stage_key) COUNT |

### 1.4 Feature별 객체 테이블 매핑

| Feature | 객체 테이블 (`table_name`) | 핵심 객체 유형 |
| --- | --- | --- |
| MV2_LD | `gen2_lines`, `gen2_lanes`, `gen2_road_boundaries`, `gen2_topologies` | line, lane, road_boundary, topology |
| MV2_OD / MV2_SOD / MV2_TSTLD | `gen2_dynamic_targets`, `gen2_static_targets` | bbox3d |
| MV2_RMD | `gen2_polywall_roadmark_objects`, `gen2_box_roadmark_objects` | polywall, bbox3d |

**조인 키**: `stg_object_counts_by_task.task_id` → `raw_labelit__gen2_tasks._id` → `companyId`, `policyId`

### 1.5 Stage 전환 이벤트 정의

| Stage | 시작 이벤트 (from_state → to_state, trigger) | 종료 이벤트 |
| --- | --- | --- |
| Labeling | `waiting_labeling → labeling, trigger='start'` | `labeling → waiting_review` |
| Review | `waiting_review → review, trigger='start'` | `review → waiting_submit` |
| Inspection | `waiting_submit → inspection, trigger='deliver'` | `inspection → waiting_final_qa` |
| Final QA | `waiting_final_qa → final_qa, trigger='start'` | `final_qa → completed` |

---

## 2. 핵심 비즈니스 규칙

### 2.1 Pass 식별 (Reject 후 재진입)

동일 Task에서 Reject로 인해 동일 Stage에 2회 이상 진입할 수 있다. 각 진입을 **별도 pass**로 식별한다.

```
pass_num = ROW_NUMBER() OVER (
  PARTITION BY task_id, stage
  ORDER BY stage_start_at
)
```

- pass 1: 최초 수행
- pass 2+: Reject 후 재작업
- **집계 시 pass별 소요 시간을 합산**하여 Task 기준 총 소요 시간 산출

### 2.2 Reassign 처리

동일 Stage 내 `trigger='reassign'` 이벤트는 담당자 변경이지 새 pass가 아니다.

- Labeling reassign: `from_state='labeling' AND to_state='labeling' AND trigger='reassign'` → **시작 이벤트에서 제외**
- 동일 pass 내 Reassign 구간은 소요 시간에 **그대로 포함** (중단 없이 이어진 작업으로 처리)

### 2.3 종료 이벤트 누락 처리

Stage 종료 이벤트가 없는 경우 (Task가 현재 해당 Stage에 있는 경우):

```sql
-- 다음 Stage 시작 이벤트의 action_at을 종료 시점으로 대체
-- 대체값이 없으면 CURRENT_TIMESTAMP() 사용 (진행 중인 Task)
stage_end_at = COALESCE(실제종료, 다음Stage시작, CURRENT_TIMESTAMP())
```

### 2.4 Object Delta 집계 원칙

- Object Delta = `to_stage_count − from_stage_count`
- `from_stage_count = 0`인 경우 delta_ratio = NULL (NULLIF 처리)
- 양수(+): 후속 Stage에서 객체 추가 / 음수(−): 후속 Stage에서 객체 삭제
- **집계 단위**: task_id × table_name × Stage 전환 쌍

### 2.5 KST 기준

모든 `action_at` 기반 집계는 KST(UTC+9) 기준.

```sql
CAST(CONVERT_TIMEZONE('UTC', 'Asia/Seoul', action_at) AS DATE) AS event_date_kst
```

---

## 3. 지표 정의

### 3.1 Stage Duration 지표

| 지표 | 단위 | 집계 방식 |
| --- | --- | --- |
| `stage_duration_hours` | hours / task × pass | `(stage_end_at − stage_start_at) / 3600.0` |
| `avg_stage_duration_hours` | hours / task | Task 기준 pass 합산 후 평균 (업체 × Feature × 주) |
| `p50_stage_duration_hours` | hours | 분포 중앙값 (업체 × Feature × Stage) |
| `p90_stage_duration_hours` | hours | 분포 90th percentile |
| `total_pipeline_hours` | hours / task | Labeling 착수 → 납품 경과 시간 |
| `rework_pass_count` | 횟수 / task | pass_num ≥ 2인 패스 수 (Reject 재작업 횟수) |

### 3.2 Object Delta 지표

| 지표 | 단위 | 산출식 |
| --- | --- | --- |
| `delta_count` | 개 / task | `to_stage_count − from_stage_count` |
| `delta_ratio` | % | `delta_count / NULLIF(from_stage_count, 0) × 100` |
| `avg_delta_count` | 개 / task | `AVG(delta_count)` (업체 × Feature × Stage 전환) |
| `avg_abs_delta_ratio` | % | `AVG(ABS(delta_ratio))` — 수정 강도 (방향 무관) |

### 3.3 반려율 (보조 지표)

| 지표 | 산출식 |
| --- | --- |
| Review 반려율 | `COUNT(from_state='review' AND trigger='reject') / NULLIF(COUNT(review 완료), 0) × 100` |
| Inspection 반려율 | `COUNT(from_state='inspection' AND trigger='reject') / NULLIF(COUNT(inspection 완료), 0) × 100` |

> Policy §1.3 원칙: 분모 = 0인 경우 `NULL`로 산출 (`NULLIF` 적용).

---

## 4. SQL 템플릿

> 운영 SQL 위치: `.sql/ops__stage_duration.sql` · `.sql/ops__object_delta.sql`  
> **현재 미생성** — 아래 템플릿 기반으로 파일 작성 필요

### 4.1 Stage Duration (`ops__stage_duration.sql`)

```sql
-- ops__stage_duration.sql
-- Stage별 소요 시간 산출 — task_id × stage × pass 단위
-- 주기: 주 배치 — stg_task_transition_events 갱신 후 실행

CREATE WIDGET TEXT target_week DEFAULT "";

DECLARE OR REPLACE VARIABLE analysis_week DATE =
  CASE WHEN LENGTH('${target_week}') = 0
    THEN DATE_TRUNC('WEEK', CURRENT_DATE() - INTERVAL 1 DAY)
    ELSE TO_DATE('${target_week}')
  END;

INSERT INTO analytics.ops_stage_duration
REPLACE WHERE event_week = analysis_week
WITH base_events AS (
  SELECT task_id, company_id, policy_id,
         from_state, to_state, trigger, action_at, reason, event_week
  FROM analytics.stg_task_transition_events
  WHERE event_week >= DATE_SUB(analysis_week, 90)  -- reject 재진입 고려 90일 범위
),

-- Labeling
labeling_starts AS (
  SELECT task_id, company_id, policy_id, action_at AS stage_start_at,
    ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY action_at) AS pass_num
  FROM base_events
  WHERE from_state = 'waiting_labeling' AND to_state = 'labeling' AND trigger = 'start'
),
labeling_ends AS (
  SELECT task_id, action_at AS stage_end_at,
    ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY action_at) AS pass_num
  FROM base_events
  WHERE from_state = 'labeling' AND to_state = 'waiting_review'
),
labeling_duration AS (
  SELECT s.task_id, s.company_id, s.policy_id,
    'labeling' AS stage, s.pass_num,
    s.stage_start_at,
    -- NOTE: §2.3 규칙은 3단 fallback (실제종료 → 다음Stage시작 → CURRENT_TIMESTAMP())이나,
    -- 현 구현은 2단 간소화. "다음Stage시작" fallback은 LEAD/서브쿼리 필요 — 향후 개선 대상.
    COALESCE(e.stage_end_at, CURRENT_TIMESTAMP()) AS stage_end_at,
    ROUND((UNIX_TIMESTAMP(COALESCE(e.stage_end_at, CURRENT_TIMESTAMP()))
           - UNIX_TIMESTAMP(s.stage_start_at)) / 3600.0, 3) AS duration_hours,
    (e.stage_end_at IS NULL) AS is_open
  FROM labeling_starts s
  LEFT JOIN labeling_ends e ON s.task_id = e.task_id AND s.pass_num = e.pass_num
),

-- Review
review_starts AS (
  SELECT task_id, company_id, policy_id, action_at AS stage_start_at,
    ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY action_at) AS pass_num
  FROM base_events
  WHERE from_state = 'waiting_review' AND to_state = 'review' AND trigger = 'start'
),
review_ends AS (
  SELECT task_id, action_at AS stage_end_at,
    CASE WHEN to_state = 'waiting_labeling' THEN TRUE ELSE FALSE END AS is_rejected,
    reason,
    ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY action_at) AS pass_num
  FROM base_events
  WHERE from_state = 'review'
    AND to_state IN ('waiting_submit', 'waiting_labeling')
),
review_duration AS (
  SELECT s.task_id, s.company_id, s.policy_id,
    'review' AS stage, s.pass_num,
    s.stage_start_at,
    COALESCE(e.stage_end_at, CURRENT_TIMESTAMP()) AS stage_end_at,
    ROUND((UNIX_TIMESTAMP(COALESCE(e.stage_end_at, CURRENT_TIMESTAMP()))
           - UNIX_TIMESTAMP(s.stage_start_at)) / 3600.0, 3) AS duration_hours,
    COALESCE(e.is_rejected, FALSE) AS is_rejected,
    e.reason AS reject_reason,
    (e.stage_end_at IS NULL) AS is_open
  FROM review_starts s
  LEFT JOIN review_ends e ON s.task_id = e.task_id AND s.pass_num = e.pass_num
),

-- Inspection
inspection_starts AS (
  SELECT task_id, company_id, policy_id, action_at AS stage_start_at,
    ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY action_at) AS pass_num
  FROM base_events
  WHERE from_state = 'waiting_submit' AND to_state = 'inspection' AND trigger = 'deliver'
),
inspection_ends AS (
  SELECT task_id, action_at AS stage_end_at,
    CASE WHEN to_state = 'waiting_submit' THEN TRUE ELSE FALSE END AS is_rejected,
    reason,
    ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY action_at) AS pass_num
  FROM base_events
  WHERE from_state = 'inspection'
    AND to_state IN ('waiting_final_qa', 'waiting_submit')
),
inspection_duration AS (
  SELECT s.task_id, s.company_id, s.policy_id,
    'inspection' AS stage, s.pass_num,
    s.stage_start_at,
    COALESCE(e.stage_end_at, CURRENT_TIMESTAMP()) AS stage_end_at,
    ROUND((UNIX_TIMESTAMP(COALESCE(e.stage_end_at, CURRENT_TIMESTAMP()))
           - UNIX_TIMESTAMP(s.stage_start_at)) / 3600.0, 3) AS duration_hours,
    COALESCE(e.is_rejected, FALSE) AS is_rejected,
    e.reason AS reject_reason,
    (e.stage_end_at IS NULL) AS is_open
  FROM inspection_starts s
  LEFT JOIN inspection_ends e ON s.task_id = e.task_id AND s.pass_num = e.pass_num
),

-- Final QA
final_qa_starts AS (
  SELECT task_id, company_id, policy_id, action_at AS stage_start_at,
    ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY action_at) AS pass_num
  FROM base_events
  WHERE from_state = 'waiting_final_qa' AND to_state = 'final_qa' AND trigger = 'start'
),
final_qa_ends AS (
  SELECT task_id, action_at AS stage_end_at,
    ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY action_at) AS pass_num
  FROM base_events
  WHERE from_state = 'final_qa' AND to_state = 'completed'
),
final_qa_duration AS (
  SELECT s.task_id, s.company_id, s.policy_id,
    'final_qa' AS stage, s.pass_num,
    s.stage_start_at,
    COALESCE(e.stage_end_at, CURRENT_TIMESTAMP()) AS stage_end_at,
    ROUND((UNIX_TIMESTAMP(COALESCE(e.stage_end_at, CURRENT_TIMESTAMP()))
           - UNIX_TIMESTAMP(s.stage_start_at)) / 3600.0, 3) AS duration_hours,
    FALSE AS is_rejected,
    NULL AS reject_reason,
    (e.stage_end_at IS NULL) AS is_open
  FROM final_qa_starts s
  LEFT JOIN final_qa_ends e ON s.task_id = e.task_id AND s.pass_num = e.pass_num
),

all_stages AS (
  SELECT *, NULL AS is_rejected, NULL AS reject_reason FROM labeling_duration
  UNION ALL SELECT * FROM review_duration
  UNION ALL SELECT * FROM inspection_duration
  UNION ALL SELECT * FROM final_qa_duration
)

SELECT
  d.task_id, d.company_id, d.policy_id,
  d.stage, d.pass_num, d.stage_start_at, d.stage_end_at,
  d.duration_hours, d.is_rejected, d.reject_reason, d.is_open,
  DATE_TRUNC('WEEK', CAST(
    CONVERT_TIMEZONE('UTC', 'Asia/Seoul', d.stage_start_at) AS DATE
  )) AS event_week,
  CURRENT_TIMESTAMP() AS refreshed_at
FROM all_stages d
WHERE DATE_TRUNC('WEEK', CAST(
    CONVERT_TIMEZONE('UTC', 'Asia/Seoul', d.stage_start_at) AS DATE
  )) = analysis_week;
```

### 4.2 Object Delta (`ops__object_delta.sql`)

```sql
-- ops__object_delta.sql
-- Stage 전환별 객체 증감 산출 — task_id × table_name × Stage 전환 단위
-- 전 Feature(MV2_LD · MV2_RMD · MV2_OD · MV2_SOD · MV2_TSTLD) 대상
-- 주기: 주 배치 — stg_object_counts_by_task 갱신 후 실행

CREATE WIDGET TEXT target_week DEFAULT "";

DECLARE OR REPLACE VARIABLE analysis_week DATE =
  CASE WHEN LENGTH('${target_week}') = 0
    THEN DATE_TRUNC('WEEK', CURRENT_DATE() - INTERVAL 1 DAY)
    ELSE TO_DATE('${target_week}')
  END;

INSERT INTO analytics.ops_object_delta
REPLACE WHERE event_week = analysis_week
WITH obj AS (
  -- Stage_key별 객체 수 PIVOT (labeling / review / inspection / final_qa) — 전 Feature 객체 테이블
  SELECT task_id, table_name,
    MAX(CASE WHEN stage_key = 'labeling'   THEN object_count ELSE 0 END) AS labeling_count,
    MAX(CASE WHEN stage_key = 'review'     THEN object_count ELSE 0 END) AS review_count,
    MAX(CASE WHEN stage_key = 'inspection' THEN object_count ELSE 0 END) AS inspection_count,
    MAX(CASE WHEN stage_key = 'final_qa'   THEN object_count ELSE 0 END) AS final_qa_count
  FROM analytics.stg_object_counts_by_task
  GROUP BY task_id, table_name
),
deliver_events AS (
  -- 납품 이벤트 기준으로 analysis_week 결정
  SELECT task_id, company_id, policy_id, event_week
  FROM analytics.stg_task_transition_events
  WHERE from_state = 'waiting_submit' AND to_state = 'inspection'
    AND event_week = analysis_week
),
delta_base AS (
  SELECT
    e.task_id, e.company_id, e.policy_id, o.table_name,
    o.labeling_count, o.review_count, o.inspection_count,
    e.event_week
  FROM deliver_events e
  JOIN obj o ON e.task_id = o.task_id
),

-- Stage 전환별 delta 계산 (unpivot)
labeling_to_review AS (
  SELECT task_id, company_id, policy_id, table_name,
    'labeling'   AS from_stage_key,
    'review'     AS to_stage_key,
    labeling_count   AS from_count,
    review_count     AS to_count,
    (review_count - labeling_count) AS delta_count,
    event_week
  FROM delta_base
),
review_to_inspection AS (
  SELECT task_id, company_id, policy_id, table_name,
    'review'     AS from_stage_key,
    'inspection' AS to_stage_key,
    review_count     AS from_count,
    inspection_count AS to_count,
    (inspection_count - review_count) AS delta_count,
    event_week
  FROM delta_base
),
inspection_to_final_qa AS (
  SELECT task_id, company_id, policy_id, table_name,
    'inspection' AS from_stage_key,
    'final_qa'   AS to_stage_key,
    inspection_count AS from_count,
    final_qa_count   AS to_count,
    (final_qa_count - inspection_count) AS delta_count,
    event_week
  FROM delta_base
  WHERE final_qa_count > 0  -- Final QA 미진입 Task 제외
),
labeling_to_final_qa AS (
  -- 전체 순증: Labeling 기준 대비 Final QA 완료 시점 변화량
  SELECT task_id, company_id, policy_id, table_name,
    'labeling' AS from_stage_key,
    'final_qa' AS to_stage_key,
    labeling_count AS from_count,
    final_qa_count AS to_count,
    (final_qa_count - labeling_count) AS delta_count,
    event_week
  FROM delta_base
  WHERE final_qa_count > 0
)

SELECT
  task_id, company_id, policy_id, table_name,
  from_stage_key, to_stage_key,
  from_count, to_count, delta_count,
  ROUND(delta_count / NULLIF(from_count, 0) * 100, 2) AS delta_ratio,
  event_week,
  CURRENT_TIMESTAMP() AS refreshed_at
FROM labeling_to_review
UNION ALL
SELECT
  task_id, company_id, policy_id, table_name,
  from_stage_key, to_stage_key,
  from_count, to_count, delta_count,
  ROUND(delta_count / NULLIF(from_count, 0) * 100, 2) AS delta_ratio,
  event_week,
  CURRENT_TIMESTAMP() AS refreshed_at
FROM review_to_inspection
UNION ALL
SELECT
  task_id, company_id, policy_id, table_name,
  from_stage_key, to_stage_key,
  from_count, to_count, delta_count,
  ROUND(delta_count / NULLIF(from_count, 0) * 100, 2) AS delta_ratio,
  event_week,
  CURRENT_TIMESTAMP() AS refreshed_at
FROM inspection_to_final_qa
UNION ALL
SELECT
  task_id, company_id, policy_id, table_name,
  from_stage_key, to_stage_key,
  from_count, to_count, delta_count,
  ROUND(delta_count / NULLIF(from_count, 0) * 100, 2) AS delta_ratio,
  event_week,
  CURRENT_TIMESTAMP() AS refreshed_at
FROM labeling_to_final_qa;
```

---

## 5. DDL 제안

> 운영 SQL 위치: `.sql/ops__ddl.sql` (미생성)

```sql
-- ops__stage_duration
CREATE TABLE IF NOT EXISTS analytics.ops_stage_duration (
  task_id        STRING,
  company_id     STRING,
  policy_id      STRING,
  stage          STRING,   -- labeling / review / inspection / final_qa
  pass_num       INT,      -- 1 = 최초, 2+ = reject 후 재작업
  stage_start_at TIMESTAMP,
  stage_end_at   TIMESTAMP,
  duration_hours DOUBLE,
  is_rejected    BOOLEAN,
  reject_reason  STRING,
  is_open        BOOLEAN,  -- 종료 이벤트 없음 (진행 중)
  event_week     DATE,
  refreshed_at   TIMESTAMP
)
USING DELTA
PARTITIONED BY (event_week)
TBLPROPERTIES ('delta.columnMapping.mode' = 'name');

-- ops_object_delta
CREATE TABLE IF NOT EXISTS analytics.ops_object_delta (
  task_id        STRING,
  company_id     STRING,
  policy_id      STRING,
  table_name     STRING,
  from_stage_key STRING,
  to_stage_key   STRING,
  from_count     BIGINT,
  to_count       BIGINT,
  delta_count    BIGINT,
  delta_ratio    DOUBLE,   -- delta / from_count × 100, NULL if from_count = 0
  event_week     DATE,
  refreshed_at   TIMESTAMP
)
USING DELTA
PARTITIONED BY (event_week)
TBLPROPERTIES ('delta.columnMapping.mode' = 'name');
```

---

## 6. 운영 주의사항

| 항목 | 내용 |
| --- | --- |
| pass_num 매핑 | Labeling start와 Labeling end는 pass_num 기준으로 join. 시작이 있지만 종료가 없으면 `is_open=TRUE` |
| 90일 범위 조회 | Reject 재진입 Task가 여러 주에 걸쳐 있으므로 Stage Duration SQL은 `event_week >= analysis_week - 90일` 범위로 이벤트를 수집한다 |
| Reassign 제외 | `trigger='reassign'` 이벤트는 Stage 시작으로 카운트하지 않는다. 종료 이벤트 기준 pass_num 매핑 시 시작이 없는 종료가 생기지 않도록 주의 |
| staging 선행 의존 | ops 배치 실행 전 반드시 `stg__task_transition_events` · `stg__object_counts_by_task` 갱신 완료 확인 |
| 종료 이벤트 fallback | §2.3 규칙은 3단 fallback(실제종료 → 다음Stage시작 → CURRENT_TIMESTAMP())이나, §4.1 SQL은 2단 간소화 구현. `is_open=TRUE` Task는 집계에서 제외하여 영향 최소화. "다음Stage시작" fallback 추가는 향후 개선 |
| 테이블명 불일치 | Productivity SKILL은 단수형(`gen2_lanes`, `gen2_road_boundaries`), Operation SKILL은 복수형(`gen2_lanes`, `gen2_road_boundaries`) 사용. DDL 확인 후 통일 필요. RMD: `gen2_box_roadmark_objects` vs `gen2_box_roadmark_objects` 동일 여부 미확인 |

---

## 7. 현황 확인 쿼리

```sql
-- Stage Duration 적재 현황
SELECT stage, COUNT(*) AS rows, COUNT(DISTINCT task_id) AS tasks,
       MIN(event_week) AS first_week, MAX(event_week) AS last_week
FROM analytics.ops_stage_duration
GROUP BY stage ORDER BY stage;

-- 업체 × Feature × Stage 평균 소요 시간 (최근 4주)
SELECT
  c.name AS company_name,
  p.name AS feature_name,
  d.stage,
  ROUND(AVG(d.duration_hours), 2) AS avg_hours,
  ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY d.duration_hours), 2) AS p50_hours,
  ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY d.duration_hours), 2) AS p90_hours,
  COUNT(DISTINCT d.task_id) AS task_count
FROM analytics.ops_stage_duration d
JOIN `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__company` c
  ON d.company_id = c.`_id`
JOIN `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_annotation_policies` p
  ON d.policy_id = p.`_id`
WHERE d.event_week >= DATE_SUB(DATE_TRUNC('WEEK', CURRENT_DATE()), 28)
  AND d.is_open = FALSE
GROUP BY company_name, feature_name, d.stage
ORDER BY avg_hours DESC;

-- Object Delta 적재 현황
SELECT from_stage_key, to_stage_key, table_name,
       COUNT(*) AS rows, COUNT(DISTINCT task_id) AS tasks,
       ROUND(AVG(delta_ratio), 2) AS avg_delta_ratio_pct
FROM analytics.ops_object_delta
GROUP BY from_stage_key, to_stage_key, table_name
ORDER BY from_stage_key, to_stage_key, table_name;

-- Review 반려율 (최근 4주)
SELECT
  DATE_TRUNC('WEEK', CAST(CONVERT_TIMEZONE('UTC', 'Asia/Seoul', action_at) AS DATE)) AS week,
  company_id,
  COUNT(*) AS total_review_end,
  SUM(CASE WHEN trigger = 'reject' THEN 1 ELSE 0 END) AS rejected,
  ROUND(SUM(CASE WHEN trigger = 'reject' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0) * 100, 2) AS reject_rate_pct
FROM analytics.stg_task_transition_events
WHERE from_state = 'review'
  AND to_state IN ('waiting_submit', 'waiting_labeling')
  AND event_week >= DATE_SUB(DATE_TRUNC('WEEK', CURRENT_DATE()), 28)
GROUP BY week, company_id
ORDER BY week DESC, reject_rate_pct DESC;
```

---

## 8. 제약사항 및 검증 미완료 항목

| 항목 | 상태 | 비고 |
| --- | --- | --- |
| 객체 테이블 ↔ TransitionHistory 시점 정합성 | 미검증 | `stg_object_counts_by_task`의 `stage_key`별 스냅샷이 `actionAt` 기준 stage 전환 시점과 일치하는지 확인 필요 |
| 객체 `updatedAt` ↔ `actionAt` 매핑 | 미검증 | 객체 테이블 `updatedAt`과 전환 이력 `actionAt` 차이로 인한 stage_key 귀속 오류 가능성 |
| Reject 재진입 소요 시간 합산 정밀도 | 미검증 | 동일 Stage 복수 pass 식별 로직 (pass_num ROW_NUMBER 기반)의 정밀도 — 엣지케이스에서 start/end 쌍 불일치 여부 |

---

## 9. Initialize / Bootstrap 절차

Operation Analytics는 staging layer에 의존하므로 staging이 먼저 적재되어 있어야 한다.

```
Phase 0 — DDL 생성
Phase A — 이력 소급 적재
Phase B — 주 배치 정규 운영
```

### Phase 0: DDL 생성

```sql
-- ops__ddl.sql 실행 (§5 DDL 참조)
-- analytics.ops_stage_duration · analytics.ops_object_delta 테이블 생성
```

**진입 조건 확인**:

```sql
SHOW TABLES IN analytics LIKE 'ops_*';
-- 기대: 2행 (ops_stage_duration, ops_object_delta)
```

### Phase A: 이력 소급 적재

staging이 적재된 전체 기간을 소급한다.

```sql
-- stg_task_transition_events 적재 기간 확인
SELECT MIN(event_week) AS first_week, MAX(event_week) AS last_week
FROM analytics.stg_task_transition_events;

-- ops__stage_duration.sql: target_week를 최초 주부터 순차 실행
-- ops__object_delta.sql: target_week를 최초 납품 이벤트 주부터 순차 실행
```

> 소급 완료 기준: `ops_stage_duration`에서 `MIN(event_week) ≒ stg_task_transition_events MIN(event_week)`

### Phase B: 정규 배치

**실행 순서** (주 배치, 월요일 기준):

```
1. stg__task_transition_events (일 OVERWRITE — 선행 필수)
2. stg__object_counts_by_task  (일 배치 — 선행 필수)
3. ops__stage_duration          (주 배치)
4. ops__object_delta            (주 배치)
```

**진입 조건 확인** (Phase A → B 전환 전):

```sql
-- Stage Duration 소급 완료 확인
SELECT COUNT(DISTINCT event_week) AS weeks_loaded,
       MIN(event_week) AS first_week, MAX(event_week) AS last_week,
       COUNT(DISTINCT task_id) AS tasks
FROM analytics.ops_stage_duration;

-- Object Delta 소급 완료 확인
SELECT COUNT(DISTINCT event_week) AS weeks_loaded,
       MIN(event_week) AS first_week, MAX(event_week) AS last_week
FROM analytics.ops_object_delta;
```
