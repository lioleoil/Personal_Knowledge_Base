-- Databricks notebook source
-- Marts: mrt_focus_drop_user_day_kpi (유저 일 KPI 최종 판정, 일 배치)
-- 의존성  : int_focus_drop_user_day_kpi, int_focus_drop_user_thresholds
-- 갱신 전략 : INSERT INTO mrt_focus_drop_user_day_kpi REPLACE WHERE analysis_date
-- 실행 주기 : 일 배치 (focus_drop_daily Job 후행)
-- 파라미터  : analysis_date (YYYY-MM-DD) — 미입력 시 어제 자동 산출
-- 선행 조건 : int__focus_drop_user_day_kpi + int__focus_drop_user_thresholds 적재 완료
-- 백필      : statement 3에서 int_focus_drop_user_day_kpi에 있지만 mrt에 없는 날짜 자동 복원

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

-- ★ 당일 적재 (어제 기준)
INSERT INTO sv_nova_dev_an2_catalog.analytics.mrt_focus_drop_user_day_kpi
REPLACE WHERE analysis_date = CURRENT_DATE() - INTERVAL 1 DAY
WITH user_daily AS (
  SELECT analysis_date, user_id, light_session_count, heavy_session_count, idle_gap_total, total_sessions
  FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi
  WHERE analysis_date = CURRENT_DATE() - INTERVAL 1 DAY
),
thresholds AS (
  SELECT user_light_session_count_p90, user_heavy_session_count_p95, user_idle_gap_total_p99
  FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_thresholds
  WHERE version = (SELECT MAX(version) FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_thresholds)
)
SELECT
  d.analysis_date, d.user_id,
  d.light_session_count, d.heavy_session_count, d.idle_gap_total, d.total_sessions,
  CASE WHEN d.light_session_count > 0 AND d.light_session_count > t.user_light_session_count_p90 THEN TRUE ELSE FALSE END AS is_light_user,
  CASE WHEN d.heavy_session_count > 0 AND d.heavy_session_count > t.user_heavy_session_count_p95 THEN TRUE ELSE FALSE END AS is_heavy_user,
  CASE WHEN d.idle_gap_total > 0 AND d.idle_gap_total > t.user_idle_gap_total_p99 THEN TRUE ELSE FALSE END AS is_idle_user,
  CASE
    WHEN d.idle_gap_total > 0 AND d.idle_gap_total > t.user_idle_gap_total_p99 THEN 'idle'
    WHEN d.heavy_session_count > 0 AND d.heavy_session_count > t.user_heavy_session_count_p95 THEN 'heavy'
    WHEN d.light_session_count > 0 AND d.light_session_count > t.user_light_session_count_p90 THEN 'light'
    ELSE 'normal'
  END AS user_focus_drop_level
FROM user_daily d
CROSS JOIN thresholds t;

-- COMMAND ----------

-- ★ Gap 백필: int_focus_drop_user_day_kpi에 있지만 mrt에 없는 날짜 자동 복원
INSERT INTO sv_nova_dev_an2_catalog.analytics.mrt_focus_drop_user_day_kpi
REPLACE WHERE analysis_date IN (
  SELECT DISTINCT i.analysis_date
  FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi i
  WHERE NOT EXISTS (
    SELECT 1 FROM sv_nova_dev_an2_catalog.analytics.mrt_focus_drop_user_day_kpi m
    WHERE m.analysis_date = i.analysis_date
  )
  AND i.analysis_date < CURRENT_DATE() - INTERVAL 1 DAY
)
WITH missing_dates AS (
  SELECT DISTINCT i.analysis_date
  FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi i
  WHERE NOT EXISTS (
    SELECT 1 FROM sv_nova_dev_an2_catalog.analytics.mrt_focus_drop_user_day_kpi m
    WHERE m.analysis_date = i.analysis_date
  )
  AND i.analysis_date < CURRENT_DATE() - INTERVAL 1 DAY
),
user_daily AS (
  SELECT analysis_date, user_id, light_session_count, heavy_session_count, idle_gap_total, total_sessions
  FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi
  WHERE analysis_date IN (SELECT analysis_date FROM missing_dates)
),
thresholds AS (
  SELECT user_light_session_count_p90, user_heavy_session_count_p95, user_idle_gap_total_p99
  FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_thresholds
  WHERE version = (SELECT MAX(version) FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_thresholds)
)
SELECT
  d.analysis_date, d.user_id,
  d.light_session_count, d.heavy_session_count, d.idle_gap_total, d.total_sessions,
  CASE WHEN d.light_session_count > 0 AND d.light_session_count > t.user_light_session_count_p90 THEN TRUE ELSE FALSE END AS is_light_user,
  CASE WHEN d.heavy_session_count > 0 AND d.heavy_session_count > t.user_heavy_session_count_p95 THEN TRUE ELSE FALSE END AS is_heavy_user,
  CASE WHEN d.idle_gap_total > 0 AND d.idle_gap_total > t.user_idle_gap_total_p99 THEN TRUE ELSE FALSE END AS is_idle_user,
  CASE
    WHEN d.idle_gap_total > 0 AND d.idle_gap_total > t.user_idle_gap_total_p99 THEN 'idle'
    WHEN d.heavy_session_count > 0 AND d.heavy_session_count > t.user_heavy_session_count_p95 THEN 'heavy'
    WHEN d.light_session_count > 0 AND d.light_session_count > t.user_light_session_count_p90 THEN 'light'
    ELSE 'normal'
  END AS user_focus_drop_level
FROM user_daily d
CROSS JOIN thresholds t;

-- COMMAND ----------

-- ★ 적재 확인
SELECT user_focus_drop_level, COUNT(*) AS user_count
FROM sv_nova_dev_an2_catalog.analytics.mrt_focus_drop_user_day_kpi
WHERE analysis_date >= CURRENT_DATE() - INTERVAL 7 DAYS
GROUP BY user_focus_drop_level
ORDER BY CASE user_focus_drop_level
  WHEN 'idle' THEN 1 WHEN 'heavy' THEN 2 WHEN 'light' THEN 3 ELSE 4
END;