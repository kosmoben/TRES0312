#!/usr/bin/env python3
"""Lager forkurs/index.qmd og sidemenyen i _quarto.yml ut fra forkurs/_innhold.json.
Bruk: python3 meny.py <quarto-prosjektmappe>"""
import json, re, sys
from pathlib import Path

P = Path(sys.argv[1])
toc = json.loads((P / 'forkurs' / '_innhold.json').read_text(encoding='utf-8'))

# ---- oversiktsside
q = ['---', 'title: "Forkurs (TRES0312)"',
     'subtitle: "Fysikk for deg som ikke har hatt mye matematikk eller fysikk før. Video, forklaring, eksempler og oppgaver med løsning og hint."',
     'toc: false', 'page-layout: full', '---', '']
klare = [c for c in toc if c['status'] == 'klar']
n_opp_tot = sum(s['oppgaver'] for c in toc for s in c['sider'])
n_vid_tot = sum(c.get('videoer', 0) for c in toc)
q += ['```{=html}', f'<p class="forkurs-tall">→ {len(klare)} ferdige kapitler, {n_opp_tot} oppgaver, {n_vid_tot} videoer</p>', '<div class="kapitler">']
for c in toc:
    live = c['status'] == 'klar'
    n_opp = sum(s['oppgaver'] for s in c['sider'])
    meta = []
    if c.get('videoer'): meta.append(f"{c['videoer']} videoer")
    if n_opp: meta.append(f"{n_opp} oppgaver")
    q.append(f'<div class="kapittel{"" if live else " arbeid"}">')
    q.append(f'  <a class="kap-hode" href="{c["dir"]}/index.html"><span class="kap-nr">{c["nr"]}</span><span class="kap-navn">{c["tittel"]}</span>'
             + ('' if live else '<em class="pill off">under arbeid</em>') + '</a>')
    if meta: q.append(f'  <p class="kap-meta">{" · ".join(meta)}</p>')
    q.append('  <ul>')
    for s in c['sider']:
        t = re.sub(r'^\d+\.\d+\s+', '', s['tittel'])
        q.append(f'    <li><a href="{c["dir"]}/{s["fil"].replace(".qmd", ".html")}">{t}</a></li>')
    q.append('  </ul>\n</div>')
q += ['</div>', '```', '']
(P / 'forkurs' / 'index.qmd').write_text('\n'.join(q), encoding='utf-8')

# ---- sidemeny
lines = ['  sidebar:', '    - id: forkurs', '      title: "Forkurs (TRES)"', '      style: docked', '      collapse-level: 1',
         '      contents:', '        - forkurs/index.qmd']
for c in toc:
    lines.append(f'        - section: "{c["nr"]}. {c["tittel"]}"')
    lines.append(f'          href: forkurs/{c["dir"]}/index.qmd')
    lines.append('          contents:')
    for s in c['sider']:
        lines.append(f'            - forkurs/{c["dir"]}/{s["fil"]}')
yml = (P / '_quarto.yml').read_text(encoding='utf-8')
yml = re.sub(r'  sidebar:\n(?:    .*\n|      .*\n)*', '\n'.join(lines) + '\n', yml, count=1)
(P / '_quarto.yml').write_text(yml, encoding='utf-8')
print('meny:', len(toc), 'kapitler')
