# Plan: pm-skills 플러그인 설치 및 구성

## Context

`C:\Users\psh93\Downloads\pm-skills-main\pm-skills-main`에 있는 pm-skills 플러그인 컬렉션을 Claude Code에서 사용할 수 있도록 설치·구성한다. 이 플러그인은 PM 업무 전반(Discovery, Strategy, Execution, Analytics 등)을 위한 65개 스킬과 36개 커맨드로 구성된 오픈소스 마켓플레이스다.

---

## 플러그인 구조 요약

| 플러그인 | 스킬 | 커맨드 | 핵심 기능 |
|---|---|---|---|
| pm-execution | 15 | 10 | PRD, OKR, 로드맵, 스프린트 |
| pm-product-discovery | 13 | 5 | 아이디에이션, 실험, 인터뷰 |
| pm-product-strategy | 12 | 5 | 비전, 캔버스, 가격, SWOT |
| pm-market-research | 7 | 3 | 페르소나, 세그멘테이션, 여정지도 |
| pm-go-to-market | 6 | 3 | GTM 전략, ICP, 배틀카드 |
| pm-marketing-growth | 5 | 2 | 포지셔닝, 네이밍, North Star |
| pm-data-analytics | 3 | 3 | SQL 생성, 코호트, A/B 테스트 |
| pm-toolkit | 4 | 5 | 이력서 검토, 법무문서, 교정 |

---

## 설치 방법 (2가지 옵션)

### Option A: Claude Code CLI 플러그인 커맨드 (권장, 지원 시)

```bash
# GitHub에서 마켓플레이스 등록 후 설치
claude plugin marketplace add phuryn/pm-skills

# 원하는 플러그인 개별 설치
claude plugin install pm-execution@pm-skills
claude plugin install pm-product-discovery@pm-skills
claude plugin install pm-product-strategy@pm-skills
# ... 필요한 플러그인 반복
```

> 현재 Claude Code 버전에서 `claude plugin` 커맨드 지원 여부 먼저 확인 필요:
> `claude plugin --help`

---

### Option B: 수동 설치 (로컬 경로에서 직접 복사)

스킬 파일을 `~/.claude/` 또는 프로젝트 `.claude/` 디렉토리에 배치한다.

**글로벌 설치 (모든 프로젝트에서 사용):**
```bash
# 스킬 디렉토리 생성
mkdir -p ~/.claude/skills

# 각 플러그인의 스킬 복사
for plugin in pm-execution pm-product-discovery pm-product-strategy pm-market-research pm-data-analytics pm-go-to-market pm-marketing-growth pm-toolkit; do
  cp -r "C:/Users/psh93/Downloads/pm-skills-main/pm-skills-main/$plugin/skills/"* ~/.claude/skills/
done
```

**프로젝트 로컬 설치 (현재 Claude 워크스페이스에만):**
```bash
mkdir -p /c/Users/psh93/OneDrive/Desktop/Claude/.claude/skills

for plugin in pm-execution pm-product-discovery pm-product-strategy; do
  cp -r "C:/Users/psh93/Downloads/pm-skills-main/pm-skills-main/$plugin/skills/"* \
    /c/Users/psh93/OneDrive/Desktop/Claude/.claude/skills/
done
```

---

## 추천 설치 범위 (PO/PM 역할 기준)

우선순위 높음 (즉시 유용):
- `pm-execution` — PRD, OKR, 스프린트 등 일상 업무
- `pm-product-discovery` — 실험 설계, 인터뷰
- `pm-product-strategy` — 전략 캔버스, SWOT

필요 시 추가:
- `pm-data-analytics` — SQL, A/B 테스트 분석
- `pm-toolkit` — 문서 교정, 이력서

---

## 검증 방법

1. 플러그인 유효성 사전 확인:
   ```bash
   cd "C:/Users/psh93/Downloads/pm-skills-main/pm-skills-main"
   python validate_plugins.py
   ```

2. 설치 후 스킬 호출 테스트:
   - `/write-prd` — PRD 작성 커맨드
   - `/discover` — Discovery 워크플로우

3. 스킬 파일 위치 확인:
   ```bash
   ls ~/.claude/skills/
   ```

---

## 핵심 파일 경로

- 소스: `C:/Users/psh93/Downloads/pm-skills-main/pm-skills-main/`
- 각 플러그인 매니페스트: `pm-*/  .claude-plugin/plugin.json`
- 스킬 파일: `pm-*/skills/*/SKILL.md`
- 커맨드 파일: `pm-*/commands/*.md`
- 검증 스크립트: `validate_plugins.py`
