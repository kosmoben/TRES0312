import sys, io

path = sys.argv[1]
with io.open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_slide10 = """%--------------------------------------------------------------------------
%  SLIDE 10 \u2014 Aktivitet: Kraft og motkraft i tre tilfeller
%--------------------------------------------------------------------------
\\begin{frame}{Aktivitet}

  \\aktivitet{Kraft og motkraft}{%
  Hva er motkrafta i hvert av de tre tilfellene under?
  }

  \\vspace{4pt}
  \\begin{center}
  \\begin{minipage}[t]{0.30\\textwidth}
    \\centering
    \\includegraphics[height=1.9cm,keepaspectratio]{Images/motkraft_boff_enkraft.png}

    \\onslide<2->{\\includegraphics[height=1.9cm,keepaspectratio]{Images/motkraft_boff_kraftpar.png}}

    {\\footnotesize Tilfelle 1}
  \\end{minipage}%
  \\hfill
  \\begin{minipage}[t]{0.30\\textwidth}
    \\centering
    \\includegraphics[height=1.9cm,keepaspectratio]{Images/motkraft_hallo_enkraft.png}

    \\onslide<2->{\\includegraphics[height=1.9cm,keepaspectratio]{Images/motkraft_hallo_kraftpar.png}}

    {\\footnotesize Tilfelle 2}
  \\end{minipage}%
  \\hfill
  \\begin{minipage}[t]{0.30\\textwidth}
    \\centering
    \\includegraphics[height=1.9cm,keepaspectratio]{Images/motkraft_rakett_enkraft.png}

    \\onslide<2->{\\includegraphics[height=1.9cm,keepaspectratio]{Images/motkraft_rakett_kraftpar.png}}

    {\\footnotesize Tilfelle 3}
  \\end{minipage}
  \\end{center}
  \\pause

\\end{frame}

%--------------------------------------------------------------------------
%  SLIDE 11 \u2014 Newtons 2. lov: kraft som endring av bevegelse
%--------------------------------------------------------------------------"""

assert old_slide10 in content, "old_slide10 block not found!"

new_block = """%--------------------------------------------------------------------------
%  SLIDE 10 \u2014 Aktivitet: Kraft og motkraft i tre tilfeller
%--------------------------------------------------------------------------
\\begin{frame}{Hva er motkrafta i hvert av de tre tilfellene?}

  \\vspace{4pt}
  \\begin{center}
  \\begin{minipage}[t]{0.30\\textwidth}
    \\centering
    \\onslide<1->{\\includegraphics[height=3.1cm,keepaspectratio]{Images/motkraft_boff_enkraft.png}}

    \\onslide<2->{\\includegraphics[height=3.1cm,keepaspectratio]{Images/motkraft_boff_kraftpar.png}}

    {\\footnotesize Tilfelle 1}
  \\end{minipage}%
  \\hfill
  \\begin{minipage}[t]{0.30\\textwidth}
    \\centering
    \\onslide<3->{\\includegraphics[height=3.1cm,keepaspectratio]{Images/motkraft_hallo_enkraft.png}}

    \\onslide<4->{\\includegraphics[height=3.1cm,keepaspectratio]{Images/motkraft_hallo_kraftpar.png}}

    {\\footnotesize Tilfelle 2}
  \\end{minipage}%
  \\hfill
  \\begin{minipage}[t]{0.30\\textwidth}
    \\centering
    \\onslide<5->{\\includegraphics[height=3.1cm,keepaspectratio]{Images/motkraft_rakett_enkraft.png}}

    \\onslide<6->{\\includegraphics[height=3.1cm,keepaspectratio]{Images/motkraft_rakett_kraftpar.png}}

    {\\footnotesize Tilfelle 3}
  \\end{minipage}
  \\end{center}

\\end{frame}

%--------------------------------------------------------------------------
%  SLIDE 11 \u2014 Hvordan tegne krefter
%--------------------------------------------------------------------------
\\begin{frame}{Hvordan tegne krefter}

  \\begin{center}
  \\only<1>{\\includegraphics[height=6.4cm,keepaspectratio]{Images/krefter_buss.png}}%
  \\only<2>{\\includegraphics[height=6.4cm,keepaspectratio]{Images/krefter_boks.png}}%
  \\only<3>{\\includegraphics[height=6.4cm,keepaspectratio]{Images/krefter_boks_krefter.png}}%
  \\end{center}

\\end{frame}

%--------------------------------------------------------------------------
%  SLIDE 12 \u2014 Aktivitet: Akselerasjon av et skip
%--------------------------------------------------------------------------
\\begin{frame}{Aktivitet}

  \\aktivitet{Akselerasjon av et skip}{%
  Et skip beveger seg rettlinjet og er p\u00e5virket av en motorkraft $F_m = 500\\,\\mathrm{kN}$ framover og en motstandskraft fra b\u00f8lgene $F_b = 100\\,\\mathrm{kN}$ bakover. Skipets masse er $m = 2000\\,\\mathrm{tonn}$.
  \\begin{enumerate}[a)]
      \\item Finn resultantkraften p\u00e5 skipet.
      \\item Beregn skipets akselerasjon $a$.
  \\end{enumerate}
  }

\\end{frame}

%--------------------------------------------------------------------------
%  SLIDE 13 \u2014 Newtons 2. lov: kraft som endring av bevegelse
%--------------------------------------------------------------------------"""

content = content.replace(old_slide10, new_block)

content = content.replace(
    "%  SLIDE 12 \u2014 Newtons 1. lov: krefter og treghet",
    "%  SLIDE 14 \u2014 Newtons 1. lov: krefter og treghet")
content = content.replace(
    "%  SLIDE 13 \u2014 Oppsummering: Newtons tre lover",
    "%  SLIDE 15 \u2014 Oppsummering: Newtons tre lover")
content = content.replace(
    "%  SLIDE 14 \u2014 Neste gang",
    "%  SLIDE 16 \u2014 Neste gang")

with io.open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("OK, patched.")
