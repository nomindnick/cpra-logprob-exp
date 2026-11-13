// The dot world: 496 dots (one per test pair) that never leave the screen. A layout gives every dot a place, size, colour and
// opacity; keyframes move the dots from one layout to the next. The state at time t is a pure function of t.
(function () {
  var F = window.F, N = window.FD.n, TAU = Math.PI * 2;
  var W = F.world = { N: N, keys: [], cams: [], under: [], over: [] };
  var FIELDS = ['x', 'y', 'r', 'a', 'cr', 'cg', 'cb', 'd'];        // d = drift weight (1 for dots resting out of focus)
  W.C = { pos: [57, 135, 229], neg: [217, 89, 38], neu: [150, 162, 184], gold: [255, 206, 64], f1: [189, 140, 18], f2: [23, 165, 143], f3: [160, 112, 240], miss: [240, 138, 128] };
  W.lay = function () { var o = { m: {} }; FIELDS.forEach(function (f) { o[f] = new Float32Array(N); }); return o; };
  W.clone = function (L) { var o = { m: L.m }; FIELDS.forEach(function (f) { o[f] = new Float32Array(L[f]); }); return o; };
  W.col = function (L, i, c) { L.cr[i] = c[0]; L.cg[i] = c[1]; L.cb[i] = c[2]; };
  // a changed copy of a layout: fn(i, L) edits dot i
  W.mod = function (L, fn) { var o = W.clone(L), i; for (i = 0; i < N; i++) fn(i, o); return o; };
  var rnd = F.rng(4177), i;
  W.u = new Float32Array(N); W.sg = new Float32Array(N); var ph1 = new Float32Array(N), ph2 = new Float32Array(N);
  W.home = { x: new Float32Array(N), y: new Float32Array(N), r: new Float32Array(N), a: new Float32Array(N) };
  for (i = 0; i < N; i++) {
    W.u[i] = rnd(); W.sg[i] = rnd() < 0.5 ? -1 : 1; ph1[i] = rnd() * TAU; ph2[i] = rnd() * TAU;
    W.home.x[i] = -60 + rnd() * 1200; W.home.y[i] = 120 + rnd() * 1000; var q = rnd(); W.home.r[i] = 13 + q * q * 34; W.home.a[i] = 0.035 + rnd() * 0.05;
  }
  // send dot i out of focus: a large faint disc drifting in the background
  W.away = function (L, i, k) { L.x[i] = W.home.x[i]; L.y[i] = W.home.y[i]; L.r[i] = W.home.r[i]; L.a[i] = W.home.a[i] * (k == null ? 1 : k); L.d[i] = 1; };
  var zero = new Float32Array(N);
  W.ord = {
    rand: W.u,
    by: function (fn) { var v = new Float32Array(N), lo = 1e9, hi = -1e9, j; for (j = 0; j < N; j++) { v[j] = fn(j); if (v[j] < lo) lo = v[j]; if (v[j] > hi) hi = v[j]; } for (j = 0; j < N; j++) v[j] = hi > lo ? (v[j] - lo) / (hi - lo) : 0; return v; },
    x: function (L, jit) { return W.ord.by(function (j) { return L.x[j] + (jit || 0) * W.u[j]; }); },
    y: function (L, jit) { return W.ord.by(function (j) { return L.y[j] + (jit || 0) * W.u[j]; }); },
    from: function (L, x, y) { return W.ord.by(function (j) { return Math.hypot(L.x[j] - x, L.y[j] - y); }); }
  };
  // key(t, layout, {dur, stg, ord, arc, lift, ease}): from time t each dot moves to its place in the layout over dur seconds,
  // starting stg*ord[i] seconds late
  W.key = function (t, lay, o) {
    o = o || {};
    var k = { t: t, lay: lay, dur: o.dur || 1.2, stg: o.stg || 0, ord: o.ord || zero, arc: o.arc || 0, lift: o.lift || 0, ease: o.ease || F.eio };
    k.end = k.t + k.dur + k.stg; W.keys.push(k); return k;
  };
  W.cam = function (t, s, x, y, dur, ease) { W.cams.push({ t: t, s: s, x: x == null ? 540 : x, y: y == null ? 675 : y, dur: dur || 1.2, ease: ease || F.eio }); };
  W.finish = function () { W.keys.sort(function (a, b) { return a.t - b.t; }); W.cams.sort(function (a, b) { return a.t - b.t; }); };
  var st = W.st = W.lay();
  function evalState(t) {
    var ks = W.keys, j0 = 0, j, i, k, L, p, e, x0, y0, dx, dy, len, amp, s;
    for (j = 1; j < ks.length; j++) if (ks[j].end <= t) j0 = j;
    L = ks[j0].lay; FIELDS.forEach(function (f) { st[f].set(L[f]); });
    for (j = j0 + 1; j < ks.length && ks[j].t < t; j++) {
      k = ks[j]; L = k.lay;
      for (i = 0; i < N; i++) {
        p = (t - k.t - k.stg * k.ord[i]) / k.dur;
        if (p <= 0) continue;
        if (p >= 1) { st.x[i] = L.x[i]; st.y[i] = L.y[i]; st.r[i] = L.r[i]; st.a[i] = L.a[i]; st.cr[i] = L.cr[i]; st.cg[i] = L.cg[i]; st.cb[i] = L.cb[i]; st.d[i] = L.d[i]; continue; }
        e = k.ease(p); x0 = st.x[i]; y0 = st.y[i]; dx = L.x[i] - x0; dy = L.y[i] - y0;
        st.x[i] = x0 + dx * e; st.y[i] = y0 + dy * e;
        s = Math.sin(Math.PI * p);
        if (k.arc) { len = Math.hypot(dx, dy); if (len > 1) { amp = k.arc * s * W.sg[i] * Math.min(1, len / 260) * (0.5 + W.u[i]); st.x[i] -= dy / len * amp; st.y[i] += dx / len * amp; } }
        st.r[i] = (st.r[i] + (L.r[i] - st.r[i]) * e) * (1 + k.lift * s);
        st.a[i] += (L.a[i] - st.a[i]) * e; st.cr[i] += (L.cr[i] - st.cr[i]) * e; st.cg[i] += (L.cg[i] - st.cg[i]) * e; st.cb[i] += (L.cb[i] - st.cb[i]) * e; st.d[i] += (L.d[i] - st.d[i]) * e;
      }
    }
    for (i = 0; i < N; i++) if (st.d[i] > 0.001) { st.x[i] += st.d[i] * 20 * Math.sin(0.21 * t + ph1[i]); st.y[i] += st.d[i] * 15 * Math.cos(0.17 * t + ph2[i]); }
  }
  W.at = function (t) { evalState(t); return st; };
  function camAt(t) {
    var c = { s: 1, x: 540, y: 675 }, j, k, e;
    for (j = 0; j < W.cams.length && W.cams[j].t < t; j++) { k = W.cams[j]; e = k.ease(F.lin(t, k.t, k.t + k.dur)); c.s += (k.s - c.s) * e; c.x += (k.x - c.x) * e; c.y += (k.y - c.y) * e; }
    return c;
  }
  W.camAt = camAt;
  function dots(c, t) {
    evalState(t);
    var pass, i, a, r, big;
    for (pass = 0; pass < 2; pass++) for (i = 0; i < N; i++) {
      a = st.a[i]; if (a < 0.004) continue;
      r = st.r[i]; big = r > 12.5 && a < 0.3; if (big !== (pass === 0)) continue;
      c.globalAlpha = a > 1 ? 1 : a; c.fillStyle = 'rgb(' + (st.cr[i] | 0) + ',' + (st.cg[i] | 0) + ',' + (st.cb[i] | 0) + ')';
      c.beginPath(); c.arc(st.x[i], st.y[i], r, 0, TAU); c.fill();
    }
    c.globalAlpha = 1;
  }
  var cv, ctx, dc, dctx, sc, sctx, bc, bctx, wl, SH = 0.021, KSUB = 6, BLOOM = 0.6;
  W.init = function () {
    cv = document.getElementById('cv'); ctx = cv.getContext('2d'); wl = document.getElementById('wl');
    var mk = function (w, h) { var c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
    dc = mk(F.W, F.H); dctx = dc.getContext('2d'); sc = mk(F.W, F.H); sctx = sc.getContext('2d'); bc = mk(F.W / 4, Math.ceil(F.H / 4)); bctx = bc.getContext('2d');
  };
  W.draw = function (t) {
    var cam = camAt(t), s = cam.s, tx = F.W / 2 - cam.x * s, ty = F.H / 2 - cam.y * s, k, moving = false;
    W.keys.forEach(function (q) { if (t > q.t && t < q.end + SH) moving = true; });
    dctx.setTransform(1, 0, 0, 1, 0, 0); dctx.globalCompositeOperation = 'source-over'; dctx.globalAlpha = 1; dctx.clearRect(0, 0, F.W, F.H);
    if (!moving) { dctx.setTransform(s, 0, 0, s, tx, ty); dots(dctx, t); }
    else {
      for (k = KSUB - 1; k >= 0; k--) {                      // sub-frames across the shutter, averaged: real motion blur
        sctx.setTransform(1, 0, 0, 1, 0, 0); sctx.clearRect(0, 0, F.W, F.H); sctx.setTransform(s, 0, 0, s, tx, ty); dots(sctx, t - SH * k / KSUB);
        dctx.globalCompositeOperation = 'lighter'; dctx.globalAlpha = 1 / KSUB; dctx.drawImage(sc, 0, 0);
      }
    }
    bctx.clearRect(0, 0, bc.width, bc.height); bctx.filter = 'blur(2.2px)'; bctx.drawImage(dc, 0, 0, bc.width, bc.height); bctx.filter = 'none';
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1; ctx.clearRect(0, 0, F.W, F.H);
    ctx.setTransform(s, 0, 0, s, tx, ty); W.under.forEach(function (fn) { ctx.save(); fn(ctx, t); ctx.restore(); });
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = BLOOM; ctx.imageSmoothingQuality = 'high'; ctx.drawImage(bc, 0, 0, F.W, F.H);
    ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1; ctx.drawImage(dc, 0, 0);
    ctx.setTransform(s, 0, 0, s, tx, ty); W.over.forEach(function (fn) { ctx.save(); fn(ctx, t); ctx.restore(); });
    wl.style.transform = 'translate(' + tx + 'px,' + ty + 'px) scale(' + s + ')';
  };
  // drawing helpers for chart furniture (world coordinates)
  W.line = function (c, x1, y1, x2, y2, col, a, w, dash) { if (a <= 0.003) return; c.globalAlpha = a; c.strokeStyle = col; c.lineWidth = w || 2; c.setLineDash(dash || []); c.beginPath(); c.moveTo(x1, y1); c.lineTo(x2, y2); c.stroke(); c.setLineDash([]); c.globalAlpha = 1; };
  W.ring = function (c, x, y, r, col, a, w) { if (a <= 0.003) return; c.globalAlpha = a; c.strokeStyle = col; c.lineWidth = w || 2; c.beginPath(); c.arc(x, y, r, 0, TAU); c.stroke(); c.globalAlpha = 1; };
  W.disc = function (c, x, y, r, col, a) { if (a <= 0.003) return; c.globalAlpha = a; c.fillStyle = col; c.beginPath(); c.arc(x, y, r, 0, TAU); c.fill(); c.globalAlpha = 1; };
})();
