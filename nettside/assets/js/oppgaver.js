// Oppgaver: «Vis løsning» og «Få et hint» (KI-hint via hint-tjeneren).
// Bruk i en .qmd-fil:
//   ::: {.oppgave niva="Middels"}
//   Oppgavetekst …
//   ::: {.losning}
//   Løsning …
//   :::
//   :::
(function () {
  var meta = document.querySelector('meta[name="fysikkhjelp-hint-api"]');
  var API = meta ? meta.getAttribute('content') : '';
  var MAX_HINT = 3;
  var emne = ((document.querySelector('h1.title') || {}).textContent || document.title) + ' – ' + ((document.querySelector('.subtitle') || {}).textContent || '');

  document.querySelectorAll('div.oppgave').forEach(function (opp, i) {
    var los = opp.querySelector(':scope > .losning');
    var niva = opp.getAttribute('data-niva') || opp.getAttribute('niva') || '';
    var tittel = opp.getAttribute('data-tittel') || opp.getAttribute('tittel') || '';
    var tEl = opp.querySelector(':scope > p > .oppg-tittel, :scope > .oppg-tittel'); if (tEl) { var par = tEl.closest('p'); (par && par.parentNode === opp && par.textContent.trim() === tEl.textContent.trim() ? par : tEl).remove(); }

    // Oppgaveteksten = alt utenom løsningen
    var tekstDeler = [];
    Array.prototype.forEach.call(opp.children, function (ch) { if (ch !== los) tekstDeler.push(ch.textContent.trim()); });
    var oppgavetekst = (tittel ? tittel + '\n' : '') + tekstDeler.join('\n');
    var losningstekst = los ? los.textContent.trim() : '';

    var hode = document.createElement('div');
    hode.className = 'oppg-hode';
    hode.innerHTML = '<span class="nr">Oppgave</span>' + (tittel ? '<span class="tt"></span>' : '') + (niva ? '<span class="niva"></span>' : '');
    if (tittel) hode.querySelector('.tt').textContent = tittel;
    if (niva) hode.querySelector('.niva').textContent = niva;
    opp.insertBefore(hode, opp.firstChild);

    var verktoy = document.createElement('div');
    verktoy.className = 'oppg-verktoy';
    verktoy.innerHTML = '<button type="button" class="hint" aria-expanded="false">Få et hint</button>' +
                        (los ? '<button type="button" class="vis" aria-expanded="false">Vis løsning</button>' : '');
    var panel = document.createElement('div');
    panel.className = 'hint-panel'; panel.hidden = true;
    var id = 'forsok-' + (i + 1);
    panel.innerHTML = '<label for="' + id + '">Hva har du prøvd så langt? (valgfritt)</label>' +
      '<textarea id="' + id + '" placeholder="For eksempel: Jeg ganget 50 med 20 og fikk 1000 J, men fasiten er annerledes."></textarea>' +
      '<div><button type="button" class="hint send">Send og få hint</button></div>' +
      '<div class="hint-liste" aria-live="polite"></div>';
    if (los) { los.hidden = true; opp.insertBefore(verktoy, los); opp.insertBefore(panel, los); }
    else { opp.appendChild(verktoy); opp.appendChild(panel); }

    var visBtn = verktoy.querySelector('.vis');
    if (visBtn) visBtn.addEventListener('click', function () {
      los.hidden = !los.hidden;
      visBtn.textContent = los.hidden ? 'Vis løsning' : 'Skjul løsning';
      visBtn.setAttribute('aria-expanded', String(!los.hidden));
      if (!los.hidden && window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise([los]);
    });

    var hintBtn = verktoy.querySelector('.hint');
    hintBtn.addEventListener('click', function () {
      panel.hidden = !panel.hidden;
      hintBtn.setAttribute('aria-expanded', String(!panel.hidden));
      if (!panel.hidden) panel.querySelector('textarea').focus();
    });

    var liste = panel.querySelector('.hint-liste');
    var send = panel.querySelector('.send');
    var tidligere = [];
    send.addEventListener('click', function () {
      if (tidligere.length >= MAX_HINT) { vis('Du har fått tre hint på denne oppgaven. Prøv litt selv, eller se på løsningen.', true); return; }
      if (!API || API.indexOf('DITTNAVN') >= 0) { vis('Hint-tjenesten er ikke satt opp ennå.', true); return; }
      send.disabled = true; send.textContent = 'Tenker …';
      fetch(API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          emne: emne.trim(),
          oppgave: oppgavetekst,
          losning: losningstekst,
          forsok: panel.querySelector('textarea').value.slice(0, 1500),
          tidligereHint: tidligere
        })
      }).then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok) throw new Error(j.feil || 'Hint-tjenesten svarte ikke (' + r.status + ').');
          return j;
        });
      }).then(function (j) {
        tidligere.push(j.hint);
        vis(j.hint, false, tidligere.length);
      }).catch(function (e) {
        vis(e instanceof TypeError ? 'Fikk ikke kontakt med hint-tjenesten. Prøv igjen om litt.' : (e.message || 'Noe gikk galt. Prøv igjen om litt.'), true);
      }).finally(function () {
        send.disabled = false;
        send.textContent = tidligere.length ? 'Gi meg et hint til' : 'Send og få hint';
      });
    });
    function vis(tekst, feil, n) {
      var d = document.createElement('div');
      d.className = 'hint-svar' + (feil ? ' feil' : '');
      var t = document.createElement('div'); t.className = 'hint-tittel'; t.textContent = feil ? 'Obs' : 'Hint ' + n;
      var p = document.createElement('div'); p.textContent = tekst;
      d.appendChild(t); d.appendChild(p); liste.appendChild(d);
      if (window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise([d]);
    }
  });
})();
