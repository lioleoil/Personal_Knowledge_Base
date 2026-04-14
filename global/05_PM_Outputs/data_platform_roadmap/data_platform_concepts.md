# 데이터 통합 플랫폼 운영 핵심 개념

> 데이터 통합 플랫폼을 운영할 때 고려해야 할 7가지 영역별 핵심 개념 정리

---

## 1. 데이터 품질 & 신뢰성

- **Data Contract** — 생산자/소비자 간 스키마, SLA, 의미론적 정의를 명문화한 약속
- **Data Quality Rules** — Null 비율, 범위 검증, 유일성 등 측정 가능한 품질 기준
- **Data Observability** — 파이프라인 전체에서 데이터 상태를 실시간 모니터링 (예: Great Expectations, Monte Carlo)
- **SLA/SLO** — 데이터 적시성(freshness), 가용성 목표치 설정

---

## 2. 거버넌스 & 컴플라이언스

- **Data Governance** — 데이터 소유권, 정책, 접근 규칙 수립
- **Data Catalog** — 데이터 자산 탐색 및 메타데이터 관리 (예: Datahub, Atlan)
- **Data Lineage** — 데이터가 어디서 와서 어디로 가는지 추적
- **Access Control / RBAC** — 역할 기반 접근 제어, 컬럼 수준 보안
- **PII / 개인정보 처리** — 마스킹, 익명화, GDPR/개인정보보호법 준수

---

## 3. 아키텍처 & 설계

- **Data Mesh** — 도메인 팀이 데이터를 직접 소유·제공하는 분산 아키텍처
- **Data Product** — 재사용 가능한 단위로 데이터를 패키징
- **Medallion Architecture** — Bronze → Silver → Gold 계층 구조
- **CDC (Change Data Capture)** — 원본 시스템 변경사항을 실시간 전파

---

## 4. 운영 & 신뢰성

- **Idempotency** — 파이프라인 재실행 시 중복 없이 동일 결과 보장
- **Backfill 전략** — 과거 데이터 재처리 방법 정의
- **Dead Letter Queue** — 처리 실패 데이터 격리 및 재처리
- **Circuit Breaker** — 다운스트림 장애 전파 차단

---

## 5. 메타데이터 & 시맨틱

- **Schema Registry** — 스키마 버전 관리 및 호환성 검증 (예: Confluent Schema Registry)
- **Semantic Layer** — 비즈니스 용어와 물리 데이터의 매핑 (예: dbt Metrics, Cube)
- **Data Dictionary** — 필드 정의, 비즈니스 용어 사전

---

## 6. 비용 & 성능

- **Cost Governance** — 쿼리/스토리지 비용 모니터링 및 최적화
- **Partitioning / Clustering 전략** — 쿼리 성능과 비용의 균형
- **Data Tiering** — 접근 빈도에 따른 스토리지 계층 분리 (Hot/Warm/Cold)

---

## 7. 변경 관리

- **Schema Evolution** — 하위 호환 스키마 변경 전략 (Backward/Forward Compatibility)
- **Versioning** — 파이프라인 코드, 데이터셋 버전 관리
- **Impact Analysis** — 변경 시 다운스트림 영향 범위 사전 파악

---

## 핵심 조합 추천

현대적인 데이터 플랫폼에서 가장 먼저 갖춰야 할 핵심 3종 세트:

| 조합 | 역할 |
|------|------|
| **Data Contract** | 데이터 기대값의 기준 정의 |
| **Data Lineage** | 데이터 흐름과 영향 범위 가시화 |
| **Data Observability** | 이상 징후 자동 감지 및 알람 |

> 세 가지가 유기적으로 연결될 때 "무엇이 문제인가 + 왜 생겼는가 + 어디까지 영향을 미치는가"를 한 번에 파악할 수 있다.
