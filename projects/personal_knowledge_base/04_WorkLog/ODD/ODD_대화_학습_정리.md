# OpenODD & 운행설계영역 — GPT 대화 학습 정리

> 관련 대화 수: **16개** | 기간: 2025-07-15 ~ 2026-02-04

---

## 핵심 주제 목록

- `2025-07-15` ASAM OpenSCENARIO 버전 확인
- `2025-07-16` OpenScenario 호환성 분석
- `2025-07-16` OpenODD와 OpenLABEL 비교
- `2025-07-17` OpenSCENARIO OpenDRIVE 참조
- `2025-07-17` ODD와 OpenDRIVE 구분
- `2025-07-17` OpenScenario to OpenLABEL Mapping
- `2025-07-17` OpenX 시리즈 점검
- `2025-07-18` OpenODD 시나리오 구성
- `2025-07-18` OpenDRIVE XML 포맷
- `2025-07-18` OpenSCENARIO v2.0 구조
- `2025-07-23` MCIP 의미 해석
- `2025-07-24` ASAM OpenODD COD 의미
- `2025-07-24` OpenSCENARIO 버전 비교
- `2025-12-12` YML 테이블 구조 작성
- `2026-01-16` ODD 메타 데이터 여부
- `2026-02-04` CCAN vs PCAN

---

## 대화별 상세 내용

### ASAM OpenSCENARIO 버전 확인
**날짜:** 2025-07-15 | **파일:** conversations-002.json

**맥락/질문:** ASAM OpenSCENARIO는 v1.1.0이 최신이야? v2.0.0도 있는 것 같은데 아직 공식적으로 배포는 되지 않은건가?

**핵심 답변/결론:** ASAM OpenSCENARIO has evolved significantly, and to clarify:  | **Standard** | **Latest Official Public Release** | **Release Date** | |--------------|------------------------------------|------------------| | **OpenSCENARIO 1.x (XML)** | v1.3.0 | ~July 2024 citeturn0search17turn0search8 | | **OpenSCENARIO 2.x (DSL)** | v2.1.0 | ~July 2024 citeturn0search17 | | **OpenSCENARIO 1.1.0** | Older version (Mar 2021) citeturn0search0 | – | | **OpenSCENARIO 2.0.0** | Initial DSL-based release (Jul 20, 2022) citeturn0search1turn0search3 | – |  ### ✅ Summary  - **v1.1.0 is *not* the latest...

**대화 길이:** 총 8개 메시지 (질문 4개)

---

### OpenScenario 호환성 분석
**날짜:** 2025-07-16 | **파일:** conversations-002.json

**맥락/질문:** 이렇게 yaml파일 기반의 시나리오가 있을 때 OpenScenario와 호환이 잘되는 버전은 어떤 버전이지?

**핵심 답변/결론:** {"queries": ["OpenSCENARIO와 호환되는 yaml 시나리오 버전 확인", "OpenSCENARIO 지원 포맷 yaml", "OpenSCENARIO에서 yaml 시나리오 사용 가능 여부", "OpenSCENARIO와 yaml 형식 호환성", "OpenSCENARIO 버전별 입력 파일 포맷"]}

**대화 길이:** 총 96개 메시지 (질문 44개)

---

### OpenODD와 OpenLABEL 비교
**날짜:** 2025-07-16 | **파일:** conversations-002.json

**맥락/질문:** OpenScenario는 따로 포맷이 있는데 OpenODD에도 포맷이 있어? OpenLABEL의 ontology tag 파일과는 어떤 차이가 있지?

**핵심 답변/결론:** OpenODD는 개념적으로 OpenScenario나 OpenLABEL과 달리 **"운행 설계 영역(ODD, Operational Design Domain)"을 명세하는 포맷**입니다. 다음은 OpenODD의 포맷 존재 여부 및 OpenLABEL의 ontology와의 차이점에 대한 비교입니다.  ---  ### 🔹 1. OpenODD에도 포맷이 존재하는가?  | 항목 | 설명 | |------|------| | **포맷 존재 여부** | ✅ **있음** | | **형식** | YAML 기반의 **계층적 텍스트 포맷**<br>(→ ODD 항목들을 트리 구조로 정의) | | **표준 문서** | `ASAM OpenODD` 명세서 기반 (공식 릴리스 기준 v1.0) | | **주요 목적** | 시스템이 작동 가능한 환경을 명확히 정의<br>예: 날씨, 도로 유형, 교통 밀도 등 | | **예시 필드** | `weather: {rain: none}`, `road: {type: urban}`, `traffic: {density: low}` |  ---  ### 🔹 2. OpenODD 포맷 vs OpenLABEL Ontology Tag 파일  | 항목 | **OpenOD...

**대화 길이:** 총 36개 메시지 (질문 18개)

---

### OpenSCENARIO OpenDRIVE 참조
**날짜:** 2025-07-17 | **파일:** conversations-002.json

**맥락/질문:** 시나리오 기반 학습에서 디테일한 이벤트까지 디자인하기 위해서는 OpenDRIVE가 필수라고 했는데 OpenScenario에서는 OpenDRIVE의 데이터를 어떻게 참조하고 있어? 예시로 보여줘

**핵심 답변/결론:** OpenSCENARIO는 실제 도로의 구조 및 지형 정보를 OpenDRIVE 포맷을 통해 참조함으로써 **정밀한 시나리오 실행**이 가능하도록 설계되어 있음. OpenSCENARIO 파일 내부에서는 외부 OpenDRIVE 파일을 `<RoadNetwork>` 요소를 통해 참조하며, 주로 다음과 같은 방식으로 연계함:  ---  ### ✅ OpenSCENARIO에서 OpenDRIVE 참조 예시 (XML 기반)  ```xml <OpenSCENARIO>   <FileHeader author="analyst" date="2025-07-17" description="Scenario with road reference"/>      <RoadNetwork>     <LogicFile filepath="maps/sample_map.xodr"/>     <!-- Optional: SceneGraph or 3D model can also be included -->     <!-- <SceneGraphFile filepath="maps/scene_graph.osgb"/> -->   </RoadNetwork>    <Storyboard>     <!-- 시나리오 이벤트 정의 -...

**대화 길이:** 총 34개 메시지 (질문 17개)

---

### ODD와 OpenDRIVE 구분
**날짜:** 2025-07-17 | **파일:** conversations-003.json

**맥락/질문:** 단계  구성 요소  내용  예시  1  OpenODD  자율주행이 가능한 운행 조건 정의  weather.rain: none, road.type: urban  2  OpenScenario  ODD 조건에 따른 주행 시나리오 구성  Ego vehicle → 좌회전 후 정지선 정지 → 보행자 감지  3  시뮬레이터 실행 (e.g. Applied Simian, CARLA 등)  정의된 시나리오 조건 하에서 주행 데이터 수집  위치, 속도, 센서 RawData 추출  4  OpenLABEL Ontology  라벨링 대상에 대한 분류 체계 정의  "object--vehicle--car", "behavior--crossing"  5  Auto Labeling & Export (OpenLABEL Output)  시뮬레이...

**핵심 답변/결론:** 정확한 지적이야. ODD(Open Operational Design Domain)는 단순히 “운행 조건”을 정의하는 것이 아니라, **자율주행 시스템이 작동할 수 있는 도메인(domain)의 범위**를 기술하는 개념이기 때문에, 다음과 같이 정리하는 것이 더 정확함:  ---  ### 🔁 수정된 전체 흐름 및 설명  | 단계 | 구성 요소                     | 내용                                                                 | 예시 | |------|------------------------------|----------------------------------------------------------------------|------| | 1    | **OpenODD**                  | 자율주행 시스템이 작동 가능한 **도메인(환경, 조건, 맥락)** 정의<br>즉, 어디서 어떻게 운행 가능한가에 대한 선언적 제약 명세 | `weather.rain: none`, `road.type: urban`, `speed.max: 30km/h` | | 2    | **Op...

**대화 길이:** 총 6개 메시지 (질문 3개)

---

### OpenScenario to OpenLABEL Mapping
**날짜:** 2025-07-17 | **파일:** conversations-003.json

**맥락/질문:** OpenScenario를 기반으로 실행한 시뮬레이션 결과를 export한 OpenLABEL 에는 action, event 등이 객체와 매핑되어서 나오는 것이 툴에서 지원해야하는 기본 사양이지?

**핵심 답변/결론:** 맞음. **OpenScenario 기반 시뮬레이션 결과를 OpenLABEL 포맷으로 export**할 때, 다음과 같은 매핑이 **툴에서 기본적으로 지원되어야 하는 사양**으로 간주됨:  ---  ### ✅ **기본 사양 요건**  | 항목 | 설명 | OpenLABEL 내 위치 | |------|------|-------------------| | **Action** | 객체가 수행하는 동작 (e.g. `braking`, `lane_change`) | `objects → object_data → actions` | | **Event** | 시나리오 상에서 발생한 사건 (e.g. `pedestrian crossing`, `vehicle overtaking`) | `events` 필드로 별도 정의하고, 객체와 연결 가능 | | **Object-Level Association** | 특정 action/event가 어떤 객체에 관련되는지 연결 | `associations`, `event → involved_objects` | | **Time Alignment** | 각 action/event가 발생한 타이밍 정보 | `frame` 단위 또는 `timestamp`...

**대화 길이:** 총 48개 메시지 (질문 24개)

---

### OpenX 시리즈 점검
**날짜:** 2025-07-17 | **파일:** conversations-003.json

**맥락/질문:** 자, 지금까지의 결과를 OpenX 시리즈 항목별로 점검해보자.  OpenODD는 내부에서 취득하고 있는 xml 포맷 기반의 데이터를 YAML로 변환하여 OpenLABEL과 Merge. OpenDRIVE는 3D Annotation 결과인 JSON 파일을 .xodr 포맷으로 변환하여 OpenScenario 파일에서 참조. OpenScenario는 내부에서 사용하고 있는 YAML 파일을 기반으로 OpenScenario v2.0의 구조로 확장하고, OpenLABEL과 Merge. 이러한 과정을 거쳐서 결과물인 OpenLABEL에는 시나리오의 모든 컨텍스트가 포함된 결과물이 출력됨. 맞을까?

**핵심 답변/결론:** 네, 전체 흐름과 구조적 연계 방향은 정확하게 정리하셨고, 아래와 같이 항목별로 요약해볼 수 있습니다. 시각적으로 점검이 용이하도록 항목별 목적, 변환 방식, 연계 지점을 정리한 표로 제공드립니다.  | OpenX 항목       | 입력 포맷 (내부)         | 변환 대상 포맷                  | 변환 목적 및 역할 | OpenLABEL과의 연계 방식 | |------------------|----------------------------|----------------------------------|------------------|------------------------| | **OpenODD**      | XML                        | YAML                             | 주행 조건 정의 (ODD 정보) | OpenLABEL metadata/tagging에 ODD 조건을 merge (e.g., `weather`, `road`, `traffic`) | | **OpenDRIVE**    | 3D Annotation 결과 (JSON) | .xodr (OpenDRIVE 표준)...

**대화 길이:** 총 14개 메시지 (질문 7개)

---

### OpenODD 시나리오 구성
**날짜:** 2025-07-18 | **파일:** conversations-003.json

**맥락/질문:** 좋아. 지금까지 현재 수준 분석에서부터 OpenX로 전환하기 위한 실행 전략에 대해 얻은 내용들을 하나의 리포트로 통합하려고 해. 전체 프레임을 생각하면서 내가 입력하는 각 항목별 정보를 정리해줘. 일단은 OpenODD 부터 시작할게.   OpenODD 목적과 역할 구분  OpenODD  핵심 목적  시스템이 작동 가능한 실제 환경 조건 정의  표현 대상  도로 유형, 날씨, 교통 상황 등 외부 세계의 실제 상태  포맷  YAML 또는 JSON (ODD 트리 구조)  사용 맥락  OpenScenario 시나리오 실행 전 “어떤 조건에서 주행하는가?”  예시  weather.rain: none, road.type: motorway, traffic.density:...

**핵심 답변/결론:** 사용자는 OpenODD와 관련된 목적, 구조, 포맷, SV 포맷과의 연계 전략, XML → YAML 변환 방식, OpenLABEL metadata 확장 규칙 등을 포함한 OpenX 전환 리포트 작성을 진행하고 있으며, 각 항목별 정보를 순차적으로 통합하고자 함.

**대화 길이:** 총 72개 메시지 (질문 28개)

---

### OpenDRIVE XML 포맷
**날짜:** 2025-07-18 | **파일:** conversations-003.json

**맥락/질문:** OpenDRIVE 파일은 xodr 포맷을 지원하는 거야 XML 포맷을 지원하는 거야

**핵심 답변/결론:** OpenDRIVE 파일은 **기본적으로 XML 포맷**을 사용하며, 그 파일의 확장자가 일반적으로 **`.xodr`**입니다. 즉, `xodr`는 **OpenDRIVE XML 스키마에 기반한 파일 형식의 확장자명**일 뿐이며, 내용은 **표준 XML 문법**을 따릅니다.  ### 요약 정리  | 구분 | 설명 | |------|------| | **파일 확장자** | `.xodr` | | **내부 포맷** | XML | | **표준 명칭** | OpenDRIVE | | **정의 목적** | 도로 네트워크(차선, 경계, 신호 등)의 정밀한 추상화 표현 | | **스키마 기준** | OpenDRIVE XML Schema (예: `OpenDRIVE_1.6.xsd`) |  ### 예시 (간단한 `.xodr` 파일 내용) ```xml <OpenDRIVE>   <road name="MainStreet" length="100.0" id="1" junction="-1">     <planView>       <geometry s="0.0" x="0.0" y="0.0" hdg="0.0" length="100.0">         <line />       </geometry...

**대화 길이:** 총 2개 메시지 (질문 1개)

---

### OpenSCENARIO v2.0 구조
**날짜:** 2025-07-18 | **파일:** conversations-003.json

**맥락/질문:** 2.1 OpenSCENARIO의 정의와 목적 OpenSCENARIO는 자율주행 또는 운전자 지원 시스템에서 사용할 주행 시나리오를 정형적으로 정의하는 표준이다. 차량, 보행자, 도로, 트리거, 행동 등의 구성요소를 시간 기반 계층 구조로 정의하여 시뮬레이터에서 실행 가능하게 한다.  v1.x는 XML 기반, v2.0은 DSL(Domain-Specific Language) 기반 YAML 유사 포맷을 사용한다.  주요 활용 목적:  정량적 시나리오 검증 및 비교  학습용 행동 시나리오 생성  이벤트 중심의 상황 인지 학습 데이터 구성     2.2 OpenSCENARIO v2.0 주요 계층 구조 및 DSL 구조 OpenSCENARIO v2.0은 시간 흐름에 따른 계층 제어 구조를 가...

**핵심 답변/결론:** 이어서 작성할 문서에서 'SV의 단일 프레임 기반 포맷에서 OpenLABEL로 마이그레이션'하는 내용을 기술하시려는 목적이 아래 중 어떤 것에 가까운지 알려주실 수 있을까요?  1. 실제 변환 파이프라인 설계 문서 (예: 데이터 처리 흐름, 스크립트 개발 기준 등) 2. 형식 비교 및 표준 정합 가이드 (예: 좌표계, object ID 등 필드 매핑 중심) 3. 시나리오 기반 학습 데이터 생성 관점에서의 정합성 확보 방법  또한, 결과물 포맷은 테이블 중심이 좋다고 하셨는데, 어떤 구조(예: 마이그레이션 단계별 / 필드별 비교 / 예외 처리 패턴 등)를 선호하시는지도 함께 알려주세요.

**대화 길이:** 총 8개 메시지 (질문 3개)

---

### MCIP 의미 해석
**날짜:** 2025-07-23 | **파일:** conversations-003.json

**맥락/질문:** 자율주행 데이터에서 MCIP는 무엇을 의미해?

**핵심 답변/결론:** 자율주행 데이터 문맥에서 "MCIP"는 일반적으로 통용되는 약어는 아니며, **문맥에 따라 다르게 해석될 수 있는 약어**입니다. 하지만 자율주행, 센서, 시뮬레이션, HD Map 또는 차량 통신(V2X) 관련 기술 영역에서 아래와 같은 의미로 사용될 가능성이 있습니다:  ---  ### 1. **Multi-Camera Image Projection** - **의미**: 다중 카메라의 영상 데이터를 통합하여 하나의 정합된 시야(view) 또는 투영(projection)으로 만드는 과정. - **용도**: Bird’s Eye View(BEV) 생성, 3D scene reconstruction, 센서 정합(Sensor Fusion)에 활용됨. - **예시**: 6대의 SVC/MVC 카메라 데이터를 차량의 top-down view로 정렬할 때.  ---  ### 2. **Map Calibration & Integration Pipeline** - **의미**: HD 맵과 센서 데이터를 일치시키기 위한 정합(calibration) 및 통합(integration) 파이프라인. - **용도**: OpenDRIVE나 LaneNet 기반 도로 구조 정합, SLAM 기반 자...

**대화 길이:** 총 2개 메시지 (질문 1개)

---

### ASAM OpenODD COD 의미
**날짜:** 2025-07-24 | **파일:** conversations-003.json

**맥락/질문:** ASAM OpenODD에서 COD는 무슨 의미일까

**핵심 답변/결론:** 알겠습니다. ASAM OpenODD에서 "COD"라는 용어의 의미를 정확히 파악하기 위해 먼저 ASAM OpenODD 관련 자료를 온라인으로 검색해보겠습니다. 이후 확인된 정보를 바탕으로 이해하기 쉽게 설명해드리겠습니다.

**대화 길이:** 총 10개 메시지 (질문 4개)

---

### OpenSCENARIO 버전 비교
**날짜:** 2025-07-24 | **파일:** conversations-003.json

**맥락/질문:** 다음과 같은 OpenSCENARIO 샘플을 찾았어. import osc.standard  scenario elk_overtaking:     gvt: vehicle                # Target vehicle     dut: vehicle                # Device under test     routeToFollow: route with:  # Route to be followed         keep(it.min_lanes == 2)       do parallel:             dut.drive(duration: 5s) with:                 along(route: routeToFollow)...

**핵심 답변/결론:** 네가 제시한 OpenSCENARIO 샘플은 **OpenSCENARIO v2.0의 DSL (Domain-Specific Language) 기반 표현**이며, 내가 설명한 내용은 **OpenSCENARIO v1.x(XML) 기반의 계층 구조 규칙**을 기반으로 정리된 것이다.  따라서 이 둘은 서로 다른 구조 체계를 갖고 있으며, **표현 방식과 스키마 규칙이 전혀 다르다.**  ---  ### 🔁 두 버전의 구조적 차이 비교  | 항목 | OpenSCENARIO v1.x (XML) | OpenSCENARIO v2.0 (DSL) | |------|--------------------------|--------------------------| | **표현 방식** | XML 계층 구조 | Python-like DSL 스크립트 | | **Entity 등록** | `<Entities>` 블록 안에 정의 (Ego, target 등) | `gvt: vehicle`, `dut: vehicle` 등 변수 선언 방식 | | **초기 위치 지정** | `<Init> → <PrivateAction> → <TeleportAction>` | `position(distance: .....

**대화 길이:** 총 21개 메시지 (질문 9개)

---

### YML 테이블 구조 작성
**날짜:** 2025-12-12 | **파일:** conversations-005.json

**맥락/질문:** raw_data_key를 key id로 하는 다음 테이블의 구조를 YML 형식으로 작성해줘

**핵심 답변/결론:** 아래는 **`raw_data_key`를 Key ID(Primary Key)**로 하는 테이블 구조를 **YAML(YML) 형식**으로 정리한 것이다.   데이터 모델/스키마 정의용으로 바로 사용할 수 있도록 **필드 타입, nullable, 설명**까지 포함했다.  ```yaml table:   name: da_lpsd_context   description: >     LPSD(Parking) 관련 도로/주차 공간 컨텍스트 정보를 저장하는 테이블.     raw_data_key를 기준으로 1:1 매핑된다.    primary_key:     - raw_data_key    columns:     raw_data_key:       type: string       nullable: false       description: Raw 데이터의 고유 식별 키 (Primary Key)      da_main_type:       type: string       nullable: true       description: 데이터의 메인 유형 (예: road, parking_space 등)      da_road_surface_material:       type...

**대화 길이:** 총 4개 메시지 (질문 2개)

---

### ODD 메타 데이터 여부
**날짜:** 2026-01-16 | **파일:** conversations-005.json

**맥락/질문:** 이거 하나만 판단해줘. ODD 정보는 Meta 데이터다 -> 맞다 / 아니다 Meta tag는 ODD 정보다 -> 맞다 / 아니다

**핵심 답변/결론:** 결론부터 명확히 판단한다.  ---  ## 1️⃣ **ODD 정보는 Meta 데이터다**   **→ 맞다**  **이유 (구조 기준)**   - ODD(Operational Design Domain)는 **데이터 그 자체의 내용이 아니라, 그 데이터가 유효하게 해석·사용될 수 있는 조건과 범위**를 정의한다. - 이는 센서 원시 데이터, annotation 결과, feature GT와 **분리된 상위 컨텍스트 정보**다. - 따라서 ODD는 **Data about Data**, 즉 메타데이터의 정의에 정확히 부합한다.  **정리** - 주행 데이터: Primary data   - Annotation 결과: Derived data   - **ODD: Context / Constraint / Validity를 설명하는 Meta data**  ---  ## 2️⃣ **Meta tag는 ODD 정보다**   **→ 아니다**  **이유 (개념 방향성 기준)**   - Meta tag는 **표현 수단**이다.   - ODD는 **의미 체계(도메인 모델)**다. - Meta tag는 ODD를 *표현할 수는 있지만*, **Meta tag 자체가 곧 ODD는 아니다**....

**대화 길이:** 총 4개 메시지 (질문 2개)

---

### CCAN vs PCAN
**날짜:** 2026-02-04 | **파일:** conversations-005.json

**맥락/질문:** ccan과 pcan의 기능 및 목적, 담고 있는 데이터에 대해서 알려줘

**핵심 답변/결론:** 핵심부터 정리할게.   **CCAN**과 **PCAN**은 같은 CAN 버스 세계에 있지만, **역할·목적·데이터 성격**이 다르다.  ---  ## 한눈에 비교  | 구분 | **CCAN (Chassis CAN)** | **PCAN (PC-based CAN Interface)** | |---|---|---| | 본질 | **차량 내부 CAN 네트워크 도메인** | **PC ↔ CAN 연결용 인터페이스/툴** | | 목적 | 주행·차체 제어 신호의 **실시간 교환** | CAN 데이터 **수집·송신·분석·시뮬레이션** | | 위치 | 차량 ECU 간 통신 | 개발자 PC, 테스트 장비 | | 주 사용처 | 제동·조향·서스펜션 등 | 개발·디버깅·검증·로그 | | 데이터 성격 | **실시간 제어 데이터** | **원시 CAN 프레임 + 메타데이터** |  ---  ## CCAN — 차량 제어용 네트워크  image_group{"query":["automotive chassis CAN network diagram","vehicle CAN bus ECU diagram"]}  ### 기능 & 목적 - **차량 섀시(Chassis) 영역**의 ECU 간 통신 -...

**대화 길이:** 총 80개 메시지 (질문 30개)

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---

### "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들
**날짜:** 2026-04-08 | **파일:** 4f6718f9-c865-497e-806a-42ce968f4bc4.jsonl

**맥락 요약:** "C:\Users\psh93\OneDrive\Desktop\ODD" 폴더에 있는 JSON 파일들 구조 분석하고, 엑셀 파일 형태로 추출해서 만들어줘. rawDataKey 1개당 하나의 시트에 정보를 정리하면 좋을 것 같아. 구조를 파악했습니다. JSON 구조: - 최상위: `policy`, `phase`, `rawDataKey`, `task`, `task_...

**대화 길이:** 총 89개 메시지

---
