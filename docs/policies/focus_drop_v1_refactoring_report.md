# Labeler 작업 집중도 저하 탐지 — v1.0 전환 리팩토링 보고서

**문서 상태**: Draft  
**작성일**: 2026-04-23  
**적용 범위**: `projects/nova_log_analytics` — `anomaly_detection_runner.py` 내 집중도 탐지 로직 분리 및 KPI Metric 체계 재설계  
**선행 문서**:
- `labeler_focus_drop_policy.md` (v0.9)
- `labeler_focus_drop_concept_design.md` (v1.0 Draft)
- `labeler_focus_drop_metric_design.md` (v1.0 Draft)

---

## 1. 목적

본 보고서는 `anomaly_detection_runner.py`의 STEP 8b에 내재된 v0.9 집중도 저하 탐지 로직을 v1.0 설계안 기준으로 재설계하기 위한 근거와 구현 방향을 정리한다.

v1.0 전환의 핵심 목표는 다음과 같다.

- 절대값 기반 임계값에서 **분포 기반 percentile 체계**로 전환
- 사용자 전체 평균 집계에서 **세션 단위 반복성 판정**으로 중심 이동
- 단일 `warning` 레벨에서 **warning / critical / departure 3단계 심각도**로 확장
- anomaly runner 내 임베딩 구조에서 **독립 KPI 파이프라인**으로 분리

---

## 2. 현황 분석 — v0.9 로직

### 2.1 위치

`anomaly_detection_runner.py` STEP 8 "작업 집중도 이상" 블록

- **STEP 8a** (line 558~580): 스테일 세션 탐지 (`gap > 36,000초`)
- **STEP 8b** (line 582~609): 집중도 저하 사용자 탐지 → **분리 및 재설계 대상**

### 2.2 현재 로직

```sql
WITH with_diff AS (
  SELECT user_name, session_id, task_id,
         UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
           LAG(event_time) OVER (PARTITION BY session_id, task_id ORDER BY event_time)
         ) AS diff_sec
  FROM events
),
user_stats AS (
  SELECT user_name,
         AVG(diff_sec)                                    AS avg_gap,
         SUM(CASE WHEN diff_sec > 300 THEN 1 ELSE 0 END) AS gaps_5min
  FROM with_diff WHERE diff_sec IS NOT NULL
  GROUP BY user_name
)
SELECT COUNT(*) AS low_focus_users
FROM user_stats
WHERE avg_gap > 30 AND gaps_5min > 10
```

**스코어링 연결**: `save_result(step_id=3, "집중도저하", "S2", "warning")` → B. 수집 시간 정합성으로 병합

### 2.3 v0.9 로직의 한계

| 항목 | 내용 |
|------|------|
| **집계 단위** | `user_name` 전체 평균 — 세션 내 반복성 패턴을 희석시킴 |
| **판정 기준** | `avg_gap > 30s AND gaps_5min > 10` 절대값 고정 — 분포 변화 반영 불가 |
| **역할 구분** | role 필터 없음 — manager/reviewer가 Labeler 기준으로 오탐됨 |
| **심각도 구분** | 단일 `warning` — warning / critical / departure 미분리 |
| **스코어링 위치** | `step_id=3` 시간 정합성으로 병합 — 집중도 KPI 독립성 훼손 |
| **보정 부재** | 세션 길이 차이에 대한 ratio 보정 없음 |

> `labeler_focus_drop_policy.md §7`에서도 이 한계를 명시하고 있으며, 향후 percentile 기반 보완 방향을 제시하고 있다.

---

## 3. v1.0 전환 타당성 검토

### 3.1 설계 원칙 정합성

v1.0 설계 문서에서 정의한 핵심 원칙과 현재 runner 구조의 정합성을 검토한다.

| v1.0 설계 원칙 | 현재 runner 상태 | 전환 필요 여부 |
|---------------|----------------|:---:|
| 분포 기반 percentile 경계 | 절대값 고정 임계값 | **필요** |
| count 중심 세션 판정 | 사용자 전체 평균 | **필요** |
| ratio 보조 보정 | 없음 | **필요** |
| Labeler role 한정 | role 필터 없음 | **필요** |
| warning / critical / departure 분리 | 단일 warning | **필요** |
| observation 판정 레벨 미사용 | 해당 없음 (N/A) | — |
| session_avg_gap 정식 판정 제외 | 정식 판정에 avg_gap 사용 중 | **필요** |

**결론**: 현재 v0.9 로직은 v1.0 설계 원칙 전체 항목과 충돌한다. 부분 수정이 아닌 **전면 재설계**가 타당하다.

### 3.2 분리 타당성

현재 runner는 **feature 단위** (`od / ld / rmd`) anomaly를 처리하도록 설계되어 있다. 반면 집중도 탐지는 **Labeler role 단위** 분석이 기본 단위다. 두 처리 단위가 다르기 때문에 runner 내 임베딩 구조는 구조적으로 맞지 않는다.

또한 v1.0 로직은 두 단계의 percentile 계산을 요구한다.

- **1차**: `diff_sec` 분포 → `gap_p75 / p90 / p95 / p99` 산출
- **2차**: 세션 집계 지표 분포 → `session_warning_count_p90` 등 산출

이 구조는 runner에 임베딩하면 쿼리 복잡도가 급증하고 재사용성도 낮아진다. **독립 파이프라인**으로 분리하는 것이 타당하다.

### 3.3 오탐 원인 확인

현재 runner에서 탐지된 집중도 저하 대상은 manager/reviewer 4명이다. 이는 역할 특성상 이벤트 간격이 길어지는 것이 자연스럽기 때문이다. Labeler role만 필터링하면 이 오탐은 구조적으로 해소된다.

> `labeler_focus_drop_policy.md §3`: "Reviewer, Manager 등 타 역할의 패턴은 참고 정보로 활용하되, Labeler 저하 탐지 기준의 직접 임계값은 Labeler 관찰값을 우선 적용한다."

---

## 4. v1.0 KPI Metric 체계

### 4.1 지표 계층 구조

v1.0에서는 세 계층의 지표를 분리하여 관리한다.

```
[1차 percentile]  gap_p75 / gap_p90 / gap_p95 / gap_p99
        ↓  각 gap을 4개 구간으로 분류
[세션 지표]       warning_gap_count / critical_gap_count / departure_gap_count
                  warning_gap_ratio / critical_gap_ratio / departure_gap_ratio
        ↓  세션 분포에 2차 percentile 적용
[세션 판정]       is_warning_session / is_critical_session / is_departure_session
        ↓  사용자 일 단위 집계
[사용자 KPI]      warning_session_count / critical_session_count / departure_gap_total
        ↓  사용자 분포에 2차 percentile 적용
[사용자 판정]     is_warning_user / is_critical_user / is_departure_user
```

### 4.2 gap 구간 정의

| 구간 | 조건 | 역할 |
|------|------|------|
| 정상 | `diff_sec <= gap_p75` | 정상 작업 흐름 |
| observation | `gap_p75 < diff_sec <= gap_p90` | 분석용 보조 — 판정 레벨 미사용 |
| warning | `gap_p90 < diff_sec <= gap_p95` | warning_gap_count 산출 기준 |
| critical | `gap_p95 < diff_sec <= gap_p99` | critical_gap_count 산출 기준 |
| departure | `diff_sec > gap_p99` | departure_gap_count 산출 기준 |

### 4.3 세션 판정 구조

| 판정 | 주판정 조건 | 보조 조건 | 최소 조건 |
|------|-----------|-----------|----------|
| warning 세션 | `warning_gap_count > session_warning_count_p90` | `warning_gap_ratio > session_warning_ratio_p90` | `warning_gap_count > 0` |
| critical 세션 | `critical_gap_count > session_critical_count_p95` | `critical_gap_ratio > session_critical_ratio_p95` | `critical_gap_count > 0` |
| departure 세션 | `departure_gap_count > session_departure_count_p99` | `departure_gap_ratio > session_departure_ratio_p99` | `departure_gap_count > 0` |

### 4.4 사용자 일 단위 판정 구조

| 판정 | 조건 | 최소 조건 |
|------|------|----------|
| warning 사용자 후보 | `warning_session_count > user_warning_session_count_p90` | `warning_session_count > 0` |
| critical 사용자 후보 | `critical_session_count > user_critical_session_count_p95` | `critical_session_count > 0` |
| departure 사용자 후보 | `departure_gap_total > user_departure_gap_total_p99` | `departure_gap_total > 0` |

### 4.5 판정에서 제외하는 지표

v1.0에서 다음 지표는 정식 판정 기준에서 제외하고 참고용 진단 지표로만 유지한다.

- `session_avg_gap` — 현재 v0.9의 핵심 판정 지표이나 v1.0에서 제외
- `user_day_avg_gap`
- 단일 gap 1회 발생 여부만으로 하는 판정
- 절대 count 고정값만을 사용한 판정

---

## 5. 리팩토링 구현 계획

### 5.1 runner 수정 사항

**제거 대상**: STEP 8b 블록 전체 (lines 582~609)

```python
# 제거: v1.0으로 이관
# conc_row = spark.sql("""...""").collect()[0]
# if conc_row.low_focus_users > 0: ...
```

**수정 대상**: `step8_details` 딕셔너리

```python
# Before
step8_details = {"stale_sessions": stale_count, "low_focus_users": conc_row.low_focus_users}

# After
step8_details = {"stale_sessions": stale_count, "focus_drop": "v1.0_pipeline"}
```

**수정 대상**: 보고서 마크다운 lines 947

```python
# Before
f"| STEP 8b 집중도저하 | {step8_details['low_focus_users']}명 | → S3 (B) |"

# After
f"| STEP 8b 집중도저하 | → v1.0 KPI 파이프라인으로 이관 | analytics.focus_drop_user_day_kpi |"
```

### 5.2 신규 파이프라인 구조

```
[독립 실행 — Labeler 집중도 KPI v1.0]

06_focus_drop__gap_percentiles.sql
  목적: diff_sec 분포에서 gap_p75/p90/p95/p99 산출
  실행: 충분한 Labeler 표본 확보 후 1회 (분포 변화 시 재실행)
  출력: analytics.focus_drop_gap_thresholds

        ↓ (gap_thresholds 확보 후 일 단위 배치)

07_focus_drop__session_metrics.sql
  목적: 세션별 gap 분류 및 count/ratio 지표 산출
  실행: 일 단위 배치 (analysis_date 파라미터)
  출력: analytics.focus_drop_session_metrics

        ↓

08_focus_drop__session_tags.sql
  목적: 세션 count 분포의 2차 percentile 산출 후 세션 판정
  실행: 일 단위 배치
  출력: analytics.focus_drop_session_tags

        ↓

09_focus_drop__user_day_kpi.sql
  목적: 사용자 일 단위 반복성 집계 및 최종 KPI 판정
  실행: 일 단위 배치
  출력: analytics.focus_drop_user_day_kpi
```

### 5.3 신규 Delta 테이블 목록

| 테이블명 | 갱신 전략 | 설명 |
|---------|-----------|------|
| `analytics.focus_drop_gap_thresholds` | 버전업 시 INSERT | gap_p75/p90/p95/p99 기준값 이력 관리 |
| `analytics.focus_drop_session_metrics` | CREATE OR REPLACE (일 단위) | 세션별 count/ratio 지표 |
| `analytics.focus_drop_session_tags` | CREATE OR REPLACE (일 단위) | 세션 warning/critical/departure 판정 |
| `analytics.focus_drop_user_day_kpi` | CREATE OR REPLACE (일 단위) | 사용자 일 단위 최종 KPI |

### 5.4 노트북별 핵심 로직 요약

#### 06 — gap_percentiles

```sql
-- Labeler role 필터링 후 diff_sec 분포 산출
WITH labeler_diffs AS (
  SELECT
    UNIX_TIMESTAMP(event_time) -
    UNIX_TIMESTAMP(LAG(event_time) OVER (
      PARTITION BY user_id, session_id, task_id ORDER BY event_time
    )) AS diff_sec
  FROM stg_labelit__events
  WHERE role = 'Labeler'
    AND diff_sec IS NOT NULL AND diff_sec > 0
)
SELECT
  PERCENTILE(diff_sec, 0.50) AS gap_p50,
  PERCENTILE(diff_sec, 0.75) AS gap_p75,
  PERCENTILE(diff_sec, 0.90) AS gap_p90,
  PERCENTILE(diff_sec, 0.95) AS gap_p95,
  PERCENTILE(diff_sec, 0.99) AS gap_p99
FROM labeler_diffs;
```

#### 07 — session_metrics

```sql
-- gap 구간 분류 → 세션 단위 count/ratio 집계
CASE
  WHEN diff_sec <= gap_p75  THEN 'normal'
  WHEN diff_sec <= gap_p90  THEN 'observation'
  WHEN diff_sec <= gap_p95  THEN 'warning'
  WHEN diff_sec <= gap_p99  THEN 'critical'
  ELSE 'departure'
END AS gap_severity
```

#### 08 — session_tags

```sql
-- 2차 percentile 적용 → 세션 판정
CASE WHEN warning_gap_count > 0
      AND warning_gap_count > PERCENTILE(warning_gap_count, 0.90) OVER ()
     THEN TRUE ELSE FALSE END AS is_warning_session
```

#### 09 — user_day_kpi

```sql
-- 세션 판정 집계 → 사용자 일 KPI
SUM(CASE WHEN is_warning_session  THEN 1 ELSE 0 END) AS warning_session_count,
SUM(CASE WHEN is_critical_session THEN 1 ELSE 0 END) AS critical_session_count,
SUM(departure_gap_count)                              AS departure_gap_total
```

---

## 6. v0.9 대비 변화 요약

| 항목 | v0.9 (현재) | v1.0 (목표) |
|------|------------|------------|
| **위치** | `anomaly_detection_runner.py` STEP 8b 내 임베딩 | 독립 KPI 파이프라인 (06~09 노트북) |
| **집계 단위** | 사용자 전체 평균 | 세션 단위 반복성 |
| **판정 기준** | `avg_gap > 30s AND gaps_5min > 10` 절대값 | 분포 기반 percentile 경계 |
| **핵심 지표** | `avg_gap`, `gaps_5min` | `warning/critical/departure_gap_count` |
| **보조 지표** | 없음 | `warning/critical/departure_gap_ratio` |
| **역할 필터** | 없음 (전 사용자) | Labeler role 한정 |
| **심각도** | 단일 warning | warning / critical / departure 3단계 |
| **스코어링 연결** | `step_id=3` B. 시간 정합성으로 병합 | 독립 KPI 테이블로 분리 관리 |
| **오탐 구조** | manager/reviewer 오탐 내재 | 역할 필터로 구조적 해소 |

---

## 7. 구현 전 확인 사항

v1.0 파이프라인 구현 전 다음 사항을 확인해야 한다.

### 7.1 role 컬럼 존재 여부

`stg_labelit__events`에 `role` 컬럼이 없는 경우 `user_id` → role 매핑 테이블 조인이 필요하다. 매핑 테이블의 위치와 최신성을 사전에 확인한다.

### 7.2 Labeler 표본 크기 기준

`gap_p90 / p95 / p99`의 신뢰도 확보를 위한 최소 표본 수 기준을 정의한다. 표본이 충분하지 않은 상태에서 산출한 percentile은 기준선으로 사용하기 어렵다.

### 7.3 zero-inflation 보정 기준

세션 내 gap 수가 매우 적은 경우 `warning_gap_count = 0` 이 대부분을 차지해 2차 percentile 값 자체가 `0`이 될 수 있다. 세션을 분석 대상으로 포함하기 위한 **최소 gap 수 기준** (`min_gap_count`)을 협의 후 파라미터로 관리한다.

### 7.4 feature별 분리 여부

od / rmd / ld feature 간 gap 분포 차이가 유의미하다면 `feature_scope = 'all_features'` 단일 기준 대신 feature별 percentile 기준을 분리 산출하는 방향을 검토한다.

---

## 8. 버전 히스토리

| 버전 | 일자 | 상태 | 주요 내용 |
|------|------|------|-----------|
| `v0.9` | 2026-04-22 | Existing | anomaly_detection_runner STEP 8b — 절대값 기반 집중도 저하 탐지 운영 중 |
| `v1.0-refactoring` | 2026-04-23 | Draft | percentile 기반 독립 KPI 파이프라인 전환 설계 및 타당성 검토 |
