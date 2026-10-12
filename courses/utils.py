"""Chunking and hybrid search (Guide v2 sections 4.4, 4.5).

Owner: Wahib. REFERENCE STAND-IN written with the CMP 305 module so it can run end to end.

Search = BM25 (rank_bm25) + a dense embedding, combined into one absolute score in [0, 1]:
    score = W_LEX * bm25_norm + (1 - W_LEX) * dense_cos
bm25_norm is the BM25 score divided by the sum of the query terms' IDF, so a chunk of average length that
contains every query term once scores 1.0 and the score means the same thing for every query (a raw BM25
score is unbounded and cannot carry a fixed MIN_SCORE).
The dense part uses all-MiniLM-L6-v2 when its weights are available; otherwise it falls back to LSA
(TF-IDF + truncated SVD fitted on the indexed chunks). The index records which embedder built it, and
search uses the same one. An index built with MiniLM is never searched with LSA: MIN_SCORE was calibrated
on MiniLM scores, so loading such an index without MiniLM raises EmbedderUnavailable. Setting
FACTCHECK_ALLOW_LSA=1 allows the fallback anyway (with a warning) for running tests on a machine
without the model; results then do not match the eval report.
Loaded indexes are cached in memory (one load per process, not per claim).
"""
import json
import math
import os
import re
from functools import lru_cache

import numpy as np

from .normalize import normalize

W_LEX = 0.5
DATA_DIR = os.environ.get('FACTCHECK_DATA', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data'))
MONO_FONT = re.compile(r'mono|courier|lettergothic|consol|menlo|typewriter', re.I)

STOP = set("""a an the and or of to in on at by for with from as is are was were be been being it its this that
these those there their they them then than so such not no but if into onto over under we you your our can
could may might will would shall should do does did done has have had having which who whom whose what when
where why how all any each every some more most other also only very just about after before between both
same one two three use used using uses like e.g i.e etc vs via per thus hence therefore since because while
here s t""".split())


try:
    from nltk.stem.snowball import SnowballStemmer
    _snow = SnowballStemmer('english').stem
except Exception:                                   # nltk missing: tiny fallback
    _snow = None


@lru_cache(maxsize=200_000)
def stem(w: str) -> str:
    """Snowball stem (sorts/sorting/sorted -> sort, trees -> tree, probing/probe -> probe)."""
    if _snow is not None:
        return _snow(w)
    if w.endswith('ies') and len(w) > 4:
        return w[:-3] + 'y'
    if w.endswith(('ss', 'us', 'is')):
        return w
    for suf in ('ing', 'ed', 's'):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)]
    return w


def tokens(text: str) -> list[str]:
    """Lowercase word tokens without stopwords, stemmed. Identifiers like push_back stay whole."""
    out = []
    for w in re.findall(r"[A-Za-z_][A-Za-z0-9_+]*|\d+|[ΘΩΣ∫≤≥]", text.lower()):
        if w in STOP or (len(w) == 1 and w.isalpha()):
            continue
        out.append(stem(w))
    return out


# ----------------------------------------------------------------------------- chunking
def _bucket(sp):
    return round(sp['bbox'][3] / 3)           # baseline bucket (3 pt)


def _is_mono(sp):
    return bool(MONO_FONT.search(sp['font']) or sp['flags'] & 8)


def page_blocks(page, glyph_map=None):
    """Split one PyMuPDF page into ('code', text) and ('prose', text) blocks, in reading order.
    Spans are grouped into visual rows by baseline; a row whose characters are mostly monospace is code.
    Consecutive code rows form one code block that keeps its line breaks and indentation (from the x
    position); listing line numbers are dropped. Prose keeps PyMuPDF's reading order (better for math)."""
    d = page.get_text('dict')
    lines = [ln for b in d['blocks'] for ln in b.get('lines', []) if any(sp['text'].strip() for sp in ln['spans'])]
    rows = {}
    for ln in lines:
        for sp in ln['spans']:
            if sp['text'].strip():
                rows.setdefault(_bucket(sp), []).append(sp)
    is_digits = lambda t: re.fullmatch(r'\d{1,3}', t.strip()) is not None
    code_rows = {}
    for y in sorted(rows):
        r = sorted(rows[y], key=lambda sp: sp['bbox'][0])
        if len(r) > 1 and is_digits(r[0]['text']) and not _is_mono(r[0]):
            r = r[1:]                          # leading listing line number
        mono = [sp for sp in r if _is_mono(sp)]
        n_mono = sum(len(sp['text'].strip()) for sp in mono)
        n_all = sum(len(sp['text'].strip()) for sp in r)
        if mono and n_mono > 0.6 * n_all:
            code_rows[y] = mono
    # code regions: runs of code rows, allowing digit-only rows (numbers of blank listing lines) between
    ys = sorted(rows)
    region_of, regions, cur = {}, [], None
    for y in ys:
        if y in code_rows:
            if cur is None:
                cur = []
                regions.append(cur)
            cur.append(y)
            region_of[y] = len(regions) - 1
        elif all(is_digits(sp['text']) for sp in rows[y]) and cur is not None:
            region_of[y] = len(regions) - 1      # blank listing line: belongs to the region, no text
        else:
            cur = None

    def region_text(reg):
        x0 = min(code_rows[y][0]['bbox'][0] for y in reg)
        out = []
        for y in reg:
            r = sorted(code_rows[y], key=lambda sp: sp['bbox'][0])
            size = r[0]['size']
            text, last = '', None
            for sp in r:
                if last is not None:
                    text += ' ' * max(1 if sp['bbox'][0] - last > size * 0.15 else 0, int((sp['bbox'][0] - last) / (size * 0.6)))
                text += sp['text'].strip() if last is None else sp['text']
                last = sp['bbox'][2]
            out.append(' ' * max(0, int(round((r[0]['bbox'][0] - x0) / max(size * 0.6, 1)))) + text.rstrip())
        return '\n'.join(out)

    out, prose, emitted = [], [], set()
    for ln in lines:
        sps = [sp for sp in ln['spans'] if sp['text'].strip()]
        y = _bucket(sps[0])
        if y in region_of:
            reg = region_of[y]
            if reg not in emitted and y in code_rows:
                if prose:
                    out.append(('prose', '\n'.join(prose)))
                    prose = []
                out.append(('code', region_text(regions[reg])))
                emitted.add(reg)
            if y in code_rows or all(is_digits(sp['text']) for sp in sps):
                continue
        # superscript spans (PyMuPDF flag bit 0, smaller than the line's text) get one caret per run,
        # so N² extracts as N^2 and 2^(N+1) as 2^N+1 instead of N2 / 2N+1
        big = max(sp['size'] for sp in sps)
        txt, prev_sup = '', False
        for sp in ln['spans']:
            sup = bool(sp['flags'] & 1) and sp['size'] < 0.9 * big and sp['text'].strip() != ''
            txt += ('^' if sup and not prev_sup and not sp['text'].startswith(' ') else '') + sp['text']
            prev_sup = sup
        prose.append(txt)
    if prose:
        out.append(('prose', '\n'.join(prose)))
    res = []
    for k, t in out:
        t = normalize(t, glyph_map, code=(k == 'code'))
        if t.strip():
            res.append((k, t))
    return res


def chunk_prose(text: str, size: int = 90, overlap: int = 30) -> list[str]:
    words = text.split()
    if len(words) <= size:
        return [' '.join(words)] if words else []
    step = size - overlap
    return [' '.join(words[i:i + size]) for i in range(0, max(1, len(words) - overlap), step)]


def chunk_code(text: str, max_lines: int = 40) -> list[str]:
    lines = text.split('\n')
    return ['\n'.join(lines[i:i + max_lines]) for i in range(0, len(lines), max_lines)]


# ----------------------------------------------------------------------------- embeddings
class EmbedderUnavailable(RuntimeError):
    """The index was built with MiniLM and MiniLM cannot be loaded here."""


_MINILM_ERR = None


def _minilm():
    global _MINILM_ERR
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer('all-MiniLM-L6-v2')
    except Exception as e:
        _MINILM_ERR = f'{type(e).__name__}: {e}'
        return None


class Dense:
    """MiniLM if available, else LSA fitted on the corpus. Same object embeds documents and queries."""

    def __init__(self, texts, prefer='auto', stored=None):
        self.kind = None
        if prefer in ('auto', 'minilm'):
            m = _minilm()
            if m is not None:
                self.model, self.kind = m, 'minilm'
                self.doc = stored if stored is not None else self._enc(texts)
            elif prefer == 'minilm':
                msg = ('this index was built with MiniLM, but all-MiniLM-L6-v2 could not be loaded '
                       f'({_MINILM_ERR}). MIN_SCORE was calibrated on MiniLM scores, so an LSA search '
                       'would give different results. Install sentence-transformers and allow the model '
                       'download once, or set FACTCHECK_ALLOW_LSA=1 to use LSA anyway.')
                if os.environ.get('FACTCHECK_ALLOW_LSA') != '1':
                    raise EmbedderUnavailable(msg)
                import warnings
                warnings.warn('FACTCHECK_ALLOW_LSA=1: ' + msg.split('. MIN_SCORE')[0] + '; searching with LSA.',
                              RuntimeWarning, stacklevel=2)
        if self.kind is None:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.decomposition import TruncatedSVD
            self.vec = TfidfVectorizer(tokenizer=tokens, lowercase=False, token_pattern=None,
                                       sublinear_tf=True, min_df=1, ngram_range=(1, 2))
            X = self.vec.fit_transform(texts)
            self.svd = TruncatedSVD(n_components=min(256, X.shape[1] - 1, X.shape[0] - 1), random_state=0)
            self.doc = self._unit(self.svd.fit_transform(X))
            self.kind = 'lsa'

    @staticmethod
    def _unit(M):
        n = np.linalg.norm(M, axis=1, keepdims=True)
        return M / np.where(n == 0, 1, n)

    def _enc(self, texts):
        return np.asarray(self.model.encode(list(texts), normalize_embeddings=True, batch_size=64))

    def query(self, q: str):
        if self.kind == 'minilm':
            return self._enc([q])[0]
        return self._unit(self.svd.transform(self.vec.transform([q])))[0]


# ----------------------------------------------------------------------------- index
def index_paths(course_id: str, which: str):
    base = os.path.join(DATA_DIR, course_id)
    return (os.path.join(base, f'{which}_index.json'), os.path.join(base, f'{which}_emb.npy'))


def save_index(course_id: str, which: str, chunks: list[dict], meta: dict, embedder='auto'):
    """chunks: dicts with at least 'text' and 'ref'. Embeds them and writes json (+ npy for MiniLM)."""
    jp, npy = index_paths(course_id, which)
    os.makedirs(os.path.dirname(jp), exist_ok=True)
    dense = Dense([c['text'] for c in chunks], prefer=embedder)
    meta = dict(meta, embedder=dense.kind, n_chunks=len(chunks))
    json.dump(dict(meta=meta, chunks=chunks), open(jp, 'w'), ensure_ascii=False)
    if dense.kind == 'minilm':
        np.save(npy, dense.doc)
    elif os.path.exists(npy):
        os.remove(npy)
    load_index.cache_clear()
    return meta


class Index:
    def __init__(self, meta, chunks, stored_emb):
        from rank_bm25 import BM25Okapi
        self.meta, self.chunks = meta, chunks
        self.toks = [tokens(c['text']) for c in chunks]
        self.bm25 = BM25Okapi(self.toks)
        self.dense = Dense([c['text'] for c in chunks], prefer=meta.get('embedder', 'auto'), stored=stored_emb)
        self.embedder = self.dense.kind           # what search actually uses (meta['embedder'] = what built it)

    def search(self, query: str, k: int = 5, min_score: float = 0.0):
        q = tokens(query)
        if not q or not self.chunks:
            return []
        q = list(dict.fromkeys(q))
        idf_sum = sum(max(self.bm25.idf.get(t, 0.0), 0.0) for t in q)
        known = [t for t in q if t in self.bm25.idf]
        if not known or idf_sum <= 0:
            return []
        # unknown query words (not in the book at all) count against the claim: a claim about Paris
        # shares no vocabulary with the book, and its lexical score should be ~0, not undefined.
        unk_penalty = sum(1 for t in q if t not in self.bm25.idf) * max(self.bm25.idf.values())
        raw = self.bm25.get_scores(q)
        lex = np.clip(raw / (idf_sum + unk_penalty), 0, 1)
        den = np.clip(self.dense.doc @ self.dense.query(query), 0, 1)
        s = W_LEX * lex + (1 - W_LEX) * den
        # the absolute score s gates (MIN_SCORE); ranking adds a small share of raw BM25 so that among
        # chunks that all contain the claim's words, the one that uses them most comes first
        order = np.argsort(-(s + 0.1 * raw / max(raw.max(), 1e-9)))
        out = []
        for i in order[:max(k * 4, 20)]:
            if s[i] < min_score:
                continue
            out.append(dict(self.chunks[i], score=float(s[i]), lex=float(lex[i]), dense=float(den[i])))
        return out[:k]


@lru_cache(maxsize=32)
def load_index(course_id: str, which: str):
    """Load an index once per process. Returns None when it has not been built."""
    jp, npy = index_paths(course_id, which)
    if not os.path.exists(jp):
        return None
    d = json.load(open(jp))
    stored = np.load(npy) if os.path.exists(npy) and d['meta'].get('embedder') == 'minilm' else None
    return Index(d['meta'], d['chunks'], stored)


def search_index(course_id: str, which: str, query: str, k: int = 5, min_score: float = 0.0,
                 glyph_map=None):
    idx = load_index(course_id, which)
    if idx is None:
        return []
    return idx.search(normalize(query, glyph_map), k=k, min_score=min_score)


def sha256(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()
