-- Databricks notebook source
-- Staging: stg_object_counts_by_task
-- 10개 객체 테이블 CDC dedup → task_id × table_name × stage_key 집계
-- 갱신 전략: REPLACE WHERE table_name = '...' (테이블별 독립 교체, 멱등성 보장)
-- 실행 주기: 일 배치 04:00 UTC

-- COMMAND ----------

-- ─── LD 1/6: gen2_lines ──────────────────────────────────────────────────────
INSERT INTO analytics.stg_object_counts_by_task
REPLACE WHERE table_name = 'gen2_lines'
SELECT
  get_json_object(`_raw`, '$.taskId')   AS task_id,
  'gen2_lines'                           AS table_name,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  COUNT(*)                               AS object_count,
  CURRENT_TIMESTAMP()                    AS refreshed_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_lines`
  WHERE `_is_deleted` = false
) WHERE rn = 1
GROUP BY 1, 2, 3;

-- COMMAND ----------

-- ─── LD 2/6: gen2_line_point ─────────────────────────────────────────────────
INSERT INTO analytics.stg_object_counts_by_task
REPLACE WHERE table_name = 'gen2_line_point'
SELECT
  get_json_object(`_raw`, '$.taskId')   AS task_id,
  'gen2_line_point'                      AS table_name,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  COUNT(*)                               AS object_count,
  CURRENT_TIMESTAMP()                    AS refreshed_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_line_point`
  WHERE `_is_deleted` = false
) WHERE rn = 1
GROUP BY 1, 2, 3;

-- COMMAND ----------

-- ─── LD 3/6: gen2_road_boundary ──────────────────────────────────────────────
INSERT INTO analytics.stg_object_counts_by_task
REPLACE WHERE table_name = 'gen2_road_boundary'
SELECT
  get_json_object(`_raw`, '$.taskId')   AS task_id,
  'gen2_road_boundary'                   AS table_name,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  COUNT(*)                               AS object_count,
  CURRENT_TIMESTAMP()                    AS refreshed_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_road_boundary`
  WHERE `_is_deleted` = false
) WHERE rn = 1
GROUP BY 1, 2, 3;

-- COMMAND ----------

-- ─── LD 4/6: gen2_road_boundary_point ────────────────────────────────────────
INSERT INTO analytics.stg_object_counts_by_task
REPLACE WHERE table_name = 'gen2_road_boundary_point'
SELECT
  get_json_object(`_raw`, '$.taskId')   AS task_id,
  'gen2_road_boundary_point'             AS table_name,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  COUNT(*)                               AS object_count,
  CURRENT_TIMESTAMP()                    AS refreshed_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_road_boundary_point`
  WHERE `_is_deleted` = false
) WHERE rn = 1
GROUP BY 1, 2, 3;

-- COMMAND ----------

-- ─── LD 5/6: gen2_lane ───────────────────────────────────────────────────────
INSERT INTO analytics.stg_object_counts_by_task
REPLACE WHERE table_name = 'gen2_lane'
SELECT
  get_json_object(`_raw`, '$.taskId')   AS task_id,
  'gen2_lane'                            AS table_name,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  COUNT(*)                               AS object_count,
  CURRENT_TIMESTAMP()                    AS refreshed_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_lane`
  WHERE `_is_deleted` = false
) WHERE rn = 1
GROUP BY 1, 2, 3;

-- COMMAND ----------

-- ─── LD 6/6: gen2_topology ───────────────────────────────────────────────────
INSERT INTO analytics.stg_object_counts_by_task
REPLACE WHERE table_name = 'gen2_topology'
SELECT
  get_json_object(`_raw`, '$.taskId')   AS task_id,
  'gen2_topology'                        AS table_name,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  COUNT(*)                               AS object_count,
  CURRENT_TIMESTAMP()                    AS refreshed_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_topology`
  WHERE `_is_deleted` = false
) WHERE rn = 1
GROUP BY 1, 2, 3;

-- COMMAND ----------

-- ─── RMD 1/2: gen2_polywall_roadmark_objects ─────────────────────────────────
INSERT INTO analytics.stg_object_counts_by_task
REPLACE WHERE table_name = 'gen2_polywall_roadmark_objects'
SELECT
  get_json_object(`_raw`, '$.taskId')   AS task_id,
  'gen2_polywall_roadmark_objects'       AS table_name,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  COUNT(*)                               AS object_count,
  CURRENT_TIMESTAMP()                    AS refreshed_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_polywall_roadmark_objects`
  WHERE `_is_deleted` = false
) WHERE rn = 1
GROUP BY 1, 2, 3;

-- COMMAND ----------

-- ─── RMD 2/2: gen2_bbox3d_object ─────────────────────────────────────────────
INSERT INTO analytics.stg_object_counts_by_task
REPLACE WHERE table_name = 'gen2_bbox3d_object'
SELECT
  get_json_object(`_raw`, '$.taskId')   AS task_id,
  'gen2_bbox3d_object'                   AS table_name,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  COUNT(*)                               AS object_count,
  CURRENT_TIMESTAMP()                    AS refreshed_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_bbox3d_object`
  WHERE `_is_deleted` = false
) WHERE rn = 1
GROUP BY 1, 2, 3;

-- COMMAND ----------

-- ─── OD / SOD / TSTLD: gen2_dynamic_targets ──────────────────────────────────
INSERT INTO analytics.stg_object_counts_by_task
REPLACE WHERE table_name = 'gen2_dynamic_targets'
SELECT
  get_json_object(`_raw`, '$.taskId')   AS task_id,
  'gen2_dynamic_targets'                 AS table_name,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  COUNT(*)                               AS object_count,
  CURRENT_TIMESTAMP()                    AS refreshed_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_dynamic_targets`
  WHERE `_is_deleted` = false
) WHERE rn = 1
GROUP BY 1, 2, 3;

-- COMMAND ----------

-- ─── OD / SOD / TSTLD: gen2_static_targets ───────────────────────────────────
INSERT INTO analytics.stg_object_counts_by_task
REPLACE WHERE table_name = 'gen2_static_targets'
SELECT
  get_json_object(`_raw`, '$.taskId')   AS task_id,
  'gen2_static_targets'                  AS table_name,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  COUNT(*)                               AS object_count,
  CURRENT_TIMESTAMP()                    AS refreshed_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_static_targets`
  WHERE `_is_deleted` = false
) WHERE rn = 1
GROUP BY 1, 2, 3;

-- COMMAND ----------

-- ★ 적재 확인
SELECT table_name,
       COUNT(DISTINCT task_id)           AS tasks,
       SUM(object_count)                 AS total_objects,
       COUNT(DISTINCT stage_key)         AS stage_key_types
FROM analytics.stg_object_counts_by_task
GROUP BY table_name
ORDER BY table_name;
