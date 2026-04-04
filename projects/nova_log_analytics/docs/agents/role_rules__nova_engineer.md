# Role Rules — Nova Engineer

## 역할 개요

| 항목 | 내용 |
|------|------|
| **역할** | Nova Engineer |
| **환경** | Databricks |
| **핵심 책임** | 수집 정의 반영, 파이프라인 실행, 데이터 도달 검증 |

---

## 책임 범위

### 담당
- 신규 커맨드 스펙 수신 후 파이프라인에 반영
- 수집 요청 이력 관리 (`docs/collection_requests.md`)
- `01_raw` ~ `03_int` 파이프라인 실행 및 모니터링
- Spot Check 실행 (QA 수행 정보 기반)
- 04a/b 정기 검증 실행 및 이상 조사
- Labelit Engineer에게 파이프라인 반영 완료 통보

### 담당하지 않음
- 앱 커맨드 로그 구현 (Labelit Engineer 역할)
- 앱 배포 (Labelit Engineer 역할)
- QA 시나리오 수행 (QA/Tester 역할)

---

## 워크플로우

### 신규 커맨드 등록 시

```
① Labelit Engineer로부터 커맨드 스펙 정의서 수신
   - docs/command_spec_template.md 내용 확인
   - feature_value, event_type, data 구조, Command Stack 여부 파악

② 수집 요청 이력 등록
   - docs/collection_requests.md 이력 테이블에 항목 추가
   - 상태: ⏳ 반영 대기

③ 파이프라인 반영
   - 01_raw ~ 03_int 파이프라인 실행 확인

④ Labelit Engineer에게 반영 완료 통보
   - 반영 완료 후 Labelit Engineer에게 통보하여 앱 배포 진행 요청

⑤ QA로부터 테스트 세션 정보 수신 후 Spot Check 실행
   - 05_spot_check__command_arrival.sql 실행
   - QA가 전달한 session_id, user_id, user_name, task_id, action_date 기반으로 위젯 파라미터 입력
   - action_time_from/to: QA의 대략적 일시를 날짜 단위 범위로 변환 (예: 오전 → 00:00~12:00)

⑥ Spot Check 결과 처리
   - PASS → 이력 테이블 상태 "✅ 완료" 업데이트 → 04a/b 정기 검증 이관
   - FAIL → 아래 FAIL 처리 절차 참고
```

### 정기 배치 실행 순서

```
01_raw__workspace_command  ┐  Raw 레이어 증분 적재 (od/od2 — CloudEvent JSON)
01_raw__ld                 ┘  Raw 레이어 증분 적재 (ld — pre-exploded 컬럼 구조) ※ 병렬 실행 가능
02_stg__events                (Staging 이벤트 파싱)
02_stg__event_changes         (changes 배열 EXPLODE)
02_stg__undo_history          (undo/redo 분리)
03_int__effective_changes     (is_reverted 플래그 계산)
03_int__bbox3d_transforms     (3D 이동 거리 계산)
04a_validate__completeness    (C1~C5 완전성 검증)
04b_validate__quality         (Q1~Q4 품질 검증)
```

---

## 반영 체크리스트 (신규 커맨드 추가 시)

| # | 확인 항목 | 파일 |
|---|-----------|------|
| 1 | 수집 요청 이력 테이블에 항목 추가 | `docs/collection_requests.md` |
| 2 | (신규 event_type 추가 시) `event_category` CASE 문 수정 | `02_stg__events.sql` |
| 3 | (Raw 포맷이 다른 경우) 전용 Raw 노트북 생성 | `01_raw__<feature>.sql` |
| 4 | `01_raw` ~ `03_int` 파이프라인 실행 확인 | — |
| 5 | Labelit Engineer에게 반영 완료 통보 | — |

---

## Spot Check 실행 가이드

### 위젯 파라미터 입력

| 파라미터 | 입력값 출처 | 비고 |
|----------|-------------|------|
| `target_feature` | QA 전달 정보 | feature 값 (예: od, rmd, ld) |
| `target_event_type` | QA 전달 정보 | 수행한 커맨드 타입 |
| `target_session_id` | QA 전달 정보 | 수행 세션 ID |
| `target_user_name` | QA 전달 정보 | 수행 계정명 |
| `target_task_id` | QA 전달 정보 | 작업한 태스크 ID |
| `action_time_from` | QA action_date 변환 | 예: "오전" → 00:00:00 |
| `action_time_to` | QA action_date 변환 | 예: "오전" → 12:00:00 |

### PASS / FAIL 판정 기준

| 판정 | 조건 | 다음 액션 |
|------|------|-----------|
| ✅ PASS | Raw 도달 + Staging 전량 반영 | 이력 "✅ 완료" 업데이트 → 04a/b 이관 |
| ⚠️ PARTIAL | Raw 도달 + Staging 일부 미반영 | 02_stg 재실행 후 재확인 |
| ❌ FAIL (Raw) | Raw 미도달 | 아래 FAIL 처리 참고 |
| ❌ FAIL (Stg) | Raw 도달 + Staging 전체 미반영 | 02_stg 실행 여부 확인 |

---

## 검증 노트북 판정 기준

### 04a_validate__completeness (완전성)

| 시나리오 | 판정 기준 | 비고 |
|----------|-----------|------|
| C1: Raw-Staging 건수 | diff = 0 → PASS | 모든 stg 노트북 실행 완료 후 검증 |
| C2: changes EXPLODE | 0행 → PASS | params 없는 이벤트는 검증 제외 |
| C3: 스트림 갭 | 정보성 (PASS/FAIL 없음) | 30분 임계값, 비즈니스 판단 필요 |
| C4: undo 시간 역전 (event_time) | 0행 → PASS | 클라이언트 시계 오차 가능 |
| C4-B: undo 시간 역전 (occurred_at) | 0행 → PASS | C4 역전 발견 시 이 쿼리로 재검증 |
| C5: 선행 select 없는 transform | 0행 → PASS | 세션 시작 첫 transform은 정상일 수 있음 |

### 04b_validate__quality (품질)

| 시나리오 | 판정 기준 | 비고 |
|----------|-----------|------|
| Q1: orphan undo | 0행 → PASS | C1 누락 여부와 함께 조사 |
| Q2: NULL 규칙 | 0행 → PASS | NULL 발생 시 Labelit Engineer에게 스펙 확인 |
| Q3: 증분 중복 | 0행 → PASS | occurred_at 경계값 중복 처리 확인 |
| Q4: transform position 누락 | 0행 → PASS | rotation/size만 변경인 경우 의도적일 수 있음 |

---

## 핵심 규칙

1. **배포 통보 의무**: 파이프라인 반영 완료 시 반드시 Labelit Engineer에게 통보
2. **Spot Check 우선**: 신규 커맨드는 정기 검증 이전에 반드시 Spot Check PASS 확인
3. **이력 관리**: 모든 수집 요청을 `collection_requests.md` 이력 테이블에 기록
4. **C4-B 교차 검증**: C4에서 undo 역전 발견 시 C4-B로 서버 시간 기준 재검증 후 심각도 판단
5. **Q2 NULL 대응**: Q2 NULL 발생 시 → Labelit Engineer에게 스펙 확인 요청

---

## 인수인계 (Handoff)

| 방향 | 내용 | 수단 |
|------|------|------|
| ← Labelit Engineer | 커맨드 스펙 정의서 수신 | `docs/command_spec_template.md` |
| → Labelit Engineer | 파이프라인 반영 완료 통보 | 직접 통보 |
| ← QA / Tester | 테스트 세션 정보 수신 | 기록 양식 (session_id, user_id, task_id 등) |

---

## FAIL 처리 절차

### Raw 미도달 시
```
1. QA 수행 정보(session_id, task_id) 재확인 → 입력 오류 여부 점검
2. 앱 이벤트 발생 여부 확인 (Labelit Engineer와 협력)
3. Zerobus 커넥터 상태 확인
4. (참고) 미정의 커맨드인 경우에도 Raw 미도달로 나타남
   → event_type, feature 값이 스펙과 일치하는지 Labelit Engineer에게 확인
```

### Staging 미반영 시
```
1. history.undo / history.redo 이벤트 → 02_stg__undo_history.sql 재실행
2. 그 외 이벤트 → 02_stg__events.sql 재실행
3. 재실행 후 Q2 NULL 여부 확인
```

### Q2 NULL 발생 시
```
- user_id NULL  → Labelit Engineer에게 data.user.id 구현 여부 확인 요청
- feature 관련 NULL → Labelit Engineer에게 feature_value 스펙 확인 요청
- session_id NULL → 파이프라인 sessionid 파싱 경로 확인 ($.sessionid)
- old_val NULL (create 액션) → 정상. create 액션은 변경 전 상태가 없으므로 old_val=NULL 허용.
  Q2 old_val 검증은 change_action != 'create' 조건으로 제외됨 (04b_validate__quality.sql 참고).
```
