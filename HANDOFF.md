# CMP 305 handoff to Wahib

From Ahmed, October 2026. The CMP 305 course module, built to Course Module Guide v2.

## What you're getting

| File | What it is |
|---|---|
| `courses/cmp305.py` | Course class. Page range 20-369, offset 19, SHA-256, claim types prose + code, 13-glyph map, MIN_SCORE from the eval report |
| `data/cmp305/known_issues.json` (Drive) | 68 verified issues: 23 official errata, 15 defects found beyond the errata, 30 VR7-VR10 findings (errors, conventions, naming, outdated). Every entry has a printed page that was checked against the book |
| `data/cmp305/urls.txt` (Drive) | 14 trusted pages (algs4, cppreference) |
| `data/cmp305/book_index*`, `web_index*` (Drive) | Book index (MiniLM) and web index, built 2026-10-11. You can rebuild them with your own scripts |
| `tests/test_cmp305.py` | The 4 required tests + 29 more; 32 pass with `data/cmp305/` in place (the no-web-index test skips), and the ones that need it skip without it |
| `tests/eval/cmp305.jsonl` + `cmp305_report.md` | 50 paraphrased claims + 20 negatives (8 from CMP 220 topics Weiss does not cover). Rates and MIN_SCORE are in the report |
| `verification/` (Drive) | The evidence behind known_issues.json (registries, VR results, the code-verification run, and the 3 shipped-code issues) |

The branch has no book text in it (guide section 10). Everything marked (Drive) is in the team Drive under
`cmp305-data/`: copy `data/cmp305/` and `verification/` into the clone. The PDF's SHA-256 must be
`d3510f9b88bb8ea0178d980772657c5a485a0ae319816ede9ef620c65b643f76`.

## Your files: stand-ins I wrote so the module could run

The guide assigns `base.py`, `utils.py`, `normalize.py`, `compute/`, the index scripts, `eval_course.py`
and the engine to you. None of them existed, so I wrote working versions with the guide's interfaces.
Keep them, change them or replace them. They are marked REFERENCE STAND-IN at the top of each file.

- `courses/base.py`: Evidence, CourseModule, `check_against_book` / `check_against_web` / `check_computed`, and the known-issues contradiction check
- `courses/utils.py`: hybrid search (normalized BM25 + dense cosine, 50/50), code-preserving chunking, index cache. Refuses to search a MiniLM index without MiniLM unless `FACTCHECK_ALLOW_LSA=1`
- `courses/normalize.py`: the normalizer from section 4.3, including the LaTeX step
- `courses/compute/`: C++ checker (C++17, then C++11; reports outdated) and SymPy checker, both run in a limited subprocess (rlimits, no network, uid nobody)
- `engine/engine.py` + `scripts/fact_check.py`: routing, claim typing and a reliability score, plain Python with a CLI

## Decide these before you integrate (otherwise the module still runs, just worse)

1. **Five optional fields in known_issues.json**: `terms`, `claim_types`, `also_pages`, `defect`, `scope`. They stop a code defect from flipping an unrelated prose claim on the same page, make a code claim count as wrong only when it contains the defect, and let book-wide conventions (height in edges, Rule of Five) apply on every page. If your contradiction check ignores them, everything still runs, but those false flips come back. Please adopt them or propose a replacement.
2. **`check_against_book(claim, claim_type="prose")`**: I added an optional second argument, so code claims only get code issues. Two tests use it.
3. **Your API contract**: the extension-to-engine request and response format isn't defined anywhere yet. `engine.check_page(blocks)` takes `[{"type": "text" | "code" | "math", "text": ..., "output": optional}]` and returns, per claim, `{course, claim, type, score, label, evidence[]}`. Wrapping that in FastAPI is the easiest route.
4. **The sandbox**: mine uses rlimits and a network namespace. The guide requires a separate container before you run code from real pages.

## Quick start

    pip install -r requirements.txt
    # copy cmp305-data/data/cmp305/ and cmp305-data/verification/ from the Drive into the clone
    python -m pytest -q
    python scripts/fact_check.py "Selection sort needs a quadratic number of swaps"
