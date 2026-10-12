"""Build a course's book index (Guide v2 section 4.5). Owner: Wahib. REFERENCE STAND-IN.

    python scripts/build_book_index.py cmp305 [--pdf data/cmp305/book.pdf]

- refuses to run if the PDF's SHA-256 differs from the course's book_sha256 (when that is set)
- indexes only page_range (PDF pages, inclusive); every chunk carries the PRINTED page
  (PDF page - page_offset), which is what references show
- code-preserving chunking: monospace lines keep their line breaks and are chunked apart from prose
- the course's glyph_map and the shared normalizer are applied to every chunk
"""
import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pymupdf  # noqa: E402

from courses import by_id  # noqa: E402
from courses import utils  # noqa: E402


def build(course, pdf):
    digest = utils.sha256(pdf)
    if course.book_sha256 and digest != course.book_sha256:
        raise SystemExit(f'refusing to index: {pdf} has SHA-256 {digest}, course expects {course.book_sha256}')
    doc = pymupdf.open(pdf)
    lo, hi = course.page_range or (1, doc.page_count)
    chunks = []
    for pdf_page in range(lo, hi + 1):
        page = doc[pdf_page - 1]
        printed = pdf_page - course.page_offset
        blocks = utils.page_blocks(page, course.glyph_map)
        prose = ' '.join(t for k, t in blocks if k == 'prose')
        for t in utils.chunk_prose(prose):
            chunks.append(dict(text=t, page=printed, pdf_page=pdf_page, kind='prose'))
        for k, t in blocks:
            if k == 'code':
                for c in utils.chunk_code(t):
                    if len(c.split()) >= 3:
                        chunks.append(dict(text=c, page=printed, pdf_page=pdf_page, kind='code'))
    meta = dict(course_id=course.course_id, book_title=course.book_title, sha256=digest,
                page_range=[lo, hi], page_offset=course.page_offset,
                built=datetime.date.today().isoformat())
    return utils.save_index(course.course_id, 'book', chunks, meta)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('course_id')
    ap.add_argument('--pdf')
    a = ap.parse_args()
    c = by_id(a.course_id)
    if c is None:
        raise SystemExit(f'unknown course {a.course_id}')
    pdf = a.pdf or os.path.join(utils.DATA_DIR, c.course_id, 'book.pdf')
    print(build(c, pdf))
