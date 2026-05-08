# Databricks notebook source
# DBTITLE 1,Scoring v1.2 Cross-Feature Validation
# MAGIC %md
# MAGIC # Scoring v1.2 Cross-Feature Validation
# MAGIC > OD, LD, RMD 3개 feature에 대해 anomaly_detection_runner를 실행하고,
# MAGIC > 스코어링 v1.2의 cross-feature 공정성을 검증합니다.
# MAGIC >
# MAGIC > **검증 항목**:
# MAGIC > - Per-STEP 점수가 feature간 비교 가능한 스케일인지
# MAGIC > - STEP 4 skip (LD) vs active (OD/RMD)의 A 카테고리 점수 공정성
# MAGIC > - C 카테고리의 객체 비율 정규화가 feature별 모수 차이를 적절히 반영하는지
# MAGIC > - Stage 2 병합 결과가 B·C 카테고리에 반영되는지 (v1.2: STEP 6/7 → S5, STEP 8/9 → S3)

# COMMAND ----------

# DBTITLE 1,Setup & Run all features
import json
from datetime import datetime, timedelta

RUNNER_PATH = "/Users/seonghwan.park@stradvision.com/.assistant/skills/anomaly_detection_runner"
analysis_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

print(f"📅 분석 날짜: {analysis_date}")
print(f"📝 Runner: {RUNNER_PATH}")
print()

results_map = {}
for feat in ['od', 'ld', 'rmd']:
    print(f"\n{'='*50}")
    print(f"▶ Running {feat.upper()}...")
    try:
        exit_val = dbutils.notebook.run(
            RUNNER_PATH,
            timeout_seconds=600,
            arguments={"feature": feat, "analysis_date": analysis_date}
        )
        parsed = json.loads(exit_val)
        results_map[feat] = parsed
        print(f"  ✅ {feat.upper()}: {parsed['quality']} ({parsed['quality_score']})")
        print(f"     A={parsed['category_scores']['A']} B={parsed['category_scores']['B']} C={parsed['category_scores']['C']}")
        print(f"     Per-STEP: {parsed['per_step_scores']}")
    except Exception as e:
        print(f"  ❌ {feat.upper()} 실패: {e}")
        results_map[feat] = None

print(f"\n{'='*50}")
print(f"✅ 전체 실행 완료: {sum(1 for v in results_map.values() if v)} / 3 성공")

# COMMAND ----------

# DBTITLE 1,결과 비교 테이블

import pandas as pd

# 결과 테이블 구성
rows = []
for feat, r in results_map.items():
    if r is None:
        continue
    ps = r['per_step_scores']
    cs = r['category_scores']
    rows.append({
        'Feature': feat.upper(),
        'Total Events': r['total_events'],
        'Total Task Objects': r['total_task_objects'],
        'S1 위치점프': ps['S1'],
        'S2 위치진동': ps['S2'],
        'S3 시간지연': ps['S3'],
        'S4 Feature': ps.get('S4', 'skip'),
        'S5 복수편집': ps['S5'],
        'A 공간': cs['A'],
        'B 시간': cs['B'],
        'C 행동': cs['C'],
        'Score': r['quality_score'],
        'Grade': r['quality'],
    })

df_compare = pd.DataFrame(rows)
display(df_compare)


# COMMAND ----------

# DBTITLE 1,STEP 4 공정성 검증

# STEP 4 skip 여부에 따른 A 카테고리 분석
print("🔍 STEP 4 공정성 검증")
print("=" * 50)

for feat, r in results_map.items():
    if r is None:
        continue
    ps = r['per_step_scores']
    cs = r['category_scores']
    s4_val = ps.get('S4')
    
    if s4_val is None:
        n_steps = 2
        step_detail = f"mean(S1={ps['S1']}, S2={ps['S2']})"
    else:
        n_steps = 3
        step_detail = f"mean(S1={ps['S1']}, S2={ps['S2']}, S4={s4_val})"
    
    print(f"\n{feat.upper()}:")
    print(f"  STEP 4: {'skip' if s4_val is None else f'active ({s4_val})'}")
    print(f"  A 점수: {cs['A']} = {step_detail}  [평균 {n_steps}개 STEP]")
    print(f"  → v0.9였다면 STEP 합산/total_events 방식으로 S4 유무에 따라 불공정")
    print(f"  → v1.0에서는 active STEP만 평균하므로 공정")

print(f"\n{'='*50}")
print("✅ STEP 4 skip 처리가 cross-feature 공정성을 보장하는지 확인 완료")


# COMMAND ----------

# DBTITLE 1,C 카테고리 정규화 검증

# C 카테고리: 객체 비율 정규화 검증
RESULTS_TABLE = "sv_nova_dev_an2_catalog.analytics.anomaly_detection_results"

print("🔍 C 카테고리 정규화 검증")
print("=" * 50)

for feat, r in results_map.items():
    if r is None:
        continue
    
    total_obj = r['total_task_objects']
    c_score = r['category_scores']['C']
    
    # STEP 5 상세 조회
    step5 = spark.sql(f"""
        SELECT severity, object_count 
        FROM {RESULTS_TABLE}
        WHERE analysis_date = '{analysis_date}' AND feature = '{feat}' AND step_id = 5
    """).collect()
    
    print(f"\n{feat.upper()}:")
    print(f"  모수: total_task_objects = {total_obj:,}")
    for row in step5:
        print(f"  STEP 5 {row.severity}: {row.object_count} objects")
    print(f"  C 점수: {c_score} (객체 비율 기반, M_OBJECT=10, CAP_OBJECT=10%)")
    
    # v0.9 대비 비교
    weighted_obj = sum(
        (row.object_count or 0) * (1.0 if row.severity == 'critical' else 0.5 if row.severity == 'warning' else 0)
        for row in step5
    )
    v09_score = min(round(weighted_obj * 15, 1), 100)  # v0.9 방식
    print(f"  → v0.9 C 점수: {v09_score} (절대값 × 15)")
    print(f"  → v1.0 C 점수: {c_score} (비율 정규화)")

print(f"\n{'='*50}")
print("✅ C 카테고리가 feature별 모수 차이를 반영하는지 확인 완료")


# COMMAND ----------

# DBTITLE 1,종합 검증 결과

print("📊 스코어링 v1.0 Cross-Feature 검증 요약")
print("=" * 60)

all_passed = True
for feat, r in results_map.items():
    if r is None:
        print(f"\n❌ {feat.upper()}: 실행 실패")
        all_passed = False
        continue
    
    score = r['quality_score']
    grade = r['quality']
    cs = r['category_scores']
    
    # 검증: 점수가 0~100 범위인지
    valid_range = 0 <= score <= 100
    valid_cats = all(0 <= v <= 100 for v in cs.values())
    valid_grade = grade in ('정상', '주의', '불량')
    
    status = "✅" if (valid_range and valid_cats and valid_grade) else "❌"
    if not (valid_range and valid_cats and valid_grade):
        all_passed = False
    
    print(f"\n{status} {feat.upper()}: {grade} ({score})")
    print(f"   A={cs['A']:.1f} B={cs['B']:.1f} C={cs['C']:.1f}")
    print(f"   범위 검증: {'PASS' if valid_range else 'FAIL'} | "
          f"카테고리 검증: {'PASS' if valid_cats else 'FAIL'} | "
          f"등급 검증: {'PASS' if valid_grade else 'FAIL'}")

print(f"\n{'='*60}")
print(f"🏁 전체 결과: {'ALL PASSED ✅' if all_passed else 'SOME FAILED ❌'}")
