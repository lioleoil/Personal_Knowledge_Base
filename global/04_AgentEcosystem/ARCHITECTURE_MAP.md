# Agent Ecosystem — 전체 구조도

> **버전**: 2.1 | **최종 수정**: 2026-04-12  
> 설계 원칙·상세 R&R → [AGENT_ECOSYSTEM_RR.md](AGENT_ECOSYSTEM_RR.md) | 빠른 참조 → [ecosystem_design.md](ecosystem_design.md) | GitHub 렌더링 → [ARCHITECTURE_MAP_MERMAID.md](ARCHITECTURE_MAP_MERMAID.md)

---

## 1. 전체 흐름도 (Full Pipeline v2.0)

```
╔══════════════════════════════════════════════════════════════════════╗
║                        사용자 (CLI / 터미널)                          ║
║  python .scripts/orchestrator.py --task "..." --domain <d>           ║
║                        --full-pipeline                               ║
╚══════════════════════════╤═══════════════════════════════════════════╝
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Orchestrator  (.scripts/orchestrator.py)                            │
│  · 토큰 예산 확인 (.status/token_usage.json)                         │
│  · Task ID 생성 · Bus Manifest 작성 (.agents/bus/)                   │
│  · 에이전트 subprocess spawn (claude -p)                             │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ spawn
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  User Interface Agent                              [Haiku]            │
│  · 사용자 자연어 요청 구조화                                          │
│  · 에이전트 내부 로그 터미널 미출력                                   │
│  · 평가 보고서 포워딩 + 승인/거절/피드백 수집                         │
│                                                                      │
│  출력: _requirement.json  /  _user_decision.json                     │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ _requirement.json
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Advisor Agent (PM)                              [Opus 4.7]           │
│                                                                      │
│  Phase 1  컨텍스트 파악                                               │
│           · global/01_Identity, 02_Profile, 03_Instructions 읽기     │
│           · .agents/advisor/learnings/ 최신 10건 로드                │
│  Phase 2  플랜 수립                                                   │
│           · advisor_plan_{task_id}.md → global/05_PM_Outputs/        │
│           · _advisor_plan.json → Bus                                 │
│  Phase 3  Execution·Validation 루프 감독 (FAIL 시 advice.json 발행)  │
│  Phase 4  결과 리뷰                                                   │
│  Phase 5  10항목 평가 보고서 → _evaluation.json → 사용자 승인 게이트 │
│  Phase 6  자기개선 → .agents/advisor/learnings/{date}_{task_id}.json │
└────┬─────────────────────────────────────────────────────────────────┘
     │ _advisor_plan.json
     ▼
┌──────────────────────────────┐        ┌────────────────────────────────┐
│  Execution Agent             │◄──────►│  Validation Agent              │
│                   [Sonnet *] │피드백   │                [Sonnet / codex]│
│  · _manifest.json 기반 작업  │        │  · Read-only 독립 검증         │
│  · Domain Sub-Agent spawn    │        │  · verdict: PASS / FAIL /      │
│  · 결과 수집 → _result.json  │        │    INSUFFICIENT                │
│                              │        │  · _validation.json 발행       │
└──────────────────────────────┘        └──────────┬─────────────────────┘
                                                   │ PASS
                                                   ▼
                                        ┌────────────────────────────────┐
                                        │  Reporter Agent   [codex-1 *]  │
                                        │  · 마크다운 보고서 생성         │
                                        │  · _report.json 발행           │
                                        │  · Slack 알림 (선택)           │
                                        └──────────────┬─────────────────┘
                                                       │
                                                       ▼
                                             사용자 승인 게이트
                                          ┌──────┬────────┬──────┐
                                          │      │        │      │
                                        approve reject  feedback │
                                          │      │        │      │
                                          ▼      ▼        ▼      │
                                       commit  종료    재실행─────┘
                                       & PR          + 재평가
                                          │
                                          ▼
                              feat/{task_id} 브랜치 자동 생성
                              git commit + gh pr create
```

---

## 2. Domain Sub-Agent 레이어

```
Execution Agent
     │
     ├── spawn ──► nova_helper          [default preset: Sonnet]
     │             projects/nova_helper/
     │
     ├── spawn ──► nova_log_analytics   [cross_vendor preset: Sonnet+codex-1]
     │             projects/nova_log_analytics/
     │
     ├── spawn ──► pkb_worklog          [cost_optimized preset: Haiku]
     │             projects/personal_knowledge_base/04_WorkLog/
     │
     ├── spawn ──► sv_dqat              [cross_vendor preset: Sonnet+codex-1]
     │             projects/sv_dqat/
     │
     ├── spawn ──► sv_lakehouse         [cross_vendor preset: Sonnet+codex-1]
     │             projects/sv_lakehouse/
     │
     └── spawn ──► daily_scrap          [cost_optimized preset: Haiku]
                   projects/04_WorkLog/Daily_Scrap__Geek_news/
```

---

## 3. 에이전트별 스펙

| 에이전트 | 모델 (기본) | 권한 | Role Rules |
|---|---|---|---|
| **User Interface** | Haiku 4.5 | Read + requirement/decision 쓰기 | `agents/role_rules__user_interface.md` |
| **Advisor (PM)** | Opus 4.7 | Read-only + Bus 5종 + WebSearch | `agents/role_rules__advisor.md` |
| **Execution** | Sonnet 4.6 | Read/Write/Edit/Bash + spawn | `agents/role_rules__execution.md` |
| **Validation** | Sonnet / codex-1 | Read-only + validation.json | `agents/role_rules__validation.md` |
| **Reporter** | codex-1 / Sonnet | Read-only + report.json | `agents/role_rules__reporter.md` |

> `*` 실제 모델은 도메인 프리셋에 따라 다름 — 아래 표 참조

---

## 4. 도메인별 모델 프리셋

| 도메인 | 프리셋 | Execution | Advisor | Validation | Reporter |
|---|---|---|---|---|---|
| `daily_scrap` | cost_optimized | Haiku 4.5 | Sonnet 4.6 | Haiku 4.5 | Haiku 4.5 |
| `pkb_worklog` | cost_optimized | Haiku 4.5 | Sonnet 4.6 | Haiku 4.5 | Haiku 4.5 |
| `nova_helper` | default | Sonnet 4.6 | Sonnet 4.6 | Sonnet 4.6 | Sonnet 4.6 |
| `nova_log_analytics` | cross_vendor | Sonnet 4.6 | Opus 4.7 | codex-1 | codex-1 |
| `sv_dqat` | cross_vendor | Sonnet 4.6 | Opus 4.7 | codex-1 | codex-1 |
| `sv_lakehouse` | cross_vendor | Sonnet 4.6 | Opus 4.7 | codex-1 | codex-1 |

> 설정 파일: `.scripts/model_config.json`

---

## 5. Agent Bus 통신 프로토콜

```
.agents/bus/<task_id>_<type>.json
```

| 파일 | 발행자 → 수신자 | 내용 |
|---|---|---|
| `_manifest.json` | Orchestrator → Execution | 작업 정의, 도메인, 파일 경로 |
| `_requirement.json` | UserInterface → Advisor | 구조화된 사용자 요구사항 |
| `_advisor_plan.json` | Advisor → Execution | 작업 계획, 체크리스트 |
| `_result.json` | Domain → Execution | 작업 결과 요약 |
| `_validation.json` | Validation → Bus | PASS/FAIL/INSUFFICIENT + issues |
| `_advice.json` | Advisor → Execution | FAIL 원인 분석 + 솔루션 |
| `_report.json` | Reporter → Bus | 마크다운 최종 보고서 |
| `_evaluation.json` | Advisor → User | 10항목 평가 점수·등급·커밋 승인 여부 |
| `_user_decision.json` | User → Advisor | approve / reject / feedback 텍스트 |
| `_learning.json` | Advisor 내부 | 자기개선 패턴 (learnings/로 복사) |

Python 유틸리티: `.scripts/agent_bus.py` (`AgentBus` 클래스)

---

## 6. 에스컬레이션 정책

```
Validation 결과
     │
     ├── PASS          ──► Advisor Phase 4-5 (평가 보고서)
     │
     ├── INSUFFICIENT  ──► retry_count < 5 ? Execution 재시도 : escalate
     │
     └── FAIL
          │
          ├── advisor_needed = true  AND  advisor_calls < 3
          │        ──► Advisor Phase 3 (advice.json 발행) → Execution 재시도
          │
          └── advisor_calls ≥ 3  OR  advisor_needed = false
                   ──► escalate_to_user = true  →  사용자 대기
                                                   (nova_helper Slack 알림)
```

---

## 7. Advisor 자기개선 루프

```
Phase 6 (매 작업 완료 후)
     │
     ├── _manifest.json + _result.json + _validation.json 분석
     │
     ├── 패턴 추출 → _learning.json (Bus)
     │
     └── .agents/advisor/learnings/{YYYYMMDD}_{task_id}.json 저장
                    ↑
          다음 작업 Phase 1에서 최신 10건 로드 → 플랜에 반영
```

---

## 8. 자동화 스케줄

| 이름 | 스케줄 | 실행 방식 | 출력 |
|---|---|---|---|
| Weekly Retrospective Report | 매주 토요일 15:00 KST | CCR (Anthropic Cloud) | `global/05_PM_Outputs/retrospective_{YYYY-MM-DD}.md` |
| Daily Scrap — GeekNews | ~~평일 09:00 KST~~ **수동 전환** | `python .scripts/daily_scrap_runner.py` | `projects/04_WorkLog/Daily_Scrap__Geek_news/Daily_Scrap.md` |

> Trigger 관리: https://claude.ai/code/scheduled

---

## 9. 인프라 파일 위치

```
.scripts/
  orchestrator.py        진입점 CLI (--full-pipeline / --auto / --dry-run)
  agent_bus.py           Bus R/W 유틸리티 (AgentBus 클래스)
  agent_log.py           에이전트 로그 유틸리티 (AgentLog 클래스)
  retrospective.py       주간 회고 보고서 생성
  model_config.json      도메인별 모델 프리셋 설정
  daily_scrap_runner.py  GeekNews 스크랩 (수동 실행)

.status/
  monitor.py             에이전트 실행 상태 GUI (tkinter)
  auto_track.py          Stop 훅 연동 자동 토큰 추적
  token_usage.json       토큰 사용량 (4시간 롤링 윈도우)

.agents/
  bus/                   버스 파일 저장 (.json)
  advisor/learnings/     Advisor 자기개선 메모 (최신 10건 활성)
  <agent_type>/          에이전트 실행 로그 {YYYYMMDD_HHMMSS}_{id}.json

global/
  01_Identity/           사용자 정체성 파일
  02_Profile/            직업 프로필 · 역량맵
  03_Instructions/       Claude 응답 규칙 · 토큰 효율화 매뉴얼
  04_AgentEcosystem/     에이전트 설계 문서 (이 파일 포함)
  05_PM_Outputs/         평가 보고서 · 회고 · 플랜 MD
```

---

## 10. 빠른 실행 명령어

```bash
# Full Pipeline (v2.0 — 권장)
python .scripts/orchestrator.py \
  --task "04_WorkLog 분류 실행" --domain pkb_worklog --full-pipeline

# Auto 모드 (v1.x 호환)
python .scripts/orchestrator.py \
  --task "이상탐지 실행" --domain nova_log_analytics --auto

# Dry Run (Manifest 확인만)
python .scripts/orchestrator.py \
  --task "sv_dqat 점검" --domain sv_dqat --dry-run

# 복수 도메인 병렬
python .scripts/orchestrator.py \
  --tasks "이상탐지::nova_log_analytics,분류::pkb_worklog" \
  --auto --parallel --no-confirm

# 버스 작업 목록 조회
python .scripts/orchestrator.py --list

# 주간 회고 수동 실행
python .scripts/retrospective.py

# GeekNews 스크랩 수동 실행
python .scripts/daily_scrap_runner.py

# 모니터 GUI 실행
python .status/monitor.py
```

---

## 11. 설계 원칙 요약

| # | 원칙 | 설명 |
|---|---|---|
| 1 | **단방향 의존성** | Domain → Execution → Validation → Advisor. 역방향 없음 |
| 2 | **파일 기반 비동기 버스** | `.agents/bus/` JSON 파일 기반. 재시작 내성·상태 영속 |
| 3 | **역할 경계 명확화** | Validation 수정 권한 없음. Advisor 실행 권한 없음 |
| 4 | **토큰 예산 인식** | 잔여 10,000 미만 시 병렬 → 순차 전환 |
| 5 | **도메인 격리** | Domain Agent는 자신의 role_rules만 읽음 |
| 6 | **멱등성** | 동일 task_id 재시도 시 파일 덮어쓰기만 발생 |
| 7 | **최소 권한** | auto_approved 목록 명시. 파일 삭제는 항상 사용자 동의 필요 |
| 8 | **자기개선 루프** | Advisor Phase 6 learnings → 다음 플랜 Phase 1 반영 (최신 10건) |
| 9 | **feat 브랜치 자동 생성** | --full-pipeline 커밋 시 feat/{task_id} 브랜치 자동 생성 |

---

_자동 생성 금지 — 수동 관리 문서_
