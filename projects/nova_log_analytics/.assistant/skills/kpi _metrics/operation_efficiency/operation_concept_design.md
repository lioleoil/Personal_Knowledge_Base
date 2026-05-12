# Operational Metrics — Stage Object Delta & Stage Duration

**문서 상태**: Released (v1.1)  
**작성일**: 2026-05-12  
**적용 범위**: `projects/nova_log_analytics` — MV2_LD, MV2_OD, MV2_SOD, MV2_RMD, MV2_TSTLD  
**선행 문서**: `stage_transition_analysis.md`, `productivity_concept_design.md`  
**관련 SKILL**: `.assistant/skills/kpi_metrics/operation_efficiency/SKILL.md`

---

## 1. 개요

라벨링 파이프라인 각 Stage에서 발생하는 **산출물 변화**와 **소요 시간**을 정량화한다.

두 축의 교차 분석을 통해 수정 강도가 높은 업체·Stage·Feature 조합을 파악하고 운영 개선 의사결정 근거를 제공한다.

> **Stage 파이프라인 구조 및 전환 이력**: `stage_transition_analysis.md` 참조  
> 실제 작업 Stage (stageAssignees.stageKey): `labeling` · `review` · `inspection` · `final_qa`

---

## 2. Stage별 산출물 변화 (Object Delta)

동일 Task가 Stage를 진행하면서 객체 수가 어떻게 변화했는가를 측정한다. 리뷰어·검수자가 추가하거나 삭제한 객체 수를 Stage 전환 단위로 정량화한다.

### 2.1 증감 지표

| Stage 전환 | 정의 | 산출 로직 |
|---|---|---|
| Labeling → Review | 리뷰어가 추가·삭제한 순 객체 수 | `stageKey='review'` COUNT − `stageKey='labeling'` COUNT |
| Review → Inspection | 검수 진입 시점 변화 (리뷰 완료본 기준) | `stageKey='inspection'` COUNT − `stageKey='review'` COUNT |
| Inspection → Final QA | 최종 QA 단계 변화 | `stageKey='final_qa'` COUNT − `stageKey='inspection'` COUNT |
| 전체 순증 (Labeling → Final QA) | 파이프라인 전체 순 변화량 | `stageKey='final_qa'` COUNT − `stageKey='labeling'` COUNT |

### 2.2 집계 Metric

| Metric | 단위 | 의미 |
|---|---|---|
| `delta_count` | 개/task | 순 증감 (양수: 추가, 음수: 삭제) |
| `delta_ratio` | % | `delta_count / NULLIF(from_stage_count, 0) × 100` — 수정 강도 |
| `avg_delta_count` | 개/task | Stage 전환별 평균 순증 (업체 × Feature × 주) |
| `avg_abs_delta_ratio` | % | `AVG(ABS(delta_ratio))` — 방향 무관 수정 강도 |

**집계 축**: 업체 × Feature × 기간(일/주/월) × Stage 전환 쌍

### 2.3 Feature별 객체 테이블 매핑

| Feature | 객체 테이블 | 핵심 객체 유형 |
|---|---|---|
| MV2_LD | `gen2_lines`, `gen2_lanes`, `gen2_road_boundaries`, `gen2_topologies` | line, lane, road_boundary, topology |
| MV2_OD / MV2_SOD / MV2_TSTLD | `gen2_dynamic_targets`, `gen2_static_targets` | bbox3d |
| MV2_RMD | `gen2_polywall_roadmark_objects`, `gen2_box_roadmark_objects` | polywall, bbox3d |

> ⚠️ **테이블명 검증 필요**: Productivity SKILL에서는 단수형(`gen2_lanes`, `gen2_topologies`, `gen2_road_boundaries`)을 사용하나, 본 문서 및 Operation SKILL에서는 복수형(`gen2_lanes`, `gen2_topologies`, `gen2_road_boundaries`)을 사용한다. 실제 Unity Catalog DDL 기준으로 정본 테이블명을 확인하고 전 문서 통일 필요.  
> ⚠️ RMD: Productivity SKILL은 `gen2_box_roadmark_objects`, Operation SKILL은 `gen2_box_roadmark_objects` — 동일 테이블 여부 확인 필요.

**조인 키**: 객체 테이블 `taskId` → task `_id` → `companyId`, `policyId`  
**소스**: `analytics.stg_object_counts_by_task` (staging PIVOT — CDC dedup 완료)

---

## 3. Stage 소요 시간 (Stage Duration)

각 작업 Stage에서 Task가 실제 처리되는 데 걸린 시간. 업체별·Feature별 비교를 통해 병목 구간을 파악하고 Section 2의 수정 강도와 교차 분석한다.

### 3.1 Stage별 시작/종료 이벤트 정의

| Stage | 시작 이벤트 | 종료 이벤트 |
|---|---|---|
| Labeling | `waiting_labeling → labeling` (`trigger='start'`) | `labeling → waiting_review` |
| Review | `waiting_review → review` (`trigger='start'`) | `review → waiting_submit` |
| Inspection | `waiting_submit → inspection` (`trigger='deliver'`) | `inspection → waiting_final_qa` |
| Final QA | `waiting_final_qa → final_qa` (`trigger='start'`) | `final_qa → completed` |

> 소스: `analytics.stg_task_transition_events` (staging snake_case 기준)

### 3.2 집계 Metric

| Metric | 단위 | 집계 방식 |
|---|---|---|
| `stage_duration_hours` | hours/task×pass | `(stage_end_at − stage_start_at) / 3600.0` |
| `avg_stage_duration_hours` | hours/task | pass 합산 후 평균 (업체 × Feature × Stage × 주) |
| `p50_stage_duration_hours` | hours | 분포 중앙값 (업체 × Feature × Stage) |
| `p90_stage_duration_hours` | hours | 분포 90th percentile |
| `total_pipeline_hours` | hours/task | Labeling 착수 → 납품(deliver) 경과 시간 |
| `rework_pass_count` | 횟수/task | `pass_num ≥ 2` 패스 수 (Reject 재작업 횟수) |

### 3.3 비즈니스 규칙 (Edge Case 처리)

#### 3.3.1 Pass 식별 (Reject 후 재진입)

동일 Task에서 Reject로 동일 Stage에 2회 이상 진입할 수 있다. 각 진입을 **별도 pass**로 식별한다.

```
pass_num = ROW_NUMBER() OVER (
  PARTITION BY task_id, stage
  ORDER BY stage_start_at
)
```

- pass 1: 최초 수행
- pass 2+: Reject 후 재작업
- **집계 시 pass별 소요 시간을 합산**하여 Task 기준 총 소요 시간 산출

#### 3.3.2 Reassign 처리

동일 Stage 내 `trigger='reassign'` 이벤트는 담당자 변경이지 새 pass가 아니다.

- `from_state='labeling' AND to_state='labeling' AND trigger='reassign'` → **시작 이벤트에서 제외**
- 동일 pass 내 Reassign 구간은 소요 시간에 **그대로 포함** (중단 없이 이어진 작업으로 처리)

#### 3.3.3 종료 이벤트 누락

Stage 종료 이벤트가 없는 경우 (Task가 현재 해당 Stage에 있는 경우):

```
stage_end_at = COALESCE(실제종료, 다음Stage시작, CURRENT_TIMESTAMP())
```

- 1순위: 해당 Stage의 실제 종료 이벤트 `action_at`
- 2순위: 다음 Stage 시작 이벤트의 `action_at` (로그 기반 대체)
- 3순위: `CURRENT_TIMESTAMP()` (진행 중인 Task)
- `is_open = TRUE` 플래그를 부여하여 집계 시 제외/포함 선택 가능

### 3.4 반려율 (Reject Rate)

소요 시간 증가의 주요 원인이므로 소요 시간과 함께 집계한다.

| Metric | 산출 로직 | 소스 |
|---|---|---|
| Review 반려율 | `COUNT(from_state='review' AND trigger='reject') / NULLIF(COUNT(review 종료 이벤트), 0) × 100` | `stg_task_transition_events` |
| Inspection 반려율 | `COUNT(from_state='inspection' AND trigger='reject') / NULLIF(COUNT(inspection 종료 이벤트), 0) × 100` | `stg_task_transition_events` |

> Review 종료 이벤트: `from_state='review' AND to_state IN ('waiting_submit', 'waiting_labeling')`  
> `NULLIF` 처리: Policy §1.3 원칙 준수

---

## 4. 집계 Dimension

| 축 | 소스 | 값 |
|---|---|---|
| 업체 | `task.companyId → company.name` | CW, LTS, NexterSystems, StradVision, LTSMM |
| Feature | `task.policyId → policy.feature` | MV2_LD, MV2_OD, MV2_SOD, MV2_RMD, MV2_TSTLD |
| 기간 | `transitionHistory.actionAt` | 일 / 주 / 월 |
| Stage | 객체 테이블 `stageKey` / transition `from_state` | labeling, review, inspection, final_qa |

> **시간대 기준**: `actionAt` 집계는 KST(UTC+9) 기준으로 통일.  
> SQL 규약: `CONVERT_TIMEZONE('UTC', 'Asia/Seoul', action_at)` 적용.

---

## 5. 제약사항

| 항목 | 상태 | 비고 |
|---|---|---|
| 객체 테이블 ↔ TransitionHistory 시점 정합성 검증 | 미완료 | `stg_object_counts_by_task` 기반 `stage_key`별 스냅샷 정합성 확인 필요 |
| 객체 테이블 ↔ TransitionHistory 시점 정합성 | 미검증 | 객체 `updatedAt`과 `actionAt` 매핑 검증 필요 |
| Reject 재진입 시 소요 시간 합산 정밀도 | 미검증 | pass_num ROW_NUMBER 기반 확정 — start/end 쌍 불일치 엣지케이스 검증 필요 |
| Feature별 테이블명 단수/복수 통일 | 미완료 | Productivity SKILL(단수) vs Operation SKILL(복수) 불일치 — DDL 확인 후 전 문서 통일 |

---

## 6. 다음 단계

| 순서 | 작업 | 산출물 | 상태 |
|---|---|---|---|
| 1 | DDL 생성 | `.sql/ops__ddl.sql` (ops_stage_duration · ops_object_delta) | 📋 SKILL 제안 완료, 파일 생성 필요 |
| 2 | Stage Duration SQL 작성 | `.sql/ops__stage_duration.sql` | 📋 SKILL 템플릿 완료, 파일 생성 필요 |
| 3 | Object Delta SQL 작성 | `.sql/ops__object_delta.sql` | 📋 SKILL 템플릿 완료, 파일 생성 필요 |
| 4 | 테이블명 단수/복수 통일 | 전 문서 (Policy·기획·SKILL) | ⬜ 미착수 |
| 5 | 이력 소급 적재 및 검증 | Phase A Bootstrap | ⬜ 미착수 |

---

## 7. 버전 히스토리

| 버전 | 일자 | 상태 | 주요 내용 |
|---|---|---|---|
| `v1` | 2026-05-11 | Draft | `production_volume_metric_design_v1.md`에서 운영 지표 영역 분리 / Stage 구조 참조 일원화 (`stage_transition_analysis.md`) / 문서 영문 제목 통일 |
| `v1.1` | 2026-05-12 | Released | SKILL 비즈니스 규칙 역반영 — pass_num ROW_NUMBER 확정 / Reassign 처리 규칙 명시 / 종료 이벤트 3단 fallback 확정 / 반려율 산출 구체화(NULLIF) / 테이블명 불일치 이슈 기록 / DDL·SQL 참조 추가 |
