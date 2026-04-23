-- Databricks notebook source
-- task_key: stg_labelit__undo_history

-- ============================================================
-- Notebook 02-C: Staging — stg_labelit__undo_history
-- 실행 빈도: 배치 실행마다 (01_raw 완료 후, 02-A와 병렬 실행 가능)
--
-- 목적:
--   history.undo / history.redo 이벤트 전용 처리
--   changes 배열 없이 reverted_command_id 로 원본 이벤트를 참조하는 구조
--
--   stg_labelit__events 와의 JOIN 키:
--     stg_labelit__undo_history.reverted_event_id = stg_labelit__events.event_id
--   → int_labelit__effective_changes 에서 is_reverted 플래그 계산에 사용
--
-- 소스:  {catalog}.labelit_raw.raw_labelit__workspace_command
-- 타깃:  {catalog}.labelit_stg.stg_labelit__undo_history
-- ============================================================


-- ─────────────────────────────────────────────
-- [CELL 1] 테이블 전체 재계산 (CREATE OR REPLACE)
-- ─────────────────────────────────────────────
CREATE OR REPLACE TABLE ${catalog}.labelit_stg.stg_labelit__undo_history
USING DELTA
PARTITIONED BY (event_date)
AS

-- 1st CTE: history.undo / history.redo 이벤트만 선택
WITH filtered AS (
  SELECT
    _id,
    _raw,
    occurred_at
  FROM ${catalog}.labelit_raw.raw_labelit__workspace_command
  WHERE get_json_object(_raw, '$.type') IN ('history.undo', 'history.redo')
),

-- 2nd CTE: _raw JSON 필드 추출
parsed AS (
  SELECT
    _id                                                             AS event_id,
    get_json_object(_raw, '$.type')                                 AS event_type,
    to_timestamp(get_json_object(_raw, '$.time'))                   AS event_time,
    DATE(to_timestamp(get_json_object(_raw, '$.time')))             AS event_date,
    to_timestamp(occurred_at)                                       AS occurred_at,
    get_json_object(_raw, '$.sessionid')                            AS session_id,
    get_json_object(_raw, '$.data.user.id')                         AS user_id,
    get_json_object(_raw, '$.data.user.name')                       AS user_name,
    get_json_object(_raw, '$.data.project.dataset_id')              AS dataset_id,
    get_json_object(_raw, '$.data.project.task_id')                 AS task_id,
    get_json_object(_raw, '$.data.feature')                         AS feature,
    get_json_object(_raw, '$.data.reverted_command_id')             AS reverted_event_id,
    get_json_object(_raw, '$.data.reverted_command_type')           AS reverted_command_type,
    CAST(get_json_object(_raw, '$.data.count') AS INT)              AS reverted_count
  FROM filtered
)

-- Final: is_redo 파생 컬럼 추가
SELECT
  event_id,
  event_type,
  event_time,
  event_date,
  occurred_at,
  session_id,
  user_id,
  user_name,
  dataset_id,
  task_id,
  feature,
  CASE
    WHEN event_type = 'history.redo' THEN TRUE
    ELSE FALSE
  END                                                             AS is_redo,
  reverted_event_id,
  reverted_command_type,
  reverted_count
FROM parsed;


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 2] 테이블/컬럼 문서화 (Catalog Explorer에서 조회 가능)
-- ─────────────────────────────────────────────
COMMENT ON TABLE ${catalog}.labelit_stg.stg_labelit__undo_history
  IS 'history.undo / history.redo 이벤트 전용. reverted_event_id → stg_labelit__events.event_id 참조';

ALTER TABLE ${catalog}.labelit_stg.stg_labelit__undo_history
  ALTER COLUMN event_date            SET COMMENT '파티션 키';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__undo_history
  ALTER COLUMN event_type            SET COMMENT 'history.undo / history.redo';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__undo_history
  ALTER COLUMN event_time            SET COMMENT '클라이언트 발생 시각 (ms 오차 있음 — 분석 시 주의)';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__undo_history
  ALTER COLUMN occurred_at           SET COMMENT '서버 수신 시각';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__undo_history
  ALTER COLUMN feature               SET COMMENT '라벨링 피처 값 (od / rmd / ld 등)';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__undo_history
  ALTER COLUMN is_redo               SET COMMENT 'FALSE: undo (취소) / TRUE: redo (복원)';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__undo_history
  ALTER COLUMN reverted_event_id     SET COMMENT '취소(복원)된 이벤트의 event_id → stg_labelit__events.event_id 참조';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__undo_history
  ALTER COLUMN reverted_command_type SET COMMENT '취소된 커맨드 종류 (UpdateBbox3dTransformCommand 등)';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__undo_history
  ALTER COLUMN reverted_count        SET COMMENT '되돌린 단계 수';


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 3] 품질 제약 (Delta Lake가 자동 검증)
-- ─────────────────────────────────────────────
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__undo_history
  ADD CONSTRAINT uh_pk_not_null CHECK (event_id IS NOT NULL);


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 4] 적재 현황 확인
-- ─────────────────────────────────────────────
SELECT
  event_date,
  feature,
  is_redo,
  COUNT(*) AS event_cnt
FROM   ${catalog}.labelit_stg.stg_labelit__undo_history
GROUP BY event_date, feature, is_redo
ORDER BY event_date DESC, feature, is_redo;
