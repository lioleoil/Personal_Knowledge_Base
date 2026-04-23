-- Databricks notebook source
-- task_key: stg_labelit__event_changes

-- ============================================================
-- Notebook 02-B: Staging — stg_labelit__event_changes
-- 실행 빈도: 배치 실행마다 (02_stg__events 완료 후)
--
-- 목적:
--   stg_labelit__events.changes_raw (JSON array string)를 행으로 EXPLODE
--   1 이벤트 → N행 (changes 배열 원소 수만큼)
--
--   old_val / new_val 은 event_type에 따라 구조가 다름:
--     - annotation.bbox3d.transform : {position:{x,y,z}, rotation:{roll,pitch,yaw}, size:{length,width,height}}
--     - annotation.object.select    : {selectedTrackingIds:[...]}
--   → JSON string 으로 보존, int 레이어에서 타입별 파싱
--
-- [ld feature — object_type별 new_val 구조]
--   object_type = 'line'     : {trackingId, pointCount, isClosed}
--   object_type = 'point'    : {trackingId}
--   object_type = 'lane'     : {trackingId, boundaries:{left:{trackingId,startPointTrackingId,endPointTrackingId},
--                                                        right:{trackingId,startPointTrackingId,endPointTrackingId}},
--                               subClassId}
--   object_type = 'topology' : {trackingId, sourceTrackingId, destinationTrackingId}
--   → create 액션의 경우 old_val = NULL (변경 전 상태 없음 — 정상)
--
-- 소스:  {catalog}.labelit_stg.stg_labelit__events
-- 타깃:  {catalog}.labelit_stg.stg_labelit__event_changes
--
-- 고유키: (event_id, change_idx)
-- ============================================================


-- ─────────────────────────────────────────────
-- [CELL 1] 테이블 전체 재계산 (CREATE OR REPLACE)
-- ─────────────────────────────────────────────
CREATE OR REPLACE TABLE ${catalog}.labelit_stg.stg_labelit__event_changes
USING DELTA
PARTITIONED BY (event_date)
AS

-- 1st CTE: changes_raw 가 있는 이벤트만 선택
WITH events_with_changes AS (
  SELECT
    event_id,
    event_type,
    event_time,
    event_date,
    occurred_at,
    session_id,
    user_id,
    task_id,
    feature,
    changes_raw
  FROM ${catalog}.labelit_stg.stg_labelit__events
  WHERE changes_raw IS NOT NULL
    AND changes_raw != '[]'
),

-- 2nd CTE: changes 배열 → 행 분해 (1 이벤트 → N행)
exploded AS (
  SELECT
    e.event_id,
    e.event_type,
    e.event_time,
    e.event_date,
    e.occurred_at,
    e.session_id,
    e.user_id,
    e.task_id,
    e.feature,
    change_idx,
    change.object_id                                               AS object_id,
    change.object_type                                             AS object_type,
    change.action                                                  AS change_action,
    change.old                                                     AS old_val,
    change.new                                                     AS new_val
  FROM events_with_changes e
  LATERAL VIEW POSEXPLODE(
    from_json(
      e.changes_raw,
      'ARRAY<STRUCT<
        object_id:   INT,
        object_type: STRING,
        action:      STRING,
        old:         STRING,
        new:         STRING
      >>'
    )
  ) t AS change_idx, change
)

SELECT * FROM exploded;


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 2] 테이블/컬럼 문서화 (Catalog Explorer에서 조회 가능)
-- ─────────────────────────────────────────────
COMMENT ON TABLE ${catalog}.labelit_stg.stg_labelit__event_changes
  IS 'Raw changes 배열 EXPLODE. 1 이벤트 → N행 (changes 원소 수만큼) — old_val/new_val은 JSON string 보존';

ALTER TABLE ${catalog}.labelit_stg.stg_labelit__event_changes
  ALTER COLUMN event_id      SET COMMENT 'stg_labelit__events.event_id 참조';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__event_changes
  ALTER COLUMN event_date    SET COMMENT '파티션 키';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__event_changes
  ALTER COLUMN occurred_at   SET COMMENT '서버 수신 시각';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__event_changes
  ALTER COLUMN change_idx    SET COMMENT 'changes 배열 내 순서 (0부터 시작)';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__event_changes
  ALTER COLUMN change_action SET COMMENT '변경 액션 (update / create / delete)';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__event_changes
  ALTER COLUMN old_val       SET COMMENT '변경 전 상태 JSON string — int 레이어에서 타입별 파싱';
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__event_changes
  ALTER COLUMN new_val       SET COMMENT '변경 후 상태 JSON string — int 레이어에서 타입별 파싱';


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 3] 품질 제약 (Delta Lake가 자동 검증)
-- ─────────────────────────────────────────────
ALTER TABLE ${catalog}.labelit_stg.stg_labelit__event_changes
  ADD CONSTRAINT ec_pk_not_null CHECK (event_id IS NOT NULL AND change_idx IS NOT NULL);


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 4] 적재 현황 확인
-- ─────────────────────────────────────────────
SELECT
  event_date,
  feature,
  event_type,
  object_type,
  change_action,
  COUNT(*) AS change_cnt
FROM   ${catalog}.labelit_stg.stg_labelit__event_changes
GROUP BY event_date, feature, event_type, object_type, change_action
ORDER BY event_date DESC, feature, event_type;
