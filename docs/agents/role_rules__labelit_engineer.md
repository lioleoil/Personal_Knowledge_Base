# Role Rules — Labelit Engineer

## 역할 개요

| 항목 | 내용 |
|------|------|
| **역할** | Labelit Engineer |
| **환경** | Labelit 개발 환경 |
| **핵심 책임** | Labelit 워크스페이스 커맨드에 CloudEvent 로그 구현 및 배포 |

---

## 책임 범위

### 담당
- 커맨드 실행 시점에 CloudEvents 형식 로그 발생 구현
- 커맨드 스펙 정의서 작성 (`docs/command_spec_template.md` 템플릿 사용)
- Nova Engineer에게 스펙 전달
- 앱 배포

### 담당하지 않음
- 이상 탐지 검증 실행 (Nova Engineer 역할)
- 미정의 커맨드 수집 탐지 (Nova Engineer 역할)
- QA 시나리오 수행 (QA/Tester 역할)

---

## 워크플로우

**① 커맨드 로그 구현**

| # | 내용 |
|---|------|
| 1 | CloudEvents 1.0 스펙으로 이벤트 발생 로직 구현 |
| 2 | feature, event_type, data 구조, params, changes 배열 구현 |

**② 커맨드 스펙 정의서 작성**

| # | 내용 |
|---|------|
| 1 | `docs/command_spec_template.md` 템플릿 사용 |
| 2 | feature, event_type, data 구조, 발생 조건, Command Stack 여부, QA 시나리오 기술 |

**③ Nova Engineer에게 스펙 전달**

| # | 내용 |
|---|------|
| 1 | 작성 완료된 스펙 정의서를 Nova Engineer에게 전달 |

**④ 앱 배포**

| # | 내용 |
|---|------|
| 1 | 배포 전 체크리스트 확인 후 배포 진행 |
| 2 | 배포 후 QA에게 수행 가능한 커맨드 목록 공유 |

---

## 배포 전 체크리스트

| # | 확인 항목 |
|---|-----------|
| 1 | CloudEvent 구조가 스펙 정의서와 일치하는지 확인 |
| 2 | `data.user.id`, `data.user.name`, `data.project.task_id` 필드 구현 여부 확인 |
| 3 | `params.updateCount` (transform) / `params.selectedCount` (select) 값이 `changes` 배열 크기와 일치하는지 확인 |
| 4 | Command Stack 해당 커맨드에 `reverted_command.id` / `reverted_command.type` 필드 포함 여부 확인 |
| 5 | 기존 커맨드와 동일한 event_type을 사용하는 경우, data 구조 차이를 스펙 정의서에 반드시 명시 (Nova Engineer 검증 판단에 필요) |

---

## CloudEvent 필수 필드

```
specversion  : "1.0"
id           : <UUID>
source       : <앱 소스 경로>
type         : <event_type>
time         : <ISO 8601, 클라이언트 발생 시각>
sessionid    : <세션 식별자>
data:
  feature      : <feature 값>               ← 예: "od", "rmd", "ld"
  user:
    id         : <사용자 고유 ID>            ← Nova Engineer Stage 1 user_id 검증에 활용
    name       : <사용자 계정명>
  project:
    task_id    : <태스크 ID>
  params       : <파라미터 구조>             ← 없으면 생략
  changes      : [...]                      ← 없으면 빈 배열 []
```

---

## 인수인계 (Handoff)

| 방향 | 내용 | 수단 |
|------|------|------|
| → Nova Engineer | 커맨드 스펙 정의서 전달 | `docs/command_spec_template.md` 작성 후 전달 |
| → QA / Tester | 배포 완료 및 수행 커맨드 목록 공유 | 직접 전달 |

---

## 실패 처리

| 상황 | 조치 |
|------|------|
| Stage 1 이상 발견 통보 수신 | Nova Engineer와 협력하여 CloudEvent 구조 및 data 필드 구현 여부 확인 |
