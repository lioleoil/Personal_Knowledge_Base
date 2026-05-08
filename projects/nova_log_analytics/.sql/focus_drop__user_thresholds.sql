-- Databricks notebook source
-- Focus Drop — 유저 기준선 산출 (주 1회 월요일 03:00 UTC)
-- 의존성: focus_drop_user_day_kpi (직전 rolling_window_days 분)
-- Phase B: 수동 INSERT로 초기화 후 실행 (skill 문서 §12.4 참조)

-- COMMAND ----------

CREATE WIDGET TEXT rolling_window_days DEFAULT "30";
CREATE WIDGET TEXT is_bootstrap         DEFAULT "false";

-- COMMAND ----------

-- 최소 요건 확인
SELECT
  COUNT(DISTINCT analysis_date) AS available_days,
  COUNT(DISTINCT user_id)       AS total_users,
  CASE
    WHEN COUNT(DISTINCT analysis_date) >= ${rolling_window_days} AND COUNT(*) >= 30
    THEN 'READY'
    ELSE 'INSUFFICIENT — is_bootstrap=true 또는 데이터 축적 후 재실행'
  END AS status
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date BETWEEN DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AND DATE_SUB(CURRENT_DATE(), 1);

-- COMMAND ----------

INSERT INTO analytics.focus_drop_user_thresholds
SELECT
  COALESCE((SELECT MAX(version) FROM analytics.focus_drop_user_thresholds), 0) + 1 AS version,
  CURRENT_TIMESTAMP()                               AS computed_at,
  CAST('${is_bootstrap}' AS BOOLEAN)               AS is_bootstrap,
  DATE_SUB(CURRENT_DATE(), ${rolling_window_days})  AS window_start,
  DATE_SUB(CURRENT_DATE(), 1)                       AS window_end,
  PERCENTILE(warning_session_count,  0.90)          AS user_warning_session_count_p90,
  PERCENTILE(critical_session_count, 0.95)          AS user_critical_session_count_p95,
  PERCENTILE(departure_gap_total,    0.99)          AS user_departure_gap_total_p99
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date BETWEEN DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AND DATE_SUB(CURRENT_DATE(), 1);

-- COMMAND ----------

-- 결과 확인
SELECT version, is_bootstrap, window_start, window_end,
       user_warning_session_count_p90, user_critical_session_count_p95, user_departure_gap_total_p99
FROM analytics.focus_drop_user_thresholds
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_user_thresholds);
