// Kjørbar Python i nettleseren (Pyodide).
// Bruk i en .qmd-fil:   ```{.python .kjor}
//                        print("hei")
//                        ```
(function () {
  var PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js';
  var blocks = [];
  document.querySelectorAll('pre.kjor, div.sourceCode.kjor').forEach(function (el) {
    var outer = el.closest('div.sourceCode') || el;
    if (blocks.indexOf(outer) < 0) blocks.push(outer);
  });
  if (!blocks.length) return;

  var pyPromise = null;
  function loadPy() {
    if (pyPromise) return pyPromise;
    pyPromise = new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = PYODIDE;
      s.onload = function () { window.loadPyodide().then(resolve, reject); };
      s.onerror = function () { reject(new Error('Fikk ikke lastet Python. Sjekk nettforbindelsen og prøv igjen.')); };
      document.head.appendChild(s);
    });
    return pyPromise;
  }

  // Kjøres etter brukerkoden: henter matplotlib-figurer ut som PNG.
  var GRAB_FIGS = [
    'import sys',
    '_figs = []',
    'if "matplotlib" in sys.modules:',
    '    import io, base64',
    '    import matplotlib.pyplot as _plt',
    '    for _n in _plt.get_fignums():',
    '        _b = io.BytesIO(); _plt.figure(_n).savefig(_b, format="png", dpi=110)',
    '        _figs.append(base64.b64encode(_b.getvalue()).decode())',
    '    _plt.close("all")',
    '_figs'
  ].join('\n');

  blocks.forEach(function (blk, i) {
    var pre = blk.tagName === 'PRE' ? blk : blk.querySelector('pre');
    var code = pre && pre.querySelector('code');
    var original = (code || pre || blk).textContent.replace(/\s+$/, '');
    var box = document.createElement('div');
    box.className = 'kode-boks';
    box.innerHTML =
      '<div class="kode-topp"><span>Python · kan redigeres</span><span class="kode-knapper">' +
      '<button type="button" class="tilbake">Tilbakestill</button>' +
      '<button type="button" class="kjor">▶ Kjør</button></span></div>' +
      '<textarea spellcheck="false" aria-label="Python-kode"></textarea>' +
      '<div class="kode-ut" aria-live="polite"></div>';
    var ta = box.querySelector('textarea');
    var out = box.querySelector('.kode-ut');
    var run = box.querySelector('.kjor');
    ta.id = 'kode-' + (i + 1);
    ta.value = original;
    function fit() { ta.style.height = 'auto'; ta.style.height = (ta.scrollHeight + 4) + 'px'; }
    ta.addEventListener('input', fit);
    ta.addEventListener('keydown', function (e) {
      if (e.key === 'Tab') { e.preventDefault(); var p = ta.selectionStart; ta.setRangeText('    ', p, ta.selectionEnd, 'end'); }
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); run.click(); }
    });
    box.querySelector('.tilbake').addEventListener('click', function () { ta.value = original; out.textContent = ''; fit(); });

    run.addEventListener('click', function () {
      run.disabled = true;
      out.textContent = pyPromise ? 'Kjører …' : 'Laster Python første gang (tar noen sekunder) …';
      var lines = [];
      loadPy().then(function (py) {
        py.setStdout({ batched: function (s) { lines.push(s); } });
        py.setStderr({ batched: function (s) { lines.push(s); } });
        return py.loadPackagesFromImports(ta.value).then(function () {
          return py.runPythonAsync(ta.value);
        }).then(function () {
          return py.runPythonAsync(GRAB_FIGS);
        }).then(function (figs) {
          out.textContent = lines.join('\n');
          var list = figs && figs.toJs ? figs.toJs() : [];
          list.forEach(function (b64) {
            var img = document.createElement('img'); img.alt = 'Figur fra koden'; img.src = 'data:image/png;base64,' + b64; out.appendChild(img);
          });
          if (!lines.length && !list.length) out.textContent = '(Koden kjørte uten utskrift.)';
        });
      }).catch(function (err) {
        out.textContent = lines.join('\n');
        var e = document.createElement('div'); e.className = 'feil';
        var msg = String(err && err.message || err);
        var last = msg.trim().split('\n').slice(-1)[0];
        e.textContent = (lines.length ? '\n' : '') + 'Feil: ' + last;
        out.appendChild(e);
      }).finally(function () { run.disabled = false; });
    });

    blk.replaceWith(box);
    fit();
  });
})();
