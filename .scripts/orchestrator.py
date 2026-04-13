"""
Multi-Agent Orchestrator
사용자 요청을 받아 Execution → Validation → (Advisor) → Reporter 흐름을 실행.

사용법 (단일 도메인):
  python .scripts/orchestrator.py --task "이상탐지" --domain nova_log_analytics
  python .scripts/orchestrator.py --task "..." --dry-run
  python .scripts/orchestrator.py --task "..." --auto
  python .scripts/orchestrator.py --task "..." --auto --no-confirm

사용법 (복수 도메인 병렬):
  python .scripts/orchestrator.py \
    --tasks "이상탐지::nova_log_analytics,뉴스스크랩::daily_scrap" \
    --auto --parallel
  --tasks 형식: "작업1::도메인1,작업2::도메인2,..."

기타:
  python .scripts/orchestrator.py --list

환경변수 (Slack 에스컬레이션 알림):
  SLACK_WEBHOOK_URL       Incoming Webhook URL (우선)
  SLACK_BOT_TOKEN         Bot OAuth Token
  SLACK_ESCALATION_CHANNEL 알림 채널 (기본: #alerts)

--auto 전제 조건:
  - claude CLI가 PATH에 존재해야 함 (Claude Code 설치 시 자동 등록)
  - 터미널에서 직접 실행 권장
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

# Windows CP949 콘솔에서 UTF-8 문자(em dash 등) 출력 오류 방지
if sys.stdout.encoding and sys.stdout.encoding.lower() in ('cp949', 'cp950', 'gbk', 'euc-kr'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
)
sys.path.insert(0, os.path.join(PROJECT_ROOT, '.scripts'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, '.status'))

# .env 자동 로드 (nova_helper/.env 우선, 루트 .env 차선)
def _load_dotenv():
    # 루트 .env 우선, 이후 보조 .env 병합 (break 없이 전부 읽음)
    for env_path in [
        os.path.join(PROJECT_ROOT, '.env'),
        os.path.join(PROJECT_ROOT, '.scripts', '.env'),
        os.path.join(PROJECT_ROOT, 'projects', 'nova_helper', '.env'),
    ]:
        if os.path.exists(env_path):
            with open(env_path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, _, v = line.partition('=')
                        key, val = k.strip(), v.strip()
                        if val and not os.environ.get(key):
                            os.environ[key] = val

_load_dotenv()

from agent_bus import AgentBus, BusFile
from agent_log import AgentLog
from permission_bus import PermissionBus
import show_tokens as _show_tokens

_PERM_BUS = PermissionBus()

def check_permission(perm_type: str, task_id: str = 'orchestrator', context: str = '') -> bool:
    """
    권한 레지스트리 기반 체크. auto_approved → True, user_approval_required → False.
    레지스트리 로드 실패 시 True 반환 (허용 우선, 비중단).
    """
    try:
        return _PERM_BUS.check(task_id, perm_type, context)
    except Exception:
        return True  # 레지스트리 오류 시 비중단

# ── 상수 ──────────────────────────────────────────────────────────
TOKEN_USAGE_PATH = os.path.join(PROJECT_ROOT, '.status', 'token_usage.json')
TOKEN_PARALLEL_THRESHOLD = 10_000

# ── 모델 설정 로드 ─────────────────────────────────────────────────

# 에스컬레이션 한도 (플랜 설계 기준)
MAX_EXECUTION_RETRIES = 5
MAX_ADVISOR_CALLS = 3

# 버스 파일 대기 설정
BUS_POLL_INTERVAL = 3    # 초
BUS_POLL_TIMEOUT  = 600  # 10분

# ── 에이전트 모델 배정 (기본값) ────────────────────────────────────────
_AGENT_MODELS_DEFAULT = {
    'execution':  'claude-sonnet-4-5',
    'validation': 'gpt-4.1',
    'advisor':    'claude-opus-4-5',
    'reporter':   'gpt-4.1-mini',
}
_AGENT_PROVIDERS_DEFAULT = {
    'execution':  'anthropic',
    'validation': 'openai',
    'advisor':    'anthropic',
    'reporter':   'openai',
}

_MODEL_CONFIG_PATH = os.path.join(
    PROJECT_ROOT, 'global', '04_AgentEcosystem', 'model_config.json'
)

def _load_model_config() -> tuple[dict, dict, dict, dict, dict, dict]:
    try:
        with open(_MODEL_CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        agents_cfg = cfg.get('agents', {})
        agent_models = {role: v['model'] for role, v in agents_cfg.items() if 'model' in v}
        agent_providers = {
            role: v.get('provider', _AGENT_PROVIDERS_DEFAULT.get(role, 'anthropic'))
            for role, v in agents_cfg.items()
        }
        agent_params = {
            role: {k: v[k] for k in ('temperature', 'max_tokens') if k in v}
            for role, v in agents_cfg.items()
        }
        costs          = {k: v for k, v in cfg.get('model_costs', {}).items() if not k.startswith('_')}
        domain_presets = {k: v for k, v in cfg.get('domain_presets', {}).items() if not k.startswith('_')}
        presets        = {k: v for k, v in cfg.get('_presets', {}).items() if not k.startswith('_')}
        return (
            {**_AGENT_MODELS_DEFAULT, **agent_models},
            {**_AGENT_PROVIDERS_DEFAULT, **agent_providers},
            agent_params, costs, domain_presets, presets,
        )
    except Exception:
        return (_AGENT_MODELS_DEFAULT.copy(), _AGENT_PROVIDERS_DEFAULT.copy(), {}, {}, {}, {})

(AGENT_MODELS, AGENT_PROVIDERS, AGENT_PARAMS,
 MODEL_COSTS, DOMAIN_PRESETS, PRESETS) = _load_model_config()


def get_domain_preset(domain: str) -> dict:
    """도메인 프리셋을 flat dict(구 스키마)로 반환. run_auto/run_full_pipeline 공용."""
    preset_name = DOMAIN_PRESETS.get(domain, 'default')
    if preset_name != 'default' and preset_name in PRESETS:
        p = PRESETS[preset_name]
        def _m(role):    return p.get(role, {}).get('model',       AGENT_MODELS.get(role, ''))
        def _tmp(role):  return p.get(role, {}).get('temperature', AGENT_PARAMS.get(role, {}).get('temperature', 0.3))
        def _mx(role, d): return p.get(role, {}).get('max_tokens', AGENT_PARAMS.get(role, {}).get('max_tokens', d))
    else:
        def _m(role):    return AGENT_MODELS.get(role, '')
        def _tmp(role):  return AGENT_PARAMS.get(role, {}).get('temperature', 0.3)
        def _mx(role, d): return AGENT_PARAMS.get(role, {}).get('max_tokens', d)
    return {
        'execution_model':       _m('execution'),
        'validation_model':      _m('validation'),
        'advisor_model':         _m('advisor'),
        'reporter_model':        _m('reporter'),
        'temperature_execution': _tmp('execution'),
        'temperature_advisor':   _tmp('advisor'),
        'max_tokens_execution':  _mx('execution',  8192),
        'max_tokens_validation': _mx('validation', 4096),
        'max_tokens_advisor':    _mx('advisor',    4096),
        'max_tokens_reporter':   _mx('reporter',   8192),
    }


def get_domain_config(domain: str, role: str) -> tuple[str, str, dict]:
    """domain + role → (model, provider, params).
    preset_name == 'default'도 _presets.default 항목이 있으면 그것을 사용한다.
    _presets에 없는 preset_name이면 agents 블록 기본값으로 폴백.
    """
    preset_name = DOMAIN_PRESETS.get(domain, 'default')
    if preset_name in PRESETS:
        role_cfg = PRESETS[preset_name].get(role, {})
        model    = role_cfg.get('model',    AGENT_MODELS.get(role, ''))
        provider = role_cfg.get('provider', AGENT_PROVIDERS.get(role, 'anthropic'))
        params   = {k: role_cfg[k] for k in ('temperature', 'max_tokens') if k in role_cfg}
    else:
        model    = AGENT_MODELS.get(role, '')
        provider = AGENT_PROVIDERS.get(role, 'anthropic')
        params   = AGENT_PARAMS.get(role, {})
    return model, provider, params


# ── auto-domain 키워드 라우팅 ──────────────────────────────────────────
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    'nova_helper':        ['nova', 'slack', 'bolt', 'bot', '봇'],
    'nova_log_analytics': ['로그', 'log', '이상탐지', 'anomaly', 'pipeline', '파이프라인', 'analytics', '분석'],
    'pkb_worklog':        ['worklog', '대화', '분류', 'pkb', '정리', 'knowledge', '로그분류', '워크로그'],
    'sv_dqat':            ['dqat', '어노테이션', 'annotation', 'labelit', 'quality', 'qa', '품질'],
    'sv_lakehouse':       ['lakehouse', 'lake', 'sv_lakehouse', 'warehouse'],
    'daily_scrap':        ['스크랩', 'scrap', 'geeknews', '뉴스', 'news', 'daily'],
}

def detect_domain(task: str) -> str:
    """태스크 설명에서 키워드 매칭으로 도메인 자동 판단. 매칭 없으면 pkb_worklog."""
    task_lower = task.lower()
    scores: dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in task_lower)
        if score:
            scores[domain] = score
    if scores:
        best = max(scores, key=lambda d: scores[d])
        print(f'[auto-domain] "{best}" 선택 (점수: {scores})')
        return best
    print('[auto-domain] 매칭 없음 → pkb_worklog 기본값 사용')
    return 'pkb_worklog'


DOMAIN_MAP = {
    'nova_helper':        {
        'role_rules': 'global/04_AgentEcosystem/agents/domains/role_rules__nova_helper.md',
        'context':    ['projects/nova_helper/'],
    },
    'nova_log_analytics': {
        'role_rules': 'global/04_AgentEcosystem/agents/domains/role_rules__nova_log_analytics.md',
        'context':    ['projects/nova_log_analytics/config.yaml'],
    },
    'pkb_worklog':        {
        'role_rules': 'global/04_AgentEcosystem/agents/domains/role_rules__pkb_worklog.md',
        'context':    ['projects/personal_knowledge_base/04_WorkLog/INDEX.md'],
    },
    'sv_dqat':            {
        'role_rules': 'global/04_AgentEcosystem/agents/domains/role_rules__sv.md',
        'context':    ['projects/sv_dqat/'],
    },
    'sv_lakehouse':       {
        'role_rules': 'global/04_AgentEcosystem/agents/domains/role_rules__sv.md',
        'context':    ['projects/sv_lakehouse/'],
    },
    'daily_scrap':        {
        'role_rules': 'global/04_AgentEcosystem/agents/domains/role_rules__pkb_worklog.md',
        'context':    ['.scripts/daily_scrap_runner.py'],
    },
}

# ── 토큰 잔여량 ────────────────────────────────────────────────────

def get_remaining_tokens() -> int | None:
    if not os.path.exists(TOKEN_USAGE_PATH):
        return None
    try:
        with open(TOKEN_USAGE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        used = data.get('used', 0)
        limit = data.get('window_limit', 72_000)
        return max(0, limit - used)
    except Exception:
        return None

# ── Manifest 생성 ──────────────────────────────────────────────────

def build_manifest(task: str, domain: str, task_id: str | None = None,
                   retry_count: int = 0) -> AgentBus:
    bus = AgentBus(task_id=task_id)
    info = DOMAIN_MAP.get(domain, {})
    context_files = list(info.get('context', []))
    role_rules = info.get('role_rules', '')
    if role_rules:
        context_files = [role_rules] + context_files

    bus.write_manifest(
        domain=domain,
        instructions=task,
        context_files=context_files,
        expected_outputs=[f'type:{domain}_result'],
        deadline_hint='10min',
        retry_count=retry_count,
    )
    return bus

# ── 프롬프트 생성 ──────────────────────────────────────────────────

def _abs(rel_path: str) -> str:
    return os.path.join(PROJECT_ROOT, rel_path).replace('\\', '/')

def make_execution_prompt(task: str, domain: str, task_id: str, bus_path: str,
                           retry_count: int = 0) -> str:
    retry_note = f'\n[재시도 {retry_count}회차]' if retry_count else ''
    return (
        f'당신은 Execution Agent + {domain} Domain Agent입니다.{retry_note}\n\n'
        f'Role Rules: {_abs("global/04_AgentEcosystem/agents/role_rules__execution.md")}\n'
        f'Domain Rules: {_abs(DOMAIN_MAP[domain]["role_rules"])}\n'
        f'Protocol: {_abs("global/04_AgentEcosystem/protocol/task_manifest_schema.md")}\n\n'
        f'Task ID: {task_id}\nDomain: {domain}\nTask: {task}\n\n'
        f'수행 순서:\n'
        f'1. 위 Task를 충분히 분석하고 작업을 수행한다\n'
        f'2. 작업 결과를 마크다운 형식으로 상세히 출력한다\n'
        f'3. 응답 마지막 줄에 반드시 다음 신호를 출력한다:\n'
        f'   EXECUTION_DONE:{task_id}\n\n'
        f'※ SDK 직접 호출 모드: 파일 저장은 orchestrator가 자동 처리함.\n'
        f'   AgentBus Python 코드를 응답에 포함하지 말 것.\n'
        f'   결과 텍스트만 출력하고 마지막에 EXECUTION_DONE 신호를 붙일 것.'
    )

def make_validation_prompt(task_id: str, domain: str,
                            manifest_content: str = '', result_content: str = '') -> str:
    return (
        f'당신은 Validation Agent입니다. 아래 실행 결과를 검증하고 판정을 내려야 합니다.\n\n'
        f'=== Task Manifest ===\n{manifest_content or "(없음)"}\n\n'
        f'=== Execution Result ===\n{result_content or "(없음)"}\n\n'
        f'검증 기준:\n'
        f'1. Task 요구사항이 충족되었는가?\n'
        f'2. 결과물의 품질이 충분한가?\n'
        f'3. 오류나 누락된 항목이 없는가?\n\n'
        f'판정 이유를 간략히 서술한 후, 아래 두 블록을 순서대로 출력하라:\n\n'
        f'1) 통과한 검증 항목을 JSON 형식으로 출력:\n'
        f'PASSED_CHECKS_JSON:{{"passed_checks":["항목1","항목2",...]}}\n\n'
        f'2) 응답 마지막 줄에 판정 신호:\n'
        f'  VALIDATION_DONE:{task_id}:PASS\n'
        f'  VALIDATION_DONE:{task_id}:FAIL\n'
        f'  VALIDATION_DONE:{task_id}:INSUFFICIENT\n\n'
        f'※ SDK 직접 호출 모드: 파일 저장은 orchestrator가 자동 처리함.\n'
        f'   AgentBus Python 코드를 응답에 포함하지 말 것.\n'
        f'   PASSED_CHECKS_JSON과 VALIDATION_DONE 신호를 반드시 출력할 것.'
    )

def make_advisor_prompt(task_id: str, call_count: int,
                         manifest_content: str = '', result_content: str = '',
                         validation_content: str = '') -> str:
    return (
        f'당신은 Advisor Agent입니다. [호출 {call_count}회차]\n\n'
        f'=== Task Manifest ===\n{manifest_content or "(없음)"}\n\n'
        f'=== Execution Result ===\n{result_content or "(없음)"}\n\n'
        f'=== Validation 판정 ===\n{validation_content or "(없음)"}\n\n'
        f'수행:\n'
        f'1. Validation이 FAIL/INSUFFICIENT인 근본 원인 분석\n'
        f'2. Execution 재시도 시 개선할 구체적 액션 플랜 제시\n\n'
        f'분석 후, 응답 마지막 줄에 아래 형식 중 하나를 출력하라:\n'
        f'  ADVICE_DONE:{task_id}:retry\n'
        f'  ADVICE_DONE:{task_id}:escalate\n\n'
        f'※ SDK 직접 호출 모드: 파일 저장은 orchestrator가 처리함.\n'
        f'   AgentBus Python 코드를 응답에 포함하지 말 것.'
    )

def make_reporter_prompt(task_id: str, domain: str,
                          manifest_content: str = '', result_content: str = '') -> str:
    return (
        f'당신은 Reporter Agent입니다.\n\n'
        f'=== Task Manifest ===\n{manifest_content or "(없음)"}\n\n'
        f'=== Execution Result ===\n{result_content or "(없음)"}\n\n'
        f'위 실행 결과를 바탕으로 사용자에게 전달할 마크다운 보고서를 작성하라.\n'
        f'보고서는 명확하고 구조적이어야 하며 핵심 결과, 인사이트, 다음 액션을 포함해야 한다.\n\n'
        f'보고서 전문을 stdout에 출력하라.\n'
        f'※ SDK 직접 호출 모드: 파일 저장은 orchestrator가 처리함.\n'
        f'   AgentBus Python 코드를 응답에 포함하지 말 것.'
    )

# ── Anthropic SDK 직접 호출 (단일 정의) ───────────────────────────


def _track_anthropic_usage(tokens: int, task_name: str) -> None:
    """Anthropic 에이전트 토큰을 token_usage.json에 집계 (show_tokens.add_session 재사용)."""
    try:
        show_tokens_path = os.path.join(PROJECT_ROOT, '.status', 'show_tokens.py')
        if not os.path.exists(show_tokens_path):
            return
        import importlib.util
        spec = importlib.util.spec_from_file_location('show_tokens', show_tokens_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.add_session(tokens, f'agent:{task_name}')
    except Exception:
        pass  # 추적 실패는 비중단


def run_agent(prompt: str, label: str, log: AgentLog,
              role: str, domain: str, timeout: int = 600) -> tuple[bool, str]:
    """
    domain + role 기반으로 model_config.json 프리셋을 해석하고 적합한
    실행 함수(run_anthropic_agent / run_openai_agent)를 자동 선택.
    모든 에이전트 호출의 단일 진입점.
    """
    model, provider, params = get_domain_config(domain, role)
    preset_name = DOMAIN_PRESETS.get(domain, 'default')
    log.add(f'[{label}] {model} (provider={provider}, preset={preset_name})')

    if provider == 'anthropic':
        temperature = params.get('temperature', 0.3) if params else 0.3
        max_tokens  = params.get('max_tokens', 4096) if params else 4096
        ok, stdout, _, _ = run_anthropic_agent(prompt, label, log, model=model,
                                               temperature=temperature,
                                               max_tokens=max_tokens)
        return ok, stdout
    elif provider == 'openai':
        return run_openai_agent(prompt, label, log, model=model,
                                params=params, timeout=timeout)
    else:
        log.add(f'[{label}] 알 수 없는 provider: {provider}')
        return False, ''


# ── claude CLI 실행 (레거시 폴백) ──────────────────────────────────

def find_claude_cli() -> str | None:
    """claude CLI 경로 탐색."""
    # 1. PATH에서 찾기
    for candidate in ['claude', 'claude.exe']:
        result = subprocess.run(
            ['where', candidate] if sys.platform == 'win32' else ['which', candidate],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return candidate

    # 2. 알려진 Windows 설치 경로
    known = [
        os.path.expandvars(r'%LOCALAPPDATA%\AnthropicClaude\claude.exe'),
        os.path.expandvars(r'%APPDATA%\npm\claude.cmd'),
        r'C:\Program Files\Claude\claude.exe',
    ]
    for path in known:
        if os.path.exists(path):
            return path

    return None


def run_claude_agent(prompt: str, label: str, log: AgentLog,
                     timeout: int = 600, model: str | None = None) -> tuple[bool, str]:
    """
    claude -p <prompt> 를 서브프로세스로 실행.
    model 지정 시 --model <id> 플래그 추가.
    반환: (성공 여부, stdout 텍스트)
    """
    claude = find_claude_cli()
    if not claude:
        log.add(f'[{label}] claude CLI 없음 — PATH 확인 필요')
        return False, ''

    cmd = [
        claude,
        '--dangerously-skip-permissions',
        '-p', prompt,
    ]
    if model:
        cmd += ['--model', model]

    log.add(f'[{label}] claude 실행 시작')
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=PROJECT_ROOT,
            timeout=timeout,
        )
        stdout = result.stdout or ''
        stderr = result.stderr or ''

        if result.returncode != 0:
            log.add(f'[{label}] 비정상 종료 (rc={result.returncode}): {stderr[:200]}')
            return False, stdout

        log.add(f'[{label}] 완료 (출력 {len(stdout)} chars)')
        return True, stdout

    except subprocess.TimeoutExpired:
        log.add(f'[{label}] 타임아웃 ({timeout}s)')
        return False, ''
    except Exception as e:
        log.add(f'[{label}] 오류: {e}')
        return False, ''


def run_anthropic_agent(prompt: str, label: str, log: AgentLog,
                        model: str = 'claude-sonnet-4-5',
                        temperature: float = 0.3,
                        max_tokens: int = 8192) -> tuple[bool, str, int, int]:
    """Anthropic SDK로 에이전트 실행.
    반환: (성공 여부, 응답 텍스트, input_tokens, output_tokens)
    SDK 불가 시 run_claude_agent() CLI fallback — token 수는 0, 0 반환.
    """
    try:
        import anthropic as _anthropic
    except ImportError:
        log.add(f'[{label}] anthropic SDK 없음 — CLI fallback')
        ok, stdout = run_claude_agent(prompt, label, log)
        return ok, stdout, 0, 0

    api_key = os.environ.get('CLAUDE_API_KEY') or os.environ.get('ANTHROPIC_API_KEY')
    # env에 없으면 .env 파일에서 직접 읽기 (setdefault 타이밍 이슈 방어)
    if not api_key:
        _load_dotenv()
        api_key = os.environ.get('CLAUDE_API_KEY') or os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        log.add(f'[{label}] API 키 없음 — CLI fallback')
        ok, stdout = run_claude_agent(prompt, label, log)
        return ok, stdout, 0, 0

    log.add(f'[{label}] SDK 실행 (model={model}, temp={temperature})')
    try:
        client = _anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{'role': 'user', 'content': prompt}],
        )
        text = message.content[0].text if message.content else ''
        in_tok = message.usage.input_tokens
        out_tok = message.usage.output_tokens
        log.add(f'[{label}] 완료 ({in_tok:,}in / {out_tok:,}out tokens)')
        return True, text, in_tok, out_tok
    except Exception as e:
        log.add(f'[{label}] SDK 오류: {e} — CLI fallback')
        ok, stdout = run_claude_agent(prompt, label, log)
        return ok, stdout, 0, 0


def run_openai_agent(prompt: str, label: str, log: AgentLog,
                     model: str = 'gpt-4.1', timeout: int = 600,
                     params: dict | None = None) -> tuple[bool, str]:
    """
    OpenAI API 호출.
    - gpt-*/o* 계열: Chat Completions API
    - codex-* 계열: Responses API
    params: model_config.json에서 로드된 temperature/max_tokens 등.
    OPENAI_API_KEY 환경변수 필요.
    반환: (성공 여부, stdout 텍스트)
    """
    try:
        import openai  # noqa: PLC0415
    except ImportError:
        log.add(f'[{label}] openai 패키지 없음 — pip install openai')
        return False, ''

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        log.add(f'[{label}] OPENAI_API_KEY 없음 — .env 설정 필요')
        return False, ''

    p = params or {}
    temperature = p.get('temperature')
    max_tokens  = p.get('max_tokens')
    log.add(f'[{label}] OpenAI({model}, temp={temperature}) 실행 시작')
    try:
        client = openai.OpenAI(api_key=api_key)
        usage_in = usage_out = 0

        if model.startswith('codex'):
            # Responses API (codex-1 등) — temperature/max_tokens 미지원
            response = client.responses.create(model=model, input=prompt)
            result = response.output_text or ''
            if hasattr(response, 'usage') and response.usage:
                usage_in  = getattr(response.usage, 'input_tokens', 0)
                usage_out = getattr(response.usage, 'output_tokens', 0)
        else:
            # Chat Completions API (gpt-4.1, gpt-4.1-mini, o3 등)
            kwargs: dict = {
                'model': model,
                'messages': [{'role': 'user', 'content': prompt}],
            }
            if temperature is not None:
                kwargs['temperature'] = temperature
            if max_tokens is not None:
                kwargs['max_tokens'] = max_tokens
            response = client.chat.completions.create(**kwargs)
            result = response.choices[0].message.content or ''
            if hasattr(response, 'usage') and response.usage:
                usage_in  = getattr(response.usage, 'prompt_tokens', 0)
                usage_out = getattr(response.usage, 'completion_tokens', 0)

        log.add(f'[{label}] 완료 (출력 {len(result)} chars, '
                f'토큰 in={usage_in} out={usage_out})')
        _track_openai_usage(model, usage_in, usage_out, label)
        return True, result
    except Exception as e:
        log.add(f'[{label}] 오류: {e}')
        return False, ''


def _track_openai_usage(model: str, input_tokens: int, output_tokens: int,
                        task_name: str) -> None:
    """OpenAI 토큰 사용량을 .status/openai_usage.json에 기록."""
    try:
        tracker_path = os.path.join(PROJECT_ROOT, '.status', 'openai_cost_tracker.py')
        if os.path.exists(tracker_path):
            import importlib.util
            spec = importlib.util.spec_from_file_location('openai_cost_tracker', tracker_path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.track_usage(model, input_tokens, output_tokens, task_name,
                            model_costs=MODEL_COSTS)
    except Exception:
        pass


def _is_openai_model(model: str) -> bool:
    """모델 이름으로 OpenAI 라우팅 여부 판별."""
    return model.startswith(('codex-', 'gpt-', 'o1', 'o3', 'o4'))


def _run_agent(prompt: str, label: str, log: AgentLog,
               model: str = 'claude-sonnet-4-5',
               temperature: float = 0.3,
               max_tokens: int = 8192) -> tuple[bool, str]:
    """모델명에 따라 Anthropic SDK / OpenAI API / CLI fallback 라우팅.
    full-pipeline 전용. run_auto는 run_agent() 사용.
    반환: (성공 여부, 응답 텍스트)
    """
    if _is_openai_model(model):
        return run_openai_agent(prompt, label, log,
                                model=model, params={'max_tokens': max_tokens})

    ok, stdout, in_tok, out_tok = run_anthropic_agent(
        prompt, label, log, model=model,
        temperature=temperature, max_tokens=max_tokens,
    )
    if in_tok + out_tok > 0:
        _show_tokens.add_agent_tokens(in_tok, out_tok,
                                      task_name=label, model=model)
    return ok, stdout


def wait_for_bus_file(bus: AgentBus, file_type: BusFile,
                      timeout: int = BUS_POLL_TIMEOUT) -> dict | None:
    """버스 파일이 생성될 때까지 폴링. 타임아웃 시 None 반환."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = bus.read(file_type)
        if data is not None:
            return data
        time.sleep(BUS_POLL_INTERVAL)
    return None

# ── Dry Run ────────────────────────────────────────────────────────

def dry_run(task: str, domain: str):
    bus = build_manifest(task, domain)
    manifest = bus.read(BusFile.MANIFEST)
    print('\n=== DRY RUN - Task Manifest ===')
    print(json.dumps(manifest, ensure_ascii=True, indent=2))
    print(f'\nManifest: {bus._path(BusFile.MANIFEST)}')

    preset_name = DOMAIN_PRESETS.get(domain, 'default')
    print(f'\n=== 모델 배정 (domain={domain}, preset={preset_name}) ===')
    total_cost = 0.0
    for role in ('execution', 'validation', 'advisor', 'reporter'):
        model, provider, params = get_domain_config(domain, role)
        temp = params.get('temperature', '-')
        mtok = params.get('max_tokens', '-')
        rate = MODEL_COSTS.get(model, {})
        tok_est = {'execution': (4000, 1500), 'validation': (3000, 500),
                   'advisor': (3000, 800), 'reporter': (2000, 1000)}
        freq    = 0.3 if role == 'advisor' else 1.0
        ti, to  = tok_est.get(role, (2000, 500))
        cost    = ((ti * rate.get('input', 0) + to * rate.get('output', 0))
                   / 1_000_000 * freq) if rate else 0
        total_cost += cost
        print(f'  {role:<12} {model:<30} provider={provider:<10} '
              f'temp={temp}  max_tokens={mtok}  est=${cost:.4f}')
    print(f'  {"─"*78}')
    print(f'  {"태스크당 추정 비용":<12} {"":30}                                  ${total_cost:.4f}')

    print('\n=== Execution Agent 프롬프트 미리보기 ===')
    print(make_execution_prompt(task, domain, bus.task_id,
                                bus._path(BusFile.MANIFEST)))
    print('\n--dry-run 없이 실행하면 수행됩니다.')
    print(f'  자동 실행: python .scripts/orchestrator.py --task "{task}" --domain {domain} --auto')


def compare_domains():
    """모든 도메인의 모델 배정과 예상 비용을 비교 출력 (--compare 플래그용)."""
    tok_est = {'execution': (4000, 1500), 'validation': (3000, 500),
               'advisor': (3000, 800),    'reporter': (2000, 1000)}
    freq_map = {'advisor': 0.3}

    print('\n=== 도메인별 모델 배정 비교 ===\n')
    print(f'{"도메인":<22} {"프리셋":<16} {"Execution":<30} {"Advisor":<22} '
          f'{"Validation":<16} {"Reporter":<16} {"$/task":<8}')
    print('─' * 134)

    for domain in list(DOMAIN_MAP.keys()) + ['(default)']:
        real_domain = domain if domain != '(default)' else list(DOMAIN_MAP.keys())[0]
        preset_name = DOMAIN_PRESETS.get(real_domain, 'default') if domain != '(default)' else 'default'

        row = {}
        total = 0.0
        for role in ('execution', 'validation', 'advisor', 'reporter'):
            if domain == '(default)':
                m, _, p = get_domain_config(list(DOMAIN_MAP.keys())[2], role)
            else:
                m, _, p = get_domain_config(domain, role)
            row[role] = m.replace('claude-', '').replace('-4-6', '').replace('-4-5-20251001', '')
            rate  = MODEL_COSTS.get(m, {})
            freq  = freq_map.get(role, 1.0)
            ti, to = tok_est[role]
            total += (ti * rate.get('input', 0) + to * rate.get('output', 0)) / 1_000_000 * freq

        print(f'{domain:<22} {preset_name:<16} {row["execution"]:<30} '
              f'{row["advisor"]:<22} {row["validation"]:<16} {row["reporter"]:<16} '
              f'${total:.4f}')

    print('\n─ 가격 기준 ─')
    for model, costs in MODEL_COSTS.items():
        print(f'  {model:<32} in=${costs["input"]}/1M  out=${costs["output"]}/1M')

# ── 작업 목록 ──────────────────────────────────────────────────────

def list_tasks():
    tasks = AgentBus.list_tasks()
    if not tasks:
        print('버스에 작업 없음.')
        return
    print(f'\n=== Agent Bus ({len(tasks)}개) ===\n')
    for t in tasks:
        s = AgentBus.get_task_status(t['task_id'])
        verdict  = s.get('verdict') or '-'
        reported = '완료' if s.get('reported') else '-'
        advice   = '있음' if s.get('has_advice') else '-'
        print(f"  {t['task_id']}  {s['domain']:<22}"
              f"  result:{'O' if s['has_result'] else 'X'}"
              f"  verdict:{verdict:<12}"
              f"  advice:{advice}"
              f"  report:{reported}")

# ── Auto 파이프라인 ────────────────────────────────────────────────

def run_auto(task: str, domain: str, no_confirm: bool, log: AgentLog,
             shared_task_id: str | None = None):
    """Execution → Validation → (Advisor) → Reporter 자동 실행."""

    # ── 0. 권한 사전 체크 ────────────────────────────────────────
    if not check_permission('agent_spawn', context=f'task={task} domain={domain}'):
        log.error('agent_spawn 권한 없음 — 사용자 승인 필요 (.agents/bus/*_permission_request.json 확인)')
        return

    exec_retries   = 0
    advisor_calls  = 0
    bus: AgentBus | None = None

    # 도메인 프리셋 로드
    preset = get_domain_preset(domain)
    exec_model   = preset.get('execution_model',   'claude-sonnet-4-5')
    val_model    = preset.get('validation_model',  'claude-sonnet-4-5')
    adv_model    = preset.get('advisor_model',     'claude-sonnet-4-5')
    rep_model    = preset.get('reporter_model',    'claude-sonnet-4-5')
    temp_exec    = preset.get('temperature_execution', 0.3)
    temp_adv     = preset.get('temperature_advisor',   0.2)
    max_tok_exec = preset.get('max_tokens_execution',  8192)
    max_tok_val  = preset.get('max_tokens_validation', 4096)
    max_tok_adv  = preset.get('max_tokens_advisor',    4096)
    max_tok_rep  = preset.get('max_tokens_reporter',   8192)
    log.add(f'프리셋: exec={exec_model} adv={adv_model}')

    # ── 1. Execution 루프 ────────────────────────────────────────
    while exec_retries <= MAX_EXECUTION_RETRIES:
        # Manifest 생성 (재시도 시 새 bus 유지, retry_count 갱신)
        if bus is None:
            bus = build_manifest(task, domain,
                                 task_id=shared_task_id,
                                 retry_count=exec_retries)
        else:
            # 재시도: 기존 task_id 유지, retry_count만 갱신
            bus.write_manifest(
                domain=domain,
                instructions=task,
                context_files=list(DOMAIN_MAP[domain].get('context', [])),
                expected_outputs=[f'type:{domain}_result'],
                retry_count=exec_retries,
            )

        manifest_path = bus._path(BusFile.MANIFEST)
        log.update(progress=10 + exec_retries * 5,
                   message=f'Execution 실행 중 (시도 {exec_retries + 1})')

        prompt = make_execution_prompt(task, domain, bus.task_id,
                                       manifest_path, exec_retries)
        ok, stdout = run_agent(prompt, f'Execution#{exec_retries+1}', log,
                               role='execution', domain=domain)

        if not ok:
            exec_retries += 1
            if exec_retries > MAX_EXECUTION_RETRIES:
                break
            log.add(f'Execution 실패 — 재시도 {exec_retries}/{MAX_EXECUTION_RETRIES}')
            time.sleep(2)
            continue

        # result.json 확인 — SDK 모드에서는 orchestrator가 직접 생성
        result_data = bus.read(BusFile.RESULT)
        if result_data is None:
            if ok and stdout.strip():
                # SDK 응답이 있으면 orchestrator가 result.json 자동 저장
                has_done_signal = f'EXECUTION_DONE:{bus.task_id}' in stdout
                status = 'success' if has_done_signal else 'partial'
                log.add(f'SDK 응답으로 result.json 자동 생성 (status={status})')
                bus.write_result(
                    domain, status,
                    [{'type': f'{domain}_result',
                      'summary': stdout[:300],
                      'content': stdout}],
                )
                result_data = bus.read(BusFile.RESULT)
            else:
                log.add('EXECUTION_DONE 신호 없음 — Execution 실패로 처리')
                exec_retries += 1
                continue

        log.update(progress=40, message='Execution 완료 — Validation 진행')

        # ── 2. Validation ──────────────────────────────────────
        # 컨텍스트를 인라인으로 전달 (SDK 모드에서 파일 I/O 불가)
        _manifest_data = bus.read(BusFile.MANIFEST) or {}
        _manifest_str  = json.dumps(_manifest_data, ensure_ascii=False, indent=2)
        _result_str    = json.dumps(result_data, ensure_ascii=False, indent=2) if result_data else (stdout or '')[:3000]

        val_prompt = make_validation_prompt(bus.task_id, domain, _manifest_str, _result_str)
        ok, val_stdout = run_agent(val_prompt, 'Validation', log,
                                   role='validation', domain=domain)

        # stdout에서 verdict + passed_checks 파싱 (SDK 모드: 파일 미작성)
        _VALID_VERDICTS = {'PASS', 'FAIL', 'INSUFFICIENT'}
        validation = bus.read(BusFile.VALIDATION)
        if validation is None:
            # passed_checks 파싱
            passed_checks = []
            _pc_match = re.search(r'PASSED_CHECKS_JSON:\s*(\{.*?"passed_checks"\s*:\s*\[.*?\].*?\})',
                                   val_stdout or '', re.DOTALL)
            if _pc_match:
                try:
                    passed_checks = json.loads(_pc_match.group(1)).get('passed_checks', [])
                except (json.JSONDecodeError, Exception):
                    pass

            # verdict 파싱
            match_str = f'VALIDATION_DONE:{bus.task_id}:'
            idx = (val_stdout or '').find(match_str)
            if idx >= 0:
                raw = val_stdout[idx + len(match_str):].split()[0].strip().upper()
                parsed_verdict = raw if raw in _VALID_VERDICTS else 'INSUFFICIENT'
            else:
                parsed_verdict = 'INSUFFICIENT'
            bus.write_validation(parsed_verdict,
                                  advisor_needed=(parsed_verdict == 'FAIL'),
                                  passed_checks=passed_checks)
            validation = bus.read(BusFile.VALIDATION)

        if validation is None:
            log.add('validation.json 없음 — INSUFFICIENT 처리')
            validation = {'verdict': 'INSUFFICIENT', 'advisor_needed': False}

        verdict = validation.get('verdict', 'INSUFFICIENT')
        if verdict not in _VALID_VERDICTS:
            log.add(f'verdict 값 비정상({verdict!r}) — INSUFFICIENT 처리')
            verdict = 'INSUFFICIENT'
            validation['verdict'] = verdict
        log.add(f'Validation 판정: {verdict}')

        # ── 3. 판정 분기 ─────────────────────────────────────
        if verdict == 'PASS':
            log.update(progress=80, message='Validation PASS — Reporter 실행')
            break  # Execution 루프 탈출 → Reporter로

        elif verdict == 'INSUFFICIENT':
            exec_retries += 1
            log.add(f'INSUFFICIENT — 재시도 {exec_retries}/{MAX_EXECUTION_RETRIES}')
            if exec_retries > MAX_EXECUTION_RETRIES:
                log.add('최대 재시도 초과 — Advisor 호출')
                verdict = 'FAIL'
                break

        elif verdict == 'FAIL':
            if validation.get('advisor_needed') and advisor_calls < MAX_ADVISOR_CALLS:
                advisor_calls += 1
                log.update(progress=60, message=f'Advisor 호출 ({advisor_calls}/{MAX_ADVISOR_CALLS})')
                _validation_str = json.dumps(validation, ensure_ascii=False, indent=2)
                adv_prompt = make_advisor_prompt(bus.task_id, advisor_calls,
                                                 _manifest_str, _result_str, _validation_str)
                ok_adv, adv_stdout = run_agent(adv_prompt, f'Advisor#{advisor_calls}', log,
                                               role='advisor', domain=domain)

                advice = bus.read(BusFile.ADVICE)
                # Advisor 결과 stdout에서 파싱 (SDK 모드)
                if advice is None and adv_stdout:
                    adv_match = f'ADVICE_DONE:{bus.task_id}:'
                    adv_idx = adv_stdout.find(adv_match)
                    adv_action = 'retry'
                    if adv_idx >= 0:
                        adv_raw = adv_stdout[adv_idx + len(adv_match):].split()[0].strip().lower()
                        adv_action = adv_raw if adv_raw in ('retry', 'escalate') else 'retry'
                    bus.write_advice(
                        root_cause=adv_stdout[:500],
                        solutions=[{'action': adv_stdout[:1000], 'target_agent': 'execution', 'priority': 'high'}],
                        escalate_to_user=(adv_action == 'escalate'),
                    )
                    advice = bus.read(BusFile.ADVICE)

                if advice and advice.get('escalate_to_user'):
                    log.error('Advisor: 사용자 에스컬레이션 필요')
                    _escalate_to_user(bus, log)
                    return

                exec_retries += 1
                log.add('Advisor 완료 — Execution 재시도')
            else:
                if advisor_calls >= MAX_ADVISOR_CALLS:
                    log.error(f'Advisor 최대 호출 ({MAX_ADVISOR_CALLS}회) 후에도 FAIL')
                    _escalate_to_user(bus, log)
                    return
                exec_retries += 1

    else:
        # Execution 루프가 max 초과로 종료
        log.error('최대 재시도 초과 — 에스컬레이션')
        if bus:
            _escalate_to_user(bus, log)
        return

    # ── 4. Reporter ─────────────────────────────────────────────
    if bus and verdict == 'PASS':
        _manifest_data = bus.read(BusFile.MANIFEST) or {}
        _manifest_str  = json.dumps(_manifest_data, ensure_ascii=False, indent=2)
        _result_data   = bus.read(BusFile.RESULT)
        _result_str    = json.dumps(_result_data, ensure_ascii=False, indent=2) if _result_data else ''
        rep_prompt = make_reporter_prompt(bus.task_id, domain, _manifest_str, _result_str)
        ok, rep_stdout = run_agent(rep_prompt, 'Reporter', log,
                                   role='reporter', domain=domain)

        report = bus.read(BusFile.REPORT)
        if report is None and rep_stdout:
            # stdout을 보고서 내용으로 저장
            bus.write_report(
                summary=rep_stdout[:500],
                sections=[{'title': '보고서', 'content': rep_stdout}],
            )

        log.done('파이프라인 완료')
        print('\n' + '='*60)
        print(rep_stdout or '[Reporter 출력 없음]')
        print('='*60)
        print(f'\nTask ID: {bus.task_id}')
        print(f'상태 확인: python .scripts/orchestrator.py --list')
    else:
        if bus:
            log.error(f'파이프라인 종료 (verdict={verdict})')


def _escalate_to_user(bus: AgentBus, log: AgentLog):
    """사용자 에스컬레이션: 현재 상태 요약 출력 + Slack 알림."""
    log.update(status='error', message='사용자 에스컬레이션')
    status = AgentBus.get_task_status(bus.task_id)
    print('\n' + '='*60)
    print('[에스컬레이션] 자동 해결 불가 — 사용자 확인 필요')
    print(f'Task ID : {bus.task_id}')
    print(f'Domain  : {status["domain"]}')
    print(f'Verdict : {status["verdict"]}')
    print(f'\n버스 파일 위치: .agents/bus/{bus.task_id}_*.json')
    advice = bus.read(BusFile.ADVICE)
    if advice:
        print(f'\n[Advisor 근본 원인] {advice.get("root_cause", "-")}')
        for s in advice.get('solutions', []):
            if s.get('target_agent') == 'user':
                print(f'  [{s["priority"]}] {s["action"]}')
    print('='*60)
    _notify_slack_escalation(bus, log)


def _notify_slack_escalation(bus: AgentBus, log: AgentLog):
    """Advisor escalate_to_user=True 시 Slack 알림 (non-fatal)."""
    import urllib.request
    try:
        webhook_url = os.environ.get('SLACK_WEBHOOK_URL', '')
        bot_token   = os.environ.get('SLACK_BOT_TOKEN', '')
        channel     = os.environ.get('SLACK_ESCALATION_CHANNEL', '#alerts')

        status = AgentBus.get_task_status(bus.task_id)
        advice = bus.read(BusFile.ADVICE)
        root_cause = advice.get('root_cause', '-') if advice else '-'

        message = (
            f':warning: *Agent Escalation \u2014 \uc0ac\uc6a9\uc790 \ud655\uc778 \ud544\uc694*\n'
            f'> Task ID: `{bus.task_id}`\n'
            f'> Domain: `{status["domain"]}`\n'
            f'> Verdict: `{status.get("verdict", "-")}`\n'
            f'> \uc6d0\uc778: {root_cause}\n'
            f'\uc138\ubd80 \uc815\ubcf4: `.agents/bus/{bus.task_id}_*.json`'
        )

        if webhook_url:
            payload = json.dumps({'text': message}).encode('utf-8')
            req = urllib.request.Request(
                webhook_url, data=payload,
                headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=10)
            log.add('Slack webhook \uc5d0\uc2a4\ucf4c\ub808\uc774\uc158 \uc54c\ub9bc \uc644\ub8cc')
        elif bot_token:
            payload = json.dumps(
                {'channel': channel, 'text': message}).encode('utf-8')
            req = urllib.request.Request(
                'https://slack.com/api/chat.postMessage',
                data=payload,
                headers={'Content-Type': 'application/json',
                         'Authorization': f'Bearer {bot_token}'})
            urllib.request.urlopen(req, timeout=10)
            log.add(f'Slack bot \uc5d0\uc2a4\ucf4c\ub808\uc774\uc158 \uc54c\ub9bc \uc644\ub8cc ({channel})')
        else:
            log.add('Slack \ud658\uacbd\ubcc0\uc218 \ubbf8\uc124\uc815 \u2014 \uc54c\ub9bc skip')
    except Exception as e:
        log.add(f'Slack \uc54c\ub9bc \uc2e4\ud328 (non-fatal): {e}')


# ── 병렬 실행 ──────────────────────────────────────────────────────

def parse_tasks_arg(tasks_str: str) -> list[tuple[str, str]]:
    """--tasks 'task1::domain1,task2::domain2' 파싱 → [(task, domain), ...]"""
    result = []
    for item in tasks_str.split(','):
        item = item.strip()
        if '::' not in item:
            print(f'[경고] --tasks 형식 오류: "{item}" (형식: 작업::도메인)')
            continue
        task, domain = item.split('::', 1)
        task, domain = task.strip(), domain.strip()
        if domain not in DOMAIN_MAP:
            print(f'[경고] 알 수 없는 도메인: {domain}')
            continue
        result.append((task, domain))
    return result


def run_parallel(task_domain_pairs: list[tuple[str, str]],
                 no_confirm: bool, log: AgentLog):
    """복수 도메인을 ThreadPoolExecutor로 병렬 실행."""
    remaining = get_remaining_tokens()
    if remaining is not None and remaining < TOKEN_PARALLEL_THRESHOLD:
        print(f'[경고] 토큰 잔여 {remaining:,} — 순차 실행으로 전환')
        for task, domain in task_domain_pairs:
            run_auto(task, domain, no_confirm, log)
        return

    workers = min(len(task_domain_pairs), 4)  # 최대 4개 병렬
    print(f'\n병렬 실행: {len(task_domain_pairs)}개 도메인 / {workers} workers')
    print('  ' + ', '.join(f'{d}({t[:20]})' for t, d in task_domain_pairs))

    results: dict[str, str] = {}  # domain → verdict

    def _run_one(pair: tuple[str, str]) -> tuple[str, str]:
        task, domain = pair
        sub_log = AgentLog(
            agent_id=f'Parallel_{domain}_{datetime.now().strftime("%H%M%S")}',
            title=f'Parallel — {domain}',
            agent_type='orchestrator',
        )
        sub_log.add(f'병렬 실행 시작: {task}')
        run_auto(task, domain, no_confirm=True, log=sub_log)
        status_list = AgentBus.list_tasks()
        # 가장 최근 해당 도메인 task의 verdict 반환
        for t in reversed(status_list):
            s = AgentBus.get_task_status(t['task_id'])
            if s['domain'] == domain:
                return domain, s.get('verdict') or 'unknown'
        return domain, 'unknown'

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_run_one, pair): pair
                   for pair in task_domain_pairs}
        for future in as_completed(futures):
            try:
                domain, verdict = future.result()
                results[domain] = verdict
                log.add(f'완료: {domain} → {verdict}')
                print(f'  [{domain}] {verdict}')
            except Exception as e:
                pair = futures[future]
                log.add(f'오류: {pair[1]} — {e}')
                results[pair[1]] = 'error'

    # 최종 요약
    print('\n' + '='*60)
    print('병렬 실행 완료')
    for domain, verdict in results.items():
        icon = 'PASS' if verdict == 'PASS' else 'FAIL'
        print(f'  {icon}  {domain}')
    print('='*60)
    log.done(f'병렬 완료: {len(results)}개 도메인')

# ── Full Pipeline (User Interface → Advisor → Eval → 승인 게이트) ──

def make_user_interface_prompt(task: str, domain: str, task_id: str) -> str:
    return (
        f'당신은 User Interface Agent입니다.\n\n'
        f'Role Rules: {_abs("global/04_AgentEcosystem/agents/role_rules__user_interface.md")}\n\n'
        f'Task ID: {task_id}\nDomain: {domain}\n\n'
        f'사용자 요청: {task}\n\n'
        f'수행 순서:\n'
        f'1. 요청을 구조화하여 AgentBus.write_requirement()로 저장\n'
        f'   from agent_bus import AgentBus; bus = AgentBus("{task_id}")\n'
        f'2. 에이전트 내부 소통은 터미널 출력 금지 — 로그만\n'
        f'3. 완료 후 "REQUIREMENT_DONE:{task_id}" 를 마지막 줄에 출력\n\n'
        f'AgentBus import: sys.path.insert(0, "{_abs(".scripts")}")'
    )


def make_advisor_plan_prompt(task_id: str, domain: str, task: str) -> str:
    return (
        f'당신은 Advisor Agent (PM 역할)입니다.\n\n'
        f'Role Rules: {_abs("global/04_AgentEcosystem/agents/role_rules__advisor.md")}\n'
        f'Plan Schema: {_abs("global/04_AgentEcosystem/protocol/advisor_plan_schema.md")}\n\n'
        f'Task ID: {task_id}\nDomain: {domain}\nTask: {task}\n\n'
        f'수행 순서 [Phase 1-2]:\n'
        f'1. 로컬 컨텍스트 파악: global/01_Identity, 02_Profile, 03_Instructions 읽기\n'
        f'2. .agents/advisor/learnings/ 이전 학습 파일 읽기 (mtime 내림차순 최신 10건만)\n'
        f'3. advisor_plan_{task_id}.md 작성 → global/05_PM_Outputs/ 저장\n'
        f'4. AgentBus.write_advisor_plan()으로 버스 파일 저장\n'
        f'   from agent_bus import AgentBus; bus = AgentBus("{task_id}")\n'
        f'5. 완료 후 "ADVISOR_PLAN_DONE:{task_id}" 를 마지막 줄에 출력\n\n'
        f'AgentBus import: sys.path.insert(0, "{_abs(".scripts")}")'
    )


def make_advisor_evaluation_prompt(task_id: str, manifest_content: str = '',
                                    result_content: str = '',
                                    validation_content: str = '') -> str:
    return (
        f'당신은 Advisor Agent (PM 역할)입니다.\n\n'
        f'=== Task Manifest ===\n{manifest_content or "(없음)"}\n\n'
        f'=== Execution Result (요약) ===\n{result_content or "(없음)"}\n\n'
        f'=== Validation 결과 ===\n{validation_content or "(없음)"}\n\n'
        f'Task ID: {task_id}\n\n'
        f'위 내용을 분석하여 10항목 평가를 수행하라:\n'
        f'  code_quality, agent_utilization, parallelization, token_cost,\n'
        f'  retry_waste, comm_efficiency, completion_rate,\n'
        f'  duration, issue_resolution, autonomy\n\n'
        f'각 항목을 0~10점으로 평가하고, 아래 JSON 형식으로 출력하라:\n\n'
        f'EVALUATION_JSON:{{\n'
        f'  "scores": {{\n'
        f'    "code_quality": {{"score": 0, "evidence": "...", "issues": []}},\n'
        f'    "completion_rate": {{"score": 0, "evidence": "...", "issues": []}},\n'
        f'    ... (나머지 8항목 동일 형식)\n'
        f'  }},\n'
        f'  "total_score": 0,\n'
        f'  "commit_ready": false,\n'
        f'  "improvement_items": ["개선항목1", "개선항목2"]\n'
        f'}}\n\n'
        f'그 다음 줄에 반드시 아래 신호를 출력하라:\n'
        f'EVALUATION_DONE:{task_id}:{{total_score}}\n\n'
        f'※ SDK 직접 호출 모드: 파일 저장은 orchestrator가 자동 처리함.\n'
        f'   AgentBus Python 코드를 응답에 포함하지 말 것.'
    )


def make_advisor_learning_prompt(task_id: str) -> str:
    return (
        f'당신은 Advisor Agent (PM 역할)입니다.\n\n'
        f'Role Rules: {_abs("global/04_AgentEcosystem/agents/role_rules__advisor.md")}\n\n'
        f'Task ID: {task_id}\n\n'
        f'수행 순서 [Phase 6 — 자기개선]:\n'
        f'1. .agents/bus/{task_id}_evaluation.json 분석\n'
        f'2. 낮은 점수 항목의 근본 원인 파악\n'
        f'3. AgentBus.write_learning()으로 patterns 저장\n'
        f'   from agent_bus import AgentBus; bus = AgentBus("{task_id}")\n'
        f'4. {os.path.join(PROJECT_ROOT, ".agents", "advisor", "learnings")}/를 생성하고\n'
        f'   학습 파일을 {{YYYYMMDD}}_{task_id}.json으로 복사 저장\n'
        f'5. 완료 후 "LEARNING_DONE:{task_id}" 를 마지막 줄에 출력\n\n'
        f'AgentBus import: sys.path.insert(0, "{_abs(".scripts")}")'
    )


def git_commit_and_pr(task_id: str, task_summary: str, branch_name: str,
                      log: AgentLog) -> str | None:
    """평가 승인 후 git commit + PR 생성. PR URL 반환."""
    import subprocess as _sp

    def _run(cmd: list[str]) -> tuple[int, str]:
        r = _sp.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        return r.returncode, (r.stdout + r.stderr).strip()

    # feat/{task_id} 브랜치 생성 (없으면 신규, 있으면 체크아웃)
    rc, _ = _run(['git', 'checkout', '-b', branch_name])
    if rc != 0:
        rc, out = _run(['git', 'checkout', branch_name])
        if rc != 0:
            log.add(f'브랜치 체크아웃 실패: {out}')
            return None
    log.add(f'브랜치 전환: {branch_name}')

    # git add (버스 파일 제외, 주요 변경 파일만)
    rc, out = _run(['git', 'add', '-A', '--', ':(exclude).agents/bus/*'])
    log.add(f'git add: rc={rc}')

    # git commit
    commit_msg = f'feat({task_id}): {task_summary[:60]}'
    rc, out = _run(['git', 'commit', '-m', commit_msg])
    if rc != 0:
        log.add(f'git commit 실패: {out}')
        return None
    log.add(f'git commit 완료: {commit_msg}')

    # git push
    rc, out = _run(['git', 'push', '-u', 'origin', branch_name])
    if rc != 0:
        log.add(f'git push 실패: {out}')
        return None
    log.add('git push 완료')

    # gh pr create
    rc, out = _run([
        'gh', 'pr', 'create',
        '--title', commit_msg,
        '--body', f'Task ID: {task_id}\n\nAuto-generated by Orchestrator full pipeline.',
        '--head', branch_name,
    ])
    if rc != 0:
        log.add(f'gh pr create 실패: {out}')
        return None

    pr_url = out.strip().split()[-1]
    log.add(f'PR 생성: {pr_url}')
    return pr_url


def run_full_pipeline(task: str, domain: str, no_confirm: bool, log: AgentLog):
    """
    User Interface → Advisor Plan → Execution·Validation 루프 →
    Advisor 평가 → 사용자 승인 게이트 → commit/PR
    """
    preset = get_domain_preset(domain)
    adv_model    = preset.get('advisor_model',   'claude-opus-4-5')
    temp_adv     = preset.get('temperature_advisor', 0.2)
    max_tok_adv  = preset.get('max_tokens_advisor',  4096)
    ui_model     = AGENT_MODELS.get('user_interface', 'claude-haiku-4-5-20251001')
    ui_temp      = AGENT_PARAMS.get('user_interface', {}).get('temperature', 0.3)
    ui_max_tok   = AGENT_PARAMS.get('user_interface', {}).get('max_tokens', 1024)

    bus = AgentBus()
    task_id = bus.task_id
    log.add(f'Full Pipeline 시작: task_id={task_id}')

    # ── Step 1: User Interface — requirement 구조화 ────────────────
    log.update(progress=5, message='User Interface: 요구사항 구조화')
    ui_prompt = make_user_interface_prompt(task, domain, task_id)
    _run_agent(ui_prompt, 'UserInterface', log,
               model=ui_model, temperature=ui_temp, max_tokens=ui_max_tok)

    req = bus.read(BusFile.REQUIREMENT)
    if req is None:
        # fallback: 기본 requirement 작성
        bus.write_requirement(
            raw_request=task,
            structured={'goal': task, 'domain': domain,
                        'constraints': [], 'expected_outputs': []},
        )
        req = bus.read(BusFile.REQUIREMENT)

    # ── Step 2: Advisor — 컨텍스트 파악 + 플랜 수립 ───────────────
    log.update(progress=10, message='Advisor: 플랜 수립 중')
    plan_prompt = make_advisor_plan_prompt(task_id, domain, task)
    _run_agent(plan_prompt, 'AdvisorPlan', log,
               model=adv_model, temperature=temp_adv, max_tokens=max_tok_adv)

    advisor_plan = bus.read(BusFile.ADVISOR_PLAN)
    if advisor_plan:
        plan_path = advisor_plan.get('plan_md_path', '')
        print(f'\n[Advisor 플랜] {plan_path}')

    # ── Step 3: Execution ↔ Validation 루프 (기존 run_auto 재사용) ─
    log.update(progress=20, message='Execution 루프 시작')
    run_auto(task, domain, no_confirm=True, log=log, shared_task_id=task_id)

    # 루프 종료 후 verdict 확인 (동일 task_id bus에서 읽음)
    validation = bus.read(BusFile.VALIDATION)
    verdict = validation.get('verdict', 'FAIL') if validation else 'FAIL'
    log.add(f'Execution 루프 완료: verdict={verdict}')

    if verdict != 'PASS':
        log.error(f'파이프라인 종료 (verdict={verdict}) — 승인 게이트 도달 불가')
        return

    # ── Step 4: Advisor — 결과 리뷰 + 10항목 평가 ─────────────────
    log.update(progress=80, message='Advisor: 결과 평가 중')
    _manifest_eval  = json.dumps(bus.read(BusFile.MANIFEST)  or {}, ensure_ascii=False)[:2000]
    _result_eval    = json.dumps(bus.read(BusFile.RESULT)    or {}, ensure_ascii=False)[:2000]
    _validation_eval= json.dumps(bus.read(BusFile.VALIDATION)or {}, ensure_ascii=False)[:1000]
    eval_prompt = make_advisor_evaluation_prompt(
        task_id,
        manifest_content=_manifest_eval,
        result_content=_result_eval,
        validation_content=_validation_eval,
    )
    ok_eval, eval_stdout = _run_agent(eval_prompt, 'AdvisorEval', log,
                                       model=adv_model, temperature=temp_adv,
                                       max_tokens=max_tok_adv)

    evaluation = bus.read(BusFile.EVALUATION)
    if evaluation is None and eval_stdout:
        # EVALUATION_DONE:{task_id}:{total_score} 신호 파싱
        _eval_match_str = f'EVALUATION_DONE:{task_id}:'
        _eval_idx = eval_stdout.find(_eval_match_str)
        if _eval_idx >= 0:
            _raw_score = eval_stdout[_eval_idx + len(_eval_match_str):].split()[0].strip()
            try:
                _total_score = int(_raw_score)
            except (ValueError, IndexError):
                _total_score = 0
            # EVALUATION_JSON:{...} 블록 파싱
            _json_match = re.search(r'EVALUATION_JSON:\s*(\{[\s\S]*?\})\s*\n', eval_stdout)
            if _json_match:
                try:
                    _eval_data = json.loads(_json_match.group(1))
                    bus.write_evaluation(
                        scores=_eval_data.get('scores', {}),
                        total_score=_total_score,
                        improvement_items=_eval_data.get('improvement_items', []),
                        commit_ready=_eval_data.get('commit_ready', _total_score >= 70),
                    )
                    log.add(f'evaluation.json 저장 완료 (score={_total_score})')
                except (json.JSONDecodeError, Exception) as _e:
                    bus.write_evaluation(scores={}, total_score=_total_score,
                                          improvement_items=[],
                                          commit_ready=(_total_score >= 70))
                    log.add(f'evaluation.json 기본 저장 (score={_total_score}, err={_e})')
            else:
                bus.write_evaluation(scores={}, total_score=_total_score,
                                      improvement_items=[],
                                      commit_ready=(_total_score >= 70))
                log.add(f'evaluation.json 저장 (EVALUATION_JSON 블록 없음, score={_total_score})')
        evaluation = bus.read(BusFile.EVALUATION)

    if evaluation is None:
        log.add('evaluation.json 없음 — 평가 생략')
        evaluation = {'total_score': 0, 'grade': '?', 'commit_ready': False,
                      'summary': '평가 미완료', 'improvement_items': []}

    # ── Step 5: 사용자 승인 게이트 ────────────────────────────────
    _print_evaluation(task_id, evaluation)

    if no_confirm:
        bus.write_user_decision('approve')
        log.add('사용자 승인: auto-approve (no_confirm)')
        print('\n[자동 승인] --no-confirm 플래그로 자동 처리됨')
        return

    while True:
        decision = input('\napprove / reject / feedback 중 선택: ').strip().lower()
        if decision in ('approve', 'a'):
            bus.write_user_decision('approve')
            log.add('사용자 승인: approve')
            break
        elif decision in ('reject', 'r'):
            bus.write_user_decision('reject')
            log.add('사용자 거절: reject')
            print('거절됨. 파이프라인 종료.')

            # Phase 6: 자기개선
            _run_advisor_learning(task_id, adv_model, temp_adv, max_tok_adv, log)
            return
        else:
            # feedback → Execution 재시도
            bus.write_user_decision('feedback', feedback=decision)
            log.add(f'피드백: {decision}')
            print('피드백 반영 — Execution 재실행 중...')
            run_auto(task + f'\n[추가 피드백] {decision}',
                     domain, no_confirm=True, log=log)

            # 재평가
            _manifest_eval2   = json.dumps(bus.read(BusFile.MANIFEST)  or {}, ensure_ascii=False)[:2000]
            _result_eval2     = json.dumps(bus.read(BusFile.RESULT)    or {}, ensure_ascii=False)[:2000]
            _validation_eval2 = json.dumps(bus.read(BusFile.VALIDATION)or {}, ensure_ascii=False)[:1000]
            eval_prompt2 = make_advisor_evaluation_prompt(
                task_id,
                manifest_content=_manifest_eval2,
                result_content=_result_eval2,
                validation_content=_validation_eval2,
            )
            ok_eval2, eval_stdout2 = _run_agent(eval_prompt2, 'AdvisorEval#2', log,
                                                 model=adv_model, temperature=temp_adv,
                                                 max_tokens=max_tok_adv)
            # stdout 파싱하여 evaluation.json 저장
            if eval_stdout2:
                _em2 = f'EVALUATION_DONE:{task_id}:'
                _ei2 = eval_stdout2.find(_em2)
                if _ei2 >= 0:
                    try:
                        _ts2 = int(eval_stdout2[_ei2 + len(_em2):].split()[0].strip())
                    except (ValueError, IndexError):
                        _ts2 = 0
                    _jm2 = re.search(r'EVALUATION_JSON:\s*(\{[\s\S]*?\})\s*\n', eval_stdout2)
                    if _jm2:
                        try:
                            _ed2 = json.loads(_jm2.group(1))
                            bus.write_evaluation(scores=_ed2.get('scores', {}),
                                                  total_score=_ts2,
                                                  improvement_items=_ed2.get('improvement_items', []),
                                                  commit_ready=_ed2.get('commit_ready', _ts2 >= 70))
                        except (json.JSONDecodeError, Exception):
                            bus.write_evaluation(scores={}, total_score=_ts2,
                                                  improvement_items=[], commit_ready=(_ts2 >= 70))
            evaluation = bus.read(BusFile.EVALUATION) or evaluation
            _print_evaluation(task_id, evaluation)

    # ── Step 6: commit + PR ────────────────────────────────────────
    branch_name = f'feat/{task_id}'

    pr_url = git_commit_and_pr(task_id, task, branch_name, log)
    if pr_url:
        print(f'\nPR 생성 완료: {pr_url}')
    else:
        print('\ngit commit/PR 실패 — 로그 확인: .agents/')

    # Phase 6: 자기개선
    _run_advisor_learning(task_id, adv_model, temp_adv, max_tok_adv, log)
    log.done('Full Pipeline 완료')


def _print_evaluation(task_id: str, evaluation: dict):
    """평가 보고서를 터미널에 출력."""
    scores = evaluation.get('scores', {})
    print(f'\n{"="*60}')
    print(f'=== 에이전트 평가 보고서 (Task: {task_id}) ===')
    print(f'총점: {evaluation.get("total_score", "?")}/100  등급: {evaluation.get("grade", "?")}')
    print()

    groups = [
        ('[효율성]', ['code_quality', 'agent_utilization', 'parallelization']),
        ('[경제성]', ['token_cost', 'retry_waste', 'comm_efficiency']),
        ('[생산성]', ['completion_rate', 'duration', 'issue_resolution', 'autonomy']),
    ]
    labels = {
        'code_quality': '코드 품질', 'agent_utilization': '에이전트 활용',
        'parallelization': '병렬화 효율', 'token_cost': '토큰 비용',
        'retry_waste': '재시도 낭비', 'comm_efficiency': '소통 효율',
        'completion_rate': '태스크 완결률', 'duration': '소요 시간',
        'issue_resolution': '이슈 해결', 'autonomy': '자율성',
    }
    for group_name, keys in groups:
        print(group_name)
        for k in keys:
            item = scores.get(k, {})
            s = item.get('score', '-')
            ev = item.get('evidence', '')
            print(f'  {labels.get(k, k):<12}: {s}/10 — {ev}')
        print()

    print(f'요약: {evaluation.get("summary", "-")}')
    impr = evaluation.get('improvement_items', [])
    if impr:
        print(f'개선 항목: {", ".join(impr)}')
    print(f'커밋 준비: {"O" if evaluation.get("commit_ready") else "X"}')
    print('='*60)


def _run_advisor_learning(task_id: str, model: str, temperature: float,
                          max_tokens: int, log: AgentLog):
    """Phase 6 자기개선 실행."""
    os.makedirs(os.path.join(PROJECT_ROOT, '.agents', 'advisor', 'learnings'),
                exist_ok=True)
    learn_prompt = make_advisor_learning_prompt(task_id)
    _run_agent(learn_prompt, 'AdvisorLearning', log,
               model=model, temperature=temperature, max_tokens=max_tokens)
    log.add('Phase 6 자기개선 완료')


# ── 메인 ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Multi-Agent Orchestrator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # 단일 도메인
    parser.add_argument('--task',       type=str, help='수행할 작업 (단일 도메인)')
    parser.add_argument('--domain',     type=str, default='pkb_worklog',
                        choices=list(DOMAIN_MAP.keys()))
    # 복수 도메인 병렬
    parser.add_argument('--tasks',      type=str,
                        help='복수 도메인: "작업1::도메인1,작업2::도메인2"')
    parser.add_argument('--parallel',   action='store_true',
                        help='--tasks와 함께 사용: 병렬 실행 (기본: 순차)')
    # 공통 옵션
    parser.add_argument('--dry-run',       action='store_true', help='Manifest+프롬프트 미리보기')
    parser.add_argument('--auto',          action='store_true', help='SDK/API 자동 실행 모드')
    parser.add_argument('--no-confirm',    action='store_true', help='--auto 실행 전 확인 생략')
    parser.add_argument('--list',          action='store_true', help='bus 작업 목록 조회')
    parser.add_argument('--compare',       action='store_true',
                        help='전체 도메인 모델 배정·비용 비교표 출력')
    parser.add_argument('--full-pipeline', action='store_true',
                        help='UserInterface→Advisor→Eval→승인 게이트→commit/PR 전체 플로우')
    parser.add_argument('--auto-domain',   action='store_true',
                        help='도메인 자동 판단 (태스크 키워드 기반). --domain 지정 불필요')
    args = parser.parse_args()

    if args.list:
        list_tasks()
        return

    if args.compare:
        compare_domains()
        return

    # --tasks (복수 도메인) vs --task (단일 도메인)
    if args.tasks:
        pairs = parse_tasks_arg(args.tasks)
        if not pairs:
            print('[오류] --tasks 파싱 실패. 형식: "작업1::도메인1,작업2::도메인2"')
            return

        remaining = get_remaining_tokens()
        if remaining is not None:
            tag = 'OK' if remaining > TOKEN_PARALLEL_THRESHOLD else 'LOW'
            print(f'토큰 잔여: {remaining:,} / 72,000 [{tag}]')

        if args.auto:
            claude = find_claude_cli()
            if not claude:
                print('[오류] claude CLI를 찾을 수 없습니다.')
                return

            mode = '병렬' if args.parallel else '순차'
            print(f'\n복수 도메인 {mode} 실행: {len(pairs)}개')
            for t, d in pairs:
                print(f'  {d}: {t}')

            if not args.no_confirm:
                ans = input(f'\n{mode} 실행을 시작할까요? [y/N] ').strip().lower()
                if ans != 'y':
                    print('취소됨.')
                    return

            log = AgentLog(
                agent_id=f'Orchestrator_Multi_{datetime.now().strftime("%Y-%m-%d_%H%M%S")}',
                title=f'Orchestrator ({mode}) — {len(pairs)}도메인',
                agent_type='orchestrator',
            )
            try:
                if args.parallel:
                    run_parallel(pairs, args.no_confirm, log)
                else:
                    for task, domain in pairs:
                        log.add(f'순차 실행: {domain}')
                        run_auto(task, domain, no_confirm=True, log=log)
            except KeyboardInterrupt:
                log.error('사용자 중단 (Ctrl+C)')
                print('\n중단됨.')
            except Exception as e:
                log.error(f'오류: {e}')
                raise
        else:
            # dry-run 모드
            for task, domain in pairs:
                print(f'\n--- {domain} ---')
                dry_run(task, domain)
        return

    if not args.task:
        parser.print_help()
        return

    # --auto-domain: 키워드 기반 도메인 자동 판단
    if args.auto_domain:
        args.domain = detect_domain(args.task)

    # ── 단일 도메인 ────────────────────────────────────────────────

    # 토큰 예산 표시
    remaining = get_remaining_tokens()
    if remaining is not None:
        status = 'OK' if remaining > TOKEN_PARALLEL_THRESHOLD else 'LOW'
        print(f'토큰 잔여: {remaining:,} / 72,000 [{status}]')
        if remaining < TOKEN_PARALLEL_THRESHOLD:
            print(f'  -> 잔여 {TOKEN_PARALLEL_THRESHOLD:,} 미만 — 순차 실행 모드')

    if args.dry_run:
        dry_run(args.task, args.domain)
        return

    if args.full_pipeline:
        log = AgentLog(
            agent_id=f'Orchestrator_Full_{datetime.now().strftime("%Y-%m-%d_%H%M%S")}',
            title=f'Full Pipeline — {args.domain}',
            agent_type='orchestrator',
        )
        log.add(f'Full Pipeline 시작: {args.task}')
        try:
            run_full_pipeline(args.task, args.domain, args.no_confirm, log)
        except KeyboardInterrupt:
            log.error('사용자 중단 (Ctrl+C)')
            print('\n중단됨.')
        except Exception as e:
            log.error(f'Full Pipeline 오류: {e}')
            raise
        return

    if args.auto:
        preset = DOMAIN_PRESETS.get(args.domain, 'default')
        exec_model, _, _ = get_domain_config(args.domain, 'execution')
        print(f'\n도메인: {args.domain}  (preset={preset})')
        print(f'Execution 모델: {exec_model}')
        print(f'작업: {args.task}')
        print(f'최대 Execution 재시도: {MAX_EXECUTION_RETRIES}회')
        print(f'최대 Advisor 호출: {MAX_ADVISOR_CALLS}회')

        if not args.no_confirm:
            ans = input('\n자동 실행을 시작할까요? [y/N] ').strip().lower()
            if ans != 'y':
                print('취소됨.')
                return

        log = AgentLog(
            agent_id=f'Orchestrator_{datetime.now().strftime("%Y-%m-%d_%H%M%S")}',
            title=f'Orchestrator (Auto) — {args.domain}',
            agent_type='orchestrator',
        )
        log.add(f'Auto 모드 시작: {args.task}')
        log.add(f'도메인: {args.domain}')

        try:
            run_auto(args.task, args.domain, args.no_confirm, log)
        except KeyboardInterrupt:
            log.error('사용자 중단 (Ctrl+C)')
            print('\n중단됨.')
        except Exception as e:
            log.error(f'Orchestrator 오류: {e}')
            raise

    else:
        # 기본 모드: Manifest 생성 + 프롬프트 출력
        log = AgentLog(
            agent_id=f'Orchestrator_{datetime.now().strftime("%Y-%m-%d")}',
            title=f'Orchestrator — {args.domain}',
            agent_type='orchestrator',
        )
        bus = build_manifest(args.task, args.domain)
        log.add(f'Manifest: {bus._path(BusFile.MANIFEST)}')
        log.update(progress=20, message='Manifest 완료 — 수동 실행 대기')

        print(f'\nTask ID: {bus.task_id}')
        print(f'Manifest: {bus._path(BusFile.MANIFEST)}')
        print('\n--- Execution Agent 프롬프트 ---')
        print(make_execution_prompt(args.task, args.domain, bus.task_id,
                                    bus._path(BusFile.MANIFEST)))
        print('\n자동 실행: python .scripts/orchestrator.py'
              f' --task "{args.task}" --domain {args.domain} --auto')


if __name__ == '__main__':
    main()
