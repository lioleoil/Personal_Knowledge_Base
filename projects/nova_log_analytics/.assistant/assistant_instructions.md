# Assistant Instructions

## 분석 가이드

- 커맨드 로그 이상 탐지 워크플로우: `.assistant/skills/anomaly_detection_guide/SKILL.md` 참조
- 대상 Feature: OD, LD, RMD
- 분석 시 가이드 파일을 먼저 읽고 해당 Feature의 STEP별 절차를 따를 것
- **트리거 키워드**: "이상 탐지", "anomaly", "편집 패턴", "커맨드 로그 분석", "위치 점프", "진동 탐지", "시간 괴리" 중 하나라도 요청에 포함되면 반드시 `readSkillFile("skills/anomaly_detection_guide/SKILL.md")`를 먼저 호출할 것

## 스코어링 검증 및 튜닝

- 스코어링 검증/튜닝 가이드: `.assistant/skills/anomaly_detection_scoring/SKILL.md` 참조
- 포함 노트북:
  - `Scoring v1.0 Cross-Feature Validation` — cross-feature 공정성 검증
  - `Scoring Weight Tuning Simulation` — 가중치/CAP 파라미터 시뮬레이션
- **트리거 키워드**: "스코어링", "scoring", "가중치", "weight", "튜닝", "tuning", "CAP", "cross-feature", "공정성", "품질 점수", "quality score", "등급 기준", "민감도 분석" 중 하나라도 요청에 포함되면 반드시 `readSkillFile("skills/anomaly_detection_scoring/SKILL.md")`를 먼저 호출할 것

## 검수 품질 지표 (Inspection Quality Metrics)

- 검수 반려율/FPY 산출 가이드: `.assistant/skills/inspection_quality_metrics/SKILL.md` 참조
- 포함 노트북:
  - `Inspection Reject Rate - Monthly FPY Test` (ID: 3293698563438951) — 월별 반려율 & 다중 반려 분석
- **트리거 키워드**: "검수 반려율", "FPY", "First Pass Yield", "inspection reject", "반려 사유", "다중 반려", "품질 지표", "rejection rate" 중 하나라도 요청에 포함되면 반드시 `readSkillFile("skills/inspection_quality_metrics/SKILL.md")`를 먼저 호출할 것
- 핵심 규칙:
  - 모집단: `deliveryId IS NOT NULL` (inspection 진입 시 배정)
  - 월 기준: `updatedAt`의 YY-MM
  - Reject 범위: `fromState='inspection' AND trigger='reject'`만 대상
  - CDC 중복 제거 필수: `ROW_NUMBER() OVER (PARTITION BY _id ORDER BY _ingested_at DESC)`

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
