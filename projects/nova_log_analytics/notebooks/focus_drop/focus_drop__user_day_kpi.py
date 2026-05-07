# Databricks notebook source
# Focus Drop — 사용자 일 KPI 산출 (일 단위 배치)
# 의존성: focus_drop_session_tags, focus_drop_user_thresholds

# COMMAND ----------

dbutils.widgets.text("analysis_date", "", "Analysis Date (YYYY-MM-DD)")

import re
analysis_date = dbutils.widgets.get("analysis_date")
assert re.match(r"^\d{4}-\d{2}-\d{2}$", analysis_date), "analysis_date must be YYYY-MM-DD"

# COMMAND ----------

# 기준선 존재 여부 사전 확인 (safe fail)
threshold_count = spark.sql("""
  SELECT COUNT(*) AS cnt FROM analytics.focus_drop_user_thresholds
""").collect()[0]["cnt"]

if threshold_count == 0:
    raise Exception("ALERT: focus_drop_user_thresholds 비어있음 — Phase B Bootstrap Step 3 (수동 INSERT) 필요. user_day_kpi 적재 스킵.")

# COMMAND ----------

spark.sql(f"""
INSERT INTO analytics.focus_drop_user_day_kpi
REPLACE WHERE analysis_date = '{analysis_date}'
WITH user_daily AS (
  SELECT
    user_id,
    analysis_date,
    SUM(CASE WHEN is_warning_session  THEN 1 ELSE 0 END) AS warning_session_count,
    SUM(CASE WHEN is_critical_session THEN 1 ELSE 0 END) AS critical_session_count,
    SUM(departure_gap_count)                              AS departure_gap_total,
    COUNT(*)                                              AS total_sessions
  FROM analytics.focus_drop_session_tags
  WHERE analysis_date = '{analysis_date}'
  GROUP BY user_id, analysis_date
),
user_thresholds AS (
  SELECT user_warning_session_count_p90, user_critical_session_count_p95, user_departure_gap_total_p99
  FROM analytics.focus_drop_user_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_user_thresholds)
)
SELECT
  d.analysis_date,
  d.user_id,
  d.warning_session_count,
  d.critical_session_count,
  d.departure_gap_total,
  d.total_sessions,
  CASE WHEN d.warning_session_count > 0
        AND d.warning_session_count > t.user_warning_session_count_p90
       THEN TRUE ELSE FALSE END AS is_warning_user,
  CASE WHEN d.critical_session_count > 0
        AND d.critical_session_count > t.user_critical_session_count_p95
       THEN TRUE ELSE FALSE END AS is_critical_user,
  CASE WHEN d.departure_gap_total > 0
        AND d.departure_gap_total > t.user_departure_gap_total_p99
       THEN TRUE ELSE FALSE END AS is_departure_user,
  CASE
    WHEN d.departure_gap_total > 0
         AND d.departure_gap_total > t.user_departure_gap_total_p99    THEN 'departure'
    WHEN d.critical_session_count > 0
         AND d.critical_session_count > t.user_critical_session_count_p95 THEN 'critical'
    WHEN d.warning_session_count > 0
         AND d.warning_session_count > t.user_warning_session_count_p90   THEN 'warning'
    ELSE 'normal'
  END AS user_focus_drop_level
FROM user_daily d
CROSS JOIN user_thresholds t
""")

# COMMAND ----------

# 결과 확인
spark.sql(f"""
SELECT user_focus_drop_level, COUNT(*) AS user_count
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date = '{analysis_date}'
GROUP BY user_focus_drop_level
ORDER BY CASE user_focus_drop_level WHEN 'departure' THEN 1 WHEN 'critical' THEN 2 WHEN 'warning' THEN 3 ELSE 4 END
""").display()

# COMMAND ----------

# Pipeline health check
spark.sql(f"""
SELECT
  CASE
    WHEN (SELECT COUNT(*) FROM analytics.focus_drop_user_day_kpi
          WHERE analysis_date = '{analysis_date}') = 0
     AND (SELECT COUNT(*) FROM analytics.focus_drop_session_tags
          WHERE analysis_date = '{analysis_date}') > 0
    THEN 'ALERT: user_day_kpi 0행 — 기준선 테이블(user_thresholds) 비어있음'
    ELSE 'OK'
  END AS pipeline_health_status
""").display()
