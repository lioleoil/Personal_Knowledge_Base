"""
PKB LLM Wiki Synthesizer
각 WorkLog 카테고리의 대화 로그를 분석하여 "지금 아는 것" 합성 위키 페이지를 자동 생성한다.

사용법:
  python .scripts/pkb_wiki_synthesize.py --category AgentEcosystem
  python .scripts/pkb_wiki_synthesize.py --all
  python .scripts/pkb_wiki_synthesize.py --all --min-entries 3   # 항목 3개 이상인 카테고리만

산출물:
  projects/personal_knowledge_base/04_WorkLog/{Category}/SYNTHESIS.md
  (없으면 생성, 있으면 덮어쓰기)

요구사항:
  ANTHROPIC_API_KEY 환경변수 필요 (Sonnet 사용)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# .env 로드
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass

# Windows 터미널 UTF-8 출력
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE    = Path(__file__).parent.parent
WORKLOG = BASE / 'projects' / 'personal_knowledge_base' / '04_WorkLog'

SYNTHESIS_MODEL = 'claude-sonnet-4-6'

# 각 카테고리의 설명 (합성 프롬프트에 컨텍스트로 사용)
CATEGORY_CONTEXT = {
    'Gen2_Policy':          '자율주행 어노테이션 Gen2 Policy 수립, Sequence 기반 정책 조항, OD/RMD/3DP 규칙',
    'OpenLABEL':            'ASAM OpenLABEL 포맷, SV→OpenLABEL 마이그레이션 스크립트, 좌표계 변환',
    'AgentEcosystem':       'Multi-Agent 생태계 설계, Orchestrator/Bus/Validation 패턴, 토큰 추적',
    'Nova':                 'Nova 사내 서비스(대시보드/Lakehouse), nova_helper Slack 봇, 배포 운영',
    'ODD':                  '운행설계영역(ODD), OpenODD, 주차/주행 ODD 커버리지',
    'DQA':                  '데이터 품질 분석, 라벨 검증 자동화, Acceptance Criteria',
    'Gen1_Gen2_Labeling':   'OD/RMD/3DP 라벨링 통계, 클래스별 카운트, 성능 측정',
    'Career':               '커리어 전략, 이직, 이력서, Analytics Engineer/PO 포트폴리오',
    'Strategy_Business':    'KPI/OKR, 비즈니스 전략, Jira 에픽, 로드맵, 협상',
    'Python_Scripts':       'Python 자동화 스크립트, 파싱, 데이터 처리 패턴',
    'Misc':                 '기타 일회성 주제',
}


def load_entries(category_path: Path, max_entries: int = 30) -> list[dict]:
    """카테고리 마크다운에서 ### 섹션별 항목 파싱"""
    md_files = list(category_path.glob('*_대화_학습_정리.md'))
    if not md_files:
        return []

    entries = []
    for md in md_files:
        text = md.read_text(encoding='utf-8')
        sections = re.split(r'\n(?=### )', text)
        for sec in sections:
            sec = sec.strip()
            if not sec or not sec.startswith('###'):
                continue
            header_m = re.match(r'### (.+)', sec)
            header = header_m.group(1).strip() if header_m else '(제목 없음)'
            date_m = re.search(r'\*\*날짜:\*\* (\d{4}-\d{2}-\d{2})', sec)
            date = date_m.group(1) if date_m else ''
            entries.append({
                'header': header[:100],
                'date': date,
                'text': sec[:600],
            })

    # 최신순 정렬
    entries.sort(key=lambda x: x.get('date', ''), reverse=True)
    return entries[:max_entries]


def synthesize_category(category: str, entries: list[dict]) -> str:
    """Sonnet으로 카테고리 지식 합성. 반환: 마크다운 문자열"""
    try:
        import anthropic
    except ImportError:
        return _fallback_synthesis(category, entries)

    ctx = CATEGORY_CONTEXT.get(category, category)
    entries_text = '\n'.join(
        f'[{i+1}] ({e["date"]}) {e["header"]}\n{e["text"][:300]}'
        for i, e in enumerate(entries)
    )

    prompt = (
        f"당신은 개인 지식 관리 전문가입니다. "
        f"다음은 '{category}' 주제의 대화 로그 요약입니다.\n\n"
        f"주제 컨텍스트: {ctx}\n\n"
        f"대화 로그 ({len(entries)}개):\n{entries_text}\n\n"
        "이 로그들을 분석하여 아래 형식의 위키 합성 문서를 작성하세요:\n\n"
        "## 핵심 지식\n"
        "1. (가장 중요한 패턴/결론)\n"
        "2. ...\n"
        "3. ...\n\n"
        "## 반복 등장 패턴\n"
        "- (여러 대화에서 공통으로 나타난 주제나 문제)\n\n"
        "## 미해결 질문\n"
        "- (아직 명확한 답을 찾지 못한 것들)\n\n"
        "## 관련 카테고리\n"
        "- (연결되는 다른 카테고리)\n\n"
        "규칙:\n"
        "- 구체적이고 실용적으로 작성 (추상적 표현 금지)\n"
        "- 핵심 지식은 3-6개\n"
        "- 한국어로 작성"
    )

    try:
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=SYNTHESIS_MODEL,
            max_tokens=1200,
            messages=[{'role': 'user', 'content': prompt}]
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f'  [합성 오류] {e} → fallback')
        return _fallback_synthesis(category, entries)


def _fallback_synthesis(category: str, entries: list[dict]) -> str:
    """API 없을 때 기계적 요약"""
    lines = ['## 핵심 지식', '']
    for e in entries[:5]:
        lines.append(f'- ({e["date"]}) {e["header"]}')
    lines += ['', '## 반복 등장 패턴', '- (API 없음 — 수동 작성 필요)', '',
              '## 미해결 질문', '- (API 없음 — 수동 작성 필요)', '',
              '## 관련 카테고리', '- (API 없음 — 수동 작성 필요)']
    return '\n'.join(lines)


def write_synthesis(category_path: Path, category: str, body: str, entry_count: int):
    """SYNTHESIS.md 파일 생성/갱신"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    content = (
        f'# {category} 지식 합성\n\n'
        f'> 마지막 갱신: {now} | 기반 항목 수: {entry_count}\n\n'
        f'---\n\n'
        f'{body}\n'
    )
    out = category_path / 'SYNTHESIS.md'
    out.write_text(content, encoding='utf-8')
    print(f'  ✓ {out.relative_to(BASE)} ({entry_count}개 항목 기반)')
    return out


def run_all(min_entries: int = 1):
    """전체 카테고리 합성"""
    categories = [d for d in WORKLOG.iterdir() if d.is_dir()]
    if not categories:
        print('WorkLog 카테고리 디렉터리를 찾을 수 없습니다.')
        return

    print(f'전체 카테고리 합성 시작 ({len(categories)}개)...\n')
    success = 0
    for cat_path in sorted(categories):
        category = cat_path.name
        entries = load_entries(cat_path)
        if len(entries) < min_entries:
            print(f'  건너뜀: {category} ({len(entries)}개 항목 — 최소 {min_entries}개 필요)')
            continue
        print(f'처리: {category} ({len(entries)}개 항목)')
        body = synthesize_category(category, entries)
        write_synthesis(cat_path, category, body, len(entries))
        success += 1

    print(f'\n완료: {success}개 카테고리 합성됨')


def run_single(category: str):
    """단일 카테고리 합성"""
    cat_path = WORKLOG / category
    if not cat_path.exists():
        print(f'카테고리 디렉터리 없음: {cat_path}')
        sys.exit(1)

    entries = load_entries(cat_path)
    if not entries:
        print(f'처리할 항목이 없습니다: {category}')
        sys.exit(1)

    print(f'처리: {category} ({len(entries)}개 항목)')
    body = synthesize_category(category, entries)
    write_synthesis(cat_path, category, body, len(entries))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PKB LLM Wiki 합성')
    parser.add_argument('--category', help='단일 카테고리 이름')
    parser.add_argument('--all', action='store_true', help='전체 카테고리 합성')
    parser.add_argument('--min-entries', type=int, default=1,
                        help='최소 항목 수 (--all 사용 시, 기본: 1)')
    args = parser.parse_args()

    if not args.category and not args.all:
        parser.print_help()
        sys.exit(1)

    if args.all:
        run_all(min_entries=args.min_entries)
    else:
        run_single(args.category)
