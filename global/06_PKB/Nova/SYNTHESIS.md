# Nova 지식 합성

> 마지막 갱신: 2026-04-22 07:55 | 기반 항목 수: 30

---

# Nova 위키 합성 문서

## 핵심 지식

1. **venv 활성화는 bash에서 `source .venv/Scripts/activate`로 실행해야 한다**
   - `& .venv\Scripts\Activate.ps1`은 PowerShell 전용이므로 bash 환경(Git Bash, WSL 등)에서는 동작하지 않음
   - 올바른 명령: `source /c/Users/psh93/OneDrive/Desktop/Workspace/projects/sv_lakehouse/.venv/Scripts/activate`
   - 이 문제가 2026-04-04 ~ 2026-04-13 사이에 6회 이상 반복 발생함

2. **nova_helper Slack 봇의 SLACK_BOT_TOKEN은 `nova_helper/.env`에서 로드된다**
   - orchestrator가 해당 `.env`를 자동 로드하므로 파이프라인 실행 시 별도 토큰 주입 불필요
   - 파이프라인 테스트 시 dry-run → Slack 알림 순서로 검증 (2026-04-14)

3. **데일리 스크랩 자동 트리거(매일 오전 9시)는 명시적으로 등록해야 작동한다**
   - 지시만으로는 설정되지 않으며, 실제 트리거 등록 작업이 별도로 필요함
   - 2026-04-08 기준 마지막 실행은 2026-04-04로, 4일간 공백 발생한 사례 있음

4. **Nova의 아키텍처는 Databricks 플랫폼 기반으로 전환 중이며, Beta 출범 후 사내 프로모션 예정이다**
   - 전환 완료 후 통합 서비스로서 "Nova Beta Launch" 티켓으로 관리 (2026-03-06)
   - 개발 프로세스는 Dev/Ops 역할 분리, Lakehouse + Analytics Service 구조로 정합성 확인됨 (2025-12-30)

5. **Nova Lakehouse의 역할 분리: Data Engineer(인프라/파이프라인) vs Analytics Engineer(데이터 가공·변환·모델링)**
   - Analytics Engineer를 단순 분석가로 정의하면 역할 범위가 맞지 않음
   - dbt intermediate 모델이 스테이징 데이터 가공 레이어로 활용됨 (2026-01-03, 2026-02-05)

6. **Nova 대시보드는 주행 데이터(CAN), GT(Ground Truth), ODD 데이터를 차량 모델·국가별로 세분화하여 제공한다**
   - 알고리즘 개발자 채널 공개 기준: Parking GT 조회 가능, ODD는 샘플 수준 (2026-01-05)
   - 대시보드 명칭은 "Mileage"보다 운행 행태 전반을 포괄하는 "Driving Statistics" 계열 권장

---

## 반복 등장 패턴

- **bash vs PowerShell 환경 혼용 오류**: `.ps1` 스크립트를 bash에서 실행 시도하는 문제가 `sv_lakehouse` 프로젝트에서 집중적으로 반복 (최소 6회, 2026-04-04 ~ 04-13)
- **자동화 트리거 미등록 문제**: 구두 지시 후 실제 cron/스케줄러 등록이 누락되는 패턴 (데일리 스크랩 사례)
- **영어 네이밍 요청 반복**: 대시보드명, 티켓명, 연혁, DB 설계 등 산출물 명칭을 영어로 표현하는 요청이 다수 (2025-12 ~ 2026-02)
- **Multi-Agent / PKB 파이프라인 설계 진행**: nova_helper, sv_lakehouse, orchestrator 간 연동 구조를 지속적으로 설계·테스트 중

---

## 미해결 질문

- **데일리 스크랩 트리거가 실제로 정상 등록되어 안정적으로 실행되고 있는지 확인 필요** (2026-04-08 이후 후속 확인 로그 없음)
- **bash 환경에서 venv 활성화 문제가 근본적으로 해결되었는지 불명확** — 반복 발생 중이므로 `.bashrc` 또는 작업 가이드 고정화 필요
- **Nova Beta Launch 이후 사내 프로모션 실제 진행 여부 및 결과** 미확인 (2026-03-06 티켓 이후 후속 로그 없음)
- **Multi-Agent Ecosystem 설계 플랜의 실제 구현 진행 상태** 불명확 (2026-04-11 승인 이후 세부 구현 로그 부재)

---

## 관련 카테고리

- **sv_lakehouse**: Nova Lakehouse 파이프라인, dbt 모델, venv 환경 설정
- **nova_helper**: Slack 봇, orchestrator 연동, PKB 파이프라인 자동화
- **데이터 엔지니어링**: dbt intermediate 모델, CAN 데이터 처리, 데이터 라이프사이클
- **배포 운영(DevOps)**: 트리거 스케줄링, Databricks 전환, 파이프라인 테스트 및 알림
- **사내 커뮤니케이션**: 대시보드 공개 안내, 채널 공지 작성, 영어 명칭 정의
