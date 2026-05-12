# Labeler 작업 집중도 저하 탐지 개념 정의 설계안 v1.0

**문서 상태**: Released (v1.0)  
**작성자**: OpenAI Codex  
**적용 범위**: `projects/nova_log_analytics` 내 Labeler role 대상 작업 집중도 저하 탐지 기준 고도화 설계  
**선행 문서**: `labeler_focus_drop_policy.md`

---

## 1. 목적

본 문서는 Labeler 작업 로그를 기반으로 `작업 집중도 저하 구간`을 보다 정교하게 탐지하기 위한 `v1.0 개념 설계안`을 정의한다.

v0.9가 anomaly 문서 관찰값을 기반으로 한 운영 기준이라면, v1.0은 Labeler 실측 로그 분포를 기반으로 `percentile 중심 기준 체계`를 수립하는 것을 목표로 한다.

---

## 2. 설계 방향

v1.0의 핵심 방향은 다음과 같다.

- `절대 고정 임계값` 중심 기준에서 `분포 기반 기준`으로 전환한다.
- `집중도 자체의 측정`보다 `집중도 저하 신호 탐지`를 우선 목표로 둔다.
- 개별 gap 하나만으로 판정하지 않고, `정상 분포 대비 긴 gap의 반복 발생`을 함께 본다.
- 3D point cloud annotation 특성을 반영하여 탐색, 판단, 시점 조정 등 비명시적 작업 시간을 고려한 해석 원칙을 둔다.

---

## 3. 기본 전제

현재 수집 데이터는 command 로그 기반이며, 주로 다음 행위를 포함한다.

- 객체 생성
- 객체 수정
- 객체 삭제
- grouping
- undo
- redo

반면 다음 행위는 현재 기준에서 충분히 수집되지 않거나 직접 포함되지 않는다.

- 마우스 클릭
- 마우스 휠
- 시점 이동
- 화면 탐색
- 객체 확인
- 판단 및 사고 시간

따라서 `무커맨드 시간 = 비집중 또는 idle`로 직접 해석해서는 안 되며, 분포 기반 저하 탐지 기준이 필요하다.

---

## 4. v1.0 핵심 개념

### 4.1 작업 집중도 저하

작업 집중도 저하란 Labeler의 정상 작업 로그 분포 대비 비정상적으로 긴 이벤트 간 공백이 반복적으로 발생하여 유효 작업 흐름이 약화된 상태를 의미한다.

### 4.2 작업 집중도 저하 구간

작업 집중도 저하 구간은 Labeler 정상군 분포 기준 상위 꼬리 영역에 해당하는 긴 gap이 세션 내에서 반복적으로 관측되는 구간을 의미한다.

### 4.3 작업 이탈 (Idle)

작업 이탈(Idle)은 연속 이벤트 간격이 **3분(180초) 이상**인 gap으로, 작업자가 물리적으로 자리를 비웠거나 세션을 유지한 채 실질적인 작업이 중단된 상태를 의미한다. percentile 기반 집중도 저하 구간(light·heavy)과 달리, 협의된 고정 임계값으로 정의된다.

---

## 5. 분석 단위

v1.0에서는 다음 3개 단위를 구분한다.

### 5.1 개별 gap 단위

- 연속 이벤트 간 시간 차 `diff_sec`
- 분포 기반 경계 산출의 기본 단위

### 5.2 세션 단위

- `user + session + task` 기준
- 세션 내 긴 공백의 반복 횟수와 비율을 해석하는 기본 단위

### 5.3 사용자 일 단위

- 사용자 1일 기준 집계
- 저하 세션 반복 여부를 요약하는 상위 단위

---

## 6. 핵심 지표

### 6.1 개별 gap 지표

#### `diff_sec`

- 동일 세션/작업 내 연속 이벤트 간 시간 차
- 모든 percentile 계산의 기본 모수

### 6.2 세션 지표

#### `observation_gap_count`

- `p75 초과 ~ p90 이하` 구간에 해당하는 gap 수
- 추세 관찰용 보조 지표이며 직접적인 저하 판정 태그로 사용하지 않는다

#### `light_gap_count`

- `p90 초과 ~ p95 이하` 구간에 해당하는 gap 수
- `light` 판정의 핵심 반복성 지표

#### `heavy_gap_count`

- `p95 초과 ~ p99 이하` 구간에 해당하는 gap 수
- `heavy` 판정의 핵심 반복성 지표

#### `idle_gap_count`

- `diff_sec ≥ 180`(3분 고정 임계값) 구간에 해당하는 gap 수
- `idle` 판정의 핵심 반복성 지표

#### `light_gap_ratio`

- 세션 내 전체 gap 중 `light` 구간 gap의 비율
- 세션 길이 차이를 보정하기 위한 보조 지표

#### `heavy_gap_ratio`

- 세션 내 전체 gap 중 `heavy` 구간 gap의 비율
- 세션 길이 차이를 보정하기 위한 보조 지표

#### `idle_gap_ratio`

- 세션 내 전체 gap 중 `idle` 구간 gap의 비율
- 세션 길이 차이를 보정하기 위한 보조 지표

### 6.3 사용자 일 단위 지표

#### `light_session_count`

- 하루 동안 `light` 세션으로 판정된 세션 수

#### `heavy_session_count`

- 하루 동안 `heavy` 세션으로 판정된 세션 수

#### `idle_gap_total`

- 하루 동안 관측된 `idle` gap(≥ 180초) 총합

---

## 7. percentile 기반 기준 구조

### 7.1 분포 산출 대상

기준 산출 시 다음 조건을 적용한다.

- 대상 role: `Labeler`
- 기준 기간: 충분한 표본이 확보된 안정 구간
- 필요 시 feature별 분포 분리 산출 가능

### 7.2 gap percentile

v1.0에서는 최소 다음 percentile을 산출한다.

- `p50`
- `p75`
- `p90`
- `p95`
- `p99`

문서 내에서는 개별 gap 길이 분포의 percentile을 다음과 같이 표기한다.

- `gap_p50`
- `gap_p75`
- `gap_p90`
- `gap_p95`
- `gap_p99`

각 gap percentile의 해석은 다음과 같다.

- `gap_p50`: 일반적인 작업 리듬의 중앙값
- `gap_p75`: 정상 범위 상단의 관찰 경계
- `gap_p90`: `light` 구간 시작점
- `gap_p95`: `heavy` 구간 시작점
- `gap_p99`: (참고 진단용) 분류 경계로 사용하지 않음 — idle 구간은 고정 기준 180s로 대체

### 7.3 집계 percentile 표기

세션 및 사용자 집계 지표 분포의 percentile은 개별 gap percentile과 구분하여 표기한다.

예시:

- `session_light_count_p90`
- `session_light_ratio_p90`
- `session_heavy_count_p95`
- `session_idle_count_p99`
- `user_light_session_count_p90`
- `user_heavy_session_count_p95`
- `user_idle_gap_total_p99`

---

## 8. gap 해석 원칙

### 8.1 정상 공백

```text
diff_sec <= gap_p75
```

- 정상 작업 흐름의 일부로 간주한다.

### 8.2 observation 공백

```text
gap_p75 < diff_sec <= gap_p90
```

- 관찰용 보조 구간으로 본다.
- severity 태그는 부여하지 않는다.
- 추세 해석과 향후 기준 보정 참고값으로만 사용한다.

### 8.3 light 공백

```text
gap_p90 < diff_sec <= gap_p95
```

- `light` 태그 산출의 직접 기준 구간으로 사용한다.

### 8.4 heavy 공백

```text
gap_p95 < diff_sec < 180
```

- `heavy` 태그 산출의 직접 기준 구간으로 사용한다.

### 8.5 idle 공백 (작업 이탈)

```text
diff_sec >= 180  -- 고정 기준 (3분)
```

- 작업자 이탈로 확정하는 고정 임계값 기준 구간이다.
- `idle` 태그 산출의 직접 기준으로 사용하며, percentile 기반 구간(light·heavy)과 독립적으로 적용된다.

---

## 9. 지표 역할 정의

v1.0에서는 `percentile`, `count`, `ratio`의 역할을 명확히 구분한다.

### 9.1 percentile

- 개별 gap의 심각도 구간을 정의하는 기준선으로 사용한다.
- 즉, `light`, `heavy` 구간을 나누는 경계값 역할을 한다. (`idle`은 고정 임계값 180s 적용)

### 9.2 count

- 세션 내에서 각 심각도 구간의 gap이 몇 번 반복되었는지를 나타내는 핵심 판정 지표로 사용한다.
- v1.0의 세션 저하 판정은 `count` 중심으로 구성한다.

### 9.3 ratio

- 세션 길이 차이에 따른 편차를 보정하기 위한 보조 지표로 사용한다.
- `count`만으로 해석이 왜곡될 수 있는 경우 보완 지표로 사용한다.

### 9.4 observation의 역할

- `observation`은 분석용 보조 구간이다.
- 직접적인 저하 판정 태그로 사용하지 않는다.
- 실제 판정의 중심은 `light`, `heavy`, `idle`에 둔다.

---

## 10. 세션 단위 판정 원칙

개별 gap 하나만으로 세션 저하를 판단하지 않고, 반복성 지표를 함께 적용한다.

### 10.1 observation 해석

- `observation_gap_count`는 산출 가능하나, 정식 세션 저하 판정 기준으로 사용하지 않는다.
- 분포 변화 관찰, 추세 점검, threshold 재검토를 위한 보조 해석 지표로 사용한다.

### 10.2 light 세션 판정 원칙

- `light_gap_count`를 핵심 판정 지표로 사용한다.
- 기준은 `light_gap_count > session_light_count_p90`으로 정의한다.
- 필요 시 `light_gap_ratio > session_light_ratio_p90`을 보조 조건으로 사용한다.
- zero-inflation 방지를 위해 `light_gap_count > 0` 조건을 함께 둔다.
- 필요 시 최소 세션 길이 또는 최소 gap 수 조건을 추가한다.

### 10.3 heavy 세션 판정 원칙

- `heavy_gap_count`를 핵심 판정 지표로 사용한다.
- 기준은 `heavy_gap_count > session_heavy_count_p95`로 정의한다.
- 필요 시 `heavy_gap_ratio > session_heavy_ratio_p95`를 보조 조건으로 사용한다.
- zero-inflation 방지를 위해 `heavy_gap_count > 0` 조건을 함께 둔다.
- 필요 시 최소 세션 길이 또는 최소 gap 수 조건을 추가한다.

### 10.4 idle 세션 판정 원칙

- `idle_gap_count`를 핵심 판정 지표로 사용한다.
- 기준은 `idle_gap_count > session_idle_count_p99`로 정의한다.
- 필요 시 `idle_gap_ratio > session_idle_ratio_p99`를 보조 조건으로 사용한다.
- zero-inflation 방지를 위해 `idle_gap_count > 0` 조건을 함께 둔다.
- 필요 시 최소 세션 길이 또는 최소 gap 수 조건을 추가한다.

### 10.5 세션 평균 지표의 위치

- `session_avg_gap`은 참고용 진단 지표로는 활용 가능하다.
- 그러나 v1.0의 정식 세션 저하 판정 기준으로는 사용하지 않는다.

---

## 11. 사용자 일 단위 판정 원칙

사용자 일 단위 평가는 세션 판정 결과의 반복성을 집계하는 방식으로 수행한다.

### 11.1 light 사용자 후보

- `light_session_count > user_light_session_count_p90`으로 해석한다.
- 필요 시 `light_session_count > 0` 조건을 함께 둔다.

### 11.2 heavy 사용자 후보

- `heavy_session_count > user_heavy_session_count_p95`로 해석한다.
- 필요 시 `heavy_session_count > 0` 조건을 함께 둔다.

### 11.3 idle 사용자 후보

- `idle_gap_total > user_idle_gap_total_p99`로 해석한다.
- 필요 시 `idle_gap_total > 0` 조건을 함께 둔다.

### 11.4 사용자 평균 지표의 위치

- `user_day_avg_gap`은 참고용 진단 지표로만 활용할 수 있다.
- 사용자 일 단위 정식 판정 기준은 세션 반복성 지표 중심으로 구성한다.

---

## 12. 기준 산출 절차

v1.0 기준 산출은 다음 절차를 따른다.

1. Labeler role만 필터링한 로그를 준비한다.
2. `diff_sec` 분포를 산출한다.
3. `p50, p75, p90, p95`를 계산한다. (`gap_p99`는 참고 진단용. idle 경계는 고정 180s)
4. 각 gap을 `observation`, `light`, `heavy`, `idle` 구간으로 분류한다.
5. 세션별 `light_gap_count`, `heavy_gap_count`, `idle_gap_count`를 집계한다.
6. 필요 시 각 ratio 지표를 함께 산출한다.
7. count와 ratio의 세션 분포 percentile을 계산하고 `session_light_count_p90`, `session_heavy_count_p95`, `session_idle_count_p99` 등을 산출한다.
8. 사용자 일 단위 반복성 지표 분포를 산출하고 `user_light_session_count_p90`, `user_heavy_session_count_p95`, `user_idle_gap_total_p99` 등을 산출한다.
9. zero-inflation 여부를 점검하고 최소 세션 길이 또는 최소 gap 수 조건을 보정한다.
10. 샘플 검토를 통해 오탐과 미탐을 점검한다.

---

## 13. 설계 상 유의사항

- 3D point cloud annotation 도메인에서는 긴 공백이 항상 비집중을 의미하지 않는다.
- 탐색, 회전, 확대/축소, 객체 확인, 공간 판단 등의 시간이 command 로그에 직접 반영되지 않을 수 있다.
- 따라서 `개별 long gap`보다 `정상 분포 대비 긴 gap의 반복성`을 우선적으로 본다.
- 세션 길이 차이로 인해 count 해석이 왜곡될 수 있으므로 ratio를 보조 지표로 병행한다.
- feature 특성이 충분히 다를 경우 공통 기준보다 feature별 percentile 기준이 더 적합할 수 있다.

---

## 14. v0.9 대비 변화

v0.9와 비교한 v1.0 설계 변화는 다음과 같다.

- `avg_gap > 30s AND gaps_5min > 10` 방식에서 분포 기반 체계로 전환
- 평균 기반 판단에서 `반복 횟수 기반 판단`으로 중심 이동
- 절대 count 기준에서 `count percentile 기반 기준`으로 확장
- `observation`을 판정 레벨이 아닌 분석용 보조 구간으로 재정의
- 실제 저하 판정 중심을 `light`, `heavy`, `idle`에 명시
- `idle` 기준을 percentile 기반(p99)에서 고정 임계값(180s, 3분)으로 전환

---

## 15. 향후 확장 방향

- feature별 기준 분리
- task complexity 보정
- 보조 지표의 percentile 기준 추가
- role 내 세부 분포 차이 반영

---

## 16. 버전 히스토리

| 버전 | 일자 | 상태 | 주요 내용 |
|------|------|------|-----------|
| `v0.9` | 2026-04-22 | Existing | anomaly 관찰값 기반 초기 운영 기준 |
| `v1.0-design` | 2026-04-22 | Draft | percentile 기반 개념 체계와 count 중심 판정 원칙 정리 |
| `v1.1-design` | 2026-05-11 | Updated | `departure` → `idle` 대체: 3분(180s) 고정 임계값 도입, `gap_p99` 분류 경계 제거, critical 상한 `< 180s`로 변경 |
| `v1.2-design` | 2026-05-11 | Updated | `warning` → `light`, `critical` → `heavy` 레벨 명칭 변경 |
