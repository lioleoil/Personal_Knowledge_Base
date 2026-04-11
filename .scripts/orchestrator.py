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
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
)
sys.path.insert(0, os.path.join(PROJECT_ROOT, '.scripts'))

# .env 자동 로드 (nova_helper/.env 우선, 루트 .env 차선)
def _load_dotenv():
    for env_path in [
        os.path.join(PROJECT_ROOT, 'projects', 'nova_helper', '.env'),
        os.path.join(PROJECT_ROOT, '.env'),
    ]:
        if os.path.exists(env_path):
            with open(env_path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, _, v = line.partition('=')
                        os.environ.setdefault(k.strip(), v.strip())
            break

_load_dotenv()

from agent_bus import AgentBus, BusFile
from agent_log import AgentLog

# ── 상수 ──────────────────────────────────────────────────────────
TOKEN_USAGE_PATH = os.path.join(PROJECT_ROOT, '.status', 'token_usage.json')
TOKEN_PARALLEL_THRESHOLD = 10_000

# 에스컬레이션 한도 (플랜 설계 기준)
MAX_EXECUTION_RETRIES = 5
MAX_ADVISOR_CALLS = 3

# 버스 파일 대기 설정
BUS_POLL_INTERVAL = 3    # 초
BUS_POLL_TIMEOUT  = 600  # 10분

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
        f'1. Manifest 읽기: {bus_path}\n'
        f'2. context_files 참고하여 작업 수행\n'
        f'3. 결과를 AgentBus.write_result()로 저장\n'
        f'   from agent_bus import AgentBus; bus = AgentBus("{task_id}")\n'
        f'4. 완료 후 "EXECUTION_DONE:{task_id}" 를 마지막 줄에 출력\n\n'
        f'AgentBus import: sys.path.insert(0, "{_abs(".scripts")}")'
    )

def make_validation_prompt(task_id: str, domain: str) -> str:
    return (
        f'당신은 Validation Agent입니다.\n\n'
        f'Role Rules: {_abs("global/04_AgentEcosystem/agents/role_rules__validation.md")}\n'
        f'Protocol: {_abs("global/04_AgentEcosystem/protocol/task_manifest_schema.md")}\n\n'
        f'Task ID: {task_id}\n\n'
        f'수행 순서:\n'
        f'1. Manifest 읽기: .agents/bus/{task_id}_manifest.json\n'
        f'2. Result 읽기: .agents/bus/{task_id}_result.json\n'
        f'3. Role Rules 기준 3단계 검증 수행\n'
        f'4. AgentBus.write_validation()으로 verdict 저장\n'
        f'   from agent_bus import AgentBus; bus = AgentBus("{task_id}")\n'
        f'5. 완료 후 "VALIDATION_DONE:{task_id}:{{PASS|FAIL|INSUFFICIENT}}" 를 마지막 줄에 출력\n\n'
        f'AgentBus import: sys.path.insert(0, "{_abs(".scripts")}")'
    )

def make_advisor_prompt(task_id: str, call_count: int) -> str:
    return (
        f'당신은 Advisor Agent입니다. [호출 {call_count}회차]\n\n'
        f'Role Rules: {_abs("global/04_AgentEcosystem/agents/role_rules__advisor.md")}\n\n'
        f'Task ID: {task_id}\n\n'
        f'수행 순서:\n'
        f'1. Manifest/Result/Validation 읽기 (.agents/bus/{task_id}_*.json)\n'
        f'2. 근본 원인 분석\n'
        f'3. AgentBus.write_advice()로 솔루션 저장\n'
        f'   from agent_bus import AgentBus; bus = AgentBus("{task_id}")\n'
        f'4. 완료 후 "ADVICE_DONE:{task_id}:{{escalate|retry}}" 를 마지막 줄에 출력\n\n'
        f'AgentBus import: sys.path.insert(0, "{_abs(".scripts")}")'
    )

def make_reporter_prompt(task_id: str, domain: str) -> str:
    return (
        f'당신은 Reporter Agent입니다.\n\n'
        f'Role Rules: {_abs("global/04_AgentEcosystem/agents/role_rules__reporter.md")}\n\n'
        f'Task ID: {task_id}\n\n'
        f'수행 순서:\n'
        f'1. Manifest/Result/Validation 읽기 (.agents/bus/{task_id}_*.json)\n'
        f'2. 마크다운 보고서 작성\n'
        f'3. AgentBus.write_report()로 저장\n'
        f'   from agent_bus import AgentBus; bus = AgentBus("{task_id}")\n'
        f'4. 필요 시 global/05_PM_Outputs/{{domain}}_report_{datetime.now().strftime("%Y-%m-%d")}.md 저장\n'
        f'5. 보고서 내용을 stdout에 출력\n\n'
        f'AgentBus import: sys.path.insert(0, "{_abs(".scripts")}")'
    )

# ── claude CLI 실행 ────────────────────────────────────────────────

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
                     timeout: int = 600) -> tuple[bool, str]:
    """
    claude -p <prompt> 를 서브프로세스로 실행.
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

    print('\n=== Execution Agent 프롬프트 미리보기 ===')
    print(make_execution_prompt(task, domain, bus.task_id,
                                bus._path(BusFile.MANIFEST)))
    print('\n--dry-run 없이 실행하면 수행됩니다.')
    print(f'  자동 실행: python .scripts/orchestrator.py --task "{task}" --domain {domain} --auto')

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

def run_auto(task: str, domain: str, no_confirm: bool, log: AgentLog):
    """Execution → Validation → (Advisor) → Reporter 자동 실행."""

    exec_retries   = 0
    advisor_calls  = 0
    bus: AgentBus | None = None

    # ── 1. Execution 루프 ────────────────────────────────────────
    while exec_retries <= MAX_EXECUTION_RETRIES:
        # Manifest 생성 (재시도 시 새 bus 유지, retry_count 갱신)
        if bus is None:
            bus = build_manifest(task, domain, retry_count=exec_retries)
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
        ok, stdout = run_claude_agent(prompt, f'Execution#{exec_retries+1}', log)

        if not ok:
            exec_retries += 1
            if exec_retries > MAX_EXECUTION_RETRIES:
                break
            log.add(f'Execution 실패 — 재시도 {exec_retries}/{MAX_EXECUTION_RETRIES}')
            time.sleep(2)
            continue

        # result.json 대기 (에이전트가 직접 쓰지 않은 경우 stdout 파싱 시도)
        result_data = bus.read(BusFile.RESULT)
        if result_data is None:
            log.add('result.json 없음 — stdout에서 파싱 시도')
            # stdout에 "EXECUTION_DONE:<task_id>" 확인
            if f'EXECUTION_DONE:{bus.task_id}' not in stdout:
                log.add('EXECUTION_DONE 신호 없음 — Execution 실패로 처리')
                exec_retries += 1
                continue

            # 결과 없이 신호만 있으면 기본 result 작성
            bus.write_result(domain, 'partial', [], errors=['result.json 미작성'])

        log.update(progress=40, message='Execution 완료 — Validation 진행')

        # ── 2. Validation ──────────────────────────────────────
        val_prompt = make_validation_prompt(bus.task_id, domain)
        ok, val_stdout = run_claude_agent(val_prompt, 'Validation', log)

        validation = bus.read(BusFile.VALIDATION)
        if validation is None and f'VALIDATION_DONE:{bus.task_id}' in (val_stdout or ''):
            # stdout 파싱으로 verdict 추출
            match_str = f'VALIDATION_DONE:{bus.task_id}:'
            idx = val_stdout.find(match_str)
            verdict = val_stdout[idx + len(match_str):].split()[0] if idx >= 0 else 'INSUFFICIENT'
            bus.write_validation(verdict, advisor_needed=(verdict == 'FAIL'))
            validation = bus.read(BusFile.VALIDATION)

        if validation is None:
            log.add('validation.json 없음 — INSUFFICIENT 처리')
            validation = {'verdict': 'INSUFFICIENT', 'advisor_needed': False}

        verdict = validation.get('verdict', 'INSUFFICIENT')
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
                adv_prompt = make_advisor_prompt(bus.task_id, advisor_calls)
                run_claude_agent(adv_prompt, f'Advisor#{advisor_calls}', log)

                advice = bus.read(BusFile.ADVICE)
                if advice and advice.get('escalate_to_user'):
                    # 사용자 에스컬레이션
                    log.error('Advisor: 사용자 에스컬레이션 필요')
                    _escalate_to_user(bus, log)
                    return

                exec_retries += 1  # Advisor 후 재시도
                log.add('Advisor 완료 — Execution 재시도')
            else:
                # Advisor 한도 초과 또는 advisor_needed=false
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
        rep_prompt = make_reporter_prompt(bus.task_id, domain)
        ok, rep_stdout = run_claude_agent(rep_prompt, 'Reporter', log)

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
    parser.add_argument('--dry-run',    action='store_true', help='Manifest+프롬프트 미리보기')
    parser.add_argument('--auto',       action='store_true', help='claude CLI 자동 실행 모드')
    parser.add_argument('--no-confirm', action='store_true', help='--auto 실행 전 확인 생략')
    parser.add_argument('--list',       action='store_true', help='bus 작업 목록 조회')
    args = parser.parse_args()

    if args.list:
        list_tasks()
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

    if args.auto:
        # claude CLI 존재 여부 확인
        claude = find_claude_cli()
        if not claude:
            print('\n[오류] claude CLI를 찾을 수 없습니다.')
            print('Claude Code가 PATH에 등록되었는지 확인하세요.')
            print('수동 모드: --dry-run 후 출력된 프롬프트를 직접 실행')
            return

        print(f'\nclaude CLI: {claude}')
        print(f'도메인: {args.domain}')
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
