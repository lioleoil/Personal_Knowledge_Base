# Labelit — Databricks Command Log Pipeline

Labelit 라벨링 도구의 워크스페이스 커맨드 로그를 수집·변환·검증하는 Databricks 기반 데이터 파이프라인입니다.
사용자가 라벨링 작업 중 수행하는 커맨드(오브젝트 선택, 3D bbox 이동, undo/redo 등)를
CloudEvents 1.0 형식으로 수신하여 분석 가능한 형태로 가공합니다.

---

## 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [데이터 레이어 구조](#데이터-레이어-구조)
3. [디렉터리 구조](#디렉터리-구조)
4. [핵심 컨셉](#핵심-컨셉)
5. [파이프라인 실행 순서](#파이프라인-실행-순서)
6. [검증 시스템](#검증-시스템)
7. [수집 커맨드 목록](#수집-커맨드-목록)
8. [역할 및 프로세스](#역할-및-프로세스)
9. [문서 가이드](#문서-가이드)
10. [용어 정리](#용어-정리)

---

## 프로젝트 개요

### 목적

| 항목 | 내용 |
|------|------|
| **수집 대상** | Labelit 워크스페이스에서 발생하는 커맨드 이벤트 |
| **이벤트 형식** | CloudEvents 1.0 (JSON) |
| **실행 환경** | Databricks (Unity Catalog) |
| **카탈로그** | `sv_nova_dev_an2_catalog` |
| **스키마 구조** | `labelit_raw` / `labelit_stg` / `labelit_int` / `labelit_mart` |

### 분석 목적

- 라벨러의 오브젝트 선택 행동 패턴 분석
- 3D bbox 이동 거리 및 빈도 분석
- 작업 취소(undo) 패턴 분석
- 피처별(od, rmd, ld) 행동 비교

---

## 데이터 레이어 구조

```
[소스: Zerobus / Kafka]
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  RAW 레이어  labelit_raw                                │
│  raw_labelit__workspace_command  (od, rmd 이벤트)       │
│  raw_labelit__ld                 (ld feature 전용)       │
│  - CloudEvent JSON 원본 보존 (_raw 컬럼)                │
│  - 파싱 없음, 1:1 미러링                                │
│  - occurred_at 기준 증분 MERGE                          │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  STAGING 레이어  labelit_stg                            │
│                                                         │
│  stg_labelit__events          ← annotation.* 이벤트    │
│  stg_labelit__event_changes   ← changes 배열 EXPLODE   │
│  stg_labelit__undo_history    ← history.undo/redo       │
│                                                         │
│  - JSON 파싱 완료                                       │
│  - event_category 분류 (select/transform/create/other)  │
│  - CREATE OR REPLACE (전체 재계산)                      │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  INTERMEDIATE 레이어  labelit_int                       │
│                                                         │
│  int_labelit__effective_changes  ← is_reverted 플래그  │
│  int_labelit__bbox3d_transforms  ← 3D 이동 거리/분류   │
│                                                         │
│  - 비즈니스 로직 적용                                   │
│  - CREATE OR REPLACE (전체 재계산)                      │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  MART 레이어  labelit_mart                              │
│  (분석 목적별 집계 테이블)                              │
└─────────────────────────────────────────────────────────┘
```

### 주요 테이블

| 레이어 | 테이블명 | 설명 | 고유키 | 갱신 전략 |
|--------|---------|------|--------|-----------|
| Raw | `raw_labelit__workspace_command` | CloudEvent 원본 JSON (od/rmd) | `event_id` | 증분 MERGE |
| Raw | `raw_labelit__ld` | ld feature — pre-exploded 컬럼 구조 | `(event_id, change_idx)` | 증분 MERGE |
| Stg | `stg_labelit__events` | annotation.* 이벤트 JSON 파싱 | `event_id` | CREATE OR REPLACE |
| Stg | `stg_labelit__event_changes` | changes 배열 행 단위 전개 | `(event_id, change_idx)` | CREATE OR REPLACE |
| Stg | `stg_labelit__undo_history` | history.undo/redo 이벤트 | `event_id` | CREATE OR REPLACE |
| Int | `int_labelit__effective_changes` | is_reverted 플래그 포함 | `(event_id, change_idx)` | CREATE OR REPLACE |
| Int | `int_labelit__bbox3d_transforms` | position/rotation/size 파싱 + 이동 거리·분류 | `(event_id, change_idx)` | CREATE OR REPLACE |

---

## 디렉터리 구조

```
nova_log_analytics/
│
├── README.md                                     ← 이 파일
│
├── docs/                                         ← 프로세스 및 정책 문서
│   ├── overview.md                               과업 목적, 목표, 핵심 컨셉 개요
│   ├── collection_requests.md                    수집 정책, 프로세스 흐름, 수집 요청 이력
│   ├── command_spec_template.md                  신규 커맨드 스펙 정의 템플릿 (App Engineer 작성)
│   ├── nova_rules/                               ← Nova 개발 규칙 문서 (DIC-788 기준)
│   │   ├── naming_rules.md                           파일/테이블/컬럼 네이밍 규칙
│   │   ├── connectors_rules.md                       커넥터 사용 규칙
│   │   ├── deployment_rules.md                       배포 규칙
│   │   └── sql-notebooks_rules.md                    SQL 노트북 작성 규칙
│   └── agents/                                   ← Role / Agent 문서
│       ├── role_rules__labelit_engineer.md           Labelit Engineer 역할 규칙
│       ├── role_rules__qa_tester.md                  QA/Tester 역할 규칙
│       ├── role_rules__nova_engineer.md              Nova Engineer 역할 규칙
│       ├── scenario__case1_initialize.md             검증 시나리오 1: Feature workspace 초기 셋업
│       ├── scenario__case2_new_command.md            검증 시나리오 2: 신규 기능/커맨드 추가
│       ├── scenario__case3_ux_change.md              검증 시나리오 3: UI/UX 기반 사용자 플로우 변경
│       └── cross_validation.md                       에이전트 간 교차 검증 결과
│
├── notebooks/                                    ← Databricks 실행 노트북 (SQL)
│   ├── 01_raw__workspace_command.sql             Raw 레이어 증분 MERGE (od/rmd)
│   ├── 01_raw__ld.sql                            Raw 레이어 증분 MERGE (ld — pre-exploded)
│   ├── 02_stg__events.sql                        Staging — annotation.* 이벤트 파싱 (CREATE OR REPLACE)
│   ├── 02_stg__event_changes.sql                 Staging — changes 배열 EXPLODE (CREATE OR REPLACE)
│   ├── 02_stg__undo_history.sql                  Staging — history.undo/redo 분리 (CREATE OR REPLACE)
│   ├── 03_int__effective_changes.sql             Intermediate — is_reverted 플래그 계산
│   ├── 03_int__bbox3d_transforms.sql             Intermediate — position/rotation/size 파싱 + 이동 거리
│   ├── 04a_validate__completeness.sql            완전성 검증 (C1~C5)
│   ├── 04b_validate__quality.sql                 품질 검증 (Q1~Q4)
│   ├── 05_spot_check__command_arrival.sql        신규 커맨드 도달 확인 (수동 실행)
│   ├── template__stg.sql                         Staging 노트북 템플릿
│   └── template__int.sql                         Intermediate 노트북 템플릿
│
├── raw_datas/                                    ← [샘플] CloudEvent JSON 샘플 (12개)
│   ├── 00_dfdbda29_history.undo.json
│   ├── 01_7c069578_annotation.object.select.json
│   ├── 02_bf7317b6_annotation.bbox3d.transform.json
│   └── ... (총 12개)
│
├── tables/                                       ← [샘플] 레이어별 CSV 출력 샘플
│   ├── raw_labelit__ld.csv                       ld feature Raw 입력 데이터
│   ├── stg_labelit__events.csv
│   ├── stg_labelit__event_changes.csv
│   ├── stg_labelit__undo_history.csv
│   ├── int_labelit__effective_changes.csv
│   ├── int_labelit__undo_links.csv               undo 연결 관계 (int_layer.py 로컬 출력)
│   ├── stg_labelit__ld__events.csv               ld feature Staging 결과 (로컬 출력)
│   ├── stg_labelit__ld__event_changes.csv        ld feature Staging changes 결과 (로컬 출력)
│   ├── int_labelit__ld__effective_changes.csv    ld feature Intermediate 결과 (로컬 출력)
│   └── pipeline_report__ld.md                    ld 파이프라인 처리 이슈 리포트
│
├── int_layer.py                                  ← 로컬 Python 처리 — od/rmd 중간 레이어 시뮬레이션
└── run_ld_pipeline.py                            ← 로컬 Python 처리 — ld feature 파이프라인 시뮬레이션
```

> **int_layer.py / run_ld_pipeline.py**: Databricks 환경 없이 로컬에서 중간 레이어 처리를 검증하기 위한 스크립트. 프로덕션 파이프라인은 `notebooks/` 의 SQL 노트북을 사용한다.

---

## 핵심 컨셉

### CloudEvent 1.0 구조

Labelit 앱이 발행하는 이벤트는 CloudEvents 1.0 형식을 따릅니다.

```json
{
  "specversion": "1.0",
  "id": "<UUID>",
  "source": "/labelit/workspace/od",
  "type": "annotation.bbox3d.transform",
  "time": "2026-03-24T04:32:10.123Z",
  "sessionid": "sess-abc123",
  "data": {
    "feature": "od",
    "user": { "id": "usr-0001", "name": "labeler_01" },
    "project": { "task_id": "task-9999" },
    "params": { "updateCount": 2 },
    "changes": [
      {
        "object_id": 101,
        "object_type": "bbox3d",
        "action": "update",
        "old": { "position": {"x": 1.0, "y": 2.0, "z": 0.5}, ... },
        "new": { "position": {"x": 1.5, "y": 2.5, "z": 0.5}, ... }
      }
    ]
  }
}
```

> **`time` vs `occurred_at`**
> - `time`: 클라이언트 발생 시각 (배치 전송으로 오차 있음, 파이프라인 증분 기준 제외)
> - `occurred_at`: 서버 수신 시각 (Raw 레이어 증분 MERGE 기준)

### feature 값과 수집 대상

파이프라인은 `data.feature` 값으로 피처를 구분합니다.

| feature 값 | 설명 | Raw 테이블 |
|-----------|------|------------|
| `"od"` | Object Detection (3D bbox) | `raw_labelit__workspace_command` |
| `"rmd"` | RMD (Object Detection 계열) | `raw_labelit__workspace_command` |
| `"ld"` | Lane Detection (차선 어노테이션) | `raw_labelit__ld` (전용 테이블) |

> **ld feature 주의**: 로그 포맷이 기존(CloudEvent JSON)과 다름. 앱에서 이미 파싱·분해된 컬럼 구조(1행 = 1 change)로 발행됨 → `raw_labelit__ld` 전용 테이블로 분리 관리.

### event_category

Staging에서 `event_type` 을 기반으로 파생하는 분류 컬럼입니다.

| event_type | event_category |
|------------|----------------|
| `annotation.object.select` | `select` |
| `annotation.bbox3d.transform` | `transform` |
| `annotation.line.create`, `annotation.lane.create`, `annotation.topology.create` | `create` |
| 그 외 | `other` |

### Command Stack (undo/redo 대상)

커맨드는 **Command Stack** 포함 여부에 따라 처리가 달라집니다.

| 커맨드 타입 | Command Stack | Staging 테이블 |
|-------------|:---:|----------------|
| `annotation.bbox3d.transform` | ✅ 해당 | `stg_labelit__events` (취소 가능) |
| `annotation.object.select` | ❌ 비해당 | `stg_labelit__events` (취소 불가) |
| `history.undo` | ❌ 비해당 | `stg_labelit__undo_history` |
| `history.redo` | ❌ 비해당 | `stg_labelit__undo_history` |

### is_reverted 플래그

`int_labelit__effective_changes`에서 각 변경이 최종적으로 취소된 상태인지를 나타냅니다.

```
is_reverted = TRUE  조건:
  해당 event_id 가 undo 대상이고, redo 로 복원되지 않은 경우

계산 방법 (EXCEPT 연산):
  undone  = {is_redo=FALSE인 reverted_event_id 집합}
  redone  = {is_redo=TRUE인 reverted_event_id 집합}
  reverted = undone EXCEPT redone
```

> is_reverted=TRUE 행은 삭제하지 않고 플래그로 보존 — "얼마나 수정·취소했는가" 행동 분석에 활용 가능

### changes 배열과 EXPLODE

`annotation.*` 이벤트의 `data.changes` 배열은 Staging에서 행 단위로 전개됩니다.

```
이벤트 1건 (changes 배열 크기 = N)
        │
        ▼
stg_labelit__event_changes: N개 행
  (event_id, change_idx=0), (event_id, change_idx=1), ...
```

검증: `params.updateCount` (transform) 또는 `params.selectedCount` (select) = `changes` 배열 원소 수 (C2 시나리오)

### int_labelit__bbox3d_transforms

`annotation.bbox3d.transform` 이벤트의 `old_val` / `new_val` JSON을 파싱하여 위치·자세·크기 필드를 추출하고 3D 유클리드 이동 거리를 계산합니다.

| move_category | 기준 |
|---------------|------|
| 미세조정 | move_distance < 0.1 |
| 소폭이동 | 0.1 ≤ move_distance < 1.0 |
| 중폭이동 | 1.0 ≤ move_distance < 3.0 |
| 대폭이동 | move_distance ≥ 3.0 |

---

## 파이프라인 실행 순서

배치 실행 시 아래 순서를 준수합니다.

```
[1] 01_raw__workspace_command  ┐
    01_raw__ld                 ┘ 병렬 실행 가능 (소스 독립적)
    ↓ Raw 레이어 증분 MERGE 완료

[2] 02_stg__events           ┐
    02_stg__event_changes    ├─ 병렬 실행 가능 (소스: raw 레이어)
    02_stg__undo_history     ┘
    ↓ Staging 전 테이블 CREATE OR REPLACE 완료

[3] 03_int__effective_changes    ┐
    03_int__bbox3d_transforms    ┘ Staging 완료 후 실행 (CREATE OR REPLACE)
    ↓ Intermediate 계산 완료

[4] 04a_validate__completeness   ← Staging 완전성 검증 (C1~C5)
    04b_validate__quality        ← 품질 검증 (Q1~Q4)

[5] 05_spot_check__command_arrival  ← 신규 커맨드 시 수동 실행 (1회성)
```

> **카탈로그 설정**: 각 노트북에서 `${catalog}` 위젯으로 주입  
> dev: `sv_nova_dev_an2_catalog` / prod: `sv_nova_prod_an2_catalog`

---

## 검증 시스템

### 04a — 완전성 검증 (Completeness)

> 실행 빈도: 배치 실행마다 (02_stg 완료 후)

| 시나리오 | 검증 내용 | 판정 기준 |
|----------|-----------|-----------|
| **C1** | Raw ↔ Staging 건수 정합성 | `raw_cnt = stg_events + stg_undo` → diff = 0 PASS |
| **C2** | changes EXPLODE 완전성 | `params 기대 건수 = 실제 explode 행 수` → 0행 PASS |
| **C3** | 이벤트 스트림 갭 탐지 | 30분 초과 갭 목록 반환 (정보성 — PASS/FAIL 없음) |
| **C4** | undo 시간 역전 (event_time) | undo가 원본보다 먼저 발생 → 0행 PASS |
| **C4-B** | undo 시간 역전 (occurred_at) | C4 역전 발견 시 occurred_at 기준 재검증 |
| **C5** | 세션 내 커맨드 시퀀스 | 선행 select 없는 transform → 0행 PASS |

### 04b — 품질 검증 (Quality)

> 실행 빈도: 배치 실행마다 (03_int 완료 후)

| 시나리오 | 검증 내용 | 판정 기준 |
|----------|-----------|-----------|
| **Q1** | orphan undo 탐지 | reverted_event_id 매칭 실패 → 0행 PASS |
| **Q2** | Staging 전 테이블 필수 필드 NULL 규칙 (10개) | 3개 테이블 필수 필드 NULL/empty → 0행 PASS |
| **Q3** | 증분 적재 중복 | event_id 또는 (event_id, change_idx) 중복 → 0행 PASS |
| **Q4** | transform position 구조 무결성 | position 필드 누락 → 0행 PASS |

**Q2 규칙 상세 (10개)**

| 테이블 | 규칙 |
|--------|------|
| `stg_labelit__events` (4개) | event_type, user_id, task_id, session_id |
| `stg_labelit__event_changes` (3개) | change_action, old_val (create 제외), new_val |
| `stg_labelit__undo_history` (3개) | reverted_event_id, reverted_command_type, session_id |

> `stg_event_changes`의 `old_val` 규칙: `change_action = 'create'`인 경우 old_val=NULL이 정상 (신규 생성) → 해당 행 제외

### 05 — Spot Check (신규 커맨드 도달 확인)

> 실행 빈도: 신규 커맨드 등록 후 1회 (수동 실행)

QA/Tester가 앱에서 시나리오를 수행한 뒤, Nova Engineer가 해당 이벤트의 Raw → Staging 도달을 확인합니다.

**Widget 파라미터**

| 파라미터 | 출처 | 비고 |
|----------|------|------|
| `target_feature_gen` | QA 전달 | 피처 값 (od / rmd / ld) |
| `target_event_type` | QA 전달 | 수행한 커맨드 타입 |
| `target_session_id` | QA 전달 | 수행 세션 ID (빈값 = 전체) |
| `target_user_name` | QA 전달 | 수행 계정명 (빈값 = 전체) |
| `target_task_id` | QA 전달 | 작업 태스크 ID (빈값 = 전체) |
| `action_time_from/to` | QA action_date 변환 | 예: "오전" → 00:00:00~12:00:00 |

**판정 결과**

| 결과 | 의미 | 다음 액션 |
|------|------|-----------|
| ✅ PASS | Raw 도달 + Staging 전량 반영 | 이력 "완료" 업데이트 → 04a/b 정기 검증 이관 |
| ⚠️ PARTIAL | Raw 도달 + 일부 미반영 | 02_stg 재실행 후 재확인 |
| ❌ FAIL (Raw) | Raw 미도달 | 앱 이벤트 발생 여부 / Zerobus 상태 확인 |
| ❌ FAIL (Stg) | Raw 도달 + 전체 미반영 | 02_stg 실행 여부 확인 |

---

## 수집 커맨드 목록

현재 수집 중인 커맨드 11종:

| # | feature | event_type | Command Stack | 분석 목적 | 상태 |
|---|---------|------------|:---:|-----------|------|
| 1 | od | `annotation.object.select` | ❌ | 라벨러 선택 행동 분석 | ✅ 완료 |
| 2 | od | `annotation.bbox3d.transform` | ✅ | 3D bbox 이동 거리 분석 | ✅ 완료 |
| 3 | od | `history.undo` | ❌ | 작업 취소 패턴 분석 | ✅ 완료 |
| 4 | od | `history.redo` | ❌ | redo 발생 여부 모니터링 | 🔄 모니터링 중 |
| 5 | rmd | `annotation.object.select` | ❌ | rmd 선택 행동 분석 | 🔄 모니터링 중 |
| 6 | rmd | `annotation.bbox3d.transform` | ✅ | rmd 3D bbox 이동 분석 | 🔄 모니터링 중 |
| 7 | rmd | `history.undo` | ❌ | rmd 취소 패턴 분석 | 🔄 모니터링 중 |
| 8 | rmd | `history.redo` | ❌ | rmd redo 발생 여부 모니터링 | 🔄 모니터링 중 |
| 9 | ld | `annotation.line.create` | ❓ | ld 차선 경계선 생성 | ⏳ 반영 대기 |
| 10 | ld | `annotation.lane.create` | ❓ | ld 차선 생성 | ⏳ 반영 대기 |
| 11 | ld | `annotation.topology.create` | ❓ | ld 차선 연결관계 생성 | ⏳ 반영 대기 |

> ❓ Command Stack 여부 미확인 (undo 이벤트 미관측) — App Engineer(Labelit Engineer) 확인 필요  
> ld feature는 Raw 데이터 포맷이 기존(CloudEvent JSON)과 상이 → `raw_labelit__ld` 전용 테이블 사용  
> ld 항목(9~11): 스펙 문서 및 공식 수집 요청 등록 전 파이프라인 유입 — 정식 절차 소급 적용 필요

신규 커맨드 추가 시 → `docs/command_spec_template.md` 및 `docs/collection_requests.md` 참고

---

## 역할 및 프로세스

### 3개 역할

| 역할 | 환경 | 핵심 책임 |
|------|------|-----------|
| **Labelit Engineer** (= App Engineer) | Labelit 개발 환경 | CloudEvent 로그 구현 및 배포 |
| **QA / Tester** | Labelit 앱 | 정의된 커맨드를 플로우대로 수행 후 세션 정보 전달 |
| **Nova Engineer** (= Data Engineer) | Databricks | 수집 정의 반영, 파이프라인 실행, 도달 검증 |

### 신규 커맨드 등록 프로세스

```
[Labelit Engineer]          [Nova Engineer]           [QA/Tester]
      │                       │                        │
  ① 로그 구현                │                        │
  ② 스펙 정의서 작성          │                        │
  ③ 스펙 전달 ──────────→ ④ 파이프라인 반영           │
                              ↓                        │
  ⑤ 앱 배포 ←── 반영 완료 통보                        │
      │                       │                        │
      └──────────────────────────────→ ⑥ 시나리오 수행 │
                              │        ⑦ 세션 정보 전달 ┘
                              │              │
                         ⑧ Spot Check ←─────┘
                              │
                         ⑨ 정기 검증 이관 (04a/b)
```

> **핵심 순서 제약**: 앱 배포(⑤)는 반드시 파이프라인 반영 완료 통보(④) 이후에 진행  
> 순서가 뒤바뀌면 해당 커맨드 이벤트가 파이프라인에 미반영 상태로 유입됨

---

## 문서 가이드

| 문서 | 대상 독자 | 내용 |
|------|-----------|------|
| `docs/overview.md` | 전체 | 과업 목적, 목표하는 결과, 핵심 컨셉, 파이프라인 구조 개요 |
| `docs/collection_requests.md` | 전체 | 수집 정책, 프로세스 흐름도, 수집 요청 이력 테이블 |
| `docs/command_spec_template.md` | Labelit Engineer | 신규 커맨드 스펙 작성 템플릿 + 예시 5종 + 배포 전 체크리스트 |
| `docs/nova_rules/naming_rules.md` | Nova Engineer | 파일/테이블/컬럼/리소스 네이밍 규칙 (DIC-788) |
| `docs/agents/role_rules__labelit_engineer.md` | Labelit Engineer | 구현·배포 워크플로우, CloudEvent 필수 필드, 실패 처리 |
| `docs/agents/role_rules__qa_tester.md` | QA/Tester | 시나리오 수행 기준, 기록 양식, 책임 범위 |
| `docs/agents/role_rules__nova_engineer.md` | Nova Engineer | 파이프라인 반영 체크리스트, Spot Check 실행 가이드, 검증 판정 기준, FAIL 처리 절차 |
| `docs/agents/scenario__case1_initialize.md` | 전체 | 검증 시나리오 1 — Feature workspace 초기 셋업 |
| `docs/agents/scenario__case2_new_command.md` | 전체 | 검증 시나리오 2 — 신규 기능/커맨드 추가 |
| `docs/agents/scenario__case3_ux_change.md` | 전체 | 검증 시나리오 3 — UI/UX 기반 사용자 플로우 변경 |
| `docs/agents/cross_validation.md` | 전체 | 에이전트 간 교차 검증 결과 및 공통 보완 사항 |

---

## 용어 정리

| 용어 | 설명 |
|------|------|
| **CloudEvent** | Labelit 앱이 커맨드 실행 시 발행하는 표준 이벤트 (v1.0) |
| **feature** | 라벨링 피처 값 — od / rmd / ld 등 |
| **event_category** | event_type 기반 파생 분류 — select / transform / create / other |
| **Command Stack** | undo/redo 취소·복원 대상이 되는 커맨드 여부 |
| **is_reverted** | 해당 변경이 undo로 취소되고 redo로 복원되지 않은 상태 (`TRUE` = 취소됨) |
| **is_redo** | undo_history 레코드에서 undo(`FALSE`) / redo(`TRUE`) 구분 |
| **changes** | 하나의 커맨드 이벤트에서 변경된 오브젝트 목록 (배열) |
| **occurred_at** | 서버 수신 시각 — Raw 레이어 증분 MERGE 기준값 |
| **event_time** | 클라이언트 발생 시각 — 배치 전송 지연으로 오차 있음 (분석 시 주의) |
| **Spot Check** | 신규 커맨드가 Raw → Staging까지 정상 도달했는지 확인하는 1회성 검증 |
| **orphan undo** | reverted_event_id가 stg_labelit__events에 없는 undo 이벤트 |
| **move_distance** | 3D 유클리드 이동 거리 (bbox3d.transform 전용) |
| **move_category** | 이동 거리 분류 — 미세조정 / 소폭이동 / 중폭이동 / 대폭이동 |
