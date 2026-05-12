# Nova Log Analytics — KPI Metric Policy

**문서 상태**: Released (v1.2)  
**작성일**: 2026-05-12  
**적용 범위**: `projects/nova_log_analytics` 내 전 KPI 영역  
**상위 문서**: `[Performance] Labeling KPI Definition - Productivity, Quality ,Operational Efficiency.md`  
**관련 문서**:
- 설계 배경 → 각 도메인 `*_concept_design.md` / `*_metric_design.md`
- 운영 SQL → `.assistant/skills/kpi _metrics/<domain>/SKILL.md` · `.sql/<domain>__*.sql`

---

## 구현 현황 요약

| 카테고리 | 우선순위 | 지표 | 구현 |
|----------|----------|------|------|
| 생산성 | P0 | 생산량 (납품 Task 수 · 납품 객체 수) | ✅ |
| 생산성 | P0 | 생산성 (시간당 Object 수 · 1인 1일 납품 Task 수) | ✅ |
| 생산성 | P1 | 신규 생성 vs ALT 비율 (ALT) | ⬜ |
| 생산성 | P1 | 작업 집중도 / Idle (Focus Drop) | ✅ |
| 검수 품질 | P0 | 검수 반려율 | ✅ |
| 검수 품질 | P0 | First Pass Yield (FPY) | ✅ |
| 검수 품질 | P1 | Tracking ID당 평균 커버 프레임 수 | ⬜ |
| 검수 품질 | P2 | 삭제 후 재생성 패턴 (ALT) | ⬜ |
| 검수 품질 | P3 | Merge / Split 발생 빈도 (ALT) | ⬜ |
| 운영 효율성 | P0 | Stage별 Cycle Time (파이프라인 합산) | ✅ |
| 운영 효율성 | P1 | Stage별 소요 시간 세분화 (Stage Duration) | ⬜ |
| 운영 효율성 | P1 | Stage별 객체 증감 (Object Delta) | ⬜ |
| 운영 효율성 | P1 | Review 반려율 | ⬜ |
| 운영 효율성 | P1 | Undo/Redo 비율 · Frame/Channel 이동 패턴 | ⬜ |
> ALT : ALT로 생성된 객체의 정보가 추가되는대로 구현 착수 예정.

---

## 1. 정책 원칙

1. **단일 산출식 원칙**: 동일 지표의 산출식은 이 문서에만 정의한다. SQL 구현은 이 문서의 정의를 따른다.
2. **지표 추가·변경 시 버전 갱신**: §7 버전 히스토리를 업데이트하고, 관련 SQL·SKILL.md에 동기화한다.
3. **분모 0 처리**: 모든 비율 지표는 분모 = 0인 경우 `NULL`로 산출한다 (`NULLIF(분모, 0)` 적용).
4. **시간대**: 모든 날짜·시각 기준은 KST(UTC+9). `CONVERT_TIMEZONE('UTC', 'Asia/Seoul', col)` 적용.
5. **소수점**: 비율·퍼센트 지표는 소수점 2자리(`ROUND(…, 2)`), 시간 지표는 소수점 2자리 hours.

---

## 2. 생산성 지표 (Productivity Metrics)

> **목적**: 협력업체별 작업 속도·작업량을 정량적으로 비교하고, 생산성 기준선을 수립한다.

### 2.1 생산량 (Production Volume) [P0 · ✅ 구현]

협력업체가 납품한 Task 수와 객체 수를 측정하는 결과물 기준 지표.

**생산량 정의**:

| 지표 | 정의 | 기준 이벤트 |
|------|------|------------|
| `delivered_task_count` | 납품 Task 수 | `from_state='waiting_submit' AND to_state='inspection'` |
| `delivered_object_count` | 납품 Task의 primary 객체 수 | 납품 Task의 `stageKey='inspection'` 스냅샷 |

**Feature별 primary 객체 테이블**:

| Feature | primary objects |
|---------|----------------|
| MV2_LD | `gen2_lines`, `gen2_road_boundary`, `gen2_lane`, `gen2_topology` |
| MV2_RMD | `gen2_polywall_roadmark_objects`, `gen2_bbox3d_object` |
| MV2_OD | `gen2_dynamic_targets` + `gen2_static_targets` |
| MV2_SOD | `gen2_static_targets` |
| MV2_TSTLD | `gen2_static_targets` |

> LD points(`gen2_line_point`, `gen2_road_boundary_point`)는 `delivered_point_count`로 별도 집계. primary objects에 미포함.  
> 재납품 중복 처리: 동일 Task는 납품 1건으로 카운트. 재납품 월 귀속은 최초 착수 월 기준 (v2 이관 예정).

**운영 SQL**: `production_volume__weekly.sql`

---

### 2.2 생산성 (Productivity Rate) [P0 · ✅ 구현]

생산량 ÷ 투입 자원. 협력업체별 실 투입 시간 대비 산출 효율을 측정하는 1차 기준 지표.

**투입 자원 산출** (Active Time 기반 — 단순 접속 시간 아님):

| 지표 | 산출식 | 범위 |
|------|--------|------|
| `user_hour_slots` | `COUNT(DISTINCT CONCAT(user_name, '-', event_hour))` | Labeler + Reviewer 합산 |
| `person_days` | `COUNT(DISTINCT CONCAT(user_name, '-', event_date))` | Labeler + Reviewer 합산 |

> 커맨드 발생 구간 기준 산출 — 커맨드 수는 생산량 산출에 사용하지 않음.

**생산성 Metric**:

| 지표 | 산출식 | 단위 |
|------|--------|------|
| `obj_per_person_hour` | `delivered_object_count / NULLIF(user_hour_slots, 0)` | obj/person-hour |
| `task_per_person_day` | `delivered_task_count / NULLIF(person_days, 0)` | tasks/person-day |

> 집계 Dimension: 업체 × Feature × 주차 / 선행 문서: `productivity_concept_design.md`  
> **운영 SQL**: `production_volume__weekly.sql`

### 2.3 신규 생성 vs ALT 사용 비율 [P1 · ⬜ 미구현]

신규 Dynamic Cuboid 생성 비율과 ALT/Interpolation 결과물 재활용 비율을 비교. 자동화 도구 활용도 측정. 처리량·품질 지표와 교차 분석 시 유의미.

| 지표 | 정의 | 비고 |
|------|------|------|
| `new_creation_ratio` | 신규 생성 객체 수 / 전체 객체 수 | Command Log 신규 생성 커맨드 기반 |
| `alt_usage_ratio` | ALT/Interpolation 사용 객체 수 / 전체 객체 수 | `1 - new_creation_ratio` |

> 산출식 및 커맨드 분류 기준은 구현 착수 시 확정.

### 2.4 작업 집중도 / Idle (Focus Drop) [P1 · ✅ 구현]

세션 내 Active vs Idle 비율, 연속 작업 지속 시간 분석. 비효율 세션 패턴 식별. 내부 분석용 지표.

> 선행 문서: `labeler_focus_drop_concept_design.md` · `labeler_focus_drop_metric_design.md`

**gap 구간 정의 (1차 percentile 기반)**:

| 구간 | 조건 | 비고 |
|------|------|------|
| normal | `diff_sec ≤ gap_p75` | 정상 공백 |
| observation | `gap_p75 < diff_sec ≤ gap_p90` | 분석용 보조 — 정식 판정 제외 |
| light | `gap_p90 < diff_sec ≤ gap_p95` | 정식 저하 판정 레벨 |
| heavy | `gap_p95 < diff_sec < 180` | 정식 저하 판정 레벨 |
| idle | `diff_sec ≥ 180` | 고정 임계값 3분, 작업 이탈 |

- `gap_p75` · `gap_p90` · `gap_p95`: `focus_drop_gap_thresholds` 최신 버전 참조
- idle 경계 `180s`는 고정값, percentile 갱신과 무관

**세션 단위 메트릭**:

| 메트릭 | 산출식 | 역할 |
|--------|--------|------|
| `light_gap_count` | 세션 내 light 구간 gap 수 | 핵심 판정 |
| `heavy_gap_count` | 세션 내 heavy 구간 gap 수 | 핵심 판정 |
| `idle_gap_count` | 세션 내 idle 구간 gap 수 | 핵심 판정 |
| `light_gap_ratio` | `light_gap_count / total_gaps` | 보조 보정 |
| `heavy_gap_ratio` | `heavy_gap_count / total_gaps` | 보조 보정 |
| `idle_gap_ratio` | `idle_gap_count / total_gaps` | 보조 보정 |
| `idle_gap_duration_sec` | 세션 내 idle gap 지속 초수 합산 | 생산성 연계 |
| `observation_gap_count` | 세션 내 observation 구간 gap 수 | 분석용 |

**세션 판정 기준 (2차 percentile 기반)**:

| 판정 레벨 | 주판정 | 보조 조건 (선택) |
|-----------|--------|-----------------|
| light 세션 | `light_gap_count > session_light_count_p90` | `AND light_gap_ratio > session_light_ratio_p90 AND light_gap_count > 0` |
| heavy 세션 | `heavy_gap_count > session_heavy_count_p95` | `AND heavy_gap_ratio > session_heavy_ratio_p95 AND heavy_gap_count > 0` |
| idle 세션 | `idle_gap_count > session_idle_count_p99` | `AND idle_gap_ratio > session_idle_ratio_p99 AND idle_gap_count > 0` |

- 2차 percentile 소스: `focus_drop_session_thresholds` 최신 버전
- zero-inflation 보정: count 기반 판정에 항상 `해당 count > 0` 동반

**유저 일 단위 메트릭**:

| 메트릭 | 산출식 | 역할 |
|--------|--------|------|
| `light_session_count` | 해당 일 light 세션 수 | 핵심 반복성 |
| `heavy_session_count` | 해당 일 heavy 세션 수 | 핵심 반복성 |
| `idle_gap_total` | 해당 일 idle gap 발생 횟수 합산 | 핵심 반복성 |

**유저 일 판정 기준 (2차 percentile 기반)**:

| 판정 레벨 | 주판정 |
|-----------|--------|
| light 후보 | `light_session_count > user_light_session_count_p90 AND light_session_count > 0` |
| heavy 후보 | `heavy_session_count > user_heavy_session_count_p95 AND heavy_session_count > 0` |
| idle 후보 | `idle_gap_total > user_idle_gap_total_p99 AND idle_gap_total > 0` |

- 2차 percentile 소스: `focus_drop_user_thresholds` 최신 버전

---

## 3. 검수 품질 지표 (Quality Metrics)

> **목적**: 작업 결과물의 품질 수준을 다각도로 측정하고, 반복 오류를 조기에 식별하여 협력업체 피드백에 활용한다.

> 선행 문서: `inspection-fpy_concept_design.md`

### 3.1 검수 반려율 + FPY [P0 · ✅ 구현]

| 지표 | 정의 | 산출식 |
|------|------|--------|
| `검수 반려율 (%)` | 대상 Task 중 inspection reject 1회 이상 Task 비율 | `rejected_count / NULLIF(total_inspected, 0) × 100` |
| `First Pass Yield — FPY (%)` | 최초 검수 통과 Task 비율 | `100 − 검수 반려율 (%)` |
| `다중 반려 Task` | 동일 Task 내 inspection reject 2회 이상 발생 건 | `inspection_reject_count ≥ 2` |

**모집단 정의 (Delivered Tasks)**:

| 항목 | 조건 |
|------|------|
| 대상 필터 | `deliveryId IS NOT NULL` — inspection 단계 진입 task와 동치 |
| 월 그룹핑 기준 | `updatedAt`의 `YY-MM` (KST) |
| 중복 제거 | `_id` 기준 `_ingested_at DESC` ROW_NUMBER 1번 (CDC dedup) |
| 삭제 제외 | `_is_deleted = false` |

**Reject 이벤트 필터** (`stg_task_transition_events` 기준):

| 필드 | 조건 |
|------|------|
| `from_state` | `= 'inspection'` |
| `trigger` | `= 'reject'` |

> `from_state = 'review'` reject는 대상 제외.

### 3.2 Tracking ID당 평균 커버 프레임 수 [P1 · ⬜ 미구현]

하나의 Tracking ID가 실제 객체 존재 구간을 얼마나 커버하는지 측정. GT/기준 데이터와의 Sync 필요 — 사후 분석(Post-hoc) 지표.

| 지표 | 정의 |
|------|------|
| `avg_cover_frame_per_id` | Tracking ID당 실제 커버 프레임 수 평균 |

> 산출식 및 GT 데이터 소스는 구현 착수 시 확정.

### 3.3 삭제 후 재생성 패턴 [P2 · ⬜ 미구현]

단순 수정이 아닌 삭제→동일 객체 재생성 케이스 식별. 재작업 비용과 근본 품질 이슈 간접 확인.

| 지표 | 정의 |
|------|------|
| `delete_recreate_count` | 삭제 후 동일 위치·속성 객체 재생성 발생 건수 |
| `delete_recreate_ratio` | 전체 편집 이벤트 대비 삭제→재생성 비율 |

> Command Log 커맨드 분류 기준은 구현 착수 시 확정.

### 3.4 Merge / Split 발생 빈도 [P3 · ⬜ 미구현]

Tracking ID의 잘못된 연결·단절로 인한 사후 수정 빈도 측정. Stage별 분리 집계 시 ALT 모델 문제 vs Labeling 품질 문제 구분 가능.

| 지표 | 정의 |
|------|------|
| `merge_count` | Tracking ID 병합 발생 건수 (Stage별) |
| `split_count` | Tracking ID 분리 발생 건수 (Stage별) |

> Command Log 커맨드 분류 기준은 구현 착수 시 확정.

---

## 4. 운영 효율성 지표 (Operational Efficiency Metrics)

> **목적**: 전체 스테이지의 흐름을 모니터링하고, 병목 구간을 식별하여 운영 최적화를 위한 분석 인사이트를 도출한다.

### 4.1 Stage별 Cycle Time [P0 · ✅ 구현]

라벨링 → 검수 → 제출 → 검사 → 최종 QA 등 각 단계별 소요 시간 측정. 전체 프로세스 병목 구간 식별.

**Task 소요시간 지표**:

| 지표 | 산출식 | 단위 |
|------|--------|------|
| `gross_task_hours` | `(deliver_actionAt − start_actionAt) / 3600.0` | hours/task |
| `net_task_hours` | `GREATEST(gross_task_sec − task_total_idle_sec, 0) / 3600.0` | hours/task |

- `task_total_idle_sec` 소스: `focus_drop_task_idle_rollup`
  - Phase A/B: `role_scope='labeler'`
  - Phase C: `role_scope='all_roles'`
- Focus Drop 미적재 Task: `COALESCE(task_total_idle_sec, 0)` → net = gross

**라벨링 착수 이벤트 정의** (Task 소요시간 기준점):

| 항목 | 조건 |
|------|------|
| 필터 | `from_state='waiting_labeling' AND to_state='labeling' AND trigger='start'` |
| reassign 제외 | `trigger='reassign'` 이벤트는 착수 기준 제외 |
| 복수 착수 | 재작업으로 복수 진입 시 **최초 시점** 기준 |
| 미존재 Task | 집계 제외 |

**집계 Dimension**:

| 축 | 소스 | 값 |
|----|------|----|
| 업체 | `task.companyId → company.name` | CW, LTS, NexterSystems, StradVision, LTSMM |
| Feature | `task.policyId → policy.feature` | MV2_LD, MV2_OD, MV2_SOD, MV2_RMD, MV2_TSTLD |
| 기간 | `transitionHistory.actionAt` | 일 / 주 / 월 |
| Stage | `stageAssignees.stageKey` | labeling, review, inspection, final_qa |

### 4.2 Stage별 소요 시간 세분화 (Stage Duration) [P1 · ⬜ 미구현]

Labeling / Review / Inspection / Final QA 각 단계의 소요시간을 개별 측정하여 병목 단계를 특정. §4.1 Cycle Time(파이프라인 합산)을 Stage 단위로 분해한 지표.

| 지표 | 산출식 | 단위 |
|------|--------|------|
| `stage_duration_hours` | `(stage_end_at − stage_start_at) / 3600.0` (pass별 합산) | hours/task |
| `p50_stage_duration_hours` | `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_hours)` | hours |
| `p90_stage_duration_hours` | `PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY duration_hours)` | hours |
| `rework_pass_count` | Reject 재작업 횟수 (`pass_num ≥ 2`) | 횟수/task |

> 집계 Dimension: 업체 × Feature × Stage × 주차  
> 비즈니스 규칙: Reassign(`trigger='reassign'`)은 새 pass가 아님. 종료 이벤트 누락 시 `CURRENT_TIMESTAMP()` 대체.  
> **운영 SQL**: `ops__stage_duration.sql` (미생성) / 선행 문서: `operation_concept_design.md`

### 4.3 Stage별 객체 증감 (Object Delta) [P1 · ⬜ 미구현]

Review·Inspection 단계에서 추가·삭제된 객체 수를 Stage 전환 단위로 정량화. 수정 강도와 Stage Duration을 교차 분석하여 고수정 업체·Feature 조합 파악.

| 지표 | 산출식 | 단위 |
|------|--------|------|
| `delta_count` | `to_stage_count − from_stage_count` | 개/task |
| `delta_ratio` | `delta_count / NULLIF(from_stage_count, 0) × 100` | % |
| `avg_delta_count` | `AVG(delta_count)` by 업체 × Feature × Stage 전환 | 개/task |
| `avg_abs_delta_ratio` | `AVG(ABS(delta_ratio))` — 수정 강도 (방향 무관) | % |

> 전환 쌍: Labeling→Review / Review→Inspection / Inspection→Final QA / Labeling→Final QA(전체 순증)  
> 소스: `stg_object_counts_by_task` PIVOT by `stage_key` / 양수(+): 객체 추가, 음수(−): 객체 삭제  
> **운영 SQL**: `ops__object_delta.sql` (미생성) / 선행 문서: `operation_concept_design.md`

### 4.4 Review 반려율 [P1 · ⬜ 미구현]

Review 단계 반려 건수 / 리뷰 완료 건수. §3.1 Inspection 반려율과 별도 집계. Stage Duration 증가의 주요 원인 분석에 활용.

| 지표 | 산출식 |
|------|--------|
| `review_reject_rate_pct` | `COUNT(from_state='review' AND trigger='reject') / NULLIF(COUNT(review 완료), 0) × 100` |

> 소스: `stg_task_transition_events` / `from_state='review' AND to_state IN ('waiting_labeling')` 기준  
> **운영 SQL**: `ops__stage_duration.sql` (미생성)

### 4.5 Undo/Redo 비율 · Frame/Channel 이동 패턴 [P1 · ⬜ 미구현]

Tool UX 및 세부 작업 흐름 분석. Scene 내 작업 흐름 분석이 구체화된 이후 보조 지표로 단계적 도입.

| 지표 | 정의 |
|------|------|
| `undo_redo_ratio` | 전체 커맨드 대비 Undo/Redo 커맨드 비율 |
| `frame_channel_move_count` | 세션 내 Frame/Channel 이동 커맨드 발생 건수 |

> Command Log 커맨드 분류 기준은 `.assistant/skills/common/gen2_command_definitions.md` 참조. 산출식은 구현 착수 시 확정.

---

## 5. 지표 변경 절차

1. 이 문서(§2–4)에서 산출식·정의 수정
2. 관련 도메인 `*_concept_design.md` 또는 `*_metric_design.md`에 변경 사유 기록
3. `SKILL.md` SQL 템플릿 및 `.sql/<domain>__*.sql` 동기화
4. §6 구현 현황 요약 업데이트
5. §7 버전 히스토리 항목 추가
6. DDL 컬럼 변경이 수반되는 경우 `*__ddl.sql` 갱신 후 `ALTER TABLE` 또는 재생성

---

## 6. 구현 로드맵

| 우선순위 | 지표 | 선행 조건 |
|----------|------|-----------|
| P1 — Stage별 소요 시간 세분화 | `stg_task_transition_events` 적재 완료 / `ops__ddl.sql` 실행 |
| P1 — Stage별 객체 증감 (Object Delta) | `stg_object_counts_by_task` 적재 완료 / `ops__ddl.sql` 실행 |
| P1 — Review 반려율 | `stg_task_transition_events` 적재 완료 |
| P1 — 신규 생성 vs ALT 사용 비율 | Command Log 커맨드 분류 체계 확정 (`gen2_command_definitions.md`) |
| P1 — Undo/Redo 비율·이동 패턴 | Command Log 커맨드 분류 체계 확정 |
| P1 — Tracking ID 커버 프레임 수 | GT/기준 데이터 소스 확정 |
| P2 — 삭제 후 재생성 패턴 | Command Log 커맨드 분류 체계 확정 |
| P3 — Merge/Split 발생 빈도 | Command Log 커맨드 분류 체계 확정 |

---

## 7. 버전 히스토리

| 버전 | 일자 | 주요 내용 |
|------|------|-----------|
| v1.0 | 2026-05-12 | Focus Drop · Inspection Quality · Labeling Productivity 전 KPI 메트릭 정의 통합 초판 (도메인 기반 구조) |
| v1.1 | 2026-05-12 | 상위 문서([Performance] Labeling KPI Definition) 3대 카테고리 구조로 재편 — 생산성 / 검수 품질 / 운영 효율성 / 미구현 지표 우선순위 포함 |
| v1.2 | 2026-05-12 | §2.1 처리량 → §2.1 생산량 / §2.2 생산성으로 분리 / Focus Drop 우선순위 P2 → P1 / §4에 Stage Duration 세분화·Object Delta·Review 반려율(P1 ⬜) 추가 / 구현 현황 요약·로드맵 갱신 |
