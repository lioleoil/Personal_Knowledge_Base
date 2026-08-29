# Assistant Instructions

## SKILL 로딩 가이드

| 도메인 | SKILL 경로 | 트리거 키워드 |
| --- | --- | --- |
| 이상 탐지 | `skills/anomaly_detection/guide/SKILL.md` | 이상 탐지, anomaly, 편집 패턴, 커맨드 로그 분석, 위치 점프, 진동 탐지, 시간 괴리 |
| 스코어링 | `skills/anomaly_detection/scoring/SKILL.md` | 스코어링, scoring, 가중치, weight, 튜닝, tuning, CAP, cross-feature, 공정성, 품질 점수, 등급 기준, 민감도 분석 |
| 검수 품질 | `skills/kpi_metrics/inspection_quality/SKILL.md` | 검수 반려율, FPY, First Pass Yield, inspection reject, 반려 사유, 다중 반려, 품질 지표, rejection rate |
| 생산량/생산성 | `skills/kpi_metrics/labeling_productivity/productivity/SKILL.md` | 생산량, 생산성, production volume, productivity, 납품 Task, 납품 객체, 시간당 객체, 인시, 인일, person-hour, person-day, Task 소요시간, 투입 시간, user_hour_slots |
| Focus Drop | `skills/kpi_metrics/labeling_productivity/focus_drop/SKILL.md` | 집중도, focus drop, 집중도 저하, gap 분석, gap percentile, 긴 공백, light session, heavy session, idle session, 작업 이탈, idle 탐지, 3분 기준, 180초, idle 차감, 순소요시간, net working time, task idle |
| 운영 효율성 | `skills/kpi_metrics/operation_efficiency/SKILL.md` | Stage 소요 시간, Cycle Time, 병목, stage duration, object delta, 산출물 변화, 객체 증감, 반려율, review reject, ops, 운영 지표, TAT, Turn-Around Time |
| 쿼리 편집 | `skills/common/query_id_mapping.md` | 쿼리 원격 편집, editAsset query, Numeric ID |
| 파이프라인 DAG | `skills/kpi_metrics/pipeline_dag.md` | 파이프라인, DAG, 의존성, Job 구성, 테이블 상태, 배포 현황, table_name 매핑 |

## 추가 SKILL 참조

- Focus Drop 배포·운영: `.assistant/skills/kpi_metrics/labeling_productivity/focus_drop/focus_drop_deployment.md`
- Focus Drop 생산성 연계: `.assistant/skills/kpi_metrics/labeling_productivity/focus_drop/focus_drop_productivity_linkage.md`
- KPI 메트릭 정책 (전 도메인 공통): `.assistant/skills/kpi_metrics/kpi_metric_policy.md`
- Stage 파이프라인 구조: `.assistant/skills/common/stage_transition_analysis.md`
- 커맨드 분류 체계: `.assistant/skills/common/gen2_command_definitions.md`

## 분석 템플릿 노트북

- OD: `.assistant/skills/anomaly_detection_templates/od_template`
- LD: `.assistant/skills/anomaly_detection_templates/ld_template`
- RMD: `.assistant/skills/anomaly_detection_templates/rmd_template`

## 프로젝트 컨텍스트

- 데이터 소스: `sv_nova_dev_an2_catalog.raw` 스키마의 Labelit 원시 테이블
- 주요 테이블: `raw_labelit__workspace_command`, `raw_labelit__workspace_history`, `raw_labelit__gen2_tasks`, `raw_labelit__gen2_assignments`, `raw_labelit__gen2_annotation_policies`, `raw_labelit__company`
- 원시 데이터 구조: `_id` (PK), `_raw` (variant JSON), `_is_deleted` (soft delete 플래그)
- JSON 파싱: `_raw:field::TYPE` 또는 `get_json_object(_raw, '$.field')` 사용
- **object_id는 단일 task 내에서만 unique** — 분석 시 반드시 task_id와 함께 사용
- 조인: task.policyId → annotation_policy._id / task.assignmentId → assignment._id / task.companyId → company._id

## Agent Memories

### User Preferences
- 한국어 응답 선호
- Databricks SQL 문법 + 테이블 alias (e.g., `t`, `a`, `p`, `c`)

### Data Architecture (2026-05-15)
- **dim 테이블 3종**: `dim_companies`, `dim_assignments`, `dim_policies` (analytics, gold)
- **stg_tasks에 `assignment_id` 컨럼 추가**: task.assignmentId → dim_assignments FK
- **Focus Drop 리팩토링**: raw → stg_workspace_commands + stg_tasks 교체 완료. role 테이블은 TODO
- **설계 원칙**: intermediate에서 디멘션 조인은 dim 테이블 경유 (raw 직접 참조 X)
- **Reviewer 확장**: role 필터만 변경하면 동일 로직으로 확장 가능
- **Mart 테이블 4종**: `mrt_` prefix, 내장 백필 로직 포함, DDL에 컨럼 COMMENT 적용
- **SQL Runner 패턴**: `.dbquery.ipynb` → `_run_sql_query` 노트북 경유 실행
- **Job reset API 사용 시 `name` 필드 필수** (Untitled 방지)
- **kpi_staging_daily 9 tasks**: stg 4종 + dim 3종 (병렬) + int_object_counts(←stg_objects) + int_command_slots(←stg_workspace_commands)
- **stg_objects → int_object_counts 의존성 필수**: 순서 미보장 시 납품 Task 객체 수 누락 발생 (5/15 확인)
- **int_object_counts_by_task**: stg_objects 전체 상태를 일별 스냅샷 (snapshot_date 파티션)

### Key Discoveries
- deliveryId는 inspection 진입 시점에 배정됨 (납품 승인 이후 아님)
- reason 필드에 대소문자/trailing space 중복 → NULLIF(TRIM(reason), '') + LOWER() 필요
- transitionHistory의 from_json 스키마는 반드시 문자열 리터럴로 전달
- 재납품: 동일 Task는 1건 (월 경계 귀속 미확정)
- role_group 테이블 미생성 — 별도 생성 예정
- **table_name은 반드시 복수형** 사용 (gen2_lines, gen2_road_boundaries 등). 단수형(gen2_road_boundary) 사용 시 매칭 실패 → objects=0 발생 (5/15 버그 수정)
