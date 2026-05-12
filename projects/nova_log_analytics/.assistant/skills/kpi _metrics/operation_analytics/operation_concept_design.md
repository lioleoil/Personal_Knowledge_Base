# Operational Metrics — Stage Object Delta & Stage Duration

**문서 상태**: Draft  
**작성일**: 2026-05-11  
**적용 범위**: `projects/nova_log_analytics` — MV2_LD, MV2_OD, MV2_SOD, MV2_RMD, MV2_TSTLD  
**선행 문서**: `stage_transition_analysis.md`, `productivity_concept_design.md`

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
| Stage별 평균 순증 객체 수 | 개/task | 수정 방향 (양수: 추가, 음수: 삭제) |
| 객체 변화 비율 | % | `|순증| / stageKey='labeling' 객체 수` — 수정 강도 |

**집계 축**: 업체 × Feature × 기간(일/주/월)

### 2.3 Feature별 객체 테이블 매핑

| Feature | 객체 테이블 | 핵심 객체 유형 |
|---|---|---|
| MV2_LD | `gen2_lines`, `gen2_lanes`, `gen2_road_boundaries`, `gen2_topologies` | line, lane, road_boundary, topology |
| MV2_OD / MV2_SOD / MV2_TSTLD | `gen2_dynamic_targets`, `gen2_static_targets` | bbox3d |
| MV2_RMD | `gen2_polywall_roadmark_objects`, `gen2_box_roadmark_objects` | polywall, bbox3d |

**조인 키**: 객체 테이블 `taskId` → task `_id` → `companyId`, `policyId`

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

### 3.2 집계 Metric

| Metric | 단위 | 집계 방식 |
|---|---|---|
| Stage 평균 소요 시간 | hours/task | avg by 업체 × Feature × 기간 |
| Stage 소요 시간 분포 | hours | p50 / p90 by 업체 × Feature |
| 전체 파이프라인 소요 시간 | hours/task | Labeling 착수 → 납품(deliver) 경과 시간 |

### 3.3 Edge Case 처리

| 상황 | 처리 방식 |
|---|---|
| Reassign (재배정) | 동일 Stage 내 여러 구간을 합산하여 총 소요 시간으로 계산 |
| Reject 후 재진입 | Stage별 각 패스(pass)를 개별 측정 후 합산. 재작업 횟수도 별도 집계 |
| 종료 이벤트 누락 | 다음 Stage 시작 이벤트의 `actionAt`을 종료 시점으로 대체 |

### 3.4 반려율 (Reject Rate)

소요 시간 증가의 주요 원인이므로 소요 시간과 함께 집계한다.

| Metric | 산출 로직 |
|---|---|
| Review 반려율 | `fromState='review' AND trigger='reject'` 건수 / 리뷰 완료 건수 |
| Inspection 반려율 | `fromState='inspection' AND trigger='reject'` 건수 / 검수 완료 건수 |

---

## 4. 집계 Dimension

| 축 | 소스 | 값 |
|---|---|---|
| 업체 | `task.companyId → company.name` | CW, LTS, NexterSystems, StradVision, LTSMM |
| Feature | `task.policyId → policy.feature` | MV2_LD, MV2_OD, MV2_SOD, MV2_RMD, MV2_TSTLD |
| 기간 | `transitionHistory.actionAt` | 일 / 주 / 월 |
| Stage | 객체 테이블 `stageKey` | labeling, review, inspection, final_qa |

> **시간대 기준**: `actionAt` 집계는 KST(UTC+9) 기준으로 통일.

---

## 5. 제약사항

| 항목 | 상태 | 비고 |
|---|---|---|
| 객체 테이블 ↔ TransitionHistory 시점 정합성 검증 | 미완료 | stg_object_counts_by_task 기반 stage_key별 스냅샷 정합성 확인 필요 |
| 객체 테이블 ↔ TransitionHistory 시점 정합성 | 미검증 | 객체 `updatedAt`과 `actionAt` 매핑 검증 필요 |
| Reject 재진입 시 소요 시간 합산 정밀도 | 미검증 | 동일 Stage 복수 패스 식별 로직 필요 |

---

## 6. 다음 단계

| 순서 | 작업 | 산출물 |
|---|---|---|
| 1 | Stage별 산출물 변화 SQL 초안 작성 (stageKey 간 COUNT 비교) | `.sql/ops__object_delta.sql` |
| 2 | Stage 소요 시간 SQL 초안 작성 (transitionHistory 이벤트 쌍 기반) | `.sql/ops__stage_duration.sql` |

---

## 7. 버전 히스토리

| 버전 | 일자 | 상태 | 주요 내용 |
|---|---|---|---|
| `v1` | 2026-05-11 | Draft | `production_volume_metric_design_v1.md`에서 운영 지표 영역 분리 / Stage 구조 참조 일원화 (`stage_transition_analysis.md`) / 문서 영문 제목 통일 |
