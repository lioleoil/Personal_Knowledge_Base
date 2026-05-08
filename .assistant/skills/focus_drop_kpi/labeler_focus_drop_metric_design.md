# Labeler 작업 집중도 저하 탐지 메트릭 설계안 v1.0

**문서 상태**: Draft  
**작성자**: OpenAI Codex  
**적용 범위**: `projects/nova_log_analytics` 내 Labeler role 대상 작업 집중도 저하 탐지 메트릭 설계  
**선행 문서**: `labeler_focus_drop_concept_design.md`

---

## 1. 목적

본 문서는 `Labeler 작업 집중도 저하 탐지 개념 정의 설계안 v1.0`에서 정의한 개념을 실제 분석 로직으로 옮기기 위한 메트릭 구조와 산출 원칙을 정의한다.

본 문서의 초점은 고정 숫자를 확정하는 것이 아니라, `percentile`, `count`, `ratio`가 각각 어떤 역할로 쓰이는지 명확히 하고, warning과 critical 중심의 판정 구조를 정리하는 데 있다.

---

## 2. 기본 원칙

- 개별 gap의 심각도 구간은 `percentile`로 정의한다.
- 세션 저하 판정의 핵심은 `count`로 정의한다.
- 세션 길이 차이 보정은 `ratio`로 수행한다.
- `observation`은 분석용 보조 구간으로만 유지한다.
- 정식 저하 판정의 중심은 `warning`, `critical`, `departure`에 둔다.
- `session_avg_gap`, `user_day_avg_gap`은 참고용 진단 지표로만 유지하고, 정식 판정식에서는 제외한다.

---

## 3. gap 구간 정의

개별 `diff_sec`는 Labeler 정상군 분포 기준 다음과 같이 구간화한다.

- `diff_sec <= gap_p75`: 정상 공백
- `gap_p75 < diff_sec <= gap_p90`: observation 공백
- `gap_p90 < diff_sec <= gap_p95`: warning 공백
- `gap_p95 < diff_sec <= gap_p99`: critical 공백
- `diff_sec > gap_p99`: departure 또는 extreme 공백

이때 `gap_p90`, `gap_p95`, `gap_p99`는 severity 태그의 직접 기준선으로 사용한다.

---

## 4. 지표 역할 정의

### 4.1 percentile

`percentile`은 개별 gap의 심각도 경계값을 정의하는 기준선이다.

예시:

- `gap_p90`: warning gap 시작점
- `gap_p95`: critical gap 시작점
- `gap_p99`: departure gap 시작점

즉 percentile은 판정 결과가 아니라, 판정을 위한 구간 경계 역할을 한다.

### 4.2 count

`count`는 특정 severity 구간의 gap이 세션 안에서 몇 번 반복되었는지를 나타내는 핵심 판정 지표다.

예시:

- `warning_gap_count`
- `critical_gap_count`
- `departure_gap_count`

세션 저하 판정의 중심은 `count`에 둔다.

### 4.3 ratio

`ratio`는 전체 gap 수 대비 severity gap이 차지하는 비중을 나타내는 보조 지표다.

예시:

- `warning_gap_ratio`
- `critical_gap_ratio`
- `departure_gap_ratio`

ratio는 세션 길이가 매우 짧거나 매우 긴 경우 count 해석이 왜곡되는 문제를 보완하기 위해 사용한다.

### 4.4 observation

`observation`은 정식 판정 레벨이 아니라 분석용 보조 구간이다.

- observation gap은 집계 가능하다.
- observation 세션 태그는 운영상 필수 판정 레벨로 사용하지 않는다.
- observation은 추세 분석과 기준 조정 검토에 사용한다.

### 4.5 percentile 표기 규칙

개별 gap 길이 분포의 percentile과 세션/사용자 집계 지표 분포의 percentile은 서로 다른 이름으로 표기한다.

예시:

- gap 분포: `gap_p90`, `gap_p95`, `gap_p99`
- 세션 count 분포: `session_warning_count_p90`, `session_critical_count_p95`
- 세션 ratio 분포: `session_warning_ratio_p90`, `session_critical_ratio_p95`
- 사용자 분포: `user_warning_session_count_p90`, `user_departure_gap_total_p99`

---

## 5. 세션 단위 메트릭

### 5.1 관찰용 메트릭

- `observation_gap_count`

### 5.2 핵심 판정 메트릭

- `warning_gap_count`
- `critical_gap_count`
- `departure_gap_count`

### 5.3 보조 보정 메트릭

- `warning_gap_ratio`
- `critical_gap_ratio`
- `departure_gap_ratio`

### 5.4 참고용 진단 메트릭

- `session_avg_gap`
- `session_p95_gap`

참고용 진단 메트릭은 리포트와 해석에는 활용할 수 있으나, v1.0 정식 판정 기준에는 포함하지 않는다.

---

## 6. 사용자 일 단위 메트릭

### 6.1 핵심 반복성 메트릭

- `warning_session_count`
- `critical_session_count`
- `departure_gap_total`

### 6.2 참고용 진단 메트릭

- `user_day_avg_gap`

사용자 일 단위 판정 역시 반복성 지표 중심으로 구성하며, 평균 지표는 참고용으로만 유지한다.

---

## 7. 세션 판정 구조

### 7.1 warning 세션

warning 세션은 `warning_gap_count`를 핵심 기준으로 판정한다.

추천 구조:

- 주판정: `warning_gap_count > session_warning_count_p90`
- 보조판정: `warning_gap_ratio > session_warning_ratio_p90`
- 최소 조건: `warning_gap_count > 0`
- 필요 시 최소 세션 길이 또는 최소 gap 수 조건 추가

예시 표현:

```text
warning_gap_count > session_warning_count_p90
```

필요 시 아래를 보조 조건으로 추가한다.

```text
warning_gap_ratio > session_warning_ratio_p90
AND warning_gap_count > 0
```

### 7.2 critical 세션

critical 세션은 `critical_gap_count`를 핵심 기준으로 판정한다.

추천 구조:

- 주판정: `critical_gap_count > session_critical_count_p95`
- 보조판정: `critical_gap_ratio > session_critical_ratio_p95`
- 최소 조건: `critical_gap_count > 0`
- 필요 시 최소 세션 길이 또는 최소 gap 수 조건 추가

예시 표현:

```text
critical_gap_count > session_critical_count_p95
```

필요 시 아래를 보조 조건으로 추가한다.

```text
critical_gap_ratio > session_critical_ratio_p95
AND critical_gap_count > 0
```

### 7.3 departure 세션

departure 세션은 `departure_gap_count`를 핵심 기준으로 판정한다.

추천 구조:

- 주판정: `departure_gap_count > session_departure_count_p99`
- 보조판정: `departure_gap_ratio > session_departure_ratio_p99`
- 최소 조건: `departure_gap_count > 0`
- 필요 시 최소 세션 길이 또는 최소 gap 수 조건 추가

예시 표현:

```text
departure_gap_count > session_departure_count_p99
```

필요 시 아래를 보조 조건으로 추가한다.

```text
departure_gap_ratio > session_departure_ratio_p99
AND departure_gap_count > 0
```

### 7.4 제외 원칙

다음 지표는 v1.0 정식 세션 판정 기준에서 제외한다.

- `session_avg_gap`
- 단일 gap 1회 발생 여부만으로 하는 판정
- 절대 count 고정값만을 사용한 판정

### 7.5 zero-inflation 보정 원칙

warning, critical, departure gap은 실제 운영 데이터에서 드물게 나타날 수 있으므로, 세션 분포 percentile 값 자체가 `0`이 되는 경우가 발생할 수 있다.

이 경우 다음 원칙을 함께 적용한다.

- count 기반 판정에는 항상 `해당 count > 0` 조건을 함께 둔다.
- 필요 시 최소 세션 길이 또는 최소 gap 수 조건을 함께 둔다.
- ratio는 count가 0인 세션을 직접 판정하지 않고, count 조건을 통과한 세션에 대한 보조 지표로 사용한다.

---

## 8. 사용자 일 단위 판정 구조

### 8.1 warning 사용자 후보

- 주판정: `warning_session_count > user_warning_session_count_p90`
- 최소 조건: `warning_session_count > 0`

### 8.2 critical 사용자 후보

- 주판정: `critical_session_count > user_critical_session_count_p95`
- 최소 조건: `critical_session_count > 0`

### 8.3 departure 사용자 후보

- 주판정: `departure_gap_total > user_departure_gap_total_p99`
- 최소 조건: `departure_gap_total > 0`

### 8.4 제외 원칙

다음 지표는 v1.0 정식 사용자 판정 기준에서 제외한다.

- `user_day_avg_gap`
- 하루 평균 gap만으로 하는 사용자 판정

---

## 9. percentile 적용 계층

v1.0에서는 percentile이 두 계층에 걸쳐 적용된다.

### 9.1 1차 percentile

개별 gap 길이 분포에 적용한다.

- `gap_p75`, `gap_p90`, `gap_p95`, `gap_p99`
- 목적: gap severity 구간 정의

### 9.2 2차 percentile

세션 및 사용자 집계 지표 분포에 적용한다.

- `warning_gap_count distribution`
- `critical_gap_count distribution`
- `departure_gap_count distribution`
- 필요 시 각 ratio distribution

목적:

- 세션 저하 판정 기준 정의
- 사용자 일 단위 반복성 판정 기준 정의

---

## 10. 권장 산출 순서

1. Labeler role만 필터링한 로그를 준비한다.
2. `diff_sec` 분포에서 `gap_p75`, `gap_p90`, `gap_p95`, `gap_p99`를 계산한다.
3. 각 gap을 observation, warning, critical, departure로 분류한다.
4. 세션별 `warning_gap_count`, `critical_gap_count`, `departure_gap_count`를 집계한다.
5. 세션별 ratio 지표를 함께 산출한다.
6. 각 count와 ratio의 세션 분포 percentile을 계산하고 `session_warning_count_p90`, `session_critical_count_p95`, `session_departure_count_p99` 등을 산출한다.
7. 세션 판정 결과를 바탕으로 사용자 일 단위 반복성 지표를 집계한다.
8. 사용자 일 단위 분포 percentile을 계산하고 `user_warning_session_count_p90`, `user_critical_session_count_p95`, `user_departure_gap_total_p99` 등을 산출한다.
9. zero-inflation 여부를 점검하고 최소 세션 길이 또는 최소 gap 수 조건을 보정한다.
10. 샘플 검토를 통해 오탐과 미탐을 조정한다.

---

## 11. 운영 해석 원칙

- warning과 critical은 실제 저하 판정의 중심 태그로 사용한다.
- departure는 작업 이탈 또는 extreme 구간 후보를 나타내는 별도 보조 태그로 사용한다.
- observation은 리포트, 추세, 기준 튜닝용 분석 지표로만 유지한다.
- 최종 운영 해석에서는 세션의 실제 작업 맥락과 task 특성을 함께 검토한다.

---

## 12. 향후 보완 방향

v1.0에서는 percentile 기준을 다음과 같이 고정한다.

- `warning`: `p90`
- `critical`: `p95`
- `departure`: `p99`

향후 보완 대상은 다음과 같다.

- 최소 세션 길이 또는 최소 gap 수 조건
- feature별 분리 기준 여부
- task complexity 보정 여부
- ratio 보조 조건의 적용 방식

---

## 13. 버전 히스토리

| 버전 | 일자 | 상태 | 주요 내용 |
|------|------|------|-----------|
| `v1.0-metric-design` | 2026-04-22 | Draft | percentile, count, ratio의 역할 분리 및 count 중심 판정 구조 정리 |
