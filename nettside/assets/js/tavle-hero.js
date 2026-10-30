// Krittegning på forsiden: kjelke dratt med kraften F i vinkel θ, med komponenter og forflytning.
(function () {
  var cv = document.getElementById('tavle-hero');
  if (!cv) return;
  var c = cv.getContext('2d');
  var C = { chalk: '#ecefe6', neon: '#6ef04a', orange: '#f19c2c', cyan: '#56d7b8', yellow: '#eee462' };
  function chalk(w, color) { c.lineWidth = w; c.strokeStyle = color; c.lineCap = 'round'; c.lineJoin = 'round'; c.shadowColor = color; c.shadowBlur = 2; }
  function line(x1, y1, x2, y2) {
    var n = 14; c.beginPath(); c.moveTo(x1, y1);
    for (var i = 1; i <= n; i++) { var t = i / n; c.lineTo(x1 + (x2 - x1) * t + Math.sin(i * 2.3) * 0.8, y1 + (y2 - y1) * t + Math.cos(i * 1.7) * 0.8); }
    c.stroke();
  }
  function arrow(x1, y1, x2, y2, head) {
    line(x1, y1, x2, y2);
    var a = Math.atan2(y2 - y1, x2 - x1);
    c.beginPath(); c.moveTo(x2 - head * Math.cos(a - 0.45), y2 - head * Math.sin(a - 0.45)); c.lineTo(x2, y2);
    c.lineTo(x2 - head * Math.cos(a + 0.45), y2 - head * Math.sin(a + 0.45)); c.stroke();
  }
  function dashed(fn) { c.setLineDash([10, 9]); fn(); c.setLineDash([]); }
  function label(t, x, y, color, size) { c.shadowBlur = 0; c.fillStyle = color; c.font = (size || 26) + 'px "Architects Daughter", cursive'; c.fillText(t, x, y); }
  function draw() {
    c.clearRect(0, 0, cv.width, cv.height);
    var ox = 200, oy = 300, L = 230, th = 30 * Math.PI / 180;
    chalk(2.5, C.chalk); line(20, 330, 620, 330);
    c.beginPath(); c.moveTo(40, 300); c.lineTo(180, 300); c.quadraticCurveTo(205, 302, 200, 318); c.quadraticCurveTo(190, 330, 168, 330); c.lineTo(42, 330); c.closePath(); c.stroke();
    chalk(5, C.orange); arrow(ox, oy, 590, oy, 18); label('s', 520, 280, C.orange, 30);
    var fx = ox + L * Math.cos(th), fy = oy - L * Math.sin(th);
    chalk(3, C.cyan);
    dashed(function () { arrow(ox, oy + 2, fx, oy + 2, 14); });
    dashed(function () { arrow(fx, oy, fx, fy + 6, 14); });
    chalk(6, C.neon); arrow(ox, oy, fx, fy, 20); label('F', fx - 40, fy - 6, C.neon, 30);
    label('Fx', ox + 80, oy + 26, C.cyan, 22); label('Fy', fx + 10, oy - 50, C.cyan, 22);
    chalk(2.5, C.yellow); c.beginPath(); c.arc(ox, oy, 52, -th, 0); c.stroke();
    label('θ', ox + 60, oy - 10, C.yellow, 24);
    label('A', ox - 6, 360, C.yellow, 20); label('B', 590, 360, C.yellow, 20);
  }
  draw();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw);
})();
