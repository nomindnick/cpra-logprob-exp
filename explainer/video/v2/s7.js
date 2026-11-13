// Beat 7: the line itself. Each request wanted its own line; request 1's line on request 2 misses 14 of 143 responsive.
F.scene(function () {
  var W = F.world, L = F.L, FD = window.FD, D = FD.dots, sh = F.sh, C = W.C, e = {};
  var s0 = F.seg('s7').start, tSet = F.cue('s7', 'I set'), tNew = F.cue('s7', 'A new'), tTwo = F.cue('s7', 'And the two'), tUse = F.cue('s7', 'Use'), tMiss = F.cue('s7', 'misses'),
    t14 = F.cue('s7', '14'), tWhere = F.cue('s7', 'Where'), end = F.seg('s8').start - 0.45, tIn = s0 - 0.4;
  var A = FD.cut.a, B = FD.cut.b, P = 14, U = 12, Dn = 9, HO = { key: 'lp', pitch: P, cap: U, capDn: Dn };
  var po = function (d) { return d.po; }, px = function (d) { return d.px; }, r2 = function (d) { return d.q === 1; };
  var h1 = L.hist(Object.assign({}, HO, { cy: 518, sel: function (d) { return d.q === 0; }, cut: A.lo, pass: po }));
  var h2 = L.hist(Object.assign({}, HO, { cy: 904, sel: r2, cut: B.lo, pass: po, cut2: A.lo, pass2: px }));
  var two = L.merge(h1, h2, r2), m1 = h1.m, m2 = h2.m; F.lays.two = two;
  var twoCut = W.mod(two, function (i, o) { if (!D[i].po) o.a[i] = 0.3; });
  var twoGrey = W.mod(two, function (i, o) { W.col(o, i, C.neu); o.a[i] = 0.75; });
  var missed = [];
  var twoX = W.mod(twoCut, function (i, o) {
    var d = D[i]; if (d.q !== 1) return;
    if (d.px) { o.a[i] = 1; return; }
    if (d.l) { W.col(o, i, C.miss); o.a[i] = 1; o.r[i] *= 1.3; missed.push(i); } else o.a[i] = 0.3;
  });
  if (missed.length !== FD.cut.x.missed) throw new Error('missed ' + missed.length);
  var xA = m1.cutX, xB = m2.cutX, a1 = m1.cy - m1.band - U * P - 22, a2 = m1.cy + m1.band + Dn * P + 14, b1 = m2.cy - m2.band - U * P - 22, b2 = m2.cy + m2.band + Dn * P + 14;
  var l1 = F.track({ x: xA, y1: a1, y2: a1, a: 0 }).key(tSet - 0.02, { a: 1 }, 0.02).key(tSet, { y2: a2 }, 0.5, F.eo).key(tNew, { a: 0.22 }, 0.5).key(tTwo - 0.1, { a: 1 }, 0.5)
    .key(tUse + 0.1, { y2: b2 }, 1.5).key(end - 0.1, { a: 0 }, 0.45);
  var l2 = F.track({ x: xB, y1: b1, y2: b1, a: 0 }).key(tSet + 0.33, { a: 1 }, 0.02).key(tSet + 0.35, { y2: b2 }, 0.5, F.eo).key(tNew, { a: 0.22 }, 0.5).key(tTwo - 0.1, { a: 1 }, 0.5)
    .key(tUse + 1.0, { a: 0.3 }, 0.6).key(end - 0.1, { a: 0 }, 0.45);
  sh.cut.key(tIn, { a: 0 }, 0.5);
  W.key(tIn, two, { dur: 1.5, stg: 0.9, ord: W.ord.by(function (i) { return D[i].q * 0.6 + W.u[i] * 0.6; }), arc: 50, lift: 0.3 });
  W.key(tSet + 0.3, twoCut, { dur: 0.6 }); W.key(tNew, twoGrey, { dur: 0.6 }); W.key(tTwo - 0.1, twoCut, { dur: 0.6 }); W.key(tMiss - 0.35, twoX, { dur: 0.7 });
  W.cam(tIn, 1, 540, 675, 1.4); W.cam(tUse, 1.012, 540, 662, 8, F.eo);
  F.snd(tIn, 'whoosh', 1); F.snd(tSet, 'thud', 0.9); F.snd(tSet + 0.35, 'thud', 0.8); F.snd(tNew + 0.1, 'pop', 0.6); F.snd(tTwo, 'pop', 0.7);
  F.snd(tUse + 0.1, 'rise', 0.8); F.snd(tUse + 1.6, 'thud', 1); F.snd(t14 - 0.05, 'tick', 1); F.snd(tWhere - 0.1, 'chime', 0.8);
  var ax1, ax2;
  W.under.push(function (c, t) {
    if (t < tIn || t > end + 0.1) return;
    var a = F.span(t, tIn + 1.1, end, 0.8, 0.4); F.axisLine(c, m1, ax1, a); F.axisLine(c, m2, ax2, a);
    var b = F.span(t, tMiss - 0.3, end, 0.6, 0.4);
    if (b > 0) { c.globalAlpha = 0.13 * b; c.fillStyle = '#f08a80'; c.fillRect(xB, b1, xA - xB, b2 - b1); c.globalAlpha = 1; }
  });
  W.over.push(function (c, t) {
    if (t < tSet - 0.1 || t > end + 0.5) return;
    F.cutDraw(c, l2.at(t)); F.cutDraw(c, l1.at(t));
    var p = F.lin(t, tMiss - 0.05, tMiss + 1.0);
    if (p > 0 && p < 1) missed.forEach(function (i) { W.ring(c, twoX.x[i], twoX.y[i], twoX.r[i] + 3 + 16 * F.eo(p), '#f08a80', (1 - p) * 0.9, 2); });
  });
  var st = function (wl, y, html) { return F.h('div', { cls: 'abs t', style: 'left:60px;top:' + y + 'px;font-size:24px;line-height:1.35' }, wl, html); };
  F.act({ id: 'b7', start: tIn + 0.2, end: end, kick: 'The line',
    build: function (el, wl) {
      e.h = F.h('div', { cls: 'abs h1', style: 'left:60px;top:124px' }, el, 'Then the line itself');
      e.hb = F.h('div', { cls: 'abs h1', style: 'left:60px;top:112px;font-size:56px;line-height:1.12' }, el, 'Where the line goes<br>is a legal judgment.');
      e.leg = F.legend(el, 60, 258);
      e.note = F.h('div', { cls: 'abs note', style: 'left:60px;top:1092px;font-size:19px' }, el, 'qwen3.8:27b, one-word score. Each line keeps 98% of its own request’s responsive.');
      e.ax = F.h('div', { style: 'position:absolute;left:0;top:0;width:1080px;height:1350px' }, wl);
      ax1 = F.axisBuild(e.ax, m1, { fs: 18 }); ax2 = F.axisBuild(e.ax, m2, { fs: 18 });
      e.t1 = F.h('div', { cls: 'abs lab', style: 'left:60px;top:' + (a1 - 4) + 'px;color:var(--ink)' }, wl, 'Request 1');
      e.t2 = F.h('div', { cls: 'abs lab', style: 'left:60px;top:' + (b1 - 4) + 'px;color:var(--ink)' }, wl, 'Request 2');
      e.s1 = st(wl, a1 + 30, '<b>91</b> of 101 cleared<br><b>2</b> of 146 responsive missed');
      e.s2 = st(wl, b1 + 30, '<b>81</b> of 106 cleared<br><b>2</b> of 143 responsive missed');
      e.s2x = st(wl, b1 + 30, '<b>94</b> of 106 cleared<br><span class="sw" style="background:var(--stamp)"></span><b style="font-size:32px" id="b7m">14</b> of 143 responsive <b>missed</b>');
      e.la = F.h('div', { cls: 'abs lab g', style: 'left:' + (xA + 14) + 'px;top:' + (a1 - 4) + 'px' }, wl, 'keep at 36% or more');
      e.lb = F.h('div', { cls: 'abs lab g', style: 'right:' + (F.W - xB + 14) + 'px;top:' + (b1 - 4) + 'px' }, wl, '5.7% or more');
      e.lx = F.h('div', { cls: 'abs lab g', style: 'left:' + (xA + 14) + 'px;top:' + (b1 - 4) + 'px' }, wl, 'request 1’s line');
      e.nw = F.h('div', { cls: 'abs lab', style: 'right:60px;top:' + (a2 + 6) + 'px;color:var(--ink)' }, wl, 'a new request: no answers, no line');
    },
    draw: function (t) {
      F.show(e.h, F.span(t, s0 - 0.1, tWhere - 0.25, 0.5, 0.3)); F.show(e.hb, F.rise(t, tWhere - 0.05)); F.fade(e.leg, F.rise(t, tIn + 1.2)); F.fade(e.note, F.rise(t, tSet + 0.8));
      F.fade(e.ax, F.rise(t, tIn + 1.1, 0.8)); F.fade(e.t1, F.rise(t, tIn + 1.0)); F.fade(e.t2, F.rise(t, tIn + 1.2));
      var g = 1 - 0.75 * F.span(t, tNew, tTwo - 0.1, 0.4, 0.4);
      F.fade(e.s1, F.rise(t, tSet + 0.5) * g); F.fade(e.s2, F.span(t, tSet + 0.85, tMiss - 0.3, 0.5, 0.3) * g); F.show(e.s2x, F.rise(t, tMiss - 0.15), 8);
      F.txt(document.getElementById('b7m'), Math.round(F.count(t, tMiss, t14 - tMiss + 0.25, 2, 14)));
      F.fade(e.la, F.rise(t, tSet + 0.4) * g); F.fade(e.lb, F.rise(t, tSet + 0.75) * g * (1 - 0.6 * F.rise(t, tUse + 1.0))); F.fade(e.lx, F.rise(t, tUse + 1.4));
      F.fade(e.nw, F.span(t, tNew + 0.15, tTwo - 0.15, 0.4, 0.3));
    } });
});
