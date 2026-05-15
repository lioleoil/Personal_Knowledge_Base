-- Intermediate: int_focus_drop_task_idle_rollup (Task별 idle 누적, 일 배치)
-- 의존성: int_focus_drop_session_metrics (raw 의존 없음)
-- 갱신 전략: INSERT INTO REPLACE WHERE analysis_date (일별 누적)
-- 실행 주기: 일 배치 04:00 UTC (session_metrics 완료 후)
-- 백필 로직 내장: session_metrics에 idle_gap_count>0인 날짜 중 task_idle_rollup에 없는 날짜 자동 감지
--
-- ★ 백필 로직 내장:
--   정상 배치: statement 2만 실행 (CURRENT_DATE()-1)
--   gap 감지 시: statement 2 → statement 3 순서로 실행 (당일 + 백필)

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

-- ★ 당일 적재 (어제 기준)
INSERT INTO sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup
REPLACE WHERE analysis_date = CURRENT_DATE() - INTERVAL 1 DAY
SELECT
  analysis_date,
  task_id,
  'all_roles'                    AS role_scope,
  'all_roles'                    AS role_group,
  COUNT(DISTINCT session_id)     AS contributing_sessions,
  COUNT(DISTINCT user_id)        AS contributing_users,
  SUM(idle_gap_count)            AS idle_gap_total,
  SUM(idle_gap_duration_sec)     AS idle_gap_duration_sec
FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics
WHERE analysis_date = CURRENT_DATE() - INTERVAL 1 DAY
  AND idle_gap_count > 0
GROUP BY analysis_date, task_id;

-- COMMAND ----------

-- ★ Gap 백필: session_metrics에 있지만 task_idle_rollup에 없는 날짜 자동 복원
-- 정상 배치(gap 없음) 시 0건 INSERT — 안전하게 스킵됨
INSERT INTO sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup
WITH gap_dates AS (
  SELECT DISTINCT analysis_date AS gap_date
  FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics
  WHERE idle_gap_count > 0
    AND analysis_date NOT IN (
      SELECT DISTINCT analysis_date
      FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup
    )
    AND analysis_date < CURRENT_DATE() - INTERVAL 1 DAY
)
SELECT
  m.analysis_date,
  m.task_id,
  'all_roles'                    AS role_scope,
  'all_roles'                    AS role_group,
  COUNT(DISTINCT m.session_id)   AS contributing_sessions,
  COUNT(DISTINCT m.user_id)      AS contributing_users,
  SUM(m.idle_gap_count)          AS idle_gap_total,
  SUM(m.idle_gap_duration_sec)   AS idle_gap_duration_sec
FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics m
WHERE m.analysis_date IN (SELECT gap_date FROM gap_dates)
  AND EXISTS (SELECT 1 FROM gap_dates)
  AND m.idle_gap_count > 0
GROUP BY m.analysis_date, m.task_id;

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- [Labeler/Reviewer Role 세분화] 주석 해제 조건:
--   1. session_metrics에 role_group 컬럼 추가 완료
--   2. Reviewer 커맨드 데이터가 session_metrics에 적재 시작
--
-- 활성화 후 production_volume__weekly.sql의 task_idle CTE에서
--   WHERE role_scope = 'labeler' → WHERE role_scope = 'all_roles' 으로 전환
-- ════════════════════════════════════════════════

-- INSERT INTO sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup
-- REPLACE WHERE analysis_date = CURRENT_DATE() - INTERVAL 1 DAY
-- -- labeler rows
-- SELECT
--   analysis_date, task_id,
--   'labeler'                  AS role_scope,
--   'labeler'                  AS role_group,
--   COUNT(DISTINCT session_id) AS contributing_sessions,
--   COUNT(DISTINCT user_id)    AS contributing_users,
--   SUM(idle_gap_count)        AS idle_gap_total,
--   SUM(idle_gap_duration_sec) AS idle_gap_duration_sec
-- FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics
-- WHERE analysis_date = CURRENT_DATE() - INTERVAL 1 DAY
--   AND idle_gap_count > 0
--   AND role_group = 'labeler'
-- GROUP BY analysis_date, task_id
-- UNION ALL
-- -- all_roles rows (Labeler + Reviewer 합산)
-- SELECT
--   analysis_date, task_id,
--   'all_roles'                AS role_scope,
--   'all_roles'                AS role_group,
--   COUNT(DISTINCT session_id) AS contributing_sessions,
--   COUNT(DISTINCT user_id)    AS contributing_users,
--   SUM(idle_gap_count)        AS idle_gap_total,
--   SUM(idle_gap_duration_sec) AS idle_gap_duration_sec
-- FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics
-- WHERE analysis_date = CURRENT_DATE() - INTERVAL 1 DAY
--   AND idle_gap_count > 0
-- GROUP BY analysis_date, task_id;

-- COMMAND ----------

-- ★ 테이블/컬럼 설명 업데이트
COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup
  IS 'Task별 idle gap 누적 집계. grain: (task_id) x analysis_date. idle_gap_count>0 세션만 대상. role_scope=all_roles. 갱신: INSERT INTO REPLACE WHERE. 실행: 일 배치. gap 백필 내장.';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup ALTER COLUMN analysis_date COMMENT 'KST 기준 분석 대상 일자 — 파티션 키';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup ALTER COLUMN task_id COMMENT '소속 Task ID';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup ALTER COLUMN role_scope COMMENT '집계 범위 (현재: all_roles, 향후: labeler/reviewer)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup ALTER COLUMN role_group COMMENT '역할 그룹 (현재: all_roles)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup ALTER COLUMN contributing_sessions COMMENT 'idle이 1건 이상인 기여 세션 수';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup ALTER COLUMN contributing_users COMMENT '기여 유저 수';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup ALTER COLUMN idle_gap_total COMMENT 'idle gap 총 건수';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup ALTER COLUMN idle_gap_duration_sec COMMENT 'idle gap 총 누적 시간 (초)';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup SET TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ★ 적재 확인 (analysis_date별 추이)
SELECT
  analysis_date,
  COUNT(DISTINCT task_id) AS tasks,
  SUM(idle_gap_total) AS total_idle_gaps,
  ROUND(SUM(idle_gap_duration_sec) / 3600.0, 2) AS idle_hours
FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup
GROUP BY analysis_date
ORDER BY analysis_date DESC
LIMIT 10;