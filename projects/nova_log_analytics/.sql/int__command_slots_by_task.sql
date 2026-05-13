-- Databricks notebook source
-- Intermediate: int_command_slots_by_task
-- stg_workspace_commands → task별 투입 자원 집계 (전체 기간 합산)
-- grain: task_id
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체)
-- 실행 주기: 일 배치 04:00 UTC (stg_workspace_commands 갱신 완료 후)
-- 대체: stg_command_slots_by_task [DEPRECATED]
-- 후행 소스: mrt__production_volume_weekly.sql

-- COMMAND ----------

INSERT OVERWRITE analytics.int_command_slots_by_task
SELECT
  task_id,
  COUNT(DISTINCT CONCAT(user_name, '-', CAST(event_date AS STRING), '-', CAST(event_hour AS STRING)))
                      AS user_hour_slots,
  COUNT(DISTINCT CONCAT(user_name, '-', CAST(event_date AS STRING)))
                      AS person_days,
  CURRENT_TIMESTAMP() AS _loaded_at
FROM analytics.stg_workspace_commands
WHERE task_id    IS NOT NULL
  AND user_name  IS NOT NULL
  AND event_date IS NOT NULL
GROUP BY task_id;

-- COMMAND ----------

-- ★ 적재 확인
SELECT
  COUNT(DISTINCT task_id)       AS total_tasks,
  SUM(user_hour_slots)          AS total_hour_slots,
  SUM(person_days)              AS total_person_days,
  ROUND(AVG(user_hour_slots), 1) AS avg_slots_per_task
FROM analytics.int_command_slots_by_task;
