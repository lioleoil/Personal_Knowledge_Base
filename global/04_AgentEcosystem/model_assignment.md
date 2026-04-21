# 에이전트 모델 배정 설계서

> **버전**: 2.0 | **최종 수정**: 2026-04-12  
> 설정 위치: `global/04_AgentEcosystem/model_config.json`  
> 비용 추적: `.status/openai_usage.json` + Claude Pro 토큰 대시보드

---

## 현행 모델 배정

| 에이전트 | 기본 (default) | cost_optimized | quality_max | 실행 방식 |
|---|---|---|---|---|
| **Execution** | Sonnet 4.6 / temp=0.3 | **Haiku 4.5** / temp=0.3 | Sonnet 4.6 / temp=0.3 | Anthropic SDK |
| **Validation** | gpt-4.1 / temp=0.1 | gpt-4.1-mini / temp=0.1 | gpt-4.1 / temp=0.1 | OpenAI API |
| **Advisor** | Opus 4.7 / temp=0.2 | **Sonnet 4.6** / temp=0.2 | Opus 4.7 / temp=0.1 | Anthropic SDK |
| **Reporter** | gpt-4.1-mini / temp=0.5 | gpt-4.1-mini / temp=0.5 | gpt-4.1 / temp=0.5 | OpenAI API |

## 도메인-프리셋 매핑

| 도메인 | 프리셋 | 근거 |
|---|---|---|
| `daily_scrap` | **cost_optimized** | 뉴스 수집·저장, 구조화 단순 |
| `pkb_worklog` | **cost_optimized** | 파일 분류·인덱싱, 패턴 반복적 |
| `nova_helper` | default | Slack 봇 로직, 중간 복잡도 |
| `nova_log_analytics` | **quality_max** | 이상 탐지·SQL 분석, 오류 비용 높음 |
| `sv_dqat` | **quality_max** | 데이터 품질 검증, 정확도 최우선 |
| `sv_lakehouse` | **quality_max** | 데이터 파이프라인, 신뢰성 최우선 |

---

## 예상 효과 보고서

> 기준: 일일 추정 태스크 60회 (도메인 분포: daily_scrap 30 · pkb_worklog 10 · nova_helper 10 · nova_log_analytics 5 · sv 5)

### Q1 — Execution Haiku 적용 (cost_optimized 프리셋)

**이점**
- Haiku는 Sonnet 대비 응답 속도 **2-3배 빠름** → daily_scrap 30회/일 기준 배치 처리 시간 50% 단축
- Execution 비용 $0.0345 → $0.0029/task (**-92%**)
- 구조화된 Manifest JSON 입력 방식 → Haiku도 안정적으로 파싱 가능
- 실패 시 MAX_EXECUTION_RETRIES(5회) 내 자동 재시도 → 품질 보완 내성 존재

**리스크 완화**
- daily_scrap, pkb_worklog는 domain role_rules가 단순·명확 → Haiku 오작동 확률 낮음
- nova_log_analytics, sv_* 는 quality_max 유지 → 중요 도메인 품질 타협 없음

**A/B 테스트 방법**
```bash
# 현행(default)과 cost_optimized 비교
python .scripts/orchestrator.py --compare                        # 전체 도메인 비용표 출력
python .scripts/orchestrator.py --task "뉴스 스크랩" --domain daily_scrap --dry-run
# → 모델 배정 + 예상 비용 출력 후 확인
python .scripts/orchestrator.py --task "뉴스 스크랩" --domain daily_scrap --auto
```
실제 실행 후 `.agents/<agent_type>/*.json` 로그에서 Haiku 모델 표기 및 성공 여부 확인.

---

### Q2 — Anthropic SDK 직접 호출 (temperature 정밀 제어)

**변경 전 (claude CLI 경유)**
```
orchestrator → subprocess(claude -p prompt) → 모델 미지정, temperature 제어 불가
```

**변경 후 (SDK 직접)**
```
orchestrator → anthropic.messages.create(model=..., temperature=..., max_tokens=...) → 정밀 제어
```

**이점**

| 항목 | CLI 방식 | SDK 방식 |
|---|---|---|
| temperature 제어 | ✗ 불가 | ✓ 0.0-1.0 직접 지정 |
| max_tokens 제어 | ✗ 불가 | ✓ 출력 상한 → 비용 예측 가능 |
| 토큰 사용량 반환 | ✗ | ✓ input/output tokens 직접 획득 |
| 오류 핸들링 | subprocess returncode | exception 계층 구조 |
| claude CLI 의존성 | 필요 | **제거** (API 키만 있으면 동작) |
| 타임아웃 제어 | subprocess.timeout | SDK 내장 |

**Advisor temperature=0.2 효과**  
동일 실패 케이스에 Advisor 3회 호출 시 일관된 `root_cause` 출력 확률 ↑  
이전: 매 호출마다 다른 해결책 제안 가능 → 이후: 재현 가능한 분석 결과

**Execution temperature=0.3 효과**  
창의적 해석보다 Manifest 지시 충실도 ↑ → INSUFFICIENT 판정 빈도 감소 예상

---

### Q3 — 도메인별 프리셋 분기

**아키텍처**

```
run_auto(task, domain)
    └─ run_agent(role, domain)
           └─ get_domain_config(domain, role)
                  ├─ domain_presets["daily_scrap"] = "cost_optimized"
                  │       └─ Haiku + gpt-4.1-mini + Sonnet(Advisor) + gpt-4.1-mini
                  ├─ domain_presets["nova_log_analytics"] = "quality_max"
                  │       └─ Sonnet + gpt-4.1 + Opus + gpt-4.1
                  └─ domain_presets["nova_helper"] = "default"
                          └─ Sonnet + gpt-4.1 + Opus + gpt-4.1-mini
```

**비용 시뮬레이션 (일 60 태스크 기준)**

| 도메인 | 태스크/일 | 프리셋 | $/task | 일 비용 |
|---|---|---|---|---|
| daily_scrap | 30 | cost_optimized | $0.042 | $1.26 |
| pkb_worklog | 10 | cost_optimized | $0.042 | $0.42 |
| nova_helper | 10 | default | $0.096 | $0.96 |
| nova_log_analytics | 5 | quality_max | $0.124 | $0.62 |
| sv_dqat + sv_lakehouse | 5 | quality_max | $0.124 | $0.62 |
| **합계** | **60** | — | **avg $0.065** | **$3.88** |

**비교 (전체 default 적용 시):** 60 × $0.096 = **$5.76/일**  
**도메인 프리셋 적용 후:** $3.88/일 → **-33% 절감**  
**월 환산:** ~$173 → ~$116 (-$57/월)

---

## 전체 효과 요약

| 항목 | 변경 전 | 변경 후 | 개선 |
|---|---|---|---|
| Reporter 모델 | gpt-4.1 | gpt-4.1-mini | -92% (Reporter 단독) |
| Claude 에이전트 실행 | CLI subprocess | Anthropic SDK | temperature 제어 + CLI 의존 제거 |
| Advisor 일관성 | temp 미지정 | temp=0.2 고정 | 반복 호출 재현성 ↑ |
| Execution 충실도 | temp 미지정 | temp=0.3 고정 | Manifest 지시 준수율 ↑ |
| 단순 도메인 비용 | $0.096/task | $0.042/task | -56% |
| 전체 일 비용 (60 tasks) | $5.76 | $3.88 | **-33%** |
| 월 비용 절감 | — | — | **-$57/월** |
| claude CLI 의존성 | 필수 | 선택적 (레거시) | 안정성 ↑ |

---

## 운영 명령어

```bash
# 전체 도메인 모델 배정 및 비용 비교
python .scripts/orchestrator.py --compare

# 특정 도메인 프리셋 확인
python .scripts/orchestrator.py --task "테스트" --domain daily_scrap --dry-run

# 실행 (SDK 자동 사용)
python .scripts/orchestrator.py --task "뉴스 스크랩" --domain daily_scrap --auto

# 복수 도메인 병렬
python .scripts/orchestrator.py \
  --tasks "스크랩::daily_scrap,분류::pkb_worklog,이상탐지::nova_log_analytics" \
  --auto --parallel
```

## 환경변수 요구사항

| 변수 | 용도 | 비고 |
|---|---|---|
| `ANTHROPIC_API_KEY` 또는 `CLAUDE_API_KEY` | Execution, Advisor | `.scripts/.env`에 `CLAUDE_API_KEY` 설정됨 |
| `OPENAI_API_KEY` | Validation, Reporter | `.scripts/.env`에 추가 필요 |

```bash
pip install anthropic openai   # SDK 의존성
```

---

## cross_vendor 프리셋 라우팅

`orchestrator.py`의 `_run_agent()` 함수가 모델명 prefix로 자동 라우팅 (full-pipeline 전용):

```python
def _is_openai_model(model: str) -> bool:
    return model.startswith(('codex-', 'gpt-', 'o1', 'o3', 'o4'))
```

- `codex-*`, `gpt-*`, `o1/o3/o4` → `run_openai_agent()` (Responses API + Chat Completions)
- `claude-*` → `run_anthropic_agent()` (Anthropic SDK) → CLI fallback
