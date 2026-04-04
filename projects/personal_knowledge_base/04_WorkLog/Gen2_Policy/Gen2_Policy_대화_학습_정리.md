# Gen2 Sequence Annotation Policy — GPT 대화 학습 정리

> **범위:** 2025-11-21 ~ 2026-02-24
> **주제:** Sequence 기반 Gen2 Annotation Policy 수립, 조항 작성·검토·번역, 용어 정의, 정책 운영·문서화 전략
> **원본 파일:** Gen1_Gen2_Labeling_대화_학습_정리.md 에서 분리
> **관련 대화 수:** 40개

---

## 목차

### Policy 기획 및 마일스톤
- [문서 목적과 구조 분석](#문서-목적과-구조-분석) — 2025-11-21
- [GEN2 policy Jira 티켓](#gen2-policy-jira-티켓) — 2025-11-24
- [변환 규칙 정리](#변환-규칙-정리) — 2025-12-10
- [Gen1 Gen2 OD 비교](#gen1-gen2-od-비교) — 2026-01-06
- [Operation 비용 측정](#operation-비용-측정) — 2026-01-07
- [MVGen2 요구사항 검토](#mvgen2-요구사항-검토) — 2026-01-16
- [Gen2 ODD 전환 필요성](#gen2-odd-전환-필요성) — 2026-01-19
- [GEN2 성능 측정 전략](#gen2-성능-측정-전략) — 2026-01-19

### Sequence OD 개념 정의
- [구간별 Static Dynamic 판정](#구간별-static-dynamic-판정) — 2025-11-25
- [AI 영상 생성 프롬프트](#ai-영상-생성-프롬프트) — 2025-11-26
- [2D fallback geometry 필요성](#2d-fallback-geometry-필요성) — 2025-11-26
- [Sequence OD vs Map-base vs 4DP](#sequence-od-vs-map-base-vs-4dp) — 2025-11-26
- [FoV와 Visibility 구분](#fov와-visibility-구분) — 2025-11-29

### 조항 작성 및 검토
- [Policy 테이블 포맷 적용](#policy-테이블-포맷-적용) — 2025-11-25
- [클래스별 어노테이션 규칙](#클래스별-어노테이션-규칙) — 2025-12-03
- [Policy 언급 필요성](#policy-언급-필요성) — 2025-12-05
- [시각적 인식 불가 속성](#시각적-인식-불가-속성) — 2026-01-02
- [Cuboid 도로 객체 설명](#cuboid-도로-객체-설명) — 2026-01-07
- [Pole 높이 표현 방법](#pole-높이-표현-방법) — 2026-01-08
- [Vehicle Attribute 제목 순서](#vehicle-attribute-제목-순서) — 2026-01-08
- [문법적 표현 수정](#문법적-표현-수정) — 2026-01-09
- [Obstacle 분류 및 정의](#obstacle-분류-및-정의) — 2026-01-11
- [Barrier 분류 검토 및 수정](#barrier-분류-검토-및-수정) — 2026-01-13

### 번역 및 표현 정제
- [번역 요청 검토](#번역-요청-검토) — 2025-11-25
- [복수형 기준 설명](#복수형-기준-설명) — 2025-11-27
- [공간적 정합성 번역](#공간적-정합성-번역) — 2025-11-29
- [객체 명칭 영어 번역](#객체-명칭-영어-번역) — 2025-12-02
- [Translate animal specification](#translate-animal-specification) — 2025-12-05
- [배리어와 바리케이드 차이](#배리어와-바리케이드-차이) — 2026-01-09
- [투시 투과 투사](#투시-투과-투사) — 2026-01-12
- [교량 난간 영어 표현](#교량-난간-영어-표현) — 2026-01-13

### Policy 운영 및 문서화 전략
- [자세 변화 크기 변화](#자세-변화-크기-변화) — 2026-02-02
- [자율주행 객체 검출 용어](#자율주행-객체-검출-용어) — 2026-02-05
- [AI 기반 정책 관리](#ai-기반-정책-관리) — 2026-02-09
- [네이밍 개선 제안](#네이밍-개선-제안) — 2026-02-09
- [JSON Schema 검토 결과](#json-schema-검토-결과) — 2026-02-09
- [데이터 정책 이미지 요청](#데이터-정책-이미지-요청) — 2026-02-10
- [정책 실효성 검증 표현](#정책-실효성-검증-표현) — 2026-02-11
- [Policy review 표현 수정](#policy-review-표현-수정) — 2026-02-13
- [상반기 Policy 목표 설정](#상반기-policy-목표-설정) — 2026-02-24

---

## Policy 기획 및 마일스톤

### 문서 목적과 구조 분석
**날짜:** 2025-11-21 | **파일:** conversations-004.json

**맥락/질문:** 이 문서의 목적과 구조에 대해서 분석해줘.

**핵심 답변/결론:** 분석 대상: `3DP_MV_OD_Annotation Policy_KR_1.7.1_Gen2_Draft.xlsx` — 엑셀 파일로 된 GEN2 초안 Policy 문서 구조 분석. 시트 구성, 항목 정의, 계층 구조 파악.

**대화 길이:** 총 84개 메시지 (질문 34개)

---

### GEN2 policy Jira 티켓
**날짜:** 2025-11-24 | **파일:** conversations-004.json

**맥락/질문:** GEN2 policy 관련 task에 대하여 Jira epic - task 티켓으로 마일스톤을 세우고 진행하려고 해. 1. CDG 요구사항 수집 2. Output format 확정 3. Limitation 확인

**핵심 답변/결론:** 각 항목을 **Jira Epic/Task 티켓에 바로 넣기 좋은 concise 영문 액션 문구**로 정리. GEN2 Policy – Jira Ticket-Ready English Items: 1. Collect CDG Requirements 2. Define Output Format 3. Publish First Draft 4. Review & Provide Feedback 5. Validate Sequence Structure 6. Verify Class-level Details 7. Identify Limitations 8. Validate Criteria 9. Review Issue Cases

**대화 길이:** 총 7개 메시지 (질문 4개)

---

### 변환 규칙 정리
**날짜:** 2025-12-10 | **파일:** conversations-004.json

**맥락/질문:** Feature별 Policy ver. 변환 규칙 — OD: MV_OD_v1.7 → MV_OD_3D_BoundBox_v1.7.0 / SOD: MV_SOD_v1.6 → MV_SOD_3D_BoundBox_v1.6.0 / TSTLD, RMD, LPSD 등

**핵심 답변/결론:** 공통 규칙: `MV_<FEATURE>_vA.B → MV_<FEATURE>_3D_BoundBox_vA.B.0`. Patch version `.0` 고정, Feature 코드 유지. 예외: LPSD만 `MV_LPSD_Parking_v1.5.0` (3D 접미어 없이 도메인 명시).

**대화 길이:** 총 2개 메시지 (질문 1개)

---

### Gen1 Gen2 OD 비교
**날짜:** 2026-01-06 | **파일:** conversations-005.json

**맥락/질문:** Frame base Gen1 OD와 Map base Gen2 OD의 작업 공수를 비교하기 위한 컨셉 초안. 목표: Gen2 Sequential OD와 Gen1 MV OD 작업 효율 임팩트 측정. Frame base: 최고 밀도 구간 객체수 × 프레임수 × 2/3. Map base: 시퀀스 전체 객체수.

**핵심 답변/결론:** 비교식의 구조적 위험: "최대 밀집 구간" 기준은 피크값이라 왜곡 가능. 공수(Effort)로 연결되는 브릿지(가정/보정/검증) 보강 필요. 권장: 비교 축을 "동일 금액 대비 확보 가치"로 전환.

**대화 길이:** 총 50개 메시지 (질문 25개)

---

### Operation 비용 측정
**날짜:** 2026-01-07 | **파일:** conversations-005.json

**맥락/질문:** Map base와 Frame base Feature의 작업 공수 차이를 작업 결과물로 비교하기엔 무리가 있는 것 같아. 동일한 금액 대비 결과물이 어떤지 비교하는 것이 더 좋을까?

**핵심 답변/결론:** **결론: Output 기준 직접 비교는 구조적으로 성립하지 않음.** Frame-based(미시적·선형)와 Map-based(거시적·비선형, 재사용성 큼)는 성격 자체가 다름. 비교 프레임 전환: "같은 돈을 썼을 때, 무엇을 얼마나 확보했는가"로 접근.

**대화 길이:** 총 6개 메시지 (질문 3개)

---

### MVGen2 요구사항 검토
**날짜:** 2026-01-16 | **파일:** conversations-005.json

**맥락/질문:** v2.7.0 ODD 문서의 정보를 바탕으로 MVGen2 Object Detection의 시나리오 요구사항을 충족할 수 있는지 확인. ODD 데이터 구조 비교.

**핵심 답변/결론:** `v2.7.0_odd_class_info_total.xlsx`와 `MVGen2-DB-ODD_ObjectDetection.xlsx` 데이터 비교 분석. 요구사항 충족 여부를 항목별로 매핑.

**대화 길이:** 총 271개 메시지 (질문 120개)

---

### Gen2 ODD 전환 필요성
**날짜:** 2026-01-19 | **파일:** conversations-005.json

**맥락/질문:** Gen2 ODD 정책·포맷이 완전히 정리된 후, 데이터 선별·관리·cost control 목표를 위해 odd v2.7.0 구조에서 전환이 필수불가결함을 제시하는 문서 작성. 두 정책 문서 스펙을 테이블 형태로 비교하는 방식으로 전개.

**핵심 답변/결론:** 문서 논리 구조: A. 문제 정의 → B. 스펙 비교 테이블(메인, 60~70%) → C. 전환 효과 정리(Data Selection / Data Governance / Cost Control / Scalability) → D. 결론. 핵심 메시지: "Gen2 전환은 개선이 아니라 **목표 달성을 위한 전제 조건**".

**대화 길이:** 총 51개 메시지 (질문 26개)

---

### GEN2 성능 측정 전략
**날짜:** 2026-01-19 | **파일:** conversations-005.json

**맥락/질문:** Phase 1: Performance Measurement 전략·컨셉 수정. 목적: GEN2 Feature가 라벨링 생산성·난이도·효율성에 미치는 영향을 정밀 측정. 단가 산정에 직접 사용하지 않으므로 측정 민감성 최대화.

**핵심 답변/결론:** Phase 1의 전략적 포지션 재정의: **"Cost Model이 왜 바뀌어야 하는지를 증명하는 단계"**. 현재 문서는 "무엇을 측정하는지"는 명확하나 "왜 이 측정이 이후 Phase를 가능하게 하는가"가 약함 → 보강 필요.

**대화 길이:** 총 367개 메시지 (질문 183개)

---

## Sequence OD 개념 정의

### 구간별 Static Dynamic 판정
**날짜:** 2025-11-25 | **파일:** conversations-004.json

**맥락/질문:** 시퀀스로 객체를 어노테이션할 때, 구간에 따라서 스태틱/다이내믹 값을 가지도록 하는 경우도 있어?

**핵심 답변/결론:** **있음.** 시퀀스 기반 어노테이션에서는 동일한 객체라도 구간별로 static ↔ dynamic이 바뀌는 케이스가 자주 발생. 예: 보행자 정지→재이동, 차량 신호대기→출발. ASAM OpenLABEL / OpenSCENARIO 관점에서도 객체 상태는 `frame_intervals` 또는 `object_data`의 timeRange로 static/dynamic을 정의.

**대화 길이:** 총 17개 메시지 (질문 8개)

---

### AI 영상 생성 프롬프트
**날짜:** 2025-11-26 | **파일:** conversations-004.json

**맥락/질문:** 단일 프레임 기반 Policy에서 Sequence 작업으로 전환 시 충돌 케이스: ① 2량 이상 버스/기차 커브 ② 트럭 헤드/트레일러 교차로 회전 ③ 라이더 하차 ④ 렉카 견인 ⑤ 아이 안고 내리는 경우 — 각 케이스별 AI 영상 생성 프롬프트 작성 요청.

**핵심 답변/결론:** 각 케이스별 AI 영상 생성 프롬프트 제공. 공통 규칙: "단일 프레임에서는 하나의 객체로 보이지만, 시퀀스에서는 물리적으로 분리되거나 각도가 달라져 충돌이 발생하는 장면"을 기본 조건으로 포함. Annotation 정책 검증용으로 카메라 시점·움직임·프레임 간 변화·객체 분리·결합을 명확히 묘사.

**대화 길이:** 총 12개 메시지 (질문 6개)

---

### 2D fallback geometry 필요성
**날짜:** 2025-11-26 | **파일:** conversations-004.json

**맥락/질문:** sequence OD annotation에서 2D bbox는 정규 geometry가 될 수 있어? 보편적으로는 어떻게 하고 있어?

**핵심 답변/결론:** **2D bbox가 정규 Geometry가 되기 어려운 이유:** ① temporal consistency 유지에 취약 (scale 변화, occlusion 시 좌표 급변) ② 객체의 실제 물리적 위치 추정 불가. 보편적으로는 3D cuboid를 primary geometry로 사용하고, 2D bbox는 fallback 또는 보조 geometry로 허용.

**대화 길이:** 총 8개 메시지 (질문 4개)

---

### Sequence OD vs Map-base vs 4DP
**날짜:** 2025-11-26 | **파일:** conversations-004.json

**맥락/질문:** Sequence OD 개념이 내부적으로 제대로 정의가 되었는지 잘 모르겠어. Map base와 4DP의 개념을 혼용하는 것 같은데 어떤 차이가 있는지 비교 분석해줘.

**핵심 답변/결론:**

| 개념 | 핵심 정의 | 기준 좌표 | 시간 개념 | 주 용도 |
|------|-----------|-----------|-----------|---------|
| **Sequence OD** | 프레임 흐름에서 OD 수행, frame-to-frame ID continuity 관리 | Ego-centered | 있음 | 멀티프레임 OB 분석 |
| **Map-base Annotation** | 정적 맵(PCD) 상에서 공간 정보 기반 정적 라벨링 | Global Map | 없음 | 구조적 맵 라벨링 |
| **4DP** | 4D Perception/Reconstruction, 시간+공간 통합 | Global/Temporal | 있음 (4D) | 시공간 통합 인식 |

**대화 길이:** 총 56개 메시지 (질문 28개)

---

### FoV와 Visibility 구분
**날짜:** 2025-11-29 | **파일:** conversations-004.json

**맥락/질문:** FoV는 단순히 화각의 개념이야, 아니면 실제 이미지에서 보이는지 여부도 포함하는 거야?

**핵심 답변/결론:** FoV는 두 수준으로 구분: ① **기하학적 FoV** — 센서가 이론적으로 관측 가능한 공간적 범위 (프러스텀, 고정된 스펙값). Occlusion·조도·거리 포함 안 됨. ② **FoV 내부 실제 가시성(Visibility)** — 가려짐, 포인트 밀도, 조도, 객체 크기 등 현실 요소 반영. Policy에서 두 개념은 반드시 분리해서 정의해야 함.

**대화 길이:** 총 6개 메시지 (질문 3개)

---

## 조항 작성 및 검토

### Policy 테이블 포맷 적용
**날짜:** 2025-11-25 | **파일:** conversations-004.json

**맥락/질문:** 다음의 내용을 policy에 추가하려고 해. 테이블 포맷을 고려해서 포맷에 맞게 넣어줘. **Temporal Annotation Area – Working Scope**: 1. Annotation 대상 공간의 기본 원칙 (Spatial Validity Rule), 1.1 Primary Roadway Relevance (본선·현재 주행도로와의 관련성) 등.

**핵심 답변/결론:** 정책 문서 내 테이블 포맷으로 구조화. 통일된 구조: **Section / Rule / Description / Criteria / Included / Excluded**. Row 단위 블록으로 정리하여 표 형태로 바로 전환 가능.

**대화 길이:** 총 12개 메시지 (질문 6개)

---

### 클래스별 어노테이션 규칙
**날짜:** 2025-12-03 | **파일:** conversations-004.json

**맥락/질문:** 각 클래스별 어노테이션 방법이라는 조항을 쓰려고 하는데 이름을 어떻게 하는 것이 좋을까?

**핵심 답변/결론:** 추천 제목 후보:
- **Class-Specific Annotation Rules** — 가장 직관적, 정책 문서에 자주 쓰임
- **Class-Wise Annotation Guidelines** — 원칙·가이드 성격 포함
- **Object Class Annotation Protocols** — 절차·규범·일관성 강조
- **Per-Class Labeling Specifications** — 기술적 스펙 중심

**대화 길이:** 총 18개 메시지 (질문 9개)

---

### Policy 언급 필요성
**날짜:** 2025-12-05 | **파일:** conversations-004.json

**맥락/질문:** Base rule에 신규 챕터로 객체의 Occlusion / Truncation / Visibility 표현에 대한 조항을 추가하고 싶어.

**핵심 답변/결론:** **Chapter X. Occlusion / Truncation / Visibility Rules** 초안 제공. Purpose: 모든 perception 기반 annotation 태스크에 적용. 3D cuboid primary geometry, 2D bbox 보조 geometry 구조 반영. Shall 기반 규범적 문장 구성. 다른 챕터(Geometry, Temporal Area, Limitation)와 충돌 없이 편입 가능한 구조.

**대화 길이:** 총 22개 메시지 (질문 11개)

---

### 시각적 인식 불가 속성
**날짜:** 2026-01-02 | **파일:** conversations-005.json

**맥락/질문:** 어두워서 이미지 상에서는 인식이 되지 않는 물체를 attribute로 표기하려고 하는데 어떤 명칭이 좋을까?

**핵심 답변/결론:** 조건: 객체는 존재하지만 조도/노출 문제로 시각적 식별 불가 (not visible ≠ not present). 제외: `visibility=false`(FoV 혼동), `occluded`(기하적 가림), `ignored`(의도적 배제). **추천: `illumination_insufficient`** — 원인 명확, visibility/occlusion과 개념 충돌 없음. boolean 또는 enum 타입.

**대화 길이:** 총 10개 메시지 (질문 5개)

---

### Cuboid 도로 객체 설명
**날짜:** 2026-01-07 | **파일:** conversations-005.json

**맥락/질문:** Cuboid로 annotation된 도로 위 간이 객체에 대해서 알려줘.

**핵심 답변/결론:** **정의:** 공사·통제·유도 목적의 임시 교통 안전물 (Operational Object). 특징: 설치·철거 빈번, 위치 변동성 높음, 야간 시인성 강화(반사/조명). **Cuboid(3D)로 라벨링하는 이유:** 2D bbox로는 방향·부피·주행 영향 범위 표현 불가. 3D cuboid로 heading angle, 점유 공간 정의.

**대화 길이:** 총 18개 메시지 (질문 9개)

---

### Pole 높이 표현 방법
**날짜:** 2026-01-08 | **파일:** conversations-005.json

**맥락/질문:** pole의 attribute로 높이를 부여할 때 low/high가 맞을까, short/tall이 맞을까?

**핵심 답변/결론:** **`short / tall`이 맞다.** `low/high`는 기준면 대비 상대적 위치 표현 (low beam, high-mounted). `short/tall`은 객체 자체의 물리적 길이(높이) 표현. Pole은 높이가 정체성에 직접적인 영향을 주는 객체이므로 내부 물리적 차이를 표현해야 함.

**대화 길이:** 총 2개 메시지 (질문 1개)

---

### Vehicle Attribute 제목 순서
**날짜:** 2026-01-08 | **파일:** conversations-005.json

**맥락/질문:** Vehicle Type Classification Criteria, Sequence Annotation Method 조항이 있고, Vehicle의 attribute에 대한 조항을 신설하려고 할 때 제목은? 순서는?

**핵심 답변/결론:** 추천 제목:
- **Vehicle Attribute Definition** — 가장 정제, 규범적 선언에 적합 (1순위)
- **Vehicle Attribute Specification** — 허용 범위·값·조건까지 포함 시
- **Vehicle State & Attribute Rules** — 동적 상태 변화까지 포함 시

순서 권장: Vehicle Type Classification Criteria → **Vehicle Attribute Definition** → Sequence Annotation Method (분류 기준 → 속성 정의 → 시간 기반 규칙 순서가 논리적)

**대화 길이:** 총 38개 메시지 (질문 19개)

---

### 문법적 표현 수정
**날짜:** 2026-01-09 | **파일:** conversations-005.json

**맥락/질문:** "Shall include all objects located within a 200 m radius in the forward, rear, and lateral directions around the ego vehicle." 문법적인 부분 확인해줘.

**핵심 답변/결론:** 문법 오류 없음. 다만 `radius`와 `directions`의 조합이 의미적으로 어색 (radius는 원형 범위, 이를 방향별로 나누면 개념 충돌). **권장안 1:** "Shall include all objects located within a **200 m radius around the ego vehicle**, including the forward, rear, and lateral areas." **권장안 2 (방향 강조):** "within 200 m in the forward, rear, and lateral directions relative to the ego vehicle."

**대화 길이:** 총 223개 메시지 (질문 108개)

---

### Obstacle 분류 및 정의
**날짜:** 2026-01-11 | **파일:** conversations-005.json

**맥락/질문:** Obstacle 조항 검토 (Hierarchy/Description/Limitation/Acceptance Criteria 구조). 7개 Class: cone, cylinder, bollard 등 포함.

**핵심 답변/결론:** **강점:** 기능 중심(차단/유도/임시) 분류 방향 적절. **개선 포인트:** ① Cylinder vs Bollard 경계: 차단 의도와 물리적 결과 혼재 → Bollard 정의 1차 기준을 '설치 목적'으로 고정, 수치는 보조 기준으로만 사용. ② 제안 문구: "Bollard: 차량의 통과를 물리적으로 차단하는 것을 주된 목적으로 설치된 고정형 또는 반고정형 장애물. 참고 기준: 지름 ≥15cm 또는 중량 ≥10kg."

**대화 길이:** 총 20개 메시지 (질문 10개)

---

### Barrier 분류 검토 및 수정
**날짜:** 2026-01-13 | **파일:** conversations-005.json

**맥락/질문:** Barrier 조항 검토 (4개 Class: Solid / Rail / Fence / Temporary). 기본 정의: 차량 또는 보행자의 이동을 물리적으로 제한하거나 충격을 완화하는 구조물.

**핵심 답변/결론:** **개선 필요사항:** ① 기능 정의 vs 형태 정의 혼재 — 정의 문장에 "연속적 또는 분절형 구조물" 추가로 Cuboid 분할 규칙(15m)과 자연스럽게 연결. ② Fence: "시각적으로 투과가 가능한" — 투과성 정의 기준 명확화 필요. ③ Temporary: 임시성 판단 기준(설치 형태 vs 목적 vs 기간) 명시 필요. ④ Rail: bridge railing vs guardrail 구분 여부 검토.

**대화 길이:** 총 50개 메시지 (질문 25개)

---

## 번역 및 표현 정제

### 번역 요청 검토
**날짜:** 2025-11-25 | **파일:** conversations-004.json

**맥락/질문:** "class별 작업 규정에 대하여 검토하다"를 번역해줘.

**핵심 답변/결론:** **"Reviewing class-specific annotation rules"** (가장 직접적). 맥락별 변형:
- 정책·가이드라인 관점: *Assessing class-level annotation guidelines*
- 규정·룰 기반: *Evaluating class-specific working criteria*
- 업무 수행 기준: *Reviewing class-based labeling rules*

**대화 길이:** 총 24개 메시지 (질문 12개)

---

### 복수형 기준 설명
**날짜:** 2025-11-27 | **파일:** conversations-004.json

**맥락/질문:** criteria의 복수형은 영어로 어떻게 돼?

**핵심 답변/결론:** 복수형 그대로 **criteria**. 단수형: **criterion**. Policy 문서에서 평가 기준·판단 기준을 표현할 때 두 개 이상이면 항상 criteria.

**대화 길이:** 총 6개 메시지 (질문 3개)

---

### 공간적 정합성 번역
**날짜:** 2025-11-29 | **파일:** conversations-004.json

**맥락/질문:** 공간적 정합성을 영어로 번역해줘.

**핵심 답변/결론:** **"Spatial Consistency"** (권장) — 3D annotation, SLAM, multi-sensor fusion, tracking 분야 표준. **"Spatial Coherence"** — 렌더링·영상처리·시각화 문맥. Annotation과 프레임 정합성 맥락에서는 Spatial Consistency가 정식.

**대화 길이:** 총 28개 메시지 (질문 14개)

---

### 객체 명칭 영어 번역
**날짜:** 2025-12-02 | **파일:** conversations-004.json

**맥락/질문:** 이미지에 있는 사물(공사·운반용 간이 객체들)을 구별해서 영어 명칭 알려줘.

**핵심 답변/결론:** Annotation class명 참고용 영어 명칭 정리: Wheelbarrow, Stroller, Cement mixer cart, Flatbed trailer, Garbage truck / Waste collection truck, Utility service truck, Tow truck / Vehicle transporter, 등 — 도로 환경 간이 객체 영문 클래스명 기준으로 활용.

**대화 길이:** 총 219개 메시지 (질문 106개)

---

### Translate animal specification
**날짜:** 2025-12-05 | **파일:** conversations-004.json

**맥락/질문:** "Animal의 Heading Angle은 상체를 기준으로 ±11.46도를 규정한다. - 머리와 상체의 방향이 다른 경우에도 상체를 기준으로 규정한다." "Animal의 GroundPlane은 ±1.71도 이내를 규정한다." 번역해줘.

**핵심 답변/결론:**
- **Heading Angle:** "The Heading Angle of an animal shall be defined based on the torso with an allowable range of ±11.46°. – Even when the head and torso are oriented differently, the Heading Angle shall be determined according to the torso orientation."
- **Ground Plane:** "The Ground Plane of an animal shall fall within ±1.71°."

**대화 길이:** 총 14개 메시지 (질문 7개)

---

### 배리어와 바리케이드 차이
**날짜:** 2026-01-09 | **파일:** conversations-005.json

**맥락/질문:** 배리어와 바리케이드의 차이를 알려줘.

**핵심 답변/결론:**
- **Barrier:** 사람·차량·에너지의 이동을 **제어하거나 위험을 완화**하기 위해 설계된 보호 구조물. 영구/반영구 설치, 규격·성능 기준 존재 (충돌 등급 등). 예: 가드레일, 콘크리트 중앙분리대.
- **Barricade:** 특정 상황(공사, 군중 통제)에서 임시로 통행을 **차단하거나 격리**하는 구조물. 임시 설치, 경량·이동식. 예: 공사 바리케이드, 경찰 통제선.

→ Annotation에서는 Barrier(구조적·영구적)와 Barricade(임시·운영적)를 class로 분리해야 함.

**대화 길이:** 총 8개 메시지 (질문 4개)

---

### 투시 투과 투사
**날짜:** 2026-01-12 | **파일:** conversations-005.json

**맥락/질문:** 그물망 같은 거 통과해서 볼 수 있는 성질을 뭐라고 표현해? 투사? 투과? 투시?

**핵심 답변/결론:** **투과(透過)가 가장 정확.** 빛·시선·신호가 물체를 막히지 않고 통과하는 성질. Annotation 정책에서 "시각적 투과성", "부분 투과 구조"로 표현. Barrier Fence 정의("시각적으로 투과가 가능한 고정형 펜스") 등에 적용. 투시는 X-ray 뉘앙스, 투사는 projection 의미로 부적절.

**대화 길이:** 총 8개 메시지 (질문 4개)

---

### 교량 난간 영어 표현
**날짜:** 2026-01-13 | **파일:** conversations-005.json

**맥락/질문:** 교량에 설치된 난간을 영어로 따로 구분해? 아니면 그냥 rail이라고 해?

**핵심 답변/결론:**
- **Bridge railing** — 교량 가장자리 보행자/차량 추락 방지용 난간. **Annotation 기본 클래스명으로 가장 무난.**
- **Parapet** — 교량 상부 가장자리의 연속적 구조물 (토목·설계 문맥).
- **Bridge guardrail** — 차량 이탈 방지 목적이 강조된 경우.

→ `rail`만으로는 교량 난간을 특정하기 어려움. Barrier Rail class 하위에 `bridge_railing`으로 명시 권장.

**대화 길이:** 총 13개 메시지 (질문 6개)

---

---

## Policy 운영 및 문서화 전략 (2026-02 추가)

> 2026년 2월 이후 Gen1_Gen2_Labeling에서 이전된 항목

### 자세 변화 크기 변화
**날짜:** 2026-02-02 | **파일:** conversations-005.json

**맥락/질문:** "자세 변화로 인한 크기 변화가 허용된다." — 기준 문서·정책 문맥에 맞는 표현 제안 요청.

**핵심 답변/결론:** 권장 표현 (정책·가이드 문맥):
- **가장 중립·표준:** "자세 변화에 따른 객체 크기 변화는 허용된다."
- **검수 기준 문서용:** "자세 변화에 기인한 크기 변동은 annotation 일관성 위반으로 간주하지 않는다."
- **퍼셉션/비전 강조:** "객체의 자세 변화로 인해 발생하는 크기 변화는 정상 범위로 간주한다."

**대화 길이:** 총 16개 메시지 (질문 8개)

---

### 자율주행 객체 검출 용어
**날짜:** 2026-02-05 | **파일:** conversations-005.json

**맥락/질문:** Line 클래스는 color·shape에 따라 성격이 달라져 class로 규정하기 어렵고, attribute는 부가적 느낌. 자율주행 학습 도메인에서 적합한 용어가 있을까?

**핵심 답변/결론:** **"Semantic Variant" (또는 Semantic Type)** — 동일한 physical object(class)에 대해 **법·의미·행동 해석을 바꾸는 하위 의미 타입**. Class와 Attribute 사이 포지션. 예: `Object Class: LaneMarking / Semantic Variant: Solid_Yellow`. 업계에서는 `semantic_type`, `semantic_class`로도 사용됨.

**대화 길이:** 총 44개 메시지 (질문 22개)

---

### AI 기반 정책 관리
**날짜:** 2026-02-09 | **파일:** conversations-005.json

**맥락/질문:** AI driven annotation policy document management — Policy 문서를 Markdown+JSON 포맷으로 작성하고, Git으로 이력 관리하면서 AI를 통해 호환성·정합성 판단이 쉬운 구조로 만드는 것이 목표. Tool 개발 관점에서도 대응하기 쉬운 구조.

**핵심 답변/결론:** **Policy-as-Code 전환 전략.** 문서 포맷 분리: Markdown(인간 중심 — 정책 의도·정의·교육용) + JSON Schema(기계 해석 가능 — validation, 자동 호환성 검사). Git으로 정책 시간축 관리. 흐름: `Policy → Spec → Validation → Tool Behavior`. 목표: "사람이 읽는 정책" → "모델이 해석 가능한 정책 자산".

**대화 길이:** 총 29개 메시지 (질문 14개)

---

### 네이밍 개선 제안
**날짜:** 2026-02-09 | **파일:** conversations-005.json

**맥락/질문:** `DynamicODTarget`, `StaticODTarget` 이름 refine 요청.

**핵심 답변/결론:** 추천 우선순위:
- **`ODDynamicTarget` / `ODStaticTarget`** — OD를 접두로 올려 도메인 범위 명확화, 이행 비용 낮음 (1순위)
- **`DynamicODObject` / `StaticODObject`** — "Target"보다 객체 본질 강조
- **`KinematicODTarget` / `AnchoredODTarget`** — 가장 기술적·정확한 표현 (정책 문서보다 시스템 스펙에 적합)

**대화 길이:** 총 10개 메시지 (질문 5개)

---

### JSON Schema 검토 결과
**날짜:** 2026-02-09 | **파일:** conversations-005.json

**맥락/질문:** "GEN2 Road Scene Annotation Strict Schema" JSON Schema 구조 이상 여부 검토.

**핵심 답변/결론:** **치명적 오류 2건:** ① `cameraConfigs`가 required에 있으나 properties에 정의 없음 → validation fail. ② `roadmarkItem`에 properties 기본 정의 없음. **개선 필요:** objects 배열 내 `frame_intervals` 정합성 기준 명시 필요. 전반적 스키마 개념은 일관되나 구현 누락 다수.

**대화 길이:** 총 2개 메시지 (질문 1개)

---

### 데이터 정책 이미지 요청
**날짜:** 2026-02-10 | **파일:** conversations-005.json

**맥락/질문:** "Data Policy Part" 이름에 어울리는 섹션 커버 이미지 생성 요청.

**핵심 답변/결론:** 생성 프롬프트: "Abstract architecture of data governance: layered documents, flow diagrams, structured grids, interconnected nodes. Visual metaphors for policy, rules, and control — checklists, schemas, versioned documents, directional arrows. Deep blue, slate gray, white palette. Flat + isometric hybrid design." — 정책 문서 커버 이미지 기준 확립.

**대화 길이:** 총 10개 메시지 (질문 5개)

---

### 정책 실효성 검증 표현
**날짜:** 2026-02-11 | **파일:** conversations-006.json

**맥락/질문:** "정책의 유효성"이라는 표현 어때? 수립된 정책이 어떤지 직접 어노테이션을 해보며 점검할 계획.

**핵심 답변/결론:** "유효성"은 추상적·법적 뉘앙스. 실제 annotation으로 점검하는 의도에는 **"정책의 실효성 검증"** 이 가장 정확. 활용 예: "수립된 정책의 실효성을 실제 annotation을 통해 검증한다." DQA/검수 문서에서는 **"정책 적용 가능성 검증(Policy Applicability Verification)"** 도 사용 가능.

**대화 길이:** 총 4개 메시지 (질문 2개)

---

### Policy review 표현 수정
**날짜:** 2026-02-13 | **파일:** conversations-006.json

**맥락/질문:** "Policy review on Annotation data" 표현 어때?

**핵심 답변/결론:** `review on` → `review of`로 수정 필요. 의도에 따른 권장안:
- **정책 기준으로 데이터 검토:** "Policy Review of Annotation Data"
- **데이터로 정책 타당성 검증:** "Annotation Data Review for Policy Validation"
- **정책 재정비 목적:** "Annotation Policy Review & Update"

**대화 길이:** 총 4개 메시지 (질문 2개)

---

### 상반기 Policy 목표 설정
**날짜:** 2026-02-24 | **파일:** conversations-006.json

**맥락/질문:** MVGen2 Annotation Policy의 호환 및 자동화된 이력 관리체계로 전환, AI 환경에서 활용도 높은 자산화. 상반기 Goal·KPI 구체화 요청.

**핵심 답변/결론:** 3개 Goal 재정의:
- **Goal 1:** MVGen2 Annotation Policy를 Git-Managed 구조로 전환 (문서 → 버전 관리 자산)
- **Goal 2:** Policy Output Schema 표준화, 모든 필드 Acceptance Criteria 명문화
- **Goal 3:** AI 학습/검증 파이프라인에서 활용 가능한 정책 자산 구조 완성

KPI 클러스터: Git 기반 정책 전환율 / Acceptance Criteria 정의율 / Policy-as-Code 활용도. 핵심 메시지: "설명 중심 문서" → "검증 가능한 스펙 문서".

**대화 길이:** 총 24개 메시지 (질문 12개)

---

*생성일: 2026-03-14 | Gen1_Gen2_Labeling_대화_학습_정리.md 에서 분리*
*2026-03-14 업데이트: 2026-02 항목 9개 추가 이전*
