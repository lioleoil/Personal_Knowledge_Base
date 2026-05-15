-- Intermediate: int_focus_drop_session_metrics (세션 메트릭 산출, 일 배치)
-- 의존성: stg_workspace_commands, stg_tasks, int_focus_drop_gap_thresholds (raw 의존 없음)
-- 갱신 전략: INSERT INTO ... REPLACE WHERE analysis_date (일별 누적)
-- 시간 기준: event_date는 이미 KST 변환 완료
-- 실행 주기: 일 배치 04:00 UTC
-- 필터 기준: min_gap_count=5, min_event_count=10, min_session_duration_sec=60
--
-- TODO: dim_role 테이블 생성 후 mart 레이어에서 조인하여 role='labeler' 필터 적용 예정
--       현재는 전체 커맨드 대상으로 산출 (role 필터 미적용)
--
-- ★ 백필 로직 내장:
--   정상 배치: statement 2만 실행 (CURRENT_DATE()-1 스냅샷)
--   gap 감지 시: statement 2 → statement 3 순서로 실행 (당일 + 백필)

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

-- ★ 당일 적재 (어제 기준)
-- ⚠️ role 필터 미적용: dim_role 테이블 생성 후 mart 레이어에서 조인 예정
INSERT INTO sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics
REPLACE WHERE analysis_date = CURRENT_DATE() - INTERVAL 1 DAY
WITH thresholds AS (
  SELECT gap_p75, gap_p90, gap_p95
  FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_gap_thresholds
  WHERE version = (SELECT MAX(version) FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_gap_thresholds)
),
commands AS (
  SELECT
    c.user_id,
    c.session_id,
    c.task_id,
    c.event_time
  FROM sv_nova_dev_an2_catalog.analytics.stg_workspace_commands c
  INNER JOIN sv_nova_dev_an2_catalog.analytics.stg_tasks       t ON c.task_id = t.task_id
  WHERE c.event_date = CURRENT_DATE() - INTERVAL 1 DAY
    -- TODO: dim_role 조인 후 role = 'labeler' 필터 추가
    -- INNER JOIN sv_nova_dev_an2_catalog.analytics.dim_role r
    --   ON t.task_id = r.task_id AND c.user_id = r.user_id
    -- WHERE r.role = 'labeler'
),
with_diff AS (
  SELECT *,
    UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
      LAG(event_time) OVER (PARTITION BY user_id, session_id, task_id ORDER BY event_time)
    ) AS diff_sec,
    UNIX_TIMESTAMP(event_time) AS event_ts_unix
  FROM commands
),
gap_classified AS (
  SELECT
    g.user_id, g.session_id, g.task_id, g.diff_sec, g.event_ts_unix,
    CASE
      WHEN g.diff_sec >= 180       THEN 'idle'
      WHEN g.diff_sec <= t.gap_p75 THEN 'normal'
      WHEN g.diff_sec <= t.gap_p90 THEN 'observation'
      WHEN g.diff_sec <= t.gap_p95 THEN 'light'
      ELSE 'heavy'
    END AS gap_severity
  FROM with_diff g
  CROSS JOIN thresholds t
  WHERE g.diff_sec IS NOT NULL AND g.diff_sec > 0
)
SELECT
  CAST(CURRENT_DATE() - INTERVAL 1 DAY AS DATE)                           AS analysis_date,
  user_id, session_id, task_id,
  COUNT(*)                                                                AS total_gaps,
  SUM(CASE WHEN gap_severity = 'observation' THEN 1 ELSE 0 END)          AS observation_gap_count,
  SUM(CASE WHEN gap_severity = 'light'       THEN 1 ELSE 0 END)          AS light_gap_count,
  SUM(CASE WHEN gap_severity = 'heavy'       THEN 1 ELSE 0 END)          AS heavy_gap_count,
  SUM(CASE WHEN gap_severity = 'idle'        THEN 1 ELSE 0 END)          AS idle_gap_count,
  SUM(CASE WHEN gap_severity = 'idle'        THEN diff_sec ELSE 0 END)   AS idle_gap_duration_sec,
  ROUND(SUM(CASE WHEN gap_severity = 'light' THEN 1 ELSE 0 END) / COUNT(*), 4) AS light_gap_ratio,
  ROUND(SUM(CASE WHEN gap_severity = 'heavy' THEN 1 ELSE 0 END) / COUNT(*), 4) AS heavy_gap_ratio,
  ROUND(SUM(CASE WHEN gap_severity = 'idle'  THEN 1 ELSE 0 END) / COUNT(*), 4) AS idle_gap_ratio,
  AVG(diff_sec)                                                           AS session_avg_gap
FROM gap_classified
GROUP BY user_id, session_id, task_id
HAVING COUNT(*) >= 5
   AND COUNT(*) + 1 >= 10
   AND (MAX(event_ts_unix) - MIN(event_ts_unix)) >= 60;

-- COMMAND ----------

-- ★ Gap 백필: 마지막 analysis_date 이후 누락된 날짜들을 자동 복원
-- CDC 복구 후 stg_workspace_commands에 데이터가 적재되면 이 쿼리로 누락 기간을 자동 채움
-- 정상 배치(gap 없음) 시 0건 INSERT — 안전하게 스킵됨
INSERT INTO sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics
WITH last_date AS (
  SELECT COALESCE(
    (SELECT MAX(analysis_date) FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics
     WHERE analysis_date < CURRENT_DATE() - INTERVAL 1 DAY),
    DATE '2026-04-05'
  ) AS last_analysis_date
),
gap_dates AS (
  SELECT EXPLODE(
    CASE WHEN DATEDIFF(CURRENT_DATE() - INTERVAL 1 DAY, last_analysis_date) > 1
         THEN SEQUENCE(DATE_ADD(last_analysis_date, 1), CURRENT_DATE() - INTERVAL 2 DAY, INTERVAL 1 DAY)
         ELSE ARRAY()
    END
  ) AS gap_date
  FROM last_date
),
thresholds AS (
  SELECT gap_p75, gap_p90, gap_p95
  FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_gap_thresholds
  WHERE version = (SELECT MAX(version) FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_gap_thresholds)
),
commands AS (
  SELECT
    c.user_id,
    c.session_id,
    c.task_id,
    c.event_time,
    c.event_date
  FROM sv_nova_dev_an2_catalog.analytics.stg_workspace_commands c
  INNER JOIN sv_nova_dev_an2_catalog.analytics.stg_tasks       t ON c.task_id = t.task_id
  WHERE c.event_date IN (SELECT gap_date FROM gap_dates)
    AND EXISTS (SELECT 1 FROM gap_dates)
),
with_diff AS (
  SELECT *,
    UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
      LAG(event_time) OVER (PARTITION BY user_id, session_id, task_id ORDER BY event_time)
    ) AS diff_sec,
    UNIX_TIMESTAMP(event_time) AS event_ts_unix
  FROM commands
),
gap_classified AS (
  SELECT
    g.user_id, g.session_id, g.task_id, g.event_date, g.diff_sec, g.event_ts_unix,
    CASE
      WHEN g.diff_sec >= 180       THEN 'idle'
      WHEN g.diff_sec <= t.gap_p75 THEN 'normal'
      WHEN g.diff_sec <= t.gap_p90 THEN 'observation'
      WHEN g.diff_sec <= t.gap_p95 THEN 'light'
      ELSE 'heavy'
    END AS gap_severity
  FROM with_diff g
  CROSS JOIN thresholds t
  WHERE g.diff_sec IS NOT NULL AND g.diff_sec > 0
)
SELECT
  CAST(event_date AS DATE)                                                AS analysis_date,
  user_id, session_id, task_id,
  COUNT(*)                                                                AS total_gaps,
  SUM(CASE WHEN gap_severity = 'observation' THEN 1 ELSE 0 END)          AS observation_gap_count,
  SUM(CASE WHEN gap_severity = 'light'       THEN 1 ELSE 0 END)          AS light_gap_count,
  SUM(CASE WHEN gap_severity = 'heavy'       THEN 1 ELSE 0 END)          AS heavy_gap_count,
  SUM(CASE WHEN gap_severity = 'idle'        THEN 1 ELSE 0 END)          AS idle_gap_count,
  SUM(CASE WHEN gap_severity = 'idle'        THEN diff_sec ELSE 0 END)   AS idle_gap_duration_sec,
  ROUND(SUM(CASE WHEN gap_severity = 'light' THEN 1 ELSE 0 END) / COUNT(*), 4) AS light_gap_ratio,
  ROUND(SUM(CASE WHEN gap_severity = 'heavy' THEN 1 ELSE 0 END) / COUNT(*), 4) AS heavy_gap_ratio,
  ROUND(SUM(CASE WHEN gap_severity = 'idle'  THEN 1 ELSE 0 END) / COUNT(*), 4) AS idle_gap_ratio,
  AVG(diff_sec)                                                           AS session_avg_gap
FROM gap_classified
GROUP BY event_date, user_id, session_id, task_id
HAVING COUNT(*) >= 5
   AND COUNT(*) + 1 >= 10
   AND (MAX(event_ts_unix) - MIN(event_ts_unix)) >= 60;

-- COMMAND ----------

-- ★ 테이블/컬럼 설명 업데이트
COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics
  IS '세션별 gap count/ratio/idle duration 메트릭. grain: (user_id, session_id, task_id) x analysis_date. 갱신: INSERT INTO REPLACE WHERE analysis_date. 실행: 일 배치 04:00 UTC. gap 백필 내장. role 필터 미적용 (dim_role 대기).';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics ALTER COLUMN analysis_date COMMENT 'KST 기준 분석 대상 일자 — 파티션 키';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics ALTER COLUMN user_id COMMENT '작업자 ID';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics ALTER COLUMN session_id COMMENT 'Focus Drop 세션 키';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics ALTER COLUMN task_id COMMENT '소속 Task ID';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics ALTER COLUMN total_gaps COMMENT '전체 gap 수 (diff_sec > 0)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics ALTER COLUMN observation_gap_count COMMENT 'observation 구간 (p75～p90) gap 수';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics ALTER COLUMN light_gap_count COMMENT 'light 구간 (p90～p95) gap 수';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics ALTER COLUMN heavy_gap_count COMMENT 'heavy 구간 (p95～180s) gap 수';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics ALTER COLUMN idle_gap_count COMMENT 'idle 구간 (≥180s) gap 수';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics ALTER COLUMN idle_gap_duration_sec COMMENT 'idle gap 총 누적 시간 (초)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics ALTER COLUMN light_gap_ratio COMMENT 'light gap 비율 (light_count / total_gaps)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics ALTER COLUMN heavy_gap_ratio COMMENT 'heavy gap 비율 (heavy_count / total_gaps)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics ALTER COLUMN idle_gap_ratio COMMENT 'idle gap 비율 (idle_count / total_gaps)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics ALTER COLUMN session_avg_gap COMMENT '세션 평균 gap (초)';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics SET TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ★ 적재 확인 (스냅샷 일별 추이)
SELECT
  analysis_date,
  COUNT(*) AS session_count,
  SUM(light_gap_count)  AS total_light_gaps,
  SUM(heavy_gap_count)  AS total_heavy_gaps,
  SUM(idle_gap_count)   AS total_idle_gaps,
  ROUND(SUM(idle_gap_duration_sec) / 3600.0, 2) AS total_idle_hours
FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics
GROUP BY analysis_date
ORDER BY analysis_date DESC
LIMIT 10;