# Personal Knowledge Base

> 기본 저장 경로: `C:\Users\psh93\OneDrive\Desktop\Workspace\projects\personal_knowledge_base`

## 저장소 목적

개인 지식 관리 시스템(Personal Knowledge Base). Claude 대화 학습 결과물, 사용자 정체성·프로필, 커스텀 인터랙션 설정, 업무 지식을 구조화하여 저장한다.

## 폴더 구조 및 역할

```
personal_knowledge_base/
├── 01_Identity/         # 사용자 정체성 분석 (자기완결적 본질주의자, ESTP)
│   ├── user_identity.md         → 자기완결적 본질주의자 정의, 핵심 행동 원리, 커리어 방향
│   └── your_curse_explained.md  → Your Curse Explained 심층 대화 전체 구조화 (2025-11-26)
│
├── 02_Profile/          # 직업 프로필 (자율주행 어노테이션 PO/PM), 역량맵
│   ├── user_profile.md          → 자율주행 어노테이션, 데이터 플랫폼, Python, 커리어 이력
│   ├── More about you.md        → 사용자 추가 자기소개 및 보완 정보
│   └── 역량맵_Capability_Map.md → 689개 대화 기반 증거 중심 역량 맵
│
├── 03_Instructions/     # Claude 인터랙션 커스텀 설정 및 효율화 가이드
│   ├── user_custom_instructions.md    → 역할, 톤, 응답 포맷, Q1/Q2/Q3 규칙
│   └── Claude_Code_효율화_매뉴얼.md  → 토큰 절약 전략, 파일 읽기 규칙, 에이전트 사용법
│
├── 04_WorkLog/          # 대화 로그 요약 + 정리 마크다운 전용
│   ├── Nova/                → Nova 대시보드, 사내 서비스 기획/릴리즈
│   ├── ODD/                 → ASAM OpenODD, 운행설계영역
│   ├── OpenLABEL/           → ASAM OpenLABEL, SV→OpenLABEL 마이그레이션
│   ├── DQA/                 → 데이터 품질 분석, 라벨 검증
│   ├── Gen1_Gen2_Labeling/  → OD/RMD/3DP 라벨링 성능 측정, Policy
│   ├── Gen2_Policy/         → Sequence 기반 Gen2 Annotation Policy 수립·조항 작성·번역 (2025-11~)
│   ├── Career/              → 이직, 커리어 전략, 이력서, 포트폴리오
│   ├── Python_Scripts/      → Python 스크립트, 자동화, 파일 처리
│   ├── Strategy_Business/   → 전략 문서, KPI/OKR, 비즈니스 번역
│   ├── Misc/                → 기타 (개인 관심사, 일회성 질문)
│   ├── Daily_Scrap/         → GeekNews 일간 뉴스 스크랩 (자동 수집)
│   │   └── Daily_Scrap.md
│   ├── INDEX.md             → 전체 대화 분류 현황 요약 (자동 생성)
│   └── update_index.py      → INDEX.md 자동 갱신 스크립트
│
├── 05_PM_Outputs/       # PM 스킬 산출물 저장 (OKR, PRD, 로드맵 등)
│   └── README.md
│
├── pm_ppt_generator.py  # 마크다운 산출물 → Gemini 구조화 → python-pptx .pptx 생성
└── pm_skill.py          # PM Skill Launcher (CLI 진입점)
```

> **참고:** Nova Slack 봇(nova_helper)은 `projects/nova_helper/`에 독립 프로젝트로 분리되어 있습니다.
> 공용 유틸리티(.scripts/, .status/, .agents/)는 Workspace 루트에 위치합니다.

## 핵심 파일

- `03_Instructions/user_custom_instructions.md` — Claude 응답 방식 규칙 (한국어 응답, Q1/Q2/Q3 후속 질문 형식 등)
- `03_Instructions/Claude_Code_효율화_매뉴얼.md` — 토큰 효율화 전략 및 에이전트 운영 규칙
- `01_Identity/user_identity.md` — 사용자 정체성 심층 분석
- `02_Profile/user_profile.md` — 직업·기술 스택·커리어 맥락
- `02_Profile/역량맵_Capability_Map.md` — 689개 대화 기반 증거 중심 역량 맵
- `04_WorkLog/INDEX.md` — 전체 WorkLog 파일 인덱스
- `04_WorkLog/Gen2_Policy/Gen2_Policy_대화_학습_정리.md` — Gen2 Policy 특화 대화 정리 (31개, 2025-11~2026-01)

## 자주 쓰는 명령

```bash
# Workspace 루트에서 실행
cd C:\Users\psh93\OneDrive\Desktop\Workspace

# INDEX.md 갱신 (새 파일 추가 후 실행)
python projects/personal_knowledge_base/04_WorkLog/update_index.py

# 에이전트 모니터 실행 (tkinter GUI)
python .status/monitor.py

# 대화 분류 파이프라인
python .scripts/classify.py <file.jsonl>         # 단일 파일 (오분류 시 팝업)
python .scripts/classify.py --dry-run            # 미리보기
python .scripts/classify.py --no-popup           # 팝업 없이 자동 처리

# GeekNews 뉴스 스크랩 수동 실행
python .scripts/daily_scrap_runner.py

# 토큰 사용량 수동 확인
python .status/show_tokens.py                      # 현재 사용량만 표시
python .status/show_tokens.py <토큰수> "<작업명>"  # 기록 추가 후 표시
```

## 토큰 자동 추적

Stop 훅이 자동으로 `show_tokens.py`를 실행하여 터미널에 토큰 바 출력.
- 토큰 데이터: `Workspace/.status/token_usage.json` (5시간 롤링 윈도우)
- Claude Pro 한도: 72,000 토큰 / 5시간, 855,485 토큰 / 주

## 토큰 효율화 필수 규칙

`03_Instructions/Claude_Code_효율화_매뉴얼.md` 기반:
- 대용량 파일: Grep 위치 확인 → offset+limit Read
- 서브에이전트: Write/Edit 권한 필요 명시 + 대용량 파일 Grep 우선 지시
- 내용 복사: verbatim 금지 → 요약 형태로 append

## 인터랙션 규칙

`03_Instructions/user_custom_instructions.md` 기준:
- 항상 한국어로 응답
- 모든 응답 마지막에 Q1/Q2/Q3 후속 질문 3개 제시
- AI임을 언급하지 않음, 사과·유감 표현 금지

## 에이전트 실행 기록 관리

에이전트 로그는 `Workspace/.agents/<agent_type>/` 에 저장. WorkLog와 완전히 분리.

```python
import sys
sys.path.insert(0, 'C:/Users/psh93/OneDrive/Desktop/Workspace/.scripts')
from agent_log import AgentLog

log = AgentLog(
    agent_id   = "작업명_날짜",
    title      = "표시용 제목",
    agent_type = "classify",   # .agents/ 하위 폴더명
)
log.add('처리 시작')
log.update(progress=50)
log.done('완료 메시지')
```

**저장 위치:** `.agents/{agent_type}/{YYYYMMDD_HHMMSS}_{agent_id}.json`

## 업데이트 이력

| 날짜 | 내용 |
|------|------|
| 2026-03-14 | 초기 구조 생성, 기존 메모리 파일 이전 |
| 2026-03-14 | 04_WorkLog 주제별 하위 구조 생성, Custom instructions 통합, 694개 대화 학습 시작 |
| 2026-03-14 | token window_limit 44000 → 72000 수정 (실측 기반) |
| 2026-03-14 | Gen2_Sequence_Annotation_Policy_대화_정리.md 분리 생성 (31개 대화, 2025-11~2026-01) |
| 2026-03-15 | Daily Scrap Agent 구축 (GeekNews 자동 수집, Task Scheduler, 팝업 알림) |
| 2026-03-15 | 디렉토리 정책 재편: scripts/ → .scripts/, .agents/ 최상위 분리, WorkLog 순수화 |
| 2026-04-04 | pm_ppt_generator.py / pm_skill.py / 05_PM_Outputs/ 이 personal_knowledge_base/ 내부로 정착 |
| 2026-04-04 | nova_helper/ → projects/nova_helper/ 로 독립 분리, Workspace 루트 경로 전환 (Desktop/Claude → Desktop/Workspace) |
