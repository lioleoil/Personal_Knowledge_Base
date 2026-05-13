-- Databricks notebook source
-- [DEPRECATED] Production Volume DDL → mrt__ddl.sql 로 통합됨
-- 이 파일은 mrt__ddl.sql 마이그레이션 검증 완료 후 삭제 예정
-- ────────────────────────────────────────────────────────────────
-- Production Volume & Productivity — 테이블 초기 생성 DDL
-- 실행 조건: Unity Catalog 환경, analytics 스키마 존재

-- COMMAND ----------

-- ════════════════════════════════════════════════
-- 1. production_volume_weekly
--    주별 납품 Task 수 · 세부 객체 수 · 생산성 지표
--    소스: production_volume__weekly.sql
-- ════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analytics.production_volume_weekly (
  deliver_week_start          DATE,      -- 해당 주 월요일 (KST 기준) — 파티션 키
  company_name                STRING,    -- 업체명
  feature                     STRING,    -- Feature (MV2_LD, MV2_OD, MV2_SOD, MV2_RMD, MV2_TSTLD)
  delivered_task_count        BIGINT,    -- 주당 납품 Task 수 (재납품 중복 제거)

  -- ─── LD 세부 객체 (MV2_LD 전용, 타 feature NULL) ──────────────────────
  ld_lines                    BIGINT,    -- gen2_lines
  ld_line_points              BIGINT,    -- gen2_line_point  (보조 지표)
  ld_road_boundaries          BIGINT,    -- gen2_road_boundary
  ld_road_boundary_points     BIGINT,    -- gen2_road_boundary_point (보조 지표)
  ld_lanes                    BIGINT,    -- gen2_lane
  ld_topologies               BIGINT,    -- gen2_topology

  -- ─── RMD 세부 객체 (MV2_RMD 전용, 타 feature NULL) ──────────────────
  rmd_polywall_objects        BIGINT,    -- gen2_polywall_roadmark_objects
  rmd_bbox3d_objects          BIGINT,    -- gen2_bbox3d_object

  -- ─── OD / SOD / TSTLD 세부 객체 ──────────────────────────────────────
  -- OD: dynamic_targets + static_targets 모두 집계
  -- SOD / TSTLD: static_targets만 (feature 행으로 자연 분리)
  dynamic_targets             BIGINT,    -- gen2_dynamic_targets (MV2_OD 전용)
  static_targets              BIGINT,    -- gen2_static_targets (MV2_OD / SOD / TSTLD)

  -- ─── 요약 지표 (생산성 산출 기준) ────────────────────────────────────
  delivered_object_count      BIGINT,    -- primary objects 합산 (feature별 기준 정의)
  delivered_point_count       BIGINT,    -- LD 포인트 합산 (line_points + road_boundary_points), 타 feature NULL
  avg_points_per_object       DOUBLE,    -- LD 복잡도 proxy = delivered_point_count / delivered_object_count

  -- ─── 투입 자원 ────────────────────────────────────────────────────────
  user_hour_slots             BIGINT,    -- 투입 인시 (납품 Task 실발생 커맨드, Labeler+Reviewer 합산)
  person_days                 BIGINT,    -- 투입 인일 (납품 Task 실발생 커맨드, Labeler+Reviewer 합산)

  -- ─── 생산성 지표 ──────────────────────────────────────────────────────
  objects_per_hour            DOUBLE,    -- 시간당 납품 primary 객체 수
  tasks_per_person_day        DOUBLE,    -- 인일당 납품 Task 수
  objects_per_person_day      DOUBLE,    -- 인일당 납품 primary 객체 수 (1일 capa)
  avg_hours_per_task          DOUBLE,    -- Task 평균 소요시간 gross (착수→납품, 시간)
  median_hours_per_task       DOUBLE,    -- Task 소요시간 중앙값 gross (시간)
  avg_net_hours_per_task      DOUBLE,    -- Task 평균 순소요시간 (idle 차감, 시간)
  median_net_hours_per_task   DOUBLE     -- Task 순소요시간 중앙값 (idle 차감, 시간)
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
  AND table_name LIKE 'production_volume%'
ORDER BY table_name;
