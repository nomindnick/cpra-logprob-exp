// Beat 4: the scoreboard. The dots condense into 13 orbs, one per setup: seconds per email against share cleared.
F.scene(function () {
  var W = F.world, L = F.L, FD = window.FD, sh = F.sh, e = {};
  var s0 = F.seg('s4').start, tWrit = F.cue('s4', 'Writing'), tLess = F.cue('s4', 'cleared less'), tBest = F.cue('s4', 'The best'), t83 = F.cue('s4', '83'), tGap = F.cue('s4', 'a gap'),
    tHost = F.cue('s4', 'The hosted'), tFast = F.cue('s4', 'fastest'), t64 = F.cue('s4', '64'), end = F.seg('s5').start - 0.45;
  var B = L.board(), bm = B.m, P = bm.pts, keyOf = [];
  Object.keys(P).forEach(function (k) { for (var i = P[k].i0; i < P[k].i0 + P[k].n; i++) keyOf[i] = k; });
  var hi = function (re) { return W.mod(B, function (i, o) { if (!re.test(keyOf[i])) o.a[i] = 0.2; }); };
  var bW = hi(/^j[sr]/), bD = hi(/^(d27|lp27)$/), bJ = hi(/^jev$/), tIn = s0 - 0.4;
  var orb = W.ord.by(function (i) { return P[keyOf[i]].x + W.u[i] * 300; });
  W.key(tIn, B, { dur: 1.5, stg: 1.0, ord: orb, arc: 70, lift: 0.3 });
  W.key(tWrit - 0.25, bW, { dur: 0.5 }); W.key(tBest - 0.25, bD, { dur: 0.5 }); W.key(tHost - 0.25, bJ, { dur: 0.5 });
  W.cam(tIn, 1, 540, 675, 1.4); W.cam(s0 + 1.6, 1.02, 548, 690, 17, F.eo);
  F.snd(tIn, 'whoosh', 1); F.snd(tIn + 2.2, 'chime', 0.6); F.snd(tWrit - 0.2, 'pop', 0.9); F.snd(tLess, 'thud', 0.7); F.snd(tBest - 0.2, 'pop', 0.9);
  F.snd(t83, 'tick', 1); F.snd(tGap, 'pop', 0.7); F.snd(tHost - 0.2, 'pop', 0.9); F.snd(tFast, 'tick', 1); F.snd(t64, 'tick', 1);
  var fam = [['lp4', 'lp9', 'lp27', '#bd8c12'], ['d4', 'd9', 'd27', '#17a58f'], ['js4', 'js9', 'js27', '#a070f0'], ['jr4', 'jr9', 'jr27', '#a070f0', [7, 6]]];
  var XT = [[0.1, '0.1 s'], [0.3, '0.3'], [1, '1 s'], [3, '3'], [10, '10 s']], YT = [0, 25, 50, 75, 100];
  var ringOn = function (t) { return t >= tHost - 0.25 ? ['jev'] : t >= tBest - 0.25 ? ['d27', 'lp27'] : t >= tWrit - 0.25 ? ['js4', 'js9', 'js27', 'jr4', 'jr9', 'jr27'] : []; };
  W.under.push(function (c, t) {
    if (t < tIn || t > end + 0.1) return;
    var a = F.span(t, s0 + 0.5, end, 0.9, 0.4);
    YT.forEach(function (v) { W.line(c, bm.bx0 - 6, bm.Y(v), bm.bx1 + 30, bm.Y(v), v ? '#263146' : '#3a4760', a, v ? 1 : 1.5); });
    XT.forEach(function (q) { W.line(c, bm.X(q[0]), bm.by0 + 22, bm.X(q[0]), bm.by0 + 30, '#3a4760', a, 1.5); });
    fam.forEach(function (f) { for (var k = 0; k < 2; k++) W.line(c, P[f[k]].x, P[f[k]].y, P[f[k + 1]].x, P[f[k + 1]].y, f[3], a * 0.42, 2, f[4]); });
  });
  W.over.push(function (c, t) {
    if (t < tWrit - 0.3 || t > end + 0.1) return;
    var a = F.span(t, tWrit - 0.25, end, 0.4, 0.4);
    ringOn(t).forEach(function (k) { W.ring(c, P[k].x, P[k].y, P[k].R + 7, '#e8edf4', a * 0.85, 2); });
  });
  var lab = function (wl, css, html) { return F.h('div', { cls: 'abs t', style: 'font-size:24px;line-height:1.25;' + css }, wl, html); };
  F.act({ id: 'b4', start: tIn + 0.2, end: end, kick: 'The scoreboard',
    build: function (el, wl) {
      e.h = F.h('div', { cls: 'abs h1', style: 'left:60px;top:124px' }, el, 'Every setup, one chart');
      e.leg = F.h('div', { cls: 'abs t', style: 'left:60px;top:226px;font-size:25px' }, el, '<span class="sw" style="background:var(--f1)"></span>one-word odds<span style="display:inline-block;width:30px"></span><span class="sw" style="background:var(--f2)"></span>decision model<span style="display:inline-block;width:30px"></span><span class="sw" style="background:var(--f3)"></span>written answer');
      var dot = function (r) { return '<span style="display:inline-block;width:' + 2 * r + 'px;height:' + 2 * r + 'px;border-radius:50%;background:var(--ink3);vertical-align:middle;margin:0 8px 0 18px"></span>'; };
      e.size = F.h('div', { cls: 'abs t', style: 'left:60px;top:272px;font-size:25px' }, el, 'Model size' + dot(12) + '4B' + dot(15.5) + '9B' + dot(21) + '27B<span style="display:inline-block;width:26px"></span><span style="color:var(--ink3)">- - -</span> written, reasons first');
      e.yt = F.h('div', { cls: 'abs lab', style: 'left:60px;top:352px' }, wl, '↑ share of non-responsive emails cleared');
      e.xt = F.h('div', { cls: 'abs lab', style: 'right:50px;top:' + (bm.by0 + 62) + 'px' }, wl, 'seconds per email, log scale →');
      e.ticks = F.h('div', { style: 'position:absolute;left:0;top:0;width:1080px;height:1350px' }, wl);
      YT.forEach(function (v) { F.h('div', { cls: 'abs tick', style: 'right:' + (F.W - bm.bx0 + 16) + 'px;top:' + (bm.Y(v) - 10) + 'px' }, e.ticks, v + '%'); });
      XT.forEach(function (q) { F.h('div', { cls: 'abs tick', style: 'left:' + (bm.X(q[0]) - 40) + 'px;width:80px;text-align:center;top:' + (bm.by0 + 36) + 'px' }, e.ticks, q[1]); });
      e.note = F.h('div', { cls: 'abs note', style: 'left:60px;top:1066px;font-size:19px;white-space:normal;width:980px;line-height:1.3' }, el, '98% of responsive kept. Cutoffs set with the answers in hand. Median time on one desktop; the hosted model’s time includes the network.');
      e.wT = lab(wl, 'right:192px;top:650px;text-align:right', 'Written answers took<br><b style="font-size:30px">at least 2.5× the time</b>');
      e.w0 = lab(wl, 'right:' + (F.W - P.jr4.x + 26) + 'px;top:' + (bm.by0 - 34) + 'px;text-align:right', 'three setups cleared <b>0%</b>');
      e.w67 = lab(wl, 'right:' + (F.W - P.jr27.x + 34) + 'px;top:' + (P.jr27.y - 15) + 'px', 'written <b>67%</b>');
      e.d83 = lab(wl, 'right:54px;top:' + (P.d27.y - 78) + 'px', 'd3-27b decision model <b style="font-size:30px">83%</b>');
      e.l77 = lab(wl, 'right:' + (F.W - P.lp27.x + 34) + 'px;top:' + (P.lp27.y - 62) + 'px', '27B one-word odds <b style="font-size:30px">77%</b>');
      e.gap = lab(wl, 'right:192px;top:614px;text-align:right;font-size:23px', '+5 points, interval −6 to +9<br><b style="font-size:27px">Too close to call here</b>');
      e.jev = lab(wl, 'left:' + (P.jev.x - 16) + 'px;top:' + (P.jev.y - 122) + 'px', 'Jev, a hosted API');
      e.jevF = lab(wl, 'left:' + (P.jev.x - 16) + 'px;top:' + (P.jev.y - 88) + 'px', '<b style="font-size:30px">0.12 s</b> per email');
      e.jev64 = lab(wl, 'left:' + (P.jev.x + 30) + 'px;top:' + (P.jev.y - 16) + 'px', '<b style="font-size:30px">64%</b> cleared');
    },
    draw: function (t) {
      F.show(e.h, F.rise(t, s0 - 0.1)); F.fade(e.leg, F.rise(t, s0 + 0.7)); F.fade(e.size, F.rise(t, s0 + 0.9)); F.fade(e.note, F.rise(t, s0 + 1.4));
      var a = F.rise(t, s0 + 0.5, 0.9); F.fade(e.yt, a); F.fade(e.xt, a); F.fade(e.ticks, a);
      F.show(e.wT, F.span(t, tWrit - 0.1, tBest - 0.3), 10); F.show(e.w0, F.span(t, tLess - 0.1, tBest - 0.3), 10); F.show(e.w67, F.span(t, tLess + 0.5, tBest - 0.3), 10);
      F.show(e.d83, F.span(t, t83 - 0.5, tHost - 0.3), 10); F.show(e.l77, F.span(t, tGap - 0.7, tHost - 0.3), 10); F.show(e.gap, F.span(t, tGap - 0.1, tHost - 0.3), 10);
      F.show(e.jev, F.rise(t, tHost - 0.1), 10); F.show(e.jevF, F.rise(t, tFast - 0.2), 10); F.show(e.jev64, F.rise(t, t64 - 0.2), 10);
    } });
});
