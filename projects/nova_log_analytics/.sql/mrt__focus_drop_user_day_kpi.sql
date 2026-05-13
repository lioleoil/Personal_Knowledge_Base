-- Databricks notebook source
-- Marts: focus_drop_user_day_kpi (유저 일 KPI 최종 판정, 일 배치)
-- 의존성: focus_drop_session_tags, focus_drop_user_thresholds

-- COMMAND ----------

CREATE WIDGET TEXT analysis_date DEFAULT "";

-- COMMAND ----------

-- focus_drop_user_thresholds 미적재 시 CROSS JOIN → 0행 → safe fail
INSERT INTO analytics.focus_drop_user_day_kpi
REPLACE WHERE analysis_date = '${analysis_date}'
WITH user_daily AS (
  SELECT
    user_id,
    analysis_date,
    SUM(CASE WHEN is_light_session THEN 1 ELSE 0 END) AS light_session_count,
    SUM(CASE WHEN is_heavy_session THEN 1 ELSE 0 END) AS heavy_session_count,
    -- 세션 판정 무관, 모든 세션의 idle gap 누적 절대량
    SUM(idle_gap_count)                                   AS idle_gap_total,
    COUNT(*)                                              AS total_sessions
  FROM analytics.focus_drop_session_tags
  WHERE analysis_date = '${analysis_date}'
  GROUP BY user_id, analysis_date
),
thresholds AS (
  SELECT user_light_session_count_p90, user_heavy_session_count_p95, user_idle_gap_total_p99
  FROM analytics.focus_drop_user_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_user_thresholds)
)
SELECT
  d.analysis_date,
  d.user_id,
  d.light_session_count,
  d.heavy_session_count,
  d.idle_gap_total,
  d.total_sessions,
  CASE WHEN d.light_session_count > 0
        AND d.light_session_count > t.user_light_session_count_p90
       THEN TRUE ELSE FALSE END AS is_light_user,
  CASE WHEN d.heavy_session_count > 0
        AND d.heavy_session_count > t.user_heavy_session_count_p95
       THEN TRUE ELSE FALSE END AS is_heavy_user,
  CASE WHEN d.idle_gap_total > 0
        AND d.idle_gap_total > t.user_idle_gap_total_p99
       THEN TRUE ELSE FALSE END AS is_idle_user,
  -- 배타적 최종 레벨
  CASE
    WHEN d.idle_gap_total > 0
         AND d.idle_gap_total > t.user_idle_gap_total_p99             THEN 'idle'
    WHEN d.heavy_session_count > 0
         AND d.heavy_session_count > t.user_heavy_session_count_p95   THEN 'heavy'
    WHEN d.light_session_count > 0
         AND d.light_session_count > t.user_light_session_count_p90   THEN 'light'
    ELSE 'normal'
  END AS user_focus_drop_level
FROM user_daily d
CROSS JOIN thresholds t;

-- COMMAND ----------

-- 결과 확인
SELECT user_focus_drop_level, COUNT(*) AS user_count
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date = '${analysis_date}'
GROUP BY user_focus_drop_level
ORDER BY CASE user_focus_drop_level WHEN 'idle' THEN 1 WHEN 'heavy' THEN 2 WHEN 'light' THEN 3 ELSE 4 END;

-- COMMAND ----------

-- Pipeline health check
SELECT
  CASE
    WHEN (SELECT COUNT(*) FROM analytics.focus_drop_user_day_kpi   WHERE analysis_date = '${analysis_date}') = 0
     AND (SELECT COUNT(*) FROM analytics.focus_drop_session_tags    WHERE analysis_date = '${analysis_date}') > 0
    THEN 'ALERT: user_day_kpi 0행 — user_thresholds 비어있음'
    ELSE 'OK'
  END AS pipeline_health_status;
