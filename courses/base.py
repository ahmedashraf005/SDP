"""CourseModule and Evidence (Guide v2 section 4.1).

Owner: Wahib. REFERENCE STAND-IN written with the CMP 305 module so the module runs end to end; the
attributes and the Evidence fields are exactly the ones in the guide. Methods every course inherits:

    match_score(text) / matches(text)       whole-word keyword routing (guide 4.1)
    check_against_book(claim, claim_type='prose') -> [Evidence]  book index, printed pages, known issues
    check_against_web(claim)   -> [Evidence]  trusted-site index, fetch date in the reference
    check_computed(claim, claim_type, stated_output=None) -> [Evidence]   SymPy / C++ (guide 4.6)
    known_issues()             -> list of known_issues.json entries

All of them return [] when nothing is found and never raise for "not found".
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from . import utils
from .normalize import normalize


@dataclass
class Evidence:
    source_type: Literal["book", "website", "computed", "ai"]
    reference: str
    snippet: str
    verdict: Literal["supports", "contradicts", "not_found", "outdated", "convention"]
    confidence: float
    note: str = ""


@lru_cache(maxsize=32)
def _load_issues(course_id: str):
    p = os.path.join(utils.DATA_DIR, course_id, 'known_issues.json')
    if not os.path.exists(p):
        return ()
    try:
        return tuple(json.load(open(p)))
    except Exception:
        return ()


def _phrase_in(phrase: str, text: str) -> bool:
    """Whole-word, stem-tolerant phrase test: every token of phrase appears in text, in order.
    Phrases with a one-letter word, a hyphen, '+' or a symbol ("B-tree", "little o", "&x") are matched
    literally instead (case-insensitive, space or hyphen between words), because the tokenizer drops
    one-letter words and "B-tree" would otherwise shrink to "tree"."""
    words = phrase.split()
    if any(len(w) == 1 or re.search(r'[^A-Za-z0-9_]', w) for w in words):
        pat = r'[\s-]+'.join(re.escape(w) for w in re.split(r'[\s-]+', phrase.strip().lower()) if w)
        return re.search(r'(?<![a-z0-9])' + pat + r'(?![a-z0-9])', text.lower()) is not None
    pt, tt = utils.tokens(phrase), utils.tokens(text)
    if not pt:
        return False
    i = 0
    for t in tt:
        if t == pt[i]:
            i += 1
            if i == len(pt):
                return True
    return False


NEG = re.compile(r"\b(not|no|never|cannot|can't|doesn't|isn't|aren't|fails?|false|only|incorrect|wrong)\b|!=|≠", re.I)


def _closer_to(claim: str, book_says: str, correct: str) -> int:
    """+1 if the claim repeats the book's wrong statement, -1 if it states the correction, 0 if it cannot
    tell. Lexical stand-in for an NLI model: counts the claim's words that are distinctive to each
    statement, plus negation agreement (corrections usually negate the book: "does not apply")."""
    c = set(utils.tokens(claim))
    A, B = set(utils.tokens(book_says)), set(utils.tokens(correct))
    a, b = len(c & (A - B)), len(c & (B - A))
    neg_c, neg_a, neg_b = bool(NEG.search(claim)), bool(NEG.search(book_says)), bool(NEG.search(correct))
    if neg_b and not neg_a:
        b, a = (b + 1, a) if neg_c else (b, a + 1)
    elif neg_a and not neg_b:
        a, b = (a + 1, b) if neg_c else (a, b + 1)
    return 0 if a == b else (1 if a > b else -1)


class CourseModule:
    course_id = ""
    book_title = ""
    keywords: list[str] = []
    trusted_domains: list[str] = []
    MIN_SCORE = 0.55                              # each course overrides after its eval
    page_range: tuple[int, int] | None = None     # PDF pages to index, inclusive
    page_offset = 0                               # printed page = PDF page - page_offset
    claim_types = ["prose"]                       # add "equation" and/or "code"
    glyph_map: dict[str, str] = {}                # book-specific broken glyphs
    book_sha256 = ""                              # index script refuses a different PDF

    TOP_K = 3                                     # book / web hits returned per claim

    # ------------------------------------------------------------------ routing
    def match_score(self, text: str) -> int:
        text = text.lower()
        return sum(bool(re.search(rf"\b{re.escape(k)}\b", text))
                   for k in self.keywords)

    def matches(self, text: str) -> bool:         # kept for v1 compatibility
        return self.match_score(text) >= 2

    # ------------------------------------------------------------------ book
    def known_issues(self) -> list[dict]:
        return list(_load_issues(self.course_id))

    def issues_for(self, claim: str, page, claim_type: str = 'prose') -> list[dict]:
        """Known issues that apply to this claim at this printed page.
        An entry applies when
          - its page (or one of its optional 'also_pages') is within one page of the hit, or it has no page,
            or its optional 'scope' is "book" (a convention the whole book follows, e.g. height in edges);
          - the claim type is in its optional 'claim_types' (default: every type), so a code defect
            does not flip a prose claim about the same topic;
          - the claim mentions its subject: one of its optional 'terms' (a term "a & b" needs both
            phrases), else most of the words of its 'topic'."""
        out = []
        for it in _load_issues(self.course_id):
            # +-1 page: a discussion often continues onto the next page, and chunks cross page breaks
            pages = [it.get('page')] + list(it.get('also_pages') or [])
            if it.get('scope') != 'book' and it.get('page') is not None and not any(isinstance(p, int) and isinstance(page, int)
                                                       and abs(page - p) <= 1 for p in pages):
                continue
            if claim_type not in (it.get('claim_types') or [claim_type]):
                continue
            terms = it.get('terms') or []
            if terms:
                hit = any(all(_phrase_in(part, claim) for part in t.split('&')) for t in terms)
            else:
                tt = set(utils.tokens(it.get('topic', '')))
                hit = bool(tt) and len(tt & set(utils.tokens(claim))) >= max(1, (2 * len(tt) + 2) // 3)
            if hit:
                out.append(it)
        return out

    def _apply_issue(self, ev: Evidence, claim: str, it: dict, claim_type: str = 'prose') -> Evidence:
        kind = it.get('kind')
        tag = f"[{it.get('id')}] "
        if kind == 'error' and claim_type == 'code':
            # a code snippet is wrong only if it carries the defect itself (optional 'defect' regex);
            # otherwise the book listing's defect is reported and the computation check decides
            if it.get('defect') and re.search(it['defect'], claim):
                ev.verdict = 'contradicts'
                ev.note = tag + f"Contains the book's known defect. Correct: {it.get('correct')}"
            else:
                ev.note = (ev.note + ' ' if ev.note else '') + tag + f"The book listing has a known defect: {it.get('correct')}"
            return ev
        if kind == 'error':
            side = _closer_to(claim, it.get('book_says', ''), it.get('correct', ''))
            if side >= 0:     # claim repeats the book's error (or cannot tell): the book hit is not support
                ev.verdict = 'contradicts'
                ev.note = tag + f"The book is wrong here. Correct: {it.get('correct')}"
            else:
                ev.verdict = 'supports'
                ev.note = tag + f"The book is wrong on this page; the claim matches the verified correction: {it.get('correct')}"
        elif kind == 'outdated':
            ev.verdict = 'outdated'
            ev.note = tag + f"Correct for the book's C++11 era, not current practice. Today: {it.get('correct')}"
        elif kind in ('convention', 'naming'):
            ev.verdict = 'convention'
            ev.note = tag + f"{it.get('correct')}"
        else:                 # imprecise: the book is right in substance; say what is loose
            ev.note = tag + f"Book imprecise: {it.get('correct')}"
        return ev

    def check_against_book(self, claim: str, claim_type: str = 'prose') -> list[Evidence]:
        hits = utils.search_index(self.course_id, 'book', claim, k=self.TOP_K * 3,
                                  min_score=self.MIN_SCORE, glyph_map=self.glyph_map)
        out, seen = [], set()
        for h in hits:
            page = h.get('page')
            if page in seen:
                continue
            seen.add(page)
            ev = Evidence(source_type='book', reference=f"{self.book_title}, p.{page}",
                          snippet=h['text'][:400], verdict='supports', confidence=round(h['score'], 3))
            for it in self.issues_for(claim, page, claim_type):
                ev = self._apply_issue(ev, claim, it, claim_type)
                if ev.verdict == 'contradicts':
                    break
            out.append(ev)
            if len(out) == self.TOP_K:
                break
        return self._add_book_conventions(claim, claim_type, out)

    def _add_book_conventions(self, claim: str, claim_type: str, out: list[Evidence]) -> list[Evidence]:
        """A convention the whole book follows (optional 'scope': "book", e.g. height counted in edges) is
        a fact about the book, not about one retrieved chunk. It is reported whenever the claim mentions
        its subject, even if no chunk clears MIN_SCORE, so the note does not depend on the threshold.
        Its confidence is the retrieval score of the convention's own page (0 if that page is not in the
        top results), so callers can still tell a strong page match from a terms-only match."""
        conv = [it for it in _load_issues(self.course_id)
                if it.get('scope') == 'book' and it.get('kind') in ('convention', 'naming')
                and not any(f"[{it.get('id')}]" in e.note for e in out)
                and it in self.issues_for(claim, it.get('page'), claim_type)]
        if not conv:
            return out
        scores = {}
        for h in utils.search_index(self.course_id, 'book', claim, k=40, glyph_map=self.glyph_map):
            scores.setdefault(h.get('page'), (h['score'], h['text']))
        notes = []
        for it in conv:
            sc, txt = scores.get(it.get('page'), (0.0, it.get('book_says', '')))
            ev = Evidence(source_type='book', reference=f"{self.book_title}, p.{it.get('page')}",
                          snippet=txt[:400], verdict='supports', confidence=round(sc, 3))
            notes.append(self._apply_issue(ev, claim, it, claim_type))
        # the notes take the last places when the list is full, keeping at least the best page hit
        keep = max(min(len(out), 1), self.TOP_K - len(notes))
        return out[:keep] + notes

    # ------------------------------------------------------------------ web
    def check_against_web(self, claim: str) -> list[Evidence]:
        hits = utils.search_index(self.course_id, 'web', claim, k=self.TOP_K * 3,
                                  min_score=self.MIN_SCORE, glyph_map=None)
        out, seen = [], set()
        for h in hits:
            url = h.get('url', '')
            if url in seen or not any(d in url for d in self.trusted_domains):
                continue
            seen.add(url)
            out.append(Evidence(source_type='website', reference=f"{url} (fetched {h.get('fetched', '?')})",
                                snippet=h['text'][:400], verdict='supports', confidence=round(h['score'], 3)))
            if len(out) == self.TOP_K:
                break
        return out

    # ------------------------------------------------------------------ computation
    def check_computed(self, claim: str, claim_type: str, stated_output: str | None = None) -> list[Evidence]:
        if claim_type not in self.claim_types:
            return []
        try:
            if claim_type == 'equation':
                from .compute.sympy_check import check_equation
                return check_equation(normalize(claim))
            if claim_type == 'code':
                from .compute.cpp_check import check_cpp
                return check_cpp(claim, stated_output)
        except Exception:
            return []
        return []
