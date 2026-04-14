# Python_Scripts 지식 합성

> 마지막 갱신: 2026-04-14 19:52 | 기반 항목 수: 30

---

# Python_Scripts 위키 합성 문서

---

## 핵심 지식

1. **bash 환경에서 PowerShell 가상환경 활성화 스크립트는 직접 실행 불가**
   - `& .venv\Scripts\Activate.ps1`은 PowerShell 전용이므로 bash에서는 `source .venv/Scripts/activate` 또는 `.venv/Scripts/activate` 사용
   - sv_lakehouse 프로젝트 기준 경로: `c:\Users\psh93\OneDrive\Desktop\Workspace\projects\sv_lakehouse\.venv\Scripts\`
   - 반복적으로 동일 오류 발생 (2026-04-05 ~ 2026-04-13 최소 5회)

2. **Python 환경 설정 미비로 인한 도구 실패 패턴**
   - Windows에서 `python --version` 실행 시 Microsoft Store 리디렉션 발생 → App execution aliases 비활성화 필요
   - dbt VS Code 확장이 Python 3 인터프리터를 찾지 못하는 경우 → 인터프리터 경로 명시적 지정 필요
   - GitHub Enterprise 리포 클론 후 일부 파일 소실 → 원격 main 브랜치에 삭제 커밋이 이미 반영된 상태가 원인

3. **Windows GUI 툴(.exe) Excel export 오류의 주요 원인**
   - PyInstaller 패키징 시 `openpyxl`, `xlsxwriter` 등 라이브러리가 번들에 포함되지 않는 경우 발생
   - `.exe` 실행 경로 권한 문제 또는 파일 잠금(Lock) 상태도 원인이 될 수 있음
   - 해결 방향: spec 파일에 hidden imports 명시 또는 `--collect-all` 옵션 사용

4. **SQL 쿼리 패턴 — 반복 사용된 구문**
   - `DISTINCT`: 단일/복수 컬럼 중복 제거, `COUNT(DISTINCT col)` 집계 패턴
   - `LIKE '%keyword%'` 다중 조건: `WHERE col LIKE '%A%' OR col LIKE '%B%'` → `GROUP BY`와 조합
   - `SUM(CASE WHEN ... THEN ... ELSE 0 END)` 조건부 집계 패턴 반복 등장
   - 대상 테이블: `staging.base_labelit__dataset`, `marts.odd`

5. **변환 스크립트 설계 원칙 (Feature Policy 버전 변환)**
   - 변환 규칙을 먼저 테이블 형태로 정의한 뒤 Python/SQL/JSON 중 하나로 구현하는 순서가 효율적
   - 규칙 세트를 분리 관리하면 동일 로직을 여러 언어로 재사용 가능

6. **에이전트 태스크 보고서 위치 규칙**
   - `.agents/bus/{task_id}_report.json` 경로에 저장됨
   - task ID `9dea7c73` 기준: "Waza 도입 및 활용 전략 리포트" (완료: 2026-04-14 00:33)

---

## 반복 등장 패턴

- **bash vs PowerShell 혼용 오류**: sv_lakehouse 프로젝트 작업 시 셸 환경 착오로 인한 `Activate.ps1` 실행 시도가 2026-04-05부터 2026-04-13까지 최소 5개 대화에서 반복됨 → 작업 환경을 bash로 고정하거나 alias 설정 필요
- **디버깅 요청 패턴**: 오류 로그를 붙여넣고 원인 분석 요청 → "겉으로 터진 오류(JSON 직렬화 실패)"와 "진짜 원인(DB 커넥션 고갈)" 구분이 핵심
- **쿼리 수정/
