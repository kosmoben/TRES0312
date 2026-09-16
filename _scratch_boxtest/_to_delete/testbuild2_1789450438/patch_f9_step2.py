import sys, io

path = sys.argv[1]
with io.open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Insert new activity slide (terminalfart + lampe) between the
# Newtons-1.-lov theory frame's \end{frame} and the Oppsummering header,
# and rename Oppsummering -> SLIDE 16, Neste gang -> SLIDE 17.
anchor = """\\end{frame}

%--------------------------------------------------------------------------
%  SLIDE 15 — Oppsummering: Newtons tre lover
%--------------------------------------------------------------------------"""
assert anchor in content, "anchor not found"

replacement = """\\end{frame}

%--------------------------------------------------------------------------
%  SLIDE 15 — Aktivitet: Newtons 1. lov (terminalfart og lampe)
%--------------------------------------------------------------------------
\\begin{frame}{Aktivitet}

  \\aktivitet{Terminalfart}{%
  En stein har nådd terminalfart på vei ned mot bakken. På steinen virker tyngdekraften $G = 6\\,\\mathrm{N}$ (nedover) og luftmotstanden $R = 6\\,\\mathrm{N}$ (oppover).

  Akselererer steinen? Begrunn svaret.
  }

  \\pause
  \\aktivitet{Lampa i taket}{%
  På ei lampe som henger i ro virker tyngdekraften (nedover) og snorkraften (oppover). Tyngdekraften er $G = 10\\,\\mathrm{N}$.
  \\begin{enumerate}[a)]
      \\item Tegn inn kreftene som virker på lampa.
      \\item Hva er snorkrafta?
      \\item Er snorkrafta motkrafta til $G$?
  \\end{enumerate}
  }

\\end{frame}

%--------------------------------------------------------------------------
%  SLIDE 16 — Oppsummering: Newtons tre lover
%--------------------------------------------------------------------------"""

content = content.replace(anchor, replacement)

old_h2 = "%  SLIDE 16 — Neste gang"
new_h2 = "%  SLIDE 17 — Neste gang"
assert old_h2 in content
content = content.replace(old_h2, new_h2)

with io.open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("OK step2 patched.")
