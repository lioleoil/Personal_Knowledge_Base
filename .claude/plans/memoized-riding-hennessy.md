# Labelit 커맨드 로그 수집 정책 및 프로세스 플랜

## Context

기존 04a/b/c 검증 노트북은 **이미 적재된 데이터**를 검증하는 것에 집중.
그 전제인 "수집 대상이 올바르게 등록되고 실제로 파이프라인에 흘러들어왔는가"를
보장하는 **프로세스**가 없는 상태.

신규 커맨드 추가 또는 수집 이상 발생 시 누가, 어떻게, 무엇을 확인해야 하는지
정의하고, 앱에서 실제 액션을 수행한 뒤 로그 도달을 추적하는 spot check 노트북이 필요.

---

## 3단계 수집 정책 프로세스

```
[Step 1] 수집 요청
  요청자 → docs/collection_requests.md 에 요청 항목 기재
  (feature_gen, event_type, 목적, 요청자, 요청일)

         ↓

[Step 2] 수집 정의 반영  (담당 엔지니어)
  ① 00_setup 커맨드 주석 업데이트
  ② 04a defined_commands VALUES 블록에 항목 추가
  ③ (신규 Gen 추가 시) stg 레이어 feature_gen CASE 문 수정

         ↓

[Step 3] 시나리오 액션 기반 확인
  ① 검증자가 Labelit 앱에서 해당 커맨드 액션 직접 수행
     → 수행 시각·task_id·user 기록
  ② 05_spot_check__command_arrival.sql 실행
     → Raw 도달 여부 → Staging 반영 여부 → 단계별 소요 시간 확인
  ③ PASS → 04a/b/c 정기 검증으로 이관
```

---

## 생성 파일

```
docs/
└── collection_requests.md                   ← [NEW] 수집 요청 이력 + 프로세스 가이드

notebooks/
└── 05_spot_check__command_arrival.sql       ← [NEW] 시나리오 액션 기반 도달 확인
```

---

## `docs/collection_requests.md` 설계

**역할**: 수집 요청 이력 관리 + 프로세스 체크리스트

**포함 내용**:
1. 3단계 프로세스 요약 (개요)
2. 수집 요청 템플릿 (feature_gen / event_type / 목적 / 요청일 / 요청자 / 상태)
3. 수집 요청 이력 테이블 (누적 기록)
4. 반영 체크리스트 (Step 2 시 담당자가 확인할 항목)
5. 액션 수행 가이드 (Step 3-① 시 기록할 정보 안내)

---

## `05_spot_check__command_arrival.sql` 설계

### Widget 파라미터

| Widget | 예시값 | 설명 |
|--------|--------|------|
| `catalog` | `sv_nova_dev_an2_catalog` | Databricks 카탈로그 |
| `target_feature_gen` | `Gen1` | 확인할 세대 |
| `target_event_type` | `annotation.bbox3d.transform` | 확인할 커맨드 타입 |
| `action_time_from` | `2026-03-24 04:30:00` | 앱 액션 수행 시작 시각 |
| `action_time_to` | `2026-03-24 04:45:00` | 앱 액션 수행 종료 시각 |
| `target_user_name` | `test_owner` (빈값 = 전체) | 수행 계정 (선택) |
| `target_task_id` | `` (빈값 = 전체) | 작업 태스크 ID (선택) |

### 노트북 셀 구성

**CELL 1: 파라미터 확인 및 검증 대상 요약**
```sql
-- 입력된 파라미터를 그대로 출력해 검증자가 확인
SELECT
  '${target_feature_gen}' AS feature_gen,
  '${target_event_type}'  AS event_type,
  '${action_time_from}'   AS from_time,
  '${action_time_to}'     AS to_time,
  '${target_user_name}'   AS user_filter,
  '${target_task_id}'     AS task_filter;
```

**CELL 2: Raw 도달 확인**
```sql
-- 시간 범위 내 해당 커맨드가 Raw에 도달했는지
SELECT
  _id AS event_id,
  get_json_object(_raw, '$.type')              AS event_type,
  get_json_object(_raw, '$.data.feature')      AS feature,
  to_timestamp(get_json_object(_raw,'$.time')) AS event_time,   -- 클라이언트 시각
  to_timestamp(occurred_at)                    AS occurred_at,  -- 서버 수신 시각
  ROUND(UNIX_TIMESTAMP(occurred_at)
    - UNIX_TIMESTAMP(get_json_object(_raw,'$.time')), 1)        AS latency_sec,
  get_json_object(_raw, '$.data.user.name')    AS user_name,
  get_json_object(_raw, '$.data.project.task_id') AS task_id
FROM ${catalog}.labelit_raw.raw_labelit__workspace_command
WHERE get_json_object(_raw, '$.type')         = '${target_event_type}'
  AND get_json_object(_raw, '$.data.feature') = CASE '${target_feature_gen}'
        WHEN 'Gen1' THEN 'od' WHEN 'Gen2' THEN 'od2' END
  AND to_timestamp(occurred_at) BETWEEN '${action_time_from}' AND '${action_time_to}'
  AND ('${target_user_name}' = ''
       OR get_json_object(_raw,'$.data.user.name') = '${target_user_name}')
  AND ('${target_task_id}' = ''
       OR get_json_object(_raw,'$.data.project.task_id') = '${target_task_id}')
ORDER BY occurred_at;
```

**CELL 3: Staging 반영 확인**
```sql
-- Raw에 도달한 event_id가 stg_events / stg_undo_history 에도 있는지
WITH raw_events AS (
  SELECT _id AS event_id
  FROM ${catalog}.labelit_raw.raw_labelit__workspace_command
  WHERE get_json_object(_raw,'$.type') = '${target_event_type}'
    AND to_timestamp(occurred_at) BETWEEN '${action_time_from}' AND '${action_time_to}'
)
SELECT
  r.event_id,
  CASE WHEN e.event_id IS NOT NULL THEN 'stg_events 반영'
       WHEN u.event_id IS NOT NULL THEN 'stg_undo_history 반영'
       ELSE '미반영 (stg 적재 대기 또는 누락)'
  END AS staging_status,
  e.feature_gen,
  e.event_time,
  e.occurred_at
FROM raw_events r
LEFT JOIN ${catalog}.labelit_stg.stg_labelit__events e ON r.event_id = e.event_id
LEFT JOIN ${catalog}.labelit_stg.stg_labelit__undo_history u ON r.event_id = u.event_id
ORDER BY r.event_id;
```

**CELL 4: 도달 결과 요약**
```sql
-- Raw 건수 / Stg 반영 건수 / 미반영 건수 한 눈에 확인
WITH raw_cnt AS (
  SELECT COUNT(*) AS cnt FROM ${catalog}.labelit_raw.raw_labelit__workspace_command
  WHERE get_json_object(_raw,'$.type') = '${target_event_type}'
    AND to_timestamp(occurred_at) BETWEEN '${action_time_from}' AND '${action_time_to}'
),
stg_cnt AS (
  SELECT COUNT(*) AS cnt FROM ${catalog}.labelit_stg.stg_labelit__events
  WHERE event_type = '${target_event_type}'
    AND occurred_at BETWEEN '${action_time_from}' AND '${action_time_to}'
)
SELECT
  raw_cnt.cnt                            AS raw_도달_건수,
  stg_cnt.cnt                            AS stg_반영_건수,
  raw_cnt.cnt - stg_cnt.cnt             AS 미반영_건수,
  CASE
    WHEN raw_cnt.cnt = 0                 THEN 'FAIL — Raw 미도달 (파이프라인 또는 앱 확인)'
    WHEN raw_cnt.cnt = stg_cnt.cnt       THEN 'PASS — 전 단계 정상 반영'
    WHEN stg_cnt.cnt > 0                 THEN 'PARTIAL — 일부 미반영 (stg 재실행 필요)'
    ELSE                                      'FAIL — Stg 미반영 (02_stg 실행 확인)'
  END                                    AS result
FROM raw_cnt, stg_cnt;
```

---

## 전체 워크플로우 연결

```
수집 요청 등록
  docs/collection_requests.md 에 항목 추가

     ↓ [Step 2: 반영]

00_setup 주석 + 04a defined_commands 업데이트
01_raw ~ 03_int 실행

     ↓ [Step 3: 시나리오 액션]

검증자: Labelit 앱에서 해당 커맨드 수행 후 시각·세션 기록
  → 05_spot_check__command_arrival 실행

     ↓ PASS 시

04a_validate__definition    (D3: 정의 커맨드 전체 유입 확인)
04b_validate__completeness  (C1~C5: 완전성 확인)
04c_validate__quality       (Q1~Q4: 품질 확인)
```

---

## 수정 대상 기존 파일 없음

새 파일 2개만 추가. 기존 04a/b/c, 01~03 노트북 수정 없음.
(04a의 defined_commands 는 Step 2 반영 시 담당자가 수동 편집)
