# 커맨드 로그 스펙 정의서

**작성 주체**: App Engineer
**전달 대상**: Data Engineer
**작성 시점**: 신규 커맨드 로그 구현 완료 후, Data Engineer에게 수집 반영 요청 시

---

## 작성 방법

아래 템플릿을 복사하여 커맨드별로 하나씩 작성.
완성 후 Data Engineer에게 전달하면 Data Engineer가 파이프라인에 반영.

---

## 커맨드 스펙 템플릿

```
──────────────────────────────────────────────────────────
커맨드 로그 스펙 정의서
──────────────────────────────────────────────────────────

[기본 정보]
  feature_value    :          ← 실제 feature 필드값 (예: od, rmd, ld)
  event_type       :          ← CloudEvent type (예: annotation.bbox3d.transform)
  발생 조건        :          ← 어떤 사용자 액션 시 이벤트가 발생하는지 서술
  Command Stack    :          ← undo/redo 대상 여부 (해당 / 비해당)

[CloudEvent 구조]
  specversion  : "1.0"
  id           : <UUID>
  source       : <앱 소스 경로>
  type         : <event_type 과 동일>
  time         : <ISO 8601, 클라이언트 발생 시각>
  dataschema   : <스키마 URL (없으면 생략)>
  sessionid    : <세션 식별자>
  data:
    feature      :            ← feature_value 와 동일
    user:
      id         :            ← 사용자 고유 식별자 (파이프라인에서 user_id 컬럼으로 파싱)
      name       :            ← 사용자 계정명 (파이프라인에서 user_name 컬럼으로 파싱)
    project:
      task_id    :            ← 태스크 ID
    params       :            ← (있을 경우) 파라미터 구조 기술
    changes      : []         ← 변경 배열 (없으면 빈 배열)

[changes 배열 원소 구조]
  ※ changes 가 없는 커맨드는 이 항목 생략

  {
    "object_id"   : <INT>,
    "object_type" : "<문자열>",
    "action"      : "<create | update | delete>",
    "old"         : { <변경 전 필드 구조> },
    "new"         : { <변경 후 필드 구조> }
  }

  old / new 필드 구조:
    ← 실제 old/new 에 포함되는 키 목록과 타입을 기술
    ← 예: { "position": {"x": Float, "y": Float, "z": Float},
              "rotation": {"x": Float, "y": Float, "z": Float},
              "size":     {"x": Float, "y": Float, "z": Float} }

[params 구조]
  ※ params 가 없는 커맨드는 이 항목 생략

    ← params 에 포함되는 키 목록과 타입을 기술
    ← 예: { "updateCount": INT }   ← changes 배열 원소 수와 일치해야 함

[QA 시나리오]
  QA/Tester 가 이 커맨드를 발생시키기 위해 수행할 앱 액션:
    ←  (예: bbox3d 오브젝트를 드래그하여 위치를 이동시킨다)

──────────────────────────────────────────────────────────
```

---

## 작성 예시 — `annotation.bbox3d.transform` (od)

```
──────────────────────────────────────────────────────────
커맨드 로그 스펙 정의서
──────────────────────────────────────────────────────────

[기본 정보]
  feature_value    : od
  event_type       : annotation.bbox3d.transform
  발생 조건        : 3D 바운딩 박스 오브젝트를 이동·회전·크기 변경할 때 발생
  Command Stack    : 해당 (undo/redo 대상)

[CloudEvent 구조]
  specversion  : "1.0"
  id           : "550e8400-e29b-41d4-a716-446655440000"
  source       : "/labelit/workspace/od"
  type         : "annotation.bbox3d.transform"
  time         : "2026-03-24T04:32:10.123Z"
  dataschema   : (없음)
  sessionid    : "sess-abc123"
  data:
    feature      : "od"
    user:
      id         : "usr-0001"
      name       : "labeler_01"
    project:
      task_id    : "task-9999"
    params       : { "updateCount": 2 }
    changes      : [ ... ]   ← 아래 구조 참고

[changes 배열 원소 구조]
  {
    "object_id"   : 101,
    "object_type" : "bbox3d",
    "action"      : "update",
    "old"         : {
      "position": {"x": 1.0, "y": 2.0, "z": 0.5},
      "rotation": {"roll": 0.0, "pitch": 0.0, "yaw": 45.0},
      "size":     {"length": 4.51, "width": 1.804, "height": 1.589}
    },
    "new"         : {
      "position": {"x": 1.5, "y": 2.5, "z": 0.5},
      "rotation": {"roll": 0.0, "pitch": 0.0, "yaw": 45.0},
      "size":     {"length": 4.51, "width": 1.804, "height": 1.589}
    }
  }

  old / new 필드 구조:
    position : { x: Float, y: Float, z: Float }              ← 3D 좌표
    rotation : { roll: Float, pitch: Float, yaw: Float }     ← 오일러각 (도 단위)
    size     : { length: Float, width: Float, height: Float } ← 각 축 길이

[params 구조]
  { "updateCount": INT }   ← changes 배열 원소 수와 반드시 일치

[QA 시나리오]
  QA/Tester 가 이 커맨드를 발생시키기 위해 수행할 앱 액션:
    bbox3d 오브젝트를 선택한 뒤 드래그하여 위치를 이동시킨다.
    (2개 이상 이동 시 changes 배열 원소 수가 updateCount 와 같은지 확인)

──────────────────────────────────────────────────────────
```

---

## 작성 예시 — `annotation.object.select` (od)

```
──────────────────────────────────────────────────────────
커맨드 로그 스펙 정의서
──────────────────────────────────────────────────────────

[기본 정보]
  feature_value    : od
  event_type       : annotation.object.select
  발생 조건        : 라벨링 오브젝트를 클릭 또는 범위 선택할 때 발생
  Command Stack    : 비해당 (undo/redo 대상 아님)

[CloudEvent 구조]
  specversion  : "1.0"
  id           : "550e8400-e29b-41d4-a716-446655440001"
  source       : "/labelit/workspace/od"
  type         : "annotation.object.select"
  time         : "2026-03-24T04:31:55.000Z"
  dataschema   : (없음)
  sessionid    : "sess-abc123"
  data:
    feature      : "od"
    user:
      id         : "usr-0001"
      name       : "labeler_01"
    project:
      task_id    : "task-9999"
    params       : { "selectedCount": 1 }
    changes      : [ ... ]

[changes 배열 원소 구조]
  {
    "object_id"   : 101,
    "object_type" : "bbox3d",
    "action"      : "update",
    "old"         : { "selectedTrackingIds": [] },
    "new"         : { "selectedTrackingIds": [1] }
  }

  old / new 필드 구조:
    selectedTrackingIds : Array<INT>  ← 선택된 오브젝트 trackingId 배열 (선택 전: [], 선택 후: [id, ...])

[params 구조]
  { "selectedCount": INT }   ← changes 배열 원소 수와 반드시 일치

[QA 시나리오]
  QA/Tester 가 이 커맨드를 발생시키기 위해 수행할 앱 액션:
    3D 뷰어에서 bbox3d 오브젝트를 클릭하여 선택 상태로 만든다.

──────────────────────────────────────────────────────────
```

---

## 작성 예시 — `history.undo` (od)

```
──────────────────────────────────────────────────────────
커맨드 로그 스펙 정의서
──────────────────────────────────────────────────────────

[기본 정보]
  feature_value    : od
  event_type       : history.undo
  발생 조건        : Ctrl+Z 또는 툴바 undo 버튼 클릭 시 발생
  Command Stack    : 비해당 (undo 자체는 스택에 쌓이지 않음)

[CloudEvent 구조]
  specversion  : "1.0"
  id           : "550e8400-e29b-41d4-a716-446655440002"
  source       : "/labelit/workspace/od"
  type         : "history.undo"
  time         : "2026-03-24T04:32:30.000Z"
  dataschema   : (없음)
  sessionid    : "sess-abc123"
  data:
    feature      : "od"
    user:
      id         : "usr-0001"
      name       : "labeler_01"
    project:
      task_id    : "task-9999"
    reverted_command_id   : "550e8400-e29b-41d4-a716-446655440000"  ← 취소 대상 이벤트 ID (평탄화 필드)
    reverted_command_type : "UpdateBbox3dTransformCommand"           ← 취소 대상 커맨드 클래스명
    count                 : 1                                        ← 되돌린 단계 수

[changes 배열 원소 구조]
  없음 (changes 는 항상 빈 배열 — history.undo/redo 는 changes 없음)

[params 구조]
  없음

[QA 시나리오]
  QA/Tester 가 이 커맨드를 발생시키기 위해 수행할 앱 액션:
    오브젝트 이동 등 변경 액션 수행 후 Ctrl+Z 를 눌러 취소한다.
    undo 직전에 수행한 커맨드의 event_id 가 reverted_command_id 와 일치하는지 확인.

──────────────────────────────────────────────────────────
```

---

## 작성 예시 — `annotation.line.create` (ld)

```
──────────────────────────────────────────────────────────
커맨드 로그 스펙 정의서
──────────────────────────────────────────────────────────

[기본 정보]
  feature_value    : ld
  event_type       : annotation.line.create
  발생 조건        : 차선 경계선(line) 오브젝트를 생성할 때 발생.
                     1개의 line + N개의 point가 동일 event_id의 changes 배열에 포함됨.
  Command Stack    : (미확인 — undo 이벤트 미관측)

[Raw 포맷 특이사항]
  기존 od/od2와 달리 CloudEvent JSON(_raw)이 아닌 파싱·분해된 컬럼 구조로 발행됨.
  1 이벤트 = N행 (changes 원소 수만큼 pre-exploded).
  누락 필드: subject, dataschema, user_name, dataset_id, action, input_type, targets, params

[changes 배열 원소 구조]
  -- change_idx = 0: line 오브젝트
  {
    "object_id"   : <INT>,           ← line trackingId
    "object_type" : "line",
    "action"      : "create",
    "old"         : null,            ← create 액션은 항상 null
    "new"         : {
      "trackingId" : <INT>,
      "pointCount" : <INT>,          ← 이 line에 속한 point 수
      "isClosed"   : <Boolean>
    }
  }

  -- change_idx = 1~N: point 오브젝트 (pointCount 수만큼 반복)
  {
    "object_id"   : <INT>,           ← point trackingId
    "object_type" : "point",
    "action"      : "create",
    "old"         : null,
    "new"         : {
      "trackingId" : <INT>
    }
  }

[params 구조]
  없음 (미포함 — App Engineer 확인 필요: createCount 등 추가 여부)

[QA 시나리오]
  QA/Tester 가 이 커맨드를 발생시키기 위해 수행할 앱 액션:
    ld 워크스페이스에서 차선 경계선을 그린다 (포인트 2개 이상 지정).
    생성된 line의 change_idx=0이 line 오브젝트, 이후 idx가 point임을 확인.

──────────────────────────────────────────────────────────
```

---

## 작성 예시 — `annotation.lane.create` (ld)

```
──────────────────────────────────────────────────────────
커맨드 로그 스펙 정의서
──────────────────────────────────────────────────────────

[기본 정보]
  feature_value    : ld
  event_type       : annotation.lane.create
  발생 조건        : 좌·우 경계선(line)을 지정하여 차선(lane) 오브젝트를 생성할 때 발생.
                     lane은 기존 line 오브젝트를 참조(trackingId)하여 boundaries를 구성함.
  Command Stack    : (미확인 — undo 이벤트 미관측)

[changes 배열 원소 구조]
  {
    "object_id"   : <INT>,           ← lane trackingId
    "object_type" : "lane",
    "action"      : "create",
    "old"         : null,
    "new"         : {
      "trackingId" : <INT>,
      "boundaries" : {
        "left"  : {
          "trackingId"            : <INT>,   ← 좌측 경계선 line trackingId
          "startPointTrackingId"  : <INT>,   ← 시작 point trackingId
          "endPointTrackingId"    : <INT>    ← 끝 point trackingId
        },
        "right" : {
          "trackingId"            : <INT>,
          "startPointTrackingId"  : <INT>,
          "endPointTrackingId"    : <INT>
        }
      },
      "subClassId" : "<String>"      ← 차선 서브 클래스 ID (MongoDB ObjectId)
    }
  }

[params 구조]
  없음 (미포함)

[QA 시나리오]
  QA/Tester 가 이 커맨드를 발생시키기 위해 수행할 앱 액션:
    ld 워크스페이스에서 좌·우 경계선을 각각 지정하여 차선을 생성한다.
    생성된 lane의 boundaries.left / right가 기존 line trackingId를 참조하는지 확인.

──────────────────────────────────────────────────────────
```

---

## 작성 예시 — `annotation.topology.create` (ld)

```
──────────────────────────────────────────────────────────
커맨드 로그 스펙 정의서
──────────────────────────────────────────────────────────

[기본 정보]
  feature_value    : ld
  event_type       : annotation.topology.create
  발생 조건        : 두 차선(lane) 사이의 연결관계(topology)를 생성할 때 발생.
                     sourceTrackingId → destinationTrackingId 방향의 단방향 연결.
  Command Stack    : (미확인 — undo 이벤트 미관측)

[changes 배열 원소 구조]
  {
    "object_id"   : <INT>,           ← topology trackingId
    "object_type" : "topology",
    "action"      : "create",
    "old"         : null,
    "new"         : {
      "trackingId"            : <INT>,
      "sourceTrackingId"      : <INT>,   ← 출발 lane trackingId
      "destinationTrackingId" : <INT>    ← 도착 lane trackingId
    }
  }

[params 구조]
  없음 (미포함)

[QA 시나리오]
  QA/Tester 가 이 커맨드를 발생시키기 위해 수행할 앱 액션:
    ld 워크스페이스에서 차선 연결 도구를 사용하여 두 차선을 연결한다.
    source → destination 방향이 의도한 방향과 일치하는지 확인.

──────────────────────────────────────────────────────────
```

---

## App Engineer 배포 전 체크리스트

신규 커맨드 로그 구현 완료 후 Data Engineer에게 스펙을 전달하고,
**Data Engineer로부터 파이프라인 반영 완료 통보를 받은 뒤** 앱을 배포합니다.

| # | 확인 항목 |
|---|-----------|
| 1 | CloudEvent 구조가 이 문서의 스펙 템플릿과 일치하는지 확인 |
| 2 | `data.user.id`, `data.user.name`, `data.project.task_id` 필드가 정확히 구현됐는지 확인 |
| 3 | `params.updateCount` (transform) / `params.selectedCount` (select) 값이 `changes` 배열 크기와 일치하는지 확인 |
| 4 | Command Stack 해당 커맨드에서 `reverted_command_id` / `reverted_command_type` / `count` 필드가 포함됐는지 확인 |
| 5 | Data Engineer로부터 파이프라인 반영 완료 통보 수신 확인 후 배포 진행 |

> **배포 순서 주의**: 파이프라인 반영 완료 통보 수신 후 배포해야 합니다.

---

## 커맨드 목록 현황

Data Engineer가 현재 수집 정의에 반영한 커맨드 목록.
신규 커맨드 추가 시 이 표에도 항목을 추가하고 스펙 정의서를 함께 전달.

| feature | event_type | Command Stack | 수집 상태 |
|---------|------------|---------------|-----------|
| od | annotation.object.select | 비해당 | ✅ 수집 중 |
| od | annotation.bbox3d.transform | 해당 | ✅ 수집 중 |
| od | history.undo | 비해당 | ✅ 수집 중 |
| od | history.redo | 비해당 | ✅ 수집 중 |
| rmd | annotation.object.select | 비해당 | ✅ 수집 중 |
| rmd | annotation.bbox3d.transform | 해당 | ✅ 수집 중 |
| rmd | history.undo | 비해당 | ✅ 수집 중 |
| rmd | history.redo | 비해당 | ✅ 수집 중 |
| ld | annotation.line.create | 미확인 | ⏳ 반영 대기 |
| ld | annotation.lane.create | 미확인 | ⏳ 반영 대기 |
| ld | annotation.topology.create | 미확인 | ⏳ 반영 대기 |
