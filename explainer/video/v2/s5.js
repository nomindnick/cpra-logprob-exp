// Beat 5: where it breaks. Real non-responsive emails were easy; the built near misses were not.
F.scene(function () {
  var W = F.world, L = F.L, FD = window.FD, D = FD.dots, sh = F.sh, m = sh.m, hC = F.lays.hC, e = {};
  var s0 = F.seg('s5').start, tReal = F.cue('s5', 'The real'), tThis = F.cue('s5', 'this model'), tNear = F.cue('s5', 'The near'), tRight = F.cue('s5', 'Right subject'),
    tKey = F.cue('s5', 'A keyword'), tIt = F.cue('s5', 'It cleared'), end = F.seg('s6').start - 0.45, tIn = s0 - 0.4, tRows = tNear - 0.45;
  var h5a = W.mod(hC, function (i, o) { if (D[i].l) o.a[i] = 0.14; });
  var h5b = W.mod(h5a, function (i, o) { if (!D[i].l && D[i].k !== 1) o.a[i] = 0.22; });
  var rows = L.rows(), rm = rows.m;
  var rowHi = function (rc) { return W.mod(rows, function (i, o) { if (D[i].rc >= 0 && D[i].rc !== rc) o.a[i] *= 0.3; }); };
  W.key(tIn, h5a, { dur: 1.5, stg: 0.9, ord: W.ord.x(hC, 240), arc: 70, lift: 0.3 });
  W.key(tReal - 0.2, h5b, { dur: 0.5 });
  W.key(tRows, rows, { dur: 1.4, stg: 0.7, ord: W.ord.by(function (i) { return D[i].rc >= 0 ? D[i].rc + W.u[i] : 6 * W.u[i]; }), arc: 50, lift: 0.3 });
  W.key(tRight - 0.2, rowHi(0), { dur: 0.4 }); W.key(tKey - 0.2, rowHi(1), { dur: 0.4 }); W.key(tIt - 0.3, rows, { dur: 0.4 });
  sh.cut.key(tIn, { x: m.cutX, y1: sh.lineTop, y2: m.bot + 14 }, 0.02).key(tIn + 1.4, { a: 1 }, 0.5)
    .key(tRows + 0.2, { x: rm.cx, y1: rm.y0 - 96, y2: rm.y0 + 4 * rm.dy + 34 }, 1.3);
  W.cam(tIn, 1, 540, 690, 1.4); W.cam(tIn + 1.5, 1.03, 540, 700, 6, F.eo); W.cam(tRows, 1, 540, 675, 1.4);
  F.snd(tIn, 'whoosh', 1); F.snd(tReal - 0.1, 'pop', 0.8); F.snd(tThis + 0.5, 'chime', 0.7); F.snd(tRows, 'whoosh', 1); F.snd(tRows + 1.5, 'thud', 0.8);
  F.snd(tRight - 0.1, 'tick', 1); F.snd(tKey - 0.1, 'tick', 1); F.snd(tIt + 0.1, 'thud', 1);
  var axis;
  W.under.push(function (c, t) { if (t > tIn && t < tRows + 1) F.axisLine(c, m, axis, F.span(t, tIn + 1.3, tRows + 0.5, 0.8, 0.5)); });
  F.act({ id: 'b5', start: tIn + 0.2, end: end, kick: 'Where it breaks',
    build: function (el, wl) {
      e.h = F.h('div', { cls: 'abs h1', style: 'left:60px;top:124px' }, el, 'The hard part');
      e.p1 = F.h('div', { cls: 'abs h2', style: 'left:60px;top:218px;font-size:34px' }, el, '<span class="sw" style="background:var(--neg)"></span>The <b>real</b> non-responsive emails');
      e.n1 = F.h('div', { cls: 'abs mid', style: 'left:60px;top:272px' }, el, '120 of 120');
      e.n1l = F.h('div', { cls: 'abs t', style: 'left:520px;top:286px' }, el, '<b>cleared</b><br>none got past the line');
      e.p2 = F.h('div', { cls: 'abs h2', style: 'left:60px;top:218px;font-size:34px' }, el, '<span class="sw" style="background:var(--neg)"></span><b>87 near misses</b>, built to fool it');
      e.n2 = F.h('div', { cls: 'abs mid', style: 'left:60px;top:272px' }, el, '40 of 87');
      e.n2l = F.h('div', { cls: 'abs t', style: 'left:440px;top:286px' }, el, '<b>cleared</b><br>fewer than half');
      e.leg = F.legend(el, 60, 384);
      e.note = F.h('div', { cls: 'abs note', style: 'left:60px;top:1078px;font-size:20px;white-space:normal;width:970px;line-height:1.3' }, el, 'Near misses are synthetic: real emails edited for this test. Same cutoff as before, set with the answers in hand.');
      e.ax = F.h('div', { style: 'position:absolute;left:0;top:0' }, wl); axis = F.axisBuild(e.ax, m);
      e.rw = F.h('div', { style: 'position:absolute;left:0;top:0;width:1080px;height:1350px' }, wl);
      F.h('div', { cls: 'abs lab', style: 'right:' + (F.W - rm.cx + 18) + 'px;top:' + (rm.y0 - 96) + 'px;color:var(--ink2)' }, e.rw, '← cleared');
      F.h('div', { cls: 'abs lab g', style: 'left:' + (rm.cx + 18) + 'px;top:' + (rm.y0 - 96) + 'px' }, e.rw, 'got through →');
      e.rl = FD.recipes.map(function (r, k) {
        var y = rm.y0 + k * rm.dy - 62, g = F.h('div', { style: 'position:absolute;left:0;top:0;width:1080px;height:1350px' }, e.rw);
        F.h('div', { cls: 'abs t', style: 'left:60px;top:' + y + 'px;font-size:24px;color:var(--ink)' }, g, r.text);
        F.h('div', { cls: 'abs t', style: 'right:60px;top:' + y + 'px;font-size:24px' }, g, '<b>' + r.cleared + '</b> of ' + r.n + ' cleared');
        return g;
      });
    },
    draw: function (t) {
      F.show(e.h, F.rise(t, s0 - 0.1));
      F.show(e.p1, F.span(t, tReal - 0.15, tRows - 0.1)); F.show(e.n1, F.span(t, tThis - 0.1, tRows - 0.1)); F.show(e.n1l, F.span(t, tThis + 0.2, tRows - 0.1));
      F.show(e.p2, F.rise(t, tNear - 0.1)); F.show(e.n2, F.rise(t, tIt - 0.1)); F.show(e.n2l, F.rise(t, tIt + 0.2));
      F.fade(e.leg, F.span(t, tIn + 1.2, tRows - 0.1, 0.5, 0.4)); F.fade(e.note, F.rise(t, tNear + 0.6));
      F.fade(e.ax, F.span(t, tIn + 1.3, tRows + 0.5, 0.8, 0.5)); F.fade(e.rw, F.rise(t, tRows + 1.0, 0.7));
      var hi = t >= tIt - 0.3 ? -1 : t >= tKey - 0.2 ? 1 : t >= tRight - 0.2 ? 0 : -1;
      e.rl.forEach(function (g, k) { g.style.opacity = hi < 0 || hi === k ? 1 : 0.35; });
    } });
});
