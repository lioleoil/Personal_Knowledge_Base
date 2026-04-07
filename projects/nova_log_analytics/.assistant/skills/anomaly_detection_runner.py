# Databricks notebook source
# DBTITLE 1,커맨드 로그 이상 탐지 자동화 러너
# MAGIC %md
# MAGIC # 커맨드 로그 이상 탐지 자동화 러너
# MAGIC > Feature별 파라미터를 받아 전체 STEP을 실행하고, 결과를 Delta 테이블에 저장합니다.
# MAGIC >
# MAGIC > **실행 방법**: Job에서 `feature`, `analysis_date` 파라미터와 함께 호출
# MAGIC

# COMMAND ----------

# DBTITLE 1,Parameters & Configuration

from datetime import datetime, timedelta
import json

# --- Parameters ---
dbutils.widgets.text("feature", "ld", "Feature (od/ld/rmd)")
dbutils.widgets.text("analysis_date", "", "Analysis Date (YYYY-MM-DD, default: yesterday)")

feature = dbutils.widgets.get("feature").strip().lower()
analysis_date = dbutils.widgets.get("analysis_date").strip()
if not analysis_date:
    analysis_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

assert feature in ('od', 'ld', 'rmd'), f"Invalid feature: {feature}"
print(f"🔧 Feature: {feature} | Date: {analysis_date} | Run: {run_ts}")

# --- Feature-specific Configuration ---
CONFIG = {
    'od': {
        'move_events': "('annotation.bbox3d.transform')",
        'json_x': '$.position.x',  'json_y': '$.position.y',  'json_z': '$.position.z',
        'vib_threshold': 0.75,  'min_dist': 0.05,
        'step4': 'yaw',   # yaw drift
    },
    'ld': {
        'move_events': "('annotation.point.move', 'annotation.point.move_batch')",
        'json_x': '$.position[0]', 'json_y': '$.position[1]', 'json_z': '$.position[2]',
        'vib_threshold': 0.83,  'min_dist': 0.05,
        'step4': None,     # no feature-specific check
    },
    'rmd': {
        'move_events': "('annotation.point.move', 'annotation.point.move_batch', 'annotation.polywall.transform')",
        'json_x': '$.position[0]', 'json_y': '$.position[1]', 'json_z': '$.position[2]',
        'vib_threshold': 0.75,  'min_dist': 0.05,
        'step4': 'height', # height anomaly
    },
}

cfg = CONFIG[feature]

# --- Helper: insert results ---
RESULTS_TABLE = "sv_nova_dev_an2_catalog.analytics.anomaly_detection_results"
REPORTS_TABLE = "sv_nova_dev_an2_catalog.analytics.anomaly_detection_reports"

def save_result(step_id, step_name, stage, severity, event_count=0, object_count=0, avg_metric=None, max_metric=None, details=None):
    spark.sql(f"""
        INSERT INTO {RESULTS_TABLE} VALUES (
            '{analysis_date}', '{feature}', {step_id}, '{step_name}', '{stage}',
            '{severity}', {event_count}, {object_count},
            {avg_metric if avg_metric is not None else 'NULL'},
            {max_metric if max_metric is not None else 'NULL'},
            {repr(json.dumps(details, ensure_ascii=False)) if details else 'NULL'},
            '{run_ts}'
        )
    """)

# --- Clear previous results for this date+feature ---
spark.sql(f"DELETE FROM {RESULTS_TABLE} WHERE analysis_date = '{analysis_date}' AND feature = '{feature}'")
spark.sql(f"DELETE FROM {REPORTS_TABLE} WHERE analysis_date = '{analysis_date}' AND feature = '{feature}'")
print("✅ Config loaded, previous results cleared")


# COMMAND ----------

# DBTITLE 1,데이터 준비: events temp view

spark.sql(f"""
CREATE OR REPLACE TEMP VIEW events AS
WITH raw_parsed AS (
  SELECT
    e._id AS event_id,
    e._raw:source::STRING AS event_source,
    e._raw:type::STRING AS event_type,
    to_timestamp(e._raw:time::STRING) AS event_time,
    DATE(to_timestamp(e._raw:time::STRING)) AS event_date,
    e._raw:sessionid::STRING AS session_id,
    to_timestamp(e._occurred_at) AS occurred_at,
    e._raw:data.user.id::STRING AS user_id,
    e._raw:data.user.name::STRING AS user_name,
    e._raw:data.project.dataset_id::STRING AS dataset_id,
    e._raw:data.project.task_id::STRING AS task_id,
    e._raw:data.feature::STRING AS feature,
    e._raw:data.action::STRING AS action,
    e._raw:data.input_type::STRING AS input_type,
    from_json(e._raw:data.changes::STRING,
      'ARRAY<STRUCT<object_id:INT, object_type:STRING, action:STRING, old:STRING, new:STRING>>'
    ) AS changes,
    from_json(e._raw:data.targets::STRING, 'ARRAY<STRING>') AS targets
  FROM sv_nova_dev_an2_catalog.raw.raw_labelit__workspace_command e
  WHERE e._raw:type::STRING NOT IN ('history.undo', 'history.redo')
    AND e._raw:data.changes IS NOT NULL AND e._raw:data.changes != '[]'
    AND e._raw:data.feature::STRING = '{feature}'
    AND DATE(to_timestamp(e._raw:time::STRING)) = '{analysis_date}'
)
SELECT event_id, event_source, event_type, event_time, event_date,
  session_id, occurred_at, user_id, user_name, dataset_id, task_id,
  feature, action, input_type,
  c.object_id, c.object_type, c.action AS change_action,
  c.old AS old_val, c.new AS new_val, targets
FROM raw_parsed LATERAL VIEW EXPLODE(changes) AS c
""")

total = spark.sql("SELECT COUNT(*) FROM events").collect()[0][0]
print(f"✅ events temp view: {total:,} rows")
assert total > 0, f"No data for feature={feature}, date={analysis_date}"


# COMMAND ----------

# DBTITLE 1,[S1-A] STEP 0: 이벤트 요약 통계

# ═══ Stage 1 — Group A ═══
# [S1-A] STEP 0: 이벤트 요약 통계
overview = spark.sql("""
    SELECT COUNT(*) AS total_events,
           COUNT(DISTINCT session_id) AS sessions,
           COUNT(DISTINCT user_name) AS users,
           COUNT(DISTINCT task_id) AS tasks,
           COUNT(DISTINCT dataset_id) AS datasets
    FROM events
""").collect()[0]

step0_details = {
    "total_events": overview.total_events,
    "sessions": overview.sessions,
    "users": overview.users,
    "tasks": overview.tasks,
    "datasets": overview.datasets,
}

# event_type 분포
et_rows = spark.sql("SELECT event_type, COUNT(*) AS cnt FROM events GROUP BY event_type ORDER BY cnt DESC").collect()
step0_details["event_type_dist"] = {r.event_type: r.cnt for r in et_rows}

save_result(0, "이벤트 요약 통계", "S1-A", "info",
            event_count=overview.total_events, details=step0_details)

print(f"✅ STEP 0: {overview.total_events:,} events, {overview.sessions} sessions, {overview.users} users, {overview.tasks} tasks")


# COMMAND ----------

# DBTITLE 1,[S1-A] STEP 3: 타임스탬프 지연

# [S1-A] STEP 3: 타임스탬프 지연
delay_rows = spark.sql("""
    SELECT CASE WHEN TIMESTAMPDIFF(SECOND, event_time, occurred_at) < 0 THEN 'negative'
                WHEN TIMESTAMPDIFF(SECOND, event_time, occurred_at) > 60 THEN 'critical'
                WHEN TIMESTAMPDIFF(SECOND, event_time, occurred_at) > 30 THEN 'warning'
                ELSE 'normal' END AS severity,
           COUNT(*) AS cnt,
           ROUND(AVG(TIMESTAMPDIFF(SECOND, event_time, occurred_at)), 2) AS avg_diff,
           MAX(TIMESTAMPDIFF(SECOND, event_time, occurred_at)) AS max_diff
    FROM events GROUP BY severity
""").collect()

for r in delay_rows:
    sev = r.severity if r.severity != 'negative' else 'critical'
    save_result(3, "타임스탬프 지연", "S1-A", sev,
                event_count=r.cnt, avg_metric=r.avg_diff, max_metric=float(r.max_diff) if r.max_diff else None,
                details={"label": f"{r.severity} ({r.cnt:,}건, avg={r.avg_diff}s, max={r.max_diff}s)"})

delay_map = {r.severity: r.cnt for r in delay_rows}
print(f"✅ STEP 3: normal={delay_map.get('normal',0):,}, warning={delay_map.get('warning',0):,}, critical={delay_map.get('critical',0)+delay_map.get('negative',0):,}")


# COMMAND ----------

# DBTITLE 1,[S1-B] STEP 1: 위치 점프

# ═══ Stage 1 — Group B ═══
# [S1-B] STEP 1: 위치 점프
jx, jy, jz = cfg['json_x'], cfg['json_y'], cfg['json_z']
move_evts = cfg['move_events']

jump_rows = spark.sql(f"""
    WITH movements AS (
      SELECT session_id, user_name, task_id, object_id,
             CAST(get_json_object(old_val, '{jx}') AS DOUBLE) AS ox,
             CAST(get_json_object(old_val, '{jy}') AS DOUBLE) AS oy,
             CAST(get_json_object(old_val, '{jz}') AS DOUBLE) AS oz,
             CAST(get_json_object(new_val, '{jx}') AS DOUBLE) AS nx,
             CAST(get_json_object(new_val, '{jy}') AS DOUBLE) AS ny,
             CAST(get_json_object(new_val, '{jz}') AS DOUBLE) AS nz
      FROM events
      WHERE event_type IN {move_evts} AND old_val IS NOT NULL AND new_val IS NOT NULL
    ),
    distances AS (
      SELECT *, SQRT(POW(nx-ox,2)+POW(ny-oy,2)+POW(nz-oz,2)) AS dist FROM movements
    )
    SELECT CASE WHEN dist > 15.0 THEN 'critical' WHEN dist > 5.0 THEN 'warning' ELSE 'normal' END AS severity,
           COUNT(*) AS cnt, ROUND(AVG(dist),4) AS avg_d, ROUND(MAX(dist),4) AS max_d
    FROM distances GROUP BY severity
""").collect()

for r in jump_rows:
    save_result(1, "위치 점프", "S1-B", r.severity,
                event_count=r.cnt, avg_metric=r.avg_d, max_metric=r.max_d)

jump_map = {r.severity: r.cnt for r in jump_rows}
print(f"✅ STEP 1: normal={jump_map.get('normal',0):,}, warning={jump_map.get('warning',0):,}, critical={jump_map.get('critical',0):,}")


# COMMAND ----------

# DBTITLE 1,[S1-B] STEP 2: 위치 진동
# [S1-B] STEP 2: 위치 진동
# ev_cnt는 진동 에피소드 수 (연속 진동 구간의 시작점 카운트). v1.1 수정: sliding window 과대평가 해소
vib_t = cfg['vib_threshold']
min_d = cfg['min_dist']

vib_rows = spark.sql(f"""
    WITH ordered AS (
      SELECT session_id, task_id, object_id, event_time,
             CAST(get_json_object(new_val, '{jx}') AS DOUBLE) AS x,
             CAST(get_json_object(new_val, '{jy}') AS DOUBLE) AS y,
             CAST(get_json_object(new_val, '{jz}') AS DOUBLE) AS z,
             ROW_NUMBER() OVER (PARTITION BY session_id, task_id, object_id ORDER BY event_time) AS rn
      FROM events WHERE event_type IN {move_evts} AND new_val IS NOT NULL
    ),
    deltas AS (
      SELECT a.session_id, a.task_id, a.object_id, a.rn,
             (b.x-a.x) AS dx, (b.y-a.y) AS dy, (b.z-a.z) AS dz,
             SQRT(POW(b.x-a.x,2)+POW(b.y-a.y,2)+POW(b.z-a.z,2)) AS md
      FROM ordered a JOIN ordered b ON a.session_id=b.session_id AND a.task_id=b.task_id
                   AND a.object_id=b.object_id AND b.rn=a.rn+1
    ),
    sig AS (
      SELECT *, ROW_NUMBER() OVER (PARTITION BY session_id,task_id,object_id ORDER BY rn) AS sr
      FROM deltas WHERE md >= {min_d}
    ),
    dc AS (
      SELECT a.session_id,a.task_id,a.object_id,a.sr,
             CASE WHEN SIGN(a.dx)!=SIGN(b.dx) OR SIGN(a.dy)!=SIGN(b.dy) OR SIGN(a.dz)!=SIGN(b.dz) THEN 1 ELSE 0 END AS rv
      FROM sig a JOIN sig b ON a.session_id=b.session_id AND a.task_id=b.task_id
                   AND a.object_id=b.object_id AND b.sr=a.sr+1
    ),
    w AS (
      SELECT *,SUM(rv) OVER (PARTITION BY session_id,task_id,object_id ORDER BY sr ROWS BETWEEN 5 PRECEDING AND CURRENT ROW) AS r,
             COUNT(*) OVER (PARTITION BY session_id,task_id,object_id ORDER BY sr ROWS BETWEEN 5 PRECEDING AND CURRENT ROW) AS ws
      FROM dc
    ),
    flagged AS (
      SELECT session_id, task_id, object_id, sr,
             ROUND(r/ws, 2) AS ratio,
             CASE WHEN ROUND(r/ws,2) >= {vib_t} AND ws >= 4 THEN 1 ELSE 0 END AS in_vib
      FROM w
    ),
    with_lag AS (
      SELECT *,
             LAG(in_vib, 1, 0) OVER (PARTITION BY session_id,task_id,object_id ORDER BY sr) AS prev_vib
      FROM flagged
    ),
    obj AS (
      SELECT session_id,task_id,object_id,
             MAX(ratio) AS mr,
             SUM(in_vib) AS ec,
             SUM(CASE WHEN in_vib = 1 AND prev_vib = 0 THEN 1 ELSE 0 END) AS episodes
      FROM with_lag
      GROUP BY session_id,task_id,object_id
      HAVING MAX(in_vib) = 1
    )
    SELECT CASE WHEN episodes>=3 AND mr>={vib_t} THEN 'critical'
                WHEN mr>={vib_t} THEN 'warning' ELSE 'normal' END AS severity,
           COUNT(*) AS obj_cnt, SUM(episodes) AS ev_cnt, SUM(ec) AS window_hits
    FROM obj WHERE mr>={vib_t} GROUP BY severity
""").collect()

for r in vib_rows:
    save_result(2, "위치 진동", "S1-B", r.severity,
                event_count=r.ev_cnt, object_count=r.obj_cnt,
                details={"threshold": vib_t, "min_dist": min_d, "window_hits": r.window_hits})

vib_map = {r.severity: (r.obj_cnt, r.ev_cnt, r.window_hits) for r in vib_rows}
print(f"✅ STEP 2: " + ", ".join(f"{k}={v[0]} objects ({v[1]} episodes, {v[2]} window hits)" for k,v in vib_map.items()) if vib_map else "✅ STEP 2: 이상 없음")

# COMMAND ----------

# DBTITLE 1,[S1-B] STEP 4: Feature-specific

# [S1-B] STEP 4: Feature-specific (OD: yaw, RMD: height, LD: skip)
if cfg['step4'] == 'yaw':
    yaw_rows = spark.sql(f"""
        WITH yaw_vals AS (
          SELECT session_id, task_id, object_id,
                 CAST(get_json_object(new_val, '$.rotation.yaw') AS DOUBLE) AS yaw
          FROM events WHERE event_type IN {move_evts} AND new_val IS NOT NULL
        )
        SELECT COUNT(DISTINCT CONCAT(session_id,':',task_id,':',object_id)) AS obj_cnt,
               COUNT(*) AS ev_cnt, MAX(ABS(yaw)) AS max_yaw
        FROM yaw_vals WHERE ABS(yaw) < 1E-6 AND ABS(yaw) > 0
    """).collect()[0]
    if yaw_rows.obj_cnt > 0:
        sev = 'warning' if yaw_rows.max_yaw > 1E-10 else 'info'
        save_result(4, "yaw 드리프트", "S1-B", sev,
                    event_count=yaw_rows.ev_cnt, object_count=yaw_rows.obj_cnt,
                    max_metric=yaw_rows.max_yaw)
        print(f"✅ STEP 4 (yaw): {yaw_rows.obj_cnt} objects, max={yaw_rows.max_yaw:.2e}")
    else:
        save_result(4, "yaw 드리프트", "S1-B", "normal")
        print("✅ STEP 4 (yaw): 이상 없음")

elif cfg['step4'] == 'height':
    h_rows = spark.sql("""
        WITH heights AS (
          SELECT session_id, user_name, object_id,
                 CAST(get_json_object(new_val, '$.height') AS DOUBLE) AS h
          FROM events
          WHERE event_type IN ('annotation.polywall.create','annotation.polywall.transform')
            AND new_val IS NOT NULL
        )
        SELECT CASE WHEN ABS(h)>1.0 THEN 'critical' WHEN ABS(h)>0.5 THEN 'warning' ELSE 'normal' END AS severity,
               COUNT(*) AS cnt, ROUND(AVG(ABS(h)),4) AS avg_h, ROUND(MAX(ABS(h)),4) AS max_h
        FROM heights GROUP BY severity
    """).collect()
    for r in h_rows:
        save_result(4, "높이 이상", "S1-B", r.severity,
                    event_count=r.cnt, avg_metric=r.avg_h, max_metric=r.max_h)
    h_map = {r.severity: r.cnt for r in h_rows}
    print(f"✅ STEP 4 (height): " + ", ".join(f"{k}={v}" for k,v in h_map.items()))

else:
    save_result(4, "해당 없음", "S1-B", "skip", details={"note": "LD는 STEP 4 해당 없음"})
    print("✅ STEP 4: LD — 해당 없음 (skip)")


# COMMAND ----------

# DBTITLE 1,[S2] STEP 5: 복수 사용자 편집

# ═══ Stage 2 ═══
# [S2] STEP 5: 복수 사용자 편집 (시간 겹침 조건)
multi_rows = spark.sql("""
    WITH user_sessions AS (
      SELECT object_id, task_id, user_name,
             MIN(event_time) AS fe, MAX(event_time) AS le
      FROM events WHERE object_id IS NOT NULL
      GROUP BY object_id, task_id, user_name
    ),
    pairs AS (
      SELECT a.object_id, a.task_id, a.user_name AS ua, b.user_name AS ub,
             CASE WHEN a.le < b.fe THEN TIMESTAMPDIFF(SECOND, a.le, b.fe)
                  WHEN b.le < a.fe THEN TIMESTAMPDIFF(SECOND, b.le, a.fe)
                  ELSE 0 END AS gap
      FROM user_sessions a JOIN user_sessions b
        ON a.object_id=b.object_id AND a.task_id=b.task_id AND a.user_name < b.user_name
    )
    SELECT CASE WHEN gap=0 THEN 'critical'
                WHEN gap<=300 THEN 'critical'
                WHEN gap<=3600 THEN 'warning'
                ELSE 'normal' END AS severity,
           COUNT(*) AS pair_cnt
    FROM pairs GROUP BY severity
""").collect()

for r in multi_rows:
    label = {'critical': 'overlap/≤5min', 'warning': '5min~1h', 'normal': '>1h (순차)'}
    save_result(5, "복수 사용자 편집", "S2", r.severity,
                object_count=r.pair_cnt,
                details={"label": label.get(r.severity, r.severity)})

mu_map = {r.severity: r.pair_cnt for r in multi_rows}
print(f"✅ STEP 5: critical={mu_map.get('critical',0)}, warning={mu_map.get('warning',0)}, normal={mu_map.get('normal',0)}")


# COMMAND ----------

# DBTITLE 1,[S2] STEP 6: Undo/Redo 패턴 이상
# [S2] STEP 6: Undo/Redo 패턴 이상 (→ step_id=5 병합)
# 데이터 소스: workspace_history 테이블 (history.undo / history.redo)
HISTORY_TABLE = "sv_nova_dev_an2_catalog.raw.raw_labelit__workspace_history"

# ── 6a: 사용자별 Undo 비율 (undo건수 / 전체 커맨드건수) ──
undo_user_rows = spark.sql(f"""
    WITH undo_counts AS (
        SELECT
            _raw:data.user.name::STRING AS user_name,
            _raw:data.project.task_id::STRING AS task_id,
            _raw:type::STRING AS event_type,
            COUNT(*) AS cnt
        FROM {HISTORY_TABLE}
        WHERE _raw:data.feature::STRING = '{feature}'
          AND DATE(to_timestamp(_raw:time::STRING)) = '{analysis_date}'
          AND _raw:type::STRING IN ('history.undo', 'history.redo')
        GROUP BY user_name, task_id, event_type
    ),
    user_undo_agg AS (
        SELECT user_name, task_id,
               COALESCE(SUM(CASE WHEN event_type = 'history.undo' THEN cnt ELSE 0 END), 0) AS undo_cnt,
               COALESCE(SUM(CASE WHEN event_type = 'history.redo' THEN cnt ELSE 0 END), 0) AS redo_cnt
        FROM undo_counts
        GROUP BY user_name, task_id
    ),
    user_cmd_counts AS (
        SELECT user_name, task_id, COUNT(*) AS cmd_cnt
        FROM events
        GROUP BY user_name, task_id
    )
    SELECT u.user_name, u.task_id, u.undo_cnt, u.redo_cnt,
           COALESCE(c.cmd_cnt, 0) AS cmd_cnt,
           CASE WHEN c.cmd_cnt > 0 THEN ROUND(u.undo_cnt * 100.0 / c.cmd_cnt, 1) ELSE 0 END AS undo_rate
    FROM user_undo_agg u
    LEFT JOIN user_cmd_counts c ON u.user_name = c.user_name AND u.task_id = c.task_id
    ORDER BY undo_rate DESC
""").collect()

total_undos = sum(r.undo_cnt for r in undo_user_rows)
total_redos = sum(r.redo_cnt for r in undo_user_rows)
high_undo_users = [(r.user_name, r.task_id, float(r.undo_rate), r.undo_cnt, r.cmd_cnt)
                   for r in undo_user_rows if float(r.undo_rate) > 30]

if any(r[2] > 50 for r in high_undo_users):
    save_result(5, "Undo과다", "S2", "critical",
                event_count=total_undos,
                object_count=len([r for r in high_undo_users if r[2] > 50]),
                details={"label": f"Undo과다 사용자 {len(high_undo_users)}명 (rate>30%) (STEP 6a → S5 병합)",
                         "high_undo_users": [{"user": u, "task": t, "rate": r, "undos": uc, "cmds": cc}
                                              for u, t, r, uc, cc in high_undo_users]})
    print(f"❌ STEP 6a: Undo 과다 사용자 {len(high_undo_users)}명 (>30%), critical {len([r for r in high_undo_users if r[2] > 50])}명 (>50%)")
elif high_undo_users:
    save_result(5, "Undo과다", "S2", "warning",
                event_count=total_undos,
                object_count=len(high_undo_users),
                details={"label": f"Undo비율 주의 {len(high_undo_users)}명 (rate>30%) (STEP 6a → S5 병합)",
                         "high_undo_users": [{"user": u, "task": t, "rate": r, "undos": uc, "cmds": cc}
                                              for u, t, r, uc, cc in high_undo_users]})
    print(f"⚠️ STEP 6a: Undo 비율 주의 {len(high_undo_users)}명 (>30%)")
else:
    print(f"✅ STEP 6a: Undo 비율 정상 (전체 {total_undos}건)")

# ── 6b: Undo burst (30초 내 5건 이상 연속 undo) ──
burst_row = spark.sql(f"""
    WITH undo_seq AS (
        SELECT
            _raw:data.user.name::STRING AS user_name,
            _raw:sessionid::STRING AS session_id,
            _raw:data.project.task_id::STRING AS task_id,
            to_timestamp(_raw:time::STRING) AS event_time
        FROM {HISTORY_TABLE}
        WHERE _raw:type::STRING = 'history.undo'
          AND _raw:data.feature::STRING = '{feature}'
          AND DATE(to_timestamp(_raw:time::STRING)) = '{analysis_date}'
    ),
    with_window AS (
        SELECT *,
            COUNT(*) OVER (
                PARTITION BY session_id, task_id
                ORDER BY UNIX_TIMESTAMP(event_time)
                RANGE BETWEEN 30 PRECEDING AND CURRENT ROW
            ) AS undo_in_30s
        FROM undo_seq
    )
    SELECT
        COUNT(DISTINCT CONCAT(session_id, ':', task_id)) AS burst_sessions,
        COUNT(*) AS burst_events,
        MAX(undo_in_30s) AS max_burst_size
    FROM with_window
    WHERE undo_in_30s >= 5
""").collect()[0]

burst_sessions = burst_row.burst_sessions
if burst_sessions > 0:
    sev = "critical" if burst_row.max_burst_size >= 10 else "warning"
    save_result(5, "Undo연속", "S2", sev,
                event_count=burst_row.burst_events,
                object_count=burst_sessions,
                details={"label": f"Undo burst {burst_sessions}세션, max={burst_row.max_burst_size}건/30s (STEP 6b → S5 병합)",
                         "max_burst_size": int(burst_row.max_burst_size)})
    print(f"{'❌' if sev == 'critical' else '⚠️'} STEP 6b: Undo burst {burst_sessions}세션, max={burst_row.max_burst_size}건/30s")
else:
    print(f"✅ STEP 6b: Undo burst 없음")

step6_details = {
    "total_undos": int(total_undos),
    "total_redos": int(total_redos),
    "high_undo_users": len(high_undo_users),
    "burst_sessions": int(burst_sessions),
    "max_burst_size": int(burst_row.max_burst_size) if burst_row.max_burst_size else 0,
}
print(f"✅ STEP 6 완료: undos={total_undos}, redos={total_redos}, high_rate_users={len(high_undo_users)}, bursts={burst_sessions}")

# COMMAND ----------

# DBTITLE 1,[S2] STEP 7: Command Stack 플로우 정합성
# [S2] STEP 7: Command Stack 플로우 정합성 (→ step_id=5 병합)
# 7a: 시간 역전 검사
reversal_row = spark.sql("""
    WITH seq AS (
      SELECT session_id, task_id, event_time,
             LAG(event_time) OVER (PARTITION BY session_id, task_id ORDER BY event_time) AS prev_time
      FROM events
    )
    SELECT
      COUNT(*) AS total_pairs,
      SUM(CASE WHEN event_time < prev_time THEN 1 ELSE 0 END) AS reversals
    FROM seq WHERE prev_time IS NOT NULL
""").collect()[0]

reversal_count = reversal_row.reversals
if reversal_count > 0:
    save_result(5, "시간역전", "S2", "critical",
                event_count=reversal_count,
                details={"label": f"시간역전 {reversal_count}건 (STEP 7a → S5 병합)"})
    print(f"❌ STEP 7a: 시간역전 {reversal_count}건")
else:
    print(f"✅ STEP 7a: 시간역전 0건")

# 7b: task별 object_id 복수편집 비율
multi_edit_row = spark.sql("""
    WITH obj_editors AS (
      SELECT task_id, object_id,
             COUNT(DISTINCT user_name) AS editor_count
      FROM events WHERE object_id IS NOT NULL
      GROUP BY task_id, object_id
    )
    SELECT
      COUNT(*) AS total_objects,
      SUM(CASE WHEN editor_count > 1 THEN 1 ELSE 0 END) AS multi_objects
    FROM obj_editors
""").collect()[0]

multi_pct = round(multi_edit_row.multi_objects / multi_edit_row.total_objects * 100, 1) if multi_edit_row.total_objects > 0 else 0
if multi_pct > 50:
    save_result(5, "복수편집비율", "S2", "warning",
                object_count=multi_edit_row.multi_objects,
                details={"label": f"복수편집 {multi_pct}% ({multi_edit_row.multi_objects}/{multi_edit_row.total_objects}) (STEP 7b → S5 병합)"})
    print(f"⚠️ STEP 7b: 복수편집 {multi_pct}% ({multi_edit_row.multi_objects}/{multi_edit_row.total_objects})")
else:
    print(f"✅ STEP 7b: 복수편집 {multi_pct}% ({multi_edit_row.multi_objects}/{multi_edit_row.total_objects})")

step7_details = {
    "reversals": reversal_count,
    "multi_edit_pct": multi_pct,
    "multi_objects": int(multi_edit_row.multi_objects),
    "total_objects": int(multi_edit_row.total_objects),
}
print(f"✅ STEP 7 완료")

# COMMAND ----------

# DBTITLE 1,[S2] STEP 8: 작업 집중도 이상
# [S2] STEP 8: 작업 집중도 이상 (→ step_id=3 병합)
# 8a: 스테일 세션 (gap > 600분 = 36000초)
stale_row = spark.sql("""
    WITH with_diff AS (
      SELECT session_id, task_id, user_name, event_time,
             UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
               LAG(event_time) OVER (PARTITION BY session_id, task_id ORDER BY event_time)
             ) AS diff_sec
      FROM events
    )
    SELECT COUNT(*) AS stale_count,
           MAX(diff_sec) AS max_gap_sec
    FROM with_diff
    WHERE diff_sec > 36000
""").collect()[0]

stale_count = stale_row.stale_count
if stale_count > 0:
    max_gap_min = round(stale_row.max_gap_sec / 60, 1) if stale_row.max_gap_sec else 0
    save_result(3, "스테일세션", "S2", "critical",
                event_count=stale_count, avg_metric=max_gap_min,
                details={"label": f"스테일세션 {stale_count}건, max={max_gap_min}분 (STEP 8a → S3 병합)"})
    print(f"❌ STEP 8a: 스테일세션 {stale_count}건, max={max_gap_min}분")
else:
    print(f"✅ STEP 8a: 스테일세션 0건")

# 8b: 집중도 저하 사용자 (avg_gap > 30s AND gaps_over_5min > 10)
conc_row = spark.sql("""
    WITH with_diff AS (
      SELECT user_name, session_id, task_id,
             UNIX_TIMESTAMP(event_time) - UNIX_TIMESTAMP(
               LAG(event_time) OVER (PARTITION BY session_id, task_id ORDER BY event_time)
             ) AS diff_sec
      FROM events
    ),
    user_stats AS (
      SELECT user_name,
             AVG(diff_sec) AS avg_gap,
             SUM(CASE WHEN diff_sec > 300 THEN 1 ELSE 0 END) AS gaps_5min
      FROM with_diff WHERE diff_sec IS NOT NULL
      GROUP BY user_name
    )
    SELECT COUNT(*) AS low_focus_users
    FROM user_stats
    WHERE avg_gap > 30 AND gaps_5min > 10
""").collect()[0]

if conc_row.low_focus_users > 0:
    save_result(3, "집중도저하", "S2", "warning",
                event_count=conc_row.low_focus_users,
                details={"label": f"집중도저하 사용자 {conc_row.low_focus_users}명 (STEP 8b → S3 병합)"})
    print(f"⚠️ STEP 8b: 집중도저하 {conc_row.low_focus_users}명")
else:
    print(f"✅ STEP 8b: 집중도저하 0명")

step8_details = {"stale_sessions": stale_count, "low_focus_users": conc_row.low_focus_users}
print(f"✅ STEP 8 완료")

# COMMAND ----------

# DBTITLE 1,[S2] STEP 9: 수집 공백 시간대
# [S2] STEP 9: 수집 공백 시간대 (→ step_id=3 병합)
hourly = spark.sql("""
    SELECT HOUR(event_time) AS h, COUNT(*) AS cnt
    FROM events
    GROUP BY HOUR(event_time)
""").collect()

hourly_map = {r.h: r.cnt for r in hourly}
# 활성시간(09~23시) 내 dead hour / low activity 체크
dead_hours = [h for h in range(9, 24) if hourly_map.get(h, 0) == 0]
low_hours = [h for h in range(9, 24) if 0 < hourly_map.get(h, 0) < 100]

if dead_hours:
    save_result(3, "수집공백", "S2", "critical",
                event_count=len(dead_hours),
                details={"label": f"Dead hour {len(dead_hours)}건: {dead_hours} (STEP 9 → S3 병합)",
                         "dead_hours": dead_hours})
    print(f"❌ STEP 9: Dead hour {dead_hours}")
elif low_hours:
    save_result(3, "수집공백", "S2", "warning",
                event_count=len(low_hours),
                details={"label": f"저활동 {len(low_hours)}시간대 (STEP 9 → S3 병합)",
                         "low_hours": low_hours})
    print(f"⚠️ STEP 9: 저활동 시간대 {low_hours}")
else:
    print(f"✅ STEP 9: 수집 공백 없음 (24시간 정상)")

step9_details = {"dead_hours": dead_hours, "low_hours": low_hours, "hourly": {str(k): v for k, v in hourly_map.items()}}
print(f"✅ STEP 9 완료")

# COMMAND ----------

# DBTITLE 1,품질 평가 기준 분류 체계
# MAGIC %md
# MAGIC ## 품질 평가 기준 분류 체계 (v1.2)
# MAGIC **Date : 2026-04-07**
# MAGIC
# MAGIC ### 카테고리 구분
# MAGIC
# MAGIC | 카테고리 | STEP | 평가 대상 | 의미 |
# MAGIC |----------|------|-----------|------|
# MAGIC | **A. 공간 무결성** | 1, 2, 4 | 좌표·기하학적 값의 물리적 합리성 | 어노테이션 품질에 **직접 영향** |
# MAGIC | **B. 수집 시간 정합성** | 3 ← (8, 9 병합) | event_time 지연 + 커맨드 간격 + 수집 공백 | 수집 무결성에 **직접 영향** |
# MAGIC | **C. 작업 행동 패턴** | 5 ← (6, 7 병합) | 복수 사용자 편집 + Undo/Redo 패턴 + 시간 역전 + 복수편집 비율 | 데이터 충돌·무결성 위험 |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### A. 공간 무결성 (STEP 1, 2, 4) — 세부 분류
# MAGIC
# MAGIC #### STEP 1: 위치 점프
# MAGIC
# MAGIC | 등급 | 기준 | 실제 데이터 패턴 | 분류 |
# MAGIC |------|------|-----------------|------|
# MAGIC | normal | ≤ 5m | LD 259,870건 (avg 0.07m) · OD 25,499건 (avg 0.10m) | — |
# MAGIC | ⚠️ warning | 5\~15m | LD 122건 (avg 6.42m) · OD 154건 (avg 7.66m) | **노이즈 판정** — 객체 이동 시 정상 범위 (보정 이력: p999=12.1m) |
# MAGIC | ❌ critical | > 15m | LD 3건 (avg 15.70m, max 16.24m) · OD 26건 (avg 20.82m, max 32.00m) | **이상값** — 물리적인 오류, 혹은 비정상적 패턴 |
# MAGIC
# MAGIC > **판정**: warning의 대부분은 객체 편집 시 발생 가능한 노이즈. critical만 실제 이상으로 카운트.
# MAGIC
# MAGIC #### STEP 2: 위치 진동
# MAGIC
# MAGIC | 등급 | 기준 | 실제 데이터 패턴 | 분류 |
# MAGIC |------|------|-----------------|------|
# MAGIC | ⚠️ warning | reversal ≥ threshold, < 10건/객체 | LD 99객체/471이벤트 | **노이즈 판정** — 짧은 편집 망설임 가능, 단발성 |
# MAGIC | ❌ critical | reversal ≥ threshold, ≥ 10건/객체 | LD 117객체/2,323이벤트 | **이상값** — 지속적 진동 패턴 (Tool 오류 또는 비정상 편집) |
# MAGIC
# MAGIC > **판정**: warning은 단발성 경계 사례 (가중치 낮음). critical은 객체 단위 지속 패턴으로 실제 이상.
# MAGIC
# MAGIC #### STEP 4: Feature-specific
# MAGIC
# MAGIC | Feature | 등급 | 기준 | 분류 |
# MAGIC |---------|------|------|------|
# MAGIC | OD (yaw) | ⚠️ warning | \|yaw\| < 1E-10 | **노이즈 판정** — 짧은 편집 망설임 가능, 단발성 |
# MAGIC | OD (yaw) | ❌ critical | 1E-10 ≤ \|yaw\| < 1E-6 | **이상 확정** — 누적 드리프트 |
# MAGIC | RMD (height) | ⚠️ warning | 0.5\~1.0m | **노이즈 판정** — 도로면 기준 허용 상한, 객체 이동 |
# MAGIC | RMD (height) | ❌ critical | > 1.0m | **이상 확정** — 물리적인 오류, 혹은 비정상적 패턴 |
# MAGIC | LD | skip | — | 해당 없음 |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### B. 수집 시간 정합성 (STEP 3 ← STEP 8, 9 병합) — 세부 분류
# MAGIC
# MAGIC #### STEP 3: 타임스탬프 지연 (기존)
# MAGIC
# MAGIC | 등급 | 기준 | 실제 데이터 패턴 | 분류 |
# MAGIC |------|------|-----------------|------|
# MAGIC | normal | ≤ 30s | LD 319,049건 (avg 14.36s) · OD 32,902건 · RMD 31,966건 (전량 정상) | **구조적 지연** — 파이프라인 p50=14s, p99=29s |
# MAGIC | ⚠️ warning | 30\~60s | LD 256건 (avg 42.96s) · OD 20건 (avg 33.25s) | **일시적 과부하** — 수집 지연, 파이프라인 부하 징후 |
# MAGIC | ❌ critical | > 60s 또는 음수 | LD 116건 (avg 170.54s, max 235s) · OD 7건 (avg 113.86s) | **시스템 이상** — 파이프라인 장애 또는 시간 역전 |
# MAGIC
# MAGIC #### STEP 8a → S3 병합: 스테일 세션
# MAGIC
# MAGIC | 등급 | 기준 | 실제 데이터 패턴 | 분류 |
# MAGIC |------|------|-----------------|------|
# MAGIC | ❌ critical | gap > 600분 (36,000s) | reviewer 3명 (634, 630, 560분) | **세션 미종료** — 브라우저 미종료 후 익일 동일 세션 유지 |
# MAGIC
# MAGIC > **판정**: 스테일 세션은 수집 시간 정합성을 직접 훼손. 동일 세션에서 10시간+ 공백 → 데이터 파이프라인 신뢰도 저하.
# MAGIC
# MAGIC #### STEP 8b → S3 병합: 집중도 저하
# MAGIC
# MAGIC | 등급 | 기준 | 실제 데이터 패턴 | 분류 |
# MAGIC |------|------|-----------------|------|
# MAGIC | ⚠️ warning | avg_gap > 30s AND gaps_5min > 10 | manager/reviewer 4명 | **역할 확인 필요** — reviewer/manager는 리뷰 특성상 높은 gap 가능 |
# MAGIC
# MAGIC > **판정**: labeler p50 gap 0\~2s, 1분초과 <1.5%로 정상. manager 9.7%는 역할 특성으로 정상 범위일 수 있음.
# MAGIC
# MAGIC #### STEP 9 → S3 병합: 수집 공백 시간대
# MAGIC
# MAGIC | 등급 | 기준 | 실제 데이터 패턴 | 분류 |
# MAGIC |------|------|-----------------|------|
# MAGIC | ❌ critical | 활성시간(09\~23시) 내 0건 시간대 | 분석일 기준 Dead hour 없음 | **수집 중단** — 파이프라인 장애 의심 |
# MAGIC | ⚠️ warning | 활성시간 내 < 100건 시간대 | 최저 08시 521건 | **저활동** — 수집량 급감 |
# MAGIC
# MAGIC > **판정**: 24시간 전체 수집 확인. 최소 521건/시간. Dead hour 발생 시 파이프라인 긴급 점검 필요.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### C. 작업 행동 패턴 (STEP 5 ← STEP 6, 7 병합) — 세부 분류
# MAGIC
# MAGIC #### STEP 5: 복수 사용자 편집 (기존)
# MAGIC
# MAGIC | 등급 | 기준 | 실제 데이터 패턴 | 분류 |
# MAGIC |------|------|-----------------|------|
# MAGIC | normal | > 1h gap | 대다수 (보정 이력: 83% 순차 리뷰) | **정상 워크플로우** |
# MAGIC | ⚠️ warning | 5min\~1h gap | LD 1객체 | **경계** — 의도적 협업 가능 |
# MAGIC | ❌ critical | overlap / ≤ 5min | LD 2객체 | **충돌 확정** — 실제 동시 편집으로 데이터 무결성 위험 |
# MAGIC
# MAGIC #### STEP 6a → S5 병합: Undo 비율
# MAGIC
# MAGIC | 등급 | 기준 | 실제 데이터 패턴 | 분류 |
# MAGIC |------|------|-----------------|------|
# MAGIC | ⚠️ warning | 사용자별 undo_rate > 30% | 해당 사용자 존재 시 | **작업 비효율** — 잦은 되돌리기로 편집 품질 저하 가능성 |
# MAGIC | ❌ critical | 사용자별 undo_rate > 50% | 해당 사용자 존재 시 | **이상 확정** — 작업량 반 이상을 되돌리는 비정상 패턴 |
# MAGIC
# MAGIC > **판정**: Undo 비율은 전체 커맨드 대비 undo 횟수로 산정. history 테이블(`raw_labelit__workspace_history`) 기준.
# MAGIC
# MAGIC #### STEP 6b → S5 병합: Undo burst
# MAGIC
# MAGIC | 등급 | 기준 | 실제 데이터 패턴 | 분류 |
# MAGIC |------|------|-----------------|------|
# MAGIC | ⚠️ warning | 30초 내 5\~9회 연속 undo | 해당 세션 존재 시 | **작업 망설임** — 단발성 연속 되돌리기 |
# MAGIC | ❌ critical | 30초 내 10회 이상 연속 undo | 해당 세션 존재 시 | **이상 확정** — Tool 오류 또는 비정상 작업 패턴 |
# MAGIC
# MAGIC > **판정**: 동일 session+task 내 30초 윈도우 기준. 기계적 연타 버스트는 Tool 오류 의심.
# MAGIC
# MAGIC #### STEP 7a → S5 병합: 시간 역전
# MAGIC
# MAGIC | 등급 | 기준 | 실제 데이터 패턴 | 분류 |
# MAGIC |------|------|-----------------|------|
# MAGIC | ❌ critical | session+task 내 event_time 역전 > 0건 | 245 session-task 전수검사, 0건 | **시퀀스 오류** — 커맨드 순서 무결성 훼손 |
# MAGIC
# MAGIC > **판정**: 시간 역전은 데이터 신뢰성에 치명적. 1건이라도 발생 시 critical.
# MAGIC
# MAGIC #### STEP 7b → S5 병합: 복수편집 비율
# MAGIC
# MAGIC | 등급 | 기준 | 실제 데이터 패턴 | 분류 |
# MAGIC |------|------|-----------------|------|
# MAGIC | ⚠️ warning | task 내 object 복수편집 비율 > 50% | OD 73\~100%, LD <1%, RMD 15% | **워크플로우 확인** — labeler→reviewer 순차 리뷰 vs 실제 동시 편집 |
# MAGIC
# MAGIC > **판정**: OD에서 높은 비율은 리뷰 워크플로우 특성일 수 있음. STEP 5의 시간 겹침 분석과 교차 확인 필요.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### 스코어링 매핑 (Stage 2 → 기존 STEP 병합)
# MAGIC
# MAGIC | 분석 STEP | 분석 항목 | 스코어링 step_id | Category | 가중치 |
# MAGIC |-----------|-----------|-----------------|----------|--------|
# MAGIC | STEP 6a | Undo 비율 | 5 (복수편집) | C 행동 패턴 | critical ×1.0 / warning ×0.5 |
# MAGIC | STEP 6b | Undo burst | 5 (복수편집) | C 행동 패턴 | critical ×1.0 / warning ×0.5 |
# MAGIC | STEP 7a | 시간 역전 | 5 (복수편집) | C 행동 패턴 | critical ×1.0 |
# MAGIC | STEP 7b | 복수편집 비율 | 5 (복수편집) | C 행동 패턴 | warning ×0.5 |
# MAGIC | STEP 8a | 스테일 세션 | 3 (시간지연) | B 시간 정합성 | critical ×1.0 |
# MAGIC | STEP 8b | 집중도 저하 | 3 (시간지연) | B 시간 정합성 | warning ×0.5 |
# MAGIC | STEP 9 | 수집 공백 | 3 (시간지연) | B 시간 정합성 | critical ×1.0 / warning ×0.5 |
# MAGIC
# MAGIC > **설계 원칙**: 별도 스코어링 단계를 만들지 않고 기존 step_id에 결과를 병합하여, scoring v1.1 수식 변경 없이 자연스럽게 반영.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### 스코어링 반영 요약 (v1.2)
# MAGIC
# MAGIC | 분류 | 세부 | 가중치 | 근거 |
# MAGIC |------|------|--------|------|
# MAGIC | A 공간 — 노이즈 | STEP 1 warning, STEP 2 warning, STEP 4 warning | **제외 (×0)** | 객체 편집 시 정상 범위, 단발성 노이즈 |
# MAGIC | A 공간 — 이상값 | STEP 1 critical, STEP 2 critical, STEP 4 critical | **×1.0** | 물리적 오류, 지속 패턴 |
# MAGIC | B 시간 — 노이즈 | STEP 3 warning, STEP 8b 집중도저하, STEP 9 저활동 | **×0.5** | 일시적 과부하, 역할 특성 가능, 저활동 징후 |
# MAGIC | B 시간 — 이상값 | STEP 3 critical, STEP 8a 스테일세션, STEP 9 Dead hour | **×1.0** | 파이프라인 장애·시간 역전·세션 미종료, 수집 중단 |
# MAGIC | C 행동 — 경계 | STEP 5 warning, STEP 6a warning, STEP 6b warning, STEP 7b 복수편집비율 | **×0.5** | 의도적 협업 가능성, 작업 망설임, 워크플로우 확인 필요 |
# MAGIC | C 행동 — 충돌 확정 | STEP 5 critical, STEP 6a critical, STEP 6b critical, STEP 7a 시간역전 | **×1.0** | 데이터 무결성 직접 위험, 시퀀스 오류, 비정상 Undo 패턴 |

# COMMAND ----------

# DBTITLE 1,종합 보고서 생성 및 저장

# ═══ 종합 보고서 생성 및 저장 (Scoring v1.1) ═══
results = spark.sql(f"""
    SELECT step_id, step_name, stage, severity, event_count, object_count, avg_metric, max_metric, details
    FROM {RESULTS_TABLE}
    WHERE analysis_date = '{analysis_date}' AND feature = '{feature}'
    ORDER BY step_id, severity
""").collect()

# ─── 스코어링 파라미터 ───
CAP_EVENT_RATE  = 5.0    # 이벤트 이상 비율 cap (%)
CAP_OBJECT_RATE = 10.0   # 객체 충돌 비율 cap (%)
M_EVENT  = 100 / CAP_EVENT_RATE    # 20
M_OBJECT = 100 / CAP_OBJECT_RATE   # 10
W_A, W_B, W_C = 0.40, 0.40, 0.20
STEP4_CONFIG = {'od': True, 'ld': False, 'rmd': True}

# ─── Finding weight ───
def get_finding_weight(step_id, severity):
    if step_id in (1, 2, 4):
        return 1.0 if severity == 'critical' else 0.0
    elif step_id == 3:
        return {'critical': 1.0, 'warning': 0.5}.get(severity, 0.0)
    elif step_id >= 5:
        return {'critical': 1.0, 'warning': 0.5}.get(severity, 0.0)
    return 0.0

total_events = step0_details['total_events']
warnings = sum(1 for r in results if r.severity == 'warning')
criticals = sum(1 for r in results if r.severity == 'critical')

# ─── total_task_objects (STEP 5용 모수) ───
total_task_objects = spark.sql("""
    SELECT COUNT(DISTINCT CONCAT(object_id, ':', task_id)) AS cnt
    FROM events WHERE object_id IS NOT NULL
""").collect()[0].cnt

# ─── Per-STEP 점수 계산 ───
def step_score(step_id, use_objects=False):
    metric = 'object_count' if use_objects else 'event_count'
    weighted = sum(
        (getattr(r, metric) or 0) * get_finding_weight(r.step_id, r.severity)
        for r in results if r.step_id == step_id
    )
    denom = total_task_objects if use_objects else total_events
    mult = M_OBJECT if use_objects else M_EVENT
    rate = weighted / denom * 100 if denom > 0 else 0
    score = min(round(rate * mult, 1), 100)
    return {'weighted': int(weighted), 'denominator': denom, 'rate_pct': round(rate, 3), 'multiplier': mult, 'score': score}

s1 = step_score(1)
s2 = step_score(2)
s3 = step_score(3)
s5 = step_score(5, use_objects=True)

step4_active = STEP4_CONFIG.get(feature, False)
if step4_active:
    s4 = step_score(4)
else:
    s4 = {'skipped': True}

# ─── 카테고리 집계 ───
a_scores = [s1['score'], s2['score']] + ([s4['score']] if step4_active else [])
a_val = round(sum(a_scores) / len(a_scores), 1)
b_val = s3['score']
c_val = s5['score']

quality_score = round(W_A * a_val + W_B * b_val + W_C * c_val, 1)

if quality_score <= 20:
    quality = "정상"
elif quality_score <= 45:
    quality = "주의"
else:
    quality = "불량"

scoring_details = {
    "version": "v1.2",
    "quality_score": quality_score,
    "grade": quality,
    "population": {"total_events": total_events, "total_task_objects": total_task_objects},
    "sensitivity": {"CAP_EVENT_RATE": CAP_EVENT_RATE, "CAP_OBJECT_RATE": CAP_OBJECT_RATE, "M_EVENT": M_EVENT, "M_OBJECT": M_OBJECT},
    "weights": {"W_A": W_A, "W_B": W_B, "W_C": W_C},
    "categories": {"A": a_val, "B": b_val, "C": c_val},
    "per_step": {"S1": s1, "S2": s2, "S3": s3, "S4": s4, "S5": s5},
    "finding_weights": {"A_warning": 0.0, "A_critical": 1.0, "B_warning": 0.5, "B_critical": 1.0, "C_warning": 0.5, "C_critical": 1.0},
    "summary_counts": {"warnings": warnings, "criticals": criticals},
    "stage2_extended": {
        "step6": step6_details,
        "step7": step7_details,
        "step8": step8_details,
        "step9": step9_details,
    },
}

# ─── 마크다운 보고서 ───
lines = [
    f"# {feature.upper()} 이상 탐지 보고서 — {analysis_date}",
    "",
    "## 개요",
    "",
    "| 항목 | 값 |",
    "|------|----|" ,
    f"| 총 이벤트 | {total_events:,} |",
    f"| 총 객체(task 기준) | {total_task_objects:,} |",
    f"| 세션 | {step0_details['sessions']} |",
    f"| 사용자 | {step0_details['users']} |",
    f"| Task | {step0_details['tasks']} |",
    f"| Warning 건수 | {warnings} |",
    f"| Critical 건수 | {criticals} |",
    "",
    "## 품질 평가 (Scoring v1.2 — Per-STEP CAP + Stage 2 병합)",
    "",
    "| STEP | 가중 이상량 | 모수 | 비율 | M | 점수 |",
    "|------|-----------|------|------|---|------|",
    f"| S1 위치점프 | {s1['weighted']:,} events | {total_events:,} | {s1['rate_pct']:.3f}% | {M_EVENT} | {s1['score']} |",
    f"| S2 위치진동 | {s2['weighted']:,} episodes | {total_events:,} | {s2['rate_pct']:.3f}% | {M_EVENT} | {s2['score']} |",
    f"| S3 시간정합성 | {s3['weighted']:,} events | {total_events:,} | {s3['rate_pct']:.3f}% | {M_EVENT} | {s3['score']} |",
    f"| S4 Feature | {s4.get('weighted','skip'):,} | {s4.get('denominator','-'):,} | {s4.get('rate_pct','-')} | {s4.get('multiplier','-')} | {s4.get('score','skip')} |" if step4_active else f"| S4 Feature | — | — | — | — | skip |",
    f"| S5 행동패턴 | {s5['weighted']:,} objects | {total_task_objects:,} | {s5['rate_pct']:.3f}% | {M_OBJECT} | {s5['score']} |",
    "",
    f"| 카테고리 | 점수 | 가중치 | 기여도 |",
    f"|----------|------|--------|--------|",
    f"| A 공간 무결성 (mean S1,S2{''.join([',S4'] if step4_active else [])}) | {a_val} | ×{W_A} | {round(W_A * a_val, 1)} |",
    f"| B 시간 정합성 (S3+STEP8+STEP9) | {b_val} | ×{W_B} | {round(W_B * b_val, 1)} |",
    f"| C 행동 패턴 (S5+STEP6+STEP7) | {c_val} | ×{W_C} | {round(W_C * c_val, 1)} |",
    f"| **종합** | | | **{quality_score} → {quality}** |",
    "",
    "## Stage 2 확장 분석 (STEP 6/7/8/9)",
    "",
    "| 분석 | 결과 | 스코어링 매핑 |",
    "|------|------|-------------|",
    f"| STEP 6a Undo비율 | undos={step6_details['total_undos']} redos={step6_details['total_redos']} 과다={step6_details['high_undo_users']}명 | → S5 (C) |",
    f"| STEP 6b Undo burst | {step6_details['burst_sessions']}세션, max={step6_details['max_burst_size']}건/30s | → S5 (C) |",
    f"| STEP 7a 시간역전 | {step7_details['reversals']}건 | → S5 (C) |",
    f"| STEP 7b 복수편집비율 | {step7_details['multi_edit_pct']}% ({step7_details['multi_objects']}/{step7_details['total_objects']}) | → S5 (C) |",
    f"| STEP 8a 스테일세션 | {step8_details['stale_sessions']}건 | → S3 (B) |",
    f"| STEP 8b 집중도저하 | {step8_details['low_focus_users']}명 | → S3 (B) |",
    f"| STEP 9 수집공백 | Dead={len(step9_details.get('dead_hours',[]))} Low={len(step9_details.get('low_hours',[]))} | → S3 (B) |",
    "",
    f"> Scoring v1.2 | CAP_EVENT={CAP_EVENT_RATE}% CAP_OBJECT={CAP_OBJECT_RATE}% | W={W_A}/{W_B}/{W_C}",
    f"> STEP 6/7 → step_id=5 병합 | STEP 8/9 → step_id=3 병합 | 수식 변경 없이 통합",
]

report_md = "\n".join(lines)

# ─── Delta 저장 ───
spark.sql(f"""
    INSERT INTO {REPORTS_TABLE}
    (analysis_date, feature, total_events, total_sessions, total_users, total_tasks,
     data_quality, warning_count, critical_count, report_markdown, run_timestamp,
     quality_score, scoring_details)
    VALUES (
        '{analysis_date}', '{feature}',
        {step0_details['total_events']}, {step0_details['sessions']},
        {step0_details['users']}, {step0_details['tasks']},
        '{quality}', {warnings}, {criticals},
        {repr(report_md)},
        '{run_ts}',
        {quality_score},
        {repr(json.dumps(scoring_details, ensure_ascii=False))}
    )
""")

print(f"✅ 보고서 저장 완료: {feature.upper()} / {analysis_date}")
print(f"   품질 점수: {quality_score} → {quality}")
print(f"   ├─ S1={s1['score']}  S2={s2['score']}  S3={s3['score']}  S4={s4.get('score','skip')}  S5={s5['score']}")
print(f"   ├─ A={a_val} (×{W_A}={round(W_A*a_val,1)})  B={b_val} (×{W_B}={round(W_B*b_val,1)})  C={c_val} (×{W_C}={round(W_C*c_val,1)})")
print(f"   ├─ STEP6: undos={step6_details['total_undos']} bursts={step6_details['burst_sessions']}")
print(f"   ├─ STEP7: 역전={step7_details['reversals']} 복수편집={step7_details['multi_edit_pct']}%")
print(f"   ├─ STEP8: 스테일={step8_details['stale_sessions']} 집중도저하={step8_details['low_focus_users']}명")
print(f"   └─ events={total_events:,}  task_objects={total_task_objects:,}")

dbutils.notebook.exit(json.dumps({
    "feature": feature, "date": analysis_date, "quality": quality, "quality_score": quality_score,
    "warnings": warnings, "criticals": criticals,
    "category_scores": {"A": a_val, "B": b_val, "C": c_val},
    "per_step_scores": {"S1": s1['score'], "S2": s2['score'], "S3": s3['score'], "S4": s4.get('score'), "S5": s5['score']},
    "total_events": total_events, "total_task_objects": total_task_objects,
    "stage2_extended": {"step6": step6_details, "step7": step7_details, "step8": step8_details, "step9": step9_details},
}))
