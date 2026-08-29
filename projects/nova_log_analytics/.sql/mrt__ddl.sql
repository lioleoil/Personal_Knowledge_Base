-- Databricks notebook source
-- Marts Layer — 테이블 초기 생성 DDL
-- 실행 조건: Unity Catalog 환경, analytics 스키마 존재
-- 레이어 역할: 도메인별 최종 리포트, 외부 소비 대상
-- 네이밍: mrt_ prefix
--
-- 현행 테이블:
--   mrt_focus_drop_user_day_kpi          — 유저 일 KPI 최종 판정
--   mrt_inspection_quality_monthly_fpy   — 월별 검수 반려율 & FPY
--   mrt_inspection_quality_multi_reject  — 다중 반려 Task 상세
--   mrt_production_volume_weekly         — 주별 납품 생산량 & 생산성

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS sv_nova_dev_an2_catalog.analytics;

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 1. mrt_focus_drop_user_day_kpi
--    일 배치 — 유저 일 KPI 및 최종 판정
--    소스: int_focus_drop_user_day_kpi + int_focus_drop_user_thresholds
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.mrt_focus_drop_user_day_kpi (
  analysis_date         DATE      COMMENT '분석 대상일 (KST)',
  user_id               STRING    COMMENT '유저 ID (workspace_command.userId)',
  light_session_count   INT       COMMENT 'light 판정 세션 수',
  heavy_session_count   INT       COMMENT 'heavy 판정 세션 수',
  idle_gap_total        INT       COMMENT 'idle gap 총 횟수',
  total_sessions        INT       COMMENT '해당일 전체 세션 수',
  is_light_user         BOOLEAN   COMMENT 'light 유저 여부 (p90 초과)',
  is_heavy_user         BOOLEAN   COMMENT 'heavy 유저 여부 (p95 초과)',
  is_idle_user          BOOLEAN   COMMENT 'idle 유저 여부 (p99 초과)',
  user_focus_drop_level STRING    COMMENT '최종 판정 (idle > heavy > light > normal)'
)
USING DELTA
PARTITIONED BY (analysis_date)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.mrt_focus_drop_user_day_kpi
  IS 'Daily user-level Focus Drop KPI with final classification. grain: (user_id) x analysis_date. 소스: int_focus_drop_user_day_kpi + user_thresholds.';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.mrt_focus_drop_user_day_kpi
  ADD CONSTRAINT mrt_fdkpi_analysis_date_not_null CHECK (analysis_date IS NOT NULL);

ALTER TABLE sv_nova_dev_an2_catalog.analytics.mrt_focus_drop_user_day_kpi
  ADD CONSTRAINT mrt_fdkpi_user_id_not_null       CHECK (user_id       IS NOT NULL);


-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 2. mrt_inspection_quality_monthly_fpy
--    월 1회 — 월별 검수 반려율 & First Pass Yield
--    소스: stg_task_transition_events + raw gen2_tasks
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_monthly_fpy (
  deliver_month        STRING    COMMENT '납품 월 (yy-MM 형식, KST)',
  total_inspected      BIGINT    COMMENT '검수 완료 Task 수',
  rejected_count       BIGINT    COMMENT '반려 경험 Task 수 (≥ 1회)',
  rejection_rate_pct   DOUBLE    COMMENT '반려율 (%) = rejected / inspected * 100',
  first_pass_yield_pct DOUBLE    COMMENT 'FPY (%) = 100 - rejection_rate_pct',
  distinct_reasons     ARRAY<STRING> COMMENT '해당 월 반려 사유 목록 (DISTINCT)'
)
USING DELTA
PARTITIONED BY (deliver_month)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_monthly_fpy
  IS 'Monthly inspection rejection rate and First Pass Yield (FPY). grain: deliver_month. 소스: stg_task_transition_events + raw gen2_tasks.';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_monthly_fpy
  ADD CONSTRAINT mrt_fpy_deliver_month_not_null CHECK (deliver_month IS NOT NULL);


-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 3. mrt_inspection_quality_multi_reject
--    월 1회 — 다중 반려 Task 상세 (reject ≥ 2)
--    소스: stg_task_transition_events + raw gen2_tasks
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_multi_reject (
  task_id        STRING    COMMENT 'gen2_tasks._id (PK)',
  task_name      STRING    COMMENT 'Task 이름 (gen2_tasks.name)',
  assignment_id  STRING    COMMENT '어사인먼트 ID (dim_assignments FK)',
  deliver_month  STRING    COMMENT '납품 월 (yy-MM 형식, KST)',
  reject_count   BIGINT    COMMENT '반려 횟수 (≥ 2)',
  reject_details ARRAY<STRUCT<
    rejected_at:   STRING COMMENT '반려 시각',
    rejected_by:   STRING COMMENT '반려자',
    reject_reason: STRING COMMENT '반려 사유'
  >>                       COMMENT '반려 이력 상세 배열'
)
USING DELTA
PARTITIONED BY (deliver_month)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_multi_reject
  IS 'Monthly task-level detail for inspection reject >= 2. grain: task_id x deliver_month. 소스: stg_task_transition_events + raw gen2_tasks.';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_multi_reject
  ADD CONSTRAINT mrt_mr_task_id_not_null       CHECK (task_id       IS NOT NULL);

ALTER TABLE sv_nova_dev_an2_catalog.analytics.mrt_inspection_quality_multi_reject
  ADD CONSTRAINT mrt_mr_deliver_month_not_null CHECK (deliver_month IS NOT NULL);


-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 4. mrt_production_volume_weekly
--    주 1회 — 납품 Task 수 · 객체 수 · 생산성 지표
--    소스: stg_task_transition_events + int_object_counts + int_command_slots + dim
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sv_nova_dev_an2_catalog.analytics.mrt_production_volume_weekly (
  deliver_week_start          DATE      COMMENT '납품 기준 주 월요일 (KST) — 파티션 키',
  company_name                STRING    COMMENT '업체명 (dim_companies.company_name)',
  feature                     STRING    COMMENT 'Feature (MV2_LD / MV2_OD / MV2_SOD / MV2_RMD / MV2_TSTLD)',
  delivered_task_count        BIGINT    COMMENT '주당 납품 Task 수',
  ld_lines                    BIGINT    COMMENT 'LD: gen2_lines 객체 수',
  ld_line_points              BIGINT    COMMENT 'LD: gen2_line_points 포인트 수',
  ld_road_boundaries          BIGINT    COMMENT 'LD: gen2_road_boundaries 객체 수',
  ld_road_boundary_points     BIGINT    COMMENT 'LD: gen2_road_boundary_points 포인트 수',
  ld_lanes                    BIGINT    COMMENT 'LD: gen2_lanes 객체 수',
  ld_topologies               BIGINT    COMMENT 'LD: gen2_topologies 객체 수',
  rmd_polywall_objects        BIGINT    COMMENT 'RMD: gen2_polywall_roadmark_objects 객체 수',
  rmd_bbox3d_objects          BIGINT    COMMENT 'RMD: gen2_box_roadmark_objects 객체 수',
  dynamic_targets             BIGINT    COMMENT 'OD: gen2_dynamic_targets 객체 수',
  static_targets              BIGINT    COMMENT 'OD/SOD/TSTLD: gen2_static_targets 객체 수',
  delivered_object_count      BIGINT    COMMENT 'primary objects 합산 (feature별 산식 상이)',
  delivered_point_count       BIGINT    COMMENT 'LD points 합산 (타 feature NULL)',
  avg_points_per_object       DOUBLE    COMMENT 'LD 복잡도 proxy (points / objects)',
  user_hour_slots             BIGINT    COMMENT '투입 인시 (DISTINCT user × hour)',
  person_days                 BIGINT    COMMENT '투입 인일 (DISTINCT user × date)',
  objects_per_hour            DOUBLE    COMMENT '시간당 납품 객체 수',
  tasks_per_person_day        DOUBLE    COMMENT '인일당 납품 Task 수',
  objects_per_person_day      DOUBLE    COMMENT '인일당 납품 객체 수',
  avg_hours_per_task          DOUBLE    COMMENT 'Task 평균 소요시간 (gross, hours)',
  median_hours_per_task       DOUBLE    COMMENT 'Task 소요시간 중앙값 (gross)',
  avg_net_hours_per_task      DOUBLE    COMMENT 'Task 평균 순소요시간 (idle 차감)',
  median_net_hours_per_task   DOUBLE    COMMENT 'Task 순소요시간 중앙값 (idle 차감)'
)
USING DELTA
PARTITIONED BY (deliver_week_start)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE sv_nova_dev_an2_catalog.analytics.mrt_production_volume_weekly
  IS 'Weekly production volume and productivity metrics. grain: (deliver_week_start, company_name, feature). 소스: stg_task_transition_events + int_object_counts + int_command_slots + dims.';

ALTER TABLE sv_nova_dev_an2_catalog.analytics.mrt_production_volume_weekly
  ADD CONSTRAINT mrt_pvw_deliver_week_not_null CHECK (deliver_week_start IS NOT NULL);


-- COMMAND ----------

-- ★ 생성 확인
SELECT table_name, comment
FROM information_schema.tables
WHERE table_schema = 'analytics'
  AND table_name LIKE 'mrt_%'
ORDER BY table_name;