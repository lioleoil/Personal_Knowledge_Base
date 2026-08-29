-- Dimension: dim_companies (업체 마스터)
-- 소스: raw.raw_labelit__company (CDC dedup)
-- grain: company_id
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체)
-- 실행 주기: 일 배치 04:00 UTC

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

INSERT OVERWRITE sv_nova_dev_an2_catalog.analytics.dim_companies
WITH latest AS (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__company`
  WHERE `_is_deleted` = false
)
SELECT
  `_id`                                    AS company_id,
  get_json_object(`_raw`, '$.name')        AS company_name,
  CURRENT_TIMESTAMP()                      AS _loaded_at
FROM latest
WHERE rn = 1;

-- COMMAND ----------

COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.dim_companies
  IS '업체 마스터. grain: company_id. 소스: raw_labelit__company (CDC dedup). 갱신: INSERT OVERWRITE.';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.dim_companies ALTER COLUMN company_id COMMENT '업체 고유 ID (raw_labelit__company._id)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.dim_companies ALTER COLUMN company_name COMMENT '업체명 ($.name)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.dim_companies ALTER COLUMN _loaded_at COMMENT '적재 시점';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.dim_companies SET TBLPROPERTIES ('quality' = 'gold');

-- COMMAND ----------

-- ★ 적재 확인: 업체별 Task 수 결합 검증 (dim 조인 가능성 확인)
SELECT
  c.company_name,
  COUNT(t.task_id) AS task_count
FROM sv_nova_dev_an2_catalog.analytics.dim_companies c
LEFT JOIN sv_nova_dev_an2_catalog.analytics.stg_tasks t ON c.company_id = t.company_id
GROUP BY c.company_name
ORDER BY task_count DESC;