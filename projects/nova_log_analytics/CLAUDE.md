# Nova Log Analytics — Claude Code 가이드

Labelit 워크스페이스 커맨드 로그를 기반으로 라벨러 행동 패턴을 분석하는 프로젝트.
현재는 이상 탐지(anomaly detection)가 구현된 상태이며, 분석 영역 확장 예정.
Databricks 노트북(Python) 기반, Unity Catalog 환경에서 실행됩니다.

---

## 핵심 파일

> 모든 소스는 `.assistant/skills/` 단일 위치에서 관리됩니다.

### 공용
| 파일 | 역할 |
|------|------|
| `.assistant/skills/common/gen2_command_definitions.md` | 커맨드 정의서 — QA 커버리지 비교용 전체 커맨드 기준 문서 |
| `.assistant/skills/common/stage_transition_analysis.md` | Stage 파이프라인 구조·전환 이력 (stageKey / transitionHistory 샘플) — 전 분석 영역 공통 참조 |

### 이상 탐지 (Anomaly Detection)
| 파일 | 역할 |
|------|------|
| `.assistant/skills/anomaly_detection/anomaly_detection_runner.py` | 메인 러너 — feature·date 파라미터로 전체 STEP 실행 |
| `.assistant/skills/anomaly_detection/templates/od_template.py` | OD 탐색적 분석 템플릿 |
| `.assistant/skills/anomaly_detection/templates/ld_template.py` | LD 탐색적 분석 템플릿 |
| `.assistant/skills/anomaly_detection/templates/rmd_template.py` | RMD 탐색적 분석 템플릿 |
| `.assistant/skills/anomaly_detection/scoring/Scoring v1.2 Cross-Feature Validation.py` | Cross-feature 스코어링 공정성 검증 |
| `.assistant/skills/anomaly_detection/scoring/Scoring Weight Tuning Simulation.py` | 가중치·CAP 파라미터 시뮬레이션 |
| `.assistant/skills/anomaly_detection/guide/SKILL.md` | STEP별 판정 기준, 임계값, 워크플로우 |
| `.assistant/skills/anomaly_detection/scoring/SKILL.md` | 스코어링 수식, Stage 2 병합 구조 |

### Focus Drop KPI
| 파일 | 역할 |
|------|------|
| `.assistant/skills/kpi _metrics/labeling_productivity/focus_drop/SKILL.md` | 통합 운영 가이드 (파이프라인 설계·SQL·Bootstrap 절차) |
| `.sql/focus_drop__ddl.sql` | **[DEPRECATED]** → int__ddl.sql + mrt__ddl.sql 로 통합 |
| `.sql/int__focus_drop_gap_percentiles.sql` | gap 1차 percentile 산출 — 분기 1회 |
| `.sql/int__focus_drop_session_metrics.sql` | 세션별 gap count/ratio/idle_duration 산출 — 일 배치 |
| `.sql/int__focus_drop_task_idle_rollup.sql` | Task별 idle gap 누적 (생산성 연계용) — 일 배치 |
| `.sql/int__focus_drop_session_tags.sql` | 세션 판정 (기준선 참조) — 일 배치 |
| `.sql/mrt__focus_drop_user_day_kpi.sql` | 유저 일 KPI 산출 및 판정 — 일 배치 |
| `.sql/int__focus_drop_session_thresholds.sql` | 세션 2차 기준선 갱신 — 주 1회 |
| `.sql/int__focus_drop_user_thresholds.sql` | 유저 2차 기준선 갱신 — 주 1회 |

### KPI Metric Policy (공통)
| 파일 | 역할 |
|------|------|
| `.assistant/skills/kpi _metrics/kpi_metric_policy.md` | 전 KPI 메트릭 정의·산출식·판정 기준 단일 정책 문서 — 거버넌스 기준 |

### Inspection Quality
| 파일 | 역할 |
|------|------|
| `.assistant/skills/kpi _metrics/inspection_quality/SKILL.md` | 검수 품질 지표 운영 가이드 (데이터 소스·비즈니스 규칙·SQL 템플릿) |
| `.assistant/skills/kpi _metrics/inspection_quality/inspection-fpy_concept_design.md` | 검수 반려율·FPY 기획문서 (지표 정의·필터 조건·검증 결과) |
| `.sql/inspection_quality__ddl.sql` | **[DEPRECATED]** → mrt__ddl.sql 로 통합 |
| `.sql/mrt__inspection_quality_monthly_fpy.sql` | 월별 검수 반려율 & First Pass Yield 산출 — 월 1회 |
| `.sql/mrt__inspection_quality_multi_reject_detail.sql` | 다중 반려 Task 상세 (inspection reject ≥ 2회) — 월 1회 |

### Staging Layer (KPI 공통 선행 레이어)
> 모든 KPI metric SQL은 raw table 직접 참조 대신 staging table을 소스로 사용한다.
> 레이어 구조: `raw → stg → int (dim 포함) → mrt`

**DDL**
| 파일 | 역할 |
|------|------|
| `.sql/stg__ddl.sql` | Staging DDL (5개 현행 + 2개 deprecated) |
| `.sql/int__ddl.sql` | Intermediate DDL (int_object_counts_by_task, int_command_slots_by_task, focus_drop intermediate 6개) |
| `.sql/dim__ddl.sql` | Intermediate DDL — Dimension Lookup Tables (dim_companies, dim_policies, dim_assignments; dim_users 대기) |
| `.sql/mrt__ddl.sql` | Marts DDL (focus_drop_user_day_kpi, inspection_quality 2개, production_volume_weekly) |

**Staging DML**
| 파일 | 역할 |
|------|------|
| `.sql/stg__task_transition_events.sql` | gen2_tasks transitionHistory 전체 flatten — 일 OVERWRITE |
| `.sql/stg__tasks.sql` | gen2_tasks CDC dedup, 태스크 핵심 속성 추출 — 일 OVERWRITE |
| `.sql/stg__workspace_commands.sql` | workspace_command CDC dedup, CloudEvents 1.0 row-level flatten — 일 OVERWRITE |
| `.sql/stg__workspace_command_details.sql` | workspace_command targets·changes·params 상세 — 일 OVERWRITE |
| `.sql/stg__objects.sql` | 10개 객체 테이블 unified CDC dedup, grain: object_id × table_name — 일 REPLACE per-table |
| `.sql/stg__object_counts_by_task.sql` | **[DEPRECATED]** → int__object_counts_by_task.sql |
| `.sql/stg__command_slots_by_task.sql` | **[DEPRECATED]** → int__command_slots_by_task.sql |

**Intermediate DML**
| 파일 | 역할 |
|------|------|
| `.sql/int__object_counts_by_task.sql` | stg_objects → task × table_name × stage_key 집계 — 일 OVERWRITE |
| `.sql/int__command_slots_by_task.sql` | stg_workspace_commands → task별 user_hour_slots·person_days 집계 — 일 OVERWRITE |

**Dimension DML (Intermediate Layer)**
| 파일 | 역할 |
|------|------|
| `.sql/dim__companies.sql` | raw_labelit__company CDC dedup → dim_companies (company_id, company_name) — 일 OVERWRITE |
| `.sql/dim__policies.sql` | raw_labelit__gen2_annotation_policies CDC dedup → dim_policies (policy_id, feature) — 일 OVERWRITE |
| `.sql/dim__assignments.sql` | raw_labelit__assignments CDC dedup → dim_assignments (전 필드 포함, tags ARRAY) — 일 OVERWRITE |
| `.sql/dim__users.sql` | **[대기]** raw 샘플 확인 후 추가 예정 |

### Labeling Productivity
| 파일 | 역할 |
|------|------|
| `.assistant/skills/kpi _metrics/labeling_productivity/productivity/productivity_concept_design.md` | 생산량·생산성 지표 설계 — 납품 Task 수·객체 수·생산성 Metric |
| `.assistant/skills/kpi _metrics/labeling_productivity/productivity/SKILL.md` | 생산량·생산성 운영 가이드 (데이터 소스·비즈니스 규칙·SQL 템플릿) |
| `.sql/production_volume__ddl.sql` | **[DEPRECATED]** → mrt__ddl.sql 로 통합 |
| `.sql/mrt__production_volume_weekly.sql` | 주별 납품 Task 수·객체 수·생산성 집계 — 주 1회 (dim_companies·dim_policies join, int_command_slots_by_task 참조) |

### Operation Analytics
| 파일 | 역할 |
|------|------|
| `.assistant/skills/kpi _metrics/operation_efficiency/SKILL.md` | 운영 지표 운영 가이드 (Stage Duration · Object Delta SQL 템플릿 · DDL · Bootstrap) |
| `.assistant/skills/kpi _metrics/operation_efficiency/operation_concept_design.md` | 운영 지표 설계 — Stage별 산출물 변화(증감)·소요 시간·반려율 |
| `.assistant/skills/stage_progress_dashboard_design.md` | Stage 진행 현황 대시보드 설계 — 업체별 Task 분포·파이프라인 진척률 Funnel·Aging·Reject 재작업·SQL 스케치 3개 |

### 에이전트 R&R
| 파일 | 역할 |
|------|------|
| `.assistant/skills/agents/role_rules__labelit_engineer.md` | Labelit Engineer 에이전트 R&R |
| `.assistant/skills/agents/role_rules__nova_engineer.md` | Nova Engineer 에이전트 R&R |
| `.assistant/skills/agents/role_rules__qa_tester.md` | QA Tester 에이전트 R&R |

### 시나리오
| 파일 | 역할 |
|------|------|
| `.scenario/scenario__case1_initialize.md` | 초기화 케이스 |
| `.scenario/scenario__case2_new_command.md` | 신규 커맨드 케이스 |
| `.scenario/scenario__case3_ux_change.md` | UX 변경 케이스 |

---

## 분석 영역

| 영역 | 상태 | 설명 |
|------|------|------|
| 이상 탐지 (Anomaly Detection) | ✅ 구현 완료 | STEP 0–9, 스코어링 v1.2 |
| Focus Drop KPI | ✅ 구현 완료 | 세션·Task·유저 KPI 파이프라인 (.sql/, 일 배치) + 생산성 idle 연계 |
| Inspection Quality | ✅ 구현 완료 | 월별 검수 반려율·FPY·다중 반려 분석 (.sql/ 작성 완료, DDL 작성 완료) |
| Labeling Productivity | ✅ 구현 완료 | 주별 납품 Task 수·객체 수·생산성·순소요시간 (.sql/ 작성 완료, DDL 작성 완료) |
| Operation Analytics | ⚙️ SQL 작성 중 | Stage별 산출물 변화·소요 시간·반려율·Stage 진행 현황 대시보드 (설계 완료, .sql/ 미생성) |

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

`.assistant/skills/kpi _metrics/labeling_productivity/focus_drop/` 문서들은 이상 탐지(STEP 8)의 근거 문서인 동시에, KPI 메트릭 설계의 직접 선행 자료다.

| 문서 | 역할 | KPI 연결 포인트 |
|------|------|----------------|
| `labeler_focus_drop_concept_design.md` (v1.0) | 절대값 → percentile 기반 체계 전환 설계 | gap severity 구간(observation·warning·critical·departure) 정의 |
| `labeler_focus_drop_metric_design.md` (v1.0) | 메트릭 구조 및 산출 원칙 | warning/critical/departure count/ratio — KPI 집계 구조의 청사진 |
| `SKILL.md` | **통합 운영 가이드 (최신)** | 파이프라인 구조·SQL 레퍼런스·Bootstrap 절차·트러블슈팅 |

**설계 계보**: v1.0 개념·메트릭 설계 → Focus Drop KPI 파이프라인(집계·리포팅)

**파이프라인 실행 순서** (`.sql/`):
- **분기**: `int__focus_drop_gap_percentiles` (1차 percentile 산출)
- **주 1회 (월)**: `int__focus_drop_session_thresholds` → `int__focus_drop_user_thresholds` (rolling 30일 기준선 갱신)
- **일 배치 (04:00 UTC)**:
  1. **Staging**: `stg__task_transition_events` → `stg__tasks` → `stg__workspace_commands` + `stg__workspace_command_details` (병렬) → `stg__objects` (10개 per-table 병렬)
  2. **Intermediate + Dimension** (병렬):
     - Intermediate: `int__object_counts_by_task` + `int__command_slots_by_task` (병렬)
     - Dimension: `dim__companies` + `dim__policies` + `dim__assignments` (병렬, raw 직접 참조)
  3. **Focus Drop (Intermediate)**: `int__focus_drop_session_metrics` → `int__focus_drop_task_idle_rollup` → `int__focus_drop_session_tags` → `mrt__focus_drop_user_day_kpi`
- **주 배치 (월요일)**: `mrt__production_volume_weekly` (int + dim 완료 후)

---

## 작업 시 참고

- 노트북 파일은 Databricks Python 형식 (`# COMMAND ----------` 구분자)
- `analysis_date` 파라미터는 `YYYY-MM-DD` 형식만 허용 (regex 검증)
- STEP 6–9 결과는 별도 step_id 없이 step_id=3(B) 또는 step_id=5(C)에 병합
- `object_id`는 단일 task 내에서만 unique → 분석 시 반드시 `task_id`와 함께 사용
