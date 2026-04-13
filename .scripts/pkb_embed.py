"""
PKB RAG Embedder
PKB WorkLog 마크다운을 섹션 단위로 청킹하여 벡터 인덱스를 생성한다.

사용법:
  python .scripts/pkb_embed.py --rebuild       # 전체 인덱스 재빌드
  python .scripts/pkb_embed.py --incremental   # 변경된 파일만 업데이트
  python .scripts/pkb_embed.py --status        # 인덱스 상태 조회

벡터 저장소:
  ChromaDB (로컬) → .agents/pkb_index/
  임베딩 백엔드 우선순위:
    1. OpenAI text-embedding-3-small (OPENAI_API_KEY 환경변수 필요)
    2. ChromaDB 기본 임베딩 (sentence-transformers, 로컬 모델)
    3. TF-IDF fallback (순수 stdlib, 낮은 정확도)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

BASE     = Path(__file__).parent.parent
WORKLOG  = BASE / 'projects' / 'personal_knowledge_base' / '04_WorkLog'
PKB_IDX  = BASE / '.agents' / 'pkb_index'
META_FILE = PKB_IDX / 'embed_meta.json'

COLLECTION_NAME = 'pkb_worklog'


# ──────────────────────────────────────────────
# 청킹
# ──────────────────────────────────────────────

def chunk_markdown(filepath: Path) -> list[dict]:
    """마크다운을 ### 헤더 기준으로 청킹. 각 청크는 dict."""
    text = filepath.read_text(encoding='utf-8')
    category = filepath.parent.name

    # ### 헤더로 분리
    sections = re.split(r'\n(?=### )', text)
    chunks = []
    for sec in sections:
        sec = sec.strip()
        if not sec or len(sec) < 30:
            continue
        # 헤더 추출
        header_m = re.match(r'### (.+)', sec)
        header = header_m.group(1).strip() if header_m else '(제목 없음)'

        # 날짜 추출 (있으면)
        date_m = re.search(r'\*\*날짜:\*\* (\d{4}-\d{2}-\d{2})', sec)
        date = date_m.group(1) if date_m else ''

        chunks.append({
            'id': f'{category}::{filepath.stem}::{header[:60]}',
            'text': sec[:1500],  # 임베딩용 최대 길이
            'metadata': {
                'category': category,
                'file': filepath.name,
                'header': header[:100],
                'date': date,
                'char_count': len(sec),
            }
        })
    return chunks


def load_all_chunks() -> list[dict]:
    """WorkLog 전체 마크다운 청킹"""
    chunks = []
    for md in WORKLOG.rglob('*_대화_학습_정리.md'):
        chunks.extend(chunk_markdown(md))
    # SYNTHESIS.md도 포함
    for md in WORKLOG.rglob('SYNTHESIS.md'):
        chunks.extend(chunk_markdown(md))
    return chunks


# ──────────────────────────────────────────────
# 임베딩 백엔드 선택
# ──────────────────────────────────────────────

def _get_openai_ef():
    """OpenAI text-embedding-3-small 임베딩 함수 (chromadb 호환)"""
    import chromadb.utils.embedding_functions as ef
    return ef.OpenAIEmbeddingFunction(
        api_key=os.environ['OPENAI_API_KEY'],
        model_name='text-embedding-3-small',
    )


def _get_default_ef():
    """ChromaDB 기본 임베딩 (sentence-transformers all-MiniLM-L6-v2)"""
    import chromadb.utils.embedding_functions as ef
    return ef.DefaultEmbeddingFunction()


def get_embedding_function():
    """사용 가능한 임베딩 함수 반환. 우선순위: OpenAI > ChromaDB default"""
    if os.environ.get('OPENAI_API_KEY'):
        try:
            ef = _get_openai_ef()
            print('  임베딩 백엔드: OpenAI text-embedding-3-small')
            return ef, 'openai'
        except Exception as e:
            print(f'  OpenAI 임베딩 초기화 실패: {e}')

    try:
        ef = _get_default_ef()
        print('  임베딩 백엔드: ChromaDB default (sentence-transformers)')
        return ef, 'chromadb_default'
    except Exception as e:
        print(f'  ChromaDB default 임베딩 실패: {e}')
        return None, 'tfidf'


# ──────────────────────────────────────────────
# TF-IDF fallback (chromadb 없을 때)
# ──────────────────────────────────────────────

def _tfidf_index(chunks: list[dict]) -> dict:
    """청크 리스트를 TF-IDF 인덱스로 변환 (순수 stdlib + json)"""
    import math
    from collections import Counter

    def tokenize(text: str) -> list[str]:
        return re.findall(r'[가-힣a-zA-Z0-9_]+', text.lower())

    # IDF 계산
    N = len(chunks)
    df: dict[str, int] = {}
    tokenized = []
    for ch in chunks:
        tokens = set(tokenize(ch['text']))
        tokenized.append(list(tokenize(ch['text'])))
        for t in tokens:
            df[t] = df.get(t, 0) + 1

    idf = {t: math.log(N / (d + 1)) for t, d in df.items()}

    # TF-IDF 벡터
    vectors = []
    for toks in tokenized:
        tf = Counter(toks)
        total = len(toks) or 1
        vec = {t: (c / total) * idf.get(t, 0) for t, c in tf.items()}
        vectors.append(vec)

    return {'chunks': chunks, 'vectors': vectors, 'idf': idf}


def _tfidf_save(index: dict, path: Path):
    path.mkdir(parents=True, exist_ok=True)
    (path / 'tfidf_index.json').write_text(
        json.dumps({'chunks': index['chunks'], 'idf': index['idf']}, ensure_ascii=False),
        encoding='utf-8'
    )
    # vectors는 별도 (리스트 of dict)
    (path / 'tfidf_vectors.json').write_text(
        json.dumps(index['vectors'], ensure_ascii=False),
        encoding='utf-8'
    )


def save_meta(backend: str, chunk_count: int):
    PKB_IDX.mkdir(parents=True, exist_ok=True)
    META_FILE.write_text(json.dumps({
        'backend': backend,
        'chunk_count': chunk_count,
        'updated': datetime.now().isoformat(),
    }, ensure_ascii=False, indent=2), encoding='utf-8')


# ──────────────────────────────────────────────
# 메인 빌드 로직
# ──────────────────────────────────────────────

def build_index(rebuild: bool = False):
    print('PKB 임베딩 인덱스 빌드 시작...')
    chunks = load_all_chunks()
    print(f'  청크 수: {len(chunks)}')

    if not chunks:
        print('  처리할 청크가 없습니다.')
        return

    try:
        import chromadb
    except ImportError:
        print('  chromadb 미설치 → TF-IDF fallback 사용')
        print('  (pip install chromadb 로 semantic 검색 활성화 가능)')
        idx = _tfidf_index(chunks)
        _tfidf_save(idx, PKB_IDX)
        save_meta('tfidf', len(chunks))
        print(f'  TF-IDF 인덱스 저장 완료: {PKB_IDX}')
        return

    ef, backend = get_embedding_function()

    PKB_IDX.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(PKB_IDX))

    if rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
            print('  기존 컬렉션 삭제 완료')
        except Exception:
            pass

    kwargs = {'name': COLLECTION_NAME}
    if ef is not None:
        kwargs['embedding_function'] = ef
    collection = client.get_or_create_collection(**kwargs)

    # 배치 upsert (최대 100개씩)
    batch_size = 100
    total = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        collection.upsert(
            ids=[c['id'] for c in batch],
            documents=[c['text'] for c in batch],
            metadatas=[c['metadata'] for c in batch],
        )
        total += len(batch)
        print(f'  upsert {total}/{len(chunks)}')

    save_meta(backend, len(chunks))
    print(f'\n인덱스 빌드 완료: {len(chunks)}개 청크 → {PKB_IDX}')
    print(f'백엔드: {backend}')


def show_status():
    if not META_FILE.exists():
        print('인덱스 없음. python .scripts/pkb_embed.py --rebuild 로 생성하세요.')
        return
    meta = json.loads(META_FILE.read_text(encoding='utf-8'))
    print('PKB 인덱스 상태:')
    print(f'  백엔드    : {meta["backend"]}')
    print(f'  청크 수   : {meta["chunk_count"]}')
    print(f'  마지막 갱신: {meta["updated"]}')
    print(f'  저장 위치  : {PKB_IDX}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PKB 임베딩 인덱스 관리')
    parser.add_argument('--rebuild', action='store_true', help='전체 재빌드')
    parser.add_argument('--incremental', action='store_true', help='증분 업데이트 (현재는 --rebuild와 동일)')
    parser.add_argument('--status', action='store_true', help='인덱스 상태 조회')
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        build_index(rebuild=args.rebuild or not META_FILE.exists())
