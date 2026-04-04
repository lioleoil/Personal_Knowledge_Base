-- Databricks notebook source
-- task_key: raw_labelit__workspace_command

-- ============================================================
-- Notebook 01: Raw Layer — raw_labelit__workspace_command
-- 실행 빈도: 배치 실행마다
--
-- 목적:
--   소스 Delta Table을 1:1 미러링
--   _raw JSON 파싱 없음 — 타입 캐스팅 및 컬럼명 정리만 수행
--
-- 소스:  {catalog}.labelit_raw.raw_labelit_workspace_command
--         (Zerobus → MongoDB → Delta Table, 스트리밍 적재)
-- 타깃:  {catalog}.labelit_raw.raw_labelit__workspace_command
--
-- 증분 기준: occurred_at (서버 수신 시각)
--   - event_time(클라이언트 발생 시각)은 배치 전송 특성상 ms 오차가 있어 기준에서 제외
-- ============================================================


-- ─────────────────────────────────────────────
-- [CELL 1] 타깃 테이블 생성 (최초 1회)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ${catalog}.labelit_raw.raw_labelit__workspace_command (
  event_id    STRING    NOT NULL COMMENT '이벤트 고유 ID (소스 _id)',
  _raw        STRING    NOT NULL COMMENT 'CloudEvent 1.0 전체 JSON 원본 (파싱 없이 보존)',
  occurred_at TIMESTAMP NOT NULL COMMENT '서버 수신 시각 (배치 전송으로 여러 이벤트가 동일 시각일 수 있음)',
  loaded_date DATE      NOT NULL COMMENT '파티션 키 — occurred_at 기준 날짜'
)
USING DELTA
PARTITIONED BY (loaded_date)
COMMENT 'Raw 레이어: 소스 1:1 미러 — 비즈니스 로직 없음';


-- ─────────────────────────────────────────────
-- [CELL 2] Schema Evolution 활성화
-- 소스 스키마 변경 시 타깃 테이블에 자동 병합 (raw 레이어 전략)
-- ─────────────────────────────────────────────
SET spark.databricks.delta.schema.autoMerge.enabled = true;


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 3] 증분 MERGE (배치 실행마다)
-- 전략: event_id 기준 upsert (중복 없이 신규만 삽입)
-- ─────────────────────────────────────────────
MERGE INTO ${catalog}.labelit_raw.raw_labelit__workspace_command AS t
USING (
  SELECT
    _id                               AS event_id,
    _raw,
    to_timestamp(occurred_at)         AS occurred_at,
    DATE(to_timestamp(occurred_at))   AS loaded_date
  FROM ${catalog}.labelit_raw.raw_labelit_workspace_command
  WHERE to_timestamp(occurred_at) > (
    SELECT COALESCE(MAX(occurred_at), TIMESTAMP '1970-01-01 00:00:00')
    FROM   ${catalog}.labelit_raw.raw_labelit__workspace_command
  )
) AS s
ON t.event_id = s.event_id
WHEN NOT MATCHED THEN INSERT *;


-- ─────────────────────────────────────────────
-- [CELL 4] 적재 현황 확인
-- ─────────────────────────────────────────────
SELECT
  loaded_date,
  COUNT(*)  AS event_cnt,
  MIN(occurred_at) AS min_occurred_at,
  MAX(occurred_at) AS max_occurred_at
FROM   ${catalog}.labelit_raw.raw_labelit__workspace_command
GROUP BY loaded_date
ORDER BY loaded_date DESC
LIMIT 10;
