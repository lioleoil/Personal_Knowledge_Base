# 검증 시나리오 3 — UI/UX 기반 사용자 플로우 변경

## 개요

| 항목 | 내용 |
|------|------|
| **트리거** | 기존 커맨드의 UI/UX가 변경되어 발생 조건, 사용자 플로우, 또는 CloudEvent 구조가 바뀔 때 |
| **범위** | 커맨드 타입 자체는 동일하지만 발생 맥락, 구조, 또는 순서가 변경됨 |
| **Case 2와 차이** | 신규 커맨드 추가가 아닌 기존 커맨드의 변경. 파이프라인 수정 필요 여부를 먼저 판단해야 함 |

> **예시 상황**:
> - select 없이 직접 transform 가능해짐 → C5 검증 판정 기준 영향
> - changes 배열의 old/new 필드 구조 변경 → Q4 검증 영향
> - params 필드명 변경 (예: `updateCount` → `changeCount`) → C2, Q2 영향
> - undo/redo 단축키 변경 (발생 조건 변경, CloudEvent 구조는 동일)

---

## 변경 유형 분류

UI/UX 변경이 파이프라인에 미치는 영향은 변경 유형에 따라 달라집니다.
**App Engineer가 먼저 변경 유형을 판단하여 Data Engineer에게 통보해야 합니다.**

| 변경 유형 | CloudEvent 구조 변경 | 파이프라인 수정 필요 | 영향 검증 항목 |
|-----------|:---:|:---:|----------------|
| 발생 조건/단축키만 변경 | ❌ | ❌ | C5 판정 기준 재검토 |
| params 필드명/구조 변경 | ✅ | ✅ | C2, Q2 |
| old/new 필드 구조 변경 | ✅ | ✅ | Q4, Q2 |
| 사용자 플로우 순서 변경 | ❌ | ❌ | C5 판정 기준 재검토 |

---

## 역할별 절차

### App Engineer

**① 변경 내용 분석 및 통보**

| # | 확인 항목 |
|---|-----------|
| 1 | CloudEvent 구조(specversion, type, data 필드)가 변경되었는지 확인 |
| 2 | changes 배열의 old/new 필드 구조가 변경되었는지 확인 |
| 3 | params 필드 구조/명칭이 변경되었는지 확인 |
| 4 | 발생 조건(사용자 액션 방식)만 변경된 경우 구조 무변경 확인 |
| 5 | Data Engineer에게 변경 유형 및 범위 통보 (CloudEvent 구조 변경 유무 명시) |
| 6 | QA에게 변경된 플로우 내용 별도 공유 (기존 QA 시나리오 업데이트 포함) |

**구조 변경 있는 경우 추가 항목:**

| # | 확인 항목 |
|---|-----------|
| 7 | 변경된 CloudEvent 구조로 스펙 정의서 재작성 (변경 전/후 구조 비교표 포함) |
| 8 | Data Engineer에게 재작성한 스펙 전달 |
| 9 | Data Engineer 반영 완료 통보 수신 후 배포 진행 |

---

### Data Engineer

**① 변경 영향 범위 판단**

App Engineer로부터 변경 유형 수신 후 파이프라인 수정 여부 결정:

| 변경 유형 | 조치 |
|-----------|------|
| 구조 변경 없음 | 파이프라인 수정 불필요. 검증 쿼리 판정 기준만 재검토 |
| params 구조 변경 | 02_stg 파싱 로직 수정, C2/Q2 검증 조건 확인 |
| old/new 구조 변경 | 03_int 처리 로직 수정, Q4 검증 조건 확인 |
| 사용자 플로우 순서 변경 | C5 판정 기준 비즈니스 재검토 (select 없는 transform 허용 여부 판단) |

**② 구조 변경 있는 경우 파이프라인 반영**

| # | 확인 항목 | 파일 |
|---|-----------|------|
| 1 | 변경된 파싱 필드 반영 | `notebooks/02_stg__events.sql` |
| 2 | Intermediate 처리 로직 확인 | `notebooks/03_int__bbox3d_transforms.sql` |
| 3 | Q2 NULL 규칙 대상 필드 목록 갱신 여부 검토 | `notebooks/04b_validate__quality.sql` |
| 4 | App Engineer에게 반영 완료 통보 | — |

**③ Spot Check 실행**

구조 변경 여부와 관계없이 Spot Check는 동일하게 실행:

| 항목 | 내용 |
|------|------|
| 실행 노트북 | `05_spot_check__command_arrival.sql` |
| 입력 기반 | QA가 변경된 플로우로 수행한 세션 정보 |
| PASS 조건 | Raw 도달 + Staging 반영 |

**④ 중점 검증 항목**

| 검증 | 항목 | 이유 |
|------|------|------|
| C5 | select 없는 transform | 플로우 변경으로 의도적 발생 가능 → 허용 여부 재판단 후 QA에게 결과 통보 |
| Q4 | transform position 구조 무결성 | old/new 구조 변경 시 필드 누락 여부 확인 |
| Q2 | NULL 규칙 | 변경된 필드 구조에서 기존 파싱 경로가 NULL이 되지 않는지 확인 |
| C2 | changes EXPLODE 완전성 | params 구조 변경 시 updateCount 파싱 경로 확인 |

---

### QA / Tester

**① 변경 내용 파악**

| # | 확인 항목 |
|---|-----------|
| 1 | App Engineer로부터 변경된 UI/UX 내용 및 갱신된 QA 시나리오 수신 |
| 2 | 변경 전 플로우와 변경 후 플로우의 차이 파악 |
| 3 | 기존 방식으로 수행하지 않도록 주의 (변경 후 방식으로만 수행) |

**② 시나리오 수행**

| # | 확인 항목 |
|---|-----------|
| 1 | **변경된 플로우 기준**으로 시나리오 수행 |
| 2 | 변경 전/후 방식 혼용하지 않도록 주의 |
| 3 | 수행 내용에 변경된 발생 조건을 구체적으로 명시 |

**③ 수행 후 기록 (변경 내용 명시 필수)**

```
- feature      : <feature 값 (예: od, rmd, ld)>
- event_type   : (변경 대상 커맨드 타입)
- session_id   : <수행 세션 ID>
- user_id      : <수행 계정 고유 ID>
- user_name    : <계정명>
- task_id      : <태스크 ID>
- action_date  : <수행 일시>
- 수행 내용    : [변경 후 플로우로 수행] (예: select 없이 직접 transform 수행)
- 변경 사항    : (예: UI 변경으로 select 없이 transform 가능해짐 → Data Engineer C5 판정 시 참고)
```

---

## 역할 간 핸드오프 순서

```
[App Engineer]                    [Data Engineer]               [QA/Tester]
      │                                 │                            │
  ① UI/UX 변경 발생                    │                            │
  ② 변경 유형 분석                      │                            │
     (CloudEvent 구조 변경 여부)         │                            │
  ③ 변경 내용 통보 ──────────────→ ④ 영향 범위 판단                  │
     (구조 변경 유무 명시)            파이프라인 수정 여부 결정         │
                                       │                            │
  ⑤ 앱 배포 ←── 반영 완료 통보 ──────────┘                            │
  (구조 변경 시)                        │                            │
  ⑥ 갱신된 QA 시나리오 공유 ──────────────────────────────→ ⑦ 변경 플로우로 수행
                                       │                            │
                               ⑧ Spot Check ←──── 세션 정보 + 변경 사항 전달
                               ⑨ C5/Q4/Q2 중점 검증
                               ⑩ C5 판정 결과 → QA에게 통보
                                       │
                               ⑪ PASS → 검증 기준 갱신 후 정기 검증 이관
```

---

## 검증 판정 요약

| 단계 | 도구 | Case 3 특이 기준 |
|------|------|------------------|
| Spot Check | `05_spot_check__command_arrival.sql` | 동일 (Raw 도달 + Staging 반영) |
| 완전성 검증 | `04a_validate__completeness.sql` | **C5**: 의도적 플로우 변경인지 확인 후 PASS/이슈 판정 |
| 품질 검증 | `04b_validate__quality.sql` | **Q4, Q2** 집중 확인. 변경된 구조 기준으로 판정 |

---

> 관련 문서: `docs/role_rules__app_engineer.md` / `docs/role_rules__data_engineer.md` / `docs/role_rules__qa_tester.md`
