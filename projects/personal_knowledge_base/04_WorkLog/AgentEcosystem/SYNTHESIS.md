# AgentEcosystem 지식 합성

> 마지막 갱신: 2026-04-14 19:48 | 기반 항목 수: 20

---

# AgentEcosystem 위키 합성 문서

## 핵심 지식

1. **Multi-Agent 역할 분리 구조가 실제 운영 중**: User Interface Agent, Advisor Agent (PM 역할), Execution Agent + Domain Agent(pkb_worklog) 세 레이어로 구성되며, 각 역할별 `role_rules` 파일이 `04_AgentEcosystem/agents/` 경로에 분리 저장된다.

2. **Orchestrator + Bus 패턴으로 태스크 흐름 관리**: 태스크는 `.agents/bus/{task_id}_report.json` 형태로 저장되고, orchestrator 스크립트(`.scripts/orchestrator`)가 파이프라인을 조율한다. 실제 완료된 태스크 예시: `9dea7c73` (Waza 도입 전략 리포트, 2026-04-14 00:33).

3. **Advisor Agent가 반응형 → 능동형으로 전환 설계됨**: v2.0 보완 계획(2026-04-12)에서 기존 Advisor가 반응형 Validation 역할에 머물던 구조를 능동적 PM 역할로 격상하는 방향으로 승인된 구현 계획이 존재한다.

4. **비용 최적화를 위한 Haiku Execution 프리셋 운영**: `daily_scrap`, `pkb_worklog` 도메인에 `cost_optimized` 프리셋을 자동 적용하는 테스트가 진행되었으며, 예상 효과 보고서(Q1)가 작성되었다.

5. **트리거/스케줄 설정이 실행 누락의 반복 원인**: 매일 오전 9시 데일리 스크랩 트리거가 등록되지 않아 2026-04-04 이후 4일간 실행 공백이 발생했다. 트리거 등록은 구두 지시만으로는 반영되지 않으며, 명시적 등록 단계가 필요하다.

6. **Claude Code 웹 예약 실행 기능이 생태계 자동화 후보로 검토됨**: code.claude.com의 클라우드 예약 기능(로컬 PC 꺼져 있어도 백그라운드 실행)이 데일리 스크랩 등 반복 업무 자동화 대안으로 2026-04-11에 스크랩되었다.

---

## 반복 등장 패턴

- **User Interface Agent 세션이 압도적으로 많음**: 20개 로그 중 8개가 UI Agent 세션 → 사용자 진입점이 UI Agent로 고정되어 있으나, 세션이 짧고 분절되는 경향이 있음
- **`role_rules` 파일 경로가 매 세션 시스템 프롬프트에 반복 포함**: 에이전트 초기화 시마다 로컬 파일 경로를 명시적으로 주입하는 방식 사용 중
- **승인된 구현 계획(`approved implementation plan`) 패턴**: 설계 변경 시 계획 문서를 먼저 작성 → 승인 후 실행하는 워크플로가 2회(v1.0, v2.0) 반복됨
- **로컬 커맨드 실행 로그가 대화에 혼입**: `local-command-caveat` 태그가 붙은 세션이 2개 존재 → 에이전트가 CLI 실행 결과를 컨텍스트로 받는 구조

---

## 미해결 질문

- **트리거 등록의 영속성 보장 방법이 확정되지 않음**: 오전 9시 스크랩 트리거를 "지금 설정"했다는 응답이 있었으나, 재시작 후에도 유지되는지, 어떤 레이어(OS cron / Claude Code 스케줄 / 자체
