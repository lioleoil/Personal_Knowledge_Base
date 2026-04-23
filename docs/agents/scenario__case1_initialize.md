# 시나리오 #1 — Feature Workspace 초기 셋업 및 로그 수집 (Initialize)

## 1. 개요

| 항목 | 내용 |
|------|------|
| **트리거** | 신규 feature workspace가 처음 도입될 때 |
| **범위** | 복수의 커맨드를 일괄 도입, 피처별 검증 노트북 초기 실행 포함 |
| **Case 2와 차이** | 단일 커맨드 추가가 아닌 전체 커맨드 목록 일괄 등록. 해당 feature의 `{feature}_template.ipynb`를 처음으로 실행 |

> **예시 상황:** `ld` feature workspace가 신규 도입되어 `annotation.line.create`, `annotation.lane.create`, `annotation.topology.create` 3종을 처음으로 수집 시작하는 경우

---

## 2. 역할별 절차

### 2.1 Labelit Engineer

#### 2.1.1 ① 커맨드 목록 확정 및 스펙 작성

| # | 확인 항목 |
|---|-----------|
| 1 | 수집 대상 커맨드 타입 전체 목록 확정 |
| 2 | feature 값 확정 (예: `ld`, `od`, `rmd`) |
| 3 | 각 커맨드별 `docs/command_spec_template.md` 스펙 정의서 개별 작성 |
| 4 | 커맨드별 Command Stack 해당 여부 명시 |
| 5 | 전체 스펙 묶음을 Nova Engineer에게 일괄 전달 |

#### 2.1.2 ② 배포 전 확인

| # | 확인 항목 |
|---|-----------|
| 1 | feature 값이 앱 코드의 `data.feature` 필드 값과 일치하는지 확인 |
| 2 | 모든 수집 대상 커맨드에 `data.user.id`, `data.user.name`, `data.project.task_id` 구현 여부 확인 |
| 3 | 앱 배포 후 QA에게 수행 가능한 커맨드 목록 공유 |

---

### 2.2 Nova Engineer

#### 2.2.1 ① 스펙 수신 및 검토

| # | 확인 항목 | 참고 |
|---|-----------|------|
| 1 | 수집 대상 커맨드 전체 목록 수신 확인 | `docs/command_spec_template.md` |
| 2 | feature, event_type, data 구조, Command Stack 여부 파악 | — |

#### 2.2.2 ② 데이터 도달 확인 (QA 수행 후)

| # | 확인 항목 | 참고 |
|---|-----------|------|
| 1 | `{feature}_template.ipynb` Stage 1 STEP 0 실행 | `docs/agents/{feature}_template.ipynb` |
| 2 | 신규 feature / event_type이 집계에 포함되는지 확인 | — |
| 3 | 데이터 미집계 시 → STEP 0 데이터 미집계 처리 절차 참고 | `role_rules__nova_engineer.md` |

#### 2.2.3 ③ 중점 검증 항목 — 커맨드 타입별 각각 실행

| Stage | STEP | 항목 | 이유 |
|-------|------|------|------|
| Stage 1 Group A | STEP 0 | 이벤트 요약 통계 | 신규 feature 이벤트가 정상 수집되고 있는지 집계 확인 |
| Stage 1 Group A | STEP 3 | 타임스탬프 지연 | 초기 적재 시 클라이언트-서버 시각 차이 이상 여부 확인 |
| Stage 1 Group B | STEP 1 | 위치 점프 | 초기 수집 데이터 기하학적 무결성 확인 |
| Stage 2 | STEP 5 | 복수 사용자 편집 | 초기 배포 단계의 비정상 편집 패턴 선점 탐지 |

> **최우선 확인:** Stage 1 STEP 0에서 신규 feature의 `event_type`이 집계에 나타나는지 확인

---

### 2.3 QA / Tester

#### 2.3.1 ① 시나리오 수행 준비

| # | 확인 항목 |
|---|-----------|
| 1 | 신규 feature workspace가 앱에 배포된 것을 확인 |
| 2 | Labelit Engineer로부터 수행할 커맨드 타입 목록 및 QA 시나리오 수신 |
| 3 | 단일 세션, 단일 태스크 기준으로 수행 계획 수립 (복수 커맨드 타입을 동일 세션에서 수행해도 무방) |

#### 2.3.2 ② 커맨드 타입별 수행 순서

Command Stack 의존성으로 인해 아래 순서 권장:

```
annotation.object.select
→ annotation.bbox3d.transform
→ history.undo (직전 transform 취소)
→ history.redo (undo 이후에만 발생)
```

> **주의:** `history.undo` / `history.redo`는 반드시 `annotation.bbox3d.transform` 이후에 수행
> (undo 대상 Command Stack 커맨드가 선행되어야 `reverted_command.id` 매칭 가능)

#### 2.3.3 ③ 수행 후 기록 — 커맨드 타입별 각각 기록

**[커맨드 타입 1: `annotation.object.select`]**
- `feature`: (예: od)
- `event_type`: annotation.object.select
- `session_id`: \<수행 세션 ID\>
- `user_id`: \<수행 계정 고유 ID\>
- `user_name`: \<계정명\>
- `task_id`: \<태스크 ID\>
- `action_date`: \<수행 일시\>
- `수행 내용`: bbox3d 오브젝트 클릭하여 선택

**[커맨드 타입 2: `annotation.bbox3d.transform`]**
- (동일 양식, event_type 변경)

**[커맨드 타입 3: `history.undo`]**
- (동일 양식, event_type 변경)

**[커맨드 타입 4: `history.redo`]**
- (동일 양식, event_type 변경)

---

## 3. 역할 간 핸드오프 순서

**[Labelit Engineer] → [Nova Engineer] → [QA/Tester] 흐름:**

1. Labelit Engineer: 전체 커맨드 스펙 작성
2. Labelit Engineer → Nova Engineer: 스펙 일괄 전달
3. Nova Engineer: 스펙 수신 및 검토
4. Labelit Engineer: 앱 배포
5. Labelit Engineer → QA/Tester: 커맨드 목록 공유
6. QA/Tester: 커맨드별 시나리오 수행 (권장 순서대로)
7. QA/Tester → Nova Engineer: 세션 정보 전달
8. Nova Engineer: Stage 1 STEP 0 확인 (데이터 도달 확인)
9. Nova Engineer: Stage 1 / Stage 2 전체 실행 (`{feature}_template.ipynb`)

---

## 4. 검증 판정 요약

| 단계 | 도구 | 기준 |
|------|------|------|
| 데이터 도달 확인 | `{feature}_template.ipynb` Stage 1 STEP 0 | 신규 feature/event_type이 집계에 포함됨 |
| Stage 1 Group A | `{feature}_template.ipynb` STEP 0, 3 | STEP 0: 이벤트 집계 확인 / STEP 3: 타임스탬프 지연 없음 |
| Stage 1 Group B | `{feature}_template.ipynb` STEP 1, 2, 4 | 위치 점프·진동·기하학적 이상 없음 |
| Stage 2 | `{feature}_template.ipynb` STEP 5 | 복수 사용자 편집 이상 없음 |

> **이상 발생 처리 절차:** `docs/agents/role_rules__nova_engineer.md` → 이상 발생 처리 절차 참고

---

## 5. 참고 문서

- `docs/agents/role_rules__labelit_engineer.md`
- `docs/agents/role_rules__qa_tester.md`
- `docs/agents/role_rules__nova_engineer.md`
