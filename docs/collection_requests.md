# Labelit 커맨드 로그 수집 정책 및 프로세스

## 역할 정의

| 역할 | 환경 | 책임 |
|------|------|------|
| **App Engineer** | Labelit 개발 환경 | 워크스페이스 커맨드에 로그 삽입 (CloudEvent 스펙 구현 및 배포) |
| **QA / Tester** | Labelit 앱 | 정의된 커맨드를 설계된 플로우대로 동작 테스트 및 수행 정보 기록 |
| **Data Engineer** | Databricks | 수집 정의 반영, 파이프라인 실행, 데이터 도달 검증 |

---

## 수집 프로세스 흐름

```
[App Engineer]                [QA / Tester]              [Data Engineer]
  개발 환경                      Labelit 앱                 Databricks
      │                              │                          │
  ① 커맨드 로그 구현                 │                          │
    CloudEvent 스펙 정의             │                          │
    (feature, event_type,            │                          │
     data 필드 구조)                 │                          │
      │                              │                          │
  ② 스펙 전달 ──────────────────────────────────────────→ ③ 수집 정의 반영
    (커맨드 스펙 문서)                │                    수집 요청 이력 등록
                                      │                    stg 파싱 로직 수정(필요시)
                                      │                    파이프라인 실행 확인
                                      │                          │
  ④ 앱 배포 ←────────────────────────────────────────── 반영 완료 통보
    (파이프라인 반영 확인 후          │                          │
     해당 버전 앱 배포)              │                          │
      │                              │                          │
                              ⑤ 시나리오 액션 수행               │
                                정의된 커맨드를                  │
                                설계된 플로우대로 수행            │
                                (session·task_id·user 기록)     │
                                      │                          │
                              ⑥ 테스트 세션 정보 전달 ────→ ⑦ spot check 실행
                                                            05_spot_check 노트북으로
                                                            Raw 도달 및 Stg 반영 확인
                                                                  │
                                                            ⑧ 정기 검증 이관
                                                            04a/b 검증 배치에 포함
```

---

## 단계별 역할 상세

### ① App Engineer — 커맨드 로그 구현

Labelit 워크스페이스의 커맨드 실행 시점에 CloudEvents 1.0 형식의 로그를 발생시키도록 구현.

**커맨드 스펙 정의 항목** (Data Engineer에게 전달):

```
- feature_value  : 실제 feature 필드값 (예: od, rmd, ld)
- event_type     : CloudEvent type (예: annotation.bbox3d.transform)
- data 구조      : data.changes 배열의 old/new 필드 구조
- 발생 조건      : 어떤 사용자 액션 시 발생하는지
- Command Stack  : undo/redo 대상 여부
```

전달 양식: `docs/command_spec_template.md` 의 템플릿 사용.

---

### ② 스펙 전달 → ③ 수집 정의 반영 (Data Engineer)

App Engineer로부터 커맨드 스펙을 수신한 뒤 파이프라인에 반영.

**반영 체크리스트**:

| # | 확인 항목 | 파일 |
|---|-----------|------|
| 1 | 수집 요청 이력 테이블에 항목 추가 | `docs/collection_requests.md` |
| 2 | `01_raw` ~ `03_int` 파이프라인 실행 확인 | — |
| 3 | App Engineer에게 반영 완료 통보 (앱 배포 요청) | — |

> **핵심**: 파이프라인 반영이 완료된 후에 App Engineer가 앱을 배포해야 합니다.

---

### ④ App Engineer — 앱 배포

Data Engineer로부터 파이프라인 반영 완료 통보를 받은 뒤 해당 커맨드 로그가 포함된 앱 버전을 배포.

> 배포 순서가 뒤바뀌지 않도록 주의. Data Engineer 반영 완료 확인 후 배포 진행.

---

### ⑤ QA / Tester — 시나리오 액션 수행

정의된 커맨드 스펙(`docs/command_spec_template.md`)을 기준으로, 설계된 사용자 플로우대로 액션을 수행하고 정상 동작을 확인.

**QA의 책임 범위**:
- 정의된 커맨드가 앱에서 올바른 플로우로 동작하는지 테스트
- 수행 정보를 기록하여 Data Engineer에게 전달
- 미정의 커맨드 수집 여부나 파이프라인 상태는 QA 책임 범위 밖

**수행 후 기록할 정보** (Data Engineer에게 전달):

```
- feature      : feature 값 (예: od, rmd, ld)
- event_type   : 수행한 커맨드 타입
- session_id   : 수행 세션 ID
- user_id      : 수행 계정 고유 ID
- user_name    : 수행 계정명
- task_id      : 작업한 태스크 ID
- action_date  : 수행 일시 (예: 2026-03-24 오전)  ← 대략적 범위로 충분
- 수행 내용    : (예: bbox3d 오브젝트를 드래그하여 위치 이동 후 undo 실행)
```

> session_id + task_id 조합으로 이벤트를 특정할 수 있으므로 수행 시각은 대략적인 범위면 충분합니다.

---

### ⑥ 테스트 세션 정보 전달 → ⑦ spot check 실행 (Data Engineer)

QA로부터 테스트 세션 정보를 수신하고 `05_spot_check__command_arrival.sql`을 실행.

- Raw 레이어에 이벤트가 도달했는지 확인
- Staging 레이어에 반영됐는지 확인
- 결과: `✅ PASS` → 정기 검증 이관 / `❌ FAIL` → App Engineer 또는 파이프라인 조사

---

### ⑧ 정기 검증 이관 (Data Engineer)

Spot check PASS 이후 이 문서의 이력 테이블을 "✅ 완료"로 업데이트하고
해당 커맨드를 `04a/b` 정기 검증 배치에 포함.

---

## 수집 요청 이력

| # | 요청일 | feature | event_type | 목적 | 스펙 수신 | 반영일 | 확인일 | 상태 |
|---|--------|---------|------------|------|-----------|--------|--------|------|
| 1 | 2026-03-24 | od | annotation.object.select | 라벨러 선택 행동 분석 | ✅ | 2026-03-24 | 2026-03-24 | ✅ 완료 |
| 2 | 2026-03-24 | od | annotation.bbox3d.transform | 3D bbox 이동 거리 분석 | ✅ | 2026-03-24 | 2026-03-24 | ✅ 완료 |
| 3 | 2026-03-24 | od | history.undo | 작업 취소 패턴 분석 | ✅ | 2026-03-24 | 2026-03-24 | ✅ 완료 |
| 4 | 2026-03-24 | od | history.redo | redo 발생 여부 모니터링 | ✅ | 2026-03-24 | — | 🔄 모니터링 중 |
| 5 | 2026-03-24 | rmd | annotation.object.select | rmd 선택 행동 분석 | ✅ | 2026-03-24 | — | 🔄 모니터링 중 |
| 6 | 2026-03-24 | rmd | annotation.bbox3d.transform | rmd 3D bbox 이동 분석 | ✅ | 2026-03-24 | — | 🔄 모니터링 중 |
| 7 | 2026-03-24 | rmd | history.undo | rmd 취소 패턴 분석 | ✅ | 2026-03-24 | — | 🔄 모니터링 중 |
| 8 | 2026-03-24 | rmd | history.redo | rmd redo 발생 여부 모니터링 | ✅ | 2026-03-24 | — | 🔄 모니터링 중 |
| 9 | 2026-03-26 | ld | annotation.line.create | ld 차선 경계선 생성 수집 | ❌ 미수신 | — | — | ⏳ 반영 대기 |
| 10 | 2026-03-26 | ld | annotation.lane.create | ld 차선 오브젝트 생성 수집 | ❌ 미수신 | — | — | ⏳ 반영 대기 |
| 11 | 2026-03-26 | ld | annotation.topology.create | ld 차선 연결관계 생성 수집 | ❌ 미수신 | — | — | ⏳ 반영 대기 |

> **상태 범례**
> - 🔄 모니터링 중: 반영 완료, 정기 검증(04a/b)에서 유입 여부 주기적 확인 중
> - ✅ 완료: spot check 통과, 정기 검증 배치 포함
> - ⏳ 반영 대기: 스펙 수신 전 또는 파이프라인 미반영 (App Engineer 확인 필요)
> - ❌ 철회: 수집 불필요로 판단되어 철회

> **[ld feature 비고]** (항목 9~11)
> - 로그가 정식 수집 요청 이력 등록 전 파이프라인에 유입됨 (절차 선후 관계 미준수)
> - Raw 데이터 포맷이 기존(CloudEvent JSON)과 상이: 파싱·분해된 컬럼 구조로 발행됨 → `raw_labelit__ld` 전용 테이블로 관리 (`notebooks/01_raw__ld.sql`)
> - 공식 스펙 문서, Command Stack 여부 모두 App Engineer 확인 필요
