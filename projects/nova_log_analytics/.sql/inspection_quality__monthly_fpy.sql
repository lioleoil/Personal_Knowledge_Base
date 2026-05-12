-- Databricks notebook source
-- Inspection Quality — 월별 검수 반려율 & First Pass Yield
-- 소스: analytics.stg_task_transition_events (reject 이벤트)
--      + sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_tasks (deliveryId / updatedAt 메타)
-- 실행 주기: 월 1회 (또는 수동)
-- 선행 조건: stg_task_transition_events 갱신 완료
-- 기준값: 26-04 FPY 69.23% / 26-05 FPY 98.65%

-- COMMAND ----------

-- target_month: 빈 값이면 전체 월 산출, 값 지정 시 해당 월만 갱신 (형식: yy-MM)
CREATE WIDGET TEXT target_month DEFAULT "";

-- COMMAND ----------

INSERT INTO analytics.inspection_quality_monthly_fpy
REPLACE WHERE (LENGTH('${target_month}') = 0 OR deliver_month = '${target_month}')
WITH delivered_tasks AS (
  SELECT
    t.`_id`                                                              AS task_id,
    DATE_FORMAT(
      TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt')), 'yy-MM'
    )                                                                    AS deliver_month
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_tasks`
    WHERE `_is_deleted` = false
  ) t
  WHERE t.rn = 1
    AND get_json_object(t.`_raw`, '$.deliveryId') IS NOT NULL
    AND (
      LENGTH('${target_month}') = 0
      OR DATE_FORMAT(TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt')), 'yy-MM') = '${target_month}'
    )
),
reject_stats AS (
  SELECT
    task_id,
    COUNT(*)            AS inspection_reject_count,
    COLLECT_SET(reason) AS reject_reasons
  FROM analytics.stg_task_transition_events
  WHERE from_state = 'inspection'
    AND trigger    = 'reject'
  GROUP BY task_id
)
SELECT
  d.deliver_month,
  COUNT(*)                                                             AS total_inspected,
  SUM(CASE WHEN r.inspection_reject_count > 0 THEN 1 ELSE 0 END)       AS rejected_count,
  ROUND(
    SUM(CASE WHEN r.inspection_reject_count > 0 THEN 1 ELSE 0 END)
    / COUNT(*) * 100, 2
  )                                                                    AS rejection_rate_pct,
  ROUND(
    100 - SUM(CASE WHEN r.inspection_reject_count > 0 THEN 1 ELSE 0 END)
          / COUNT(*) * 100, 2
  )                                                                    AS first_pass_yield_pct,
  FLATTEN(COLLECT_SET(r.reject_reasons))                               AS distinct_reasons
FROM delivered_tasks d
LEFT JOIN reject_stats r ON d.task_id = r.task_id
GROUP BY d.deliver_month
ORDER BY d.deliver_month;

-- COMMAND ----------

-- 결과 확인
SELECT
  deliver_month,
  total_inspected,
  rejected_count,
  rejection_rate_pct,
  first_pass_yield_pct,
  SIZE(distinct_reasons) AS distinct_reason_count
FROM analytics.inspection_quality_monthly_fpy
ORDER BY deliver_month DESC;
