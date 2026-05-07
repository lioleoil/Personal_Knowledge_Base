# Nova Log Analytics — Claude Code 가이드

Labelit 워크스페이스 커맨드 로그를 기반으로 라벨러 행동 패턴을 분석하는 프로젝트.
현재는 이상 탐지(anomaly detection)가 구현된 상태이며, 분석 영역 확장 예정.
Databricks 노트북(Python) 기반, Unity Catalog 환경에서 실행됩니다.

---

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `notebooks/anomaly_detection_runner.py` | 메인 러너 — feature·date 파라미터로 전체 STEP 실행 |
| `notebooks/templates/od_template.py` | OD 탐색적 분석 템플릿 |
| `notebooks/templates/ld_template.py` | LD 탐색적 분석 템플릿 |
| `notebooks/templates/rmd_template.py` | RMD 탐색적 분석 템플릿 |
| `notebooks/scoring/cross_feature_validation.py` | Cross-feature 스코어링 공정성 검증 |
| `notebooks/scoring/weight_tuning_simulation.py` | 가중치·CAP 파라미터 시뮬레이션 |
| `docs/anomaly_detection_guide.md` | STEP별 판정 기준, 임계값, 워크플로우 |
| `docs/anomaly_detection_scoring.md` | 스코어링 수식, Stage 2 병합 구조 |
| `docs/anomaly_detection_review.md` | 로직 검토 보고서 — 이슈 수정 이력 및 검증 결과 |
| `docs/policies/focus_drop_kpi_monitoring_skill.md` | Focus Drop KPI 통합 운영 가이드 (파이프라인 설계·SQL·Bootstrap 절차) |
| `notebooks/focus_drop/focus_drop__gap_percentiles.sql` | gap 1차 percentile 산출 — 분기 1회 |
| `notebooks/focus_drop/focus_drop__session_metrics.sql` | 세션별 gap count/ratio 산출 — 일 배치 |
| `notebooks/focus_drop/focus_drop__session_tags.sql` | 세션 판정 (기준선 참조) — 일 배치 |
| `notebooks/focus_drop/focus_drop__user_day_kpi.sql` | 유저 일 KPI 산출 및 판정 — 일 배치 |
| `notebooks/focus_drop/focus_drop__session_thresholds.sql` | 세션 2차 기준선 갱신 — 주 1회 |
| `notebooks/focus_drop/focus_drop__user_thresholds.sql` | 유저 2차 기준선 갱신 — 주 1회 |

---

## 분석 영역

| 영역 | 상태 | 설명 |
|------|------|------|
| 이상 탐지 (Anomaly Detection) | ✅ 구현 완료 | STEP 0–9, 스코어링 v1.2 |
| KPI 메트릭 설계 및 분석 | 🔧 구현 중 | Focus Drop KPI 파이프라인 구축 (notebooks/focus_drop/) |

---

## 탐지 구조 요약

- **Stage 1** (STEP 0–4): Raw 수집 무결성 — 이동 거리·진동·타임스탬프 지연·기하학적 이상
- **Stage 2** (STEP 5–9): 행동 패턴 이상 — 복수 편집·Undo 패턴·생산성·파이프라인 신선도
- **스코어링**: `quality_score = 0.40×A + 0.40×B + 0.20×C` (CAP 기반 정규화, v1.2)
- **등급**: 정상(≤20) / 주의(21–45) / 불량(>45)

---

## 분석 대상 Feature

| feature | 설명 | 전용 처리 |
|---------|------|-----------|
| `od` | Object Detection (3D bbox) | STEP 4: yaw 드리프트 탐지 |
| `ld` | Lane Detection | STEP 4 skip |
| `rmd` | Road Mark Detection | STEP 4: 높이 이상 탐지 |

---

## KPI 메트릭 설계 — 선행 자료 연결 구조

`docs/policies/` 문서들은 이상 탐지(STEP 8)의 근거 문서인 동시에, KPI 메트릭 설계의 직접 선행 자료다.

| 문서 | 역할 | KPI 연결 포인트 |
|------|------|----------------|
| `labeler_focus_drop_concept_design.md` (v1.0) | 절대값 → percentile 기반 체계 전환 설계 | gap severity 구간(observation·warning·critical·departure) 정의 |
| `labeler_focus_drop_metric_design.md` (v1.0) | 메트릭 구조 및 산출 원칙 | warning/critical/departure count/ratio — KPI 집계 구조의 청사진 |
| `focus_drop_kpi_monitoring_skill.md` | **통합 운영 가이드 (최신)** | 파이프라인 구조·SQL 레퍼런스·Bootstrap 절차·트러블슈팅 |

**설계 계보**: v1.0 개념·메트릭 설계 → Focus Drop KPI 파이프라인(집계·리포팅)

**파이프라인 실행 순서** (`notebooks/focus_drop/`):
- **분기**: `gap_percentiles` (1차 percentile 산출)
- **주 1회 (월)**: `session_thresholds` → `user_thresholds` (rolling 30일 기준선 갱신)
- **일 배치 (04:00 UTC)**: `session_metrics` → `session_tags` → `user_day_kpi`

---

## 작업 시 참고

- 노트북 파일은 Databricks Python 형식 (`# COMMAND ----------` 구분자)
- `analysis_date` 파라미터는 `YYYY-MM-DD` 형식만 허용 (regex 검증)
- STEP 6–9 결과는 별도 step_id 없이 step_id=3(B) 또는 step_id=5(C)에 병합
- `object_id`는 단일 task 내에서만 unique → 분석 시 반드시 `task_id`와 함께 사용
