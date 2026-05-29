# SFM × Nova 통합 설계 전략 2 — 분석 데이터 모델

> **작성일:** 2026-05-21
> **분석 대상:** SV Fleet Manager 1.0-rc / `SFM_Architecture_Report.md`
> **범위:** Nova 레이어 매핑, dim/mrt 설계, ODD × MV2 Feature 매핑, 통합 분석 시나리오

---

## 1. Nova 레이어 구조 매핑

```
raw_sfm_*          ← PostgreSQL 직수집 / Kafka change_events
stg_sfm_*          ← JSONB 파싱, version join 해소, PTP 시각 보정
          │
          ├─ dim_vehicle              ← Registry+Versions 평탄화 SCD Type 2
          ├─ dim_vehicle_config       ← config 버전 평탄화, scene_type·thresholds 포함
          ├─ dim_odd_class            ← odd_attributes + odd_values 계층 평탄화 + MV2 매핑
          │
          └─ int_sfm_session_quality  ← collection_sessions × quality_summaries 조인
                    │
                    ├─ mrt_collection_quality_kpi       ← 수집 품질 × Nova 어노테이션 KPI
                    └─ mrt_session_odd_distribution     ← 세션 ODD 분포 집계
```

---

## 2. `int_sfm_session_quality` — 수집 세션 품질 통합

### 설계 의도

`collection_sessions`와 `collection_quality_summaries`를 조인하여 분석 쿼리에서 반복되는 조인을 제거한다.

### DDL

```sql
CREATE OR REPLACE TABLE int_sfm_session_quality
USING DELTA
PARTITIONED BY (collection_date)
AS
SELECT
  s.session_id,
  s.vehicle_uuid,
  s.config_uuid,
  s.config_version,
  s.scene_type,
  CAST(s.start_time AS DATE)      AS collection_date,
  s.start_time,
  s.end_time,
  DATEDIFF(MINUTE, s.start_time, s.end_time) AS session_duration_min,
  s.status                        AS session_status,

  -- quality 집계
  q.overall_drop_rate,
  q.quality_grade,                -- PASS / WARNING / FAIL
  CASE q.quality_grade
    WHEN 'PASS'    THEN 3
    WHEN 'WARNING' THEN 2
    WHEN 'FAIL'    THEN 1
    ELSE 0
  END                             AS quality_score,

  -- 세그먼트 집계
  q.total_segment_count,
  q.failed_segment_count,
  ROUND(
    q.failed_segment_count * 100.0 / NULLIF(q.total_segment_count, 0), 2
  )                               AS segment_fail_pct

FROM stg_sfm_collection_sessions s
JOIN stg_sfm_collection_quality  q USING (session_id)
WHERE s.status = 'completed'
```

---

## 3. `mrt_collection_quality_kpi` — 수집 품질 × Nova 어노테이션 KPI

### 연계 전제

SFM 수집 세션과 Nova 어노테이션 작업은 `collection_date + scene_type + vehicle_uuid`를 브릿지 키로 연계한다.
`session_id` 직접 매핑이 가능한 경우 해당 키로 대체한다.

### DDL

```sql
CREATE OR REPLACE TABLE mrt_collection_quality_kpi
USING DELTA
COMMENT 'SFM 수집 품질 × Nova 어노테이션 KPI 통합 — grain: collection_date × scene_type × vehicle_uuid'
PARTITIONED BY (collection_date)
AS
SELECT
  -- 수집 dimension
  sq.collection_date,
  sq.vehicle_uuid,
  sq.scene_type,

  -- 수집 품질 집계
  COUNT(sq.session_id)                          AS session_count,
  ROUND(AVG(sq.overall_drop_rate), 4)           AS avg_drop_rate,
  ROUND(AVG(sq.quality_score), 2)               AS avg_quality_score,
  COUNT_IF(sq.quality_grade = 'FAIL')           AS fail_session_count,
  COUNT_IF(sq.quality_grade = 'WARNING')        AS warning_session_count,
  COUNT_IF(sq.quality_grade = 'PASS')           AS pass_session_count,
  ROUND(
    COUNT_IF(sq.quality_grade = 'PASS') * 100.0 / COUNT(*), 1
  )                                             AS pass_rate_pct,
  SUM(sq.session_duration_min)                  AS total_collection_min,

  -- Nova 어노테이션 KPI (브릿지: collection_date + scene_type)
  nk.annotation_task_count,
  nk.net_annotation_hours,
  nk.inspection_pass_rate,      -- inspection_quality KPI
  nk.avg_focus_drop_score,      -- focus_drop KPI
  nk.productivity_score,        -- productivity KPI

  -- 파생 지표 — 수집 품질 → 어노테이션 영향 복합 지수
  ROUND(
    avg_drop_rate * (1 - COALESCE(nk.inspection_pass_rate, 1)), 4
  )                                             AS quality_impact_index,

  CURRENT_TIMESTAMP()                           AS updated_at

FROM int_sfm_session_quality sq
LEFT JOIN int_nova_annotation_daily_kpi nk
  ON  nk.work_date  = sq.collection_date
  AND nk.scene_type = sq.scene_type

GROUP BY
  sq.collection_date,
  sq.vehicle_uuid,
  sq.scene_type,
  nk.annotation_task_count,
  nk.net_annotation_hours,
  nk.inspection_pass_rate,
  nk.avg_focus_drop_score,
  nk.productivity_score
```

### 핵심 분석 쿼리

```sql
-- 수집 품질 구간별 검수 통과율 비교
SELECT
  scene_type,
  quality_grade_bucket,
  ROUND(AVG(inspection_pass_rate), 3) AS avg_inspection_pass,
  ROUND(AVG(avg_drop_rate), 4)        AS avg_drop_rate,
  SUM(session_count)                  AS sessions
FROM (
  SELECT *,
    CASE
      WHEN pass_rate_pct >= 80 THEN 'HIGH'
      WHEN pass_rate_pct >= 50 THEN 'MID'
      ELSE 'LOW'
    END AS quality_grade_bucket
  FROM mrt_collection_quality_kpi
  WHERE collection_date >= DATEADD(DAY, -30, CURRENT_DATE())
)
GROUP BY scene_type, quality_grade_bucket
ORDER BY scene_type, quality_grade_bucket
```

---

## 4. `dim_odd_class` — ODD 계층 × Nova MV2 Feature 매핑

### MV2 Feature 매핑 기준

| MV2 Feature | ODD super_class | class_name 패턴 | object_motion_type |
|---|---|---|---|
| `OD` | Object | Car, Pedestrian, Cyclist, Truck, Bus, Motorcycle, Van | dynamic + static |
| `SOD` | Object | TrafficCone, Barrier, Boulder, Debris | static |
| `TSTLD` | Road | TrafficSign, TrafficLight | — |
| `LD` | Road | LaneLine, StopLine, CrossWalk | — |
| `RMD` | Road | PolyWall, RoadMarking, GuardRail | — |

### DDL

```sql
CREATE OR REPLACE TABLE nova_dim.dim_odd_class
USING DELTA
COMMENT 'ODD 속성 계층 평탄화 + Nova MV2 Feature 매핑 — grain: schema_id × attribute_id'
AS
WITH odd_values_flat AS (
  -- 자기참조 계층 최대 3레벨 평탄화
  SELECT
    v0.attribute_id,
    v0.value_id       AS root_value_id,
    v0.value_code     AS root_value_code,
    v1.value_id       AS child_value_id,
    v1.value_code     AS child_value_code,
    v2.value_id       AS grandchild_value_id,
    v2.value_code     AS grandchild_value_code,
    CASE
      WHEN v2.value_id IS NOT NULL THEN 3
      WHEN v1.value_id IS NOT NULL THEN 2
      ELSE 1
    END               AS hierarchy_depth
  FROM odd_values v0
  LEFT JOIN odd_values v1 ON v1.parent_value_id = v0.value_id
  LEFT JOIN odd_values v2 ON v2.parent_value_id = v1.value_id
  WHERE v0.parent_value_id IS NULL
),

value_aggregated AS (
  SELECT
    attribute_id,
    MAX(hierarchy_depth)          AS max_value_depth,
    COLLECT_SET(root_value_code)  AS root_value_codes,
    COLLECT_SET(child_value_code) AS child_value_codes,
    COUNT(DISTINCT root_value_id) AS root_value_count
  FROM odd_values_flat
  GROUP BY attribute_id
),

label_pivot AS (
  SELECT
    al.attribute_id,
    MAX(CASE WHEN al.locale = 'ko' THEN al.label END) AS label_ko,
    MAX(CASE WHEN al.locale = 'en' THEN al.label END) AS label_en,
    MAX(CASE WHEN al.locale = 'ja' THEN al.label END) AS label_ja
  FROM odd_attribute_labels al
  GROUP BY al.attribute_id
)

SELECT
  a.attribute_id,
  a.schema_id,
  s.version                       AS schema_version,
  s.status                        AS schema_status,
  a.super_class,
  a.class_name,
  a.attribute_key,
  a.tag_mode,                     -- SINGLE / MULTIPLE
  a.is_required,

  -- Nova MV2 Feature 매핑
  CASE
    WHEN a.super_class = 'Object'
     AND a.class_name IN ('Car','Pedestrian','Cyclist','Truck','Bus','Motorcycle','Van')
    THEN 'OD'
    WHEN a.super_class = 'Object'
     AND a.class_name IN ('TrafficCone','Barrier','Boulder','Debris')
    THEN 'SOD'
    WHEN a.super_class = 'Road'
     AND a.class_name IN ('TrafficSign','TrafficLight')
    THEN 'TSTLD'
    WHEN a.super_class = 'Road'
     AND a.class_name IN ('LaneLine','StopLine','CrossWalk')
    THEN 'LD'
    WHEN a.super_class = 'Road'
     AND a.class_name IN ('PolyWall','RoadMarking','GuardRail')
    THEN 'RMD'
    ELSE 'UNCLASSIFIED'
  END                             AS nova_mv2_feature,

  -- 동적/정적 객체 구분
  CASE
    WHEN a.super_class = 'Object'
     AND a.class_name IN ('Car','Pedestrian','Cyclist','Truck','Bus','Motorcycle','Van')
    THEN 'dynamic'
    WHEN a.super_class = 'Object'
    THEN 'static'
    ELSE NULL
  END                             AS object_motion_type,

  lp.label_ko,
  lp.label_en,
  lp.label_ja,
  va.root_value_count,
  va.max_value_depth,
  va.root_value_codes,
  va.child_value_codes,

  CURRENT_TIMESTAMP()             AS updated_at

FROM odd_attributes  a
JOIN odd_schemas     s  ON s.schema_id  = a.schema_id
LEFT JOIN label_pivot     lp ON lp.attribute_id = a.attribute_id
LEFT JOIN value_aggregated va ON va.attribute_id = a.attribute_id
WHERE s.status = 'active'
```

---

## 5. `mrt_session_odd_distribution` — 세션 ODD 분포 집계

```sql
CREATE OR REPLACE TABLE mrt_session_odd_distribution
USING DELTA
COMMENT '세션별 MV2 Feature × ODD 클래스 분포 — grain: session_id × nova_mv2_feature'
PARTITIONED BY (collection_date)
AS
SELECT
  t.session_id,
  sq.collection_date,
  sq.scene_type,
  sq.vehicle_uuid,
  d.nova_mv2_feature,
  d.object_motion_type,
  d.super_class,
  COUNT(*)                                       AS tag_count,
  COUNT(DISTINCT d.class_name)                   AS distinct_class_count,
  COLLECT_SET(
    GET_JSON_OBJECT(t.tag_value, CONCAT('$.', d.attribute_key))
  )                                              AS observed_values,
  CURRENT_TIMESTAMP()                            AS updated_at

FROM session_odd_tags   t
JOIN dim_odd_class      d  ON d.attribute_id = t.attribute_id
JOIN int_sfm_session_quality sq ON sq.session_id = t.session_id

WHERE d.nova_mv2_feature != 'UNCLASSIFIED'

GROUP BY
  t.session_id,
  sq.collection_date,
  sq.scene_type,
  sq.vehicle_uuid,
  d.nova_mv2_feature,
  d.object_motion_type,
  d.super_class
```

---

## 6. ODD 매핑 유지보수 전략

`dim_odd_class`의 `CASE WHEN` 하드코딩은 ODD 스키마 신버전 배포 시 깨질 수 있다.
장기적으로 **매핑 브릿지 테이블**로 분리한다.

```sql
-- 관리용 브릿지 테이블
CREATE TABLE nova_dim.ref_odd_to_mv2_feature (
  class_name         STRING  NOT NULL,
  nova_mv2_feature   STRING  NOT NULL,   -- OD/SOD/TSTLD/LD/RMD/UNCLASSIFIED
  object_motion_type STRING,             -- dynamic/static/NULL
  effective_from     DATE    NOT NULL,
  effective_to       DATE,               -- NULL = 현재 유효
  note               STRING
);
```

`odd_schemas.status`가 `draft → active`로 전환될 때 `change_events` 스트림을 트리거로 Slack 알림을 발송하여 매핑 테이블 리뷰 프로세스를 실행한다.

---

## 7. 주요 분석 연계 시나리오

### 시나리오 A — 수집 품질 → 어노테이션 품질 상관관계

```
collection_quality_summaries.quality_grade (PASS/WARNING/FAIL)
  × Nova inspection_pass_rate
→ mrt_collection_quality_kpi.quality_impact_index
```

수집 `drop_rate`가 높은 세그먼트가 검수 통과율 저하와 상관관계가 있는지 30일 롤링 분석.

### 시나리오 B — ODD 태그 분포 → 어노테이션 작업량 예측

```
mrt_session_odd_distribution.tag_count (MV2 feature별)
  → 작업 볼륨 예측 (scene_type × feature 조합별 단위 시간 추정)
```

### 시나리오 C — 차량 × 씬 타입 × 어노테이션 품질 3-way 조인

```
collection_sessions.vehicle_uuid + scene_type + start_time
  → Nova annotation_batch 매핑
→ 특정 차량·씬 타입 수집분의 어노테이션 품질 편차 분석
```

---

## 8. 전체 통합 흐름 요약

```
SFM PostgreSQL / Kafka
        │
        ├─ Kafka stream ──→ raw_sfm_change_events
        │                 → stg_sfm_change_events
        │                         (전략 1 파이프라인)
        │
        ├─ 배치 스냅샷 ──→ stg_sfm_collection_*
        │               → int_sfm_session_quality
        │
        └─ 배치 스냅샷 ──→ odd_attributes / odd_values
                        → dim_odd_class (§4)
                                │
                    session_odd_tags JOIN
                                │
                    mrt_session_odd_distribution (§5)

Nova KPI (기존 Labelit 로그 기반)
        │
        └──────────── JOIN ──→ mrt_collection_quality_kpi (§3)
```

---

*관련 문서: [`sfm_nova_integration_01_ingestion_pipeline_2026-05-21.md`](./sfm_nova_integration_01_ingestion_pipeline_2026-05-21.md)*
