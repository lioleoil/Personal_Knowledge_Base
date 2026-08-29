-- Databricks notebook source
-- Staging: stg_tasks
-- gen2_tasks CDC dedup, 태스크 핵심 속성 추출 (row-level, 집계 없음)
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체)
-- 실행 주기: 일 배치 04:00 UTC (stg_task_transition_events 와 동일 선행 레이어)

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.stg_tasks (
  task_id        STRING    COMMENT 'gen2_tasks._id (PK)',
  company_id     STRING    COMMENT 'task.companyId — 작업 소속 회사 ID',
  policy_id      STRING    COMMENT 'task.policyId — 적용된 어노테이션 정책 ID',
  status         STRING    COMMENT 'task.currentState — 현재 상태 (labeling, inspection 등)',
  stage_key      STRING    COMMENT 'task.currentStageKey — 현재 Stage Key',
  created_at     TIMESTAMP COMMENT 'task.createdAt — 태스크 생성 시각 (UTC)',
  created_week   DATE      COMMENT 'createdAt 기준 KST 변환 후 주 시작일 (DATE_TRUNC WEEK)',
  _loaded_at     TIMESTAMP COMMENT '데이터 적재 시각 (CURRENT_TIMESTAMP at INSERT)',
  assignment_id  STRING    COMMENT 'task.assignmentId — 소속 어사인먼트 ID (dim_assignments FK)'
)
COMMENT 'Task 핵심 속성 (CDC dedup). 소스: raw.raw_labelit__gen2_tasks. 갱신: INSERT OVERWRITE (일 전체 교체). 실행 주기: 일 배치 04:00 UTC.'
PARTITIONED BY (created_week)
TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

INSERT OVERWRITE sv_nova_dev_an2_catalog.analytics.stg_tasks
WITH latest_tasks AS (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_tasks`
  WHERE `_is_deleted` = false
)
SELECT
  `_id`                                                                       AS task_id,
  get_json_object(`_raw`, '$.companyId')                                      AS company_id,
  get_json_object(`_raw`, '$.policyId')                                       AS policy_id,
  get_json_object(`_raw`, '$.currentState')                                   AS status,
  get_json_object(`_raw`, '$.currentStageKey')                                AS stage_key,
  TO_TIMESTAMP(get_json_object(`_raw`, '$.createdAt'))                        AS created_at,
  CAST(DATE_TRUNC('WEEK',
    CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
      TO_TIMESTAMP(get_json_object(`_raw`, '$.createdAt')))
  ) AS DATE)                                                                  AS created_week,
  CURRENT_TIMESTAMP()                                                         AS _loaded_at,
  get_json_object(`_raw`, '$.assignmentId')                                   AS assignment_id
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
FROM sv_nova_dev_an2_catalog.analytics.stg_tasks
WHERE created_week >= DATE_TRUNC('WEEK', CURRENT_DATE() - INTERVAL 28 DAYS)
GROUP BY created_week
ORDER BY created_week DESC;