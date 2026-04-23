-- Databricks notebook source
-- task_key: int_labelit__bbox3d_transforms

-- ============================================================
-- Notebook 03-B: Intermediate — int_labelit__bbox3d_transforms
-- 실행 빈도: 배치 실행마다 (02_stg__event_changes 완료 후)
--
-- 목적:
--   annotation.bbox3d.transform 이벤트의 old_val / new_val JSON을 파싱
--   position(x,y,z) / rotation(roll,pitch,yaw) / size(length,width,height) 필드 추출
--   3D 유클리드 이동 거리 계산 및 이동 분류
--
--   old_val / new_val 구조 (bbox3d.transform 한정):
--     {
--       "position": {"x": float, "y": float, "z": float},
--       "rotation": {"roll": float, "pitch": float, "yaw": float},
--       "size":     {"length": float, "width": float, "height": float}
--     }
--
--   주의:
--     - event_time 기준 정렬 시 ms 단위 오차 발생 가능
--       (클라이언트 배치 전송으로 발생 순서 ≠ 기록 순서)
--     - 연속된 transform 은 하나의 드래그 제스처를 N개로 쪼갠 것
--
-- 갱신 전략: CREATE OR REPLACE (전체 재계산)
-- ============================================================


-- ─────────────────────────────────────────────
-- [CELL 1] 테이블 전체 재계산 (CREATE OR REPLACE)
-- ─────────────────────────────────────────────
CREATE OR REPLACE TABLE ${catalog}.labelit_int.int_labelit__bbox3d_transforms
USING DELTA
PARTITIONED BY (event_date)
AS

-- 1st CTE: bbox3d.transform 이벤트 + position 필드가 존재하는 행만
WITH base AS (
  SELECT
    event_id,
    event_time,
    event_date,
    occurred_at,
    session_id,
    user_id,
    task_id,
    feature,
    change_idx,
    object_id,
    object_type,
    change_action,
    old_val,
    new_val
  FROM ${catalog}.labelit_stg.stg_labelit__event_changes
  WHERE event_type = 'annotation.bbox3d.transform'
    AND get_json_object(old_val, '$.position.x') IS NOT NULL
    AND get_json_object(new_val, '$.position.x') IS NOT NULL
),

-- 2nd CTE: position / rotation / size 필드 추출 + 3D 이동 거리 계산
with_positions AS (
  SELECT
    event_id,
    event_time,
    event_date,
    occurred_at,
    session_id,
    user_id,
    task_id,
    feature,
    change_idx,
    object_id,
    object_type,
    change_action,

    -- ── old position ──────────────────────────
    CAST(get_json_object(old_val, '$.position.x') AS DOUBLE)  AS old_x,
    CAST(get_json_object(old_val, '$.position.y') AS DOUBLE)  AS old_y,
    CAST(get_json_object(old_val, '$.position.z') AS DOUBLE)  AS old_z,

    -- ── new position ──────────────────────────
    CAST(get_json_object(new_val, '$.position.x') AS DOUBLE)  AS new_x,
    CAST(get_json_object(new_val, '$.position.y') AS DOUBLE)  AS new_y,
    CAST(get_json_object(new_val, '$.position.z') AS DOUBLE)  AS new_z,

    -- ── rotation (변경 여부 확인용) ────────────
    CAST(get_json_object(old_val, '$.rotation.roll')  AS DOUBLE) AS old_roll,
    CAST(get_json_object(new_val, '$.rotation.roll')  AS DOUBLE) AS new_roll,
    CAST(get_json_object(old_val, '$.rotation.pitch') AS DOUBLE) AS old_pitch,
    CAST(get_json_object(new_val, '$.rotation.pitch') AS DOUBLE) AS new_pitch,
    CAST(get_json_object(old_val, '$.rotation.yaw')   AS DOUBLE) AS old_yaw,
    CAST(get_json_object(new_val, '$.rotation.yaw')   AS DOUBLE) AS new_yaw,

    -- ── size (변경 여부 확인용) ────────────────
    CAST(get_json_object(old_val, '$.size.length') AS DOUBLE)  AS old_length,
    CAST(get_json_object(new_val, '$.size.length') AS DOUBLE)  AS new_length,
    CAST(get_json_object(old_val, '$.size.width')  AS DOUBLE)  AS old_width,
    CAST(get_json_object(new_val, '$.size.width')  AS DOUBLE)  AS new_width,
    CAST(get_json_object(old_val, '$.size.height') AS DOUBLE)  AS old_height,
    CAST(get_json_object(new_val, '$.size.height') AS DOUBLE)  AS new_height,

    -- ── 3D 이동 거리 (유클리드 거리, 소수점 4자리) ──
    ROUND(
      SQRT(
        POW(CAST(get_json_object(new_val, '$.position.x') AS DOUBLE)
          - CAST(get_json_object(old_val, '$.position.x') AS DOUBLE), 2) +
        POW(CAST(get_json_object(new_val, '$.position.y') AS DOUBLE)
          - CAST(get_json_object(old_val, '$.position.y') AS DOUBLE), 2) +
        POW(CAST(get_json_object(new_val, '$.position.z') AS DOUBLE)
          - CAST(get_json_object(old_val, '$.position.z') AS DOUBLE), 2)
      ), 4
    )                                                           AS move_distance
  FROM base
)

-- Final: move_distance 를 재사용하여 이동 분류 (SQRT 중복 계산 없음)
SELECT
  event_id,
  event_time,
  event_date,
  occurred_at,
  session_id,
  user_id,
  task_id,
  feature,
  change_idx,
  object_id,
  object_type,
  change_action,
  old_x, old_y, old_z,
  new_x, new_y, new_z,
  old_roll,  new_roll,
  old_pitch, new_pitch,
  old_yaw,   new_yaw,
  old_length, new_length,
  old_width,  new_width,
  old_height, new_height,
  move_distance,
  CASE
    WHEN move_distance < 0.1 THEN '미세조정'
    WHEN move_distance < 1.0 THEN '소폭이동'
    WHEN move_distance < 3.0 THEN '중폭이동'
    ELSE '대폭이동'
  END                                                           AS move_category
FROM with_positions;


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 2] 품질 제약 (Delta Lake가 자동 검증)
-- ─────────────────────────────────────────────
ALTER TABLE ${catalog}.labelit_int.int_labelit__bbox3d_transforms
  ADD CONSTRAINT bt_pk_not_null CHECK (event_id IS NOT NULL AND change_idx IS NOT NULL);


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 3] 이동 분류 통계 확인
-- ─────────────────────────────────────────────
SELECT
  feature,
  move_category,
  COUNT(*)                     AS cnt,
  ROUND(MIN(move_distance), 4) AS min_dist,
  ROUND(AVG(move_distance), 4) AS avg_dist,
  ROUND(MAX(move_distance), 4) AS max_dist
FROM   ${catalog}.labelit_int.int_labelit__bbox3d_transforms
GROUP BY feature, move_category
ORDER BY feature, move_category;
