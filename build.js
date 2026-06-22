// build.js — kompiler TRES0312 Kompendium
// Kjør med: node build.js
// (latexmk må være installert, f.eks. via MacTeX)

const { spawnSync } = require('child_process');
const path = require('path');

const kompendiumDir = path.join(__dirname, 'TRES0312 Kompendium');

console.log('Kompilerer fra:', kompendiumDir);

const result = spawnSync(
  'latexmk',
  ['-pdf', '-interaction=nonstopmode', 'main.tex'],
  {
    cwd: kompendiumDir,
    stdio: 'inherit',
  }
);

if (result.status !== 0) {
  console.error('Kompilering feilet med kode', result.status);
  process.exit(result.status);
} else {
  console.log('Ferdig! PDF: TRES0312 Kompendium/main.pdf');
}
