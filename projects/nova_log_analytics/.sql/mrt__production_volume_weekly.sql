-- Databricks notebook source
-- Marts: production_volume_weekly (납품 생산량 & 생산성, 주 1회)
-- 집계 단위 : deliver_week_start (납품 시점 기준 주 월요일, KST)
-- 갱신 전략 : INSERT INTO analytics.production_volume_weekly REPLACE WHERE deliver_week_start
-- 실행 주기 : 주 1회 (월요일, 전 주 데이터 대상)
-- 파라미터  : analysis_week (YYYY-MM-DD, 대상 주 월요일) — 미입력 시 전 주 자동 산출
-- 선행 조건 : stg__task_transition_events / int__object_counts_by_task / int__command_slots_by_task / dim__companies / dim__policies 갱신 완료

-- COMMAND ----------

DECLARE OR REPLACE VARIABLE analysis_week DATE
  DEFAULT DATE_TRUNC('WEEK', CURRENT_DATE() - INTERVAL 7 DAYS);

-- Job 실행 시 base_parameters.analysis_week 로 주입됨
-- 수동 실행 시: SET VAR analysis_week = DATE '2026-05-05';

-- COMMAND ----------

INSERT INTO analytics.production_volume_weekly
REPLACE WHERE deliver_week_start = analysis_week
WITH

-- ─────────────────────────────────────────────
-- 1. 납품 이벤트 (대상 주 최초 납품만)
-- ─────────────────────────────────────────────
deliver_events AS (
  SELECT
    task_id,
    company_id,
    policy_id,
    action_at                                                                  AS deliver_at,
    event_week                                                                 AS deliver_week_start,
    ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY action_at ASC)            AS deliver_seq
  FROM analytics.stg_task_transition_events
  WHERE from_state = 'waiting_submit'
    AND to_state   = 'inspection'
    AND event_week = analysis_week
),
first_delivers AS (
  SELECT * FROM deliver_events WHERE deliver_seq = 1
),

-- ─────────────────────────────────────────────
-- 2. 라벨링 착수 시점 (최초 start 이벤트)
-- ─────────────────────────────────────────────
start_events AS (
  SELECT task_id, MIN(action_at) AS start_at
  FROM analytics.stg_task_transition_events
  WHERE from_state = 'waiting_labeling'
    AND to_state   = 'labeling'
    AND trigger    = 'start'
    AND task_id IN (SELECT task_id FROM first_delivers)
  GROUP BY task_id
),

-- ─────────────────────────────────────────────
-- 3. 납품 객체 수 — staging PIVOT
--    int_object_counts_by_task (task_id × table_name × stage_key)
-- ─────────────────────────────────────────────
obj AS (
  SELECT
    task_id,
    SUM(CASE WHEN table_name = 'gen2_lines'                     THEN object_count END) AS ld_lines,
    SUM(CASE WHEN table_name = 'gen2_line_point'                THEN object_count END) AS ld_line_points,
    SUM(CASE WHEN table_name = 'gen2_road_boundary'             THEN object_count END) AS ld_road_boundaries,
    SUM(CASE WHEN table_name = 'gen2_road_boundary_point'       THEN object_count END) AS ld_road_boundary_points,
    SUM(CASE WHEN table_name = 'gen2_lane'                      THEN object_count END) AS ld_lanes,
    SUM(CASE WHEN table_name = 'gen2_topology'                  THEN object_count END) AS ld_topologies,
    SUM(CASE WHEN table_name = 'gen2_polywall_roadmark_objects' THEN object_count END) AS rmd_polywall_objects,
    SUM(CASE WHEN table_name = 'gen2_bbox3d_object'             THEN object_count END) AS rmd_bbox3d_objects,
    SUM(CASE WHEN table_name = 'gen2_dynamic_targets'           THEN object_count END) AS dynamic_targets,
    SUM(CASE WHEN table_name = 'gen2_static_targets'            THEN object_count END) AS static_targets
  FROM analytics.int_object_counts_by_task
  WHERE stage_key = 'inspection'
    AND task_id IN (SELECT task_id FROM first_delivers)
  GROUP BY task_id
),

-- ─────────────────────────────────────────────
-- 4. 투입 자원
-- ─────────────────────────────────────────────
cmd AS (
  SELECT task_id, user_hour_slots, person_days
  FROM analytics.int_command_slots_by_task
  WHERE task_id IN (SELECT task_id FROM first_delivers)
),

-- ─────────────────────────────────────────────
-- 5. Task 순소요시간 — idle 차감 (Focus Drop 연계)
--    role_scope='labeler' : Phase A/B 기본값
--    Phase C 전환 시: 'all_roles' 로 변경
-- ─────────────────────────────────────────────
task_idle AS (
  SELECT task_id, SUM(idle_gap_duration_sec) AS task_total_idle_sec
  FROM analytics.focus_drop_task_idle_rollup
  WHERE role_scope = 'labeler'
  GROUP BY task_id
),

-- ─────────────────────────────────────────────
-- 6. Task 단위 상세 (집계 전)
-- ─────────────────────────────────────────────
task_detail AS (
  SELECT
    d.task_id,
    d.deliver_week_start,
    c.company_name,
    p.feature,

    -- ─── LD 세부 객체 ───────────────────────────────────────────────────
    obj.ld_lines,
    obj.ld_line_points,
    obj.ld_road_boundaries,
    obj.ld_road_boundary_points,
    obj.ld_lanes,
    obj.ld_topologies,

    -- ─── RMD 세부 객체 ──────────────────────────────────────────────────
    obj.rmd_polywall_objects,
    obj.rmd_bbox3d_objects,

    -- ─── OD / SOD / TSTLD 세부 객체 ─────────────────────────────────────
    obj.dynamic_targets,
    obj.static_targets,

    -- ─── 요약 지표 ───────────────────────────────────────────────────────
    CASE p.feature
      WHEN 'MV2_LD'    THEN COALESCE(obj.ld_lines,           0)
                          + COALESCE(obj.ld_road_boundaries, 0)
                          + COALESCE(obj.ld_lanes,           0)
                          + COALESCE(obj.ld_topologies,      0)
      WHEN 'MV2_RMD'   THEN COALESCE(obj.rmd_polywall_objects, 0)
                          + COALESCE(obj.rmd_bbox3d_objects,    0)
      WHEN 'MV2_OD'    THEN COALESCE(obj.dynamic_targets,    0)
                          + COALESCE(obj.static_targets,     0)
      WHEN 'MV2_SOD'   THEN COALESCE(obj.static_targets,     0)
      WHEN 'MV2_TSTLD' THEN COALESCE(obj.static_targets,     0)
      ELSE NULL
    END                                                                    AS delivered_object_count,
    CASE p.feature
      WHEN 'MV2_LD' THEN COALESCE(obj.ld_line_points,          0)
                       + COALESCE(obj.ld_road_boundary_points, 0)
      ELSE NULL
    END                                                                    AS delivered_point_count,

    -- ─── 투입 자원 ────────────────────────────────────────────────────────
    cmd.user_hour_slots,
    cmd.person_days,

    -- ─── 소요시간 ─────────────────────────────────────────────────────────
    CASE WHEN s.start_at IS NOT NULL
      THEN (
        UNIX_TIMESTAMP(d.deliver_at)
        - UNIX_TIMESTAMP(s.start_at)
      ) / 3600.0
    END                                                                    AS hours_per_task,
    CASE WHEN s.start_at IS NOT NULL
      THEN GREATEST(
        UNIX_TIMESTAMP(d.deliver_at)
        - UNIX_TIMESTAMP(s.start_at)
        - COALESCE(idle.task_total_idle_sec, 0),
        0
      ) / 3600.0
    END                                                                    AS net_hours_per_task

  FROM first_delivers    d
  LEFT JOIN analytics.dim_companies c    ON d.company_id = c.company_id
  LEFT JOIN analytics.dim_policies  p    ON d.policy_id  = p.policy_id
  LEFT JOIN obj               ON d.task_id    = obj.task_id
  LEFT JOIN cmd               ON d.task_id    = cmd.task_id
  LEFT JOIN start_events s    ON d.task_id    = s.task_id
  LEFT JOIN task_idle    idle ON d.task_id    = idle.task_id
)

-- ─────────────────────────────────────────────
-- 7. 최종 집계
-- ─────────────────────────────────────────────
SELECT
  deliver_week_start,
  company_name,
  feature,
  COUNT(DISTINCT task_id)                                                          AS delivered_task_count,
  -- LD 세부
  SUM(ld_lines)                                                                    AS ld_lines,
  SUM(ld_line_points)                                                              AS ld_line_points,
  SUM(ld_road_boundaries)                                                          AS ld_road_boundaries,
  SUM(ld_road_boundary_points)                                                     AS ld_road_boundary_points,
  SUM(ld_lanes)                                                                    AS ld_lanes,
  SUM(ld_topologies)                                                               AS ld_topologies,
  -- RMD 세부
  SUM(rmd_polywall_objects)                                                        AS rmd_polywall_objects,
  SUM(rmd_bbox3d_objects)                                                          AS rmd_bbox3d_objects,
  -- OD / SOD / TSTLD 세부
  SUM(dynamic_targets)                                                             AS dynamic_targets,
  SUM(static_targets)                                                              AS static_targets,
  -- 요약
  SUM(delivered_object_count)                                                      AS delivered_object_count,
  SUM(delivered_point_count)                                                       AS delivered_point_count,
  ROUND(
    SUM(delivered_point_count) / NULLIF(SUM(delivered_object_count), 0), 2
  )                                                                                AS avg_points_per_object,
  -- 투입 자원
  SUM(user_hour_slots)                                                             AS user_hour_slots,
  SUM(person_days)                                                                 AS person_days,
  -- 생산성
  ROUND(SUM(delivered_object_count) / NULLIF(SUM(user_hour_slots), 0), 3)         AS objects_per_hour,
  ROUND(COUNT(DISTINCT task_id)     / NULLIF(SUM(person_days),     0), 2)         AS tasks_per_person_day,
  ROUND(SUM(delivered_object_count) / NULLIF(SUM(person_days),     0), 2)         AS objects_per_person_day,
  ROUND(AVG(hours_per_task),                                             2)        AS avg_hours_per_task,
  ROUND(PERCENTILE_APPROX(hours_per_task,     0.5),                      2)        AS median_hours_per_task,
  ROUND(AVG(net_hours_per_task),                                         2)        AS avg_net_hours_per_task,
  ROUND(PERCENTILE_APPROX(net_hours_per_task, 0.5),                      2)        AS median_net_hours_per_task
FROM task_detail
GROUP BY deliver_week_start, company_name, feature;

-- COMMAND ----------

-- ★ 적재 확인 (대상 주 결과 검증)
SELECT
  deliver_week_start,
  company_name,
  feature,
  delivered_task_count,
  delivered_object_count,
  delivered_point_count,
  avg_points_per_object,
  user_hour_slots,
  person_days,
  objects_per_hour,
  tasks_per_person_day,
  avg_hours_per_task,
  avg_net_hours_per_task,
  median_net_hours_per_task
FROM analytics.production_volume_weekly
WHERE deliver_week_start = analysis_week
ORDER BY company_name, feature;

-- COMMAND ----------

-- ★ feature별 집계 요약
SELECT
  deliver_week_start,
  feature,
  COUNT(*)                     AS row_count,
  SUM(delivered_task_count)    AS total_tasks,
  SUM(delivered_object_count)  AS total_objects
FROM analytics.production_volume_weekly
WHERE deliver_week_start = analysis_week
GROUP BY deliver_week_start, feature
ORDER BY feature;
