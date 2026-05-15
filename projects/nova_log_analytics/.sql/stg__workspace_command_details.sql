-- Databricks notebook source
-- Staging: stg_workspace_command_details
-- workspace_command 상세 — targets / changes(old/new 포함 전체) / params
-- grain: command _id (stg_workspace_commands와 1:1 대응)
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체, stg_workspace_commands와 동일 배치)
-- 실행 주기: 일 배치 04:00 UTC (stg_workspace_commands 와 함께 실행)
-- 활용: 객체 영향 범위 분석, 변경 내역 추적 (intermediate에서 explode 처리)

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.stg_workspace_command_details (
  command_id   STRING         COMMENT 'workspace_command._id — 커맨드 고유 식별자 (stg_workspace_commands FK)',
  event_date   DATE           COMMENT 'event_time KST 변환 후 DATE',
  targets      ARRAY<BIGINT>  COMMENT 'data.targets — 영향받은 객체 ID 목록',
  changes      STRING         COMMENT 'data.changes — 변경 내역 JSON (old/new 포함)',
  params       STRING         COMMENT 'data.params — 커맨드 파라미터 JSON',
  _loaded_at   TIMESTAMP      COMMENT '데이터 적재 시각 (CURRENT_TIMESTAMP at INSERT)'
)
COMMENT 'workspace_command 상세 (targets/changes/params). grain: command_id (1:1). 소스: raw.raw_labelit__workspace_command. 갱신: INSERT OVERWRITE (일 전체 교체). 실행 주기: 일 배치 04:00 UTC.'
TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

INSERT OVERWRITE sv_nova_dev_an2_catalog.analytics.stg_workspace_command_details
WITH latest_commands AS (
  SELECT `_id`, `_raw`, `_occurred_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_occurred_at` DESC) AS rn
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__workspace_command`
)
SELECT
  `_id`                                                                       AS command_id,
  DATE(CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
    TO_TIMESTAMP(`_raw`:time::STRING)))                                       AS event_date,
  FROM_JSON(`_raw`:data.targets::STRING, 'ARRAY<BIGINT>')                     AS targets,
  `_raw`:data.changes::STRING                                                 AS changes,
  `_raw`:data.params::STRING                                                  AS params,
  CURRENT_TIMESTAMP()                                                         AS _loaded_at
FROM latest_commands
WHERE rn = 1
  AND `_raw`:time::STRING IS NOT NULL;

-- COMMAND ----------

-- ★ 테이블/컬럼 설명 업데이트 (기존 테이블 대응)
COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_command_details IS 'workspace_command 상세 (targets/changes/params). grain: command_id (1:1). 소스: raw.raw_labelit__workspace_command. 갱신: INSERT OVERWRITE (일 전체 교체). 실행 주기: 일 배치 04:00 UTC.';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_command_details ALTER COLUMN command_id COMMENT 'workspace_command._id — 커맨드 고유 식별자 (stg_workspace_commands FK)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_command_details ALTER COLUMN event_date COMMENT 'event_time KST 변환 후 DATE';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_command_details ALTER COLUMN targets COMMENT 'data.targets — 영향받은 객체 ID 목록';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_command_details ALTER COLUMN changes COMMENT 'data.changes — 변경 내역 JSON (old/new 포함)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_command_details ALTER COLUMN params COMMENT 'data.params — 커맨드 파라미터 JSON';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_command_details ALTER COLUMN _loaded_at COMMENT '데이터 적재 시각 (CURRENT_TIMESTAMP at INSERT)';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_command_details SET TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ★ 적재 확인
SELECT
  event_date,
  COUNT(DISTINCT command_id)                            AS commands,
  COUNT(CASE WHEN targets IS NOT NULL THEN 1 END)       AS has_targets,
  COUNT(CASE WHEN changes IS NOT NULL THEN 1 END)       AS has_changes,
  ROUND(AVG(SIZE(targets)), 1)                          AS avg_target_count
FROM sv_nova_dev_an2_catalog.analytics.stg_workspace_command_details
WHERE event_date >= CURRENT_DATE() - INTERVAL 7 DAYS
GROUP BY event_date
ORDER BY event_date DESC;