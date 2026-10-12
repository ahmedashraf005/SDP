"""Runs INSIDE the sandbox: parse_expr calls eval, so untrusted equations are parsed only here.
stdin: JSON {"claim": str}. stdout: JSON {"verdict", "confidence", "how"} or {"verdict": null}."""
import json
import random
import re
import sys


def main():
    try:
        import sympy as sp
        from sympy.parsing.sympy_parser import (parse_expr, standard_transformations,
                                                implicit_multiplication_application, convert_xor)
    except Exception as e:      # e.g. site-packages not readable by the sandbox user: say so, do not go quiet
        print(json.dumps(dict(verdict=None, error=f'cannot import sympy in the sandbox: {type(e).__name__}: {e}')))
        sys.exit(3)
    T = standard_transformations + (implicit_multiplication_application, convert_xor)
    claim = json.loads(sys.stdin.read())['claim']
    s = claim.replace('·', '*').replace('×', '*').replace('−', '-').replace('√', 'sqrt')
    s = s.replace('∞', 'oo').replace('ln', 'log').strip().rstrip('.')
    x = sp.Symbol('x')
    loc = {'e': sp.E, 'pi': sp.pi, 'C': sp.Symbol('C'), 'x': x, 'N': sp.Symbol('N', positive=True),
           'n': sp.Symbol('n', positive=True), 'log': sp.log}

    def P(t):
        return parse_expr(t.strip(), local_dict=loc, transformations=T)

    kind = None
    m = re.match(r'^\s*∫\s*(.+?)\s*d([a-z])\s*=\s*(.+)$', s)
    if m:                                   # indefinite integral: differentiate the claimed antiderivative
        v = sp.Symbol(m.group(2)); loc[m.group(2)] = v
        lhs = P(m.group(1)); rhs = P(m.group(3)).subs(sp.Symbol('C'), 0)
        diff = sp.simplify(sp.diff(rhs, v) - lhs); kind = 'antiderivative'; free = [v]
    else:
        m = re.match(r'^\s*d/d([a-z])\s*(.+?)\s*=\s*(.+)$', s) or re.match(r'^\s*the derivative of (.+?) is (.+)$', s, re.I)
        if m and m.re.pattern.startswith('^\\s*d/d'):
            v = sp.Symbol(m.group(1)); loc[m.group(1)] = v
            diff = sp.simplify(sp.diff(P(m.group(2)), v) - P(m.group(3))); kind = 'derivative'; free = [v]
        elif m:
            diff = sp.simplify(sp.diff(P(m.group(1)), x) - P(m.group(2))); kind = 'derivative'; free = [x]
        else:
            m = re.match(r'^\s*lim\s*_?\(?\s*([a-z])\s*→\s*([^\s)]+)\s*\)?\s*(.+?)\s*=\s*(.+)$', s)
            if m:
                v = sp.Symbol(m.group(1)); loc[m.group(1)] = v
                val = sp.limit(P(m.group(3)), v, P(m.group(2)))
                ok = sp.simplify(val - P(m.group(4))) == 0
                print(json.dumps(dict(verdict='supports' if ok else 'contradicts', confidence=1.0,
                                      how=f'limit computed symbolically = {val}'))); return
            if s.count('=') != 1 or any(c in s for c in '<>≤≥'):
                print(json.dumps(dict(verdict=None))); return
            a, b = s.split('=')
            diff = sp.simplify(P(a) - P(b)); kind = 'identity'
            free = sorted(diff.free_symbols | P(a).free_symbols, key=str)
    if diff == 0:
        print(json.dumps(dict(verdict='supports', confidence=1.0, how=f'{kind}: proven symbolically'))); return
    rnd = random.Random(0); bad = 0; tried = 0
    for _ in range(20):
        vals = {v: rnd.uniform(0.3, 3.0) for v in diff.free_symbols}
        try:
            r = complex(diff.evalf(subs=vals))
        except Exception:
            continue
        tried += 1
        if abs(r) > 1e-8 * (1 + abs(r)):
            bad += 1
    if tried == 0:
        print(json.dumps(dict(verdict=None))); return
    if bad:
        print(json.dumps(dict(verdict='contradicts', confidence=0.9,
                              how=f'{kind}: sides differ at {bad} of {tried} random points'))); return
    print(json.dumps(dict(verdict='supports', confidence=0.8, how=f'{kind}: equal at {tried} random points')))


try:
    main()
except Exception:
    print(json.dumps(dict(verdict=None)))
