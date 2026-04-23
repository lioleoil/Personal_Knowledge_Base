# Role Rules — Nova Engineer

## 역할 개요

| 항목 | 내용 |
|------|------|
| **역할** | Nova Engineer |
| **환경** | Databricks |
| **핵심 책임** | 피처별 이상 탐지 검증 정기 실행 및 이상 조사 |

---

## 책임 범위

### 담당
- 신규 커맨드 스펙 수신 및 검토
- 피처별 이상 탐지 검증 노트북(`{feature}_template.ipynb`) 정기 실행
- Stage 1 / Stage 2 이상 발견 시 원인 조사 및 Labelit Engineer에게 공유

### 담당하지 않음
- 앱 커맨드 로그 구현 (Labelit Engineer 역할)
- 앱 배포 (Labelit Engineer 역할)
- QA 시나리오 수행 (QA/Tester 역할)

---

## 워크플로우

### 신규 커맨드/피처 도입 시

**① 커맨드 스펙 정의서 수신**

| # | 내용 |
|---|------|
| 1 | Labelit Engineer로부터 스펙 정의서 수신 |
| 2 | feature, event_type, data 구조, Command Stack 여부 파악 |

**② 데이터 도달 확인 (QA 수행 후)**

| 항목 | 내용 |
|------|------|
| 실행 노트북 | `{feature}_template.ipynb` Stage 1 STEP 0 |
| 입력 조건 | QA로부터 수신한 session_id, user_id, task_id 기반 필터링 |
| 확인 기준 | 신규 feature / event_type이 집계에 포함됨 (데이터 도달 확인) |
| 미집계 시 | 아래 이상 발생 처리 절차 참고 |

**③ Stage 1 / Stage 2 전체 실행**

| # | 내용 |
|---|------|
| 1 | STEP별 판정 기준에 따라 이상 여부 확인 |
| 2 | 이상 발견 시 → 아래 이상 발생 처리 절차 참고 |
| 3 | PASS → 정기 검증 사이클로 이관 |

---

## 이상 탐지 검증 구조

피처별 이상 탐지 검증 노트북(`{feature}_template.ipynb`)을 정기적으로 실행한다.

### 피처별 검증 노트북

| feature | 노트북 | 비고 |
|---------|--------|------|
| od | `od_template.ipynb` | OD (Object Detection) 이상 탐지 |
| rmd | `rmd_template.ipynb` | RMD (Road Mark Detection) 이상 탐지 |
| ld | `ld_template.ipynb` | LD (Lane Detection) 이상 탐지 |

### Stage 1 — 수집 데이터 무결성 검증

| Group | STEP | 분석 항목 | 판정 기준 |
|-------|------|-----------|-----------|
| A (Raw 직접) | STEP 0 | 이벤트 요약 통계 | event_type별 건수, session·user·object 집계 (정보성) |
| A (Raw 직접) | STEP 3 | 타임스탬프 지연 | >30s ⚠️ / >60s·음수 ❌ |
| B (인라인 파싱) | STEP 1 | 위치 점프 | >5.0m ⚠️ / >15.0m ❌ |
| B (인라인 파싱) | STEP 2 | 위치 진동 (reversal 비율) | od/rmd: ≥75% ⚠️/❌ / ld: ≥83% ⚠️/❌ |
| B (인라인 파싱) | STEP 4 | 피처별 기하학적 이상 | od: yaw 드리프트(\|yaw\| < 1E-6 누적) / rmd: 높이(>0.5m ⚠️ / >1.0m ❌) / ld: 해당 없음 |

> Group A는 Raw 컬럼만으로 검증 가능 (파싱 불필요). Group B는 old/new_val JSON 파싱 필요.

### Stage 2 — 가공 데이터 기반 행동 이상 탐지

| STEP | 분석 항목 | 판정 기준 | 상태 |
|------|-----------|-----------|------|
| STEP 5 | 복수 사용자 편집 | overlap/≤5min ❌ / 5min~1h ⚠️ / >1h 순차 정상 | 구현 완료 |
| STEP 6 | Undo/Redo 패턴 이상 | `is_reverted`, `reverted_event_id` 활용 | 구현 예정 |
| STEP 7 | Command Stack 플로우 정합성 | 이벤트 시퀀스 누락·중복·역전 탐지 | 구현 예정 |
| STEP 8 | 작업 생산성 이상 | 비정상적으로 높거나 낮은 생산성 탐지 | 구현 예정 |

---

## 핵심 규칙

1. **데이터 도달 확인 우선**: 신규 커맨드는 Stage 1 STEP 0로 event_type 집계 포함 여부를 먼저 확인
2. **Stage 1 이상 발견 시**: Labelit Engineer에게 data 필드 구현 여부 및 CloudEvent 구조 확인 요청

---

## 인수인계 (Handoff)

| 방향 | 내용 | 수단 |
|------|------|------|
| ← Labelit Engineer | 커맨드 스펙 정의서 수신 | `docs/command_spec_template.md` |
| ← QA / Tester | 테스트 세션 정보 수신 | 기록 양식 (session_id, user_id, task_id 등) |

---

## 이상 발생 처리 절차

### STEP 0 데이터 미집계 시 (신규 커맨드/피처 도달 미확인)
```
1. QA 수행 정보(session_id, task_id) 재확인 → 입력 오류 여부 점검
2. 앱 이벤트 발생 여부 확인 (Labelit Engineer와 협력)
3. event_type, feature 값이 스펙과 일치하는지 Labelit Engineer에게 확인
```

### Stage 1 이상 발생 시
```
- STEP 1 위치 점프 ❌  → 해당 session·object의 event 시퀀스 상세 확인
- STEP 2 위치 진동 ❌  → 라벨러 작업 패턴 확인 및 Labelit Engineer에게 공유
- STEP 3 타임스탬프 지연 ❌  → 클라이언트-서버 시간 동기화 상태 확인
- STEP 4 기하학적 이상 ❌  → 피처별 기준값 검토 (od: yaw drift, rmd: height)
```

### 데이터 필드 NULL 발생 시
```
- user_id NULL   → Labelit Engineer에게 data.user.id 구현 여부 확인 요청
- user_name NULL → Labelit Engineer에게 data.user.name 구현 여부 확인 요청
- session_id NULL → CloudEvent $.sessionid 필드 파싱 경로 확인
- old_val NULL (create 액션) → 정상. create 액션은 변경 전 상태 없음
                               Stage 1 STEP 1/2 분석 시 old_val IS NULL 행 제외
```
