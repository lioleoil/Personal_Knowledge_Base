# Personal Knowledge Base

> 기본 저장 경로: `C:\Users\psh93\OneDrive\Desktop\Workspace\projects\personal_knowledge_base`

## 저장소 목적

개인 지식 관리 시스템(Personal Knowledge Base). Claude 대화 학습 결과물을 주제별로 구조화하여 저장한다.

**글로벌 자산(Identity, Profile, Instructions, PM Outputs)은 Workspace 루트의 `global/` 폴더로 이관되었습니다.**  
→ 루트 `CLAUDE.md` 참고

## 이 프로젝트의 역할

`personal_knowledge_base/`는 이제 **04_WorkLog — 대화 로그 주제별 정리** 전용 폴더입니다.

## 폴더 구조

```
personal_knowledge_base/
└── 04_WorkLog/          # 대화 로그 요약 + 정리 마크다운 전용
    ├── Nova/                → Nova 대시보드, 사내 서비스 기획/릴리즈
    ├── ODD/                 → ASAM OpenODD, 운행설계영역
    ├── OpenLABEL/           → ASAM OpenLABEL, SV→OpenLABEL 마이그레이션
    ├── DQA/                 → 데이터 품질 분석, 라벨 검증
    ├── Gen1_Gen2_Labeling/  → OD/RMD/3DP 라벨링 성능 측정, Policy
    ├── Gen2_Policy/         → Sequence 기반 Gen2 Annotation Policy 수립·조항 작성·번역 (2025-11~)
    ├── Career/              → 이직, 커리어 전략, 이력서, 포트폴리오
    ├── Python_Scripts/      → Python 스크립트, 자동화, 파일 처리
    ├── Strategy_Business/   → 전략 문서, KPI/OKR, 비즈니스 번역
    ├── Misc/                → 기타 (개인 관심사, 일회성 질문)
    ├── Daily_Scrap/         → GeekNews 일간 뉴스 스크랩 (자동 수집)
    │   └── Daily_Scrap.md
    ├── INDEX.md             → 전체 대화 분류 현황 요약 (자동 생성)
    └── update_index.py      → INDEX.md 자동 갱신 스크립트
```

## 글로벌 자산 참조 (Workspace 루트)

| 폴더 | 내용 |
|---|---|
| `../../global/01_Identity/` | 사용자 정체성 분석 |
| `../../global/02_Profile/` | 직업 프로필, 역량맵 |
| `../../global/03_Instructions/` | Claude 인터랙션 커스텀 설정 |
| `../../global/05_PM_Outputs/` | PM 스킬 산출물 |
| `../../.scripts/pm_ppt_generator.py` | 마크다운 → PPT 생성기 |
| `../../.scripts/pm_skill.py` | PM Skill Launcher |

## 자주 쓰는 명령

```bash
# Workspace 루트에서 실행
cd C:\Users\psh93\OneDrive\Desktop\Workspace

# INDEX.md 갱신 (새 파일 추가 후 실행)
python projects/personal_knowledge_base/04_WorkLog/update_index.py

# 에이전트 모니터 실행 (tkinter GUI)
python .status/monitor.py

# 대화 분류 파이프라인
python .scripts/classify.py <file.jsonl>
python .scripts/classify.py --dry-run
python .scripts/classify.py --no-popup

# GeekNews 뉴스 스크랩 수동 실행
python .scripts/daily_scrap_runner.py

# PM 스킬 런처
python .scripts/pm_skill.py

# 토큰 사용량 확인
python .status/show_tokens.py
python .status/show_tokens.py <토큰수> "<작업명>"
```

## 업데이트 이력

| 날짜 | 내용 |
|------|------|
| 2026-03-14 | 초기 구조 생성, 기존 메모리 파일 이전 |
| 2026-03-14 | 04_WorkLog 주제별 하위 구조 생성, Custom instructions 통합, 694개 대화 학습 시작 |
| 2026-03-14 | token window_limit 44000 → 72000 수정 (실측 기반) |
| 2026-03-14 | Gen2_Sequence_Annotation_Policy_대화_정리.md 분리 생성 (31개 대화, 2025-11~2026-01) |
| 2026-03-15 | Daily Scrap Agent 구축 (GeekNews 자동 수집, Task Scheduler, 팝업 알림) |
| 2026-03-15 | 디렉토리 정책 재편: scripts/ → .scripts/, .agents/ 최상위 분리, WorkLog 순수화 |
| 2026-04-04 | pm_ppt_generator.py / pm_skill.py / 05_PM_Outputs/ → personal_knowledge_base/ 내부로 정착 |
| 2026-04-04 | nova_helper/ → projects/nova_helper/ 로 독립 분리, Workspace 루트 경로 전환 |
| 2026-04-11 | 글로벌 통합 관리 체계 구축: 01_Identity, 02_Profile, 03_Instructions, 05_PM_Outputs → global/, pm_ppt_generator.py, pm_skill.py → .scripts/ |
