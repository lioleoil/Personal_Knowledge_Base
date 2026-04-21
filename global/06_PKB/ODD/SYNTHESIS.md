# ODD 지식 합성

> 마지막 갱신: 2026-04-22 07:56 | 기반 항목 수: 17

---

# ODD (운행설계영역) 위키 합성 문서

## 핵심 지식

1. **ODD는 메타데이터다**: ODD(Operational Design Domain)는 데이터 자체의 내용이 아니라 **시스템이 작동 가능한 환경 조건을 기술하는 메타데이터**다. 반대로 "Meta tag = ODD 정보"는 성립하지 않는다. (태그는 ODD 외 다른 메타 정보도 포함)

2. **OpenODD의 역할과 포맷**: OpenODD는 ASAM 표준 기반으로 **자율주행이 가능한 운행 조건(날씨, 도로 유형, 속도 등)을 명세**하는 포맷이다. OpenLABEL의 ontology tag와 다른 점은, OpenLABEL은 객체·어노테이션 정보를 담고 OpenODD는 시스템 작동 전제 조건(환경 제약)을 정의한다는 것이다.

3. **OpenX 전환 전략의 계층 구조**: 실무 전환 흐름은 다음 3단계로 정립됨:
   - **1단계 OpenODD** → 내부 XML 데이터를 YAML로 변환 후 OpenLABEL과 Merge
   - **2단계 OpenDRIVE** → 3D Annotation JSON을 `.xodr` 포맷으로 변환, OpenSCENARIO에서 참조
   - **3단계 OpenSCENARIO** → 내부 YAML 시나리오를 OpenSCENARIO 표준으로 변환

4. **OpenDRIVE는 XML 기반, 확장자는 `.xodr`**: 포맷 자체는 표준 XML 문법을 따르며, `.xodr`는 단순히 OpenDRIVE 전용 확장자명이다. OpenSCENARIO는 `.xodr` 파일을 직접 참조하여 도로 구조 정보를 불러온다.

5. **OpenSCENARIO 버전 분기**: v1.x는 XML 기반, v2.0은 DSL(Domain-Specific Language) 기반으로 구조가 크게 다르다. ASAM OpenSCENARIO v2.0은 공식 배포 확인 필요. 내부 YAML 시나리오와의 호환성은 버전별로 상이하므로 전환 전 버전 정합성 검토가 필수다.

6. **ODD 데이터의 DB 설계**: `raw_data_key`를 Primary Key로 하는 테이블 구조로 ODD 정보를 관리하며, YAML 스키마로 필드 타입·nullable·설명을 명세하는 방식이 채택됨. JSON 파일 구조 분석 시 `rawDataKey` 1개당 1개의 시트로 분리하는 방식이 유효하다.

---

## 반복 등장 패턴

- **OpenX 표준 간 관계 정리 반복**: OpenODD → OpenSCENARIO → OpenDRIVE → OpenLABEL 간의 역할 분담과 데이터 흐름을 여러 대화에서 반복적으로 재정의함. 개념 혼동이 자주 발생하는 지점임
- **내부 포맷 → 표준 포맷 변환 문제**: 사내에서 사용하는 XML/YAML/JSON 포맷을 OpenX 표준으로 변환하는 실행 방법을 지속적으로 탐색 중
- **약어 해석 요청 반복**: MCIP, COD, CCAN/PCAN 등 자율주행 도메인 약어의 정확한 의미를 반복적으로 질의함 → 내부 용어 사전 부재 가능성
- **ODD 조건 표현 방식 탐색**: `weather.rain: none`, `road.type: urban` 같은 키-값 형태의 ODD 조건 표기법을 여러 맥락에서 예시로 사용함

---

## 미해결 질문

- **ASAM OpenSCENARIO v2.0의 공식 배포 상태**: v2.0이 정식 릴리즈되었는지, 내부 YAML 기반 시나리오와 실제 호환 가능한지 검증되지 않음
- **ASAM OpenODD의 COD(Concept of Operations Document?) 정확한 정의**: 검색 기반으로 확인 시도했으나 명확한 결론 문서 부재
- **OpenSCENARIO 기반 시뮬레이션 결과 → OpenLABEL export 시 툴 지원 범위**: action/event와 객체 매핑이 툴 기본 사양인지, 커스텀 구현이 필요한지 완전히 확정되지 않음
- **내부 JSON 파일의 `rawDataKey` 기반 구조 분석 완료 여부**: 엑셀 추출 작업이 진행 중이며 최종 결과 확인 필요

---

## 관련 카테고리

- **자율주행 표준 (ASAM OpenX 시리즈)**: OpenDRIVE, OpenSCENARIO, OpenLABEL, OpenODD 전체 연계
- **시나리오 기반 테스트 (Scenario-Based Testing)**: ODD 조건 → 시나리오 설계 → 시뮬레이터 실행 파이프라인
- **데이터 어노테이션 및 레이블링**: OpenLABEL, ontology tag, 3D Annotation JSON 관리
- **차량 네트워크 (CAN)**: CCAN/PCAN 구조 — ODD 조건 판단에 필요한 차량 상태 데이터 소스
- **HD Map / 도로 데이터**: OpenDRIVE 기반 정밀 지도, 시나리오 실행의 공간 기반 정보
