"""
주간 회고 스크립트
매주 토요일 15:00 자동 실행 (Claude Code scheduled trigger)

수동 실행:
  python .scripts/retrospective.py
  python .scripts/retrospective.py --dry-run   # 수집만, 저장·출력 없음
  python .scripts/retrospective.py --days 14   # 지난 14일치 수집

산출물: global/05_PM_Outputs/retrospective_{YYYY-MM-DD}.md
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
)
sys.path.insert(0, os.path.join(PROJECT_ROOT, '.scripts'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, '.status'))

from agent_log import AgentLog

AGENTS_DIR   = os.path.join(PROJECT_ROOT, '.agents')
PM_OUTPUTS   = os.path.join(PROJECT_ROOT, 'global', '05_PM_Outputs')


# ── 로그 수집 ──────────────────────────────────────────────────────

def collect_week_logs(days: int = 7) -> list[dict]:
    """지난 N일 에이전트 로그 JSON 수집."""
    cutoff = datetime.now() - timedelta(days=days)
    logs = []
    if not os.path.exists(AGENTS_DIR):
        return logs

    for agent_type in os.listdir(AGENTS_DIR):
        agent_dir = os.path.join(AGENTS_DIR, agent_type)
        if not os.path.isdir(agent_dir) or agent_type == 'bus':
            continue
        for fname in os.listdir(agent_dir):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(agent_dir, fname)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                if mtime < cutoff:
                    continue
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data['_source_file'] = fpath
                data['_agent_type']  = agent_type
                logs.append(data)
            except Exception:
                pass
    return logs


def collect_evaluations(days: int = 7) -> list[dict]:
    """지난 N일 평가 보고서 (bus/*_evaluation.json) 수집."""
    cutoff = datetime.now() - timedelta(days=days)
    evaluations = []
    bus_dir = os.path.join(AGENTS_DIR, 'bus')
    if not os.path.exists(bus_dir):
        return evaluations

    for fname in os.listdir(bus_dir):
        if not fname.endswith('_evaluation.json'):
            continue
        fpath = os.path.join(bus_dir, fname)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if mtime < cutoff:
                continue
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            evaluations.append(data)
        except Exception:
            pass
    return evaluations


# ── 집계 ──────────────────────────────────────────────────────────

def aggregate_stats(logs: list[dict], evaluations: list[dict]) -> dict:
    """수집 데이터 집계."""
    total_tasks  = len(evaluations)
    total_logs   = len(logs)
    avg_score    = (sum(e.get('total_score', 0) for e in evaluations) / total_tasks
                    if total_tasks else 0)
    grades       = [e.get('grade', '?') for e in evaluations]
    grade_counts = {g: grades.count(g) for g in set(grades)}
    commit_ready = sum(1 for e in evaluations if e.get('commit_ready'))

    # 항목별 평균 점수
    score_keys = [
        'code_quality', 'agent_utilization', 'parallelization',
        'token_cost', 'retry_waste', 'comm_efficiency',
        'completion_rate', 'duration', 'issue_resolution', 'autonomy',
    ]
    item_avgs = {}
    for k in score_keys:
        vals = [e['scores'][k]['score']
                for e in evaluations
                if 'scores' in e and k in e['scores']]
        item_avgs[k] = round(sum(vals) / len(vals), 1) if vals else None

    # 반복 이슈 수집
    all_issues = []
    for e in evaluations:
        for k in score_keys:
            item = (e.get('scores') or {}).get(k, {})
            all_issues.extend(item.get('issues', []))

    issue_freq: dict[str, int] = {}
    for issue in all_issues:
        issue_freq[issue] = issue_freq.get(issue, 0) + 1
    top_issues = sorted(issue_freq.items(), key=lambda x: -x[1])[:5]

    return {
        'total_tasks':   total_tasks,
        'total_logs':    total_logs,
        'avg_score':     round(avg_score, 1),
        'grade_counts':  grade_counts,
        'commit_ready':  commit_ready,
        'item_avgs':     item_avgs,
        'top_issues':    top_issues,
    }


# ── SDK 호출 (Advisor Opus) ───────────────────────────────────────

def generate_retrospective_md(stats: dict, logs: list[dict],
                               evaluations: list[dict],
                               dry_run: bool = False) -> str:
    """Advisor SDK 호출로 회고 보고서 생성."""
    today = datetime.now().strftime('%Y-%m-%d')

    # 기본 통계 기반 마크다운 구성
    grade_str = ', '.join(f'{g}:{c}건' for g, c in
                          sorted(stats['grade_counts'].items()))
    item_rows = '\n'.join(
        f'| {k} | {v if v is not None else "-"}/10 |'
        for k, v in stats['item_avgs'].items()
    )
    issue_rows = '\n'.join(
        f'| {i+1} | {issue} | {cnt}건 |'
        for i, (issue, cnt) in enumerate(stats['top_issues'])
    ) if stats['top_issues'] else '| — | 반복 이슈 없음 | — |'

    md = f"""# 주간 회고 보고서

> **생성일**: {today}
> **대상 기간**: 지난 7일
> **에이전트 로그**: {stats['total_logs']}건 | **평가 완료 태스크**: {stats['total_tasks']}건

---

## 1. 성과 요약

| 항목 | 값 |
|---|---|
| 평균 평가 점수 | {stats['avg_score']}/100 |
| 등급 분포 | {grade_str if grade_str else '해당 없음'} |
| 커밋 준비 완료 | {stats['commit_ready']}/{stats['total_tasks']}건 |

---

## 2. 항목별 평균 점수

| 항목 | 평균 점수 |
|---|---|
{item_rows}

---

## 3. 반복 이슈 Top 5

| # | 이슈 | 발생 빈도 |
|---|---|---|
{issue_rows}

---

## 4. 개선 권고

"""
    # SDK 호출 가능 시 심층 분석 추가
    if not dry_run:
        try:
            import anthropic as _ant

            api_key = (os.environ.get('CLAUDE_API_KEY') or
                       os.environ.get('ANTHROPIC_API_KEY'))
            if api_key:
                client = _ant.Anthropic(api_key=api_key)
                prompt = (
                    f'다음 주간 에이전트 성과 데이터를 분석하여 한국어로 개선 권고안을 3-5줄로 작성하라.\n\n'
                    f'평균 점수: {stats["avg_score"]}/100\n'
                    f'항목별 평균: {json.dumps(stats["item_avgs"], ensure_ascii=False)}\n'
                    f'반복 이슈: {json.dumps(stats["top_issues"], ensure_ascii=False)}\n\n'
                    f'출력 형식: 마크다운 불릿 리스트 (- 항목)'
                )
                msg = client.messages.create(
                    model='claude-opus-4-6',
                    max_tokens=512,
                    temperature=0.2,
                    messages=[{'role': 'user', 'content': prompt}],
                )
                md += msg.content[0].text if msg.content else '(SDK 응답 없음)'
            else:
                md += '- API 키 없음 — 자동 분석 생략\n'
        except Exception as e:
            md += f'- SDK 분석 실패: {e}\n'
    else:
        md += '- (dry-run 모드 — SDK 분석 생략)\n'

    md += '\n---\n\n_자동 생성: retrospective.py_\n'
    return md


def _safe_print(text: str):
    """Windows cp949 터미널 호환 출력."""
    sys.stdout.buffer.write(text.encode('utf-8', errors='replace'))
    sys.stdout.buffer.flush()


# ── 메인 ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='주간 회고 보고서 생성')
    parser.add_argument('--dry-run', action='store_true',
                        help='수집·집계만, 저장·SDK 호출 없음')
    parser.add_argument('--days', type=int, default=7,
                        help='수집 기간 (일, 기본 7)')
    args = parser.parse_args()

    # .env 로드 (orchestrator.py와 동일 패턴)
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

    log = AgentLog(
        agent_id=f'Retrospective_{datetime.now().strftime("%Y-%m-%d")}',
        title='주간 회고',
        agent_type='orchestrator',
    )
    log.add(f'회고 시작 (days={args.days}, dry_run={args.dry_run})')

    # 1. 수집
    print(f'로그 수집 중 (지난 {args.days}일)...')
    logs        = collect_week_logs(days=args.days)
    evaluations = collect_evaluations(days=args.days)
    print(f'  에이전트 로그 {len(logs)}건, 평가 보고서 {len(evaluations)}건')

    # 2. 집계
    stats = aggregate_stats(logs, evaluations)
    print(f'  평균 점수: {stats["avg_score"]}/100')

    # 3. 보고서 생성
    print('보고서 생성 중...')
    md = generate_retrospective_md(stats, logs, evaluations, dry_run=args.dry_run)

    # 4. 저장
    today = datetime.now().strftime('%Y-%m-%d')
    out_path = os.path.join(PM_OUTPUTS, f'retrospective_{today}.md')

    if not args.dry_run:
        os.makedirs(PM_OUTPUTS, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(md)
        log.done(f'회고 보고서 저장: {out_path}')
        print(f'\n저장 완료: {out_path}')
    else:
        log.done('dry-run 완료 — 저장 생략')
        print('\n[dry-run] 저장 생략')

    print('\n' + '='*60)
    _safe_print(md + '\n')
    print('='*60)

    # 5. PKB Wiki 합성 (dry-run이 아닐 때만)
    if not args.dry_run:
        wiki_script = os.path.join(PROJECT_ROOT, '.scripts', 'pkb_wiki_synthesize.py')
        if os.path.exists(wiki_script):
            print('\nPKB 지식 합성 시작...')
            import subprocess
            # venv DLL 문제 회피: 글로벌 Python 우선 사용
            _global_py = r'C:\Users\psh93\AppData\Local\Programs\Python\Python313\python.exe'
            _py = _global_py if os.path.exists(_global_py) else sys.executable
            result = subprocess.run(
                [_py, wiki_script, '--all', '--min-entries', '2'],
                capture_output=True, text=True, encoding='utf-8',
            )
            if result.stdout:
                print(result.stdout)
            if result.returncode != 0 and result.stderr:
                print(f'  [합성 경고] {result.stderr[:300]}')


if __name__ == '__main__':
    main()
