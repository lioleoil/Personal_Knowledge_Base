# AgentEcosystem 지식 합성

> 마지막 갱신: 2026-04-14 19:36 | 기반 항목 수: 30

---

## 핵심 지식

1. **Agent 역할 분리 구조**: 이 생태계는 최소 3가지 역할로 명확히 분리되어 운영된다 — `User Interface Agent`(사용자 입출력 처리), `Advisor Agent / PM 역할`(방향 결정 및 조율), `Execution Agent + Domain Agent`(실제 작업 수행 및 도메인 특화 처리). 각 역할은 독립적인 `role_rules` 파일로 정의된다.

2. **Bus 기반 태스크 보고서 저장 경로**: full pipeline으로 실행된 태스크의 결과물은 `.agents/bus/{task_id}_report.json` 경로에 저장된다. 예: task ID `9dea7c73`의 "Waza 도입 및 활용 전략 리포트"는 `.agents/bus/9dea7c73_report.json`에 저장 및 완료 확인됨 (완료 시각 2026-04-14 00:33).

3. **Domain Agent 결합 패턴**: Execution Agent는 단독으로 동작하지 않고 특정 도메인 Agent와 결합하여 인스턴스화된다. 현재 확인된 결합: `Execution Agent + pkb_worklog Domain Agent`. 이는 작업 실행 로직과 도메인 지식을 분리하면서도 런타임에 합성하는 설계 방식이다.

4. **Role Rules 파일 위치 규칙**: 모든 Agent의 역할 규칙은 `C:/Users/psh93/OneDrive/Desktop/Workspace/global/04_AgentEcosystem/agents/role_rules__{agent_type}` 경로에 파일로 관리된다. Agent 초기화 시 해당 파일을 시스템 프롬프트로 로드하는 방식으로 동작한다.

5. **Daily Scrap 연동**: `.agents/daily_scrap/` 디렉토리에 날짜+시간 기반 파일명(`2026-04-13_100433_DailyScrap...`)으로 스크랩 데이터가 저장되며, IDE에서 직접 열어 Agent 컨텍스트로 투입하는 워크플로우가 존재한다.

6. **대화 로그 중복 수집 문제**: 동일한 파일(동일 UUID)이 30개 로그 중 반복 등장한다 (예: `22e6248e`, `29f311db`, `3ed1532c` 등이 각각 3회씩 중복). 로그 수집 파이프라인에서 중복 제거 로직이 누락되어 있거나, 요약 트리거가 과도하게 발동되고 있다.

---

## 반복 등장 패턴

- **User Interface Agent가 가장 빈번히 활성화**: 30개 로그 중 약 18개가 UI Agent 세션 — 사용자와의 상호작용이 생태계 활동의 주된 진입점임을 의미
- **동일 UUID 세션의 반복 수집**: 같은 `.jsonl` 파일이 2~3회씩 중복 인덱싱됨 — 파이프라인의 멱등성(idempotency) 미확보
- **pkb_worklog 도메인이 Execution에 고정 결합**: 현재 로그 범위 내에서 Execution Agent는 항상 `pkb_worklog`와 결합 — 다른 도메인 결합 사례는 아직 미확인
- **full pipeline 태스크 결과 추적 패턴**: 사용자가 직접 보고서 위치를 질의하는 행동 → 현재 태스크 상태를 능동적으로 노출하는 대시보드 또는 알림 메커니즘 부재

---

## 미해결 질문

- **중복 로그 수집의 원인**: 동일 UUID가 반복 수집되는 것이 수집 스크립트 버
