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
- Gen1 / Gen2 피처 간 행동 비교

---

## 데이터 레이어 구조

```
[소스: Zerobus/Kafka]
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  RAW 레이어  labelit_raw                                │
│  raw_labelit__workspace_command                         │
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
│  - feature_gen 분류 (Gen1/Gen2/unknown)                 │
│  - occurred_at 기준 증분 INSERT                         │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  INTERMEDIATE 레이어  labelit_int                       │
│                                                         │
│  int_labelit__effective_changes  ← is_reverted 플래그  │
│  int_labelit__bbox3d_transforms  ← 3D 이동 거리 계산   │
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

| 레이어 | 테이블명 | 설명 | 고유키 |
|--------|---------|------|--------|
| Raw | `raw_labelit__workspace_command` | CloudEvent 원본 JSON (od/od2) | `event_id` |
| Raw | `raw_labelit__ld` | ld feature 로그 — pre-exploded 컬럼 구조 | `(event_id, change_idx)` |
| Stg | `stg_labelit__events` | annotation 이벤트 파싱 결과 | `event_id` |
| Stg | `stg_labelit__event_changes` | changes 배열 행 단위 전개 | `(event_id, change_idx)` |
| Stg | `stg_labelit__undo_history` | undo/redo 이벤트 | `event_id` |
| Int | `int_labelit__effective_changes` | is_reverted 플래그 포함 | `(event_id, change_idx)` |
| Int | `int_labelit__bbox3d_transforms` | 3D 이동 거리 | `(event_id, change_idx)` |

---

## 디렉터리 구조

```
Log_samples/
│
├── README.md                                     ← 이 파일
│
├── docs/                                         ← 프로세스 및 정책 문서
│   ├── overview.md                               과업 목적, 목표, 핵심 컨셉 개요
│   ├── collection_requests.md                    수집 정책, 프로세스 흐름, 수집 요청 이력
│   ├── command_spec_template.md                  신규 커맨드 스펙 정의 템플릿 (Labelit Engineer 작성)
│   └── agents/                                   ← Role / Agent 문서
│       ├── role_rules__labelit_engineer.md           Labelit Engineer 역할 규칙
│       ├── role_rules__qa_tester.md              QA/Tester 역할 규칙
│       ├── role_rules__nova_engineer.md          Nova Engineer 역할 규칙
│       ├── scenario__case1_initialize.md         검증 시나리오 1: Feature workspace 초기 셋업
│       ├── scenario__case2_new_command.md        검증 시나리오 2: 신규 기능/커맨드 추가
│       ├── scenario__case3_ux_change.md          검증 시나리오 3: UI/UX 기반 사용자 플로우 변경
│       └── cross_validation.md                   에이전트 간 교차 검증 결과
│
├── notebooks/                                    ← Databricks 실행 노트북 (SQL)
│   ├── 01_raw__workspace_command.sql             Raw 레이어 증분 MERGE (od/od2)
│   ├── 01_raw__ld.sql                            Raw 레이어 증분 INSERT (ld — pre-exploded 컬럼 구조)
│   ├── 02_stg__events.sql                        Staging — annotation.* 이벤트 파싱
│   ├── 02_stg__event_changes.sql                 Staging — changes 배열 행 단위 EXPLODE
│   ├── 02_stg__undo_history.sql                  Staging — history.undo/redo 분리
│   ├── 03_int__effective_changes.sql             Intermediate — is_reverted 플래그 계산
│   ├── 03_int__bbox3d_transforms.sql             Intermediate — 3D 이동 거리 계산
│   ├── 04a_validate__completeness.sql            완전성 검증 (C1~C5)
│   ├── 04b_validate__quality.sql                 품질 검증 (Q1~Q4)
│   └── 05_spot_check__command_arrival.sql        신규 커맨드 도달 확인 (수동 실행)
│
├── models/                                       ← [샘플] 초기 dbt 모델 원본 (참고용)
│   ├── raw/labelit/
│   │   ├── _raw_labelit__models.yml              dbt 모델 정의 (raw 레이어)
│   │   └── raw_labelit__workspace_command.sql    Raw 레이어 dbt 모델
│   ├── staging/labelit/
│   │   ├── _sources.yml                          dbt 소스 정의
│   │   ├── _stg_labelit__models.yml              dbt 모델 정의 (staging 레이어)
│   │   ├── stg_labelit__events.sql               Staging 이벤트 파싱 모델
│   │   ├── stg_labelit__event_changes.sql        Staging changes EXPLODE 모델
│   │   ├── stg_labelit__event_changes_temp.sql   [샘플] 임시 변환 모델 (작업용)
│   │   └── stg_labelit__undo_history.sql         Staging undo/redo 모델
│   └── intermediate/labelit/
│       ├── _int_labelit__models.yml              dbt 모델 정의 (intermediate 레이어)
│       ├── int_labelit__effective_changes.sql    is_reverted 플래그 계산 모델
│       ├── int_labelit__bbox3d_transforms.sql    3D 이동 거리 계산 모델
│       └── int_labelit__undo_links.sql           undo 연결 관계 모델
│
├── raw_datas/                                    ← [샘플] CloudEvent JSON 샘플 (12개)
│   ├── 00_dfdbda29_history.undo.json
│   ├── 01_7c069578_annotation.object.select.json
│   ├── 02_bf7317b6_annotation.bbox3d.transform.json
│   ├── 03_c12f39f1_annotation.bbox3d.transform.json
│   ├── 04_b0095b1f_annotation.bbox3d.transform.json
│   ├── 05_b139f4f4_annotation.bbox3d.transform.json
│   ├── 06_4234fb43_annotation.object.select.json
│   ├── 07_3c0930fb_annotation.object.select.json
│   ├── 08_13b9cb86_annotation.bbox3d.transform.json
│   ├── 09_fc2849f8_annotation.object.select.json
│   ├── 10_9e7f783e_annotation.bbox3d.transform.json
│   └── 11_7687c6a7_annotation.object.select.json
│
├── tables/                                       ← [샘플] 레이어별 CSV 출력 샘플
│   ├── raw_labelit__ld.csv                       ld feature Raw 입력 데이터
│   ├── stg_labelit__events.csv
│   ├── stg_labelit__event_changes.csv
│   ├── stg_labelit__undo_history.csv
│   ├── int_labelit__effective_changes.csv
│   ├── int_labelit__undo_links.csv
│   ├── stg_labelit__ld__events.csv               ld feature Staging 결과
│   ├── stg_labelit__ld__event_changes.csv        ld feature Staging changes 결과
│   ├── int_labelit__ld__effective_changes.csv    ld feature Intermediate 결과
│   └── pipeline_report__ld.md                    ld 파이프라인 처리 이슈 리포트
│
└── int_layer.py                                  ← 로컬 Python 처리 스크립트
```

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
    "user": {
      "id": "usr-0001",
      "name": "labeler_01"
    },
    "project": {
      "task_id": "task-9999"
    },
    "params": { "updateCount": 2 },
    "changes": [
      {
        "object_id": 101,
        "object_type": "bbox3d",
        "action": "update",
        "old": { "position": { "x": 1.0, "y": 2.0, "z": 0.5 }, ... },
        "new": { "position": { "x": 1.5, "y": 2.5, "z": 0.5 }, ... }
      }
    ]
  }
}
```

> **`time` vs `occurred_at`**
> - `time`: 클라이언트 발생 시각 (배치 전송으로 오차 있음, 파이프라인 증분 기준 제외)
> - `occurred_at`: 서버 수신 시각 (모든 레이어 증분 적재 기준)

### feature_gen 분류

파이프라인은 `data.feature` 값으로 세대를 구분합니다.

| feature 값 | feature_gen | 설명 |
|-----------|-------------|------|
| `"od"` | `Gen1` | 1세대 피처 |
| `"od2"` | `Gen2` | 2세대 피처 |
| 그 외 | `unknown` | 신규 Gen 추가 또는 이상 데이터 → 스펙 확인 필요 |

### Command Stack (undo/redo 대상)

커맨드는 **Command Stack** 포함 여부에 따라 처리가 달라집니다.

| 커맨드 타입 | Command Stack | Staging 테이블 |
|-------------|:---:|----------------|
| `annotation.bbox3d.transform` | ✅ 해당 | `stg_labelit__events` (취소 가능) |
| `annotation.object.select` | ❌ 비해당 | `stg_labelit__events` (취소 불가) |
| `history.undo` | ❌ 비해당 | `stg_labelit__undo_history` |
| `history.redo` | ❌ 비해당 | `stg_labelit__undo_history` |

### is_reverted 플래그

`int_labelit__effective_changes`에서 각 변경이 실제로 적용된 상태인지를 나타냅니다.

```
is_reverted = TRUE  조건:
  해당 event_id 가 undo 대상이고, redo 로 복원되지 않은 경우

계산 방법 (EXCEPT 연산):
  undone  = {undo 대상 event_id 집합}
  redone  = {redo 로 복원된 event_id 집합}
  reverted = undone EXCEPT redone
```

> is_reverted=TRUE 행은 삭제하지 않고 보존 — 행동 분석에 활용 가능

### changes 배열과 EXPLODE

`annotation.*` 이벤트의 `data.changes` 배열은 Staging에서 행 단위로 전개됩니다.

```
이벤트 1건 (changes 배열 크기 = N)
        │
        ▼
stg_labelit__event_changes: N개 행
  (event_id, change_idx=0), (event_id, change_idx=1), ...
```

검증: `params.updateCount` (또는 `selectedCount`) = `changes` 배열 원소 수 (C2 시나리오)

---

## 파이프라인 실행 순서

배치 실행 시 아래 순서를 준수합니다.

```
[1] 01_raw__workspace_command  ┐
    01_raw__ld                 ┘ 병렬 실행 가능 (소스 독립적)
    ↓ Raw 레이어 증분 MERGE/INSERT 완료

[2] 02_stg__events           ┐
    02_stg__event_changes    ├─ 병렬 실행 가능
    02_stg__undo_history     ┘
    ↓ Staging 전 테이블 적재 완료

[3] 03_int__effective_changes    ┐
    03_int__bbox3d_transforms    ┘ Staging 완료 후 실행 (CREATE OR REPLACE)
    ↓ Intermediate 계산 완료

[4] 04a_validate__completeness   ← Staging 완전성 검증 (C1~C5)
    04b_validate__quality        ← 품질 검증 (Q1~Q4)

[5] 05_spot_check__command_arrival  ← 신규 커맨드 시 수동 실행 (1회성)
```

> **카탈로그 설정**: 각 노트북 상단 `USE CATALOG sv_nova_dev_an2_catalog;`
> 카탈로그 변경 시 이 한 줄만 수정하면 모든 쿼리에 자동 반영

---

## 검증 시스템

### 04a — 완전성 검증 (Completeness)

> 실행 빈도: 배치 실행마다 (02_stg 완료 후)

| 시나리오 | 검증 내용 | 판정 기준 |
|----------|-----------|-----------|
| **C1** | Raw ↔ Staging 건수 정합성 | `raw = stg_events + stg_undo` → 0 차이 PASS |
| **C2** | changes EXPLODE 완전성 | `params 기대 건수 = 실제 행 수` → 0행 PASS |
| **C3** | 이벤트 스트림 갭 탐지 | 30분 초과 갭 목록 반환 (정보성, PASS/FAIL 없음) |
| **C4** | undo 시간 역전 (event_time) | undo가 원본보다 먼저 발생 → 0행 PASS |
| **C4-B** | undo 시간 역전 (occurred_at) | C4 역전 발견 시 재검증 기준 |
| **C5** | 세션 내 커맨드 시퀀스 | select 없는 transform → 0행 PASS |

### 04b — 품질 검증 (Quality)

> 실행 빈도: 배치 실행마다 (03_int 완료 후)

| 시나리오 | 검증 내용 | 판정 기준 |
|----------|-----------|-----------|
| **Q1** | orphan undo 탐지 | reverted_event_id 매칭 실패 → 0행 PASS |
| **Q2** | Staging NULL 규칙 (11개) | 3개 테이블 필수 필드 NULL/empty/unknown → 0행 PASS |
| **Q3** | 증분 적재 중복 | event_id 또는 (event_id, change_idx) 중복 → 0행 PASS |
| **Q4** | transform position 구조 무결성 | position 필드 누락 → 0행 PASS |

**Q2 규칙 상세 (11개)**

| 테이블 | 규칙 |
|--------|------|
| `stg_labelit__events` | event_type, feature_gen(unknown 포함), user_id, task_id, session_id |
| `stg_labelit__event_changes` | change_action, old_val, new_val |
| `stg_labelit__undo_history` | reverted_event_id, reverted_command_type, session_id |

### 05 — Spot Check (신규 커맨드 도달 확인)

> 실행 빈도: 신규 커맨드 등록 후 1회 (수동 실행)

QA/Tester가 앱에서 시나리오를 수행한 뒤, Nova Engineer가 해당 이벤트의 Raw → Staging 도달을 확인합니다.

**Widget 파라미터**

| 파라미터 | 출처 | 비고 |
|----------|------|------|
| `target_feature_gen` | QA 전달 | Gen1 / Gen2 |
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

| # | feature_gen | event_type | Command Stack | 분석 목적 | 상태 |
|---|-------------|------------|:---:|-----------|------|
| 1 | Gen1 | `annotation.object.select` | ❌ | 라벨러 선택 행동 분석 | ✅ 완료 |
| 2 | Gen1 | `annotation.bbox3d.transform` | ✅ | 3D bbox 이동 거리 분석 | ✅ 완료 |
| 3 | Gen1 | `history.undo` | ❌ | 작업 취소 패턴 분석 | ✅ 완료 |
| 4 | Gen1 | `history.redo` | ❌ | redo 발생 여부 모니터링 | 🔄 모니터링 중 |
| 5 | Gen2 | `annotation.object.select` | ❌ | Gen2 선택 행동 분석 | 🔄 모니터링 중 |
| 6 | Gen2 | `annotation.bbox3d.transform` | ✅ | Gen2 3D bbox 이동 분석 | 🔄 모니터링 중 |
| 7 | Gen2 | `history.undo` | ❌ | Gen2 취소 패턴 분석 | 🔄 모니터링 중 |
| 8 | Gen2 | `history.redo` | ❌ | Gen2 redo 모니터링 | 🔄 모니터링 중 |
| 9 | ld (Gen 미정의) | `annotation.line.create` | ❓ | ld 차선 경계선 생성 | ⏳ 반영 대기 |
| 10 | ld (Gen 미정의) | `annotation.lane.create` | ❓ | ld 차선 생성 | ⏳ 반영 대기 |
| 11 | ld (Gen 미정의) | `annotation.topology.create` | ❓ | ld 차선 연결관계 생성 | ⏳ 반영 대기 |

> ❓ Command Stack 여부 미확인 (undo 이벤트 미관측) — Labelit Engineer 확인 필요
> ld feature는 raw 데이터 포맷이 기존과 상이 (`raw_labelit__ld` 전용 테이블 사용)

신규 커맨드 추가 시 → `docs/command_spec_template.md` 및 `docs/collection_requests.md` 참고

---

## 역할 및 프로세스

### 3개 역할

| 역할 | 환경 | 핵심 책임 |
|------|------|-----------|
| **Labelit Engineer** | Labelit 개발 환경 | CloudEvent 로그 구현 및 배포 |
| **QA / Tester** | Labelit 앱 | 정의된 커맨드를 플로우대로 동작 테스트 |
| **Nova Engineer** | Databricks | 수집 정의 반영, 파이프라인 실행, 도달 검증 |

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
> 순서가 뒤바뀌면 해당 커맨드의 `feature_gen`이 `'unknown'`으로 적재될 수 있음

---

## 문서 가이드

| 문서 | 대상 독자 | 내용 |
|------|-----------|------|
| `docs/overview.md` | 전체 | 과업 목적, 목표하는 결과, 핵심 컨셉, 파이프라인 구조 개요 |
| `docs/collection_requests.md` | 전체 | 수집 정책, 프로세스 흐름도, 수집 이력 테이블 |
| `docs/command_spec_template.md` | Labelit Engineer | 신규 커맨드 스펙 작성 템플릿 + 예시 3종 + 배포 전 체크리스트 |
| `docs/agents/role_rules__labelit_engineer.md` | Labelit Engineer | 구현·배포 워크플로우, CloudEvent 필수 필드, 실패 처리 |
| `docs/agents/role_rules__qa_tester.md` | QA/Tester | 시나리오 수행 기준, 기록 양식, 책임 범위 |
| `docs/agents/role_rules__nova_engineer.md` | Nova Engineer | 파이프라인 반영 체크리스트, Spot Check 실행 가이드, 검증 판정 기준, FAIL 처리 절차 |
| `docs/agents/scenario__case1_initialize.md` | 전체 | 검증 시나리오 1 — Feature workspace 초기 셋업 및 로그 수집 initialize |
| `docs/agents/scenario__case2_new_command.md` | 전체 | 검증 시나리오 2 — 신규 기능/커맨드 추가 |
| `docs/agents/scenario__case3_ux_change.md` | 전체 | 검증 시나리오 3 — UI/UX 기반 사용자 플로우 변경 |
| `docs/agents/cross_validation.md` | 전체 | 에이전트 간 교차 검증 결과 및 공통 보완 사항 |

---

## 용어 정리

| 용어 | 설명 |
|------|------|
| **CloudEvent** | Labelit 앱이 커맨드 실행 시 발행하는 표준 이벤트 (v1.0) |
| **feature_gen** | 피처 세대 분류 — Gen1(`od`) / Gen2(`od2`) / unknown |
| **Command Stack** | undo/redo 취소·복원 대상이 되는 커맨드 여부 |
| **is_reverted** | 해당 변경이 undo로 취소되고 redo로 복원되지 않은 상태 (`TRUE` = 취소됨) |
| **changes** | 하나의 커맨드 이벤트에서 변경된 오브젝트 목록 (배열) |
| **occurred_at** | 서버 수신 시각 — 증분 적재 기준값 |
| **event_time** | 클라이언트 발생 시각 — 배치 전송 지연으로 오차 있음 |
| **Spot Check** | 신규 커맨드가 Raw → Staging까지 정상 도달했는지 확인하는 1회성 검증 |
| **orphan undo** | reverted_event_id 가 stg_labelit__events에 없는 undo 이벤트 |
