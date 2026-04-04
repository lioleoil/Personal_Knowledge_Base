# Role Rules — QA / Tester

## 역할 개요

| 항목 | 내용 |
|------|------|
| **역할** | QA / Tester |
| **환경** | Labelit 앱 (Databricks 아님) |
| **핵심 책임** | 정의된 커맨드를 설계된 플로우대로 동작 테스트 및 수행 정보 기록 |

---

## 책임 범위

### 담당
- 커맨드 스펙 정의서(`docs/command_spec_template.md`)에 기재된 QA 시나리오 수행
- 정의된 커맨드가 앱에서 설계된 플로우대로 정상 동작하는지 확인
- 수행 세션 정보 기록 및 Data Engineer에게 전달

### 담당하지 않음
- 미정의 커맨드가 수집되는지 여부 탐지 (Data Engineer 역할)
- 파이프라인 데이터 도달 여부 확인 (Data Engineer 역할)
- 앱 로그 구현 (App Engineer 역할)
- spot check 실행 (Data Engineer 역할)

---

## 워크플로우

```
① 커맨드 스펙 수신
   - App Engineer가 제공한 docs/command_spec_template.md 의 QA 시나리오 확인
   - 수행할 커맨드 타입, 액션 방법, 예상 동작 파악

② 앱에서 시나리오 액션 수행
   - 단일 세션 · 단일 태스크 기준으로 수행
   - 정의된 QA 시나리오대로 정확하게 액션 수행
   - 수행 시작 시각 대략적으로 메모 (정확한 초 단위 불필요)

③ 수행 정보 기록
   - 아래 기록 양식에 따라 정보 기록

④ Data Engineer에게 전달
   - 기록한 세션 정보를 Data Engineer에게 전달
   - Data Engineer가 spot check를 실행할 수 있도록 정보 제공
```

---

## 수행 후 기록 양식

Data Engineer에게 전달할 정보:

```
- feature      : feature 값 (예: od, rmd, ld)
- event_type   : 수행한 커맨드 타입  (예: annotation.bbox3d.transform)
- session_id   : 수행 세션 ID
- user_id      : 수행 계정 고유 ID
- user_name    : 수행 계정명
- task_id      : 작업한 태스크 ID
- action_date  : 수행 일시  (예: 2026-03-24 오전)  ← 대략적 범위로 충분
- 수행 내용    : (예: bbox3d 오브젝트를 드래그하여 위치 이동 후 undo 실행)
```

> session_id + task_id 조합으로 이벤트를 특정할 수 있으므로
> 수행 시각은 날짜·오전/오후 수준의 대략적 범위면 충분합니다.

---

## QA 시나리오 수행 기준

| 커맨드 타입 | 수행 방법 | 비고 |
|-------------|-----------|------|
| `annotation.object.select` | 3D 뷰어에서 오브젝트 클릭하여 선택 | 단일 또는 다중 선택 |
| `annotation.bbox3d.transform` | 선택된 오브젝트 드래그하여 이동·회전·크기 변경 | select 먼저 수행 후 transform |
| `history.undo` | Ctrl+Z 또는 툴바 undo 버튼 클릭 | 직전 커맨드 취소 |
| `history.redo` | Ctrl+Y 또는 툴바 redo 버튼 클릭 | undo 이후에만 발생 가능 |

> 각 커맨드의 상세 QA 시나리오는 `docs/command_spec_template.md` 의 해당 커맨드 스펙 참고.

---

## 핵심 규칙

1. **단일 세션 수행**: 테스트는 하나의 세션 안에서 수행 (세션 전환 없이)
2. **스펙 기반 수행**: command_spec_template.md의 QA 시나리오대로 정확하게 수행
3. **session_id 반드시 기록**: spot check 필터의 핵심 식별자
4. **미정의 커맨드 탐지 불필요**: 정의된 커맨드 동작 확인이 QA의 역할

---

## 인수인계 (Handoff)

| 방향 | 내용 | 수단 |
|------|------|------|
| ← App Engineer | 커맨드 스펙 정의서 (QA 시나리오 포함) 수신 | `docs/command_spec_template.md` |
| → Data Engineer | 수행 세션 정보 전달 | 위 기록 양식 사용 |

---

## 실패 처리

| 상황 | 조치 |
|------|------|
| 앱에서 커맨드가 발생하지 않음 | App Engineer에게 구현 여부 확인 요청 |
| 앱 배포가 되어 있지 않음 | App Engineer 또는 Data Engineer에게 배포 완료 여부 확인 |
| Data Engineer의 spot check FAIL 통보 | 수행 정보(session_id, task_id 등)가 정확한지 재확인 후 재전달 |
