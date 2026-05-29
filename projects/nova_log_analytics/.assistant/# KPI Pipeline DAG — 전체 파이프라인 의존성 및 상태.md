# KPI Pipeline DAG — 전체 파이프라인 의존성 및 상태

> 최종 갱신: 2026-05-15 (kpi_staging_daily 9 tasks 확장, int_object_counts/int_command_slots 의존성 추가)

---

## 1. 레이어 구조

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│  RAW  │  sv_nova_dev_an2_catalog.raw.*                                           │
│       │  (CDC 원본 — _id, _raw, _ingested_at, _is_deleted)                       │
└───────┴───────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│  STG  │  stg_tasks │ stg_workspace_commands │ stg_task_transition_events │    │
│       │  stg_objects │ stg_workspace_command_details │ stg_workspace_history  │
└───────┴───────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│  INT  │  dim_companies │ dim_assignments │ dim_policies                        │
│       │  int_object_counts_by_task │ int_command_slots_by_task                 │
│       │  int_focus_drop_gap_thresholds                                          │
│       │  int_focus_drop_session_metrics → int_focus_drop_task_idle_rollup       │
│       │                                 → int_focus_drop_session_tags            │
│       │  int_focus_drop_session_thresholds                                      │
│       │  int_focus_drop_user_day_kpi → int_focus_drop_user_thresholds           │
└───────┴───────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│  MRT  │  mrt_production_volume_weekly                                           │
│       │  mrt_focus_drop_user_day_kpi                                            │
│       │  mrt_inspection_quality_monthly_fpy                                     │
│       │  mrt_inspection_quality_multi_reject                                    │
└───────┴───────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Job 스케줄 및 Task DAG

```
╔═════════════════════════════════════════════════════════════════╗
║  04:00 UTC │ kpi_staging_daily (Job ID: 794781503662993)       ║
╠═══════════╩═══════════════════════════════════════════╣
║                                                                   ║
║  [Phase 1: 병렬 실행 — 의존성 없음]                                 ║
║  stg_tasks                     ─┐                                ║
║  stg_workspace_commands        ─┼── 병렬                         ║
║  stg_task_transition_events    ─┤                                ║
║  stg_objects                   ─┤                                ║
║  dim_companies                 ─┤                                ║
║  dim_assignments               ─┤                                ║
║  dim_policies                  ─┘                                ║
║                                                                   ║
║  [Phase 2: 의존성 있음]                                           ║
║  int_object_counts  ← stg_objects                                ║
║  int_command_slots  ← stg_workspace_commands                     ║
║                                                                   ║
╚═════════════════════════════════════════════════════════════════╝
                          │
                          ▼ (시간차 보장)
╔═════════════════════════════════════════════════════════════════╗
║  04:30 UTC │ focus_drop_daily (Job ID: 11361746396560)         ║
╠═══════════╩═══════════════════════════════════════════╣
║                                                                   ║
║  session_metrics                                                   ║
║      ├── task_idle_rollup                                        ║
║      └── session_tags                                            ║
║              └── user_day_kpi                                    ║
║                                                                   ║
╚═════════════════════════════════════════════════════════════════╝

╔═════════════════════════════════════════════════════════════════╗
║  월 03:00 UTC │ focus_drop_weekly (Job ID: 1008497285809413)  ║
╠══════════════╩════════════════════════════════════════╣
║                                                                   ║
║  session_thresholds  ─┐ 병렬                                     ║
║  user_thresholds     ─┘                                           ║
║                                                                   ║
╚═════════════════════════════════════════════════════════════════╝

╔═════════════════════════════════════════════════════════════════╗
║  월 05:00 UTC │ kpi_weekly (Job ID: 1034375050896341)         ║
╠══════════════╩════════════════════════════════════════╣
║                                                                   ║
║  production_volume_weekly                                          ║
║    sql_path: .sql/mart/mrt__production_volume_weekly.dbquery.ipynb  ║
║                                                                   ║
╚═════════════════════════════════════════════════════════════════╝
```

---

## 3. 데이터 의존성 DAG (테이블 레벨)

```
raw_labelit__workspace_command
    └── stg_workspace_commands
            ├── int_command_slots_by_task [← stg_workspace_commands]
            │       └── mrt_production_volume_weekly (투입 자원)
            ├── int_focus_drop_session_metrics
            │       ├── int_focus_drop_task_idle_rollup
            │       │       └── mrt_production_volume_weekly (idle 차감)
            │       ├── int_focus_drop_session_tags
            │       │       └── int_focus_drop_user_day_kpi
            │       │               ├── int_focus_drop_user_thresholds
            │       │               └── mrt_focus_drop_user_day_kpi
            │       └── int_focus_drop_session_thresholds
            └── (focus_drop_daily 에서 참조)

raw_labelit__gen2_* (10개 객체 테이블)
    └── stg_objects (unified CDC dedup, 10종 per-table REPLACE)
            └── int_object_counts_by_task [← stg_objects]
                    └── mrt_production_volume_weekly (객체 수)

raw_labelit__gen2_tasks
    ├── stg_tasks (task 속성)
    ├── stg_task_transition_events (transitionHistory flatten)
    │       ├── mrt_production_volume_weekly (납품/착수 이벤트)
    │       ├── mrt_inspection_quality_monthly_fpy (reject 이벤트)
    │       └── mrt_inspection_quality_multi_reject (reject 상세)
    └── stg_objects (10개 객체 테이블 CDC)

raw_labelit__company
    └── dim_companies
            └── mrt_production_volume_weekly (company_name)

raw_labelit__gen2_annotation_policies
    └── dim_policies
            └── mrt_production_volume_weekly (feature)

raw_labelit__gen2_assignments
    └── dim_assignments
```

---

## 4. 전체 테이블 상태 (현황)

### Staging (6개)

| 테이블 | 갱신 전략 | 현황 |
|--------|----------|------|
| `stg_tasks` | INSERT OVERWRITE | ✅ 3,058행 (5/15) |
| `stg_workspace_commands` | INSERT OVERWRITE | ✅ 11.3M행 (5/15) |
| `stg_task_transition_events` | INSERT OVERWRITE | ✅ 10,775행 (5/15) |
| `stg_objects` | per-table REPLACE | ✅ 1,273 tasks 운영 중 |
| `stg_workspace_command_details` | INSERT OVERWRITE | ✅ 운영 중 |
| `stg_workspace_history` | INSERT OVERWRITE | ✅ 운영 중 |

### Dimension (3개)

| 테이블 | 갱신 전략 | 현황 |
|--------|----------|------|
| `dim_companies` | INSERT OVERWRITE | ✅ 33행 |
| `dim_assignments` | INSERT OVERWRITE | ✅ 96행 |
| `dim_policies` | INSERT OVERWRITE | ✅ 6행 |

### Intermediate — Productivity (2개)

| 테이블 | 갱신 전략 | 현황 |
|--------|----------|------|
| `int_object_counts_by_task` | REPLACE WHERE snapshot_date | ✅ 1,273 tasks/일 (5/15) |
| `int_command_slots_by_task` | REPLACE WHERE event_date | ✅ 운영 중 |

### Intermediate — Focus Drop (7개)

| 테이블 | 갱신 전략 | 현황 |
|--------|----------|------|
| `int_focus_drop_gap_thresholds` | 예정 INSERT (version) | ✅ v2 |
| `int_focus_drop_session_metrics` | REPLACE WHERE analysis_date | ✅ 9,252행 (4/6∼5/14) |
| `int_focus_drop_session_thresholds` | 예정 INSERT (version) | ✅ v2 |
| `int_focus_drop_task_idle_rollup` | REPLACE WHERE analysis_date | ✅ 2,959행 |
| `int_focus_drop_session_tags` | REPLACE WHERE analysis_date | ✅ 9,252행 |
| `int_focus_drop_user_day_kpi` | REPLACE WHERE analysis_date | ✅ 2,371행 |
| `int_focus_drop_user_thresholds` | 예정 INSERT (version) | ✅ v2 |

### Mart (4개)

| 테이블 | 갱신 전략 | 백필 | 현황 |
|--------|----------|------|------|
| `mrt_production_volume_weekly` | REPLACE WHERE deliver_week_start | 누락 주 자동 | ✅ 52행 (4/6∼5/11) |
| `mrt_focus_drop_user_day_kpi` | REPLACE WHERE analysis_date | 누락일 자동 | ✅ 2,426행 (4/6∼5/14) |
| `mrt_inspection_quality_monthly_fpy` | REPLACE WHERE deliver_month | 누락 월 자동 | ✅ 2행 (26-04, 26-05) |
| `mrt_inspection_quality_multi_reject` | REPLACE WHERE deliver_month | 누락 월 자동 | ✅ 26행 |

---

## 5. 실행 아키텍처

### SQL Runner 패턴

```
Databricks Job Task
    └── notebook_task: _run_sql_query
            └── base_parameters: {"sql_path": "<.dbquery.ipynb 경로>"}
                    └── 파일 읽기 → COMMAND 구분자 분리 → spark.sql() 순차 실행
```

- `.dbquery.ipynb`는 Databricks SQL Query 타입 → `notebook_task`로 직접 실행 불가
- Runner 경로: `/Workspace/Users/seonghwan.park@stradvision.com/.sql/_run_sql_query`
- 모든 SQL 파일에 내장 백필 로직 포함 (gap 감지 → 누락 기간 자동 복원)

### 알림 설정

- `on_success` + `on_failure`: seonghwan.park@stradvision.com
- Health rule: 실행 > 1시간 경고
- 안정화 후 `on_success` 제거 권장

---

## 6. SQL 파일 폴더 구조

```
/Users/seonghwan.park@stradvision.com/.sql/
├── staging/          (폴더 ID: 44484998357622)
│   ├── stg__tasks
│   ├── stg__workspace_commands
│   ├── stg__workspace_command_details
│   ├── stg__workspace_history
│   ├── stg__task_transition_events
│   ├── stg__objects
│   └── stg__ddl
├── intermediate/     (폴더 ID: 44484998357623)
│   ├── dim__companies / dim__assignments / dim__policies / dim__ddl
│   ├── int__object_counts_by_task / int__command_slots_by_task
│   ├── int__focus_drop_gap_thresholds
│   ├── int__focus_drop_session_metrics / session_tags / session_thresholds
│   ├── int__focus_drop_task_idle_rollup
│   ├── int__focus_drop_user_day_kpi / user_thresholds
│   └── int__ddl
├── mart/             (폴더 ID: 1540627169472552)
│   ├── mrt__production_volume_weekly
│   ├── mrt__focus_drop_user_day_kpi
│   ├── mrt__inspection_quality_monthly_fpy
│   ├── mrt__inspection_quality_multi_reject_detail
│   └── mrt__ddl
└── _run_sql_query    (노트북 ID: 1540627169472554)
```

---

## 7. 의존성 설계 근거

| 판단 | 근거 |
|------|------|
| dim 3종 ↛ stg_tasks | dim은 raw CDC dedup으로 직접 산출. stg_tasks 결과 미참조 |
| int_object_counts ← stg_objects | stg_objects 갱신 후 스냅샷 필수 (순서 미보장 시 누락 발생 확인됨, 5/15) |
| int_command_slots ← stg_workspace_commands | 커맨드 데이터 반영 후 집계 필수 |
| focus_drop_daily 내부 순서 | session_tags가 session_metrics 결과 참조, user_day_kpi가 session_tags 참조 |
| kpi_weekly 독립 | staging + focus_drop 선행 적재 데이터 읽기만 함 (시간차로 보장) |
| Job 간 시간차 | 04:00 → 04:30 → 월 03:00 / 월 05:00 — 스케줄 순서로 선후행 보장 |
| mrt 백필 | 각 mart SQL에 내장 — 파라미터 없이 Run All 시 누락 기간 자동 복원 |

---

## 8. 알려진 이슈 & 해결 이력

| 날짜 | 이슈 | 해결 |
|------|------|------|
| 5/15 | `mrt_production_volume_weekly` obj CTE에서 table_name 단수형 사용 → LD의 lines만 집계 | 10개 복수형으로 수정, 전체 재적재 |
| 5/15 | 5/11주 objects=0 — int_object_counts가 stg_objects 갱신 전 스냅샷 실행 | 의존성 추가 + 5/7~14 백필 |
| 5/15 | mrt__ddl COMMENT에 소스 테이블명 오류 (bbox3d 등) | 4개 컨럼 ALTER COLUMN COMMENT |

---

## 9. Bootstrap 절차 (재초기화 시)

1. `int__ddl` 실행 (9개 int 테이블 DDL)
2. `mrt__ddl` 실행 (4개 mrt 테이블 DDL)
3. `setup_kpi_jobs` 노트북 Bootstrap 실행 — int 7단계
4. mart 초기 적재: `INSERT OVERWRITE` 전체 복원
5. `setup_kpi_jobs` Job 재설정 Cell 실행 — 4개 Job reset
6. Job 수동 트리거로 검증

> Bootstrap 노트북: `/Users/seonghwan.park@stradvision.com/setup_kpi_jobs`

---

## 10. table_name 매핑 (int_object_counts → mrt)

`int_object_counts_by_task.table_name` 값과 `mrt_production_volume_weekly` 컨럼 매핑:

| table_name (복수형) | mrt 컨럼 | Feature |
|---|---|---|
| `gen2_lines` | ld_lines | MV2_LD |
| `gen2_line_points` | ld_line_points | MV2_LD |
| `gen2_road_boundaries` | ld_road_boundaries | MV2_LD |
| `gen2_road_boundary_points` | ld_road_boundary_points | MV2_LD |
| `gen2_lanes` | ld_lanes | MV2_LD |
| `gen2_topologies` | ld_topologies | MV2_LD |
| `gen2_polywall_roadmark_objects` | rmd_polywall_objects | MV2_RMD |
| `gen2_box_roadmark_objects` | rmd_bbox3d_objects | MV2_RMD |
| `gen2_dynamic_targets` | dynamic_targets | MV2_OD |
| `gen2_static_targets` | static_targets | MV2_OD/SOD/TSTLD |
