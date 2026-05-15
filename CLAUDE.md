# Personal Knowledge Base — 글로벌 워크스페이스

> 이 파일은 Claude Code가 어느 프로젝트 디렉터리에서 열리더라도 자동으로 로드됩니다.

---

## 글로벌 자산 위치

| 폴더 | 내용 |
|---|---|
| `global/01_Identity/` | 사용자 정체성 (자기완결적 본질주의자, ESTP) |
| `global/02_Profile/` | 직업 프로필 (자율주행 어노테이션 PO/PM), 역량맵 |
| `global/03_Instructions/` | Claude 인터랙션 커스텀 설정 및 효율화 가이드 |
| `global/04_AgentEcosystem/` | Multi-Agent 생태계 설계 (Role Rules, 버스 프로토콜, 권한 레지스트리) |
| `global/05_PM_Outputs/` | PM 스킬 산출물 (OKR, PRD, 로드맵 등) |

핵심 파일:
- `global/01_Identity/user_identity.md` — 사용자 정체성 심층 분석
- `global/02_Profile/user_profile.md` — 직업·기술 스택·커리어 맥락
- `global/02_Profile/역량맵_Capability_Map.md` — 689개 대화 기반 증거 중심 역량 맵
- `global/03_Instructions/user_custom_instructions.md` — 응답 규칙 전문 (한국어, Q1/Q2/Q3 등)
- `global/03_Instructions/Claude_Code_효율화_매뉴얼.md` — 토큰 효율화 전략
- `global/04_AgentEcosystem/ecosystem_design.md` — 에이전트 생태계 아키텍처 overview
- `projects/nova_log_analytics/CLAUDE.md` — nova_log_analytics 프로젝트 가이드 (핵심 파일, 탐지 구조, feature별 처리)

---

## 응답 규칙 핵심 요약

전문은 `global/03_Instructions/user_custom_instructions.md` 참고.

- **언어**: 항상 한국어로 응답
- **후속 질문**: 모든 응답 마지막에 Q1/Q2/Q3 세 개 제시 (볼드 처리, 앞뒤 두 줄 간격)
- **역할**: 라이프코치·컨설턴트·어드바이저·멘토·청중 역할, AI임 언급 금지
- **태도**: 사과·유감 표현 금지, 전문가 부인 금지, 반복 표현 금지
- **PM Skill 요청**: `[PM_SKILL_REQUEST]` 블록 감지 시 적합 스킬 후보 2~3개 제시 후 사용자 선택 대기
- **PM Outputs 저장**: 스킬 실행 후 `global/05_PM_Outputs/`에 `.md` 저장 (파일명: `{skill-name}_{컨텍스트}_{YYYY-MM-DD}.md`)

---

## 프로젝트 디렉터리 맵

```
projects/
├── 04_WorkLog/            # Daily Scrap 자동 수집 출력 (.scripts/daily_scrap.py)
├── nova_helper/           # Nova Slack 봇 (Bolt, HTTP/Socket Mode)
├── nova_log_analytics/    # Labelit 커맨드 로그 기반 분석 (Databricks)
│   └── .assistant/skills/ # 단일 소스 — anomaly_detection/ · focus_drop_kpi/ · agents/
├── personal_knowledge_base/  # 04_WorkLog/ — 대화 로그 주제별 정리
├── sv_dqat/               # 별도 git 관리 (embedded)
└── sv_lakehouse/          # 별도 git 관리 (embedded)
```

---

## 공용 스크립트 (.scripts/)

| 스크립트 | 용도 | 실행 예 |
|---|---|---|
| `classify.py` | 대화 JSONL → 주제별 분류 | `python .scripts/classify.py <file.jsonl>` |
| `daily_scrap_runner.py` | GeekNews 뉴스 스크랩 (수동) | `python .scripts/daily_scrap_runner.py` |
| `doc_gen.py` | Confluence 페이지 생성·업로드 | import 전용 |
| `pm_ppt_generator.py` | 마크다운 → Gemini → .pptx 생성 | `python .scripts/pm_ppt_generator.py <md_path>` |
| `pm_skill.py` | PM Skill Launcher (CLI) | `python .scripts/pm_skill.py` |
| `agent_log.py` | 에이전트 로그 유틸리티 | import 전용 |
| `agent_bus.py` | Agent Bus R/W 유틸리티 | import 전용 (`AgentBus` 클래스) |
| `orchestrator.py` | Multi-Agent 진입점 CLI | `python .scripts/orchestrator.py --task "..." --domain <domain>` |

### Orchestrator 빠른 실행

```bash
# Dry run (Manifest 확인만)
python .scripts/orchestrator.py --task "04_WorkLog 분류" --domain pkb_worklog --dry-run

# 실제 실행
python .scripts/orchestrator.py --task "이상탐지" --domain nova_log_analytics

# 버스 작업 목록
python .scripts/orchestrator.py --list
```

도메인 목록: `nova_helper`, `nova_log_analytics`, `pkb_worklog`, `sv_dqat`, `sv_lakehouse`, `daily_scrap`

```bash
# 복수 도메인 병렬 실행
python .scripts/orchestrator.py \
  --tasks "이상탐지::nova_log_analytics,뉴스스크랩::daily_scrap" \
  --auto --parallel --no-confirm
```

에이전트 R&R 설계 문서: `global/04_AgentEcosystem/AGENT_ECOSYSTEM_RR.md`  
권한 레지스트리: `global/04_AgentEcosystem/allowed_permissions.json`

---

## 에이전트 로그 (.agents/)

로그 저장 위치: `.agents/<agent_type>/{YYYYMMDD_HHMMSS}_{agent_id}.json`

```python
import sys
sys.path.insert(0, 'C:/Users/psh93/OneDrive/Desktop/Workspace/.scripts')
from agent_log import AgentLog

log = AgentLog(agent_id="작업명_날짜", title="표시용 제목", agent_type="classify")
log.add('처리 시작')
log.done('완료')
```

---

## 토큰 효율화 필수 규칙

`global/03_Instructions/Claude_Code_효율화_매뉴얼.md` 기반:

- 대용량 파일: Grep으로 위치 확인 → offset+limit Read
- 서브에이전트: Write/Edit 권한 필요 명시 + 대용량 파일은 Grep 우선 지시
- 내용 복사: verbatim 금지 → 요약 형태로 append

---

## 멀티에이전트 권한 프로토콜

> 전문: `global/04_AgentEcosystem/advisor_protocol.md`  
> 레지스트리: `global/04_AgentEcosystem/allowed_permissions.json`

Execution 에이전트가 작업 권한이 필요한 경우 Advisor 에이전트에게 요청한다.

**Advisor 에이전트 권한 규칙:**
- `allowed_permissions.json`의 `auto_approved` 목록 작업은 **즉시 자동 승인**
- `file_delete`(파일 삭제)는 **항상 사용자 동의 필요** — Advisor가 단독으로 승인 불가
- 레지스트리에 없는 신규 권한 → 사용자 에스컬레이션 후 승인 시 파일에 추가
- 에스컬레이션 발생 시 nova_helper Slack 알림 (`NOVA_ESCALATION_CHANNEL` 설정 시)

**이 프로토콜은 모든 규칙, 워크플로우, 자동화 스크립트에 적용된다.**
