-- Databricks notebook source
-- [DEPRECATED] Inspection Quality DDL → mrt__ddl.sql 로 통합됨
-- 이 파일은 mrt__ddl.sql 마이그레이션 검증 완료 후 삭제 예정
-- ────────────────────────────────────────────────────────────────
-- Inspection Quality — 테이블 초기 생성 DDL
-- 실행 조건: Unity Catalog 환경, analytics 스키마 존재

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 1. inspection_quality_monthly_fpy
--    월별 검수 반려율 & First Pass Yield
--    소스: inspection_quality__monthly_fpy.sql
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.inspection_quality_monthly_fpy (
  deliver_month        STRING,   -- 'yy-MM' 형식 (예: 26-04)
  total_inspected      BIGINT,   -- 해당 월 전체 검수 통과 Task 수
  rejected_count       BIGINT,   -- 1회 이상 inspection 반려된 Task 수
  rejection_rate_pct   DOUBLE,   -- 반려율 (%) = rejected_count / total_inspected × 100
  first_pass_yield_pct DOUBLE,   -- FPY (%) = 100 - rejection_rate_pct
  distinct_reasons     ARRAY<STRING>  -- 월별 반려 사유 전체 목록 (중복 제거)
)
USING DELTA
PARTITIONED BY (deliver_month)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE analytics.inspection_quality_monthly_fpy
  IS 'Monthly inspection rejection rate and First Pass Yield (FPY) by delivered tasks.';
ALTER TABLE analytics.inspection_quality_monthly_fpy
  ADD CONSTRAINT fpy_deliver_month_not_null CHECK (deliver_month IS NOT NULL);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 2. inspection_quality_multi_reject
--    다중 반려 Task 상세 (inspection reject ≥ 2)
--    소스: inspection_quality__multi_reject_detail.sql
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.inspection_quality_multi_reject (
  task_id       STRING,
  task_name     STRING,
  assignment_id STRING,
  deliver_month STRING,  -- 'yy-MM' 형식
  reject_count  BIGINT,  -- 해당 task의 inspection 반려 횟수 (≥ 2)
  reject_details ARRAY<STRUCT<
    rejected_at:     STRING,
    rejected_by:     STRING,
    reject_reason:   STRING
  >>             -- 반려 이벤트 시계열 (actionAt, actionBy, reason)
)
USING DELTA
PARTITIONED BY (deliver_month)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE analytics.inspection_quality_multi_reject
  IS 'Monthly task-level detail for inspection reject >= 2 occurrences.';
ALTER TABLE analytics.inspection_quality_multi_reject
  ADD CONSTRAINT mr_task_id_not_null     CHECK (task_id       IS NOT NULL);
ALTER TABLE analytics.inspection_quality_multi_reject
  ADD CONSTRAINT mr_deliver_month_not_null CHECK (deliver_month IS NOT NULL);

-- COMMAND ----------

-- ★ 생성 확인
SELECT table_name, partition_columns
FROM information_schema.tables
WHERE table_schema = 'analytics'
  AND table_name LIKE 'inspection_quality_%'
ORDER BY table_name;
