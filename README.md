# fact-checker: CMP 305 course module (Course Module Guide v2)

The CMP 305 module built to Course Module Guide v2, plus working stand-ins for the shared pieces so it runs
end to end and can be checked now.

## Who owns what

| Path | Owner (guide) | In this repo |
|---|---|---|
| `courses/cmp305.py` | Ahmed | **the deliverable**: course class with page range, offset, glyph map, SHA-256, claim types |
| `data/cmp305/known_issues.json` | Ahmed | **the deliverable**: 68 verified issues (not in git, it quotes the book) |
| `data/cmp305/urls.txt` | Ahmed | 14 algs4 / cppreference pages |
| `tests/test_cmp305.py` | Ahmed | the 4 required tests + 29 more, including a check that no test or eval string is copied from the book |
| `tests/eval/cmp305.jsonl`, `cmp305_report.md` | Ahmed | 50 paraphrased claims + 20 negatives (8 of them CMP 220 topics); report sets MIN_SCORE |
| `courses/base.py`, `utils.py`, `normalize.py`, `compute/`, `scripts/*_index.py`, `scripts/eval_course.py` | Wahib | **reference stand-ins**: same interfaces as the guide, for Wahib to keep, change or replace |
| `engine/engine.py`, `scripts/fact_check.py` | Wahib | minimal stand-in for the engine (routing, claim typing, score) plus a CLI |
| `courses/calc1.py` | Calc 1 teammate | the guide's own example; the required sibling-course test imports it |

## What is in git and what is on the Drive

Guide section 10: nothing copied from the book goes into git. The branch has the code, tests, eval set and
report. The team Drive has `cmp305-data/`, which you copy into the clone:

| Drive | Goes to | Why not in git |
|---|---|---|
| the textbook PDF | `data/cmp305/book.pdf` | the book |
| `known_issues.json` | `data/cmp305/` | quotes the book (`book_says`) |
| `book_index.json`, `book_emb.npy` | `data/cmp305/` | chunked book text |
| `web_index.json`, `web_emb.npy`, `urls.txt` | `data/cmp305/` | kept with the other data files |
| `verification/` | `verification/` | the registries quote the book at length; the tarballs hold the author's source files |

Without `data/cmp305/` the tests that need it skip with a reason (17 pass, 16 skip); with it, 32 pass and the no-web-index test skips.

## Run it

    pip install -r requirements.txt
    # copy cmp305-data/ from the Drive into data/cmp305/ (or symlink the PDF and build the index)
    python scripts/build_book_index.py cmp305           # only if you rebuild; refuses a different PDF
    python -m pytest -q                                  # 33 tests
    python scripts/eval_course.py cmp305 --write         # writes tests/eval/cmp305_report.md
    python scripts/fact_check.py "Selection sort needs a quadratic number of swaps"
    python scripts/fact_check.py --code snippet.cpp --output "4"
    python scripts/build_web_index.py cmp305             # needs network access to the two trusted domains

## known_issues.json (68 entries)

- 23 official errata (every in-scope entry; 19 errors, 4 addenda filed as `imprecise`).
- NEW-001 to NEW-020 from this verification (NEW-014 retracted, NEW-017 not in the records, and NEW-006 / 019 / 020
  moved to `verification/shipped_code_issues.json` because they are in the author's downloadable files, not
  the printed book, so 15 entries). Every entry has a printed page.
- VR9: the p.51 little-o gloss error, conventions (B-tree = B+ tree, height in edges, empty tree -1,
  npl(null) = -1, complete tree, clustering, insertion-sort passes) and naming (Rule of Five, pass-by,
  member initializer list, default argument, member function, open hashing), one `outdated` (implicit conversion).
- VR10: p.6 edge case (N = 2), imprecisions p.68 / p.145 / p.271 / p.301.
- VR7 / VR8: push_back amortized, hinted set insert (`outdated`), balls into bins, hopscotch, binomial insert,
  median lower bound, word-ladder output-sensitivity.
- Every page was checked against the book text by a marker string when the file was generated.

Fields are the guide's (`id, page, kind, topic, book_says, correct, how_verified, source`) plus five
optional ones that the stand-in contradiction check uses and other engines can ignore:
`terms` (phrases the claim must mention; `a & b` = both), `claim_types` (e.g. code defects apply only to
code claims), `also_pages`, `defect` (regex: a code claim is contradicted only if it contains the defect), and
`scope: "book"` (a convention the whole book follows, such as height in edges, applies on any page, and is
reported from the claim's wording even when no chunk clears MIN_SCORE).

How the check applies an entry to a book hit (within one page of the entry's page):
`error` -> contradicts when the claim repeats the book's statement, supports with a note when it states the
correction (lexical stand-in for NLI); `outdated` -> outdated; `convention` / `naming` -> convention;
`imprecise` -> note only.

## Results

- MIN_SCORE, hit rate and false-accept rate: `tests/eval/cmp305_report.md` (the report is the source;
  `test_min_score_from_eval_report` fails if `cmp305.py` disagrees with it).
- The eval and tests contain no book text. The code claims are written the way a student would write them,
  and `test_no_book_text_in_tests_or_eval` fails on any prose string sharing more than 10 consecutive tokens
  with the book, or code sharing more than 12 or over half its 4-grams.
- Search is BM25 (normalized to [0, 1]) + MiniLM cosine, 50/50. An index built with MiniLM refuses to load
  without MiniLM (`EmbedderUnavailable`), because MIN_SCORE was calibrated on MiniLM scores.
  `FACTCHECK_ALLOW_LSA=1` allows the LSA fallback with a warning, for running tests on a machine without the
  model; the eval script will not write a report from such a run.
- Code-preserving chunking keeps listing indentation and drops listing line numbers; superscripts are
  extracted as `^` (N^2 instead of N2); all 13 control-character glyphs in Weiss's math fonts are mapped.

## Not done here

- No NLI model: "supports" from the book means "the book discusses this" (guide limitation 1).
- Sandbox is a stand-in (rlimits, no-network namespace, uid nobody), not the separate container the guide requires.
- Records correction found while building this: NEW-013 (Fig 2.7 maxSubSum3) is on printed pp. 63-64, not p. 60.
