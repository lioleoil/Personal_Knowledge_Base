# 배포 & 운영 규칙

## 브랜치 전략 (GitHub Flow)

- MUST: main 브랜치에 직접 push 금지 — PR을 통해서만 merge
- MUST: feature 브랜치는 main에서 분기, `feat/`, `fix/` prefix 사용
- MUST: feature 브랜치는 단기 유지 (1-3일), 장기 브랜치 금지

| 환경 | 브랜치 | 배포 방식 |
|------|--------|----------|
| dev | feature 브랜치 | 각 개발자가 `bundle deploy -t dev` (`mode: development`로 격리) |
| prod | main | CI/CD → release tag → `bundle deploy -t prod` (Service Principal) |

- `mode: development`에서 각 개발자의 Job은 `[dev username]` prefix로 격리됨 — 서로 영향 없음
- `mode: production`은 `git.branch: main`에서만 배포 허용

## DABs 지원 리소스 (2026-03 기준)

DABs YAML로 관리 가능한 리소스 타입. 이 목록에 없는 리소스는 UI, REST API, 또는 Terraform으로 관리한다.

| 카테고리 | 리소스 |
|----------|--------|
| Compute | Cluster, Job, Pipeline (DLT), SQL Warehouse |
| Unity Catalog | Catalog, Schema, Volume, External Location, Registered Model |
| ML/AI | Experiment, Model (legacy), Model Serving Endpoint, Quality Monitor |
| Observability | Alert, Dashboard |
| App | App |
| Database | Database Catalog, Database Instance, Synced Database Table, Postgres Branch, Postgres Endpoint, Postgres Project |
| Security | Secret Scope |

**미지원 (UI 또는 API로 관리):**
- ZeroBus / Ingestion Endpoint
- Metastore
- Storage Credential
- Group / Permission (UC Grant)
- Connection
- Share / Recipient (Delta Sharing)

- MUST: DABs 미지원 리소스를 UI/API로 설정한 경우, [docs/ui-managed-resources.dev.md](../ui-managed-resources.dev.md)에 설정 내용을 기록한다
- TODO: Group, UC Grant는 Terraform(`sv-data-pipeline-infra`)으로 이관 예정 → [docs/backlog.md](../backlog.md) 참고

## Pre-commit Hooks

커밋 시 자동 검증. `pre-commit install`로 활성화.

| Hook | 대상 | 역할 |
|------|------|------|
| yamllint | `*.yml` | YAML 포맷 검증 |
| check-naming (DIC-788) | `nova/models/`, `nova/resources/` | 파일명 네이밍 규칙 |
| check-sql-select-star | `nova/models/staging/*.sql` | `SELECT *` 차단 |

## Job 중복 방지 ([ADR-005](../adrs/005-dabs-worktree-state.md))

- MUST: 새 환경(워크트리, 다른 머신)에서 첫 `bundle deploy` 전에 기존 Job 확인
  ```bash
  databricks jobs list --profile dev | grep "<job_name>"
  ```
- MUST: 중복 발견 시 이전 Job 삭제 후 배포
- MUST: 워크트리 제거 전 `bundle destroy -t dev`로 리소스 정리

## 기타

- MUST: `databricks.yml` 수정 시 **CODEOWNERS 승인** (모든 리소스에 영향)
- `data_security_mode`는 명시하지 않음 (Auto — Runtime 15.4+ 기본값 Standard로 충분)
- MUST: prod는 Service Principal만 배포. 일반 사용자는 조회만 가능
- WARNING: UI에서 직접 수정한 내용은 다음 `bundle deploy` 시 Git 기준으로 덮어쓰기됨
