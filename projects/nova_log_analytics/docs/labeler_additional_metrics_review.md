# Labeler 추가 지표 요청 검토

**작성일**: 2026-05-06  
**문서 유형**: 요청 검토  
**적용 범위**: `projects/nova_log_analytics` Labeler role 대상 추가 지표 수집 가능성 및 활용성 검토

---

## 1. 배경

커맨드 로그 기반으로 수집 및 분석 가능한 추가 지표 목록이 요청되었다.  
검토에 앞서 기존 설계와의 중복 여부를 먼저 확인하였다.

**기존 설계 문서** (별도 관리):

| 문서 | 버전 | 커버 지표 |
|---|---|---|
| `docs/policies/labeler_focus_drop_policy.md` | v0.9 | 작업 집중도 저하 탐지 운영 기준 |
| `docs/policies/labeler_focus_drop_concept_design.md` | v1.0 Draft | 집중도 저하 개념 정의, gap 분류 체계 |
| `docs/policies/labeler_focus_drop_metric_design.md` | v1.0 Draft | count / ratio / percentile 판정 구조 |

---

## 2. 기존 설계와의 중복 확인

요청된 지표 중 아래 4개는 기존 설계 문서에서 이미 다루고 있다.  
신규 설계 없이 기존 문서 체계를 따른다.

| 요청 지표 | 기존 문서 커버 방식 |
|---|---|
| Active 작업 시간 | `diff_sec <= gap_p75` 구간을 정상 작업 흐름으로 정의 |
| Idle 시간 / Idle 비율 | `departure gap`(gap_p99 초과) 및 `gaps_5min` 집계로 이탈 후보 정량화 |
| 작업 집중도 | gap severity 분류 및 세션·사용자 단위 판정 체계 전반 |
| 작업 지속 시간 | 세션 단위(`user + session + task`) 집계 구조 |

---

## 3. 검토 대상 지표

중복 4개를 제외한 나머지 **13개 지표**를 검토한다.

### 3.1 평가 기준

| 기준 | 질문 |
|---|---|
| **의사결정 연결성** | 수치 변화 시 실제로 무엇을 바꿀 수 있는가 |
| **중복성** | 기존 지표로 이미 파악되는 정보인가 |
| **수집 비용 대비 가치** | 외부 데이터 확보 비용이 얻는 인사이트를 정당화하는가 |
| **측정 노이즈** | 작업 외 요인이 수치를 오염시킬 가능성이 있는가 |

수집 가능 여부 기호:

| 기호 | 의미 |
|---|---|
| ○ | 현재 로그만으로 즉시 구현 가능 |
| △ | 외부 데이터 조인 또는 추가 로직 필요 |
| × | 현재 로그로 측정 불가 |

### 3.2 검토 결과

| # | 지표명 | 수집 가능 | 측정 방법 | 필요 추가 데이터 | 활용성 | 비고 |
|---|---|:---:|---|---|:---:|---|
| 1 | **처리량** | ○ | `change_action = 'create'` 수 / Active 시간. task_id · user_id · 일자별 집계 | 처리 단위(object / frame / task) 팀 합의 필요 | 상 | |
| 2 | **난이도 보정 처리량** | △ | object_type 다양성·task 내 change 수로 부분 난이도 추정. 처리량(#1)과 세트로만 의미 있음 | scene 메타데이터(dynamic 비율, occlusion) 외부 DB 조인 필요 | 중 | 처리량(#1) 운영 후 필요성 검토 권장 |
| 3 | **재작업 비율** | ○ | `is_reverted = TRUE` 비율, 동일 `object_id`의 create → delete 패턴. `stg_labelit__undo_history` 전용 테이블 활용 | 없음 | 상 | |
| 4 | **Review 수정률** | △ | Reviewer의 `change_action = 'update'` 이벤트 비율. user role 구분 확보 시 즉시 산출 가능 | user role 매핑 테이블 (labeler / reviewer 구분) | 상 | |
| 5 | **검수 반려율** | △ | task_id를 키로 외부 시스템 반려 이벤트와 조인 | Task management 시스템 rejection 로그 API/DB 연동 필요 | 상 | |
| 6 | **First Pass Yield** | △ | Review 단계에서 해당 task_id에 change 없으면 FPY = 1 처리 | task stage 메타데이터 (#5와 동일 소스) | 상 | |
| 7 | **Reviewer 개입량** | △ | Reviewer user_id의 command 수·change 수 집계. role 데이터 주입 시 즉시 산출 | user role 매핑 테이블 (#4와 동일 소스) | 상 | |
| 8 | **결함 유형별 비율** | △ | `old_val → new_val` 차분으로 유형 분류: 위치(move_distance), 크기(size diff), 각도(rotation diff), 클래스(object_type 변경). 누락은 Reviewer create로 간접 추정 | Reviewer role 구분 + 누락 오류 정의 명확화 필요 | 상 | |
| 9 | **Undo/Redo 비율** | ○ | `stg_labelit__undo_history`의 `is_redo` 필드로 구분. 전체 event 수 대비 비율 산출 | 없음 | 상 | |
| 10 | **Frame/Channel 이동 패턴** | △ | C-2(Frame Nav), C-3(Channel Nav) event_type 집계. 체류 시간은 consecutive nav 이벤트 간 gap으로 추정 | workflow 병목 분석 로직 별도 개발 필요 | 중 | "이 수치가 높으면 무엇을 바꾼다"는 결정 경로 미정의. UX 개선 목적으로는 유효하나 성과 관리 지표로는 간접적 |
| 11 | **Tool 기능 사용 후 수정 강도** | △ | CB-4(Prediction) / CB-5(Interpolation) create 이후 동일 `object_id`의 update 이벤트 추적. move_distance 및 size/rotation 변화량 집계 | Prediction / Interpolation 생성 object_id 출처 구분 로직 필요 | 상 | |
| 12 | **ALT 결과물 수용률** | △ | ALT 전용 event_type 존재 시, create 후 수정 없이 유지된 object 비율 산출 | 커맨드 정의서 전체 검토로 ALT event_type 존재 여부 확인 필요 | 상 | 선결 조건: ALT event_type 유무 확인 |
| 13 | **Stage별 Cycle Time** | △ | Labeling 구간: C-1(Task Entry) ~ 마지막 커맨드까지 산출 가능(○). Review / 반려 구간은 외부 데이터 필요 | Task management DB stage transition 타임스탬프 조인 필요 (#5와 동일 소스) | 상 | |

---

## 4. 요약

### 즉시 구현 가능 (○, 3개)

| 지표 | 활용 테이블 |
|---|---|
| 처리량 | `stg_labelit__event_changes` |
| 재작업 비율 | `stg_labelit__undo_history`, `int_labelit__effective_changes` |
| Undo/Redo 비율 | `stg_labelit__undo_history` |

### 외부 데이터 확보 시 구현 가능 (△, 10개)

△ 지표 10개는 아래 3개 데이터 소스 확보 순서에 따라 단계적으로 구현 가능하다.

| 확보 순서 | 필요 데이터 | 해결되는 지표 |
|:---:|---|---|
| 1 | user role 매핑 테이블 | Review 수정률(#4), Reviewer 개입량(#7), 결함 유형별 비율(#8) |
| 2 | Task management DB stage 정보 | 검수 반려율(#5), First Pass Yield(#6), Stage별 Cycle Time(#13) |
| 3 | ALT event_type 존재 여부 확인 | ALT 결과물 수용률(#12) |

> 난이도 보정 처리량(#2)과 Frame/Channel 이동 패턴(#10)은 활용성 중으로 분류되었으며, 우선순위를 낮게 책정한다.  
> Tool 기능 사용 후 수정 강도(#11)는 출처 구분 로직 개발이 선행되어야 한다.
