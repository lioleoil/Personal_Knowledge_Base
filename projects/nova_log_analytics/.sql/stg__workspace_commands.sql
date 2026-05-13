-- Databricks notebook source
-- Staging: stg_workspace_commands
-- workspace_command CDC dedup, CloudEvents 1.0 필드 추출 (row-level, 집계 없음)
-- 갱신 전략: INSERT OVERWRITE (일 전체 교체)
-- 실행 주기: 일 배치 04:00 UTC
-- 후행 소스: int_command_slots_by_task (task별 투입 자원 집계)
--
-- CloudEvents 1.0/1.1 필드 구조 (old/new 중첩 객체 제외, 전 필드 컬럼화):
--   root: id                  → command_id
--   root: type                → event_type   (e.g. annotation.object.delete)
--   root: dataschema          → dataschema   (1.0.0 / 1.1.0 ...)
--   root: time                → event_time   + event_date / event_hour (KST 파생)
--   root: subject             → subject      (이벤트 대상 엔티티 ID)
--   root: sessionid           → session_id   (Focus Drop 세션 키)
--   data: project.task_id     → task_id
--   data: project.dataset_id  → dataset_id
--   data: user.id             → user_id
--   data: user.name           → user_name
--   data: feature             → feature      (ld / od / rmd)
--   data: action              → action       (create / delete / update / transform ...)
--   data: input_type          → input_type   (mouse / keyboard)
--   data: input_view          → input_view   (rear / front / ... ; 1.1.0+ nullable)
--   data: targets / changes / params → stg_workspace_command_details (별도 상세 테이블)

-- COMMAND ----------

CREATE WIDGET TEXT catalog DEFAULT "sv_nova_dev_an2_catalog";

-- COMMAND ----------

INSERT OVERWRITE analytics.stg_workspace_commands
WITH latest_commands AS (
  SELECT `_id`, `_raw`, `_ingested_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
  FROM ${catalog}.`raw`.`raw_labelit__workspace_command`
  WHERE `_is_deleted` = false
)
SELECT
  -- ── CloudEvents root ────────────────────────────────────────────
  `_id`                                                                       AS command_id,
  `_raw`:type::STRING                                                         AS event_type,
  `_raw`:dataschema::STRING                                                   AS dataschema,
  TO_TIMESTAMP(`_raw`:time::STRING)                                           AS event_time,
  DATE(CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
    TO_TIMESTAMP(`_raw`:time::STRING)))                                       AS event_date,
  HOUR(CONVERT_TIMEZONE('UTC', 'Asia/Seoul',
    TO_TIMESTAMP(`_raw`:time::STRING)))                                       AS event_hour,
  `_raw`:subject::STRING                                                      AS subject,
  `_raw`:sessionid::STRING                                                    AS session_id,
  -- ── data.project ────────────────────────────────────────────────
  `_raw`:data.project.task_id::STRING                                         AS task_id,
  `_raw`:data.project.dataset_id::STRING                                      AS dataset_id,
  -- ── data.user ───────────────────────────────────────────────────
  `_raw`:data.user.id::STRING                                                 AS user_id,
  `_raw`:data.user.name::STRING                                               AS user_name,
  -- ── data.action context ─────────────────────────────────────────
  `_raw`:data.feature::STRING                                                 AS feature,
  `_raw`:data.action::STRING                                                  AS action,
  `_raw`:data.input_type::STRING                                              AS input_type,
  `_raw`:data.input_view::STRING                                              AS input_view,
  -- ── metadata ────────────────────────────────────────────────────
  CURRENT_TIMESTAMP()                                                         AS _loaded_at
FROM latest_commands
WHERE rn = 1
  AND `_raw`:time::STRING                    IS NOT NULL
  AND `_raw`:data.project.task_id::STRING    IS NOT NULL
  AND `_raw`:data.user.name::STRING          IS NOT NULL;

-- COMMAND ----------

-- ★ 적재 확인
SELECT
  event_date,
  COUNT(DISTINCT command_id)              AS commands,
  COUNT(DISTINCT task_id)                 AS tasks,
  COUNT(DISTINCT user_name)               AS users,
  MIN(event_time)                         AS earliest,
  MAX(event_time)                         AS latest
FROM analytics.stg_workspace_commands
WHERE event_date >= CURRENT_DATE() - INTERVAL 7 DAYS
GROUP BY event_date
ORDER BY event_date DESC;
