-- Intermediate: int_object_counts_by_task
-- stg_objects → task_id × table_name × stage_key 집계 (일별 스냅샷 누적)
-- grain: snapshot_date × task_id × table_name × stage_key
-- 갱신 전략: INSERT INTO REPLACE WHERE snapshot_date (일별 누적)
-- 실행 주기: 일 배치 04:00 UTC (stg_objects 전체 갱신 완료 후)
-- 선행 조건: stg__objects.sql (10개 테이블 전부 REPLACE 완료)
-- 후행 소스: production_volume__weekly.sql (production_volume_weekly PIVOT 소스)
--
-- ★ 백필 로직: CDC 복구 후 gap이 발생한 경우,
--   raw 테이블의 _ingested_at 기반 point-in-time 스냅샷을 자동 복원합니다.
--   정상 배치 시: statement 2만 실행 (CURRENT_DATE 스냅샷)
--   gap 감지 시: statement 2 → statement 3 순서로 실행 (백필 + 당일)

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

-- ★ 당일 스냅샷 적재 (CURRENT_DATE)
INSERT INTO sv_nova_dev_an2_catalog.analytics.int_object_counts_by_task
REPLACE WHERE snapshot_date = CURRENT_DATE()
SELECT
  task_id,
  table_name,
  stage_key,
  COUNT(*)            AS object_count,
  CURRENT_DATE()      AS snapshot_date,
  CURRENT_TIMESTAMP() AS _loaded_at
FROM sv_nova_dev_an2_catalog.analytics.stg_objects
WHERE task_id IS NOT NULL
GROUP BY task_id, table_name, stage_key;

-- COMMAND ----------

-- ★ Gap 백필: 마지막 스냅샷 이후 누락된 날짜들을 raw에서 point-in-time으로 복원
-- CDC 복구 후 raw에 데이터가 적재되면 이 쿼리로 누락 기간을 자동 채움
-- 정상 배치(gap 없음) 시 0건 INSERT — 안전하게 스킵됨
INSERT INTO sv_nova_dev_an2_catalog.analytics.int_object_counts_by_task
WITH last_snapshot AS (
  -- 오늘 제외한 가장 최근 스냅샷 날짜
  SELECT COALESCE(
    (SELECT MAX(snapshot_date) FROM sv_nova_dev_an2_catalog.analytics.int_object_counts_by_task
     WHERE snapshot_date < CURRENT_DATE()),
    DATE '2026-04-05'  -- 스냅샷 없으면 초기 기준일
  ) AS last_date
),
gap_dates AS (
  -- 마지막 스냅샷 다음날 ~ 어제까지 (간격 2일 이상일 때만 날짜 생성)
  SELECT EXPLODE(
    CASE WHEN DATEDIFF(CURRENT_DATE(), last_date) > 1
         THEN SEQUENCE(DATE_ADD(last_date, 1), CURRENT_DATE() - INTERVAL 1 DAY, INTERVAL 1 DAY)
         ELSE ARRAY()
    END
  ) AS snapshot_date
  FROM last_snapshot
),
all_raw_objects AS (
  SELECT _id, get_json_object(_raw, '$.taskId') AS task_id, get_json_object(_raw, '$.stageKey') AS stage_key, 'gen2_lines' AS table_name, _ingested_at, _is_deleted FROM sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_lines
  UNION ALL SELECT _id, get_json_object(_raw, '$.taskId'), get_json_object(_raw, '$.stageKey'), 'gen2_line_points', _ingested_at, _is_deleted FROM sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_line_points
  UNION ALL SELECT _id, get_json_object(_raw, '$.taskId'), get_json_object(_raw, '$.stageKey'), 'gen2_road_boundaries', _ingested_at, _is_deleted FROM sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_road_boundaries
  UNION ALL SELECT _id, get_json_object(_raw, '$.taskId'), get_json_object(_raw, '$.stageKey'), 'gen2_road_boundary_points', _ingested_at, _is_deleted FROM sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_road_boundary_points
  UNION ALL SELECT _id, get_json_object(_raw, '$.taskId'), get_json_object(_raw, '$.stageKey'), 'gen2_lanes', _ingested_at, _is_deleted FROM sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_lanes
  UNION ALL SELECT _id, get_json_object(_raw, '$.taskId'), get_json_object(_raw, '$.stageKey'), 'gen2_topologies', _ingested_at, _is_deleted FROM sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_topologies
  UNION ALL SELECT _id, get_json_object(_raw, '$.taskId'), get_json_object(_raw, '$.stageKey'), 'gen2_polywall_roadmark_objects', _ingested_at, _is_deleted FROM sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_polywall_roadmark_objects
  UNION ALL SELECT _id, get_json_object(_raw, '$.taskId'), get_json_object(_raw, '$.stageKey'), 'gen2_box_roadmark_objects', _ingested_at, _is_deleted FROM sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_box_roadmark_objects
  UNION ALL SELECT _id, get_json_object(_raw, '$.taskId'), get_json_object(_raw, '$.stageKey'), 'gen2_dynamic_targets', _ingested_at, _is_deleted FROM sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_dynamic_targets
  UNION ALL SELECT _id, get_json_object(_raw, '$.taskId'), get_json_object(_raw, '$.stageKey'), 'gen2_static_targets', _ingested_at, _is_deleted FROM sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_static_targets
),
point_in_time AS (
  SELECT
    d.snapshot_date,
    r._id,
    r.task_id,
    r.stage_key,
    r.table_name,
    r._is_deleted,
    ROW_NUMBER() OVER (PARTITION BY d.snapshot_date, r.table_name, r._id ORDER BY r._ingested_at DESC) AS rn
  FROM gap_dates d
  INNER JOIN all_raw_objects r ON CAST(r._ingested_at AS DATE) <= d.snapshot_date
  WHERE EXISTS (SELECT 1 FROM gap_dates)  -- gap 없으면 전체 스킵
)
SELECT
  task_id,
  table_name,
  stage_key,
  COUNT(*) AS object_count,
  snapshot_date,
  CURRENT_TIMESTAMP() AS _loaded_at
FROM point_in_time
WHERE rn = 1
  AND _is_deleted = false
  AND task_id IS NOT NULL
GROUP BY snapshot_date, task_id, table_name, stage_key;

-- COMMAND ----------

-- ★ 테이블/컬럼 설명 업데이트
COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.int_object_counts_by_task
  IS 'stg_objects → task_id × table_name × stage_key 객체 수 집계. grain: snapshot_date × (task_id, table_name, stage_key). 갱신: INSERT INTO REPLACE WHERE snapshot_date. 실행: 일 배치 04:00 UTC. CDC gap 자동 백필 내장.';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_object_counts_by_task ALTER COLUMN task_id COMMENT '소속 Task ID';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_object_counts_by_task ALTER COLUMN table_name COMMENT '소스 객체 테이블명 (e.g. gen2_lines, gen2_dynamic_targets)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_object_counts_by_task ALTER COLUMN stage_key COMMENT '작업 Stage 키 (labeling / inspection / ...)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_object_counts_by_task ALTER COLUMN object_count COMMENT '해당 (task, table, stage) 조합의 객체 수';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_object_counts_by_task ALTER COLUMN snapshot_date COMMENT '스냅샷 기준일 — 파티션 키';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_object_counts_by_task ALTER COLUMN _loaded_at COMMENT '적재 시점';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_object_counts_by_task SET TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ★ 적재 확인 (스냅샷 일별 추이)
SELECT
  snapshot_date,
  COUNT(DISTINCT task_id)   AS tasks,
  SUM(object_count)         AS total_objects,
  COUNT(DISTINCT table_name) AS tables
FROM sv_nova_dev_an2_catalog.analytics.int_object_counts_by_task
GROUP BY snapshot_date
ORDER BY snapshot_date DESC
LIMIT 10;