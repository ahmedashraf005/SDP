"""Shared text normalizer (Guide v2 section 4.3).

Owner: Wahib. This file is a REFERENCE STAND-IN written with the CMP 305 module so the module can run
end to end; Wahib's version replaces it. Apply it to book text and web text at index time and to every
claim at query time - applying it on one side only makes matching worse.

Steps, in order:
  1. the course's glyph_map (book-specific broken glyphs, e.g. Weiss renders Θ as U+0007)
  2. Unicode superscript/subscript digits -> ^d / _d (NFKC would turn N² into N2 and lose the exponent)
  3. NFKC (splits the fi / fl ligatures)
  4. Unicode minus and dashes -> "-"; ≥ ≤ ≠ kept as symbols (combining "̸=" rebuilt as ≠)
  5. line-break hyphens rejoined ("out-\\nput" -> "output")
  6. LaTeX to one plain form: \\int -> ∫, \\frac{a}{b} -> (a)/(b), x^{2} -> x^2, \\Theta -> Θ ...
  7. whitespace collapsed (prose) or kept line by line (code=True)
"""
import re
import unicodedata

_SUP = str.maketrans({'⁰': '^0', '¹': '^1', '²': '^2', '³': '^3', '⁴': '^4', '⁵': '^5', '⁶': '^6',
                      '⁷': '^7', '⁸': '^8', '⁹': '^9', 'ⁿ': '^n', '⁻': '^-',
                      '₀': '_0', '₁': '_1', '₂': '_2', '₃': '_3', '₄': '_4', '₅': '_5', '₆': '_6',
                      '₇': '_7', '₈': '_8', '₉': '_9'})
_DASHES = dict.fromkeys(map(ord, '\u2212\u2010\u2011\u2012\u2013\u2014\u2015\ufe63\uff0d'), '-')
_QUOTES = {ord('\u2018'): "'", ord('\u2019'): "'", ord('\u201c'): '"', ord('\u201d'): '"'}

_LATEX_SYMBOLS = {
    r'\int': '∫', r'\sum': 'Σ', r'\prod': 'Π', r'\infty': '∞', r'\leq': '≤', r'\le': '≤',
    r'\geq': '≥', r'\ge': '≥', r'\neq': '≠', r'\ne': '≠', r'\approx': '≈', r'\cdot': '·',
    r'\times': '×', r'\Theta': 'Θ', r'\Omega': 'Ω', r'\theta': 'θ', r'\omega': 'ω', r'\lambda': 'λ',
    r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ', r'\Delta': 'Δ', r'\pi': 'π',
    r'\epsilon': 'ε', r'\varepsilon': 'ε', r'\phi': 'φ', r'\to': '→', r'\rightarrow': '→',
    r'\lfloor': '⌊', r'\rfloor': '⌋', r'\lceil': '⌈', r'\rceil': '⌉', r'\ldots': '...',
    r'\dots': '...', r'\cdots': '...', r'\log': 'log', r'\ln': 'ln', r'\lg': 'log', r'\sin': 'sin',
    r'\cos': 'cos', r'\tan': 'tan', r'\exp': 'exp', r'\lim': 'lim', r'\max': 'max', r'\min': 'min',
    r'\mid': '|', r'\in': '∈', r'\pm': '±', r'\partial': '∂',
}
_LATEX_DROP = [r'\left', r'\right', r'\displaystyle', r'\mathrm', r'\mathit', r'\mathbf', r'\text',
               r'\operatorname', r'\,', r'\;', r'\:', r'\!', r'\quad', r'\qquad']
_BRACE = r'\{((?:[^{}]|\{[^{}]*\})*)\}'           # one level of nested braces


def _latex(t: str) -> str:
    if '\\' not in t and '^{' not in t and '_{' not in t:
        return t
    t = re.sub(r'\\\(|\\\)|\\\[|\\\]|\$\$?', ' ', t)                 # math delimiters
    for _ in range(4):                                                   # nested fractions
        t2 = re.sub(r'\\[dt]?frac\s*' + _BRACE + r'\s*' + _BRACE, r'(\1)/(\2)', t)
        t2 = re.sub(r'\\sqrt\s*' + _BRACE, r'√(\1)', t2)
        t2 = re.sub(r'\\binom\s*' + _BRACE + r'\s*' + _BRACE, r'C(\1,\2)', t2)
        if t2 == t:
            break
        t = t2
    for k in _LATEX_DROP:
        t = t.replace(k, ' ' if k.startswith('\\') and len(k) == 2 else '')
    for k in sorted(_LATEX_SYMBOLS, key=len, reverse=True):
        t = re.sub(re.escape(k) + r'(?![A-Za-z])', _LATEX_SYMBOLS[k], t)
    t = re.sub(r'([\^_])\{([^{}\s]+)\}', r'\1\2', t)                  # x^{2} -> x^2
    t = re.sub(r'([\^_])\{([^{}]*)\}', r'\1(\2)', t)                   # x^{n+1} -> x^(n+1)
    t = t.replace('{', '').replace('}', '') if '\\' in t else t
    return t


def normalize(text: str, glyph_map: dict | None = None, code: bool = False) -> str:
    """Return the normalized form of text. Never raises on str input."""
    if not text:
        return ''
    if glyph_map:
        for k, v in glyph_map.items():
            text = text.replace(k, v)
    text = text.translate(_SUP)
    text = unicodedata.normalize('NFKC', text)
    text = text.translate(_DASHES).translate(_QUOTES)
    text = re.sub(r'\s*\u0338\s*=', ' ≠', text)                        # "T(N)̸ =" -> "T(N) ≠"
    text = text.replace('\u0338', '')
    if code:
        lines = [ln.rstrip() for ln in text.replace('\r', '').split('\n')]
        return '\n'.join(lines).strip('\n')
    text = re.sub(r'([A-Za-z])-[ \t]*\n[ \t]*([a-z])', r'\1\2', text)   # line-break hyphens
    text = _latex(text)
    text = re.sub(r'[ \t\r\f\v]+', ' ', text)
    text = re.sub(r'\s*\n\s*', ' ', text)
    return text.strip()
