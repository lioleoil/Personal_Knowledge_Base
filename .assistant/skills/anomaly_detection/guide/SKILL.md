# 커맨드 로그 이상 탐지 분석 가이드

> Labelit 워크스페이스 커맨드 로그의 비정상 편집 패턴을 탐지하고 구조화된 형식으로 보고한다.

---

## 워크플로우 구조 (2-Stage)

```
Stage 1 — 수집 데이터 무결성 검증 (Raw 기반)
│
├── [Group A] Raw 직접 접근 — 파싱 불필요
│   ├── STEP 0: 이벤트 요약 통계
│   └── STEP 3: 타임스탬프 지연 (event_time vs occurred_at)
│
└── [Group B] 인라인 파싱 필요 — Staging 역할 임시 수행
    ├── STEP 1: 이동 거리 이상
    ├── STEP 2: 시간적 역전/반복 (진동)
    └── STEP 4: 피처별 기하학적 이상

Stage 2 — 가공 데이터 기반 행동 이상 탐지 (Intermediate/Mart 기반)
│
├── STEP 5: 사용자/객체 행동 이상   ← 구현 완료 (복수 사용자 동시 편집)
├── STEP 6: Undo/Redo 패턴 이상     ← 구현 완료 (workspace_history 테이블 활용)
├── STEP 7: Command Stack 플로우 정합성 ← 구현 완료 (시간 역전 + 복수편집 비율)
├── STEP 8: 작업 생산성 이상         ← 구현 완료 (스테일 세션 + 집중도 저하)
└── STEP 9: 파이프라인 신선도         ← 구현 완료 (수집 공백 시간대)
```

### Stage 경계 기준

| 기준 | Stage 1 | Stage 2 |
|------|---------|---------|
| 핵심 질문 | "이 로그가 올바르게 수집되었는가?" | "이 라벨러/세션의 작업 패턴이 비정상인가?" |
| 범위 | 데이터 구조, 값의 물리적 합리성, 수집 시점 이상 | 비즈니스 로직, 행동 패턴, 파이프라인 가공 결과 |
| 데이터 소스 | `_raw` (인라인 파싱 포함) | Staging / Intermediate 테이블 |
| STEPs | 0, 1, 2, 3, 4 | 5, 6, 7, 8, 9 |
| 현재 상태 | 3개 템플릿으로 구현됨 | STEP 5~9 전체 구현 완료 (runner 통합) |

### Group A vs B (Stage 1 내부)

- **Group A**: `event_time`, `occurred_at` 등 Raw 컬럼 직접 접근. 파싱 불필요.
- **Group B**: `position`, `rotation`, `height` 등 JSON 값 파싱 필요. → Staging 테이블 안정화 시 `_raw` 대신 Staging 참조로 교체 가능.

> **마이그레이션 경로**: Group B의 인라인 파싱 쿼리는 Staging 테이블이 안정화된 시점에 Stage 2로 이관하거나 Staging 테이블 직접 참조로 교체할 수 있다.

---

## 공통 규칙

- 이상이 없는 항목도 "이상 없음"으로 명시
- `old_val`이 null인 create 이벤트는 위치 점프·진동 분석에서 제외
- 판정은 반드시 데이터 수치에 근거, 추측 금지
- 시각화 최소 3개 포함
- SQL 결과를 sqlCitation으로 인용하여 근거 명확화
- **object_id는 단일 task 내에서만 unique** → 분석 시 반드시 task_id와 함께 사용

---

## 출력 형식

### 1. 개요
event_type별 건수 / action별 분포 / object_type별 분포 / 세션·사용자·task·object 목록 요약

### 2. 이상 탐지 요약

| 이상 유형 | 영향 범위 | 심각도 | Stage |
|-----------|-----------|--------|-------|
| ...       | ...       | 높음·중간·낮음 | 1 or 2 |

### 3. 이상별 상세

> **[유형 - 심각도]** 요약
> - 근거: 데이터 수치·구간, SQL 결과 인용
> - 주요 사례: session_id, user_name, object_id 등
> - 의심 원인: 한 줄

### 4. 종합 의견
- 데이터 신뢰도: 정상 / 주의 / 불량
- 우선 점검 항목
- 정상 동작 확인

---

## Stage 1: Feature별 분석 항목 및 판정 기준

### OD (bbox3d)

- object_type: `box` / event_type: `bbox3d.transform`, `bbox3d.create`, `bbox3d.delete`
- feature 필터: `feature = 'od'` (event_type에 bbox3d가 포함되지만, feature 필드는 `od`)
- old_val/new_val: `position {x,y,z}`, `rotation {roll,pitch,yaw}`, `size {length,width,height}`
- JSON 경로: `$.position.x`, `$.position.y`, `$.position.z`, `$.rotation.yaw` 등 (배열이 아닌 object 형식)

| STEP | Group | 분석 항목 | 대상 | 판정 기준 |
|------|-------|-----------|------|-----------|
| 0 | A | 데이터 개요 | 전체 | event_type·세션·사용자·object 집계 |
| 3 | A | 시간 괴리 | 전체 | occurred_at − event_time > 30s ⚠️ / > 60s·음수 ❌ |
| 1 | B | 위치 점프 | bbox3d.transform | 이동거리 > 5.0m ⚠️ / > 15.0m ❌ |
| 2 | B | 위치·회전 진동 | bbox3d.transform (≥ 0.05m) | 윈도우(6) reversal 비율 ≥ 75% → < 10건 주의 / ≥ 10건 심각 |
| 4 | B | yaw 드리프트 | bbox3d.transform | \|yaw\| < 1E-6 누적증가 ⚠️ (E-10 미만은 FP 노이즈로 정보 표기) |

### LD (Lane Detection)

- object_type: `point`(98%), `line`, `road-boundary`, `lane`, `topology`
- event_type: `point.move_batch`(80%), `point.scale`, `line.create`, `road_boundary.create`
- old_val/new_val: `position [x,y,z]` (배열 형식)
- 미세 조정이 빈번하여 진동 탐지 시 최소 이동거리 필터(≥ 0.05m) 적용

| STEP | Group | 분석 항목 | 대상 | 판정 기준 |
|------|-------|-----------|------|-----------|
| 0 | A | 데이터 개요 | 전체 | event_type·action·object_type·세션·사용자·task·object 집계 |
| 3 | A | 시간 괴리 | 전체 | occurred_at − event_time > 30s ⚠️ / > 60s·음수 ❌ |
| 1 | B | 위치 점프 | point.move, point.move_batch | 이동거리 > 5.0m ⚠️ / > 15.0m ❌ |
| 2 | B | 위치 진동 | point.move, point.move_batch (≥ 0.05m) | 윈도우(6) reversal 비율 ≥ 83% → < 10건 주의 / ≥ 10건 심각 |
| 4 | — | (해당 없음) | — | LD는 피처별 기하학적 이상 항목 없음 |

### RMD (Road Mark Detection)

- object_type: `polywall`, `point`, `polygon`
- event_type: `polywall.create`, `polywall.transform`, `point.move_batch`, `polygon.create`
- old_val/new_val: `position [x,y,z]`, `height` (스칼라), `vertices` (배열)
- polywall의 `height`는 도로면 기준 0에 가까워야 정상
- 진동 탐지 시 최소 이동거리 필터(≥ 0.05m) 적용

| STEP | Group | 분석 항목 | 대상 | 판정 기준 |
|------|-------|-----------|------|-----------|
| 0 | A | 데이터 개요 | 전체 | event_type·action·object_type·세션·사용자·task·object 집계 |
| 3 | A | 시간 괴리 | 전체 | occurred_at − event_time > 30s ⚠️ / > 60s·음수 ❌ |
| 1 | B | 위치 점프 | point.move, point.move_batch, polywall.transform | 이동거리 > 5.0m ⚠️ / > 15.0m ❌ |
| 2 | B | 위치 진동 | point.move, point.move_batch (≥ 0.05m) | 윈도우(6) reversal 비율 ≥ 75% → < 10건 주의 / ≥ 10건 심각 |
| 4 | B | 높이 이상 | polywall.create, polywall.transform | height > 0.5m ⚠️ / > 1.0m ❌ |

---

## Stage 2: 행동 이상 탐지 항목

| STEP | 분석 항목 | 설명 | 상태 |
|------|-----------|------|------|
| 5 | 사용자/객체 행동 이상 | 동일 object 복수 사용자 편집: 시간 겹침(overlap/≤5min) → ❌, 5min~1h gap → ⚠️, >1h gap → 순차 패턴(정상) | ✅ 구현 완료 |
| 6 | Undo/Redo 패턴 이상 | `workspace_history` 테이블 활용: 6a 사용자별 undo 비율(>30% ⚠️, >50% ❌), 6b undo burst(30초 내 5건+ ⚠️, 10건+ ❌) → step_id=5 병합 | ✅ 구현 완료 |
| 7 | Command Stack 플로우 정합성 | 7a 시간 역전(session+task 내 event_time 역순 → ❌), 7b 복수편집 비율(task 내 >50% → ⚠️) → step_id=5 병합 | ✅ 구현 완료 |
| 8 | 작업 생산성 이상 | 8a 스테일 세션(gap>600분 → ❌), 8b 집중도 저하(avg>30s & gaps_5min>10 → ⚠️) → step_id=3 병합 | ✅ 구현 완료 |
| 9 | 파이프라인 신선도 | 활성시간(09~23시) Dead hour → ❌, <100건 → ⚠️ → step_id=3 병합 | ✅ 구현 완료 |

> **확장 시점**: Intermediate 레이어가 안정화되고 피처 간 교차 분석(STEP 10)이 필요해지는 시점에 Stage 3 분리를 고려.

---

## 진동 탐지 Feature별 차등 기준

| Feature | reversal 비율 임계값 | 최소 이동거리 | 근거 |
|---------|----------------------|--------------|------|
| OD      | ≥ 75% (4.5/6)        | ≥ 0.05m       | 서브cm 노이즈 제거 후 의미 있는 진동만 탐지 (2026-04-03 OD 데이터 기반 보정) |
| LD      | ≥ 83% (5/6)          | ≥ 0.05m       | 미세 조정 빈번, 거의 전부 반전이어야 이상 |
| RMD     | ≥ 75% (4.5/6)        | ≥ 0.05m       | OD와 LD 중간 성격 |

---

## 임계값 보정 이력

### 2026-04-03 OD 데이터 기반 보정 (v2)

| STEP | 변경 전 | 변경 후 | 근거 |
|------|---------|---------|------|
| 3 | ⚠️ >10s / ❌ >30s | ⚠️ >30s / ❌ >60s | 파이프라인 구조적 지연 p50=14s, p99=29s. 기존 10s 기준에서 62% warning 발생 |
| 1 | ⚠️ >1.0m / ❌ >3.0m | ⚠️ >5.0m / ❌ >15.0m | p99=3.8m, p999=12.1m. 프레임 전환 시 정상 범위 포함 문제 해소 |
| 2 (OD) | reversal ≥67%, min_dist 없음 | reversal ≥75%, min_dist ≥0.05m | 82% 객체 심각 판정 → 0.05m 필터+75%로 11% critical (조치 가능 수준) |
| 4 | \|yaw\| < 1E-10 | \|yaw\| < 1E-6 | 전체 160건이 E-14~E-18 FP 노이즈. E-10~E-6 구간 0건 |
| 5 | 복수 사용자만 체크 | 시간 겹침 조건: overlap/≤5min ❌, 5min~1h ⚠️, >1h 정상 | 83% 순차 리뷰 패턴, 실제 동시 편집 16%만 |

---

## 분석 템플릿

Feature별 SQL 템플릿 노트북 (전체 셀 순서대로 실행):

- OD: `anomaly_detection_templates/od_template`
- LD: `anomaly_detection_templates/ld_template`
- RMD: `anomaly_detection_templates/rmd_template`

### 템플릿 셀 구조

```
1.  타이틀 (Markdown)
2.  데이터 준비 (temp view 생성)
3.  ─── Stage 1 — Group A ───
4.  STEP 0: 이벤트 요약 통계
5.  STEP 3: 타임스탬프 지연
6.  ─── Stage 1 — Group B ───
7.  STEP 1: 이동 거리 이상
8.  STEP 2: 시간적 역전/반복 (진동)
9.  STEP 4: 피처별 기하학적 이상 (OD: yaw / RMD: 높이 / LD: 없음)
10. ─── Stage 2 ───
11. STEP 5: 사용자/객체 행동 이상
12. STEP 6~9: 구현 예정 placeholder (runner에서 통합 실행)
```

> **참고**: STEP 6~9는 runner 노트북에서 통합 실행됨. 템플릿은 탐색적 분석용(Stage 1 + STEP 5)으로 유지.

---

## 체크리스트

### Stage 1 — 수집 무결성
- [x] STEP 0: 데이터 개요 집계 [Group A]
- [x] STEP 3: 시간 괴리 탐지 (음수, 30s↑, 60s↑) [Group A]
- [x] STEP 1: 위치 점프 탐지 및 심각도 분류 (5m↑, 15m↑) [Group B]
- [x] STEP 2: 위치 진동 패턴 분석 (Feature별 비율 기준 적용) [Group B]
- [x] STEP 4: Feature 고유 분석 (OD: yaw 드리프트 1E-6↑ / RMD: 높이 이상) [Group B]

### Stage 2 — 행동 이상
- [x] STEP 5: 복수 사용자 동시 편집 (시간 겹침 기준 적용)
- [x] STEP 6: Undo/Redo 패턴 이상 (workspace_history 테이블, 6a undo 비율 + 6b burst)
- [x] STEP 7: Command Stack 플로우 정합성 (7a 시간 역전 + 7b 복수편집 비율)
- [x] STEP 8: 작업 생산성 이상 (8a 스테일 세션 + 8b 집중도 저하)
- [x] STEP 9: 파이프라인 신선도 (수집 공백 시간대)

### 공통
- [ ] 시각화 3개 이상
- [ ] 이상 탐지 요약 테이블
- [ ] 종합 의견 및 우선 점검 항목
