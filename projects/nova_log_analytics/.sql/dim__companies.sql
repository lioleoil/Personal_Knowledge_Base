-- Databricks notebook source
-- Dimension: dim_companies (업체 목록, 일 OVERWRITE)
-- 소스: raw_labelit__company (CDC dedup)
-- grain: company _id
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체)
-- 실행 주기: 일 배치 (stg 완료 후)
-- 선행 조건: 없음 (raw 직접 참조)

-- COMMAND ----------

CREATE WIDGET TEXT catalog DEFAULT "sv_nova_dev_an2_catalog";

-- COMMAND ----------

INSERT OVERWRITE analytics.dim_companies
WITH latest AS (
  SELECT
    `_id`,
    `_raw`,
    `_ingested_at`,
    ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__company`
  WHERE `_is_deleted` = false
)
SELECT
  `_id`                                        AS company_id,
  get_json_object(`_raw`, '$.name')            AS company_name,
  CURRENT_TIMESTAMP()                          AS _loaded_at
FROM latest
WHERE rn = 1
  AND `_id` IS NOT NULL;

-- COMMAND ----------

-- ★ 적재 확인
SELECT company_id, company_name, _loaded_at
FROM analytics.dim_companies
ORDER BY company_name;
