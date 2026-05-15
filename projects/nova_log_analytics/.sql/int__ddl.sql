-- Intermediate Layer — 테이블 초기 생성 DDL
-- 실행 조건: Unity Catalog 환경, analytics 스키마 존재
-- 현행 테이블: int_command_slots_by_task / int_object_counts_by_task / int_focus_drop_* (7종)

-- COMMAND ----------

-- ════ 1. int_command_slots_by_task ════
-- task별 투입 자원 집계 (stg_workspace_commands 기반)
CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.int_command_slots_by_task (
  task_id          STRING    COMMENT '소속 Task ID',
  event_date       DATE      COMMENT '활동 일자 — 파티션 키',
  user_hour_slots  BIGINT    COMMENT '투입 시간 슬롯 수 (DISTINCT user_name × event_hour)',
  person_days      BIGINT    COMMENT '투입 인원 수 (DISTINCT user_name)',
  _loaded_at       TIMESTAMP COMMENT '적재 시점'
)
USING DELTA
PARTITIONED BY (event_date)
TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ════ 2. int_object_counts_by_task ════
-- task별 객체 수 집계 (stg_objects 기반)
CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.int_object_counts_by_task (
  task_id        STRING    COMMENT '소속 Task ID',
  table_name     STRING    COMMENT '소스 객체 테이블명 (e.g. gen2_lines)',
  stage_key      STRING    COMMENT '작업 Stage 키 (labeling / inspection / ...)',
  object_count   BIGINT    COMMENT '해당 (task, table, stage) 조합의 객체 수',
  snapshot_date  DATE      COMMENT '스냅샷 기준일 — 파티션 키',
  _loaded_at     TIMESTAMP COMMENT '적재 시점'
)
USING DELTA
PARTITIONED BY (snapshot_date)
TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ════ 3. int_focus_drop_gap_thresholds ════
-- gap percentile 기준선 (분기 1회, 90일 rolling)
CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.int_focus_drop_gap_thresholds (
  version        INT       COMMENT '기준선 버전 (auto-increment)',
  computed_at    TIMESTAMP COMMENT '산출 시각',
  feature_scope  STRING    COMMENT '대상 Feature 범위 (all_features / ld / od / rmd)',
  sample_count   BIGINT    COMMENT 'Percentile 산출에 사용된 gap 표본 수',
  gap_p50        DOUBLE    COMMENT 'gap 중앙값 (50th percentile, 초)',
  gap_p75        DOUBLE    COMMENT 'normal/observation 경계 (75th percentile, 초)',
  gap_p90        DOUBLE    COMMENT 'observation/light 경계 (90th percentile, 초)',
  gap_p95        DOUBLE    COMMENT 'light/heavy 경계 (95th percentile, 초)',
  gap_p99        DOUBLE    COMMENT '진단 참고용 (99th percentile, 초) — 분류 경계 아님'
) TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ════ 4. int_focus_drop_session_thresholds ════
-- 세션 판정 기준선 (주 1회, 30일 rolling)
CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_thresholds (
  version                   INT       COMMENT '기준선 버전 (auto-increment)',
  computed_at               TIMESTAMP COMMENT '산출 시각',
  is_bootstrap              BOOLEAN   COMMENT '초기 부트스트랩 여부 (데이터 부족 시 true)',
  window_start              DATE      COMMENT 'Rolling window 시작일',
  window_end                DATE      COMMENT 'Rolling window 종료일',
  session_light_count_p90   DOUBLE    COMMENT 'light gap count 90th percentile (세션 판정 경계)',
  session_heavy_count_p95   DOUBLE    COMMENT 'heavy gap count 95th percentile (세션 판정 경계)',
  session_idle_count_p99    DOUBLE    COMMENT 'idle gap count 99th percentile (세션 판정 경계)',
  session_light_ratio_p90   DOUBLE    COMMENT 'light gap ratio 90th percentile (보조 판정용)',
  session_heavy_ratio_p95   DOUBLE    COMMENT 'heavy gap ratio 95th percentile (보조 판정용)',
  session_idle_ratio_p99    DOUBLE    COMMENT 'idle gap ratio 99th percentile (보조 판정용)'
) TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ════ 5. int_focus_drop_user_thresholds ════
-- 유저 판정 기준선 (주 1회, 30일 rolling)
CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_thresholds (
  version                        INT       COMMENT '기준선 버전 (auto-increment)',
  computed_at                    TIMESTAMP COMMENT '산출 시각',
  is_bootstrap                   BOOLEAN   COMMENT '초기 부트스트랩 여부 (데이터 부족 시 true)',
  window_start                   DATE      COMMENT 'Rolling window 시작일',
  window_end                     DATE      COMMENT 'Rolling window 종료일',
  user_light_session_count_p90   DOUBLE    COMMENT 'light session count 90th percentile (유저 판정 경계)',
  user_heavy_session_count_p95   DOUBLE    COMMENT 'heavy session count 95th percentile (유저 판정 경계)',
  user_idle_gap_total_p99        DOUBLE    COMMENT 'idle gap total 99th percentile (유저 판정 경계)'
) TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ════ 6. int_focus_drop_session_metrics ════
-- 세션별 gap count/ratio/idle duration 메트릭 (일 배치)
CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_metrics (
  analysis_date        DATE      COMMENT 'KST 기준 분석 대상 일자 — 파티션 키',
  user_id              STRING    COMMENT '작업자 ID',
  session_id           STRING    COMMENT 'Focus Drop 세션 키',
  task_id              STRING    COMMENT '소속 Task ID',
  total_gaps           INT       COMMENT '전체 gap 수 (diff_sec > 0)',
  observation_gap_count INT      COMMENT 'observation 구간 (p75～p90) gap 수',
  light_gap_count      INT       COMMENT 'light 구간 (p90～p95) gap 수',
  heavy_gap_count      INT       COMMENT 'heavy 구간 (p95～180s) gap 수',
  idle_gap_count       INT       COMMENT 'idle 구간 (≥180s) gap 수',
  idle_gap_duration_sec DOUBLE   COMMENT 'idle gap 총 누적 시간 (초)',
  light_gap_ratio      DOUBLE    COMMENT 'light gap 비율 (light_count / total_gaps)',
  heavy_gap_ratio      DOUBLE    COMMENT 'heavy gap 비율 (heavy_count / total_gaps)',
  idle_gap_ratio       DOUBLE    COMMENT 'idle gap 비율 (idle_count / total_gaps)',
  session_avg_gap      DOUBLE    COMMENT '세션 평균 gap (초)'
)
USING DELTA
PARTITIONED BY (analysis_date)
TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ════ 7. int_focus_drop_session_tags ════
-- 세션 Focus Drop 판정 결과 (일 배치)
CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.int_focus_drop_session_tags (
  analysis_date      DATE      COMMENT 'KST 기준 분석 대상 일자 — 파티션 키',
  user_id            STRING    COMMENT '작업자 ID',
  session_id         STRING    COMMENT 'Focus Drop 세션 키',
  task_id            STRING    COMMENT '소속 Task ID',
  light_gap_count    INT       COMMENT 'light 구간 (p90～p95) gap 수',
  heavy_gap_count    INT       COMMENT 'heavy 구간 (p95～180s) gap 수',
  idle_gap_count     INT       COMMENT 'idle 구간 (≥180s) gap 수',
  is_light_session   BOOLEAN   COMMENT 'light 판정 여부 (count > session_light_count_p90)',
  is_heavy_session   BOOLEAN   COMMENT 'heavy 판정 여부 (count > session_heavy_count_p95)',
  is_idle_session    BOOLEAN   COMMENT 'idle 판정 여부 (count > session_idle_count_p99)',
  focus_drop_level   STRING    COMMENT '배타적 최종 레벨 (idle / heavy / light / normal)'
)
USING DELTA
PARTITIONED BY (analysis_date)
TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ════ 8. int_focus_drop_user_day_kpi ════
-- 유저 일 단위 Focus Drop KPI 집계 (일 배치)
CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.int_focus_drop_user_day_kpi (
  analysis_date        DATE      COMMENT 'KST 기준 분석 대상 일자 — 파티션 키',
  user_id              STRING    COMMENT '작업자 ID',
  light_session_count  BIGINT    COMMENT 'light 판정 세션 수',
  heavy_session_count  BIGINT    COMMENT 'heavy 판정 세션 수',
  idle_gap_total       BIGINT    COMMENT '전체 idle gap 누적 (세션 판정 무관)',
  total_sessions       BIGINT    COMMENT '당일 총 유효 세션 수'
)
USING DELTA
PARTITIONED BY (analysis_date)
TBLPROPERTIES ('quality' = 'silver');

-- COMMAND ----------

-- ════ 9. int_focus_drop_task_idle_rollup ════
-- Task별 idle gap 누적 집계 (일 배치)
CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.int_focus_drop_task_idle_rollup (
  analysis_date          DATE      COMMENT 'KST 기준 분석 대상 일자 — 파티션 키',
  task_id                STRING    COMMENT '소속 Task ID',
  role_scope             STRING    COMMENT '집계 범위 (현재: all_roles, 향후: labeler/reviewer)',
  role_group             STRING    COMMENT '역할 그룹 (현재: all_roles)',
  contributing_sessions  INT       COMMENT 'idle이 1건 이상인 기여 세션 수',
  contributing_users     INT       COMMENT '기여 유저 수',
  idle_gap_total         INT       COMMENT 'idle gap 총 건수',
  idle_gap_duration_sec  DOUBLE    COMMENT 'idle gap 총 누적 시간 (초)'
)
USING DELTA
PARTITIONED BY (analysis_date)
TBLPROPERTIES ('quality' = 'silver');