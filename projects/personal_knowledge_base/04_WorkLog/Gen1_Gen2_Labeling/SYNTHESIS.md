# Gen1_Gen2_Labeling 지식 합성

> 마지막 갱신: 2026-04-14 19:49 | 기반 항목 수: 30

---

# Gen1_Gen2_Labeling 지식 위키

## 핵심 지식

1. **Gen1 vs Gen2 OD 비교 구조**: Gen1은 Frame-based MV OD, Gen2는 Map-based Sequential OD로 설계된다. 작업 공수 비교 시 결과물(Output) 수량 직접 비교는 구조적으로 부적합하며, **동일 비용 대비 산출물 품질/양**을 축으로 비교하는 것이 유효하다. (대화 [22], [20])

2. **Gen2 ODD 전환 필요성 논거**: ODD v2.7.0에서 Gen2 정책으로의 전환은 데이터 선별·관리 및 Cost Control 목적에서 필수불가결하다. 두 정책의 스펙을 테이블 형태로 비교하는 문서 구조가 권장된다. MVGen2 OD 시나리오 요구사항 충족 여부는 v2.7.0 ODD 문서 기반으로 검증된다. (대화 [9], [11])

3. **GEN2 성능 측정 Phase 1 전략**: 라벨링 생산성·난이도·효율성에 대한 GEN2 Feature의 영향을 **변동성을 그대로 반영하여 실데이터 기반으로 정밀 측정**하는 것이 Phase 1의 핵심 목적이다. 측정 결과는 전략/컨셉 수정의 입력값으로 사용된다. (대화 [10])

4. **Policy 문서 내 클래스 어노테이션 규칙 작성 원칙**: 챕터명은 Geometry, Temporal Area, Limitation 등 기존 챕터와 구조적 충돌이 없어야 하며, 정확성·일관성·확장성을 기준으로 명명한다. Occlusion/Truncation/Visibility는 Base Rule 신규 챕터로 분리 추가하는 것이 권장된다. (대화 [30], [28])

5. **Feature Policy 버전 변환 규칙 (Gen1→Gen2 네이밍)**: 변환 패턴은 `MV_{Feature}_v{X.X}` → `MV_{Feature}_3D_BoundBox_v{X.X.0}` 형식이다. 예: `MV_OD_v1.7` → `MV_OD_3D_BoundBox_v1.7.0`, `MV_RMD_v1.2` → `MV_RMD_3D_BoundBox_v1.2.0`. (대화 [27])

6. **Labeling Analytics 파이프라인 구조**: 1단계(Labeling Log Upload): Labelit Publisher(labelit 담당) + DataLakeHouse Receiver(NOVA 담당-수진), 2단계 이후는 별도 구현 범위로 분리된다. 역할별 담당자 구분이 명확히 정의되어 있다. (대화 [1])

---

## 반복 등장 패턴

- **Gen1↔Gen2 비교 필요성**: 작업 공수, ODD 스펙, 정책 버전 등 다양한 축에서 Gen1과 Gen2를 비교하는 요청이 반복된다. 비교 문서 작성 및 전환 근거 마련이 지속적인 작업 흐름이다.
- **Policy/Guideline 문서 설계**: 클래스 정의(Barrier, Obstacle, Pole, Animal 등), 속성(Attribute) 명명, 챕터 순서·제목 결정 등 라벨링 정책 문서를 체계화하는 작업이 대화 전반에 걸쳐 반복된다.
- **영어 기술 용어 확정**: 도메인 특화 객체(교량 난간, 주차금지봉, 배리어 등)의 영어 공식 명칭을 확정하는 요청이 다수 등장한다. 정책
