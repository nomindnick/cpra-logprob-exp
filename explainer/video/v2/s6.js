// Beat 6: every request is different. Request 2 asked for a committee's email; the roster takes it from 76% cleared to 93%.
F.scene(function () {
  var W = F.world, L = F.L, FD = window.FD, D = FD.dots, sh = F.sh, e = {};
  var s0 = F.seg('s6').start, tOne = F.cue('s6', 'One asked'), tModel = F.cue('s6', 'The model'), tGive = F.cue('s6', 'Give'), t76 = F.cue('s6', '76'), t93 = F.cue('s6', '93'),
    end = F.seg('s7').start - 0.45, tIn = s0 - 0.4, tM = t76 + 0.35, dM = t93 - tM + 0.1;
  var q2 = function (d) { return d.q === 1; }, HO = { key: 'lp', cy: 792, pitch: 18, cap: 14, capDn: 13, sel: q2, awayK: 0.3 };
  var dim = function (h, f) { return W.mod(h, function (i, o) { if (q2(D[i]) && !D[i][f]) o.a[i] = 0.3; }); };
  var hB = dim(L.hist(Object.assign({}, HO, { cut: FD.cut.b.lo, pass: function (d) { return d.po; } })), 'po'), mB = hB.m;
  var hR = dim(L.hist(Object.assign({}, HO, { key: 'ro', cut: FD.cut.ro.lo, pass: function (d) { return d.pr; } })), 'pr'), mR = hR.m;
  var depthR = function (m) { var cb = Math.round((m.cutX - m.x0) / m.pitch), q = 0, c; for (c = cb; c < m.ncol; c++) if (m.hDn[c] > q) q = m.hDn[c]; return m.cy + m.band + q * m.pitch; };
  var yT = Math.min(mB.top, mR.top) - 16, yB = Math.max(mB.bot, mR.bot) + 14;
  W.key(tIn, hB, { dur: 1.5, stg: 0.9, ord: W.ord.x(hB, 240), arc: 60, lift: 0.3 });
  W.key(tM, hR, { dur: dM - 0.5, stg: 0.5, ord: W.ord.x(hR, 200), arc: 40, lift: 0.25 });
  sh.cut.key(tIn + 0.1, { x: mB.cutX, y1: yT, y2: yB }, 1.4).key(tM + 0.2, { x: mR.cutX }, dM - 0.4);
  W.cam(tIn, 1, 540, 675, 1.4); W.cam(tIn + 1.5, 1.03, 540, 690, 12, F.eo);
  F.snd(tIn, 'whoosh', 1); F.snd(tOne - 0.1, 'pop', 0.8); F.snd(tModel + 0.1, 'tick', 1); F.snd(tGive + 0.4, 'pop', 1); F.snd(tM, 'whoosh', 0.9); F.snd(t93 + 0.1, 'chime', 0.9);
  var axis;
  W.under.push(function (c, t) { if (t > tIn && t < end + 0.1) F.axisLine(c, mB, axis, F.span(t, tIn + 1.2, end, 0.8, 0.4)); });
  F.act({ id: 'b6', start: tIn + 0.2, end: end, kick: 'The roster',
    build: function (el, wl) {
      e.h = F.h('div', { cls: 'abs h1', style: 'left:60px;top:124px' }, el, 'Every request is different');
      e.card = F.h('div', { cls: 'card', style: 'white-space:normal;left:60px;top:226px;width:590px;padding:16px 26px 18px' }, el,
        '<div class="lab" style="font-size:18px;margin-bottom:8px">Request 2, paraphrased</div><div class="t" style="color:var(--ink);font-size:28px">All emails to or from the members of a committee.</div>');
      e.chip = F.h('div', { cls: 'abs chip', style: 'left:676px;top:256px;border-color:var(--gold);color:var(--ink)' }, el, '+ the committee roster');
      e.pct = F.h('div', { cls: 'abs mid', style: 'left:60px;top:372px' }, el, '76%');
      e.pl = F.h('div', { cls: 'abs t', style: 'left:278px;top:380px' }, el, '');
      e.leg = F.legend(el, 650, 420);
      e.note = F.h('div', { cls: 'abs note', style: 'left:60px;top:1078px;font-size:20px;white-space:normal;width:970px;line-height:1.3' }, el, 'One request. The roster was compiled partly from that request’s own production. Cutoffs set with the answers in hand.');
      e.ax = F.h('div', { style: 'position:absolute;left:0;top:0;width:1080px;height:1350px' }, wl); axis = F.axisBuild(e.ax, mB);
      e.g1 = F.h('div', { cls: 'abs t', style: 'left:' + (mB.cutX + 16) + 'px;top:' + (depthR(mB) + 10) + 'px;font-size:24px' }, wl, '<b>25</b> non-responsive got through');
      e.g2 = F.h('div', { cls: 'abs t', style: 'left:' + (mR.cutX + 16) + 'px;top:' + (depthR(mR) + 10) + 'px;font-size:24px' }, wl, '<b>7</b> got through');
    },
    draw: function (t) {
      F.show(e.h, F.rise(t, s0 - 0.1)); F.show(e.card, F.rise(t, tOne - 0.2)); F.show(e.chip, F.rise(t, tGive + 0.3), 10);
      var n = Math.round(F.count(t, tM, dM, 81, 99)), p = Math.round(F.count(t, tM, dM, 76.4, 93.4));
      F.txt(e.pct, p + '%'); e.pl.innerHTML = 'of non-responsive <b>cleared</b><br>' + n + ' of 106' + (t >= tM ? ', with the roster' : '');
      F.show(e.pct, F.rise(t, tModel - 0.1)); F.show(e.pl, F.rise(t, tModel + 0.1)); F.fade(e.leg, F.rise(t, tIn + 1.4)); F.fade(e.note, F.rise(t, tGive + 0.6));
      F.fade(e.ax, F.span(t, tIn + 1.2, end, 0.8, 0.4));
      F.show(e.g1, F.span(t, tModel + 0.4, tM - 0.1), 8); F.show(e.g2, F.rise(t, t93 + 0.15), 8);
    } });
});
