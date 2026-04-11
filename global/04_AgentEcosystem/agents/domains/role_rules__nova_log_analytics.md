# Nova Log Analytics Domain Agent — Role Rules

`agent_type: nova_log_analytics`

## 목적
로그 파이프라인 분석, 이상탐지(Anomaly Detection), SQL 파이프라인 실행.

---

## 담당 파일

| 경로 | 용도 |
|---|---|
| `projects/nova_log_analytics/` | 이상탐지·SQL 파이프라인 소스 |
| `projects/nova_log_analytics/config.yaml` | 파이프라인 설정 (DB 연결 포함) |
| `projects/nova_log_analytics/output/` | 분석 결과 출력 디렉터리 |

---

## 권한
- Read / Write / Edit / Bash: `projects/nova_log_analytics/` 하위
- Write: `projects/nova_log_analytics/output/`
- Read: `global/04_AgentEcosystem/agents/domains/role_rules__nova_log_analytics.md`

## 제약
- 다른 도메인 디렉터리 접근 금지
- DB 스키마 변경 금지 (SELECT/분석 쿼리만)
- 결과 파일 덮어쓰기 금지 → 날짜 suffix 사용 (`report_YYYY-MM-DD.md`)

---

## 이상탐지 파이프라인 실행 순서

```
1. config.yaml 읽기 (DB 연결, feature 목록, 임계값)
2. SQL 쿼리 실행 → raw data 수집
3. 이상탐지 알고리즘 실행
4. 결과 요약 → output/report_YYYY-MM-DD.md 저장
5. result.json 작성
```

---

## feature 값 목록 (하드코딩 금지 — config.yaml 기준)

config.yaml의 `features` 섹션을 읽어 동적으로 처리. README에 명시된 값과 다를 수 있으므로 반드시 파일 기준.

---

## Result 작성 기준

```json
{
  "domain": "nova_log_analytics",
  "status": "success",
  "outputs": [
    {
      "type":    "anomaly_report",
      "path":    "projects/nova_log_analytics/output/report_2026-04-11.md",
      "summary": "이상치 3건 감지 (HIGH×1, MEDIUM×2)"
    },
    {
      "type":    "sql_result",
      "path":    "projects/nova_log_analytics/output/sql_2026-04-11.json",
      "summary": "1500행 처리"
    }
  ],
  "metadata": {"rows_processed": 1500, "anomalies_found": 3}
}
```

---

## 도메인 특화 검증 체크리스트 (Validation Agent 참고)

- output 파일이 `output/` 디렉터리에 존재하는가
- 파일명에 날짜 suffix가 포함되는가
- `metadata.rows_processed` > 0 인가
- anomaly_report에 심각도(HIGH/MEDIUM/LOW) 분류가 있는가
