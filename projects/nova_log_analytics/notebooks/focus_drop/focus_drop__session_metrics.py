# Databricks notebook source
# Focus Drop — 세션 메트릭 산출 (일 단위 배치, 매일 04:00 UTC)
# 의존성: focus_drop_gap_thresholds (1차 percentile 값을 위젯으로 전달)

# COMMAND ----------

dbutils.widgets.text("analysis_date", "", "Analysis Date (YYYY-MM-DD)")
dbutils.widgets.text("gap_p75", "", "Gap P75 (sec)")
dbutils.widgets.text("gap_p90", "", "Gap P90 (sec)")
dbutils.widgets.text("gap_p95", "", "Gap P95 (sec)")
dbutils.widgets.text("gap_p99", "", "Gap P99 (sec)")
dbutils.widgets.text("min_gap_count", "5", "Min Gap Count")
dbutils.widgets.text("min_event_count", "10", "Min Event Count")
dbutils.widgets.text("min_session_duration_sec", "60", "Min Session Duration (sec)")

import re
analysis_date = dbutils.widgets.get("analysis_date")
assert re.match(r"^\d{4}-\d{2}-\d{2}$", analysis_date), "analysis_date must be YYYY-MM-DD"

gap_p75  = float(dbutils.widgets.get("gap_p75"))
gap_p90  = float(dbutils.widgets.get("gap_p90"))
gap_p95  = float(dbutils.widgets.get("gap_p95"))
gap_p99  = float(dbutils.widgets.get("gap_p99"))
min_gap_count             = int(dbutils.widgets.get("min_gap_count"))
min_event_count           = int(dbutils.widgets.get("min_event_count"))
min_session_duration_sec  = int(dbutils.widgets.get("min_session_duration_sec"))

# COMMAND ----------

# gap_thresholds에서 자동으로 최신 값 로드 (위젯 미전달 시 폴백)
if not dbutils.widgets.get("gap_p75"):
    thresholds = spark.sql("""
        SELECT gap_p75, gap_p90, gap_p95, gap_p99
        FROM analytics.focus_drop_gap_thresholds
        WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_gap_thresholds)
    """).collect()[0]
    gap_p75 = thresholds["gap_p75"]
    gap_p90 = thresholds["gap_p90"]
    gap_p95 = thresholds["gap_p95"]
    gap_p99 = thresholds["gap_p99"]

print(f"Gap thresholds — p75:{gap_p75} p90:{gap_p90} p95:{gap_p95} p99:{gap_p99}")

# COMMAND ----------

spark.sql(f"""
INSERT INTO analytics.focus_drop_session_metrics
REPLACE WHERE analysis_date = '{analysis_date}'
WITH labeler_commands AS (
  SELECT
    c._raw:userId::STRING       AS user_id,
    c._raw:sessionId::STRING    AS session_id,
    c._raw:taskId::STRING       AS task_id,
    c._raw:createdAt::TIMESTAMP AS event_time
  FROM sv_nova_dev_an2_catalog.raw.raw_labelit__workspace_command c
  INNER JOIN sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_tasks t
    ON c._raw:taskId::STRING = t._id
  INNER JOIN sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_assignments a
    ON t._raw:assignmentId::STRING = a._id
  WHERE c._is_deleted = false
    AND LOWER(a._raw:role::STRING) = 'labeler'
    AND CAST(c._raw:createdAt::TIMESTAMP AS DATE) = '{analysis_date}'
),
with_diff AS (
  SELECT *,
    UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
      LAG(event_time) OVER (PARTITION BY user_id, session_id, task_id ORDER BY event_time)
    ) AS diff_sec,
    UNIX_TIMESTAMP(event_time) AS event_ts_unix
  FROM labeler_commands
),
gap_classified AS (
  SELECT
    user_id, session_id, task_id, diff_sec, event_ts_unix,
    CASE
      WHEN diff_sec <= {gap_p75} THEN 'normal'
      WHEN diff_sec <= {gap_p90} THEN 'observation'
      WHEN diff_sec <= {gap_p95} THEN 'warning'
      WHEN diff_sec <= {gap_p99} THEN 'critical'
      ELSE 'departure'
    END AS gap_severity
  FROM with_diff
  WHERE diff_sec IS NOT NULL AND diff_sec > 0
)
SELECT
  '{analysis_date}'                                           AS analysis_date,
  user_id, session_id, task_id,
  COUNT(*)                                                    AS total_gaps,
  SUM(CASE WHEN gap_severity = 'observation' THEN 1 ELSE 0 END) AS observation_gap_count,
  SUM(CASE WHEN gap_severity = 'warning'     THEN 1 ELSE 0 END) AS warning_gap_count,
  SUM(CASE WHEN gap_severity = 'critical'    THEN 1 ELSE 0 END) AS critical_gap_count,
  SUM(CASE WHEN gap_severity = 'departure'   THEN 1 ELSE 0 END) AS departure_gap_count,
  ROUND(SUM(CASE WHEN gap_severity = 'warning'   THEN 1 ELSE 0 END) / COUNT(*), 4) AS warning_gap_ratio,
  ROUND(SUM(CASE WHEN gap_severity = 'critical'  THEN 1 ELSE 0 END) / COUNT(*), 4) AS critical_gap_ratio,
  ROUND(SUM(CASE WHEN gap_severity = 'departure' THEN 1 ELSE 0 END) / COUNT(*), 4) AS departure_gap_ratio,
  AVG(diff_sec)                                               AS session_avg_gap
FROM gap_classified
GROUP BY user_id, session_id, task_id
HAVING COUNT(*) >= {min_gap_count}
   AND COUNT(*) + 1 >= {min_event_count}
   AND (MAX(event_ts_unix) - MIN(event_ts_unix)) >= {min_session_duration_sec}
""")

# COMMAND ----------

# 결과 확인
spark.sql(f"""
SELECT COUNT(*) AS session_count,
       SUM(warning_gap_count) AS total_warning_gaps,
       SUM(critical_gap_count) AS total_critical_gaps,
       SUM(departure_gap_count) AS total_departure_gaps
FROM analytics.focus_drop_session_metrics
WHERE analysis_date = '{analysis_date}'
""").display()
