"""CMP 305 module tests. The first four are the guide's required tests (section 8.1); the rest check the
pieces the module depends on: normalizer, page references, known issues, computation checks, routing."""
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from courses.cmp305 import CMP305  # noqa: E402
from courses.calc1 import Calc1  # noqa: E402
from courses import utils  # noqa: E402

m = CMP305()
ISSUES_PATH = os.path.join(utils.DATA_DIR, 'cmp305', 'known_issues.json')
# Printed pages where the book states heapsort's O(N log N) worst case (complexity_claims_v3.json:
# p300 heapsort O(N log N), p301 2N log N - O(N) comparisons worst case, p310 introsort, p341 summary).
EXPECTED_PAGES = [300, 301, 310, 341]



def _index_status():
    """None when the book index loads; otherwise the reason to skip. data/ is not in git (guide section 10),
    so a fresh clone has no index until the files from the Drive are copied into data/cmp305/."""
    try:
        if utils.load_index('cmp305', 'book') is None:
            return 'book index not present: copy data/cmp305/ from the Drive or run scripts/build_book_index.py cmp305'
    except utils.EmbedderUnavailable:
        return 'index built with MiniLM, which cannot be loaded here (FACTCHECK_ALLOW_LSA=1 runs these on LSA)'
    return None


_IDX = _index_status()
needs_index = pytest.mark.skipif(_IDX is not None, reason=_IDX or '')


# ----------------------------------------------------------------------------- required (guide 8.1)
def test_matches():
    assert m.match_score("A binary search tree and a binary heap both "
                         "support insertion in O(log N) time") >= 2


@needs_index
def test_book_finds_known_fact():
    ev = m.check_against_book("Heapsort sorts N items in O(N log N) time in the worst case")
    assert ev and ev[0].source_type == "book"
    assert any(e.reference.endswith(f"p.{p}") for e in ev for p in EXPECTED_PAGES)


@needs_index
def test_unrelated_claim_returns_empty():
    assert m.check_against_book("The capital of France is Paris") == []


@needs_index
def test_sibling_course_returns_empty():
    assert m.check_against_book("The derivative of sin x is cos x") == []
    assert Calc1().match_score("heapsort and binary heap insertion") < 2


# ----------------------------------------------------------------------------- course file
def test_course_config():
    assert m.course_id == m.course_id.lower() and ' ' not in m.course_id
    assert m.page_range == (20, 369) and m.page_offset == 19
    assert m.claim_types == ["prose", "code"]
    assert re.fullmatch(r'[0-9a-f]{64}', m.book_sha256)
    assert 8 <= len(m.keywords) <= 15 and len(set(m.keywords)) == len(m.keywords)


def test_match_score_whole_words():
    assert m.match_score("cheap hash tablespoons") == 0          # no substring matches
    assert m.match_score("Separate chaining in a hash table") == 2


def test_book_pdf_checksum():
    pdf = os.path.join(utils.DATA_DIR, 'cmp305', 'book.pdf')
    if not os.path.exists(pdf):
        pytest.skip('book.pdf not present')
    assert utils.sha256(pdf) == m.book_sha256


def test_index_refuses_other_pdf(tmp_path):
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    import build_book_index
    fake = tmp_path / 'other.pdf'
    fake.write_bytes(b'%PDF-1.4 not the course book')
    with pytest.raises(SystemExit):
        build_book_index.build(m, str(fake))


# ----------------------------------------------------------------------------- normalizer
def test_normalizer():
    from courses.normalize import normalize
    assert normalize("T(N) = \x07(N log N)", m.glyph_map) == "T(N) = Θ(N log N)"
    assert normalize("\x06(N²)", m.glyph_map) == "Ω(N^2)"
    assert normalize("ﬁnd the out-\nput") == "find the output"
    assert normalize("N − 1 and a–b") == "N - 1 and a-b"
    assert normalize(r"\(\Theta(N \log N)\)") == "Θ(N log N)"
    assert normalize(r"\frac{N(N-1)}{2}") == "(N(N-1))/(2)"
    assert normalize("  for( int i = 0; ++i )\n      x;", code=True) == "  for( int i = 0; ++i )\n      x;"


# ----------------------------------------------------------------------------- page references
# Code claims are written the way a student would write them (own names and layout), never copied from
# the book; test_no_book_text_in_tests_or_eval enforces that.
STUDENT_SORTDOWN = """template <typename T>
void heapsort(vector<T>& v) {
    int n = v.size();
    for (int k = n / 2 - 1; k >= 0; k--)      // build a max heap
        percDown(v, k, n);
    for (int last = n - 1; last > 0; last--) {
        swap(v[0], v[last]);                    // largest item goes to the end
        percDown(v, 0, last);
    }
}"""
STUDENT_RADIX = """void countingRadixSort(vectro<string>& words, int len) {
    const int R = 256;                           // one bucket per character value
    vector<string> tmp(words.size());
    for (int pos = len - 1; pos >= 0; pos--) {   // least significant character first
        vector<int> cnt(R + 1, 0);
        for (auto& w : words) cnt[(unsigned char)w[pos] + 1]++;
        for (int b = 0; b < R; b++) cnt[b + 1] += cnt[b];
        for (auto& w : words) tmp[cnt[(unsigned char)w[pos]]++] = w;
        words.swap(tmp);
    }
}"""
STUDENT_HEAPIFY = """int n = v.size();
for (int k = n / 2 - 1; k >= 0; k--)
    percDown(v, k, n);   // heapify the array first"""

@needs_index
def test_printed_page_in_reference():
    ev = m.check_against_book(STUDENT_SORTDOWN, claim_type='code')
    assert any(e.reference.endswith("p.302") for e in ev)        # Fig 7.10 is on printed p.302 (PDF 321)


@needs_index
def test_code_chunks_keep_indentation():
    idx = utils.load_index('cmp305', 'book')
    code = [c['text'] for c in idx.chunks if c['kind'] == 'code' and 'void heapsort' in c['text']]
    assert code
    lines = code[0].split('\n')
    # the loops inside the function body are indented relative to the signature line
    sig = next(i for i, l in enumerate(lines) if 'void heapsort' in l)
    body_loops = [l for l in lines[sig + 1:] if l.lstrip().startswith('for')]
    assert body_loops and all(len(l) - len(l.lstrip()) >= 3 for l in body_loops)


# ----------------------------------------------------------------------------- known issues
@pytest.fixture(scope='module')
def issues():
    if not os.path.exists(ISSUES_PATH):
        pytest.skip('known_issues.json not present: copy data/cmp305/ from the Drive')
    with open(ISSUES_PATH) as f:
        return json.load(f)


def test_known_issues_format(issues):
    ISSUES = issues
    keys = {'id', 'page', 'kind', 'topic', 'book_says', 'correct', 'how_verified', 'source'}
    assert len({i['id'] for i in ISSUES}) == len(ISSUES)
    for i in ISSUES:
        assert keys <= set(i), i['id']
        assert i['kind'] in ('error', 'outdated', 'imprecise', 'convention', 'naming')
        assert i['source'] in ('errata', 'verification')
        assert isinstance(i['page'], int) and 1 <= i['page'] <= 350, i['id']   # printed pages only
    assert sum(i['source'] == 'errata' for i in ISSUES) == 23      # every in-scope official erratum
    assert not any(i['id'] == 'NEW-014' for i in ISSUES)          # retracted


@needs_index
def test_book_error_flips_verdict():
    ev = m.check_against_book("Selection sort needs a quadratic number of swaps because of the adjacent-exchange lower bound")
    hit = [e for e in ev if e.reference.endswith("p.296")]
    assert hit and hit[0].verdict == "contradicts" and "ERRATA-p296" in hit[0].note


@needs_index
def test_claim_stating_the_correction_is_supported():
    ev = m.check_against_book("Selection sort performs at most N-1 swaps, so the adjacent exchange lower bound does not apply to it")
    hit = [e for e in ev if e.reference.endswith("p.296")]
    assert hit and hit[0].verdict == "supports" and "ERRATA-p296" in hit[0].note


@needs_index
def test_errata_theorem_5_2():
    # repeats the book's wrong statement of Theorem 5.2, in a student's words
    ev = m.check_against_book("Throw N balls at random into N^2 bins and the odds that every bin holds at most one ball are under 50%")
    assert ev[0].reference.endswith("p.213") and ev[0].verdict == "contradicts"


@needs_index
def test_convention_note():
    # at the real MIN_SCORE: a book-wide convention is reported from the claim's wording, even when no chunk
    # clears the threshold (with MiniLM this wordy claim scores ~0.57 on p.122, under 0.60)
    ev = m.check_against_book("In Weiss the height of a leaf is 0, but many sites say a leaf has height 1")
    assert any(e.reference.endswith("p.122") and e.verdict == "convention" and "edges" in e.note for e in ev)
    ev = m.check_against_book("AVL tree height is at most about 1.44 log N")      # no false convention note
    assert all(e.verdict != "convention" for e in ev)


@needs_index
def test_code_issue_does_not_flip_prose():
    # NEW-018 is a code defect in makeEmpty; a prose claim about separate chaining must not be flipped
    ev = m.check_against_book("With separate chaining, each bucket stores a linked list of the keys that hash there")
    assert ev and all(e.verdict != "contradicts" for e in ev)


# ----------------------------------------------------------------------------- computation
def test_cpp_supports_and_contradicts():
    from courses.compute.cpp_check import check_cpp
    ok = check_cpp('#include <iostream>\nint main(){ std::cout << 2 + 2 << std::endl; }', '4')
    assert ok[0].source_type == 'computed' and ok[0].verdict == 'supports'
    bad = check_cpp('#include <iostream>\nint main(){ std::cout << 2 + 2 << std::endl; }', '5')
    assert bad[0].verdict == 'contradicts'


def test_cpp_outdated():
    from courses.compute.cpp_check import check_cpp
    ev = check_cpp('#include <iostream>\nint main(){ register int x = 3; std::cout << x; }', '3')
    assert ev[0].verdict == 'outdated'


def test_cpp_book_defect_new005():
    # Fig 1.22 as printed uses end1 (digit one) for endl
    from courses.compute.cpp_check import check_cpp
    ev = check_cpp('#include <iostream>\nusing namespace std;\nint main(){ cout << "hi" << end1; return 0; }', 'hi')
    assert ev[0].verdict == 'contradicts' and 'end1' in ev[0].note


def test_cpp_book_defect_new001():
    # Fig 7.10 printed order: heapsort defined before percDown -> fails at instantiation
    from courses.compute.cpp_check import check_cpp
    # a student's own heapsort with the same ordering as the book (sort first, helper after); not the
    # book's listing
    code = '''#include <vector>
#include <utility>
using namespace std;

template <typename T>
void heapsort(vector<T>& v) {
    int n = v.size();
    for (int k = n / 2 - 1; k >= 0; k--) percDown(v, k, n);
    for (int last = n - 1; last > 0; last--) { swap(v[0], v[last]); percDown(v, 0, last); }
}

template <typename T>
void percDown(vector<T>& v, int hole, int size) {
    T item = move(v[hole]);
    while (2 * hole + 1 < size) {
        int c = 2 * hole + 1;
        if (c + 1 < size && v[c] < v[c + 1]) c++;
        if (!(item < v[c])) break;
        v[hole] = move(v[c]);
        hole = c;
    }
    v[hole] = move(item);
}

int main() { vector<int> v{3, 1, 2}; heapsort(v); }
'''
    ev = check_cpp(code, '')
    assert ev and ev[0].verdict == 'contradicts' and 'percDown' in ev[0].note


def test_cpp_never_raises():
    from courses.compute.cpp_check import check_cpp
    assert check_cpp('int main(){ while(1); }', '') == []           # CPU limit -> []
    assert check_cpp('', None) == []


def test_equations_not_checked_for_cmp305():
    assert m.check_computed("d/dx sin(x) = cos(x)", "equation") == []   # claim_types is prose + code


def test_sympy_checker():
    from courses.compute.sympy_check import check_equation
    assert check_equation("2^N + 2^N = 2^(N+1)")[0].verdict == 'supports'
    assert check_equation("2^N + 2^N = 2^(2N)")[0].verdict == 'contradicts'
    assert check_equation('__import__("os").system("id") = 1') == []


def test_minilm_index_refuses_lsa(monkeypatch):
    # an index built with MiniLM must not be searched with LSA behind the user's back (review item 4)
    monkeypatch.setattr(utils, '_minilm', lambda: None)
    chunks = [dict(text='binary heap insertion percolates up', ref='p1'), dict(text='hash table probing', ref='p2'),
              dict(text='quicksort pivot partition', ref='p3')]
    monkeypatch.delenv('FACTCHECK_ALLOW_LSA', raising=False)
    with pytest.raises(utils.EmbedderUnavailable):
        utils.Index(dict(embedder='minilm'), chunks, None)
    monkeypatch.setenv('FACTCHECK_ALLOW_LSA', '1')
    with pytest.warns(RuntimeWarning, match='LSA'):
        idx = utils.Index(dict(embedder='minilm'), chunks, None)
    assert idx.embedder == 'lsa'


# ----------------------------------------------------------------------------- web
def test_web_without_index_returns_empty():
    if os.path.exists(utils.index_paths('cmp305', 'web')[0]):
        pytest.skip('web index present')
    assert m.check_against_web("Heapsort runs in O(N log N) time") == []


def test_web_html_parser_keeps_math_and_code():
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    import build_web_index
    html = (b'<html><body><p>Insertion sort is <script type="math/tex">\\Theta(N^{2})</script> on average.</p>'
            b'<pre>for (int i = 1; i < n; i++)\n    insert(a, i);</pre><script>var x=1;</script></body></html>')
    blocks = build_web_index.html_blocks(html)
    assert ('code', 'for (int i = 1; i < n; i++)\n    insert(a, i);', None) in blocks
    prose = [t for k, t, _ in blocks if k == 'prose'][0]
    assert 'Θ(N^2)' in prose and 'var x' not in prose


# ----------------------------------------------------------------------------- engine
def test_routing():
    from engine.engine import route
    assert [c.course_id for c in route("Quicksort and heapsort both sort an array; a binary heap gives heapsort")] == ['cmp305']
    assert [c.course_id for c in route("Use the chain rule and the product rule to find the derivative of x sin x")] == ['calc1']
    assert route("The capital of France is Paris") == []


def test_min_score_from_eval_report():
    rep = os.path.join(ROOT, 'tests', 'eval', 'cmp305_report.md')
    chosen = re.search(r'Chosen MIN_SCORE = ([0-9.]+)', open(rep).read())
    assert chosen and float(chosen.group(1)) == m.MIN_SCORE


@needs_index
def test_code_claim_with_book_defect_is_contradicted():
    ev = m.check_against_book(STUDENT_RADIX, claim_type='code')
    assert ev[0].reference.endswith("p.334") and ev[0].verdict == "contradicts" and "NEW-003" in ev[0].note


@needs_index
def test_code_claim_without_the_defect_gets_a_note_only():
    ev = m.check_against_book(STUDENT_HEAPIFY, claim_type='code')
    hit = [e for e in ev if e.reference.endswith("p.302")]
    assert hit and hit[0].verdict == "supports" and "NEW-001" in hit[0].note


@needs_index
def test_extraction_clean():
    idx = utils.load_index('cmp305', 'book')
    text = ''.join(c['text'] for c in idx.chunks)
    assert not re.search(r'[\x00-\x08\x0b-\x1f]', text.replace('\t', ''))   # every glyph mapped
    assert '�' not in text and 'ﬁ' not in text
    pages = {c['page'] for c in idx.chunks}
    assert min(pages) == 1 and max(pages) <= 350


# ----------------------------------------------------------------------------- no book text in git
# Guide sections 8.2 and 10: eval claims and test strings are paraphrased, never copied from the book.
# Measured against the book index: the longest run of consecutive tokens a string shares with any book
# chunk, and for code the share of its 4-token sequences that occur in the book. A shared run of 9 tokens
# is a stock phrase ("runs in O(N log N) time"); copied sentences and listings share 15 to 80.
PROSE_MAX_RUN, CODE_MAX_RUN, CODE_MAX_4GRAM_SHARE = 10, 12, 0.5


def _tok(s):
    return re.findall(r"[A-Za-z_]\w*|\d+|[^\sA-Za-z_\d]", s.lower())


def _strings_to_check():
    out = []
    for line in open(os.path.join(ROOT, 'tests', 'eval', 'cmp305.jsonl')):
        if line.strip():
            r = json.loads(line)
            out.append((f"eval: {r['claim'][:50]}", r['claim'], r['type'] == 'code'))
    import ast
    tree = ast.parse(open(os.path.abspath(__file__)).read())
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) > 30 and n.lineno < _GUARD_LINE:
            is_code = bool(re.search(r'[;{}]|\bint\b', n.value)) and not n.value.strip()[:1].isupper()
            out.append((f"test line {n.lineno}", n.value, is_code))
    return out


_GUARD_LINE = sys._getframe().f_lineno


def test_no_book_text_in_tests_or_eval():
    # reads the chunk text only, so it runs wherever data/cmp305/ is present, with or without MiniLM
    jp = utils.index_paths('cmp305', 'book')[0]
    if not os.path.exists(jp):
        pytest.skip('book index not present: copy data/cmp305/ from the Drive')
    with open(jp) as f:
        chunks = [_tok(c['text']) for c in json.load(f)['chunks']]
    book = ' \x00 ' + ' \x00 '.join(' '.join(t) for t in chunks) + ' \x00 '     # \x00: runs never cross chunks
    grams = {tuple(t[i:i + 4]) for t in chunks for i in range(len(t) - 3)}
    bad = []
    for label, s, is_code in _strings_to_check():
        t = _tok(s)
        run, i = 0, 0
        while i + run < len(t):
            if ' ' + ' '.join(t[i:i + run + 1]) + ' ' in book:
                run += 1
            else:
                i += 1
        g = [tuple(t[j:j + 4]) for j in range(len(t) - 3)]
        share = sum(x in grams for x in g) / max(1, len(g))
        if run > (CODE_MAX_RUN if is_code else PROSE_MAX_RUN) or (is_code and len(t) >= 30 and share > CODE_MAX_4GRAM_SHARE):
            bad.append(f'{label}: {run} tokens in a row from the book, {share:.0%} of 4-grams')
    assert not bad, '\n'.join(bad)
