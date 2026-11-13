// Layout builders: each returns a layout (a place, size, colour and opacity for every dot) plus measurements in .m
(function () {
  var F = window.F, W = F.world, FD = window.FD, D = FD.dots, N = FD.n, C = W.C, clamp = F.clamp;
  var L = F.L = {};
  L.lab = function (d) { return d.l ? C.pos : C.neg; };
  // Dot histogram on a log-odds axis: responsive dots stack up from the axis, non-responsive dots stack down.
  // o: key (score field), cy, pitch, cut (log-odds) + pass(d) so no dot is drawn on the wrong side of the cutoff line,
  //    sel(d) (dots left out rest out of focus), col(d), alpha(d), cap/capDn (rows before a column spills sideways)
  L.hist = function (o) {
    var lay = W.lay(), pitch = o.pitch || 13, r = o.r || pitch * 0.4, lo = o.lo == null ? -5.3 : o.lo, hi = o.hi == null ? 4.5 : o.hi;
    var xa = o.x0 == null ? 60 : o.x0, xb = o.x1 == null ? 1020 : o.x1, ncol = Math.floor((xb - xa) / pitch), x0 = xa + ((xb - xa) - ncol * pitch) / 2;
    var band = o.band == null ? 24 : o.band, cy = o.cy, cap = o.cap || 30, capDn = o.capDn || cap, m = o.m || 12;
    var colOf = function (v) { return clamp(Math.floor((v - lo) / (hi - lo) * ncol), 0, ncol - 1); };
    var cb = o.cut == null ? null : clamp(Math.round((o.cut - lo) / (hi - lo) * ncol), 0, ncol);
    var cb2 = o.cut2 == null ? null : clamp(Math.round((o.cut2 - lo) / (hi - lo) * ncol), 0, ncol), p2;
    var h = [new Int16Array(ncol), new Int16Array(ncol)], items = [], i, d, c;
    for (i = 0; i < N; i++) {
      d = D[i]; c = o.col ? o.col(d, i) : L.lab(d); W.col(lay, i, c);
      if (o.sel && !o.sel(d, i)) { W.away(lay, i, o.awayK); continue; }
      items.push({ i: i, v: d[o.key], side: d.l });
    }
    items.sort(function (a, b) { return a.v - b.v || a.i - b.i; });
    items.forEach(function (it) {
      var d = D[it.i], pass = cb == null ? null : o.pass(d), cmin = 0, cmax = ncol - 1;
      if (pass === 1) cmin = cb; else if (pass === 0) cmax = cb - 1;
      if (cb2 != null) { p2 = o.pass2(d); if (p2 === 1) cmin = Math.max(cmin, cb2); else if (p2 === 0) cmax = Math.min(cmax, cb2 - 1); }
      var c0 = clamp(colOf(it.v), cmin, cmax), hh = h[it.side], capS = it.side ? cap : capDn, best = -1, k, c, sg = W.sg[it.i];
      for (k = 0; k <= m && best < 0; k++) {
        c = c0 - sg * k; if (c >= cmin && c <= cmax && hh[c] < capS) { best = c; break; }
        c = c0 + sg * k; if (c >= cmin && c <= cmax && hh[c] < capS) { best = c; break; }
      }
      if (best < 0) { best = c0; for (c = Math.max(cmin, c0 - m); c <= Math.min(cmax, c0 + m); c++) if (hh[c] < hh[best]) best = c; }
      var row = hh[best]++;
      lay.x[it.i] = x0 + (best + 0.5) * pitch; lay.y[it.i] = it.side ? cy - band - (row + 0.5) * pitch : cy + band + (row + 0.5) * pitch;
      lay.r[it.i] = r; lay.a[it.i] = o.alpha ? o.alpha(d, it.i) : 1;
    });
    var mx = function (a) { var q = 0, j; for (j = 0; j < a.length; j++) if (a[j] > q) q = a[j]; return q; };
    lay.m = { x0: x0, x1: x0 + ncol * pitch, cy: cy, band: band, pitch: pitch, r: r, lo: lo, hi: hi, ncol: ncol,
      X: function (v) { return x0 + clamp((v - lo) / (hi - lo), 0, 1) * ncol * pitch; }, cutX: cb == null ? null : x0 + cb * pitch, cutX2: cb2 == null ? null : x0 + cb2 * pitch,
      top: cy - band - mx(h[1]) * pitch, bot: cy + band + mx(h[0]) * pitch, hUp: h[1], hDn: h[0] };
    return lay;
  };
  // take dots from b where sel(d, i) is true, the rest from a
  L.merge = function (a, b, sel) { var o = W.clone(a), i; for (i = 0; i < N; i++) if (sel(D[i], i)) ['x', 'y', 'r', 'a', 'cr', 'cg', 'cb', 'd'].forEach(function (f) { o[f][i] = b[f][i]; }); return o; };
  // the unsorted pile
  L.heap = function () {
    var lay = W.lay(), pitch = 21, ncol = 42, x0 = (F.W - ncol * pitch) / 2, base = 1052, rowH = pitch * 0.9, slots = [], c, rw, scale = 20, tot, hs, it;
    var prof = function (c) { var z = (c - (ncol - 1) / 2) / (ncol * 0.27); return Math.exp(-z * z); };
    for (it = 0; it < 60; it++) { hs = []; tot = 0; for (c = 0; c < ncol; c++) { hs[c] = Math.round(prof(c) * scale); tot += hs[c]; } if (tot === N) break; scale *= 1 + (N - tot) / N * 0.6; }
    for (c = 0; tot < N; c = (c + 5) % ncol) { hs[c]++; tot++; }
    for (c = 0; tot > N; c = (c + 5) % ncol) if (hs[c] > 1) { hs[c]--; tot--; }
    for (c = 0; c < ncol; c++) for (rw = 0; rw < hs[c]; rw++) slots.push({ x: x0 + (c + 0.5) * pitch + (rw % 2 ? pitch * 0.25 : -pitch * 0.25), y: base - (rw + 0.5) * rowH, row: rw });
    var rnd = F.rng(99), i, j, tmp; for (i = slots.length - 1; i > 0; i--) { j = Math.floor(rnd() * (i + 1)); tmp = slots[i]; slots[i] = slots[j]; slots[j] = tmp; }
    var rows = new Float32Array(N);
    for (i = 0; i < N; i++) { lay.x[i] = slots[i].x; lay.y[i] = slots[i].y; lay.r[i] = 8.3; lay.a[i] = 0.92; W.col(lay, i, C.neu); rows[i] = slots[i].row; }
    lay.m = { rows: rows, top: base - Math.max.apply(null, hs) * rowH, base: base };
    return lay;
  };
  // the scoreboard: 13 orbs, one per setup, at (seconds per email, share cleared); orb size = model size
  L.board = function () {
    var lay = W.lay(), bx0 = 190, bx1 = 1000, by0 = 975, by1 = 420, cnt = { '4b': 22, '9b': 36, '27b': 58 }, rad = { '4b': 12, '9b': 15.5, '27b': 21 };
    var X = function (sec) { return bx0 + (Math.log10(sec) + 1) / 2 * (bx1 - bx0); }, Y = function (sh) { return by0 - sh / 100 * (by0 - by1); };
    var pts = {}, i = 0;
    FD.configs.forEach(function (c) {
      var n = c.key === 'jev' ? 32 : cnt[c.size], R = c.key === 'jev' ? 16 : rad[c.size], x = X(c.sec), y = Y(c.share), k;
      var col = /^lp/.test(c.key) ? C.f1 : /^(d|jev)/.test(c.key) ? C.f2 : C.f3;
      pts[c.key] = { x: x, y: y, R: R, c: c, i0: i, n: n };
      for (k = 0; k < n; k++, i++) { var rr = R * Math.sqrt((k + 0.5) / n), th = k * 2.399963; lay.x[i] = x + rr * Math.cos(th); lay.y[i] = y + rr * Math.sin(th); lay.r[i] = 3.7; lay.a[i] = 0.95; W.col(lay, i, col); }
    });
    if (i !== N) throw new Error('board uses ' + i + ' dots');
    lay.m = { X: X, Y: Y, pts: pts, bx0: bx0, bx1: bx1, by0: by0, by1: by1 };
    return lay;
  };
  // near misses in rows by type, split at the cutoff line: cleared to the left, got through to the right
  L.rows = function () {
    var lay = W.lay(), cx = 560, y0 = 500, dy = 116, pitch = 27, nL = [0, 0, 0, 0, 0], nR = [0, 0, 0, 0, 0], i, d, k;
    for (i = 0; i < N; i++) {
      d = D[i]; W.col(lay, i, L.lab(d));
      if (d.rc < 0) { W.away(lay, i, d.l ? 0.3 : 0.25); continue; }
      if (d.pp) { k = nR[d.rc]++; lay.x[i] = cx + 26 + k * pitch; lay.a[i] = 1; } else { k = nL[d.rc]++; lay.x[i] = cx - 26 - k * pitch; lay.a[i] = 0.4; }
      lay.y[i] = y0 + d.rc * dy; lay.r[i] = 10;
    }
    lay.m = { cx: cx, y0: y0, dy: dy, pitch: pitch, nL: nL, nR: nR };
    return lay;
  };
  // the closing picture: responsive dots spell "yes", non-responsive dots spell "no"
  L.words = function (size, baseY) {
    var lay = W.lay(), cv = document.createElement('canvas'), c = cv.getContext('2d'); cv.width = F.W; cv.height = 700;
    var font = '700 ' + size + 'px Besley'; c.font = font;
    var wy = c.measureText('yes').width, wn = c.measureText('no').width, gap = size * 0.3, x0 = (F.W - (wy + gap + wn)) / 2;
    var sample = function (text, x, n, seed) {
      c.clearRect(0, 0, cv.width, cv.height); c.font = font; c.fillStyle = '#fff'; c.textBaseline = 'alphabetic'; c.fillText(text, x, 520);
      var im = c.getImageData(0, 0, cv.width, cv.height).data, pts = [], px, py, st = 3, rnd = F.rng(seed), i, j, it;
      for (py = 0; py < cv.height; py += st) for (px = 0; px < cv.width; px += st) if (im[(py * cv.width + px) * 4 + 3] > 140) pts.push([px, py]);
      var cen = [], used = {}; while (cen.length < n) { j = Math.floor(rnd() * pts.length); if (!used[j]) { used[j] = 1; cen.push([pts[j][0], pts[j][1]]); } }
      for (it = 0; it < 22; it++) {                              // Lloyd relaxation: even spacing inside the letters
        var sx = new Float64Array(n), sy = new Float64Array(n), sn = new Float64Array(n);
        for (i = 0; i < pts.length; i++) { var bd = 1e18, bj = 0, dd; for (j = 0; j < n; j++) { dd = (pts[i][0] - cen[j][0]) * (pts[i][0] - cen[j][0]) + (pts[i][1] - cen[j][1]) * (pts[i][1] - cen[j][1]); if (dd < bd) { bd = dd; bj = j; } } sx[bj] += pts[i][0]; sy[bj] += pts[i][1]; sn[bj]++; }
        for (j = 0; j < n; j++) if (sn[j]) { cen[j][0] = sx[j] / sn[j]; cen[j][1] = sy[j] / sn[j]; }
      }
      return { cen: cen, pitch: Math.sqrt(pts.length * st * st / n) };
    };
    var ny = D.filter(function (d) { return d.l; }).length, a = sample('yes', x0, ny, 5), b = sample('no', x0 + wy + gap, N - ny, 6), ia = 0, ib = 0, i, p;
    a.cen.sort(function (p, q) { return p[0] - q[0]; }); b.cen.sort(function (p, q) { return p[0] - q[0]; });
    var r = Math.min(a.pitch, b.pitch) * 0.39;
    for (i = 0; i < N; i++) { p = D[i].l ? a.cen[ia++] : b.cen[ib++]; lay.x[i] = p[0]; lay.y[i] = p[1] - 520 + baseY; lay.r[i] = r; lay.a[i] = 1; W.col(lay, i, L.lab(D[i])); }
    lay.m = { x0: x0, x1: x0 + wy + gap + wn, r: r };
    return lay;
  };
})();
