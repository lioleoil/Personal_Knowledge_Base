# Stage Transition Analysis

## stageAssignees - stageKey별 샘플 (4건)

| stageKey | assigneeId | assignedAt |
|----------|------------|------------|
| final_qa | 65efe672...07c58d | 2026-04-08T02:11:14 |
| inspection | 65efe672...07c58d | 2026-04-08T02:09:07 |
| labeling | 69c3572a...40fe86 | 2026-04-06T20:46:19 |
| review | 69c3572a...40fe86 | 2026-04-06T20:46:11 |

---

## transitionHistory - fromState/toState별 샘플 (17건)

| fromState | toState | trigger | actionBy |
|-----------|---------|---------|----------|
| ready | waiting_labeling | auto | system |
| waiting_labeling | labeling | start | user |
| labeling | waiting_review | submit | user |
| labeling | labeling | reassign | user |
| waiting_review | review | start | user |
| review | waiting_submit | submit | user |
| review | waiting_labeling | reject | user |
| review | review | reassign | user |
| waiting_submit | inspection | deliver | user |
| waiting_submit | waiting_review | reject | user |
| inspection | waiting_final_qa | submit | user |
| inspection | waiting_review | reject | user |
| inspection | inspection | reassign | user |
| waiting_final_qa | final_qa | start | user |
| final_qa | completed | submit | user |
| final_qa | final_qa | reassign | user |

---

## 상태 흐름 (State Flow)

### 메인 파이프라인

```
ready
  └─(auto)─→ waiting_labeling
                └─(start)─→ labeling
                              └─(submit)─→ waiting_review
                                             └─(start)─→ review
                                                           └─(submit)─→ waiting_submit
                                                                          └─(deliver)─→ inspection
                                                                                         └─(submit)─→ waiting_final_qa
                                                                                                        └─(start)─→ final_qa
                                                                                                                      └─(submit)─→ completed
```

### 분기 (Branches)

| 단계 | trigger | 결과 |
|------|---------|------|
| labeling | reassign | labeling (재배정) |
| review | reject | waiting_labeling (반려 → 재작업) |
| review | reassign | review (재배정) |
| waiting_submit | reject | waiting_review (반려 → 재검토) |
| inspection | reject | waiting_review (반려 → 재검토) |
| inspection | reassign | inspection (재배정) |
| final_qa | reassign | final_qa (재배정) |

### 요약

- **순방향 파이프라인**: `ready → waiting_labeling → labeling → waiting_review → review → waiting_submit → inspection → waiting_final_qa → final_qa → completed`
- **자동 전환**: `ready → waiting_labeling` 는 system에 의해 auto 트리거
- **reject (반려)**: 이전 단계로 되돌아가는 분기 (review, inspection 단계에서 발생)
- **reassign (재배정)**: 동일 단계 내에서 담당자 변경 (labeling, review, inspection, final_qa)
