-- Dimension: dim_assignments (어사인먼트 마스터)
-- 소스: raw.raw_labelit__gen2_assignments (CDC dedup)
-- grain: assignment_id
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체)
-- 실행 주기: 일 배치 04:00 UTC
-- 제약조건: company_id IS NOT NULL (CHECK constraint 존재)

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

INSERT OVERWRITE sv_nova_dev_an2_catalog.analytics.dim_assignments
WITH latest AS (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_assignments`
  WHERE `_is_deleted` = false
)
SELECT
  `_id`                                                          AS assignment_id,
  get_json_object(`_raw`, '$.companyId')                         AS company_id,
  get_json_object(`_raw`, '$.reviewCompanyIds[0]')               AS review_company_id,
  get_json_object(`_raw`, '$.name')                              AS assignment_name,
  get_json_object(`_raw`, '$.description')                       AS description,
  get_json_object(`_raw`, '$.status')                            AS status,
  get_json_object(`_raw`, '$.purpose')                           AS purpose,
  FROM_JSON(get_json_object(`_raw`, '$.tags'), 'ARRAY<STRING>')  AS tags,
  get_json_object(`_raw`, '$.workflowDefinitionId')              AS workflow_definition_id,
  CAST(get_json_object(`_raw`, '$.totalDataPackageCount') AS BIGINT) AS total_data_package_count,
  TO_TIMESTAMP(get_json_object(`_raw`, '$.createdAt'))           AS created_at,
  CURRENT_TIMESTAMP()                                            AS _loaded_at
FROM latest
WHERE rn = 1
  AND get_json_object(`_raw`, '$.companyId') IS NOT NULL;

-- COMMAND ----------

COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.dim_assignments
  IS '어사인먼트 마스터. grain: assignment_id. 소스: raw_labelit__gen2_assignments (CDC dedup). 갱신: INSERT OVERWRITE. 제약: company_id NOT NULL.';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.dim_assignments SET TBLPROPERTIES ('quality' = 'gold');

-- COMMAND ----------

-- ★ 적재 확인
SELECT COUNT(*) AS total_assignments, COUNT(DISTINCT company_id) AS companies
FROM sv_nova_dev_an2_catalog.analytics.dim_assignments;