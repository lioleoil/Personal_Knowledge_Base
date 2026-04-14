# Gen2_Policy 지식 합성

> 마지막 갱신: 2026-04-14 19:37 | 기반 항목 수: 30

---

# Gen2_Policy 위키 합성 문서

## 핵심 지식

1. **Policy-as-Code 전환 원칙**: MVGen2 Annotation Policy는 일반 문서가 아닌 Markdown+JSON 포맷으로 작성하고 Git으로 버전 관리하는 구조로 전환해야 한다. 목표는 AI 호환성·정합성 판단이 쉬운 자산화이며, 공통 규칙은 `MV_<FEATURE>_vA.B → MV_<FEATURE>_3D_BoundBox_vA.B.0` 형식으로 버전 체계를 통일한다.

2. **Gen2 OD의 Map-based 특성과 비용 측정 주의사항**: Gen2 Sequential OD는 Frame-based(미시적·선형)가 아닌 Map-based(거시적·비선형, 재사용성 큼) 구조이므로, Gen1 MV OD와 Output 수량 기준으로 직접 비교하는 것은 구조적으로 성립하지 않는다. 비용 측정 시 "최대 밀집 구간 피크값" 기준은 왜곡 위험이 있으며, 동일 금액 대비 결과물 품질 비교 방식이 더 적합하다.

3. **Sequence 기반 정책의 클래스 정의 원칙**: 클래스 정의 시 기능 중심 분류와 형태 기반 정의를 혼재하면 Cuboid 분할 규칙(예: Barrier 15m 규칙)과 충돌한다. 정의 문장에 구조 형태("연속적 또는 분절형")를 명시하여 검수 기준과 자연스럽게 연결해야 한다. Obstacle의 Cylinder vs Bollard처럼 유사 클래스는 "차단 의도"와 "물리적 결과"를 기준으로 경계를 명확히 해야 한다.

4. **Visibility·Occlusion·FoV 3개념의 명확한 구분**: FoV는 ①기하학적 관측 가능 공간(고정 스펙, occlusion 미포함)과 ②FoV 내 실제 가시성(Visibility)으로 구분된다. 어두워서 식별 불가한 객체는 `occluded`(기하적 가림)나 `visibility=false`가 아닌 `illumination_obscured`(또는 유사 명칭)로 별도 attribute를 부여해야 한다. Base Rule에 Occlusion/Truncation/Visibility 조항을 독립 챕터로 추가하는 것이 권장된다.

5. **정책 문서 용어 선택 기준**: 정책·가이드 문서에서 용어 선택은 의미의 정밀도가 핵심이다. 주요 확정 사례: "유효성" → **"실효성 검증"**, `review on` → **`review of`**, `low/high`(위치) → **`short/tall`**(물리적 길이), "투사/투시" → **"투과"**(시각적 통과 성질), Barrier vs Barricade(영구 보호 구조물 vs 임시 차단 구조물).

6. **상반기 3대 Goal 체계**: ①MVGen2 Annotation Policy를 Git-Managed 구조로 전환(문서→버전 관리 자산), ②Policy 실효성을 실제 annotation 수행으로 검증, ③Gen2 ODD 전환 필요성 문서화(스펙 비교 테이블 중심, 전환 효과: Data Selection·관리·Cost Control).

---

## 반복 등장 패턴

- **용어 정제 요청 반복**: 한국어 정책 표현("유효성", "투과", "자세 변화로 인한") 및 영어 표현("review on", `low/high`, `DynamicODTarget`) 모두 정밀한 용어
