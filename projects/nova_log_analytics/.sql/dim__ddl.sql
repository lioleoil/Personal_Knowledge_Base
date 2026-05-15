-- Dimension Layer — 테이블 초기 생성 DDL
-- 실행 조건: Unity Catalog 환경, analytics 스키마 존재
-- 현행 테이블: dim_companies / dim_assignments / dim_policies

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 1. dim_companies
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.dim_companies (
  company_id   STRING    COMMENT '업체 고유 ID (raw_labelit__company._id)',
  company_name STRING    COMMENT '업체명 ($.name)',
  _loaded_at   TIMESTAMP COMMENT '적재 시점'
)
COMMENT '업체 마스터. grain: company_id. 소스: raw_labelit__company (CDC dedup). 갱신: INSERT OVERWRITE.'
TBLPROPERTIES ('quality' = 'gold');

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 2. dim_assignments
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.dim_assignments (
  assignment_id            STRING         COMMENT '어사인먼트 고유 ID (raw_labelit__gen2_assignments._id)',
  company_id               STRING         COMMENT '소속 업체 ID ($.companyId)',
  review_company_id        STRING         COMMENT '검수 업체 ID ($.reviewCompanyIds[0])',
  assignment_name          STRING         COMMENT '어사인먼트명 ($.name)',
  description              STRING         COMMENT '설명 ($.description)',
  status                   STRING         COMMENT '상태 (READY / PENDING 등)',
  purpose                  STRING         COMMENT '목적 (PRODUCTION / NON_PRODUCTION)',
  tags                     ARRAY<STRING>  COMMENT '태그 배열 ($.tags)',
  workflow_definition_id   STRING         COMMENT '워크플로우 정의 ID',
  total_data_package_count BIGINT         COMMENT '총 데이터 패키지 수',
  created_at               TIMESTAMP      COMMENT '어사인먼트 생성 시각 (UTC)',
  _loaded_at               TIMESTAMP      COMMENT '적재 시점'
)
COMMENT '어사인먼트 마스터. grain: assignment_id. 소스: raw_labelit__gen2_assignments (CDC dedup). 갱신: INSERT OVERWRITE.'
TBLPROPERTIES ('quality' = 'gold');

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 3. dim_policies
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.dim_policies (
  policy_id  STRING    COMMENT '정책 고유 ID (raw_labelit__gen2_annotation_policies._id)',
  feature    STRING    COMMENT 'Feature 도메인 (OD / LD / RMD 등)',
  _loaded_at TIMESTAMP COMMENT '적재 시점'
)
COMMENT '어노테이션 정책 마스터. grain: policy_id. 소스: raw_labelit__gen2_annotation_policies (CDC dedup). 갱신: INSERT OVERWRITE.'
TBLPROPERTIES ('quality' = 'gold');