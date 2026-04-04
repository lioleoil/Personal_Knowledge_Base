# 네이밍 규칙 (DIC-788)

## 파일 네이밍

| 계층 | 패턴 | 예시 |
|------|------|------|
| raw | `raw_[domain]__[entity]_[connector].py` | `raw_labelit__atlas_collections_mongodb.py` |
| staging | `base_[domain]__[entity].sql` 또는 `stg_[domain]__[entity].sql` | `base_labelit__data_item.sql` |
| intermediate | `int_[domain]__[entity]_[verb].sql` | `int_datacenter__raw_data_enriched.sql` |
| marts | `[entity].sql` (snake_case) | `annotation.sql` |

- MUST: `__` (이중 언더스코어)로 도메인과 엔티티 구분
- MUST: 테이블명은 **복수형**, **snake_case** (하이픈, 도트 금지)
- MUST: task_key = 파일명 (확장자 제외) 그대로 사용

## Connector Suffix (raw 계층 필수)

| 카테고리 | suffix |
|----------|--------|
| Databases | `_mysql`, `_postgresql`, `_mongodb`, `_oracle` |
| Events | `_kafka`, `_kinesis`, `_pubsub`, `_eventhub`, `_zerobus` |
| Files | `_s3`, `_gcs`, `_adls`, `_autoloader` |
| File Servers | `_sftp`, `_qumulo` |
| Applications | `_api` |
| Managed | `_lakeflow` |

## Verb Suffix

| 용도 | 허용 suffix |
|------|------------|
| base (서비스 내부 join) | `_joined`, `_unioned`, `_merged`, `_pivoted` |
| int (서비스 간 join) | `_matched`, `_joined`, `_enriched`, `_aggregated`, `_filtered`, `_ranked` |

## 컬럼 네이밍

| 유형 | 규칙 | 예시 |
|------|------|------|
| Primary key | `{entity}_id` (string) | `customer_id` |
| Boolean | `is_` 또는 `has_` prefix | `is_completed`, `has_attachment` |
| Timestamp | `{event}_at` (UTC) | `created_at`, `updated_at` |
| Date | `{event}_date` | `created_date` |
| 금액 | 소수점 또는 `_in_cents` suffix | `price`, `amount_in_cents` |

- MUST NOT: 약어 사용 금지 (`cust` → `customer`, `o` → `order`)
- MUST: 비즈니스 용어 우선 (소스에서 `user_id`여도 비즈니스에서 customer면 `customer_id`)

## Resource YAML 네이밍

패턴: `{계층}_{서비스}__{트리거}.yml` 또는 `{계층}__{트리거}.yml` (도메인 없는 통합 job)

허용 트리거: `daily`, `hourly`, `streaming`, `event`, `ondemand`

## DABs 리소스 네이밍

| 항목 | 형식 | 예시 |
|------|------|------|
| bundle name | kebab-case | `sv-data-pipeline` |
| target name | 짧은 소문자 | `dev`, `prod` |
| resource key | snake_case (`__`로 구분) | `raw_labelit__streaming` |
| task key | 파일명 (확장자 제외) | `raw_labelit__atlas_collections_mongodb` |
| variable name | snake_case | `warehouse_id` |

## Unity Catalog

| 환경 | Catalog |
|------|---------|
| dev | `sv_nova_dev_an2_catalog` |
| prod | `sv_nova_prod_an2_catalog` |

스키마: `raw`, `staging`, `intermediate`, `marts`

## Secret Scope 네이밍

패턴: `{org}-{connector}-{service|shared}-{env}`

```
sv-mongo-labelit-dev
│    │     │       │
org  conn  service env(소스 환경)
```

- env는 **소스 환경** (워크스페이스 환경이 아님) — dev WS에서 prod MongoDB 접근 가능
- S3 인증은 External Location (Unity Catalog) / Instance Profile → Terraform 영역
- `config`도 connector로 취급 (non-sensitive 설정 저장)

**관리:** `secrets/` 디렉토리의 YAML + 스크립트

```bash
cp secrets/secrets.example.yml secrets/secrets.dev.yml
vi secrets/secrets.dev.yml    # 실제 값 입력
./secrets/register-secrets.sh dev
```

## Checkpoint 네이밍

패턴: `{bucket}/checkpoints/{connector_type}/{connector}/{domain}-{env}/{collection}`

```
s3://sv-nova-dev-an2-s3-uc-metastore/.../checkpoints/databases/mongodb/labelit-dev/classtype
│                                                     │          │       │      │    │
│                                                     │          │       │      │    collection (소문자)
│                                                     │          │       │      env (소스 DB 환경)
│                                                     │          │       domain (서비스명)
│                                                     │          connector (기술)
│                                                     connector_type (connectors/ 하위 디렉토리)
bucket (환경별 S3)
```

| 세그먼트 | 설명 | 예시 |
|----------|------|------|
| connector_type | `connectors/` 하위 디렉토리 | `databases`, `streams`, `apis` |
| connector | 구체적 기술 | `mongodb`, `mysql`, `kafka` |
| domain | 서비스/도메인명 | `labelit`, `datacenter` |
| env | 소스 DB 환경 | `dev`, `prod` |
| collection | 소스 엔티티 (소문자) | `classtype`, `calibration` |

예시:

```
databases/mongodb/labelit-dev/classtype
databases/mongodb/labelit-prod/classtype
databases/mongodb/datacenter-dev/calibration
databases/mysql/auth-prod/users
streams/kafka/events-prod/clicks
```

- MUST: `{domain}-{env}`로 소스 환경 명시 — Secret Scope의 `{service}-{env}`와 일치
- MUST: collection은 소문자
- MUST: checkpoint_location은 Secret Scope에서 관리 (key: `checkpoint_location`)
