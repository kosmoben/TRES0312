#!/usr/bin/env python3
"""Kjør fra mappen TRES0312_Kompendium etter at filene i denne pakken er kopiert inn.
Legger kapittel 7 inn i LosningsforslagTRES0312.tex og oppgaver_manifest.json."""
import json, pathlib
here = pathlib.Path('.')
lf = here/'LosningsforslagTRES0312.tex'
s = lf.read_text(encoding='utf-8')
linje = r'\subfile{files_losning/0.0.7_Fluidynamikk_LF}'
if linje not in s:
    gammel = r'\subfile{files_losning/0.0.6_Statikk_LF}'
    s = s.replace(gammel, gammel + '\n' + linje)
    lf.write_text(s, encoding='utf-8'); print('La til kapittel 7 i løsningsforslaget')
titler = ["Hvilket metall?","Tegnestift","Vannkanne","Vanntårn","Billøfter på verkstedet",
          "Hydrauliske bremser","Er kronen av gull?","Trekloss som flyter","Lufta i et klasserom",
          "Dykking i sjøen","Sugerør","Vindu i en ubåt","Heliumballong","Olje og vann i et U-rør"]
mf = here/'oppgaver_manifest.json'
data = json.loads(mf.read_text(encoding='utf-8'))
data = [d for d in data if d.get('chapter') != 7]
for i, t in enumerate(titler, 1):
    data.append({"chapter": 7, "number": i, "kind": "oppgave", "title": t,
                 "label": f"k7oppg{i}", "was_labeled": False,
                 "bodyfile": f"Oppgaver/k7_oppg{i:02d}.tex", "sourcefile": "0.0.7_Fluidynamikk.tex"})
mf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('Oppdaterte oppgaver_manifest.json med', len(titler), 'oppgaver')
