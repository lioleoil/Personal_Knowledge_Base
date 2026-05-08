-- Databricks notebook source
-- Focus Drop — 세션 판정 (일 단위 배치)
-- 의존성: focus_drop_session_metrics, focus_drop_session_thresholds

-- COMMAND ----------

CREATE WIDGET TEXT analysis_date DEFAULT "";

-- COMMAND ----------

-- focus_drop_session_thresholds 미적재 시 CROSS JOIN → 0행 → safe fail
INSERT INTO analytics.focus_drop_session_tags
REPLACE WHERE analysis_date = '${analysis_date}'
WITH thresholds AS (
  SELECT
    session_warning_count_p90, session_critical_count_p95, session_departure_count_p99,
    session_warning_ratio_p90, session_critical_ratio_p95, session_departure_ratio_p99
  FROM analytics.focus_drop_session_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds)
)
SELECT
  m.analysis_date,
  m.user_id, m.session_id, m.task_id,
  m.warning_gap_count, m.critical_gap_count, m.departure_gap_count,
  CASE WHEN m.warning_gap_count > 0
        AND m.warning_gap_count > t.session_warning_count_p90
       THEN TRUE ELSE FALSE END AS is_warning_session,
  CASE WHEN m.critical_gap_count > 0
        AND m.critical_gap_count > t.session_critical_count_p95
       THEN TRUE ELSE FALSE END AS is_critical_session,
  CASE WHEN m.departure_gap_count > 0
        AND m.departure_gap_count > t.session_departure_count_p99
       THEN TRUE ELSE FALSE END AS is_departure_session,
  -- 배타적 최종 레벨 (departure > critical > warning > normal)
  CASE
    WHEN m.departure_gap_count > 0
         AND m.departure_gap_count > t.session_departure_count_p99 THEN 'departure'
    WHEN m.critical_gap_count > 0
         AND m.critical_gap_count > t.session_critical_count_p95   THEN 'critical'
    WHEN m.warning_gap_count > 0
         AND m.warning_gap_count > t.session_warning_count_p90     THEN 'warning'
    ELSE 'normal'
  END AS focus_drop_level
FROM analytics.focus_drop_session_metrics m
CROSS JOIN thresholds t
WHERE m.analysis_date = '${analysis_date}';
-- ratio 보조판정 활성화 시: AND m.warning_gap_ratio > t.session_warning_ratio_p90 추가

-- COMMAND ----------

-- 결과 확인
SELECT focus_drop_level, COUNT(*) AS session_count
FROM analytics.focus_drop_session_tags
WHERE analysis_date = '${analysis_date}'
GROUP BY focus_drop_level
ORDER BY CASE focus_drop_level WHEN 'departure' THEN 1 WHEN 'critical' THEN 2 WHEN 'warning' THEN 3 ELSE 4 END;

-- COMMAND ----------

-- Pipeline health check (기준선 부재 감지)
SELECT
  CASE
    WHEN (SELECT COUNT(*) FROM analytics.focus_drop_session_tags   WHERE analysis_date = '${analysis_date}') = 0
     AND (SELECT COUNT(*) FROM analytics.focus_drop_session_metrics WHERE analysis_date = '${analysis_date}') > 0
    THEN 'ALERT: session_tags 0행 — session_thresholds 비어있음'
    ELSE 'OK'
  END AS pipeline_health_status;
