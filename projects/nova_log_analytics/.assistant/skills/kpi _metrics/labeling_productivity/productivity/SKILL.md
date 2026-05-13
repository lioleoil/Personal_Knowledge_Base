# Production Volume & Productivity Skill

생산량(납품 Task 수, 납품 객체 수)과 생산성(시간당 객체 수, 1인 1일 Task 수, Task 평균 소요시간) 산출을 위한 가이드.

## 트리거 키워드

"생산량", "생산성", "production volume", "productivity", "납품 Task", "납품 객체", "시간당 객체", "인시", "인일", "person-hour", "person-day", "Task 소요시간", "투입 시간", "user_hour_slots" 중 하나라도 포함되면 이 스킬을 로드할 것.

---

## 1. 데이터 소스

> **운영 SQL 원칙**: `.sql/mrt__production_volume_weekly.sql`은 raw 객체 테이블/transitionHistory를 직접 파싱하지 않고 staging/intermediate 레이어 테이블을 소스로 사용한다.
> staging 갱신: `.sql/stg__*.sql` / intermediate 갱신: `.sql/int__*.sql` (일 배치).
> raw 메타(`company`, `gen2_annotation_policies`)와 `focus_drop_task_idle_rollup`만 직접 참조한다.

> 전체 카탈로그 prefix: `sv_nova_dev_an2_catalog.raw.raw_labelit__`

### 1.0 운영 소스 (Staging / Intermediate)

| 소스 테이블 | grain | 출처 | 용도 |
| --- | --- | --- | --- |
| `analytics.stg_task_transition_events` | task_id × event row | `raw_labelit__gen2_tasks` transitionHistory flatten | 납품/착수 이벤트 추출 |
| `analytics.int_object_counts_by_task` | task_id × table_name × stage_key | 10개 객체 테이블 CDC dedup + GROUP BY | 납품 객체 수 PIVOT |
| `analytics.int_command_slots_by_task` | task_id | `raw_labelit__workspace_command` 집계 | user_hour_slots / person_days |

### 1.1 raw 메타 직접 참조 (staging에 없음)

| 항목 | 테이블 | 용도 |
| --- | --- | --- |
| 업체 메타 | `raw_labelit__company` | companyId → company name |
| Annotation Policy | `raw_labelit__gen2_annotation_policies` | policyId → feature name |
| idle 차감 | `analytics.focus_drop_task_idle_rollup` | net 소요시간 산출 (idle gap 차감) |

### 1.2 raw 객체 테이블 (staging 산출 입력 — 참고만)

| 항목 | 테이블 | Feature |
| --- | --- | --- |
| 객체 테이블 (LD) | `gen2_lines`, `gen2_line_points`, `gen2_road_boundaries`, `gen2_road_boundary_points`, `gen2_lanes`, `gen2_topologies` | MV2_LD |
| 객체 테이블 (RMD) | `gen2_polywall_roadmark_objects`, `gen2_box_roadmark_objects` | MV2_RMD |
| 객체 테이블 (OD) | `gen2_dynamic_targets`, `gen2_static_targets` | MV2_OD (합산) |
| 객체 테이블 (SOD) | `gen2_static_targets` | MV2_SOD |
| 객체 테이블 (TSTLD) | `gen2_static_targets` | MV2_TSTLD |

> 10개 객체 테이블은 `stg__objects.sql` 내부에서만 직접 참조. PIVOT 집계는 `int__object_counts_by_task.sql` 경유 → 운영 KPI SQL은 `int_object_counts_by_task` 테이블만 본다.

### 1.3 transitionHistory 스키마 (staging 적재 입력 구조 참조)

```
array<struct<
  fromState: string,
  toState: string,
  trigger: string,
  actionBy: string,
  actionAt: string,
  reason: string,
  metadata: map<string, string>
>>
```

**from_json 파싱 패턴** (staging 적재 SQL 내부에서만 사용):
```sql
from_json(
  get_json_object(`_raw`, '$.transitionHistory'),
  'array<struct<fromState:string,toState:string,trigger:string,actionBy:string,actionAt:string,reason:string,metadata:map<string,string>>>'
)
```

> 주의: 스키마를 **문자열 리터럴** (작은따옴표)로 전달해야 함. 타입 표현식 `ARRAY<STRUCT<...>>`은 중첩 `>` 파싱 오류 발생.

### 1.4 핵심 전환 이벤트 (staging 컬럼 기준)

| 이벤트 | 필터 (staging snake_case) | 의미 |
| --- | --- | --- |
| 납품 | `from_state='waiting_submit' AND to_state='inspection'` | 리뷰어가 검수팀에 제출 |
| 라벨링 착수 | `from_state='waiting_labeling' AND to_state='labeling' AND trigger='start'` | 라벨러 최초 작업 시작 |
| 재배정 (제외) | `from_state='labeling' AND to_state='labeling' AND trigger='reassign'` | 담당자 변경, 착수 아님 |

### 1.5 Command Log 주요 필드 (staging 적재 입력 — 참고만)

운영 KPI SQL은 `int_command_slots_by_task`의 집계 컬럼(`user_hour_slots`, `person_days`)만 사용. raw `workspace_command` 직접 참조는 staging SQL 내부에서만 발생.

| 필드 | 파싱 | 설명 |
| --- | --- | --- |
| `user_name` | `_raw:userName::STRING` | 작업자 이름 |
| `event_hour` | `DATE_FORMAT(CONVERT_TIMEZONE('UTC', 'Asia/Seoul', TO_TIMESTAMP(_raw:createdAt::STRING)), 'yyyy-MM-dd HH')` | KST 시간 슬롯 |
| `event_date` | `DATE(CONVERT_TIMEZONE('UTC', 'Asia/Seoul', TO_TIMESTAMP(_raw:createdAt::STRING)))` | KST 날짜 |
| `task_id` | `_raw:taskId::STRING` | 연결 Task ID |

---

## 2. 핵심 비즈니스 규칙

### 2.1 설계 원칙

- Command Log 커맨드 수는 **객체 생산량 산출에 사용하지 않음**. 커맨드는 과정이며, 결과물은 객체 테이블 스냅샷.
- 생산성 = 생산량 ÷ 투입 자원. 투입 자원은 Command Log 기반 추정.
- 측정 목적: **업체 납품 대비 총 투입 효율** (Labeler + Reviewer 합산).
- Stage별 개별 효율은 운영 지표(`operation_concept_design.md`)에서 후속 처리.

### 2.2 납품 카운트 규칙

- 동일 Task의 deliver 이벤트가 복수(reject 후 재납품)여도 **하나의 납품 건**으로 카운트.
- 재납품 시점(`actionAt`)이 최초 착수 주와 다를 경우 집계 주 귀속 로직 별도 정의 필요 (미확정).

### 2.3 라벨링 착수 시점

- `fromState='waiting_labeling' AND toState='labeling' AND trigger='start'`의 `actionAt`.
- reject 후 재작업으로 복수 발생 시 **최초 진입 시점** 기준.
- 착수 이벤트 없는 Task는 소요시간 집계 제외.

### 2.4 투입 자원 범위

- **Labeler + Reviewer 합산** (전체 파이프라인 투입).
- `role_group` 테이블 생성 전까지 Command Log의 전체 user_name 사용 (role 필터 미적용).

### 2.5 시간대 규약

- 모든 시간 집계는 **KST (UTC+9)** 기준.
- SQL 변환: `CONVERT_TIMEZONE('UTC', 'Asia/Seoul', column)` 또는 `column + INTERVAL 9 HOURS`.

### 2.6 CDC 중복 제거

```sql
ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
-- WHERE rn = 1
```

모든 raw 테이블은 CDC 수집 → 동일 `_id` 복수 버전 존재 가능.

---

## 3. 지표 정의

### 3.1 생산량 (Production Volume)

| 지표 | 산출식 | 소스 |
| --- | --- | --- |
| 납품 Task 수 | 납품 이벤트 발생 Task DISTINCT COUNT | transitionHistory |
| 납품 객체 수 (primary) | 납품 Task의 `stageKey='inspection'` 객체 COUNT (feature별 기준 테이블) | 객체 테이블 |
| 납품 포인트 수 (보조) | LD 전용: `gen2_line_points` + `gen2_road_boundary_points` COUNT | 객체 테이블 |
| 객체당 포인트 수 | `delivered_point_count / delivered_object_count` — LD 복잡도 proxy | 산출값 |

> **2-tier 설계**: primary objects(lines·rb·lanes·topo·polywall·bbox3d·dynamic·static)는 사람이 직접 생성한 산출물. points는 lines·road_boundary에 종속되는 보조 지표로 복잡도 추정에 활용. LD `delivered_object_count`에 points는 포함하지 않음.

### 3.2 생산성 (Productivity)

| 지표 | 분자 | 분모 | 단위 |
| --- | --- | --- | --- |
| 시간당 객체 수 | 납품 객체 수 | `user_hour_slots` | obj/person-hour |
| 1인 1일 납품 Task 수 | 납품 Task 수 | `person-days` | tasks/person-day |
| Task 평균 소요시간 (gross) | — | 납품 `actionAt` − 착수 `actionAt` | hours/task |
| Task 순소요시간 (net) | — | gross − `task_total_idle_sec` (Focus Drop 연계) | hours/task |

> `task_total_idle_sec` 소스: `analytics.focus_drop_task_idle_rollup` (`role_scope='labeler'`, Phase C: `'all_roles'`). Focus Drop 파이프라인 미적재 시 `COALESCE(0)` → net = gross.

### 3.3 투입 자원 산출

| 지표 | 산출식 | 비고 |
| --- | --- | --- |
| `user_hour_slots` | `COUNT(DISTINCT CONCAT(user_name, '-', event_hour))` | 인시 근사치 |
| `person-days` | `COUNT(DISTINCT CONCAT(user_name, '-', event_date))` | 인일 근사치 |

---

## 4. SQL 템플릿 (staging 기반 — 운영 SQL)

> 실제 운영 SQL은 주 단위 (`deliver_week_start` 파티션) — `.sql/mrt__production_volume_weekly.sql` 참조. 아래는 운영 SQL의 핵심 CTE 패턴을 발췌한다.

### 4.1 납품 이벤트 추출 (대상 주 최초 납품)

```sql
WITH deliver_events AS (
  SELECT
    task_id,
    company_id,
    policy_id,
    action_at                                                        AS deliver_at,
    event_week                                                       AS deliver_week_start,
    ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY action_at ASC)  AS deliver_seq
  FROM analytics.stg_task_transition_events
  WHERE from_state = 'waiting_submit'
    AND to_state   = 'inspection'
    AND event_week = analysis_week           -- 파티션 프루닝
),
first_delivers AS (
  SELECT * FROM deliver_events WHERE deliver_seq = 1
)
```

> staging의 `event_week`는 `DATE_TRUNC('WEEK', action_at KST)` 파티션 키 → 주 단위 파티션 프루닝으로 스캔 최소화.

### 4.2 라벨링 착수 시점 (최초 start)

```sql
start_events AS (
  SELECT task_id, MIN(action_at) AS start_at
  FROM analytics.stg_task_transition_events
  WHERE from_state = 'waiting_labeling'
    AND to_state   = 'labeling'
    AND trigger    = 'start'
    AND task_id IN (SELECT task_id FROM first_delivers)
  GROUP BY task_id
)
```

### 4.3 납품 객체 수 (staging PIVOT)

```sql
obj AS (
  SELECT
    task_id,
    SUM(CASE WHEN table_name = 'gen2_lines'                     THEN object_count END) AS ld_lines,
    SUM(CASE WHEN table_name = 'gen2_line_points'                THEN object_count END) AS ld_line_points,
    SUM(CASE WHEN table_name = 'gen2_road_boundaries'             THEN object_count END) AS ld_road_boundaries,
    SUM(CASE WHEN table_name = 'gen2_road_boundary_points'       THEN object_count END) AS ld_road_boundary_points,
    SUM(CASE WHEN table_name = 'gen2_lanes'                      THEN object_count END) AS ld_lanes,
    SUM(CASE WHEN table_name = 'gen2_topologies'                  THEN object_count END) AS ld_topologies,
    SUM(CASE WHEN table_name = 'gen2_polywall_roadmark_objects' THEN object_count END) AS rmd_polywall_objects,
    SUM(CASE WHEN table_name = 'gen2_box_roadmark_objects'             THEN object_count END) AS rmd_bbox3d_objects,
    SUM(CASE WHEN table_name = 'gen2_dynamic_targets'           THEN object_count END) AS dynamic_targets,
    SUM(CASE WHEN table_name = 'gen2_static_targets'            THEN object_count END) AS static_targets
  FROM analytics.int_object_counts_by_task
  WHERE stage_key = 'inspection'
    AND task_id IN (SELECT task_id FROM first_delivers)
  GROUP BY task_id
)
```

> 10개 객체 테이블의 CDC dedup + COUNT는 stg_objects에 완료되어 있다. KPI SQL은 int_object_counts_by_task 경유로 PIVOT 결과만 참조.

### 4.4 투입 자원 (intermediate 직접 SELECT)

```sql
cmd AS (
  SELECT task_id, user_hour_slots, person_days
  FROM analytics.int_command_slots_by_task
  WHERE task_id IN (SELECT task_id FROM first_delivers)
)
```

> staging이 task_id별 사전 집계를 보유하므로 raw workspace_command 직접 파싱 불필요.

### 4.5 Task idle 차감 (Focus Drop 연계)

```sql
task_idle AS (
  SELECT task_id, SUM(idle_gap_duration_sec) AS task_total_idle_sec
  FROM analytics.focus_drop_task_idle_rollup
  WHERE role_scope = 'labeler'           -- Phase A/B 기본값, Phase C 전환 시 'all_roles'
  GROUP BY task_id
)
```

> 동일 Task가 여러 일자에 걸쳐 진행될 수 있으므로 `task_id` 기준 합산이 필수. `role_scope` 전환 조건은 §6 참조.

### 4.6 메타 조회 (raw 직접)

```sql
companies AS (
  SELECT `_id`, get_json_object(`_raw`, '$.name')    AS company_name
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__company`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
policies AS (
  SELECT `_id`, get_json_object(`_raw`, '$.feature') AS feature
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_annotation_policies`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
)
```

> company/policy 메타는 staging에 별도 존재하지 않으므로 raw 직접 참조 + CDC dedup. 전체 .sql 흐름과 최종 SELECT는 `.sql/mrt__production_volume_weekly.sql` 참조.

---

## 5. 집계 Dimension

| 축 | 소스 | 값 |
| --- | --- | --- |
| 업체 | `task.companyId → company.name` | CW, LTS, NexterSystems, StradVision, LTSMM |
| Feature | `task.policyId → policy.feature` | MV2_LD, MV2_OD, MV2_SOD, MV2_RMD, MV2_TSTLD |
| 기간 | `actionAt` (KST 변환 후) | 일 / 주 / 월 |
| 역할 | `role_group` (별도 생성 예정) | Labeler, Reviewer |

---

## 6. 제약사항 및 주의사항

1. **CDC 중복 제거**: staging은 적재 단계에서 dedup 완료. raw 메타(`company`, `gen2_annotation_policies`) 참조 시에만 `ROW_NUMBER` 패턴 필요
2. **`from_json` 스키마**: staging 적재 SQL 내부에서만 사용 (운영 KPI SQL은 staging 컬럼 직접 사용)
3. **object_id**: task 간 중복 가능 → staging은 `task_id × table_name × stage_key` grain으로 분리됨
4. **gen2_static_targets 다중 feature 공유**: OD static / SOD / TSTLD 객체가 동일 테이블에 저장되나, `task_id`가 단일 policyId(feature)에 귀속되므로 staging에서 PIVOT 후 feature별 분기 처리 (Q5.1 매핑 메모리 참조)
5. **재납품**: 동일 Task는 1건. `deliver_seq = 1` (최초 납품)으로 처리
6. **주 경계 귀속**: staging `event_week`는 `action_at`(deliver 또는 재납품) 기준. 재납품 시 해당 주에 귀속
7. **`role_group` 미생성**: Phase A/B에서 `focus_drop_task_idle_rollup.role_scope = 'labeler'` 사용. Phase C 전환 조건은 §6.1 참조
8. **KST 변환**: staging 적재 시점에 KST 변환 완료 (`event_week`, `event_date`). 운영 SQL에서 추가 변환 불필요
9. **staging 신선도**: 운영 KPI SQL 실행 전 모든 staging 테이블이 대상 주 데이터를 포함해야 함 (§10 절차 참조)

### 6.1 role_scope Phase 전환 조건

| Phase | `role_scope` 값 | 적용 시점 |
| --- | --- | --- |
| A/B | `labeler` | 기본값 — Focus Drop session_metrics에 `role_group` 컬럼 미존재 |
| C | `all_roles` | session_metrics에 role 차원 추가 + Reviewer command 데이터 적재 완료 후 전환 |

전환 시 변경 위치: `mrt__production_volume_weekly.sql`의 `task_idle` CTE → `WHERE role_scope = 'all_roles'`

---

## 7. 관련 문서

| 문서 | 내용 |
| --- | --- |
| `productivity_concept_design.md` | 본 스킬의 원본 설계 문서 |
| `stage_transition_analysis.md` | Stage 파이프라인 구조 및 전환 이력 |
| `operation_concept_design.md` | 운영 지표 (Stage별 효율, 소요시간) |
| `inspection-fpy_concept_design.md` | 검수 반려율 / FPY 설계 |
| `labeler_focus_drop_concept_design.md` | 라벨러 집중도 저하 탐지 |

---

## 8. Delta 테이블 스키마

### 8.1 `analytics.production_volume_weekly`

> 초기 생성 DDL: `.sql/mrt__ddl.sql` (`production_volume_weekly` 포함, `PARTITIONED BY (deliver_week_start)`)
> Wide-table 구조: feature 행으로 분리, 비해당 feature 컬럼은 NULL

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `deliver_week_start` | DATE | 해당 주 월요일 (KST 기준) — 파티션 키 |
| `company_name` | STRING | 업체명 |
| `feature` | STRING | Feature (MV2_LD, MV2_OD, MV2_SOD, MV2_RMD, MV2_TSTLD) |
| `delivered_task_count` | BIGINT | 주당 납품 Task 수 (재납품 중복 제거) |
| `ld_lines` | BIGINT | gen2_lines (MV2_LD 전용, 타 feature NULL) |
| `ld_line_points` | BIGINT | gen2_line_points — 보조 지표 |
| `ld_road_boundaries` | BIGINT | gen2_road_boundaries |
| `ld_road_boundary_points` | BIGINT | gen2_road_boundary_points — 보조 지표 |
| `ld_lanes` | BIGINT | gen2_lanes |
| `ld_topologies` | BIGINT | gen2_topologies |
| `rmd_polywall_objects` | BIGINT | gen2_polywall_roadmark_objects (MV2_RMD 전용) |
| `rmd_bbox3d_objects` | BIGINT | gen2_box_roadmark_objects |
| `dynamic_targets` | BIGINT | gen2_dynamic_targets (MV2_OD 전용) |
| `static_targets` | BIGINT | gen2_static_targets (MV2_OD / SOD / TSTLD 공유) |
| `delivered_object_count` | BIGINT | primary objects 합산 (LD: lines+rb+lanes+topo, RMD: pw+bb, OD: dyn+st, SOD/TSTLD: st) |
| `delivered_point_count` | BIGINT | LD points 합산 (line_points + rb_points), 타 feature NULL |
| `avg_points_per_object` | DOUBLE | LD 복잡도 proxy = delivered_point_count / delivered_object_count |
| `user_hour_slots` | BIGINT | 투입 인시 (납품 Task 실발생 커맨드, Labeler+Reviewer 합산) |
| `person_days` | BIGINT | 투입 인일 (납품 Task 실발생 커맨드, Labeler+Reviewer 합산) |
| `objects_per_hour` | DOUBLE | 시간당 납품 primary 객체 수 |
| `tasks_per_person_day` | DOUBLE | 인일당 납품 Task 수 |
| `objects_per_person_day` | DOUBLE | 인일당 납품 primary 객체 수 (1일 capa) |
| `avg_hours_per_task` | DOUBLE | Task 평균 소요시간 gross (착수→납품, 시간) |
| `median_hours_per_task` | DOUBLE | Task 소요시간 중앙값 gross (시간) |
| `avg_net_hours_per_task` | DOUBLE | Task 평균 순소요시간 (idle 차감, 시간) |
| `median_net_hours_per_task` | DOUBLE | Task 순소요시간 중앙값 (idle 차감, 시간) |

---

## 9. 다음 단계

| 산출물 | 경로 | 상태 |
| --- | --- | --- |
| Staging DDL | `.sql/stg__ddl.sql` | ✅ 완료 |
| Intermediate DDL | `.sql/int__ddl.sql` | ✅ 완료 |
| Dimension DDL | `.sql/dim__ddl.sql` | ✅ 완료 |
| Marts DDL | `.sql/mrt__ddl.sql` | ✅ 완료 |
| Staging SQL (task events) | `.sql/stg__task_transition_events.sql` | ✅ 완료 |
| Intermediate SQL (object counts) | `.sql/int__object_counts_by_task.sql` | ✅ 완료 |
| Intermediate SQL (cmd slots) | `.sql/int__command_slots_by_task.sql` | ✅ 완료 |
| 주별 집계 SQL | `.sql/mrt__production_volume_weekly.sql` | ✅ 완료 |
| 역할 매핑 | `.sql/dim_role_group.sql` | ⏸ 보류 |
| STEP 8 이상탐지 연계 | Anomaly Detection 문서 업데이트 | 📋 예정 |

---

## 10. Initialize / Bootstrap 절차

테이블 부재 상태에서 시작하는 신규 배포 흐름. staging 3종 + KPI 1종 + Focus Drop 의존성.

### 10.1 Phase 0: 인프라 준비 (Day 0)

1. **DDL 적용** (레이어별):
   - `.sql/stg__ddl.sql` 실행 → `stg_task_transition_events` 생성
   - `.sql/int__ddl.sql` 실행 → `int_object_counts_by_task` / `int_command_slots_by_task` / focus_drop 중간 테이블 생성
   - `.sql/dim__ddl.sql` 실행 → `dim_companies` / `dim_policies` / `dim_assignments` 생성
   - `.sql/mrt__ddl.sql` 실행 → `production_volume_weekly` / focus_drop KPI 테이블 생성
2. **존재 확인**:
   ```sql
   SHOW TABLES IN analytics LIKE 'stg_%';
   SHOW TABLES IN analytics LIKE 'int_%';
   SHOW TABLES IN analytics LIKE 'dim_%';
   SHOW TABLES IN analytics LIKE 'production_volume_%';
   SHOW TABLES IN analytics LIKE 'focus_drop_%';
   ```

### 10.2 Phase A: Staging 초기 적재 (Day 1)

세 staging SQL을 순차 실행 (위젯 미설정 시 전체 기간 적재).

1. `stg__task_transition_events.sql` 실행 → transitionHistory 전체 flatten
2. `stg__objects.sql` 실행 → 10개 객체 테이블 CDC dedup (stg_objects 적재, per-table REPLACE)
3. `int__object_counts_by_task.sql` 실행 → stg_objects → task별 PIVOT 집계
4. `int__command_slots_by_task.sql` 실행 → workspace_command task별 인시/인일 집계
4. 적재 검증:
   ```sql
   SELECT
     'transition' AS layer, COUNT(*) AS rows, COUNT(DISTINCT task_id) AS distinct_tasks
   FROM analytics.stg_task_transition_events
   UNION ALL SELECT 'object_counts', COUNT(*), COUNT(DISTINCT task_id) FROM analytics.int_object_counts_by_task
   UNION ALL SELECT 'cmd_slots',     COUNT(*), COUNT(DISTINCT task_id) FROM analytics.int_command_slots_by_task;
   ```

### 10.3 Phase B: Focus Drop idle rollup 적재 (Day 1)

Focus Drop 파이프라인이 미적재 상태이면 `task_idle` LEFT JOIN 결과가 NULL → `net_hours = gross_hours`로 산출됨 (정상 동작).

- 초기 배포 시 `production_volume_weekly`의 `avg_net_hours_per_task`/`median_net_hours_per_task` 컬럼은 idle 미적용 상태(= gross 값)로 채워진다.
- Focus Drop SKILL.md §12.4 Phase A/B 절차 완료 후 다음 주 배치부터 idle 차감 자동 반영.

### 10.4 Phase C: KPI 초기 산출 (Day 1)

```sql
-- mrt__production_volume_weekly.sql 실행
-- analysis_week 미입력 시 전 주 자동 산출 (DEFAULT DATE_TRUNC('WEEK', CURRENT_DATE() - INTERVAL 7 DAYS))
-- 과거 주 백필 시: SET VAR analysis_week = DATE '2026-05-05';
```

- 백필 시 주 단위로 반복 실행 (REPLACE WHERE deliver_week_start = analysis_week)
- 검증:
  ```sql
  SELECT deliver_week_start, COUNT(*) AS rows, SUM(delivered_task_count) AS total_tasks
  FROM analytics.production_volume_weekly
  GROUP BY deliver_week_start
  ORDER BY deliver_week_start DESC;
  ```

### 10.5 Phase D: Steady-state (Day 2+)

| 레이어 | 스케줄 | 갱신 전략 |
| --- | --- | --- |
| staging (stg__task_transition_events 등 5종) | 매일 04:00 UTC | 일 OVERWRITE / per-table REPLACE |
| int + dim (int 2종 + dim 3종, 병렬) | 매일 04:00 UTC | 일 OVERWRITE |
| Focus Drop session/task/user | 매일 04:00 UTC | analysis_date REPLACE WHERE |
| production_volume_weekly | 매주 월요일 05:00 UTC | deliver_week_start REPLACE WHERE (전 주) |

> staging/intermediate 일 배치가 완료된 다음 주 월요일에 KPI 주 배치가 안전하게 실행된다.

### 10.6 의존성 다이어그램

```
[Phase 0] stg__ddl.sql                ─┐
          int__ddl.sql                 ─┤
          dim__ddl.sql                 ─┤
          mrt__ddl.sql                 ─┘
                                          ↓
[Phase A] stg__task_transition_events.sql      ─┐
          stg__objects.sql                     ─┤  (stg 백필 1회)
          int__object_counts_by_task.sql       ─┤  (int 집계)
          int__command_slots_by_task.sql       ─┤
          dim__companies/policies/assignments  ─┘  (dim 초기 적재)
                                          ↓
[Phase B] focus_drop pipeline (선택; 미적재 시 idle=0)
                                          ↓
[Phase C] mrt__production_volume_weekly.sql  (analysis_week 지정 / 전 주 자동)
                                          ↓
[Phase D] 일 staging + 일 Focus Drop + 주 KPI 정기 스케줄
```
