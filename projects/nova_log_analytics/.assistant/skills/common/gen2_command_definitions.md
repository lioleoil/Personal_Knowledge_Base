# 커맨드 정의서 (QA 커버리지 비교용)

> **목적**: QA 테스터가 수행한 커맨드와 정의된 전체 커맨드를 LLM이 비교 분석하여 누락 여부를 확인하기 위한 기준 문서  
> **원본 출처**: Labelit Engineer 제공 커맨드 수집 요청서  
> **총 섹션**: 6개 (Common / Cuboid / Point / Polygon / Polyline / Topology)
>
> | 수정 이력 | 내용 |
> |-----------|------|
> | 1차 수정 | C-3 Channel Change 미수집 수정 / CB-19 로그명·subclass name 보완 / CB-20 attribute 로그 추가 / Polywall class update 로그 오류 수정 / 그룹핑 object type 표기 통일 |
> | 1차 보완 | 공통 로그 필드 신설 — input_type·view 수집 / TP-1 Topology 생성 이벤트 범위 재정의 |
> | 2차 수집 | 공통 로그 필드 신설 — is_batch_mode 수집 |

---

## 목차

- [공통 로그 필드](#공통-로그-필드)
- [2.1 Common](#21-common)
  - [2.1.1 Contextual Action](#211-contextual-action)
  - [2.1.2 Tracking ID Group](#212-tracking-id-group)
- [2.2 Cuboid Action](#22-cuboid-action)
- [2.3 Point Action](#23-point-action)
- [2.4 Polygon Action](#24-polygon-action)
- [2.5 Polyline Action](#25-polyline-action)
- [2.6 Topology Action](#26-topology-action)

---

## 공통 로그 필드

> 모든 커맨드 액션에 공통으로 수집·기록되는 필드 (1차 보완·2차 수집 요구사항 반영)

| 필드명 | 값 예시 | 설명 | 근거 |
|--------|---------|------|------|
| `input_type` | `keyboard` / `mouse` | 커맨드 액션을 발생시킨 입력 수단 | 1차 보완 — 사용자 행동 패턴 및 UX/UI 분석 |
| `view` | `lidar` / `top` / `right` / `rear` / `height` / `image` | 액션이 발생한 Workspace UI View | 1차 보완 — View별 상호작용 분석 |
| `is_batch_mode` | `true` / `false` | 해당 액션이 Batch Mode에서 발생했는지 여부 | 2차 수집 — Batch Mode 기능 사용 빈도·임팩트·활성화 수준 분석 |

**적용 범위**: C-1(Task 진입)을 제외한 모든 커맨드 액션 로그에 포함.

---

## 2.1 Common

### 2.1.1 Contextual Action

> 모든 Feature에서 공통으로 발생하는 컨텍스트성 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| C-1 | **Task 진입** | - | All | - | - | 작업자가 Task에 진입할 때 발생하는 Context 정보 | 기록 필수 항목: task id / policy name·ver. / stage 정보 / 작업자 정보(id·authority·company) / 진입 세션 정보(동일 task stage 다회 접속 포함) / 진입 시간. 작업자별 Stage 구분 및 라벨링 공수 분석에 활용 |
| C-2 | **Frame 이동** | - | All | - | 키보드 또는 마우스 | 현재 작업 프레임을 다른 프레임으로 이동할 때 발생 | 이동 전후 프레임 정보(구간) 필수 기록. 직전 커맨드 실행 시간과의 차이 기록. Object 선택 상태 vs 미선택 상태 구분 필요 |
| C-3 | **Image Channel 이동** | - | All | Image Preview | 키보드 또는 마우스 | 현재 보고 있는 이미지 채널을 변경할 때 발생 | 이전 채널과 변경된 채널 정보(구간) 필수 기록. 직전 커맨드 실행 시간과의 차이 기록. **[1차 수정]** Image Preview에서 Channel Change 발생 시 입력 타입(keyboard/mouse)과 채널 정보가 기록되지 않던 문제 수정 — `input_type`·채널 정보 수집 필수 |
| C-4 | **Undo** | - | All | - | 키보드 (Ctrl+Z) | 직전 커맨드를 취소할 때 발생 | (TBU) 여러 단계를 한 번에 취소하는 Batch Undo는 별도 기록 필요 |
| C-5 | **Redo** | - | All | - | 키보드 (Ctrl+Shift+Z) | 취소한 커맨드를 다시 실행할 때 발생 | (TBU) 여러 단계를 한 번에 재실행하는 Batch Redo는 별도 기록 필요 |

---

### 2.1.2 Tracking ID Group

> OD / LD / Lane / Topology Feature의 Sidebar에서 Group 단위로 발생하는 커맨드
>
> **[1차 수정]** 그룹핑 관련 로그의 `object_type` 필드는 Feature에 관계없이 `annotation-group`으로 통일하여 기록한다. (기존: LD → `annotation-group`, OD → `annotationGroup` 으로 표기 불일치 → 단일화)

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| G-1 | **Group 생성** | 생성 | OD / LD / Lane / Topology | Sidebar | 마우스 (우클릭 → "Create Group") | 1개 이상의 Object를 선택한 상태에서 새로운 Group을 생성할 때 발생 | 생성된 Group ID와 포함된 Object ID 목록 기록 필요. Object 1개로 생성 가능하나 Task Done 시 멤버 1개 이하 Group은 자동 삭제됨 |
| G-2 | **Group에 Object 추가** | 수정 | OD / LD / Lane / Topology | Sidebar | 마우스 (우클릭 → "Add to Group") | Group 멤버가 아닌 Object를 기존 Group에 추가할 때 발생 | 추가된 Object ID와 대상 Group ID 기록 필요. Group을 다른 Group에 추가하는 경우(G-3)와 구분 필요 |
| G-3 | **Group에 Group 추가** | 수정 | OD / LD / Lane / Topology | Sidebar | 마우스 (우클릭 → "Add to Group") | 기존 Group을 다른 Group의 하위 Group으로 이동할 때 발생 (중첩 구조 형성) | 이동된 하위 Group ID와 상위 Group ID 기록 필요. G-2와 Input이 동일하므로 payload에서 대상 타입(Object/Group)으로 구분 필요 |
| G-4 | **Group에서 Object 제거** | 수정 | OD / LD / Lane / Topology | Sidebar | 마우스 (우클릭 → "Remove from Group") | Group에서 특정 Object를 제거할 때 발생. Object 자체는 삭제되지 않고 일반 Object로 유지됨 | 제거된 Object ID와 해당 Group ID 기록 필요 |
| G-5 | **Group 해제** | 삭제 | OD / LD / Lane / Topology | Sidebar | 마우스 (우클릭 → "Ungroup") | Group 구조를 해제할 때 발생. 멤버 Object는 삭제되지 않고 일반 Object로 유지됨 | 하위 Group이 있는 경우 하위 Group도 함께 해제됨. 해제된 Group ID 기록 필요 |
| G-6 | **Group 선택** | 선택 | OD / LD / Lane / Topology | Sidebar | 마우스 (클릭) | Sidebar에서 Group을 선택할 때 발생. Timeline에 Group 전체 멤버의 프레임 범위가 표시됨 | Group ID 기록 필요. Sub View는 기본 상태(Object 미선택)로 유지. G-7(Group 내 Object 선택)과 구분 필요 |
| G-7 | **Group 내 Object 선택** | 선택 | OD / LD / Lane / Topology | Sidebar | 마우스 (클릭) | Group 탭 Sidebar에서 Group 내 개별 Object를 선택할 때 발생 | 선택된 Object ID와 소속 Group ID 기록 필요. 현재 프레임에 없는 Dimmed 상태의 Object도 선택 가능. G-6(Group 선택)과 구분 필요 |
| G-8 | **Group 자동 삭제** | 삭제 | OD / LD / Lane / Topology | - | (Task Done 시 자동 발생) | Task Done 처리 시 멤버가 1개 이하인 불완전 Group이 자동 삭제될 때 발생. 멤버 Object가 있는 경우 Object는 일반 Object로 유지됨 | 자동 삭제된 Group ID 기록 필요. **사용자가 직접 트리거하는 커맨드가 아님 — 수집 방식 별도 확인 필요** |

---

## 2.2 Cuboid Action

> OD / SOD / TSTLD / RMD Feature의 LiDAR View 및 Sub View에서 Cuboid 단위로 발생하는 커맨드

### 생성 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| CB-1 | **Cuboid Tracking ID 신규 생성** | 생성 | OD / SOD / TSTLD | LiDAR View | 키보드 + 마우스 (Shift + 좌클릭) | 새로운 Cuboid를 최초로 생성할 때 발생. 신규 Tracking ID가 부여됨 | CB-4(Prediction 생성), CB-5(Interpolation 생성)와 반드시 구분하여 기록 |
| CB-2 | **Cuboid Split으로 Tracking ID 신규 생성** | 생성 | OD | LiDAR View | - | 하나의 Tracking ID를 특정 프레임 기준으로 두 개의 Tracking ID로 분리할 때 발생. 분리된 구간에 신규 Tracking ID가 부여된 Cuboid 생성 | CB-22(Cuboid Split) 커맨드 이후에만 발생 |
| CB-3 | **Cuboid Tracking ID 이어서 생성** | 생성 | OD / SOD | LiDAR View | 키보드 + 마우스 (Shift + 좌클릭) | 사용자가 직접 기존 Tracking ID를 이어받아 다음 프레임에 Cuboid를 생성할 때 발생 | CB-1(신규 생성), CB-4(Prediction 확정)와 구분하여 기록 |
| CB-4 | **Cuboid Prediction 생성 (점선 → 실선 확정)** | 생성 | OD / SOD | LiDAR View | 마우스 (더블클릭) 또는 크기/각도 조정 | Prediction 기능으로 점선 표시된 Cuboid를 작업자가 확정하여 실선으로 저장할 때 발생 | 커맨드는 확정 시점에 발생. 확정 없이 다음 프레임으로 이동하면 기록하지 않음. CB-1, CB-3과 반드시 구분하여 기록 |
| CB-5 | **Cuboid Interpolation 생성** | 생성 | OD / SOD | LiDAR View | 마우스 | 두 키프레임 사이 구간을 지정하여 Cuboid를 자동 보간 생성할 때 발생 | 보간 시작/종료 키프레임과 자동 생성된 총 프레임 수 기록 필요. Tool 자동 생성 vs 사용자 직접 수정 구분 필요 |
| CB-6 | **Cuboid 붙여넣기** | 생성 | OD / SOD / TSTLD / RMD | - | 키보드 (Ctrl+V) | 복사된 Cuboid를 현재 프레임에 붙여넣을 때 발생. 새로운 Object가 생성됨 | payload에 복사 원본 Tracking ID 포함하여 기록. 복사 커맨드는 별도 수집하지 않음 |

### 수정 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| CB-7 | **Cuboid 위치 조정** | 수정 | OD / SOD / TSTLD / RMD | LiDAR View | 키보드 또는 마우스 | Cuboid의 x, y 위치를 조정 | 마우스 조정과 키보드 조정 반드시 구분하여 기록 |
| CB-8 | **Cuboid 위치 조정** | 수정 | OD / SOD / TSTLD / RMD | Sub View - Top | 키보드 또는 마우스 | Cuboid의 x, y 위치를 조정 | 마우스 조정과 키보드 조정 반드시 구분하여 기록 |
| CB-9 | **Cuboid 위치 조정** | 수정 | OD / SOD / TSTLD / RMD | Sub View - Right | 키보드 또는 마우스 | Cuboid의 x, z 위치를 조정 | 마우스 조정과 키보드 조정 반드시 구분하여 기록 |
| CB-10 | **Cuboid 위치 조정** | 수정 | OD / SOD / TSTLD / RMD | Sub View - Rear | 키보드 또는 마우스 | Cuboid의 y, z 위치를 조정 | 마우스 조정과 키보드 조정 반드시 구분하여 기록 |
| CB-11 | **Cuboid 각도 조정 (yaw)** | 수정 | OD / SOD / TSTLD / RMD | LiDAR View | 키보드 + 마우스 | Cuboid의 회전값(yaw)을 조정 | - |
| CB-12 | **Cuboid 각도 조정 (yaw)** | 수정 | OD / SOD / TSTLD / RMD | Sub View - Top | 키보드 | Cuboid의 회전값(yaw)을 조정 | - |
| CB-13 | **Cuboid 각도 조정 (pitch)** | 수정 | OD / SOD / TSTLD / RMD | Sub View - Right | 키보드 | Cuboid의 회전값(pitch)을 조정 | - |
| CB-14 | **Cuboid 각도 조정 (roll)** | 수정 | OD / SOD / TSTLD / RMD | Sub View - Rear | 키보드 | Cuboid의 회전값(roll)을 조정 | - |
| CB-15 | **Cuboid 크기 조정 (width/length)** | 수정 | OD / SOD / TSTLD / RMD | LiDAR View | 키보드 + 마우스 | Cuboid의 너비, 길이를 조정 | - |
| CB-16 | **Cuboid 크기 조정 (width/length)** | 수정 | OD / SOD / TSTLD / RMD | Sub View - Top | 마우스 | Cuboid의 너비, 길이를 조정 | - |
| CB-17 | **Cuboid 크기 조정 (length/height)** | 수정 | OD / SOD / TSTLD / RMD | Sub View - Right | 마우스 | Cuboid의 길이, 높이를 조정 | - |
| CB-18 | **Cuboid 크기 조정 (width/height)** | 수정 | OD / SOD / TSTLD / RMD | Sub View - Rear | 마우스 | Cuboid의 너비, 높이를 조정 | - |
| CB-19 | **Cuboid 클래스 변경 (생성 후)** | 수정 | OD / SOD / TSTLD / RMD | Sidebar | 키보드 또는 마우스 | 이미 생성된 Cuboid의 클래스/서브클래스를 변경할 때 발생 | 생성 시 클래스 지정과 반드시 구분하여 기록. **[1차 수정]** 로그명: `annotation.object.update_class`. subclass name 포함 필수 (기존 로그에는 subclass id만 기록되고 name 누락) |
| CB-20 | **Cuboid 속성 부여** | 수정 | OD / SOD / TSTLD / RMD | - | 키보드 또는 마우스 | 특정 프레임 또는 Sequence 전체에 걸쳐 적용되는 속성을 Cuboid에 부여하거나 변경 | **[1차 수정]** 로그명: `annotation.object.update_attributes`. 기존 로그에서 attribute 정보 및 액션이 미수집. class·subclass와 함께 old/new 값을 모두 포함하여 기록 필수 |

### 삭제 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| CB-21 | **Cuboid 전체 삭제** | 삭제 | OD / SOD / TSTLD / RMD | - | 키보드 (Delete) | Tracking ID 전체(모든 프레임에 걸친 해당 Object)를 삭제 | - |
| CB-22-del | **Cuboid 구간 삭제** | 삭제 | OD / SOD / TSTLD / RMD | - | 키보드 (Delete) | Tracking ID가 존재하는 구간 중 특정 프레임 범위만 선택하여 삭제 | 삭제 시작/종료 프레임과 총 삭제 프레임 수 함께 기록 필요 |

### 병합 / 분리 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| CB-22 | **Cuboid Merge** | 병합 | OD / SOD | - | 마우스 | 두 개의 Tracking ID를 하나로 합칠 때 발생. 하나의 ID가 나머지 ID에 흡수됨 | 흡수되어 사라지는 ID와 기준이 되어 유지되는 Primary ID 모두 기록 필요. 흡수 후에도 크기 정보가 남아있는 경우 존재 (Dynamic non-fixed) |
| CB-23 | **Cuboid Split** | 분리 | OD | - | 마우스 | 하나의 Tracking ID를 특정 프레임 기준으로 두 개의 Tracking ID로 분리 | 분리 기준 프레임 인덱스, 기존 Tracking ID, 새로 생성된 Tracking ID 함께 기록 필요. 신규 Tracking ID는 Split 결과로 자동 부여되므로 Split payload에 포함 (별도 커맨드 수집 없음) |

### 선택 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| CB-24 | **Cuboid 선택** | 선택 | OD / SOD / TSTLD / RMD | LiDAR View | 마우스 (Click) | 작업할 Cuboid Object를 선택 | - |
| CB-25 | **Cuboid 선택** | 선택 | OD / SOD / TSTLD / RMD | Sidebar | 키보드 또는 마우스 (Tab, Shift+Tab) | 작업할 Cuboid Object를 선택 | - |
| CB-26 | **Cuboid 선택** | 선택 | OD / SOD / TSTLD / RMD | Image View | 마우스 (Click) | 작업할 Cuboid Object를 선택 | - |
| CB-27 | **Cuboid 선택 해제** | 선택 | OD / SOD / TSTLD / RMD | - | 키보드 또는 마우스 | 선택했던 Cuboid Object를 선택 해제 | - |

---

## 2.3 Point Action

> Point는 Polygon(RMD), Polyline(LD/RBD)에서 공통으로 사용되며, Geometry 단위로 다르게 적용되는 것만 별도 분리하여 작성

### 생성 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| PT-1 | **초기 Point 생성 (Polygon)** | 생성 | RMD | LiDAR View | 마우스 (좌클릭) | Polygon 생성을 시작하기 위해 첫 번째 Point를 찍을 때 발생 | 일반 Point 생성과 구분하기 위해 '초기' Point임을 기록 필요 |
| PT-2 | **초기 Point 생성 (Polyline)** | 생성 | LD / RBD | LiDAR View | 마우스 (좌클릭) | Polyline 생성을 시작하기 위해 첫 번째 Point를 찍을 때 발생 | 일반 Point 생성과 구분하기 위해 '초기' Point임을 기록 필요 |
| PT-3 | **Point 생성 (Polygon)** | 생성 | RMD | LiDAR View | 마우스 (좌클릭) | Polygon 윤곽선을 구성하기 위해 추가 Point를 찍을 때 발생. 초기 Point 생성 이후 연속으로 발생 | 생성 후 Point 추가(PT-20)와 구분 필요 |
| PT-4 | **Point 생성 (Polyline)** | 생성 | LD / RBD | LiDAR View | 마우스 (좌클릭) | Polyline 윤곽을 구성하기 위해 추가 Point를 찍을 때 발생. 초기 Point 생성 이후 연속으로 발생 | 생성 후 Point 추가(PT-21)와 구분 필요 |
| PT-5 | **Point 클래스 지정 - Point 단위 (생성 시)** | 생성 | RBD | - | 마우스 또는 키보드 | 개별 Point 단위로 클래스를 부여할 때 발생 | 생성 후 클래스 변경과 구분 필요. Object 단위 클래스 지정(PT-6)과 구분 필요 |
| PT-6 | **Point 클래스 지정 - Object 단위 (생성 시)** | 생성 | RBD | - | 마우스 또는 키보드 | Object 단위로 클래스를 부여할 때 발생 | Point 단위 클래스 지정(PT-5)과 구분 필요 |
| PT-7 | **Point 너비 조정 (생성 시)** | 생성 | LD | - | 키보드 | Polyline의 너비(width)를 조정 | - |

### 취소 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| PT-8 | **Point 생성 취소 (Polygon)** | 취소 | RMD | LiDAR View | 마우스 (우클릭) | Polygon 윤곽선 구성 중 찍은 Point를 취소 | - |
| PT-9 | **Point 생성 취소 (Polyline)** | 취소 | LD / RBD | LiDAR View | 마우스 (우클릭) | Polyline 윤곽 구성 중 찍은 Point를 취소 | - |

### 선택 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| PT-10 | **Point 단일 선택** | 선택 | RMD / LD / RBD | LiDAR View | 마우스 또는 키보드 | Polyline의 특정 Point를 개별 선택 | Object 선택과 구분 필요 |
| PT-11 | **Point 다중 선택** | 선택 | RMD / LD / RBD | LiDAR View | 마우스 또는 키보드 | Polyline의 특정 Point를 다중으로 선택 | Object 선택과 구분 필요 |
| PT-12 | **Lane 구성 Point 선택** | 선택 | Lane | LiDAR View / Sidebar | 마우스 + 키보드 | Lane을 구성할 Point를 선택. Point 1개 선택마다 커맨드 발생. 총 4개 선택 (Left Start, Left End, Right Start, Right End) | 선택된 Point 4개(좌측 시작/끝, 우측 시작/끝)의 ID 기록 필요. PT-10 항목과 취합 여부 검토 필요 |
| PT-13 | **Point 선택 해제** | 선택 | RMD / LD / RBD | - | 키보드 또는 마우스 | 선택했던 Object를 선택 해제 | - |

### 수정 커맨드 — 클래스 변경 (생성 후)

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| PT-14 | **Point 클래스 변경 - Point 단위 (생성 후)** | 수정 | RBD | - | 마우스 또는 키보드 | 생성된 Polyline의 Point 클래스를 개별 단위로 변경 | Point 선택 커맨드 이후에만 발생. 생성 시 클래스 지정과 구분 필요. Object 단위 클래스 변경(PT-15)과 구분 필요 |
| PT-15 | **Point 클래스 변경 - Object 단위 (생성 후)** | 수정 | RBD | - | 마우스 또는 키보드 | 생성된 Polyline의 Point 클래스를 Object 단위로 변경 | Point 선택 커맨드 이후에만 발생. Point 단위 클래스 지정과 구분 필요 |
| PT-16 | **Point 클래스 변경 - 다중 선택 (생성 후)** | 수정 | RBD | - | 마우스 또는 키보드 | 생성된 Polyline의 Point 클래스를 다중 선택하여 변경 | Point 선택 커맨드 이후에만 발생. Point 다중 선택 후 부여하는 것도 필요할지 확인 필요 |
| PT-17 | **Point 너비 조정 (생성 후)** | 수정 | LD | - | 키보드 | Polyline의 너비(width)를 조정 | Point 선택 커맨드 이후에만 발생 |

### 수정 커맨드 — 위치 조정

| # | Command | Type | Feature | Tool View | Input | Mode | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|------|---------|
| PT-18 | **Point 위치 조정 (x, y)** | 수정 | RMD | LiDAR View | 키보드 또는 마우스 | General | Polygon의 특정 Point x, y 위치를 조정 | Point 선택 커맨드 이후에만 발생. Polygon 높이 조정과 구분 필요 |
| PT-19 | **Point 위치 조정 (x, y)** | 수정 | LD / RBD | LiDAR View | 키보드 또는 마우스 | General | Polyline의 특정 Point x, y 위치를 조정 | Point 선택 커맨드 이후에만 발생 |
| PT-20 | **Point 위치 조정 (z)** | 수정 | RMD | LiDAR View | 키보드 | Height | Polygon의 특정 Point z 위치를 조정 | Point 선택 커맨드 이후에만 발생. Polygon 높이 조정과 구분 필요 |
| PT-21 | **Point 위치 조정 (x, y) - Free view** | 수정 | RMD | Sub View - Free view | 키보드 | General | Polygon의 특정 Point x, y 위치를 조정 | Point 선택 커맨드 이후에만 발생. Polygon 높이 조정과 구분 필요 |
| PT-22 | **Point 위치 조정 (x, y) - Free view** | 수정 | LD / RBD | Sub View - Free view | 키보드 | General | Polyline의 특정 Point x, y 위치를 조정 | Point 선택 커맨드 이후에만 발생 |
| PT-23 | **Point 위치 조정 (z) - Free view** | 수정 | RMD | Sub View - Free view | 키보드 | Height | Polygon의 특정 Point z 위치를 조정 | Point 선택 커맨드 이후에만 발생. Polygon 높이 조정과 구분 필요 |
| PT-24 | **Point 위치 조정 (x, y) - Top** | 수정 | RMD | Sub View - Top | 키보드 | General | Polygon의 특정 Point x, y 위치를 조정 | Point 선택 커맨드 이후에만 발생. Polygon 높이 조정과 구분 필요 |
| PT-25 | **Point 위치 조정 (x, y) - Top** | 수정 | LD / RBD | Sub View - Top | 키보드 | General | Polyline의 특정 Point x, y 위치를 조정 | Point 선택 커맨드 이후에만 발생 |
| PT-26 | **Point 위치 조정 (z) - Top** | 수정 | RMD | Sub View - Top | 키보드 | Height | Polygon의 특정 Point z 위치를 조정 | Point 선택 커맨드 이후에만 발생. Polygon 높이 조정과 구분 필요 |
| PT-27 | **Point 위치 조정 (x, z) - Right** | 수정 | RMD | Sub View - Right | 키보드 | General | Polygon의 특정 Point x, z 위치를 조정 | Point 선택 커맨드 이후에만 발생. Polygon 높이 조정과 구분 필요 |
| PT-28 | **Point 위치 조정 (x, z) - Right** | 수정 | LD / RBD | Sub View - Right | 키보드 | General | Polyline의 특정 Point x, z 위치를 조정 | Point 선택 커맨드 이후에만 발생 |
| PT-29 | **Point 위치 조정 (z) - Right** | 수정 | RMD | Sub View - Right | 키보드 | Height | Polygon의 특정 Point z 위치를 조정 | Point 선택 커맨드 이후에만 발생. Polygon 높이 조정과 구분 필요 |
| PT-30 | **Point 위치 조정 (y, z) - Rear** | 수정 | RMD | Sub View - Rear | 키보드 | General | Polygon의 특정 Point y, z 위치를 조정 | Point 선택 커맨드 이후에만 발생. Polygon 높이 조정과 구분 필요 |
| PT-31 | **Point 위치 조정 (y, z) - Rear** | 수정 | LD / RBD | Sub View - Rear | 키보드 | General | Polyline의 특정 Point y, z 위치를 조정 | Point 선택 커맨드 이후에만 발생 |
| PT-32 | **Point 위치 조정 (z) - Rear** | 수정 | RMD | Sub View - Rear | 키보드 | Height | Polygon의 특정 Point z 위치를 조정 | Point 선택 커맨드 이후에만 발생. Polygon 높이 조정과 구분 필요 |

### 수정 커맨드 — Object 생성 후 Point 추가

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| PT-33 | **생성 후 Point 추가 (Polygon 윤곽선)** | 수정 | RMD | LiDAR View | 키보드 + 마우스 (Shift + 좌클릭) | Polygon 생성 완료 후 윤곽선에 Point를 추가 | 생성 전 Point 생성(PT-3)과 구분 필요. 추가된 Point 위치(인덱스) 기록 필요 |
| PT-34 | **생성 후 Point 추가 (Polyline 중간 삽입)** | 수정 | LD / RBD | LiDAR View | 키보드 + 마우스 (Shift + 좌클릭) | Polyline 생성 완료 후 Polyline 중간에 Point를 추가 | 생성 전 Point 생성(PT-4) 및 끝점 연장(PT-35)과 구분 필요. 추가된 Point 위치(인덱스) 기록 필요 |
| PT-35 | **생성 후 Point 추가 (Polyline 끝점 연장)** | 수정 | LD / RBD | LiDAR View | 마우스 | 생성 완료된 Polyline의 끝점에 이어서 Point를 추가로 그릴 때 발생 | 생성 후 Point 추가 중간 삽입(PT-34)과 구분 필요. 기존 Polyline 끝점에서 연장되는 경우에 해당 |

### 삭제 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| PT-36 | **Point 삭제** | 삭제 | RMD / LD / RBD | - | 키보드 | 생성된 Object의 특정 Point를 삭제 | - |

---

## 2.4 Polygon Action

> RMD / LD / Lane / RBD Feature에서 Polygon Object 단위로 발생하는 커맨드

### 생성 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| PG-1 | **Polygon 클래스 지정 (생성 시)** | 생성(선택) | LD | LiDAR View / Sidebar | 마우스 | Lane 생성 시 Lane Type(클래스)를 선택 | - |
| PG-2 | **Polygon 생성 (RMD/LD/RBD)** | 생성 | RMD / LD / RBD | LiDAR View | 키보드 또는 마우스 (C 또는 시작점 클릭) | Point 입력을 완료하고 Polygon Object를 확정 | - |
| PG-3 | **Polygon 생성 (Lane)** | 생성 | Lane | LiDAR View / Sidebar | 키보드 또는 마우스 | 선택한 Point와 클래스 설정을 기반으로 Lane Object를 확정·생성 | 구성 Point 선택 및 클래스 지정 이후 마지막에 발생하는 커맨드 |

### 수정 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| PG-4 | **Polygon 클래스 변경 (생성 후)** | 수정 | RMD / Lane / LD / RBD | Sidebar | 키보드 또는 마우스 | 이미 생성된 Polygon의 클래스/서브클래스를 변경 | 생성 시 클래스 지정과 반드시 구분하여 기록. **[1차 수정]** Polywall 객체의 class 변경: 로그명은 `polywall.class.update`, object type도 `polywall`로 기록. (기존 오류: 로그명에 `bbox3d`로 표기되고 object type도 `bbox3d`로 기록되던 문제 수정) |
| PG-5 | **Polygon 높이 조정 - General mode (Free view)** | 수정 | RMD / LD / RBD | Sub View - Free view | 키보드 | Polygon 생성 후 외곽 경계 전체의 높이(z축)를 조정 | Point 단위 높이 조정과 구분 필요 |
| PG-6 | **Polygon 높이 조정 - General mode (Right)** | 수정 | RMD / LD / RBD | Sub View - Right | 키보드 | Polygon 생성 후 외곽 경계 전체의 높이(z축)를 조정 | Point 단위 높이 조정과 구분 필요 |
| PG-7 | **Polygon 높이 조정 - General mode (Rear)** | 수정 | RMD / LD / RBD | Sub View - Rear | 키보드 | Polygon 생성 후 외곽 경계 전체의 높이(z축)를 조정 | Point 단위 높이 조정과 구분 필요 |
| PG-8 | **Polygon 높이 조정 - Height mode (LiDAR View)** | 수정 | RMD | LiDAR View | 키보드 | Polygon 생성 후 외곽 경계 Point의 높이(z축)를 조정 | Point 단위 높이 조정과 구분 필요 |
| PG-9 | **Polygon 높이 조정 - Height mode (Free view)** | 수정 | RMD | Sub View - Free view | 키보드 | Polygon 생성 후 외곽 경계 Point의 높이(z축)를 조정 | Point 단위 높이 조정과 구분 필요 |
| PG-10 | **Polygon 높이 조정 - Height mode (Right)** | 수정 | RMD | Sub View - Right | 키보드 | Polygon 생성 후 외곽 경계 Point의 높이(z축)를 조정 | Point 단위 높이 조정과 구분 필요 |
| PG-11 | **Polygon 높이 조정 - Height mode (Rear)** | 수정 | RMD | Sub View - Rear | 키보드 | Polygon 생성 후 외곽 경계 Point의 높이(z축)를 조정 | Point 단위 높이 조정과 구분 필요 |
| PG-12 | **Polygon 속성 부여** | 수정 | RMD / LD | - | 마우스 | Sequence 전체에 걸쳐 적용되는 속성을 Polygon에 부여하거나 변경 | - |

### 삭제 / 선택 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| PG-13 | **Polygon 삭제** | 삭제 | RMD / Lane | - | 키보드 | 생성된 Polygon Object를 삭제 | - |
| PG-14 | **Polygon 선택 해제** | 선택 | RMD / LD / RBD | - | 키보드 또는 마우스 | 선택했던 Object를 선택 해제 | - |

---

## 2.5 Polyline Action

> LD / RBD Feature에서 Polyline Object 단위로 발생하는 커맨드

### 생성 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| PL-1 | **Polyline 생성** | 생성 | LD / RBD | LiDAR View | 키보드 | Point 입력을 완료하고 Line Object를 확정 | Point 생성 커맨드와 Polyline 생성 커맨드는 별도로 기록 |
| PL-2 | **Polyline Split으로 Tracking ID 신규 생성** | 생성 | LD / RBD | LiDAR View | - | 하나의 Polyline을 특정 Point 기준으로 두 개의 Polyline으로 분리할 때 발생. 분리된 point 기준으로 신규 Tracking ID가 부여된 Polyline이 생성됨 | PL-7(Polyline Split) 커맨드 이후에만 발생 |
| PL-3 | **Polyline 클래스 지정 (생성 시)** | 생성 | LD | - | 마우스 또는 키보드 | 생성 시 또는 생성 직후 Polyline Object에 클래스를 부여 | 생성 후 클래스 변경(PL-9)과 구분 필요. Point 단위 클래스 지정과 구분 필요. LD 다중 클래스 선택 관련 내용 기록 여부 확인 필요 |

### 수정 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| PL-4 | **Polyline 이동** | 수정 | LD / RBD | LiDAR View | 마우스 | 생성된 Polyline Object 전체를 이동 | Point 이동과 구분 필요. Object 전체가 이동 대상임을 기록 |
| PL-9 | **Polyline 클래스 변경 (생성 후)** | 수정 | LD | - | 마우스 또는 키보드 | 생성된 Polyline Object의 클래스를 변경 | 생성 시 클래스 지정(PL-3)과 구분 필요. Point 단위 클래스 변경과 구분 필요 |

### 병합 / 분리 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| PL-5 | **Polyline Merge** | 병합 | LD / RBD | LiDAR View | 마우스 | 두 개의 Polyline Object를 하나로 합칠 때 발생 | 병합 기준(어떤 Line이 기준이 되는지) 기록 필요 |
| PL-7 | **Polyline Split** | 분리 | LD / RBD | LiDAR View | 마우스 | 하나의 Polyline을 특정 Point 기준으로 두 개의 Polyline으로 분리 | 분리 기준 Point ID와 새로 생성된 Polyline ID 함께 기록 필요. 신규 Tracking ID는 Split payload에 포함 (별도 커맨드 수집 없음) |

### 선택 / 삭제 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| PL-6a | **Polyline Object 선택** | 선택 | LD / RBD | LiDAR View | 마우스 | 작업할 Polyline Object를 선택 | Point 선택과 구분 필요 |
| PL-6b | **Polyline Object 선택** | 선택 | LD / RBD | Sidebar | 마우스 또는 키보드 | 작업할 Polyline Object를 선택 | Point 선택과 구분 필요 |
| PL-8 | **Polyline 삭제** | 삭제 | LD / RBD | - | 키보드 | 생성된 Polyline Object를 삭제 | - |
| PL-10 | **Polyline 선택 해제** | 선택 | LD / RBD | - | 키보드 또는 마우스 | 선택했던 Object를 선택 해제 | - |

---

## 2.6 Topology Action

> Lane Feature에서 Topology Object 단위로 발생하는 커맨드

### 생성 커맨드

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| TP-1 | **Topology 생성** | 생성 | Lane | - | 마우스 | Source / Destination Lane 선택 및 Type 설정을 기반으로 Topology Object를 확정·생성 | Lane 선택 및 클래스 지정 이후 마지막에 발생하는 커맨드. **[1차 보완]** 생성에 투입된 시간 정의 재수립: TP-2(Source Lane 선택) 시점부터 TP-4(클래스 부여 1회 확정)까지를 단일 생성 이벤트로 정의. 이 구간의 소요 시간(`creation_duration_ms`)을 생성 로그에 포함하여 기록. (Topology 생성에 투입되는 평균 시간 정확도 및 라벨링 비효율 분석에 활용) |
| TP-2 | **Topology 선택 - Source Lane (생성 시)** | 선택 | Lane | LiDAR View | 마우스 | Topology를 구성할 Source Lane을 선택 | Source Lane ID 기록 필요. Destination Lane 선택(TP-3)과 별도 커맨드로 기록 |
| TP-3 | **Topology 선택 - Destination Lane (생성 시)** | 선택 | Lane | LiDAR View | 마우스 | Topology를 구성할 Destination Lane을 선택 | Destination Lane ID 기록 필요. Source Lane 선택(TP-2) 이후에 발생 |
| TP-4 | **Topology 클래스 지정 (생성 시)** | 생성(선택) | Lane | Sidebar | 마우스 | Topology 생성 시 Topology Type을 선택 | - |

### 수정 / 삭제 / 선택 커맨드 (생성 후)

| # | Command | Type | Feature | Tool View | Input | 설명 | 특이사항 |
|---|---------|------|---------|-----------|-------|------|---------|
| TP-5 | **Topology 선택 (생성 후) - LiDAR View** | 선택 | Lane | LiDAR View | 마우스 | 작업할 Topology Object를 선택 | - |
| TP-6 | **Topology 선택 (생성 후) - Sidebar** | 선택 | Lane | Sidebar | 마우스 | 작업할 Topology Object를 선택 | - |
| TP-7 | **Topology 클래스 변경 (생성 후)** | 수정 | Lane | LiDAR View / Sidebar | 마우스 | 생성된 Topology의 클래스를 변경 | - |
| TP-8 | **Topology 삭제** | 삭제 | Lane | LiDAR View | 마우스 | 생성된 Topology Object를 삭제 | - |
| TP-9 | **Topology 선택 해제** | 선택 | Lane | - | 키보드 또는 마우스 | 선택했던 Object를 선택 해제 | - |

---

## 커맨드 요약 (섹션별 카운트)

| 섹션 | 커맨드 수 | 비고 |
|------|-----------|------|
| 2.1.1 Contextual Action | 5 | C-1 ~ C-5 |
| 2.1.2 Tracking ID Group | 8 | G-1 ~ G-8 (G-8은 자동 발생, 수집 방식 별도 확인 필요) |
| 2.2 Cuboid Action | 27 | CB-1 ~ CB-27 (CB-22-del 포함) |
| 2.3 Point Action | 36 | PT-1 ~ PT-36 |
| 2.4 Polygon Action | 14 | PG-1 ~ PG-14 |
| 2.5 Polyline Action | 10 | PL-1 ~ PL-10 |
| 2.6 Topology Action | 9 | TP-1 ~ TP-9 |
| **합계** | **109** | |

---

## LLM 비교 분석 시 주의사항

1. **동일 커맨드, 다른 Tool View**: Cuboid 위치/각도/크기 조정, Point 위치 조정 등은 Tool View(LiDAR View / Sub View - Top / Right / Rear / Free view)별로 별도 커맨드로 등록되어 있음
2. **생성 시 vs 생성 후 구분**: 클래스 지정, 너비 조정 등은 생성 시점과 생성 후 시점을 반드시 구분하여 수집
3. **자동 발생 커맨드**: G-8(Group 자동 삭제)은 사용자 액션이 아닌 Task Done 시점에 자동 발생 — 수집 방식 별도 확인 필요
4. **Split → 신규 생성 연계**: CB-2(Cuboid Split으로 신규 생성)는 CB-23(Cuboid Split) 이후 자동 발생, PL-2(Polyline Split으로 신규 생성)는 PL-7(Polyline Split) 이후 자동 발생
5. **payload 구분 필요 항목**: G-2와 G-3은 Input이 동일하므로 payload의 대상 타입(Object/Group)으로 구분
6. **공통 로그 필드**: `input_type`·`view`·`is_batch_mode` 세 필드는 C-1을 제외한 전체 커맨드 로그에 포함. QA 로그 수집 시 이 필드 누락 여부도 커버리지 비교 대상에 포함
7. **로그명 수정 항목**: CB-19(`annotation.object.update_class`), CB-20(`annotation.object.update_attributes`), PG-4 Polywall(`polywall.class.update`) — 실제 수집 로그 검증 시 이전 로그명(`bbox3d` 등)으로 조회하면 오탐 발생 가능
8. **Topology 생성 이벤트 범위**: TP-1은 TP-2 ~ TP-4 구간 전체를 포함하는 단일 이벤트. TP-2·TP-3·TP-4를 개별 이벤트로 분석하지 않도록 주의
