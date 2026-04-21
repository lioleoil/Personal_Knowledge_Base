# OpenLABEL 지식 합성

> 마지막 갱신: 2026-04-22 07:57 | 기반 항목 수: 30

---

# OpenLABEL 위키 합성 문서

## 핵심 지식

1. **OpenLABEL 최상위 스키마 구조**: 총 13개 최상위 필드를 정의하며, 유일한 필수 필드(`:required`)는 `metadata`뿐이다. 나머지 필드(`frames`, `objects`, `streams`, `coordinate_systems` 등)는 조건부 필수 또는 선택적으로 사용된다.

2. **SV → OpenLABEL 필드 매핑 핵심 규칙**: SV bbox3d Cuboid를 OpenLABEL VCS 좌표계로 변환할 때 `width→sy`, `height→sz`, `length→sx` 순서로 매핑해야 한다. 쿼터니언(w, x, y, z) 기반 회전 표현을 사용하며 단위는 radian, float 정밀도는 float(18)을 기준으로 한다.

3. **`transformations` 전역 배치 원칙**: `transformations`는 `frames` 하위가 아닌 `openlabel` 최상위에 배치한다. 이유는 데이터 정규화(normalization)로, 동일 좌표계 변환 정보를 프레임마다 중복 기재하지 않기 위함이다. 단, 프레임별로 변환값이 동적으로 바뀌는 경우에는 `frames` 하위에 별도로 기재할 수 있다.

4. **변환 스크립트 경로 관리**: `SV_to_OpenLABEL` 변환 스크립트에서 템플릿 JSON 파일을 참조할 때 `__file__` 기준 상대경로를 사용해야 실행 위치와 무관하게 안정적으로 파일을 불러올 수 있다.

5. **`image_info` 필드 생성 조건**: `stream_properties`가 없는 경우에도 `channel` 이름만으로 `image_info`를 생성하도록 변환 로직을 설계해야 버그 없이 출력 포맷이 완성된다.

6. **멀티 프레임 시퀀스 정렬 기준**: 비전 퍼셉션(객체 탐지) 관점에서는 카메라 timestamp 기준으로, 차량 제어 소프트웨어 관점에서는 LiDAR timestamp 기준으로 정렬하는 것이 권장된다. GPS 같은 저주기 센서는 timestamp 보간(interpolation) 또는 nearest-match 전략을 별도로 적용해야 한다.

---

## 반복 등장 패턴

- **OpenLABEL 포맷 검증 반복 요청**: 작성한 JSON 샘플이나 문서 문장이 OpenLABEL 공식 스펙에 부합하는지 여러 차례 교차 검토 요청이 있었음 (대화 [13], [14], [17], [22])
- **SV↔OpenLABEL 변환 스크립트 디버깅**: 좌표 매핑 오류, 경로 문제, 필드 누락 등 변환 스크립트 관련 버그 수정이 반복적으로 발생함 (대화 [12], [15], [16], [20])
- **좌표계 및 회전 표현 확인**: 쿼터니언 구성값, LCS/VCS 좌표계 구분, 단위(meter/radian) 확인 질문이 여러 시점에 걸쳐 반복됨 (대화 [9], [10], [11], [16])
- **policy 문서 작성용 포맷 정의**: 실무 정책 문서에 들어갈 필드 단위·속성·범위 정의를 OpenLABEL 기준으로 정제하려는 작업이 지속됨 (대화 [6], [9], [14])

---

## 미해결 질문

- **`frame_interval`의 하위 필드 활용 범위**: `frame`과 동일 레벨에 있는 `frame_interval`을 하위 필드로 활용할 수 있는지, 단순 프레임 구간 정보 외의 데이터를 담을 수 있는지 명확히 정리되지 않은 상태 (대화 [23], [24])
- **`object_data_pointers` 실제 운용 방식**: 설명은 존재하나, SV 마이그레이션 스크립트에서 이 필드를 실제로 어떻게 생성·연결하는지 구현 예시가 완결되지 않음 (대화 [7])
- **OpenLABEL output format 엑셀 정의 완성 여부**: `schema` 필드부터 시작한 정책 문서용 포맷 정의가 이후 대화에서 완결되었는지 불명확함 (대화 [6])

---

## 관련 카테고리

- **좌표계 변환**: LCS, VCS 좌표계, 쿼터니언, 센서 캘리브레이션, deskewing
- **SV 포맷 (StandardJson_v1.0)**: SV 출력 포맷 구조, bbox3d Cuboid 필드 정의
- **센서 퍼셉션 파이프라인**: 멀티 프레임 시퀀스, 카메라/LiDAR/GPS 스트림 정렬
- **ASAM 표준군**: OpenLABEL, OpenODD (ODD taxonomy, 클래스 분류 체계)
- **Git / 개발 환경**: 변환 스크립트 브랜치 관리, 경로 설정 (`__file__` 기준)
- **데이터 레이블링 정책 문서**: 클래스명 정의, attribute 명칭 표준화, output format 엑셀 명세
