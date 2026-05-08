# Databricks notebook source
# DBTITLE 1,OD bbox3d 이상 탐지 분석 템플릿
# MAGIC %md
# MAGIC # OD (Object Detection) 이상 탐지 분석 템플릿
# MAGIC > 전체 셀을 순서대로 실행하세요. 데이터 준비 셀이 temp view `bbox3d_events`를 생성한 후, 각 STEP이 이를 참조합니다.
# MAGIC
# MAGIC ### 워크플로우 구조
# MAGIC ```
# MAGIC Stage 1 — 수집 데이터 무결성 검증
# MAGIC ├── [Group A] STEP 0 → STEP 3  (Raw 직접, 파싱 불필요)
# MAGIC └── [Group B] STEP 1 → STEP 2 → STEP 4  (인라인 파싱)
# MAGIC
# MAGIC Stage 2 — 가공 데이터 기반 행동 이상 탐지
# MAGIC ├── STEP 5: 복수 사용자 (템플릿 포함)
# MAGIC └── STEP 6~9: runner 노트북에서 통합 실행
# MAGIC ```

# COMMAND ----------

# DBTITLE 1,데이터 준비: bbox3d_events temp view
# MAGIC %sql
# MAGIC -- 데이터 준비: raw 테이블에서 bbox3d 이벤트를 파싱하여 temp view 생성
# MAGIC CREATE OR REPLACE TEMP VIEW bbox3d_events AS
# MAGIC WITH raw_parsed AS (
# MAGIC   SELECT
# MAGIC     e._id                                         AS event_id,
# MAGIC     e._raw:source::STRING                         AS event_source,
# MAGIC     e._raw:type::STRING                           AS event_type,
# MAGIC     to_timestamp(e._raw:time::STRING)             AS event_time,
# MAGIC     DATE(to_timestamp(e._raw:time::STRING))       AS event_date,
# MAGIC     e._raw:sessionid::STRING                      AS session_id,
# MAGIC     to_timestamp(e._occurred_at)                  AS occurred_at,
# MAGIC     e._raw:data.user.id::STRING                   AS user_id,
# MAGIC     e._raw:data.user.name::STRING                 AS user_name,
# MAGIC     e._raw:data.project.dataset_id::STRING        AS dataset_id,
# MAGIC     e._raw:data.project.task_id::STRING           AS task_id,
# MAGIC     e._raw:data.feature::STRING                   AS feature,
# MAGIC     e._raw:data.action::STRING                    AS action,
# MAGIC     e._raw:data.input_type::STRING                AS input_type,
# MAGIC     from_json(
# MAGIC       e._raw:data.changes::STRING,
# MAGIC       'ARRAY<STRUCT<
# MAGIC         object_id:   INT,
# MAGIC         object_type: STRING,
# MAGIC         action:      STRING,
# MAGIC         old:         STRING,
# MAGIC         new:         STRING
# MAGIC       >>'
# MAGIC     ) AS changes,
# MAGIC     from_json(
# MAGIC       e._raw:data.targets::STRING,
# MAGIC       'ARRAY<STRING>'
# MAGIC     ) AS targets
# MAGIC   FROM sv_nova_dev_an2_catalog.raw.raw_labelit__workspace_command e
# MAGIC   WHERE e._raw:type::STRING NOT IN ('history.undo', 'history.redo')
# MAGIC     AND e._raw:data.changes IS NOT NULL
# MAGIC     AND e._raw:data.changes != '[]'
# MAGIC     AND e._raw:data.feature::STRING = 'od'
# MAGIC )
# MAGIC SELECT
# MAGIC   event_id, event_source, event_type, event_time, event_date,
# MAGIC   session_id, occurred_at, user_id, user_name, dataset_id, task_id,
# MAGIC   feature, action, input_type,
# MAGIC   c.object_id, c.object_type, c.action AS change_action,
# MAGIC   c.old AS old_val, c.new AS new_val, targets
# MAGIC FROM raw_parsed
# MAGIC LATERAL VIEW EXPLODE(changes) AS c

# COMMAND ----------

# MAGIC %md
# MAGIC ## ═══ Stage 1 — Group A: 수집 무결성 검증 (Raw 직접 접근, 파싱 불필요) ═══
# MAGIC > event_time, occurred_at 등 Raw 컬럼만으로 검증 가능한 항목

# COMMAND ----------

# DBTITLE 1,[S1-A] STEP 0: 이벤트 요약 통계
# MAGIC %sql
# MAGIC -- [Stage 1 · Group A] STEP 0: 이벤트 요약 통계
# MAGIC SELECT event_type, COUNT(*) AS event_count,
# MAGIC        COUNT(DISTINCT session_id) AS session_count,
# MAGIC        COUNT(DISTINCT user_id) AS user_count,
# MAGIC        COUNT(DISTINCT object_id) AS object_count
# MAGIC FROM bbox3d_events
# MAGIC GROUP BY event_type
# MAGIC ORDER BY event_count DESC

# COMMAND ----------

# DBTITLE 1,[S1-A] STEP 3: 타임스탬프 지연
# MAGIC %sql
# MAGIC -- [Stage 1 · Group A] STEP 3: 타임스탬프 지연 (> 30s ⚠️ / > 60s·음수 ❌)
# MAGIC SELECT CASE WHEN TIMESTAMPDIFF(SECOND, event_time, occurred_at) < 0 THEN 'negative (critical)'
# MAGIC             WHEN TIMESTAMPDIFF(SECOND, event_time, occurred_at) > 60 THEN '>60s (critical)'
# MAGIC             WHEN TIMESTAMPDIFF(SECOND, event_time, occurred_at) > 30 THEN '30-60s (warning)'
# MAGIC             ELSE 'normal' END AS severity,
# MAGIC        COUNT(*) AS event_count,
# MAGIC        ROUND(AVG(TIMESTAMPDIFF(SECOND, event_time, occurred_at)), 2) AS avg_diff_seconds,
# MAGIC        MIN(TIMESTAMPDIFF(SECOND, event_time, occurred_at)) AS min_diff,
# MAGIC        MAX(TIMESTAMPDIFF(SECOND, event_time, occurred_at)) AS max_diff
# MAGIC FROM bbox3d_events
# MAGIC GROUP BY severity
# MAGIC ORDER BY severity

# COMMAND ----------

# MAGIC %md
# MAGIC ## ═══ Stage 1 — Group B: 수집 무결성 검증 (인라인 파싱 필요) ═══
# MAGIC > position, rotation 등 JSON 파싱이 필요한 항목. Staging 테이블 안정화 시 참조 교체 가능.

# COMMAND ----------

# DBTITLE 1,[S1-B] STEP 1: 위치 점프
# MAGIC %sql
# MAGIC -- [Stage 1 · Group B] STEP 1: 위치 점프 (이동거리 > 5.0m ⚠️ / > 15.0m ❌)
# MAGIC WITH movements AS (
# MAGIC   SELECT session_id, object_id, event_time,
# MAGIC          get_json_object(old_val, '$.position.x') AS old_x,
# MAGIC          get_json_object(old_val, '$.position.y') AS old_y,
# MAGIC          get_json_object(old_val, '$.position.z') AS old_z,
# MAGIC          get_json_object(new_val, '$.position.x') AS new_x,
# MAGIC          get_json_object(new_val, '$.position.y') AS new_y,
# MAGIC          get_json_object(new_val, '$.position.z') AS new_z
# MAGIC   FROM bbox3d_events
# MAGIC   WHERE event_type = 'annotation.bbox3d.transform'
# MAGIC     AND old_val IS NOT NULL AND new_val IS NOT NULL
# MAGIC ),
# MAGIC distances AS (
# MAGIC   SELECT session_id, object_id,
# MAGIC          SQRT(POW(CAST(new_x AS DOUBLE) - CAST(old_x AS DOUBLE), 2) +
# MAGIC               POW(CAST(new_y AS DOUBLE) - CAST(old_y AS DOUBLE), 2) +
# MAGIC               POW(CAST(new_z AS DOUBLE) - CAST(old_z AS DOUBLE), 2)) AS distance
# MAGIC   FROM movements
# MAGIC )
# MAGIC SELECT CASE WHEN distance > 15.0 THEN '>15.0m (critical)'
# MAGIC             WHEN distance > 5.0 THEN '5.0-15.0m (warning)'
# MAGIC             ELSE 'normal' END AS severity,
# MAGIC        COUNT(*) AS event_count,
# MAGIC        ROUND(AVG(distance), 4) AS avg_distance,
# MAGIC        ROUND(MAX(distance), 4) AS max_distance
# MAGIC FROM distances
# MAGIC GROUP BY severity

# COMMAND ----------

# DBTITLE 1,[S1-B] STEP 2: 위치·회전 진동
# MAGIC %sql
# MAGIC -- [Stage 1 · Group B] STEP 2: 위치·회전 진동 (reversal 비율 기준, 이동거리 0.05m 이상만 카운트)
# MAGIC -- OD: min_dist 0.05m 필터 적용 후 비율 ≥ 75%일 때 이상으로 판정
# MAGIC WITH ordered AS (
# MAGIC   SELECT session_id, task_id, object_id, event_time,
# MAGIC          CAST(get_json_object(new_val, '$.position.x') AS DOUBLE) AS x,
# MAGIC          CAST(get_json_object(new_val, '$.position.y') AS DOUBLE) AS y,
# MAGIC          CAST(get_json_object(new_val, '$.position.z') AS DOUBLE) AS z,
# MAGIC          ROW_NUMBER() OVER (PARTITION BY session_id, task_id, object_id ORDER BY event_time) AS rn
# MAGIC   FROM bbox3d_events
# MAGIC   WHERE event_type = 'annotation.bbox3d.transform'
# MAGIC     AND new_val IS NOT NULL
# MAGIC ),
# MAGIC deltas AS (
# MAGIC   SELECT a.session_id, a.task_id, a.object_id, a.rn,
# MAGIC          (b.x - a.x) AS dx, (b.y - a.y) AS dy, (b.z - a.z) AS dz,
# MAGIC          SQRT(POW(b.x - a.x, 2) + POW(b.y - a.y, 2) + POW(b.z - a.z, 2)) AS move_dist
# MAGIC   FROM ordered a
# MAGIC   JOIN ordered b ON a.session_id = b.session_id AND a.task_id = b.task_id
# MAGIC                 AND a.object_id = b.object_id AND b.rn = a.rn + 1
# MAGIC ),
# MAGIC significant_deltas AS (
# MAGIC   SELECT *, ROW_NUMBER() OVER (PARTITION BY session_id, task_id, object_id ORDER BY rn) AS sig_rn
# MAGIC   FROM deltas
# MAGIC   WHERE move_dist >= 0.05
# MAGIC ),
# MAGIC direction_changes AS (
# MAGIC   SELECT a.session_id, a.task_id, a.object_id, a.sig_rn,
# MAGIC          CASE WHEN SIGN(a.dx) != SIGN(b.dx) OR SIGN(a.dy) != SIGN(b.dy) OR SIGN(a.dz) != SIGN(b.dz) THEN 1 ELSE 0 END AS is_reversal
# MAGIC   FROM significant_deltas a
# MAGIC   JOIN significant_deltas b ON a.session_id = b.session_id AND a.task_id = b.task_id
# MAGIC               AND a.object_id = b.object_id AND b.sig_rn = a.sig_rn + 1
# MAGIC ),
# MAGIC windowed AS (
# MAGIC   SELECT session_id, task_id, object_id, sig_rn,
# MAGIC          SUM(is_reversal) OVER (PARTITION BY session_id, task_id, object_id ORDER BY sig_rn ROWS BETWEEN 5 PRECEDING AND CURRENT ROW) AS reversals_in_window,
# MAGIC          COUNT(*) OVER (PARTITION BY session_id, task_id, object_id ORDER BY sig_rn ROWS BETWEEN 5 PRECEDING AND CURRENT ROW) AS window_size
# MAGIC   FROM direction_changes
# MAGIC ),
# MAGIC with_ratio AS (
# MAGIC   SELECT *,
# MAGIC          ROUND(reversals_in_window / window_size, 2) AS reversal_ratio
# MAGIC   FROM windowed
# MAGIC   WHERE window_size >= 4
# MAGIC )
# MAGIC SELECT session_id                          AS `세션ID`,
# MAGIC        task_id                             AS `태스크ID`,
# MAGIC        object_id                           AS `객체ID`,
# MAGIC        MAX(reversal_ratio)                 AS `최대_반전비율`,
# MAGIC        MAX(reversals_in_window)            AS `최대_반전횟수`,
# MAGIC        COUNT(*)                            AS `이벤트수`,
# MAGIC        CASE WHEN COUNT(*) >= 10 AND MAX(reversal_ratio) >= 0.75 THEN '심각'
# MAGIC             WHEN MAX(reversal_ratio) >= 0.75 THEN '주의'
# MAGIC             ELSE '정상' END              AS `심각도`
# MAGIC FROM with_ratio
# MAGIC GROUP BY session_id, task_id, object_id
# MAGIC HAVING MAX(reversal_ratio) >= 0.75
# MAGIC ORDER BY `최대_반전비율` DESC, `최대_반전횟수` DESC

# COMMAND ----------

# DBTITLE 1,[S1-B] STEP 4: yaw 드리프트
# MAGIC %sql
# MAGIC -- [Stage 1 · Group B] STEP 4: yaw 드리프트 (|yaw| < 1E-6 누적증가 ⚠️, E-10 미만은 FP 노이즈)
# MAGIC WITH yaw_vals AS (
# MAGIC   SELECT session_id, object_id, event_time,
# MAGIC          CAST(get_json_object(new_val, '$.rotation.yaw') AS DOUBLE) AS yaw
# MAGIC   FROM bbox3d_events
# MAGIC   WHERE event_type = 'annotation.bbox3d.transform'
# MAGIC     AND new_val IS NOT NULL
# MAGIC )
# MAGIC SELECT session_id, object_id,
# MAGIC        MIN(ABS(yaw)) AS min_abs_yaw,
# MAGIC        MAX(ABS(yaw)) AS max_abs_yaw,
# MAGIC        COUNT(*) AS event_count
# MAGIC FROM yaw_vals
# MAGIC WHERE ABS(yaw) < 1E-6 AND ABS(yaw) > 0
# MAGIC GROUP BY session_id, object_id
# MAGIC HAVING MAX(ABS(yaw)) > 1E-10
# MAGIC ORDER BY max_abs_yaw DESC

# COMMAND ----------

# MAGIC %md
# MAGIC ## ═══ Stage 2 — 가공 데이터 기반 행동 이상 탐지 ═══
# MAGIC > 핵심 질문: "이 라벨러/세션의 작업 패턴이 비정상인가?"
# MAGIC >
# MAGIC > 데이터 소스: Staging / Intermediate 테이블 (현재는 temp view 활용)

# COMMAND ----------

# DBTITLE 1,[S2] STEP 5: 복수 사용자 동시 편집
# MAGIC %sql
# MAGIC -- [Stage 2] STEP 5: 복수 사용자 편집 (overlap/≤5min ❌ / 5min~1h ⚠️ / >1h 순차 정상)
# MAGIC WITH object_users AS (
# MAGIC   SELECT object_id, task_id, session_id, user_id,
# MAGIC          MIN(event_time) AS first_edit,
# MAGIC          MAX(event_time) AS last_edit
# MAGIC   FROM bbox3d_events
# MAGIC   WHERE object_id IS NOT NULL
# MAGIC   GROUP BY object_id, task_id, session_id, user_id
# MAGIC )
# MAGIC SELECT object_id, task_id,
# MAGIC        COUNT(DISTINCT user_id) AS user_count,
# MAGIC        COLLECT_SET(user_id) AS users,
# MAGIC        MIN(first_edit) AS earliest,
# MAGIC        MAX(last_edit) AS latest
# MAGIC FROM object_users
# MAGIC GROUP BY object_id, task_id
# MAGIC HAVING COUNT(DISTINCT user_id) > 1
# MAGIC ORDER BY user_count DESC

# COMMAND ----------

# MAGIC %md
# MAGIC ### Stage 2 — STEP 6~9 (runner 통합 실행)
# MAGIC
# MAGIC | STEP | 분석 항목 | 설명 | 스코어링 병합 |
# MAGIC |------|-----------|------|-------------|
# MAGIC | 6 | Undo/Redo 패턴 이상 | workspace_history 테이블: 6a undo 비율, 6b burst | → step_id=5 (C) |
# MAGIC | 7 | Command Stack 플로우 정합성 | 7a 시간 역전, 7b 복수편집 비율 | → step_id=5 (C) |
# MAGIC | 8 | 작업 생산성 이상 | 8a 스테일 세션, 8b 집중도 저하 | → step_id=3 (B) |
# MAGIC | 9 | 파이프라인 신선도 | 활성시간 수집 공백 탐지 | → step_id=3 (B) |
# MAGIC
# MAGIC > **참고**: STEP 6~9는 `anomaly_detection_runner` 노트북에서 통합 실행됩니다. 템플릿은 탐색적 분석(Stage 1 + STEP 5)용으로 유지됩니다.