# Stage Progress Dashboard — Design

**문서 상태**: Draft  
**작성일**: 2026-05-11  
**적용 범위**: `projects/nova_log_analytics` — MV2_LD, MV2_OD, MV2_SOD, MV2_RMD, MV2_TSTLD  
**선행 문서**: `stage_transition_analysis.md`, `productivity_concept_design.md`

---

## 1. 개요

업체에 배정된 전체 Task가 파이프라인의 어느 단계에 있는지 실시간으로 확인한다. 업체별 납품 진척률과 Stage 분포를 통해 병목·지연 구간을 조기에 파악한다.

> **Stage 파이프라인 구조 및 전환 이력**: `stage_transition_analysis.md` 참조

**상태 분류 기준**:

| 분류 | 포함 상태 | 설명 |
|---|---|---|
| 진행 중 | `to_state IN ('labeling', 'review', 'inspection', 'final_qa')` | 작업자가 활성 작업 중 |
| 대기 중 | `to_state LIKE 'waiting_%'` | 다음 Stage 배정 전 |
| 완료 | `to_state = 'completed'` | 전체 파이프라인 통과 |

> **데이터 소스**: raw `transitionHistory` 대신 `stg_task_transition_events` staging table을 소스로 사용한다. 최신 상태는 Task별 `action_at` DESC 1위 레코드로 특정한다.

---

## 2. 배정 현황 개요

업체별 배정 Task의 전체 규모와 완료 현황을 집계한다.

| Metric | 산출 로직 | 소스 |
|---|---|---|
| 총 배정 Task 수 | `from_state='waiting_labeling' AND trigger='start'` 도달 Task COUNT (라벨링 착수 = 배정 확정 기준) | stg_task_transition_events |
| 현재 상태별 Task 수 | Task별 최신 `to_state` 기준 분류 | stg_task_transition_events |
| 대기 상태 Task 수 | 최신 `to_state LIKE 'waiting_%'` Task COUNT | stg_task_transition_events |
| 완료 Task 수 | `from_state='final_qa' AND to_state='completed'` 도달 Task COUNT | stg_task_transition_events |
| 납품 완료율 | 완료 Task 수 / 총 배정 Task 수 | — |

**집계 축**: 업체 × Feature × 기간(일/주/월)

---

## 3. Stage별 Task 분포 (현재 스냅샷)

현재 파이프라인에서 각 상태별 Task 수를 일 배치 기준으로 확인한다.

| 현재 상태 | 이전 전환 이벤트 | 의미 |
|---|---|---|
| `waiting_labeling` | `ready → waiting_labeling` (auto) | 라벨링 배정 전 대기 |
| `labeling` | `waiting_labeling → labeling` (start) | 라벨러 작업 중 |
| `waiting_review` | `labeling → waiting_review` (submit) 또는 reject 반려 | 리뷰어 배정 전 대기 |
| `review` | `waiting_review → review` (start) | 리뷰어 작업 중 |
| `waiting_submit` | `review → waiting_submit` (submit) | 납품 전 검수 대기 |
| `inspection` | `waiting_submit → inspection` (deliver) | 검수자 작업 중 |
| `waiting_final_qa` | `inspection → waiting_final_qa` (submit) | 최종 QA 배정 전 |
| `final_qa` | `waiting_final_qa → final_qa` (start) | 최종 QA 진행 중 |
| `completed` | `final_qa → completed` (submit) | 파이프라인 통과 |

---

## 4. 파이프라인 진척률 (누적 Funnel)

업체별로 배정 Task 대비 각 Stage 누적 도달 비율을 측정한다. 동일 Task가 복수 pass를 거쳤더라도 "도달 여부"로만 집계한다.

| Metric | 정의 | 이벤트 조건 |
|---|---|---|
| 라벨링 착수율 | 라벨링 착수 Task / 총 배정 | `from_state='waiting_labeling' AND trigger='start'` |
| 라벨링 완료율 | 라벨링 완료 Task / 총 배정 | `from_state='labeling' AND to_state='waiting_review'` |
| 납품률 | 납품 Task / 총 배정 | `from_state='waiting_submit' AND trigger='deliver'` |
| 검수 완료율 | 검수 완료 Task / 총 배정 | `from_state='inspection' AND to_state='waiting_final_qa'` |
| 최종 완료율 | 완료 Task / 총 배정 | `from_state='final_qa' AND to_state='completed'` |

---

## 5. 집계 Dimension

| 축 | 소스 | 값 |
|---|---|---|
| 업체 | `task.companyId → company.name` | CW, LTS, NexterSystems, StradVision, LTSMM |
| Feature | `task.policyId → policy.feature` | MV2_LD, MV2_OD, MV2_SOD, MV2_RMD, MV2_TSTLD |
| 기간 | `transitionHistory.actionAt` | 일 / 주 / 월 |

> **시간대 기준**: `action_at` 집계는 KST(UTC+9) 기준으로 통일. `CONVERT_TIMEZONE('UTC', 'Asia/Seoul', action_at)`

---

## 6. Task Aging 분석

대기 상태에 체류 중인 Task의 경과 시간을 집계하여 병목·지연 구간을 조기 탐지한다.

### 6.1 Aging 임계값

| 등급 | 기준 | 판정 |
|---|---|---|
| 정상 | 체류 시간 ≤ 72h | — |
| 경고 | 72h < 체류 시간 ≤ 168h (3일 초과 ~ 7일 이내) | `aging_flag = '경고'` |
| 심각 | 체류 시간 > 168h (7일 초과) | `aging_flag = '심각'` |

### 6.2 집계 Metric

| Metric | 단위 | 산출 |
|---|---|---|
| 대기 상태별 Task 수 | 건 | `current_state LIKE 'waiting_%'` GROUP BY |
| 평균 대기 시간 | hours | `AVG((CURRENT_TIMESTAMP - state_entered_at) / 3600)` |
| 최장 대기 시간 | hours | `MAX(...)` |
| Aging 등급별 Task 수 | 건 | `COUNT by aging_flag` |

**집계 축**: 업체 × Feature × `current_state` × `aging_flag`

---

## 7. Reject 재작업 현황

반려(reject) 이후 재작업 중인 Task 수를 별도 집계하여 파이프라인 내 재순환 규모를 파악한다.

### 7.1 Reject 경로

| reject 발생 위치 | 결과 상태 | 의미 |
|---|---|---|
| `review → waiting_labeling` | 현재 `waiting_labeling` 또는 `labeling` | 리뷰 반려 → 재라벨링 |
| `waiting_submit → waiting_review` | 현재 `waiting_review` 또는 `review` | 납품 전 반려 → 재리뷰 |
| `inspection → waiting_review` | 현재 `waiting_review` 또는 `review` | 검수 반려 → 재리뷰 |

### 7.2 집계 Metric

| Metric | 산출 로직 |
|---|---|
| Reject 이력 보유 Task 수 | `trigger='reject'` 이벤트가 1회 이상 존재하는 Task COUNT |
| 현재 재작업 중인 Task 수 | reject 이력 보유 + 최신 `to_state IN ('labeling', 'review', 'waiting_labeling', 'waiting_review')` |
| Reject 후 재완료율 | 최종 `completed` 도달 Task 중 reject 이력 보유 비율 |

---

## 8. SQL 스케치

### 8.1 현재 파이프라인 스냅샷 (`dashboard__pipeline_snapshot.sql`)

```sql
WITH latest_transition AS (
  SELECT
    task_id, company_id, policy_id,
    to_state                                                            AS current_state,
    action_at                                                           AS state_entered_at,
    ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY action_at DESC)   AS rn
  FROM sv_nova_dev_an2_catalog.raw.stg_task_transition_events
),
current_state AS (
  SELECT
    task_id, company_id, policy_id, current_state, state_entered_at,
    CASE
      WHEN current_state IN ('labeling','review','inspection','final_qa') THEN '진행중'
      WHEN current_state LIKE 'waiting_%'                                THEN '대기중'
      WHEN current_state = 'completed'                                   THEN '완료'
      ELSE '기타'
    END AS status_group
  FROM latest_transition
  WHERE rn = 1
)
SELECT
  cs.company_id,
  p.feature,
  cs.current_state,
  cs.status_group,
  COUNT(DISTINCT cs.task_id)                                           AS task_count,
  DATE(CONVERT_TIMEZONE('UTC', 'Asia/Seoul', CURRENT_TIMESTAMP()))    AS snapshot_date
FROM current_state cs
LEFT JOIN sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_policies p
  ON cs.policy_id = p._id
GROUP BY ALL
ORDER BY cs.company_id, p.feature, cs.current_state
```

### 8.2 파이프라인 누적 진척률 (`dashboard__pipeline_funnel.sql`)

```sql
WITH milestones AS (
  SELECT
    task_id, company_id, policy_id,
    MAX(CASE WHEN from_state='waiting_labeling' AND trigger='start'
             THEN 1 END)                                               AS labeling_started,
    MAX(CASE WHEN from_state='labeling'         AND to_state='waiting_review'
             THEN 1 END)                                               AS labeling_done,
    MAX(CASE WHEN from_state='waiting_submit'   AND trigger='deliver'
             THEN 1 END)                                               AS delivered,
    MAX(CASE WHEN from_state='inspection'       AND to_state='waiting_final_qa'
             THEN 1 END)                                               AS inspection_done,
    MAX(CASE WHEN from_state='final_qa'         AND to_state='completed'
             THEN 1 END)                                               AS completed
  FROM sv_nova_dev_an2_catalog.raw.stg_task_transition_events
  GROUP BY task_id, company_id, policy_id
)
SELECT
  m.company_id,
  p.feature,
  COUNT(DISTINCT m.task_id)                                                         AS total_tasks,
  COUNT(DISTINCT CASE WHEN m.labeling_started = 1 THEN m.task_id END)              AS labeling_started_count,
  COUNT(DISTINCT CASE WHEN m.labeling_done    = 1 THEN m.task_id END)              AS labeling_done_count,
  COUNT(DISTINCT CASE WHEN m.delivered        = 1 THEN m.task_id END)              AS delivered_count,
  COUNT(DISTINCT CASE WHEN m.inspection_done  = 1 THEN m.task_id END)              AS inspection_done_count,
  COUNT(DISTINCT CASE WHEN m.completed        = 1 THEN m.task_id END)              AS completed_count,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN m.completed = 1 THEN m.task_id END)
             / NULLIF(COUNT(DISTINCT m.task_id), 0), 1)                            AS completion_rate_pct
FROM milestones m
LEFT JOIN sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_policies p
  ON m.policy_id = p._id
GROUP BY m.company_id, p.feature
ORDER BY m.company_id, p.feature
```

### 8.3 대기 Aging 현황 (`dashboard__waiting_aging.sql`)

```sql
WITH latest_transition AS (
  SELECT
    task_id, company_id, policy_id,
    to_state                                                            AS current_state,
    action_at                                                           AS state_entered_at,
    ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY action_at DESC)   AS rn
  FROM sv_nova_dev_an2_catalog.raw.stg_task_transition_events
),
waiting_tasks AS (
  SELECT
    task_id, company_id, policy_id,
    current_state,
    state_entered_at,
    ROUND((UNIX_TIMESTAMP(CURRENT_TIMESTAMP())
           - UNIX_TIMESTAMP(state_entered_at)) / 3600.0, 1)           AS waiting_hours,
    CASE
      WHEN (UNIX_TIMESTAMP(CURRENT_TIMESTAMP())
            - UNIX_TIMESTAMP(state_entered_at)) / 3600 > 168 THEN '심각'
      WHEN (UNIX_TIMESTAMP(CURRENT_TIMESTAMP())
            - UNIX_TIMESTAMP(state_entered_at)) / 3600 >  72 THEN '경고'
      ELSE '정상'
    END                                                                AS aging_flag
  FROM latest_transition
  WHERE rn = 1
    AND current_state LIKE 'waiting_%'
)
SELECT
  wt.company_id,
  p.feature,
  wt.current_state,
  wt.aging_flag,
  COUNT(DISTINCT wt.task_id)    AS task_count,
  ROUND(AVG(wt.waiting_hours), 1) AS avg_waiting_hours,
  ROUND(MAX(wt.waiting_hours), 1) AS max_waiting_hours
FROM waiting_tasks wt
LEFT JOIN sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_policies p
  ON wt.policy_id = p._id
GROUP BY ALL
ORDER BY wt.company_id, p.feature, wt.current_state, wt.aging_flag
```

---

## 9. 갱신 주기 및 데이터 소스

| 항목 | 내용 |
|---|---|
| 소스 테이블 | `stg_task_transition_events` (일 OVERWRITE 배치 완료 후) |
| 갱신 주기 | **일 배치** — `stg__task_transition_events.sql` 완료 후 실행 |
| 실행 순서 | stg__task_transition_events → dashboard__pipeline_snapshot → dashboard__pipeline_funnel → dashboard__waiting_aging |
| 저장 방식 | 스냅샷 테이블 불필요 — 임시 조회(VIEW 또는 직접 실행) 권장. snapshot_date 컬럼으로 일자 구분 |

---

## 10. 제약사항

| 항목 | 상태 | 비고 |
|---|---|---|
| 총 배정 Task 기준 | 미결정 | 라벨링 착수(`waiting_labeling → labeling`) 기준 vs 최초 `ready → waiting_labeling` 기준 정의 필요 |
| 대기 상태 Task 중복 카운트 | 미검증 | 동일 Task가 reject 후 재진입 시 최신 `to_state`로만 집계 → 의도한 동작인지 확인 필요 |
| Reject 재작업 Task 식별 정밀도 | 미검증 | 현재 `labeling/review` 상태 + reject 이력 보유 조합으로 특정하나, reject 후 이미 재완료된 Task가 포함될 수 있음 |
| `waiting_submit` 존재 여부 | 미확인 | 일부 Feature에서 `waiting_submit → inspection` 없이 직접 `review → inspection` 전환 가능성 검토 필요 |

---

## 11. 다음 단계

| 순서 | 작업 | 산출물 |
|---|---|---|
| 1 | 총 배정 Task 기준(착수 vs ready) 데이터 검증 | 데이터 검증 노트 |
| 2 | 현재 파이프라인 스냅샷 SQL 작성 | `.sql/dashboard__pipeline_snapshot.sql` |
| 3 | 파이프라인 누적 진척률 SQL 작성 | `.sql/dashboard__pipeline_funnel.sql` |
| 4 | 대기 Aging 현황 SQL 작성 | `.sql/dashboard__waiting_aging.sql` |

---

## 12. 버전 히스토리

| 버전 | 일자 | 상태 | 주요 내용 |
|---|---|---|---|
| `v1` | 2026-05-11 | Draft | `production_volume_metric_design_v3.md`에서 Stage 진행 현황 대시보드 영역 분리 / Stage 구조 참조 일원화 (`stage_transition_analysis.md`) / 문서 영문 제목 통일 |
| `v2` | 2026-05-12 | Draft | §4 진척률 Funnel 보완 (라벨링 착수율 추가) / §6 Task Aging 분석 신규 / §7 Reject 재작업 현황 신규 / §8 SQL 스케치 3개 신규 / §9 갱신 주기 신규 / §10 제약사항 보완 / 데이터 소스를 stg_task_transition_events로 명시 |
