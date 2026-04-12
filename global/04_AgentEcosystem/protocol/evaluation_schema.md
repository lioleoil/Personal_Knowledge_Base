# Evaluation Schema — 10항목 평가 보고서

> Advisor Agent가 Validation PASS 후 생성하는 평가 보고서 JSON 스키마.  
> 저장 위치: `.agents/bus/<task_id>_evaluation.json`  
> Python: `AgentBus.write_evaluation(scores, total_score, summary, ...)`

---

## JSON 스키마

```json
{
  "_task_id":     "abc12345",
  "_file_type":   "evaluation",
  "_written_at":  "2026-04-12T15:00:00",
  "scores": {
    "code_quality": {
      "score":    8,
      "evidence": "lint 이슈 0개, 중복 코드 없음",
      "issues":   []
    },
    "agent_utilization": {
      "score":    7,
      "evidence": "Execution 1회, Validation 1회 — 투입 대비 기여 양호",
      "issues":   []
    },
    "parallelization": {
      "score":    6,
      "evidence": "독립 서브태스크 3개 중 2개만 병렬 실행",
      "issues":   ["파일 분류 단계 순차 실행 → 병렬 가능했음"]
    },
    "token_cost": {
      "score":    9,
      "evidence": "실소비 $0.042 (예상 $0.05 대비 84%)",
      "issues":   []
    },
    "retry_waste": {
      "score":    8,
      "evidence": "재시도 0회",
      "issues":   []
    },
    "comm_efficiency": {
      "score":    7,
      "evidence": "메시지 4건 / 핵심 정보 밀도 양호",
      "issues":   []
    },
    "completion_rate": {
      "score":    10,
      "evidence": "expected_outputs 3/3 달성 (100%)",
      "issues":   []
    },
    "duration": {
      "score":    7,
      "evidence": "실소요 8분 (플랜 예상 6분 대비 133%)",
      "issues":   ["Validation 단계 지연 2분"]
    },
    "issue_resolution": {
      "score":    9,
      "evidence": "FAIL/INSUFFICIENT 발생 없음",
      "issues":   []
    },
    "autonomy": {
      "score":    10,
      "evidence": "에스컬레이션 0회",
      "issues":   []
    }
  },
  "total_score":       81,
  "grade":             "A",
  "summary":           "전반적으로 높은 완결률과 자율성. 병렬화 효율 개선 여지 있음.",
  "improvement_items": ["병렬화 가능 단계 식별 및 병렬 실행 적용"],
  "commit_ready":      true
}
```

---

## 점수 기준

| 점수 | 의미 |
|---|---|
| 9-10 | 최적. 개선 불필요. |
| 7-8  | 양호. 소폭 개선 가능. |
| 5-6  | 보통. 개선 권장. |
| 3-4  | 미흡. 개선 필요. |
| 1-2  | 심각. 즉시 조치 필요. |

## 등급 기준

| 등급 | 총점 | 의미 |
|---|---|---|
| S | 90점 이상 | 탁월 — 그대로 커밋 권장 |
| A | 80-89점 | 우수 — 커밋 가능 |
| B | 70-79점 | 양호 — 경미한 개선 후 커밋 |
| C | 60-69점 | 보통 — 개선 후 재평가 권장 |
| D | 60점 미만 | 미흡 — 재작업 권장 |

---

## commit_ready 판단 기준

- `true`: 총점 ≥ 70 AND completion_rate.score ≥ 8
- `false`: 위 조건 불충족 OR 심각 이슈 발견
