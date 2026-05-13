-- Databricks notebook source
-- Intermediate: focus_drop_session_thresholds (세션 기준선 산출, 주 1회)
-- 의존성: focus_drop_session_metrics (직전 rolling_window_days 분)

-- COMMAND ----------

CREATE WIDGET TEXT rolling_window_days DEFAULT "30";
CREATE WIDGET TEXT is_bootstrap         DEFAULT "false";

-- COMMAND ----------

-- 최소 요건 확인 (실행 전 데이터 현황 점검)
SELECT
  COUNT(DISTINCT analysis_date) AS available_days,
  COUNT(*)                      AS total_sessions,
  CASE
    WHEN COUNT(DISTINCT analysis_date) >= ${rolling_window_days} AND COUNT(*) >= 100
    THEN 'READY'
    ELSE 'INSUFFICIENT — is_bootstrap=true 또는 데이터 축적 후 재실행'
  END AS status
FROM analytics.focus_drop_session_metrics
WHERE analysis_date BETWEEN DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AND DATE_SUB(CURRENT_DATE(), 1);

-- COMMAND ----------

INSERT INTO analytics.focus_drop_session_thresholds
SELECT
  COALESCE((SELECT MAX(version) FROM analytics.focus_drop_session_thresholds), 0) + 1 AS version,
  CURRENT_TIMESTAMP()                               AS computed_at,
  CAST('${is_bootstrap}' AS BOOLEAN)               AS is_bootstrap,
  DATE_SUB(CURRENT_DATE(), ${rolling_window_days})  AS window_start,
  DATE_SUB(CURRENT_DATE(), 1)                       AS window_end,
  PERCENTILE(light_gap_count,     0.90)             AS session_light_count_p90,
  PERCENTILE(heavy_gap_count,     0.95)             AS session_heavy_count_p95,
  PERCENTILE(idle_gap_count,      0.99)             AS session_idle_count_p99,
  PERCENTILE(light_gap_ratio,     0.90)             AS session_light_ratio_p90,
  PERCENTILE(heavy_gap_ratio,     0.95)             AS session_heavy_ratio_p95,
  PERCENTILE(idle_gap_ratio,      0.99)             AS session_idle_ratio_p99
FROM analytics.focus_drop_session_metrics
WHERE analysis_date BETWEEN DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AND DATE_SUB(CURRENT_DATE(), 1);

-- COMMAND ----------

-- zero-inflation 보정 (threshold = 0이면 최솟값 1로 올림 → 단일 gap 오탐 방지)
UPDATE analytics.focus_drop_session_thresholds
SET session_idle_count_p99    = GREATEST(session_idle_count_p99, 1),
    session_heavy_count_p95   = GREATEST(session_heavy_count_p95, 1),
    session_light_count_p90   = GREATEST(session_light_count_p90, 1)
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds)
  AND (session_idle_count_p99   = 0
    OR session_heavy_count_p95  = 0
    OR session_light_count_p90  = 0);

-- COMMAND ----------

-- 결과 확인
SELECT version, is_bootstrap, window_start, window_end,
       session_light_count_p90, session_heavy_count_p95, session_idle_count_p99
FROM analytics.focus_drop_session_thresholds
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds);
