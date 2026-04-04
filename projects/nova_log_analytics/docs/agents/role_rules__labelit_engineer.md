# Role Rules — Labelit Engineer

## 역할 개요

| 항목 | 내용 |
|------|------|
| **역할** | Labelit Engineer |
| **환경** | Labelit 개발 환경 (Databricks 아님) |
| **핵심 책임** | Labelit 워크스페이스 커맨드에 CloudEvent 로그 구현 및 배포 |

---

## 책임 범위

### 담당
- 커맨드 실행 시점에 CloudEvents 1.0 형식 로그 발생 구현
- 커맨드 스펙 정의서 작성 (`docs/command_spec_template.md` 템플릿 사용)
- Nova Engineer에게 스펙 전달
- 파이프라인 반영 완료 통보 수신 후 앱 배포

### 담당하지 않음
- 파이프라인 데이터 도달 여부 확인 (Nova Engineer 역할)
- 미정의 커맨드 수집 탐지 (Nova Engineer 역할)
- QA 시나리오 수행 (QA/Tester 역할)

---

## 워크플로우

```
① 커맨드 로그 구현
   - CloudEvents 1.0 스펙으로 이벤트 발생 로직 구현
   - feature, event_type, data 구조, params, changes 배열 구현

② 커맨드 스펙 정의서 작성
   - docs/command_spec_template.md 의 템플릿 사용
   - feature_value, event_type, data 구조,
     발생 조건, Command Stack 여부, QA 시나리오 기술

③ Nova Engineer에게 스펙 전달
   - 작성 완료된 스펙 정의서를 Nova Engineer에게 전달
   - Nova Engineer가 파이프라인에 반영할 때까지 배포 대기

④ 파이프라인 반영 완료 통보 수신
   - Nova Engineer로부터 반영 완료 통보를 받은 뒤 배포 진행
   - 통보 전 배포 시 로그가 'unknown'으로 처리될 수 있음 (주의)

⑤ 앱 배포
   - 배포 전 체크리스트 확인 후 배포 진행
```

---

## 배포 전 체크리스트

| # | 확인 항목 |
|---|-----------|
| 1 | CloudEvent 구조가 스펙 정의서와 일치하는지 확인 |
| 2 | `data.user.id`, `data.user.name`, `data.project.task_id` 필드 구현 여부 확인 |
| 3 | `params.updateCount` (transform) / `params.selectedCount` (select) 값이 `changes` 배열 크기와 일치하는지 확인 |
| 4 | Command Stack 해당 커맨드에 `reverted_command_id` / `reverted_command_type` / `count` 필드 포함 여부 확인 |
| 5 | Nova Engineer로부터 파이프라인 반영 완료 통보 수신 확인 |

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
  feature      : <feature_value>        ← 예: "od" / "rmd" / "ld"
  user:
    id         : <사용자 고유 ID>        ← 파이프라인에서 user_id 컬럼으로 파싱
    name       : <사용자 계정명>         ← 파이프라인에서 user_name 컬럼으로 파싱
  project:
    task_id    : <태스크 ID>
  params       : <파라미터 구조>         ← 없으면 생략
  changes      : [...]                  ← 없으면 빈 배열 []
```

---

## 핵심 규칙

1. **배포 순서 준수**: Nova Engineer의 파이프라인 반영 완료 통보 이후에만 배포
2. **user.id 필수**: `data.user.id` 와 `data.user.name` 모두 구현 (id 누락 시 파이프라인에서 NULL)
3. **params 정합성**: `params.updateCount` (또는 `selectedCount`) 값 = `changes` 배열 원소 수

---

## 인수인계 (Handoff)

| 방향 | 내용 | 수단 |
|------|------|------|
| → Nova Engineer | 커맨드 스펙 정의서 전달 | `docs/command_spec_template.md` 작성 후 전달 |
| ← Nova Engineer | 파이프라인 반영 완료 통보 수신 | 통보 수신 후 배포 진행 |

---

## 실패 처리

| 상황 | 조치 |
|------|------|
| Spot Check FAIL (Raw 미도달) | Nova Engineer와 협력하여 CloudEvent 발생 여부 및 구조 확인 |
| Q2 user_id NULL 발생 | `data.user.id` 필드 구현 여부 확인 |
