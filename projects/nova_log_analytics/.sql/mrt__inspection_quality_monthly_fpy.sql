-- Databricks notebook source
-- Marts: mrt_inspection_quality_monthly_fpy (월별 검수 반려율 & First Pass Yield)
-- 소스      : stg_task_transition_events + raw.raw_labelit__gen2_tasks
-- 갱신 전략 : INSERT INTO mrt_inspection_quality_monthly_fpy REPLACE WHERE deliver_month
-- 실행 주기 : 월 1회 (또는 수동)
-- 파라미터  : target_month (yy-MM) — 빈 값이면 전체 월 재산출
-- 선행 조건 : stg_task_transition_events 갱신 완료
-- 백필      : statement 3에서 stg에 납품 이벤트가 있지만 mrt에 없는 월 자동 복원

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

DECLARE OR REPLACE VARIABLE target_month STRING DEFAULT '';

-- 수동 실행 시: SET VAR target_month = '26-05';

-- COMMAND ----------

-- ★ 당월 적재 (target_month 지정 시 해당 월만, 빈 값이면 전체 월)
INSERT INTO sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_monthly_fpy
REPLACE WHERE (LENGTH(target_month) = 0 OR deliver_month = target_month)
WITH delivered_tasks AS (
  SELECT
    t.`_id` AS task_id,
    DATE_FORMAT(
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
    AND (LENGTH(target_month) = 0
         OR DATE_FORMAT(CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
              TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt'))), 'yy-MM') = target_month)
),
reject_stats AS (
  SELECT task_id,
    COUNT(*) AS inspection_reject_count,
    COLLECT_SET(NULLIF(TRIM(reason), '')) AS reject_reasons
  FROM sv_nova_dev_an2_catalog.analytics.stg_task_transition_events
  WHERE from_state = 'inspection' AND trigger = 'reject'
  GROUP BY task_id
)
SELECT
  d.deliver_month,
  COUNT(*) AS total_inspected,
  SUM(CASE WHEN r.inspection_reject_count > 0 THEN 1 ELSE 0 END) AS rejected_count,
  ROUND(SUM(CASE WHEN r.inspection_reject_count > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS rejection_rate_pct,
  ROUND(100 - SUM(CASE WHEN r.inspection_reject_count > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS first_pass_yield_pct,
  FLATTEN(COLLECT_SET(r.reject_reasons)) AS distinct_reasons
FROM delivered_tasks d
LEFT JOIN reject_stats r ON d.task_id = r.task_id
GROUP BY d.deliver_month
ORDER BY d.deliver_month;

-- COMMAND ----------

-- ★ Gap 백필: stg에 납품 이벤트가 있지만 mrt에 없는 월 자동 복원
INSERT INTO sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_monthly_fpy
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
        NOT IN (SELECT DISTINCT deliver_month FROM sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_monthly_fpy)
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
        NOT IN (SELECT DISTINCT deliver_month FROM sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_monthly_fpy)
    AND DATE_FORMAT(CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
          TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt'))), 'yy-MM')
        < DATE_FORMAT(CURRENT_DATE(), 'yy-MM')
),
delivered_tasks AS (
  SELECT t.`_id` AS task_id,
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
reject_stats AS (
  SELECT task_id, COUNT(*) AS inspection_reject_count,
    COLLECT_SET(NULLIF(TRIM(reason), '')) AS reject_reasons
  FROM sv_nova_dev_an2_catalog.analytics.stg_task_transition_events
  WHERE from_state = 'inspection' AND trigger = 'reject'
  GROUP BY task_id
)
SELECT d.deliver_month,
  COUNT(*) AS total_inspected,
  SUM(CASE WHEN r.inspection_reject_count > 0 THEN 1 ELSE 0 END) AS rejected_count,
  ROUND(SUM(CASE WHEN r.inspection_reject_count > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS rejection_rate_pct,
  ROUND(100 - SUM(CASE WHEN r.inspection_reject_count > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS first_pass_yield_pct,
  FLATTEN(COLLECT_SET(r.reject_reasons)) AS distinct_reasons
FROM delivered_tasks d
LEFT JOIN reject_stats r ON d.task_id = r.task_id
GROUP BY d.deliver_month;

-- COMMAND ----------

-- ★ 적재 확인
SELECT deliver_month, total_inspected, rejected_count,
  rejection_rate_pct, first_pass_yield_pct,
  SIZE(distinct_reasons) AS distinct_reason_count
FROM sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_monthly_fpy
ORDER BY deliver_month DESC;