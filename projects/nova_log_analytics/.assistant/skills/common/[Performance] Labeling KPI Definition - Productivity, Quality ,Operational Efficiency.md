# [Performance] Labeling KPI Definition - Productivity / Quality / Operational Efficiency

**문서 상태**: Released (v1.2)  
**최초 작성**: 2026-05-08 · **최종 수정**: 2026-05-12  
**상세 산출식**: [`kpi_metric_policy.md`](kpi_metric_policy.md)  
**운영 SQL**: `.sql/` 하위 각 도메인 파일 참조

---

본 문서는 협력업체의 3D 라벨링 운영 성과를 체계적으로 측정하고 개선하기 위한 **핵심 KPI 지표 체계**를 정의합니다.

현재 라벨링 작업의 품질과 효율성은 협력업체별 역량 차이, ALT(Auto Labeling Tool) 결과물의 정확도, 그리고 검수 프로세스의 일관성 등 다양한 변수에 의해 영향을 받고 있습니다. 이를 정량적으로 비교·분석할 수 있는 통합된 지표 기준이 부재하여, 병목 구간 식별이나 품질 이슈의 근본 원인 추적이 어려운 상황을 개선하고자 전체 지표를 **3대 핵심 KPI 카테고리**로 재분류하였습니다.

- **생산성 지표** — 협력업체별 작업 속도와 작업량을 정량 비교
- **검수 품질 지표** — 작업 결과물의 초기 품질 수준과 반복 오류 패턴을 다각도로 측정
- **운영 효율성 지표** — 전체 흐름의 병목 구간을 식별하고 운영을 최적화

---

## 1. 생산성 지표 (Productivity Metrics)

> **목적**: 협력업체별 작업 속도·작업량을 정량적으로 비교하고, 생산성 기준선을 수립한다.

| 우선순위 | 지표 | 구현 | 활용도 | 기대효과 |
| --- | --- | --- | --- | --- |
| **P0** | **생산량** (납품 Task 수 · 납품 객체 수) | ✅ | 협력업체가 실제 납품한 Task 수와 객체 수를 집계하는 **결과물 기준 지표**. 주간 납품량 추이와 업체별 규모 비교에 활용. | ① 협력업체 간 납품량 규모 비교 ② 주간·월간 납품 추이 모니터링 ③ 투입 리소스 대비 산출 규모 파악 |
| **P0** | **생산성** (시간당 Object 처리 수 · 1인 1일 납품 Task 수) | ✅ | Active 작업 시간 대비 산출 효율을 측정하는 **1차 기준 지표**. 단순 접속 시간이 아닌 커맨드 발생 구간(Active Time) 기준 산출이 핵심. | ① 협력업체 간 생산성 벤치마크 수립 ② 인력 투입 대비 산출량 최적화 ③ 프로젝트별 적정 투입 인력 산정 기준 마련 |
| **P1** | **작업 집중도 / Idle / 작업 지속 시간** | ✅ | 세션 내 Active vs Idle 비율, 연속 작업 지속 시간 등을 분석하여 **세션 품질과 작업 패턴**을 파악. 작업자 모니터링 이슈를 고려해 내부 분석용으로 제한 활용. | ① 비효율 세션 패턴 식별 (잦은 이탈, 과도한 Idle 등) ② 적정 작업 세션 길이 가이드라인 도출 ③ 장기적으로 작업 환경·UX 개선 근거 확보 |
| **P1** | **신규 생성 vs ALT 사용 비율** | ⬜ | 신규 Dynamic Cuboid 생성 비율과 기존 ALT/Interpolation 결과물 재활용 비율을 비교하여 **자동화 도구 활용도**를 측정. 단독 해석보다 처리량·품질 지표와 교차 분석 시 유의미. | ① ALT 정확도 간접 평가 → 모델 개선 피드백 ② 자동화 활용률 향상을 통한 작업 시간 단축 ③ 불필요한 수동 작업 비중 감소 |

**P0 구현 세부 — 생산량**

| 지표명 | 산출식 | 주기 | SQL |
|--------|--------|------|-----|
| `delivered_task_count` | `waiting_submit → inspection` 전환 Task 수 | 주 | `production_volume__weekly.sql` |
| `delivered_object_count` | 납품 Task의 `stageKey='inspection'` 스냅샷 객체 수 | 주 | `production_volume__weekly.sql` |

**P0 구현 세부 — 생산성**

| 지표명 | 산출식 | 주기 | SQL |
|--------|--------|------|-----|
| `obj_per_person_hour` | `delivered_object_count / user_hour_slots` | 주 | `production_volume__weekly.sql` |
| `task_per_person_day` | `delivered_task_count / person_days` | 주 | `production_volume__weekly.sql` |

> 집계 Dimension: 업체 × Feature × 주차 / 투입 자원 = Labeler + Reviewer 합산

**P1 구현 세부 — 작업 집중도 / Idle (Focus Drop KPI)**

| 지표명 | 설명 | 주기 | SQL |
|--------|------|------|-----|
| `focus_drop_level` | 세션 판정 (light / heavy / idle / normal) | 일 | `focus_drop__session_tags.sql` |
| `idle_gap_duration_sec` | 세션 idle 구간 지속 초수 합산 | 일 | `focus_drop__session_metrics.sql` |
| `heavy_session_count` | 유저 일 단위 heavy 세션 수 | 일 | `focus_drop__user_day_kpi.sql` |
| `idle_gap_total` | 유저 일 단위 idle gap 횟수 합산 | 일 | `focus_drop__user_day_kpi.sql` |

> gap 구간 기준: normal / observation / light(p90) / heavy(p95) / idle(≥180s 고정)  
> 미구현 — P1 신규 생성 vs ALT 사용 비율: ALT 관련 Log 확정 후 착수

---

## 2. 검수 품질 지표 (Quality Metrics)

> **목적**: 작업 결과물의 품질 수준을 다각도로 측정하고, 반복 오류를 조기에 식별하여 협력업체 피드백에 활용한다.

| 우선순위 | 지표 | 구현 | 활용도 | 기대효과 |
| --- | --- | --- | --- | --- |
| **P0** | **검수 반려율 (+ 결함 유형별 비율)** | ✅ | Inspection 단계 Reject 건수와 반려 사유를 유형별로 집계하여 **반복 오류 패턴을 정량화**하는 핵심 품질 지표. 협력업체별·프로젝트별 비교 분석의 기본 축.
(결함 유형에 대한 정보는 추후 Labelit에 통합 필요.)| ① 반복 결함 Top-N 도출 → 타겟 교육·가이드 개선 ② 협력업체별 품질 등급 산정 기준 마련 ③ 품질 기준(Acceptance Criteria) 고도화 |
| **P0** | **First Pass Yield** | ✅ | Review/검수에서 **수정 없이 1회 통과한 비율**을 측정. 검수 반려율과 상호 보완적으로 활용하여 "처음부터 올바르게 완료된 작업" 비중을 확인. | ① 협력업체별 초기 품질 수준 입체적 비교 ② 재작업(Rework) 비용 절감 효과 정량화 ③ 품질 우수 업체 인센티브 기준 수립 |
| **P1** | **Tracking ID당 평균 커버 프레임 수 (ALT)** | ⬜ | 하나의 Tracking ID가 실제 객체 존재 구간을 얼마나 커버하는지 측정. GT/기준 데이터와의 Sync가 필요하므로 **사후 분석(Post-hoc) 지표**로 활용. | ① Dynamic Object Tracking 완성도 정량 평가 ② ID 단편화(Fragmentation) 문제 조기 발견 ③ 장기적으로 Tracking 품질 벤치마크 구축 |
| **P2** | **삭제 후 재생성 패턴 (ALT)** | ⬜ | 단순 수정이 아닌 **삭제→동일 객체 재생성** 케이스를 식별하여 재작업 비용과 근본 품질 이슈를 간접 확인. | ① 재작업 비용(Hidden Cost) 가시화 ② ALT 품질 또는 Labeling 가이드 미흡 구간 특정 ③ 프로세스 개선 ROI 산출 근거 확보 |
| **P3** | **Merge / Split 발생 빈도 (ALT)** | ⬜ | Tracking ID의 잘못된 연결·단절로 인한 사후 수정 빈도를 측정. **Stage별 분리 집계** 시 ALT 모델 문제 vs Labeling 품질 문제를 구분 가능. | ① Tracking 오류 원인 분리 (ALT vs 작업자) ② ALT 모델 개선 우선순위 도출 ③ 작업자 교육 포인트 구체화 |

**P0 구현 세부 — 검수 반려율 + FPY**

| 지표명 | 산출식 | 주기 | SQL |
|--------|--------|------|-----|
| `rejection_rate_pct` | `rejected_count / total_inspected × 100` | 월 | `inspection_quality__monthly_fpy.sql` |
| `first_pass_yield_pct` | `100 − rejection_rate_pct` | 월 | `inspection_quality__monthly_fpy.sql` |
| 다중 반려 Task | `inspection_reject_count ≥ 2` | 월 | `inspection_quality__multi_reject_detail.sql` |

> 모집단: `deliveryId IS NOT NULL` (inspection 진입 Task) / Reject 기준: `from_state='inspection' AND trigger='reject'` / `from_state='review'` reject 제외  
> 미구현 — P1~P3: ALT 관련 Log 확정 후 착수

---

## 3. 운영 효율성 지표 (Operational Efficiency Metrics)

> **목적**: 전체 스테이지의 흐름을 모니터링하고, 병목 구간을 식별하여 운영 최적화를 위한 분석 인사이트를 도출한다.

| 우선순위 | 지표 | 구현 | 활용도 | 기대효과 |
| --- | --- | --- | --- | --- |
| **P0** | **Stage별 Cycle Time** | ✅ | 라벨링 → 검수 → 제출 → 검사 → 최종 QA 등 **각 단계별 소요 시간**을 측정하여 전체 프로세스의 병목 구간을 식별하는 핵심 운영 지표. | ① 병목 Stage 특정 → 리소스 재배치·프로세스 개선 ② 전체 TAT(Turn-Around Time) 단축 목표 수립 ③ SLA 기반 납기 예측 정확도 향상 |
| **P1** | **Stage별 소요 시간 세분화** | ⬜ | Labeling / Review / Inspection / Final QA 각 단계의 소요시간(avg · p50 · p90)을 개별 측정하여 병목 단계를 특정. Reject 재작업 구간의 추가 소요시간도 별도 집계. | ① 단계별 병목 구간 정량 식별 ② Reject 재작업 횟수·소요시간 구분 집계 ③ 업체·Feature별 Stage 효율성 비교 |
| **P1** | **Stage별 객체 증감 (Object Delta)** | ⬜ | Review·Inspection 단계에서 추가·삭제된 객체 수를 Stage 전환 단위로 정량화. 수정 강도(delta_ratio)와 Stage Duration을 교차 분석하여 고수정 업체·Feature 조합을 파악. | ① 단계별 수정 강도 정량화 ② 수정 빈도가 높은 업체·Feature 조합 특정 ③ 검수 품질 지표와 교차 분석으로 근본 원인 추적 |
| **P1** | **Review 반려율** | ⬜ | Review 단계에서의 반려 건수 / 리뷰 완료 건수. Inspection 반려율(§2 P0)과 함께 파이프라인 전체 반려 패턴을 파악하는 운영 지표. Stage Duration 증가의 주요 원인 분석에 활용. | ① Review 병목 구간 식별 ② 재작업 빈도 추이 모니터링 ③ Labeling 품질과 Review 부하의 상관관계 분석 |
| **P2** | **Undo/Redo 비율, Frame/Channel 이동 패턴** | ⬜ | Tool UX 및 세부 작업 흐름 분석에 활용. Scene 내 작업 흐름 분석이 구체화된 이후 **보조 지표**로 단계적 도입 검토. | ① Tool UX 개선 포인트 데이터 기반 도출 ② 비효율적 작업 패턴 식별 → 워크플로우 최적화 ③ 교육 커리큘럼 설계 시 참고 자료 활용 |

**P0 구현 세부 — Cycle Time (파이프라인 합산)**

| 지표명 | 산출식 | 주기 | SQL |
|--------|--------|------|-----|
| `gross_task_hours` | `(deliver_actionAt − start_actionAt) / 3600.0` | 주 | `production_volume__weekly.sql` |
| `net_task_hours` | `GREATEST(gross_task_sec − task_total_idle_sec, 0) / 3600.0` | 주 | `production_volume__weekly.sql` |

> `net_task_hours`는 Focus Drop idle 차감 후 순작업시간 (생산성 지표 P1 연계)

**P1 구현 대상 — Stage Duration · Object Delta · Review 반려율**

| 지표명 | 설명 | 주기 | SQL |
|--------|------|------|-----|
| `stage_duration_hours` | Stage별 소요시간 (pass별 합산) | 주 | `ops__stage_duration.sql`
| `p50_stage_duration_hours` | Stage별 소요시간 중앙값 | 주 | `ops__stage_duration.sql`
| `p90_stage_duration_hours` | Stage별 소요시간 90th percentile | 주 | `ops__stage_duration.sql`
| `rework_pass_count` | Reject 재작업 횟수 (pass_num ≥ 2) | 주 | `ops__stage_duration.sql`
| `avg_delta_count` | Stage 전환별 평균 순증 객체 수 | 주 | `ops__object_delta.sql`
| `avg_abs_delta_ratio` | Stage 전환별 평균 수정 강도 (%) | 주 | `ops__object_delta.sql`
| `review_reject_rate_pct` | Review 단계 반려율 | 주 | `ops__stage_duration.sql`

> 집계 Dimension: 업체 × Feature × Stage 전환 × 주차  
> 선행 조건: `stg_task_transition_events` · `int_object_counts_by_task` 적재 완료  
> 미구현 — P2 Undo/Redo: 우선 순위 낮음.

---

## 카테고리별 요약 매트릭스

| 카테고리 | P0 | P1 | P2 | P3 | 합계 |
| --- | --- | --- | --- | --- | --- |
| **생산성 지표** | 생산량 ✅ · 생산성 ✅ | 작업 집중도/Idle ✅ · 신규 생성 vs ALT 사용 비율 ⬜ | — | — | 4개 |
| **검수 품질 지표** | 검수 반려율 ✅ · FPY ✅ | Tracking ID 커버 프레임 수 ⬜ | 삭제 후 재생성 ⬜ | Merge/Split 빈도 ⬜ | 5개 |
| **운영 효율성 지표** | Stage별 Cycle Time ✅ | Stage Duration 세분화 ⬜ · Object Delta ⬜ · Review 반려율 ⬜ · Undo/Redo ⬜ | — | — | 5개 |

**구현 현황**: 14개 지표 중 6개 ✅ 구현 범위 포함 · 8개 ⬜ 후속 아이템으로 진행

---
