-- Databricks notebook source
-- Staging: stg_task_transition_events
-- gen2_tasks.transitionHistory 전체 flatten — CDC dedup 포함
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체)
-- 실행 주기: 일 배치 04:00 UTC (Focus Drop 이전 선행 실행)

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.stg_task_transition_events (
  task_id        STRING    COMMENT 'gen2_tasks._id',
  company_id     STRING    COMMENT 'task.companyId',
  policy_id      STRING    COMMENT 'task.policyId',
  from_state     STRING    COMMENT 'transitionHistory.fromState',
  to_state       STRING    COMMENT 'transitionHistory.toState',
  trigger        STRING    COMMENT 'transitionHistory.trigger',
  action_by      STRING    COMMENT 'transitionHistory.actionBy',
  action_at      TIMESTAMP COMMENT 'transitionHistory.actionAt (UTC)',
  reason         STRING    COMMENT 'transitionHistory.reason (정규화)',
  event_week     TIMESTAMP COMMENT 'actionAt 기준 KST 주 시작일',
  _loaded_at     TIMESTAMP COMMENT '적재 시각'
)
COMMENT 'Task 상태 전환 이력 (flatten). 일 배치 전체 교체.'
TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

INSERT OVERWRITE sv_nova_dev_an2_catalog.analytics.stg_task_transition_events
WITH latest_tasks AS (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_tasks`
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
FROM sv_nova_dev_an2_catalog.analytics.stg_task_transition_events
WHERE event_week >= DATE_TRUNC('WEEK', CURRENT_DATE() - INTERVAL 28 DAYS)
GROUP BY event_week
ORDER BY event_week DESC;