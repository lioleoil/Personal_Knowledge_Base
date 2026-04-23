-- Databricks notebook source
-- task_key: int_{domain}__{entity}_{verb}
--
-- ─────────────────────────────────────────────
-- 파일 네이밍 규칙 (naming_rules.md)
--   intermediate : int_{domain}__{entity}_{verb}.sql
--   verb 허용값  : _matched / _joined / _enriched / _aggregated / _filtered / _ranked
--   task_key     : 파일명 (확장자 제외) 그대로 사용
--   테이블명      : 복수형, snake_case, __ 로 도메인-엔티티 구분
--
-- 체크리스트
--   [ ] task_key 파일명과 일치하는지 확인
--   [ ] ${catalog} 위젯 사용 (${var.catalog} 사용 금지)
--   [ ] SELECT * 사용 금지
--   [ ] 테이블 COMMENT: MUST (한 줄, '{소스} 정제. {핵심 비즈니스 룰 요약}')
--   [ ] 컬럼 COMMENT: 비자명 컬럼에만 작성
--   [ ] PK CHECK CONSTRAINT: MUST
--   [ ] 갱신 전략: 전체 재계산 (is_reverted 등 전체 재집계 필요한 경우)
--                 데이터 볼륨 증가 시 MERGE 방식 전환 고려
-- ─────────────────────────────────────────────

-- ============================================================
-- Notebook: Intermediate — int_{domain}__{entity}_{verb}
-- 실행 빈도: 배치 실행마다 ({선행 태스크} 완료 후)
--
-- 목적:
--   {목적 설명}
--
-- 소스:  {catalog}.{source_schema}.{source_table}
-- 타깃:  {catalog}.{target_schema}.int_{domain}__{entity}_{verb}
--
-- 갱신 전략: CREATE OR REPLACE (전체 재계산)
--   {재계산이 필요한 이유 — 예: is_reverted는 undo/redo 도착 시 전체 재집계 필요}
-- ============================================================


-- ─────────────────────────────────────────────
-- [CELL 1] 테이블 전체 재계산 (CREATE OR REPLACE)
-- ─────────────────────────────────────────────
CREATE OR REPLACE TABLE ${catalog}.{target_schema}.int_{domain}__{entity}_{verb}
USING DELTA
PARTITIONED BY ({partition_col})
AS

-- 1st CTE: {필터링/기본 선택 목적 — 예: 특정 조건 행만, 필요한 컬럼만 선택}
WITH base AS (
  SELECT
    {col_1},
    {col_2}
  FROM ${catalog}.{source_schema}.{source_table}
  WHERE {filter_condition}
),

-- 2nd CTE: {변환/집계/조인 목적 — 예: 파생 지표 계산, 외부 테이블 조인}
transformed AS (
  SELECT
    b.{col_1},
    {expression}                   AS {derived_col}
  FROM base b
  -- LEFT JOIN ${catalog}.{schema}.{other_table} x ON b.{key} = x.{key}
)

-- Final: {파생 컬럼 목적 — 예: CASE 분류, 최종 플래그}
SELECT
  {col_1},
  {col_2},
  CASE
    WHEN {condition_1} THEN '{value_1}'
    ELSE '{default_value}'
  END                              AS {derived_col}
FROM transformed;


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 2] 테이블/컬럼 문서화 (Catalog Explorer에서 조회 가능)
-- ─────────────────────────────────────────────
-- 테이블 COMMENT: MUST — '{소스} 정제. {핵심 비즈니스 룰 요약}'
COMMENT ON TABLE ${catalog}.{target_schema}.int_{domain}__{entity}_{verb}
  IS '{소스 레이어}: {핵심 변환 내용 요약}';

-- 컬럼 COMMENT: 아래 경우에만 작성 (자명한 컬럼 제외)
--   - 비즈니스 룰 내장 컬럼  예) is_reverted — undo로 최종 취소된 이벤트 여부
--   - 계산 로직이 있는 컬럼  예) move_distance — 3D 유클리드 거리 (소수점 4자리)
--   - CASE 분류 컬럼         예) move_category — 미세조정/소폭이동/중폭이동/대폭이동
ALTER TABLE ${catalog}.{target_schema}.int_{domain}__{entity}_{verb}
  ALTER COLUMN {col} SET COMMENT '{설명}';


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 3] 품질 제약 (Delta Lake가 자동 검증)
-- ─────────────────────────────────────────────
-- 네이밍: {테이블약칭}_{규칙}
--   약칭 예시: eff (effective_changes) / bt (bbox3d_transforms)
-- PK not null: MUST
ALTER TABLE ${catalog}.{target_schema}.int_{domain}__{entity}_{verb}
  ADD CONSTRAINT {약칭}_pk_not_null CHECK ({pk_col} IS NOT NULL);


-- COMMAND ----------

-- ─────────────────────────────────────────────
-- [CELL 4] 결과 확인
-- ─────────────────────────────────────────────
SELECT
  {partition_col},
  COUNT(*) AS row_cnt
FROM   ${catalog}.{target_schema}.int_{domain}__{entity}_{verb}
GROUP BY {partition_col}
ORDER BY {partition_col} DESC;
