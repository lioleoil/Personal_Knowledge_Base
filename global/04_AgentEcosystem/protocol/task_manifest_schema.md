# Agent Bus — Task Manifest Schema

에이전트 간 통신 프로토콜 명세. 버스 파일은 `.agents/bus/` 에 저장됨.

---

## 버스 파일 유형

| 파일 패턴 | 방향 | 작성 주체 |
|---|---|---|
| `<task_id>_manifest.json` | Execution → Domain | Execution Agent |
| `<task_id>_result.json` | Domain → Execution | Domain Sub-Agent |
| `<task_id>_validation.json` | Bus (검증 결과) | Validation Agent |
| `<task_id>_advice.json` | Bus (솔루션) | Advisor Agent |
| `<task_id>_report.json` | Bus (최종 보고) | Reporter Agent |

---

## Task Manifest (`_manifest.json`)

```json
{
  "task_id":          "abc12345",
  "created_at":       "2026-04-11T09:00:00",
  "parent_agent":     "execution",
  "domain":           "nova_log_analytics",
  "instructions":     "이상탐지 파이프라인 실행 후 결과 요약",
  "context_files":    ["projects/nova_log_analytics/config.yaml"],
  "expected_outputs": ["type:anomaly_report", "type:sql_result"],
  "deadline_hint":    "10min",
  "retry_count":      0,
  "_task_id":         "abc12345",
  "_file_type":       "manifest",
  "_written_at":      "2026-04-11T09:00:00"
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `task_id` | str | 8자리 UUID prefix |
| `domain` | str | 대상 Domain Agent (`nova_log_analytics`, `nova_helper`, `pkb_worklog`, `sv_dqat`, `sv_lakehouse`, `daily_scrap`) |
| `instructions` | str | 자연어 작업 지시 |
| `context_files` | list[str] | 읽어야 할 파일 경로 목록 |
| `expected_outputs` | list[str] | `type:schema` 형식 기대 출력 |
| `deadline_hint` | str | 권장 완료 시간 (참고용) |
| `retry_count` | int | 재시도 횟수 (0-based) |

---

## Result (`_result.json`)

```json
{
  "domain":  "nova_log_analytics",
  "status":  "success",
  "outputs": [
    {
      "type":    "anomaly_report",
      "path":    "projects/nova_log_analytics/output/report_2026-04-11.md",
      "summary": "이상치 3건 감지 (HIGH×1, MEDIUM×2)"
    }
  ],
  "errors":   [],
  "metadata": {"rows_processed": 1500}
}
```

`status` 값: `"success"` | `"partial"` | `"error"`

---

## Validation (`_validation.json`)

```json
{
  "verdict":       "FAIL",
  "issues": [
    {
      "severity": "HIGH",
      "item":     "anomaly_report",
      "reason":   "expected_outputs 중 sql_result 누락"
    }
  ],
  "passed_checks":  ["구조 검증", "경로 존재 확인"],
  "advisor_needed": true
}
```

`verdict` 값: `"PASS"` | `"FAIL"` | `"INSUFFICIENT"`

**검증 기준:**
- **구조 검증**: 결과물이 스키마를 충족하는가
- **일관성 검증**: 기존 문서/코드와 충돌하지 않는가
- **완결성 검증**: 요청된 모든 항목이 처리되었는가

---

## Advice (`_advice.json`)

```json
{
  "root_cause": "SQL 파이프라인 실행 중 연결 타임아웃",
  "solutions": [
    {
      "priority":     1,
      "action":       "nova_log_analytics에 SQL 실행 재시도 지시 (timeout=60s)",
      "target_agent": "domain"
    },
    {
      "priority":     2,
      "action":       "sql_result 없이 anomaly_report만으로 보고 진행",
      "target_agent": "execution"
    }
  ],
  "escalate_to_user": false
}
```

`escalate_to_user: true` → Reporter가 중간 보고 후 사용자 입력 대기.

---

## Report (`_report.json`)

```json
{
  "summary": "이상탐지 완료. 이상치 3건 감지.",
  "sections": [
    {"title": "실행 결과",  "content": "..."},
    {"title": "검증 결과",  "content": "PASS — 모든 체크 통과"},
    {"title": "산출물",     "content": "report_2026-04-11.md 저장 완료"}
  ],
  "artifacts":   ["projects/nova_log_analytics/output/report_2026-04-11.md"],
  "report_path": "global/05_PM_Outputs/nova_log_analytics_이상탐지_2026-04-11.md"
}
```

---

## 에스컬레이션 규칙

| 조건 | 동작 |
|---|---|
| `verdict=PASS` | Reporter 활성화 |
| `verdict=INSUFFICIENT` | Execution 재시도 (max 5회) |
| `verdict=FAIL` + `advisor_needed=true` | Advisor 활성화 (max 3회) |
| Advisor 3회 후 여전히 FAIL | `escalate_to_user=true` → 사용자 입력 대기 |
