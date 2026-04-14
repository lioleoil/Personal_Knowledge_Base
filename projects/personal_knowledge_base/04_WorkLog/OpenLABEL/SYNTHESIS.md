# OpenLABEL 지식 합성

> 마지막 갱신: 2026-04-14 19:39 | 기반 항목 수: 30

---

# OpenLABEL 위키 합성 문서

## 핵심 지식

1. **OpenLABEL 최상위 필드 구조**: 스키마가 정의하는 최상위 필드는 총 13개이며, 필수(`required`) 필드는 `metadata` 단 하나뿐이다. 나머지 필드(`objects`, `frames`, `streams`, `coordinate_systems`, `frame_intervals` 등)는 선택적이나, 실질적 데이터 표현을 위해 조건부로 필요하다.

2. **SV → OpenLABEL 필드 매핑 핵심 규칙**: SV의 `bbox3d Cuboid` 변환 시 축 매핑이 직관과 다르다. `width→sy`, `height→sz`, `length→sx`로 변환해야 하며, 회전은 쿼터니언 `(w, x, y, z)` 형식으로 LCS 좌표계 기준 radian 단위 float(18)로 표현한다.

3. **`transformations` 위치는 전역 구조가 표준**: `transformations`를 각 프레임 하위에 반복 배치하지 않고, `openlabel` 상위 전역 구조에 두는 이유는 **데이터 정규화(normalization)** 때문이다. 프레임마다 동일한 변환 행렬을 중복 기재하는 것은 OpenLABEL 설계 원칙에 반한다.

4. **멀티 프레임 시퀀스 정렬 기준**: 비전 퍼셉션(객체 탐지) 관점과 차량 제어 소프트웨어 관점 모두 **frame timestamp 기준 정렬**이 원칙이다. 단, GPS처럼 저주기(low-frequency) 센서는 timestamp 보간(interpolation) 또는 nearest-frame 매핑 전략이 별도로 필요하다.

5. **`object_data_pointers` 역할**: 객체 데이터를 직접 중복 저장하지 않고, 프레임·스트림·좌표계 맥락에서 "어느 프레임의 어떤 데이터가 이 객체에 속하는지"를 참조(reference)하는 포인터 구조다. 실제 데이터는 `object_data`에 위치한다.

6. **변환 스크립트 경로 관리**: 템플릿 JSON을 다른 폴더에서 읽을 때 `__file__` 기준 상대경로(`os.path.join(os.path.dirname(__file__), ...)`)로 설정해야 실행 위치에 관계없이 안정적으로 동작한다.

---

## 반복 등장 패턴

- **포맷 검증 반복**: OpenLABEL 샘플/예시 JSON을 작성한 뒤 "이 포맷이 적절한가"를 재확인하는 흐름이 여러 대화([17], [22], [27])에서 반복됨. 한 번에 완성되지 않고 필드 누락 → 수정 → 재검토 사이클이 지속적으로 발생함.

- **좌표계 혼선**: VCS, LCS 등 좌표계 명칭과 축 방향 매핑([16], [9], [11])이 반복적으로 등장하며, 변환 스크립트 버그의 주요 원인으로 작용함.

- **스크립트 버그 수정 루프**: `image_info` 미생성([15]), `width/height/length` 축 매핑 오류([16]), 경로 오류([12]) 등 변환 스크립트에서 크고 작은 버그가 반복 발생하고 있음.

- **용어 정의 요구**: `conversion script` vs `migration script`, `convert`의 명사형, 한국어 클래스명 등 **명칭/용어 통일** 이슈가 반복
