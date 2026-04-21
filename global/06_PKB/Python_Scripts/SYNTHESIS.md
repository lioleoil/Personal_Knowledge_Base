# Python_Scripts 지식 합성

> 마지막 갱신: 2026-04-22 07:57 | 기반 항목 수: 30

---

# Python_Scripts 위키 합성 문서

## 핵심 지식

1. **Windows PowerShell 가상환경 활성화 스크립트는 bash에서 직접 실행 불가**
   - `& .venv\Scripts\Activate.ps1`은 PowerShell 전용 → bash에서는 `source .venv/Scripts/activate` 또는 `.venv/Scripts/activate` 사용
   - sv_lakehouse 프로젝트에서 반복적으로 동일 실수 발생 (로그 2, 5, 6, 8, 13)

2. **Python 인터프리터 미설치/미연결 시 dbt, VS Code 확장이 정상 작동하지 않음**
   - `python --version` 실행 시 Microsoft Store 리다이렉트 발생 → Python을 공식 설치하거나 PATH 수동 등록 필요
   - dbt Power User 확장은 Python 3 인터프리터가 명시적으로 선택되어 있어야 작동

3. **SQL 쿼리 패턴: DISTINCT, GROUP BY, LIKE 조건의 혼용 규칙**
   - `DISTINCT`는 단일/다중 컬럼 중복 제거에 사용, `GROUP BY`와 함께 쓸 경우 집계 대상 컬럼 명확히 지정 필요
   - `LIKE '%keyword%'` 다중 조건은 `OR`로 연결, `COUNT` 집계 시 그루핑 기준 컬럼과 집계 컬럼 분리
   - 실제 오류 케이스: `WHERE name LIKE '%Delete%' OR name LIKE '%Workload%'` + `GROUP BY` 구성 (로그 21, 27, 30)

4. **GitHub Enterprise 리포지토리를 로컬 Python 환경에서 사용하는 방법**
   - 권장 방식: `git clone https://<GHE_HOST>/<org>/<repo>.git` → 로컬 venv 생성 → 패키지 설치
   - 파일 삭제 원인 추적: 브랜치 클론 후 파일 소실 시, 원격 main에 해당 파일을 지운 커밋이 이미 반영된 상태일 가능성 우선 확인

5. **데이터 변환 스크립트 작성 시 Feature-Policy 버전 매핑 규칙이 선행되어야 함**
   - 변환 규칙(Transformation Rules)을 먼저 문서화한 뒤 Python/SQL/JSON 스크립트로 구현하는 순서가 안정적
   - 타임스탬프 기반 구간 태깅(start/end + tag)은 JSON 포맷 출력으로 표준화 (로그 28, 29)

6. **자동화 스크랩 트리거는 명시적으로 등록해야 하며, 구두 지시만으로는 유지되지 않음**
   - 매일 오전 9시 실행 지시 후에도 등록된 트리거가 없던 사례 확인 (로그 12)
   - 스케줄 등록 후 실제 트리거 존재 여부를 별도로 확인하는 습관 필요

---

## 반복 등장 패턴

- **bash vs PowerShell 환경 혼동**: sv_lakehouse 프로젝트에서 5회 이상 동일한 `Activate.ps1` 실행 오류 반복 → 프로젝트 README에 환경별 활성화 명령어를 고정 문서화 필요
- **Python 환경 미설정 상태에서 도구 실행 시도**: Python 미설치 → dbt 미작동 → GHE clone 시도 순서로 환경 구성 없이 작업 진행하는 패턴
- **SQL 작성 후 오류 수정 요청**: 쿼리를 직접 작성한 뒤 오류 분석을 요청하는 방식이 반복됨 (로그 21, 26, 27, 30) → 쿼리 템플릿 사전 정의로 개선 가능
- **브라우저 자동화 시도 실패**: Claude 브라우저 확장 미설치 상태에서 Chrome 제어 요청 3회 반복 (로그 9, 10, 11)
- **작업 결과 위치 추적 어려움**: 자동화 파이프라인 실행 후 보고서/결과물 위치를 별도로 확인해야 하는 상황 반복 (로그 3, 12)

---

## 미해결 질문

- **bash 환경에서 venv 활성화 후에도 Python 경로가 올바르게 잡히는지 검증하는 표준 절차**가 정해지지 않음
- **매일 오전 9시 데일리 스크랩 트리거**가 현재 실제로 등록되어 있는지, 어느 시스템에서 관리되는지 명확하지 않음
- **Claude 브라우저 확장 프로그램** 설치 완료 여부 및 연결 상태 미확인 (3회 시도 후 결과 불명)
- **sv_lakehouse 프로젝트의 main 브랜치 보호 규칙**(Merge 방지)이 현재도 유지되고 있는지 확인 필요 (로그 18)
- **Apache Superset SQL Templating** 설정을 실제 프로젝트에 적용했는지 결과 미확인 (로그 23)

---

## 관련 카테고리

- **`sv_lakehouse` 프로젝트**: Python 환경 설정, venv 관리, dbt 연동이 집중된 핵심 프로젝트
- **`SQL_Queries`**: DISTINCT, GROUP BY, LIKE 패턴, 쿼리 오류 수정, Superset SQL Templating
- **`Git_Workflow`**: GitHub Enterprise 접근, 브랜치 관리, 파일 삭제 원인 분석, PR merge 방지
- **`Automation_Pipeline`**: 데일리 스크랩 스케줄, task 보고서 추적, Claude Code 예약 실행
- **`Dev_Environment`**: Python 설치, PATH 설정, VS Code 확장, PowerShell vs bash 환경 분리
