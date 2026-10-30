#!/usr/bin/env python3
"""
TRES0312-kompendiet (LaTeX) -> Quarto-sider for fysikkhjelp.no

Bruk:  python3 convert.py <TRES0312_Kompendium-mappe> <quarto-prosjektmappe>

Gjør:
  * deler hvert kapittel i én side per \\section (+ en kapittelside)
  * \\defn, \\exm, \\svar, \\merk, \\tips, \\oppsum, \\tanke, \\spm, \\graabox ... -> Quarto-bokser
  * \\oppgaver{tittel}{label}{\\input{...}} -> oppgaveblokk med løsningsforslag fra files_losning
  * siunitx (\\SI, \\si, \\num, \\ang) -> vanlig LaTeX som MathJax forstår
  * TikZ-figurer -> SVG (kompileres med pdflatex + pdftocairo)
  * YouTube-lenker -> innebygd video
  * pythonkode -> kjørbare Python-bokser
"""
import json, os, re, shutil, subprocess, sys, unicodedata, hashlib, tempfile
from pathlib import Path

SRC = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
SEC_DIR = OUT / 'forkurs'
IMG_DIR = OUT / 'forkurs' / 'bilder'
FIG_DIR = OUT / 'forkurs' / 'figurer'
FIG_CACHE = Path(os.environ.get('FIG_CACHE', '/tmp/tres_fig_cache'))

CHAPTERS = [  # (fil, kortnavn, status)
    ('0.0.1_HvaErFysikk.tex', 'hva-er-fysikk', 'klar'),
    ('0.0.2_MatematikkViTrenger.tex', 'matematikk', 'klar'),
    ('0.0.3_Kinematikk.tex', 'kinematikk', 'klar'),
    ('0.0.4_Krefter.tex', 'krefter', 'klar'),
    ('0.0.5_Energi.tex', 'energi', 'klar'),
    ('0.0.6_Statikk.tex', 'statikk', 'klar'),
    ('0.0.7_Fluidynamikk.tex', 'fluider', 'klar'),
    ('0.0.8_Termofysikk.tex', 'termofysikk', 'arbeid'),
    ('0.0.9_Elektrisitet.tex', 'elektrisitet', 'arbeid'),
]

# --------------------------------------------------------------------------- helpers
def slug(s):
    s = unicodedata.normalize('NFKD', s.replace('æ', 'ae').replace('ø', 'o').replace('å', 'a')
                              .replace('Æ', 'ae').replace('Ø', 'o').replace('Å', 'a'))
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s[:50] or 'side'

def read(p):
    return Path(p).read_text(encoding='utf-8', errors='replace')

def strip_comments(t):
    out = []
    for line in t.split('\n'):
        m = re.search(r'(?<!\\)%', line)
        if m:
            # keep a trailing % that only joins lines
            line = line[:m.start()]
        out.append(line)
    return '\n'.join(out)

def find_group(t, i, open_='{', close='}'):
    """t[i] == open_; return index after matching close."""
    assert t[i] == open_, (t[i:i + 30])
    depth = 0
    j = i
    while j < len(t):
        c = t[j]
        if c == '\\':
            j += 2
            continue
        if c == open_:
            depth += 1
        elif c == close:
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    raise ValueError('unbalanced group at ' + t[i:i + 60])

def skip_ws(t, i):
    while i < len(t) and t[i] in ' \t\n':
        i += 1
    return i

def parse_args(t, i, spec):
    """spec: string of 'm' (mandatory) / 'o' (optional [..]). returns (args, end)."""
    args = []
    for s in spec:
        k = skip_ws(t, i)
        if s == 'o':
            if k < len(t) and t[k] == '[':
                e = find_group(t, k, '[', ']')
                args.append(t[k + 1:e - 1])
                i = e
            else:
                args.append(None)
        else:
            if k < len(t) and t[k] == '{':
                e = find_group(t, k)
                args.append(t[k + 1:e - 1])
                i = e
            else:  # single token argument
                m = re.match(r'\\[a-zA-Z]+|.', t[k:])
                args.append(m.group(0))
                i = k + len(m.group(0))
    return args, i

def replace_macro(t, name, spec, fn):
    pat = re.compile(r'\\' + name + r'(?![a-zA-Z])')
    out = []
    pos = 0
    while True:
        m = pat.search(t, pos)
        if not m:
            out.append(t[pos:])
            break
        out.append(t[pos:m.start()])
        try:
            args, end = parse_args(t, m.end(), spec)
        except Exception:
            out.append(t[m.start():m.end()])
            pos = m.end()
            continue
        out.append(fn(*args))
        pos = end
    return ''.join(out)

def env_blocks(t, env):
    """yield (start, end, body) for \\begin{env}...\\end{env} (outermost, nesting-aware)."""
    b = '\\begin{' + env + '}'
    e = '\\end{' + env + '}'
    res = []
    i = 0
    while True:
        s = t.find(b, i)
        if s < 0:
            break
        depth = 0
        j = s
        while True:
            nb = t.find(b, j)
            ne = t.find(e, j)
            if ne < 0:
                raise ValueError('unclosed ' + env)
            if 0 <= nb < ne:
                depth += 1
                j = nb + len(b)
            else:
                depth -= 1
                j = ne + len(e)
                if depth == 0:
                    break
        res.append((s, j, t[s + len(b):j - len(e)]))
        i = j
    return res

def replace_env(t, env, fn):
    blocks = env_blocks(t, env)
    out = []
    pos = 0
    for s, e, body in blocks:
        out.append(t[pos:s])
        out.append(fn(body))
        pos = e
    out.append(t[pos:])
    return ''.join(out)

# --------------------------------------------------------------------------- siunitx
UNITS = {
    'metre': 'm', 'meter': 'm', 'gram': 'g', 'kilogram': 'kg', 'second': 's', 'newton': 'N', 'joule': 'J',
    'watt': 'W', 'pascal': 'Pa', 'hour': 'h', 'minute': 'min', 'litre': 'L', 'liter': 'L', 'kelvin': 'K',
    'degreeCelsius': '{}^{\\circ}\\mathrm{C}', 'celsius': '{}^{\\circ}\\mathrm{C}', 'percent': '\\%', 'degree': '{}^{\\circ}',
    'radian': 'rad', 'bar': 'bar', 'atmosphere': 'atm', 'atm': 'atm', 'volt': 'V', 'ampere': 'A', 'ohm': '\\Omega',
    'coulomb': 'C', 'hertz': 'Hz', 'mole': 'mol', 'calorie': 'cal', 'day': 'd', 'year': 'år', 'tonne': 't',
    'electronvolt': 'eV', 'farad': 'F', 'tesla': 'T', 'mmHg': 'mmHg', 'kWh': 'kWh', 'knot': 'knop', 'lightyear': 'ly',
}
PREFIX = {'kilo': 'k', 'milli': 'm', 'centi': 'c', 'mega': 'M', 'giga': 'G', 'micro': '\\mu ', 'nano': 'n', 'deci': 'd',
          'hecto': 'h', 'tera': 'T', 'pico': 'p'}

def unit_tex(u):
    u = u.strip()
    if not u:
        return ''
    if re.fullmatch(r'\^\\circ\s*C', u) or u in ('\\celsius', '\\degreeCelsius'):
        return '{}^{\\circ}\\mathrm{C}'
    if '\\' not in u:  # literal like m/s^2 or N.m
        lit = u.replace('.', '\\,').replace('~', '\\,')
        lit = re.sub(r'\^(-?\d+)', r'^{\1}', lit)
        return '\\mathrm{' + lit + '}'
    toks = re.findall(r'\\[a-zA-Z]+|\{[^}]*\}|[^\\\s{}]+', u)
    parts = []  # [symbol, power]
    per = False
    pref = ''
    i = 0
    while i < len(toks):
        tk = toks[i]
        name = tk[1:] if tk.startswith('\\') else None
        if name == 'per':
            per = True
        elif name in PREFIX:
            pref += PREFIX[name]
        elif name in ('squared',):
            if parts: parts[-1][1] *= 2
        elif name in ('cubed',):
            if parts: parts[-1][1] *= 3
        elif name in ('tothe', 'raiseto'):
            i += 1
            p = toks[i].strip('{}')
            if parts: parts[-1][1] *= float(p) if '.' in p else int(p)
        elif name in ('square',):
            pref = '^2' + pref
        elif name in UNITS:
            sym = UNITS[name]
            pw = -1 if per else 1
            if pref.startswith('^2'):
                pref = pref[2:]; pw *= 2
            parts.append([pref + sym, pw])
            pref = ''
            per = False
        elif name:
            parts.append([name, -1 if per else 1]); per = False
        else:
            parts.append([tk.strip('{}'), -1 if per else 1]); per = False
        i += 1
    out = []
    for sym, pw in parts:
        s = sym if sym.startswith('{}^') or sym.startswith('\\%') else '\\mathrm{' + sym + '}'
        if pw != 1:
            s += '^{' + str(pw) + '}'
        out.append(s)
    return '\\,'.join(out)

def num_tex(n):
    n = n.strip().replace('~', '')
    n = n.replace('+-', '\\pm ').replace('x', '\\times ')
    m = re.match(r'^([-+]?[\d.,]*)\s*[eE]\s*([-+]?\d+)$', n)
    if m:
        mant, ex = m.groups()
        ex = str(int(ex))
        if mant in ('', '1') and False:
            return '10^{' + ex + '}'
        return (mant + '\\cdot ' if mant else '') + '10^{' + ex + '}'
    return n

def si_convert(t, inmath0=False):
    """Convert siunitx macros. Track math mode so text-mode quantities get $...$."""
    out = []
    i = 0
    math = None  # None or closing delimiter
    envmath = 1 if inmath0 else 0
    MATHENVS = ('align', 'align*', 'equation', 'equation*', 'gather', 'gather*', 'multline', 'eqnarray', 'cases', 'aligned', 'split')
    while i < len(t):
        c = t[i]
        if c == '\\':
            m = re.match(r'\\doubleunderline(?![a-zA-Z])', t[i:])
            if m:
                args, end = parse_args(t, i + len(m.group(0)), 'm')
                inner = si_convert(args[0], bool(math or envmath))
                if math or envmath:
                    out.append('\\underline{\\underline{' + inner + '}}')
                else:
                    out.append('\\textbf{' + inner + '}')
                i = end
                continue
            m = re.match(r'\\(SI|si|num|ang|qty|unit|SIrange)(?![a-zA-Z])', t[i:])
            if m:
                name = m.group(1)
                spec = {'SI': 'omm', 'qty': 'omm', 'si': 'om', 'unit': 'om', 'num': 'om', 'ang': 'om', 'SIrange': 'ommm'}[name]
                args, end = parse_args(t, i + len(m.group(0)), spec)
                if name in ('SI', 'qty'):
                    v = num_tex(args[1]) + '\\,' + unit_tex(args[2])
                elif name in ('si', 'unit'):
                    v = unit_tex(args[1])
                elif name == 'num':
                    v = num_tex(args[1])
                elif name == 'ang':
                    v = num_tex(args[1]) + '^{\\circ}'
                else:
                    v = num_tex(args[1]) + '\\text{ til }' + num_tex(args[2]) + '\\,' + unit_tex(args[3])
                inmath = math is not None or envmath > 0
                out.append(v if inmath else '$' + v + '$')
                i = end
                continue
            m = re.match(r'\\(begin|end)\{([a-zA-Z*]+)\}', t[i:])
            if m and m.group(2) in MATHENVS:
                if math is None:
                    envmath += 1 if m.group(1) == 'begin' else -1
                out.append(m.group(0)); i += len(m.group(0)); continue
            if t.startswith('\\(', i) and math is None and not envmath:
                math = '\\)'; out.append('\\('); i += 2; continue
            if t.startswith('\\[', i) and math is None and not envmath:
                math = '\\]'; out.append('\\['); i += 2; continue
            if math in ('\\)', '\\]') and t.startswith(math, i):
                out.append(math); i += 2; math = None; continue
            if re.match(r'\\(textbf|textit|text|mbox|mathrm)\{', t[i:]) and (math or envmath):
                # inside \text{...} we are in text mode again: convert recursively as text
                m2 = re.match(r'\\(textbf|textit|text|mbox|mathrm)(?![a-zA-Z])', t[i:])
                k = i + len(m2.group(0))
                e = find_group(t, k)
                inner = t[k + 1:e - 1]
                if m2.group(1) != 'mathrm':
                    inner = si_convert(inner)
                out.append(m2.group(0) + '{' + inner + '}')
                i = e
                continue
            out.append(t[i:i + 2]); i += 2; continue
        if c == '$':
            if t.startswith('$$', i):
                if math == '$$':
                    math = None
                elif math is None:
                    math = '$$'
                out.append('$$'); i += 2; continue
            if math == '$':
                math = None
            elif math is None:
                math = '$'
            out.append('$'); i += 1; continue
        out.append(c); i += 1
    return ''.join(out)

# --------------------------------------------------------------------------- TikZ -> SVG
TIKZ_PREAMBLE = r'''\documentclass[border=6pt]{standalone}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb,graphicx,xcolor}
\usepackage{siunitx}
\sisetup{output-decimal-marker={.}, group-separator={\,}, exponent-product=\cdot}
\usepackage{tikz}
\usepackage{pgfplots}\pgfplotsset{compat=1.16}
\usetikzlibrary{positioning,shapes.geometric,arrows,arrows.meta,calc,decorations.pathmorphing,decorations.pathreplacing,decorations.markings,patterns,shadows,shadows.blur,shapes.misc,angles,quotes,intersections,backgrounds,fit}
\definecolor{mycolor}{RGB}{38,168,148}
\definecolor{oppsumcol}{rgb}{0.8,0.5,0}
\definecolor{defscol}{HTML}{449944}
\definecolor{exmscol}{HTML}{e04b52}
\definecolor{clmscol}{HTML}{165c58}
\definecolor{oppgcol}{HTML}{1A6B9A}
\definecolor{natKonstCol}{RGB}{0, 115, 60}
\definecolor{spmcol}{HTML}{F9F3EE}
\definecolor{codebg}{HTML}{EEECE9}
\newcommand{\doubleunderline}[1]{\underline{\underline{#1}}}
\graphicspath{{%IMG%/}{%SRC%/}}
%COLORS%
\begin{document}
%BODY%
\end{document}
'''

def compile_tikz(body, chap_short, n):
    key = hashlib.sha1(body.encode()).hexdigest()[:12]
    name = f'{chap_short}-{n:02d}-{key}.svg'
    FIG_CACHE.mkdir(parents=True, exist_ok=True)
    cached = FIG_CACHE / name
    if not cached.exists():
        with tempfile.TemporaryDirectory() as td:
            cols = '\n'.join(l.strip() for f in [SRC / 'amd.sty'] + sorted((SRC / 'files').glob('*.tex')) for l in read(f).split('\n') if l.strip().startswith(('\\definecolor', '\\colorlet')))
            doc = TIKZ_PREAMBLE.replace('%IMG%', str(SRC / 'Images')).replace('%SRC%', str(SRC)).replace('%COLORS%', cols).replace('%BODY%', body)
            (Path(td) / 'f.tex').write_text(doc, encoding='utf-8')
            r = subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error', 'f.tex'], cwd=td,
                               capture_output=True, text=True, timeout=120)
            if r.returncode != 0 or not (Path(td) / 'f.pdf').exists():
                err = [l for l in r.stdout.split('\n') if l.startswith('!')][:2]
                FAILED.append((chap_short, n, ' | '.join(err)))
                return None
            subprocess.run(['pdftocairo', '-svg', 'f.pdf', 'f.svg'], cwd=td, check=True)
            shutil.copy(Path(td) / 'f.svg', cached)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(cached, FIG_DIR / name)
    return name

FAILED = []

# --------------------------------------------------------------------------- images
IMG_MAP = {}

def image_ref(path):
    p = path.strip()
    cand = [SRC / p, SRC / 'Images' / p]
    src = None
    for c in cand:
        for ext in ('', '.png', '.PNG', '.jpg', '.jpeg', '.pdf'):
            if Path(str(c) + ext).exists():
                src = Path(str(c) + ext); break
        if src: break
    if not src:
        MISSING.append(p)
        return None
    if src not in IMG_MAP:
        stem = slug(src.stem)
        ext = src.suffix.lower()
        IMG_DIR.mkdir(parents=True, exist_ok=True)
        if ext == '.pdf':
            subprocess.run(['pdftocairo', '-svg', str(src), str(IMG_DIR / (stem + '.svg'))], check=False)
            IMG_MAP[src] = stem + '.svg'
        else:
            shutil.copy(src, IMG_DIR / (stem + ext))
            IMG_MAP[src] = stem + ext
    return IMG_MAP[src]

MISSING = []

# --------------------------------------------------------------------------- solutions
def load_solutions():
    sol = {}
    for f in sorted((SRC / 'files_losning').glob('*.tex')):
        t = strip_comments(read(f))
        pat = re.compile(r'\\oppgaver\s*\{')
        pos = 0
        while True:
            m = pat.search(t, pos)
            if not m: break
            args, end = parse_args(t, m.start() + len('\\oppgaver'), 'mmm')
            label = args[1].strip()
            k = skip_ws(t, end)
            if t.startswith('\\svar', k):
                sargs, send = parse_args(t, k + len('\\svar'), 'om')
                sol[label] = sargs[1]
                pos = send
            else:
                pos = end
    return sol

# --------------------------------------------------------------------------- body conversion
def inline_inputs(t):
    def rep(path):
        p = SRC / (path if path.endswith('.tex') else path + '.tex')
        return strip_comments(read(p)) if p.exists() else ''
    return replace_macro(t, 'input', 'm', rep)

def B(kind, title=''):
    return f'\n\nFHBEGIN{kind}FHT{title}FHE\n\n'

def E(kind):
    return f'\n\nFHEND{kind}FHE\n\n'

class Conv:
    def __init__(self, short, solutions):
        self.short = short
        self.fig = 0
        self.sol = solutions
        self.videos = 0

    def video(self, body):
        m = re.search(r'https?://(?:www\.)?youtu(?:\.be/|be\.com/watch\?v=)([\w-]{6,})', body)
        if not m:
            return body
        self.videos += 1
        return f'\n\nFHVIDEO{m.group(1)}FHE\n\n'

    def tikz(self, body):
        self.fig += 1
        name = compile_tikz('\\begin{tikzpicture}' + body + '\\end{tikzpicture}', self.short, self.fig)
        if not name:
            return '\n\nFHFIGFAIL\n\n'
        svg = (FIG_DIR / name).read_text(errors='ignore')[:600]
        m = re.search(r'width="([\d.]+)(pt|px)?"', svg)
        w = int(min(760, float(m.group(1)) * (1.333 if (m.group(2) or 'pt') == 'pt' else 1) * 1.45)) if m else 480
        return f'\n\nFHFIG{name}WIDTH{w}FHE\n\n'

    def convert(self, t):
        # YouTube thumbnails (wrapfigure/figure/center containing a youtu link)
        for env in ('wrapfigure', 'figure', 'center', 'minipage'):
            def maybe(body, env=env):
                if 'youtu' in body and '\\href' in body:
                    return self.video(body)
                return '\\begin{' + env + '}' + body + '\\end{' + env + '}'
            t = replace_env(t, env, maybe)
        t = replace_macro(t, 'href', 'mm', lambda url, txt: self.video(url) if 'youtu' in url else f'\\href{{{url}}}{{{txt}}}')
        # tikz
        t = replace_env(t, 'tikzpicture', self.tikz)
        # python code
        t = replace_env(t, 'pythonkode', lambda b: '\n\nFHCODE' + b.strip('\n').replace('\n', 'FHNL') + 'FHE\n\n')
        t = replace_env(t, 'pythonoutput', lambda b: '\n\nFHOUT' + b.strip('\n').replace('\n', 'FHNL') + 'FHE\n\n')
        t = replace_macro(t, 'pyfile', 'mm', lambda n, p: f'\n\n\\textit{{Kodefil: \\href{{https://github.com/kosmoben/TRES0312/blob/main/TRES0312%20Python/{p}}}{{{n}}}}}\n\n')
        t = replace_macro(t, 'pyfilenote', 'm', lambda x: '')
        t = replace_macro(t, 'pyfolderlink', '', lambda: '\\href{https://github.com/kosmoben/TRES0312/tree/main/TRES0312%20Python}{TRES0312 Python}')
        # boxes
        t = replace_macro(t, 'defn', 'mm', lambda a, b: B('defn', a) + b + E('defn'))
        t = replace_macro(t, 'defnr', 'mmm', lambda a, l, b: B('defn', a) + b + E('defn'))
        t = replace_macro(t, 'exm', 'mm', lambda a, b: B('exm', a) + b + E('exm'))
        t = replace_macro(t, 'exmr', 'mmm', lambda a, l, b: B('exm', a) + b + E('exm'))
        t = replace_macro(t, 'svar', 'om', lambda o, b: B('svar') + b + E('svar'))
        t = replace_macro(t, 'merk', 'mm', lambda a, b: B('merk', a) + b + E('merk'))
        t = replace_macro(t, 'merkr', 'mmm', lambda a, l, b: B('merk', a) + b + E('merk'))
        t = replace_macro(t, 'tips', 'mm', lambda a, b: B('tips', a) + b + E('tips'))
        t = replace_macro(t, 'tipsr', 'mmm', lambda a, l, b: B('tips', a) + b + E('tips'))
        t = replace_macro(t, 'oppsum', 'mm', lambda a, b: B('oppsum', a) + b + E('oppsum'))
        t = replace_macro(t, 'oppsumr', 'mmm', lambda a, l, b: B('oppsum', a) + b + E('oppsum'))
        t = replace_macro(t, 'tanke', 'mm', lambda a, b: B('tanke', a) + b + E('tanke'))
        t = replace_macro(t, 'asum', 'mm', lambda a, b: B('merk', 'Antakelse' + (': ' + a if a.strip() else '')) + b + E('merk'))
        t = replace_macro(t, 'rmk', 'm', lambda b: B('merk', '') + b + E('merk'))
        t = replace_macro(t, 'rmkb', 'm', lambda b: B('merk', '') + b + E('merk'))
        t = replace_macro(t, 'spm', 'mm', lambda a, b: B('spm', a) + '\\begin{enumerate}' + b + '\\end{enumerate}' + E('spm'))
        t = replace_macro(t, 'spq', 'm', lambda b: B('spq') + b + E('spq'))
        t = replace_macro(t, 'intro', 'm', lambda b: B('intro') + b + E('intro'))
        t = replace_macro(t, 'introTo', 'm', lambda b: B('intro') + b + E('intro'))
        t = replace_macro(t, 'chaptersubtitle', 'm', lambda b: B('intro') + b + E('intro'))
        t = replace_macro(t, 'graabox', 'm', lambda b: B('graa') + b + E('graa'))
        t = replace_macro(t, 'thm', 'mm', lambda a, b: B('defn', 'Teorem: ' + a) + b + E('defn'))

        def opp(title, label, body):
            label = label.strip()
            s = self.sol.get(label)
            r = B('oppg', title) + body
            if s:
                r += B('los') + s + E('los')
            return r + E('oppg')
        t = replace_macro(t, 'oppgaver', 'mmm', opp)
        t = replace_macro(t, 'oppgave', 'mm', lambda a, b: B('oppg', a) + b + E('oppg'))
        # misc formatting
        t = replace_macro(t, 'paragraph', 'm', lambda x: '\\textbf{' + x + '} ')
        t = replace_macro(t, 'captionof', 'mm', lambda k, c: '\n\nFHKAPSJON' + c + 'FHE\n\n')
        t = replace_macro(t, 'rotatebox', 'mm', lambda a, b: b)
        t = re.sub(r'\\(newpage|clearpage|noindent|smallskip|medskip|bigskip|centering|vfill|hfill|small|footnotesize|scriptsize|large|Large|normalsize|par)(?![a-zA-Z])', ' ', t)
        t = re.sub(r'\\(vspace|hspace)\*?\{[^}]*\}', ' ', t)
        t = re.sub(r'\\label\{[^}]*\}', '', t)
        t = re.sub(r'\\(tag\*?\{[^}]*\}|nonumber|notag)', '', t)
        t = re.sub(r'Kapittel~\\ref\{[^}]*\}', 'kompendiet', t)
        t = re.sub(r'(figur|Figur|tabell|Tabell|likning|Likning|ligning|Ligning|seksjon|Seksjon|avsnitt|Avsnitt|eksempel|Eksempel|oppgave|Oppgave)(en)?~?\s*\\ref\{[^}]*\}', lambda m: m.group(1) + 'en', t)
        t = re.sub(r'\(\\ref\{[^}]*\}\)|\\eqref\{[^}]*\}', '', t)
        t = re.sub(r'\\ref\{[^}]*\}', '', t)
        t = re.sub(r'\\begin\{(wrapfigure)\}(\[[^\]]*\])?\{[^}]*\}(\[[^\]]*\])?\{[^}]*\}', r'\\begin{\1}', t)
        t = re.sub(r'\\begin\{minipage\}(\[[^\]]*\])?\{[^}]*\}', r'\\begin{minipage}', t)
        t = re.sub(r'\\begin\{tcolorbox\}(\[[^\]]*\])?', r'\\begin{tcolorbox}', t)
        # images -> markers with copied file
        def img(o, p):
            name = image_ref(p)
            return f'\n\nFHIMG{name}FHE\n\n' if name else ''
        t = replace_macro(t, 'includegraphics', 'om', img)
        t = si_convert(t)
        return t

# --------------------------------------------------------------------------- pandoc + post-processing
BOX = {
    'defn': ('callout-note', 'Definisjon'),
    'merk': ('callout-important', 'Merk'),
    'tips': ('callout-tip', 'Tips'),
    'oppsum': ('callout-warning', 'Oppsummering'),
    'tanke': ('callout-tip', 'Til ettertanke'),
}

def pandoc(tex):
    r = subprocess.run([QUARTO, 'pandoc', '-f', 'latex', '-t', 'markdown-raw_html-native_divs-native_spans-fenced_divs+fenced_divs-simple_tables-multiline_tables-grid_tables+pipe_tables-smart',
                        '--wrap=none'], input=tex, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:2000])
    return r.stdout

def post(md, exm_counter):
    md = md.replace('\\_', '_') if False else md

    def un(s):  # pandoc escapes inside markers
        return s.replace('\\_', '_').replace('\\', '').strip()

    def begin(m):
        kind, title = m.group(1), m.group(2).strip()
        if kind in BOX:
            cls, default = BOX[kind]
            ttl = default + (': ' + title if title else '')
            return f'::: {{.{cls} title="{esc(ttl)}"}}'
        if kind == 'exm':
            exm_counter[0] += 1
            return f'::: {{.eksempel}}\n[Eksempel {exm_counter[1]}.{exm_counter[0]}: {title}]{{.eks-tittel}}\n'
        if kind == 'svar':
            return '::: {.callout-note .svar collapse="true" title="Vis løsning"}'
        if kind == 'oppg':
            return f'::: {{.oppgave tittel="{esc(title)}"}}\n[{title}]{{.oppg-tittel}}\n'
        if kind == 'los':
            return '::: {.losning}'
        if kind == 'spm':
            return '::: {.spm}\n[Spørsmål vi jobber med i dette kapitlet]{.spm-tittel}\n'
        if kind == 'spq':
            return '::: {.spm .spq}'
        if kind == 'intro':
            return '::: {.intro}'
        if kind == 'graa':
            return '::: {.graa}'
        return ':::'

    md = re.sub(r'FHBEGIN(\w+?)FHT(.*?)FHE', begin, md)
    md = re.sub(r'FHEND\w+?FHE', ':::', md)
    md = re.sub(r'FHVIDEO([\w\\-]+)FHE', lambda m: '{{< video https://www.youtube.com/watch?v=' + m.group(1).replace('\\', '') + ' >}}', md)
    md = re.sub(r'FHFIG(.+?)WIDTH(\d+)FHE', lambda m: f'![](../figurer/{un(m.group(1))}){{.tikz-fig style="width:{m.group(2)}px"}}', md)
    md = re.sub(r'FHIMG(.+?)FHE', lambda m: f'![](../bilder/{un(m.group(1))}){{.kompendium-bilde}}', md)
    md = md.replace('FHFIGFAIL', '*[Figur kommer]*')
    md = re.sub(r'FHKAPSJON(.+?)FHE', lambda m: f'[{m.group(1).strip()}]{{.figurtekst}}', md)

    def code(m, cls):
        body = m.group(1)
        body = body.replace('FHNL', '\n')
        body = re.sub(r'\\(.)', r'\1', body)  # pandoc escaping
        return f'```{cls}\n{body}\n```'
    md = re.sub(r'FHCODE(.*?)FHE', lambda m: code(m, '{.python .kjor}'), md, flags=re.S)
    md = re.sub(r'FHOUT(.*?)FHE', lambda m: code(m, '{.text .utskrift}'), md, flags=re.S)
    md = re.sub(r'\$\$(.*?)\$\$', lambda m: '$$' + re.sub(r'\n[ \t]*(?=\n)', '', m.group(1)) + '$$', md, flags=re.S)
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md

def esc(s):
    return s.replace('"', '\\"').replace('\n', ' ')

def pandoc_code_protect(t):
    """pandoc would mangle code; it's already in FHCODE markers with FHNL; escape $ and \\ to survive."""
    def prot(m):
        s = m.group(0)
        return s.replace('\\', 'ZQXBSQ').replace('$', 'ZQXDLQ').replace('%', 'ZQXPCQ').replace('{', 'ZQXLBQ').replace('}', 'ZQXRBQ').replace('_', 'ZQXUSQ').replace('#', 'ZQXHSQ').replace('&', 'ZQXAMQ').replace('^', 'ZQXCAQ').replace('~', 'ZQXTIQ')
    return re.sub(r'FH(CODE|OUT).*?FHE', prot, t, flags=re.S)

def pandoc_code_unprotect(md):
    for a, b in (('ZQXBSQ', '\\'), ('ZQXDLQ', '$'), ('ZQXPCQ', '%'), ('ZQXLBQ', '{'), ('ZQXRBQ', '}'), ('ZQXUSQ', '_'), ('ZQXHSQ', '#'), ('ZQXAMQ', '&'), ('ZQXCAQ', '^'), ('ZQXTIQ', '~')):
        md = md.replace(a, b)
    return md

QUARTO = os.environ.get('QUARTO', 'quarto')

def split_sections(t):
    """returns (chapter_title, pre, [(title, body)])"""
    m = re.search(r'\\chapter\*?(\[[^\]]*\])?\{', t)
    ct_end = find_group(t, m.end() - 1)
    ctitle = t[m.end():ct_end - 1]
    rest = t[ct_end:]
    pat = re.compile(r'\\section\*?(\[[^\]]*\])?\{')
    parts = []
    idx = [mm for mm in pat.finditer(rest)]
    pre = rest[:idx[0].start()] if idx else rest
    for k, mm in enumerate(idx):
        te = find_group(rest, mm.end() - 1)
        title = rest[mm.end():te - 1]
        body_end = idx[k + 1].start() if k + 1 < len(idx) else len(rest)
        parts.append((title, rest[te:body_end]))
    return ctitle, pre, parts

def plain(s):
    s = replace_macro(s, 'texorpdfstring', 'mm', lambda a, b: b)
    s = s.replace('\\ ', ' ').replace('~', ' ')
    s = re.sub(r'\\[a-zA-Z]+\*?', '', s)
    return s.replace('{', '').replace('}', '').replace('$', '').strip()

def main():
    sol = load_solutions()
    print('løsningsforslag:', len(sol))
    if SEC_DIR.exists():
        for p in SEC_DIR.glob('*'):
            if p.is_dir() and p.name not in ('figurer',):
                shutil.rmtree(p)
            elif p.suffix == '.qmd':
                p.unlink()
    SEC_DIR.mkdir(parents=True, exist_ok=True)
    toc = []
    for ci, (fname, short, status) in enumerate(CHAPTERS, 1):
        raw = strip_comments(read(SRC / 'files' / fname))
        raw = inline_inputs(raw)
        ctitle, pre, sections = split_sections(raw)
        ctitle_p = plain(ctitle)
        cdir = SEC_DIR / f'{ci:02d}-{short}'
        cdir.mkdir(parents=True, exist_ok=True)
        conv = Conv(f'k{ci}', sol)
        exm_counter = [0, ci]
        entry = {'nr': ci, 'tittel': ctitle_p, 'dir': cdir.name, 'status': status, 'sider': []}
        # chapter page
        pre_c = conv.convert(pre)
        md_pre = post(pandoc_code_unprotect(pandoc(pandoc_code_protect(pre_c))), exm_counter)
        chap_q = f'---\ntitle: "Kapittel {ci}: {esc(ctitle_p)}"\ntoc: false\n---\n\n'
        if status != 'klar':
            chap_q += '::: {.callout-warning title="Under arbeid"}\nDette kapittelet skrives fortsatt. Innholdet kan endre seg.\n:::\n\n'
        chap_q += md_pre + '\n\n## Innhold\n\n'
        for si, (stitle, body) in enumerate(sections, 1):
            st = plain(stitle)
            fn = f'{si:02d}-{slug(st)}.qmd'
            c = conv.convert(body)
            md = post(pandoc_code_unprotect(pandoc(pandoc_code_protect(c))), exm_counter)
            md = re.sub(r'^(#+) ', lambda m: '#' * (len(m.group(1)) + 1) + ' ', md, flags=re.M) if md.lstrip().startswith('# ') else md
            n_opp = md.count('{.oppgave ')
            head = f'---\ntitle: "{ci}.{si} {esc(st)}"\nsubtitle: "Kapittel {ci}: {esc(ctitle_p)}"\n---\n\n'
            if status != 'klar':
                head += '::: {.callout-warning title="Under arbeid"}\nDette kapittelet skrives fortsatt.\n:::\n\n'
            extra = Path(__file__).parent / 'tillegg' / cdir.name / fn.replace('.qmd', '.md')
            if extra.exists():
                md += '\n\n' + extra.read_text(encoding='utf-8')
            (cdir / fn).write_text(head + ':::: {.oppgaver}\n\n' + md + '\n\n::::\n', encoding='utf-8')
            entry['sider'].append({'fil': fn, 'tittel': f'{ci}.{si} {st}', 'oppgaver': n_opp})
            chap_q += f'- [{ci}.{si} {st}]({fn})' + (f' · {n_opp} oppgaver' if n_opp else '') + '\n'
        (cdir / 'index.qmd').write_text(chap_q, encoding='utf-8')
        entry['videoer'] = conv.videos
        entry['figurer'] = conv.fig
        toc.append(entry)
        print(f'kap {ci} {ctitle_p}: {len(sections)} sider, {conv.fig} figurer, {conv.videos} videoer')
    (SEC_DIR / '_innhold.json').write_text(json.dumps(toc, ensure_ascii=False, indent=1), encoding='utf-8')
    print('feilede figurer:', len(FAILED))
    for f in FAILED[:30]:
        print('  ', f)
    print('manglende bilder:', len(MISSING), MISSING[:10])

if __name__ == '__main__':
    main()
