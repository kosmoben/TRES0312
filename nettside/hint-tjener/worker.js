// Hint-tjener for fysikkhjelp.no (Cloudflare Worker).
// Tar imot en oppgave fra nettsiden, spør Claude om ETT hint, og sender hintet tilbake.
// API-nøkkelen ligger som hemmelighet i Cloudflare og vises aldri på nettsiden.
//
// VALG AV KI-LEVERANDØR (innstillinger på workeren i Cloudflare, ingen kodeendring):
//   LEVERANDOR = "claude"  (standard)  -> hemmelighet ANTHROPIC_API_KEY
//   LEVERANDOR = "openai"              -> hemmelighet KI_API_KEY, og variabelen KI_URL
//        KI_URL = adressen til en tjeneste med OpenAI-format, f.eks. NTNU sin GPT-server:
//                 "https://gpt.ntnu.no/api/models/chat-completion"  (MODELL = "gpt-oss-120b")
//   MODELL = navnet på modellen (valgfritt). Standard: "claude-haiku-5-5" for Claude.

const STANDARD_MODELL = { claude: "claude-haiku-5-5", openai: "gpt-4o-mini" };
const TILLATTE_OPPRINNELSER = [
  "https://fysikkhjelp.no",
  "https://www.fysikkhjelp.no",
  "https://www.bendavidnormann.com",    // test på Squarespace-siden
  "https://bendavidnormann.com",
  "http://localhost:4200",              // quarto preview
];

const SYSTEM = `Du er en tålmodig fysikklærer på fysikkhjelp.no, laget av Dr. Normann, for studenter på forkurs for ingeniør- og realfag.
Studenten jobber med en oppgave og ber om et hint.

Regler:
- Gi ETT kort hint (2–4 setninger) på norsk bokmål. Aldri hele løsningen, aldri det endelige tallsvaret.
- Bygg videre på tidligere hint: hvert nytt hint skal være litt mer konkret enn det forrige.
- Har studenten skrevet hva hen har prøvd, ta utgangspunkt i det. Pek på den konkrete feilen eller neste steg, og si gjerne hva som var riktig.
- Still gjerne et ledende spørsmål i stedet for å fortelle svaret.
- Løsningsforslaget du får er bare til hjelp for deg. Ikke siter det.
- Skriv matematikk med \\( ... \\) rundt, for eksempel \\( W = F s \\cos\\theta \\). Ikke bruk Markdown, overskrifter eller lister.
- Spør studenten om noe som ikke handler om oppgaven, svar kort at du bare hjelper med oppgaven.`;

function cors(origin) {
  const ok = TILLATTE_OPPRINNELSER.includes(origin);
  return {
    "Access-Control-Allow-Origin": ok ? origin : TILLATTE_OPPRINNELSER[0],
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Vary": "Origin",
  };
}
const json = (data, status, headers) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json; charset=utf-8", ...headers } });
const kort = (s, n) => String(s || "").slice(0, n);

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const h = cors(origin);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: h });
    if (request.method !== "POST") return json({ feil: "Bruk POST." }, 405, h);
    if (!TILLATTE_OPPRINNELSER.includes(origin)) return json({ feil: "Ikke tillatt." }, 403, h);

    // Enkel begrensning: maks 30 hint per IP-adresse per time (krever KV-bindingen HINT_KV, valgfritt).
    if (env.HINT_KV) {
      const ip = request.headers.get("CF-Connecting-IP") || "ukjent";
      const nokkel = `rate:${ip}:${new Date().toISOString().slice(0, 13)}`;
      const n = parseInt((await env.HINT_KV.get(nokkel)) || "0", 10);
      if (n >= 30) return json({ feil: "Du har bedt om mange hint den siste timen. Prøv igjen litt senere." }, 429, h);
      await env.HINT_KV.put(nokkel, String(n + 1), { expirationTtl: 3700 });
    }

    let b;
    try { b = await request.json(); } catch { return json({ feil: "Ugyldig forespørsel." }, 400, h); }
    const tidligere = Array.isArray(b.tidligereHint) ? b.tidligereHint.slice(-3).map((x) => kort(x, 600)) : [];

    const melding =
      `Emne: ${kort(b.emne, 120)}\n\n` +
      `Oppgave:\n${kort(b.oppgave, 2000)}\n\n` +
      `Løsningsforslag (bare for deg, ikke vis det):\n${kort(b.losning, 2500)}\n\n` +
      (tidligere.length ? `Hint studenten allerede har fått:\n${tidligere.map((t, i) => `${i + 1}. ${t}`).join("\n")}\n\n` : "") +
      `Dette har studenten prøvd:\n${kort(b.forsok, 1500) || "(ingenting skrevet)"}\n\n` +
      `Gi neste hint.`;

    let hint;
    try {
      hint = await spor(env, melding);
    } catch (e) {
      return json({ feil: "Hint-tjenesten er midlertidig utilgjengelig. Prøv igjen om litt." }, 502, h);
    }
    return json({ hint: hint || "Prøv å tegne opp kreftene og forflytningen først. Hvilken del av kraften peker langs bevegelsen?" }, 200, h);
  },
};

// Spør valgt KI-leverandør og returner teksten.
async function spor(env, melding) {
  const lev = (env.LEVERANDOR || "claude").toLowerCase();
  const modell = env.MODELL || STANDARD_MODELL[lev] || STANDARD_MODELL.claude;
  if (lev === "openai") {
    const r = await fetch(env.KI_URL, {
      method: "POST",
      headers: { "Authorization": `Bearer ${env.KI_API_KEY}`, "content-type": "application/json" },
      body: JSON.stringify({
        model: modell, max_tokens: 350,
        messages: [{ role: "system", content: SYSTEM }, { role: "user", content: melding }],
      }),
    });
    if (!r.ok) throw new Error("KI " + r.status);
    const d = await r.json();
    // OpenAI-format, med reserve for varianter (f.eks. NTNU sin chat-completion)
    const c = (d.choices || [])[0];
    const t = c?.message?.content ?? c?.text ?? d.message?.content ?? d.content ?? d.response ?? "";
    return (typeof t === "string" ? t : JSON.stringify(t)).trim();
  }
  const r = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "x-api-key": env.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json" },
    body: JSON.stringify({ model: modell, max_tokens: 350, system: SYSTEM, messages: [{ role: "user", content: melding }] }),
  });
  if (!r.ok) throw new Error("KI " + r.status);
  const d = await r.json();
  return (d.content || []).filter((c) => c.type === "text").map((c) => c.text).join("\n").trim();
}
