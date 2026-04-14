# Gen1_Gen2_Labeling 지식 합성

> 마지막 갱신: 2026-04-14 19:37 | 기반 항목 수: 30

---

# Gen1_Gen2_Labeling 위키 합성 문서

## 핵심 지식

1. **Gen1(Frame-base MV OD) vs Gen2(Map-base Sequential OD) 비교 측정 방법론**
   - 작업 결과물(Output) 수량 기준 직접 비교는 구조적으로 무리가 있음
   - 권장 비교 축: **동일 금액 대비 산출물(Cost per Output)** 또는 **단위 시간당 처리량(Throughput per Hour)**
   - Gen2 Sequential OD는 Map-base이므로 Frame-base Gen1과 작업 단위 자체가 다름 → 공수 비교 시 환산 기준 명시 필수

2. **Gen2 ODD v2.7.0 → 신규 포맷 전환의 필요성 근거**
   - 전환 불가결성 문서화 방향: 두 정책의 스펙을 테이블 형태로 비교하여 데이터 선별·관리·Cost Control 목표 달성 불가 지점을 명시
   - MVGen2 OD 시나리오 요구사항과 v2.7.0 ODD 구조의 충족 여부는 Excel 기반 클래스 매핑으로 검증함

3. **GEN2 Phase 1 성능 측정 전략 핵심 원칙**
   - 목적: GEN2 Feature가 라벨링 생산성·난이도·효율성에 미치는 영향을 정밀 측정
   - 변동성을 통제하지 않고 실제 데이터를 있는 그대로 수집하는 방식(측정 단계에서 보정 없음)
   - Map-base Feature와 Frame-base Feature의 작업 공수 차이는 **동일 비용 대비 결과물** 기준이 더 유효한 비교 방법

4. **Labeling Analytics 2단계 파이프라인 구조**
   - 1단계: Labelit Publisher(라벨링 툴 담당) → DataLakeHouse Receiver(NOVA 담당, 수진) 구현
   - 2단계: 이후 단계로 연결되는 분석 구조 (MDPG Confluence 문서 기준)
   - 관련 Jira/Confluence 연동 포함된 구조로 설계됨

5. **클래스 정의 문서 작성 규칙 (OD/RMD/3DP 공통)**
   - 챕터 명칭은 정확성·일관성·확장성을 기준으로 선택: `Class-Specific Annotation Rules` 또는 `Per-Class Annotation Specification` 권장
   - Geometry, Temporal Area, Limitation 챕터와 구조적 충돌 없이 설계해야 함
   - Occlusion / Truncation / Visibility 표현 규정은 Base Rule 신규 챕터로 분리하여 추가하는 것이 적합

6. **Policy 버전 명칭 변환 규칙 (Feature별)**
   - OD: `MV_OD_v1.7` → `MV_OD_3D_BoundBox_v1.7.0`
   - SOD: `MV_SOD_v1.6` → `MV_SOD_3D_BoundBox_v1.6.0`
   - TSTLD: `MV_TSTLD_v1.3` → `MV_TSTLD_3D_BoundBox_v1.3.0`
   - RMD: `MV_RMD_v1.2` → `MV_RMD_3D_BoundBox_v1.2.0`
   - 패턴: Feature명 + `3D_BoundBox` + 기존 버전 + `.0` 추가

---

## 반복 등장 패턴

- **클래스 분류 및 정의 작업 반복**: Barrier, Obstacle, Pole, Animal, Vehicle 등 개별 클래스에 대해 Hierarchy 기반 조항 작성이 지속적으로 이루어짐 →
