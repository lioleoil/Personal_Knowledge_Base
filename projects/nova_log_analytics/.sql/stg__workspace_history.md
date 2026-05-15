-- Staging: stg_workspace_history
-- workspace_history CDC dedup, Undo/Redo 이벤트 추출
-- grain: history_id
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체)
-- 실행 주기: 일 배치 04:00 UTC

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

INSERT OVERWRITE sv_nova_dev_an2_catalog.analytics.stg_workspace_history
WITH latest AS (
  SELECT `_id`, `_raw`, `_occurred_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_occurred_at` DESC) AS rn
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__workspace_history`
)
SELECT
  `_id`                                                                       AS history_id,
  `_raw`:type::STRING                                                         AS event_type,
  `_raw`:dataschema::STRING                                                   AS dataschema,
  TO_TIMESTAMP(`_raw`:time::STRING)                                           AS event_time,
  DATE(CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
    TO_TIMESTAMP(`_raw`:time::STRING)))                                       AS event_date,
  `_raw`:subject::STRING                                                      AS subject,
  `_raw`:sessionid::STRING                                                    AS session_id,
  `_raw`:data.project.task_id::STRING                                         AS task_id,
  `_raw`:data.project.dataset_id::STRING                                      AS dataset_id,
  `_raw`:data.user.id::STRING                                                 AS user_id,
  `_raw`:data.user.name::STRING                                               AS user_name,
  `_raw`:data.feature::STRING                                                 AS feature,
  `_raw`:data.reverted_command_id::STRING                                     AS reverted_command_id,
  `_raw`:data.reverted_command_type::STRING                                   AS reverted_command_type,
  CAST(`_raw`:data.count::STRING AS INT)                                      AS undo_count,
  CURRENT_TIMESTAMP()                                                         AS _loaded_at
FROM latest
WHERE rn = 1
  AND `_raw`:time::STRING IS NOT NULL;

-- COMMAND ----------

COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_history
  IS 'workspace_history Undo/Redo 이벤트 (CDC dedup). grain: history_id. 갱신: INSERT OVERWRITE.';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_history SET TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ★ 적재 확인
SELECT event_type, COUNT(*) AS cnt
FROM sv_nova_dev_an2_catalog.analytics.stg_workspace_history
GROUP BY event_type ORDER BY cnt DESC;