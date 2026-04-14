# Nova 지식 합성

> 마지막 갱신: 2026-04-14 19:51 | 기반 항목 수: 30

---

# Nova 주제 위키 합성 문서

## 핵심 지식

1. **sv_lakehouse 프로젝트 venv 활성화는 bash 셸 기준으로 해야 한다**
   PowerShell 활성화 스크립트(`.ps1`)는 bash 환경에서 동작하지 않음. Windows Git Bash 또는 WSL 환경에서는 반드시 `source /c/Users/psh93/.../activate` 방식으로 실행해야 하며, `& ...Activate.ps1` 형식은 사용 불가. 이 문제가 2026-04-04 ~ 2026-04-13 사이에 10회 이상 반복됨 → **환경 설정을 한 번 고정해두지 않으면 계속 재발하는 구조적 문제**

2. **Nova는 Lakehouse + Dashboard로 구성된 통합 사내 데이터 서비스다**
   - Lakehouse: 데이터 수집·스테이징·변환 파이프라인 담당 (dbt intermediate 모델 포함)
   - Dashboard: GT 조회, ODD 샘플, 주행통계(누적 주행거리·시간·차량별·국가별) 등 분석 서비스 제공
   - 2026-03-06 기준으로 Databricks 플랫폼 기반 전환 후 Nova Beta Launch를 준비 중

3. **Nova의 R&R은 Data Engineer / Analytics Engineer로 이원화되어 있다**
   - Data Engineer: Lakehouse 아키텍처·인프라 설계, 스테이징 파이프라인 구축 (담당: sujin.lim)
   - Analytics Engineer: 스테이징된 데이터 가공·변환 및 분석 서비스 제공
   - 두 역할의 범위가 실무에서 혼동되는 경향이 있어 명확한 경계 정의가 필요하다고 검토됨 (2026-02-05)

4. **Nova 서비스 개발 프로세스는 Dev / Ops 역할 분리 + Lakehouse 정합 구조로 설계되어 있다**
   - 사용자 요구사항 수집(Ops) → 분석(Dev & Ops) → 개발 → 배포의 순환 플로우
   - Nova Help Center가 요구사항 수집 채널 역할
   - 전체 구조는 Lakehouse + Analytics Service 관점에서 정합적으로 평가됨 (2025-12-30)

5. **dbt intermediate 모델을 활용한 데이터 정제 레이어가 존재한다**
   - 예: `int_labelit__invalid_dataset` — Labelit에서 %Delete%, %Workload%, %Test% 포함 데이터셋을 필터링하는 모델
   - Lakehouse 내 중간 변환 레이어로 사용되며, 최종 mart 모델에 공급되는 구조

6. **데일리 스크랩 자동화 트리거가 설정되지 않은 상태로 운영된 이력이 있다**
   - 2026-04-08 기준, 마지막 스크랩은 2026-04-04 실행 / 그 이후 트리거 미등록 상태
   - "매일 오전 9시 실행" 지시가 있었으나 실제 트리거는 등록되지 않았음 → **자동화 설정 후 등록 여부를 반드시 검증해야 함**

---

## 반복 등장 패턴

- **venv 활성화 오류 반복 (10회+):** `Activate.ps1`을 bash에서 실행 시도하는 문제가 2026-04-04부터 2026-04-13까지 거의 매일 재발. 근본 원인은 셸 환경 고정 미비
- **대시보드·서비스 명칭을 영어로 표현하는 작업 반복:** "전사 데이터 대시보드", "주행
