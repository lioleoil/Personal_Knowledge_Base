-- Intermediate: int_focus_drop_gap_thresholds (gap percentile 기준선)
-- 의존성: stg_workspace_commands (raw 의존 없음)
-- 갱신 전략: INSERT INTO (versioned append)
-- 실행 주기: 분기 1회 (수동) — 90일 rolling window
-- 참조: Focus Drop SKILL

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

-- ★ gap percentile 산출 (90일 rolling window)
INSERT INTO sv_nova_dev_an2_catalog.analytics.int_focus_drop_gap_thresholds
WITH gaps AS (
  SELECT
    UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
      LAG(event_time) OVER (PARTITION BY user_id, session_id, task_id ORDER BY event_time)
    ) AS diff_sec
  FROM sv_nova_dev_an2_catalog.analytics.stg_workspace_commands
  WHERE event_date >= CURRENT_DATE() - INTERVAL 90 DAY
    AND event_date < CURRENT_DATE()
    AND task_id IS NOT NULL
    AND user_id IS NOT NULL
),
filtered AS (
  SELECT diff_sec
  FROM gaps
  WHERE diff_sec IS NOT NULL AND diff_sec > 0 AND diff_sec < 180
)
SELECT
  COALESCE(
    (SELECT MAX(version) + 1 FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_gap_thresholds),
    1
  )                                                AS version,
  CURRENT_TIMESTAMP()                              AS computed_at,
  'all_features'                                   AS feature_scope,
  COUNT(*)                                         AS sample_count,
  PERCENTILE_APPROX(diff_sec, 0.50)               AS gap_p50,
  PERCENTILE_APPROX(diff_sec, 0.75)               AS gap_p75,
  PERCENTILE_APPROX(diff_sec, 0.90)               AS gap_p90,
  PERCENTILE_APPROX(diff_sec, 0.95)               AS gap_p95,
  PERCENTILE_APPROX(diff_sec, 0.99)               AS gap_p99
FROM filtered;

-- COMMAND ----------

COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_gap_thresholds
  IS 'gap percentile 기준선 (90일 rolling). versioned append. idle 경계 180s 미만 gap만 대상.';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_gap_thresholds SET TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ★ 적재 확인 (최신 버전)
SELECT * FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_gap_thresholds
ORDER BY version DESC LIMIT 3;