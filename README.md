# Nova Log Analytics — Labelit 커맨드 로그 이상 탐지

Labelit 워크스페이스에서 발생하는 커맨드 로그를 분석하여 비정상 편집 패턴을 탐지하는 Databricks 기반 이상 탐지 시스템입니다.

---

## 목차

1. [시스템 개요](#시스템-개요)
2. [탐지 아키텍처](#탐지-아키텍처)
3. [디렉터리 구조](#디렉터리-구조)
4. [노트북 구성](#노트북-구성)
5. [스코어링 시스템](#스코어링-시스템)
6. [실행 방법](#실행-방법)
7. [문서 가이드](#문서-가이드)

---

## 시스템 개요

| 항목 | 내용 |
|------|------|
| **분석 대상** | Labelit 워크스페이스 커맨드 이벤트 (od / ld / rmd) |
| **실행 환경** | Databricks (Unity Catalog) |
| **카탈로그** | `sv_nova_dev_an2_catalog` |
| **결과 테이블** | `analytics.anomaly_detection_results` / `analytics.anomaly_detection_reports` |

### 탐지 목적

- 라벨러의 비정상 위치 이동(점프·진동) 탐지
- 작업 시간 역전·타임스탬프 지연 탐지
- 복수 사용자 동시 편집 및 Undo/Redo 이상 패턴 탐지
- 작업 생산성 이상(스테일 세션, 집중도 저하) 탐지
- 파이프라인 수집 공백 탐지

---

## 탐지 아키텍처

```
Stage 1 — 수집 데이터 무결성 검증 (Raw 기반)
│
├── [Group A] Raw 직접 접근
│   ├── STEP 0: 이벤트 요약 통계
│   └── STEP 3: 타임스탬프 지연 (event_time vs occurred_at)
│
└── [Group B] 인라인 파싱
    ├── STEP 1: 이동 거리 이상 (위치 점프)
    ├── STEP 2: 위치·회전 진동
    └── STEP 4: 피처별 기하학적 이상 (OD: yaw / RMD: 높이)

Stage 2 — 행동 이상 탐지 (Intermediate/Mart 기반)
│
├── STEP 5: 사용자/객체 행동 이상 (복수 사용자 동시 편집)
├── STEP 6: Undo/Redo 패턴 이상          → step_id=5 병합
├── STEP 7: Command Stack 플로우 정합성   → step_id=5 병합
├── STEP 8: 작업 생산성 이상              → step_id=3 병합
└── STEP 9: 파이프라인 신선도             → step_id=3 병합
```

### Stage 경계 기준

| 기준 | Stage 1 | Stage 2 |
|------|---------|---------|
| 핵심 질문 | "이 로그가 올바르게 수집되었는가?" | "이 라벨러/세션의 작업 패턴이 비정상인가?" |
| 데이터 소스 | Raw (`_raw` 컬럼 인라인 파싱) | Staging / Intermediate 테이블 |
| STEPs | 0, 1, 2, 3, 4 | 5, 6, 7, 8, 9 |

---

## 디렉터리 구조

```
nova_log_analytics/
│
├── README.md
│
├── notebooks/                                      ← Databricks 실행 노트북
│   ├── anomaly_detection_runner.py                 메인 러너 (feature·date 파라미터로 전체 STEP 실행)
│   ├── templates/                                  탐색적 분석용 Feature별 템플릿
│   │   ├── od_template.py                          OD (bbox3d) 분석 템플릿
│   │   ├── ld_template.py                          LD (Lane Detection) 분석 템플릿
│   │   └── rmd_template.py                         RMD (Road Mark Detection) 분석 템플릿
│   └── scoring/                                    스코어링 검증 및 튜닝
│       ├── cross_feature_validation.py             Cross-feature 공정성 검증
│       └── weight_tuning_simulation.py             가중치·CAP 파라미터 시뮬레이션
│
└── docs/                                           ← 분석 가이드 및 정책 문서
    ├── anomaly_detection_guide.md                  탐지 워크플로우·판정 기준·STEP별 상세
    ├── anomaly_detection_scoring.md                스코어링 수식·검증·튜닝 가이드
    ├── anomaly_detection_review.md                 스크립트 로직 검토 보고서 (v1.1)
    ├── gen2_command_definitions.md                 Gen2 커맨드 정의
    ├── agents/                                     역할 규칙 및 검증 시나리오
    │   ├── role_rules__labelit_engineer.md         Labelit Engineer 역할 규칙
    │   ├── role_rules__nova_engineer.md            Nova Engineer 역할 규칙
    │   ├── role_rules__qa_tester.md                QA Tester 역할 규칙
    │   ├── scenario__case1_initialize.md           검증 시나리오 1: Feature workspace 초기 셋업
    │   ├── scenario__case2_new_command.md          검증 시나리오 2: 신규 기능/커맨드 추가
    │   └── scenario__case3_ux_change.md            검증 시나리오 3: UI/UX 기반 사용자 플로우 변경
    └── policies/                                   라벨러 행동 정책 (STEP 8 근거)
        ├── labeler_focus_drop_policy.md
        ├── labeler_focus_drop_metric_design.md
        ├── labeler_focus_drop_concept_design.md
        └── focus_drop_v1_refactoring_report.md
```

---

## 노트북 구성

### `notebooks/anomaly_detection_runner.py`

Feature별 파라미터를 받아 전체 STEP을 순서대로 실행하고 결과를 Delta 테이블에 저장하는 메인 노트북.

**파라미터**

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `feature` | `"ld"` | 분석 대상 피처 (od / ld / rmd) |
| `analysis_date` | 전일 | 분석 기준일 (YYYY-MM-DD) |

**출력 테이블**

| 테이블 | 내용 |
|--------|------|
| `analytics.anomaly_detection_results` | STEP별 탐지 결과 (severity / count) |
| `analytics.anomaly_detection_reports` | 종합 보고서 (scoring_details JSON 포함) |

### `notebooks/templates/`

탐색적 분석용 Feature별 템플릿. Stage 1 (STEP 0~4) + STEP 5까지 포함. STEP 6~9는 runner에서 통합 실행.

**템플릿 셀 구조**

```
1.  타이틀
2.  데이터 준비 (temp view 생성)
3.  Stage 1 — Group A: STEP 0 (개요), STEP 3 (시간 괴리)
4.  Stage 1 — Group B: STEP 1 (점프), STEP 2 (진동), STEP 4 (기하학적 이상)
5.  Stage 2: STEP 5 (복수 사용자 편집)
```

### `notebooks/scoring/`

| 노트북 | 목적 |
|--------|------|
| `cross_feature_validation.py` | OD/LD/RMD 3개 feature 동시 실행 후 스코어링 공정성 검증 |
| `weight_tuning_simulation.py` | W_A/W_B/W_C 및 CAP 파라미터 변경 시 점수 변화 시뮬레이션 |

---

## 스코어링 시스템

### Per-STEP 정규화 점수 (v1.2)

```
rate  = 가중_이상량 / 모수 × 100
score = min(rate / CAP_RATE × 100, 100)
```

| 단위 | 대상 STEP | 모수 | CAP 비율 | M |
|------|-----------|------|---------|---|
| 이벤트 | 1, 2, 3, 4 | total_events | 5% | 20 |
| 객체 | 5 | total_task_objects | 10% | 10 |

### 카테고리 집계

```
A (공간 무결성)  = mean(S1, S2, [S4])   # LD는 S4 skip
B (시간 정합성)  = S3                    # STEP 8/9 병합 포함
C (행동 패턴)    = S5                    # STEP 6/7 병합 포함
```

### 종합 점수 및 등급

```
quality_score = 0.40×A + 0.40×B + 0.20×C

정상 : score ≤ 20
주의 : 20 < score ≤ 45
불량 : score > 45
```

### 현재 설정 기준 실행 결과 (2026-04-06, v1.1)

| Feature | Score | Grade | A | B | C |
|---------|-------|-------|-----|-----|-------|
| OD | 20.8 | 주의 | 1.1 | 1.0 | 100.0 |
| LD | 0.7 | 정상 | 0.1 | 1.5 | 0.1 |
| RMD | 5.3 | 정상 | 0.0 | 0.0 | 26.7 |

---

## 실행 방법

### 1. 단일 Feature 분석

Databricks Job에서 `anomaly_detection_runner` 노트북을 실행하고 파라미터를 주입합니다.

```python
dbutils.widgets.text("feature", "od")
dbutils.widgets.text("analysis_date", "2026-04-06")
```

### 2. Cross-Feature 검증

`scoring/cross_feature_validation.py` 노트북에서 3개 feature를 순차 실행 후 비교합니다.

### 3. 파라미터 튜닝

`scoring/weight_tuning_simulation.py` 노트북에서 가중치·CAP 조합을 시뮬레이션합니다.

---

## 문서 가이드

| 문서 | 내용 |
|------|------|
| `docs/anomaly_detection_guide.md` | 워크플로우 구조, Feature별 STEP 판정 기준, 임계값 보정 이력 |
| `docs/anomaly_detection_scoring.md` | 스코어링 수식, Stage 2 병합 구조, 검증·튜닝 노트북 설명 |
| `docs/anomaly_detection_review.md` | 스크립트 로직 검토 보고서 — 발견 이슈 5건 및 수정 내역, 최종 검증 결과 |
| `docs/gen2_command_definitions.md` | Gen2 커맨드 이벤트 정의 |
| `docs/policies/` | 라벨러 집중도 저하(Focus Drop) 정책 및 메트릭 설계 (STEP 8 근거) |
| `docs/agents/role_rules__*.md` | 역할별 규칙 문서 (Labelit Engineer / Nova Engineer / QA Tester) |
| `docs/agents/scenario__*.md` | 검증 시나리오 (case1: 초기 셋업 / case2: 신규 커맨드 / case3: UX 변경) |
