# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> 기본 저장 경로: `C:\Users\psh93\OneDrive\Desktop\Claude`

## 저장소 목적

이 저장소는 개인 지식 관리 시스템(Personal Knowledge Base)이다. GPT/Claude 대화 학습 결과물, 사용자 정체성·프로필, 커스텀 인터랙션 설정, 업무 지식을 구조화하여 저장한다.

## 폴더 구조 및 역할

```
Claude/
├── 01_Identity/         # 사용자 정체성 분석 (자기완결적 본질주의자, ESTP)
│   ├── user_identity.md         → 자기완결적 본질주의자 정의, 핵심 행동 원리, 커리어 방향
│   └── your_curse_explained.md  → Your Curse Explained 심층 대화 전체 구조화 (2025-11-26)
│
├── 02_Profile/          # 직업 프로필 (자율주행 어노테이션 PO/PM), 역량맵
│   ├── user_profile.md          → 자율주행 어노테이션, 데이터 플랫폼, Python, 커리어 이력
│   └── 역량맵_Capability_Map.md → 689개 대화 기반 증거 중심 역량 맵
│
├── 03_Instructions/     # Claude 인터랙션 커스텀 설정
│   └── user_custom_instructions.md  → 역할, 톤, 응답 포맷, Q1/Q2/Q3 규칙
│
├── 04_WorkLog/          # GPT/Claude 대화 학습 결과물 (주제별 분류)
│   ├── Nova/                → Nova 대시보드, 사내 서비스 기획/릴리즈
│   ├── ODD/                 → ASAM OpenODD, 운행설계영역
│   ├── OpenLABEL/           → ASAM OpenLABEL, SV→OpenLABEL 마이그레이션
│   ├── DQA/                 → 데이터 품질 분석, 라벨 검증
│   ├── Gen1_Gen2_Labeling/  → OD/RMD/3DP 라벨링 성능 측정, Policy
│   ├── Career/              → 이직, 커리어 전략, 이력서, 포트폴리오
│   ├── Python_Scripts/      → Python 스크립트, 자동화, 파일 처리
│   ├── Strategy_Business/   → 전략 문서, KPI/OKR, 비즈니스 번역
│   ├── Misc/                → 기타 (개인 관심사, 일회성 질문)
│   ├── INDEX.md             → 전체 대화 분류 현황 요약 (자동 생성)
│   └── update_index.py      → INDEX.md 자동 갱신 스크립트
│
└── .status/             # 에이전트 진행 상황 모니터링 (q1/q2/q3_status.json)
```

## 핵심 파일

- `03_Instructions/user_custom_instructions.md` — Claude 응답 방식 규칙 (한국어 응답, Q1/Q2/Q3 후속 질문 형식 등)
- `01_Identity/user_identity.md` — 사용자 정체성 심층 분석
- `02_Profile/user_profile.md` — 직업·기술 스택·커리어 맥락
- `02_Profile/역량맵_Capability_Map.md` — 689개 대화 기반 증거 중심 역량 맵
- `04_WorkLog/INDEX.md` — 전체 WorkLog 파일 인덱스

## 자주 쓰는 명령

```bash
# INDEX.md 갱신 (새 파일 추가 후 실행)
python 04_WorkLog/update_index.py

# 에이전트 모니터 실행 (tkinter GUI)
python .status/monitor.py

# 대화 분류 파이프라인
python scripts/classify.py <file.json>         # 단일 파일 (오분류 시 팝업)
python scripts/classify.py --dry-run <file>    # 미리보기
python scripts/classify.py --no-popup <file>   # 팝업 없이 자동 처리

# 토큰 사용량 수동 확인 / 기록 추가 (Claude가 세션 종료 시 자동 실행)
python .status/show_tokens.py                      # 현재 사용량만 표시
python .status/show_tokens.py <토큰수> "<작업명>"  # 기록 추가 후 표시
```

## 토큰 자동 추적 (Claude 필수 규칙)

**모든 주요 작업 완료 후 반드시 실행:**
```bash
python .status/show_tokens.py <추정_토큰수> "<작업명>"
```
- 추정 토큰수: 에이전트 태스크는 태스크 알림의 `total_tokens` 값 사용, 메인 대화는 응답 분량 기준 추정 (짧은 응답 ~2k, 중간 ~5k, 대규모 작업 ~15k)
- Stop 훅이 자동으로 `show_tokens.py`를 실행하여 터미널에 토큰 바 출력
- 토큰 데이터: `.status/token_usage.json` (일별 초기화)

## 토큰 효율화 필수 규칙

`03_Instructions/Claude_Code_효율화_매뉴얼.md` 기반 — 모든 작업에 자동 적용:
- 대용량 파일(Python_Scripts ~3300줄, Gen1_Gen2 ~2000줄): Grep 위치 확인 → offset+limit Read
- 서브에이전트: Write/Edit 권한 필요 명시 + 대용량 파일 Grep 우선 지시
- 내용 복사: verbatim 금지 → 요약 형태로 append

## 인터랙션 규칙

`03_Instructions/user_custom_instructions.md`에 정의된 규칙이 이 저장소에서 작업할 때 기본값이다:
- 항상 한국어로 응답
- 모든 응답 마지막에 Q1/Q2/Q3 후속 질문 3개 제시 (볼드 처리, 줄바꿈 간격 포함)
- AI임을 언급하지 않음, 사과·유감 표현 금지, 전문가 면책 조항 없음

## 에이전트 실행 기록 관리

에이전트는 작업 대상 폴더의 `.agents/` 디렉토리에 실행 기록을 저장한다.
monitor.py가 프로젝트 전체를 자동 탐색하여 모든 에이전트 기록을 표시한다.

**에이전트 로깅 사용법:**
```python
import sys
sys.path.insert(0, 'C:/Users/psh93/OneDrive/Desktop/Claude/scripts')
from agent_log import AgentLog

log = AgentLog(
    agent_id = "작업명_날짜",
    title    = "표시용 제목",
    folder   = "04_WorkLog/Python_Scripts",  # 프로젝트 루트 기준 상대경로
)
log.add('처리 시작')          # 로그 항목 추가
log.update(progress=50)      # 진행률 업데이트
log.done('완료 메시지')       # 완료 처리
log.error('오류 메시지')      # 오류 처리
```

**저장 위치:** `{folder}/.agents/{YYYYMMDD_HHMMSS}_{agent_id}.json`

**파일 스키마:**
```json
{
  "agent_id": "식별자",
  "title": "표시용 제목",
  "folder": "대상 폴더 경로",
  "started_at": "ISO8601",
  "completed_at": "ISO8601 or null",
  "status": "waiting|running|completed|error",
  "progress": 0,
  "message": "현재 작업 설명",
  "log": ["HH:MM:SS  로그 항목"]
}
```

## 서브에이전트 표준 지시문 템플릿

**Claude 필수 규칙:** 서브에이전트를 생성할 때 프롬프트 맨 앞에 아래 블록을 반드시 포함한다.
`<agent_id>`, `<title>`, `<folder>` 세 값은 작업 내용을 분석하여 Claude가 직접 채운다:
- `agent_id`: `작업명_YYYYMMDD` 형식 (예: `Nova재분류_20260315`)
- `title`: 작업 목적을 한 줄로 요약한 한국어 제목
- `folder`: 작업 대상 파일이 위치한 프로젝트 루트 기준 상대경로 (예: `04_WorkLog/Nova`)

```
[에이전트 로깅 필수]
작업 시작 시 즉시 아래 코드를 실행하여 AgentLog를 초기화하고, 이후 모든 주요 단계마다 log.add() 또는 log.update()를 호출하라. Read/Write/Edit 권한이 필요하다.

import sys
sys.path.insert(0, 'C:/Users/psh93/OneDrive/Desktop/Claude/scripts')
from agent_log import AgentLog

log = AgentLog(
    agent_id = "<agent_id>",
    title    = "<title>",
    folder   = "<folder>",
)
log.add('작업 시작')
# ... 작업 수행 ...
log.update(progress=50, message='중간 단계')
log.done('완료 메시지')   # 또는 log.error('오류 내용')
```

## 업데이트 이력

| 날짜 | 내용 |
|------|------|
| 2026-03-14 | 초기 구조 생성, 기존 메모리 파일 이전 |
| 2026-03-14 | 04_WorkLog 주제별 하위 구조 생성, Custom instructions 통합, 694개 대화 학습 시작 |
| 2026-03-14 | README.md 삭제, CLAUDE.md로 통합 |
