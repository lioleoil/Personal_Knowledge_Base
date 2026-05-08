# 이상 탐지 스코어링 검증 및 튜닝

> anomaly_detection_runner의 스코어링 결과를 cross-feature 관점에서 검증하고,
> 가중치/CAP 파라미터를 시뮬레이션하여 최적 설정을 탐색한다.

---

## 포함 노트북

### 1. Scoring v1.2 Cross-Feature Validation

**경로**: `.assistant/skills/anomaly_detection_scoring/Scoring v1.2 Cross-Feature Validation`

**목적**: OD/LD/RMD 3개 feature에 대해 runner를 실행하고, 스코어링 v1.2의 cross-feature 공정성을 검증.

**검증 항목**:
- Per-STEP 점수가 feature간 비교 가능한 스케일인지
- STEP 4 skip (LD) vs active (OD/RMD)의 A 카테고리 점수 공정성
- C 카테고리의 객체 비율 정규화가 feature별 모수 차이를 적절히 반영하는지
- Stage 2 병합 결과가 B/C 카테고리에 적절히 반영되는지 (v1.2 신규)
- 점수 0~100 범위, 등급 유효성

**셀 구조**:
1. Setup & Run all features — `dbutils.notebook.run(RUNNER_PATH)` 로 3 feature 순차 실행
2. 결과 비교 테이블 — Per-STEP, 카테고리, 종합 점수 비교
3. STEP 4 공정성 검증 — skip/active 분기별 A 점수 분석
4. C 카테고리 정규화 검증 — v0.9 vs v1.x 비교
5. 종합 검증 결과 — 범위/카테고리/등급 PASS/FAIL

**전제 조건**: anomaly_detection_runner가 실행 가능한 상태

---

### 2. Scoring Weight Tuning Simulation

**경로**: `.assistant/skills/anomaly_detection_scoring/Scoring Weight Tuning Simulation`

**목적**: anomaly_detection_results 테이블의 실제 데이터 기반으로 W_A/W_B/W_C 및 CAP_EVENT/CAP_OBJECT 파라미터를 변경하며 품질 점수 변화를 시뮬레이션.

**기능**:
- `compute_quality_score()` 함수: runner와 동일한 Per-STEP CAP 기반 스코어링 재현
- 카테고리 가중치 7종 시뮬레이션 (A중심, v1.2 기본, B중심, C강화, v0.9 기본, 균등, C최소)
- CAP 비율 격자 탐색 (CAP_EVENT × CAP_OBJECT 25개 조합)
- Heatmap 시각화 (feature별 CAP 감도)
- 최적 파라미터 추천 (std 최소 기준)

**셀 구조**:
1. 실제 데이터 로드 — results/reports 테이블에서 최신 분석 데이터 로드
2. Feature별 raw metrics 추출 — STEP별 severity/count + STEP4_CONFIG 기반 skip 판단
3. 스코어링 함수 정의 + 기준 점수 계산
4. 카테고리 가중치 시뮬레이션
5. CAP 비율 감도 시뮬레이션
6. Heatmap 시각화
7. 최적 파라미터 추천

**전제 조건**: anomaly_detection_runner가 3개 feature에 대해 실행 완료된 상태

---

## 관련 테이블

- `sv_nova_dev_an2_catalog.analytics.anomaly_detection_results` — STEP별 탐지 결과
- `sv_nova_dev_an2_catalog.analytics.anomaly_detection_reports` — 종합 보고서 (scoring_details JSON 포함)

---

## 스코어링 수식 (v1.2)

```
Per-STEP: score_i = min(weighted / denominator × 100 × M, 100)
  - 이벤트 기반 (S1,S2,S3,S4): M = 100 / CAP_EVENT_RATE(5%) = 20
  - 객체 기반 (S5):            M = 100 / CAP_OBJECT_RATE(10%) = 10

카테고리:
  A = mean(S1, S2, [S4])    # S4 skip 시 제외
  B = S3                    # STEP 3 + STEP 8/9 병합 결과
  C = S5                    # STEP 5 + STEP 6/7 병합 결과

종합: quality_score = 0.40×A + 0.40×B + 0.20×C
등급: 정상(≤20) / 주의(21~45) / 불량(>45)
```

---

## Stage 2 병합 구조 (v1.2)

STEP 6/7/8/9의 결과는 별도 스코어링 단계를 만들지 않고,
기존 step_id에 결과를 병합하여 scoring v1.1 수식 변경 없이 자연스럽게 통합됩니다.

### Category B (시간 정합성) = step_id=3 집계

| 출처 | 내용 | severity | 가중치 |
|--------|------|----------|--------|
| STEP 3 기존 | occurred_at vs event_time 지연 | normal/warning/critical | B: w=0.5/c=1.0 |
| STEP 8a → S3 | 스테일 세션 (gap > 600분) | critical | ×1.0 |
| STEP 8b → S3 | 집중도 저하 (avg>30s & gaps>10) | warning | ×0.5 |
| STEP 9 → S3 | 수집 공백 (활성시간 Dead Hour) | critical/warning | c=×1.0 / w=×0.5 |

### Category C (행동 패턴) = step_id=5 집계

| 출처 | 내용 | severity | 가중치 |
|--------|------|----------|--------|
| STEP 5 기존 | 복수 사용자 동시 편집 | normal/warning/critical | C: w=0.5/c=1.0 |
| STEP 6a → S5 | Undo 비율 (사용자별 undo_rate >30%/50%) | warning/critical | w=×0.5/c=×1.0 |
| STEP 6b → S5 | Undo burst (30초 내 5건+/10건+) | warning/critical | w=×0.5/c=×1.0 |
| STEP 7a → S5 | 시간 역전 (event_time 역순) | critical | ×1.0 |
| STEP 7b → S5 | 복수편집 비율 (task 내 >50%) | warning | ×0.5 |

### 설계 원칙

> 별도 step_id를 만들지 않고 기존 step_id=3, step_id=5에 결과를 저장.
> Per-STEP 점수 계산 시 `step_score(3)`, `step_score(5)` 호출로 자동 포함.
> 카테고리/종합 점수 수식 변경 없이 자연스럽게 반영.

### 보고서 JSON 확장 (scoring_details)

v1.2부터 `scoring_details` JSON에 `stage2_extended` 필드 추가:

```json
{
  "version": "v1.2",
  "stage2_extended": {
    "step6": {"total_undos": 62, "total_redos": 0, "high_undo_users": 0, "burst_sessions": 3, "max_burst_size": 7},
    "step7": {"reversals": 0, "multi_edit_pct": 42.1, "multi_objects": 82, "total_objects": 195},
    "step8": {"stale_sessions": 3, "low_focus_users": 2},
    "step9": {"dead_hours": [], "low_hours": [], "hourly": {"0": 1523, ...}}
  }
}
```

---

## 임계값 보정 이력

### v1.2 (2026-04-07) — Stage 2 병합

| STEP | 항목 | 기준 | 근거 |
|------|------|------|------|
| 6a | Undo 비율 | >30% → warning, >50% → critical | workspace_history 테이블 기반 사용자별 undo_count/cmd_count |
| 6b | Undo burst | 30초내 5건+ → warning, 10건+ → critical | 동일 session+task 내 윈도우 기반 |
| 7a | 시간 역전 | >0건 → critical | 245 session-task 전수검사, 역전 0건 확인 |
| 7b | 복수편집 비율 | >50% → warning | OD 73~100%, LD <1%, RMD 15% 실측 기반 |
| 8a | 스테일 세션 | gap >36000s → critical | 야간 4건 (634, 630, 560, 511분) 확인 |
| 8b | 집중도 저하 | avg>30s & gaps_5min>10 → warning | manager 9.7%, labeler <1.5% 기반 |
| 9 | 수집 공백 | 활성시간 0건 → critical, <100건 → warning | 최소 521건/시간 확인 |

---

## 사용 시점

- 스코어링 파라미터(가중치, CAP 비율) 변경 검토 시
- runner 수정 후 cross-feature 공정성 검증 시
- 새로운 feature 추가 후 기존 설정과의 호환성 확인 시
- 등급 기준(20/45) 조정 검토 시
- Stage 2 병합 결과가 B/C 카테고리 점수에 미치는 영향 확인 시 (v1.2 신규)
