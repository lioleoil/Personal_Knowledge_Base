-- Databricks notebook source
-- Staging: stg_task_transition_events
-- gen2_tasks.transitionHistory 전체 flatten — CDC dedup 포함
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체)
-- 실행 주기: 일 배치 04:00 UTC (Focus Drop 이전 선행 실행)

-- COMMAND ----------

CREATE WIDGET TEXT catalog DEFAULT "sv_nova_dev_an2_catalog";

-- COMMAND ----------

INSERT OVERWRITE analytics.stg_task_transition_events
WITH latest_tasks AS (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__gen2_tasks`
  WHERE `_is_deleted` = false
)
SELECT
  t.`_id`                                                                    AS task_id,
  get_json_object(t.`_raw`, '$.companyId')                                   AS company_id,
  get_json_object(t.`_raw`, '$.policyId')                                    AS policy_id,
  trans.fromState                                                            AS from_state,
  trans.toState                                                              AS to_state,
  trans.trigger                                                              AS trigger,
  trans.actionBy                                                             AS action_by,
  TO_TIMESTAMP(trans.actionAt)                                               AS action_at,
  NULLIF(TRIM(trans.reason), '')                                             AS reason,
  DATE_TRUNC('WEEK',
    CONVERT_TIMEZONE('UTC', 'Asia/Seoul', TO_TIMESTAMP(trans.actionAt))
  )                                                                          AS event_week,
  CURRENT_TIMESTAMP()                                                        AS _loaded_at
FROM latest_tasks t
LATERAL VIEW explode(
  from_json(
    get_json_object(t.`_raw`, '$.transitionHistory'),
    'array<struct<fromState:string,toState:string,trigger:string,actionBy:string,actionAt:string,reason:string,metadata:map<string,string>>>'
  )
) AS trans
WHERE t.rn = 1
  AND trans.actionAt IS NOT NULL;

-- COMMAND ----------

-- ★ 적재 확인
SELECT event_week,
       COUNT(DISTINCT task_id)         AS tasks,
       COUNT(*)                        AS total_events,
       COUNT(DISTINCT from_state || '→' || to_state) AS transition_types
FROM analytics.stg_task_transition_events
WHERE event_week >= DATE_TRUNC('WEEK', CURRENT_DATE() - INTERVAL 28 DAYS)
GROUP BY event_week
ORDER BY event_week DESC;
