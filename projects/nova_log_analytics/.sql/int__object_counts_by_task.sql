-- Databricks notebook source
-- Intermediate: int_object_counts_by_task
-- stg_objects → task_id × table_name × stage_key 집계
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체)
-- 실행 주기: 일 배치 04:00 UTC (stg_objects 전체 갱신 완료 후)
-- 선행 조건: stg__objects.sql (10개 테이블 전부 REPLACE 완료)
-- 후행 소스: production_volume__weekly.sql (production_volume_weekly PIVOT 소스)

-- COMMAND ----------

INSERT OVERWRITE analytics.int_object_counts_by_task
SELECT
  task_id,
  table_name,
  stage_key,
  COUNT(*)            AS object_count,
  CURRENT_TIMESTAMP() AS _loaded_at
FROM analytics.stg_objects
GROUP BY task_id, table_name, stage_key;

-- COMMAND ----------

-- ★ 적재 확인
SELECT
  table_name,
  COUNT(DISTINCT task_id)   AS tasks,
  SUM(object_count)         AS total_objects,
  COUNT(DISTINCT stage_key) AS stage_key_types
FROM analytics.int_object_counts_by_task
GROUP BY table_name
ORDER BY table_name;
