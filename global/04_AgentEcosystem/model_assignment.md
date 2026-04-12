# 에이전트 모델 배정 설계서

> **버전**: 1.0 | **최종 수정**: 2026-04-12  
> 설정 위치: `.scripts/orchestrator.py` → `AGENT_MODELS` 딕셔너리

---

## 모델 배정표

| 에이전트 | 모델 | 공급사 | 배정 근거 |
|---|---|---|---|
| **Execution** | `claude-sonnet-4-6` | Anthropic | 복잡한 작업 분해·분배. 다수 반복 호출 → 비용·품질 균형 최적 |
| **Advisor** | `claude-opus-4-6` | Anthropic | FAIL 시 소수 호출, 심층 근본 원인 분석 필요 → 최고 추론 모델 투자 가치 |
| **Validation** | `codex-1` | OpenAI | 이종 vendor 독립 검증 → Anthropic 모델의 공통 편향 차단. 코드·구조 검증 특화 |
| **Reporter** | `codex-1` | OpenAI | 구조화 마크다운 생성. Validation과 동일 vendor → 결과 해석 일관성 |

---

## 4개 구성 성능·비용 비교

> 추정 토큰 (태스크 1회): Execution 4K in/1.5K out · Validation 3K in/0.5K out · Reporter 2K in/1K out · Advisor 3K in/0.8K out (호출 확률 0.3)  
> GPT-5 Codex 가격: ~$5/$20 per 1M (추정치, 공식 변동 가능)

| 항목 | A. All Sonnet (현행) | **B. 제안 (현 설정)** | C. All Opus | D. 절감형 (Sonnet+Haiku) |
|------|---------------------|----------------------|-------------|--------------------------|
| **Advisor** | Sonnet 4.6 | **Opus 4.6** | Opus 4.6 | Sonnet 4.6 |
| **Execution** | Sonnet 4.6 | **Sonnet 4.6** | Opus 4.6 | Sonnet 4.6 |
| **Validation** | Sonnet 4.6 | **GPT-5 Codex** | Opus 4.6 | Haiku 4.5 |
| **Reporter** | Sonnet 4.6 | **GPT-5 Codex** | Opus 4.6 | Haiku 4.5 |
| **태스크당 예상 비용** | ~$0.078 | ~$0.121 | ~$0.390 | ~$0.044 |
| **Advisor 품질** | ★★★☆☆ | ★★★★★ | ★★★★★ | ★★★☆☆ |
| **Execution 품질** | ★★★★☆ | ★★★★☆ | ★★★★★ | ★★★★☆ |
| **Validation 독립성** | ✗ 동일 vendor | **✓ 이종 vendor** | ✗ 동일 vendor | ✗ 동일 vendor |
| **Validation 품질** | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★☆☆ |
| **API 복잡도** | 단일 (Anthropic) | 이중 (Anthropic+OpenAI) | 단일 | 단일 |

### 비용 상세 (태스크 1회 기준)

| 에이전트 | A (All Sonnet) | **B (제안)** | C (All Opus) | D (절감) |
|---------|---------------|-------------|-------------|---------|
| Execution | $0.0345 | $0.0345 | $0.1725 | $0.0345 |
| Validation | $0.0165 | $0.0250 | $0.0825 | $0.0014 |
| Reporter | $0.0210 | $0.0300 | $0.1050 | $0.0018 |
| Advisor ×0.3 | $0.0063 | $0.0315 | $0.0315 | $0.0063 |
| **합계** | **$0.078** | **$0.121** | **$0.390** | **$0.044** |

### 장단점 요약

| 구성 | 장점 | 단점 |
|------|------|------|
| **A. All Sonnet** | 단일 API, 관리 단순, 중간 비용 | Advisor 품질 한계, 동일 vendor bias |
| **B. 제안 (현 설정)** | Advisor 최고품질, 이종 vendor 독립 검증, 역할별 최적 배분 | 비용 +55%, OpenAI API 추가 의존 |
| **C. All Opus** | 전 구간 최고 품질 | 비용 5×, Reporter에 Opus는 낭비 |
| **D. Sonnet+Haiku** | 최저 비용 (-44%) | Validation·Reporter 품질 저하, 복잡 검증 실패 위험 |

---

## 모델 변경 방법

`AGENT_MODELS` 딕셔너리만 수정하면 전 에이전트에 즉시 반영된다.

```python
# .scripts/orchestrator.py

AGENT_MODELS = {
    'execution':  'claude-sonnet-4-6',
    'validation': 'codex-1',       # OpenAI GPT-5 Codex
    'advisor':    'claude-opus-4-6',
    'reporter':   'codex-1',       # OpenAI GPT-5 Codex
}
```

Validation·Reporter를 Claude로 전환하려면 `'codex-1'`을 `'claude-sonnet-4-6'` 등으로 교체.  
OpenAI 미사용 시 `OPENAI_API_KEY` 불필요.

---

## 환경변수 요구사항

| 변수 | 필요 에이전트 | 비고 |
|------|-------------|------|
| `ANTHROPIC_API_KEY` | Execution, Advisor | Claude CLI 자동 참조 |
| `OPENAI_API_KEY` | Validation, Reporter | `.env` 또는 환경변수 설정 필요 |
