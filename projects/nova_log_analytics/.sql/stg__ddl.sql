-- Databricks notebook source
-- Staging Layer — 테이블 초기 생성 DDL
-- 실행 조건: Unity Catalog 환경, analytics 스키마 존재
-- 갱신 전략: stg_task_transition_events / stg_cmd_slots_by_task — 일 OVERWRITE
--            stg_object_counts_by_task — 일 REPLACE WHERE table_name (per-table 단위)

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 1. stg_task_transition_events
--    gen2_tasks transitionHistory 전체 flatten
--    소스: stg__task_transition_events.sql (일 배치)
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.stg_task_transition_events (
  task_id      STRING,       -- gen2_tasks._id
  company_id   STRING,       -- gen2_tasks._raw.companyId
  policy_id    STRING,       -- gen2_tasks._raw.policyId
  from_state   STRING,       -- transitionHistory[].fromState
  to_state     STRING,       -- transitionHistory[].toState
  trigger      STRING,       -- transitionHistory[].trigger
  action_by    STRING,       -- transitionHistory[].actionBy
  action_at    TIMESTAMP,    -- transitionHistory[].actionAt (UTC 저장)
  reason       STRING,       -- transitionHistory[].reason (반려 사유 등; inspection_quality 활용)
  event_week   DATE,         -- DATE_TRUNC('WEEK', action_at KST) — 파티션 키
  refreshed_at TIMESTAMP     -- 적재 시점
)
USING DELTA
PARTITIONED BY (event_week)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 2. stg_object_counts_by_task
--    10개 객체 테이블 CDC dedup + task별 객체 수 집계
--    grain: task_id × table_name × stage_key
--    소스: stg__object_counts_by_task.sql (일 배치, per-table REPLACE)
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.stg_object_counts_by_task (
  task_id      STRING,    -- 객체 테이블 _raw.taskId
  table_name   STRING,    -- 'gen2_lines' | 'gen2_line_point' | ... (파티션 키)
  stage_key    STRING,    -- 객체 테이블 _raw.stageKey
  object_count BIGINT,    -- COUNT(*) after CDC dedup
  refreshed_at TIMESTAMP
)
USING DELTA
PARTITIONED BY (table_name)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 3. stg_cmd_slots_by_task
--    workspace_command task별 투입 자원 집계
--    grain: task_id (전체 기간 합산)
--    소스: stg__cmd_slots_by_task.sql (일 배치)
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.stg_cmd_slots_by_task (
  task_id         STRING,    -- workspace_command._raw.taskId
  user_hour_slots BIGINT,    -- COUNT DISTINCT (user × KST event_hour)
  person_days     BIGINT,    -- COUNT DISTINCT (user × KST event_date)
  refreshed_at    TIMESTAMP
)
USING DELTA
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
  AND table_name LIKE 'stg_%'
ORDER BY table_name;
