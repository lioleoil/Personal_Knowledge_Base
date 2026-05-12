-- Databricks notebook source
-- Staging: stg_cmd_slots_by_task
-- workspace_command → task별 투입 자원 집계 (전체 기간 합산)
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체)
-- 실행 주기: 일 배치 04:00 UTC

-- COMMAND ----------

INSERT OVERWRITE analytics.stg_cmd_slots_by_task
SELECT
  `_raw`:taskId::STRING AS task_id,
  COUNT(DISTINCT CONCAT(
    `_raw`:userName::STRING, '-',
    DATE_FORMAT(
      CONVERT_TIMEZONE('UTC', 'Asia/Seoul', TO_TIMESTAMP(`_raw`:createdAt::STRING)),
      'yyyy-MM-dd HH'
    )
  ))                    AS user_hour_slots,
  COUNT(DISTINCT CONCAT(
    `_raw`:userName::STRING, '-',
    DATE(CONVERT_TIMEZONE('UTC', 'Asia/Seoul', TO_TIMESTAMP(`_raw`:createdAt::STRING)))
  ))                    AS person_days,
  CURRENT_TIMESTAMP()   AS refreshed_at
FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__workspace_command`
WHERE `_is_deleted` = false
  AND `_raw`:userName::STRING IS NOT NULL
  AND `_raw`:taskId::STRING   IS NOT NULL
GROUP BY 1;

-- COMMAND ----------

-- ★ 적재 확인
SELECT COUNT(DISTINCT task_id)    AS total_tasks,
       SUM(user_hour_slots)       AS total_hour_slots,
       SUM(person_days)           AS total_person_days,
       ROUND(AVG(user_hour_slots), 1) AS avg_slots_per_task
FROM analytics.stg_cmd_slots_by_task;
