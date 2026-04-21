---
tags:
  - gen2
  - policy
  - annotation
  - sequence-based
  - autonomous-driving
  - pkb
  - synthesis
aliases:
  - Gen2_Policy 합성
  - Gen2 어노테이션 정책
category: Gen2_Policy
source: "[[Gen2_Policy_대화_학습_정리]]"
updated: 2026-04-22
---

# Gen2_Policy 지식 합성

> 마지막 갱신: 2026-04-22 07:54 | 기반 항목 수: 30

---

# Gen2_Policy 위키 합성 문서

## 핵심 지식

1. **Policy-as-Code 전환 원칙**: MVGen2 Annotation Policy는 단순 문서가 아닌 Markdown+JSON 포맷으로 작성하고 Git으로 버전 관리하는 구조로 전환해야 한다. 목표는 AI 호환성·정합성 판단이 가능한 자산화이며, `MV_<FEATURE>_vA.B → MV_<FEATURE>_3D_BoundBox_vA.B.0` 패턴의 버전 변환 규칙이 공통 적용된다.

2. **Sequence(Map-based) vs Frame-based 작업 공수 비교의 구조적 제약**: Gen2 Map-based OD와 Gen1 Frame-based OD는 작업 성격(거시적·비선형 재사용성 vs 미시적·선형)이 근본적으로 달라 단순 Output 수량 비교가 성립하지 않는다. "최대 밀집 구간 × 프레임수" 방식은 피크값 편향이 발생하므로, 동일 금액 대비 산출 결과를 기준으로 비교하는 것이 타당하다.

3. **조항 용어 선택 기준 — 기능 정의 우선, 형태 정의 배제**: Barrier(Solid/Rail/Fence/Temporary), Obstacle(cone/bollard 등), Vehicle 분류 등 모든 클래스 정의에서 **형태 기술보다 기능 중심 정의**가 원칙이다. 예: Barrier는 "이동 제어·위험 완화 구조물", Barricade는 "임시 차단·격리 구조물"로 구분. Cylinder vs Bollard처럼 경계가 모호한 경우 **차단 의도와 물리적 결과**를 기준으로 구분한다.

4. **Visibility / Occlusion / FoV 속성의 명확한 구분 체계**:
   - `FoV(기하학적)`: 센서가 이론적으로 관측 가능한 공간 범위 (조도·가림 미포함)
   - `Visibility`: FoV 내부에서 실제 가시 여부 (조도, 포인트 밀도, 가려짐 포함)
   - `Occluded`: 기하학적 가림
   - `illumination_invisible`(권장): 객체는 존재하나 조도/노출 문제로 시각적 식별 불가 (not visible ≠ not present)
   - `ignored`는 의도적 배제에만 사용, 위 상황에 혼용 금지

5. **정책 문서 영문 조항 작성 표준**:
   - 높이 속성: `short/tall`(객체 자체 길이) vs `low/high`(기준면 대비 위치) — Pole에는 `short/tall` 적용
   - 범위 표현: `radius`와 방향 `directions` 조합은 의미적으로 어색 → "200 m in the forward, rear, and lateral directions" 형태로 수정 권장
   - 실효성 검증 표현: "정책의 유효성" → **"정책의 실효성 검증(Policy Effectiveness Validation)"** 으로 대체
   - "Policy review on" → **"Policy review of"** 로 수정

6. **클래스 네이밍 우선순위 원칙**: 도메인 범주를 접두로 올리는 구조가 권장된다. 예: `DynamicODTarget` → `ODDynamicTarget`(1순위), Annotation 클래스 제목은 **"Class-Specific Annotation Rules"** 가 정책 문서 표준으로 가장 적합.

---

## 반복 등장 패턴

- **용어 정밀화 요청 반복**: 한국어·영어 모두에서 용어의 뉘앙스 차이를 정확히 구분하는 작업이 지속적으로 등장함 (투과/투시/투사, 유효성/실효성, review on/of, short/tall vs low/high 등). 정책 문서의 법적·기술적 해석 가능성을 고려한 표현 선택이 핵심 과제임.

- **Gen1 → Gen2 전환 근거 문서화 필요**: ODD v2.7.0 구조에서 Gen2로의 전환 필요성, 작업 공수 비교, 성능 측정 전략 등이 반복적으로 등장. 단순 선언이 아닌 **스펙 비교 테이블 + 전환 효과** 구조로 논리를 뒷받침하는 문서가 지속적으로 요구됨.

- **클래스 경계 모호성 해결**: Barrier vs Barricade, Cylinder vs Bollard, FoV vs Visibility처럼 **인접 개념 간 경계 정의**가 반복적으로 필요. 매번 기능·의도·물리적 결과 기준으로 해소하는 패턴이 일관됨.

- **Cuboid(3D) 라벨링 규칙의 구체화**: 도로 위 간이 객체(cone, barrier, obstacle 등)를 Cuboid로 표현해야 하는 이유와 분할 규칙(15m 기준 등)이 여러 조항에서 반복 등장.

---

## 미해결 질문

- **Gen2 작업 공수 측정 방식의 최종 확정**: Map-based와 Frame-based의 직접 비교가 구조적으로 성립하지 않는다는 결론은 나왔으나, **실제 단가 산정에 적용할 수 있는 대안 비교 모델**이 아직 구체화되지 않음.

- **`ODDynamicTarget` / `ODStaticTarget` 네이밍 최종 채택 여부**: 1순위 권장안이 제시되었으나, 실제 스키마 및 정책 문서에 반영 여부가 확인되지 않음.

- **JSON Schema 치명적 오류 수정 완료 여부**: `cameraConfigs` required 오류 및 `roadmarkItem` properties 미정의 2건의 수정이 권고되었으나, 수정된 최종 스키마 버전이 로그에 등장하지 않음.

- **상반기 Goal 3개 중 Goal 2·3의 구체적 내용**: Goal 1(Git-Managed 구조 전환)만 명시되고 나머지 목표 내용이 로그에서 잘림(truncated).

- **`illumination_invisible` 외 조도 관련 속성의 전체 체계**: 단일 값 권장안은 도출되었으나, Visibility 속성 전체 값 목록(enum)과 타 속성과의 우선순위 규칙이 정리되지 않음.

---

## 관련 카테고리

- **ODD_Schema**: v2.7.0 ODD 구조, `cameraConfigs` JSON Schema, Gen2 DB ODD 매핑
- **Gen2_Cost_Model**: Phase 1 성능 측정 전략, Map-based vs Frame-based 공수 산정, 단가 모델
- **Annotation_Taxonomy**: 클래스 계층 구조(Barrier/Obstacle/Vehicle/Animal), Semantic Variant 개념, Class-Specific Rules
- **Policy_Versioning**: Git 기반 이력 관리, Policy-as-Code, 버전 변환 규칙(`3D_BoundBox_vA.B.0`)
- **Label_Quality / DQA**: Occlusion·Truncation·Visibility 기준, 실효성 검증, 검수 기준 문서

---

## 연결 노드 (Obsidian Graph)

> PKB 내 직접 연결 문서

- 📄 소스: [[Gen2_Policy_대화_학습_정리|Gen2_Policy 대화 로그 (30건)]]
- 🔗 [[Gen1_Gen2_Labeling/SYNTHESIS|Gen1_Gen2_Labeling]] — Gen1 vs Gen2 비교, 버전 변환 규칙
- 🔗 [[ODD/SYNTHESIS|ODD]] — ODD v2.7.0 스펙, Gen2 ODD 매핑
- 🔗 [[DQA/SYNTHESIS|DQA]] — Occlusion/Truncation 기준, 검수 기준 연계
