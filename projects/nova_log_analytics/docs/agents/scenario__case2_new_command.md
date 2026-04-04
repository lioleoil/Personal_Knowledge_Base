# 검증 시나리오 2 — 신규 기능/커맨드 추가

## 개요

| 항목 | 내용 |
|------|------|
| **트리거** | 기존 feature workspace에 새로운 커맨드 타입이 추가될 때 |
| **범위** | 단일 커맨드 추가, 기존 파이프라인 구조 유지 |
| **Case 1과 차이** | 파이프라인에 해당 feature가 이미 등록되어 있음. 파이프라인 구조 변경 불필요 |

> **예시 상황**: 기존 workspace에 `annotation.bbox3d.resize` 같은 새 커맨드가 추가되는 경우

> 이 케이스는 `docs/collection_requests.md` 의 표준 수집 프로세스 흐름과 동일합니다.

---

## 역할별 절차

### App Engineer

**① 커맨드 스펙 작성 및 전달**

| # | 확인 항목 |
|---|-----------|
| 1 | `docs/command_spec_template.md` 템플릿으로 스펙 정의서 작성 |
| 2 | feature_value, event_type 명시 |
| 3 | Command Stack 해당 여부 명시 (undo/redo 대상 여부) |
| 4 | changes 배열 구조 및 old/new 필드 상세 기술 |
| 5 | params 구조 및 updateCount/selectedCount 정합성 명시 |
| 6 | changes 배열이 없는 커맨드인 경우 명시 (Data Engineer의 C2 검증 제외 판단에 필요) |
| 7 | Data Engineer에게 스펙 전달 |

**② 배포 전 확인**

| # | 확인 항목 |
|---|-----------|
| 1 | Data Engineer 반영 완료 통보 수신 확인 |
| 2 | 신규 커맨드의 CloudEvent 구조가 스펙과 일치하는지 확인 |
| 3 | `params` 값과 `changes` 배열 크기 정합성 확인 |
| 4 | Command Stack 커맨드인 경우 `reverted_command.id`, `reverted_command.type` 구현 여부 확인 |
| 5 | 배포 완료 후 QA에게 알림 |

---

### Data Engineer

**① 스펙 수신 및 파이프라인 반영**

| # | 확인 항목 | 파일 |
|---|-----------|------|
| 1 | 커맨드 스펙 정의서 내용 확인 (feature_value, Command Stack 여부, changes 구조) | `docs/command_spec_template.md` |
| 2 | 수집 요청 이력 테이블에 항목 추가 (상태: ⏳ 반영 대기) | `docs/collection_requests.md` |
| 3 | `01_raw` ~ `03_int` 파이프라인 실행 확인 | — |
| 5 | 이력 테이블 상태 업데이트 (⏳ → 🔄 모니터링 중) | `docs/collection_requests.md` |
| 6 | App Engineer에게 반영 완료 통보 | — |

**② Spot Check (QA 수행 후)**

| 항목 | 내용 |
|------|------|
| 실행 노트북 | `05_spot_check__command_arrival.sql` |
| 위젯 입력 | QA 전달 세션 정보 기반 |
| PASS 조건 | Raw 도달 + Staging 전량 반영 |
| PASS 후 액션 | 이력 상태 ✅ 완료 업데이트 → 04a/04b 정기 검증 이관 |

**③ 중점 검증 항목**

| 검증 | 항목 | 이유 |
|------|------|------|
| Q2 | NULL 규칙 (신규 커맨드 필드) | 신규 커맨드 특화 필드가 정상 파싱되는지 확인 |
| C2 | changes EXPLODE 완전성 | params.updateCount vs 실제 배열 크기 (changes 있는 커맨드만 해당) |
| Q1 | orphan undo | Command Stack 커맨드인 경우 reverted_event_id 매칭 확인 |

---

### QA / Tester

**① 시나리오 수행**

| # | 확인 항목 |
|---|-----------|
| 1 | App Engineer로부터 스펙 정의서의 QA 시나리오 수신 확인 |
| 2 | 단일 세션, 단일 태스크 기준 수행 |
| 3 | 스펙의 QA 시나리오대로 정확히 수행 |
| 4 | Command Stack 커맨드인 경우: transform 수행 직후 다른 액션 없이 바로 undo 수행 (reverted_command_id 정확한 매칭을 위해) |

**② 수행 후 기록**

```
- feature      : <feature 값 (예: od, rmd, ld)>
- event_type   : (신규 커맨드 타입)
- session_id   : <수행 세션 ID>
- user_id      : <수행 계정 고유 ID>
- user_name    : <계정명>
- task_id      : <태스크 ID>
- action_date  : <수행 일시>
- 수행 내용    : (스펙 QA 시나리오 기준으로 수행한 액션 서술)
```

---

## 역할 간 핸드오프 순서

```
[App Engineer]                    [Data Engineer]               [QA/Tester]
      │                                 │                            │
  ① 단일 커맨드 스펙 작성               │                            │
  ② 스펙 전달 ──────────────────→ ③ 파이프라인 반영                  │
                                    이력 등록                        │
                                    (신규 Gen 시 CASE 문 수정)       │
                                       │                            │
  ④ 앱 배포 ←── 반영 완료 통보 ──────────┘                            │
  ⑤ 배포 완료 알림 ──────────────────────────────────────→ ⑥ 시나리오 수행
                                       │                   (단일 세션)
                                       │                            │
                               ⑦ Spot Check ←──── 세션 정보 전달
                                       │
                               ⑧ PASS → 정기 검증 이관
                                  FAIL → 아래 참고
```

> ❌ Spot Check FAIL 시: [role_rules__data_engineer.md — FAIL 처리 절차](role_rules__data_engineer.md#fail-처리-절차)

---

## 검증 판정 요약

| 단계 | 도구 | 기준 |
|------|------|------|
| Spot Check | `05_spot_check__command_arrival.sql` | Raw 도달 + Staging 전량 반영 → PASS |
| 완전성 검증 | `04a_validate__completeness.sql` | C1, C2 확인 |
| 품질 검증 | `04b_validate__quality.sql` | Q2, Q1 (Command Stack 커맨드인 경우) 확인 |

---

> 관련 문서: `docs/collection_requests.md` / `docs/command_spec_template.md` / `docs/role_rules__data_engineer.md`
