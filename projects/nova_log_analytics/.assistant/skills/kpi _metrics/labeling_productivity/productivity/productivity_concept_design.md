# Production Volume & Productivity — Metric Design

**문서 상태**: Released (v1.3)  
**작성일**: 2026-05-11  
**적용 범위**: `projects/nova_log_analytics` — MV2_LD, MV2_OD, MV2_SOD, MV2_RMD, MV2_TSTLD  
**선행 문서**: `stage_transition_analysis.md`, `inspection-fpy_concept_design.md`, `labeler_focus_drop_concept_design.md`

---

## 1. 개요

Labelit Gen2 작업 파이프라인에서 **생산량**, **생산성**을 정량 측정하는 Metric 체계를 정의한다.

운영 지표(Stage별 산출물 변화·소요 시간)와 Stage 진행 현황 대시보드는 별도 문서로 관리한다:
- 운영 지표 → `operation_concept_design.md`
- Stage 진행 현황 → `stage_progress_dashboard_design.md`

> **Stage 파이프라인 구조 및 전환 이력**: `stage_transition_analysis.md` 참조  
> 실제 작업 Stage (stageAssignees.stageKey): `labeling` · `review` · `inspection` · `final_qa`

---

## 2. 설계 원칙: 데이터 소스 × 측정 목적 분리

| 데이터 소스 | 테이블 | 성격 | 측정 목적 |
|---|---|---|---|
| Stage별 객체 테이블 | `gen2_lines`, `gen2_dynamic_targets`, `gen2_polywall_roadmark_objects` 등 | 결과물 스냅샷 (outcome) | **생산량** — 객체 수 |
| TransitionHistory | `gen2_tasks._raw.transitionHistory` | Stage 전환 이력 | **생산량 기준 시점** |
| Workspace Command Log | `workspace_command` | 행위 로그 (process) | **투입 시간 추정** |

> **핵심 원칙**: Command Log의 커맨드 수는 객체 생산량 산출에 사용하지 않는다. 커맨드는 과정이며, 결과물은 객체 테이블의 스냅샷이다.

---

## 3. 생산량 (Production Volume)

생산량은 업체가 제출한 Task 기준으로 측정하며, Task 건수와 해당 Task의 객체 수 두 가지로 구성한다.

### 3.1 Task 기준 생산량

납품은 리뷰어가 검수팀에 Task를 전달하는 시점(`waiting_submit → inspection`)을 기준으로 한다.

| 항목 | 내용 |
|---|---|
| **필터** | `fromState='waiting_submit' AND toState='inspection'` |
| **소스** | transitionHistory |
| **집계 기준 시점** | `actionAt` |
| **집계 축** | 업체 × Feature × 기간(일/주/월) |

> 검수 반려 후 재납품된 경우에도 동일 Task는 **하나의 납품 건**으로 카운트한다. 단, 재납품 시점(`actionAt`)이 최초 작업 착수 월과 다를 경우 집계 월 귀속 로직을 별도 정의한다.

### 3.2 객체 기준 생산량

업체가 제출한 Task에 포함된 객체 수를 측정한다. 납품 시점(`waiting_submit → inspection` 전환)과 동일한 Task의 객체 테이블 `stageKey='inspection'` 스냅샷을 사용한다. `waiting_submit` 상태에서 객체 변경이 없으므로 리뷰어가 완료한 산출물 수와 동일하다.

| Metric | 산출 로직 | 소스 |
|---|---|---|
| 납품 Task 객체 수 | 납품 Task(`waiting_submit → inspection` 전환 taskId)의 `stageKey='inspection'` 객체 COUNT | Feature별 객체 테이블 |

**조인 키**: transitionHistory의 납품 전환 이벤트 `taskId` → 객체 테이블 `taskId` (`stageKey='inspection'`)

**집계 축**: 업체 × Feature × 기간(일/주/월)

**Feature별 객체 테이블 매핑**:

| Feature | primary objects (생산량 산출 기준) | 보조 지표 |
|---|---|---|
| MV2_LD | `gen2_lines`, `gen2_road_boundaries`, `gen2_lanes`, `gen2_topologies` | `gen2_line_points`, `gen2_road_boundary_points` (복잡도 proxy) |
| MV2_RMD | `gen2_polywall_roadmark_objects`, `gen2_box_roadmark_objects` | — |
| MV2_OD | `gen2_dynamic_targets` + `gen2_static_targets` | — |
| MV2_SOD | `gen2_static_targets` | — |
| MV2_TSTLD | `gen2_static_targets` | — |

> `gen2_static_targets`는 OD·SOD·TSTLD가 공유하나, `task_id`가 단일 policyId(feature)에 귀속되므로 task_id 필터만으로 feature 간 분리 보장.
> LD points는 lines/road_boundary에 종속된 보조 데이터. `delivered_object_count`에는 포함하지 않고, `delivered_point_count`로 별도 집계.


---

## 4. 생산성 (Productivity)

**정의**: 생산량 ÷ 투입 자원. 투입 자원(시간)은 Command Log 기반으로 추정한다.

**측정 목적**: 업체 납품 대비 총 투입 효율. Stage별 개별 효율 비교는 운영 지표(`operation_concept_design.md`)에서 후속 정의한다.

| Metric | 분자 소스 | 분모 소스 | 단위 |
|---|---|---|---|
| 시간당 객체 수 | 객체 생산량 (`stageKey='inspection'`) | `user_hour_slots` (Command Log, Labeler + Reviewer 합산) | obj/person-hour |
| 1인 1일 납품 Task 수 | 납품 Task 수 (`waiting_submit → inspection`) | `person-days` (Command Log, Labeler + Reviewer 합산) | tasks/person-day |
| Task 소요시간 gross | — | 납품 `actionAt` − 라벨링 착수 `actionAt` | hours/task |
| Task 순소요시간 net | — | gross − `task_total_idle_sec` (Focus Drop idle 차감) | hours/task |

> `task_total_idle_sec` 소스: `analytics.focus_drop_task_idle_rollup` (`role_scope='labeler'`). Focus Drop 파이프라인 미적재 Task는 `COALESCE(0)` → net = gross. Phase C 전환 시 `role_scope='all_roles'`로 변경.

**투입 자원 산출 로직**:

| 지표 | 산출식 | 비고 |
|---|---|---|
| `user_hour_slots` | `COUNT(DISTINCT CONCAT(user_name, '-', event_hour))` | 실 투입 인시 근사치, **Labeler + Reviewer 합산** |
| `person-days` | `COUNT(DISTINCT CONCAT(user_name, '-', event_date))` | 실 투입 인일 근사치, **Labeler + Reviewer 합산** |

**라벨링 착수 이벤트 정의** (Task 평균 소요시간 분모):

| 항목 | 내용 |
|---|---|
| **필터** | `fromState='waiting_labeling' AND toState='labeling' AND trigger='start'` |
| **소스** | transitionHistory |
| **의미** | 라벨러가 Task를 최초 수령하여 작업을 시작한 시점 |

> `labeling → labeling (trigger='reassign')`은 담당자 재배정이므로 착수 시점에서 제외한다.

> **edge case**: (1) 라벨링 착수 이벤트가 없는 Task는 집계 제외. (2) reject 후 재작업으로 `waiting_labeling → labeling` 구간이 복수인 경우 **최초 진입 시점** 기준.

---

## 5. 집계 Dimension

| 축 | 소스 | 값 |
|---|---|---|
| 업체 | `task.companyId → company.name` | CW, LTS, NexterSystems, StradVision, LTSMM |
| Feature | `task.policyId → policy.feature` | MV2_LD, MV2_OD, MV2_SOD, MV2_RMD, MV2_TSTLD |
| 기간 | `transitionHistory.actionAt` | 일 / 주 / 월 |
| Stage | 객체 테이블 `stageKey` | labeling, review, inspection, final_qa |
| 역할 | `role_group` (SQL 테이블 별도 생성 예정) | Labeler, Reviewer |

> **시간대 기준**: `actionAt` 및 `event_date` 집계는 KST(UTC+9) 기준으로 통일한다.  
> **KST 변환 규약**: UTC 저장 컬럼에 대해 `CONVERT_TIMEZONE('UTC', 'Asia/Seoul', column)` 또는 `column + INTERVAL 9 HOURS`를 SQL 표준으로 채택. 향후 모든 SQL 초안에 동일 패턴 적용.

---

## 6. 제약사항 및 후속 확인

| 항목 | 상태 | 비고 |
|---|---|---|
| 객체 테이블 ↔ TransitionHistory 시점 정합성 | 미검증 | 객체 `updatedAt`과 `actionAt` 매핑 검증 필요 |
| `person-days` 정밀도 | Command Log 기반 추정 | 외부 근태 데이터 연동 시 정밀도 향상 가능 |
| `role_group` 테이블 | 보류 | `dim_role_group.sql` 생성 보류 — 운영 필요 시점에 착수 |
| 재납품 월 경계 귀속 로직 | v2 이관 | 최초 착수 월 기준으로 v1.3 운영, 재납품 월 재귀속 정책은 v2에서 확정 |

---

## 7. 다음 단계

| 순서 | 작업 | 산출물 |
|---|---|---|
| 1 | 납품 Task·객체 수 주별 집계 SQL | `.sql/production_volume__weekly.sql` ✅ |
| 2 | `role_group` 매핑 테이블 SQL 작성 | `.sql/dim_role_group.sql` ⏸ 보류 |
| 3 | 이상탐지 STEP 8 (생산성 이상) 연계 지점 정의 | Anomaly Detection 문서 업데이트 |

---

## 8. 버전 히스토리

| 버전 | 일자 | 상태 | 주요 내용 |
|---|---|---|---|
| `v1` | 2026-05-11 | Draft | 생산량 = Task 기준 + 객체 기준 / 운영 지표·대시보드 별도 문서 분리 / Stage 구조 참조 일원화 (`stage_transition_analysis.md`) / 문서 영문 제목 통일 |
| `v1.1` | 2026-05-11 | Draft | 필터 조건 `toState='inspection'` 확정 / 생산성 분모 Labeler+Reviewer 합산으로 변경 / 재납품 카운트 정책 수정 (동일 Task = 1건) / `role_group` SQL 생성 예정 명시 / KST 변환 규약 추가 |
| `v1.2` | 2026-05-11 | Draft | 라벨링 착수 필터 확정: `fromState='waiting_labeling' AND toState='labeling' AND trigger='start'` / reassign 제외 근거 명시 |
| `v1.3` | 2026-05-11 | Draft | Feature별 객체 테이블 전체 매핑 확정 (LD 6개·RMD 2개·OD/SOD/TSTLD static 공유) / 2-tier 생산량 설계 (primary objects + LD points 보조 지표) / Task 순소요시간(net) 지표 추가 (Focus Drop idle 연계) / DDL wide-table 구조 반영 |
| `v1.3` | 2026-05-12 | Released | 제약사항 `role_group 보류` · `재납품 귀속 v2 이관` 처리 완료 / `.sql/production_volume__weekly.sql` 구현 확정 기준 정식 배포 |
