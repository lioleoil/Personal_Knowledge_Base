# Focus Drop KPI Monitoring Skill

> Labeler 작업 집중도 저하(Focus Drop)를 KPI로서 지속 모니터링하고, 생산성 산출 시 idle 시간을 차감할 수 있도록 연계하는 통합 운영 가이드

---


> **문서 분할 안내**: 본 파일은 Focus Drop 스킬의 **핵심 참조** (메트릭·판정·SQL)를 담고 있습니다.
> - 배포·운영·Bootstrap → `focus_drop_deployment.md`
> - 생산성 연계·Reviewer 확장 → `focus_drop_productivity_linkage.md`

---

## 1. 개요

### 1.1 목적

Labeler의 작업 세션에서 **작업 집중도 저하 신호**를 분포 기반으로 탐지하고, 일일 KPI로 집계하여 지속적으로 모니터링한다. 추가로, 생산성 분석 시 Focus Drop에서 판정된 idle 시간을 Task 순소요시간(net working time) 계산에 연결할 수 있도록 한다.

### 1.2 핵심 원칙

- **집중도 측정이 아닌 저하 탐지**: 심리적 몰입 상태를 측정하지 않고, 정상 분포 대비 이탈 신호를 탐지한다
- **분포 기반 percentile 체계**: 절대 임계값이 아닌 Labeler 정상군 분포에서 경계를 산출한다
- **기준선 안정성**: 판정 기준(2차 percentile)은 당일 데이터가 아닌 안정 구간(rolling window)에서 사전 산출하여 고정한다
- **반복성 중심 판정**: 개별 gap 하나가 아닌, 긴 gap의 반복 발생 패턴으로 판정한다
- **3단계 심각도 (배타적)**: light → heavy → idle 단계로 구분하며, 최고 레벨 우선 적용한다
- **생산성 연계 가능성**: idle gap의 발생 횟수뿐 아니라 지속 시간(`idle_gap_duration_sec`)을 저장하여 Task 순소요시간에서 차감 가능하도록 설계한다

### 1.3 적용 대상

- **기본 모드**: Labeler (Reviewer/Manager 제외 — KPI 기준선 보호)
- **확장 모드**: Reviewer 전용 또는 Labeler + Reviewer 통합 모드 지원 가능 (`focus_drop_productivity_linkage.md` §16 참조)
- **Feature**: OD, LD, RMD (통합 기준, 필요 시 feature별 분리)
- **분석 단위**: 개별 gap → 세션 → 사용자 일 단위 → Task idle rollup

### 1.4 관련 문서

| 문서 | 역할 |
|------|------|
| `labeler_focus_drop_concept_design.md` | v1.0 개념 설계 |
| `labeler_focus_drop_metric_design.md` | v1.0 메트릭 구조 |
| `productivity_concept_design.md` | 생산성 지표 및 Task 순소요시간 연계 |

---

## 2. 데이터 소스

### 2.1 원시 테이블

```
sv_nova_dev_an2_catalog.raw.raw_labelit__workspace_command       -- 이벤트 로그 (핵심)
sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_tasks               -- task 메타
sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_assignments         -- assignment 메타 (role 식별)
sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_annotation_policies -- feature 식별
sv_nova_dev_an2_catalog.raw.raw_labelit__company                 -- 회사 필터
```

> Focus Drop 파이프라인은 staging layer를 거치지 않고 raw 테이블을 직접 참조한다 (CDC dedup 패턴 §2.5 적용). 이벤트 시계열 분석 특성상 staging 집계가 불필요하기 때문이다.

### 2.2 핵심 필드 파싱

```sql
-- workspace_command에서 추출
c.`_raw`:userId::STRING       AS user_id,
c.`_raw`:sessionId::STRING    AS session_id,
c.`_raw`:taskId::STRING       AS task_id,
c.`_raw`:createdAt::TIMESTAMP AS event_time,
c.`_raw`:commandType::STRING  AS command_type

-- gen2_assignments에서 추출 (role 필터용)
LOWER(a.`_raw`:role::STRING)  AS user_role
```

### 2.3 조인 관계

```
command._raw:taskId → task._id
task._raw:assignmentId → assignment._id        (★ role 식별 경로)
task._raw:policyId → annotation_policy._id     (feature 식별)
task._raw:companyId → company._id
```

### 2.4 주의사항

- `_is_deleted = false` 인 레코드만 분석 대상
- `object_id`는 task 간 중복 가능 → 반드시 `task_id`와 함께 사용
- `diff_sec <= 0` (타임스탬프 역전) 제외
- **기본 KPI 파이프라인에서는 role 필터를 선행 적용해야 함** — 미적용 시 기준선 오염
- 단, **생산성 연계용 idle rollup**은 Labeler 전용/Reviewer 전용/통합(all_roles) 모드로 별도 운용 가능 (`focus_drop_productivity_linkage.md` §16)

### 2.5 CDC dedup 패턴 (필수)

raw 테이블은 CDC 적재 구조로 동일 `_id`에 여러 버전 레코드가 존재할 수 있다. 모든 raw 참조는 `_ingested_at` 기준 최신 레코드만 선택하는 dedup CTE를 거쳐야 한다.

```sql
WITH latest_commands AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__workspace_command`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
)
```

세 raw 테이블(`workspace_command`, `gen2_tasks`, `gen2_assignments`) 모두 동일 패턴을 적용한다. dedup 미적용 시 동일 이벤트가 여러 번 카운트되어 percentile/세션 메트릭이 왜곡된다.

### 2.6 시간 기준 — KST 일자 변환

`createdAt`은 UTC TIMESTAMP로 저장된다. 분석 단위가 KST 영업일이므로 다음 변환을 거친 후 `analysis_date`/`rolling_days` 필터에 적용한다.

```sql
CAST(
  CONVERT_TIMEZONE('UTC', 'Asia/Seoul', c.`_raw`:createdAt::TIMESTAMP) AS DATE
) = DATE '${analysis_date}'
```

미적용 시 KST 자정 인접 이벤트(UTC 15시–24시 = KST 0시–9시)가 잘못된 일자로 분류되어 세션이 분절될 수 있다.

---

## 3. 세션 정의

### 3.1 세션 키

```
session_key = (user_id, session_id, task_id)
```

### 3.2 세션 유효성 조건

분석 대상 세션은 다음 **3개 조건을 모두** 충족해야 한다.

| 파라미터 | 권장 초기값 | 설명 | SQL 적용 위치 |
|----------|-----------|------|--------------|
| `min_event_count` | 10 | 세션 내 최소 이벤트 수 | HAVING (gap 수 + 1 ≥ 값) |
| `min_session_duration_sec` | 60 | 세션 최소 지속 시간(초) | HAVING (MAX - MIN ≥ 값) |
| `min_gap_count` | 5 | 분석 대상 최소 gap 수 (zero-inflation 방지) | HAVING COUNT(*) ≥ 값 |

### 3.3 diff_sec 산출

```sql
UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
  LAG(event_time) OVER (
    PARTITION BY user_id, session_id, task_id
    ORDER BY event_time
  )
) AS diff_sec
```

---

## 4. 메트릭 체계

### 4.1 지표 계층 흐름

```
[1차 percentile]  gap_p75 / gap_p90 / gap_p95 (gap_p99: 참고 진단용)
        ↓ 각 gap을 severity 구간으로 분류 (idle ≥ 180s 고정)
[세션 지표]       light_gap_count / heavy_gap_count / idle_gap_count
                  light_gap_ratio / heavy_gap_ratio / idle_gap_ratio
                  idle_gap_duration_sec
        ↓ 기준선 테이블(rolling baseline)에서 2차 percentile 조회
[세션 판정]       is_light_session / is_heavy_session / is_idle_session
                  → focus_drop_level (배타적: idle > heavy > light > normal)
        ↓ 사용자 일 단위 집계 + Task 단위 rollup
[사용자 KPI]      light_session_count / heavy_session_count / idle_gap_total
[Task rollup]     idle_gap_total / idle_gap_duration_sec / contributing_sessions
        ↓ 생산성 지표와 조인
[생산성 연계]     gross_task_hours - task_total_idle_sec = net_task_hours
```

### 4.2 gap 구간 정의

| 구간 | 조건 | 용도 |
|------|------|------|
| 정상 | `diff_sec <= gap_p75` | 정상 작업 흐름 |
| observation | `gap_p75 < diff_sec <= gap_p90` | 추세 관찰 보조 (판정 미사용) |
| light | `gap_p90 < diff_sec <= gap_p95` | light_gap_count 산출 |
| heavy | `gap_p95 < diff_sec < 180` | heavy_gap_count 산출 |
| idle | `diff_sec >= 180` | idle_gap_count 및 idle_gap_duration_sec 산출 (고정 임계값 3분) |

### 4.3 세션 핵심 메트릭

| 메트릭 | 역할 | 비고 |
|--------|------|------|
| `light_gap_count` | 핵심 판정 | count 중심 |
| `heavy_gap_count` | 핵심 판정 | count 중심 |
| `idle_gap_count` | 핵심 판정 | count 중심 |
| `idle_gap_duration_sec` | 생산성 연계 | `SUM(diff_sec WHERE gap_severity='idle')`, 판정 미사용 |
| `light_gap_ratio` | 보조 보정 | 세션 길이 차이 보정 |
| `heavy_gap_ratio` | 보조 보정 | 세션 길이 차이 보정 |
| `idle_gap_ratio` | 보조 보정 | 세션 길이 차이 보정 |
| `observation_gap_count` | 추세 관찰 | 판정 미사용 |
| `session_avg_gap` | 참고 진단 | 판정 미사용 |

### 4.4 사용자 일 단위 메트릭

| 메트릭 | 역할 | 집계 범위 |
|--------|------|----------|
| `light_session_count` | 핵심 반복성 | `is_light_session = TRUE` 세션 수 |
| `heavy_session_count` | 핵심 반복성 | `is_heavy_session = TRUE` 세션 수 |
| `idle_gap_total` | 핵심 누적량 | **모든 세션**의 idle_gap_count 합산 (세션 판정 무관) |
| `idle_gap_duration_total_sec` | 생산성 보조 | **모든 세션**의 idle_gap_duration_sec 합산 (선택 집계) |

> **설계 의도 — `idle_gap_total`**: 세션 레벨 판정(`is_idle_session`)과 무관하게, 하루 전체에 걸쳐 발생한 idle gap(≥ 3분)의 절대 누적량을 측정한다. 이는 개별 세션에서는 session_idle_count_p99를 초과하지 못하더라도, 다수 세션에 걸쳐 이탈이 산재하는 패턴을 포착하기 위함이다.

> **설계 의도 — `idle_gap_duration_total_sec`**: 생산성 지표와 연결할 때는 idle gap의 **발생 횟수**보다 **실제 차감 시간(초)** 이 더 중요하다. 따라서 KPI 본체는 count 중심으로 유지하되, 별도 rollup에서 duration 합산값을 보조적으로 유지한다.

---

## 5. 판정 기준

### 5.1 세션 판정

| 레벨 | 주판정 | 보조판정 (오탐 시 전환) | 최소 조건 | 상태 |
|------|--------|---------|----------|------|
| light | `light_gap_count > session_light_count_p90` | `light_gap_ratio > session_light_ratio_p90` | `light_gap_count > 0` | ratio 현재 비활성 (`focus_drop_deployment.md` §7.4 주석). 오탐률 > 20% 시 AND 활성화 |
| heavy | `heavy_gap_count > session_heavy_count_p95` | `heavy_gap_ratio > session_heavy_ratio_p95` | `heavy_gap_count > 0` | 동일 |
| idle | `idle_gap_count > session_idle_count_p99` | `idle_gap_ratio > session_idle_ratio_p99` | `idle_gap_count > 0` | 동일 |

### 5.2 배타성 규칙

판정 레벨은 **최고 심각도 우선** 원칙으로 배타적으로 적용한다.

```
focus_drop_level = CASE
  WHEN is_idle_session  THEN 'idle'
  WHEN is_heavy_session THEN 'heavy'
  WHEN is_light_session THEN 'light'
  ELSE 'normal'
END
```

- 한 세션/유저는 **단일 focus_drop_level**만 가짐
- 대시보드 집계 시 중복 카운트 방지
- 알림은 최고 레벨 기준으로만 발송

### 5.3 사용자 일 단위 판정

| 레벨 | 조건 | 최소 조건 |
|------|------|----------|
| light 후보 | `light_session_count > user_light_session_count_p90` | `> 0` |
| heavy 후보 | `heavy_session_count > user_heavy_session_count_p95` | `> 0` |
| idle 후보 | `idle_gap_total > user_idle_gap_total_p99` | `> 0` |

사용자 레벨에도 동일한 배타성 규칙을 적용한다 (`user_focus_drop_level`).

> **차원 구분**: `heavy`은 세션 반복성(heavy 세션 수) 기준이고, `idle`은 gap 누적량(idle gap 절대 합산) 기준이다. 두 지표는 서로 다른 차원을 측정하므로, heavy이 낮더라도 idle이 높을 수 있고 그 반대도 가능하다.

### 5.4 기준선 산출 원칙

> **중요**: 세션/유저 판정에 사용하는 2차 percentile 기준은 **당일 데이터에서 산출하지 않는다**.

| 기준선 | 산출 방법 | 갱신 주기 |
|--------|----------|----------|
| gap percentile (1차) | Labeler 직전 90일 로그의 diff_sec 분포 (최소 10,000 gap 표본 필수) | 분기 1회 또는 드리프트 시 |
| session threshold (2차) | 직전 30일 세션 메트릭의 percentile | 주 1회 rolling |
| user threshold (2차) | 직전 30일 유저 KPI의 percentile | 주 1회 rolling |

### 5.5 판정 제외 지표

- `session_avg_gap`, `user_day_avg_gap` — 참고용 진단만
- `idle_gap_duration_sec` — 생산성 차감용, focus_drop 판정에는 직접 미사용
- 단일 gap 1회 발생만으로의 판정
- 절대 count 고정값만을 사용한 판정

---

---

## 7. SQL 레퍼런스

### 7.1 gap percentile 산출 (Labeler role 필터 포함)

```sql
-- int__focus_drop_gap_percentiles.sql
-- 시간 기준: rolling_days는 KST 기준 영업일 (createdAt UTC → KST 변환 후 비교)
-- 표본 10,000 미달 시 HAVING으로 자동 스킵 → 기존 기준선 유지

CREATE WIDGET TEXT rolling_days DEFAULT "90";

INSERT INTO analytics.focus_drop_gap_thresholds
WITH latest_assignments AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_assignments`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
latest_tasks AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_tasks`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
latest_commands AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__workspace_command`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
labeler_commands AS (
  SELECT
    c.`_raw`:userId::STRING       AS user_id,
    c.`_raw`:sessionId::STRING    AS session_id,
    c.`_raw`:taskId::STRING       AS task_id,
    c.`_raw`:createdAt::TIMESTAMP AS event_time
  FROM latest_commands c
  INNER JOIN latest_tasks       t ON c.`_raw`:taskId::STRING = t.`_id`
  INNER JOIN latest_assignments a ON t.`_raw`:assignmentId::STRING = a.`_id`
  WHERE LOWER(a.`_raw`:role::STRING) = 'labeler'
    AND CAST(
      CONVERT_TIMEZONE('UTC', 'Asia/Seoul', c.`_raw`:createdAt::TIMESTAMP) AS DATE
    ) >= DATE_SUB(CURRENT_DATE(), ${rolling_days})
),
with_diff AS (
  SELECT *,
    UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
      LAG(event_time) OVER (PARTITION BY user_id, session_id, task_id ORDER BY event_time)
    ) AS diff_sec
  FROM labeler_commands
)
SELECT
  COALESCE((SELECT MAX(version) FROM analytics.focus_drop_gap_thresholds), 0) + 1 AS version,
  CURRENT_TIMESTAMP()        AS computed_at,
  'all_features'             AS feature_scope,
  COUNT(*)                   AS sample_count,
  PERCENTILE(diff_sec, 0.50) AS gap_p50,
  PERCENTILE(diff_sec, 0.75) AS gap_p75,
  PERCENTILE(diff_sec, 0.90) AS gap_p90,
  PERCENTILE(diff_sec, 0.95) AS gap_p95,
  PERCENTILE(diff_sec, 0.99) AS gap_p99
FROM with_diff
WHERE diff_sec IS NOT NULL AND diff_sec > 0
  AND diff_sec < 180  -- ★ Idle gap 제외: idle 구간(≥ 180s)은 고정 임계값으로 처리, percentile 분포 오염 방지
HAVING COUNT(*) >= 10000;  -- ★ §5.4 최소 표본 요건 강제 (미달 시 0행 INSERT → 기존 기준선 유지)
```

### 7.2 세션 메트릭 산출 (유효성 3조건 완전 구현)

```sql
-- int__focus_drop_session_metrics.sql
-- 의존성: focus_drop_gap_thresholds (gap 구간 경계 — 테이블에서 자동 로드)
-- 갱신 전략: INSERT INTO ... REPLACE WHERE analysis_date
-- 시간 기준: analysis_date는 KST 일자 (createdAt UTC → KST 변환 후 비교)

CREATE WIDGET TEXT analysis_date            DEFAULT "";
CREATE WIDGET TEXT min_gap_count            DEFAULT "5";
CREATE WIDGET TEXT min_event_count          DEFAULT "10";
CREATE WIDGET TEXT min_session_duration_sec DEFAULT "60";

INSERT INTO analytics.focus_drop_session_metrics
REPLACE WHERE analysis_date = '${analysis_date}'
WITH thresholds AS (
  -- gap 구간 경계: 위젯 없이 최신 버전 자동 참조 (gap_p99 제거: idle 경계는 고정 180s)
  SELECT gap_p75, gap_p90, gap_p95
  FROM analytics.focus_drop_gap_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_gap_thresholds)
),
latest_assignments AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_assignments`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
latest_tasks AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_tasks`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
latest_commands AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__workspace_command`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
labeler_commands AS (
  SELECT
    c.`_raw`:userId::STRING       AS user_id,
    c.`_raw`:sessionId::STRING    AS session_id,
    c.`_raw`:taskId::STRING       AS task_id,
    c.`_raw`:createdAt::TIMESTAMP AS event_time
  FROM latest_commands c
  INNER JOIN latest_tasks       t ON c.`_raw`:taskId::STRING = t.`_id`
  INNER JOIN latest_assignments a ON t.`_raw`:assignmentId::STRING = a.`_id`
  WHERE LOWER(a.`_raw`:role::STRING) = 'labeler'
    AND CAST(
      CONVERT_TIMEZONE('UTC', 'Asia/Seoul', c.`_raw`:createdAt::TIMESTAMP) AS DATE
    ) = DATE '${analysis_date}'
),
with_diff AS (
  SELECT *,
    UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
      LAG(event_time) OVER (PARTITION BY user_id, session_id, task_id ORDER BY event_time)
    ) AS diff_sec,
    UNIX_TIMESTAMP(event_time) AS event_ts_unix
  FROM labeler_commands
),
gap_classified AS (
  SELECT
    g.user_id, g.session_id, g.task_id, g.diff_sec, g.event_ts_unix,
    CASE
      WHEN g.diff_sec >= 180        THEN 'idle'       -- ★ 고정 임계값 3분
      WHEN g.diff_sec <= t.gap_p75 THEN 'normal'
      WHEN g.diff_sec <= t.gap_p90 THEN 'observation'
      WHEN g.diff_sec <= t.gap_p95 THEN 'light'
      ELSE 'heavy'                                     -- gap_p95 < diff_sec < 180
    END AS gap_severity
  FROM with_diff g
  CROSS JOIN thresholds t
  WHERE g.diff_sec IS NOT NULL AND g.diff_sec > 0
)
SELECT
  DATE '${analysis_date}'                                         AS analysis_date,
  user_id, session_id, task_id,
  COUNT(*)                                                        AS total_gaps,
  SUM(CASE WHEN gap_severity = 'observation' THEN 1 ELSE 0 END)  AS observation_gap_count,
  SUM(CASE WHEN gap_severity = 'light'       THEN 1 ELSE 0 END)  AS light_gap_count,
  SUM(CASE WHEN gap_severity = 'heavy'       THEN 1 ELSE 0 END)  AS heavy_gap_count,
  SUM(CASE WHEN gap_severity = 'idle'        THEN 1 ELSE 0 END)  AS idle_gap_count,
  SUM(CASE WHEN gap_severity = 'idle'        THEN diff_sec ELSE 0 END) AS idle_gap_duration_sec,
  ROUND(SUM(CASE WHEN gap_severity = 'light'     THEN 1 ELSE 0 END) / COUNT(*), 2) AS light_gap_ratio,
  ROUND(SUM(CASE WHEN gap_severity = 'heavy'     THEN 1 ELSE 0 END) / COUNT(*), 2) AS heavy_gap_ratio,
  ROUND(SUM(CASE WHEN gap_severity = 'idle'      THEN 1 ELSE 0 END) / COUNT(*), 2) AS idle_gap_ratio,
  AVG(diff_sec)                                                   AS session_avg_gap
FROM gap_classified
GROUP BY user_id, session_id, task_id
HAVING COUNT(*) >= ${min_gap_count}
   AND COUNT(*) + 1 >= ${min_event_count}
   AND (MAX(event_ts_unix) - MIN(event_ts_unix)) >= ${min_session_duration_sec};
```

> **gap_p75/p90/p95 자동 로드**: session_metrics SQL은 위젯 파라미터 대신 `analytics.focus_drop_gap_thresholds`의 최신 버전을 CTE로 직접 참조한다. percentile 갱신 시 별도 위젯 동기화 불필요.


---

## 10. 운영 해석 원칙

### 10.1 판정 ≠ 확정

- `light`/`heavy` 판정은 **검토 필요 신호**이며, 저성과 확정이 아님
- 실제 해석 시 작업 맥락, task 특성, 운영 이슈를 함께 고려

### 10.2 도메인 특성 고려

- 3D point cloud annotation에서는 시점 탐색/회전/확인 시간이 command 로그에 반영되지 않음
- 따라서 개별 long gap 하나보다 **반복 패턴**을 우선 해석
- 생산성 연계 시에도 idle 차감은 **순작업시간 근사치**이지 완전한 근태 시간 대체값이 아님

### 10.3 feature별 해석

- OD: 객체 밀도 높음 → 짧은 gap이 정상
- LD: 연속 라인 작업 → 리듬성 갭 패턴
- RMD: 넓은 영역 탐색 → 상대적으로 긴 gap 허용 가능

---

---

## 14. 트리거 키워드

다음 키워드가 요청에 포함되면 본 skill을 참조:

- "집중도", "focus drop", "집중도 저하", "focus"
- "gap 분석", "gap percentile", "긴 공백"
- "light session", "heavy session", "idle session"
- "작업 이탈", "idle 탐지", "3분 기준", "180초"
- "KPI 모니터링", "일일 리포트"
- "idle 차감", "순소요시간", "net working time", "task idle"

---

---

## 15. 빠른 참조

### 15.1 현황 확인 쿼리

```sql
-- 오늘의 focus drop KPI 요약 (배타적 레벨)
SELECT user_id, user_focus_drop_level, light_session_count, heavy_session_count, idle_gap_total
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date = CURRENT_DATE() - 1
  AND user_focus_drop_level != 'normal'
ORDER BY
  CASE user_focus_drop_level WHEN 'idle' THEN 1 WHEN 'heavy' THEN 2 WHEN 'light' THEN 3 END;
```

### 15.2 기준값 확인

```sql
-- 현재 적용 중인 gap threshold
SELECT * FROM analytics.focus_drop_gap_thresholds
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_gap_thresholds);

-- 현재 적용 중인 세션 기준선
SELECT * FROM analytics.focus_drop_session_thresholds
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds);

-- 현재 적용 중인 유저 기준선
SELECT * FROM analytics.focus_drop_user_thresholds
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_user_thresholds);
```

### 15.3 세션 상세 드릴다운

```sql
-- 특정 사용자의 세션별 gap severity 분포
SELECT
  session_id, task_id,
  total_gaps,
  light_gap_count, heavy_gap_count, idle_gap_count,
  focus_drop_level
FROM analytics.focus_drop_session_tags
WHERE user_id = :user_id
  AND analysis_date = :date
ORDER BY
  CASE focus_drop_level WHEN 'idle' THEN 1 WHEN 'heavy' THEN 2 WHEN 'light' THEN 3 ELSE 4 END;
```

### 15.4 Task idle rollup 확인

```sql
-- 생산성 연계용 task idle 누적 초수 확인
SELECT
  analysis_date,
  task_id,
  role_scope,
  role_group,
  contributing_sessions,
  contributing_users,
  idle_gap_total,
  idle_gap_duration_sec
FROM analytics.focus_drop_task_idle_rollup
WHERE analysis_date >= DATE_SUB(CURRENT_DATE(), 7)
ORDER BY analysis_date DESC, idle_gap_duration_sec DESC;
```

