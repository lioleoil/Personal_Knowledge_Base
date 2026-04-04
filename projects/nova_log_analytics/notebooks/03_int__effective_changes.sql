-- Databricks notebook source
-- task_key: int_labelit__effective_changes

-- ============================================================
-- Notebook 03-A: Intermediate — int_labelit__effective_changes
-- 실행 빈도: 배치 실행마다 (02_stg__event_changes + 02_stg__undo_history 완료 후)
--
-- 목적:
--   stg_labelit__event_changes 에 is_reverted 플래그 추가
--
--   is_reverted 판별 기준:
--     undo 대상 event_id 집합  EXCEPT  redo로 복원된 event_id 집합
--     → 최종적으로 취소된 상태인 이벤트만 TRUE
--
--   주의:
--     - is_reverted = TRUE 행을 삭제하지 않고 플래그로 보존
--       → "얼마나 수정/취소했는가" 행동 분석에 필요
--     - annotation.object.select 이벤트는 Command Stack 대상이 아니므로
--       항상 is_reverted = FALSE
--
-- 갱신 전략: CREATE OR REPLACE (전체 재계산)
--   is_reverted 는 undo/redo 이벤트 도착 시 변경되므로 전체 재계산이 가장 단순
--   데이터 볼륨 증가 시 MERGE 방식으로 전환 고려
-- ============================================================


-- ─────────────────────────────────────────────
-- [CELL 1] 테이블 전체 재계산 (CREATE OR REPLACE)
-- ─────────────────────────────────────────────
CREATE OR REPLACE TABLE ${catalog}.labelit_int.int_labelit__effective_changes
USING DELTA
PARTITIONED BY (event_date)
COMMENT 'Intermediate 레이어: event_changes + is_reverted 플래그 (undo로 취소된 이벤트 여부)'
AS

WITH undone AS (
  -- undo 됐지만 redo 로 복원되지 않은 event_id (최종 취소 상태)
  SELECT reverted_event_id
  FROM   ${catalog}.labelit_stg.stg_labelit__undo_history
  WHERE  is_redo = FALSE

  EXCEPT

  SELECT reverted_event_id
  FROM   ${catalog}.labelit_stg.stg_labelit__undo_history
  WHERE  is_redo = TRUE
)

SELECT
  c.event_id,
  c.event_type,
  c.event_time,
  c.event_date,
  c.occurred_at,
  c.session_id,
  c.user_id,
  c.task_id,
  c.feature,
  c.change_idx,
  c.object_id,
  c.object_type,
  c.change_action,
  c.old_val,
  c.new_val,

  -- is_reverted: undo로 최종 취소된 이벤트 여부
  CASE
    WHEN u.reverted_event_id IS NOT NULL THEN TRUE
    ELSE FALSE
  END AS is_reverted

FROM ${catalog}.labelit_stg.stg_labelit__event_changes c
LEFT JOIN undone u
  ON c.event_id = u.reverted_event_id;


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 2] 품질 제약 (Delta Lake가 자동 검증)
-- ─────────────────────────────────────────────
ALTER TABLE ${catalog}.labelit_int.int_labelit__effective_changes
  ADD CONSTRAINT eff_pk_not_null CHECK (event_id IS NOT NULL AND change_idx IS NOT NULL);


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 3] 결과 확인
-- ─────────────────────────────────────────────
SELECT
  feature,
  is_reverted,
  COUNT(*) AS change_cnt
FROM   ${catalog}.labelit_int.int_labelit__effective_changes
GROUP BY feature, is_reverted
ORDER BY feature, is_reverted;
