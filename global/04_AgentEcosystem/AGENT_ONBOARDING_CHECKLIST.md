# Agent Onboarding Checklist

> 새로운 세션에서 에이전트 역할을 맡기 전 반드시 완료해야 할 준비 절차.  
> 각 역할별 체크리스트를 순서대로 수행한다. 항목을 건너뛰지 말 것.

---

## 공통 사전 확인 (모든 에이전트 공통)

```
[ ] 1. 현재 날짜·시간 확인 (KST)
[ ] 2. .agents/bus/ 디렉터리 존재 확인
[ ] 3. .status/token_usage.json 읽기 → 잔여 토큰 확인
       잔여 < 10,000 → 병렬 실행 금지, 순차 전환
[ ] 4. CLAUDE.md 로드 확인 (자동) → 응답 규칙 인지
[ ] 5. 자신의 role_rules 파일 읽기 (아래 역할별 경로 참고)
```

**잔여 토큰 읽기 코드:**
```python
import json
with open('.status/token_usage.json') as f:
    data = json.load(f)
remaining = data.get('window_limit', 72000) - data.get('used', 0)
print(f"잔여: {remaining:,}")
```

---

## Orchestrator (진입점)

**읽어야 할 파일:**
```
[ ] global/04_AgentEcosystem/ecosystem_design.md
[ ] .scripts/orchestrator.py
[ ] global/04_AgentEcosystem/allowed_permissions.json  (권한 레지스트리)
```

**실행 전 확인:**
```
[ ] task_id 생성 방식 확인 (uuid4 기반)
[ ] --dry-run으로 Manifest 미리 확인
[ ] 병렬 실행 시 토큰 잔여량 ≥ 10,000 확인
[ ] SLACK_WEBHOOK_URL 또는 SLACK_BOT_TOKEN 환경변수 설정 확인
    (에스컬레이션 알림용, 없어도 non-fatal)
```

**주요 CLI:**
```bash
# Dry run
python .scripts/orchestrator.py --task "작업명" --domain 도메인 --dry-run

# 단일 도메인 실행
python .scripts/orchestrator.py --task "작업명" --domain 도메인 --auto

# 병렬 다중 도메인
python .scripts/orchestrator.py --tasks "task1::domain1,task2::domain2" --parallel --auto

# 버스 상태 조회
python .scripts/orchestrator.py --list
```

**흔한 실수:**
- `--tasks` 없이 `--parallel` 단독 사용 → 에러
- 토큰 부족 상태에서 병렬 강행 → 자동 순차 전환되지만 경고 확인 필수

---

## Execution Agent

**읽어야 할 파일:**
```
[ ] global/04_AgentEcosystem/agents/role_rules__execution.md       ← 필수
[ ] global/04_AgentEcosystem/protocol/task_manifest_schema.md      ← 필수
[ ] global/04_AgentEcosystem/allowed_permissions.json              ← 필수
[ ] .agents/bus/<task_id>_manifest.json                            ← 작업별
```

**실행 전 확인:**
```
[ ] AgentBus import 경로 확인
    sys.path.insert(0, 'C:/Users/psh93/OneDrive/Desktop/Workspace/.scripts')
    from agent_bus import AgentBus
[ ] task_id 수신 확인 (Orchestrator로부터 전달)
[ ] domain 목록 확인 (manifest 대상)
[ ] 권한 위임 레지스트리 확인: auto_approved vs. user_approval_required
```

**Manifest 작성 체크리스트:**
```
[ ] instructions: 단일 책임 원칙 (무엇을, 어떻게, 기대 결과 포함)
[ ] context_files: 실제 필요한 파일만 (불필요한 파일 제외)
[ ] expected_outputs: Validation 체크리스트 기준이 됨 → 명확하게 작성
[ ] deadline_hint: 예상 소요 시간 (재시도 시 2배 연장 기준)
```

**재시도 규칙:**
```
[ ] 1~2회: 동일 manifest 재전송
[ ] 3~5회: deadline_hint 2배 연장 후 재전송
[ ] 5회 초과: Advisor spawn (자체 해결 시도 금지)
```

**금지 사항 재확인:**
```
[ ] Validation 없이 Reporter spawn 금지
[ ] Domain 결과 직접 수정 금지
[ ] 사용자에게 직접 보고 금지
```

---

## Validation Agent

**읽어야 할 파일:**
```
[ ] global/04_AgentEcosystem/agents/role_rules__validation.md      ← 필수
[ ] global/04_AgentEcosystem/protocol/task_manifest_schema.md      ← 필수
[ ] .agents/bus/<task_id>_manifest.json                            ← 작업별
[ ] .agents/bus/<task_id>_result.json                              ← 작업별
[ ] global/04_AgentEcosystem/agents/domains/role_rules__<domain>.md ← 해당 도메인
```

**검증 실행 순서:**
```
[ ] 1. 구조 검증
       - result.json의 outputs 각 항목에 type/path/summary 존재?
       - status가 success | partial | error 중 하나?
       - 출력 파일이 실제 존재하는가? (os.path.exists 또는 Read)
[ ] 2. 일관성 검증
       - 기존 파일과 스키마 충돌 없는가?
       - 도메인 role_rules 컨벤션 준수?
[ ] 3. 완결성 검증
       - manifest의 expected_outputs 모두 커버?
       - errors 목록이 비어있거나 허용 가능 수준?
```

**판정 기준 재확인:**
```
[ ] PASS: 구조·일관성·완결성 모두 통과, errors 없음
[ ] INSUFFICIENT: 구조 유효 + expected_outputs 일부 누락
                  → advisor_needed: false (재시도로 해결 가능)
[ ] FAIL: 구조 오류 OR 일관성 위반 OR 심각한 오류
          → advisor_needed: 단순 재시도 불가 시 true
```

**금지 사항 재확인:**
```
[ ] Execution/Domain 파일 직접 수정 금지 (Read-only)
[ ] 판정 근거 없는 PASS 금지
[ ] 사용자에게 직접 메시지 금지
```

---

## Advisor Agent

**읽어야 할 파일:**
```
[ ] global/04_AgentEcosystem/agents/role_rules__advisor.md         ← 필수
[ ] .agents/bus/<task_id>_manifest.json                            ← 작업별
[ ] .agents/bus/<task_id>_result.json                              ← 작업별
[ ] .agents/bus/<task_id>_validation.json                          ← 작업별
[ ] global/04_AgentEcosystem/allowed_permissions.json              ← 권한 확인용
```

**활성화 조건 재확인:**
```
[ ] Validation verdict=FAIL + advisor_needed=true? → 분석 시작
[ ] Execution 5회 모두 실패? → 분석 시작
[ ] 위 조건 아님? → Advisor 개입 불필요, 대기
```

**분석 체크리스트:**
```
[ ] 이슈 severity 순으로 정렬 (HIGH → LOW)
[ ] 구조적 원인 vs. 일시적 원인 구분
[ ] priority 1: 최소 변경 솔루션
[ ] priority 2: 대안 접근법
[ ] escalate_to_user 판단:
    - API 키 / 권한 필요 → true
    - 외부 서비스 장애 → true
    - 데이터 손실 위험 → true
    - 자동 해결 가능 → false
```

**솔루션 작성 기준:**
```
[ ] target_agent: "domain" | "execution" | "user"
[ ] action: 구체적 명령 형태 (파일 경로, 파라미터, 기대 결과 포함)
[ ] "재시도" 단독 금지 → "어떻게" 재시도할지 명시
```

**금지 사항 재확인:**
```
[ ] 파일 수정·스크립트 실행 금지 (Read-only)
[ ] Validation 판정 변경 요청 금지
[ ] 근본 원인 분석 없이 escalate_to_user: true 설정 금지
```

---

## Reporter Agent

**읽어야 할 파일:**
```
[ ] global/04_AgentEcosystem/agents/role_rules__reporter.md        ← 필수
[ ] .agents/bus/<task_id>_manifest.json                            ← 작업별
[ ] .agents/bus/<task_id>_result.json                              ← 작업별
[ ] .agents/bus/<task_id>_validation.json                          ← 반드시 PASS 확인
[ ] .agents/bus/<task_id>_advice.json                              ← escalate_to_user 시
```

**활성화 조건 재확인:**
```
[ ] validation.json의 verdict = "PASS" 확인 → 완료 보고
[ ] advice.json의 escalate_to_user = true → 중간 보고
[ ] 위 두 조건 없음 → Reporter 활성화 불가
```

**보고서 작성 체크리스트:**
```
[ ] PASS 확인 후 보고서 작성 시작
[ ] 섹션 구성: 요약 / 실행 결과 / 검증 결과 / 산출물 / 다음 단계
[ ] 버스 파일 기반만 서술 (추측 금지)
[ ] 저장 판단:
    - 분석 결과 / PM 산출물 / 복수 도메인 종합 → 저장
    - 단순 조회 / 에러 보고 / 5줄 이하 → 저장 X
```

**저장 경로:**
```
global/05_PM_Outputs/{domain}_{context}_{YYYY-MM-DD}.md
```

**금지 사항 재확인:**
```
[ ] PASS 없이 보고서 생성 금지
[ ] 결과 파일 수정 금지
[ ] 버스 파일에 없는 내용 추측 서술 금지
[ ] 사용자에게 Execution/Validation 내부 상태 직접 노출 금지
```

---

## Domain Sub-Agents

### nova_helper
```
[ ] global/04_AgentEcosystem/agents/domains/role_rules__nova_helper.md
[ ] projects/nova_helper/nova_helper.py
[ ] .agents/bus/<task_id>_manifest.json
[ ] projects/nova_helper/.env 존재 여부 (SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, NOVA_MODE)
```
**주의:** NOVA_MODE=server 시 aiohttp 환경 필요. Socket Mode와 혼용 금지.

### nova_log_analytics
```
[ ] global/04_AgentEcosystem/agents/domains/role_rules__nova_log_analytics.md
[ ] projects/nova_log_analytics/config.yaml
[ ] .agents/bus/<task_id>_manifest.json
```
**주의:** 파생 컬럼 네이밍 컨벤션 준수 (role_rules 확인). Anomaly Detection 임계값 하드코딩 금지.

### pkb_worklog (개인 지식베이스)
```
[ ] global/04_AgentEcosystem/agents/domains/role_rules__pkb_worklog.md
[ ] projects/personal_knowledge_base/04_WorkLog/INDEX.md
[ ] .agents/bus/<task_id>_manifest.json
```
**주의:** 대화 분류 결과를 기존 INDEX와 대조 후 기록. 파일 직접 삭제 금지 (권한 레지스트리 확인).

### sv_dqat / sv_lakehouse
```
[ ] global/04_AgentEcosystem/agents/domains/role_rules__sv.md
[ ] projects/sv_dqat/ 또는 projects/sv_lakehouse/ 내 관련 파일
[ ] .agents/bus/<task_id>_manifest.json
```
**주의:** sv_dqat, sv_lakehouse는 별도 git 관리(embedded). 루트 저장소와 혼용 금지.

---

## 에스컬레이션 발생 시 대응 요약

```
Validation FAIL + advisor_needed=true
  → Advisor spawn (최대 3회)
  → Advisor 3회 후 여전히 FAIL
  → escalate_to_user=true → Reporter 중간 보고 → 사용자 대기

Execution 5회 재시도 실패
  → Advisor spawn (동일 흐름)
```

**Slack 알림 (orchestrator 자동 처리):**
- `SLACK_WEBHOOK_URL` 또는 `SLACK_BOT_TOKEN + SLACK_ESCALATION_CHANNEL` 환경변수 필요
- 없으면 알림 없이 에스컬레이션만 발생 (non-fatal)

---

## 파일 경로 빠른 참조

| 자산 | 경로 |
|---|---|
| 권한 레지스트리 | `global/04_AgentEcosystem/allowed_permissions.json` |
| Agent Bus 유틸 | `.scripts/agent_bus.py` |
| Orchestrator | `.scripts/orchestrator.py` |
| 에이전트 로그 | `.scripts/agent_log.py` |
| 토큰 추적 | `.status/show_tokens.py`, `.status/token_usage.json` |
| Bus 파일 저장소 | `.agents/bus/` |
| 보고서 저장소 | `global/05_PM_Outputs/` |
| 설계 개요 | `global/04_AgentEcosystem/ecosystem_design.md` |
| 전체 R&R 문서 | `global/04_AgentEcosystem/AGENT_ECOSYSTEM_RR.md` |

---

*최종 업데이트: 2026-04-11*
