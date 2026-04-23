# SQL 노트북 패턴

## 금지 사항

- MUST NOT: staging/intermediate/marts에서 `SELECT *` 사용 (pre-commit으로 차단됨)
- MUST NOT: SQL 노트북에서 `${var.catalog}` 사용 → `${catalog}` 위젯으로 주입
- MUST NOT: resource YAML에서 절대 경로 사용 → YAML 파일 위치 기준 상대 경로 (예: `../../models/raw/...`)

## 필수 사항

- MUST: DABs Job `depends_on`으로 실행 순서 보장
- MUST: staging/intermediate/marts 노트북은 아래 3블록 구조를 따른다

## 노트북 템플릿

```sql
-- Databricks notebook source
-- task_key: base_{domain}__{entity}

-- 테이블 생성
CREATE OR REPLACE TABLE ${catalog}.staging.base_{domain}__{entity} AS
...;

-- COMMAND ----------

-- 테이블/컬럼 문서화 (Catalog Explorer에서 조회 가능)
COMMENT ON TABLE ${catalog}.staging.base_{domain}__{entity} IS '{소스} 정제. {핵심 비즈니스 룰 요약}';

ALTER TABLE ${catalog}.staging.base_{domain}__{entity}
  ALTER COLUMN {col} SET COMMENT '설명';

-- COMMAND ----------

-- 품질 제약 (Delta Lake가 자동 검증)
ALTER TABLE ${catalog}.staging.base_{domain}__{entity}
  ADD CONSTRAINT {약칭}_pk_not_null CHECK ({pk} IS NOT NULL);
```

## COMMENT ON 규칙

**테이블 COMMENT:** MUST — 한 줄로 `'{소스} 정제. {핵심 비즈니스 룰 요약}'`

**컬럼 COMMENT:** 아래 경우에만 작성. 자명한 컬럼(`name`, `created_at`)에는 달지 않는다.

- 변환이 비자명한 컬럼 (예: `LOWER(HEX(_id))` — MongoDB Binary → hex string)
- 비즈니스 룰이 내장된 컬럼 (예: `dimension` — flags 기반 2D/3D 판정)
- CASE/매핑 로직이 있는 컬럼 (예: `camera_key` — svc_front → 1536p_h196_bmp_f)
- 파생 컬럼 (예: `scene_index` — name이 숫자일 때만 CAST)

## CHECK CONSTRAINT 규칙

**네이밍:** `{테이블약칭}_{규칙}` — 약칭 예시: `di` (data_item), `rd` (raw_data), `obj` (object)

| 유형 | 필수 여부 | 예시 |
|------|----------|------|
| PK not null | MUST | `_id IS NOT NULL` |
| FK not null | OPTIONAL | `dataset_id IS NOT NULL` |
| 값 범위 | OPTIONAL | `dimension IN ('2D', '3D', 'UNKNOWN')` |

- `CREATE OR REPLACE TABLE`은 매 실행 시 재생성하므로 제약도 매번 재추가된다 (정상 동작)
- CHECK는 이중 안전장치 — SELECT에서 이미 걸러져야 한다
- MUST NOT: 과도한 제약 추가 — 파이프라인을 깨뜨린다. 확실한 것만 건다

## Schema Evolution 전략

| 계층 | 전략 |
|------|------|
| raw | `mergeSchema: true` — 다 받는다. COMMENT ON / CHECK CONSTRAINT 사용하지 않는다 |
| staging | 명시적 SELECT로 방어. 새 컬럼은 PR로만 전파 |
| intermediate / marts | staging과 동일 |
