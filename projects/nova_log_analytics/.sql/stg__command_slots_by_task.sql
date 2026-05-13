-- Databricks notebook source
-- Staging: stg_command_slots_by_task
-- workspace_command → task별 투입 자원 집계 (전체 기간 합산)
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체)
-- 실행 주기: 일 배치 04:00 UTC

-- COMMAND ----------

CREATE WIDGET TEXT catalog DEFAULT "sv_nova_dev_an2_catalog";

-- COMMAND ----------

INSERT OVERWRITE analytics.stg_command_slots_by_task
WITH latest_commands AS (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__workspace_command`
  WHERE `_is_deleted` = false
)
SELECT
  `_raw`:data.project.task_id::STRING AS task_id,
  COUNT(DISTINCT CONCAT(
    `_raw`:data.user.name::STRING, '-',
    DATE_FORMAT(
      CONVERT_TIMEZONE('UTC', 'Asia/Seoul', TO_TIMESTAMP(`_raw`:time::STRING)),
      'yyyy-MM-dd HH'
    )
  ))                                  AS user_hour_slots,
  COUNT(DISTINCT CONCAT(
    `_raw`:data.user.name::STRING, '-',
    DATE(CONVERT_TIMEZONE('UTC', 'Asia/Seoul', TO_TIMESTAMP(`_raw`:time::STRING)))
  ))                                  AS person_days,
  CURRENT_TIMESTAMP()                 AS _loaded_at
FROM latest_commands
WHERE rn = 1
  AND `_raw`:data.user.name::STRING       IS NOT NULL
  AND `_raw`:data.project.task_id::STRING IS NOT NULL
GROUP BY 1;

-- COMMAND ----------

-- ★ 적재 확인
SELECT COUNT(DISTINCT task_id)    AS total_tasks,
       SUM(user_hour_slots)       AS total_hour_slots,
       SUM(person_days)           AS total_person_days,
       ROUND(AVG(user_hour_slots), 1) AS avg_slots_per_task
FROM analytics.stg_command_slots_by_task;
