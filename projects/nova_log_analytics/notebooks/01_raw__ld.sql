-- Databricks notebook source
-- task_key: raw_labelit__ld

-- ============================================================
-- Notebook 01-B: Raw Layer — raw_labelit__ld
-- 실행 빈도: 배치 실행마다
--
-- 목적:
--   ld feature 로그를 Raw 레이어에 적재
--
--   [포맷 특이사항]
--   기존 od/od2 이벤트는 CloudEvent JSON 전체를 _raw 컬럼에 보존하는 방식이나,
--   ld 이벤트는 앱에서 이미 파싱·분해된 구조체 형태(1행 = 1 change)로 발행됨.
--   → _raw JSON 없음, 각 필드가 직접 컬럼으로 표현됨
--   → 1 이벤트 = N행 (changes 배열 원소 수만큼 pre-exploded)
--
--   누락 필드 (ld 로그 포맷에 포함되지 않음):
--     subject, dataschema, user_name, dataset_id, action, input_type, targets, params
--
-- 소스:  {catalog}.labelit_raw.raw_labelit_ld  (Zerobus → Delta Table)
-- 타깃:  {catalog}.labelit_raw.raw_labelit__ld
--
-- 증분 기준: occurred_at (서버 수신 시각)
-- 고유키:   (event_id, change_idx)
-- ============================================================


-- ─────────────────────────────────────────────
-- [CELL 1] 타깃 테이블 생성 (최초 1회)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ${catalog}.labelit_raw.raw_labelit__ld (
  event_id      STRING     NOT NULL COMMENT '이벤트 고유 ID',
  event_type    STRING     NOT NULL COMMENT 'CloudEvent type (annotation.line.create / annotation.lane.create / annotation.topology.create)',
  event_time    TIMESTAMP           COMMENT '클라이언트 발생 시각 (ms 오차 있음)',
  event_date    DATE       NOT NULL COMMENT '파티션 키 — event_time 기준 날짜',
  occurred_at   TIMESTAMP  NOT NULL COMMENT '서버 수신 시각',
  session_id    STRING              COMMENT '세션 ID',
  user_id       STRING              COMMENT '사용자 ID (MongoDB ObjectId)',
  task_id       STRING              COMMENT '작업 태스크 ID',
  feature       STRING              COMMENT '라벨링 피처 값 (ld)',
  change_idx    INT        NOT NULL COMMENT 'changes 내 순서 (0부터 시작). 소스에서 pre-exploded',
  object_id     INT                 COMMENT '변경 대상 오브젝트 ID (trackingId)',
  object_type   STRING              COMMENT '오브젝트 타입 — line / point / lane / topology',
  change_action STRING              COMMENT '변경 액션 (create)',
  old_val       STRING              COMMENT '변경 전 상태. create 액션은 NULL',
  new_val       STRING              COMMENT '변경 후 상태 JSON. object_type별 구조 상이'
)
USING DELTA
PARTITIONED BY (event_date)
COMMENT 'Raw 레이어: ld feature 로그 — pre-exploded 구조 (1행 = 1 change)';


-- ─────────────────────────────────────────────
-- [CELL 2] Schema Evolution 활성화
-- ─────────────────────────────────────────────
SET spark.databricks.delta.schema.autoMerge.enabled = true;


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 3] 증분 MERGE (배치 실행마다)
-- 전략: (event_id, change_idx) 기준 upsert
-- ─────────────────────────────────────────────
MERGE INTO ${catalog}.labelit_raw.raw_labelit__ld AS t
USING (
  SELECT
    event_id,
    event_type,
    to_timestamp(event_time)         AS event_time,
    DATE(to_timestamp(event_time))   AS event_date,
    to_timestamp(occurred_at)        AS occurred_at,
    session_id,
    user_id,
    task_id,
    feature,
    CAST(change_idx AS INT)          AS change_idx,
    CAST(object_id  AS INT)          AS object_id,
    object_type,
    change_action,
    NULLIF(old_val, 'null')          AS old_val,   -- 'null' 문자열 → SQL NULL 정규화
    new_val
  FROM ${catalog}.labelit_raw.raw_labelit_ld
  WHERE to_timestamp(occurred_at) > (
    SELECT COALESCE(MAX(occurred_at), TIMESTAMP '1970-01-01 00:00:00')
    FROM   ${catalog}.labelit_raw.raw_labelit__ld
  )
) AS s
ON t.event_id = s.event_id AND t.change_idx = s.change_idx
WHEN NOT MATCHED THEN INSERT *;


-- ─────────────────────────────────────────────
-- [CELL 4] 적재 현황 확인
-- ─────────────────────────────────────────────
SELECT
  event_date,
  event_type,
  object_type,
  COUNT(DISTINCT event_id) AS event_cnt,
  COUNT(*)                 AS change_cnt,
  MIN(occurred_at)         AS min_occurred_at,
  MAX(occurred_at)         AS max_occurred_at
FROM   ${catalog}.labelit_raw.raw_labelit__ld
GROUP BY event_date, event_type, object_type
ORDER BY event_date DESC, event_type, object_type;
