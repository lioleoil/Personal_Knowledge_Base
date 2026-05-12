-- Databricks notebook source
-- Focus Drop — 세션 메트릭 산출 (일 단위 배치, 매일 04:00 UTC)
-- 의존성: focus_drop_gap_thresholds (gap 구간 경계 — 테이블에서 자동 로드)
-- 갱신 전략: INSERT INTO ... REPLACE WHERE analysis_date
-- 시간 기준: analysis_date는 KST 일자 (createdAt UTC → KST 변환 후 비교)

-- COMMAND ----------

CREATE WIDGET TEXT analysis_date            DEFAULT "";
CREATE WIDGET TEXT min_gap_count            DEFAULT "5";
CREATE WIDGET TEXT min_event_count          DEFAULT "10";
CREATE WIDGET TEXT min_session_duration_sec DEFAULT "60";

-- COMMAND ----------

INSERT INTO analytics.focus_drop_session_metrics
REPLACE WHERE analysis_date = '${analysis_date}'
WITH thresholds AS (
  -- gap 구간 경계: 위젯 없이 최신 버전 자동 참조
  SELECT gap_p75, gap_p90, gap_p95
  -- gap_p99 제거: idle 경계는 고정 180s로 대체
  FROM analytics.focus_drop_gap_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_gap_thresholds)
),
latest_assignments AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_assignments`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
latest_tasks AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_tasks`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
latest_commands AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__workspace_command`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
labeler_commands AS (
  SELECT
    c.`_raw`:userId::STRING       AS user_id,
    c.`_raw`:sessionId::STRING    AS session_id,
    c.`_raw`:taskId::STRING       AS task_id,
    c.`_raw`:createdAt::TIMESTAMP AS event_time
  FROM latest_commands c
  INNER JOIN latest_tasks       t ON c.`_raw`:taskId::STRING = t.`_id`
  INNER JOIN latest_assignments a ON t.`_raw`:assignmentId::STRING = a.`_id`
  WHERE LOWER(a.`_raw`:role::STRING) = 'labeler'
    AND CAST(
      CONVERT_TIMEZONE('UTC', 'Asia/Seoul', c.`_raw`:createdAt::TIMESTAMP) AS DATE
    ) = DATE '${analysis_date}'
),
with_diff AS (
  SELECT *,
    UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
      LAG(event_time) OVER (PARTITION BY user_id, session_id, task_id ORDER BY event_time)
    ) AS diff_sec,
    UNIX_TIMESTAMP(event_time) AS event_ts_unix
  FROM labeler_commands
),
gap_classified AS (
  SELECT
    g.user_id, g.session_id, g.task_id, g.diff_sec, g.event_ts_unix,
    CASE
      WHEN g.diff_sec >= 180        THEN 'idle'       -- ★ 고정 임계값 3분
      WHEN g.diff_sec <= t.gap_p75 THEN 'normal'
      WHEN g.diff_sec <= t.gap_p90 THEN 'observation'
      WHEN g.diff_sec <= t.gap_p95 THEN 'light'
      ELSE 'heavy'                                     -- gap_p95 < diff_sec < 180
    END AS gap_severity
  FROM with_diff g
  CROSS JOIN thresholds t
  WHERE g.diff_sec IS NOT NULL AND g.diff_sec > 0
)
SELECT
  DATE '${analysis_date}'                                         AS analysis_date,
  user_id, session_id, task_id,
  COUNT(*)                                                        AS total_gaps,
  SUM(CASE WHEN gap_severity = 'observation' THEN 1 ELSE 0 END)  AS observation_gap_count,
  SUM(CASE WHEN gap_severity = 'light'       THEN 1 ELSE 0 END)  AS light_gap_count,
  SUM(CASE WHEN gap_severity = 'heavy'       THEN 1 ELSE 0 END)  AS heavy_gap_count,
  SUM(CASE WHEN gap_severity = 'idle'        THEN 1 ELSE 0 END)  AS idle_gap_count,
  SUM(CASE WHEN gap_severity = 'idle'        THEN diff_sec ELSE 0 END) AS idle_gap_duration_sec,
  ROUND(SUM(CASE WHEN gap_severity = 'light'     THEN 1 ELSE 0 END) / COUNT(*), 4) AS light_gap_ratio,
  ROUND(SUM(CASE WHEN gap_severity = 'heavy'     THEN 1 ELSE 0 END) / COUNT(*), 4) AS heavy_gap_ratio,
  ROUND(SUM(CASE WHEN gap_severity = 'idle'      THEN 1 ELSE 0 END) / COUNT(*), 4) AS idle_gap_ratio,
  AVG(diff_sec)                                                   AS session_avg_gap
FROM gap_classified
GROUP BY user_id, session_id, task_id
HAVING COUNT(*) >= ${min_gap_count}
   AND COUNT(*) + 1 >= ${min_event_count}
   AND (MAX(event_ts_unix) - MIN(event_ts_unix)) >= ${min_session_duration_sec};

-- COMMAND ----------

-- 결과 확인
SELECT COUNT(*) AS session_count,
       SUM(light_gap_count)              AS total_light_gaps,
       SUM(heavy_gap_count)              AS total_heavy_gaps,
       SUM(idle_gap_count)               AS total_idle_gaps,
       ROUND(SUM(idle_gap_duration_sec) / 3600.0, 2) AS total_idle_hours
FROM analytics.focus_drop_session_metrics
WHERE analysis_date = DATE '${analysis_date}';
