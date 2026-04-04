# 커넥터 & 데이터 수집 규칙

## 구조

```
connectors/databases/
├── mongodb.py              # MongoDBCDC 엔진 (순수 로직, 외부 의존 없음)
└── utils.py                # dedup 유틸

ingests/
└── raw__sync_mongodb.py    # 단일 진입점 (DI로 조립)
```

| 디렉토리 | 역할 |
|----------|------|
| `connectors/databases/` | CDC 엔진 (어떻게 가져올지) — 커넥터 타입별 재사용 로직 |
| `ingests/` | 노트북 진입점 — Job YAML 파라미터로 엔진 조립 (DI) |

## Config 주입 방식

- Job YAML → notebook parameters → MongoDBCDC 생성자 (DI)
- Secret Scope에서 `connection_string`, `database`, `checkpoint_location` resolve
- `for_each_task`로 컬렉션별 독립 task 생성

## 규칙

- MUST: CDC 엔진 로직 변경은 `connectors/databases/`에서만 수정 (노트북 수정 금지)
- MUST NOT: 노트북에 connection URI, collection 목록 등 하드코딩
- MUST: 새 소스 추가 시 Secret Scope 등록 + Job YAML 작성

## Raw 테이블 스키마

Raw 테이블은 고정 5컬럼 JSON 스키마를 사용한다 (ADR-003 참조).
MongoDB 문서 전체를 `$function` (JS `JSON.stringify`)으로 JSON 문자열 변환 후 `_raw`에 저장.

```
_id          STRING      — MongoDB document _id (string)
_raw         STRING      — 전체 문서 JSON string
_op          STRING      — 작업 유형 (init, upsert)
_ingested_at TIMESTAMP   — 수집 시각
_is_deleted  BOOLEAN     — 소프트 삭제 플래그
```

**Init 전략:** Spark Connector + All-StringType Schema (스키마 추론 → StringType 재읽기 → UDF JSON 재조합)

**Stream 전략:** Structured Streaming + forEachBatch MERGE upsert + hard delete

**Staging에서 필드 추출 (`:` 구문):**

```sql
SELECT
    _id,
    _raw:name::STRING AS name,
    _raw:status::STRING AS status
FROM ${catalog}.raw.raw_labelit__feature
```

- MUST: 대용량 컬렉션 초기적재는 Spark Connector batch read 사용 (Spark 분산 처리)
- MUST: incremental은 Spark Structured Streaming + `availableNow=True`
- MUST: staging에서 `:` 구문으로 `_raw`에서 필요한 필드만 명시적 추출

## Job Cluster 패턴

| 클러스터 용도 | job_cluster_key | 특징 |
|--------------|-----------------|------|
| CDC ingest | `cdc_cluster` | Spark MongoDB Connector 사용 |
| Transform | `transform_cluster` | staging/intermediate/marts 공용 |

- MUST: Job YAML에서 `job_clusters` + `job_cluster_key` 패턴 사용
- MUST NOT: task 레벨에서 `new_cluster` 인라인 정의 (클러스터 설정 중복 방지)
