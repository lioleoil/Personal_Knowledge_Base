# Focus Drop — 생산성 연계 및 Reviewer 확장

> **코어 참조**: 메트릭 정의·판정 기준은 `SKILL.md` 참조  
> **배포·운영**: DDL·Bootstrap·스케줄링은 `focus_drop_deployment.md` 참조

---

## Task Idle Rollup SQL

### 7.7 Task idle rollup (생산성 연계용)

```sql
-- focus_drop__task_idle_rollup.sql
INSERT INTO analytics.focus_drop_task_idle_rollup
REPLACE WHERE analysis_date = ${analysis_date}
SELECT
  analysis_date,
  task_id,
  'labeler'                        AS role_scope,
  'labeler'                        AS role_group,
  COUNT(*)                         AS contributing_sessions,
  COUNT(DISTINCT user_id)          AS contributing_users,
  SUM(idle_gap_count)              AS idle_gap_total,
  SUM(idle_gap_duration_sec)       AS idle_gap_duration_sec
FROM analytics.focus_drop_session_metrics
WHERE analysis_date = ${analysis_date}
GROUP BY analysis_date, task_id;
```

> 생산성 SQL에서는 동일 Task가 여러 날짜에 걸쳐 진행될 수 있으므로, `focus_drop_task_idle_rollup`을 `task_id` 기준으로 다시 합산하여 `task_total_idle_sec`를 산출한 후 `deliver_actionAt - start_actionAt`에서 차감한다. 상세 산식은 §16.1 참조.

---

---

## 16. 생산성 연계 및 Reviewer 확장

### 16.1 Task 순소요시간 차감 원칙

생산성 분석에서 Task 평균 소요시간은 다음 두 값을 모두 유지한다.

| 지표 | 산식 | 의미 |
|------|------|------|
| `gross_task_hours` | `(deliver_actionAt - start_actionAt) / 3600` | 전환 이력 기준 총 경과 시간 |
| `net_task_hours` | `GREATEST(gross_task_sec - task_total_idle_sec, 0) / 3600` | Focus Drop idle 차감 후 순작업시간 |

여기서:

```sql
gross_task_sec      = UNIX_TIMESTAMP(deliver_at) - UNIX_TIMESTAMP(start_at)
task_total_idle_sec = SUM(idle_gap_duration_sec)  -- 동일 task의 복수 session / 복수 일자 합산
net_task_hours      = GREATEST(gross_task_sec - task_total_idle_sec, 0) / 3600.0
```

> `task_total_idle_sec`는 `analytics.focus_drop_task_idle_rollup`을 `task_id` 기준으로 재합산하여 만든다. 동일 Task가 여러 날짜·세션에 걸쳐 진행될 수 있으므로 반드시 누적 합산이 필요하다.

### 16.2 생산성 SQL 연계 예시

```sql
WITH task_idle AS (
  SELECT
    task_id,
    SUM(idle_gap_duration_sec) AS task_total_idle_sec
  FROM analytics.focus_drop_task_idle_rollup
  WHERE role_scope = 'all_roles'  -- 초기에는 'labeler' fallback 가능
  GROUP BY task_id
)
SELECT
  d.task_id,
  s.start_at,
  d.deliver_at,
  ROUND((UNIX_TIMESTAMP(d.deliver_at) - UNIX_TIMESTAMP(s.start_at)) / 3600.0, 2) AS gross_task_hours,
  ROUND(COALESCE(i.task_total_idle_sec, 0) / 3600.0, 2) AS idle_hours,
  ROUND(
    GREATEST(
      UNIX_TIMESTAMP(d.deliver_at) - UNIX_TIMESTAMP(s.start_at) - COALESCE(i.task_total_idle_sec, 0),
      0
    ) / 3600.0,
    2
  ) AS net_task_hours
FROM deliver_events d
JOIN start_events s ON d.task_id = s.task_id
LEFT JOIN task_idle i ON d.task_id = i.task_id;
```

### 16.3 Reviewer 확장 모드

생산성 지표의 분모는 **Labeler + Reviewer 합산**이므로, Focus Drop idle도 최종적으로는 Reviewer까지 확장하는 것이 정합성이 높다.

권장 확장 방식은 **role 필터 제거**가 아니라, **role을 dimension으로 유지한 통합 파이프라인**이다.

| 모드 | 설명 | 사용처 |
|------|------|------|
| `labeler_only` | 기존 KPI 기준선 유지 | Focus Drop KPI 본체 |
| `reviewer_only` | Reviewer 패턴 단독 분석 | Reviewer 운영 진단 |
| `all_roles` | Labeler + Reviewer 통합 rollup | 생산성 순소요시간 차감 |

### 16.4 통합 role 파이프라인 SQL 패턴

```sql
-- 공통 소스 CTE 예시: role 차원을 보존
WITH worker_commands AS (
  SELECT
    c._raw:userId::STRING       AS user_id,
    c._raw:sessionId::STRING    AS session_id,
    c._raw:taskId::STRING       AS task_id,
    c._raw:createdAt::TIMESTAMP AS event_time,
    LOWER(a._raw:role::STRING)  AS role_group
  FROM sv_nova_dev_an2_catalog.raw.raw_labelit__workspace_command c
  INNER JOIN sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_tasks t
    ON c._raw:taskId::STRING = t._id
  INNER JOIN sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_assignments a
    ON t._raw:assignmentId::STRING = a._id
  WHERE c._is_deleted = false
    AND LOWER(a._raw:role::STRING) IN ('labeler', 'reviewer')
    AND (
      ${role_scope} = 'all_roles'
      OR LOWER(a._raw:role::STRING) = ${role_scope}
    )
)
```

이 패턴을 사용하면 `focus_drop_task_idle_rollup` 적재 시 다음 두 컬럼을 유지할 수 있다.

- `role_scope`: 실행 모드 (`labeler`, `reviewer`, `all_roles`)
- `role_group`: 실제 작업 역할 (`labeler`, `reviewer`)

### 16.5 운영 권고안

1. **즉시 적용**: Labeler 파이프라인에 `idle_gap_duration_sec`와 `task_idle_rollup` 추가
2. **중간 단계**: 생산성 SQL에서 `labeler` idle 차감 버전과 `gross_task_hours`를 병행 보고
3. **최종 단계**: Reviewer 확장 후 `role_scope = 'all_roles'` 기준을 기본값으로 전환
4. **대시보드 표기**: `gross_task_hours`, `idle_hours`, `net_task_hours` 3개를 동시에 노출하여 해석 가능성 확보
5. **Phase A/B 기간 주의**: 부트스트랩 7일 동안은 gap 기준선 미생성으로 `idle_gap_duration_sec = 0`이 될 수 있음 → 이 기간 `net_task_hours = gross_task_hours` 전체. 첫 주 생산성 리포트에 "idle 차감 미적용(부트스트랩 기간)" 주석 권고

### 16.6 해석상 주의점

- idle 차감은 **근사치**이며, 검토/인지/시야 탐색 같은 비명령 시간 전체를 완전하게 설명하지 않는다
- idle 차감 후 `net_task_hours`가 0에 가까운 Task는 로그 수집 이상 또는 세션 분절 이슈를 우선 점검해야 한다
- Reviewer 확장 시 Reviewer의 작업 리듬은 Labeler와 다를 수 있으므로, KPI 기준선과 생산성 차감 로직을 동일 테이블에 혼합하지 않는 것이 안전하다
