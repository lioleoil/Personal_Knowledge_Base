# ODD 지식 합성

> 마지막 갱신: 2026-04-14 19:51 | 기반 항목 수: 17

---

# ODD 주제 위키 합성 문서

## 핵심 지식

1. **ODD 정보는 메타데이터이며, Meta tag와 ODD는 동치가 아니다**
   - ODD(Operational Design Domain)는 데이터 내용 자체가 아니라 **데이터가 수집된 환경 조건을 설명하는 메타데이터**다
   - 반면 "Meta tag = ODD 정보"는 성립하지 않음: Meta tag는 ODD 외에도 다양한 정보를 포함할 수 있음
   - 실무 적용: raw_data_key 기반 테이블 설계 시 ODD 필드는 메타 레이어로 분리해서 관리

2. **OpenODD는 ASAM 표준 기반의 ODD 명세 포맷이며, OpenLABEL의 ontology tag와 역할이 다르다**
   - OpenODD: 자율주행 시스템이 **작동 가능한 환경 조건**을 정의 (예: `weather.rain: none`, `road.type: urban`)
   - OpenLABEL ontology tag: 객체/이벤트의 **분류 체계**를 정의
   - 전환 전략: 내부 XML 포맷 기반 ODD 데이터를 YAML로 변환 후 OpenLABEL과 Merge하는 방식이 현실적

3. **ASAM OpenODD의 COD(Conditions of Domain)는 ODD의 세부 조건 집합을 구조화하는 단위다**
   - OpenX 체계 안에서 ODD → Scenario → Simulation → Label 순서로 계층적으로 연결됨
   - COD는 이 체계에서 ODD 조건을 분류·구조화하는 핵심 구성 요소

4. **OpenX 시리즈 전환 전략의 실무 매핑 구조**
   - OpenODD: 내부 XML → YAML 변환 → OpenLABEL Merge
   - OpenDRIVE: 3D Annotation JSON → `.xodr` 변환 → OpenSCENARIO에서 참조
   - OpenSCENARIO: 내부 YAML 시나리오 파일 기반으로 작성 (v2.0 DSL 또는 v1.x XML)
   - OpenLABEL: 시뮬레이션 결과 export 시 action/event가 객체와 매핑되어 출력되는 것이 툴 기본 사양

5. **raw_data_key를 Primary Key로 하는 ODD 테이블 구조가 데이터 관리의 기준 단위**
   - raw_data_key 1개 = 하나의 수집 세션/클립에 대응
   - YAML 스키마로 필드 타입, nullable, 설명까지 정의해서 관리
   - 엑셀 추출 시 raw_data_key 1개당 1시트로 구성하는 방식이 가독성 확보에 유리

6. **OpenSCENARIO v1.x(XML)와 v2.0(DSL) 중 내부 YAML 기반 시나리오와의 호환은 v2.0 DSL 방향이 더 적합**
   - v1.x는 XML 기반으로 YAML과 직접 호환 불가, 변환 레이어 필요
   - v2.0은 DSL 문법 기반으로 구조적 유연성이 높아 YAML 시나리오 마이그레이션에 유리
   - OpenDRIVE(`.xodr`)는 XML 문법 기반이며, 확장자만 다를 뿐 표준 XML 파서로 처리 가능

---

## 반복 등장 패턴

- **OpenX 표준 전환 필요성 반복 확인**: OpenODD, OpenDRIVE, OpenSCENARIO, OpenLABEL 4종 세트를 내부 포맷에서 표준 포맷으로 전환하는
