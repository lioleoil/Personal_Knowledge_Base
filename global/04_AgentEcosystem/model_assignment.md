# 에이전트 모델 배정 설계서

> **버전**: 1.2 | **최종 수정**: 2026-04-12  
> 설정 위치: `global/04_AgentEcosystem/model_config.json`

---

## 현행 모델 배정표

| 에이전트 | 모델 | temp | max_tokens | 배정 근거 |
|---|---|---|---|---|
| **Execution** | `claude-sonnet-4-6` | — | — | 복잡한 작업 분해·분배. 다수 반복 호출 → 비용·품질 균형 |
| **Advisor** | `claude-opus-4-6` | 0.2 | 2048 | FAIL 시 소수 호출, 심층 근본 원인 분석 → 최고 추론 모델 |
| **Validation** | `gpt-4.1` | 0.1 | 1024 | 이종 vendor 독립 검증 + 낮은 temp → 규칙 기반 일관성 확보 |
| **Reporter** | `gpt-4.1-mini` | 0.5 | 2048 | 서식화 보고서. mini로 비용 92% 절감, 보고서 품질 충분 |

> Claude 에이전트 (Execution/Advisor): `temperature`는 CLI 경유로 직접 제어 불가, 프롬프트 지시문으로 동작 제어.  
> OpenAI 에이전트 (Validation/Reporter): `temperature`, `max_tokens` Chat Completions API에 직접 적용.

---

## 비용 비교표 (5개 구성)

> 추정 토큰: Execution 4K in/1.5K out · Validation 3K in/0.5K out · Reporter 2K in/1K out · Advisor 3K in/0.8K out (호출 확률 0.3)

| 항목 | A. All Sonnet | **B. 현행 설정** | B'. Haiku Exec | C. cost_optimized | D. quality_max |
|------|--------------|-----------------|----------------|-------------------|----------------|
| Execution | Sonnet | **Sonnet** | **Haiku** | Haiku | Sonnet |
| Validation | Sonnet | **gpt-4.1** | gpt-4.1 | gpt-4.1-mini | gpt-4.1 |
| Advisor | Sonnet | **Opus** | Opus | Sonnet | Opus |
| Reporter | Sonnet | **gpt-4.1-mini** | gpt-4.1-mini | gpt-4.1-mini | gpt-4.1 |
| **태스크당 비용** | ~$0.078 | **~$0.096** | ~$0.065 | ~$0.042 | ~$0.124 |
| Advisor 품질 | ★★★☆☆ | ★★★★★ | ★★★★★ | ★★★☆☆ | ★★★★★ |
| Execution 품질 | ★★★★☆ | ★★★★☆ | ★★★☆☆ | ★★★☆☆ | ★★★★☆ |
| Validation 독립성 | ✗ | **✓** | ✓ | ✓ | ✓ |
| Reporter 비용 효율 | ★★★☆☆ | ★★★★☆ | ★★★★☆ | ★★★★★ | ★★★☆☆ |

### 비용 상세 (태스크 1회)

| 에이전트 | A (All Sonnet) | **B (현행)** | B' (Haiku Exec) | C (cost_opt) | D (quality) |
|---------|----------------|-------------|-----------------|-------------|------------|
| Execution | $0.0345 | $0.0345 | **$0.0029** | $0.0029 | $0.0345 |
| Validation | $0.0165 | $0.0130 | $0.0130 | $0.0023 | $0.0130 |
| Reporter | $0.0210 | **$0.0024** | $0.0024 | $0.0024 | $0.0300 |
| Advisor ×0.3 | $0.0063 | $0.0315 | $0.0315 | $0.0063 | $0.0315 |
| **합계** | **$0.078** | **$0.096** | **$0.065** | **$0.042** | **$0.124** |

> B vs 초기 B (codex-1): Reporter gpt-4.1-mini 전환으로 $0.121 → $0.096 (-21%)  
> B' (Haiku Execution 추가 전환 시): $0.096 → $0.065 (-32%)

---

## Claude Code 기본 대화 모델: Sonnet vs Haiku

> "기본 대화에 쓰이는 모델" — Claude Code 인터랙티브 세션 기준

### 이점·단점 분석

| 기준 | Sonnet (현행) | Haiku |
|------|--------------|-------|
| **응답 속도** | 보통 | 2-3배 빠름 |
| **72K 토큰 윈도우 활용** | 기준 | 응답 간결 → 약 25-35% 더 많은 교환 가능 |
| **Claude Pro 비용** | 동일 (정액제) | 동일 (정액제) |
| **API 직접 사용 비용** | $3/$15 per 1M | $0.25/$1.25 per 1M (**12× 절감**) |
| **간단한 Q&A · 조회** | ✓ | ✓ |
| **파일 요약 · 분류** | ✓ | ✓ |
| **간단한 코드 수정 (1-3줄)** | ✓ | ✓ |
| **복잡한 버그 디버깅** | ✓ | △ (다단계 추론 약화) |
| **아키텍처 설계 · 리뷰** | ✓ | ✗ |
| **PM 문서 작성 (PRD, OKR)** | ✓ | △ (구조 완성도 저하) |
| **커스텀 인스트럭션 완전 이행** | ✓ | △ (복잡한 규칙 누락 가능) |
| **멀티파일 코드 분석** | ✓ | ✗ |
| **멀티에이전트 오케스트레이션** | ✓ | ✗ |

### 권장 전략: 태스크 기반 선택

```
세션 시작 시 판단:
  단순 (조회·요약·간단 수정)  →  /model claude-haiku-4-5-20251001
  복잡 (설계·디버깅·PM 작업)  →  기본 Sonnet 유지
```

**Haiku로 전환 기준 (복잡도 낮음):**
- nova_helper Slack 메시지 조회·요약
- 04_WorkLog 파일 분류 확인
- .scripts/ 단일 파일 간단 수정
- Q&A, 개념 설명

**Sonnet 유지 기준 (복잡도 높음):**
- nova_log_analytics 이상 탐지 분석
- PM 산출물 작성 (PRD, OKR, 로드맵)
- 멀티에이전트 설계·디버깅
- 멀티파일 리팩토링

> Haiku를 기본값으로 고정하는 것은 비권장 — user_custom_instructions.md의 복잡한 응답 규칙 (Q1/Q2/Q3, 역할 지시 등) 준수 신뢰도 저하 위험.

### 모델 전환 방법

```bash
# 세션 내 전환 (Claude Code 대화 중)
/model claude-haiku-4-5-20251001
/model claude-sonnet-4-6   # 복구

# settings.json 기본값 변경 (전체 세션 적용)
# .claude/settings.json → "model": "claude-haiku-4-5-20251001"
```

---

## 모델 변경 방법 (Multi-Agent)

`global/04_AgentEcosystem/model_config.json`의 `agents` 블록만 수정하면 코드 수정 없이 즉시 반영.

```json
// Execution을 Haiku로 전환 (92% 비용 절감, 단순 도메인 태스크에 권장)
"execution": {
  "model": "claude-haiku-4-5-20251001",
  "provider": "anthropic"
}
```

`_presets` 블록의 `cost_optimized` 또는 `quality_max`를 `agents`에 복사해 프리셋 적용 가능.

---

## 환경변수 요구사항

| 변수 | 필요 에이전트 | 비고 |
|------|-------------|------|
| `ANTHROPIC_API_KEY` | Execution, Advisor | Claude CLI 자동 참조 |
| `OPENAI_API_KEY` | Validation, Reporter | `.scripts/.env` 또는 환경변수 |
