# Gen2_Policy 지식 합성

> 마지막 갱신: 2026-04-14 19:50 | 기반 항목 수: 30

---

# Gen2_Policy 위키 합성 문서

## 핵심 지식

1. **Policy-as-Code 전환 원칙**: MVGen2 Annotation Policy는 일반 문서가 아닌 Markdown+JSON 포맷으로 작성하고 Git으로 버전 관리하는 구조로 전환해야 한다. 이를 통해 AI 호환성·정합성 판단, Tool 개발 대응, 자동화된 이력 관리가 가능해진다. 공통 네이밍 규칙: `MV_<FEATURE>_vA.B → MV_<FEATURE>_3D_BoundBox_vA.B.0`

2. **Gen2 OD 구조의 핵심 전환점**: Frame-based Gen1 OD와 Map-based Gen2 OD는 성격이 구조적으로 다르다. Frame-based는 미시적·선형, Map-based는 거시적·비선형(재사용성 큼)이므로 단순 Output 기준 직접 비교는 성립하지 않는다. 작업 공수 비교 시 "최대 밀집 구간 피크값" 기준 사용은 위험하며, 시퀀스 전체 객체수 기반으로 접근해야 한다.

3. **Sequence 기반 정책 조항 설계 순서**: Vehicle 관련 조항은 ① Type Classification Criteria → ② Sequence Annotation Method → ③ Attribute Definition 순서로 배치한다. 조항 제목은 선언적·규범적 표현(`Definition`, `Rules`, `Criteria`)을 우선하고, `Guidelines`는 원칙·가이드 성격일 때 사용한다.

4. **Visibility·Occlusion·FoV 3개념 구분 기준**:
   - **FoV(기하학적)**: 센서가 이론적으로 관측 가능한 공간 범위 (고정 스펙, occlusion/조도 미포함)
   - **Visibility**: FoV 내부의 실제 가시성 (가려짐, 조도, 포인트 밀도 포함)
   - **Occlusion**: 기하학적 가림 (다른 객체에 의해 차단)
   - 조도 문제로 인식 불가 속성명은 `illumination_insufficient` 계열 권장 (`occluded`·`visibility=false` 사용 금지)

5. **클래스 정의 시 기능 vs 형태 혼재 방지**: Barrier(Solid/Rail/Fence/Temporary), Obstacle(cone/cylinder/bollard 등) 조항 모두에서 동일한 문제 발생 — 기능 정의와 형태 정의가 혼재되면 Cuboid 분할 규칙(15m 기준 등)과 연결이 끊어진다. 정의 문장에는 구조적 특성("연속적 또는 분절형")을 명시하여 측정 기준과 자연스럽게 연결해야 한다.

6. **속성값 네이밍 원칙**: 객체 자체의 물리적 특성은 상대 위치 표현이 아닌 절대 속성 표현을 사용한다. 예: Pole 높이 → `low/high`(위치 기준) ❌, `short/tall`(물리적 길이) ✅. 도메인 접두사는 앞에 배치: `DynamicODTarget` ❌ → `ODDynamicTarget` ✅

---

## 반복 등장 패턴

- **정책 문서 표현 정제 요청 반복**: `review on → review of`, `유효성 → 실효성 검증`, `투사/투시 → 투과`, `low/high → short/tall` 등 한국어·영어 표현 모두에서 추상적·혼용 표현을 정밀 표현으로 교체하는 작업이 지속적으로 반복됨

- **클래스 경계 모호성 문제**: Barrier Fence vs Rail,
