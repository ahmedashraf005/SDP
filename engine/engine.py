"""Minimal engine (Guide v2 sections 1, 2, 4.2). Owner: Wahib. REFERENCE STAND-IN.

The real engine is Wahib's FastAPI service; this module does the same steps in plain Python so a course
module can be exercised end to end:

    route(page_text)            -> courses with the highest match_score >= 2 (all of them on a tie)
    type_claims(blocks)         -> [(claim, type, stated_output)] from blocks tagged by the extension
    check_claim(course, claim, type, stated_output) -> {"score", "label", "evidence"}
    check_page(blocks, course_id=None) -> one result per claim

Order (guide 1): computed check for equations and code (when the course declares the type), then
book -> web -> AI. A computed result outweighs a topic match. The AI fallback is not part of this
stand-in and reports not_found.
"""
import re
from dataclasses import asdict

from courses import COURSES, by_id
from courses.base import Evidence

SENT = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"(])')
MATH = re.compile(r'\\\(|\\\[|\$\$|\\frac|\\int|\\sum')


def route(text: str, courses=None):
    courses = courses or COURSES
    scored = [(c.match_score(text), c) for c in courses]
    top = max((s for s, _ in scored), default=0)
    return [c for s, c in scored if s == top and s >= 2]


def type_claims(blocks):
    """blocks: [{"type": "text" | "code" | "math", "text": str, "output": optional stated output}]"""
    out = []
    for b in blocks:
        kind, text = b.get('type', 'text'), (b.get('text') or '').strip()
        if not text:
            continue
        if kind == 'code':
            out.append((text, 'code', b.get('output')))
        elif kind == 'math' or MATH.search(text):
            out.append((text, 'equation', None))
        else:
            out += [(s.strip(), 'prose', None) for s in SENT.split(text) if len(s.split()) >= 4]
    return out


def score(evidence):
    """Reliability in [0, 1] and a label. Computed evidence dominates; then the book; then the web."""
    comp = [e for e in evidence if e.source_type == 'computed']
    book = [e for e in evidence if e.source_type == 'book']
    web = [e for e in evidence if e.source_type == 'website']
    if comp:
        e = max(comp, key=lambda e: e.confidence)
        if e.verdict == 'contradicts':
            return round(0.15 * (1 - e.confidence) + 0.05, 2), 'contradicted by computation'
        if e.verdict == 'outdated':
            return 0.6, 'outdated (works only under the older C++ standard)'
        base = 0.7 + 0.25 * e.confidence
        return round(min(1.0, base + (0.05 if book else 0)), 2), 'supported by computation'
    if book:
        if any(e.verdict == 'contradicts' for e in book):
            return 0.15, 'contradicted: the book is wrong here (known issue)'
        e = book[0]
        if e.verdict == 'convention':
            return round(0.55 + 0.3 * e.confidence, 2), 'supported, different convention'
        if e.verdict == 'outdated':
            return 0.6, 'outdated'
        return round(0.5 + 0.45 * e.confidence, 2), 'in the course textbook'
    if web:
        return round(0.4 + 0.35 * web[0].confidence, 2), 'on a trusted site'
    return 0.5, 'not found in course sources'


def check_claim(course, claim: str, claim_type: str = 'prose', stated_output=None):
    ev = []
    if claim_type in ('equation', 'code'):
        ev += course.check_computed(claim, claim_type, stated_output)
    ev += course.check_against_book(claim, claim_type=claim_type if claim_type in course.claim_types else 'prose')
    if not [e for e in ev if e.source_type == 'book']:
        ev += course.check_against_web(claim)
    s, label = score(ev)
    return dict(course=course.course_id, claim=claim, type=claim_type, score=s, label=label,
                evidence=[asdict(e) for e in ev])


def check_page(blocks, course_id=None):
    text = ' '.join(b.get('text', '') for b in blocks)
    courses = [by_id(course_id)] if course_id else route(text)
    results = []
    for claim, t, out in type_claims(blocks):
        best = None
        for c in courses:            # tie: check both, keep the stronger evidence
            r = check_claim(c, claim, t, out)
            strength = max((e['confidence'] for e in r['evidence']), default=0)
            if best is None or strength > best[0]:
                best = (strength, r)
        results.append(best[1] if best else dict(course=None, claim=claim, type=t, score=0.5,
                                                 label='no course matched', evidence=[]))
    return results
