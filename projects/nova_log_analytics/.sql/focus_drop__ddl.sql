-- Databricks notebook source
-- Focus Drop — 테이블 초기 생성 DDL (v1.2 기준)
-- 실행 조건: Unity Catalog 환경, analytics 스키마 존재
-- 실행 순서: 의존 관계 없음 — 7개 테이블 순차 또는 독립 실행 가능
-- 주의: TBLPROPERTIES에 columnMapping.mode = 'name' 포함 → 향후 컬럼 리네임 가능

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 1. focus_drop_gap_thresholds
--    분기 1회 gap percentile 산출 결과 저장
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.focus_drop_gap_thresholds (
  version        INT,
  computed_at    TIMESTAMP,
  feature_scope  STRING,
  sample_count   BIGINT,
  gap_p50        DOUBLE,
  gap_p75        DOUBLE,
  gap_p90        DOUBLE,
  gap_p95        DOUBLE,
  gap_p99        DOUBLE     -- 참고 진단용 (분류 경계 아님 — idle 경계는 고정 180s)
)
USING DELTA
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 2. focus_drop_session_thresholds
--    주 1회 세션 2차 기준선 (rolling 30일)
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.focus_drop_session_thresholds (
  version                  INT,
  computed_at              TIMESTAMP,
  is_bootstrap             BOOLEAN,
  window_start             DATE,
  window_end               DATE,
  session_light_count_p90  DOUBLE,
  session_heavy_count_p95  DOUBLE,
  session_idle_count_p99   DOUBLE,
  session_light_ratio_p90  DOUBLE,
  session_heavy_ratio_p95  DOUBLE,
  session_idle_ratio_p99   DOUBLE
)
USING DELTA
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 3. focus_drop_user_thresholds
--    주 1회 유저 2차 기준선 (rolling 30일)
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.focus_drop_user_thresholds (
  version                       INT,
  computed_at                   TIMESTAMP,
  is_bootstrap                  BOOLEAN,
  window_start                  DATE,
  window_end                    DATE,
  user_light_session_count_p90  DOUBLE,
  user_heavy_session_count_p95  DOUBLE,
  user_idle_gap_total_p99       DOUBLE
)
USING DELTA
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 4. focus_drop_session_metrics
--    일 배치 — 세션별 gap count / ratio 집계
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.focus_drop_session_metrics (
  analysis_date         DATE,
  user_id               STRING,
  session_id            STRING,
  task_id               STRING,
  total_gaps            INT,
  observation_gap_count INT,
  light_gap_count       INT,
  heavy_gap_count       INT,
  idle_gap_count        INT,
  idle_gap_duration_sec DOUBLE,   -- idle gap 총 지속 시간(초) (생산성 연계용)
  light_gap_ratio       DOUBLE,
  heavy_gap_ratio       DOUBLE,
  idle_gap_ratio        DOUBLE,
  session_avg_gap       DOUBLE
)
USING DELTA
PARTITIONED BY (analysis_date)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 5. focus_drop_session_tags
--    일 배치 — 세션 판정 결과 (light / heavy / idle / normal)
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.focus_drop_session_tags (
  analysis_date    DATE,
  user_id          STRING,
  session_id       STRING,
  task_id          STRING,
  light_gap_count  INT,
  heavy_gap_count  INT,
  idle_gap_count   INT,
  is_light_session BOOLEAN,
  is_heavy_session BOOLEAN,
  is_idle_session  BOOLEAN,
  focus_drop_level STRING
)
USING DELTA
PARTITIONED BY (analysis_date)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 6. focus_drop_user_day_kpi
--    일 배치 — 유저 일 KPI 및 판정
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.focus_drop_user_day_kpi (
  analysis_date        DATE,
  user_id              STRING,
  light_session_count  INT,
  heavy_session_count  INT,
  idle_gap_total       INT,
  total_sessions       INT,
  is_light_user        BOOLEAN,
  is_heavy_user        BOOLEAN,
  is_idle_user         BOOLEAN,
  user_focus_drop_level STRING
)
USING DELTA
PARTITIONED BY (analysis_date)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 7. focus_drop_task_idle_rollup
--    일 배치 — Task별 idle gap 누적 (생산성 연계용)
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.focus_drop_task_idle_rollup (
  analysis_date         DATE,
  task_id               STRING,
  role_scope            STRING,   -- 'labeler' / 'reviewer' / 'all_roles'
  role_group            STRING,
  contributing_sessions INT,
  contributing_users    INT,
  idle_gap_total        INT,
  idle_gap_duration_sec DOUBLE
)
USING DELTA
PARTITIONED BY (analysis_date)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

-- ★ 생성 확인
SELECT table_name, partition_columns
FROM information_schema.tables
WHERE table_schema = 'analytics'
  AND table_name LIKE 'focus_drop_%'
ORDER BY table_name;
