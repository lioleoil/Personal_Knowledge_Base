-- Databricks notebook source
-- Staging Layer — 테이블 초기 생성 DDL
-- 실행 조건: Unity Catalog 환경, analytics 스키마 존재
-- 현행 테이블: stg_task_transition_events / stg_tasks / stg_workspace_commands
--              stg_workspace_command_details / stg_workspace_history / stg_objects

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
  _loaded_at   TIMESTAMP     -- 적재 시점
)
USING DELTA
PARTITIONED BY (event_week)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);


-- COMMAND ----------

COMMENT ON TABLE analytics.stg_task_transition_events
  IS 'gen2_tasks transitionHistory flatten. CDC dedup by _id, daily OVERWRITE.';

ALTER TABLE analytics.stg_task_transition_events
  ADD CONSTRAINT tte_task_id_not_null   CHECK (task_id   IS NOT NULL);

ALTER TABLE analytics.stg_task_transition_events
  ADD CONSTRAINT tte_action_at_not_null CHECK (action_at IS NOT NULL);


-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 2. stg_tasks
--    gen2_tasks CDC dedup, 태스크 핵심 속성 추출
--    grain: task _id
--    소스: stg__tasks.sql (일 OVERWRITE)
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.stg_tasks (
  task_id      STRING,       -- gen2_tasks._id
  company_id   STRING,       -- _raw.companyId
  policy_id    STRING,       -- _raw.policyId
  status       STRING,       -- _raw.currentState (현재 태스크 상태)
  stage_key    STRING,       -- _raw.currentStageKey (현재 스테이지)
  created_at   TIMESTAMP,    -- _raw.createdAt (UTC 저장)
  created_week DATE,         -- DATE_TRUNC('WEEK', created_at KST) — 파티션 키
  _loaded_at   TIMESTAMP     -- 적재 시점
)
USING DELTA
PARTITIONED BY (created_week)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);


-- COMMAND ----------

COMMENT ON TABLE analytics.stg_tasks
  IS 'gen2_tasks CDC dedup, task-level attributes flatten. Daily OVERWRITE.';

ALTER TABLE analytics.stg_tasks
  ADD CONSTRAINT tsk_task_id_not_null  CHECK (task_id  IS NOT NULL);

ALTER TABLE analytics.stg_tasks
  ADD CONSTRAINT tsk_created_at_not_null CHECK (created_at IS NOT NULL);


-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 3. stg_workspace_commands
--    workspace_command CDC dedup, CloudEvents 1.0 필드 추출
--    grain: command _id
--    소스: stg__workspace_commands.sql (일 OVERWRITE)
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.stg_workspace_commands (
  -- ── CloudEvents root ────────────────────────────────────────────
  command_id   STRING,       -- _id (CloudEvents id)
  event_type   STRING,       -- type (e.g. annotation.object.delete)
  dataschema   STRING,       -- dataschema (1.0.0 / 1.1.0 ...)
  event_time   TIMESTAMP,    -- time (UTC)
  event_date   DATE,         -- DATE(event_time KST) — 파티션 키
  event_hour   INT,          -- HOUR(event_time KST) — slot 집계용
  subject      STRING,       -- subject (이벤트 대상 엔티티 ID)
  session_id   STRING,       -- sessionid (Focus Drop 세션 키)
  -- ── data.project ────────────────────────────────────────────────
  task_id      STRING,       -- data.project.task_id
  dataset_id   STRING,       -- data.project.dataset_id
  -- ── data.user ───────────────────────────────────────────────────
  user_id      STRING,       -- data.user.id
  user_name    STRING,       -- data.user.name
  -- ── data.action context ─────────────────────────────────────────
  feature      STRING,       -- data.feature (ld / od / rmd)
  action       STRING,       -- data.action (create / delete / update / transform ...)
  input_type   STRING,       -- data.input_type (mouse / keyboard)
  input_view   STRING,       -- data.input_view (rear / front / ... ; 1.1.0+ nullable)
  -- ── metadata ────────────────────────────────────────────────────
  _loaded_at   TIMESTAMP     -- 적재 시점
)
USING DELTA
PARTITIONED BY (event_date)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);


-- COMMAND ----------

COMMENT ON TABLE analytics.stg_workspace_commands
  IS 'workspace_command CDC dedup, CloudEvents 1.0 row-level flatten. targets/changes/params는 stg_workspace_command_details 참조. Daily OVERWRITE.';

ALTER TABLE analytics.stg_workspace_commands
  ADD CONSTRAINT wc_command_id_not_null CHECK (command_id IS NOT NULL);

ALTER TABLE analytics.stg_workspace_commands
  ADD CONSTRAINT wc_event_time_not_null CHECK (event_time IS NOT NULL);


-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 4. stg_workspace_command_details
--    workspace_command 상세 — targets / changes / params
--    grain: command _id (stg_workspace_commands 1:1 대응)
--    소스: stg__workspace_command_details.sql (일 OVERWRITE)
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.stg_workspace_command_details (
  command_id   STRING,        -- FK → stg_workspace_commands.command_id
  event_date   DATE,          -- 파티션 정렬용 (stg_workspace_commands.event_date 동일)
  targets      ARRAY<BIGINT>, -- data.targets (영향받은 object ID 목록)
  changes      STRING,        -- data.changes (JSON array, old/new 전체 보존)
  params       STRING,        -- data.params (커맨드별 부가 파라미터, JSON string)
  _loaded_at   TIMESTAMP
)
USING DELTA
PARTITIONED BY (event_date)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);


-- COMMAND ----------

COMMENT ON TABLE analytics.stg_workspace_command_details
  IS 'workspace_command targets/changes/params 상세. stg_workspace_commands와 command_id로 1:1 조인. Daily OVERWRITE.';

ALTER TABLE analytics.stg_workspace_command_details
  ADD CONSTRAINT wcd_command_id_not_null CHECK (command_id IS NOT NULL);


-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 5. stg_workspace_history
--    workspace_history Undo/Redo CDC dedup, CloudEvents 1.0 필드 추출
--    grain: history _id
--    소스: stg__workspace_history.sql (일 OVERWRITE)
--    조인: stg_workspace_commands.command_id = reverted_command_id
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.stg_workspace_history (
  -- ── CloudEvents root ────────────────────────────────────────────
  history_id             STRING,       -- _id (CloudEvents id)
  event_type             STRING,       -- type (history.undo / history.redo / history.undo_batch / history.redo_batch)
  dataschema             STRING,       -- dataschema (1.0.0 / 1.1.0)
  event_time             TIMESTAMP,    -- time (UTC)
  event_date             DATE,         -- DATE(event_time KST) — 파티션 키
  subject                STRING,       -- subject (이벤트 대상 엔티티 ID)
  session_id             STRING,       -- sessionid (Focus Drop 세션 키)
  -- ── data.project ────────────────────────────────────────────────
  task_id                STRING,       -- data.project.task_id
  dataset_id             STRING,       -- data.project.dataset_id
  -- ── data.user ───────────────────────────────────────────────────
  user_id                STRING,       -- data.user.id
  user_name              STRING,       -- data.user.name
  -- ── data.undo/redo context ───────────────────────────────────────
  feature                STRING,       -- data.feature (ld / od / rmd)
  reverted_command_id    STRING,       -- data.reverted_command_id (FK → stg_workspace_commands.command_id)
  reverted_command_type  STRING,       -- data.reverted_command_type (커맨드 타입 코드)
  undo_count             INT,          -- data.count (한 번에 취소/재실행된 단계 수)
  -- ── metadata ────────────────────────────────────────────────────
  _loaded_at             TIMESTAMP     -- 적재 시점
)
USING DELTA
PARTITIONED BY (event_date)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);


-- COMMAND ----------

COMMENT ON TABLE analytics.stg_workspace_history
  IS 'workspace_history Undo/Redo CDC dedup, CloudEvents 1.0 flatten. reverted_command_id로 stg_workspace_commands 조인. Daily OVERWRITE.';

ALTER TABLE analytics.stg_workspace_history
  ADD CONSTRAINT wh_history_id_not_null  CHECK (history_id  IS NOT NULL);

ALTER TABLE analytics.stg_workspace_history
  ADD CONSTRAINT wh_event_time_not_null  CHECK (event_time  IS NOT NULL);


-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 6. stg_objects
--    10개 객체 테이블 unified CDC dedup (집계 없음)
--    grain: object_id × table_name
--    소스: stg__objects.sql (일 배치, per-table REPLACE WHERE table_name)
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.stg_objects (
  object_id    STRING,       -- 객체 테이블 _id (table_name 내 고유)
  table_name   STRING,       -- 소스 테이블명 — 파티션 키
  task_id      STRING,       -- _raw.taskId
  stage_key    STRING,       -- _raw.stageKey
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

COMMENT ON TABLE analytics.stg_objects
  IS '10 object tables unified CDC dedup. No aggregation — grain: object_id x table_name. Daily per-table REPLACE.';

ALTER TABLE analytics.stg_objects
  ADD CONSTRAINT obj_object_id_not_null  CHECK (object_id  IS NOT NULL);

ALTER TABLE analytics.stg_objects
  ADD CONSTRAINT obj_table_name_not_null CHECK (table_name IS NOT NULL);

ALTER TABLE analytics.stg_objects
  ADD CONSTRAINT obj_task_id_not_null    CHECK (task_id    IS NOT NULL);


-- COMMAND ----------

-- ★ 생성 확인
SELECT table_name, comment
FROM information_schema.tables
WHERE table_schema = 'analytics'
  AND table_name LIKE 'stg_%'
ORDER BY table_name;