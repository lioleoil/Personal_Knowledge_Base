# 검증 시나리오 1 — Feature Workspace 초기 셋업 및 로그 수집 Initialize

## 개요

| 항목 | 내용 |
|------|------|
| **트리거** | 신규 feature workspace가 처음 도입될 때 |
| **범위** | 복수의 커맨드를 일괄 도입, 파이프라인 초기 구성 포함 |
| **Case 2와 차이** | 파이프라인에 해당 feature가 존재하지 않으므로 초기 구성 필수. 단일 커맨드 추가가 아닌 전체 커맨드 목록 일괄 등록 |

> **예시 상황**: 신규 피처 워크스페이스가 도입되어 `annotation.object.select`, `annotation.bbox3d.transform`, `history.undo`, `history.redo` 4종을 처음으로 수집 시작하는 경우

---

## 역할별 절차

### App Engineer

**① 커맨드 목록 확정 및 스펙 작성**

| # | 확인 항목 |
|---|-----------|
| 1 | 수집 대상 커맨드 타입 전체 목록 확정 |
| 2 | 각 커맨드별 `docs/command_spec_template.md` 스펙 정의서 개별 작성 |
| 4 | 커맨드별 Command Stack 해당 여부 명시 |
| 5 | 전체 스펙 묶음을 Data Engineer에게 일괄 전달 |

**② 배포 전 확인**

| # | 확인 항목 |
|---|-----------|
| 1 | Data Engineer로부터 파이프라인 반영 완료 통보 수신 확인 |
| 2 | 신규 feature_value가 앱 코드의 `data.feature` 필드 값과 일치하는지 확인 |
| 3 | 모든 수집 대상 커맨드에 `data.user.id`, `data.user.name`, `data.project.task_id` 구현 여부 확인 |
| 4 | 앱 배포 후 QA에게 수행 가능한 커맨드 목록 공유 |

> **핵심 주의**: 파이프라인 반영 완료 통보 이전에 배포하면 해당 feature의 로그가 파이프라인 미반영 상태로 적재됨

---

### Data Engineer

**① 스펙 수신 및 파이프라인 초기 구성**

| # | 확인 항목 | 파일 |
|---|-----------|------|
| 1 | 수집 대상 커맨드 전체 목록 수신 확인 | `docs/command_spec_template.md` |
| 2 | 수집 요청 이력 테이블에 커맨드별 항목 일괄 추가 (상태: ⏳ 반영 대기) | `docs/collection_requests.md` |
| 3 | `01_raw` ~ `03_int` 파이프라인 전체 실행 순서 확인 및 실행 | — |
| 4 | App Engineer에게 반영 완료 통보 (반영된 커맨드 목록 포함) | — |

**② Spot Check (QA 수행 후) — 커맨드 타입별 각각 실행**

| 커맨드 타입 | 특이사항 |
|-------------|---------|
| `annotation.object.select` | — |
| `annotation.bbox3d.transform` | — |
| `history.undo` | reverted_event_id 매칭 확인 (Q1) |
| `history.redo` | undo 이후 발생 여부 확인 |

> **Case 1 주의사항**: 모든 커맨드 타입 PASS 확인 후 정기 검증(04a/04b) 이관.
> 일부 커맨드만 PASS인 경우 해당 커맨드만 이관하고 나머지는 별도 추적.

**③ 중점 검증 항목**

| 검증 | 항목 | 이유 |
|------|------|------|
| C1 | Raw ↔ Staging 건수 정합성 | 초기 적재 누락 여부 확인 |
| Q3 | 증분 중복 | 초기 실행 시 경계값 처리 확인 |

---

### QA / Tester

**① 시나리오 수행 준비**

| # | 확인 항목 |
|---|-----------|
| 1 | 신규 feature workspace가 앱에 배포된 것을 확인 |
| 2 | App Engineer로부터 수행할 커맨드 타입 목록 및 QA 시나리오 수신 |
| 3 | 단일 세션, 단일 태스크 기준으로 수행 계획 수립 |

> **세션 수행 방식**: 여러 커맨드 타입을 하나의 세션에서 연속 수행해도 됩니다.
> Data Engineer가 `target_event_type` 위젯으로 커맨드 타입별 개별 Spot Check를 실행하므로
> 멀티 세션은 필수가 아닙니다. 단, 세션 내 수행 순서(select → transform → undo → redo)는 지켜야 합니다.

**② 커맨드 타입별 수행 순서**

> Command Stack 의존성으로 인해 아래 순서 권장:

```
annotation.object.select
  →  annotation.bbox3d.transform
    →  history.undo   (직전 transform 취소)
      →  history.redo  (undo 이후에만 발생)
```

> `history.undo` / `history.redo`는 반드시 `annotation.bbox3d.transform` 이후에 수행
> (undo 대상 Command Stack 커맨드가 선행되어야 `reverted_command_id` 매칭 가능)

**③ 수행 후 기록 — 커맨드 타입별 각각 기록**

```
[커맨드 타입 1: annotation.object.select]
- feature      : <feature 값>
- event_type   : annotation.object.select
- session_id   : <수행 세션 ID>
- user_id      : <수행 계정 고유 ID>
- user_name    : <계정명>
- task_id      : <태스크 ID>
- action_date  : <수행 일시>
- 수행 내용    : bbox3d 오브젝트 클릭하여 선택

[커맨드 타입 2: annotation.bbox3d.transform]
- (동일 양식, event_type 변경)

[커맨드 타입 3: history.undo]
- (동일 양식, event_type 변경)

[커맨드 타입 4: history.redo]
- (동일 양식, event_type 변경)
```

---

## 역할 간 핸드오프 순서

```
[App Engineer]                    [Data Engineer]               [QA/Tester]
      │                                 │                            │
  ① 전체 커맨드 스펙 작성               │                            │
  ② 스펙 일괄 전달 ─────────────→ ③ 파이프라인 초기 구성              │
                                    CASE 문 신규 추가                │
                                    파이프라인 실행                   │
                                       │                            │
  ④ 앱 배포 ←── 반영 완료 통보 ──────────┘                            │
  ⑤ 커맨드 목록 공유 ─────────────────────────────────────→ ⑥ 커맨드별 시나리오 수행
                                       │                   (권장 순서대로)
                                       │                            │
                               ⑦ 커맨드별 Spot Check ←── 세션 정보 전달
                                  (05 노트북 × 커맨드 수)
                                       │
                               ⑧ PASS → 정기 검증 이관
                                  FAIL → 아래 참고
```

> ❌ Spot Check FAIL 시: [role_rules__data_engineer.md — FAIL 처리 절차](role_rules__data_engineer.md#fail-처리-절차)

---

## 검증 판정 요약

| 단계 | 도구 | 기준 |
|------|------|------|
| Spot Check | `05_spot_check__command_arrival.sql` | 커맨드 타입별 Raw 도달 + Staging 전량 반영 → PASS |
| 완전성 검증 | `04a_validate__completeness.sql` | C1, C2 중점 확인 |
| 품질 검증 | `04b_validate__quality.sql` | Q2, Q1, Q3 |

---

> 관련 문서: `docs/role_rules__app_engineer.md` / `docs/role_rules__qa_tester.md` / `docs/role_rules__data_engineer.md`
