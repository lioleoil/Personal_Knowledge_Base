-- Databricks notebook source
-- task_key: validate_labelit__quality

-- ============================================================
-- Notebook 04b: 수집 결과 품질 검증 (Quality Validation)
-- 실행 빈도: 배치 실행마다 (03_int 완료 후)
--
-- 목적:
--   수집·변환된 데이터의 품질이 분석에 신뢰할 수 있는 수준인지 확인
--   필드 완전성, 참조 무결성, 중복 여부, 구조적 유효성 검증
--
-- 검증 원칙: 각 셀 결과 = 0행이면 PASS / 1행 이상이면 FAIL(조사 필요)
--
-- 시나리오:
--   Q1: undo/redo 참조 무결성 (orphan undo 탐지)
--   Q2: Staging 전 테이블 필수 필드 NULL 규칙 검사
--         stg_labelit__events        — 5개 규칙
--         stg_labelit__event_changes — 3개 규칙
--         stg_labelit__undo_history  — 3개 규칙
--   Q3: 증분 적재 중복 여부
--   Q4: transform position 구조 무결성
-- ============================================================


-- ─────────────────────────────────────────────
-- [환경 설정] 카탈로그: ${catalog} 위젯으로 주입
-- ─────────────────────────────────────────────


-- ─────────────────────────────────────────────
-- [Q1] undo/redo 참조 무결성
--
-- 검증 대상: stg_labelit__undo_history.reverted_event_id
-- 검증 방법: LEFT JOIN stg_labelit__events → 매칭 없는 orphan undo 탐지
-- 판정 기준: 0행 = PASS / 반환 행 = 취소 대상 이벤트 누락 (C1 누락 여부와 함께 조사)
--
-- 예상 원인 (실패 시):
--   - undo 도착 시점에 원본 transform 이벤트가 아직 stg 미적재 (레이어 간 시차)
--   - reverted_command_id 값 오류 (클라이언트 버그)
-- ─────────────────────────────────────────────
SELECT
  u.event_id                                                   AS undo_event_id,
  u.event_time,
  u.is_redo,
  u.session_id,
  u.task_id,
  u.reverted_event_id,
  u.reverted_command_type
FROM ${catalog}.labelit_stg.stg_labelit__undo_history u
LEFT JOIN ${catalog}.labelit_stg.stg_labelit__events e
  ON u.reverted_event_id = e.event_id
WHERE e.event_id IS NULL
ORDER BY u.event_time;


-- ─────────────────────────────────────────────
-- [Q2] Staging 전 테이블 필수 필드 NULL 규칙 검사
--
-- 검증 대상:
--   stg_labelit__events        : event_type / user_id / task_id / session_id
--   stg_labelit__event_changes : change_action / old_val / new_val
--   stg_labelit__undo_history  : reverted_event_id / reverted_command_type / session_id
-- 검증 방법: 규칙별 UNION ALL → 위반 행 수집
-- 판정 기준: 0행 = PASS / 반환 행 = 규칙 위반 이벤트 (issue 컬럼에 원인 명시)
-- ─────────────────────────────────────────────

-- ── stg_labelit__events ──────────────────────

SELECT event_id, 'stg_events: event_type NULL or empty'       AS issue FROM ${catalog}.labelit_stg.stg_labelit__events
WHERE event_type   IS NULL OR event_type   = ''

UNION ALL

SELECT event_id, 'stg_events: user_id NULL or empty'          AS issue FROM ${catalog}.labelit_stg.stg_labelit__events
WHERE user_id      IS NULL OR user_id      = ''

UNION ALL

SELECT event_id, 'stg_events: task_id NULL or empty'          AS issue FROM ${catalog}.labelit_stg.stg_labelit__events
WHERE task_id      IS NULL OR task_id      = ''

UNION ALL

SELECT event_id, 'stg_events: session_id NULL or empty'       AS issue FROM ${catalog}.labelit_stg.stg_labelit__events
WHERE session_id   IS NULL OR session_id   = ''

UNION ALL

-- ── stg_labelit__event_changes ────────────────

SELECT
  CONCAT(event_id, '-', CAST(change_idx AS STRING))           AS event_id,
  'stg_event_changes: change_action NULL or empty'             AS issue
FROM ${catalog}.labelit_stg.stg_labelit__event_changes
WHERE change_action IS NULL OR change_action = ''

UNION ALL

SELECT
  CONCAT(event_id, '-', CAST(change_idx AS STRING)),
  'stg_event_changes: old_val NULL'
FROM ${catalog}.labelit_stg.stg_labelit__event_changes
WHERE old_val IS NULL
  AND change_action != 'create'   -- create 액션은 old_val=NULL 이 정상 (신규 생성)

UNION ALL

SELECT
  CONCAT(event_id, '-', CAST(change_idx AS STRING)),
  'stg_event_changes: new_val NULL'
FROM ${catalog}.labelit_stg.stg_labelit__event_changes
WHERE new_val IS NULL

UNION ALL

-- ── stg_labelit__undo_history ─────────────────

SELECT event_id, 'stg_undo_history: reverted_event_id NULL or empty'     AS issue FROM ${catalog}.labelit_stg.stg_labelit__undo_history
WHERE reverted_event_id    IS NULL OR reverted_event_id    = ''

UNION ALL

SELECT event_id, 'stg_undo_history: reverted_command_type NULL or empty'  AS issue FROM ${catalog}.labelit_stg.stg_labelit__undo_history
WHERE reverted_command_type IS NULL OR reverted_command_type = ''

UNION ALL

SELECT event_id, 'stg_undo_history: session_id NULL or empty'            AS issue FROM ${catalog}.labelit_stg.stg_labelit__undo_history
WHERE session_id IS NULL OR session_id = ''

ORDER BY issue, event_id;


-- ─────────────────────────────────────────────
-- [Q3] 증분 적재 중복 여부
--
-- 검증 대상: stg_labelit__events (event_id) / stg_labelit__event_changes (event_id, change_idx)
-- 검증 방법: GROUP BY + HAVING COUNT > 1
-- 판정 기준: 0행 = PASS / 반환 행 = 동일 이벤트 중복 적재
--
-- 예상 원인 (실패 시):
--   - occurred_at 기준 증분 필터의 경계값 중복 처리
--     (MAX(occurred_at) 시각과 동일한 이벤트가 다음 배치에 재포함)
--   - 소스 데이터에 _id 중복 (upstream 문제)
-- ─────────────────────────────────────────────
SELECT
  event_id,
  COUNT(*)                          AS dup_cnt,
  MIN(occurred_at)                  AS first_occurred,
  MAX(occurred_at)                  AS last_occurred,
  'stg_events: event_id 중복'       AS issue
FROM ${catalog}.labelit_stg.stg_labelit__events
GROUP BY event_id
HAVING COUNT(*) > 1

UNION ALL

SELECT
  CONCAT(event_id, '-', CAST(change_idx AS STRING)) AS event_id,
  COUNT(*)                                           AS dup_cnt,
  MIN(occurred_at)                                   AS first_occurred,
  MAX(occurred_at)                                   AS last_occurred,
  'stg_event_changes: (event_id, change_idx) 중복'   AS issue
FROM ${catalog}.labelit_stg.stg_labelit__event_changes
GROUP BY event_id, change_idx
HAVING COUNT(*) > 1

ORDER BY issue, dup_cnt DESC;


-- ─────────────────────────────────────────────
-- [Q4] transform position 구조 무결성
--
-- 검증 대상: stg_labelit__event_changes (annotation.bbox3d.transform 이벤트)
-- 검증 방법: old_val / new_val 에서 position.x 필드 파싱 → NULL 여부 확인
-- 판정 기준: 0행 = PASS / 반환 행 = position 필드 누락 (int_bbox3d_transforms 에서 제외됨)
--
-- 주의:
--   - position 없이 rotation/size 만 변경된 경우도 해당 — 의도적 변경인지 확인 필요
-- ─────────────────────────────────────────────
SELECT
  event_id,
  change_idx,
  change_action,
  CASE
    WHEN get_json_object(old_val, '$.position.x') IS NULL AND
         get_json_object(new_val, '$.position.x') IS NULL THEN 'old·new 모두 position 누락'
    WHEN get_json_object(old_val, '$.position.x') IS NULL THEN 'old position 누락'
    WHEN get_json_object(new_val, '$.position.x') IS NULL THEN 'new position 누락'
  END                                                        AS issue
FROM ${catalog}.labelit_stg.stg_labelit__event_changes
WHERE event_type = 'annotation.bbox3d.transform'
  AND (
    get_json_object(old_val, '$.position.x') IS NULL OR
    get_json_object(new_val, '$.position.x') IS NULL
  )
ORDER BY event_id, change_idx;


-- ─────────────────────────────────────────────
-- [품질 검증 요약]
-- ─────────────────────────────────────────────
SELECT 'Q1: undo orphan (참조 무결성)' AS scenario, COUNT(*) AS fail_count
FROM (
  SELECT u.event_id
  FROM ${catalog}.labelit_stg.stg_labelit__undo_history u
  LEFT JOIN ${catalog}.labelit_stg.stg_labelit__events e ON u.reverted_event_id = e.event_id
  WHERE e.event_id IS NULL
)

UNION ALL

SELECT 'Q2: Staging NULL 규칙 위반' AS scenario, COUNT(*) AS fail_count
FROM (
  SELECT event_id FROM ${catalog}.labelit_stg.stg_labelit__events
  WHERE event_type  IS NULL OR event_type  = ''
     OR user_id     IS NULL OR user_id     = ''
     OR task_id     IS NULL OR task_id     = ''
     OR session_id  IS NULL OR session_id  = ''

  UNION ALL

  SELECT CONCAT(event_id, '-', CAST(change_idx AS STRING))
  FROM ${catalog}.labelit_stg.stg_labelit__event_changes
  WHERE change_action IS NULL OR change_action = ''
     OR (old_val IS NULL AND change_action != 'create')   -- create 액션 제외
     OR new_val       IS NULL

  UNION ALL

  SELECT event_id FROM ${catalog}.labelit_stg.stg_labelit__undo_history
  WHERE reverted_event_id    IS NULL OR reverted_event_id    = ''
     OR reverted_command_type IS NULL OR reverted_command_type = ''
     OR session_id            IS NULL OR session_id            = ''
)

UNION ALL

SELECT 'Q3: 증분 중복 (stg_events)' AS scenario, COUNT(*) AS fail_count
FROM (
  SELECT event_id FROM ${catalog}.labelit_stg.stg_labelit__events
  GROUP BY event_id HAVING COUNT(*) > 1
)

UNION ALL

SELECT 'Q4: transform position 누락' AS scenario, COUNT(*) AS fail_count
FROM (
  SELECT event_id FROM ${catalog}.labelit_stg.stg_labelit__event_changes
  WHERE event_type = 'annotation.bbox3d.transform'
    AND (get_json_object(old_val,'$.position.x') IS NULL
      OR get_json_object(new_val,'$.position.x') IS NULL)
)

ORDER BY scenario;
-- fail_count = 0 → PASS / fail_count > 0 → 상세 셀 확인
