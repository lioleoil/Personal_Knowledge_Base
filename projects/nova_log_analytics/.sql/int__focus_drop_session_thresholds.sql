-- Intermediate: int_focus_drop_session_thresholds (세션 판정 기준선)
-- 의존성: int_focus_drop_session_metrics (raw 의존 없음)
-- 갱신 전략: INSERT INTO (versioned append)
-- 실행 주기: 주 1회 (수동) — 30일 rolling window
-- 참조: Focus Drop SKILL

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

-- ★ session-level 판정 기준선 산출 (30일 rolling)
INSERT INTO sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_thresholds
WITH window_data AS (
  SELECT
    light_gap_count, heavy_gap_count, idle_gap_count,
    light_gap_ratio, heavy_gap_ratio, idle_gap_ratio
  FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics
  WHERE analysis_date >= CURRENT_DATE() - INTERVAL 30 DAY
    AND analysis_date < CURRENT_DATE()
)
SELECT
  COALESCE(
    (SELECT MAX(version) + 1 FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_thresholds),
    1
  )                                                         AS version,
  CURRENT_TIMESTAMP()                                       AS computed_at,
  (COUNT(*) < 100)                                          AS is_bootstrap,
  CURRENT_DATE() - INTERVAL 30 DAY                          AS window_start,
  CURRENT_DATE() - INTERVAL 1 DAY                           AS window_end,
  PERCENTILE_APPROX(light_gap_count, 0.90)                 AS session_light_count_p90,
  PERCENTILE_APPROX(heavy_gap_count, 0.95)                 AS session_heavy_count_p95,
  PERCENTILE_APPROX(idle_gap_count, 0.99)                  AS session_idle_count_p99,
  PERCENTILE_APPROX(light_gap_ratio, 0.90)                 AS session_light_ratio_p90,
  PERCENTILE_APPROX(heavy_gap_ratio, 0.95)                 AS session_heavy_ratio_p95,
  PERCENTILE_APPROX(idle_gap_ratio, 0.99)                  AS session_idle_ratio_p99
FROM window_data;

-- COMMAND ----------

COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_thresholds
  IS '세션 판정 기준선 (30일 rolling). versioned append. count + ratio percentile.';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_thresholds SET TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ★ 적재 확인
SELECT * FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_thresholds
ORDER BY version DESC LIMIT 3;