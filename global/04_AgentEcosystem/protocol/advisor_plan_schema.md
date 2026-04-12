# Advisor Plan Schema — 플랜 마크다운 구조 정의

> Advisor Agent가 Phase 2에서 작성하는 플랜 파일 구조.  
> 저장 위치: `global/05_PM_Outputs/advisor_plan_{task_id}.md`  
> 버스 파일: `.agents/bus/<task_id>_advisor_plan.json`

---

## 마크다운 구조

```markdown
# Advisor Plan — {task_id}

> **작성일**: {YYYY-MM-DD HH:MM}  
> **도메인**: {domain}  
> **요청 요약**: {goal 한 줄}

---

## 1. 목적 및 컨텍스트

{배경 설명 — 왜 이 작업이 필요한지, 사용자 의도}

**제약 조건**:
- {constraint_1}
- {constraint_2}

---

## 2. 에이전트별 지시

### Execution Agent
- **수행 단계**: {단계별 구체 지시}
- **사용 도구**: {Read/Write/Edit/Bash/WebSearch 등}
- **주의사항**: {실수하기 쉬운 포인트}

### Validation Agent
- **검증 기준**: {구체적 Pass/Fail 조건}
- **중점 확인**: {특별히 집중할 항목}

### Reporter Agent
- **보고서 형식**: {마크다운/JSON/etc}
- **포함 섹션**: {섹션 목록}

---

## 3. 예상 산출물

| # | 산출물 | 형태 | 저장 위치 |
|---|---|---|---|
| 1 | {output_name} | {file/json/md} | {path} |

---

## 4. 품질 기준

- [ ] {quality_criterion_1}
- [ ] {quality_criterion_2}
- [ ] {quality_criterion_3}

---

## 5. 예상 소요 시간 및 비용

| 항목 | 예상 |
|---|---|
| 소요 시간 | {N}분 |
| 토큰 예산 | {N}k tokens |
| 예상 비용 | ${N} |

---

## 6. 리스크 항목

| 리스크 | 가능성 | 대응 방안 |
|---|---|---|
| {risk_1} | 낮음/중간/높음 | {mitigation} |
```

---

## advisor_plan.json 구조

```json
{
  "_task_id":            "abc12345",
  "_file_type":          "advisor_plan",
  "_written_at":         "2026-04-12T10:00:00",
  "plan_md_path":        "global/05_PM_Outputs/advisor_plan_abc12345.md",
  "context_summary":     "pkb_worklog 분류 작업 — 최근 WorkLog 파일 주제별 자동 분류",
  "agent_instructions": {
    "execution":   "classify.py 실행하여 04_WorkLog/*.jsonl 처리. 병렬 가능한 파일은 병렬 실행.",
    "validation":  "분류 결과 파일 존재 여부 + INDEX.md 업데이트 확인",
    "reporter":    "분류 완료 파일 목록 + 요약 통계 마크다운 출력"
  },
  "expected_outputs":   ["04_WorkLog 분류 파일", "INDEX.md 업데이트"],
  "quality_criteria":   ["모든 .jsonl 파일 처리됨", "INDEX.md 최신화됨"]
}
```
