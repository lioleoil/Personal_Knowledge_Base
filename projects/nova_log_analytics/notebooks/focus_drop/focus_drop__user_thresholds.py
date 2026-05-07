# Databricks notebook source
# Focus Drop — 유저 기준선 산출 (주 1회 월요일 03:00 UTC)
# 의존성: focus_drop_user_day_kpi (직전 rolling_window_days 분)
# 주의: Phase B에서는 수동 INSERT로 초기화 후 이 노트북 실행 (skill 문서 §12.4 참조)

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
  COUNT(DISTINCT user_id) AS total_users,
  CASE WHEN COUNT(DISTINCT analysis_date) >= {rolling_window_days} AND COUNT(*) >= 30
       THEN 'READY' ELSE 'INSUFFICIENT' END AS status
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date BETWEEN DATE_SUB(CURRENT_DATE(), {rolling_window_days}) AND DATE_SUB(CURRENT_DATE(), 1)
""").collect()[0]

print(f"데이터 현황 — {status['available_days']}일분, {status['total_users']}명: {status['status']}")
if status["status"] == "INSUFFICIENT" and not is_bootstrap:
    raise Exception(f"데이터 부족. is_bootstrap=true로 실행하거나 데이터 축적 후 재시도.")

# COMMAND ----------

spark.sql(f"""
INSERT INTO analytics.focus_drop_user_thresholds
SELECT
  COALESCE((SELECT MAX(version) FROM analytics.focus_drop_user_thresholds), 0) + 1 AS version,
  CURRENT_TIMESTAMP()                              AS computed_at,
  {'TRUE' if is_bootstrap else 'FALSE'}            AS is_bootstrap,
  DATE_SUB(CURRENT_DATE(), {rolling_window_days})  AS window_start,
  DATE_SUB(CURRENT_DATE(), 1)                      AS window_end,
  PERCENTILE(warning_session_count,  0.90)         AS user_warning_session_count_p90,
  PERCENTILE(critical_session_count, 0.95)         AS user_critical_session_count_p95,
  PERCENTILE(departure_gap_total,    0.99)         AS user_departure_gap_total_p99
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date BETWEEN DATE_SUB(CURRENT_DATE(), {rolling_window_days}) AND DATE_SUB(CURRENT_DATE(), 1)
""")

# COMMAND ----------

# 결과 확인
spark.sql("""
SELECT version, is_bootstrap, window_start, window_end,
       user_warning_session_count_p90, user_critical_session_count_p95, user_departure_gap_total_p99
FROM analytics.focus_drop_user_thresholds
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_user_thresholds)
""").display()
