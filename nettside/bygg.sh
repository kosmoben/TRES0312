#!/usr/bin/env bash
# Bygger fysikkhjelp.no fra kompendiet.
#   ./nettside/bygg.sh            -> lager ferdig nettside i nettside/_site
#   ./nettside/bygg.sh preview    -> åpner forhåndsvisning i nettleseren (oppdateres når du lagrer .qmd-filer)
# Kjøres automatisk av GitHub (se .github/workflows/nettside.yml) når du pusher til main.
set -euo pipefail
HER="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HER")"
export FIG_CACHE="${FIG_CACHE:-$HER/.figur-cache}"

echo "== Gjør om kompendiet til nettsider"
python3 "$HER/verktoy/convert.py" "$REPO/TRES0312_Kompendium" "$HER"
python3 "$HER/verktoy/meny.py" "$HER"

cd "$HER"
if [ "${1:-}" = "preview" ]; then
  quarto preview --port 4200
else
  echo "== Bygger nettsiden"
  quarto render
  echo "Ferdig: $HER/_site"
fi
