"""Build a course's web index (Guide v2 sections 4.5, 7). Owner: Wahib. REFERENCE STAND-IN.

    python scripts/build_web_index.py cmp305

Reads data/<course_id>/urls.txt (one URL per line, # comments). For each URL whose host is in the course's
trusted_domains: fetches it, reads PDFs with PyMuPDF (detected by content type), HTML with BeautifulSoup
(MathJax/LaTeX kept: <script type="math/tex"> contents are inlined, then the shared normalizer converts
them), drops pages whose text is too short to be real content (JavaScript-rendered sites), keeps <pre>
blocks as code chunks, and stores each page's fetch date in its chunks.
"""
import datetime
import os
import re
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from courses import by_id, utils  # noqa: E402
from courses.normalize import normalize  # noqa: E402

MIN_WORDS = 150


def fetch(url):
    import requests
    r = requests.get(url, timeout=30, headers={'User-Agent': 'fact-checker-index/2 (course project)'})
    r.raise_for_status()
    return r.headers.get('content-type', ''), r.content


def pdf_blocks(data):
    import pymupdf
    doc = pymupdf.open(stream=data, filetype='pdf')
    out = []
    for i, page in enumerate(doc, 1):
        out += [(k, t, i) for k, t in utils.page_blocks(page)]
    return out


def html_blocks(data):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(data, 'html.parser')
    for s in soup.find_all('script'):
        if 'math/tex' in (s.get('type') or ''):
            s.replace_with(' \\(' + s.get_text() + '\\) ')
        else:
            s.decompose()
    for t in soup(['style', 'nav', 'footer', 'header', 'noscript']):
        t.decompose()
    out = []
    for pre in soup.find_all('pre'):
        out.append(('code', normalize(pre.get_text(), code=True), None))
        pre.decompose()
    out.append(('prose', normalize(soup.get_text(' ')), None))
    return out


def build(course):
    path = os.path.join(utils.DATA_DIR, course.course_id, 'urls.txt')
    urls = [u.strip() for u in open(path) if u.strip() and not u.startswith('#')]
    today = datetime.date.today().isoformat()
    chunks, report = [], []
    for url in urls:
        host = urlparse(url).netloc
        if not any(host == d or host.endswith('.' + d) for d in course.trusted_domains):
            report.append((url, 'skipped: host not in trusted_domains'))
            continue
        try:
            ctype, data = fetch(url)
            blocks = pdf_blocks(data) if 'pdf' in ctype or url.lower().endswith('.pdf') else html_blocks(data)
        except Exception as e:
            report.append((url, f'failed: {e}'))
            continue
        words = sum(len(t.split()) for k, t, _ in blocks if k == 'prose')
        if words < MIN_WORDS:
            report.append((url, f'skipped: only {words} words (JavaScript-rendered?)'))
            continue
        for k, t, pg in blocks:
            parts = utils.chunk_prose(t) if k == 'prose' else utils.chunk_code(t)
            for c in parts:
                if len(c.split()) >= 3:
                    chunks.append(dict(text=c, url=url, fetched=today, kind=k, page=pg))
        report.append((url, f'ok: {words} words'))
    for u, r in report:
        print(f'{r:45s} {u}')
    if not chunks:
        raise SystemExit('no page could be indexed; web index not written')
    return utils.save_index(course.course_id, 'web', chunks, dict(course_id=course.course_id, built=today, urls=len(urls)))


if __name__ == '__main__':
    print(build(by_id(sys.argv[1])))
