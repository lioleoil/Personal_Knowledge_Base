# SV Domain Agent — Role Rules (sv_dqat + sv_lakehouse 공용)

`agent_type: sv_dqat` | `agent_type: sv_lakehouse`

## 목적
StradVision 데이터 품질 검증(DQAT)과 데이터 파이프라인(Lakehouse) 운영.  
두 sub-domain은 별도 embedded git repo로 관리됨.

---

## 도메인 분리

| Domain | agent_type | 경로 | 주요 책임 |
|---|---|---|---|
| SV DQAT | `sv_dqat` | `projects/sv_dqat/` | 데이터 품질 검증, DQ 리포트 생성 |
| SV Lakehouse | `sv_lakehouse` | `projects/sv_lakehouse/` | 데이터 파이프라인, 적재 프로세스 |

---

## 권한
- Read / Write / Edit / Bash: 각자의 `projects/sv_dqat/` 또는 `projects/sv_lakehouse/`
- **교차 접근 금지**: sv_dqat ↔ sv_lakehouse 상호 파일 접근 불가
- 다른 도메인(nova_*, pkb_worklog) 접근 금지

## 제약
- **embedded git 주의**: 각 디렉터리는 독립 git repo. 루트 워크스페이스 git에 영향 주지 않도록 `git` 명령 사용 시 `--work-tree` 명시
- 하드코딩된 경로 `C:/Users/Seonghwan.PARK/` 감지 시 즉시 플래그 (수정 전 사용자 확인 필요)
- DB 스키마 변경, 데이터 삭제 작업 금지
- 리포트 파일 덮어쓰기 금지 → 날짜 suffix 사용

---

## sv_dqat 작업 순서

```
1. manifest의 instructions에서 검증 대상 파악
2. DQ 검증 스크립트 실행
3. 리포트 생성 → projects/sv_dqat/reports/DQ_report_YYYY-MM-DD.md
4. result.json 작성
```

## sv_lakehouse 작업 순서

```
1. manifest의 instructions에서 파이프라인 대상 파악
2. 파이프라인 실행 또는 상태 확인
3. 결과 요약 저장
4. result.json 작성
```

---

## Result 작성 기준 (sv_dqat 예시)

```json
{
  "domain": "sv_dqat",
  "status": "success",
  "outputs": [
    {
      "type":    "dq_report",
      "path":    "projects/sv_dqat/reports/DQ_report_2026-04-11.md",
      "summary": "데이터셋 3개 검증 완료. 이슈 0건."
    }
  ],
  "metadata": {"datasets_checked": 3, "issues_found": 0}
}
```

---

## 도메인 특화 검증 체크리스트 (Validation Agent 참고)

- 리포트 파일이 `reports/` 디렉터리에 존재하는가
- 파일명에 날짜 suffix가 포함되는가
- 하드코딩된 구 경로(`Seonghwan.PARK`) 없는가
- embedded git 상태가 정상인가 (`git -C projects/sv_dqat status` 오류 없음)
