"""Run a course's eval set (Guide v2 section 8.2). Owner: Wahib. REFERENCE STAND-IN.

    python scripts/eval_course.py cmp305 [--write]

For MIN_SCORE from 0.40 to 0.75 reports
  top-3 hit rate     share of positive claims whose expected page is among the top 3 book results
                     (distinct pages) scoring at least MIN_SCORE
  false-accept rate  share of negative claims (expected_pages = []) that return any book result
and recommends the threshold with the highest hit rate among those meeting the false-accept bar
(ties: the higher threshold). --write saves tests/eval/<course_id>_report.md.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from courses import by_id, utils  # noqa: E402

THRESHOLDS = [round(0.40 + 0.05 * i, 2) for i in range(8)]
HIT_BAR, FA_BAR = 0.80, 0.10


def top_pages(hits, t, k=3):
    out = []
    for h in hits:
        if h['score'] >= t and h['page'] not in out:
            out.append(h['page'])
        if len(out) == k:
            break
    return out


def run(course):
    rows = [json.loads(l) for l in open(os.path.join(ROOT, 'tests', 'eval', f'{course.course_id}.jsonl')) if l.strip()]
    idx = utils.load_index(course.course_id, 'book')
    for r in rows:
        r['hits'] = utils.search_index(course.course_id, 'book', r['claim'], k=40, glyph_map=course.glyph_map)
    pos = [r for r in rows if r['expected_pages']]
    neg = [r for r in rows if not r['expected_pages']]
    table = []
    for t in THRESHOLDS:
        hit = sum(bool(set(top_pages(r['hits'], t)) & set(r['expected_pages'])) for r in pos) / len(pos)
        fa = sum(bool(top_pages(r['hits'], t)) for r in neg) / len(neg)
        table.append((t, hit, fa))
    ok = [x for x in table if x[2] <= FA_BAR]
    best = max(ok, key=lambda x: (x[1], x[0])) if ok else None
    return rows, pos, neg, table, best, dict(idx.meta, search_embedder=idx.embedder)


def report(course, rows, pos, neg, table, best, meta):
    L = [f'# Eval report: {course.course_id}', '',
         f'Book index: {meta["n_chunks"]} chunks, embedder `{meta["embedder"]}` (search ran with `{meta["search_embedder"]}`), built {meta["built"]}, '
         f'SHA-256 {meta["sha256"][:12]}..., PDF pages {meta["page_range"][0]}-{meta["page_range"][1]} (offset {meta["page_offset"]}).',
         f'Eval set: {len(pos)} positive claims (paraphrased; expected printed pages from the verification records), {len(neg)} negatives '
         f'({sum(r.get("source") == "cmp220" for r in neg)} of them CMP 220 topics the book does not cover).',
         f'Search: score = {utils.W_LEX} x normalized BM25 + {1 - utils.W_LEX:.1f} x dense cosine.', '',
         '| MIN_SCORE | top-3 hit rate | false-accept rate | meets bar (hit >= 80%, FA <= 10%) |', '|---|---|---|---|']
    for t, h, f in table:
        L.append(f'| {t:.2f} | {h:.0%} ({round(h * len(pos))}/{len(pos)}) | {f:.0%} ({round(f * len(neg))}/{len(neg)}) | {"yes" if h >= HIT_BAR and f <= FA_BAR else "no"} |')
    L.append('')
    if best:
        L.append(f'**Chosen MIN_SCORE = {best[0]:.2f}** (highest hit rate with false-accept <= 10%): hit {best[1]:.0%}, false-accept {best[2]:.0%}.')
        t = best[0]
    else:
        L.append('No threshold meets the false-accept bar.')
        t = table[-1][0]
    L += ['', '## Caveats', '',
          '- The same eval set is used to pick MIN_SCORE and to report the rates (no held-out split); with 50 + 12 claims one claim moves the hit rate by 2 points and the false-accept rate by 8.']
    if meta['search_embedder'] != meta['embedder']:
        L.append(f'- **Not a valid calibration:** the index was built with `{meta["embedder"]}` but this run searched with '
                 f'`{meta["search_embedder"]}` (FACTCHECK_ALLOW_LSA=1). Rerun where {meta["embedder"]} loads.')
    elif meta.get('embedder') != 'minilm':
        L.append(f'- Dense part ran on the `{meta.get("embedder")}` fallback because the MiniLM weights were not available when the index was built. '
                 'Rebuild the index where MiniLM loads and rerun this script; the threshold is likely to move.')
    L += ['', f'## Per-claim results at MIN_SCORE = {t:.2f}', '', '| # | type | claim | expected | top-3 pages (score) | result |', '|---|---|---|---|---|---|']
    for i, r in enumerate(rows, 1):
        tp = top_pages(r['hits'], t)
        sc = {}
        for h in r['hits']:
            sc.setdefault(h['page'], h['score'])
        shown = ', '.join(f'{p} ({sc[p]:.2f})' for p in tp) or '-'
        if r['expected_pages']:
            res = 'hit' if set(tp) & set(r['expected_pages']) else 'MISS'
        else:
            res = 'FALSE ACCEPT' if tp else 'ok (empty)'
        c = r['claim'].replace('|', '\\|')
        L.append(f'| {i} | {r["type"]} | {c[:90]}{"..." if len(c) > 90 else ""} | {r["expected_pages"] or "-"} | {shown} | {res} |')
    return '\n'.join(L) + '\n', t


if __name__ == '__main__':
    c = by_id(sys.argv[1])
    rows, pos, neg, table, best, meta = run(c)
    text, t = report(c, rows, pos, neg, table, best, meta)
    for x in table:
        print(f'MIN_SCORE {x[0]:.2f}  hit {x[1]:.0%}  false-accept {x[2]:.0%}')
    print('chosen', t)
    if '--write' in sys.argv and meta['search_embedder'] != meta['embedder']:
        sys.exit(f'not writing the report: index built with {meta["embedder"]}, search ran with '
                 f'{meta["search_embedder"]}. Rerun where {meta["embedder"]} loads.')
    if '--write' in sys.argv:
        open(os.path.join(ROOT, 'tests', 'eval', f'{c.course_id}_report.md'), 'w').write(text)
    else:
        print(text)
