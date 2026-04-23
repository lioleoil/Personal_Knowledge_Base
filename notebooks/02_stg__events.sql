-- Databricks notebook source
-- task_key: stg_labelit__events

-- ============================================================
-- Notebook 02-A: Staging — stg_labelit__events
-- 실행 빈도: 배치 실행마다 (01_raw 완료 후)
--
-- 목적:
--   _raw JSON 파싱
--   history.undo / history.redo 는 제외 → 02_stg__undo_history 에서 별도 처리
--
-- 소스:  {catalog}.labelit_raw.raw_labelit__workspace_command
-- 타깃:  {catalog}.labelit_stg.stg_labelit__events
-- ============================================================


-- ─────────────────────────────────────────────
-- [CELL 1] 테이블 전체 재계산 (CREATE OR REPLACE)
-- ─────────────────────────────────────────────
CREATE OR REPLACE TABLE ${catalog}.labelit_stg.stg_labelit__events
USING DELTA
PARTITIONED BY (event_date)
AS

-- 1st CTE: undo/redo 제외 — stg_labelit__undo_history 에서 별도 처리
WITH filtered AS (
  SELECT
    _id,
    _raw,
    occurred_at
  FROM ${catalog}.labelit_raw.raw_labelit__workspace_command
  WHERE get_json_object(_raw, '$.type') NOT IN ('history.undo', 'history.redo')
),

-- 2nd CTE: _raw JSON 필드 추출
parsed AS (
  SELECT
    _id                                                            AS event_id,
    get_json_object(_raw, '$.type')                                AS event_type,
    to_timestamp(get_json_object(_raw, '$.time'))                  AS event_time,
    DATE(to_timestamp(get_json_object(_raw, '$.time')))            AS event_date,
    to_timestamp(occurred_at)                                      AS occurred_at,
    get_json_object(_raw, '$.sessionid')                           AS session_id,
    get_json_object(_raw, '$.subject')                             AS subject,
    get_json_object(_raw, '$.dataschema')                          AS dataschema,
    get_json_object(_raw, '$.data.user.id')                        AS user_id,
    get_json_object(_raw, '$.data.user.name')                      AS user_name,
    get_json_object(_raw, '$.data.project.dataset_id')             AS dataset_id,
    get_json_object(_raw, '$.data.project.task_id')                AS task_id,
    get_json_object(_raw, '$.data.feature')                        AS feature,
    get_json_object(_raw, '$.data.action')                         AS action,
    get_json_object(_raw, '$.data.input_type')                     AS input_type,
    get_json_object(_raw, '$.data.targets')                        AS targets,
    get_json_object(_raw, '$.data.params')                         AS params,
    get_json_object(_raw, '$.data.changes')                        AS changes_raw
  FROM filtered
)

-- Final: feature_gen / event_category 파생 컬럼 추가
SELECT
  event_id,
  event_type,
  event_time,
  event_date,
  occurred_at,
  session_id,
  subject,
  dataschema,
  user_id,
  user_name,
  dataset_id,
  task_id,
  feature,
  action,
  input_type,
  targets,
  params,
  changes_raw,
  CASE
    WHEN event_type = 'annotation.object.select'    THEN 'select'
    WHEN event_type = 'annotation.bbox3d.transform' THEN 'transform'
    WHEN event_type IN (
      'annotation.lane.create',
      'annotation.topology.create',
      'annotation.line.create'
    )                                                THEN 'create'
    ELSE 'other'
  END                                                            AS event_category
FROM parsed;


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 2] 테이블/컬럼 문서화 (Catalog Explorer에서 조회 가능)
-- ─────────────────────────────────────────────
COMMENT ON TABLE ${catalog}.labelit_stg.stg_labelit__events
  IS 'Raw JSON 파싱. undo/redo 제외 — stg_labelit__undo_history 참조';

ALTER TABLE ${catalog}.labelit_stg.stg_labelit__events
  ALTER COLUMN event_time     SET COMMENT '클라이언트 발생 시각 (ms 오차 있음 — 분석 시 주의)';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__events
  ALTER COLUMN event_date     SET COMMENT '파티션 키 — event_time 기준 날짜';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__events
  ALTER COLUMN occurred_at    SET COMMENT '서버 수신 시각';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__events
  ALTER COLUMN subject        SET COMMENT '작업 대상 MongoDB ObjectId';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__events
  ALTER COLUMN dataschema     SET COMMENT 'CloudEvent 데이터 스키마 버전';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__events
  ALTER COLUMN user_id        SET COMMENT '사용자 ID (MongoDB ObjectId)';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__events
  ALTER COLUMN feature        SET COMMENT '라벨링 피처 값 (od / rmd / ld 등)';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__events
  ALTER COLUMN targets        SET COMMENT '커맨드 대상 object ID 배열 (JSON array string)';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__events
  ALTER COLUMN params         SET COMMENT '커맨드 결과 요약 (selectedCount / updateCount 등, JSON string)';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__events
  ALTER COLUMN changes_raw    SET COMMENT 'changes 배열 원본 JSON — stg_labelit__event_changes 에서 EXPLODE';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__events
  ALTER COLUMN event_category SET COMMENT '이벤트 카테고리 (select / transform / other)';


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 3] 품질 제약 (Delta Lake가 자동 검증)
-- ─────────────────────────────────────────────
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__events
  ADD CONSTRAINT ev_pk_not_null CHECK (event_id IS NOT NULL);


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 4] 적재 현황 확인
-- ─────────────────────────────────────────────
SELECT
  event_date,
  feature,
  event_category,
  COUNT(*) AS event_cnt
FROM   ${catalog}.labelit_stg.stg_labelit__events
GROUP BY event_date, feature, event_category
ORDER BY event_date DESC, feature, event_category;
