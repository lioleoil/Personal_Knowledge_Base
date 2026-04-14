# Advisor Plan — 7e4fb271

> **작성일**: 2026-04-13 10:10  
> **도메인**: pkb_worklog  
> **요청 요약**: tw93/waza 스킬 설치 후 효과적 활용을 위한 도입·실행·결과 도출 전략 리포트 작성

---

## 1. 목적 및 컨텍스트

**배경**: 사용자는 Claude Code 기반 Multi-Agent 생태계(Orchestrator, AgentBus)를 운영 중인 자율주행 어노테이션 PM이다. 일상 업무에서 `.scripts/` 자동화, daily_scrap, nova_helper, sv_dqat 등 다양한 프로젝트를 다룬다.

**목적**: GitHub 오픈소스 `tw93/Waza`의 8개 슬래시 커맨드 스킬(`/think`, `/design`, `/check`, `/hunt`, `/write`, `/learn`, `/read`, `/health`)을 현재 워크스페이스 환경에 통합하여 엔지니어링 품질과 PM 생산성을 높이는 전략 리포트 작성.

**사용자 프로파일 반영**:
- ESTP 성향: 즉시 활용 가능한 실행 플랜 선호, 추상적 이론 최소화
- 전략적 효율 추구: 기존 워크플로우와의 통합 포인트 명시 필요
- `personal_knowledge_base/` 운영: `/learn`·`/read` 스킬과 직접 연계 가능

**제약 조건**:
- Windows 11 + bash 환경: 일부 Unix 전용 스크립트 호환성 주의
- `/write` 스킬은 중국어·영어 전용 (한국어 산출물에 적용 불가)
- 토큰 효율 우선: `/learn` (6단계)·`/check` Deep 모드는 토큰 소모 高

---

## 2. 에이전트별 지시

### Execution Agent

**수행 단계**:
1. `WebFetch`로 `github.com/tw93/waza` README 및 각 스킬 설명 수집
2. 현재 워크스페이스 구조(`global/`, `projects/`, `.scripts/`) 파악
3. 8개 스킬별 사용자 워크플로우 매핑 (기존 시스템과의 접점 분석)
4. 도입 3단계 플랜(Phase 1 설치·Phase 2 실행·Phase 3 습관화) 작성
5. 정량 성과 지표 및 주의사항 포함
6. `global/05_PM_Outputs/waza-skill-strategy_2026-04-13.md`에 저장

**사용 도구**: `WebFetch`, `Read`, `Write`

**주의사항**:
- Windows 환경에서 curl 스크립트 실행 시 WSL/Git Bash 경로 주의
- `/design` 스킬은 현재 백엔드 중심 프로젝트에서 활용 빈도 낮음 — 과대 포장 금지
- `/write` 한국어 미지원 사실 명시 필수

### Validation Agent

**검증 기준**:
- [ ] 8개 스킬 전부 설명 포함 (누락 시 FAIL)
- [ ] 설치 명령어 정확성 (`npx skills add tw93/Waza -a claude-code -g -y`)
- [ ] 현재 워크스페이스와의 구체적 연계 시나리오 3건 이상
- [ ] 단계별 실행 계획(도입→실행→결과) 구조 완비
- [ ] 정량 성과 지표 포함

**중점 확인**: Windows 환경 특이사항 기재 여부, `/write` 한국어 제한 명시 여부

### Reporter Agent

**보고서 형식**: 마크다운 (`.md`)

**포함 섹션**:
1. Waza 개요 + 스킬 목록 표
2. 설치 방법 (글로벌 설치, Statusline, English Coaching)
3. 현재 워크스페이스 환경 분석 (호환성 매핑)
4. 단계별 실행 계획 (Phase 1-3)
5. 기대 효과 및 정량 성과 지표
6. 주의사항 및 한계
7. 빠른 시작 요약 (TL;DR)

---

## 3. 예상 산출물

| # | 산출물 | 형태 | 저장 위치 |
|---|---|---|---|
| 1 | Waza 스킬 도입·실행·결과 전략 리포트 | `.md` | `global/05_PM_Outputs/waza-skill-strategy_2026-04-13.md` |
| 2 | Advisor Plan | `.md` + `.json` | `global/05_PM_Outputs/advisor_plan_7e4fb271.md` |

---

## 4. 품질 기준

- [ ] 8개 스킬 모두 실행 시점·핵심 기능 포함
- [ ] 현재 워크스페이스 구체 연계 시나리오 3건 이상
- [ ] 설치 명령어 정확 및 검증 가능
- [ ] Windows 환경 주의사항 기재
- [ ] 정량 성과 지표 (코드 리뷰 커버리지, 버그 재발률 등) 포함
- [ ] 한국어로 작성 (사용자 응답 규칙 준수)

---

## 5. 예상 소요 시간 및 비용

| 항목 | 예상 |
|---|---|
| 소요 시간 | 15분 |
| 토큰 예산 | 8k tokens |
| 예상 비용 | $0.05 이하 |

---

## 6. 리스크 항목

| 리스크 | 가능성 | 대응 방안 |
|---|---|---|
| GitHub README 구조 변경으로 스킬 정보 불일치 | 낮음 | WebFetch로 실시간 확인 후 작성 |
| Windows 환경 스크립트 호환성 문제 | 중간 | WSL/Git Bash 사용 안내 병기 |
| 기존 커스텀 규칙(CLAUDE.md)과 Waza 스킬 충돌 | 낮음 | `/health` 실행으로 사전 확인 지시 |
| 토큰 초과 (특히 /learn 6단계 실행 시) | 중간 | `.status/show_tokens.py` 모니터링 권장 안내 포함 |
