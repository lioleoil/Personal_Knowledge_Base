-- Databricks notebook source
-- Marts: mrt_inspection_quality_multi_reject (다중 반려 Task 상세, 월 1회)
-- 소스      : stg_task_transition_events + raw.raw_labelit__gen2_tasks
-- 갱신 전략 : INSERT INTO mrt_inspection_quality_multi_reject REPLACE WHERE deliver_month
-- 실행 주기 : 월 1회 (또는 수동)
-- 파라미터  : target_month (yy-MM) — 빈 값이면 전체 월 재산출
-- 선행 조건 : stg_task_transition_events 갱신 완료
-- 백필      : statement 3에서 stg에 반려 이벤트가 있지만 mrt에 없는 월 자동 복원

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

DECLARE OR REPLACE VARIABLE target_month STRING DEFAULT '';

-- 수동 실행 시: SET VAR target_month = '26-05';

-- COMMAND ----------

-- ★ 당월 적재 (target_month 지정 시 해당 월만, 빈 값이면 전체 월)
INSERT INTO sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_multi_reject
REPLACE WHERE (LENGTH(target_month) = 0 OR deliver_month = target_month)
WITH delivered_tasks AS (
  SELECT
    t.`_id` AS task_id,
    get_json_object(t.`_raw`, '$.name') AS task_name,
    get_json_object(t.`_raw`, '$.assignmentId') AS assignment_id,
    DATE_FORMAT(CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
      TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt'))), 'yy-MM') AS deliver_month
  FROM (
    SELECT `_id`, `_raw`, `_ingested_at`,
           ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_tasks`
    WHERE `_is_deleted` = false
  ) t
  WHERE t.rn = 1
    AND get_json_object(t.`_raw`, '$.deliveryId') IS NOT NULL
    AND (LENGTH(target_month) = 0
         OR DATE_FORMAT(CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
              TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt'))), 'yy-MM') = target_month)
),
inspection_rejects AS (
  SELECT task_id,
    DATE_FORMAT(action_at, 'yyyy-MM-dd HH:mm:ss') AS rejected_at,
    action_by AS rejected_by,
    NULLIF(TRIM(reason), '') AS reject_reason
  FROM sv_nova_dev_an2_catalog.analytics.stg_task_transition_events
  WHERE from_state = 'inspection' AND trigger = 'reject'
)
SELECT d.task_id, d.task_name, d.assignment_id, d.deliver_month,
  COUNT(*) AS reject_count,
  COLLECT_LIST(STRUCT(r.rejected_at, r.rejected_by, r.reject_reason)) AS reject_details
FROM delivered_tasks d
INNER JOIN inspection_rejects r ON d.task_id = r.task_id
GROUP BY d.task_id, d.task_name, d.assignment_id, d.deliver_month
HAVING COUNT(*) >= 2
ORDER BY d.deliver_month, reject_count DESC;

-- COMMAND ----------

-- ★ Gap 백필: stg에 반려 이벤트가 있지만 mrt에 없는 월 자동 복원
INSERT INTO sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_multi_reject
REPLACE WHERE deliver_month IN (
  SELECT DISTINCT DATE_FORMAT(
    CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
      TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt'))), 'yy-MM'
  )
  FROM (
    SELECT `_id`, `_raw`, `_ingested_at`,
           ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_tasks`
    WHERE `_is_deleted` = false
  ) t
  WHERE t.rn = 1
    AND get_json_object(t.`_raw`, '$.deliveryId') IS NOT NULL
    AND DATE_FORMAT(CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
          TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt'))), 'yy-MM')
        NOT IN (SELECT DISTINCT deliver_month FROM sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_multi_reject)
    AND DATE_FORMAT(CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
          TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt'))), 'yy-MM')
        < DATE_FORMAT(CURRENT_DATE(), 'yy-MM')
)
WITH missing_months AS (
  SELECT DISTINCT DATE_FORMAT(
    CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
      TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt'))), 'yy-MM'
  ) AS deliver_month
  FROM (
    SELECT `_id`, `_raw`, `_ingested_at`,
           ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_tasks`
    WHERE `_is_deleted` = false
  ) t
  WHERE t.rn = 1
    AND get_json_object(t.`_raw`, '$.deliveryId') IS NOT NULL
    AND DATE_FORMAT(CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
          TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt'))), 'yy-MM')
        NOT IN (SELECT DISTINCT deliver_month FROM sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_multi_reject)
    AND DATE_FORMAT(CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
          TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt'))), 'yy-MM')
        < DATE_FORMAT(CURRENT_DATE(), 'yy-MM')
),
delivered_tasks AS (
  SELECT t.`_id` AS task_id,
    get_json_object(t.`_raw`, '$.name') AS task_name,
    get_json_object(t.`_raw`, '$.assignmentId') AS assignment_id,
    DATE_FORMAT(CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
      TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt'))), 'yy-MM') AS deliver_month
  FROM (
    SELECT `_id`, `_raw`, `_ingested_at`,
           ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_tasks`
    WHERE `_is_deleted` = false
  ) t
  WHERE t.rn = 1
    AND get_json_object(t.`_raw`, '$.deliveryId') IS NOT NULL
    AND DATE_FORMAT(CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
          TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt'))), 'yy-MM')
        IN (SELECT deliver_month FROM missing_months)
),
inspection_rejects AS (
  SELECT task_id,
    DATE_FORMAT(action_at, 'yyyy-MM-dd HH:mm:ss') AS rejected_at,
    action_by AS rejected_by,
    NULLIF(TRIM(reason), '') AS reject_reason
  FROM sv_nova_dev_an2_catalog.analytics.stg_task_transition_events
  WHERE from_state = 'inspection' AND trigger = 'reject'
)
SELECT d.task_id, d.task_name, d.assignment_id, d.deliver_month,
  COUNT(*) AS reject_count,
  COLLECT_LIST(STRUCT(r.rejected_at, r.rejected_by, r.reject_reason)) AS reject_details
FROM delivered_tasks d
INNER JOIN inspection_rejects r ON d.task_id = r.task_id
GROUP BY d.task_id, d.task_name, d.assignment_id, d.deliver_month
HAVING COUNT(*) >= 2;

-- COMMAND ----------

-- ★ 적재 확인
SELECT deliver_month,
  COUNT(*) AS multi_reject_task_count,
  MAX(reject_count) AS max_reject_count
FROM sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_multi_reject
GROUP BY deliver_month
ORDER BY deliver_month DESC;