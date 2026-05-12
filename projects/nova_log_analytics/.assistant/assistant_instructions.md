# Assistant Instructions

## 분석 가이드

- 커맨드 로그 이상 탐지 워크플로우: `.assistant/skills/anomaly_detection/guide/SKILL.md` 참조
- 대상 Feature: OD, LD, RMD
- 분석 시 가이드 파일을 먼저 읽고 해당 Feature의 STEP별 절차를 따를 것
- **트리거 키워드**: "이상 탐지", "anomaly", "편집 패턴", "커맨드 로그 분석", "위치 점프", "진동 탐지", "시간 괴리" 중 하나라도 요청에 포함되면 반드시 `readSkillFile("skills/anomaly_detection/guide/SKILL.md")`를 먼저 호출할 것

## 스코어링 검증 및 튜닝

- 스코어링 검증/튜닝 가이드: `.assistant/skills/anomaly_detection/scoring/SKILL.md` 참조
- 포함 노트북:
  - `Scoring v1.0 Cross-Feature Validation` — cross-feature 공정성 검증
  - `Scoring Weight Tuning Simulation` — 가중치/CAP 파라미터 시뮬레이션
- **트리거 키워드**: "스코어링", "scoring", "가중치", "weight", "튜닝", "tuning", "CAP", "cross-feature", "공정성", "품질 점수", "quality score", "등급 기준", "민감도 분석" 중 하나라도 요청에 포함되면 반드시 `readSkillFile("skills/anomaly_detection/scoring/SKILL.md")`를 먼저 호출할 것

## 검수 품질 지표 (Inspection Quality Metrics)

- 검수 반려율/FPY 산출 가이드: `.assistant/skills/kpi_metrics/inspection_quality/SKILL.md` 참조
- 포함 노트북:
  - `Inspection Reject Rate - Monthly FPY Test` (ID: 3293698563438951) — 월별 반려율 & 다중 반려 분석
- **트리거 키워드**: "검수 반려율", "FPY", "First Pass Yield", "inspection reject", "반려 사유", "다중 반려", "품질 지표", "rejection rate" 중 하나라도 요청에 포함되면 반드시 `readSkillFile("skills/kpi_metrics/inspection_quality/SKILL.md")`를 먼저 호출할 것
- 핵심 규칙:
  - 모집단: `deliveryId IS NOT NULL` (inspection 진입 시 배정)
  - 월 기준: `updatedAt`의 YY-MM
  - Reject 범위: `fromState='inspection' AND trigger='reject'`만 대상
  - CDC 중복 제거 필수: `ROW_NUMBER() OVER (PARTITION BY _id ORDER BY _ingested_at DESC)`

## 생산량 & 생산성 (Production Volume & Productivity)

- 생산량/생산성 산출 가이드: `.assistant/skills/kpi_metrics/labeling_productivity/productivity/SKILL.md` 참조
- **트리거 키워드**: "생산량", "생산성", "production volume", "productivity", "납품 Task", "납품 객체", "시간당 객체", "인시", "인일", "person-hour", "person-day", "Task 소요시간", "투입 시간", "user_hour_slots" 중 하나라도 요청에 포함되면 반드시 `readSkillFile("skills/kpi_metrics/labeling_productivity/productivity/SKILL.md")`를 먼저 호출할 것
- 핵심 규칙:
  - 납품 기준: `fromState='waiting_submit' AND toState='inspection'`
  - 라벨링 착수: `fromState='waiting_labeling' AND toState='labeling' AND trigger='start'`
  - 재납품: 동일 Task = 1건 (최초 납품 기준)
  - 투입 자원: Labeler + Reviewer 합산 (Command Log 기반)
  - 시간대: KST (UTC+9) — `CONVERT_TIMEZONE('UTC', 'Asia/Seoul', column)`
  - CDC 중복 제거 필수


## 작업 집중도 저하 (Focus Drop)

- 코어 가이드: `.assistant/skills/kpi_metrics/labeling_productivity/focus_drop/SKILL.md` 참조
- 배포·운영: `.assistant/skills/kpi_metrics/labeling_productivity/focus_drop/focus_drop_deployment.md` 참조
- 생산성 연계: `.assistant/skills/kpi_metrics/labeling_productivity/focus_drop/focus_drop_productivity_linkage.md` 참조
- **트리거 키워드**: "집중도", "focus drop", "집중도 저하", "gap 분석", "gap percentile", "긴 공백", "light session", "heavy session", "idle session", "작업 이탈", "idle 탐지", "3분 기준", "180초", "idle 차감", "순소요시간", "net working time", "task idle" 중 하나라도 요청에 포함되면 반드시 Focus Drop SKILL을 참조할 것
- 핵심 규칙:
  - 세션 키: (user_id, session_id, task_id)
  - gap 구간: normal(≤p75) / observation(p75~p90) / light(p90~p95) / heavy(p95~180s) / idle(≥180s 고정)
  - 판정: count 중심 (ratio는 보조), 배타적 레벨 (idle > heavy > light > normal)
  - 기준선: 당일 데이터 아님 — rolling window 사전 산출 (1차 gap percentile: 90일, 2차 session/user threshold: 30일)
  - Role 필터: Labeler만 (기준선 보호), 생산성 연계 시 role_scope 별도 운용

## 공통 참조 문서 (common)

- Stage 파이프라인 구조: `.assistant/skills/common/stage_transition_analysis.md`
  - 라벨링 파이프라인 Stage 전환 이력, 상태 정의 (전 도메인 공통 참조)
- 커맨드 분류 체계: `.assistant/skills/common/gen2_command_definitions.md`
  - workspace_command의 commandType 분류, Undo/Redo·Frame 이동 패턴 정의

## KPI 정책 문서 (상위)

- KPI 메트릭 정책: `.assistant/skills/kpi_metrics/kpi_metric_policy.md`
  - 전 KPI 영역의 단일 산출식 정의, 구현 현황, 정책 원칙 (NULLIF, KST, ROUND 규약)
  - 지표 추가·변경 시 이 문서를 기준으로 동기화

## 운영 효율성 (Operation Efficiency)

- 운영 지표 가이드: `.assistant/skills/kpi_metrics/operation_efficiency/SKILL.md` 참조
- **트리거 키워드**: "Stage 소요 시간", "Cycle Time", "병목", "stage duration", "object delta", "산출물 변화", "객체 증감", "반려율", "review reject", "ops", "운영 지표", "TAT", "Turn-Around Time" 중 하나라도 요청에 포함되면 반드시 Operation SKILL을 참조할 것
- 핵심 규칙:
  - Pass 식별: `ROW_NUMBER() OVER (PARTITION BY task_id, stage ORDER BY stage_start_at)`
  - Reassign: 시작 이벤트에서 제외, 소요시간에 그대로 포함
  - 종료 이벤트 누락: `COALESCE(실제종료, 다음Stage시작, CURRENT_TIMESTAMP())`
  - Object Delta: `to_stage_count − from_stage_count`, NULLIF 처리

## 분석 템플릿 노트북

- OD: `.assistant/skills/anomaly_detection_templates/od_template`
- LD: `.assistant/skills/anomaly_detection_templates/ld_template`
- RMD: `.assistant/skills/anomaly_detection_templates/rmd_template`
- 사용법: 전체 셀 순서대로 실행 (데이터 준비 셀이 raw 테이블에서 temp view를 생성하고, 이후 STEP 셀들이 이를 참조)

## 프로젝트 컨텍스트

- 데이터 소스: `sv_nova_dev_an2_catalog.raw` 스키마의 Labelit 원시 테이블
- 주요 테이블: `raw_labelit__workspace_command`, `raw_labelit__workspace_history`, `raw_labelit__gen2_tasks`, `raw_labelit__gen2_assignments`, `raw_labelit__gen2_annotation_policies`, `raw_labelit__company`
- 원시 데이터 구조: `_id` (PK), `_raw` (variant JSON), `_is_deleted` (soft delete 플래그)
- JSON 파싱: `_raw:field::TYPE` 또는 `get_json_object(_raw, '$.field')` 사용
- **object_id는 UUID가 아니며, 단일 task 내에서만 unique** (task 간 동일 object_id가 존재할 수 있음 → 분석 시 반드시 task_id와 함께 사용)
- 조인 관계:
  - task.policyId → annotation_policy._id
  - task.assignmentId → assignment._id
  - task.companyId → company._id

## Agent Memories

### User Preferences
- 한국어 응답 선호
- SQL 쿼리 작성 시 Databricks SQL 문법 사용
- 테이블 alias 사용 (e.g., `t`, `a`, `p`, `c`)

### Inspection Quality Metrics
- deliveryId는 납품 승인 이후가 아니라 inspection 단계 진입 시점에 배정됨
- currentStageKey는 시점별 변동하므로 모집단 기준 부적합 → deliveryId IS NOT NULL 사용
- transitionHistory의 from_json 스키마는 반드시 문자열 리터럴로 전달 (중첩 > 파싱 오류 방지)
- reason 필드에 대소문자/trailing space 중복 존재 → NULLIF(TRIM(reason), '') + LOWER() 정규화 필요

### Production Volume & Productivity
- 납품 = waiting_submit → inspection 전환 (toState='inspection' 확정)
- 라벨링 착수 = waiting_labeling → labeling, trigger='start' (reassign 제외)
- 재납품: 동일 Task는 1건으로 카운트 (월 경계 귀속 로직 미확정)
- 생산성 분모: Labeler + Reviewer 합산 (업체 납품 대비 총 투입 효율 목적)
- Stage별 개별 효율은 운영 지표(operation_concept_design.md)에서 후속 처리
- role_group 테이블 미생성 — SQL로 별도 생성 예정
- **Feature별 객체 테이블 매핑** (절대 단순화하지 말 것):
  - LD: gen2_lines, gen2_line_points, gen2_road_boundaries, gen2_road_boundary_points, gen2_lanes, gen2_topologies (6개)
  - RMD: gen2_polywall_roadmark_objects, gen2_box_roadmark_objects (2개)
  - OD: gen2_dynamic_targets + gen2_static_targets (2개)
  - SOD/TSTLD: gen2_static_targets (단독)
  - 객체 수 산출 시 Feature별 모든 테이블을 UNION ALL 해야 정확한 수치
