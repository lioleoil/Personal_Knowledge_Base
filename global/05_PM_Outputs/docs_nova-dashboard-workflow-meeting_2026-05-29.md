# NOVA 분석 대시보드 × DAT Gen2 워크플로우 연계 정기 미팅 설계

**문서 상태**: Released (v1.0)  
**작성일**: 2026-05-29  
**작성자**: PO (NOVA Analytics)  
**관련 프로젝트**: `projects/nova_log_analytics`  
**참조 링크**: [DIC-938 Dashboard Feedback Consolidation](https://stradvision.atlassian.net/wiki/spaces/DIC/pages/49812276022/)

---

## 1. 미팅 목적

라벨링 오퍼레이션의 실질적인 효율 개선을 위해, **NOVA 분석 대시보드에서 생성된 인사이트가 DAT Gen2 Feature 담당자의 일상 의사결정과 직접 연결**되도록 한다.

단순 데이터 공유 자리가 아니라, 각 미팅에서 **구체적 액션이 도출되고 이행이 추적**되는 구조를 만드는 것이 핵심이다.

---

## 2. 참석자

| 역할 | 담당 | 비고 |
|---|---|---|
| NOVA 분석팀 PO/PM | 대시보드 결과 공유 및 미팅 진행 | 아젠다 준비 · 액션 추적 |
| DAT Gen2 Feature 담당자 | 업체별 오퍼레이션 상황 공유 및 의사결정 | 조치 권한 보유자 |
| (선택) 업체 QC 담당 | 반려·재작업 이슈 발생 시 참여 | 이슈 발생 시 초대 |

---

## 3. 미팅 주기 및 채널

| 단계 | 주기 | 채널 | 비고 |
|---|---|---|---|
| **MV1** (현재 ~) | 격주 1회 | Slack 허들 또는 Zoom | 미팅 녹화 + Confluence 기록 |
| **MV2** (대시보드 자동화 후) | 이슈 발생 시 On-demand | Slack #nova-analytics-review | 자동 알림 기반 트리거 |
| **MV2 이후** | 월 1회 전략 리뷰 | 대면 또는 Zoom | 지표 개선 방향 · 분기 계획 |

---

## 4. 정기 미팅 아젠다 프레임워크 (40분)

### 섹션 A — 지난 주기 리뷰 (10분)

| 확인 항목 | 데이터 소스 | 기대 산출 |
|---|---|---|
| Task Stage Progress 스냅샷 | `dashboard__pipeline_snapshot.sql` | 업체별 현재 상태 분포 |
| 납품 완료율 vs 목표 GAP | `dashboard__pipeline_funnel.sql` | Feature × 업체 GAP 테이블 |
| Aging 경고/심각 Task | `dashboard__waiting_aging.sql` | 즉시 처리 필요 목록 |
| 지난 회의 액션 아이템 | Confluence 기록 | 이행률 확인 |

### 섹션 B — Feature별 심층 논의 (20분)

논의 우선순위 결정 기준:
1. **납품 완료율 하위 Feature** (Funnel 기준)
2. **Aging 심각 Task 비중 상위 업체·Stage**
3. **Reject 재작업 비중 급증 조합** (Operation Analytics)

각 이슈에 대해 아래 3가지 질문을 중심으로 논의:
- 병목의 원인이 **대기 (배정 지연)** 인가, **처리 지연 (작업자 이슈)** 인가?
- 업체 자체 해결 가능한가, **NOVA/DAT 개입**이 필요한가?
- 이번 주기 내 조치가 가능한가, **일정 재조정**이 필요한가?

### 섹션 C — 액션 도출 및 마무리 (10분)

| 항목 | 내용 |
|---|---|
| 이번 주기 액션 | 업체 / Feature / 마감일 / 담당자 명확히 기록 |
| 대시보드 개선 요청 | 즉시 반영 vs DIC Backlog 등록 여부 결정 |
| 다음 미팅 포커스 | 사전 합의하여 담당자 데이터 준비 유도 |

---

## 5. MV 단계별 전개 방향

```
MV1 (현재)                          MV2 (자동화)
────────────────────────────────────────────────────────────
대시보드 수동 공유         →   담당자 셀프서브 조회
주요 이슈 발굴·논의 중     →   Aging 알림 기반 예외 탐지
PO 주도 정기 미팅          →   이슈 발생 시 On-demand 미팅
Backlog 수기 적재          →   알림 → 담당자 즉시 조치 루프
```

### MV1 목표 체크리스트

- [ ] Pipeline Snapshot / Funnel / Aging SQL 3종 완성 및 Databricks 배포
  - `dashboard__pipeline_snapshot.sql`
  - `dashboard__pipeline_funnel.sql`
  - `dashboard__waiting_aging.sql`
- [ ] Feature 담당자 대상 대시보드 해석 가이드 배포 (1장 요약 시트)
- [ ] 미팅에서 도출된 요청사항 → DIC Backlog 적재 프로세스 정립
- [ ] 총 배정 Task 기준 (착수 vs ready) 데이터 검증 완료

### MV2 목표 체크리스트

- [ ] Databricks SQL Dashboard 또는 Slack 알림 자동화 구현
- [ ] Aging 경고(72h) 임계값 도달 시 Feature 담당자 자동 노티
- [ ] Reject 재작업 급증 시 자동 Slack 알림 (업체 × Feature 조합)
- [ ] 미팅 구조 전환: 월 1회 전략 리뷰로 격상

---

## 6. 미팅 전 D-1 준비 체크리스트

NOVA 분석팀(PO/PM) 준비 사항:

- [ ] `dashboard__pipeline_snapshot.sql` 최신 실행 결과 스크린샷 준비
- [ ] Aging 경고(72h 이상) 이상 Task 목록 추출 및 업체별 정리
- [ ] 지난 주 납품 실적 vs 계획 비교 (Feature × 업체)
  - 소스: `production_volume__weekly.sql`
- [ ] 지난 미팅 액션 아이템 이행 현황 업데이트 (Confluence)
- [ ] 신규 Backlog 항목 정리 및 우선순위 예비 안 작성

Feature 담당자 준비 사항:

- [ ] 현재 진행 중 이슈 중 대시보드 상으로 보이지 않는 맥락 정리
- [ ] 업체와 공유된 일정 기준 vs 현재 진척 GAP 파악

---

## 7. 의사결정 기록 템플릿

> 매 미팅 후 Confluence에 아래 형식으로 기록. 제목 형식: `[NOVA-미팅] YYYY-MM-DD`

| 항목 | 내용 |
|---|---|
| **날짜** | |
| **참석자** | |
| **주요 이슈** | |
| **결정 사항** | |
| **액션 아이템** | 담당자 / 마감일 |
| **다음 미팅 포커스** | |

---

## 8. 향후 워크플로우 (MV2 이후 목표)

```
Databricks 일 배치 완료
        ↓
Aging 임계값 초과 탐지
        ↓
Slack 자동 알림 (#nova-analytics-review)
→ Feature 담당자 수신
        ↓
담당자 셀프서브 조회 (Databricks SQL Dashboard)
        ↓
즉시 조치 or 에스컬레이션
        ↓
월 1회 전략 리뷰 미팅에서 트렌드 검토
```

미팅이 "공유 자리"에서 **"전략 의사결정 자리"**로 격상되는 것이 최종 목표다.

---

## 9. 관련 문서 참조

| 문서 | 경로 | 용도 |
|---|---|---|
| Stage Progress Dashboard 설계 | `projects/nova_log_analytics/.assistant/skills/stage_progress_dashboard_design.md` | SQL 스케치 · Aging 임계값 정의 |
| Operation Analytics 설계 | `projects/nova_log_analytics/.assistant/skills/kpi _metrics/operation_efficiency/operation_concept_design.md` | Stage Duration · Reject 분석 |
| KPI 지표 전체 정책 | `projects/nova_log_analytics/.assistant/skills/kpi _metrics/kpi_metric_policy.md` | 지표 정의 · 산출식 기준 |
| Labeling KPI 개요 | `projects/nova_log_analytics/.assistant/skills/common/[Performance] Labeling KPI Definition - Productivity, Quality ,Operational Efficiency.md` | 3대 KPI 카테고리 |
| Stage 전환 구조 | `projects/nova_log_analytics/.assistant/skills/common/stage_transition_analysis.md` | 파이프라인 상태 전환 정의 |

---

## 버전 히스토리

| 버전 | 일자 | 내용 |
|---|---|---|
| v1.0 | 2026-05-29 | 최초 작성 — 정기 미팅 아젠다 프레임워크 · MV 단계별 전개 · D-1 체크리스트 · 의사결정 템플릿 |
