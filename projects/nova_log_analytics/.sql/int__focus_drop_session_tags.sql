-- Databricks notebook source
-- Intermediate: focus_drop_session_tags (세션 판정, 일 배치)
-- 의존성: focus_drop_session_metrics, focus_drop_session_thresholds

-- COMMAND ----------

CREATE WIDGET TEXT analysis_date DEFAULT "";

-- COMMAND ----------

-- focus_drop_session_thresholds 미적재 시 CROSS JOIN → 0행 → safe fail
INSERT INTO analytics.focus_drop_session_tags
REPLACE WHERE analysis_date = '${analysis_date}'
WITH thresholds AS (
  SELECT
    session_light_count_p90, session_heavy_count_p95, session_idle_count_p99,
    session_light_ratio_p90, session_heavy_ratio_p95, session_idle_ratio_p99
  FROM analytics.focus_drop_session_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds)
)
SELECT
  m.analysis_date,
  m.user_id, m.session_id, m.task_id,
  m.light_gap_count, m.heavy_gap_count, m.idle_gap_count,
  CASE WHEN m.light_gap_count > 0
        AND m.light_gap_count > t.session_light_count_p90
       THEN TRUE ELSE FALSE END AS is_light_session,
  CASE WHEN m.heavy_gap_count > 0
        AND m.heavy_gap_count > t.session_heavy_count_p95
       THEN TRUE ELSE FALSE END AS is_heavy_session,
  CASE WHEN m.idle_gap_count > 0
        AND m.idle_gap_count > t.session_idle_count_p99
       THEN TRUE ELSE FALSE END AS is_idle_session,
  -- 배타적 최종 레벨 (idle > heavy > light > normal)
  CASE
    WHEN m.idle_gap_count > 0
         AND m.idle_gap_count > t.session_idle_count_p99       THEN 'idle'
    WHEN m.heavy_gap_count > 0
         AND m.heavy_gap_count > t.session_heavy_count_p95     THEN 'heavy'
    WHEN m.light_gap_count > 0
         AND m.light_gap_count > t.session_light_count_p90     THEN 'light'
    ELSE 'normal'
  END AS focus_drop_level
FROM analytics.focus_drop_session_metrics m
CROSS JOIN thresholds t
WHERE m.analysis_date = '${analysis_date}';
-- ratio 보조판정 활성화 시: AND m.light_gap_ratio > t.session_light_ratio_p90 추가

-- COMMAND ----------

-- 결과 확인
SELECT focus_drop_level, COUNT(*) AS session_count
FROM analytics.focus_drop_session_tags
WHERE analysis_date = '${analysis_date}'
GROUP BY focus_drop_level
ORDER BY CASE focus_drop_level WHEN 'idle' THEN 1 WHEN 'heavy' THEN 2 WHEN 'light' THEN 3 ELSE 4 END;

-- COMMAND ----------

-- Pipeline health check (기준선 부재 감지)
SELECT
  CASE
    WHEN (SELECT COUNT(*) FROM analytics.focus_drop_session_tags   WHERE analysis_date = '${analysis_date}') = 0
     AND (SELECT COUNT(*) FROM analytics.focus_drop_session_metrics WHERE analysis_date = '${analysis_date}') > 0
    THEN 'ALERT: session_tags 0행 — session_thresholds 비어있음'
    ELSE 'OK'
  END AS pipeline_health_status;
