# Focus Drop KPI Monitoring Skill

> Labeler 작업 집중도 저하(Focus Drop)를 KPI로서 지속 모니터링하기 위한 통합 운영 가이드

---

## 1. 개요

### 1.1 목적

Labeler의 작업 세션에서 **작업 집중도 저하 신호**를 분포 기반으로 탐지하고, 일일 KPI로 집계하여 지속적으로 모니터링한다.

### 1.2 핵심 원칙

- **집중도 측정이 아닌 저하 탐지**: 심리적 몰입 상태를 측정하지 않고, 정상 분포 대비 이탈 신호를 탐지한다
- **분포 기반 percentile 체계**: 절대 임계값이 아닌 Labeler 정상군 분포에서 경계를 산출한다
- **기준선 안정성**: 판정 기준(2차 percentile)은 당일 데이터가 아닌 안정 구간(rolling window)에서 사전 산출하여 고정한다
- **반복성 중심 판정**: 개별 gap 하나가 아닌, 긴 gap의 반복 발생 패턴으로 판정한다
- **3단계 심각도 (배타적)**: warning → critical → departure 단계로 구분하며, 최고 레벨 우선 적용한다

### 1.3 적용 대상

- **Role**: Labeler (Reviewer/Manager 제외 — SQL에서 role 필터 강제)
- **Feature**: OD, LD, RMD (통합 기준, 필요 시 feature별 분리)
- **분석 단위**: 개별 gap → 세션 → 사용자 일 단위

### 1.4 관련 문서

| 문서 | 역할 |
|------|------|
| `labeler_focus_drop_concept_design.md` | v1.0 개념 설계 |
| `labeler_focus_drop_metric_design.md` | v1.0 메트릭 구조 |

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

### 2.2 핵심 필드 파싱

```sql
-- workspace_command에서 추출
c._raw:userId::STRING       AS user_id,
c._raw:sessionId::STRING    AS session_id,
c._raw:taskId::STRING       AS task_id,
c._raw:createdAt::TIMESTAMP AS event_time,
c._raw:commandType::STRING  AS command_type

-- gen2_assignments에서 추출 (role 필터용)
a._raw:role::STRING         AS user_role
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
- **role 필터는 모든 파이프라인 단계에서 선행 적용해야 함** — 미적용 시 기준선 오염

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
[1차 percentile]  gap_p75 / gap_p90 / gap_p95 / gap_p99
        ↓ 각 gap을 severity 구간으로 분류
[세션 지표]       warning_gap_count / critical_gap_count / departure_gap_count
                  warning_gap_ratio / critical_gap_ratio / departure_gap_ratio
        ↓ 기준선 테이블(rolling baseline)에서 2차 percentile 조회
[세션 판정]       is_warning_session / is_critical_session / is_departure_session
                  → focus_drop_level (배타적: departure > critical > warning > normal)
        ↓ 사용자 일 단위 집계
[사용자 KPI]      warning_session_count / critical_session_count / departure_gap_total
        ↓ 기준선 테이블(rolling baseline)에서 2차 percentile 조회
[사용자 판정]     is_warning_user / is_critical_user / is_departure_user
                  → user_focus_drop_level (배타적)
```

### 4.2 gap 구간 정의

| 구간 | 조건 | 용도 |
|------|------|------|
| 정상 | `diff_sec <= gap_p75` | 정상 작업 흐름 |
| observation | `gap_p75 < diff_sec <= gap_p90` | 추세 관찰 보조 (판정 미사용) |
| warning | `gap_p90 < diff_sec <= gap_p95` | warning_gap_count 산출 |
| critical | `gap_p95 < diff_sec <= gap_p99` | critical_gap_count 산출 |
| departure | `diff_sec > gap_p99` | departure_gap_count 산출 |

### 4.3 세션 핵심 메트릭

| 메트릭 | 역할 | 비고 |
|--------|------|------|
| `warning_gap_count` | 핵심 판정 | count 중심 |
| `critical_gap_count` | 핵심 판정 | count 중심 |
| `departure_gap_count` | 핵심 판정 | count 중심 |
| `warning_gap_ratio` | 보조 보정 | 세션 길이 차이 보정 |
| `critical_gap_ratio` | 보조 보정 | 세션 길이 차이 보정 |
| `departure_gap_ratio` | 보조 보정 | 세션 길이 차이 보정 |
| `observation_gap_count` | 추세 관찰 | 판정 미사용 |
| `session_avg_gap` | 참고 진단 | 판정 미사용 |

### 4.4 사용자 일 단위 메트릭

| 메트릭 | 역할 | 집계 범위 |
|--------|------|----------|
| `warning_session_count` | 핵심 반복성 | `is_warning_session = TRUE` 세션 수 |
| `critical_session_count` | 핵심 반복성 | `is_critical_session = TRUE` 세션 수 |
| `departure_gap_total` | 핵심 누적량 | **모든 세션**의 departure_gap_count 합산 (세션 판정 무관) |

> **설계 의도 — `departure_gap_total`**: 세션 레벨 판정(`is_departure_session`)과 무관하게, 하루 전체에 걸쳐 발생한 departure gap의 절대 누적량을 측정한다. 이는 개별 세션에서는 p99를 초과하지 못하더라도, 다수 세션에 걸쳐 departure gap이 산재하는 패턴을 포착하기 위함이다.

---

## 5. 판정 기준

### 5.1 세션 판정

| 레벨 | 주판정 | 보조판정 (오탐 시 전환) | 최소 조건 | 상태 |
|------|--------|---------|----------|------|
| warning | `warning_gap_count > session_warning_count_p90` | `warning_gap_ratio > session_warning_ratio_p90` | `warning_gap_count > 0` | ratio 현재 비활성 (§7.4 주석). 오탐률 > 20% 시 AND 활성화 |
| critical | `critical_gap_count > session_critical_count_p95` | `critical_gap_ratio > session_critical_ratio_p95` | `critical_gap_count > 0` | 동일 |
| departure | `departure_gap_count > session_departure_count_p99` | `departure_gap_ratio > session_departure_ratio_p99` | `departure_gap_count > 0` | 동일 |

### 5.2 배타성 규칙

판정 레벨은 **최고 심각도 우선** 원칙으로 배타적으로 적용한다.

```
focus_drop_level = CASE
  WHEN is_departure_session THEN 'departure'
  WHEN is_critical_session  THEN 'critical'
  WHEN is_warning_session   THEN 'warning'
  ELSE 'normal'
END
```

- 한 세션/유저는 **단일 focus_drop_level**만 가짐
- 대시보드 집계 시 중복 카운트 방지
- 알림은 최고 레벨 기준으로만 발송

### 5.3 사용자 일 단위 판정

| 레벨 | 조건 | 최소 조건 |
|------|------|----------|
| warning 후보 | `warning_session_count > user_warning_session_count_p90` | `> 0` |
| critical 후보 | `critical_session_count > user_critical_session_count_p95` | `> 0` |
| departure 후보 | `departure_gap_total > user_departure_gap_total_p99` | `> 0` |

사용자 레벨에도 동일한 배타성 규칙을 적용한다 (`user_focus_drop_level`).

> **차원 구분**: `critical`은 세션 반복성(critical 세션 수) 기준이고, `departure`는 gap 누적량(departure gap 절대 합산) 기준이다. 두 지표는 서로 다른 차원을 측정하므로, critical이 낮더라도 departure가 높을 수 있고 그 반대도 가능하다.

### 5.4 기준선 산출 원칙

> **중요**: 세션/유저 판정에 사용하는 2차 percentile 기준은 **당일 데이터에서 산출하지 않는다**.

| 기준선 | 산출 방법 | 갱신 주기 |
|--------|----------|----------|
| gap percentile (1차) | Labeler 직전 90일 로그의 diff_sec 분포 (최소 10,000 gap 표본 필수) | 분기 1회 또는 드리프트 시 |
| session threshold (2차) | 직전 30일 세션 메트릭의 percentile | 주 1회 rolling |
| user threshold (2차) | 직전 30일 유저 KPI의 percentile | 주 1회 rolling |

### 5.5 판정 제외 지표

- `session_avg_gap`, `user_day_avg_gap` — 참고용 진단만
- 단일 gap 1회 발생만으로의 판정
- 절대 count 고정값만을 사용한 판정

---

## 6. 파이프라인 구조

### 6.1 실행 순서

```
[기준선 산출 — 분기/주 단위]

focus_drop__gap_percentiles.sql          → analytics.focus_drop_gap_thresholds
                                            (1차 percentile: gap 구간 경계)

[일 단위 배치 — 매일 04:00 UTC]

focus_drop__session_metrics.sql          → analytics.focus_drop_session_metrics
        ↓                                   (세션별 count/ratio 산출)
focus_drop__session_tags.sql             → analytics.focus_drop_session_tags
        ↓                                   (기준선 참조 → 세션 판정)
focus_drop__user_day_kpi.sql             → analytics.focus_drop_user_day_kpi
                                            (기준선 참조 → 유저 판정)

[기준선 갱신 — 주 1회 월요일 03:00 UTC, session_metrics/user_day_kpi 누적 결과를 입력으로 사용]

focus_drop__session_thresholds.sql       → analytics.focus_drop_session_thresholds
                                            (직전 30일 session_metrics 기반)
focus_drop__user_thresholds.sql          → analytics.focus_drop_user_thresholds
                                            (직전 30일 user_day_kpi 기반)
```

> **의존성 방향**: session_thresholds / user_thresholds는 session_metrics / user_day_kpi의 **누적 산출물**(직전 30일분)을 입력으로 사용한다. 반대로 session_tags / user_day_kpi는 session_thresholds / user_thresholds의 **최신 기준선**을 참조한다. 따라서 정상 운영 시 실행 순서는 `session_metrics → session_tags → user_day_kpi` (일 배치) / `session_thresholds → user_thresholds` (주 배치, session_metrics / user_day_kpi 결과 반영)이다.

### 6.2 실행 스케줄

| 노트북 | 실행 주기 | 트리거 조건 |
|--------|----------|------------|
| `gap_percentiles` | 분기 1회 또는 분포 변화 시 | 기준값 드리프트 ±20% 감지 |
| `session_thresholds`, `user_thresholds` | 주 1회 (월요일 03:00 UTC) | 직전 30일 rolling window 갱신 |
| `session_metrics` → `session_tags` → `user_day_kpi` | 일 단위 배치 | 매일 04:00 UTC (전일 데이터 대상) |

### 6.3 Delta 테이블

| 테이블 | 스키마 | 갱신 전략 |
|--------|--------|----------|
| `analytics.focus_drop_gap_thresholds` | `version INT, computed_at TIMESTAMP, feature_scope STRING, sample_count BIGINT, gap_p50~p99 DOUBLE` | 버전업 시 INSERT |
| `analytics.focus_drop_session_thresholds` | `version INT, computed_at TIMESTAMP, is_bootstrap BOOLEAN, window_start DATE, window_end DATE, session_warning_count_p90 DOUBLE, session_critical_count_p95 DOUBLE, session_departure_count_p99 DOUBLE, session_warning_ratio_p90 DOUBLE, session_critical_ratio_p95 DOUBLE, session_departure_ratio_p99 DOUBLE` | 주 1회 INSERT |
| `analytics.focus_drop_user_thresholds` | `version INT, computed_at TIMESTAMP, is_bootstrap BOOLEAN, window_start DATE, window_end DATE, user_warning_session_count_p90 DOUBLE, user_critical_session_count_p95 DOUBLE, user_departure_gap_total_p99 DOUBLE` | 주 1회 INSERT |
| `analytics.focus_drop_session_metrics` | `analysis_date DATE, user_id STRING, session_id STRING, task_id STRING, total_gaps INT, observation_gap_count INT, warning_gap_count INT, critical_gap_count INT, departure_gap_count INT, warning_gap_ratio DOUBLE, critical_gap_ratio DOUBLE, departure_gap_ratio DOUBLE, session_avg_gap DOUBLE` | INSERT INTO ... REPLACE WHERE analysis_date |
| `analytics.focus_drop_session_tags` | `analysis_date DATE, user_id STRING, session_id STRING, task_id STRING, warning_gap_count INT, critical_gap_count INT, departure_gap_count INT, is_warning_session BOOLEAN, is_critical_session BOOLEAN, is_departure_session BOOLEAN, focus_drop_level STRING` | INSERT INTO ... REPLACE WHERE analysis_date |
| `analytics.focus_drop_user_day_kpi` | `analysis_date DATE, user_id STRING, warning_session_count INT, critical_session_count INT, departure_gap_total INT, total_sessions INT, is_warning_user BOOLEAN, is_critical_user BOOLEAN, is_departure_user BOOLEAN, user_focus_drop_level STRING` | INSERT INTO ... REPLACE WHERE analysis_date |

---

## 7. SQL 레퍼런스

### 7.1 gap percentile 산출 (Labeler role 필터 포함)

```sql
-- focus_drop__gap_percentiles.sql
WITH labeler_commands AS (
  SELECT
    c._raw:userId::STRING       AS user_id,
    c._raw:sessionId::STRING    AS session_id,
    c._raw:taskId::STRING       AS task_id,
    c._raw:createdAt::TIMESTAMP AS event_time
  FROM sv_nova_dev_an2_catalog.raw.raw_labelit__workspace_command c
  INNER JOIN sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_tasks t
    ON c._raw:taskId::STRING = t._id
  INNER JOIN sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_assignments a
    ON t._raw:assignmentId::STRING = a._id
  WHERE c._is_deleted = false
    AND LOWER(a._raw:role::STRING) = 'labeler'
    AND CAST(c._raw:createdAt::TIMESTAMP AS DATE) >= DATE_SUB(CURRENT_DATE(), 90)  -- ★ 직전 90일
),
with_diff AS (
  SELECT *,
    UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
      LAG(event_time) OVER (PARTITION BY user_id, session_id, task_id ORDER BY event_time)
    ) AS diff_sec
  FROM labeler_commands
)
-- ★ 표본 수 검증: 10,000 미만이면 INSERT 스킵 (기준선 오염 방지)
INSERT INTO analytics.focus_drop_gap_thresholds
SELECT
  COALESCE((SELECT MAX(version) FROM analytics.focus_drop_gap_thresholds), 0) + 1 AS version,
  CURRENT_TIMESTAMP()                AS computed_at,
  'all_features'                     AS feature_scope,
  COUNT(*)                           AS sample_count,
  PERCENTILE(diff_sec, 0.50)         AS gap_p50,
  PERCENTILE(diff_sec, 0.75)         AS gap_p75,
  PERCENTILE(diff_sec, 0.90)         AS gap_p90,
  PERCENTILE(diff_sec, 0.95)         AS gap_p95,
  PERCENTILE(diff_sec, 0.99)         AS gap_p99
FROM with_diff
WHERE diff_sec IS NOT NULL AND diff_sec > 0
HAVING COUNT(*) >= 10000;  -- ★ §5.4 최소 표본 요건 강제 (미달 시 0행 INSERT → 기존 기준선 유지)
```

### 7.2 세션 메트릭 산출 (유효성 3조건 완전 구현)

```sql
-- focus_drop__session_metrics.sql
-- ★ with_diff CTE: role 필터를 session_metrics에서도 재적용하여 결함2 재발 방지
WITH labeler_commands AS (
  SELECT
    c._raw:userId::STRING       AS user_id,
    c._raw:sessionId::STRING    AS session_id,
    c._raw:taskId::STRING       AS task_id,
    c._raw:createdAt::TIMESTAMP AS event_time
  FROM sv_nova_dev_an2_catalog.raw.raw_labelit__workspace_command c
  INNER JOIN sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_tasks t
    ON c._raw:taskId::STRING = t._id
  INNER JOIN sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_assignments a
    ON t._raw:assignmentId::STRING = a._id
  WHERE c._is_deleted = false
    AND LOWER(a._raw:role::STRING) = 'labeler'
    AND CAST(c._raw:createdAt::TIMESTAMP AS DATE) = ${analysis_date}  -- 당일 데이터만
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
    user_id, session_id, task_id, diff_sec, event_ts_unix,
    CASE
      WHEN diff_sec <= ${gap_p75}  THEN 'normal'
      WHEN diff_sec <= ${gap_p90}  THEN 'observation'
      WHEN diff_sec <= ${gap_p95}  THEN 'warning'
      WHEN diff_sec <= ${gap_p99}  THEN 'critical'
      ELSE 'departure'
    END AS gap_severity
  FROM with_diff
  WHERE diff_sec IS NOT NULL AND diff_sec > 0
)
INSERT INTO analytics.focus_drop_session_metrics
REPLACE WHERE analysis_date = ${analysis_date}
SELECT
  ${analysis_date}                                            AS analysis_date,
  user_id, session_id, task_id,
  COUNT(*)                                                    AS total_gaps,
  SUM(CASE WHEN gap_severity = 'observation' THEN 1 ELSE 0 END) AS observation_gap_count,
  SUM(CASE WHEN gap_severity = 'warning'     THEN 1 ELSE 0 END) AS warning_gap_count,
  SUM(CASE WHEN gap_severity = 'critical'    THEN 1 ELSE 0 END) AS critical_gap_count,
  SUM(CASE WHEN gap_severity = 'departure'   THEN 1 ELSE 0 END) AS departure_gap_count,
  ROUND(SUM(CASE WHEN gap_severity = 'warning'   THEN 1 ELSE 0 END) / COUNT(*), 4) AS warning_gap_ratio,
  ROUND(SUM(CASE WHEN gap_severity = 'critical'  THEN 1 ELSE 0 END) / COUNT(*), 4) AS critical_gap_ratio,
  ROUND(SUM(CASE WHEN gap_severity = 'departure' THEN 1 ELSE 0 END) / COUNT(*), 4) AS departure_gap_ratio,
  AVG(diff_sec)                                               AS session_avg_gap
FROM gap_classified
GROUP BY user_id, session_id, task_id
HAVING COUNT(*) >= ${min_gap_count}
   AND COUNT(*) + 1 >= ${min_event_count}
   AND (MAX(event_ts_unix) - MIN(event_ts_unix)) >= ${min_session_duration_sec};
```

### 7.3 세션 기준선 산출 (rolling 30일)

```sql
-- focus_drop__session_thresholds.sql
INSERT INTO analytics.focus_drop_session_thresholds
SELECT
  COALESCE((SELECT MAX(version) FROM analytics.focus_drop_session_thresholds), 0) + 1  AS version,
  CURRENT_TIMESTAMP()                              AS computed_at,
  FALSE                                            AS is_bootstrap,
  DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AS window_start,
  DATE_SUB(CURRENT_DATE(), 1)                      AS window_end,
  PERCENTILE(warning_gap_count,   0.90)            AS session_warning_count_p90,
  PERCENTILE(critical_gap_count,  0.95)            AS session_critical_count_p95,
  PERCENTILE(departure_gap_count, 0.99)            AS session_departure_count_p99,
  PERCENTILE(warning_gap_ratio,   0.90)            AS session_warning_ratio_p90,
  PERCENTILE(critical_gap_ratio,  0.95)            AS session_critical_ratio_p95,
  PERCENTILE(departure_gap_ratio, 0.99)            AS session_departure_ratio_p99
FROM analytics.focus_drop_session_metrics
WHERE analysis_date BETWEEN DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AND DATE_SUB(CURRENT_DATE(), 1);
-- ★ 기준 산출 기간과 판정 대상 기간이 분리됨 (당일 데이터 미포함)
```

### 7.4 세션 판정 (사전 산출 기준선 참조)

```sql
-- focus_drop__session_tags.sql
WITH thresholds AS (
  -- ★ 사전 산출된 rolling baseline 테이블에서 조회 (count + ratio 모두)
  SELECT
    session_warning_count_p90, session_critical_count_p95, session_departure_count_p99,
    session_warning_ratio_p90, session_critical_ratio_p95, session_departure_ratio_p99
  FROM analytics.focus_drop_session_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds)
)
INSERT INTO analytics.focus_drop_session_tags
REPLACE WHERE analysis_date = ${analysis_date}
SELECT
  m.analysis_date,
  m.user_id, m.session_id, m.task_id,
  m.warning_gap_count, m.critical_gap_count, m.departure_gap_count,
  -- 개별 레벨 판정 (count 단독; warning 오탐률 > 20% 확인 시 ratio AND 조건 활성화)
  CASE WHEN m.warning_gap_count > 0
        AND m.warning_gap_count > t.session_warning_count_p90
       THEN TRUE ELSE FALSE END AS is_warning_session,
  CASE WHEN m.critical_gap_count > 0
        AND m.critical_gap_count > t.session_critical_count_p95
       THEN TRUE ELSE FALSE END AS is_critical_session,
  CASE WHEN m.departure_gap_count > 0
        AND m.departure_gap_count > t.session_departure_count_p99
       THEN TRUE ELSE FALSE END AS is_departure_session,
  -- ★ 배타적 최종 레벨 (departure > critical > warning > normal)
  CASE
    WHEN m.departure_gap_count > 0
         AND m.departure_gap_count > t.session_departure_count_p99 THEN 'departure'
    WHEN m.critical_gap_count > 0
         AND m.critical_gap_count > t.session_critical_count_p95   THEN 'critical'
    WHEN m.warning_gap_count > 0
         AND m.warning_gap_count > t.session_warning_count_p90     THEN 'warning'
    ELSE 'normal'
  END AS focus_drop_level
FROM analytics.focus_drop_session_metrics m
CROSS JOIN thresholds t
WHERE m.analysis_date = ${analysis_date};
-- ★ ratio 보조판정 활용: 오탐 의심 시 아래 추가 조건으로 필터링 가능
-- AND m.warning_gap_ratio > t.session_warning_ratio_p90
```

### 7.5 사용자 일 KPI (사전 산출 기준선 참조)

```sql
-- focus_drop__user_day_kpi.sql
WITH user_daily AS (
  SELECT
    user_id,
    analysis_date,
    SUM(CASE WHEN is_warning_session  THEN 1 ELSE 0 END) AS warning_session_count,
    SUM(CASE WHEN is_critical_session THEN 1 ELSE 0 END) AS critical_session_count,
    -- ★ departure_gap_total: 세션 판정 무관, 모든 세션의 departure gap 누적 절대량
    SUM(departure_gap_count)                              AS departure_gap_total,
    COUNT(*)                                              AS total_sessions
  FROM analytics.focus_drop_session_tags
  WHERE analysis_date = ${analysis_date}
  GROUP BY user_id, analysis_date
),
user_thresholds AS (
  -- ★ 사전 산출된 rolling baseline에서 조회
  SELECT user_warning_session_count_p90, user_critical_session_count_p95, user_departure_gap_total_p99
  FROM analytics.focus_drop_user_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_user_thresholds)
)
INSERT INTO analytics.focus_drop_user_day_kpi
REPLACE WHERE analysis_date = ${analysis_date}
SELECT
  d.analysis_date,
  d.user_id,
  d.warning_session_count,
  d.critical_session_count,
  d.departure_gap_total,
  d.total_sessions,
  -- 개별 레벨 플래그
  CASE WHEN d.warning_session_count > 0
        AND d.warning_session_count > t.user_warning_session_count_p90
       THEN TRUE ELSE FALSE END AS is_warning_user,
  CASE WHEN d.critical_session_count > 0
        AND d.critical_session_count > t.user_critical_session_count_p95
       THEN TRUE ELSE FALSE END AS is_critical_user,
  CASE WHEN d.departure_gap_total > 0
        AND d.departure_gap_total > t.user_departure_gap_total_p99
       THEN TRUE ELSE FALSE END AS is_departure_user,
  -- ★ 배타적 최종 레벨
  CASE
    WHEN d.departure_gap_total > 0
         AND d.departure_gap_total > t.user_departure_gap_total_p99    THEN 'departure'
    WHEN d.critical_session_count > 0
         AND d.critical_session_count > t.user_critical_session_count_p95 THEN 'critical'
    WHEN d.warning_session_count > 0
         AND d.warning_session_count > t.user_warning_session_count_p90   THEN 'warning'
    ELSE 'normal'
  END AS user_focus_drop_level
FROM user_daily d
CROSS JOIN user_thresholds t;
```

### 7.6 유저 기준선 산출 (rolling 30일)

```sql
-- focus_drop__user_thresholds.sql
INSERT INTO analytics.focus_drop_user_thresholds
SELECT
  COALESCE((SELECT MAX(version) FROM analytics.focus_drop_user_thresholds), 0) + 1  AS version,
  CURRENT_TIMESTAMP()                              AS computed_at,
  FALSE                                            AS is_bootstrap,
  DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AS window_start,
  DATE_SUB(CURRENT_DATE(), 1)                      AS window_end,
  PERCENTILE(warning_session_count,  0.90)         AS user_warning_session_count_p90,
  PERCENTILE(critical_session_count, 0.95)         AS user_critical_session_count_p95,
  PERCENTILE(departure_gap_total,    0.99)         AS user_departure_gap_total_p99
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date BETWEEN DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AND DATE_SUB(CURRENT_DATE(), 1);
```

---

## 8. 모니터링 대시보드

### 8.1 일일 요약 뷰

```sql
-- 일일 KPI 현황 조회 (배타적 레벨 기준 — 중복 카운트 없음)
SELECT
  analysis_date,
  COUNT(*)                                                      AS total_labelers,
  SUM(CASE WHEN user_focus_drop_level = 'warning'   THEN 1 ELSE 0 END) AS warning_users,
  SUM(CASE WHEN user_focus_drop_level = 'critical'  THEN 1 ELSE 0 END) AS critical_users,
  SUM(CASE WHEN user_focus_drop_level = 'departure' THEN 1 ELSE 0 END) AS departure_users,
  ROUND(SUM(CASE WHEN user_focus_drop_level = 'warning'   THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS warning_pct,
  ROUND(SUM(CASE WHEN user_focus_drop_level = 'critical'  THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS critical_pct,
  ROUND(SUM(CASE WHEN user_focus_drop_level = 'departure' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS departure_pct
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date >= DATE_SUB(CURRENT_DATE(), 30)
GROUP BY analysis_date
ORDER BY analysis_date DESC;
```

### 8.2 사용자별 상세 조회

```sql
-- 특정 사용자의 최근 세션별 판정 현황
SELECT
  s.analysis_date,
  s.user_id,
  s.session_id,
  s.task_id,
  s.warning_gap_count,
  s.critical_gap_count,
  s.departure_gap_count,
  s.focus_drop_level
FROM analytics.focus_drop_session_tags s
WHERE s.user_id = ${target_user_id}
  AND s.analysis_date >= DATE_SUB(CURRENT_DATE(), 7)
ORDER BY s.analysis_date DESC, s.session_id;
```

### 8.3 추세 모니터링

```sql
-- 주간 추세: 배타적 레벨(user_focus_drop_level) 기준 사용자 비율 변화
SELECT
  DATE_TRUNC('week', analysis_date) AS week_start,
  COUNT(DISTINCT user_id) AS total_labelers,
  COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'warning'   THEN user_id END) AS warning_users,
  COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'critical'  THEN user_id END) AS critical_users,
  COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'departure' THEN user_id END) AS departure_users,
  ROUND(COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'warning'   THEN user_id END) / COUNT(DISTINCT user_id) * 100, 1) AS warning_pct,
  ROUND(COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'critical'  THEN user_id END) / COUNT(DISTINCT user_id) * 100, 1) AS critical_pct,
  ROUND(COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'departure' THEN user_id END) / COUNT(DISTINCT user_id) * 100, 1) AS departure_pct
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date >= DATE_SUB(CURRENT_DATE(), 90)
GROUP BY DATE_TRUNC('week', analysis_date)
ORDER BY week_start DESC;
```

---

## 9. 알림 기준

### 9.1 알림 레벨

| 레벨 | 조건 | 행동 |
|------|------|------|
| **INFO** | 당일 `user_focus_drop_level = 'warning'` 존재 | 일일 리포트에 포함 |
| **WARNING** | `user_focus_drop_level = 'critical'` 1명 이상 | 팀 리드 Slack 알림 |
| **CRITICAL** | `user_focus_drop_level = 'departure'` 존재 | 즉시 검토 요청 |
| **DRIFT** | `gap_p90/p95/p99` 기존 대비 ±20% 변동 | percentile 재산출 트리거 |

> 배타적 레벨 적용으로, 한 유저에게 중복 알림이 발생하지 않는다.

**DRIFT 대응 SOP** (`drift_status = 'RECALCULATE'` 감지 시):

1. **담당자**: 데이터 엔지니어 (파이프라인 소유자)
2. **확인**: §9.2 드리프트 쿼리 수동 실행 → 원인 파악 (온보딩? UX 변경? 계절성?)
3. **실행**: 정상적 분포 변화로 판단되면 `gap_percentiles` 수동 재실행 → 신규 gap_thresholds INSERT
4. **후속**: `session_thresholds` / `user_thresholds`를 다음 주 배치 전에 임시 재실행하여 2차 기준선도 갱신
5. **기록**: §13 버전업 원칙에 따라 변경 사유 기록

> §9.2의 7일 윈도우는 **급격한 분포 변화의 조기 경보**를 목적으로 한다. 완만한 drift(4\~5주)는 session_thresholds / user_thresholds의 주간 rolling 갱신 + 분기 정기 검토가 커버한다.

### 9.2 기준선 드리프트 감지

```sql
-- 현재 분포 vs 기준 비교
WITH recent_labeler_diffs AS (
  -- ★ §7.1과 동일한 JOIN 구조 (최근 7일 — 급격한 shift 조기 경보용; 완만한 drift는 session/user_thresholds rolling이 커버)
  SELECT
    UNIX_TIMESTAMP(c._raw:createdAt::TIMESTAMP) - UNIX_TIMESTAMP(
      LAG(c._raw:createdAt::TIMESTAMP) OVER (
        PARTITION BY c._raw:userId::STRING, c._raw:sessionId::STRING, c._raw:taskId::STRING
        ORDER BY c._raw:createdAt::TIMESTAMP
      )
    ) AS diff_sec
  FROM sv_nova_dev_an2_catalog.raw.raw_labelit__workspace_command c
  INNER JOIN sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_tasks t
    ON c._raw:taskId::STRING = t._id
  INNER JOIN sv_nova_dev_an2_catalog.raw.raw_labelit__gen2_assignments a
    ON t._raw:assignmentId::STRING = a._id
  WHERE c._is_deleted = false
    AND LOWER(a._raw:role::STRING) = 'labeler'
    AND CAST(c._raw:createdAt::TIMESTAMP AS DATE) >= DATE_SUB(CURRENT_DATE(), 7)
),
current_dist AS (
  SELECT
    PERCENTILE(diff_sec, 0.90) AS current_p90,
    PERCENTILE(diff_sec, 0.95) AS current_p95,
    PERCENTILE(diff_sec, 0.99) AS current_p99
  FROM recent_labeler_diffs
  WHERE diff_sec IS NOT NULL AND diff_sec > 0
),
baseline AS (
  SELECT gap_p90, gap_p95, gap_p99
  FROM analytics.focus_drop_gap_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_gap_thresholds)
)
SELECT
  ABS(c.current_p90 - b.gap_p90) / b.gap_p90 * 100 AS drift_p90_pct,
  ABS(c.current_p95 - b.gap_p95) / b.gap_p95 * 100 AS drift_p95_pct,
  ABS(c.current_p99 - b.gap_p99) / b.gap_p99 * 100 AS drift_p99_pct,
  CASE WHEN ABS(c.current_p90 - b.gap_p90) / b.gap_p90 > 0.20
         OR ABS(c.current_p95 - b.gap_p95) / b.gap_p95 > 0.20
         OR ABS(c.current_p99 - b.gap_p99) / b.gap_p99 > 0.20
       THEN 'RECALCULATE' ELSE 'STABLE' END AS drift_status
FROM current_dist c CROSS JOIN baseline b;
```

---

## 10. 운영 해석 원칙

### 10.1 판정 ≠ 확정

- `warning`/`critical` 판정은 **검토 필요 신호**이며, 저성과 확정이 아님
- 실제 해석 시 작업 맥락, task 특성, 운영 이슈를 함께 고려

### 10.2 도메인 특성 고려

- 3D point cloud annotation에서는 시점 탐색/회전/확인 시간이 command 로그에 반영되지 않음
- 따라서 개별 long gap 하나보다 **반복 패턴**을 우선 해석

### 10.3 feature별 해석

- OD: 객체 밀도 높음 → 짧은 gap이 정상
- LD: 연속 라인 작업 → 리듬성 갭 패턴
- RMD: 넓은 영역 탐색 → 상대적으로 긴 gap 허용 가능

---

## 11. 파라미터 관리

### 11.1 튜닝 가능 파라미터

| 파라미터 | 현재값 | 설명 |
|----------|--------|------|
| `min_event_count` | 10 | 세션 최소 이벤트 수 |
| `min_session_duration_sec` | 60 | 세션 최소 지속 시간 |
| `min_gap_count` | 5 | 분석 최소 gap 수 |
| `drift_threshold_pct` | 20 | 기준선 드리프트 알림 임계(%) |
| `feature_scope` | `all_features` | 기준 산출 범위 (feature별 분리 시 변경) |
| `rolling_window_days` | 30 | 세션/유저 기준선 산출 rolling 윈도우 |

### 11.2 feature별 분리 판단 기준

- feature 간 `gap_p90` 차이가 ±30% 이상 → 분리 산출
- `task._raw:policyId` → `annotation_policy._raw:feature` 조인으로 식별

---

## 12. 트러블슈팅

### 12.1 zero-inflation 문제

**증상**: `session_*_count_p90/p95/p99 = 0` → 해당 레벨의 gap이 1개만 있어도 전부 판정됨

> 예: `session_departure_count_p99 = 0`인 경우, `departure_gap_count > 0 AND > 0` = TRUE → departure gap 1개만으로 departure 세션 판정. Bootstrap 초기(7일 데이터) 또는 departure gap이 매우 드문 정상 구간에서 발생.

**해결** (warning / critical / departure 공통):
1. `min_gap_count` 파라미터 상향 (5 → 10)으로 짧은 세션 제거
2. `해당_gap_count > 0` 최소 조건은 이미 적용됨 (§7.4)
3. rolling window 기간 확대하여 기준선 재산출
4. **bootstrap 시 보수적 최솟값 적용**: `session_departure_count_p99 = 0`이면 최솟값 1로 대체

```sql
-- session_thresholds 실행 후 zero-inflation 보정 (선택적 후처리)
UPDATE analytics.focus_drop_session_thresholds
SET session_departure_count_p99 = GREATEST(session_departure_count_p99, 1),
    session_critical_count_p95  = GREATEST(session_critical_count_p95, 1),
    session_warning_count_p90   = GREATEST(session_warning_count_p90, 1)
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds)
  AND (session_departure_count_p99 = 0 OR session_critical_count_p95 = 0 OR session_warning_count_p90 = 0);
```

> 이 보정은 "threshold = 0이면 최솟값 1로 올린다"는 단순 규칙으로, `gap_count > 0 AND gap_count > 1` = `gap_count >= 2`가 되어 단일 gap 오탐을 방지한다.

### 12.2 오탐률 과다

**증상**: warning 판정 비율이 30% 이상

**해결**:
1. Labeler role 필터 정확성 확인 (gen2_assignments 조인 검증)
2. `gap_p90` 기준값이 너무 낮은지 확인 (2초 이하이면 비정상)
3. 특정 company/project의 UX 특성이 gap 분포를 왜곡하는지 확인

### 12.3 기준값 급변

**증상**: 신규 산출 percentile이 기존 대비 50% 이상 변동

**원인 후보**:
1. 신규 대량 Labeler 온보딩 (미숙련 패턴 유입)
2. 툴 UX 변경 (새 기능 추가로 gap 패턴 변화)
3. policy 변경으로 작업 방식 변화

### 12.4 기준선 테이블 부재 (초기 배포 시)

**증상**: `focus_drop_session_thresholds` 또는 `focus_drop_user_thresholds`에 데이터 없음 → session_tags / user_day_kpi 노트북 실행 시 CROSS JOIN 결과가 빈 행

**근본 원인**: 파이프라인 의존성 순환 구조

```
session_thresholds ← session_metrics 30일분 필요
user_thresholds    ← user_day_kpi 30일분 필요
session_tags       ← session_thresholds 필요
user_day_kpi       ← user_thresholds 필요  ← 자기 자신 30일분 필요 (순환)
```

**단계적 해결 — 3 Phase 배포**:

#### Phase A: Warm-up (Day 1~6)

- **실행**: `gap_percentiles` → `session_metrics` 만 일 단위 배치
- **목적**: session_metrics 데이터 축적
- **session_tags / user_day_kpi**: 실행하지 않음 (기준선 없음)
- **최소 요건**: Labeler 유효 세션 100개 이상 축적 확인

#### Phase B: Bootstrap (Day 7)

- **조건**: session_metrics에 최소 7일분 데이터 적재 확인
- **실행 순서** (순환 의존성 해소):
  1. `session_thresholds`를 `rolling_window_days = 7`로 임시 실행 (`is_bootstrap = TRUE`) → 세션 기준선 생성
  2. `session_tags`를 처음 실행 (session_thresholds 기준선 참조) → session_tags 생성
  3. **`user_thresholds`를 임시 기준값으로 수동 INSERT** → 유저 기준선 부트스트랩 (★ user_day_kpi보다 먼저)
     ```sql
     INSERT INTO analytics.focus_drop_user_thresholds VALUES (
       1, CURRENT_TIMESTAMP(), TRUE,
       DATE_SUB(CURRENT_DATE(), 7), DATE_SUB(CURRENT_DATE(), 1),
       1.0, 1.0, 3.0
       -- 근거: threshold=1 → count>1 필요 → warning/critical 세션 2회 이상,
       --       departure gap 4개 이상이어야 판정. 과탐지 방지 우선, Phase C에서 실데이터 대체.
     );
     ```
  4. `user_day_kpi`를 처음 실행 (user_thresholds 부트스트랩 기준선 참조) → user_day_kpi 생성
  5. 7일 누적 후 `user_thresholds`를 정식 rolling window로 재실행 → 부트스트랩 기준선 대체
- **주의**: Bootstrap 기준선은 `is_bootstrap = TRUE`로 마킹하여 정식 기준선과 구분

#### Phase C: Steady-state (Day 30+)

- **전환 조건**: session_metrics 30일분 + user_day_kpi 30일분 축적
- **실행**: `session_thresholds` / `user_thresholds`를 정식 30일 rolling window로 재실행 → Bootstrap 기준선 대체
- **이후**: 정상 스케줄 (`session_thresholds` / `user_thresholds` 주 1회, `session_metrics` / `session_tags` / `user_day_kpi` 일 1회) 전환

**폴백 동작 (session_tags / user_day_kpi)**:

```sql
-- session_tags / user_day_kpi에서 기준선 테이블이 비어있을 때의 방어 로직
WITH thresholds AS (
  SELECT session_warning_count_p90, session_critical_count_p95, session_departure_count_p99
  FROM analytics.focus_drop_session_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds)
)
-- thresholds CTE가 0행이면 CROSS JOIN 결과도 0행 → 판정 자체가 생략됨
-- 이 경우 session_tags 테이블에 당일 데이터가 적재되지 않으므로 알림 미발생 (safe fail)
-- ★ Silent failure 방지: 아래 모니터링 쿼리를 일 배치 마지막에 실행
```

**Bootstrap silent failure 감지 쿼리** (일 배치 마지막에 실행):

```sql
-- 기준선 부재로 인한 0행 적재 감지 → 운영자 알림 트리거
SELECT
  CASE
    WHEN (SELECT COUNT(*) FROM analytics.focus_drop_session_tags WHERE analysis_date = ${analysis_date}) = 0
     AND (SELECT COUNT(*) FROM analytics.focus_drop_session_metrics WHERE analysis_date = ${analysis_date}) > 0
    THEN 'ALERT: session_tags 0행 — 기준선 테이블(session_thresholds) 비어있음'
    WHEN (SELECT COUNT(*) FROM analytics.focus_drop_user_day_kpi WHERE analysis_date = ${analysis_date}) = 0
     AND (SELECT COUNT(*) FROM analytics.focus_drop_session_tags WHERE analysis_date = ${analysis_date}) > 0
    THEN 'ALERT: user_day_kpi 0행 — 기준선 테이블(user_thresholds) 비어있음'
    ELSE 'OK'
  END AS pipeline_health_status;
```

**Bootstrap 최소 요건 체크 쿼리**:

```sql
-- Phase B 진입 가능 여부 확인
SELECT
  COUNT(DISTINCT analysis_date) AS available_days,
  COUNT(*) AS total_sessions,
  CASE WHEN COUNT(DISTINCT analysis_date) >= 7 AND COUNT(*) >= 100
       THEN 'READY_FOR_BOOTSTRAP' ELSE 'WAIT' END AS bootstrap_status
FROM analytics.focus_drop_session_metrics;
```

---

## 13. 버전업 원칙

다음 조건 중 하나 이상 확인 시 기준 재검토 및 percentile 재산출:

- Labeler 표본이 기존 대비 50% 이상 증가
- 툴 UX 또는 작업 방식 변경
- `drift_status = 'RECALCULATE'` 연속 2주 감지
- 특정 feature에서 오탐/미탐 반복 보고
- 분기 정기 검토 시점

---

## 14. 트리거 키워드

다음 키워드가 요청에 포함되면 본 skill을 참조:

- "집중도", "focus drop", "집중도 저하", "focus"
- "gap 분석", "gap percentile", "긴 공백"
- "warning session", "critical session", "departure"
- "작업 이탈", "idle 탐지"
- "KPI 모니터링", "일일 리포트"

---

## 15. 빠른 참조

### 15.1 현황 확인 쿼리

```sql
-- 오늘의 focus drop KPI 요약 (배타적 레벨)
SELECT user_id, user_focus_drop_level, warning_session_count, critical_session_count, departure_gap_total
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date = CURRENT_DATE() - 1
  AND user_focus_drop_level != 'normal'
ORDER BY
  CASE user_focus_drop_level WHEN 'departure' THEN 1 WHEN 'critical' THEN 2 WHEN 'warning' THEN 3 END;
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
  warning_gap_count, critical_gap_count, departure_gap_count,
  focus_drop_level
FROM analytics.focus_drop_session_tags
WHERE user_id = :user_id
  AND analysis_date = :date
ORDER BY
  CASE focus_drop_level WHEN 'departure' THEN 1 WHEN 'critical' THEN 2 WHEN 'warning' THEN 3 ELSE 4 END;
```
