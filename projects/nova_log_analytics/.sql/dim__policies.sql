-- Dimension: dim_policies (어노테이션 정책 마스터)
-- 소스: raw.raw_labelit__gen2_annotation_policies (CDC dedup)
-- grain: policy_id
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체)
-- 실행 주기: 일 배치 04:00 UTC

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

INSERT OVERWRITE sv_nova_dev_an2_catalog.analytics.dim_policies
WITH latest AS (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__gen2_annotation_policies`
  WHERE `_is_deleted` = false
)
SELECT
  `_id`                                    AS policy_id,
  get_json_object(`_raw`, '$.feature')     AS feature,
  CURRENT_TIMESTAMP()                      AS _loaded_at
FROM latest
WHERE rn = 1;

-- COMMAND ----------

COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.dim_policies
  IS '어노테이션 정책 마스터. grain: policy_id. 소스: raw_labelit__gen2_annotation_policies (CDC dedup). 갱신: INSERT OVERWRITE.';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.dim_policies ALTER COLUMN policy_id COMMENT '정책 고유 ID (raw_labelit__gen2_annotation_policies._id)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.dim_policies ALTER COLUMN feature COMMENT 'Feature 도메인 (OD / LD / RMD 등)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.dim_policies ALTER COLUMN _loaded_at COMMENT '적재 시점';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.dim_policies SET TBLPROPERTIES ('quality' = 'gold');

-- COMMAND ----------

-- ★ 적재 확인: Feature별 Task 수 결합 검증 (dim 조인 가능성 확인)
SELECT
  p.feature,
  COUNT(t.task_id) AS task_count
FROM sv_nova_dev_an2_catalog.analytics.dim_policies p
LEFT JOIN sv_nova_dev_an2_catalog.analytics.stg_tasks t ON p.policy_id = t.policy_id
GROUP BY p.feature
ORDER BY task_count DESC;