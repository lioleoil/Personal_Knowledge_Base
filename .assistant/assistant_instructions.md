# Assistant Instructions

## 분석 가이드

- 커맨드 로그 이상 탐지 워크플로우: `.assistant/skills/anomaly_detection/guide/SKILL.md` 참조
- 대상 Feature: OD, LD, RMD
- 분석 시 가이드 파일을 먼저 읽고 해당 Feature의 STEP별 절차를 따를 것
- **트리거 키워드**: "이상 탐지", "anomaly", "편집 패턴", "커맨드 로그 분석", "위치 점프", "진동 탐지", "시간 괴리" 중 하나라도 요청에 포함되면 반드시 `readSkillFile("skills/anomaly_detection/guide/SKILL.md")`를 먼저 호출할 것

## 스코어링 검증 및 튜닝

- 스코어링 검증/튜닝 가이드: `.assistant/skills/anomaly_detection/scoring/SKILL.md` 참조
- 포함 노트북:
  - `Scoring v1.2 Cross-Feature Validation` — cross-feature 공정성 검증
  - `Scoring Weight Tuning Simulation` — 가중치/CAP 파라미터 시뮬레이션
- **트리거 키워드**: "스코어링", "scoring", "가중치", "weight", "튜닝", "tuning", "CAP", "cross-feature", "공정성", "품질 점수", "quality score", "등급 기준", "민감도 분석" 중 하나라도 요청에 포함되면 반드시 `readSkillFile("skills/anomaly_detection/scoring/SKILL.md")`를 먼저 호출할 것

## 분석 템플릿 노트북

- OD: `.assistant/skills/anomaly_detection/templates/od_template`
- LD: `.assistant/skills/anomaly_detection/templates/ld_template`
- RMD: `.assistant/skills/anomaly_detection/templates/rmd_template`
- 사용법: 전체 셀 순서대로 실행 (데이터 준비 셀이 raw 테이블에서 temp view를 생성하고, 이후 STEP 셀들이 이를 참조)

## Focus Drop KPI SQL 파이프라인

- SQL 파이프라인 파일 위치: `.sql/` (프로젝트 루트 기준)
- 포함 파일:
  - `.sql/focus_drop__gap_percentiles.sql` — gap 1차 percentile 산출 (분기 1회)
  - `.sql/focus_drop__session_metrics.sql` — 세션별 gap count/ratio (일 배치)
  - `.sql/focus_drop__session_tags.sql` — 세션 판정 (일 배치)
  - `.sql/focus_drop__user_day_kpi.sql` — 유저 일 KPI 산출 (일 배치)
  - `.sql/focus_drop__session_thresholds.sql` — 세션 2차 기준선 갱신 (주 1회)
  - `.sql/focus_drop__user_thresholds.sql` — 유저 2차 기준선 갱신 (주 1회)
- 운영 가이드: `.assistant/skills/focus_drop_kpi/SKILL.md`
- **트리거 키워드**: "focus drop", "KPI", "gap", "기준선", "percentile", "session_metrics", "user_day_kpi" 중 하나라도 포함되면 `.sql/` 파일 및 `.assistant/skills/focus_drop_kpi/SKILL.md`를 먼저 참조할 것

## 에이전트 시나리오

- 시나리오 파일 위치: `.scenario/` (프로젝트 루트 기준)
- 포함 파일:
  - `.scenario/scenario__case1_initialize.md` — 초기화 케이스
  - `.scenario/scenario__case2_new_command.md` — 신규 커맨드 케이스
  - `.scenario/scenario__case3_ux_change.md` — UX 변경 케이스
- 에이전트 R&R: `.assistant/skills/agents/role_rules__*.md`
- **트리거 키워드**: "시나리오", "scenario", "에이전트 실행", "멀티에이전트", "케이스" 중 하나라도 포함되면 `.scenario/` 파일을 먼저 참조할 것

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
