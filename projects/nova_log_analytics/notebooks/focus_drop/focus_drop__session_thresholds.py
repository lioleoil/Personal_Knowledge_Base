# Databricks notebook source
# Focus Drop — 세션 기준선 산출 (주 1회 월요일 03:00 UTC)
# 의존성: focus_drop_session_metrics (직전 rolling_window_days 분)

# COMMAND ----------

dbutils.widgets.text("rolling_window_days", "30", "Rolling Window Days")
dbutils.widgets.text("is_bootstrap", "false", "Is Bootstrap Run (true/false)")

rolling_window_days = int(dbutils.widgets.get("rolling_window_days"))
is_bootstrap = dbutils.widgets.get("is_bootstrap").lower() == "true"

print(f"rolling_window_days={rolling_window_days}, is_bootstrap={is_bootstrap}")

# COMMAND ----------

# 최소 요건 체크
status = spark.sql(f"""
SELECT
  COUNT(DISTINCT analysis_date) AS available_days,
  COUNT(*) AS total_sessions,
  CASE WHEN COUNT(DISTINCT analysis_date) >= {rolling_window_days} AND COUNT(*) >= 100
       THEN 'READY' ELSE 'INSUFFICIENT' END AS status
FROM analytics.focus_drop_session_metrics
WHERE analysis_date BETWEEN DATE_SUB(CURRENT_DATE(), {rolling_window_days}) AND DATE_SUB(CURRENT_DATE(), 1)
""").collect()[0]

print(f"데이터 현황 — {status['available_days']}일분, {status['total_sessions']}세션: {status['status']}")
if status["status"] == "INSUFFICIENT" and not is_bootstrap:
    raise Exception(f"데이터 부족 ({status['available_days']}일 / {status['total_sessions']}세션). is_bootstrap=true로 실행하거나 데이터 축적 후 재시도.")

# COMMAND ----------

spark.sql(f"""
INSERT INTO analytics.focus_drop_session_thresholds
SELECT
  COALESCE((SELECT MAX(version) FROM analytics.focus_drop_session_thresholds), 0) + 1 AS version,
  CURRENT_TIMESTAMP()                              AS computed_at,
  {'TRUE' if is_bootstrap else 'FALSE'}            AS is_bootstrap,
  DATE_SUB(CURRENT_DATE(), {rolling_window_days})  AS window_start,
  DATE_SUB(CURRENT_DATE(), 1)                      AS window_end,
  PERCENTILE(warning_gap_count,   0.90)            AS session_warning_count_p90,
  PERCENTILE(critical_gap_count,  0.95)            AS session_critical_count_p95,
  PERCENTILE(departure_gap_count, 0.99)            AS session_departure_count_p99,
  PERCENTILE(warning_gap_ratio,   0.90)            AS session_warning_ratio_p90,
  PERCENTILE(critical_gap_ratio,  0.95)            AS session_critical_ratio_p95,
  PERCENTILE(departure_gap_ratio, 0.99)            AS session_departure_ratio_p99
FROM analytics.focus_drop_session_metrics
WHERE analysis_date BETWEEN DATE_SUB(CURRENT_DATE(), {rolling_window_days}) AND DATE_SUB(CURRENT_DATE(), 1)
""")

# COMMAND ----------

# zero-inflation 보정 (threshold = 0이면 최솟값 1로 올림)
spark.sql("""
UPDATE analytics.focus_drop_session_thresholds
SET session_departure_count_p99 = GREATEST(session_departure_count_p99, 1),
    session_critical_count_p95  = GREATEST(session_critical_count_p95, 1),
    session_warning_count_p90   = GREATEST(session_warning_count_p90, 1)
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds)
  AND (session_departure_count_p99 = 0
    OR session_critical_count_p95  = 0
    OR session_warning_count_p90   = 0)
""")

# COMMAND ----------

# 결과 확인
spark.sql("""
SELECT version, is_bootstrap, window_start, window_end,
       session_warning_count_p90, session_critical_count_p95, session_departure_count_p99
FROM analytics.focus_drop_session_thresholds
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds)
""").display()
