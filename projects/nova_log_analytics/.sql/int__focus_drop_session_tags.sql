-- Intermediate: int_focus_drop_session_tags (세션 판정 결과, 일 배치)
-- 의존성: int_focus_drop_session_metrics, int_focus_drop_session_thresholds (raw 의존 없음)
-- 갱신 전략: INSERT INTO ... REPLACE WHERE analysis_date (일별 누적)
-- 실행 주기: 일 배치 04:00 UTC (session_metrics 완료 후)
-- 판정 기준: count 중심, 배타적 레벨 (idle > heavy > light > normal)
-- safe fail: session_thresholds 미적재 시 CROSS JOIN → 0행
--
-- ★ 백필 로직 내장:
--   정상 배치: statement 2만 실행 (CURRENT_DATE()-1)
--   gap 감지 시: statement 2 → statement 3 순서로 실행 (당일 + 백필)

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

-- ★ 당일 적재 (어제 기준)
INSERT INTO sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags
REPLACE WHERE analysis_date = CURRENT_DATE() - INTERVAL 1 DAY
WITH thresholds AS (
  SELECT session_light_count_p90, session_heavy_count_p95, session_idle_count_p99
  FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_thresholds
  WHERE version = (SELECT MAX(version) FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_thresholds)
)
SELECT
  m.analysis_date,
  m.user_id, m.session_id, m.task_id,
  m.light_gap_count, m.heavy_gap_count, m.idle_gap_count,
  CASE WHEN m.light_gap_count > 0 AND m.light_gap_count > t.session_light_count_p90 THEN TRUE ELSE FALSE END AS is_light_session,
  CASE WHEN m.heavy_gap_count > 0 AND m.heavy_gap_count > t.session_heavy_count_p95 THEN TRUE ELSE FALSE END AS is_heavy_session,
  CASE WHEN m.idle_gap_count > 0  AND m.idle_gap_count  > t.session_idle_count_p99  THEN TRUE ELSE FALSE END AS is_idle_session,
  CASE
    WHEN m.idle_gap_count > 0  AND m.idle_gap_count  > t.session_idle_count_p99  THEN 'idle'
    WHEN m.heavy_gap_count > 0 AND m.heavy_gap_count > t.session_heavy_count_p95 THEN 'heavy'
    WHEN m.light_gap_count > 0 AND m.light_gap_count > t.session_light_count_p90 THEN 'light'
    ELSE 'normal'
  END AS focus_drop_level
FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics m
CROSS JOIN thresholds t
WHERE m.analysis_date = CURRENT_DATE() - INTERVAL 1 DAY;

-- COMMAND ----------

-- ★ Gap 백필: session_metrics에 있지만 session_tags에 없는 날짜 자동 복원
-- 정상 배치(gap 없음) 시 0건 INSERT — 안전하게 스킵됨
INSERT INTO sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags
WITH gap_dates AS (
  SELECT DISTINCT analysis_date AS gap_date
  FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics
  WHERE analysis_date NOT IN (
    SELECT DISTINCT analysis_date
    FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags
  )
  AND analysis_date < CURRENT_DATE() - INTERVAL 1 DAY
),
thresholds AS (
  SELECT session_light_count_p90, session_heavy_count_p95, session_idle_count_p99
  FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_thresholds
  WHERE version = (SELECT MAX(version) FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_thresholds)
)
SELECT
  m.analysis_date,
  m.user_id, m.session_id, m.task_id,
  m.light_gap_count, m.heavy_gap_count, m.idle_gap_count,
  CASE WHEN m.light_gap_count > 0 AND m.light_gap_count > t.session_light_count_p90 THEN TRUE ELSE FALSE END AS is_light_session,
  CASE WHEN m.heavy_gap_count > 0 AND m.heavy_gap_count > t.session_heavy_count_p95 THEN TRUE ELSE FALSE END AS is_heavy_session,
  CASE WHEN m.idle_gap_count > 0  AND m.idle_gap_count  > t.session_idle_count_p99  THEN TRUE ELSE FALSE END AS is_idle_session,
  CASE
    WHEN m.idle_gap_count > 0  AND m.idle_gap_count  > t.session_idle_count_p99  THEN 'idle'
    WHEN m.heavy_gap_count > 0 AND m.heavy_gap_count > t.session_heavy_count_p95 THEN 'heavy'
    WHEN m.light_gap_count > 0 AND m.light_gap_count > t.session_light_count_p90 THEN 'light'
    ELSE 'normal'
  END AS focus_drop_level
FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics m
CROSS JOIN thresholds t
WHERE m.analysis_date IN (SELECT gap_date FROM gap_dates)
  AND EXISTS (SELECT 1 FROM gap_dates);

-- COMMAND ----------

-- ★ 테이블/컬럼 설명 업데이트
COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags
  IS '세션 Focus Drop 판정 결과. grain: (user_id, session_id, task_id) x analysis_date. 판정: count 중심, 배타적 (idle>heavy>light>normal). 갱신: INSERT INTO REPLACE WHERE. 실행: 일 배치. gap 백필 내장.';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags ALTER COLUMN analysis_date COMMENT 'KST 기준 분석 대상 일자 — 파티션 키';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags ALTER COLUMN user_id COMMENT '작업자 ID';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags ALTER COLUMN session_id COMMENT 'Focus Drop 세션 키';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags ALTER COLUMN task_id COMMENT '소속 Task ID';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags ALTER COLUMN light_gap_count COMMENT 'light 구간 (p90～p95) gap 수';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags ALTER COLUMN heavy_gap_count COMMENT 'heavy 구간 (p95～180s) gap 수';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags ALTER COLUMN idle_gap_count COMMENT 'idle 구간 (≥180s) gap 수';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags ALTER COLUMN is_light_session COMMENT 'light 판정 여부 (count > session_light_count_p90)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags ALTER COLUMN is_heavy_session COMMENT 'heavy 판정 여부 (count > session_heavy_count_p95)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags ALTER COLUMN is_idle_session COMMENT 'idle 판정 여부 (count > session_idle_count_p99)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags ALTER COLUMN focus_drop_level COMMENT '배타적 최종 레벨 (idle / heavy / light / normal)';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags SET TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ★ 적재 확인 (analysis_date별 focus_drop_level 분포)
SELECT analysis_date, focus_drop_level, COUNT(*) AS sessions
FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags
GROUP BY analysis_date, focus_drop_level
ORDER BY analysis_date DESC, focus_drop_level
LIMIT 30;