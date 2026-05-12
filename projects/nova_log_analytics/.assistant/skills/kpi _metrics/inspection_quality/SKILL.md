# Inspection Quality Metrics Skill

검수 품질 지표(검수 반려율, First Pass Yield, 다중 반려 분석) 산출을 위한 가이드.

## 트리거 키워드

"검수 반려율", "FPY", "First Pass Yield", "inspection reject", "반려 사유", "다중 반려", "품질 지표", "rejection rate" 중 하나라도 포함되면 이 스킬을 로드할 것.

---

## 1. 데이터 소스

> **실제 SQL 소스**: 운영 SQL(`.sql/inspection_quality__monthly_fpy.sql` / `.sql/inspection_quality__multi_reject_detail.sql`)은 transitionHistory를 직접 파싱하지 않고 staging 테이블 `analytics.stg_task_transition_events`를 소스로 사용한다.
> staging 갱신 SQL: `.sql/stg__task_transition_events.sql` (일 OVERWRITE)

| 항목 | 값 |
| --- | --- |
| 운영 소스 (reject 이벤트) | `analytics.stg_task_transition_events` (Delta, partitioned by `event_week`) |
| 운영 소스 (task 메타) | `sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_tasks` — `deliveryId` / `updatedAt` / `name` 조회용 |
| 보조 테이블 | `sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_assignments` (assignment name 조회) |
| raw 컬럼 (참조) | `_id` (PK), `_raw` (JSON), `_op`, `_ingested_at` (timestamp), `_is_deleted` (boolean) |

### 1.0 staging 컬럼 (`stg_task_transition_events`)

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `task_id` | STRING | gen2_tasks._id |
| `company_id` | STRING | gen2_tasks._raw.companyId |
| `policy_id` | STRING | gen2_tasks._raw.policyId |
| `from_state` | STRING | transitionHistory[].fromState |
| `to_state` | STRING | transitionHistory[].toState |
| `trigger` | STRING | transitionHistory[].trigger |
| `action_by` | STRING | transitionHistory[].actionBy |
| `action_at` | TIMESTAMP | transitionHistory[].actionAt (UTC) |
| `reason` | STRING | transitionHistory[].reason (반려 사유 등) |
| `event_week` | DATE | DATE_TRUNC('WEEK', action_at KST) — 파티션 키 |

> staging은 transitionHistory 전체 flatten 결과이므로 `from_state = 'inspection' AND trigger = 'reject'` 단순 필터로 reject 이벤트를 추출할 수 있다. LATERAL VIEW explode + from_json 재처리 불필요.

### 1.1 raw `_raw` JSON 주요 필드 (task 메타 참조용)

| 필드 | 설명 |
| --- | --- |
| `$.name` | Task 이름 (e.g., MV2_LD-001) |
| `$.assignmentId` | Assignment ObjectId |
| `$.deliveryId` | Delivery ObjectId (inspection 진입 시 배정) |
| `$.currentStageKey` | 현재 stage (labeling, review, inspection, final_qa, submit, start) |
| `$.currentState` | 현재 state (labeling, review, inspection, completed 등) |
| `$.updatedAt` | Task 최종 수정 시점 (ISO 8601) |
| `$.createdAt` | Task 생성 시점 |
| `$.lastTransitionAt` | 마지막 전이 시점 |
| `$.transitionHistory` | 전이 이력 JSON 배열 |
| `$.companyId` | 회사 ObjectId |
| `$.policyId` | Annotation policy ObjectId |

### 1.2 transitionHistory 스키마 (staging 적재 직전 구조 참조)

```
array<struct<
  fromState: string,
  toState: string,
  trigger: string,
  actionBy: string,
  actionAt: string,
  reason: string,
  metadata: map<string, string>
>>
```

**from_json 파싱 패턴** (staging SQL `stg__task_transition_events.sql` 내부에서만 사용 — 운영 KPI SQL은 staging 컬럼 직접 사용):
```sql
from_json(
  get_json_object(`_raw`, '$.transitionHistory'),
  'array<struct<fromState:string,toState:string,trigger:string,actionBy:string,actionAt:string,reason:string,metadata:map<string,string>>>'
)
```

> 주의: 스키마를 **문자열 리터럴** (작은따옴표)로 전달해야 함. 타입 표현식 `ARRAY<STRUCT<...>>`은 중첩 `>` 파싱 오류 발생.

### 1.3 주요 trigger 값

| trigger | 의미 |
| --- | --- |
| auto | 시스템 자동 전이 (생성 시) |
| start | 작업 시작 |
| submit | 작업 제출 (다음 단계로) |
| reject | 반려 (이전 단계로) |
| reassign | 재배정 (동일 단계 내 작업자 변경) |

### 1.4 주요 stage 흐름

```
ready → waiting_labeling → labeling → waiting_review → review
→ waiting_inspection → inspection → waiting_final_qa → final_qa → completed
```

---

## 2. 핵심 비즈니스 규칙

### 2.1 모집단 정의 (Delivered Tasks)

```sql
-- deliveryId IS NOT NULL = inspection 단계 진입 완료 task
-- inspection/final_qa 단계: 100% deliveryId 보유
-- labeling/review/start 단계: 0% deliveryId 보유
WHERE get_json_object(`_raw`, '$.deliveryId') IS NOT NULL
```

> `deliveryId`는 납품 승인 이후가 아니라 **inspection 단계 진입 시점**에 배정됨.
> `currentStageKey`는 시점에 따라 변하므로 모집단 기준으로 부적합.

### 2.2 월 그룹핑

```sql
DATE_FORMAT(TO_TIMESTAMP(get_json_object(`_raw`, '$.updatedAt')), 'yy-MM') AS deliver_month
```

> `updatedAt`은 re-submit 시 갱신되어 월 이동 가능성 존재.

### 2.3 CDC 중복 제거 (raw gen2_tasks 참조 시에만)

```sql
ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
-- WHERE rn = 1
```

- `gen2_tasks`는 CDC 방식 수집 → 동일 `_id` 복수 버전 존재 가능. 운영 SQL에서 `deliveryId`/`updatedAt`/`name` 조회 시 dedup CTE 필수.
- `stg_task_transition_events`는 **staging 적재 단계에서 이미 dedup 완료** (raw_labelit__gen2_tasks latest 버전 기준 flatten) → KPI SQL에서 별도 dedup 불필요.

### 2.4 Inspection Reject 조건 (staging 기반)

```sql
WHERE from_state = 'inspection' AND trigger = 'reject'
```

- Review reject (`from_state = 'review'`)는 **제외**
- Inspection reject만 품질 지표 대상
- staging 스키마는 snake_case (`from_state`, `to_state`) — raw `_raw` JSON의 camelCase (`fromState`, `toState`)와 구분

---

## 3. 지표 정의

| 지표 | 산출식 |
| --- | --- |
| 검수 반려율 (%) | `rejected_count / total_inspected * 100` |
| First Pass Yield (%) | `100 - 검수 반려율 (%)` |
| 다중 반려 Task | inspection reject >= 2회인 task |

---

## 4. SQL 템플릿

### 4.1 월별 반려율 & First Pass Yield (staging 기반)

```sql
-- inspection_quality__monthly_fpy.sql
-- target_month: 빈 값이면 전체 월 산출, 값 지정 시 해당 월만 갱신 (형식: yy-MM)
CREATE WIDGET TEXT target_month DEFAULT "";

INSERT INTO analytics.inspection_quality_monthly_fpy
REPLACE WHERE (LENGTH('${target_month}') = 0 OR deliver_month = '${target_month}')
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
    AND (
      LENGTH('${target_month}') = 0
      OR DATE_FORMAT(TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt')), 'yy-MM') = '${target_month}'
    )
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
  SUM(CASE WHEN r.inspection_reject_count > 0 THEN 1 ELSE 0 END)       AS rejected_count,
  ROUND(
    SUM(CASE WHEN r.inspection_reject_count > 0 THEN 1 ELSE 0 END)
    / COUNT(*) * 100, 2
  )                                                                    AS rejection_rate_pct,
  ROUND(
    100 - SUM(CASE WHEN r.inspection_reject_count > 0 THEN 1 ELSE 0 END)
          / COUNT(*) * 100, 2
  )                                                                    AS first_pass_yield_pct,
  FLATTEN(COLLECT_SET(r.reject_reasons))                               AS distinct_reasons
FROM delivered_tasks d
LEFT JOIN reject_stats r ON d.task_id = r.task_id
GROUP BY d.deliver_month
ORDER BY d.deliver_month;
```

> `delivered_tasks` CTE는 모집단(deliveryId IS NOT NULL)을 raw gen2_tasks에서 추출 — `deliveryId`/`updatedAt`은 staging에 없는 메타 필드이므로 raw 직접 조회 필요. `reject_stats`는 staging에서 단순 GROUP BY로 산출.

### 4.2 다중 반려 Task 상세 (staging 기반)

```sql
-- inspection_quality__multi_reject_detail.sql
CREATE WIDGET TEXT target_month DEFAULT "";

INSERT INTO analytics.inspection_quality_multi_reject
REPLACE WHERE (LENGTH('${target_month}') = 0 OR deliver_month = '${target_month}')
WITH delivered_tasks AS (
  SELECT
    t.`_id`                                                              AS task_id,
    get_json_object(t.`_raw`, '$.name')                                  AS task_name,
    get_json_object(t.`_raw`, '$.assignmentId')                          AS assignment_id,
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
    AND (
      LENGTH('${target_month}') = 0
      OR DATE_FORMAT(TO_TIMESTAMP(get_json_object(t.`_raw`, '$.updatedAt')), 'yy-MM') = '${target_month}'
    )
),
inspection_rejects AS (
  SELECT
    task_id,
    DATE_FORMAT(action_at, 'yyyy-MM-dd HH:mm:ss')        AS rejected_at,
    action_by                                            AS rejected_by,
    reason                                               AS reject_reason
  FROM analytics.stg_task_transition_events
  WHERE from_state = 'inspection'
    AND trigger    = 'reject'
)
SELECT
  d.task_id,
  d.task_name,
  d.assignment_id,
  d.deliver_month,
  COUNT(*)                                                             AS reject_count,
  COLLECT_LIST(STRUCT(r.rejected_at, r.rejected_by, r.reject_reason)) AS reject_details
FROM delivered_tasks d
INNER JOIN inspection_rejects r ON d.task_id = r.task_id
GROUP BY d.task_id, d.task_name, d.assignment_id, d.deliver_month
HAVING COUNT(*) >= 2
ORDER BY d.deliver_month, reject_count DESC;
```

> `rejected_at`은 staging의 `action_at TIMESTAMP`를 표시용 STRING (`yyyy-MM-dd HH:mm:ss`)으로 포맷해 DDL `STRUCT<rejected_at STRING, ...>` 스키마와 정합 유지.

### 4.3 특정 Assignment의 Task 전이 이력 조회

```sql
-- assignment name으로 assignmentId 조회
SELECT a.`_id`, get_json_object(a.`_raw`, '$.name') AS assignment_name
FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_assignments` AS a
WHERE get_json_object(a.`_raw`, '$.name') LIKE '%검색할_이름%'
  AND a.`_is_deleted` = false
```

### 4.4 Reason 정규화

```sql
-- 대소문자/공백 중복 통합
LOWER(TRIM(trans.reason)) AS normalized_reason
```

알려진 중복:
- `Quality issue` / `Quality Issue` / `quality issue`
- `재작업 요청` / `재작업 요청 ` (trailing space)

---

## 5. 검증된 결과 (참고 기준값)

| deliver_month | total_inspected | rejected_count | rejection_rate | FPY |
| --- | --- | --- | --- | --- |
| 26-04 | 312 | 96 | 30.77% | 69.23% |
| 26-05 | 74 | 1 | 1.35% | 98.65% |

다중 반려: 26건 (모두 26-04), 최대 3회 반려.

---

## 6. 관련 노트북

- **Inspection Reject Rate - Monthly FPY Test** (ID: 3293698563438951)
  - Cell 2: 월별 반려율 & FPY 산출
  - Cell 3: 다중 반려 Task 상세

---

## 7. 주의사항

1. `from_json` 스키마는 반드시 **문자열 리터럴**로 전달 (staging SQL 내부에서만 사용; 운영 KPI SQL은 staging 컬럼 직접 사용으로 회피)
2. CDC 중복 제거: raw `gen2_tasks` 참조 시 `ROW_NUMBER` 패턴 적용 (staging은 적재 단계에서 이미 dedup)
3. `currentStageKey`는 시점별 변동 → 모집단 기준 부적합, `deliveryId IS NOT NULL` 사용
4. `object_id`는 task 간 중복 가능 → 반드시 `task_id`와 함께 사용
5. `reason`에 빈 문자열 존재 → staging 적재 단계에서 `NULLIF(TRIM(reason), '')` 처리 완료 (KPI SQL에서는 NULL/값 분기만 처리)
6. **`updatedAt` KST 미변환**: 월 단위 집계라 경계일 영향 미미하나, 타 KPI와 규약 통일 시 `CONVERT_TIMEZONE('UTC', 'Asia/Seoul', TO_TIMESTAMP(...))` 적용 필요
7. **staging 의존성**: 운영 SQL 실행 전 `stg_task_transition_events`가 당월 전체 기간을 포함하도록 갱신되어 있어야 함 (§9 Initialize/Bootstrap 절차 참조)

---

## 8. Delta 테이블 스키마

> 초기 생성 DDL: `.sql/inspection_quality__ddl.sql` (2개 테이블, `columnMapping.mode = 'name'` 포함)

### 8.1 inspection_quality_monthly_fpy

```
analytics.inspection_quality_monthly_fpy
PARTITIONED BY (deliver_month)
갱신 전략: INSERT INTO ... REPLACE WHERE deliver_month (월 1회)
```

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `deliver_month` | STRING | `'yy-MM'` 형식 (예: `26-04`) — 파티션 키 |
| `total_inspected` | BIGINT | 해당 월 검수 통과 Task 수 |
| `rejected_count` | BIGINT | 1회 이상 inspection 반려된 Task 수 |
| `rejection_rate_pct` | DOUBLE | 반려율 (%) = `rejected_count / total_inspected × 100` |
| `first_pass_yield_pct` | DOUBLE | FPY (%) = `100 - rejection_rate_pct` |
| `distinct_reasons` | ARRAY\<STRING\> | 월별 반려 사유 목록 (중복 제거) |

### 8.2 inspection_quality_multi_reject

```
analytics.inspection_quality_multi_reject
PARTITIONED BY (deliver_month)
갱신 전략: INSERT INTO ... REPLACE WHERE deliver_month (월 1회)
```

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `task_id` | STRING | Task 고유 식별자 |
| `task_name` | STRING | Task 이름 |
| `assignment_id` | STRING | Assignment 식별자 |
| `deliver_month` | STRING | `'yy-MM'` 형식 — 파티션 키 |
| `reject_count` | BIGINT | 해당 Task의 inspection 반려 횟수 (≥ 2) |
| `reject_details` | ARRAY\<STRUCT\<rejected_at STRING, rejected_by STRING, reject_reason STRING\>\> | 반려 이벤트 시계열 |

---

## 9. Initialize / Bootstrap 절차

테이블 부재 상태에서 시작하는 신규 배포 흐름. staging 의존성 때문에 단계 구분 필요.

### 9.1 Phase 0: 인프라 준비 (Day 0)

1. **Staging DDL 적용**: `.sql/stg__ddl.sql` 실행 → `analytics.stg_task_transition_events` 등 3개 staging 테이블 생성
2. **KPI DDL 적용**: `.sql/inspection_quality__ddl.sql` 실행 → `analytics.inspection_quality_monthly_fpy`, `analytics.inspection_quality_multi_reject` 생성
3. **존재 확인**:
   ```sql
   SHOW TABLES IN analytics LIKE 'stg_task_transition_events';
   SHOW TABLES IN analytics LIKE 'inspection_quality_%';
   ```

### 9.2 Phase A: Staging 초기 적재 (Day 1)

```sql
-- stg__task_transition_events.sql 실행 (위젯 미설정 시 전체 기간 적재)
-- analysis_date 위젯 빈 값 또는 전체 백필 모드 실행
```

- staging은 transitionHistory 전체 flatten → 초기 1회 전체 적재 (소요: gen2_tasks 규모에 비례)
- 적재 검증:
  ```sql
  SELECT
    MIN(action_at) AS earliest_event,
    MAX(action_at) AS latest_event,
    COUNT(*)       AS total_events,
    COUNT(DISTINCT task_id) AS distinct_tasks
  FROM analytics.stg_task_transition_events;
  ```

### 9.3 Phase B: KPI 초기 산출 (Day 1)

```sql
-- target_month=""로 전체 월 산출
%sql USE CATALOG sv_nova_dev_an2_catalog;
-- inspection_quality__monthly_fpy.sql 실행 (target_month="")
-- inspection_quality__multi_reject_detail.sql 실행 (target_month="")
```

- 모든 월의 FPY/다중 반려 결과를 한 번에 산출
- 검증 (§5 기준값 대조):
  ```sql
  SELECT * FROM analytics.inspection_quality_monthly_fpy
  WHERE deliver_month IN ('26-04', '26-05')
  ORDER BY deliver_month;
  -- 기대값: 26-04 FPY 69.23%, 26-05 FPY 98.65%
  ```

### 9.4 Phase C: Steady-state (Day 2+)

- **staging**: 일 OVERWRITE 스케줄 (`.sql/stg__task_transition_events.sql`)로 매일 04:00 UTC 갱신
- **KPI 월 1회 실행**:
  - `inspection_quality__monthly_fpy.sql` (`target_month` 지정 시 해당 월만 REPLACE WHERE)
  - `inspection_quality__multi_reject_detail.sql` (동일)
- 신규 월 진입 시 전월 1회 + 신월 1회 갱신 패턴

### 9.5 의존성 다이어그램

```
[Phase 0] stg__ddl.sql            ─┐
          inspection_quality__ddl ─┤
                                   ↓
[Phase A] stg__task_transition_events.sql  (전체 백필 1회)
                                   ↓
[Phase B] inspection_quality__monthly_fpy.sql  (target_month="" 전체 산출)
          inspection_quality__multi_reject_detail.sql
                                   ↓
[Phase C] 일 staging OVERWRITE + 월 KPI REPLACE WHERE
```
