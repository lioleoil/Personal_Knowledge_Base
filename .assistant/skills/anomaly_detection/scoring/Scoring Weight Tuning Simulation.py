# Databricks notebook source
# DBTITLE 1,Weight Tuning Simulation
# MAGIC %md
# MAGIC # 스코어링 가중치 튜닝 시뮬레이션
# MAGIC > anomaly_detection_results 테이블의 실제 데이터를 기반으로
# MAGIC > W_A, W_B, W_C 및 CAP_EVENT/CAP_OBJECT 파라미터를 변경하며 품질 점수 변화를 시뮬레이션합니다.
# MAGIC >
# MAGIC > **스코어링 v1.2 기준**: Stage 2(STEP 6/7 → step_id=5, STEP 8/9 → step_id=3) 병합 포함
# MAGIC > B(S3)·C(S5) 집계 시 Stage 2 결과가 results 테이블에 이미 반영되어 있으므로 수식 변경 없이 자동 포함됨.
# MAGIC >
# MAGIC > **전제**: anomaly_detection_runner v1.2가 3개 feature(OD/LD/RMD)에 대해 실행된 상태

# COMMAND ----------

# DBTITLE 1,실제 데이터 로드

import pandas as pd
import numpy as np
from itertools import product

RESULTS_TABLE = "sv_nova_dev_an2_catalog.analytics.anomaly_detection_results"
REPORTS_TABLE = "sv_nova_dev_an2_catalog.analytics.anomaly_detection_reports"

# 최신 분석 날짜 조회
latest = spark.sql(f"""
    SELECT DISTINCT feature, analysis_date, 
           SUM(CASE WHEN severity='warning' THEN 1 ELSE 0 END) AS warnings,
           SUM(CASE WHEN severity='critical' THEN 1 ELSE 0 END) AS criticals
    FROM {RESULTS_TABLE}
    GROUP BY feature, analysis_date
    ORDER BY analysis_date DESC, feature
""").toPandas()

print("📊 사용 가능한 데이터:")
display(latest)

# 날짜 선택 (가장 최신)
analysis_date = latest['analysis_date'].iloc[0] if len(latest) > 0 else None
assert analysis_date is not None, "❌ 분석 데이터가 없습니다. anomaly_detection_runner를 먼저 실행해주세요."
print(f"\n📅 시뮬레이션 대상 날짜: {analysis_date}")


# COMMAND ----------

# DBTITLE 1,Feature별 raw metrics 추출

# Feature별 STEP 결과 로드
def load_feature_metrics(feat, date):
    """각 Feature의 STEP별 결과를 로드하여 스코어링에 필요한 raw metrics 반환"""
    rows = spark.sql(f"""
        SELECT step_id, severity, event_count, object_count
        FROM {RESULTS_TABLE}
        WHERE analysis_date = '{date}' AND feature = '{feat}'
        ORDER BY step_id, severity
    """).collect()
    
    # 모수
    step0 = [r for r in rows if r.step_id == 0]
    total_events = step0[0].event_count if step0 else 0
    
    # total_task_objects는 reports에서 가져오기
    report = spark.sql(f"""
        SELECT scoring_details FROM {REPORTS_TABLE}
        WHERE analysis_date = '{date}' AND feature = '{feat}'
    """).collect()
    
    import json
    total_task_objects = 0
    if report:
        details = json.loads(report[0].scoring_details)
        total_task_objects = details.get('population', {}).get('total_task_objects', 0)
    
    # STEP 4 active 여부 (feature config 기반)
    STEP4_CONFIG = {'od': True, 'ld': False, 'rmd': True}
    step4_active = STEP4_CONFIG.get(feat, False)
    
    return {
        'feature': feat,
        'total_events': total_events,
        'total_task_objects': total_task_objects,
        'step4_active': step4_active,
        'rows': rows,
    }

features_data = {}
for feat in ['od', 'ld', 'rmd']:
    try:
        features_data[feat] = load_feature_metrics(feat, analysis_date)
        m = features_data[feat]
        print(f"✅ {feat.upper()}: events={m['total_events']:,} | task_objects={m['total_task_objects']:,} | S4={'active' if m['step4_active'] else 'skip'}")
    except Exception as e:
        print(f"❌ {feat.upper()}: {e}")


# COMMAND ----------

# DBTITLE 1,스코어링 함수 정의

def get_finding_weight(step_id, severity):
    if step_id in (1, 2, 4):
        return 1.0 if severity == 'critical' else 0.0
    elif step_id == 3:
        return {'critical': 1.0, 'warning': 0.5}.get(severity, 0.0)
    elif step_id >= 5:
        return {'critical': 1.0, 'warning': 0.5}.get(severity, 0.0)
    return 0.0

def compute_quality_score(feat_data, W_A, W_B, W_C, CAP_EVENT=5.0, CAP_OBJECT=10.0):
    """주어진 파라미터로 품질 점수 계산 (CAP 비율 기반)
    CAP_EVENT: 이벤트 이상 비율 cap (%) → M_EVENT = 100/CAP_EVENT
    CAP_OBJECT: 객체 충돌 비율 cap (%) → M_OBJECT = 100/CAP_OBJECT
    """
    rows = feat_data['rows']
    total_events = feat_data['total_events']
    total_task_objects = feat_data['total_task_objects']
    step4_active = feat_data['step4_active']
    
    M_EVENT = 100 / CAP_EVENT
    M_OBJECT = 100 / CAP_OBJECT
    
    def step_score(step_id, use_objects=False):
        metric = 'object_count' if use_objects else 'event_count'
        weighted = sum(
            (getattr(r, metric) or 0) * get_finding_weight(r.step_id, r.severity)
            for r in rows if r.step_id == step_id
        )
        denom = total_task_objects if use_objects else total_events
        mult = M_OBJECT if use_objects else M_EVENT
        rate = weighted / denom * 100 if denom > 0 else 0
        return min(round(rate * mult, 1), 100)
    
    s1 = step_score(1)
    s2 = step_score(2)
    s3 = step_score(3)
    s5 = step_score(5, use_objects=True)
    s4 = step_score(4) if step4_active else None
    
    a_scores = [s1, s2] + ([s4] if step4_active else [])
    a = round(sum(a_scores) / len(a_scores), 1)
    b = s3
    c = s5
    
    score = round(W_A * a + W_B * b + W_C * c, 1)
    
    if score <= 20: grade = '정상'
    elif score <= 45: grade = '주의'
    else: grade = '불량'
    
    return {'score': score, 'grade': grade, 'A': a, 'B': b, 'C': c,
            'per_step': {'S1': s1, 'S2': s2, 'S3': s3, 'S4': s4, 'S5': s5}}

# 현재 설정 기준 확인 (CAP_EVENT=5%, CAP_OBJECT=10%)
print("📊 현재 스코어링 v1.2 기준 (CAP_EVENT=5%, CAP_OBJECT=10%)")
for feat, data in features_data.items():
    r = compute_quality_score(data, 0.40, 0.40, 0.20, CAP_EVENT=5.0, CAP_OBJECT=10.0)
    print(f"  {feat.upper()}: {r['grade']} ({r['score']}) | A={r['A']} B={r['B']} C={r['C']}")
    print(f"         S1={r['per_step']['S1']} S2={r['per_step']['S2']} S3={r['per_step']['S3']} "
          f"S4={r['per_step']['S4']} S5={r['per_step']['S5']}")


# COMMAND ----------

# DBTITLE 1,카테고리 가중치 시뮬레이션

# W_A, W_B, W_C 조합 시뮬레이션 (CAP_EVENT=5%, CAP_OBJECT=10% 고정)
weight_combos = [
    (0.50, 0.30, 0.20, 'A중심'),
    (0.40, 0.40, 0.20, 'v1.2 기본'),
    (0.30, 0.50, 0.20, 'B중심'),
    (0.35, 0.35, 0.30, 'C강화'),
    (0.40, 0.35, 0.25, 'v0.9 기본'),
    (0.33, 0.33, 0.34, '균등'),
    (0.45, 0.45, 0.10, 'C최소'),
]

result_rows = []
for w_a, w_b, w_c, label in weight_combos:
    for feat, data in features_data.items():
        r = compute_quality_score(data, w_a, w_b, w_c, CAP_EVENT=5.0, CAP_OBJECT=10.0)
        result_rows.append({
            '가중치': label,
            'W_A': w_a, 'W_B': w_b, 'W_C': w_c,
            'Feature': feat.upper(),
            'A': r['A'], 'B': r['B'], 'C': r['C'],
            'Score': r['score'],
            'Grade': r['grade'],
        })

df_weights = pd.DataFrame(result_rows)

df_pivot = df_weights.pivot_table(index=['가중치', 'W_A', 'W_B', 'W_C'], 
                                   columns='Feature', values='Score').reset_index()
df_pivot.columns.name = None
print("📊 카테고리 가중치 시뮬레이션 (CAP_EVENT=5%, CAP_OBJECT=10% 고정)")
display(df_pivot)


# COMMAND ----------

# DBTITLE 1,감도 배수 시뮬레이션

# CAP_EVENT, CAP_OBJECT 조합 시뮬레이션 (cap 비율 기반)
CAP_EVENT_range  = [2, 3, 5, 8, 10]    # 이벤트 cap %
CAP_OBJECT_range = [5, 10, 15, 20, 30]  # 객체 cap %

sens_rows = []
for cap_e, cap_o in product(CAP_EVENT_range, CAP_OBJECT_range):
    for feat, data in features_data.items():
        r = compute_quality_score(data, 0.40, 0.40, 0.20, CAP_EVENT=cap_e, CAP_OBJECT=cap_o)
        sens_rows.append({
            'CAP_EVENT': cap_e, 'CAP_OBJECT': cap_o,
            'Feature': feat.upper(),
            'A': r['A'], 'B': r['B'], 'C': r['C'],
            'Score': r['score'], 'Grade': r['grade'],
        })

df_sens = pd.DataFrame(sens_rows)

for feat in ['OD', 'LD', 'RMD']:
    sub = df_sens[df_sens['Feature'] == feat].pivot_table(
        index='CAP_EVENT', columns='CAP_OBJECT', values='Score'
    )
    print(f"\n📊 {feat} - CAP 비율 조합별 Score (CAP_EVENT=행%, CAP_OBJECT=열%)")
    display(sub)


# COMMAND ----------

# DBTITLE 1,감도 배수 Heatmap

import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'DejaVu Sans'

fig, axes = plt.subplots(1, len(features_data), figsize=(5*len(features_data), 4))
if len(features_data) == 1:
    axes = [axes]

for idx, feat in enumerate(['od', 'ld', 'rmd']):
    if feat not in features_data:
        continue
    sub = df_sens[df_sens['Feature'] == feat.upper()].pivot_table(
        index='CAP_EVENT', columns='CAP_OBJECT', values='Score'
    )
    
    ax = axes[idx]
    im = ax.imshow(sub.values, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=60)
    ax.set_xticks(range(len(sub.columns)))
    ax.set_xticklabels([f"{v}%" for v in sub.columns])
    ax.set_yticks(range(len(sub.index)))
    ax.set_yticklabels([f"{v}%" for v in sub.index])
    ax.set_xlabel('CAP_OBJECT (%)')
    ax.set_ylabel('CAP_EVENT (%)')
    ax.set_title(f'{feat.upper()}')
    
    for i in range(len(sub.index)):
        for j in range(len(sub.columns)):
            val = sub.values[i, j]
            color = 'white' if val > 30 else 'black'
            ax.text(j, i, f'{val:.1f}', ha='center', va='center', fontsize=8, color=color)

fig.suptitle('CAP Rate Sensitivity Simulation (Quality Score)', fontsize=14, y=1.02)
plt.colorbar(im, ax=axes, shrink=0.8, label='Quality Score')
plt.tight_layout()
plt.show()


# COMMAND ----------

# DBTITLE 1,최적 파라미터 추천

print("🎯 최적 파라미터 추천 (CAP 비율 기반)")
print("=" * 60)

# 가중치 시뮬레이션
print("\n▶ 카테고리 가중치 (feature간 점수 분산 최소화):")
for label in df_weights['가중치'].unique():
    sub = df_weights[df_weights['가중치'] == label]
    scores = sub['Score'].values
    std = np.std(scores)
    mean = np.mean(scores)
    grade_dist = sub['Grade'].value_counts().to_dict()
    w_row = sub.iloc[0]
    print(f"  {label:12s} (W={w_row['W_A']}/{w_row['W_B']}/{w_row['W_C']}): "
          f"mean={mean:.1f} std={std:.1f} | {grade_dist}")

# CAP 감도 시뮬레이션
print("\n▶ CAP 비율 (feature간 점수 분산 최소화):")
best_sens = []
for (cap_e, cap_o), grp in df_sens.groupby(['CAP_EVENT', 'CAP_OBJECT']):
    scores = grp['Score'].values
    std = np.std(scores)
    mean = np.mean(scores)
    best_sens.append((cap_e, cap_o, mean, std))

best_sens.sort(key=lambda x: x[3])
for cap_e, cap_o, mean, std in best_sens[:5]:
    print(f"  CAP_EVENT={cap_e:2d}%, CAP_OBJECT={cap_o:2d}%: mean={mean:.1f} std={std:.1f}")

print(f"\n{'='*60}")
print("💡 CAP 비율이 높을수록 관대한 평가 (점수 낮아짐), 낮을수록 엄격한 평가 (점수 높아짐)")
print("💡 std가 작을수록 feature간 공정한 평가. 현재 설정(v1.2): CAP_EVENT=5%, CAP_OBJECT=10%")
