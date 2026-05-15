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

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.stg_workspace_commands (
  command_id   STRING    COMMENT 'CloudEvents root id — 커맨드 고유 식별자',
  event_type   STRING    COMMENT 'CloudEvents type (e.g. annotation.object.delete)',
  dataschema   STRING    COMMENT 'CloudEvents dataschema 버전 (1.0.0 / 1.1.0)',
  event_time   TIMESTAMP COMMENT 'CloudEvents time — 이벤트 발생 시각 (UTC)',
  event_date   DATE      COMMENT 'event_time KST 변환 후 DATE',
  event_hour   INT       COMMENT 'event_time KST 변환 후 HOUR (0~23)',
  subject      STRING    COMMENT 'CloudEvents subject — 이벤트 대상 엔티티 ID',
  session_id   STRING    COMMENT 'Focus Drop 세션 키 (sessionid)',
  task_id      STRING    COMMENT 'data.project.task_id — 소속 Task ID',
  dataset_id   STRING    COMMENT 'data.project.dataset_id — 소속 Dataset ID',
  user_id      STRING    COMMENT 'data.user.id — 작업자 ID',
  user_name    STRING    COMMENT 'data.user.name — 작업자 이름',
  feature      STRING    COMMENT 'data.feature — 도메인 (ld / od / rmd)',
  action       STRING    COMMENT 'data.action — 행위 유형 (create / delete / update / transform)',
  input_type   STRING    COMMENT 'data.input_type — 입력 장치 (mouse / keyboard)',
  input_view   STRING    COMMENT 'data.input_view — 뷰포트 (rear / front 등, 1.1.0+ nullable)',
  _loaded_at   TIMESTAMP COMMENT '데이터 적재 시각 (CURRENT_TIMESTAMP at INSERT)'
)
COMMENT 'workspace_command CloudEvents 필드 추출 (CDC dedup). 소스: raw.raw_labelit__workspace_command. 갱신: INSERT OVERWRITE (일 전체 교체). 실행 주기: 일 배치 04:00 UTC.'
TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

INSERT OVERWRITE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands
WITH latest_commands AS (
  SELECT `_id`, `_raw`, `_occurred_at`,
         ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_occurred_at` DESC) AS rn
  FROM sv_nova_dev_an2_catalog.`raw`.`raw_labelit__workspace_command`
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

-- ★ 테이블/컬럼 설명 업데이트 (기존 테이블 대응)
COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands IS 'workspace_command CloudEvents 필드 추출 (CDC dedup). 소스: raw.raw_labelit__workspace_command. 갱신: INSERT OVERWRITE (일 전체 교체). 실행 주기: 일 배치 04:00 UTC.';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN command_id COMMENT 'CloudEvents root id — 커맨드 고유 식별자';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN event_type COMMENT 'CloudEvents type (e.g. annotation.object.delete)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN dataschema COMMENT 'CloudEvents dataschema 버전 (1.0.0 / 1.1.0)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN event_time COMMENT 'CloudEvents time — 이벤트 발생 시각 (UTC)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN event_date COMMENT 'event_time KST 변환 후 DATE';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN event_hour COMMENT 'event_time KST 변환 후 HOUR (0~23)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN subject COMMENT 'CloudEvents subject — 이벤트 대상 엔티티 ID';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN session_id COMMENT 'Focus Drop 세션 키 (sessionid)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN task_id COMMENT 'data.project.task_id — 소속 Task ID';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN dataset_id COMMENT 'data.project.dataset_id — 소속 Dataset ID';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN user_id COMMENT 'data.user.id — 작업자 ID';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN user_name COMMENT 'data.user.name — 작업자 이름';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN feature COMMENT 'data.feature — 도메인 (ld / od / rmd)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN action COMMENT 'data.action — 행위 유형 (create / delete / update / transform)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN input_type COMMENT 'data.input_type — 입력 장치 (mouse / keyboard)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN input_view COMMENT 'data.input_view — 뷰포트 (rear / front 등, 1.1.0+ nullable)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands ALTER COLUMN _loaded_at COMMENT '데이터 적재 시각 (CURRENT_TIMESTAMP at INSERT)';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.stg_workspace_commands SET TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ★ 적재 확인
SELECT
  event_date,
  COUNT(DISTINCT command_id)              AS commands,
  COUNT(DISTINCT task_id)                 AS tasks,
  COUNT(DISTINCT user_name)               AS users,
  MIN(event_time)                         AS earliest,
  MAX(event_time)                         AS latest
FROM sv_nova_dev_an2_catalog.analytics.stg_workspace_commands
WHERE event_date >= CURRENT_DATE() - INTERVAL 7 DAYS
GROUP BY event_date
ORDER BY event_date DESC;