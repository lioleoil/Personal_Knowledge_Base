-- Databricks notebook source
-- Dimension: dim_assignments (어사이먼트 메타데이터, 일 OVERWRITE)
-- 소스: raw_labelit__assignments (CDC dedup)
-- grain: assignment _id
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체)
-- 실행 주기: 일 배치 (stg 완료 후)
-- 선행 조건: 없음 (raw 직접 참조)
-- 참고: policy_id / delivery_id 는 raw_labelit__assignments 에 없음 → gen2_tasks._raw 참조

-- COMMAND ----------

CREATE WIDGET TEXT catalog DEFAULT "sv_nova_dev_an2_catalog";

-- COMMAND ----------

INSERT OVERWRITE analytics.dim_assignments
WITH latest AS (
  SELECT
    `_id`,
    `_raw`,
    `_ingested_at`,
    ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__assignments`
  WHERE `_is_deleted` = false
)
SELECT
  `_id`                                                                   AS assignment_id,
  get_json_object(`_raw`, '$.companyId')                                  AS company_id,
  get_json_object(`_raw`, '$.reviewCompanyIds[0]')                        AS review_company_id,
  get_json_object(`_raw`, '$.name')                                       AS assignment_name,
  get_json_object(`_raw`, '$.description')                                AS description,
  get_json_object(`_raw`, '$.status')                                     AS status,
  get_json_object(`_raw`, '$.purpose')                                    AS purpose,
  FROM_JSON(get_json_object(`_raw`, '$.tags'), 'ARRAY<STRING>')           AS tags,
  get_json_object(`_raw`, '$.workflowDefinitionId')                       AS workflow_definition_id,
  CAST(get_json_object(`_raw`, '$.totalDataPackageCount') AS BIGINT)      AS total_data_package_count,
  TO_TIMESTAMP(get_json_object(`_raw`, '$.createdAt'))                    AS created_at,
  CURRENT_TIMESTAMP()                                                     AS _loaded_at
FROM latest
WHERE rn = 1
  AND `_id` IS NOT NULL
  AND get_json_object(`_raw`, '$.companyId') IS NOT NULL;

-- COMMAND ----------

-- ★ 적재 확인
SELECT
  assignment_id,
  company_id,
  review_company_id,
  assignment_name,
  status,
  purpose,
  tags,
  total_data_package_count,
  created_at
FROM analytics.dim_assignments
ORDER BY created_at DESC
LIMIT 20;
