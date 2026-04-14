# OpenLABEL 지식 합성

> 마지막 갱신: 2026-04-14 19:51 | 기반 항목 수: 30

---

# OpenLABEL 위키 합성 문서

## 핵심 지식

1. **OpenLABEL 최상위 스키마는 13개 필드이며, 유일한 필수 필드는 `metadata`다.** 나머지 필드(`frames`, `objects`, `streams`, `coordinate_systems` 등)는 조건부 필수 또는 선택 필드이며, 커스텀 확장 필드도 허용된다.

2. **SV → OpenLABEL 변환 시 3D bbox 좌표 매핑 규칙은 `width→sy`, `height→sz`, `length→sx`이며, 좌표계는 VCS(Vehicle Coordinate System) 기준으로 정렬해야 한다.** 회전은 쿼터니언 `(w, x, y, z)` 4값으로 표현하고 단위는 radian, float(18)을 사용한다.

3. **`transformations` 필드는 프레임 하위가 아니라 전역 구조 상위에 배치하는 것이 표준이다.** 이유는 데이터 정규화(normalization)로, 프레임마다 중복 저장을 방지하기 위함이다. 단, ASAM 공식 샘플에는 프레임마다 포함된 예시도 존재한다.

4. **변환 스크립트에서 템플릿 JSON 파일 경로는 `__file__` 기준 상대경로로 설정해야 한다.** 실행 환경(CWD)이 달라져도 스크립트가 올바른 경로를 참조할 수 있도록 하기 위해서다. (`Path(__file__).parent / "template.json"` 패턴 사용)

5. **멀티 프레임 시퀀스 정렬 기준은 목적에 따라 다르다.** 비전 퍼셉션(객체 탐지) 관점은 `timestamp` 오름차순 정렬이 기본이고, 차량 제어 소프트웨어 관점은 센서 스트림 동기화(deskewing, 보간)를 우선 처리해야 한다. GPS 같은 저주기 센서는 별도 보간 전략이 필요하다.

6. **`object_data_pointers`는 `object_data`를 중복 저장하지 않고, 프레임/스트림/좌표계 맥락에서 해당 데이터의 위치를 참조(pointer)하는 방식으로 동작한다.** 하위 필드로는 `frame_intervals`, `attribute_pointers`, `element_data_pointers` 등이 포함된다.

---

## 반복 등장 패턴

- **포맷 검증 반복 요청**: OpenLABEL full structure 예시가 스펙에 맞는지 반복적으로 검토 요청됨 (로그 [17], [22], [14]). 특히 필수 필드 누락, 커스텀 필드 허용 여부, 조건부 필수 필드 혼동이 주요 오류 원인이었음.

- **SV 포맷 ↔ OpenLABEL 매핑 작업**: 변환 스크립트 작성 → 버그 수정 → 경로 문제 해결의 반복 사이클이 여러 세션에 걸쳐 진행됨 (로그 [20], [16], [15], [12]).

- **영문 용어 정확성 확인**: `conversion script` vs `migration script`, `convert`의 명사형(`conversion`) 등 문서 작성 중 영문 표현의 정확성을 재확인하는 패턴이 반복됨 (로그 [25], [23]).

- **좌표계 및 단위 정의 혼란**: Width/Length/Height의 OpenLABEL 내 sx/sy/sz 매핑, LCS vs VCS 좌표계 구분, radian 단위 표기 등이 여러 대화에
