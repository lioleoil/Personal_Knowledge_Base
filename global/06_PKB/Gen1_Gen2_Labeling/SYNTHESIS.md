# Gen1_Gen2_Labeling 지식 합성

> 마지막 갱신: 2026-04-22 07:54 | 기반 항목 수: 30

---

# Gen1_Gen2_Labeling 위키 합성 문서

## 핵심 지식

1. **Gen1(Frame-base MV OD) vs Gen2(Map-base Sequential OD) 비교 구조**
   - Gen1은 프레임 단위 독립 작업, Gen2는 시퀀스 기반 맵 연동 작업으로 작업 공수 비교 시 '결과물 수량' 기준이 아닌 **동일 비용 대비 산출물 품질/효율** 기준으로 비교해야 구조적 타당성이 확보됨
   - 비교 지표: 라벨링 생산성, 난이도, 효율성을 Phase 1(Performance Measurement) 단계에서 실측 데이터 기반으로 측정하는 전략 채택

2. **ODD v2.7.0 → Gen2 ODD 전환의 필요성 논거**
   - 전환이 필수불가결한 이유를 문서화할 때 두 정책 스펙을 **테이블 형태로 직접 비교**하는 방식이 핵심 전개 구조
   - 목적: 데이터 선별/관리 효율화, Cost Control 달성을 위한 구조적 한계 명시

3. **Policy 문서 챕터 설계 원칙**
   - 신규 조항 추가 시 기존 챕터(Geometry, Temporal Area, Limitation 등)와 **구조적 충돌 없이** 확장 가능해야 함
   - Occlusion/Truncation/Visibility, Heading Angle, GroundPlane 등 물리적 속성 규정은 **Base Rule 레벨**에서 별도 챕터로 분리하는 것이 표준 구조
   - 클래스별 어노테이션 규칙 챕터명은 정확성·일관성·확장성을 담아야 하며, 정책 문서 관행에 맞는 명칭 선택 필요

4. **Feature 정책 버전 변환 규칙 (Gen1 → Gen2 네이밍)**
   - OD: `MV_OD_v1.7` → `MV_OD_3D_BoundBox_v1.7.0`
   - SOD: `MV_SOD_v1.6` → `MV_SOD_3D_BoundBox_v1.6.0`
   - RMD: `MV_RMD_v1.2` → `MV_RMD_3D_BoundBox_v1.2.0`
   - 패턴: `MV_{Feature}_v{X.Y}` → `MV_{Feature}_3D_BoundBox_v{X.Y.0}`

5. **Labeling Analytics 아키텍처 2단계 구조**
   - 1단계: Labeling Log Upload (Labelit Publisher: labelit 담당 / DataLakeHouse Receiver: NOVA 담당-수진)
   - 참조 문서: MDPG Confluence `spaces/DIC/pages/49080893653`
   - OD/RMD/3DP 클래스별 카운트 및 성능 측정이 최종 목표

6. **도로 객체 분류 및 영어 명칭 표준화**
   - Barrier: 영구적 물리 차단 구조물 (Solid/Fence/Rail 등 4개 클래스)
   - Barricade: 임시·이동 가능한 차단 구조물
   - 교량 난간: `bridge railing` 또는 `parapet` (단순 `rail` 사용 지양)
   - 주차금지봉: `flexible delineator post` 또는 `traffic bollard`
   - Pole 높이 attribute: `short/tall` (위치 기준 `low/high` 사용 지양)

---

## 반복 등장 패턴

- **Gen1 vs Gen2 작업 공수/효율 비교**: 여러 대화([10][20][22])에서 반복적으로 비교 방법론과 측정 기준을 다듬는 과정이 등장 → 단순 수량 비교에서 비용 대비 품질 비교로 전략이 수렴됨
- **Policy 문서 작성/검토 요청**: Barrier([13]), Obstacle([15]), Occlusion/Truncation([28]), 클래스별 어노테이션([30]) 등 라벨링 정책 조항의 신설·검토·표현 수정이 전반적으로 반복됨
- **영어 기술 용어 표현 확인**: 교량 난간([12]), 주차금지봉([24]), 시각 인식 불가 속성([23]), Pole 높이([18]), 문법 검토([16]) 등 라벨링 정책 문서의 영문 표현 정확도를 지속적으로 점검
- **클래스 분류 체계 구조화**: OD/SOD/RMD/LPSD 등 Feature별 클래스 정의와 계층 구조를 반복적으로 정비

---

## 미해결 질문

- **Gen2 OD Performance Measurement Phase 1의 실측 결과**: 측정 전략은 수립되었으나([10]) 실제 측정 결과 데이터 및 분석 결론이 대화 로그 내에 나타나지 않음
- **Labeling Analytics 2단계 이후 구현 범위**: 1단계(Log Upload) 이후 2단계 내용이 로그[1]에서 잘림 → 클래스별 카운트 집계 및 성능 측정 파이프라인의 완성 여부 불명확
- **MVGen2 OD 시나리오 요구사항 충족 여부**: v2.7.0 ODD 기반 검토([11]) 결과가 코드 실행까지만 기록되고 최종 충족/미충족 판정이 확인되지 않음
- **Task Lifecycle 권한 모델 확정안**: 시나리오 검토([2])는 이루어졌으나 최종 확정된 권한 테이블이 로그 내에 명시되지 않음

---

## 관련 카테고리

- **ODD_Policy_Management**: ODD v2.7.0 구조 분석, Gen2 ODD 전환 문서, MVGen2 요구사항 검토
- **Labeling_Tool_Development**: Task Lifecycle 권한 모델, 조회 기능 모듈, Labeling Analytics 아키텍처
- **Annotation_Class_Definition**: Barrier/Obstacle/Pole/Animal 등 클래스 정의 및 조항 작성
- **Gen1_Gen2_Transition**: 버전 변환 규칙, 작업 공수 비교 방법론, 성능 측정 전략
- **Technical_Writing_English**: 라벨링 정책 문서 영문 표현 표준화, 문법 검토
