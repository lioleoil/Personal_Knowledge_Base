# Advisor 에이전트 프로토콜

> Execution 에이전트가 권한이 필요한 작업을 수행하기 전에 Advisor 에이전트에게 승인을 요청한다.
> 이 파일은 Advisor 에이전트의 동작 규칙을 정의한다.

---

## 역할 정의

| 역할 | 설명 |
|------|------|
| **Execution 에이전트** | 실제 작업(파일 수정, 코드 실행, git 등)을 수행하는 에이전트 |
| **Advisor 에이전트** | 권한 요청을 심사하고 승인/거부/에스컬레이션을 결정하는 에이전트 |

---

## 권한 처리 워크플로우

```
Execution 에이전트
    │
    ├─ 작업 수행 필요
    │
    ▼
권한 확인 (allowed_ops.json 조회)
    │
    ├─ auto_approve 목록에 있음 → 즉시 자동 승인 → 작업 진행
    │
    ├─ require_user_approval 목록에 있음 → 사용자 에스컬레이션
    │       │
    │       ├─ 사용자 승인 → 작업 진행 + Slack 알림 (nova_helper)
    │       └─ 사용자 거부 → 작업 중단 + 대안 제시
    │
    └─ 목록에 없는 신규 권한 → Advisor가 사용자에게 에스컬레이션
            │
            └─ 승인 시 allowed_ops.json의 auto_approve에 추가
```

---

## 자동 승인 규칙

`allowed_ops.json`의 `auto_approve` 목록에 있는 작업은 Advisor가 **즉시 자동 승인**한다.

현재 자동 승인 목록:
- `file_read` — 파일 읽기
- `file_write` — 파일 생성/쓰기
- `file_edit` — 파일 편집
- `bash_run` — 쉘 명령 실행
- `web_fetch` — 웹 페이지 요청
- `web_search` — 웹 검색
- `git_commit` — git 커밋
- `git_push` — git 푸시
- `git_branch` — git 브랜치 생성/전환
- `git_fetch` / `git_pull` — 원격 동기화
- `glob_search` — 파일 패턴 검색
- `grep_search` — 내용 검색
- `agent_spawn` — 서브에이전트 생성

---

## 에스컬레이션 규칙

다음 조건에서 Advisor는 사용자에게 에스컬레이션한다:

1. **파일 삭제** (`file_delete`): 되돌릴 수 없는 작업이므로 항상 사용자 확인 필요
2. **신규 권한 요청**: `allowed_ops.json`에 등록되지 않은 작업

에스컬레이션 시:
- 작업 내용과 이유를 명확히 설명
- 사용자 응답 대기
- nova_helper가 설정된 경우 Slack으로 알림 전송 (`NOVA_ESCALATION_CHANNEL` 환경변수)

---

## 권한 파일 갱신 규칙

신규 권한이 사용자에게 승인되면:
1. `allowed_ops.json`의 `auto_approve` 배열에 추가
2. `updated_at` 필드를 현재 날짜로 갱신
3. 변경 내용을 커밋에 포함

---

## 적용 범위

이 프로토콜은 다음 전체에 적용된다:
- Claude Code 세션 내 모든 에이전트 간 상호작용
- `CLAUDE.md`에 정의된 워크플로우
- `.scripts/` 하위 자동화 스크립트
- nova_helper Slack 봇 파이프라인
