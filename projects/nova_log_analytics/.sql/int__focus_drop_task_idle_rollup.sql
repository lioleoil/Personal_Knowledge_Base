-- Databricks notebook source
-- Intermediate: focus_drop_task_idle_rollup (Task별 idle gap 누적, 일 배치)
-- 의존성: focus_drop_session_metrics (동일 analysis_date 먼저 실행)
-- 목적: 생산성 연계 — Task 총 idle 시간(초) 누적 (착수→납품 gross 소요시간에서 차감)

-- COMMAND ----------

CREATE WIDGET TEXT analysis_date DEFAULT "";

-- COMMAND ----------

INSERT INTO analytics.focus_drop_task_idle_rollup
REPLACE WHERE analysis_date = '${analysis_date}'
SELECT
  analysis_date,
  task_id,
  'labeler'                  AS role_scope,
  'labeler'                  AS role_group,
  COUNT(*)                   AS contributing_sessions,
  COUNT(DISTINCT user_id)    AS contributing_users,
  SUM(idle_gap_count)        AS idle_gap_total,
  SUM(idle_gap_duration_sec) AS idle_gap_duration_sec
FROM analytics.focus_drop_session_metrics
WHERE analysis_date = '${analysis_date}'
GROUP BY analysis_date, task_id;

-- COMMAND ----------

-- 결과 확인
SELECT COUNT(DISTINCT task_id)         AS distinct_tasks,
       SUM(idle_gap_total)             AS total_idle_gaps,
       ROUND(SUM(idle_gap_duration_sec) / 3600.0, 2) AS total_idle_hours
FROM analytics.focus_drop_task_idle_rollup
WHERE analysis_date = '${analysis_date}';

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- Phase C (주석 해제 조건): session_metrics에 role_group 컬럼 추가 완료
--   + Reviewer 커맨드 데이터 session_metrics에 적재 시작 후 활성화
--
-- 실행 후 production_volume__weekly.sql의 task_idle CTE에서
--   WHERE role_scope = 'labeler' → WHERE role_scope = 'all_roles' 으로 전환
-- ════════════════════════════════════════════════

-- INSERT INTO analytics.focus_drop_task_idle_rollup
-- REPLACE WHERE analysis_date = '${analysis_date}'
-- -- labeler rows
-- SELECT
--   analysis_date, task_id,
--   'labeler'                  AS role_scope,
--   'labeler'                  AS role_group,
--   COUNT(*)                   AS contributing_sessions,
--   COUNT(DISTINCT user_id)    AS contributing_users,
--   SUM(idle_gap_count)        AS idle_gap_total,
--   SUM(idle_gap_duration_sec) AS idle_gap_duration_sec
-- FROM analytics.focus_drop_session_metrics
-- WHERE analysis_date = '${analysis_date}'
--   AND role_group = 'labeler'
-- GROUP BY analysis_date, task_id
-- UNION ALL
-- -- all_roles rows (Labeler + Reviewer 합산)
-- SELECT
--   analysis_date, task_id,
--   'all_roles'                AS role_scope,
--   'all_roles'                AS role_group,
--   COUNT(*)                   AS contributing_sessions,
--   COUNT(DISTINCT user_id)    AS contributing_users,
--   SUM(idle_gap_count)        AS idle_gap_total,
--   SUM(idle_gap_duration_sec) AS idle_gap_duration_sec
-- FROM analytics.focus_drop_session_metrics
-- WHERE analysis_date = '${analysis_date}'
-- GROUP BY analysis_date, task_id;
