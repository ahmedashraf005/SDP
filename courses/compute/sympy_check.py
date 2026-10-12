"""Equation checker (Guide v2 4.6). Owner: Wahib. REFERENCE STAND-IN.
check_equation(claim) -> [Evidence] or []. The parse runs in a sandboxed subprocess (parse_expr calls eval)."""
import json
import os
import shutil
import sys
import warnings

from ..base import Evidence
from . import sandbox

WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_sympy_worker.py')


def check_equation(claim: str) -> list:
    try:
        d = sandbox.workdir()
        # copy the worker into the sandbox directory: the unprivileged child may not be able to read
        # the repository's own path
        w = os.path.join(d, 'worker.py')
        shutil.copyfile(WORKER, w)
        os.chmod(w, 0o644)
        r = sandbox.run([sys.executable, '-I', w], d, stdin=json.dumps(dict(claim=claim)).encode(),
                        cpu=4, mem_mb=1024, wall=15)
        shutil.rmtree(d, ignore_errors=True)
        if not r['ok']:
            return []                          # timeout or limit: the equation is just left unchecked
        lines = r['out'].strip().splitlines()
        res = json.loads(lines[-1]) if lines else {}
        if res.get('error') or r['rc'] != 0:
            # a broken checker (not a hard equation): every equation would come back unchecked, so warn
            warnings.warn('SymPy checker failed: ' + (res.get('error') or f"exit {r['rc']}: {r['err'].strip()[-300:]}"),
                          RuntimeWarning, stacklevel=2)
            return []
        if not res.get('verdict'):
            return []
        return [Evidence('computed', 'SymPy', claim[:200], res['verdict'], res['confidence'], note=res['how'])]
    except Exception:
        return []
