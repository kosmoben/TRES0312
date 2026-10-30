# fysikkhjelp.no

Nettsiden lages automatisk fra kompendiet. Du skriver i LaTeX som før, pusher til GitHub, og et par minutter senere er fysikkhjelp.no oppdatert.

## 1. Vanlig arbeidsflyt

1. Skriv i `TRES0312_Kompendium/` i VS Code, som før.
2. Commit og push til `main`.
3. GitHub bygger og publiserer siden (fanen **Actions** på GitHub viser fremdriften; grønn hake = ute på nett, rødt kryss = noe feilet, og du får e-post).

YouTube-lenker legger du inn i kompendiet som før. De blir innebygde videoer på nettsiden.

## 2. Forhåndsvise på egen maskin (valgfritt)

Krever Quarto, Python 3, LaTeX (MacTeX) og `pdftocairo` (`brew install poppler`). I terminalen i VS Code, fra repo-mappen:

```
./nettside/bygg.sh preview
```

Siden åpnes på `http://localhost:4200`. Første gang tar det noen minutter (figurene tegnes), deretter går det raskt. Endrer du `.tex`-filene, kjør kommandoen på nytt.

## 3. Mappene

| Fil / mappe | Hva det er |
|---|---|
| `bygg.sh` | Gjør om kompendiet og bygger siden (brukes både lokalt og av GitHub) |
| `_quarto.yml` | Innstillinger: meny, tema, adressen til hint-tjeneren (sidemenyen lages automatisk) |
| `index.qmd` | Forsiden |
| `assets/` | Utseende (`tavle.scss`), kjørbar Python (`js/kode.js`), oppgaver og hint (`js/oppgaver.js`), bilder |
| `verktoy/convert.py` | Konverterer LaTeX til nettsider |
| `verktoy/tillegg/` | Ekstra innhold som ikke står i kompendiet, f.eks. kjørbar Python: `tillegg/<kapittelmappe>/<side>.md` |
| `hint-tjener/` | Tjeneren som henter KI-hint |
| `wrangler.toml` | Opplasting til Cloudflare |
| `forkurs/`, `_site/` | Lages automatisk – ikke rediger, og de lagres ikke i git |

## 4. Om konverteringen

- Hvert kapittel blir én mappe, og hver `\section` én side.
- `\defn`, `\exm`, `\svar`, `\merk`, `\tips`, `\oppsum`, `\tanke`, `\spm`, `\graabox` blir bokser.
- `\oppgaver{...}` får løsningsforslaget fra `files_losning/` og hint-knapp.
- TikZ-figurer tegnes om og vises som kritt på tavla.
- Kapittel 8 og 9 er merket «under arbeid». Endre `status` i `CHAPTERS` øverst i `verktoy/convert.py` når de er ferdige.

Kjørbar Python i en tilleggsfil:

````
```{.python .kjor}
print("Hei")
```
````

## 5. KI-hint

Hintene går via en liten tjener på Cloudflare, slik at API-nøkkelen aldri ligger på nettsiden. Instruksen til KI-en står øverst i `hint-tjener/worker.js`. Leverandør velges med innstillinger på tjeneren i Cloudflare:

- Claude: `ANTHROPIC_API_KEY` (hemmelighet)
- NTNU GPT eller annen tjeneste i OpenAI-format: `LEVERANDOR=openai`, `KI_URL=https://gpt.ntnu.no/api/models/chat-completion`, `MODELL=gpt-oss-120b`, og hemmeligheten `KI_API_KEY`

## 6. Oppsett av automatikken (gjøres én gang)

GitHub trenger to hemmeligheter (repo → Settings → Secrets and variables → Actions):

- `CLOUDFLARE_ACCOUNT_ID` – står på forsiden av Workers & Pages i Cloudflare
- `CLOUDFLARE_API_TOKEN` – lages i Cloudflare under *My Profile → API Tokens → Create Token → «Edit Cloudflare Workers»*
