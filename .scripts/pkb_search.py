"""
PKB RAG Searcher
PKB 벡터 인덱스에서 의미 기반 검색을 수행한다.

사용법:
  python .scripts/pkb_search.py --query "annotation policy occlusion"
  python .scripts/pkb_search.py --query "nova slack 재시작" --top 3
  python .scripts/pkb_search.py --query "..." --json   # JSON 출력 (Advisor Agent용)

전제: pkb_embed.py로 인덱스를 먼저 빌드해야 함
  python .scripts/pkb_embed.py --rebuild
"""

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE     = Path(__file__).parent.parent
PKB_IDX  = BASE / '.agents' / 'pkb_index'
META_FILE = PKB_IDX / 'embed_meta.json'
COLLECTION_NAME = 'pkb_worklog'


# ──────────────────────────────────────────────
# TF-IDF 검색 fallback
# ──────────────────────────────────────────────

def _tfidf_search(query: str, top_k: int) -> list[dict]:
    idx_file = PKB_IDX / 'tfidf_index.json'
    vec_file = PKB_IDX / 'tfidf_vectors.json'
    if not idx_file.exists():
        return []

    idx = json.loads(idx_file.read_text(encoding='utf-8'))
    vectors = json.loads(vec_file.read_text(encoding='utf-8'))
    chunks = idx['chunks']
    idf = idx['idf']

    def tokenize(text: str) -> list[str]:
        return re.findall(r'[가-힣a-zA-Z0-9_]+', text.lower())

    # 쿼리 벡터
    q_toks = tokenize(query)
    q_tf = {}
    for t in q_toks:
        q_tf[t] = q_tf.get(t, 0) + 1
    total_q = len(q_toks) or 1
    q_vec = {t: (c / total_q) * idf.get(t, 0) for t, c in q_tf.items()}

    def cosine(a: dict, b: dict) -> float:
        common = set(a) & set(b)
        if not common:
            return 0.0
        dot = sum(a[k] * b[k] for k in common)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        return dot / (norm_a * norm_b + 1e-9)

    scored = [(cosine(q_vec, vec), i) for i, vec in enumerate(vectors)]
    scored.sort(key=lambda x: -x[0])

    results = []
    for score, idx_i in scored[:top_k]:
        if score < 0.01:
            continue
        ch = chunks[idx_i]
        results.append({
            'score': round(score, 4),
            'category': ch['metadata']['category'],
            'header': ch['metadata']['header'],
            'date': ch['metadata']['date'],
            'file': ch['metadata']['file'],
            'text': ch['text'][:400],
        })
    return results


# ──────────────────────────────────────────────
# ChromaDB 검색
# ──────────────────────────────────────────────

def _chromadb_search(query: str, top_k: int, backend: str) -> list[dict]:
    import chromadb

    ef = None
    if backend == 'openai' and os.environ.get('OPENAI_API_KEY'):
        try:
            import chromadb.utils.embedding_functions as emb
            ef = emb.OpenAIEmbeddingFunction(
                api_key=os.environ['OPENAI_API_KEY'],
                model_name='text-embedding-3-small',
            )
        except Exception:
            pass

    client = chromadb.PersistentClient(path=str(PKB_IDX))
    kwargs = {'name': COLLECTION_NAME}
    if ef is not None:
        kwargs['embedding_function'] = ef
    collection = client.get_or_create_collection(**kwargs)

    res = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
        include=['documents', 'metadatas', 'distances'],
    )

    results = []
    docs = res['documents'][0]
    metas = res['metadatas'][0]
    dists = res['distances'][0]

    for doc, meta, dist in zip(docs, metas, dists):
        score = round(1.0 - dist, 4) if dist <= 1.0 else round(1.0 / (1.0 + dist), 4)
        results.append({
            'score': score,
            'category': meta.get('category', ''),
            'header': meta.get('header', ''),
            'date': meta.get('date', ''),
            'file': meta.get('file', ''),
            'text': doc[:400],
        })
    return results


# ──────────────────────────────────────────────
# 검색 진입점
# ──────────────────────────────────────────────

def search(query: str, top_k: int = 5) -> list[dict]:
    """PKB에서 query와 의미적으로 유사한 청크 top_k개 반환"""
    if not META_FILE.exists():
        print('인덱스가 없습니다. 먼저 실행하세요:')
        print('  python .scripts/pkb_embed.py --rebuild')
        return []

    meta = json.loads(META_FILE.read_text(encoding='utf-8'))
    backend = meta.get('backend', 'tfidf')

    if backend == 'tfidf':
        return _tfidf_search(query, top_k)

    try:
        return _chromadb_search(query, top_k, backend)
    except ImportError:
        print('  chromadb 미설치 → TF-IDF fallback')
        return _tfidf_search(query, top_k)
    except Exception as e:
        print(f'  ChromaDB 검색 오류: {e} → TF-IDF fallback')
        return _tfidf_search(query, top_k)


def format_results(results: list[dict], json_mode: bool = False) -> str:
    if json_mode:
        return json.dumps(results, ensure_ascii=False, indent=2)

    if not results:
        return '관련 결과를 찾지 못했습니다.'

    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f'[{i}] {r["category"]} / {r["header"]}')
        if r.get('date'):
            lines.append(f'    날짜: {r["date"]} | 파일: {r["file"]} | 유사도: {r["score"]:.3f}')
        else:
            lines.append(f'    파일: {r["file"]} | 유사도: {r["score"]:.3f}')
        preview = r['text'].replace('\n', ' ')[:200]
        lines.append(f'    {preview}')
        lines.append('')
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PKB 의미 검색')
    parser.add_argument('--query', '-q', required=True, help='검색 쿼리')
    parser.add_argument('--top', '-n', type=int, default=5, help='결과 수 (기본: 5)')
    parser.add_argument('--json', action='store_true', dest='json_mode', help='JSON 출력 (Agent용)')
    args = parser.parse_args()

    results = search(args.query, top_k=args.top)
    print(format_results(results, json_mode=args.json_mode))
