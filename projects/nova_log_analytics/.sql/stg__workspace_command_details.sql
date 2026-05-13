-- Databricks notebook source
-- Staging: stg_workspace_command_details
-- workspace_command 상세 — targets / changes(old/new 포함 전체) / params
-- grain: command _id (stg_workspace_commands와 1:1 대응)
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체, stg_workspace_commands와 동일 배치)
-- 실행 주기: 일 배치 04:00 UTC (stg_workspace_commands 와 함께 실행)
-- 활용: 객체 영향 범위 분석, 변경 내역 추적 (intermediate에서 explode 처리)

-- COMMAND ----------

CREATE WIDGET TEXT catalog DEFAULT "sv_nova_dev_an2_catalog";

-- COMMAND ----------

INSERT OVERWRITE analytics.stg_workspace_command_details
WITH latest_commands AS (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__workspace_command`
  WHERE `_is_deleted` = false
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

-- ★ 적재 확인
SELECT
  event_date,
  COUNT(DISTINCT command_id)                            AS commands,
  COUNT(CASE WHEN targets IS NOT NULL THEN 1 END)       AS has_targets,
  COUNT(CASE WHEN changes IS NOT NULL THEN 1 END)       AS has_changes,
  ROUND(AVG(SIZE(targets)), 1)                          AS avg_target_count
FROM analytics.stg_workspace_command_details
WHERE event_date >= CURRENT_DATE() - INTERVAL 7 DAYS
GROUP BY event_date
ORDER BY event_date DESC;
