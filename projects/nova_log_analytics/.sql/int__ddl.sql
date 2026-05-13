-- Databricks notebook source
-- Intermediate Layer — 테이블 초기 생성 DDL
-- 실행 조건: Unity Catalog 환경, analytics 스키마 존재
-- 레이어 역할: staging 기반 비즈니스 로직 적용, 조인, 집계 — 외부 소비 대상 아님
--
-- 현행 테이블:
--   int_object_counts_by_task   — stg_objects 기반 task별 객체 수 집계
-- [이전 예정]
--   int_command_slots_by_task   — stg_workspace_commands 기반 task별 투입 자원 집계
--   int_focus_drop_*            — focus_drop__ddl.sql 의 session/user 지표 테이블

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 1. int_object_counts_by_task
--    stg_objects → task별 객체 수 집계
--    grain: task_id × table_name × stage_key
--    소스: int__object_counts_by_task.sql (일 OVERWRITE)
--    대체: stg_object_counts_by_task [DEPRECATED]
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.int_object_counts_by_task (
  task_id      STRING,    -- stg_objects.task_id
  table_name   STRING,    -- 소스 테이블명 — 파티션 키
  stage_key    STRING,    -- stg_objects.stage_key
  object_count BIGINT,    -- COUNT(*) from stg_objects
  _loaded_at   TIMESTAMP
)
USING DELTA
PARTITIONED BY (table_name)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE analytics.int_object_counts_by_task
  IS 'task x table_name x stage_key object count. Aggregated from stg_objects. Replaces stg_object_counts_by_task. Daily OVERWRITE.';
ALTER TABLE analytics.int_object_counts_by_task
  ADD CONSTRAINT ioct_task_id_not_null    CHECK (task_id    IS NOT NULL);
ALTER TABLE analytics.int_object_counts_by_task
  ADD CONSTRAINT ioct_table_name_not_null CHECK (table_name IS NOT NULL);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 2. int_focus_drop_gap_thresholds
--    분기 1회 gap percentile 산출 결과
--    소스: int__focus_drop_gap_percentiles.sql
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
  gap_p99        DOUBLE
)
USING DELTA
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE analytics.focus_drop_gap_thresholds
  IS 'Quarterly gap percentile baselines from Labeler normal distribution. p50/p75/p90/p95/p99.';
ALTER TABLE analytics.focus_drop_gap_thresholds
  ADD CONSTRAINT gt_version_not_null CHECK (version IS NOT NULL);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 3. int_focus_drop_session_thresholds
--    주 1회 세션 2차 기준선 (rolling 30일)
--    소스: int__focus_drop_session_thresholds.sql
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

COMMENT ON TABLE analytics.focus_drop_session_thresholds
  IS 'Weekly rolling 30-day session-level classification thresholds (2nd percentile).';
ALTER TABLE analytics.focus_drop_session_thresholds
  ADD CONSTRAINT st_version_not_null CHECK (version IS NOT NULL);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 4. int_focus_drop_user_thresholds
--    주 1회 유저 2차 기준선 (rolling 30일)
--    소스: int__focus_drop_user_thresholds.sql
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

COMMENT ON TABLE analytics.focus_drop_user_thresholds
  IS 'Weekly rolling 30-day user-day KPI classification thresholds (2nd percentile).';
ALTER TABLE analytics.focus_drop_user_thresholds
  ADD CONSTRAINT ut_version_not_null CHECK (version IS NOT NULL);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 5. int_focus_drop_session_metrics
--    일 배치 — 세션별 gap count / ratio 집계
--    소스: int__focus_drop_session_metrics.sql
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
  idle_gap_duration_sec DOUBLE,
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

COMMENT ON TABLE analytics.focus_drop_session_metrics
  IS 'Daily session-level gap count, ratio, and idle duration metrics. Partitioned by analysis_date.';
ALTER TABLE analytics.focus_drop_session_metrics
  ADD CONSTRAINT sm_analysis_date_not_null CHECK (analysis_date IS NOT NULL);
ALTER TABLE analytics.focus_drop_session_metrics
  ADD CONSTRAINT sm_user_id_not_null       CHECK (user_id       IS NOT NULL);
ALTER TABLE analytics.focus_drop_session_metrics
  ADD CONSTRAINT sm_session_id_not_null    CHECK (session_id    IS NOT NULL);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 6. int_focus_drop_session_tags
--    일 배치 — 세션 판정 결과
--    소스: int__focus_drop_session_tags.sql
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

COMMENT ON TABLE analytics.focus_drop_session_tags
  IS 'Daily session focus drop classification (light/heavy/idle/normal). Partitioned by analysis_date.';
ALTER TABLE analytics.focus_drop_session_tags
  ADD CONSTRAINT stg_analysis_date_not_null CHECK (analysis_date IS NOT NULL);
ALTER TABLE analytics.focus_drop_session_tags
  ADD CONSTRAINT stg_user_id_not_null       CHECK (user_id       IS NOT NULL);
ALTER TABLE analytics.focus_drop_session_tags
  ADD CONSTRAINT stg_session_id_not_null    CHECK (session_id    IS NOT NULL);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 7. int_focus_drop_task_idle_rollup
--    일 배치 — Task별 idle gap 누적 (생산성 연계용)
--    소스: int__focus_drop_task_idle_rollup.sql
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.focus_drop_task_idle_rollup (
  analysis_date         DATE,
  task_id               STRING,
  role_scope            STRING,
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

COMMENT ON TABLE analytics.focus_drop_task_idle_rollup
  IS 'Daily task-level idle gap rollup for net working time calculation. Partitioned by analysis_date.';
ALTER TABLE analytics.focus_drop_task_idle_rollup
  ADD CONSTRAINT tir_analysis_date_not_null CHECK (analysis_date IS NOT NULL);
ALTER TABLE analytics.focus_drop_task_idle_rollup
  ADD CONSTRAINT tir_task_id_not_null       CHECK (task_id       IS NOT NULL);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 8. int_command_slots_by_task
--    stg_workspace_commands 기반 task별 투입 자원 집계
--    grain: task_id (전체 기간 합산)
--    소스: int__command_slots_by_task.sql (일 OVERWRITE)
--    대체: stg_command_slots_by_task [DEPRECATED]
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.int_command_slots_by_task (
  task_id         STRING,    -- stg_workspace_commands.task_id
  user_hour_slots BIGINT,    -- COUNT DISTINCT (user_name × event_date × event_hour)
  person_days     BIGINT,    -- COUNT DISTINCT (user_name × event_date)
  _loaded_at      TIMESTAMP
)
USING DELTA
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE analytics.int_command_slots_by_task
  IS 'task-level active time slots aggregated from stg_workspace_commands. Replaces stg_command_slots_by_task. Daily OVERWRITE.';
ALTER TABLE analytics.int_command_slots_by_task
  ADD CONSTRAINT icst_task_id_not_null CHECK (task_id IS NOT NULL);

-- COMMAND ----------

-- ★ 생성 확인
SELECT table_name, partition_columns
FROM information_schema.tables
WHERE table_schema = 'analytics'
  AND table_name LIKE 'int_%'
ORDER BY table_name;
