# 검수 품질 지표 산출 기획문서
## Inspection Reject Rate & Monthly First Pass Yield — Labelit Gen2

**문서 상태**: Released (v1.1)  
**작성일**: 2026-05-12  
**데이터 소스**: `analytics.stg_task_transition_events` (reject 이벤트) + `sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_tasks` (task 메타)  
**관련 SKILL**: `.assistant/skills/kpi_metrics/inspection_quality/SKILL.md`  
**목적**: Labelit Gen2 작업 파이프라인의 inspection 단계 반려율과 FPY를 월별로 산출하여 품질 추이를 정량 모니터링

---

## 1. 개요

Labelit Gen2 작업 파이프라인에서 **inspection 단계의 reject**를 대상으로 월별 검수 반려율과 First Pass Yield를 산출한다. 작업 품질의 정량적 추이를 확인하고, 다중 반려 task의 패턴을 분석하여 품질 개선 포인트를 식별하는 것이 핵심 목적이다.

---

## 2. 주요 지표 정의

| 지표 | 정의 | 산출식 |
|---|---|---|
| **검수 반려율 (%)** | 월별 대상 task 중 inspection reject 이력이 1회 이상인 task 비율 | `rejected_count / total_inspected × 100` |
| **First Pass Yield (%)** | 최초 inspection 검수에서 통과한 task 비율 | `100 − 검수 반려율 (%)` |
| **Reject Reasons** | 해당 월 inspection reject의 고유 반려 사유 목록 | `DISTINCT reason WHERE fromState='inspection' AND trigger='reject'` |
| **다중 반려 Task** | 동일 task에서 inspection reject 2회 이상 발생 | task별 reject 횟수, 사유, 작업자 정보 |

---

## 3. 데이터 정의 및 필터 조건

### 3.1 대상 모집단 (Delivered Tasks)

| 항목 | 조건 | 비고 |
|---|---|---|
| 모집단 필터 | `deliveryId IS NOT NULL` | inspection 단계 진입 시점에 배정됨 |
| 월 그룹핑 기준 | `updatedAt`의 `YY-MM` | task 최종 수정 시점 기준 |
| CDC 중복 제거 | `_id` 기준 `_ingested_at DESC` 최신 1건 | ROW_NUMBER 활용 |
| 삭제 제외 | `_is_deleted = false` | soft delete 필터 |

> **핵심 확인사항**: `deliveryId`는 납품 승인 이후가 아니라 **inspection 단계 진입 시점**에 배정된다.  
> - inspection/final_qa 단계 task: 100% deliveryId 보유  
> - 이전 단계(labeling/review/start): deliveryId = 0%  
> 따라서 `deliveryId IS NOT NULL` ≡ "inspection 진입 이력 존재" (동일 모집단, 더 효율적인 필터)

### 3.2 Inspection Reject 판별 기준

`transitionHistory` 배열 내 아래 조건을 **모두 충족**하는 전이:

- `fromState = 'inspection'`
- `trigger = 'reject'`

> Review reject (`fromState = 'review'`)는 **대상에서 제외**.

### 3.3 다중 반려 Task 정의

- 동일 task 내 inspection reject 전이가 **2회 이상** 발생한 건
- 제공 정보: task_id, task_name, assignment_id, reject 횟수, 각 reject 시점/사유/수행자

---

## 4. SQL 설계

### 4.1 월별 반려율 & First Pass Yield

```sql
-- 운영 SQL: staging 기반 (LATERAL VIEW explode 불필요)
-- 모집단: deliveryId IS NOT NULL (= inspection 단계 진입 task) — raw gen2_tasks에서 추출
-- Reject 이벤트: stg_task_transition_events에서 단순 필터
-- Policy §1.3: NULLIF 적용
WITH delivered_tasks AS (
  SELECT
    t.`_id`                                                              AS task_id,
    DATE_FORMAT(
      TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt')), 'yy-MM'
    )                                                                    AS deliver_month
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_tasks`
    WHERE `_is_deleted` = false
  ) t
  WHERE t.rn = 1
    AND get_json_object(t.`_raw`, '$.deliveryId') IS NOT NULL
),
reject_stats AS (
  SELECT
    task_id,
    COUNT(*)            AS inspection_reject_count,
    COLLECT_SET(reason) AS reject_reasons
  FROM analytics.stg_task_transition_events
  WHERE from_state = 'inspection'
    AND trigger    = 'reject'
  GROUP BY task_id
)
SELECT
  d.deliver_month,
  COUNT(*)                                                             AS total_inspected,
  SUM(CASE WHEN r.inspection_reject_count > 0 THEN 1 ELSE 0 END)     AS rejected_count,
  ROUND(
    SUM(CASE WHEN r.inspection_reject_count > 0 THEN 1 ELSE 0 END)
    / NULLIF(COUNT(*), 0) * 100, 2
  )                                                                    AS rejection_rate_pct,
  ROUND(
    100 - SUM(CASE WHEN r.inspection_reject_count > 0 THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0) * 100, 2
  )                                                                    AS first_pass_yield_pct,
  FLATTEN(COLLECT_SET(r.reject_reasons))                               AS distinct_reasons
FROM delivered_tasks d
LEFT JOIN reject_stats r ON d.task_id = r.task_id
GROUP BY d.deliver_month
ORDER BY d.deliver_month
```

> **설계 변경 (v1.1)**: `stg_task_transition_events`를 사용하여 `LATERAL VIEW explode + from_json` 재처리가 불필요해짐. 모집단(`deliveryId`, `updatedAt`)은 staging에 없는 메타 필드이므로 raw 직접 조회 유지.

### 4.2 다중 반려 Task 상세

```sql
-- 다중 반려 Task 상세: staging 기반 (inspection reject 2회 이상)
WITH delivered_tasks AS (
  SELECT
    t.`_id`                                        AS task_id,
    get_json_object(t.`_raw`, '$.name')            AS task_name,
    get_json_object(t.`_raw`, '$.assignmentId')    AS assignment_id,
    DATE_FORMAT(
      TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt')), 'yy-MM'
    )                                              AS deliver_month
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_tasks`
    WHERE `_is_deleted` = false
  ) t
  WHERE t.rn = 1
    AND get_json_object(t.`_raw`, '$.deliveryId') IS NOT NULL
),
multi_reject AS (
  SELECT
    e.task_id,
    e.action_by   AS rejected_by,
    e.action_at   AS rejected_at,
    NULLIF(TRIM(e.reason), '') AS reject_reason
  FROM analytics.stg_task_transition_events e
  WHERE e.from_state = 'inspection'
    AND e.trigger    = 'reject'
)
SELECT
  d.task_id, d.task_name, d.assignment_id, d.deliver_month,
  COUNT(*) AS reject_count,
  COLLECT_LIST(STRUCT(m.rejected_at, m.rejected_by, m.reject_reason)) AS reject_details
FROM delivered_tasks d
JOIN multi_reject m ON d.task_id = m.task_id
GROUP BY d.task_id, d.task_name, d.assignment_id, d.deliver_month
HAVING COUNT(*) >= 2
ORDER BY d.deliver_month, reject_count DESC
```

---

## 5. 대시보드 위젯 구성

| 위젯 | 시각화 유형 | 설명 |
|---|---|---|
| 월별 FPY 추이 | Line Chart | Y축: FPY(%), X축: YY-MM |
| 월별 검수 반려율 | Stacked Bar | 반려/통과 건수 비교 |
| 반려 사유 분포 | Table | DISTINCT reason + 빈도 (정규화 적용) |
| 다중 반려 Task 목록 | Detail Table | task_id, name, reject 횟수, 각 시점/사유/수행자 |
| KPI 카드 | Counter | 최근 월 FPY, 반려율, 다중반려 건수 |

---

## 6. 고려사항

| 항목 | 내용 |
|---|---|
| Reject 범위 | inspection reject만 대상 (`fromState='inspection'`), review reject 제외 |
| reason 정규화 | `TRIM(LOWER(reason))` 적용 — 대소문자/공백 중복 통합 |
| 다중 반려 분석 | 2회 이상 반려 task는 작업자/사유 패턴 추적으로 품질 개선 포인트 도출 |
| updatedAt 기준 유의 | re-submit 시 updatedAt 갱신 → 월 이동 가능성 존재 |
| deliveryId 배정 시점 | inspection 진입 시 배정 (납품 승인 X) → 모집단 = inspection 도달 task |

---

## 7. 검증 결과 (테스트 데이터 기준)

### 7.1 월별 반려율 & FPY

| deliver_month | total_inspected | rejected_count | rejection_rate | FPY |
|---|---|---|---|---|
| 26-04 | 312 | 96 | 30.77% | 69.23% |
| 26-05 | 74 | 1 | 1.35% | **98.65%** |

### 7.2 다중 반려 Task 상세

- **총 26건**의 task에서 inspection reject 2회 이상 발생 (모두 26-04월)
- 26-05월: 다중 반려 **0건** → 품질 개선 확인

#### 최다 반려 (3회) — 6건

| task_name | assignment_id (prefix) | reject 사유 흐름 |
|---|---|---|
| MV2_LD-010 | 69ccd6b3... | 작업 진행 → Quality issue → quality issue |
| MV2_LD-003 | 69ccd54f... | 작업 재개 요청 → 재작업 요청 → 재작업 요청 |
| MV2_LD-001 | 69ccd54f... | 재작업 요청 × 3 |
| MV2_LD-004 | 69ccd54f... | 작업 재개 요청 → 재작업 요청 × 2 |
| MV2_LD-006 | 69ccd6b3... | 작업 진행 → Quality issue → quality issue |
| MV2_LD-011 | 69ccd6b3... | 작업 진행 → Quality Issue → quality issue |

#### 패턴 분석

| 패턴 | 상세 |
|---|---|
| 집중 assignment | `69ccd6b3...` — 다중 반려 26건 중 12건 집중 (46%), 특정 배치 품질 이슈 |
| 주요 수행자 | `65853a3a...` (재작업 요청/작업 진행), `65efe672...`/`65efe673...` (quality issue) |
| 사유 흐름 패턴 | 1차: 운영적 반려("작업 진행/재개 요청") → 2~3차: 품질 반려("quality issue/재작업 요청") |
| 월별 추이 | 26-04: 26건 → 26-05: 0건 (다중 반려 완전 해소) |

---

## 8. 다음 단계

| 순서 | 작업 | 담당 |
|---|---|---|
| 1 | reason 정규화 매핑 테이블 정의 | 데이터 |
| 2 | actionBy → 사용자명 매핑 (users 테이블 조인) | 데이터 |
| 3 | 대시보드 초안 작성 및 stakeholder 리뷰 | PM |
| 4 | 스케줄링 자동화 (월별 지표 갱신) | 데이터 |

---

## 9. 버전 히스토리

| 버전 | 일자 | 상태 | 주요 내용 |
|---|---|---|---|
| `v1.0` | 2026-05-08 | Released | 초판 — raw JSON 직접 파싱 기반 SQL, 월별 FPY/반려율 산출 로직 확정 |
| `v1.1` | 2026-05-12 | Released | staging 전환 반영 — `stg_task_transition_events` 기반 SQL로 교체 / `NULLIF` 적용 (Policy §1.3) / SKILL 문서와 동기화 |
