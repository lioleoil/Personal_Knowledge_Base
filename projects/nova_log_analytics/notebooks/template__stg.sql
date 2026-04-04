-- Databricks notebook source
-- task_key: stg_{domain}__{entity}
--
-- ─────────────────────────────────────────────
-- 파일 네이밍 규칙 (naming_rules.md)
--   staging  : stg_{domain}__{entity}.sql
--   task_key : 파일명 (확장자 제외) 그대로 사용
--   테이블명  : 복수형, snake_case, __ 로 도메인-엔티티 구분
--
-- 체크리스트
--   [ ] task_key 파일명과 일치하는지 확인
--   [ ] ${catalog} 위젯 사용 (${var.catalog} 사용 금지)
--   [ ] SELECT * 사용 금지
--   [ ] 테이블 COMMENT: MUST (한 줄, '{소스} 정제. {핵심 비즈니스 룰 요약}')
--   [ ] 컬럼 COMMENT: 비자명 컬럼에만 작성
--   [ ] PK CHECK CONSTRAINT: MUST
-- ─────────────────────────────────────────────

-- ============================================================
-- Notebook: Staging — stg_{domain}__{entity}
-- 실행 빈도: 배치 실행마다 ({선행 태스크} 완료 후)
--
-- 목적:
--   {목적 설명}
--
-- 소스:  {catalog}.{source_schema}.{source_table}
-- 타깃:  {catalog}.{target_schema}.stg_{domain}__{entity}
-- ============================================================


-- ─────────────────────────────────────────────
-- [CELL 1] 테이블 전체 재계산 (CREATE OR REPLACE)
-- ─────────────────────────────────────────────
CREATE OR REPLACE TABLE ${catalog}.{target_schema}.stg_{domain}__{entity}
USING DELTA
PARTITIONED BY ({partition_col})
AS

-- 1st CTE: {필터링 목적 — 예: 특정 이벤트 타입 제외, 유효 행만 선택}
WITH filtered AS (
  SELECT
    {col_1},
    {col_2}
  FROM ${catalog}.{source_schema}.{source_table}
  WHERE {filter_condition}
),

-- 2nd CTE: {파싱/변환 목적 — 예: JSON 파싱, 타입 캐스팅, 컬럼명 정리}
parsed AS (
  SELECT
    {col_1}                        AS {renamed_col},
    {expression}                   AS {parsed_col}
  FROM filtered
)

-- Final: {파생 컬럼 목적 — 예: CASE 분류, 파생 지표}
SELECT
  {col_1},
  {col_2},
  CASE
    WHEN {condition_1} THEN '{value_1}'
    WHEN {condition_2} THEN '{value_2}'
    ELSE '{default_value}'
  END                              AS {derived_col}
FROM parsed;


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 2] 테이블/컬럼 문서화 (Catalog Explorer에서 조회 가능)
-- ─────────────────────────────────────────────
-- 테이블 COMMENT: MUST — '{소스} 정제. {핵심 비즈니스 룰 요약}'
COMMENT ON TABLE ${catalog}.{target_schema}.stg_{domain}__{entity}
  IS '{소스} 정제. {핵심 비즈니스 룰 요약}';

-- 컬럼 COMMENT: 아래 경우에만 작성 (자명한 컬럼 name / created_at 등 제외)
--   - 변환이 비자명한 컬럼  예) LOWER(HEX(_id)) — MongoDB Binary → hex string
--   - 비즈니스 룰 내장 컬럼 예) dimension — flags 기반 2D/3D 판정
--   - CASE/매핑 로직 컬럼   예) feature_gen — od → Gen1 / od2 → Gen2
--   - 파생 컬럼             예) scene_index — name이 숫자일 때만 CAST
ALTER TABLE ${catalog}.{target_schema}.stg_{domain}__{entity}
  ALTER COLUMN {col} SET COMMENT '{설명}';


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 3] 품질 제약 (Delta Lake가 자동 검증)
-- ─────────────────────────────────────────────
-- 네이밍: {테이블약칭}_{규칙}
--   약칭 예시: di (data_item) / ev (events) / ec (event_changes)
-- PK not null: MUST
-- FK not null / 값 범위: OPTIONAL — 확실한 것만 추가 (과도한 제약은 파이프라인을 깨뜨림)
ALTER TABLE ${catalog}.{target_schema}.stg_{domain}__{entity}
  ADD CONSTRAINT {약칭}_pk_not_null CHECK ({pk_col} IS NOT NULL);


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 4] 적재 현황 확인
-- ─────────────────────────────────────────────
SELECT
  {partition_col},
  COUNT(*) AS row_cnt
FROM   ${catalog}.{target_schema}.stg_{domain}__{entity}
GROUP BY {partition_col}
ORDER BY {partition_col} DESC;
