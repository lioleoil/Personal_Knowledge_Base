-- Databricks notebook source
-- task_key: validate_labelit__completeness

-- ============================================================
-- Notebook 04a: 수집 완전성 검증 (Completeness Validation)
-- 실행 빈도: 배치 실행마다 (02_stg 전체 완료 후)
--
-- 목적:
--   이벤트가 Raw → Staging 을 거치며 누락 없이 흘렀는지,
--   논리적 시퀀스(select → transform → undo)가 깨지지 않았는지 확인
--
-- 검증 원칙:
--   C1·C2·C4·C5: 0행 = PASS
--   C3: 결과 반환 = 갭 구간 정보 (정보성 — PASS/FAIL 아님, 임계값 조정 필요)
--
-- 시나리오:
--   C1: 레이어 간 건수 정합성 (Raw ↔ Staging 누락 여부)
--   C2: changes EXPLODE 완전성 (params 건수 vs 실제 explode 건수)
--   C3: 이벤트 스트림 갭 탐지 (session 내 비정상 간격)
--   C4: undo 시간 순서 정합성 (undo가 원본보다 먼저 발생한 이상 케이스)
--   C5: 세션 내 커맨드 시퀀스 (transform 이전 select 미존재)
-- ============================================================


-- ─────────────────────────────────────────────
-- [환경 설정] 카탈로그: ${catalog} 위젯으로 주입
-- ─────────────────────────────────────────────


-- ─────────────────────────────────────────────
-- [C1] 레이어 간 건수 정합성
--
-- 검증 대상: Raw 총건수 vs (stg_events + stg_undo_history) 총건수
-- 검증 방법: 두 레이어 COUNT 차이 계산
-- 판정 기준: diff = 0 → PASS / diff ≠ 0 → Raw → Staging 전환 시 누락 발생
--
-- 주의:
--   - stg_events 는 undo/redo 를 제외하므로 stg_undo_history 와 합산해야 Raw 건수와 일치
--   - 증분 적재 시 각 레이어의 반영 시점 차이로 일시적 불일치가 발생할 수 있음
--     (모든 stg 노트북 실행 완료 후 검증할 것)
-- ─────────────────────────────────────────────
SELECT
  raw_cnt,
  stg_event_cnt,
  stg_undo_cnt,
  (stg_event_cnt + stg_undo_cnt)           AS stg_total_cnt,
  raw_cnt - (stg_event_cnt + stg_undo_cnt) AS diff,
  CASE
    WHEN raw_cnt - (stg_event_cnt + stg_undo_cnt) = 0 THEN 'PASS'
    ELSE 'FAIL — 누락 의심'
  END AS result
FROM (
  SELECT
    (SELECT COUNT(*) FROM ${catalog}.labelit_raw.raw_labelit__workspace_command)  AS raw_cnt,
    (SELECT COUNT(*) FROM ${catalog}.labelit_stg.stg_labelit__events)             AS stg_event_cnt,
    (SELECT COUNT(*) FROM ${catalog}.labelit_stg.stg_labelit__undo_history)       AS stg_undo_cnt
);


-- ─────────────────────────────────────────────
-- [C2] changes EXPLODE 완전성
--
-- 검증 대상: stg_events.params 의 updateCount/selectedCount vs stg_event_changes 실제 건수
-- 검증 방법: 이벤트별 params 기대 건수와 EXPLODE 결과 건수 비교
-- 판정 기준: 0행 = PASS / 반환 행 = changes 배열 원소 누락 이벤트 목록
--
-- 주의:
--   - params.updateCount (transform) / params.selectedCount (select) 기준
--   - params 가 없거나 구조가 다른 경우 expected_change_cnt = NULL 로 처리 (검증 제외)
-- ─────────────────────────────────────────────
SELECT
  e.event_id,
  e.event_type,
  COALESCE(
    CAST(get_json_object(e.params, '$.updateCount')   AS INT),
    CAST(get_json_object(e.params, '$.selectedCount') AS INT)
  )                                                   AS expected_change_cnt,
  COUNT(c.change_idx)                                 AS actual_change_cnt
FROM ${catalog}.labelit_stg.stg_labelit__events e
LEFT JOIN ${catalog}.labelit_stg.stg_labelit__event_changes c
  ON e.event_id = c.event_id
WHERE e.changes_raw IS NOT NULL
  AND e.changes_raw != '[]'
GROUP BY e.event_id, e.event_type, e.params
HAVING
  COALESCE(
    CAST(get_json_object(e.params, '$.updateCount')   AS INT),
    CAST(get_json_object(e.params, '$.selectedCount') AS INT)
  ) IS NOT NULL
  AND COALESCE(
    CAST(get_json_object(e.params, '$.updateCount')   AS INT),
    CAST(get_json_object(e.params, '$.selectedCount') AS INT)
  ) != COUNT(c.change_idx)
ORDER BY e.event_id;


-- ─────────────────────────────────────────────
-- [C3] 이벤트 스트림 갭 탐지 (정보성)
--
-- 검증 대상: session 내 연속 이벤트 간 시간 간격
-- 검증 방법: LAG window → event_time 기준 session 내 이전 이벤트와의 간격 계산
-- 판정 기준: PASS/FAIL 없음 — 30분 초과 갭 구간 목록 반환 (임계값 조정 가능)
--
-- 활용:
--   - 스트리밍 파이프라인 장애 여부 확인
--   - 라벨러 작업 중단 구간 파악
--
-- 임계값: 기본 30분 (1800초) — 비즈니스 기준에 맞게 조정
-- ─────────────────────────────────────────────
SELECT
  session_id,
  task_id,
  event_id,
  event_type,
  event_time,
  prev_event_time,
  ROUND((UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(prev_event_time)) / 60, 1) AS gap_minutes
FROM (
  SELECT
    session_id,
    task_id,
    event_id,
    event_type,
    event_time,
    LAG(event_time) OVER (
      PARTITION BY session_id
      ORDER BY event_time
    ) AS prev_event_time
  FROM ${catalog}.labelit_stg.stg_labelit__events
)
WHERE prev_event_time IS NOT NULL
  AND (UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(prev_event_time)) > 1800
ORDER BY gap_minutes DESC;


-- ─────────────────────────────────────────────
-- [C4] undo 시간 순서 정합성
--
-- 검증 대상: undo 이벤트의 event_time vs 취소 대상 이벤트의 event_time
-- 검증 방법: undo_time < reverted_event_time 인 케이스 탐지
-- 판정 기준: 0행 = PASS / 반환 행 = 시간 역전 이상 케이스
--
-- 예상 원인 (실패 시):
--   - 클라이언트 시계 오차 (event_time 기준이므로 발생 가능)
--   - 배치 전송 지연으로 인한 타임스탬프 역전
--   → 발견 시 occurred_at(서버 수신 시각)으로 재검증 권장
-- ─────────────────────────────────────────────
SELECT
  u.event_id                                                   AS undo_event_id,
  u.session_id,
  u.event_time                                                 AS undo_time,
  e.event_id                                                   AS reverted_event_id,
  e.event_type                                                 AS reverted_event_type,
  e.event_time                                                 AS reverted_event_time,
  ROUND(UNIX_TIMESTAMP(e.event_time) - UNIX_TIMESTAMP(u.event_time), 3) AS gap_sec
FROM ${catalog}.labelit_stg.stg_labelit__undo_history u
JOIN ${catalog}.labelit_stg.stg_labelit__events e
  ON u.reverted_event_id = e.event_id
WHERE u.event_time < e.event_time    -- undo 가 원본보다 먼저 발생 → 이상
ORDER BY gap_sec ASC;


-- ─────────────────────────────────────────────
-- [C4-B] undo 시간 순서 정합성 (occurred_at 기준 재검증)
--
-- 검증 대상: undo 이벤트의 occurred_at vs 취소 대상 이벤트의 occurred_at
-- 검증 방법: undo_occurred_at < reverted_occurred_at 인 케이스 탐지
-- 판정 기준: 0행 = PASS / 반환 행 = 서버 수신 시각 기준으로도 역전 발생 (더 심각한 이상)
--
-- C4(event_time 기준)에서 역전이 발견된 경우 이 쿼리로 재검증:
--   - C4-B 도 역전 → 클라이언트 버그 또는 upstream 문제 (조사 필요)
--   - C4-B 는 정상 → 클라이언트 시계 오차만으로 설명 가능 (일반적으로 허용)
-- ─────────────────────────────────────────────
SELECT
  u.event_id                                                   AS undo_event_id,
  u.session_id,
  u.occurred_at                                                AS undo_occurred_at,
  e.event_id                                                   AS reverted_event_id,
  e.event_type                                                 AS reverted_event_type,
  e.occurred_at                                                AS reverted_occurred_at,
  ROUND(UNIX_TIMESTAMP(e.occurred_at) - UNIX_TIMESTAMP(u.occurred_at), 3) AS gap_sec
FROM ${catalog}.labelit_stg.stg_labelit__undo_history u
JOIN ${catalog}.labelit_stg.stg_labelit__events e
  ON u.reverted_event_id = e.event_id
WHERE u.occurred_at < e.occurred_at    -- 서버 수신 시각 기준 역전 → 더 심각한 이상
ORDER BY gap_sec ASC;


-- ─────────────────────────────────────────────
-- [C5] 세션 내 커맨드 시퀀스 정합성
--
-- 검증 대상: session 내 transform 이전에 select 가 존재하는지
-- 검증 방법: session 기준 윈도우에서 transform 직전까지의 최근 select 시각 확인
-- 판정 기준: 0행 = PASS / 반환 행 = 선행 select 없는 transform (비즈니스 룰 확인 필요)
--
-- 주의:
--   - 세션 시작 직후 첫 번째 이벤트가 transform 인 경우 정상일 수 있음
--     (페이지 새로고침 후 오브젝트가 이미 선택된 상태)
--   - 비즈니스 팀과 이 케이스가 예외인지 확인 후 판정 기준 확정 필요
-- ─────────────────────────────────────────────
WITH session_seq AS (
  SELECT
    session_id,
    task_id,
    event_id,
    event_time,
    event_category,
    MAX(CASE WHEN event_category = 'select' THEN event_time END)
      OVER (
        PARTITION BY session_id
        ORDER BY event_time
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
      )                                                        AS last_select_time
  FROM ${catalog}.labelit_stg.stg_labelit__events
)
SELECT
  session_id,
  task_id,
  event_id,
  event_time,
  '선행 select 없는 transform' AS issue
FROM session_seq
WHERE event_category = 'transform'
  AND last_select_time IS NULL
ORDER BY session_id, event_time;


-- ─────────────────────────────────────────────
-- [완전성 검증 요약]
-- ─────────────────────────────────────────────
SELECT 'C1: Raw-Staging 건수 불일치' AS scenario,
  CASE WHEN diff = 0 THEN 0 ELSE 1 END AS fail_count
FROM (
  SELECT
    (SELECT COUNT(*) FROM ${catalog}.labelit_raw.raw_labelit__workspace_command)
    - (SELECT COUNT(*) FROM ${catalog}.labelit_stg.stg_labelit__events)
    - (SELECT COUNT(*) FROM ${catalog}.labelit_stg.stg_labelit__undo_history) AS diff
)

UNION ALL

SELECT 'C2: changes EXPLODE 불일치' AS scenario, COUNT(*) AS fail_count
FROM (
  SELECT e.event_id
  FROM ${catalog}.labelit_stg.stg_labelit__events e
  LEFT JOIN ${catalog}.labelit_stg.stg_labelit__event_changes c ON e.event_id = c.event_id
  WHERE e.changes_raw IS NOT NULL AND e.changes_raw != '[]'
  GROUP BY e.event_id, e.params
  HAVING COALESCE(
    CAST(get_json_object(e.params,'$.updateCount') AS INT),
    CAST(get_json_object(e.params,'$.selectedCount') AS INT)
  ) IS NOT NULL
  AND COALESCE(
    CAST(get_json_object(e.params,'$.updateCount') AS INT),
    CAST(get_json_object(e.params,'$.selectedCount') AS INT)
  ) != COUNT(c.change_idx)
)

UNION ALL

SELECT 'C3: 스트림 갭 탐지 (30분+)' AS scenario, COUNT(*) AS fail_count
FROM (
  SELECT event_id FROM (
    SELECT event_id, event_time,
      LAG(event_time) OVER (PARTITION BY session_id ORDER BY event_time) AS prev_time
    FROM ${catalog}.labelit_stg.stg_labelit__events
  ) WHERE prev_time IS NOT NULL
    AND (UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(prev_time)) > 1800
)

UNION ALL

SELECT 'C4: undo 시간 역전' AS scenario, COUNT(*) AS fail_count
FROM (
  SELECT u.event_id
  FROM ${catalog}.labelit_stg.stg_labelit__undo_history u
  JOIN ${catalog}.labelit_stg.stg_labelit__events e ON u.reverted_event_id = e.event_id
  WHERE u.event_time < e.event_time
)

UNION ALL

SELECT 'C4-B: undo 시간 역전 (occurred_at 기준)' AS scenario, COUNT(*) AS fail_count
FROM (
  SELECT u.event_id
  FROM ${catalog}.labelit_stg.stg_labelit__undo_history u
  JOIN ${catalog}.labelit_stg.stg_labelit__events e ON u.reverted_event_id = e.event_id
  WHERE u.occurred_at < e.occurred_at
)

UNION ALL

SELECT 'C5: 선행 select 없는 transform' AS scenario, COUNT(*) AS fail_count
FROM (
  WITH s AS (
    SELECT session_id, event_id, event_time, event_category,
      MAX(CASE WHEN event_category='select' THEN event_time END)
        OVER (PARTITION BY session_id ORDER BY event_time
              ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS last_select_time
    FROM ${catalog}.labelit_stg.stg_labelit__events
  )
  SELECT event_id FROM s
  WHERE event_category = 'transform' AND last_select_time IS NULL
)

ORDER BY scenario;
-- C3 는 정보성 — fail_count > 0 이어도 비즈니스 판단 필요
-- C1·C2·C4·C5 는 fail_count = 0 이어야 PASS
