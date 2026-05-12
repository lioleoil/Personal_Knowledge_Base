# Focus Drop — 배포 및 운영 가이드

> **코어 참조**: 메트릭 정의·판정 기준·핵심 SQL은 `SKILL.md` 참조  
> **생산성 연계**: idle rollup → Task net hours 연계는 `focus_drop_productivity_linkage.md` 참조

---

## 6. 파이프라인 구조

### 6.1 실행 순서

```
[기준선 산출 — 분기/주 단위]

focus_drop__gap_percentiles.sql          → analytics.focus_drop_gap_thresholds
                                            (1차 percentile: gap 구간 경계)

[일 단위 배치 — 매일 04:00 UTC]

focus_drop__session_metrics.sql          → analytics.focus_drop_session_metrics
        ↓                                   (세션별 count/ratio/duration 산출)
focus_drop__task_idle_rollup.sql         → analytics.focus_drop_task_idle_rollup
        ↓                                   (Task별 idle 누적 횟수/초수 산출)
focus_drop__session_tags.sql             → analytics.focus_drop_session_tags
        ↓                                   (기준선 참조 → 세션 판정)
focus_drop__user_day_kpi.sql             → analytics.focus_drop_user_day_kpi
                                            (기준선 참조 → 유저 판정)

[기준선 갱신 — 주 1회 월요일 03:00 UTC, session_metrics/user_day_kpi 누적 결과를 입력으로 사용]

focus_drop__session_thresholds.sql       → analytics.focus_drop_session_thresholds
                                            (직전 30일 session_metrics 기반)
focus_drop__user_thresholds.sql          → analytics.focus_drop_user_thresholds
                                            (직전 30일 user_day_kpi 기반)
```

> **의존성 방향**: session_thresholds / user_thresholds는 session_metrics / user_day_kpi의 **누적 산출물**(직전 30일분)을 입력으로 사용한다. 반대로 session_tags / user_day_kpi는 session_thresholds / user_thresholds의 **최신 기준선**을 참조한다. `task_idle_rollup`은 session_metrics의 당일 산출물을 입력으로 사용하며 기준선에는 의존하지 않는다. 따라서 정상 운영 시 실행 순서는 `session_metrics → task_idle_rollup → session_tags → user_day_kpi` (일 배치) / `session_thresholds → user_thresholds` (주 배치, session_metrics / user_day_kpi 결과 반영)이다.

### 6.2 실행 스케줄

| 노트북 | 실행 주기 | 트리거 조건 |
|--------|----------|------------|
| `gap_percentiles` | 분기 1회 또는 분포 변화 시 | 기준값 드리프트 ±20% 감지 |
| `session_thresholds`, `user_thresholds` | 주 1회 (월요일 03:00 UTC) | 직전 30일 rolling window 갱신 |
| `session_metrics` → `task_idle_rollup` → `session_tags` → `user_day_kpi` | 일 단위 배치 | 매일 04:00 UTC (전일 데이터 대상) |

### 6.3 Delta 테이블

> 초기 생성 DDL: `.sql/focus_drop__ddl.sql` (7개 테이블, `PARTITIONED BY (analysis_date)` + `columnMapping.mode = 'name'` 포함)

| 테이블 | 스키마 | 갱신 전략 |
|--------|--------|----------|
| `analytics.focus_drop_gap_thresholds` | `version INT, computed_at TIMESTAMP, feature_scope STRING, sample_count BIGINT, gap_p50 DOUBLE, gap_p75 DOUBLE, gap_p90 DOUBLE, gap_p95 DOUBLE, gap_p99 DOUBLE` (gap_p99는 참고 진단용) | 버전업 시 INSERT |
| `analytics.focus_drop_session_thresholds` | `version INT, computed_at TIMESTAMP, is_bootstrap BOOLEAN, window_start DATE, window_end DATE, session_light_count_p90 DOUBLE, session_heavy_count_p95 DOUBLE, session_idle_count_p99 DOUBLE, session_light_ratio_p90 DOUBLE, session_heavy_ratio_p95 DOUBLE, session_idle_ratio_p99 DOUBLE` | 주 1회 INSERT |
| `analytics.focus_drop_user_thresholds` | `version INT, computed_at TIMESTAMP, is_bootstrap BOOLEAN, window_start DATE, window_end DATE, user_light_session_count_p90 DOUBLE, user_heavy_session_count_p95 DOUBLE, user_idle_gap_total_p99 DOUBLE` | 주 1회 INSERT |
| `analytics.focus_drop_session_metrics` | `analysis_date DATE, user_id STRING, session_id STRING, task_id STRING, total_gaps INT, observation_gap_count INT, light_gap_count INT, heavy_gap_count INT, idle_gap_count INT, idle_gap_duration_sec DOUBLE, light_gap_ratio DOUBLE, heavy_gap_ratio DOUBLE, idle_gap_ratio DOUBLE, session_avg_gap DOUBLE` | INSERT INTO ... REPLACE WHERE analysis_date |
| `analytics.focus_drop_task_idle_rollup` | `analysis_date DATE, task_id STRING, role_scope STRING, role_group STRING, contributing_sessions INT, contributing_users INT, idle_gap_total INT, idle_gap_duration_sec DOUBLE` | INSERT INTO ... REPLACE WHERE analysis_date |
| `analytics.focus_drop_session_tags` | `analysis_date DATE, user_id STRING, session_id STRING, task_id STRING, light_gap_count INT, heavy_gap_count INT, idle_gap_count INT, is_light_session BOOLEAN, is_heavy_session BOOLEAN, is_idle_session BOOLEAN, focus_drop_level STRING` | INSERT INTO ... REPLACE WHERE analysis_date |
| `analytics.focus_drop_user_day_kpi` | `analysis_date DATE, user_id STRING, light_session_count INT, heavy_session_count INT, idle_gap_total INT, total_sessions INT, is_light_user BOOLEAN, is_heavy_user BOOLEAN, is_idle_user BOOLEAN, user_focus_drop_level STRING` | INSERT INTO ... REPLACE WHERE analysis_date |

### 6.4 Databricks Job 구성

파이프라인은 **배포 단계(Phase)** 에 따라 Job 구성이 달라진다.

#### Phase A Job — Warm-up 전용 일 배치 (Day 1~6)

기준선 테이블이 없으므로 `session_metrics`와 `task_idle_rollup`만 실행. `session_tags` / `user_day_kpi`는 포함하지 않는다.

```yaml
# Job: focus_drop_warmup_daily  (Phase A 전용 — Day 7 이후 아래 steady-state job으로 교체)
# Schedule: 0 0 4 * * ?  (매일 04:00 UTC)
tasks:
  - task_key: session_metrics
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__session_metrics
      base_parameters:
        analysis_date: "{{ds}}"       # Databricks 날짜 변수: 전일 기준

  - task_key: task_idle_rollup
    depends_on:
      - task_key: session_metrics
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__task_idle_rollup
      base_parameters:
        analysis_date: "{{ds}}"
```

#### Phase B 수동 실행 순서 (Day 7 — 1회성)

Job이 아닌 수동 순차 실행. §12.4 Bootstrap 절차 참조.

```
1. session_thresholds   rolling_window_days=7, is_bootstrap=TRUE
2. zero-inflation 보정  (§12.1 UPDATE SQL)
3. task_idle_rollup     analysis_date=(누락일 전체 소급)
4. session_tags         analysis_date=(누락일 전체 소급)
5. user_thresholds      수동 INSERT (§12.4 Bootstrap INSERT 참조)
6. user_day_kpi         analysis_date=(누락일 전체 소급)
7. focus_drop_daily Job 활성화 (steady-state 일 배치 진입)
```

#### Steady-state Job — 일 배치 (Day 7+)

Phase A Job을 폐기하고 아래 Job으로 교체.

```yaml
# Job: focus_drop_daily
# Schedule: 0 0 4 * * ?  (매일 04:00 UTC)
tasks:
  - task_key: session_metrics
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__session_metrics
      base_parameters:
        analysis_date: "{{ds}}"

  - task_key: task_idle_rollup
    depends_on:
      - task_key: session_metrics
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__task_idle_rollup
      base_parameters:
        analysis_date: "{{ds}}"

  - task_key: session_tags
    depends_on:
      - task_key: session_metrics
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__session_tags
      base_parameters:
        analysis_date: "{{ds}}"

  - task_key: user_day_kpi
    depends_on:
      - task_key: session_tags
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__user_day_kpi
      base_parameters:
        analysis_date: "{{ds}}"
```

#### Steady-state Job — 주 배치 (매주 월요일)

`session_thresholds`와 `user_thresholds`는 소스 테이블이 달라 독립 실행 가능 → 병렬 실행.

```yaml
# Job: focus_drop_weekly
# Schedule: 0 0 3 ? * MON  (매주 월요일 03:00 UTC — 일 배치 완료 후)
tasks:
  - task_key: session_thresholds      # focus_drop_session_metrics 참조
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__session_thresholds
      base_parameters:
        rolling_window_days: "30"
        is_bootstrap: "false"

  - task_key: user_thresholds         # focus_drop_user_day_kpi 참조 (session_thresholds 불필요)
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__user_thresholds
      base_parameters:
        rolling_window_days: "30"
        is_bootstrap: "false"
```

#### Quarterly Job — gap_percentiles (분기 1회)

분포 드리프트 여부와 무관하게 분기 정기 실행. 드리프트 감지 시 §9.2 SOP에 따라 수동 재실행 추가 가능.

```yaml
# Job: focus_drop_quarterly
# Schedule: 0 0 2 1 1,4,7,10 ?  (1월·4월·7월·10월 1일 02:00 UTC)
tasks:
  - task_key: gap_percentiles
    notebook_task:
      notebook_path: /Workspace/.../focus_drop__gap_percentiles
      base_parameters:
        rolling_days: "90"
```

---

---

## 7. SQL 레퍼런스 (기준선 · 판정 · 유저 KPI)

### 7.3 세션 기준선 산출 (rolling 30일)

```sql
-- focus_drop__session_thresholds.sql
INSERT INTO analytics.focus_drop_session_thresholds
SELECT
  COALESCE((SELECT MAX(version) FROM analytics.focus_drop_session_thresholds), 0) + 1  AS version,
  CURRENT_TIMESTAMP()                              AS computed_at,
  FALSE                                            AS is_bootstrap,
  DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AS window_start,
  DATE_SUB(CURRENT_DATE(), 1)                      AS window_end,
  PERCENTILE(light_gap_count,   0.90)              AS session_light_count_p90,
  PERCENTILE(heavy_gap_count,   0.95)              AS session_heavy_count_p95,
  PERCENTILE(idle_gap_count,    0.99)              AS session_idle_count_p99,
  PERCENTILE(light_gap_ratio,   0.90)              AS session_light_ratio_p90,
  PERCENTILE(heavy_gap_ratio,   0.95)              AS session_heavy_ratio_p95,
  PERCENTILE(idle_gap_ratio,    0.99)              AS session_idle_ratio_p99
FROM analytics.focus_drop_session_metrics
WHERE analysis_date BETWEEN DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AND DATE_SUB(CURRENT_DATE(), 1);
-- ★ 기준 산출 기간과 판정 대상 기간이 분리됨 (당일 데이터 미포함)
```

### 7.4 세션 판정 (사전 산출 기준선 참조)

```sql
-- focus_drop__session_tags.sql
WITH thresholds AS (
  -- ★ 사전 산출된 rolling baseline 테이블에서 조회 (count + ratio 모두)
  SELECT
    session_light_count_p90, session_heavy_count_p95, session_idle_count_p99,
    session_light_ratio_p90, session_heavy_ratio_p95, session_idle_ratio_p99
  FROM analytics.focus_drop_session_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds)
)
INSERT INTO analytics.focus_drop_session_tags
REPLACE WHERE analysis_date = ${analysis_date}
SELECT
  m.analysis_date,
  m.user_id, m.session_id, m.task_id,
  m.light_gap_count, m.heavy_gap_count, m.idle_gap_count,
  -- 개별 레벨 판정 (count 단독; light 오탐률 > 20% 확인 시 ratio AND 조건 활성화)
  CASE WHEN m.light_gap_count > 0
        AND m.light_gap_count > t.session_light_count_p90
       THEN TRUE ELSE FALSE END AS is_light_session,
  CASE WHEN m.heavy_gap_count > 0
        AND m.heavy_gap_count > t.session_heavy_count_p95
       THEN TRUE ELSE FALSE END AS is_heavy_session,
  CASE WHEN m.idle_gap_count > 0
        AND m.idle_gap_count > t.session_idle_count_p99
       THEN TRUE ELSE FALSE END AS is_idle_session,
  -- ★ 배타적 최종 레벨 (idle > heavy > light > normal)
  CASE
    WHEN m.idle_gap_count > 0
         AND m.idle_gap_count > t.session_idle_count_p99    THEN 'idle'
    WHEN m.heavy_gap_count > 0
         AND m.heavy_gap_count > t.session_heavy_count_p95  THEN 'heavy'
    WHEN m.light_gap_count > 0
         AND m.light_gap_count > t.session_light_count_p90  THEN 'light'
    ELSE 'normal'
  END AS focus_drop_level
FROM analytics.focus_drop_session_metrics m
CROSS JOIN thresholds t
WHERE m.analysis_date = ${analysis_date};
-- ★ ratio 보조판정 활용: 오탐 의심 시 아래 추가 조건으로 필터링 가능
-- AND m.light_gap_ratio > t.session_light_ratio_p90
```

### 7.5 사용자 일 KPI (사전 산출 기준선 참조)

```sql
-- focus_drop__user_day_kpi.sql
WITH user_daily AS (
  SELECT
    user_id,
    analysis_date,
    SUM(CASE WHEN is_light_session THEN 1 ELSE 0 END) AS light_session_count,
    SUM(CASE WHEN is_heavy_session THEN 1 ELSE 0 END) AS heavy_session_count,
    -- ★ idle_gap_total: 세션 판정 무관, 모든 세션의 idle gap(≥ 3분) 누적 절대량
    SUM(idle_gap_count)                               AS idle_gap_total,
    COUNT(*)                                          AS total_sessions
  FROM analytics.focus_drop_session_tags
  WHERE analysis_date = ${analysis_date}
  GROUP BY user_id, analysis_date
),
user_thresholds AS (
  -- ★ 사전 산출된 rolling baseline에서 조회
  SELECT user_light_session_count_p90, user_heavy_session_count_p95, user_idle_gap_total_p99
  FROM analytics.focus_drop_user_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_user_thresholds)
)
INSERT INTO analytics.focus_drop_user_day_kpi
REPLACE WHERE analysis_date = ${analysis_date}
SELECT
  d.analysis_date,
  d.user_id,
  d.light_session_count,
  d.heavy_session_count,
  d.idle_gap_total,
  d.total_sessions,
  -- 개별 레벨 플래그
  CASE WHEN d.light_session_count > 0
        AND d.light_session_count > t.user_light_session_count_p90
       THEN TRUE ELSE FALSE END AS is_light_user,
  CASE WHEN d.heavy_session_count > 0
        AND d.heavy_session_count > t.user_heavy_session_count_p95
       THEN TRUE ELSE FALSE END AS is_heavy_user,
  CASE WHEN d.idle_gap_total > 0
        AND d.idle_gap_total > t.user_idle_gap_total_p99
       THEN TRUE ELSE FALSE END AS is_idle_user,
  -- ★ 배타적 최종 레벨 (idle > heavy > light > normal)
  CASE
    WHEN d.idle_gap_total > 0
         AND d.idle_gap_total > t.user_idle_gap_total_p99        THEN 'idle'
    WHEN d.heavy_session_count > 0
         AND d.heavy_session_count > t.user_heavy_session_count_p95 THEN 'heavy'
    WHEN d.light_session_count > 0
         AND d.light_session_count > t.user_light_session_count_p90  THEN 'light'
    ELSE 'normal'
  END AS user_focus_drop_level
FROM user_daily d
CROSS JOIN user_thresholds t;
```

### 7.6 유저 기준선 산출 (rolling 30일)

```sql
-- focus_drop__user_thresholds.sql
INSERT INTO analytics.focus_drop_user_thresholds
SELECT
  COALESCE((SELECT MAX(version) FROM analytics.focus_drop_user_thresholds), 0) + 1  AS version,
  CURRENT_TIMESTAMP()                              AS computed_at,
  FALSE                                            AS is_bootstrap,
  DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AS window_start,
  DATE_SUB(CURRENT_DATE(), 1)                      AS window_end,
  PERCENTILE(light_session_count,  0.90)          AS user_light_session_count_p90,
  PERCENTILE(heavy_session_count, 0.95)           AS user_heavy_session_count_p95,
  PERCENTILE(idle_gap_total,      0.99)           AS user_idle_gap_total_p99
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date BETWEEN DATE_SUB(CURRENT_DATE(), ${rolling_window_days}) AND DATE_SUB(CURRENT_DATE(), 1);
```

### 7.7 Task idle rollup (생산성 연계용)

```sql
-- focus_drop__task_idle_rollup.sql
INSERT INTO analytics.focus_drop_task_idle_rollup
REPLACE WHERE analysis_date = ${analysis_date}
SELECT
  analysis_date,
  task_id,
  'labeler'                        AS role_scope,
  'labeler'                        AS role_group,
  COUNT(*)                         AS contributing_sessions,
  COUNT(DISTINCT user_id)          AS contributing_users,
  SUM(idle_gap_count)              AS idle_gap_total,
  SUM(idle_gap_duration_sec)       AS idle_gap_duration_sec
FROM analytics.focus_drop_session_metrics
WHERE analysis_date = ${analysis_date}
GROUP BY analysis_date, task_id;
```

> 생산성 SQL에서는 동일 Task가 여러 날짜에 걸쳐 진행될 수 있으므로, `focus_drop_task_idle_rollup`을 `task_id` 기준으로 다시 합산하여 `task_total_idle_sec`를 산출한 후 `deliver_actionAt - start_actionAt`에서 차감한다. 상세 산식은 §16.1 참조.

---

---

## 8. 모니터링 대시보드

### 8.1 일일 요약 뷰

```sql
-- 일일 KPI 현황 조회 (배타적 레벨 기준 — 중복 카운트 없음)
SELECT
  analysis_date,
  COUNT(*) AS total_labelers,
  SUM(CASE WHEN user_focus_drop_level = 'light' THEN 1 ELSE 0 END) AS light_users,
  SUM(CASE WHEN user_focus_drop_level = 'heavy' THEN 1 ELSE 0 END) AS heavy_users,
  SUM(CASE WHEN user_focus_drop_level = 'idle'  THEN 1 ELSE 0 END) AS idle_users,
  ROUND(SUM(CASE WHEN user_focus_drop_level = 'light' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS light_pct,
  ROUND(SUM(CASE WHEN user_focus_drop_level = 'heavy' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS heavy_pct,
  ROUND(SUM(CASE WHEN user_focus_drop_level = 'idle'  THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS idle_pct
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date >= DATE_SUB(CURRENT_DATE(), 30)
GROUP BY analysis_date
ORDER BY analysis_date DESC;
```

### 8.2 사용자별 상세 조회

```sql
-- 특정 사용자의 최근 세션별 판정 현황
SELECT
  s.analysis_date,
  s.user_id,
  s.session_id,
  s.task_id,
  s.light_gap_count,
  s.heavy_gap_count,
  s.idle_gap_count,
  s.focus_drop_level
FROM analytics.focus_drop_session_tags s
WHERE s.user_id = ${target_user_id}
  AND s.analysis_date >= DATE_SUB(CURRENT_DATE(), 7)
ORDER BY s.analysis_date DESC, s.session_id;
```

### 8.3 추세 모니터링

```sql
-- 주간 추세: 배타적 레벨(user_focus_drop_level) 기준 사용자 비율 변화
SELECT
  DATE_TRUNC('week', analysis_date) AS week_start,
  COUNT(DISTINCT user_id) AS total_labelers,
  COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'light' THEN user_id END) AS light_users,
  COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'heavy' THEN user_id END) AS heavy_users,
  COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'idle'  THEN user_id END) AS idle_users,
  ROUND(COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'light' THEN user_id END) / COUNT(DISTINCT user_id) * 100, 1) AS light_pct,
  ROUND(COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'heavy' THEN user_id END) / COUNT(DISTINCT user_id) * 100, 1) AS heavy_pct,
  ROUND(COUNT(DISTINCT CASE WHEN user_focus_drop_level = 'idle'  THEN user_id END) / COUNT(DISTINCT user_id) * 100, 1) AS idle_pct
FROM analytics.focus_drop_user_day_kpi
WHERE analysis_date >= DATE_SUB(CURRENT_DATE(), 90)
GROUP BY DATE_TRUNC('week', analysis_date)
ORDER BY week_start DESC;
```

---

## 9. 알림 기준

### 9.1 알림 레벨

| 레벨 | 조건 | 행동 |
|------|------|------|
| **INFO** | 당일 `user_focus_drop_level = 'light'` 존재 | 일일 리포트에 포함 |
| **WARNING** | `user_focus_drop_level = 'heavy'` 1명 이상 | 팀 리드 Slack 알림 |
| **CRITICAL** | `user_focus_drop_level = 'idle'` 존재 | 즉시 검토 요청 |
| **DRIFT** | `gap_p90/p95` 기존 대비 ±20% 변동 | percentile 재산출 트리거 |

> 배타적 레벨 적용으로, 한 유저에게 중복 알림이 발생하지 않는다.

**DRIFT 대응 SOP** (`drift_status = 'RECALCULATE'` 감지 시):

1. **담당자**: 데이터 엔지니어 (파이프라인 소유자)
2. **확인**: §9.2 드리프트 쿼리 수동 실행 → 원인 파악 (온보딩? UX 변경? 계절성?)
3. **실행**: 정상적 분포 변화로 판단되면 `gap_percentiles` 수동 재실행 → 신규 gap_thresholds INSERT
4. **후속**: `session_thresholds` / `user_thresholds`를 다음 주 배치 전에 임시 재실행하여 2차 기준선도 갱신
5. **기록**: §13 버전업 원칙에 따라 변경 사유 기록

> §9.2의 7일 윈도우는 **급격한 분포 변화의 조기 경보**를 목적으로 한다. 완만한 drift(4~5주)는 session_thresholds / user_thresholds의 주간 rolling 갱신 + 분기 정기 검토가 커버한다.

### 9.2 기준선 드리프트 감지

```sql
-- 현재 분포 vs 기준 비교 (최근 7일 — 급격한 shift 조기 경보용; 완만한 drift는 session/user_thresholds rolling이 커버)
-- ★ §7.1과 동일한 CDC dedup + KST 변환 구조
WITH latest_assignments AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_assignments`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
latest_tasks AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__gen2_tasks`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
latest_commands AS (
  SELECT `_id`, `_raw`
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY `_id` ORDER BY `_ingested_at` DESC) AS rn
    FROM `sv_nova_dev_an2_catalog`.`raw`.`raw_labelit__workspace_command`
    WHERE `_is_deleted` = false
  ) WHERE rn = 1
),
recent_labeler_diffs AS (
  SELECT
    UNIX_TIMESTAMP(c.`_raw`:createdAt::TIMESTAMP) - UNIX_TIMESTAMP(
      LAG(c.`_raw`:createdAt::TIMESTAMP) OVER (
        PARTITION BY c.`_raw`:userId::STRING, c.`_raw`:sessionId::STRING, c.`_raw`:taskId::STRING
        ORDER BY c.`_raw`:createdAt::TIMESTAMP
      )
    ) AS diff_sec
  FROM latest_commands c
  INNER JOIN latest_tasks       t ON c.`_raw`:taskId::STRING = t.`_id`
  INNER JOIN latest_assignments a ON t.`_raw`:assignmentId::STRING = a.`_id`
  WHERE LOWER(a.`_raw`:role::STRING) = 'labeler'
    AND CAST(
      CONVERT_TIMEZONE('UTC', 'Asia/Seoul', c.`_raw`:createdAt::TIMESTAMP) AS DATE
    ) >= DATE_SUB(CURRENT_DATE(), 7)
),
current_dist AS (
  SELECT
    PERCENTILE(diff_sec, 0.90) AS current_p90,
    PERCENTILE(diff_sec, 0.95) AS current_p95,
    PERCENTILE(diff_sec, 0.99) AS current_p99
  FROM recent_labeler_diffs
  WHERE diff_sec IS NOT NULL AND diff_sec > 0
),
baseline AS (
  SELECT gap_p90, gap_p95, gap_p99
  FROM analytics.focus_drop_gap_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_gap_thresholds)
)
SELECT
  ABS(c.current_p90 - b.gap_p90) / b.gap_p90 * 100 AS drift_p90_pct,
  ABS(c.current_p95 - b.gap_p95) / b.gap_p95 * 100 AS drift_p95_pct,
  ABS(c.current_p99 - b.gap_p99) / b.gap_p99 * 100 AS drift_p99_pct,
  CASE WHEN ABS(c.current_p90 - b.gap_p90) / b.gap_p90 > 0.20
         OR ABS(c.current_p95 - b.gap_p95) / b.gap_p95 > 0.20
         OR ABS(c.current_p99 - b.gap_p99) / b.gap_p99 > 0.20
       THEN 'RECALCULATE' ELSE 'STABLE' END AS drift_status
FROM current_dist c CROSS JOIN baseline b;
```

---

---

## 11. 파라미터 관리

### 11.1 튜닝 가능 파라미터

| 파라미터 | 현재값 | 설명 |
|----------|--------|------|
| `min_event_count` | 10 | 세션 최소 이벤트 수 |
| `min_session_duration_sec` | 60 | 세션 최소 지속 시간 |
| `min_gap_count` | 5 | 분석 최소 gap 수 |
| `idle_threshold_sec` | 180 | idle 고정 임계값(초) |
| `drift_threshold_pct` | 20 | 기준선 드리프트 알림 임계(%) |
| `feature_scope` | `all_features` | 기준 산출 범위 (feature별 분리 시 변경) |
| `rolling_window_days` | 30 | 세션/유저 기준선 산출 rolling 윈도우 |
| `role_scope` | `labeler_only` | 기본 KPI 모드. 확장 시 `reviewer_only`, `all_roles` 가능 (§16) |

### 11.2 feature별 분리 판단 기준

- feature 간 `gap_p90` 차이가 ±30% 이상 → 분리 산출
- `task._raw:policyId` → `annotation_policy._raw:feature` 조인으로 식별

---

## 12. 트러블슈팅

### 12.1 zero-inflation 문제

**증상**: `session_*_count_p90/p95/p99 = 0` → 해당 레벨의 gap이 1개만 있어도 전부 판정됨

> 예: `session_idle_count_p99 = 0`인 경우, `idle_gap_count > 0 AND > 0` = TRUE → idle gap 1개만으로 idle 세션 판정. Bootstrap 초기(7일 데이터) 또는 idle gap이 매우 드문 정상 구간에서 발생.

**해결** (light / heavy / idle 공통):
1. `min_gap_count` 파라미터 상향 (5 → 10)으로 짧은 세션 제거
2. `해당_gap_count > 0` 최소 조건은 이미 적용됨 (§7.4)
3. rolling window 기간 확대하여 기준선 재산출
4. **bootstrap 시 보수적 최솟값 적용**: `session_idle_count_p99 = 0`이면 최솟값 1로 대체

```sql
-- session_thresholds 실행 후 zero-inflation 보정 (선택적 후처리)
UPDATE analytics.focus_drop_session_thresholds
SET session_idle_count_p99  = GREATEST(session_idle_count_p99, 1),
    session_heavy_count_p95 = GREATEST(session_heavy_count_p95, 1),
    session_light_count_p90 = GREATEST(session_light_count_p90, 1)
WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds)
  AND (session_idle_count_p99 = 0 OR session_heavy_count_p95 = 0 OR session_light_count_p90 = 0);
```

> 이 보정은 "threshold = 0이면 최솟값 1로 올린다"는 단순 규칙으로, `gap_count > 0 AND gap_count > 1` = `gap_count >= 2`가 되어 단일 gap 오탐을 방지한다.

### 12.2 오탐률 과다

**증상**: light 판정 비율이 30% 이상

**해결**:
1. Labeler role 필터 정확성 확인 (gen2_assignments 조인 검증)
2. `gap_p90` 기준값이 너무 낮은지 확인 (2초 이하이면 비정상)
3. 특정 company/project의 UX 특성이 gap 분포를 왜곡하는지 확인

### 12.3 기준값 급변

**증상**: 신규 산출 percentile이 기존 대비 50% 이상 변동

**원인 후보**:
1. 신규 대량 Labeler 온보딩 (미숙련 패턴 유입)
2. 툴 UX 변경 (새 기능 추가로 gap 패턴 변화)
3. policy 변경으로 작업 방식 변화

### 12.4 기준선 테이블 부재 (초기 배포 시)

**증상**: `focus_drop_session_thresholds` 또는 `focus_drop_user_thresholds`에 데이터 없음 → session_tags / user_day_kpi 노트북 실행 시 CROSS JOIN 결과가 빈 행

**근본 원인**: 파이프라인 의존성 순환 구조

```
gap_percentiles    ← workspace_command 90일분 + 표본 10,000 gap 필요
session_thresholds ← session_metrics 30일분 필요
user_thresholds    ← user_day_kpi 30일분 필요
session_tags       ← session_thresholds + gap_percentiles 필요
user_day_kpi       ← user_thresholds 필요  ← 자기 자신 30일분 필요 (순환)
```

**단계적 해결 — 4 Phase 초기 배포**:

#### Phase 0: 인프라 준비 (Day 0)

테이블이 존재하지 않는 상태에서 시작한다.

1. **DDL 적용**: `.sql/focus_drop__ddl.sql` 실행 → 7개 Delta 테이블 생성
   - `focus_drop_gap_thresholds`, `focus_drop_session_thresholds`, `focus_drop_user_thresholds`
   - `focus_drop_session_metrics`, `focus_drop_task_idle_rollup`, `focus_drop_session_tags`, `focus_drop_user_day_kpi`
2. **존재 확인 쿼리**:
   ```sql
   SHOW TABLES IN analytics LIKE 'focus_drop_*';
   ```
3. **gap_percentiles 1회 실행 시도**: 표본 부족 시 `HAVING COUNT(*) >= 10000` 가드로 0행 INSERT → Phase A에서 재시도

#### Phase A: Warm-up (Day 1~6)

- **실행**: `session_metrics` → `task_idle_rollup` 일 단위 배치 (gap_percentiles는 표본 누적 후 별도 트리거)
- **gap_percentiles**: workspace_command 누적 표본이 10,000 gap 이상 도달하면 수동 실행 → `focus_drop_gap_thresholds` 첫 버전 생성
  - 표본 부족 상태에서 session_metrics는 `thresholds` CTE가 0행 → CROSS JOIN 결과 0행 → 적재 스킵 (silent skip)
  - Phase A 진입 전제: gap_percentiles 1행 이상 적재 확인
- **session_tags / user_day_kpi**: 실행하지 않음 (2차 기준선 미생성)
- **최소 요건**: Labeler 유효 세션 100개 이상 축적 확인

#### Phase B: Bootstrap (Day 7)

- **조건**: session_metrics에 최소 7일분 데이터 적재 + gap_percentiles 1행 이상 존재 확인
- **실행 순서** (순환 의존성 해소):
  1. `session_thresholds`를 `rolling_window_days = 7`로 임시 실행 (`is_bootstrap = TRUE`) → 세션 기준선 생성
  2. zero-inflation 보정 SQL 실행 (§12.1) → `session_idle_count_p99 = 0` 등을 최솟값 1로 대체
  3. `task_idle_rollup`을 7일 소급 실행 → 생산성 연계 데이터 준비
  4. `session_tags`를 7일 소급 실행 (session_thresholds 기준선 참조) → session_tags 생성
  5. **`user_thresholds`를 임시 기준값으로 수동 INSERT** → 유저 기준선 부트스트랩 (★ user_day_kpi보다 먼저)
     ```sql
     INSERT INTO analytics.focus_drop_user_thresholds VALUES (
       1, CURRENT_TIMESTAMP(), TRUE,
       DATE_SUB(CURRENT_DATE(), 7), DATE_SUB(CURRENT_DATE(), 1),
       1.0, 1.0, 3.0
       -- 근거: threshold=1 → count>1 필요 → light/heavy 세션 2회 이상,
       --       idle gap 4개 이상이어야 판정. 과탐지 방지 우선, Phase C에서 실데이터 대체.
     );
     ```
  6. `user_day_kpi`를 7일 소급 실행 (user_thresholds 부트스트랩 기준선 참조) → user_day_kpi 생성
  7. 이후 일 배치 Job(`focus_drop_daily`)을 steady-state 구성으로 활성화
- **주의**: Bootstrap 기준선은 `is_bootstrap = TRUE`로 마킹하여 정식 기준선과 구분

#### Phase C: Steady-state (Day 30+)

- **전환 조건**: session_metrics 30일분 + user_day_kpi 30일분 축적
- **실행**: `session_thresholds` / `user_thresholds`를 정식 30일 rolling window로 재실행 → Bootstrap 기준선 대체 (`is_bootstrap = FALSE` 신규 버전)
- **gap_percentiles**: workspace_command 90일분 누적 시점에서 정식 분기 스케줄(§6.4 Quarterly Job)로 편입
- **이후**: 정상 스케줄 (`session_thresholds` / `user_thresholds` 주 1회, `session_metrics` / `task_idle_rollup` / `session_tags` / `user_day_kpi` 일 1회) 전환

**폴백 동작 (session_tags / user_day_kpi)**:

```sql
-- session_tags / user_day_kpi에서 기준선 테이블이 비어있을 때의 방어 로직
WITH thresholds AS (
  SELECT session_light_count_p90, session_heavy_count_p95, session_idle_count_p99
  FROM analytics.focus_drop_session_thresholds
  WHERE version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds)
)
-- thresholds CTE가 0행이면 CROSS JOIN 결과도 0행 → 판정 자체가 생략됨
-- 이 경우 session_tags 테이블에 당일 데이터가 적재되지 않으므로 알림 미발생 (safe fail)
-- ★ Silent failure 방지: 아래 모니터링 쿼리를 일 배치 마지막에 실행
```

**Bootstrap silent failure 감지 쿼리** (일 배치 마지막에 실행):

```sql
-- 기준선 부재로 인한 0행 적재 감지 → 운영자 알림 트리거
SELECT
  CASE
    WHEN (SELECT COUNT(*) FROM analytics.focus_drop_session_tags WHERE analysis_date = ${analysis_date}) = 0
     AND (SELECT COUNT(*) FROM analytics.focus_drop_session_metrics WHERE analysis_date = ${analysis_date}) > 0
    THEN 'ALERT: session_tags 0행 — 기준선 테이블(session_thresholds) 비어있음'
    WHEN (SELECT COUNT(*) FROM analytics.focus_drop_user_day_kpi WHERE analysis_date = ${analysis_date}) = 0
     AND (SELECT COUNT(*) FROM analytics.focus_drop_session_tags WHERE analysis_date = ${analysis_date}) > 0
    THEN 'ALERT: user_day_kpi 0행 — 기준선 테이블(user_thresholds) 비어있음'
    ELSE 'OK'
  END AS pipeline_health_status;
```

**Bootstrap 최소 요건 체크 쿼리**:

```sql
-- Phase B 진입 가능 여부 확인
SELECT
  COUNT(DISTINCT analysis_date) AS available_days,
  COUNT(*) AS total_sessions,
  CASE WHEN COUNT(DISTINCT analysis_date) >= 7 AND COUNT(*) >= 100
       THEN 'READY_FOR_BOOTSTRAP' ELSE 'WAIT' END AS bootstrap_status
FROM analytics.focus_drop_session_metrics;
```

### 12.5 Idle Bootstrap 거동 — Phase B 민감도 관리

Phase B(7일 데이터) 기준선에서 idle 관련 threshold는 구조적으로 민감도가 높아진다.

#### Phase B 상황

| threshold | 7일 데이터 예상값 | zero-inflation 보정 후 | 실제 판정 조건 |
|-----------|--------------|---------------------|--------------|
| `session_idle_count_p99` | 0 (idle 이벤트 희귀) | 1 | `idle_gap_count >= 2` → is_idle_session |
| `user_idle_gap_total_p99` | 수동 3.0 (Bootstrap INSERT) | — | `idle_gap_total >= 4` → is_idle_user |

**`user_idle_gap_total_p99 = 3.0` 근거**: 하루 전체 세션에서 idle gap 누적이 4회 이상인 사용자만 `is_idle_user = TRUE`로 판정하여 초기 과탐지를 억제. 이 값은 Phase C(30일 데이터 축적 후) `user_thresholds` 재산출 시 실데이터 기반으로 자동 대체된다.

#### Phase B 기간 운영 지침

1. **출력 마킹**: `is_bootstrap = TRUE`인 기간(session_thresholds, user_thresholds 버전 확인)의 session_tags / user_day_kpi 집계는 리포팅에서 별도 구분
2. **idle 세션 비율 수동 모니터링**: Phase B에서 idle 세션 비율이 5% 초과 시 threshold 재검토 신호
3. **`session_idle_count_p99 = 1` 상태 허용**: 단일 idle gap 오탐이 우려되면 `session_thresholds`에서 최솟값을 1 → 2로 수동 조정 가능 (zero-inflation 보정 SQL의 `GREATEST(..., 1)` → `GREATEST(..., 2)`)
4. **Phase C 전환 확인 쿼리**:

```sql
-- idle threshold가 실데이터 기반으로 갱신되었는지 확인
SELECT version, is_bootstrap, window_start, window_end,
       session_idle_count_p99, user_idle_gap_total_p99
FROM analytics.focus_drop_session_thresholds st
JOIN analytics.focus_drop_user_thresholds ut ON ut.version = (
  SELECT MAX(version) FROM analytics.focus_drop_user_thresholds WHERE is_bootstrap = FALSE
)
WHERE st.version = (SELECT MAX(version) FROM analytics.focus_drop_session_thresholds WHERE is_bootstrap = FALSE);
```

#### gap_p99 와 idle 180s 임계값 공존 원칙

`gap_p99`는 분류 경계가 아닌 **임계값 안전 마진 모니터링 지표**로 유지한다.

- `gap_p99` 산출 범위: `diff_sec < 180` 모집단 → "idle 제외 작업 리듬의 통계적 상한"
- 해석: `(180 - gap_p99)` = idle 고정 임계값과 정상 작업 분포 사이의 마진
- Phase B~C에서 gap_p99가 지속적으로 상승하면 180s 임계값 재협의 신호

```sql
-- 분기별 gap_p99 추이 — 안전 마진 모니터링
SELECT version, computed_at, gap_p95, gap_p99,
       ROUND(180 - gap_p99, 1) AS idle_safety_margin_sec
FROM analytics.focus_drop_gap_thresholds
ORDER BY version DESC
LIMIT 4;
```

---

## 13. 버전업 원칙

다음 조건 중 하나 이상 확인 시 기준 재검토 및 percentile 재산출:

- Labeler 표본이 기존 대비 50% 이상 증가
- 툴 UX 또는 작업 방식 변경
- `drift_status = 'RECALCULATE'` 연속 2주 감지
- 특정 feature에서 오탐/미탐 반복 보고
- 분기 정기 검토 시점
- 생산성 연계 시 `task_total_idle_sec / gross_task_sec` 분포가 급격히 변동

---

---

### 15.5 초기 배포 단계별 진입 확인 쿼리

Phase 0 → A → B → C 전환 시 다음 SELECT 묶음으로 다음 단계 진입 가능 여부를 미리 검증한다. 모든 쿼리는 read-only이며 실행 결과로 OK/PENDING을 판정한다.

#### Phase 0 → Phase A (DDL 적재 완료 확인)

```sql
-- 7개 focus_drop 테이블 존재 여부
SHOW TABLES IN analytics LIKE 'focus_drop_*';
-- 기대: 7행 (gap_thresholds, session_metrics, session_thresholds, session_tags,
--        user_thresholds, user_day_kpi, task_idle_rollup)

-- 각 테이블 빈 상태 확인 (Phase 0 직후엔 모두 0행이어야 정상)
SELECT 'gap_thresholds'   AS tbl, COUNT(*) AS rows FROM analytics.focus_drop_gap_thresholds
UNION ALL SELECT 'session_metrics',   COUNT(*) FROM analytics.focus_drop_session_metrics
UNION ALL SELECT 'session_thresholds',COUNT(*) FROM analytics.focus_drop_session_thresholds
UNION ALL SELECT 'session_tags',      COUNT(*) FROM analytics.focus_drop_session_tags
UNION ALL SELECT 'user_thresholds',   COUNT(*) FROM analytics.focus_drop_user_thresholds
UNION ALL SELECT 'user_day_kpi',      COUNT(*) FROM analytics.focus_drop_user_day_kpi
UNION ALL SELECT 'task_idle_rollup',  COUNT(*) FROM analytics.focus_drop_task_idle_rollup;
```

#### Phase A → Phase B (gap_percentiles + session_metrics 누적 충분)

```sql
-- gap_thresholds 최신 버전 존재 확인
SELECT version, gap_p75, gap_p90, gap_p95, sample_size, computed_at
FROM analytics.focus_drop_gap_thresholds
ORDER BY version DESC
LIMIT 1;
-- 기대: 1행, sample_size > 10000 권장

-- session_metrics 7일+ 누적 + 세션 100개 이상 (Bootstrap 기준)
SELECT
  COUNT(DISTINCT analysis_date)              AS days_loaded,
  COUNT(*)                                   AS total_sessions,
  COUNT(DISTINCT user_id)                    AS distinct_users,
  MIN(analysis_date)                         AS first_date,
  MAX(analysis_date)                         AS last_date
FROM analytics.focus_drop_session_metrics;
-- Phase B 진입 기준: days_loaded >= 7 AND total_sessions >= 100
```

#### Phase B → Phase C (기준선 부트스트랩 + 7일 KPI 적재)

```sql
-- session_thresholds 부트스트랩 버전 존재
SELECT version, role_scope, role_group, rolling_window_days, is_bootstrap, computed_at
FROM analytics.focus_drop_session_thresholds
WHERE is_bootstrap = TRUE
ORDER BY version DESC;
-- 기대: 1행 이상 (Phase B step 1 결과)

-- user_thresholds 부트스트랩 INSERT 확인
SELECT version, role_scope, role_group, rolling_window_days, is_bootstrap, computed_at
FROM analytics.focus_drop_user_thresholds
WHERE is_bootstrap = TRUE
ORDER BY version DESC;
-- 기대: 1행 이상 (Phase B step 5 수동 INSERT 결과)

-- session_tags + user_day_kpi 7일 적재 확인
SELECT 'session_tags' AS tbl, COUNT(DISTINCT analysis_date) AS days, COUNT(*) AS rows
FROM analytics.focus_drop_session_tags
UNION ALL
SELECT 'user_day_kpi', COUNT(DISTINCT analysis_date), COUNT(*)
FROM analytics.focus_drop_user_day_kpi;
-- Phase C 진입 기준: 두 테이블 모두 days >= 7
```

#### Phase C → 정상 운영 (30일 누적 + is_bootstrap=FALSE 신규 버전)

```sql
-- session_metrics 30일 누적 확인
SELECT
  COUNT(DISTINCT analysis_date) AS days_loaded,
  MIN(analysis_date)            AS first_date,
  MAX(analysis_date)            AS last_date
FROM analytics.focus_drop_session_metrics;
-- 기대: days_loaded >= 30

-- session_thresholds + user_thresholds is_bootstrap=FALSE 신규 버전 존재
SELECT 'session_thresholds' AS tbl, MAX(version) AS latest_version,
       MAX(CASE WHEN is_bootstrap = FALSE THEN version END) AS latest_steady_version
FROM analytics.focus_drop_session_thresholds
UNION ALL
SELECT 'user_thresholds', MAX(version),
       MAX(CASE WHEN is_bootstrap = FALSE THEN version END)
FROM analytics.focus_drop_user_thresholds;
-- 기대: 두 테이블 모두 latest_steady_version IS NOT NULL
```

---
