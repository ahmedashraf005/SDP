"""Fact-check claims from the command line against a course (uses the engine stand-in).

    python scripts/fact_check.py "Heapsort runs in O(N log N) in the worst case"
    python scripts/fact_check.py --code snippet.cpp --output "4"
    python scripts/fact_check.py --page page.json          # [{"type": "text"|"code"|"math", "text": ...}]
    python scripts/fact_check.py --json ...                 # machine-readable output
Default course: cmp305 (override with --course).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from courses import by_id  # noqa: E402
from engine.engine import check_claim, check_page  # noqa: E402


def show(r):
    print(f"\n{r['claim'][:200]}\n  [{r['type']}] score {r['score']:.2f}: {r['label']}")
    for e in r['evidence']:
        print(f"  - {e['source_type']:8s} {e['verdict']:11s} {e['confidence']:.2f}  {e['reference']}")
        if e['note']:
            print(f"      note: {e['note'][:300]}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('claims', nargs='*')
    ap.add_argument('--course', default='cmp305')
    ap.add_argument('--type', default='prose', choices=['prose', 'equation', 'code'])
    ap.add_argument('--code')
    ap.add_argument('--output')
    ap.add_argument('--page')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    c = by_id(a.course)
    if a.page:
        res = check_page(json.load(open(a.page)), a.course)
    elif a.code:
        res = [check_claim(c, open(a.code).read(), 'code', a.output)]
    else:
        res = [check_claim(c, q, a.type) for q in a.claims]
    if a.json:
        print(json.dumps(res, indent=1, ensure_ascii=False))
    else:
        for r in res:
            show(r)
