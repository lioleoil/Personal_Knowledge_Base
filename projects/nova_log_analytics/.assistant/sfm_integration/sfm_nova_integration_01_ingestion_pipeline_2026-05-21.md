# SFM × Nova 통합 설계 전략 1 — 데이터 수집 파이프라인

> **작성일:** 2026-05-21
> **분석 대상:** SV Fleet Manager 1.0-rc / `SFM_Architecture_Report.md`
> **범위:** SFM PostgreSQL → Nova (Databricks) 데이터 수집 전략, Kafka 스트리밍 파이프라인 설계

---

## 1. 수집 전략 개요

SFM은 PostgreSQL 16(Primary DB)과 Kafka MSK를 동시에 운영한다. Nova 통합 시 두 경로를 병행한다.

| 수집 방식 | 소스 | 대상 테이블 | 주기 |
|---|---|---|---|
| **Kafka 스트림** | `{env}.shared.sv-fleet-manager.output` | `change_events` | 실시간 (30s trigger) |
| **배치 스냅샷** | PostgreSQL JDBC | `collection_quality_summaries`, `vehicles`, `odd_*` | 일별 |
| **CDC (옵션)** | Debezium → Kafka → DLT | 전 테이블 변경 추적 필요 시 | 준실시간 |

**기본 방침:** Kafka 스트림 우선 + 마스터/집계 테이블은 일별 배치 스냅샷 병행.
SFM이 이미 `change_events`로 모든 리소스 변경을 이벤트 소싱하므로 이 테이블이 Nova raw 레이어의 핵심 소스다.

---

## 2. 민감 데이터 제외 정책

아래 테이블 및 컬럼은 파이프라인에서 **제외하거나 마스킹**한다. stg 레이어 진입 전에 처리한다.

| 테이블 | 처리 방침 | 이유 |
|---|---|---|
| `refresh_tokens` | **전체 제외** | JWT 갱신 토큰 원본 |
| `api_keys` | **전체 제외** | M2M 자격증명 (key_hash 포함) |
| `audit_logs.ip_address` | **마스킹** (NULL) | 사용자 IP — PII |
| `audit_logs.user_agent` | **마스킹** (NULL) | PII |
| `change_events.actor_email` | **SHA256 해시** | stg 레이어에서 변환 |
| `users.password_hash` | **전체 제외** | Bcrypt 해시 불필요 |

`audit_logs`의 `action`, `resource_type`은 행동 분석 용도로 허용한다.

---

## 3. Kafka → raw 레이어 파이프라인

### 3.1 raw 스키마 정의

```python
from pyspark.sql.types import *

raw_schema = StructType([
    StructField("event_id",         LongType(),    False),
    StructField("event_type",       StringType(),  False),  # created/updated/deleted
    StructField("resource_type",    StringType(),  False),
    StructField("resource_uuid",    StringType(),  False),
    StructField("resource_version", IntegerType(), True),
    StructField("parent_uuid",      StringType(),  True),
    StructField("actor_email",      StringType(),  True),
    StructField("payload",          StringType(),  True),   # JSONB → String 수신
    StructField("webhook_status",   StringType(),  True),
    StructField("kafka_status",     StringType(),  True),
    StructField("created_at",       TimestampType(), False),
])
```

### 3.2 Kafka → raw Delta 스트림

```python
from pyspark.sql import functions as F

KAFKA_BOOTSTRAP = spark.conf.get("sfm.kafka.bootstrap_servers")
KAFKA_TOPIC     = spark.conf.get("sfm.kafka.topic")   # {env}.shared.sv-fleet-manager.output
CHECKPOINT_BASE = "dbfs:/mnt/nova/checkpoints/sfm"

raw_stream = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
    .option("subscribe", KAFKA_TOPIC)
    .option("startingOffsets", "latest")
    .option("failOnDataLoss", "false")
    .option("kafka.security.protocol", "SASL_SSL")
    .option("kafka.sasl.mechanism", "AWS_MSK_IAM")
    .load()
    .select(
        F.col("offset"),
        F.col("partition"),
        F.col("timestamp").alias("kafka_timestamp"),
        F.from_json(F.col("value").cast("string"), raw_schema).alias("d")
    )
    .select("offset", "partition", "kafka_timestamp", "d.*")
    .withWatermark("created_at", "10 minutes")   # 10분 지연 허용
)

(
    raw_stream.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", f"{CHECKPOINT_BASE}/raw_sfm_change_events")
    .partitionBy("resource_type", F.to_date("created_at").alias("event_date"))
    .trigger(processingTime="30 seconds")
    .toTable("nova_raw.raw_sfm_change_events")
)
```

---

## 4. raw → stg 레이어 파이프라인

### 4.1 파생 흐름

```
raw_sfm_change_events
        │ foreachBatch (60s trigger)
        ▼
stg_sfm_change_events          ← payload 파싱, actor_email SHA256, resource_type별 분기
        │
        ├─→ int_sfm_vehicle_changes      (resource_type = 'vehicle')
        ├─→ int_sfm_config_changes       (resource_type = 'config')
        ├─→ int_sfm_collection_changes   (resource_type = 'collection_session')
        └─→ int_sfm_sensor_changes       (resource_type IN ('camera','lidar'))
```

### 4.2 stg 변환 로직

```python
def parse_payload(df, batch_id):
    df.createOrReplaceTempView("_batch")
    spark.sql("""
        INSERT INTO nova_stg.stg_sfm_change_events
        SELECT
          event_id,
          event_type,
          resource_type,
          resource_uuid,
          resource_version,
          parent_uuid,
          SHA2(actor_email, 256)                        AS actor_email_hash,
          CASE resource_type
            WHEN 'vehicle'            THEN GET_JSON_OBJECT(payload, '$.status')
            WHEN 'collection_session' THEN GET_JSON_OBJECT(payload, '$.quality_grade')
            ELSE NULL
          END                                           AS payload_status,
          CASE resource_type
            WHEN 'collection_session' THEN
              CAST(GET_JSON_OBJECT(payload, '$.drop_rate') AS DOUBLE)
            ELSE NULL
          END                                           AS payload_drop_rate,
          created_at,
          DATE(created_at)                              AS event_date,
          kafka_timestamp
        FROM _batch
        WHERE event_id IS NOT NULL
    """)

(
    spark.readStream
    .table("nova_raw.raw_sfm_change_events")
    .writeStream
    .foreachBatch(parse_payload)
    .option("checkpointLocation", f"{CHECKPOINT_BASE}/stg_sfm_change_events")
    .trigger(processingTime="60 seconds")
    .start()
)
```

---

## 5. 스키마 복잡성 — JSONB / Array 컬럼 처리 기준

| 테이블 | JSONB 컬럼 | stg 처리 방향 |
|---|---|---|
| `vehicle_config` | `network`, `thresholds`, `can_active_sensors` | struct 분해, 필요 필드만 추출 |
| `collection_sessions` | `meta_info` | 필요 필드만 추출 |
| `camera_parameters` | `intrinsic_params`, `extrinsic_params` | 캘리브레이션 분석 시 별도 파싱 |
| `session_odd_tags` | `tag_value` (GIN 인덱스) | ODD 분포 분석 시 explode |
| `change_events` | `payload` | resource_type별 분기 파싱 (§4.2) |

---

## 6. Registry + Versions 패턴 처리

SFM의 `vehicle_registry + vehicles(version N)` 구조는 Databricks에서 **int/dim 레이어에서 평탄화**한다.

```sql
-- int 레이어에서 최신 버전만 추출 (버전 조인 제거)
SELECT v.*
FROM vehicles v
JOIN vehicle_registry r
  ON  r.uuid = v.uuid
 AND  v.version = r.latest_version
```

결과물: `dim_vehicle` (SCD Type 2), `dim_vehicle_config` (config 버전 평탄화)

---

## 7. 운영 고려사항

| 항목 | 설정 |
|---|---|
| **Exactly-once** | Delta + checkpoint (Kafka offset 관리) |
| **스키마 진화** | `mergeSchema = true` + Alembic 마이그레이션 알림 연동 |
| **payload 용량** | SFM `change_events` 90일 retention 반영, raw 파티션 TTL 설정 |
| **재처리** | `startingOffsets = "earliest"` + checkpoint 삭제로 full replay 가능 |
| **PTP 시각 보정** | `vehicle_location_histories.ptp_offset_us` 기반 수집 시간 보정 필요 |

```sql
-- stg 레이어 PTP 보정 예시
start_time + INTERVAL (ptp_offset_us / 1000000) SECOND AS corrected_start_time
```

---

## 8. 통합 수집 우선순위

| 우선순위 | 대상 테이블 | 수집 방식 | 이유 |
|---|---|---|---|
| **P0** | `change_events` (Kafka) | 스트림 | 모든 리소스 변경의 단일 소스 |
| **P0** | `collection_sessions`, `collection_quality_summaries` | 배치 | 수집 품질 KPI 직접 소스 |
| **P1** | `vehicles` (최신 버전), `vehicle_config` | 배치 | 차량 dim 구성 |
| **P1** | `session_odd_tags`, `odd_attributes` | 배치 | MV2 feature 분포 분석 |
| **P2** | `audit_logs` (제한적) | 배치 | 운영자 행동 패턴 분석 |
| **P3** | `camera_parameters`, `lidar_calibrations` | 배치 | 센서 캘리브레이션 변경 영향 |

---

*관련 문서: [`sfm_nova_integration_02_analytics_data_model_2026-05-21.md`](./sfm_nova_integration_02_analytics_data_model_2026-05-21.md)*
