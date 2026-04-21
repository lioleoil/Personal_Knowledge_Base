# Agent Ecosystem — 구조도 (Mermaid)

> GitHub에서 렌더링 확인용. ASCII 버전 → [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md)

---

## Full Pipeline (v2.0)

```mermaid
flowchart TD
    USER["👤 사용자\n(CLI / 터미널)"]
    ORC["🔧 Orchestrator\norchestrator.py\n토큰 예산 확인 · Manifest 생성 · spawn"]
    UI["💬 User Interface Agent\nHaiku 4.5\n요청 구조화 · 보고서 포워딩 · 승인 수집"]
    ADV["🧠 Advisor Agent (PM)\nOpus 4.7\nPhase 1 컨텍스트 + Phase 2 플랜\nPhase 4-5 평가 · Phase 6 자기개선"]
    EXE["⚙️ Execution Agent\nSonnet 4.6 (도메인별)\nManifest 기반 작업 · Sub-Agent spawn"]
    VAL["✅ Validation Agent\nSonnet / codex-1\nRead-only 독립 검증\nPASS / FAIL / INSUFFICIENT"]
    REP["📋 Reporter Agent\ncodex-1 / Sonnet\n마크다운 보고서 · Slack 알림"]
    GATE{"🔐 사용자 승인 게이트"}
    GIT["🌿 feat/{task_id} 브랜치\ngit commit + gh pr create"]
    LEARN[".agents/advisor/learnings/\n자기개선 패턴 저장\n최신 10건 다음 플랜에 반영"]
    RETRO["🗓️ retrospective.py\n매주 토요일 15:00 KST\nCCR 자동 실행"]

    USER -->|"--full-pipeline"| ORC
    ORC -->|spawn| UI
    UI -->|"_requirement.json"| ADV
    ADV -->|"_advisor_plan.json"| EXE
    EXE <-->|"피드백 루프"| VAL
    VAL -->|PASS| REP
    REP -->|"_report.json"| ADV
    ADV -->|"_evaluation.json"| GATE
    GATE -->|approve| GIT
    GATE -->|reject| END1["종료"]
    GATE -->|feedback| EXE
    VAL -->|FAIL| ADV
    ADV -->|"Phase 6"| LEARN
    LEARN -.->|"다음 작업 Phase 1 로드"| ADV
    RETRO -.->|"주간 로그 분석"| LEARN

    style USER fill:#4A90D9,color:#fff
    style ADV fill:#7B68EE,color:#fff
    style VAL fill:#2ECC71,color:#fff
    style GATE fill:#F39C12,color:#fff
    style GIT fill:#27AE60,color:#fff
    style RETRO fill:#8E44AD,color:#fff
    style LEARN fill:#95A5A6,color:#fff
```

---

## Domain Sub-Agent 레이어

```mermaid
flowchart LR
    EXE["⚙️ Execution Agent"]

    EXE -->|spawn| NH["nova_helper\ndefault preset\nSonnet 4.6"]
    EXE -->|spawn| NL["nova_log_analytics\ncross_vendor preset\nSonnet + Opus + codex-1"]
    EXE -->|spawn| PK["pkb_worklog\ncost_optimized preset\nHaiku 4.5"]
    EXE -->|spawn| SD["sv_dqat\ncross_vendor preset\nSonnet + Opus + codex-1"]
    EXE -->|spawn| SL["sv_lakehouse\ncross_vendor preset\nSonnet + Opus + codex-1"]
    EXE -->|spawn| DS["daily_scrap\ncost_optimized preset\nHaiku 4.5"]

    style EXE fill:#E67E22,color:#fff
    style NH fill:#3498DB,color:#fff
    style NL fill:#3498DB,color:#fff
    style PK fill:#1ABC9C,color:#fff
    style SD fill:#3498DB,color:#fff
    style SL fill:#3498DB,color:#fff
    style DS fill:#1ABC9C,color:#fff
```

---

## Agent Bus 통신 흐름

```mermaid
flowchart LR
    ORC["Orchestrator"]
    UI["User Interface"]
    ADV["Advisor"]
    EXE["Execution"]
    VAL["Validation"]
    REP["Reporter"]
    BUS[("📁 .agents/bus/\n{task_id}_*.json")]

    ORC -->|"_manifest.json"| BUS
    UI -->|"_requirement.json\n_user_decision.json"| BUS
    ADV -->|"_advisor_plan.json\n_advice.json\n_evaluation.json\n_learning.json"| BUS
    EXE -->|"_result.json"| BUS
    VAL -->|"_validation.json"| BUS
    REP -->|"_report.json"| BUS
    BUS -.->|읽기| ADV
    BUS -.->|읽기| EXE
    BUS -.->|읽기| VAL

    style BUS fill:#F39C12,color:#fff
```

---

## 에스컬레이션 정책

```mermaid
flowchart TD
    VR{"Validation\n결과"}
    VR -->|PASS| AE["Advisor\nPhase 4-5 평가"]
    VR -->|INSUFFICIENT| RC{"retry_count\n< 5?"}
    RC -->|Yes| EXE2["Execution 재시도"]
    RC -->|No| ESC["escalate_to_user"]
    VR -->|FAIL| AN{"advisor_needed\n= true?"}
    AN -->|"Yes & calls < 3"| ADV2["Advisor Phase 3\nadvice.json 발행"]
    ADV2 --> EXE2
    AN -->|"No or calls ≥ 3"| ESC
    ESC --> SLACK["Slack 알림\n(nova_helper)"]

    style VR fill:#F39C12,color:#fff
    style ESC fill:#E74C3C,color:#fff
    style SLACK fill:#4A154B,color:#fff
```

---

## 모델 프리셋 비교

```mermaid
quadrantChart
    title 모델 프리셋 — 비용 vs 품질
    x-axis 저비용 --> 고비용
    y-axis 표준품질 --> 최고품질
    quadrant-1 고비용·고품질
    quadrant-2 저비용·고품질
    quadrant-3 저비용·표준품질
    quadrant-4 고비용·표준품질
    cost_optimized: [0.2, 0.3]
    default: [0.5, 0.55]
    cross_vendor: [0.75, 0.8]
    quality_max: [0.9, 0.95]
```
