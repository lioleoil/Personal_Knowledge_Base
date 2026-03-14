# 역량 맵 — Data-Driven Strategy Architect

> 기반: GPT 689개 대화 실제 작업 이력 + 정체성 분석 (Nova 29, OpenLABEL 45, ODD 16, DQA 13, Gen1/Gen2 Labeling 95, Strategy/Business 164, Python Scripts 272개 대화)
> 생성일: 2026-03-14

---

## 핵심 정체성

### 자기완결적 본질주의자 / Data-Driven Strategy Architect

> "나는 자기완결적 본질주의자다. 겉이 아니라 본질을 보고, 판단·행동·감정의 기원이 스스로에게 있다. 사람과 세상을 전체로 받아들여 빠르게 구조화하고, 투명함·일관성·깊이를 기준으로 관계를 선택한다."

**Data-Driven Strategy Architect**는 단순 데이터 분석가도, 단순 기획자도 아니다. 데이터·표준·시스템 아키텍처·비즈니스 전략을 하나의 통합 프레임워크로 연결하는 사람이다. 분석 결과를 조직의 방향성으로 전환하고, 프로세스를 구조로 재설계하며, 정책을 실행 가능한 모델로 변환한다.

**인지 구조적 특징:**
- 게슈탈트 기반 고감도 인지: 전체를 먼저 보고 구조를 파악한 뒤 필요한 부분을 선택 (순차적 처리가 아닌 동시적 처리)
- 전체 다운로드형 사고: 정보 인식 → 분해/그룹화/우선순위 → 결론 생성이 병렬로 작동
- "조각의 사람이 아니라, 구조의 사람이다"

---

## 역량 레이어 구조

### Layer 1: 기술 역량 (Technical)

#### 1-1. 데이터 스택

| 도구/기술 | 실제 사용 증거 |
|-----------|---------------|
| MySQL | d2t.npsd_raw 테이블 설계, 라벨링 데이터 DB 구축 (2023~2024) |
| PostgreSQL | Nova Lakehouse 데이터 아키텍처 설계 및 쿼리 작성 |
| MongoDB | taskId 조회 쿼리, LabelIt API 연동, MongoDB Compass 활용 (2025) |
| BigQuery | 데이터 분석 파이프라인 설계 검토 |
| Databricks | Nova 아키텍처를 Databricks 플랫폼 기반으로 전환하는 작업 직접 수행 (2026-03) |
| dbt | sv-lakehouse/dbt 토이프로젝트 진행, int_labelit__invalid_dataset 모델 설계 및 활용 (2025-12 ~ 2026-01) |
| Airflow | ETL 파이프라인 설계 검토, DAG 개념 학습 및 적용 |
| Power BI | Python 스크립트 연동, MySQL 연결 오류 해결, 시트 인식 수정 (2024-04 ~ 2025-04) |

#### 1-2. 언어 및 스크립트

| 언어 | 실제 작업 이력 |
|------|----------------|
| Python | JSON/XML 파싱 스크립트 다수 (2023~2026), API 연동 (LabelIt REST API), 병렬 처리 (멀티스레딩), tqdm 진행바, UTF-8/CP949 인코딩 처리, 객체 카운팅/통계 처리, 파일 자동화 |
| SQL | MySQL JOIN 쿼리, MongoDB 쿼리, DAX 수식 (Power BI), DISTINCT/GROUP BY 비교 분석 |
| Google Apps Script | 스프레드시트 자동화 스크립트 작업 |
| JavaScript/TypeScript | FSD 포맷 처리 스크립트 (타입 정의 포함) |

#### 1-3. 개발·운영 환경

- **OS**: Windows + WSL(Ubuntu) 혼용 환경에서 실무 스크립트 운영
- **협업 도구**: Git, VS Code, Jira, Confluence 실무 활용
- **스토리지**: Qumulo 네트워크 드라이브 마운트·파일 처리, SharePoint
- **DB 클라이언트**: MongoDB Compass, pgAdmin, MySQL Workbench

#### 1-4. 데이터 아키텍처 설계

- OLAP/OLTP 구조 이해 및 설계 적용
- 데이터 레이크하우스(Lakehouse) 아키텍처 설계 (Nova DataCenter)
- ETL 파이프라인 설계: Staging → Transform → Visualization 흐름 정의
- dbt intermediate 모델 설계: downstream exclusion 기준 테이블 구조화

---

### Layer 2: 도메인 역량 (Domain)

#### 2-1. 자율주행 어노테이션

| 도메인 | 실제 작업 이력 |
|--------|----------------|
| Gen1/Gen2 OD | Object Detection 라벨링 성능 측정, 3DP/LDRBD/RMD 포맷 통합 분석 (2024~2026) |
| 2D/3D Bounding Box | bbox3d_valid / bbox2d_valid 조건 기반 카운팅 로직 설계, Cuboid 값(x,y,z + roll, pitch, yaw + size) 해석 |
| Lane 데이터 | ref_uuid 조합 처리, 차선 비교·분류 로직 개발, top_y/bottom_y 좌표 추출 |
| Parking ODD | MV Parking ODD Dashboard 신규 공개 (2025-12) |
| 퍼셉션 윈도우 어노테이션 | 퍼셉션 윈도우 기반 어노테이션 정책 정의 및 클래스별 규칙 수립 |
| 어노테이션 Policy | Jira 티켓 기반 GEN2 Policy 작성, 클래스별 어노테이션 규칙 정의 (Bollard, Barrier, Wheel stopper 등 도로 객체 영어 명칭 정리) |

#### 2-2. ASAM OpenX 표준

| 표준 | 작업 내용 |
|------|-----------|
| ASAM OpenLABEL | SV 포맷(XML/JSON)에서 OpenLABEL JSON 스키마로 마이그레이션 전략 수립 및 실행 (2025-07 ~ 2026-03, 45개 대화) |
| ASAM OpenODD | OpenODD 구조 분석, XML → YAML 변환 전략, ODD 정보가 메타데이터임을 논리적으로 규명 |
| ASAM OpenSCENARIO | v1.x(XML) vs v2.0(DSL) 구조 비교, OpenDRIVE 참조 방식 분석 |
| ASAM OpenDRIVE | .xodr 포맷(XML 기반) 분석, 3D Annotation JSON → xodr 변환 전략 설계 |
| OpenX 통합 전략 | OpenODD + OpenDRIVE + OpenSCENARIO + OpenLABEL 전체 연계 아키텍처 설계 및 리포트 작성 |

실제 수행 작업:
- SV Feature-based annotation policy와 ASAM OpenLABEL 간 차이점 분석 리포트 작성
- 좌표계 변환(쿼터니언 + 번역 벡터), 센서 정합, GPS 저주기 센서 정렬 분석
- SV → OpenLABEL 변환 스크립트 시뮬레이션 및 완성도 검증

#### 2-3. 데이터 플랫폼 서비스 (Nova)

Nova는 단순 대시보드가 아닌 **사내 데이터 센터 서비스**로 직접 기획·릴리즈 관리한 서비스:

- **Nova Lakehouse**: Staging → Validation → Transformation → Publication 파이프라인 설계
- **Nova Dashboard**: ODD Labeling Statistics Dashboard, Data Yield Dashboard, MV Parking ODD Dashboard 개발 주도
- **릴리즈 관리**: Swimlane 로드맵 작성 (25Y Q4 ~ 26Y Q2+), Jira 티켓 규칙 매뉴얼 작성
- **플랫폼 전환**: Databricks 기반 Nova 아키텍처 전환 작업 진행 (Nova Beta Launch, 2026-03)
- **공개 전략**: 알고리즘 개발자 채널 대상 Nova 공개 공지 기획 및 작성

---

### Layer 3: 분석·설계 역량 (Analytical & Design)

#### 3-1. 데이터 분석 설계

| 역량 | 실제 작업 이력 |
|------|----------------|
| 통계 분석 | K-means 군집 분석 적용 검토, 정규분포 그래프 생성, 가설 검정(t-test, ANOVA) vs 모델링 비교 판단 |
| 워크로드 측정 | WLS(Workload Labeling System) 설계 및 활용, 1차 워크로드 측정 리포트 작성 (2024-07), FV/MV별 결과 정리 |
| 로그 분석 | 라벨링 툴 로그 데이터 이중 목적(정산/행동분석) 구조 설계, 정산용/행동분석용 분리 ETL 설계 |
| 비용 분석 | MV OD 라벨링 비용 절감 분석, 단가 변경 영향 분석, 계약 단가 비교 보고서 작성 (2025-12) |
| 성능 측정 | Bounding Box Score 계산 방식 분석, Gen2 OD/RMD 라벨링 성능 측정안 수립 (2026) |

#### 3-2. 시스템 설계

- **DB 스키마 설계**: domain/catalog 정의, metric/dimension 개념 설계, 물리 DB 스키마 설계 (Dev/Ops 역할 분리 구조)
- **데이터 모델 설계**: dbt 기반 semantic layer 설계, staging/intermediate/mart 레이어 구분
- **API 설계 검토**: LabelIt REST API (v1/v3), Django Workbench REST API 설계 방향 검토
- **데이터 라이프사이클 설계**: Generate → Ingest → Process → Use → Store → Archive → Delete 흐름 정의

#### 3-3. 프로세스 재설계

- 라벨링 검수 자동화 방안 설계 (2024-11)
- Nova 서비스 개발 프로세스 전체 검토 및 구조 강화 제안 (2025-12)
- 업무 인수인계 전략 개선 (2025-08)
- 시연 리허설 기획안 작성 (2025-11)

---

### Layer 4: 전략·기획 역량 (Strategic)

#### 4-1. KPI/OKR 설계

| 작업 | 실제 내용 |
|------|-----------|
| KPI 분석 아이템 설정 | 라벨링 성과 지표 항목 정의 (2025-04) |
| OKR 전환 | KPI → OKR 체계 전환 작업 (2026-01) |
| KPI Goal 검토 기준 | 목표 설정 기준 체계화 (2026-02) |
| KPI 설정 완성 | 상반기 KPI 목표 확정 및 성과 평가 보고서 작성 (2026-02) |
| 성과 평가 보고서 | 연간 성과 평가 보고서 작성 (2025-01) |

#### 4-2. 비즈니스 전략

- **단가 협상**: 하반기 단가 협상안 수립 (2025-05), 다중 라운드 비용 최적화 협상 진행
- **신규사업 전략**: 계약 단가 정산 효율화 방안 (2025-12), Nova 전략 전환 분석 (2026-02)
- **데이터 거버넌스**: ODD 데이터 거버넌스 전략 수립 (2026-01), 데이터 레이크하우스 정의 및 정책 수립
- **시장 분석**: 크래프톤/빗썸/펄어비스 등 IT 기업 연봉·복지 분석, 삼성전자 지배구조 분석 (2025-05)
- **서비스 로드맵**: Nova 서비스 로드맵 작성 (25Y Q4 ~ 26Y Q2+)

#### 4-3. PM/PO 역량

- **요구사항 정의**: Nova 서비스 요구사항 프로세스 개선 (2025-12), Analytics Engineer R&R 정의 및 재설계 (2026-02)
- **Jira 관리**: Epic/Story/Task 구조 설계, 티켓 명명 규칙 수립 (NOVA 티켓 매뉴얼)
- **릴리즈 관리**: Nova Dashboard 릴리즈 노트 작성, Nova Beta Launch 계획
- **서비스 정책 구조화**: 서비스 정책 체계화 방법론 적용 (2025-11)

---

### Layer 5: 리더십·소통 역량 (Leadership & Communication)

#### 5-1. 협업·평가

| 역량 | 실제 작업 이력 |
|------|----------------|
| 동료 평가 작성 | 협업 평가 사례 구체화 (A/B 근거 + 사례 구조) (2024-01, 2024-07) |
| 피어 평가 | 피어 평가 의견 작성 (2026-01) |
| 조직 개편 대응 | 비밀리에 진행되는 조직 개편에 대한 외부 설득 전략 수립 (2024-01) |
| 직무 재설계 요청 | 회사 핵심가치 5개 기준 직무 재설계 논리 작성 (2024-01) |

#### 5-2. 벤더 관리·협상

- 벤더사 의뢰 업체 포지션에서의 문서 관리 (발주처 자기 지칭 기준 정립)
- 단가 협상 전략 수립 및 다중 라운드 협상 수행
- Acceptance Minute 등 공식 인수 문서 관리
- Hitachi 등 외부 파트너 질문 대응 문서 작성 (2024-12)

#### 5-3. 문서화·커뮤니케이션

- **비즈니스 번역**: 한국어 ↔ 영어 기술·비즈니스 번역 빈번 (164개 Strategy 대화 중 상당수)
- **공지 작성**: Databricks PoC 일정 변경 공지, Nova 대시보드 공개 공지 등 내부 커뮤니케이션
- **보고서 구조화**: OpenX 전환 리포트, 워크로드 측정 리포트, 성과 평가 보고서 등 체계적 문서화
- **기술 용어 정리**: Bollard, Barrier, Wheel stopper, 델리네이터 등 도로 객체 한·영 명칭 체계화

---

## 역량별 증거 (Evidence)

### 기술 역량 증거

**[E-T1] dbt Lakehouse 설계**
- sv-lakehouse/dbt 프로젝트 구성, `int_labelit__invalid_dataset` intermediate 모델 설계
- `%Delete%`, `%Workload%`, `%Test%` 패턴을 `invalid_type` 도메인 값으로 명시화 → downstream exclusion 기준 테이블로 활용

**[E-T2] Python API 자동화**
- LabelIt REST API(v1/v3) 연동 스크립트: login → accessToken → get_task_by_id → get_data_items → get_objects 전체 플로우 구현 (2024-06)
- Qumulo 네트워크 드라이브 마운트 환경에서 대용량 파일 처리 자동화 (2025-02)

**[E-T3] 병렬 처리 스크립트**
- 멀티스레딩 기반 파일 복사 최적화 (2023-09)
- 파일 검색 병렬 처리 스크립트 (2024-11)

### 도메인 역량 증거

**[E-D1] SV → OpenLABEL 마이그레이션**
- SV의 Feature-based annotation policy(JSON)와 ASAM OpenLABEL 스펙 간 차이점 분석 리포트 작성 (2025-07-11)
- 좌표계 변환: 쿼터니언 [x,y,z,w] + 번역 벡터를 OpenLABEL `transform_src_to_dst` 구조로 매핑
- 변환 스크립트 시뮬레이션 → 완성도 평가 수행

**[E-D2] Nova ODD Dashboard 출시**
- MV Parking Scene ODD tagging 분석 대시보드 최초 공개 (v2.7.0, 2025-12)
- Feature × Dataset × Scene 레벨 Drill-down 구조, ODD 커버리지 점검 기능 포함

**[E-D3] OpenX 통합 전략**
- OpenODD(XML→YAML) + OpenDRIVE(JSON→xodr) + OpenSCENARIO(YAML→v2.0 DSL) + OpenLABEL 전체 연계 아키텍처를 리포트로 통합 정리 (2025-07-18)

### 분석·설계 역량 증거

**[E-A1] 워크로드 측정 시스템 설계**
- 1차 워크로드 측정 리포트 작성: Dataset/Participants/Policy Version/Tool Version 항목 체계화 (2024-07)
- WLS(Workload Labeling System) 활용 계획안 수립, 라벨링 로그 이중 목적 분리 설계

**[E-A2] 라벨링 로그 분석 구조 설계**
- 정산용 로그(객체 작업 시간)와 행동 분석용 로그(줌인/아웃 등)를 분리하는 ETL 이중화 방안 설계 (2025-05)
- 3D LiDAR annotation 복잡 데이터에서 통계적 가설 검정 vs 모델링 방식의 효용성 비교 판단 (2025-09)

### 전략·기획 역량 증거

**[E-S1] Nova 서비스 전략 수립**
- Nova 로드맵: 25Y Q4(ODD Stats Dashboard + Infra) → 26Y Q1(Data Yield + Collection KPI + Unstructured Staging) → 26Y Q2+(Query Service + CDC + Usage Analytics) Swimlane 작성 (2025-12)
- Databricks 기반 아키텍처 전환 후 Nova Beta 출범 계획 수립 (2026-03)

**[E-S2] 단가 협상 전략**
- 하반기 단가 협상안 수립 (2025-05), 다중 라운드 최적화 협상 전략 설계
- 비즈니스 파트너사 대응 문서(Hitachi) 작성, 계약 단가 비교 보고서 (2025-12)

**[E-S3] KPI/OKR 체계 전환**
- KPI 분석 아이템 정의 → OKR 전환 → 상반기 KPI 완성 흐름 직접 수행 (2025-04 ~ 2026-02)

### 리더십·소통 역량 증거

**[E-L1] 조직 이슈 대응**
- 비밀리에 진행되는 조직 개편에 대한 외부 설득 전략 수립: 영향 평가 → 증거 수집 → 이해관계자 파악 → 커뮤니케이션 계획 수립 (2024-01)
- 회사 핵심가치 5개(For the Customer, Self Motivation, One Team Mind, Professionalism, Bold Innovation)를 기반으로 직무 재설계 논리 작성 (2024-01)

**[E-L2] 내부 공지·커뮤니케이션**
- Databricks PoC 일정 연기 공지 작성 (책임 소재 명확, 대안 제시 포함)
- 알고리즘 개발자 채널 대상 Nova 공개 공지 기획 (과장 없이 탐색 유도 중심)

---

## 강점 집중 영역 (Top 3)

### 1. 표준 기반 데이터 아키텍처 설계 (ASAM OpenX + Lakehouse)

**밀도:** OpenLABEL(45개) + ODD(16개) + Nova(29개) = 90개 대화
**핵심 증거:** SV → OpenLABEL 마이그레이션 전략 수립 + Nova Lakehouse 설계 + Databricks 전환
**왜 강점인가:** 개별 표준을 아는 것을 넘어, OpenX 전체 연계 구조(OpenODD → OpenDRIVE → OpenSCENARIO → OpenLABEL)를 한 프레임으로 통합해서 실행 전략으로 만들었다. 이는 도메인 지식 + 시스템 설계 역량의 결합이다.

### 2. 데이터 기반 운영 최적화 (Python 스크립트 + 비용 분석 + 워크로드 측정)

**밀도:** Python Scripts(272개) + Gen1/Gen2(95개) = 367개 대화
**핵심 증거:** LabelIt API 자동화 + 워크로드 측정 시스템 설계 + 라벨링 로그 분석 구조 재설계 + MV OD 비용 절감 분석
**왜 강점인가:** 도구를 만드는 것(Python 스크립트)과 그 도구로 측정하는 것(WLS, 비용 분석)을 연결하고, 측정 결과를 조직 의사결정으로 전환하는 전체 루프를 직접 설계했다.

### 3. 서비스 기획·PM/PO 역량 (Nova)

**밀도:** Strategy/Business(164개) + Nova(29개) = 193개 대화
**핵심 증거:** Nova 서비스 로드맵 작성 → 릴리즈 관리 → Analytics Engineer R&R 재정의 → Databricks 기반 Beta 출범
**왜 강점인가:** Nova는 단순 대시보드가 아니라 사내 데이터 플랫폼 서비스다. 요구사항 정의 → Jira 티켓 관리 → 릴리즈 노트 → 공개 전략 → 조직 내 R&R 정의까지 PM/PO 전체 역할을 수행했다.

---

## 커리어 경로와의 연결

**장기 목표: CBO (Chief Business Officer)**
**경로: 데이터 분석가 → 플랫폼 PM/PO → 전략가 → 기획자 → 경영자**

| 현재 역량 | CBO 경로에서의 역할 |
|-----------|---------------------|
| **기술 역량** (dbt/Databricks/Python) | 데이터 기반 의사결정의 기술적 신뢰도 확보. CBO가 데이터팀과 대화할 때 통역 없이 직접 논의 가능. |
| **도메인 역량** (자율주행/OpenX/어노테이션) | 자율주행이라는 특정 산업 내에서 표준·정책·데이터를 모두 이해하는 레어한 포지션. 신규 사업·파트너십 전략 수립 시 핵심 자산. |
| **분석·설계 역량** (Lakehouse/워크로드/비용분석) | 조직의 운영 효율을 정량화하고 구조로 재설계하는 역량. CBO의 핵심 업무인 "수익성 최적화"와 직결. |
| **전략·기획 역량** (KPI/OKR/로드맵/협상) | CBO의 본업. 현재 이미 서비스 단위(Nova)에서 수행 중. 범위를 사업 단위, 회사 단위로 확장하는 과정이 남음. |
| **리더십·소통 역량** (벤더 관리/조직 대응/문서화) | 다양한 이해관계자를 설득하고 조율하는 역량. CBO로 가는 과정에서 이해관계자 범위(내부팀 → 임원 → 이사회 → 외부 파트너)가 확장될 것. |

**현재 포지션 요약:**
- 기술적 실행력과 전략적 사고를 동시에 보유한 "전략-실행 브릿지"
- 어노테이션 도메인의 기술 표준(OpenX)을 이해하는 동시에 사업 단가·KPI·로드맵을 설계하는 역할 수행
- 가장 적합한 중간 경로: **전략 운영 리드 / BI Strategist / 신규사업 전략 셀 Owner**

**다음 단계 역량 강화 방향:**
1. 플랫폼 PM/PO 경험을 Nova에서 더 넓은 서비스로 확장
2. Analytics Engineering 역량을 데이터 전략으로 연결하는 포트폴리오 구축
3. 사업 단위 P&L(손익) 관리 경험 확보
4. 조직 범위를 팀 → 부서 → 사업부 단위로 영향력 확장

---

> **이 문서는 689개의 GPT 대화 실제 작업 이력을 기반으로 작성되었습니다.**
> 추상적 서술이 아니라 "실제로 이런 작업을 했다"는 증거 기반 역량 맵입니다.
> 최종 생성: 2026-03-14 by Claude Sonnet 4.6
