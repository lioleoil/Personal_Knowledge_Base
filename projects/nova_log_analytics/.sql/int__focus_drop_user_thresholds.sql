-- Intermediate: int_focus_drop_user_thresholds (유저 판정 기준선)
-- 의존성: int_focus_drop_user_day_kpi (raw 의존 없음)
-- 갱신 전략: INSERT INTO (versioned append)
-- 실행 주기: 주 1회 (수동) — 30일 rolling window
-- 참조: Focus Drop SKILL

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

-- ★ user-level 판정 기준선 산출 (30일 rolling)
INSERT INTO sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_thresholds
WITH window_data AS (
  SELECT
    light_session_count, heavy_session_count, idle_gap_total
  FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi
  WHERE analysis_date >= CURRENT_DATE() - INTERVAL 30 DAY
    AND analysis_date < CURRENT_DATE()
)
SELECT
  COALESCE(
    (SELECT MAX(version) + 1 FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_thresholds),
    1
  )                                                         AS version,
  CURRENT_TIMESTAMP()                                       AS computed_at,
  (COUNT(*) < 100)                                          AS is_bootstrap,
  CURRENT_DATE() - INTERVAL 30 DAY                          AS window_start,
  CURRENT_DATE() - INTERVAL 1 DAY                           AS window_end,
  PERCENTILE_APPROX(light_session_count, 0.90)             AS user_light_session_count_p90,
  PERCENTILE_APPROX(heavy_session_count, 0.95)             AS user_heavy_session_count_p95,
  PERCENTILE_APPROX(idle_gap_total, 0.99)                  AS user_idle_gap_total_p99
FROM window_data;

-- COMMAND ----------

COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_thresholds
  IS '유저 판정 기준선 (30일 rolling). versioned append. user_day_kpi 기반 percentile.';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_thresholds SET TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ★ 적재 확인
SELECT * FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_thresholds
ORDER BY version DESC LIMIT 3;