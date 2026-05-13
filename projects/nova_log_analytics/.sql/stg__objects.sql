-- Databricks notebook source
-- Staging: stg_objects
-- 10개 객체 테이블 unified CDC dedup (집계 없음)
-- grain: object_id × table_name
-- 갱신 전략: INSERT INTO REPLACE WHERE table_name = '...' (per-table 독립 교체, 병렬 실행 가능)
-- 실행 주기: 일 배치 04:00 UTC
-- 후행 소스: int__object_counts_by_task.sql (task별 집계)

-- COMMAND ----------

CREATE WIDGET TEXT catalog DEFAULT "sv_nova_dev_an2_catalog";

-- COMMAND ----------

-- ─── LD 1/6: gen2_lines ──────────────────────────────────────────────────────
INSERT INTO analytics.stg_objects
REPLACE WHERE table_name = 'gen2_lines'
SELECT
  `_id`                                  AS object_id,
  'gen2_lines'                           AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__gen2_lines`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── LD 2/6: gen2_line_point ─────────────────────────────────────────────────
INSERT INTO analytics.stg_objects
REPLACE WHERE table_name = 'gen2_line_point'
SELECT
  `_id`                                  AS object_id,
  'gen2_line_point'                      AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__gen2_line_point`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── LD 3/6: gen2_road_boundary ──────────────────────────────────────────────
INSERT INTO analytics.stg_objects
REPLACE WHERE table_name = 'gen2_road_boundary'
SELECT
  `_id`                                  AS object_id,
  'gen2_road_boundary'                   AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__gen2_road_boundary`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── LD 4/6: gen2_road_boundary_point ────────────────────────────────────────
INSERT INTO analytics.stg_objects
REPLACE WHERE table_name = 'gen2_road_boundary_point'
SELECT
  `_id`                                  AS object_id,
  'gen2_road_boundary_point'             AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__gen2_road_boundary_point`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── LD 5/6: gen2_lane ───────────────────────────────────────────────────────
INSERT INTO analytics.stg_objects
REPLACE WHERE table_name = 'gen2_lane'
SELECT
  `_id`                                  AS object_id,
  'gen2_lane'                            AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__gen2_lane`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── LD 6/6: gen2_topology ───────────────────────────────────────────────────
INSERT INTO analytics.stg_objects
REPLACE WHERE table_name = 'gen2_topology'
SELECT
  `_id`                                  AS object_id,
  'gen2_topology'                        AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__gen2_topology`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── RMD 1/2: gen2_polywall_roadmark_objects ─────────────────────────────────
INSERT INTO analytics.stg_objects
REPLACE WHERE table_name = 'gen2_polywall_roadmark_objects'
SELECT
  `_id`                                  AS object_id,
  'gen2_polywall_roadmark_objects'       AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__gen2_polywall_roadmark_objects`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── RMD 2/2: gen2_bbox3d_object ─────────────────────────────────────────────
INSERT INTO analytics.stg_objects
REPLACE WHERE table_name = 'gen2_bbox3d_object'
SELECT
  `_id`                                  AS object_id,
  'gen2_bbox3d_object'                   AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__gen2_bbox3d_object`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── OD / SOD / TSTLD 1/2: gen2_dynamic_targets ─────────────────────────────
INSERT INTO analytics.stg_objects
REPLACE WHERE table_name = 'gen2_dynamic_targets'
SELECT
  `_id`                                  AS object_id,
  'gen2_dynamic_targets'                 AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__gen2_dynamic_targets`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── OD / SOD / TSTLD 2/2: gen2_static_targets ───────────────────────────────
INSERT INTO analytics.stg_objects
REPLACE WHERE table_name = 'gen2_static_targets'
SELECT
  `_id`                                  AS object_id,
  'gen2_static_targets'                  AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__gen2_static_targets`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ★ 적재 확인
SELECT
  table_name,
  COUNT(DISTINCT object_id)  AS objects,
  COUNT(DISTINCT task_id)    AS tasks,
  COUNT(DISTINCT stage_key)  AS stage_keys
FROM analytics.stg_objects
GROUP BY table_name
ORDER BY table_name;
