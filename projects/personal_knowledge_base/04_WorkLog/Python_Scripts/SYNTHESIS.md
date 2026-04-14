# Python_Scripts 지식 합성

> 마지막 갱신: 2026-04-14 19:39 | 기반 항목 수: 30

---

# Python_Scripts 위키 합성 문서

## 핵심 지식

1. **bash 환경에서 `.venv` 활성화는 `activate` 스크립트를 직접 사용해야 한다**
   - `& Activate.ps1`은 PowerShell 전용 문법이므로 bash에서 실행 불가
   - bash에서는 `source .venv/Scripts/activate` 또는 `.venv/Scripts/activate` 사용
   - Windows + bash(Git Bash 등) 혼용 환경에서 반복적으로 발생하는 문제

2. **프로젝트 경로: `sv_lakehouse`가 주요 작업 대상 프로젝트다**
   - 경로: `c:\Users\psh93\OneDrive\Desktop\Workspace\projects\sv_lakehouse\`
   - `.venv` 가상환경이 프로젝트 내부에 위치

3. **에이전트 task 보고서는 `.agents/bus/{task_id}_report.json` 경로에 저장된다**
   - 예시: task ID `9dea7c73` → `.agents/bus/9dea7c73_report.json`
   - 완료 시간 및 task 이름이 보고서에 포함됨 (예: "Waza 도입 및 활용 전략 리포트", 2026-04-14 00:33 완료)

4. **Claude Code의 클라우드 예약 기능으로 로컬 컴퓨터 오프라인 상태에서도 자동화 작업 실행 가능**
   - `code.claude.com`에서 웹 기반 작업 예약 실행 지원
   - 반복 업무 자동화에 활용 가능한 패턴으로 확인됨

---

## 반복 등장 패턴

- **`Activate.ps1` 오류 반복 (대화 [1]~[5], [10], [12], [13], [15], [17], [19]~[29])**: 동일한 PowerShell 활성화 스크립트 오류가 수십 회 반복 등장 → 환경 설정이 아직 자동화되지 않았거나, 매번 새 세션에서 수동으로 환경을 활성화하고 있음을 시사
- **로컬 명령어 실행 caveat 메시지 반복 (대화 [7]~[9], [11], [14], [16], [18])**: Claude가 로컬 커맨드 실행 결과를 수신할 때 응답하지 말아야 한다는 caveat가 반복 → 자동화 파이프라인에서 Claude에게 불필요한 메시지가 전달되는 구조적 문제
- **동일 파일(`.jsonl`)에서 중복 추출된 항목 다수**: `75bf4607`, `14a4ea62`, `8102ce54` 등 동일 파일에서 같은 내용이 여러 번 추출됨 → 요약 파이프라인의 중복 제거 로직 부재

---

## 미해결 질문

- **bash + Windows 환경에서 `.venv` 활성화를 세션 시작 시 자동화하는 방법은?** (`.bashrc` 또는 `direnv` 활용 여부 미확인)
- **로컬 명령어 실행 caveat가 Claude에게 전달되는 근본 원인은?** 파이프라인 어느 단계에서 필터링해야 하는지 불명확
- **`sv_lakehouse` 프로젝트의 full pipeline이 정확히 어떤 단계로 구성되어 있는지** 상세 구조가 이 로그에서는 파악 불가
- **대화 로그 요약 시 동일 파일 내 중복 항목을 어떻게 dedup할 것인가?** 현재 30개 중 실질적으로 고유한 대화는 5~6개 수준

---

## 관련 카테고리

- `sv_lakehouse`
