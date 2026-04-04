-- Databricks notebook source
-- task_key: spot_check_labelit__command_arrival

-- ============================================================
-- Notebook 05: 커맨드 도달 확인 (Spot Check) — Data Engineer 전용
-- 실행 빈도: 신규 커맨드 등록 후 1회, 또는 수집 이상 의심 시
--
-- 실행 주체: Data Engineer (Databricks)
--
-- 목적:
--   QA/Tester가 Labelit 앱에서 시나리오 액션을 수행한 뒤,
--   Data Engineer가 해당 이벤트가 Raw → Staging 까지 도달했는지 데이터 측에서 확인
--
-- 사전 조건:
--   1. App Engineer 가 해당 커맨드 로그를 앱에 구현·배포 완료
--      (배포는 Data Engineer의 파이프라인 반영 완료 통보 이후에 진행)
--   2. Data Engineer 가 수집 정의 반영 완료 (01~03 파이프라인 실행 확인)
--   3. QA/Tester 가 Labelit 앱에서 해당 커맨드 액션을 수행하고
--      session_id·user_name·task_id·수행 일시 를 Data Engineer 에게 전달한 상태
--      (docs/collection_requests.md 의 "수행 후 기록할 정보" 양식 참고)
--
-- Widget 파라미터 (실행 전 입력):
--   target_feature     : 확인할 feature 값 (예: od / rmd / ld)
--   target_event_type  : 확인할 커맨드 타입 (docs/command_spec_template.md 의 커맨드 목록 참고)
--   target_session_id  : 수행 세션 ID (빈값 = 전체 세션)
--   target_user_name   : 수행 계정 (빈값 = 전체 사용자)
--   target_task_id     : 작업 태스크 ID (빈값 = 전체 태스크)
--   action_time_from   : 앱 액션 수행 시작 시각 (예: 2026-03-24 00:00:00)
--   action_time_to     : 앱 액션 수행 종료 시각 (예: 2026-03-24 23:59:59)
--
-- 필터 우선순위: session_id + task_id 조합으로 이벤트를 충분히 특정할 수 있음
--   → action_time 은 보조 필터 역할 (QA가 전달한 대략적 수행 일시를 날짜 단위 범위로 변환하여 입력)
--   → 예: QA가 "2026-03-24 오전"으로 전달 시 → from: 2026-03-24 00:00:00 / to: 2026-03-24 12:00:00
-- ============================================================


-- ─────────────────────────────────────────────
-- [환경 설정] 카탈로그: ${catalog} 위젯으로 주입
-- ─────────────────────────────────────────────


-- ─────────────────────────────────────────────
-- [CELL 1] 검증 대상 파라미터 확인
-- 실행 후 입력값이 의도와 일치하는지 확인하고 다음 셀로 진행
-- ─────────────────────────────────────────────
SELECT
  '${target_feature}'       AS target_feature,
  '${target_event_type}'    AS target_event_type,
  CASE WHEN '${target_session_id}'  = '' THEN '(전체)' ELSE '${target_session_id}'  END AS session_filter,
  CASE WHEN '${target_user_name}'   = '' THEN '(전체)' ELSE '${target_user_name}'   END AS user_filter,
  CASE WHEN '${target_task_id}'     = '' THEN '(전체)' ELSE '${target_task_id}'     END AS task_filter,
  '${action_time_from}'     AS action_time_from,
  '${action_time_to}'       AS action_time_to;


-- ─────────────────────────────────────────────
-- [CELL 2] Raw 도달 확인
--
-- 목적: 시간 범위 내에 해당 커맨드가 Raw 레이어에 도달했는지 확인
-- 결과: 1행 이상 = 도달 / 0행 = 미도달 (앱 또는 파이프라인 이상)
--
-- 주의:
--   - occurred_at(서버 수신 시각) 기준으로 필터링
--   - session_id + task_id 로 이벤트 특정이 가능하므로 action_time 은 넓게 설정 가능
--   - latency_sec: 클라이언트 발생 → 서버 수신 소요 시간 (음수면 클라이언트 시계 오차)
-- ─────────────────────────────────────────────
SELECT
  _id                                                             AS event_id,
  get_json_object(_raw, '$.type')                                 AS event_type,
  get_json_object(_raw, '$.data.feature')                         AS feature,
  to_timestamp(get_json_object(_raw, '$.time'))                   AS event_time,
  to_timestamp(occurred_at)                                       AS occurred_at,
  ROUND(
    UNIX_TIMESTAMP(to_timestamp(occurred_at))
    - UNIX_TIMESTAMP(to_timestamp(get_json_object(_raw, '$.time'))), 1
  )                                                               AS latency_sec,
  get_json_object(_raw, '$.sessionid')                            AS session_id,
  get_json_object(_raw, '$.data.user.name')                       AS user_name,
  get_json_object(_raw, '$.data.project.task_id')                 AS task_id

FROM ${catalog}.labelit_raw.raw_labelit__workspace_command

WHERE get_json_object(_raw, '$.type') = '${target_event_type}'
  AND get_json_object(_raw, '$.data.feature') = '${target_feature}'
  AND to_timestamp(occurred_at)
        BETWEEN TIMESTAMP '${action_time_from}'
            AND TIMESTAMP '${action_time_to}'
  AND (
    '${target_session_id}' = ''
    OR get_json_object(_raw, '$.sessionid') = '${target_session_id}'
  )
  AND (
    '${target_user_name}' = ''
    OR get_json_object(_raw, '$.data.user.name') = '${target_user_name}'
  )
  AND (
    '${target_task_id}' = ''
    OR get_json_object(_raw, '$.data.project.task_id') = '${target_task_id}'
  )

ORDER BY occurred_at, event_id;


-- ─────────────────────────────────────────────
-- [CELL 3] Staging 반영 확인
--
-- 목적: Raw에 도달한 event_id 가 Staging 레이어에도 반영됐는지 확인
-- 결과: staging_status = '미반영' 인 행이 있으면 02_stg 재실행 필요
--
-- 주의:
--   - history.undo/redo 는 stg_events 가 아닌 stg_undo_history 에서 반영됨
--   - 02_stg 노트북이 Raw 적재 후 아직 실행되지 않았다면 일시적으로 미반영 표시됨
-- ─────────────────────────────────────────────
WITH raw_events AS (
  SELECT
    _id                                                           AS event_id,
    get_json_object(_raw, '$.sessionid')                          AS session_id,
    get_json_object(_raw, '$.data.user.name')                     AS user_name,
    get_json_object(_raw, '$.data.project.task_id')               AS task_id,
    to_timestamp(occurred_at)                                     AS raw_occurred_at
  FROM ${catalog}.labelit_raw.raw_labelit__workspace_command
  WHERE get_json_object(_raw, '$.type') = '${target_event_type}'
    AND get_json_object(_raw, '$.data.feature') = '${target_feature}'
    AND to_timestamp(occurred_at)
          BETWEEN TIMESTAMP '${action_time_from}'
              AND TIMESTAMP '${action_time_to}'
    AND (
      '${target_session_id}' = ''
      OR get_json_object(_raw, '$.sessionid') = '${target_session_id}'
    )
    AND (
      '${target_user_name}' = ''
      OR get_json_object(_raw, '$.data.user.name') = '${target_user_name}'
    )
    AND (
      '${target_task_id}' = ''
      OR get_json_object(_raw, '$.data.project.task_id') = '${target_task_id}'
    )
)

SELECT
  r.event_id,
  r.session_id,
  r.user_name,
  r.task_id,
  r.raw_occurred_at,
  CASE
    WHEN e.event_id IS NOT NULL THEN 'stg_events 반영'
    WHEN u.event_id IS NOT NULL THEN 'stg_undo_history 반영'
    ELSE '미반영 (02_stg 실행 확인 필요)'
  END                                                             AS staging_status,
  COALESCE(e.occurred_at, u.occurred_at)                          AS stg_occurred_at

FROM raw_events r
LEFT JOIN ${catalog}.labelit_stg.stg_labelit__events e
  ON r.event_id = e.event_id
LEFT JOIN ${catalog}.labelit_stg.stg_labelit__undo_history u
  ON r.event_id = u.event_id

ORDER BY r.raw_occurred_at, r.event_id;


-- ─────────────────────────────────────────────
-- [CELL 4] 도달 결과 요약
--
-- 목적: Raw 건수 / Staging 반영 건수 / 미반영 건수를 한 눈에 확인
-- 판정:
--   PASS     → Raw 도달 + Staging 전량 반영 = 수집 정상
--   PARTIAL  → Raw 도달 + Staging 일부 미반영 = 02_stg 재실행 후 재확인
--   FAIL(Raw)→ Raw 미도달 = 앱 액션 재수행 또는 파이프라인 상류 확인
--   FAIL(Stg)→ Raw 도달 + Staging 전체 미반영 = 02_stg 미실행 또는 오류
-- ─────────────────────────────────────────────
WITH raw_cnt AS (
  SELECT COUNT(*) AS cnt
  FROM ${catalog}.labelit_raw.raw_labelit__workspace_command
  WHERE get_json_object(_raw, '$.type') = '${target_event_type}'
    AND get_json_object(_raw, '$.data.feature') = '${target_feature}'
    AND to_timestamp(occurred_at)
          BETWEEN TIMESTAMP '${action_time_from}'
              AND TIMESTAMP '${action_time_to}'
    AND ('${target_session_id}' = ''
         OR get_json_object(_raw,'$.sessionid') = '${target_session_id}')
    AND ('${target_user_name}' = ''
         OR get_json_object(_raw,'$.data.user.name') = '${target_user_name}')
    AND ('${target_task_id}' = ''
         OR get_json_object(_raw,'$.data.project.task_id') = '${target_task_id}')
),

stg_events_cnt AS (
  SELECT COUNT(*) AS cnt
  FROM ${catalog}.labelit_stg.stg_labelit__events
  WHERE event_type = '${target_event_type}'
    AND feature = '${target_feature}'
    AND occurred_at
          BETWEEN TIMESTAMP '${action_time_from}'
              AND TIMESTAMP '${action_time_to}'
    AND ('${target_session_id}' = '' OR session_id = '${target_session_id}')
    AND ('${target_user_name}'  = '' OR user_name  = '${target_user_name}')
    AND ('${target_task_id}'    = '' OR task_id    = '${target_task_id}')
),

stg_undo_cnt AS (
  SELECT COUNT(*) AS cnt
  FROM ${catalog}.labelit_stg.stg_labelit__undo_history
  WHERE event_type = '${target_event_type}'
    AND feature = '${target_feature}'
    AND occurred_at
          BETWEEN TIMESTAMP '${action_time_from}'
              AND TIMESTAMP '${action_time_to}'
    AND ('${target_session_id}' = '' OR session_id = '${target_session_id}')
    AND ('${target_user_name}'  = '' OR user_name  = '${target_user_name}')
    AND ('${target_task_id}'    = '' OR task_id    = '${target_task_id}')
)

SELECT
  raw_cnt.cnt                                     AS raw_도달_건수,
  (stg_events_cnt.cnt + stg_undo_cnt.cnt)         AS stg_반영_건수,
  raw_cnt.cnt
    - (stg_events_cnt.cnt + stg_undo_cnt.cnt)     AS 미반영_건수,
  CASE
    WHEN raw_cnt.cnt = 0
      THEN '❌ FAIL — Raw 미도달 (앱 액션 재수행 또는 파이프라인 상류 확인)'
    WHEN raw_cnt.cnt = (stg_events_cnt.cnt + stg_undo_cnt.cnt)
      THEN '✅ PASS — Raw 도달 + Staging 전량 반영 → 04a/b 정기 검증 이관 가능'
    WHEN (stg_events_cnt.cnt + stg_undo_cnt.cnt) > 0
      THEN '⚠️ PARTIAL — 일부 미반영 → 02_stg 재실행 후 재확인'
    ELSE
         '❌ FAIL — Raw 도달 but Staging 미반영 → 02_stg 실행 여부 확인'
  END                                             AS result

FROM raw_cnt, stg_events_cnt, stg_undo_cnt;


-- ─────────────────────────────────────────────
-- [CELL 5] 다음 단계 안내
-- ─────────────────────────────────────────────
-- PASS 확인 후 수행할 사항:
--   1. docs/collection_requests.md 이력 테이블 상태를 "✅ 완료" 로 업데이트
--   2. 아래 정기 검증 노트북 순서대로 실행:
--        04a_validate__completeness  → C1~C5: 완전성 확인
--        04b_validate__quality       → Q1~Q4: 품질 확인
--
-- FAIL 시 조사 순서:
--   Raw 미도달 → 앱 이벤트 발생 여부 확인 → Zerobus 커넥터 상태 확인
--             → (참고) 커맨드 스펙의 event_type 또는 feature 값이 파이프라인 정의와
--               일치하는지 확인 (미정의 커맨드인 경우 Raw 미도달로 나타날 수 있음)
--   Stg 미반영 → 02_stg__events.sql 또는 02_stg__undo_history.sql 재실행
--   부분 반영  → C1(레이어 간 건수 정합성) 시나리오로 상세 조사

SELECT '이 셀은 참고용 안내입니다. 위 CELL 4 결과를 기준으로 다음 단계를 결정하세요.' AS guide;
