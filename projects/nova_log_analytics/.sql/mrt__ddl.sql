-- Databricks notebook source
-- Marts Layer — 테이블 초기 생성 DDL
-- 실행 조건: Unity Catalog 환경, analytics 스키마 존재
-- 레이어 역할: 도메인별 최종 리포트, 외부 소비 대상
--
-- 현행 테이블:
--   focus_drop_user_day_kpi          — 유저 일 KPI 최종 판정
--   inspection_quality_monthly_fpy   — 월별 검수 반려율 & FPY
--   inspection_quality_multi_reject  — 다중 반려 Task 상세
--   production_volume_weekly         — 주별 납품 생산량 & 생산성

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 1. focus_drop_user_day_kpi
--    일 배치 — 유저 일 KPI 및 최종 판정
--    소스: mrt__focus_drop_user_day_kpi.sql
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.focus_drop_user_day_kpi (
  analysis_date         DATE,
  user_id               STRING,
  light_session_count   INT,
  heavy_session_count   INT,
  idle_gap_total        INT,
  total_sessions        INT,
  is_light_user         BOOLEAN,
  is_heavy_user         BOOLEAN,
  is_idle_user          BOOLEAN,
  user_focus_drop_level STRING
)
USING DELTA
PARTITIONED BY (analysis_date)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE analytics.focus_drop_user_day_kpi
  IS 'Daily user-level KPI aggregation and focus drop classification. Partitioned by analysis_date.';
ALTER TABLE analytics.focus_drop_user_day_kpi
  ADD CONSTRAINT kpi_analysis_date_not_null CHECK (analysis_date IS NOT NULL);
ALTER TABLE analytics.focus_drop_user_day_kpi
  ADD CONSTRAINT kpi_user_id_not_null       CHECK (user_id       IS NOT NULL);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 2. inspection_quality_monthly_fpy
--    월 1회 — 월별 검수 반려율 & First Pass Yield
--    소스: mrt__inspection_quality_monthly_fpy.sql
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.inspection_quality_monthly_fpy (
  deliver_month        STRING,   -- 'yy-MM' 형식 (예: 26-04)
  total_inspected      BIGINT,
  rejected_count       BIGINT,
  rejection_rate_pct   DOUBLE,
  first_pass_yield_pct DOUBLE,
  distinct_reasons     ARRAY<STRING>
)
USING DELTA
PARTITIONED BY (deliver_month)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE analytics.inspection_quality_monthly_fpy
  IS 'Monthly inspection rejection rate and First Pass Yield (FPY) by delivered tasks.';
ALTER TABLE analytics.inspection_quality_monthly_fpy
  ADD CONSTRAINT fpy_deliver_month_not_null CHECK (deliver_month IS NOT NULL);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 3. inspection_quality_multi_reject
--    월 1회 — 다중 반려 Task 상세 (rejection ≥ 2)
--    소스: mrt__inspection_quality_multi_reject_detail.sql
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.inspection_quality_multi_reject (
  task_id        STRING,
  task_name      STRING,
  assignment_id  STRING,
  deliver_month  STRING,
  reject_count   BIGINT,
  reject_details ARRAY<STRUCT<
    rejected_at:   STRING,
    rejected_by:   STRING,
    reject_reason: STRING
  >>
)
USING DELTA
PARTITIONED BY (deliver_month)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE analytics.inspection_quality_multi_reject
  IS 'Monthly task-level detail for inspection reject >= 2 occurrences.';
ALTER TABLE analytics.inspection_quality_multi_reject
  ADD CONSTRAINT mr_task_id_not_null       CHECK (task_id       IS NOT NULL);
ALTER TABLE analytics.inspection_quality_multi_reject
  ADD CONSTRAINT mr_deliver_month_not_null CHECK (deliver_month IS NOT NULL);

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 4. production_volume_weekly
--    주 1회 — 납품 Task 수 · 객체 수 · 생산성 지표
--    소스: mrt__production_volume_weekly.sql
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.production_volume_weekly (
  deliver_week_start          DATE,
  company_name                STRING,
  feature                     STRING,
  delivered_task_count        BIGINT,
  ld_lines                    BIGINT,
  ld_line_points              BIGINT,
  ld_road_boundaries          BIGINT,
  ld_road_boundary_points     BIGINT,
  ld_lanes                    BIGINT,
  ld_topologies               BIGINT,
  rmd_polywall_objects        BIGINT,
  rmd_bbox3d_objects          BIGINT,
  dynamic_targets             BIGINT,
  static_targets              BIGINT,
  delivered_object_count      BIGINT,
  delivered_point_count       BIGINT,
  avg_points_per_object       DOUBLE,
  user_hour_slots             BIGINT,
  person_days                 BIGINT,
  objects_per_hour            DOUBLE,
  tasks_per_person_day        DOUBLE,
  objects_per_person_day      DOUBLE,
  avg_hours_per_task          DOUBLE,
  median_hours_per_task       DOUBLE,
  avg_net_hours_per_task      DOUBLE,
  median_net_hours_per_task   DOUBLE
)
USING DELTA
PARTITIONED BY (deliver_week_start)
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion'   = '2',
  'delta.minWriterVersion'   = '5'
);

-- COMMAND ----------

COMMENT ON TABLE analytics.production_volume_weekly
  IS 'Weekly delivered task count, object count, and productivity metrics by company and feature.';
ALTER TABLE analytics.production_volume_weekly
  ADD CONSTRAINT pvw_deliver_week_not_null CHECK (deliver_week_start IS NOT NULL);

-- COMMAND ----------

-- ★ 생성 확인
SELECT table_name, partition_columns
FROM information_schema.tables
WHERE table_schema = 'analytics'
  AND table_name IN (
    'focus_drop_user_day_kpi',
    'inspection_quality_monthly_fpy',
    'inspection_quality_multi_reject',
    'production_volume_weekly'
  )
ORDER BY table_name;
