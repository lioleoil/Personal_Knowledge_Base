# Pipeline Report — `ld` Feature 신규 로그 처리 결과

**처리 일시**: 2026-03-26
**대상 파일**: `tables/raw_labelit__ld.csv`
**처리 범위**: Raw → Staging → Intermediate (local 시뮬레이션)

---

## 처리 결과 요약

| 레이어 | 출력 파일 | 행 수 |
|--------|-----------|-------|
| Raw (입력) | `raw_labelit__ld.csv` | 23행 (24행 - 헤더) |
| Staging — events | `stg_labelit__ld__events.csv` | 9행 (unique event_id) |
| Staging — event_changes | `stg_labelit__ld__event_changes.csv` | 23행 |
| Intermediate — effective_changes | `int_labelit__ld__effective_changes.csv` | 23행 |

**이벤트 구성**

| event_type | 이벤트 수 | change 행 수 |
|------------|-----------|-------------|
| annotation.line.create | 6 | 20 (line 6 + point 14) |
| annotation.lane.create | 2 | 2 |
| annotation.topology.create | 1 | 1 |

---

## 이슈 목록

### [I-2] Raw 데이터 형식 불일치 — CloudEvent JSON 없음 🚨 BLOCKER

**현상**
기존 raw 포맷과 신규 ld raw 포맷이 완전히 다름.

| | 기존 (od / od2) | 신규 (ld) |
|---|---|---|
| 저장 단위 | 1행 / 이벤트 | **1행 / change** (이미 EXPLODE됨) |
| 원본 보존 | `_raw` 컬럼에 CloudEvent 전체 JSON | `_raw` 컬럼 없음 |
| 파싱 여부 | Raw 레이어에서 파싱 없음 | **이미 파싱·분해됨** |

**영향**
기존 파이프라인 SQL은 `get_json_object(_raw, '$.type')` 기반으로 동작하므로 ld raw 데이터를 `01_raw` 노트북으로 직접 처리 불가.
`raw_labelit__workspace_command` 테이블에 정상 적재 자체가 실패할 수 있음.

**조치 필요**
App Engineer에 ld 이벤트를 CloudEvent 1.0 JSON 형식(`_raw` 포함)으로 발행하도록 수정 요청.
또는 ld 전용 raw 테이블 및 수집 경로 별도 정의 검토.

---

### [I-3] 신규 event_type 3종 — 파이프라인 스펙 미정의 ⚠️

**현상**
아래 3종의 event_type이 파이프라인에 정의되지 않은 상태로 유입됨.

| event_type | change 행 수 |
|------------|-------------|
| `annotation.line.create` | 20 |
| `annotation.lane.create` | 2 |
| `annotation.topology.create` | 1 |

현재 파이프라인 처리 결과:
- `event_category = 'other'`
- → 기존 분석 쿼리 대상에서 완전 제외

**조치 필요**
수집 요청 이력 등록 및 `docs/command_spec_template.md` 기준으로 App Engineer 스펙 문서 수령.
Case 2 (신규 커맨드 추가) 또는 Case 1 (신규 feature workspace 초기 셋업) 프로세스 적용.

---

### [I-4] CloudEvent 필수 필드 다수 누락 ⚠️

**현상**
ld raw 데이터에 기존 CloudEvent 표준 필드가 없어 stg_events의 해당 컬럼이 모두 빈값으로 적재됨.

| 누락 필드 | 설명 |
|-----------|------|
| `subject` | 작업 대상 MongoDB ObjectId |
| `dataschema` | CloudEvent 스키마 버전 |
| `user_name` | 사용자명 |
| `dataset_id` | 데이터셋 ID |
| `action` | 커맨드 액션명 |
| `input_type` | 입력 유형 (mouse 등) |
| `targets` | 커맨드 대상 object ID 배열 |
| `params` | 커맨드 결과 요약 |

**조치 필요**
App Engineer에 ld 이벤트 CloudEvent 스펙 확인.
표준 필드 포함 여부 및 누락 필드의 ld 적용 가능성 검토.

---

### [I-5] params 필드 없음 — C2 완전성 검증 불가 ⚠️

**현상**
기존 C2 검증: `params.updateCount` (또는 `selectedCount`) = changes 배열 원소 수로 완전성 교차 확인.
ld 이벤트에 `params` 필드 자체가 없어 C2 검증 기준 수치가 없음.

예시:
```
annotation.line.create (event 1c2a6660):
  changes = 3행 (line 1 + point 2)
  params = 없음 → 기대 건수 비교 불가
```

**조치 필요**
App Engineer에 `params.createCount` (또는 동등 필드) 정의 요청.
또는 ld 전용 C2 검증 기준 별도 수립.

---

### [I-6] old_val = "null" 문자열 — create action Q2 검증 주의 ℹ️

**현상**
모든 ld 이벤트는 create 액션으로 변경 전 상태가 없음. raw 데이터에서 `old_val = "null"` (문자열).

**Q2 검증과의 관계**
- CSV 상 "null" 문자열 → `IS NOT NULL` 통과
- 단, Databricks 파이프라인에서 `from_json` ARRAY STRUCT 파싱 시 JSON의 `"old": null`은 SQL NULL로 변환됨 → Q2 FAIL 가능성

**조치 필요**
Q2 `old_val IS NOT NULL` 검증에 `change_action = 'create'`인 경우 예외 처리 추가 검토.

---

### [I-7] annotation.line.create — 단일 이벤트 내 혼합 object_type ℹ️

**현상**
1개의 `annotation.line.create` 이벤트 내에 `line`과 `point` 두 가지 object_type이 혼재.

```
event_id: 1c2a6660 (annotation.line.create)
  change_idx=0, object_type='line',  object_id=65
  change_idx=1, object_type='point', object_id=63
  change_idx=2, object_type='point', object_id=64
```

기존 파이프라인은 단일 object_type(bbox3d) 기준으로 설계되어 이 패턴이 처음 등장함.

**영향**
- stg_event_changes STRUCT 스키마 파싱 자체는 문제없음 (object_type: STRING이므로)
- int 레이어나 분석 쿼리에서 object_type별 집계 시 line / point 분리 로직 필요
- 향후 분석 정의 시 "1 이벤트 = 1 line + N points" 구조 인지 필요

---

### [I-8] 수집 요청 이력 미등록 — 프로세스 선후 관계 미확인 🚨

**현상**
`docs/collection_requests.md` 수집 요청 이력에 ld feature 관련 항목이 없음.
정상 프로세스:
```
파이프라인 반영 완료 → 앱 배포 → QA 수행 → Spot Check
```

**영향**
파이프라인 미반영 상태에서 앱이 배포되었을 가능성.
이 경우 파이프라인 미반영 상태에서 로그가 적재됐을 가능성이 있음 (역적재 불가, Raw 원본 기준 확인 필요).

**조치 필요**
1. App Engineer에 ld 로그 배포 일정 및 파이프라인 반영 통보 수령 여부 확인
2. 수집 요청 이력에 ld 항목 소급 등록
3. Spot Check 실행 전 파이프라인 반영 순서 재확인

---

## 검증 시뮬레이션 결과

파이프라인 기존 검증(04a/04b 기준) 대입 결과:

| 검증 | 항목 | 결과 | 사유 |
|------|------|------|------|
| C1 | Raw ↔ Stg 건수 정합 | ⚠️ 조건부 | I-2: raw 적재 방식에 따라 달라짐 |
| C2 | changes 완전성 | ❌ FAIL | I-5: params 필드 없어 검증 기준 없음 |
| C3 | 이벤트 스트림 갭 | ✅ 정보성 | 이상 없음 |
| C4 | undo 시간 역전 | N/A | undo/redo 이벤트 없음 |
| C5 | select 없는 transform | N/A | select/transform 이벤트 없음 |
| Q1 | orphan undo | N/A | undo/redo 이벤트 없음 |
| Q2 | NULL 규칙 | ❌ FAIL | I-6: old_val=null 가능성 |
| Q3 | 중복 여부 | ✅ PASS | event_id + change_idx 중복 없음 |
| Q4 | position 구조 무결성 | N/A | position 필드 없는 새 object_type |

---

## 다음 단계 권고

1. **App Engineer 확인 (우선)**
   - CloudEvent JSON 형식 통일 여부 확인 → I-2 해결
   - `params.createCount` 등 완전성 검증용 필드 추가 → I-5 해결

2. **파이프라인 반영 (App Engineer 확인 후)**
   - `docs/collection_requests.md` 수집 요청 이력 등록
   - (필요시) ld 전용 raw 적재 경로 설계

3. **검증 기준 보완**
   - Q2 `old_val IS NOT NULL` 에 create action 예외 처리 검토
   - C2 ld 전용 완전성 검증 기준 정의
