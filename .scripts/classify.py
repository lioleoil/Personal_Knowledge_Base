"""
Claude Code 대화 자동 분류 파이프라인
용도: ~/.claude/projects/<project>/*.jsonl 을 읽어 키워드 기반으로 카테고리 분류 후 WorkLog에 자동 append

사용법:
  python .scripts/classify.py                     # 현재 프로젝트 JSONL 전체
  python .scripts/classify.py --all               # 모든 Claude 프로젝트 JSONL
  python .scripts/classify.py --dry-run           # 분류 결과만 미리보기
  python .scripts/classify.py <file.jsonl>        # 단일 파일 지정

결과:
  - 04_WorkLog/<카테고리>/<카테고리>_대화_학습_정리.md 끝에 새 섹션 추가
  - 04_WorkLog/INDEX.md 자동 갱신 (update_index.py 호출)

─── 디렉토리 정책 ───────────────────────────────────────────────────
  04_WorkLog/          대화 로그 요약 + 정리 마크다운 파일만 보관
    <카테고리>/
      <카테고리>_대화_학습_정리.md   ← classify.py 출력 대상
      (기타 수동 정리 마크다운)

  .agents/             에이전트 실행 로그 전용 (AgentLog JSON)
    daily_scrap/       ← daily_scrap.py, daily_scrap_runner.py
    classify/          ← classify.py 에이전트 로그
    career_insight/    ← 커리어 인사이트 에이전트
    (기타 에이전트 유형)

  WorkLog에 .agents/ 폴더나 에이전트 JSON을 생성하지 않는다.
  에이전트 로그는 반드시 AgentLog(agent_type=...) 를 통해 .agents/ 에만 기록한다.
─────────────────────────────────────────────────────────────────────
"""

import json
import os
import re
import sys
import io
import subprocess
from datetime import datetime
from pathlib import Path

try:
    import anthropic as _anthropic
    _LLM_AVAILABLE = True
except ImportError:
    _LLM_AVAILABLE = False
    _anthropic = None

# Windows 터미널 UTF-8 출력 설정
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE            = Path(__file__).parent.parent
WORKLOG         = BASE / 'projects' / 'personal_knowledge_base' / '04_WorkLog'  # 대화 로그 + 마크다운 전용
AGENTS_ROOT     = BASE / '.agents' / 'classify'  # classify 에이전트 로그 위치
CLAUDE_PROJECTS = Path.home() / '.claude' / 'projects'
PROCESSED_FILES = AGENTS_ROOT / 'processed_files.json'

# 현재 프로젝트 ID (프로젝트 디렉토리명 → 슬래시 → 언더스코어 변환 기반)
CURRENT_PROJECT = 'C--Users-psh93-OneDrive-Desktop-Workspace'

# ─────────────────────────────────────────────
# 카테고리별 키워드 규칙 (우선순위 높은 순)
# ─────────────────────────────────────────────
CATEGORIES = [
    {
        'name': 'Gen2_Policy',
        'file': 'Gen2_Policy/Gen2_Policy_대화_학습_정리.md',
        'keywords': [
            'annotation policy', 'sequence annotation', 'gen2 policy', 'annotation rule',
            'heading angle', 'ground plane', 'occlusion rule', 'truncation',
            'temporal annotation', 'spatial validity', 'perception window',
            'class-specific', 'class-wise', 'attribute definition', 'vehicle attribute',
            'shall', 'acceptance criteria', 'spatial consistency',
            'barrier solid', 'barrier rail', 'barrier fence', 'barrier temporary',
            'obstacle cone', 'obstacle cylinder', 'bollard', 'mv_od_3d', '3d_boundbox',
            'policy version', 'policy table', 'policy 테이블', '정책 문서',
            'illumination_insufficient', 'cuboid 3d annotation', 'sequence od annotation',
            'policy-as-code', 'git 문서', '정책 실효성', 'policy validation',
            'annotation schema', 'semantic variant', 'dynamicodtarget', 'staticodtarget',
            '상반기 policy', 'policy kpi', 'acceptance criteria 정의',
        ],
    },
    {
        'name': 'OpenLABEL',
        'file': 'OpenLABEL/OpenLABEL_대화_학습_정리.md',
        'keywords': [
            'openlabel', 'asam', 'sv_to_openlabel', 'sv-to-openlabel',
            'cuboid', 'stream_properties', 'migration script', '변환 스크립트',
            'opendrive', 'openscenario', 'openodd', 'xodr',
            'annotation transformation', 'vcs 좌표계', 'quaternion',
        ],
    },
    {
        'name': 'AgentEcosystem',
        'file': 'AgentEcosystem/AgentEcosystem_대화_학습_정리.md',
        'keywords': [
            # 에이전트 생태계 인프라
            'agent ecosystem', '에이전트 생태계', 'multi-agent', '멀티에이전트',
            'orchestrator', 'agent bus', 'agentbus', 'agent_bus',
            'execution agent', 'validation agent', 'advisor agent', 'reporter agent',
            'role_rules', 'task_manifest', 'agent onboarding',
            'daily_scrap', 'geek news', 'remote trigger', '원격 에이전트',
            'remote_track', 'agent_log', 'agent log',
            # 토큰 추적 시스템
            'show_tokens', 'token_popup', 'token tracking', '토큰 추적',
            'token_usage', 'hourly_bucket', '4h 롤링', '4h rolling',
            'monitor.py', 'auto_track', 'remote_track',
            # Git/브랜치 관리 (워크스페이스 관리)
            'feat/ecosystem', 'branch cleanup', '브랜치 정리', 'worktree',
            'pr merge', 'pull request', '04_agentecosystem',
        ],
    },
    {
        'name': 'Nova',
        'file': 'Nova/Nova_대화_학습_정리.md',
        'keywords': [
            'power bi', 'powerbi', 'nova', 'dax', 'mysql connector',
            'wls', 'workload labeling', 'labelit api', 'lakehouse',
            'databricks', 'nova dashboard', 'nova beta', 'data yield',
            'mysql provider', 'gateway', 'dbt', 'staging',
            # nova_helper / nova_log_analytics (Nova 서비스 영역)
            'nova_helper', 'nova_log_analytics', 'nova helper', 'nova log',
            'slack bot', 'slack 봇', 'socket mode', 'http mode',
            'signing secret', 'escalation', 'nova_okr', 'nova_jira',
            'bolt', 'slack_bolt', 'flask handler', 'nova port',
        ],
    },
    {
        'name': 'ODD',
        'file': 'ODD/ODD_대화_학습_정리.md',
        'keywords': [
            'odd', 'operational design domain', 'openodd', 'parking odd',
            'driving odd', '운행설계영역', 'odd coverage',
        ],
    },
    {
        'name': 'DQA',
        'file': 'DQA/DQA_대화_학습_정리.md',
        'keywords': [
            '검수', 'qa', 'quality', 'validation', 'label review',
            '리뷰 자동화', '품질 분석', '자동화 검수', 'dqa', 'data quality',
            '라벨 검증', 'acceptance',
        ],
    },
    {
        'name': 'Gen1_Gen2_Labeling',
        'file': 'Gen1_Gen2_Labeling/Gen1_Gen2_Labeling_대화_학습_정리.md',
        'keywords': [
            'od class', 'sod', 'tstld', 'bbox2d', 'bbox3d', 'bbox3d_valid',
            '2d box', '3d box', 'bounding box count', 'object count',
            'json 객체', 'gen1', 'gen2', 'classwise', '클래스 카운트',
            'svc_front', 'svc_rear', 'labeling statistics',
        ],
    },
    {
        'name': 'Career',
        'file': 'Career/Career_대화_학습_정리.md',
        'keywords': [
            '이직', '커리어', '연봉', 'resume', 'portfolio', 'cbo',
            '경력기술서', '이력서', 'analytics engineer', '취업',
            'job', 'career', 'salary', '크래프톤', '빗썸', '펄어비스',
        ],
    },
    {
        'name': 'Strategy_Business',
        'file': 'Strategy_Business/Strategy_Business_대화_학습_정리.md',
        'keywords': [
            'kpi', 'okr', '협상', '단가', 'strategy', '전략',
            'roadmap', '로드맵', 'business', '비즈니스', '번역',
            'jira', 'epic', 'sprint', 'p&l', '손익', '계약',
            '성과 평가', '보고서', 'stakeholder',
        ],
    },
    {
        'name': 'Python_Scripts',
        'file': 'Python_Scripts/Python_Scripts_대화_학습_정리.md',
        'keywords': [
            'python', 'script', 'import os', 'import json', 'pandas',
            'def ', 'traceback', 'syntaxerror', 'keyerror', 'indexerror',
            'csv', 'xml', 'shutil', 'tqdm', 'subprocess', 'encoding',
            '자동화', '파싱', 'loop', 'function',
        ],
    },
    {
        'name': 'Misc',
        'file': 'Misc/Misc_대화_학습_정리.md',
        'keywords': [],  # 기본값: 위 카테고리에 해당 없으면 Misc
    },
]


def _llm_classify(title: str, content: str) -> tuple[str | None, list, float]:
    """Haiku API로 LLM 기반 분류. 반환: (카테고리명 or None, 태그 리스트, 신뢰도)"""
    cat_names = [c['name'] for c in CATEGORIES]
    text_sample = (title + '\n' + content)[:800]

    prompt = (
        f"다음 대화를 분석하여 가장 적합한 카테고리를 선택하세요.\n\n"
        f"카테고리 목록: {', '.join(cat_names)}\n\n"
        f"대화 제목: {title}\n"
        f"대화 내용(일부): {text_sample}\n\n"
        "JSON 형식으로만 답하세요:\n"
        '{\"category\": \"<카테고리명>\", \"tags\": [\"<태그1>\", \"<태그2>\"], \"confidence\": <0.0-1.0>}\n\n'
        "규칙:\n"
        "- category는 위 목록 중 하나 (정확히 일치)\n"
        "- tags는 대화의 핵심 주제 키워드 2-5개\n"
        "- confidence는 분류 확신도\n"
        "- 불확실하면 Misc 선택"
    )

    try:
        client = _anthropic.Anthropic()
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=200,
            messages=[{'role': 'user', 'content': prompt}]
        )
        raw = msg.content[0].text.strip()
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            cat = data.get('category', 'Misc')
            if cat not in [c['name'] for c in CATEGORIES]:
                cat = 'Misc'
            tags = [str(t) for t in data.get('tags', [])][:5]
            conf = float(data.get('confidence', 0.5))
            return cat, tags, conf
    except Exception as e:
        print(f'  [LLM 분류 오류] {e} → 키워드 방식 fallback')
    return None, [], 0.0


def _keyword_classify(title: str, content: str) -> tuple[str, int]:
    """기존 키워드 카운팅 방식 분류. 반환: (카테고리명, 최고점수)"""
    text = (title + ' ' + content).lower()
    scores: dict[str, int] = {}
    matched_keywords: dict[str, list[str]] = {}

    for cat in CATEGORIES[:-1]:
        hits = [(kw, text.count(kw.lower())) for kw in cat['keywords'] if text.count(kw.lower()) > 0]
        score = sum(cnt for _, cnt in hits)
        if score > 0:
            scores[cat['name']] = score
            matched_keywords[cat['name']] = [f'{kw}({cnt})' for kw, cnt in sorted(hits, key=lambda x: -x[1])[:5]]

    if not scores:
        return 'Misc', 0

    sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
    best, best_score = sorted_scores[0]
    if len(sorted_scores) >= 2:
        second_score = sorted_scores[1][1]
        if best_score - second_score <= 10:
            print(f'  [분류 주의] 점수 근소차: {sorted_scores[0][0]}({best_score}) vs {sorted_scores[1][0]}({second_score}) — 수동 검토 권장')
    top_kws = ', '.join(matched_keywords.get(best, []))
    print(f'  [분류 점수] {best}: {best_score}점 | 주요 키워드: {top_kws}')
    return best, best_score


def classify_conversation(title: str, content: str) -> tuple[str, int, list]:
    """카테고리 결정. LLM 우선, 실패 시 키워드 방식 fallback.
    반환: (카테고리명, 점수/신뢰도*100, 태그 리스트)"""
    if _LLM_AVAILABLE:
        cat, tags, conf = _llm_classify(title, content)
        if cat is not None:
            score = int(conf * 100)
            tags_str = ' '.join(f'#{t}' for t in tags) if tags else '없음'
            print(f'  [LLM 분류] {cat}: 신뢰도 {conf:.0%} | 태그: {tags_str}')
            return cat, score, tags

    cat, score = _keyword_classify(title, content)
    return cat, score, []


def generate_summary(conv: dict) -> dict:
    """Haiku로 구조화된 대화 요약 생성. 반환: {learned, action, keywords}"""
    if not _LLM_AVAILABLE:
        snippet = conv['content'][:200].replace('\n', ' ').strip()
        if len(conv['content']) > 200:
            snippet += '...'
        return {'learned': snippet, 'action': '', 'keywords': []}

    text_sample = (conv['title'] + '\n' + conv['content'])[:1200]
    prompt = (
        f"다음 Claude Code 대화를 분석하여 핵심을 추출하세요.\n\n"
        f"대화 제목: {conv['title']}\n"
        f"대화 내용(일부): {text_sample}\n\n"
        "JSON 형식으로만 답하세요:\n"
        "{\n"
        "  \"learned\": \"<1-2문장: 이 대화에서 배운 것 또는 해결한 것>\",\n"
        "  \"action\": \"<결정/후속 액션, 없으면 빈 문자열>\",\n"
        "  \"keywords\": [\"<핵심 기술 키워드 최대 5개>\"]\n"
        "}\n\n"
        "핵심만 간결하게. 한국어로."
    )

    try:
        client = _anthropic.Anthropic()
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=350,
            messages=[{'role': 'user', 'content': prompt}]
        )
        raw = msg.content[0].text.strip()
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            return {
                'learned': str(data.get('learned', ''))[:300],
                'action': str(data.get('action', ''))[:200],
                'keywords': [str(k) for k in data.get('keywords', [])][:5],
            }
    except Exception as e:
        print(f'  [요약 생성 오류] {e} → 스니펫 방식 fallback')

    snippet = conv['content'][:200].replace('\n', ' ').strip()
    if len(conv['content']) > 200:
        snippet += '...'
    return {'learned': snippet, 'action': '', 'keywords': []}


def save_keyword_to_category(category_name: str, keyword: str):
    """classify.py의 CATEGORIES 리스트에 키워드를 영구 추가"""
    script_path = Path(__file__)
    content = script_path.read_text(encoding='utf-8')

    # 해당 카테고리 블록 찾아서 keywords 리스트에 추가
    # 'name': 'CategoryName' 다음에 오는 'keywords': [ ... ] 에 추가
    pattern = rf"(\"'name'\": '{re.escape(category_name)}'.*?'keywords': \[)(.*?)(\])"

    # 더 단순한 방법: 카테고리 name 줄 찾고 그 다음 keywords 블록 끝에 삽입
    lines = content.split('\n')
    in_category = False
    keywords_end = -1

    for i, line in enumerate(lines):
        if f"'name': '{category_name}'" in line:
            in_category = True
        if in_category and "'keywords': [" in line:
            # keywords 블록 끝 찾기
            for j in range(i, len(lines)):
                if lines[j].strip() == '],' or lines[j].strip() == '],':
                    keywords_end = j
                    break
                elif lines[j].strip().endswith('],'):
                    keywords_end = j
                    break
            break

    if keywords_end == -1:
        print(f'  ⚠ 키워드 추가 실패: {category_name} 카테고리를 찾지 못했습니다.')
        return

    # 마지막 키워드 줄 들여쓰기 파악
    indent = '            '  # 기본 12칸
    insert_line = f"{indent}'{keyword}',"
    lines.insert(keywords_end, insert_line)

    script_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f'  ✓ 키워드 "{keyword}" → {category_name} 에 추가됨')


def popup_review(conv: dict, auto_category: str) -> str:
    """오분류/미분류 대화를 팝업으로 보여주고 사용자가 카테고리 선택 + 키워드 추가"""
    import tkinter as tk
    from tkinter import ttk

    result = [auto_category]  # mutable container

    root = tk.Tk()
    root.title('대화 분류 검토')
    root.configure(bg='#1E1E2E')
    root.resizable(False, False)

    # 헤더
    hdr = tk.Frame(root, bg='#12121E', padx=16, pady=10)
    hdr.pack(fill='x')
    tk.Label(hdr, text='분류 불확실 — 검토 필요',
             font=('', 13, 'bold'), bg='#12121E', fg='#F1C40F').pack(side='left')
    tk.Label(hdr, text=f'자동 분류: {auto_category}',
             font=('', 10), bg='#12121E', fg='#E74C3C').pack(side='right')

    # 대화 정보
    body = tk.Frame(root, bg='#2A2A3E', padx=16, pady=12)
    body.pack(fill='both', padx=12, pady=8)

    tk.Label(body, text=conv['title'], font=('', 12, 'bold'),
             bg='#2A2A3E', fg='#FFFFFF', wraplength=480, anchor='w').pack(fill='x')
    tk.Label(body, text=f"{conv['date']}  |  {conv['source_file']}  |  메시지 {conv['msg_count']}개",
             font=('Consolas', 9), bg='#2A2A3E', fg='#666688').pack(anchor='w', pady=(2, 8))

    snippet = conv['content'][:400].replace('\n', ' ').strip()
    if len(conv['content']) > 400:
        snippet += '...'
    tk.Label(body, text=snippet, font=('', 9), bg='#1A1A2E', fg='#AAAACC',
             wraplength=480, justify='left', padx=8, pady=6).pack(fill='x')

    # 카테고리 선택
    ctrl = tk.Frame(root, bg='#1E1E2E', padx=16, pady=8)
    ctrl.pack(fill='x')

    tk.Label(ctrl, text='카테고리 선택:', font=('', 10),
             bg='#1E1E2E', fg='#CCCCDD').pack(side='left')

    cat_names = [c['name'] for c in CATEGORIES]
    sel = tk.StringVar(value=auto_category)
    combo = ttk.Combobox(ctrl, textvariable=sel, values=cat_names,
                         state='readonly', width=25, font=('', 10))
    combo.pack(side='left', padx=8)

    # 키워드 추가 영역
    kw_frame = tk.Frame(root, bg='#1E1E2E', padx=16, pady=4)
    kw_frame.pack(fill='x')

    tk.Label(kw_frame, text='키워드 추가:', font=('', 9),
             bg='#1E1E2E', fg='#888899').pack(side='left')
    kw_var = tk.StringVar()
    kw_entry = tk.Entry(kw_frame, textvariable=kw_var, width=22,
                        font=('Consolas', 9), bg='#2A2A3E', fg='#CCCCFF',
                        insertbackground='white', relief='flat')
    kw_entry.pack(side='left', padx=6)

    def add_keyword():
        kw = kw_var.get().strip().lower()
        cat = sel.get()
        if kw and cat:
            save_keyword_to_category(cat, kw)
            kw_var.set('')
            status_lbl.config(text=f'✓ "{kw}" → {cat}', fg='#27AE60')
        else:
            status_lbl.config(text='키워드와 카테고리를 입력하세요', fg='#E74C3C')

    tk.Button(kw_frame, text='규칙에 추가', command=add_keyword,
              bg='#2E4A7A', fg='#AACCFF', font=('', 9),
              relief='flat', padx=8, pady=3).pack(side='left')

    status_lbl = tk.Label(kw_frame, text='', font=('', 8),
                          bg='#1E1E2E', fg='#888899')
    status_lbl.pack(side='left', padx=8)

    # 버튼
    btn_frame = tk.Frame(root, bg='#1E1E2E', padx=16, pady=10)
    btn_frame.pack(fill='x')

    def confirm():
        result[0] = sel.get()
        root.destroy()

    def skip():
        result[0] = 'Misc'
        root.destroy()

    tk.Button(btn_frame, text='확인 (이 카테고리로 저장)', command=confirm,
              bg='#27AE60', fg='white', font=('', 10, 'bold'),
              relief='flat', padx=12, pady=6).pack(side='left')
    tk.Button(btn_frame, text='기타로 저장', command=skip,
              bg='#555577', fg='#CCCCCC', font=('', 9),
              relief='flat', padx=8, pady=6).pack(side='left', padx=8)

    # 창 중앙 배치
    root.update_idletasks()
    w, h = 540, 430
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')
    root.lift()
    root.attributes('-topmost', True)
    root.mainloop()

    return result[0]


def extract_text_from_content(content) -> str:
    """message.content에서 텍스트 추출 (str / list 모두 처리)"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                parts.append(item.get('text', ''))
        return ' '.join(parts)
    return ''


def extract_conversations_jsonl(jsonl_path: Path) -> list[dict]:
    """Claude Code .jsonl 파일에서 대화 추출 (1 파일 = 1 세션)"""
    messages = []
    first_timestamp = None

    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get('type')
            if msg_type not in ('user', 'assistant'):
                continue

            ts = obj.get('timestamp', '')
            if ts and first_timestamp is None:
                first_timestamp = ts

            msg = obj.get('message', {})
            role = msg.get('role', msg_type)
            content = extract_text_from_content(msg.get('content', ''))
            if content.strip():
                messages.append({'role': role, 'content': content})

    if not messages:
        return []

    # 제목: 첫 번째 user 메시지 (앞 80자)
    title = '제목 없음'
    for m in messages:
        if m['role'] == 'user':
            raw = m['content'].strip()
            # <command-name>, <command-message> 태그 제거
            raw = re.sub(r'<[^>]+>', '', raw).strip()
            if raw:
                title = raw[:80].replace('\n', ' ')
                break

    # 날짜
    if first_timestamp:
        try:
            date = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00')).strftime('%Y-%m-%d')
        except Exception:
            date = '날짜 불명'
    else:
        date = '날짜 불명'

    full_content = ' '.join(m['content'] for m in messages)

    return [{
        'title': title,
        'date': date,
        'content': full_content,
        'source_file': jsonl_path.name,
        'msg_count': len(messages),
    }]


def find_jsonl_files(project_id: str = CURRENT_PROJECT, all_projects: bool = False) -> list[Path]:
    """Claude Code 프로젝트 디렉토리에서 .jsonl 파일 목록 반환"""
    if all_projects:
        return sorted(CLAUDE_PROJECTS.glob('*/*.jsonl'))
    project_dir = CLAUDE_PROJECTS / project_id
    if project_dir.exists():
        return sorted(project_dir.glob('*.jsonl'))
    # fallback: 현재 디렉토리 기준 유사 경로
    return sorted(CLAUDE_PROJECTS.glob(f'{project_id}/*.jsonl'))


def append_to_worklog(conv: dict, category: str):
    """분류된 대화를 해당 카테고리 마크다운 파일에 append.
    정책: WorkLog에는 *_대화_학습_정리.md 와 수동 정리 마크다운만 기록.
          에이전트 로그(JSON)는 .agents/ 에만 기록하며 이 함수에서 생성하지 않는다.
    """
    cat_info = next((c for c in CATEGORIES if c['name'] == category), CATEGORIES[-1])
    target = WORKLOG / cat_info['file']

    if not target.exists():
        print(f'  ⚠ 대상 파일 없음: {target}')
        return

    title = conv['title']
    date = conv['date']
    source = conv['source_file']
    msg_count = conv['msg_count']

    summary = generate_summary(conv)

    tags = conv.get('tags', [])
    tags_part = (' | **태그:** ' + ' '.join(f'#{t}' for t in tags)) if tags else ''

    section = f'\n### {title}\n'
    section += f'**날짜:** {date} | **파일:** {source} | **메시지:** {msg_count}개{tags_part}\n\n'
    section += f'**배운 것:** {summary["learned"]}\n'
    if summary.get('action'):
        section += f'**결정/액션:** {summary["action"]}\n'
    if summary.get('keywords'):
        section += f'**핵심 키워드:** {", ".join(summary["keywords"])}\n'
    section += '\n---\n'

    with open(target, 'a', encoding='utf-8') as f:
        f.write(section)

    print(f'  ✓ [{category}] {title[:40]} → {cat_info["file"]}')


POPUP_THRESHOLD = 50  # LLM 신뢰도*100 또는 키워드 점수가 이 값 이하이면 팝업 표시


def _load_processed_files() -> set:
    """처리 완료된 JSONL 파일명 목록 로드"""
    if PROCESSED_FILES.exists():
        try:
            data = json.loads(PROCESSED_FILES.read_text(encoding='utf-8'))
            return set(data.get('processed', []))
        except Exception:
            pass
    return set()


def _save_processed_files(processed: set):
    """처리 완료된 JSONL 파일명 목록 저장"""
    PROCESSED_FILES.parent.mkdir(parents=True, exist_ok=True)
    data = {'processed': sorted(processed), 'updated': datetime.now().isoformat()}
    PROCESSED_FILES.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def run(jsonl_files: list[Path], dry_run: bool = False, interactive: bool = True):
    results = {}
    processed_ids = _load_processed_files()
    newly_processed: set = set()

    for jf in jsonl_files:
        if not dry_run and jf.name in processed_ids:
            print(f'\n  (이미 처리됨, 건너뜀): {jf.name}')
            continue

        print(f'\n파일 처리: {jf.name}')
        try:
            conversations = extract_conversations_jsonl(jf)
        except Exception as e:
            print(f'  ✗ 파싱 실패: {e}')
            continue

        if not conversations:
            print('  (메시지 없음, 건너뜀)')
            continue

        for conv in conversations:
            category, score, tags = classify_conversation(conv['title'], conv['content'])
            conv['tags'] = tags  # 태그를 conv에 저장 (append_to_worklog에서 사용)

            needs_review = (category == 'Misc' or score <= POPUP_THRESHOLD)
            if needs_review and interactive and not dry_run:
                print(f'  [팝업] 검토 필요: {conv["title"][:50]}  (점수={score}, 자동={category})')
                category = popup_review(conv, category)

            results.setdefault(category, []).append(conv)

            if dry_run:
                marker = ' ⚠ 검토필요' if needs_review else ''
                tags_str = ' '.join(f'#{t}' for t in tags) if tags else ''
                print(f'  [{category:20s}] {conv["date"]}  {conv["title"][:50]}{marker}  {tags_str}')
            else:
                append_to_worklog(conv, category)

        if not dry_run:
            newly_processed.add(jf.name)

    print('\n─────────────────────────────')
    print('분류 결과 요약:')
    for cat, convs in sorted(results.items(), key=lambda x: -len(x[1])):
        print(f'  {cat:25s}: {len(convs):3d}개')
    print(f'  {"합계":25s}: {sum(len(v) for v in results.values()):3d}개')

    if not dry_run:
        if newly_processed:
            _save_processed_files(processed_ids | newly_processed)
            print(f'\n✓ 처리 기록 저장: {len(newly_processed)}개 파일')
        update_index = BASE / 'projects' / 'personal_knowledge_base' / '04_WorkLog' / 'update_index.py'
        if update_index.exists():
            subprocess.run([sys.executable, str(update_index)], check=False)
            print('✓ INDEX.md 갱신 완료')


if __name__ == '__main__':
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    no_popup = '--no-popup' in args
    all_projects = '--all' in args
    args = [a for a in args if a not in ('--dry-run', '--no-popup', '--all')]

    if args:
        # 직접 지정한 파일
        jsonl_files = [Path(a) for a in args if Path(a).exists()]
        if not jsonl_files:
            print('지정한 파일을 찾을 수 없습니다.')
            sys.exit(1)
    else:
        jsonl_files = find_jsonl_files(all_projects=all_projects)
        if not jsonl_files:
            print(f'처리할 .jsonl 파일을 찾을 수 없습니다.')
            print(f'  탐색 경로: {CLAUDE_PROJECTS / CURRENT_PROJECT}')
            sys.exit(1)

    interactive = not no_popup and not dry_run
    run(jsonl_files, dry_run=dry_run, interactive=interactive)
