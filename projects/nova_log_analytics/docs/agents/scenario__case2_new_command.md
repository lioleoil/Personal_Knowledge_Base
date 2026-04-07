# 시나리오 #2 — 신규 기능/커맨드 추가

## 1. 개요

| 항목 | 내용 |
|------|------|
| **트리거** | 기존 feature workspace에 새로운 커맨드 타입이 추가될 때 |
| **범위** | 단일 커맨드 추가, 기존 검증 노트북 구조 유지 |
| **Case 1과 차이** | 해당 feature의 `{feature}_template.ipynb`가 이미 존재함. 신규 event_type이 Stage 1 STEP 0 집계에 포함되는지만 추가 확인 |

> **예시 상황:** 기존 `od` workspace에 `annotation.bbox3d.resize` 같은 새 커맨드가 추가되는 경우

---

## 2. 역할별 절차

### 2.1 Labelit Engineer

#### 2.1.1 ① 커맨드 스펙 작성 및 전달

| # | 확인 항목 |
|---|-----------|
| 1 | `docs/command_spec_template.md` 템플릿으로 스펙 정의서 작성 |
| 2 | feature, event_type 명시 |
| 3 | Command Stack 해당 여부 명시 (undo/redo 대상 여부) |
| 4 | `changes` 배열 구조 및 old/new 필드 상세 기술 |
| 5 | `params` 구조 및 updateCount/selectedCount 정합성 명시 |
| 6 | `changes` 배열이 없는 커맨드인 경우 명시 (Nova Engineer의 Stage 1 Group B 검증 제외 판단에 필요) |
| 7 | 기존 커맨드와 동일한 event_type 사용 시 data 구조 차이(변경 전/후 비교)를 스펙에 반드시 명시 |
| 8 | Nova Engineer에게 스펙 전달 |

#### 2.1.2 ② 배포 전 확인

| # | 확인 항목 |
|---|-----------|
| 1 | 신규 커맨드의 CloudEvent 구조가 스펙과 일치하는지 확인 |
| 2 | `params` 값과 `changes` 배열 크기 정합성 확인 |
| 3 | Command Stack 커맨드인 경우 `reverted_command.id`, `reverted_command.type` 구현 여부 확인 |
| 4 | 배포 완료 후 QA에게 알림 |

---

### 2.2 Nova Engineer

#### 2.2.1 ① 스펙 수신 및 검토

| # | 확인 항목 | 참고 |
|---|-----------|------|
| 1 | 커맨드 스펙 정의서 내용 확인 (feature, Command Stack 여부, changes 구조) | `docs/command_spec_template.md` |
| 2 | `changes` 배열 없는 커맨드 여부 확인 → Stage 1 Group B 검증 적용 범위 파악 | — |

#### 2.2.2 ② 데이터 도달 확인 (QA 수행 후)

| 항목 | 내용 |
|------|------|
| **실행 노트북** | `{feature}_template.ipynb` Stage 1 STEP 0 |
| **확인 기준** | 신규 event_type이 집계에 포함됨 |
| **미집계 시** | `docs/agents/role_rules__nova_engineer.md` STEP 0 데이터 미집계 처리 절차 참고 |

#### 2.2.3 ③ 중점 검증 항목

| Stage | STEP | 항목 | 이유 |
|-------|------|------|------|
| Stage 1 Group A | STEP 0 | 이벤트 요약 통계 | 신규 event_type이 집계에 정상 포함되는지 확인 |
| Stage 1 Group A | STEP 3 | 타임스탬프 지연 | 신규 커맨드의 클라이언트-서버 시각 차이 확인 |
| Stage 1 Group B | STEP 1 | 위치 점프 | 신규 커맨드 위치 변화량 기준 적정성 확인 |
| Stage 1 Group B | STEP 4 | 피처별 기하학적 이상 | 신규 커맨드가 피처 기하학적 속성에 영향 줄 경우 우선 확인 |

---

### 2.3 QA / Tester

#### 2.3.1 ① 시나리오 수행

| # | 확인 항목 |
|---|-----------|
| 1 | Labelit Engineer로부터 스펙 정의서의 QA 시나리오 수신 확인 |
| 2 | 단일 세션, 단일 태스크 기준 수행 |
| 3 | 스펙의 QA 시나리오대로 정확히 수행 |
| 4 | Command Stack 커맨드인 경우: transform 수행 직후 다른 액션 없이 바로 undo 수행 (`reverted_command.id` 정확한 매칭을 위해) |

#### 2.3.2 ② 수행 후 기록

- `feature`: (예: od)
- `event_type`: (신규 커맨드 타입)
- `session_id`: \<수행 세션 ID\>
- `user_id`: \<수행 계정 고유 ID\>
- `user_name`: \<계정명\>
- `task_id`: \<태스크 ID\>
- `action_date`: \<수행 일시\>
- `수행 내용`: (스펙 QA 시나리오 기준으로 수행한 액션 서술)

---

## 3. 역할 간 핸드오프 순서

**[Labelit Engineer] → [Nova Engineer] → [QA/Tester] 흐름:**

1. Labelit Engineer: 단일 커맨드 스펙 작성
2. Labelit Engineer → Nova Engineer: 스펙 전달
3. Nova Engineer: 파이프라인 반영 + 이력 등록 (신규 Gen 필요 시 CASE 문 수정 포함)
4. Nova Engineer → Labelit Engineer: 반영 완료 통보 → 앱 배포
5. Labelit Engineer → QA/Tester: 배포 완료 알림
6. QA/Tester: 단일 세션 기준 시나리오 수행
7. QA/Tester → Nova Engineer: 세션 정보 전달
8. Nova Engineer: `{feature}_template.ipynb` Stage 1 STEP 0 확인 (데이터 도달 확인)
9. Nova Engineer: Stage 1 / Stage 2 전체 실행 → 정기 검증 이관

---

## 4. 검증 판정 요약

| 단계 | 도구 | 기준 |
|------|------|------|
| 데이터 도달 확인 | `{feature}_template.ipynb` Stage 1 STEP 0 | 신규 event_type이 집계에 포함됨 |
| Stage 1 Group A | `{feature}_template.ipynb` STEP 0, 3 | 신규 event_type 집계 확인 / 타임스탬프 지연 없음 |
| Stage 1 Group B | `{feature}_template.ipynb` STEP 1, 2, 4 | 위치 점프·진동·기하학적 이상 없음 |
| Stage 2 | `{feature}_template.ipynb` STEP 5 | 복수 사용자 편집 이상 없음 |

---

## 5. 참고 문서

- `docs/command_spec_template.md`
- `docs/agents/role_rules__labelit_engineer.md`
- `docs/agents/role_rules__qa_tester.md`
- `docs/agents/role_rules__nova_engineer.md`
