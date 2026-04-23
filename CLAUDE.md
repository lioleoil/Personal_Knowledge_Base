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

---

## 분석 영역

| 영역 | 상태 | 설명 |
|------|------|------|
| 이상 탐지 (Anomaly Detection) | ✅ 구현 완료 | STEP 0–9, 스코어링 v1.2 |
| KPI 메트릭 설계 및 분석 | 🔜 미전개 | 라벨러 생산성·효율성 지표 설계 및 집계 |

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
| `labeler_focus_drop_policy.md` (v0.9) | STEP 8에 반영된 현행 운영 기준 | `avg_gap > 30s AND gaps_5min > 10` — 생산성 저하 탐지의 출발점 |
| `labeler_focus_drop_concept_design.md` (v1.0) | 절대값 → percentile 기반 체계 전환 설계 | gap severity 구간(observation·warning·critical·departure) 정의 |
| `labeler_focus_drop_metric_design.md` (v1.0) | 메트릭 구조 및 산출 원칙 | `warning_gap_count`, `critical_gap_count`, `departure_gap_count`, ratio 지표 — KPI 집계 구조의 청사진 |
| `focus_drop_v1_refactoring_report.md` | v1.0 전환 리팩토링 보고서 | 기존 탐지 → 메트릭 체계로 전환 시 변경 사항 |

**설계 계보**: v0.9 운영 기준(탐지) → v1.0 개념·메트릭 설계(측정) → KPI 메트릭 분석(집계·리포팅)

---

## 작업 시 참고

- 노트북 파일은 Databricks Python 형식 (`# COMMAND ----------` 구분자)
- `analysis_date` 파라미터는 `YYYY-MM-DD` 형식만 허용 (regex 검증)
- STEP 6–9 결과는 별도 step_id 없이 step_id=3(B) 또는 step_id=5(C)에 병합
- `object_id`는 단일 task 내에서만 unique → 분석 시 반드시 `task_id`와 함께 사용
