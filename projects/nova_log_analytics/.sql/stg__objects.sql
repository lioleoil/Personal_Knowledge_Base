-- Databricks notebook source
-- Staging: stg_objects
-- 10개 객체 테이블 unified CDC dedup (집계 없음)
-- grain: object_id × table_name
-- 갱신 전략: INSERT INTO REPLACE WHERE table_name = '...' (per-table 독립 교체, 병렬 실행 가능)
-- 실행 주기: 일 배치 04:00 UTC
-- 후행 소스: int__object_counts_by_task.sql (task별 집계)

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.stg_objects (
  object_id    STRING    COMMENT '객체 고유 ID (_id). task 내에서만 unique — task_id와 함께 사용',
  table_name   STRING    COMMENT '소스 테이블명 (gen2_lines, gen2_static_targets 등 10종)',
  task_id      STRING    COMMENT '소속 Task ID ($.taskId)',
  stage_key    STRING    COMMENT '현재 Stage Key ($.stageKey)',
  _loaded_at   TIMESTAMP COMMENT '데이터 적재 시각 (CURRENT_TIMESTAMP at INSERT)'
)
COMMENT '10개 객체 테이블 통합 (CDC dedup). grain: object_id × table_name. 소스: raw.raw_labelit__gen2_*. 갱신: INSERT INTO REPLACE WHERE table_name (per-table 독립 교체). 실행 주기: 일 배치 04:00 UTC.'
TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ─── LD 1/6: gen2_lines ──────────────────────────────────────────────────────
INSERT INTO sv_nova_dev_an2_catalog.analytics.stg_objects
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
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_lines`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── LD 2/6: gen2_line_points ────────────────────────────────────────────────
INSERT INTO sv_nova_dev_an2_catalog.analytics.stg_objects
REPLACE WHERE table_name = 'gen2_line_points'
SELECT
  `_id`                                  AS object_id,
  'gen2_line_points'                     AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_line_points`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── LD 3/6: gen2_road_boundaries ────────────────────────────────────────────
INSERT INTO sv_nova_dev_an2_catalog.analytics.stg_objects
REPLACE WHERE table_name = 'gen2_road_boundaries'
SELECT
  `_id`                                  AS object_id,
  'gen2_road_boundaries'                 AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_road_boundaries`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── LD 4/6: gen2_road_boundary_points ───────────────────────────────────────
INSERT INTO sv_nova_dev_an2_catalog.analytics.stg_objects
REPLACE WHERE table_name = 'gen2_road_boundary_points'
SELECT
  `_id`                                  AS object_id,
  'gen2_road_boundary_points'            AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_road_boundary_points`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── LD 5/6: gen2_lanes ──────────────────────────────────────────────────────
INSERT INTO sv_nova_dev_an2_catalog.analytics.stg_objects
REPLACE WHERE table_name = 'gen2_lanes'
SELECT
  `_id`                                  AS object_id,
  'gen2_lanes'                           AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_lanes`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── LD 6/6: gen2_topologies ─────────────────────────────────────────────────
INSERT INTO sv_nova_dev_an2_catalog.analytics.stg_objects
REPLACE WHERE table_name = 'gen2_topologies'
SELECT
  `_id`                                  AS object_id,
  'gen2_topologies'                      AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_topologies`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── RMD 1/2: gen2_polywall_roadmark_objects ─────────────────────────────────
INSERT INTO sv_nova_dev_an2_catalog.analytics.stg_objects
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
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_polywall_roadmark_objects`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── RMD 2/2: gen2_box_roadmark_objects ──────────────────────────────────────
INSERT INTO sv_nova_dev_an2_catalog.analytics.stg_objects
REPLACE WHERE table_name = 'gen2_box_roadmark_objects'
SELECT
  `_id`                                  AS object_id,
  'gen2_box_roadmark_objects'            AS table_name,
  get_json_object(`_raw`, '$.taskId')    AS task_id,
  get_json_object(`_raw`, '$.stageKey')  AS stage_key,
  CURRENT_TIMESTAMP()                    AS _loaded_at
FROM (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_box_roadmark_objects`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── OD / SOD / TSTLD 1/2: gen2_dynamic_targets ─────────────────────────────
INSERT INTO sv_nova_dev_an2_catalog.analytics.stg_objects
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
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_dynamic_targets`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ─── OD / SOD / TSTLD 2/2: gen2_static_targets ───────────────────────────────
INSERT INTO sv_nova_dev_an2_catalog.analytics.stg_objects
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
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_static_targets`
  WHERE `_is_deleted` = false
) WHERE rn = 1;

-- COMMAND ----------

-- ★ 테이블/컬럼 설명 업데이트 (기존 테이블 대응)
COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.stg_objects IS '10개 객체 테이블 통합 (CDC dedup). grain: object_id × table_name. 소스: raw.raw_labelit__gen2_*. 갱신: INSERT INTO REPLACE WHERE table_name (per-table 독립 교체). 실행 주기: 일 배치 04:00 UTC.';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_objects ALTER COLUMN object_id COMMENT '객체 고유 ID (_id). task 내에서만 unique — task_id와 함께 사용';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_objects ALTER COLUMN table_name COMMENT '소스 테이블명 (gen2_lines, gen2_static_targets 등 10종)';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_objects ALTER COLUMN task_id COMMENT '소속 Task ID ($.taskId)';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_objects ALTER COLUMN stage_key COMMENT '현재 Stage Key ($.stageKey)';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_objects ALTER COLUMN _loaded_at COMMENT '데이터 적재 시각 (CURRENT_TIMESTAMP at INSERT)';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_objects SET TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ★ 적재 확인
SELECT
  table_name,
  COUNT(DISTINCT object_id)  AS objects,
  COUNT(DISTINCT task_id)    AS tasks,
  COUNT(DISTINCT stage_key)  AS stage_keys
FROM sv_nova_dev_an2_catalog.analytics.stg_objects
GROUP BY table_name
ORDER BY table_name;