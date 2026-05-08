# 시나리오 #3 — UI/UX 기반 사용자 플로우 변경

## 1. 개요

| 항목 | 내용 |
|------|------|
| **트리거** | 기존 커맨드의 UI/UX가 변경되어 발생 조건, 사용자 플로우, 또는 CloudEvent 구조가 바뀔 때 |
| **범위** | 커맨드 타입 자체는 동일하지만 발생 맥락, 구조, 또는 순서가 변경됨 |
| **Case 2와 차이** | 신규 커맨드 추가가 아닌 기존 커맨드의 변경. 검증 판정 기준 재검토 필요 여부를 먼저 판단해야 함 |

> **예시 상황**
> - `select` 없이 직접 transform 가능해짐 → Stage 2 STEP 7 커맨드 순서 정합성 판정 기준 영향
> - `changes` 배열의 old/new 필드 구조 변경 → Stage 1 STEP 1/2/4 검증 영향
> - `params` 필드명 변경 (예: `updateCount` → `changeCount`) → Stage 1 STEP 0 집계 구조 영향

---

## 2. 변경 유형 분류

UI/UX 변경이 검증에 미치는 영향은 변경 유형에 따라 달라집니다.
**Labelit Engineer가 먼저 변경 유형을 판단하여 Nova Engineer에게 통보해야 합니다.**

| 변경 유형 | CloudEvent 구조 변경 | 검증 기준 재검토 필요 | 영향 검증 항목 |
|-----------|:-------------------:|:-------------------:|----------------|
| 발생 조건/단축키만 변경 | ❌ | ⚠️ | Stage 2 STEP 7 순서 정합성 재검토 (구현 예정) |
| params 필드명/구조 변경 | ✅ | ✅ | Stage 1 STEP 0 집계 구조 |
| old/new 필드 구조 변경 | ✅ | ✅ | Stage 1 STEP 1, 2, 4 |
| 사용자 플로우 순서 변경 | ❌ | ⚠️ | Stage 2 STEP 7 순서 정합성 재검토 (구현 예정) |

---

## 3. 역할별 절차

### 3.1 Labelit Engineer

#### 3.1.1 ① 변경 내용 분석 및 통보

| # | 확인 항목 |
|---|-----------|
| 1 | CloudEvent 구조(specversion, type, data 필드)가 변경되었는지 확인 |
| 2 | `changes` 배열의 old/new 필드 구조가 변경되었는지 확인 |
| 3 | `params` 필드 구조/명칭이 변경되었는지 확인 |
| 4 | 발생 조건(사용자 액션 방식)만 변경된 경우 구조 무변경 확인 |
| 5 | Nova Engineer에게 변경 유형 및 범위 통보 (CloudEvent 구조 변경 유무 명시) |
| 6 | QA에게 변경된 플로우 내용 별도 공유 (기존 QA 시나리오 업데이트 포함) |

**구조 변경 있는 경우 추가 항목**

| # | 확인 항목 |
|---|-----------|
| 7 | 변경된 CloudEvent 구조로 스펙 정의서 재작성 (변경 전/후 구조 비교표 포함) |
| 8 | Nova Engineer에게 재작성한 스펙 전달 |

---

### 3.2 Nova Engineer

#### 3.2.1 ① 변경 영향 범위 판단

Labelit Engineer로부터 변경 유형 수신 후 검증 기준 재검토 여부를 결정합니다.

| 변경 유형 | 조치 |
|-----------|------|
| 구조 변경 없음 | Stage 1 Group B 검증 기준 유지. Stage 2 STEP 7 판정 기준 재검토 필요 여부 확인 |
| params 구조 변경 | Stage 1 STEP 0 집계 결과에서 변경 전/후 분포 비교 |
| old/new 구조 변경 | Stage 1 STEP 1/2/4 검증 시 파싱 경로 NULL 여부 집중 확인 |
| 사용자 플로우 순서 변경 | Stage 2 STEP 7 판정 기준 비즈니스 재검토 (select 없는 transform 허용 여부 판단) |

#### 3.2.2 ② 중점 검증 항목

> **변경 전/후 비교 우선:** QA가 전달한 변경 사항 정보를 검토하여 STEP별 판정 기준 조정 여부를 먼저 결정합니다.

| Stage | STEP | 항목 | 이유 |
|-------|------|------|------|
| Stage 1 Group A | STEP 0 | 이벤트 요약 통계 | 변경 후 event_type 집계가 이전 대비 정상 범위인지 확인 |
| Stage 1 Group B | STEP 1 | 위치 점프 | 플로우 변경으로 old/new 값 구조가 바뀐 경우 점프 임계값 재검토 |
| Stage 1 Group B | STEP 2 | 위치 진동 | 발생 조건 변경 시 reversal 비율 기준 영향 여부 확인 |
| Stage 1 Group B | STEP 4 | 피처별 기하학적 이상 | old/new 구조 변경 시 기존 파싱 경로가 NULL이 되지 않는지 확인 |

#### 3.2.3 ③ 데이터 도달 확인 (QA 수행 후)

| 항목 | 내용 |
|------|------|
| **실행 노트북** | `{feature}_template.ipynb` Stage 1 STEP 0 |
| **입력 기반** | QA가 변경된 플로우로 수행한 세션 정보 |
| **확인 기준** | 변경 후 event_type이 집계에 포함됨 |

---

### 3.3 QA / Tester

#### 3.3.1 ① 변경 내용 파악

| # | 확인 항목 |
|---|-----------|
| 1 | Labelit Engineer로부터 변경된 UI/UX 내용 및 갱신된 QA 시나리오 수신 |
| 2 | 변경 전 플로우와 변경 후 플로우의 차이 파악 |
| 3 | 기존 방식으로 수행하지 않도록 주의 (변경 후 방식으로만 수행) |

#### 3.3.2 ② 시나리오 수행

| # | 확인 항목 |
|---|-----------|
| 1 | 변경된 플로우 기준으로 시나리오 수행 |
| 2 | 변경 전/후 방식 혼용하지 않도록 주의 |
| 3 | 수행 내용에 변경된 발생 조건을 구체적으로 명시 |

#### 3.3.3 ③ 수행 후 기록 (변경 내용 명시 필수)

- `feature`: (예: od)
- `event_type`: (변경 대상 커맨드 타입)
- `session_id`: \<수행 세션 ID\>
- `user_id`: \<수행 계정 고유 ID\>
- `user_name`: \<계정명\>
- `task_id`: \<태스크 ID\>
- `action_date`: \<수행 일시\>
- `수행 내용`: [변경 후 플로우로 수행] (예: select 없이 직접 transform 수행)
- `변경 사항`: (예: UI 변경으로 select 없이 transform 가능해짐 → Nova Engineer Stage 1 STEP 0 집계 기준 재검토 참고)

---

## 4. 역할 간 핸드오프 순서

**[Labelit Engineer] → [Nova Engineer] → [QA/Tester] 흐름:**

1. Labelit Engineer: UI/UX 변경 발생 인지
2. Labelit Engineer: 변경 유형 분석 (CloudEvent 구조 변경 여부)
3. Labelit Engineer → Nova Engineer: 변경 내용 통보 (구조 변경 유무 명시)
4. Nova Engineer: 영향 범위 판단, 검증 기준 재검토 여부 결정
5. Labelit Engineer: 앱 배포 (구조 변경 시 스펙 재작성 후)
6. Labelit Engineer → QA/Tester: 갱신된 QA 시나리오 공유
7. QA/Tester: 변경 플로우로 시나리오 수행
8. QA/Tester → Nova Engineer: 세션 정보 + 변경 사항 전달
9. Nova Engineer: Stage 1 STEP 0 확인 (데이터 도달 확인)
10. Nova Engineer: Stage 1 Group B 중점 검증 (STEP 1, 2, 4)
11. PASS → 검증 기준 갱신 후 정기 검증 이관

---

## 5. 검증 판정 요약

| 단계 | 도구 | Case 3 특이 기준 |
|------|------|-----------------|
| 데이터 도달 확인 | `{feature}_template.ipynb` Stage 1 STEP 0 | 변경 후 event_type이 집계에 포함됨 |
| Stage 1 Group A | `{feature}_template.ipynb` STEP 0, 3 | STEP 0: 변경 후 이벤트 집계가 이전 대비 정상 범위인지 확인 |
| Stage 1 Group B | `{feature}_template.ipynb` STEP 1, 2, 4 | STEP 4 집중: old/new 구조 변경 시 파싱 경로 NULL 여부 확인 |
| Stage 2 | `{feature}_template.ipynb` STEP 5 | 변경 후 복수 사용자 패턴 이상 없음 확인 |

---

## 6. 참고 문서

- `docs/agents/role_rules__labelit_engineer.md`
- `docs/agents/role_rules__nova_engineer.md`
- `docs/agents/role_rules__qa_tester.md`
