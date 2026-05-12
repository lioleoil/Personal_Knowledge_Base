-- Databricks notebook source
-- Inspection Quality — 다중 반려 Task 상세 (inspection reject ≥ 2)
-- 소스: analytics.stg_task_transition_events (reject 이벤트)
--      + sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_tasks (task_name / assignmentId / deliveryId / updatedAt 메타)
-- 실행 주기: 월 1회 (또는 수동)
-- 선행 조건: stg_task_transition_events 갱신 완료
-- 기준값: 26-04 26건 / 26-05 0건

-- COMMAND ----------

-- target_month: 빈 값이면 전체 월 산출, 값 지정 시 해당 월만 갱신 (형식: yy-MM)
CREATE WIDGET TEXT target_month DEFAULT "";

-- COMMAND ----------

INSERT INTO analytics.inspection_quality_multi_reject
REPLACE WHERE (LENGTH('${target_month}') = 0 OR deliver_month = '${target_month}')
WITH delivered_tasks AS (
  SELECT
    t.`_id`                                                              AS task_id,
    get_json_object(t.`_raw`, '$.name')                                  AS task_name,
    get_json_object(t.`_raw`, '$.assignmentId')                          AS assignment_id,
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
inspection_rejects AS (
  SELECT
    task_id,
    DATE_FORMAT(action_at, 'yyyy-MM-dd HH:mm:ss')        AS rejected_at,
    action_by                                            AS rejected_by,
    reason                                               AS reject_reason
  FROM analytics.stg_task_transition_events
  WHERE from_state = 'inspection'
    AND trigger    = 'reject'
)
SELECT
  d.task_id,
  d.task_name,
  d.assignment_id,
  d.deliver_month,
  COUNT(*)                                                             AS reject_count,
  COLLECT_LIST(STRUCT(r.rejected_at, r.rejected_by, r.reject_reason)) AS reject_details
FROM delivered_tasks d
INNER JOIN inspection_rejects r ON d.task_id = r.task_id
GROUP BY d.task_id, d.task_name, d.assignment_id, d.deliver_month
HAVING COUNT(*) >= 2
ORDER BY d.deliver_month, reject_count DESC;

-- COMMAND ----------

-- 결과 확인: 월별 다중 반려 건수 및 최대 반려 횟수
SELECT
  deliver_month,
  COUNT(*)          AS multi_reject_task_count,
  MAX(reject_count) AS max_reject_count
FROM analytics.inspection_quality_multi_reject
GROUP BY deliver_month
ORDER BY deliver_month DESC;
