-- Databricks notebook source
-- Intermediate Layer — Dimension Lookup Tables DDL
-- 실행 조건: Unity Catalog 환경, analytics 스키마 존재
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체, CDC dedup 포함)
--
-- 현행 테이블:
--   dim_companies   — 업체 목록 (라벨링·검수 공통)
--   dim_policies    — 어노테이션 정책 (feature 매핑)
--   dim_assignments — 어사이먼트(작업 배치) 메타데이터
-- [대기]
--   dim_users       — 유저 목록 (raw 샘플 확인 후 추가 예정)

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 1. dim_companies
--    소스: raw_labelit__company (CDC dedup)
--    grain: company _id
--    소스 파일: dim__companies.sql (일 OVERWRITE)
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.dim_companies (
  company_id   STRING,       -- raw_labelit__company._id
  company_name STRING,       -- _raw.name
  _loaded_at   TIMESTAMP
)
USING DELTA
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE analytics.dim_companies
  IS 'Company lookup. CDC dedup from raw_labelit__company. Daily OVERWRITE.';
ALTER TABLE analytics.dim_companies
  ADD CONSTRAINT dc_company_id_not_null CHECK (company_id IS NOT NULL);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 2. dim_policies
--    소스: raw_labelit__gen2_annotation_policies (CDC dedup)
--    grain: policy _id
--    소스 파일: dim__policies.sql (일 OVERWRITE)
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.dim_policies (
  policy_id    STRING,       -- raw_labelit__gen2_annotation_policies._id
  feature      STRING,       -- _raw.feature (ld / od / rmd 등)
  _loaded_at   TIMESTAMP
)
USING DELTA
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE analytics.dim_policies
  IS 'Annotation policy lookup. feature field for object table mapping. CDC dedup. Daily OVERWRITE.';
ALTER TABLE analytics.dim_policies
  ADD CONSTRAINT dp_policy_id_not_null CHECK (policy_id IS NOT NULL);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 3. dim_assignments
--    소스: raw_labelit__assignments (CDC dedup)
--    grain: assignment _id
--    소스 파일: dim__assignments.sql (일 OVERWRITE)
--    참고: policy_id / delivery_id — gen2_tasks._raw 에서 확인 필요 (미포함)
--          workflowSnapshot.stages → dim_stages 설계 시 활용 예정
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.dim_assignments (
  assignment_id             STRING,        -- raw_labelit__assignments._id
  company_id                STRING,        -- _raw.companyId (라벨링 업체)
  review_company_id         STRING,        -- _raw.reviewCompanyIds[0] (검수 업체)
  assignment_name           STRING,        -- _raw.name
  description               STRING,        -- _raw.description
  status                    STRING,        -- _raw.status (READY 등)
  purpose                   STRING,        -- _raw.purpose (PRODUCTION 등)
  tags                      ARRAY<STRING>, -- _raw.tags (["DeliveryDate_YYMMDD", "CW" ...])
  workflow_definition_id    STRING,        -- _raw.workflowDefinitionId
  total_data_package_count  BIGINT,        -- _raw.totalDataPackageCount
  created_at                TIMESTAMP,     -- _raw.createdAt
  _loaded_at                TIMESTAMP
)
USING DELTA
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE analytics.dim_assignments
  IS 'Assignment metadata lookup. CDC dedup from raw_labelit__assignments. tags includes DeliveryDate/CW markers. Daily OVERWRITE.';
ALTER TABLE analytics.dim_assignments
  ADD CONSTRAINT da_assignment_id_not_null CHECK (assignment_id IS NOT NULL);
ALTER TABLE analytics.dim_assignments
  ADD CONSTRAINT da_company_id_not_null    CHECK (company_id    IS NOT NULL);

-- COMMAND ----------

-- ★ 생성 확인
SELECT table_name, partition_columns
FROM information_schema.tables
WHERE table_schema = 'analytics'
  AND table_name LIKE 'dim_%'
ORDER BY table_name;
