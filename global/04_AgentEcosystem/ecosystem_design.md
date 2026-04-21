# Multi-Agent Ecosystem — 아키텍처 Overview (v2.0)

> 이 문서는 참조용 설계 문서입니다. 각 에이전트의 상세 Role Rules는 `agents/` 디렉터리 참고.  
> 전체 구조도 (ASCII + Mermaid): **[ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md)** | 상세 R&R 정의서: **[AGENT_ECOSYSTEM_RR.md](AGENT_ECOSYSTEM_RR.md)**

---

## 아키텍처 흐름 (Full Pipeline — v2.0)

```
사용자 요청
    ↓
User Interface Agent (Haiku)
    ↓ requirement.json
Advisor Agent (Opus — PM 역할)
  Phase 1: 컨텍스트 파악 + learnings 반영
  Phase 2: advisor_plan_*.md 수립
    ↓ advisor_plan.json
Execution Agent     ↔     Validation Agent
  (Sonnet/Haiku)                (codex-1)
    ↓ PASS
Advisor Agent
  Phase 4: 결과 리뷰
  Phase 5: 10항목 평가 보고서
    ↓ evaluation.json
사용자 승인 게이트
  approve → git commit + PR
  reject  → 종료
  feedback → 재실행 후 재평가
    ↓
Advisor Agent
  Phase 6: 자기개선 (learnings/)

[주간 회고 — 매주 토요일 15:00]
retrospective.py → retrospective_{YYYY-MM-DD}.md
```

---

## 기본 플로우 (--auto 모드 — v1.x 호환)

```
orchestrator.py
    ↓ Manifest 생성
Execution Agent   (분해·분배·수집)
    ↓ spawn
Domain Sub-Agents (실제 작업 수행)
    ↓ result
Validation Agent  (독립 검증)
    ↓ PASS
Reporter Agent    (사용자 보고)

FAIL → Advisor Agent → 솔루션 → Execution 재실행
```

---

## 에이전트 역할 요약

| 에이전트 | Role Rules | 권한 | 모델 | 제약 |
|---|---|---|---|---|
| **User Interface** | `agents/role_rules__user_interface.md` | Read + requirement/decision 쓰기 | `claude-haiku-4-5-20251001` | 내부 소통 터미널 출력 금지 |
| **Execution** | `agents/role_rules__execution.md` | Read/Write/Edit/Bash + spawn | `claude-sonnet-4-6` | 사용자 직접 보고 불가 |
| **Validation** | `agents/role_rules__validation.md` | Read-only + validation.json | `codex-1` (OpenAI) | 결과 수정 불가 |
| **Advisor (PM)** | `agents/role_rules__advisor.md` | Read-only + 버스 파일 5종 + WebSearch | `claude-opus-4-7` | 직접 실행 불가 |
| **Reporter** | `agents/role_rules__reporter.md` | Read-only + report.json | `codex-1` (OpenAI) | PASS 후에만 활성 |

> 모델 배정 상세: `model_assignment.md` | 프리셋 설정: `.scripts/model_config.json`

### Domain Sub-Agents

| Domain | agent_type | Role Rules |
|---|---|---|
| nova_helper | `nova_helper` | `agents/domains/role_rules__nova_helper.md` |
| nova_log_analytics | `nova_log_analytics` | `agents/domains/role_rules__nova_log_analytics.md` |
| personal_knowledge_base/04_WorkLog | `pkb_worklog` | `agents/domains/role_rules__pkb_worklog.md` |
| sv_dqat | `sv_dqat` | `agents/domains/role_rules__sv.md` |
| sv_lakehouse | `sv_lakehouse` | `agents/domains/role_rules__sv.md` |
| Daily Scrap | `daily_scrap` | `agents/domains/role_rules__pkb_worklog.md` |

---

## Agent Bus 통신 프로토콜

버스 파일: `.agents/bus/<task_id>_<type>.json`

| 파일 유형 | 방향 | 스키마 |
|---|---|---|
| `_manifest.json` | Execution → Domain | `protocol/task_manifest_schema.md` |
| `_result.json` | Domain → Execution | `protocol/task_manifest_schema.md` |
| `_validation.json` | Validation → Bus | `protocol/task_manifest_schema.md` |
| `_advice.json` | Advisor → Bus | `protocol/task_manifest_schema.md` |
| `_report.json` | Reporter → Bus | `protocol/task_manifest_schema.md` |
| `_requirement.json` | UserInterface → Advisor | 구조화된 요구사항 |
| `_advisor_plan.json` | Advisor → Execution | `protocol/advisor_plan_schema.md` |
| `_evaluation.json` | Advisor → User | `protocol/evaluation_schema.md` |
| `_user_decision.json` | User → Advisor | approve/reject/feedback |
| `_learning.json` | Advisor 내부 | 자기개선 패턴 메모 |

Python 유틸리티: `.scripts/agent_bus.py` (`AgentBus` 클래스)

---

## 에스컬레이션 정책

| 단계 | 조건 | 동작 |
|---|---|---|
| Validation PASS | — | Advisor Phase 4-5 (평가) |
| Validation INSUFFICIENT | retry_count < 5 | Execution 재시도 |
| Execution 5회 실패 | — | Advisor 호출 (Phase 3) |
| Validation FAIL | advisor_needed=true | Advisor 호출 (max 3회) |
| Advisor 3회 후 FAIL | — | escalate_to_user=true → 사용자 대기 |
| 사용자 feedback | — | Execution 재실행 + 재평가 |

---

## 인프라 파일 위치

| 파일 | 용도 |
|---|---|
| `.scripts/agent_bus.py` | Bus R/W 유틸리티 |
| `.scripts/orchestrator.py` | 진입점 CLI (`--full-pipeline` 포함) |
| `.scripts/retrospective.py` | 주간 회고 스크립트 |
| `.scripts/agent_log.py` | 에이전트 로그 유틸리티 |
| `.status/monitor.py` | GUI 모니터 (bus/ 카드 포함) |
| `.agents/bus/` | 버스 파일 저장 위치 |
| `.agents/advisor/learnings/` | Advisor 자기개선 메모 |
| `global/05_PM_Outputs/` | 평가 보고서·회고·플랜 MD |

---

## 설계 원칙

1. **단방향 의존성** — Domain → Execution → Validation → Advisor. 역방향 없음.
2. **파일 기반 비동기 버스** — 재시작 내성, 상태 영속.
3. **역할 경계 명확화** — Validation은 수정 권한 없음. Advisor는 실행 권한 없음.
4. **토큰 예산 인식** — 잔여 10,000 미만 시 순차 실행 전환.
5. **기존 인프라 재사용** — AgentLog 패턴 유지. monitor.py 확장(최소 수정).
6. **도메인 격리** — 각 Domain Agent는 자신의 role_rules만 읽음.
7. **멱등성** — 같은 task_id 재시도 시 파일 덮어쓰기만 발생.
8. **자기개선 루프** — Advisor가 매 작업 후 learnings/ 저장, 다음 플랜에 반영.

---

## 빠른 시작

```bash
# Full Pipeline (v2.0 — 권장)
python .scripts/orchestrator.py --task "04_WorkLog 분류 실행" --domain pkb_worklog --full-pipeline

# Auto 모드 (v1.x 호환)
python .scripts/orchestrator.py --task "이상탐지 실행" --domain nova_log_analytics --auto

# Dry run (Manifest 확인만)
python .scripts/orchestrator.py --task "04_WorkLog 분류 실행" --domain pkb_worklog --dry-run

# 버스 작업 목록 조회
python .scripts/orchestrator.py --list

# 주간 회고 (수동 실행)
python .scripts/retrospective.py

# 모니터 실행
python .status/monitor.py
```
