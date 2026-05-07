# Databricks notebook source
# Focus Drop — Gap Percentile 산출 (분기 1회 또는 드리프트 감지 시)
# 실행 조건: Labeler 직전 90일 diff_sec 분포 기반 1차 percentile 산출
# 의존성: 없음 (파이프라인 최상위)

# COMMAND ----------

dbutils.widgets.text("rolling_days", "90", "Lookback Days")
rolling_days = int(dbutils.widgets.get("rolling_days"))

# COMMAND ----------

result = spark.sql(f"""
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
    AND CAST(c._raw:createdAt::TIMESTAMP AS DATE) >= DATE_SUB(CURRENT_DATE(), {rolling_days})
),
with_diff AS (
  SELECT *,
    UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
      LAG(event_time) OVER (PARTITION BY user_id, session_id, task_id ORDER BY event_time)
    ) AS diff_sec
  FROM labeler_commands
)
SELECT
  COALESCE((SELECT MAX(version) FROM analytics.focus_drop_gap_thresholds), 0) + 1 AS version,
  CURRENT_TIMESTAMP()                AS computed_at,
  'all_features'                     AS feature_scope,
  COUNT(*)                           AS sample_count,
  PERCENTILE(diff_sec, 0.50)         AS gap_p50,
  PERCENTILE(diff_sec, 0.75)         AS gap_p75,
  PERCENTILE(diff_sec, 0.90)         AS gap_p90,
  PERCENTILE(diff_sec, 0.95)         AS gap_p95,
  PERCENTILE(diff_sec, 0.99)         AS gap_p99
FROM with_diff
WHERE diff_sec IS NOT NULL AND diff_sec > 0
HAVING COUNT(*) >= 10000
""")

if result.count() == 0:
    raise Exception("표본 수 미달 (< 10,000) — 기존 기준선 유지, INSERT 스킵")

result.write.mode("append").saveAsTable("analytics.focus_drop_gap_thresholds")
print("gap_thresholds INSERT 완료")

# COMMAND ----------

# 결과 확인
spark.sql("""
SELECT version, computed_at, sample_count, gap_p75, gap_p90, gap_p95, gap_p99
FROM analytics.focus_drop_gap_thresholds
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_gap_thresholds)
""").display()
