-- Databricks notebook source
-- Staging: stg_tasks
-- gen2_tasks CDC dedup, 태스크 핵심 속성 추출 (row-level, 집계 없음)
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체)
-- 실행 주기: 일 배치 04:00 UTC (stg_task_transition_events 와 동일 선행 레이어)

-- COMMAND ----------

CREATE WIDGET TEXT catalog DEFAULT "sv_nova_dev_an2_catalog";

-- COMMAND ----------

INSERT OVERWRITE analytics.stg_tasks
WITH latest_tasks AS (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__gen2_tasks`
  WHERE `_is_deleted` = false
)
SELECT
  `_id`                                                                       AS task_id,
  get_json_object(`_raw`, '$.companyId')                                      AS company_id,
  get_json_object(`_raw`, '$.policyId')                                       AS policy_id,
  get_json_object(`_raw`, '$.status')                                         AS status,
  get_json_object(`_raw`, '$.stageKey')                                       AS stage_key,
  TO_TIMESTAMP(get_json_object(`_raw`, '$.createdAt'))                        AS created_at,
  DATE_TRUNC('WEEK',
    CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
      TO_TIMESTAMP(get_json_object(`_raw`, '$.createdAt')))
  )                                                                           AS created_week,
  CURRENT_TIMESTAMP()                                                         AS _loaded_at
FROM latest_tasks
WHERE rn = 1
  AND get_json_object(`_raw`, '$.createdAt') IS NOT NULL;

-- COMMAND ----------

-- ★ 적재 확인
SELECT
  created_week,
  COUNT(DISTINCT task_id)                              AS tasks,
  COUNT(DISTINCT company_id)                           AS companies,
  COUNT(DISTINCT policy_id)                            AS policies,
  COUNT(DISTINCT status)                               AS status_types
FROM analytics.stg_tasks
WHERE created_week >= DATE_TRUNC('WEEK', CURRENT_DATE() - INTERVAL 28 DAYS)
GROUP BY created_week
ORDER BY created_week DESC;
