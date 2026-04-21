# Multi-Agent Ecosystem — 설계 및 R&R 정의서

> **버전**: 1.2 | **최종 수정**: 2026-04-12  
> 이 문서는 Personal Knowledge Base 워크스페이스의 Multi-Agent Ecosystem 전체 설계, 역할 정의, 워크플로우, 통신 프로토콜, 권한 정책을 단일 참조 문서로 통합합니다.  
> 빠른 구조도 참조: **[ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md)**

---

## 목차

1. [설계 철학](#1-설계-철학)
2. [전체 아키텍처](#2-전체-아키텍처)
3. [에이전트 R&R 정의](#3-에이전트-rr-정의)
   - 3.0 User Interface Agent (**신규**)
   - 3.1 Orchestrator
   - 3.2 Execution Agent
   - 3.3 Validation Agent
   - 3.4 Advisor Agent (**PM 역할 격상**)
   - 3.5 Reporter Agent
   - 3.6 Domain Sub-Agents
4. [Agent Bus 통신 프로토콜](#4-agent-bus-통신-프로토콜)
5. [권한 위임 시스템](#5-권한-위임-시스템)
6. [에스컬레이션 플로우](#6-에스컬레이션-플로우)
7. [병렬 실행 정책](#7-병렬-실행-정책)
8. [파일 시스템 레이아웃](#8-파일-시스템-레이아웃)
9. [인프라 스크립트 참조](#9-인프라-스크립트-참조)
10. [운영 가이드](#10-운영-가이드)
11. [변경 이력](#11-변경-이력)

---

## 1. 설계 철학

### 핵심 원칙

| # | 원칙 | 설명 |
|---|---|---|
| 1 | **단방향 의존성** | Domain → Execution → Validation → Advisor. 역방향 호출 없음. |
| 2 | **파일 기반 비동기 버스** | `.agents/bus/` JSON 파일로 에이전트 간 통신. 재시작 내성·상태 영속. |
| 3 | **역할 경계 명확화** | Validation은 수정 권한 없음. Advisor는 실행 권한 없음. Reporter는 PASS 후에만 활성. |
| 4 | **토큰 예산 인식** | 잔여 10,000 미만 시 병렬 spawn → 순차 전환. |
| 5 | **기존 인프라 재사용** | AgentLog 패턴 유지. monitor.py 최소 수정. |
| 6 | **도메인 격리** | 각 Domain Agent는 자신의 role_rules만 읽음. 타 도메인 파일 접근 불가. |
| 7 | **멱등성** | 동일 task_id 재시도 시 파일 덮어쓰기만 발생. 부작용 없음. |
| 8 | **최소 권한 원칙** | 자동 승인 권한 목록 명시. 파일 삭제는 항상 사용자 동의 필요. |

### 설계 결정 근거

- **파일 기반 버스 선택 이유**: Python subprocess 간 공유 메모리 불가. 파일은 프로세스 경계를 넘어 상태 영속 가능. 장애 후 재시작 시 중간 상태 복구 가능.
- **Peer 레벨 Validation 선택 이유**: Execution이 자기 결과를 검증하면 편향 발생. 독립 Validation이 객관적 교차 검토 보장.
- **Advisor 조건부 활성 이유**: 매 사이클 Advisor 참여 시 토큰 낭비. FAIL/막힘 상황에서만 호출하여 비용 최적화.
- **User Interface Agent 추가 이유**: 사용자-에이전트 소통 창구 표준화. 내부 로그가 터미널에 노출되지 않도록 분리.
- **Advisor PM 격상 이유**: 반응형 개입만으로는 작업 품질 보장 불충분. 사전 플랜 수립·사후 평가를 통해 자기개선 루프 구현.

---

## 2. 전체 아키텍처 (v2.0)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     USER INTERFACE AGENT (Haiku)                    │
│  - 사용자 요구사항 수신 → 구조화 → Advisor로 전달                    │
│  - 에이전트 소통은 터미널 미출력, 로그 파일만 기록                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ requirement.json
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ADVISOR AGENT (PM / Opus 4.7)                    │
│  Phase 1: 컨텍스트 파악 (로컬 + WebSearch)                          │
│  Phase 2: 플랜 수립 → global/05_PM_Outputs/advisor_plan_*.md        │
│  Phase 3: Execution·Validation 루프 감독                            │
│  Phase 4: 결과 리뷰                                                 │
│  Phase 5: 10항목 평가 보고서 생성 → 사용자 승인 게이트              │
│  Phase 6: 로그 분석 → 자기개선 (learnings/)                        │
└──────┬───────────────────────────────────────────────┬──────────────┘
       │ advisor_plan.json                              │ advice.json
       ▼                                               │
┌──────────────────────────┐               ┌───────────┴─────────────┐
│   EXECUTION AGENT        │◄─────────────►│  VALIDATION AGENT       │
│   (Sonnet/Haiku by       │  피드백 루프   │  (gpt-4.1 / codex-1)   │
│    domain preset)        │               │  PASS/FAIL/INSUFFICIENT │
│   - Domain Sub-Agent     │               └─────────────────────────┘
│     spawn                │                           │ PASS
└──────────────────────────┘                           ▼
                                            ADVISOR REVIEW & EVAL
                                                       │ evaluation.json
                                            사용자 승인 게이트
                                            approve → commit → PR
                                            거절 → 파이프라인 종료
                                            피드백 → 보완 후 재평가

[주간 회고 — 매주 토요일 15:00]
.scripts/retrospective.py
  → 주간 로그 + 평가 보고서 분석
  → global/05_PM_Outputs/retrospective_{YYYY-MM-DD}.md 저장
```

### v1.x 기본 아키텍처 (--auto 모드)

```
사용자 요청
    │
    ▼
┌─────────────────────────────────────────────┐
│  Orchestrator (.scripts/orchestrator.py)     │
│  - 토큰 예산 확인                            │
│  - Task Manifest 생성 (.agents/bus/)         │
│  - 병렬/순차 모드 결정                       │
└──────────────┬──────────────────────────────┘
               │ spawn
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Peer Layer (동등 권한)                         │
│                                                                  │
│  ┌─────────────────────────┐    ┌─────────────────────────────┐  │
│  │    Execution Agent      │◄──►│    Validation Agent         │  │
│  │  - 작업 분해 · 분배      │    │  - 독립 검증 (Read-only)    │  │
│  │  - 권한 요청 → Advisor   │    │  - verdict: PASS/FAIL/INS.  │  │
│  │  - 결과 수집             │    │  - issues 리포트 작성        │  │
│  └──────────┬──────────────┘    └────────────┬────────────────┘  │
└─────────────┼────────────────────────────────┼────────────────────┘
              │ spawn                          │ FAIL
              ▼                               ▼
┌─────────────────────────────┐   ┌──────────────────────────────┐
│   Domain Sub-Agents         │   │    Advisor Agent              │
│   (Read/Write/Edit/Bash)    │   │    (Read-only + advice.json)  │
│                             │   │    - 근본 원인 분석            │
│  ┌──────────────────────┐   │   │    - 솔루션 명세              │
│  │ nova_helper          │   │   │    - 권한 자동 승인            │
│  │ nova_log_analytics   │   │   │    - escalate_to_user 판단    │
│  │ pkb_worklog          │   │   └──────────────────────────────┘
│  │ sv_dqat              │   │
│  │ sv_lakehouse         │   │
│  │ daily_scrap          │   │
│  └──────────────────────┘   │
└─────────────────────────────┘
              │ PASS (from Validation)
              ▼
┌─────────────────────────────┐
│    Reporter Agent           │
│    (Read-only + report.json)│
│    - 마크다운 보고서 생성    │
│    - Slack 알림 (선택)       │
│    - PM Outputs 저장         │
└─────────────┬───────────────┘
              │
              ▼
         사용자 보고
```

---

## 3. 에이전트 R&R 정의

### 3.0 User Interface Agent (**신규 — v1.2**)

**Role Rules**: `global/04_AgentEcosystem/agents/role_rules__user_interface.md`

| 항목 | 내용 |
|---|---|
| **목적** | 사용자 자연어 요청 수신 → 구조화 → Advisor 전달. 평가 보고서 포워딩. |
| **모델** | `claude-haiku-4-5-20251001` (경량) |
| **권한** | Read (입력/보고서) + Write (`_requirement.json`, `_user_decision.json`) |
| **제약** | 에이전트 내부 소통 터미널 출력 금지. 실행 작업 수행 불가. |

**핵심 책임**:
1. 사용자 요청 구조화 → `_requirement.json`
2. Advisor 플랜 도착 시 사용자에게 포워딩
3. 평가 보고서 출력 + 승인/거절/피드백 수집 → `_user_decision.json`

---

### 3.1 Orchestrator

**파일**: `.scripts/orchestrator.py`  
**역할**: 사용자와 에이전트 생태계 사이의 진입점. 파이프라인을 조율하되 직접 실행하지 않음.

| 항목 | 내용 |
|---|---|
| **주요 책임** | 요청 수신, 토큰 예산 확인, Manifest 생성, 에이전트 spawn |
| **권한** | Read/Write (버스 파일) / Bash (subprocess `claude -p`) |
| **제약** | 도메인 작업 직접 수행 불가. 검증 없이 사용자 보고 불가. |
| **입력** | CLI 인수 (`--task`, `--domain`, `--domains`, `--auto`, `--parallel`) |
| **출력** | AgentLog, Bus Manifest, 실행 지시문 또는 자동 실행 |

**실행 모드**:

| 모드 | 플래그 | 동작 |
|---|---|---|
| 기본 | (없음) | Manifest 생성 + Execution 프롬프트 출력 |
| Dry Run | `--dry-run` | Manifest + 프롬프트 미리보기만 |
| Auto (순차) | `--auto` | claude CLI로 Execution→Validation→Reporter 자동 실행 |
| Auto (병렬) | `--auto --parallel` | 복수 도메인 병렬 실행 (ThreadPoolExecutor) |
| 목록 | `--list` | Bus 작업 목록 조회 |

---

### 3.2 Execution Agent

**Role Rules**: `global/04_AgentEcosystem/agents/role_rules__execution.md`

| 항목 | 내용 |
|---|---|
| **목적** | 사용자 요청을 도메인 task로 분해하고 Domain Sub-Agent에 분배, 결과 수집 후 Validation 요청 |
| **권한** | Read / Write / Edit / Bash (Sub-agent spawn 포함) |
| **제약** | 최종 보고 불가 (Reporter 위임). Validation 통과 전 사용자 직접 응답 금지. |
| **실패 조건** | 재시도 5회 초과 → Advisor 호출. Advisor 3회 초과 → 사용자 에스컬레이션. |

**핵심 책임**:
1. Task Manifest 작성 → `.agents/bus/<task_id>_manifest.json`
2. Domain Sub-Agent spawn (독립 태스크는 병렬)
3. Result Manifest 수집 → `.agents/bus/<task_id>_result.json`
4. Validation Agent에 검증 요청
5. Validation FAIL 시 Advisor 호출 또는 자체 재시도

**재시도 정책**:

| 재시도 횟수 | 동작 |
|---|---|
| 1~2회 | 동일 manifest 재전송 |
| 3~5회 | `deadline_hint` 2배 연장 후 재전송 |
| 5회 초과 | Advisor 호출. 자체 재시도 중단. |

**권한 요청 워크플로우**:
1. 제한된 작업 전 `.agents/bus/<task_id>_granted_permissions.json` 확인
2. 권한 없으면 `_permission_request.json` 작성 → Advisor 대기
3. 파일 삭제: 항상 Advisor → 사용자 에스컬레이션. 직접 시도 절대 금지.

---

### 3.3 Validation Agent

**Role Rules**: `global/04_AgentEcosystem/agents/role_rules__validation.md`

| 항목 | 내용 |
|---|---|
| **목적** | Execution 결과를 독립적 관점에서 검증. 3단계 교차 검토. |
| **권한** | Read-only (전체) + Write (`_validation.json` 단독) |
| **제약** | Execution 파일 직접 수정 불가. 이슈는 validation.json으로만 전달. 사용자 직접 보고 불가. |

**검증 3단계**:

| 단계 | 기준 | 확인 항목 |
|---|---|---|
| **구조 검증** | 스키마 준수 | outputs 필드 완전성, status 값 유효성, 파일 실존 여부 |
| **일관성 검증** | 기존 코드·문서 충돌 없음 | 네이밍 컨벤션, 스키마 호환성, Domain role_rules 준수 |
| **완결성 검증** | 요청 완전 이행 | expected_outputs 전항목 커버, errors 목록 비어있음 |

**판정 기준**:

| verdict | 조건 | 후속 동작 |
|---|---|---|
| `PASS` | 3단계 모두 통과, errors 없음 | Reporter 활성화 |
| `INSUFFICIENT` | 구조 유효하나 expected_outputs 일부 누락 | Execution 재시도 (최대 5회) |
| `FAIL` | 구조 오류 / 일관성 위반 / 심각한 에러 | Advisor 호출 (advisor_needed=true 시) |

---

### 3.4 Advisor Agent

**Role Rules**: `global/04_AgentEcosystem/agents/role_rules__advisor.md`

| 항목 | 내용 |
|---|---|
| **목적** | Validation FAIL 또는 Execution 막힘 시 근본 원인 분석 + 솔루션 명세 제공 |
| **활성화 조건** | (a) verdict=FAIL + advisor_needed=true (b) Execution 5회 재시도 실패 |
| **권한** | Read-only (전체) + Write (`_advice.json`, `_granted_permissions.json` 단독) |
| **제약** | 직접 실행 불가. 솔루션 명세만 출력. Execution이 실행 주체. |

**권한 위임 역할** (Permission Delegation):
- 시작 시 `allowed_permissions.json` 로드
- 권한 요청(`_permission_request.json`) 수신 시:
  - `auto_approved` 목록에 있으면 → 즉시 `_granted_permissions.json` 작성
  - `user_approval_required`(특히 `file_delete`) → `escalate_to_user=true`
- 목록에 없는 권한 → `escalate_if_not_in_registry=true` 정책에 따라 에스컬레이션
- **Advisor는 새 권한을 생성할 수 없음** (`can_grant_new_permissions: false`)

**솔루션 우선순위**:

| priority | target_agent | 의미 |
|---|---|---|
| 1 | `domain` | 도메인 재실행 (파라미터 조정) |
| 2 | `execution` | Execution 전략 변경 |
| 3+ | `user` | 사용자 결정 필요 (`escalate_to_user: true`) |

**에스컬레이션 판단 기준** (`escalate_to_user: true` 설정):
- API 키 / 접근 권한 필요
- 외부 서비스 장애
- 데이터 손실 위험 작업
- Advisor 3회 호출 후 여전히 FAIL
- `file_delete` 또는 `user_approval_required` 권한 요청

---

### 3.5 Reporter Agent

**Role Rules**: `global/04_AgentEcosystem/agents/role_rules__reporter.md`

| 항목 | 내용 |
|---|---|
| **목적** | Validation PASS 후 결과를 사용자에게 구조화된 형태로 보고 |
| **활성화 조건** | (a) verdict=PASS (b) escalate_to_user=true (중간 보고) |
| **권한** | Read-only (버스 파일) + Write (`_report.json`, `global/05_PM_Outputs/*.md`) |
| **제약** | PASS 확인 전 보고서 생성 불가. 추측성 내용 포함 불가. |

**보고서 저장 기준**:

| 저장 O | 저장 X |
|---|---|
| 도메인 분석 결과 (anomaly, DQ report) | 단순 조회 결과 |
| PM 산출물 (OKR, PRD) | 에러 보고 (중간 보고) |
| 복수 도메인 종합 보고 | 5줄 이하 단순 결과 |

**Slack 알림** (선택):
- `SLACK_WEBHOOK_URL` 또는 `SLACK_BOT_TOKEN + SLACK_ESCALATION_CHANNEL` 환경변수 설정 시 자동 발송
- escalate_to_user=true 중간 보고 시에도 Slack 알림

---

### 3.6 Domain Sub-Agents

각 Domain Agent는 자신의 `role_rules` 파일만 읽음. 타 도메인 파일 접근 불가.

| Domain | agent_type | Role Rules | 담당 파일 | 주요 책임 |
|---|---|---|---|---|
| **nova_helper** | `nova_helper` | `domains/role_rules__nova_helper.md` | `projects/nova_helper/` | Slack 봇, OKR, Confluence 연동 |
| **nova_log_analytics** | `nova_log_analytics` | `domains/role_rules__nova_log_analytics.md` | `projects/nova_log_analytics/` | 이상탐지, SQL 파이프라인 |
| **PKB WorkLog** | `pkb_worklog` | `domains/role_rules__pkb_worklog.md` | `projects/personal_knowledge_base/04_WorkLog/` | 대화 분류, INDEX 갱신 |
| **SV DQAT** | `sv_dqat` | `domains/role_rules__sv.md` | `projects/sv_dqat/` | 데이터 품질 검증, DQ 리포트 |
| **SV Lakehouse** | `sv_lakehouse` | `domains/role_rules__sv.md` | `projects/sv_lakehouse/` | 데이터 파이프라인 |
| **Daily Scrap** | `daily_scrap` | `domains/role_rules__pkb_worklog.md` | `.scripts/daily_scrap_runner.py` | GeekNews 스크랩, WorkLog 기록 |

**공통 제약**:
- 타 도메인 디렉터리 접근 금지
- DB 스키마 변경 금지 (SELECT/분석 쿼리만)
- 결과 파일 덮어쓰기 금지 → 날짜 suffix 필수 (`_YYYY-MM-DD`)
- verbatim 복사 금지 → 요약 형태로 append

---

## 4. Agent Bus 통신 프로토콜

### 버스 파일 유형

| 파일 패턴 | 방향 | 작성 주체 | 설명 |
|---|---|---|---|
| `<id>_manifest.json` | Execution → Domain | Execution | 태스크 지시 |
| `<id>_result.json` | Domain → Execution | Domain | 실행 결과 |
| `<id>_validation.json` | Bus | Validation | 검증 판정 |
| `<id>_advice.json` | Bus | Advisor | 솔루션 명세 |
| `<id>_report.json` | Bus | Reporter | 최종 보고 요약 |
| `<id>_permission_request.json` | Execution → Advisor | Execution | 권한 요청 |
| `<id>_granted_permissions.json` | Advisor → Execution | Advisor | 승인된 권한 목록 |
| `<id>_requirement.json` | UserInterface → Advisor | UserInterface | 구조화된 사용자 요구사항 (**v1.2**) |
| `<id>_advisor_plan.json` | Advisor → Execution | Advisor | 플랜 + 에이전트별 지시 (**v1.2**) |
| `<id>_evaluation.json` | Advisor → User | Advisor | 10항목 평가 보고서 (**v1.2**) |
| `<id>_user_decision.json` | User → Advisor | UserInterface | 승인/거절/피드백 (**v1.2**) |
| `<id>_learning.json` | Advisor 내부 | Advisor | 자기개선 메모 (**v1.2**) |

**Python 유틸리티**:
- `AgentBus` 클래스: `.scripts/agent_bus.py`
- `PermissionBus` 클래스: `.scripts/permission_bus.py`

### Manifest 스키마

```json
{
  "task_id": "abc12345",
  "created_at": "ISO8601",
  "parent_agent": "execution",
  "domain": "nova_log_analytics",
  "instructions": "이상탐지 파이프라인 실행",
  "context_files": ["projects/nova_log_analytics/config.yaml"],
  "expected_outputs": ["type:anomaly_report"],
  "deadline_hint": "10min",
  "retry_count": 0
}
```

### Validation 스키마

```json
{
  "verdict": "FAIL",
  "issues": [
    {"severity": "HIGH", "item": "sql_result", "reason": "expected_outputs 누락"}
  ],
  "passed_checks": ["구조 검증"],
  "advisor_needed": true
}
```

### Advice 스키마

```json
{
  "root_cause": "SQL 타임아웃",
  "solutions": [
    {"priority": 1, "action": "timeout=60s로 재실행", "target_agent": "domain"},
    {"priority": 2, "action": "sql_result 없이 보고 진행", "target_agent": "execution"}
  ],
  "escalate_to_user": false
}
```

---

## 5. 권한 위임 시스템

### 권한 레지스트리

**파일**: `global/04_AgentEcosystem/allowed_permissions.json`

```
자동 승인 (Advisor 즉시 처리)
├── file_read     — 전체 읽기 허용
├── file_write    — 프로젝트 루트 내 쓰기
├── file_edit     — 프로젝트 루트 내 편집
├── bash_execute  — 안전 명령어만 (rm -rf 등 blocklist 제외)
├── bash_python   — 스크립트 실행
├── web_fetch     — 읽기 전용
└── agent_spawn   — Domain Agent에 한정

사용자 동의 필요 (항상 에스컬레이션)
├── file_delete   — 비가역적 작업
├── git_force_push — 파괴적 git 작업
└── external_api_write — 외부 서비스 쓰기
```

### 권한 처리 플로우

```
Execution 작업 시작
    │
    ├─ auto_approved 권한? ──► 즉시 진행
    │
    ├─ user_approval_required? ──► permission_request.json 작성
    │                                    │
    │                             Advisor 확인
    │                                    │
    │                             escalate_to_user=true
    │                                    │
    │                             Reporter 중간 보고
    │                             + 사용자 입력 대기
    │
    └─ 레지스트리에 없음? ──► escalate_if_not_in_registry=true
                              → 사용자 에스컬레이션
```

---

## 6. 에스컬레이션 플로우

```
Execution 수행
    │
    ▼
Validation 검증
    │
    ├─ PASS ──────────────────────────────────────► Reporter → 사용자
    │
    ├─ INSUFFICIENT ──► Execution 재시도 (max 5회)
    │                       │
    │                       ├─ 성공 ──► Validation 재검증
    │                       └─ 5회 실패 ──► Advisor 호출
    │
    └─ FAIL + advisor_needed=true
              │
              ▼
         Advisor 분석 (max 3회)
              │
              ├─ 솔루션 → Execution 재실행 → Validation 재검증
              │
              └─ 여전히 FAIL (3회 초과) ──► escalate_to_user=true
                                                │
                                         Reporter 중간 보고
                                         + Slack 알림
                                         + 사용자 입력 대기
```

**최대 사이클**: Execution 5회 + Advisor 3회. 그 이후 자동 에스컬레이션.

---

## 7. 병렬 실행 정책

### 단일 도메인 (기본)
```bash
python .scripts/orchestrator.py --task "..." --domain nova_log_analytics --auto
```
Execution → Validation → Reporter 순차 실행.

### 복수 도메인 병렬 (--parallel)
```bash
python .scripts/orchestrator.py \
  --tasks "이상탐지::nova_log_analytics,04_WorkLog 분류::pkb_worklog" \
  --auto --parallel
```

**병렬 실행 조건**:

| 조건 | 동작 |
|---|---|
| 토큰 잔여 > 10,000 | ThreadPoolExecutor로 병렬 spawn |
| 토큰 잔여 < 10,000 | 순차 실행으로 자동 전환 |
| 도메인 간 의존성 있음 | 수동 순차 지정 필요 |

**병렬 결과 처리**:
- 각 도메인별 독립 bus task_id 생성
- 모든 execution 완료 후 → 각 도메인별 validation 병렬 실행
- 모든 PASS → Reporter가 통합 보고서 작성

---

## 8. 파일 시스템 레이아웃

```
Workspace/
├── .agents/
│   ├── bus/                         # 에이전트 간 통신 파일
│   │   ├── <task_id>_manifest.json
│   │   ├── <task_id>_result.json
│   │   ├── <task_id>_validation.json
│   │   ├── <task_id>_advice.json
│   │   ├── <task_id>_report.json
│   │   ├── <task_id>_permission_request.json
│   │   ├── <task_id>_granted_permissions.json
│   │   ├── <task_id>_requirement.json      # v1.2
│   │   ├── <task_id>_advisor_plan.json     # v1.2
│   │   ├── <task_id>_evaluation.json       # v1.2
│   │   ├── <task_id>_user_decision.json    # v1.2
│   │   └── <task_id>_learning.json         # v1.2
│   ├── advisor/
│   │   └── learnings/               # Advisor 자기개선 메모 (v1.2)
│   │       └── {YYYYMMDD}_{task_id}.json
│   ├── orchestrator/                # Orchestrator 실행 로그
│   ├── daily_scrap/                 # Daily Scrap 에이전트 로그
│   └── classify/                    # Classify 에이전트 로그
│
├── .scripts/
│   ├── agent_bus.py                 # Bus R/W 유틸리티 (AgentBus)
│   ├── permission_bus.py            # 권한 버스 유틸리티 (PermissionBus)
│   ├── orchestrator.py              # 메인 진입점 CLI (--full-pipeline 추가)
│   ├── retrospective.py             # 주간 회고 스크립트 (v1.2)
│   ├── agent_log.py                 # AgentLog 유틸리티
│   └── classify.py                  # 대화 분류 스크립트
│
├── .status/
│   ├── monitor.py                   # GUI 모니터 (bus/ 카드 포함)
│   ├── show_tokens.py               # 토큰 추적 (4h 롤링)
│   ├── auto_track.py                # Stop 훅
│   ├── remote_track.py              # PostToolUse 훅 (원격 에이전트 토큰)
│   └── token_usage.json             # 토큰 데이터 (hourly_buckets)
│
└── global/
    └── 04_AgentEcosystem/
        ├── AGENT_ECOSYSTEM_RR.md    # 이 문서
        ├── ecosystem_design.md      # 아키텍처 overview (빠른 참조)
        ├── allowed_permissions.json # 권한 레지스트리
        ├── agents/
        │   ├── role_rules__user_interface.md  # v1.2 신규
        │   ├── role_rules__execution.md
        │   ├── role_rules__validation.md
        │   ├── role_rules__advisor.md         # v1.2 PM 역할 격상
        │   ├── role_rules__reporter.md
        │   └── domains/
        │       ├── role_rules__nova_helper.md
        │       ├── role_rules__nova_log_analytics.md
        │       ├── role_rules__pkb_worklog.md
        │       └── role_rules__sv.md
        └── protocol/
            ├── task_manifest_schema.md
            ├── evaluation_schema.md           # v1.2 신규
            └── advisor_plan_schema.md         # v1.2 신규
```

---

## 9. 인프라 스크립트 참조

### orchestrator.py CLI

```bash
# 기본 (Manifest + 프롬프트 출력)
python .scripts/orchestrator.py --task "작업 설명" --domain nova_log_analytics

# Dry Run (미리보기)
python .scripts/orchestrator.py --task "..." --domain pkb_worklog --dry-run

# Auto 순차 실행
python .scripts/orchestrator.py --task "..." --domain pkb_worklog --auto

# Auto 병렬 실행 (복수 도메인)
python .scripts/orchestrator.py \
  --tasks "이상탐지::nova_log_analytics,뉴스스크랩::daily_scrap" \
  --auto --parallel --no-confirm

# Bus 작업 목록
python .scripts/orchestrator.py --list
```

### AgentBus 사용법

```python
import sys
sys.path.insert(0, 'C:/Users/psh93/OneDrive/Desktop/Workspace/.scripts')
from agent_bus import AgentBus, BusFile

bus = AgentBus()  # 자동 task_id 생성
bus.write_manifest(domain="nova_log_analytics", instructions="이상탐지 실행")
result = bus.read(BusFile.RESULT)
bus.write_validation(verdict="PASS", passed_checks=["구조 검증"])
```

### PermissionBus 사용법

```python
from permission_bus import PermissionBus

pb = PermissionBus(task_id="abc12345")
if pb.is_auto_approved("file_write"):
    pb.grant_permission("abc12345", "file_write")
elif pb.requires_user_approval("file_delete"):
    pb.request_permission("abc12345", "file_delete", context="report.md 삭제 필요")
```

### monitor.py 실행

```bash
python .status/monitor.py
# - 에이전트 카드 (running/completed/error)
# - Bus Task 카드 (manifest→result→validation→report 진행)
# - 토큰 사용 추이 라인 그래프 (hourly_buckets 기반)
```

---

## 10. 운영 가이드

### 새 도메인 추가 절차

1. `global/04_AgentEcosystem/agents/domains/role_rules__<domain>.md` 작성
2. `orchestrator.py`의 `DOMAIN_MAP`에 항목 추가
3. `ecosystem_design.md` 도메인 테이블 업데이트
4. 이 문서 §3.6 테이블 업데이트

### 에스컬레이션 발생 시 대응

1. `.agents/bus/<task_id>_advice.json` 확인 → `root_cause` 파악
2. `solutions` 배열에서 `target_agent: "user"` 항목 확인
3. 필요 시 `allowed_permissions.json`에 새 권한 추가 (수동)
4. 추가 후 `orchestrator.py` 재실행

### 토큰 예산 관리

- 한도: Claude Pro 72,000 토큰 / 5h (실질적 4h 롤링 집계)
- `python .status/show_tokens.py` 로 현재 사용량 확인
- 10,000 미만 시 병렬 spawn 자동 비활성화
- 모니터: `python .status/monitor.py` 상단 라인 그래프 확인

### Daily Scrap 트리거 관리

- 스케줄 페이지: https://claude.ai/code/scheduled
- 트리거 ID: `trig_012KdqjTcxkob1J8V1zePGr2` (Daily Scrap — GeekNews)
- 현재 비활성 상태 → 구현 트리거 실행 후 수동 재활성화 필요

---

## 11. 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| 1.0 | 2026-04-11 | 최초 작성: 4에이전트 생태계 + 6도메인 설계 |
| 1.1 | 2026-04-11 | 권한 위임 시스템 추가, 병렬 실행 정책 추가, Slack 에스컬레이션 알림 추가 |
| 1.2 | 2026-04-12 | User Interface Agent 추가, Advisor PM 격상(6단계 라이프사이클), 10항목 평가 보고서, 사용자 승인 게이트, Advisor 자기개선 루프, 주간 회고 스크립트, 새 BusFile 타입 5종 추가, orchestrator.py --full-pipeline 플래그 |

---

*이 문서는 Agent Ecosystem의 단일 진실 공급원(Single Source of Truth)입니다. 에이전트 설계 변경 시 이 문서를 먼저 업데이트하고 개별 role_rules 파일에 반영합니다.*
