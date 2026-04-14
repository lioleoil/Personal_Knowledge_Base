# Waza 스킬 도입·실행·결과 도출 전략 리포트

> 작성일: 2026-04-13  
> 대상 환경: Claude Code (Windows 11 / Workspace)  
> 출처: [github.com/tw93/Waza](https://github.com/tw93/Waza) — ⭐ 2,959

---

## 1. Waza 개요

**Waza(技, わざ)** 는 일본 무술 용어로 '기술(技)' — 반사적으로 체화될 때까지 반복 수련된 동작을 의미한다.

> *"Engineering habits you already know, turned into skills Claude can run."*

Claude Code에서 `/슬래시 커맨드` 형태로 실행되는 8개 스킬 패키지다. 각 스킬은 폴더 단위로 구성되며, 마크다운 설명서 + 참조 문서 + 헬퍼 스크립트로 이루어진다.

### 1.1 스킬 목록

| 스킬 | 실행 시점 | 핵심 기능 |
|------|-----------|-----------|
| `/think` | 코드 작성 **전** | 요구사항 압박 테스트 + 아키텍처 검증, 코드 한 줄 전에 플랜 승인 |
| `/design` | 프론트엔드 UI 설계 | 미적 방향성 확정 + 심미적 판단이 담긴 UI 생성 |
| `/check` | 작업 완료 후 / 머지 전 | diff 리뷰 + 안전 이슈 자동 수정 + 보안·아키텍처 전문가 병렬 리뷰 |
| `/hunt` | 버그·크래시·예상 밖 동작 | 가설 기반 근본 원인 추적, 증거 확보 전 코드 미수정 |
| `/write` | 문서 작성·편집 | 중국어·영어 산문을 자연스럽게 재작성, AI 패턴 제거 |
| `/learn` | 새 도메인 진입 | 6단계 리서치 워크플로우: 수집→소화→개요→작성→다듬기→출판 |
| `/read` | URL·PDF 처리 | 임의 URL을 클린 마크다운으로 변환·저장 (GitHub/PDF/WeChat/Feishu 특수 처리) |
| `/health` | Claude Code 설정 감사 | 6-레이어 설정 스택 감사 (CLAUDE.md → rules → skills → hooks → subagents → verifiers) |

---

## 2. 설치 방법

### 2.1 전제 조건

```bash
# Node.js 및 npx 설치 확인
node --version  # v18+ 권장
npx --version
```

### 2.2 글로벌 설치 (권장)

```bash
# Claude Code 전용
npx skills add tw93/Waza -a claude-code -g -y
```

`-g` 플래그로 전체 프로젝트에 공통 적용.  
설치 후 Claude Code에서 `/think`, `/check` 등 슬래시 커맨드로 즉시 사용 가능.

### 2.3 Statusline 설치 (선택)

```bash
curl -sL https://raw.githubusercontent.com/tw93/Waza/main/scripts/setup-statusline.sh | bash
```

컨텍스트 윈도우 사용량 + 5시간/7일 쿼터 + 리셋까지 남은 시간을 하단 상태바에 표시.  
색상 코드: 초록(70% 미만) → 노랑(70–85%) → 빨강(85%+).

### 2.4 English Coaching 설치 (선택)

```bash
curl -fsSL https://raw.githubusercontent.com/tw93/Waza/main/rules/english.md -o ~/.claude/rules/english.md
```

영어 오류를 인라인 수정 + 패턴명 태깅. 매 세션이 영어 학습 병행.

### 2.5 제거

```bash
npx skills remove tw93/Waza -g
rm -f ~/.claude/statusline.sh
rm -f ~/.claude/rules/english.md
```

---

## 3. 현재 워크스페이스 환경 분석

### 3.1 기존 시스템과의 적합성

| 요소 | 현황 | Waza 연계 가능성 |
|------|------|----------------|
| Claude Code | 메인 IDE 환경 | ✅ 직접 설치·실행 |
| Multi-Agent 에코시스템 | Orchestrator + AgentBus 운영 중 | ✅ `/think`로 에이전트 설계 전 검증 |
| `.scripts/` 자동화 | daily_scrap, orchestrator 등 | ✅ `/check`로 PR 전 자동 리뷰 |
| `personal_knowledge_base/` | 대화 로그 주제별 정리 | ✅ `/learn`으로 리서치 산출물 생성 |
| Daily Scrap | GeekNews 뉴스 스크랩 | ✅ `/read`로 URL → 마크다운 변환 |
| `global/03_Instructions/` | 커스텀 응답 규칙 | ✅ `/health`로 설정 상태 감사 |
| nova_helper / sv_dqat 등 | 코드 작업 프로젝트 | ✅ `/hunt`으로 디버깅 체계화 |

### 3.2 가장 즉각적 가치가 높은 스킬 순위 (현재 환경 기준)

1. **`/check`** — `.scripts/` 커밋 전 diff 리뷰, 에이전트 코드 품질 보증
2. **`/think`** — 에이전트 설계·신규 기능 기획 전 아키텍처 검증
3. **`/learn`** — 새 기술 스택(lakehouse, DQA 등) 빠른 습득
4. **`/read`** — Daily Scrap의 URL 처리 보완
5. **`/health`** — CLAUDE.md + hooks + MCP 설정 주기적 감사

---

## 4. 단계별 실행 계획

### Phase 1 — 도입 (Day 1–3)

**목표:** 설치 완료 + 첫 번째 스킬 체험

```bash
# Step 1: 설치
npx skills add tw93/Waza -a claude-code -g -y

# Step 2: Statusline 설치 (토큰 모니터링과 연계)
curl -sL https://raw.githubusercontent.com/tw93/Waza/main/scripts/setup-statusline.sh | bash

# Step 3: 설치 상태 확인
/health
```

**체크포인트:**
- [ ] `/health` 실행 → 설정 감사 리포트 확인
- [ ] Statusline에서 쿼터 시각화 정상 동작 확인
- [ ] 기존 `global/03_Instructions/user_custom_instructions.md` 규칙과 충돌 없는지 확인

---

### Phase 2 — 실행 (Day 4–14)

**목표:** 기존 워크플로우에 스킬 통합

#### 시나리오 A: `.scripts/` 작업 시

```
작업 시작 전  →  /think  (아키텍처 검증, 의존성 목록화)
코딩 완료 후  →  /check  (diff 리뷰, 보안 이슈 탐지)
버그 발생 시  →  /hunt   (가설 기반 근본 원인 추적)
```

#### 시나리오 B: Daily Scrap 연계

```
뉴스 URL 처리  →  /read   (URL → 마크다운 변환)
주제 리서치    →  /learn  (6단계 워크플로우로 산출물 생성)
```

#### 시나리오 C: 에이전트 생태계 신규 설계 시

```
에이전트 R&R 설계  →  /think  (의존성 검증, 순환 참조 탐지)
설계 문서 작성     →  /write  (문서 자연스럽게 다듬기)
설계 완료 후       →  /check  (Execution 에이전트 코드 리뷰)
```

#### 시나리오 D: nova_helper / sv_dqat 개발 시

```
신규 기능 기획  →  /think
UI 컴포넌트    →  /design  (Slack 봇 관리 페이지 등)
배포 전        →  /check
```

---

### Phase 3 — 결과 도출 (Day 15+)

**목표:** 습관화 + 성과 측정

#### 3.1 운영 루틴화

| 시점 | 스킬 | 빈도 |
|------|------|------|
| 코딩 시작 전 | `/think` | 신규 기능·설계 시마다 |
| 커밋/PR 전 | `/check` | 100줄+ diff 발생 시 |
| 버그 발생 시 | `/hunt` | 즉시 |
| 주 1회 | `/health` | 매주 월요일 설정 감사 |
| 리서치 필요 시 | `/learn` | 새 도메인 진입 시 |

#### 3.2 기존 자동화와 연결

```python
# .scripts/orchestrator.py 실행 전 /think로 태스크 설계 검증
# .scripts/run_daily_scrap.bat 완료 후 /read로 주요 URL 보강
# Agent Bus 작업 완료 후 /check으로 코드 품질 검증
```

---

## 5. 기대 효과 및 성과 지표

### 5.1 정성적 기대 효과

| 영역 | Before | After (Waza) |
|------|--------|--------------|
| 설계 검증 | 코딩 도중 아키텍처 문제 발견 | `/think`로 코드 전 검증 완료 |
| 코드 리뷰 | 수동·간헐적 | `/check`로 매 PR 자동화 |
| 디버깅 | 시행착오 반복 | `/hunt`로 가설 기반 체계화 |
| 리서치 | 링크 북마크 → 휘발 | `/learn`으로 출판 가능 산출물 |
| 설정 관리 | 문제 발생 후 대응 | `/health`로 주기적 감사 |

### 5.2 정량적 성과 지표

| 지표 | 측정 방법 | 목표 |
|------|-----------|------|
| 코드 리뷰 커버리지 | `/check` 실행 횟수 / 전체 PR | 80%+ |
| 버그 재발률 | 동일 파일 `/hunt` 재실행 횟수 | 전월 대비 30% 감소 |
| 리서치 산출물 수 | `global/05_PM_Outputs/` 파일 수 | 월 4건+ |
| 설정 이슈 선제 탐지 | `/health` 경고 건수 vs 실제 장애 | 장애 전 탐지율 90%+ |
| 토큰 효율 | Statusline 쿼터 소진율 | 일 평균 30% 이하 유지 |

---

## 6. 주의사항 및 한계

### 6.1 현재 환경 특이사항

- **Windows 11 + bash**: 일부 스크립트(`scripts/fetch.sh` 등)는 Unix 환경 전제. WSL 또는 Git Bash 경로 확인 필요.
- **`/health`는 Claude Code 전용**: Codex 환경에서 미지원.
- **`/design`**: nova_helper 관리 UI 등 프론트엔드 작업 시 가치 발생. 현재 백엔드 중심 프로젝트에서는 활용 빈도 낮을 수 있음.
- **`/write`**: 중국어·영어 전용. 한국어 산출물에는 적용 불가.

### 6.2 기존 규칙과의 충돌 가능성

- `global/03_Instructions/user_custom_instructions.md`의 Q1/Q2/Q3 후속 질문 규칙 등 커스텀 지시는 유지됨. Waza 스킬이 이를 덮어쓰지 않음.
- `/health` 감사 시 기존 CLAUDE.md 규칙이 Waza 스킬보다 우선임을 확인.

### 6.3 토큰 비용

- `/learn` (6단계 워크플로우)와 `/check` Deep 모드(500줄+ diff)는 토큰 소모가 크다.
- `.status/show_tokens.py`로 실행 전후 비교 권장.

---

## 7. 빠른 시작 요약 (TL;DR)

```bash
# 1. 설치
npx skills add tw93/Waza -a claude-code -g -y

# 2. 상태 확인
/health

# 3. 첫 번째 실전 적용
# .scripts/ 어떤 파일이든 수정 후:
/check

# 새 에이전트 설계 시작 전:
/think [설계 내용]

# 버그 발생 시:
/hunt [증상 설명]
```

**핵심 원칙:** 스킬을 "쓰는 도구"가 아닌 "습관(わざ)"으로 체화할 것.  
매번 완벽하게 쓰려 하지 말고, 해당 시점에 맞는 스킬을 reflexively 실행하는 것이 목표다.

---

*리포트 생성: Claude Code (claude-sonnet-4-6) | Task ID: 7e4fb271*
