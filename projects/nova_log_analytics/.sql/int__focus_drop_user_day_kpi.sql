-- Intermediate: int_focus_drop_user_day_kpi (유저 일 단위 KPI, 일 배치)
-- 의존성: int_focus_drop_session_tags (raw 의존 없음)
-- 갱신 전략: INSERT INTO REPLACE WHERE analysis_date (일별 누적)
-- 실행 주기: 일 배치 04:00 UTC (session_tags 완료 후)
-- 백필 로직 내장: session_tags에 있지만 user_day_kpi에 없는 날짜 자동 감지
--
-- ★ 백필 로직 내장:
--   정상 배치: statement 2만 실행 (CURRENT_DATE()-1)
--   gap 감지 시: statement 2 → statement 3 순서로 실행 (당일 + 백필)

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

-- ★ 당일 적재 (어제 기준)
INSERT INTO sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi
REPLACE WHERE analysis_date = CURRENT_DATE() - INTERVAL 1 DAY
SELECT
  analysis_date,
  user_id,
  SUM(CASE WHEN is_light_session THEN 1 ELSE 0 END) AS light_session_count,
  SUM(CASE WHEN is_heavy_session THEN 1 ELSE 0 END) AS heavy_session_count,
  SUM(idle_gap_count)                                AS idle_gap_total,
  COUNT(*)                                           AS total_sessions
FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags
WHERE analysis_date = CURRENT_DATE() - INTERVAL 1 DAY
GROUP BY analysis_date, user_id;

-- COMMAND ----------

-- ★ Gap 백필: session_tags에 있지만 user_day_kpi에 없는 날짜 자동 복원
-- 정상 배치(gap 없음) 시 0건 INSERT — 안전하게 스킵됨
INSERT INTO sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi
WITH gap_dates AS (
  SELECT DISTINCT analysis_date AS gap_date
  FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags
  WHERE analysis_date NOT IN (
    SELECT DISTINCT analysis_date
    FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi
  )
  AND analysis_date < CURRENT_DATE() - INTERVAL 1 DAY
)
SELECT
  analysis_date,
  user_id,
  SUM(CASE WHEN is_light_session THEN 1 ELSE 0 END) AS light_session_count,
  SUM(CASE WHEN is_heavy_session THEN 1 ELSE 0 END) AS heavy_session_count,
  SUM(idle_gap_count)                                AS idle_gap_total,
  COUNT(*)                                           AS total_sessions
FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags
WHERE analysis_date IN (SELECT gap_date FROM gap_dates)
  AND EXISTS (SELECT 1 FROM gap_dates)
GROUP BY analysis_date, user_id;

-- COMMAND ----------

-- ★ 테이블/컬럼 설명 업데이트
COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi
  IS '유저 일 단위 Focus Drop KPI 집계. grain: (user_id) x analysis_date. 소스: session_tags → user-day 집계. 갱신: INSERT INTO REPLACE WHERE. 실행: 일 배치. gap 백필 내장.';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi ALTER COLUMN analysis_date COMMENT 'KST 기준 분석 대상 일자 — 파티션 키';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi ALTER COLUMN user_id COMMENT '작업자 ID';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi ALTER COLUMN light_session_count COMMENT 'light 판정 세션 수';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi ALTER COLUMN heavy_session_count COMMENT 'heavy 판정 세션 수';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi ALTER COLUMN idle_gap_total COMMENT '전체 idle gap 누적 (세션 판정 무관)';
ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi ALTER COLUMN total_sessions COMMENT '당일 총 유효 세션 수';

-- COMMAND ----------

ALTER TABLE sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi SET TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ★ 적재 확인 (analysis_date별 추이)
SELECT
  analysis_date,
  COUNT(DISTINCT user_id) AS users,
  ROUND(AVG(total_sessions), 1) AS avg_sessions
FROM sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi
GROUP BY analysis_date
ORDER BY analysis_date DESC
LIMIT 10;