-- Intermediate: int_command_slots_by_task
-- stg_workspace_commands → task별 투입 자원 집계 (일별 스냅샷 누적)
-- grain: analysis_date × task_id
-- 갱신 전략: INSERT INTO REPLACE WHERE analysis_date (일별 누적)
-- 실행 주기: 일 배치 04:00 UTC (stg_workspace_commands 갱신 완료 후)
-- 후행 소스: mrt__production_volume_weekly.sql

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

-- ★ task별 투입 자원 집계 (어제 기준 누적)
INSERT INTO sv_nova_dev_an2_catalog.analytics.int_command_slots_by_task
REPLACE WHERE analysis_date = CURRENT_DATE() - INTERVAL 1 DAY
SELECT
  CAST(CURRENT_DATE() - INTERVAL 1 DAY AS DATE) AS analysis_date,
  task_id,
  COUNT(DISTINCT CONCAT(user_name, '-', CAST(event_date AS STRING), '-', CAST(event_hour AS STRING)))
                      AS user_hour_slots,
  COUNT(DISTINCT CONCAT(user_name, '-', CAST(event_date AS STRING)))
                      AS person_days,
  CURRENT_TIMESTAMP() AS _loaded_at
FROM sv_nova_dev_an2_catalog.analytics.stg_workspace_commands
WHERE task_id    IS NOT NULL
  AND user_name  IS NOT NULL
  AND event_date IS NOT NULL
  AND event_date <= CURRENT_DATE() - INTERVAL 1 DAY
GROUP BY task_id;

-- COMMAND ----------

-- ★ 테이블/컬럼 설명 업데이트 (기존 테이블 대응)
COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.int_command_slots_by_task
  IS 'task-level active time slots aggregated from stg_workspace_commands. grain: analysis_date x task_id. 갱신: INSERT INTO REPLACE WHERE. 실행: 일 배치 04:00 UTC.';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_command_slots_by_task ALTER COLUMN analysis_date COMMENT 'KST 기준 분석 대상 일자 (스냅샷 기준일)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_command_slots_by_task ALTER COLUMN task_id COMMENT '소속 Task ID';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_command_slots_by_task ALTER COLUMN user_hour_slots COMMENT '투입 시간 슬롯 수 (DISTINCT user_name × event_date × event_hour)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_command_slots_by_task ALTER COLUMN person_days COMMENT '투입 인일 수 (DISTINCT user_name × event_date)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_command_slots_by_task ALTER COLUMN _loaded_at COMMENT '적재 시점';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_command_slots_by_task SET TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ★ 적재 확인
SELECT
  analysis_date,
  COUNT(DISTINCT task_id)        AS total_tasks,
  SUM(user_hour_slots)           AS total_hour_slots,
  SUM(person_days)               AS total_person_days,
  ROUND(AVG(user_hour_slots), 1) AS avg_slots_per_task
FROM sv_nova_dev_an2_catalog.analytics.int_command_slots_by_task
GROUP BY analysis_date
ORDER BY analysis_date DESC
LIMIT 7;