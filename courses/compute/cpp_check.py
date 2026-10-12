"""C++ checker (Guide v2 4.6). Owner: Wahib. REFERENCE STAND-IN.

check_cpp(code, stated_output=None) -> [Evidence]
  1. compile with g++ -std=c++17; if that fails, with -std=c++11 (book-era code)
  2. if it has main(): run it in the sandbox and compare stdout with stated_output (whitespace-insensitive)
  3. fragments without main() get a prelude (common headers + using namespace std) and a syntax check

Verdicts:
  supports     compiles under C++17 and (if an output was stated) prints it
  outdated     compiles only under C++11 (correct for the book's standard, not current practice)
  contradicts  prints something else than stated, or fails to compile under both standards for a
               reason that is not missing context
  []           cannot tell: fragment depends on declarations the snippet does not show, timeout, crash
"""
import os
import re
import shutil

from ..base import Evidence
from . import sandbox

GXX = shutil.which('g++') or shutil.which('clang++')
# explicit headers, not <bits/stdc++.h>, so the prelude also works with clang / libc++ (macOS)
PRELUDE = ''.join(f'#include <{h}>\n' for h in (
    'iostream', 'vector', 'string', 'list', 'map', 'set', 'unordered_map', 'unordered_set', 'queue',
    'stack', 'deque', 'algorithm', 'functional', 'utility', 'memory', 'iterator', 'numeric', 'sstream',
    'stdexcept', 'cmath', 'cstdlib', 'climits', 'cstring')) + 'using namespace std;\n'
# errors that mean "the snippet leans on code it does not show", not "the code is wrong"
CONTEXT_ERR = re.compile(r"was not declared in this scope|does not name a type|has not been declared|"
                         r"is not a member of|expected (?:initializer|unqualified-id|constructor)|"
                         r"no matching function|incomplete type|undefined reference|"
                         r"there are no arguments to|ISO C\+\+ forbids declaration of", re.I)


def _first_error(err: str) -> str:
    for ln in err.splitlines():
        if ': error:' in ln:
            return ln.split(': error:', 1)[1].strip()[:200]
    return err.strip().splitlines()[-1][:200] if err.strip() else ''


def _compile(src: str, std: str, d: str, link: bool):
    path = os.path.join(d, f'main_{std}.cpp')
    open(path, 'w').write(src)
    out = os.path.join(d, f'a_{std}')
    argv = [GXX, f'-std={std}', '-O1', '-pedantic-errors', path] + (['-o', out] if link else ['-fsyntax-only'])
    r = sandbox.run(argv, d, cpu=20, mem_mb=1536, wall=40)
    return r, out


def _same(a: str, b: str) -> bool:
    return a.split() == b.split()


def check_cpp(code: str, stated_output: str | None = None) -> list:
    try:
        if not GXX or not code or not code.strip():
            return []
        has_main = re.search(r'\bmain\s*\(', code) is not None
        src = code if has_main and '#include' in code else PRELUDE + code
        d = sandbox.workdir()
        try:
            r17, exe17 = _compile(src, 'c++17', d, link=has_main)
            if not r17['ok']:
                return []
            std, exe, compiled17 = 'c++17', exe17, r17['rc'] == 0
            if not compiled17:
                r11, exe11 = _compile(src, 'c++11', d, link=has_main)
                if not r11['ok']:
                    return []
                if r11['rc'] == 0:
                    std, exe = 'c++11', exe11
                else:
                    err = _first_error(r17['err'])
                    if CONTEXT_ERR.search(r17['err']) and not has_main:
                        return []
                    return [Evidence('computed', 'g++ -std=c++17 and -std=c++11', err, 'contradicts',
                                     0.9 if has_main else 0.6, note=f'does not compile: {err}')]
            note_std = '' if std == 'c++17' else f'compiles under C++11 only; C++17 error: {_first_error(r17["err"])}'
            verdict = 'supports' if std == 'c++17' else 'outdated'
            if not has_main or stated_output is None:
                return [Evidence('computed', f'g++ -std={std}', 'compiles' + ('' if has_main else ' (fragment, syntax check)'),
                                 verdict, 0.6 if has_main else 0.4, note=note_std)]
            if os.name == 'nt':
                exe += '.exe'
            rr = sandbox.run([exe], d, cpu=2, mem_mb=256, wall=5)
            if not rr['ok'] or rr['timeout']:
                return []
            got = rr['out']
            if rr['rc'] in (-24, -9):                 # SIGXCPU / SIGKILL: CPU limit, treat as timeout
                return []
            if rr['rc'] != 0 and not got:
                return [Evidence('computed', f'g++ -std={std}; run', f'exit status {rr["rc"]}', 'contradicts', 0.8,
                                 note='crashed before printing the stated output')]
            if _same(got, stated_output):
                return [Evidence('computed', f'g++ -std={std}; run', got[:400], verdict, 1.0, note=note_std)]
            return [Evidence('computed', f'g++ -std={std}; run', got[:400], 'contradicts', 0.95,
                             note=f'prints {got.strip()[:120]!r}, the page states {stated_output.strip()[:120]!r}')]
        finally:
            shutil.rmtree(d, ignore_errors=True)
    except Exception:
        return []
