// Beat 3: three ways to ask. The same dots re-sort under each; written confidence collapses onto a few values.
F.scene(function () {
  var W = F.world, L = F.L, FD = window.FD, D = FD.dots, C = W.C, sh = F.sh, e = {};
  var s0 = F.seg('s3').start, tRead = F.cue('s3', 'Read the odds'), tUse = F.cue('s3', 'Use'), tOr = F.cue('s3', 'Or let'), tWritten = F.cue('s3', 'Written'),
    tOne = F.cue('s3', 'One model'), t43 = F.cue('s3', '43'), tFlat = F.cue('s3', 'flat'), end = F.seg('s4').start - 0.45;
  var mk = function (key, cut, pf) { var h = L.hist({ key: key, cy: 772, pitch: 13, cap: 22, capDn: 20, cut: cut.lo, pass: pf }); return W.mod(h, function (i, o) { if (!pf(D[i])) o.a[i] = 0.3; }); };
  var hD = mk('d', FD.cut.d, function (d) { return d.pd; }), hJr = mk('jr', FD.cut.jr, function (d) { return d.pj; }), hJs = mk('js', FD.cut.js, function (d) { return d.p9; });
  var is43 = function (d) { return d.l === 1 && d.jsv === 0; };
  var hJsHi = W.mod(hJs, function (i, o) { if (is43(D[i])) { o.r[i] *= 1.12; } else o.a[i] = 0.22; });
  var tM1 = tUse + 0.15, tM2 = tWritten - 0.35, tM3 = tOne + 0.1;
  W.key(tM1, hD, { dur: 1.3, stg: 0.8, ord: W.ord.x(hD, 200), arc: 46, lift: 0.25 });
  W.key(tM2, hJr, { dur: 1.2, stg: 0.7, ord: W.ord.x(hJr, 200), arc: 40, lift: 0.25 });
  W.key(tM3, hJs, { dur: 1.1, stg: 0.5, ord: W.ord.x(hJs, 200), arc: 36, lift: 0.2 });
  W.key(t43 + 0.5, hJsHi, { dur: 0.6 });
  sh.cut.key(tM1 + 0.5, { x: hD.m.cutX, y2: hD.m.bot + 14 }, 1.1).key(tM2 + 0.4, { x: hJr.m.cutX, y2: hJr.m.bot + 14 }, 1.1).key(tM3 + 0.3, { x: hJs.m.cutX, y2: hJs.m.bot + 14 }, 1.0).key(end - 0.2, { a: 0 }, 0.4);
  sh.axMix = function (t) { return F.lin(t, tM2 + 0.2, tM2 + 0.9); };
  W.cam(s0 - 0.4, 1, 540, 690, 1.5); W.cam(s0 + 1.2, 1.025, 540, 700, 15, F.eo); W.cam(t43 - 0.2, 1.05, 505, 688, 2.6);
  F.snd(s0 - 0.35, 'whoosh', 0.8); F.snd(tRead - 0.1, 'pop', 0.8); F.snd(tUse - 0.1, 'pop', 0.8); F.snd(tM1, 'whoosh', 1); F.snd(tOr - 0.1, 'pop', 0.8);
  F.snd(tOr + 0.5, 'type', 0.9, 2.9); F.snd(tM2, 'whoosh', 1); F.snd(tM2 + 1.5, 'thud', 0.7); F.snd(tM3, 'whoosh', 0.9); F.snd(t43 + 0.5, 'thud', 1);
  var chips = ['Read the odds', 'Decision model', 'Written answer'], tChip = [tRead - 0.2, tUse - 0.2, tOr - 0.2];
  var models = [[0, 'qwen3.8:27b · one-word score'], [tM1 + 0.4, 'd3-27b · decision model, same base'], [tOr, 'qwen3.8:27b · written answer, reasons first'], [tM3 + 0.3, 'qwen3.5:9b · written answer']];
  var json = '{\n  "reasoning": "Discusses the revised\n     bid tabulation for the bridge…",\n  "responsive": true,\n  "confidence": 0.95\n}';
  var m9 = hJs.m, bx = m9.x0 + 2 * m9.pitch + 22, dd = sh.demoDot;
  F.act({ id: 'b3', start: s0 - 0.25, end: end, kick: 'Three ways to ask',
    build: function (el, wl) {
      e.h = F.h('div', { cls: 'abs h1', style: 'left:60px;top:124px' }, el, 'Three ways to ask');
      e.rn = F.h('div', { cls: 'abs mid', style: 'right:60px;top:118px' }, el, '77%');
      e.rl = F.h('div', { cls: 'abs t', style: 'right:60px;top:210px;font-size:24px' }, el, 'of non-responsive cleared');
      e.chips = chips.map(function (s, k) { return F.h('div', { cls: 'abs chip', style: 'left:' + [60, 344, 646][k] + 'px;top:262px' }, el, '<span class="mono" style="color:var(--ink3);margin-right:12px">' + (k + 1) + '</span>' + s); });
      e.model = F.h('div', { cls: 'abs lab g', style: 'left:60px;top:338px' }, el, '');
      e.leg = F.legend(el, 60, 384);
      e.note = F.h('div', { cls: 'abs note', style: 'left:60px;top:1082px' }, el, 'Cutoffs set with the answers in hand, keeping 98% of responsive.');
      e.json = F.h('div', { cls: 'card', style: 'left:60px;top:436px;width:500px;height:236px;padding:16px 22px;white-space:pre;font:500 21px/1.42 var(--mono);color:var(--ink2);box-shadow:0 20px 60px #000c' }, el, '');
      e.here = F.h('div', { cls: 'abs lab g', style: 'right:60px;top:' + (sh.m.cy + sh.m.band + 46) + 'px' }, wl, 'the example email ↑');
      e.l43 = F.h('div', { cls: 'abs t', style: 'left:' + bx + 'px;top:478px;font-size:25px;line-height:1.3' }, wl, '<b style="font-size:30px">43 responsive emails</b><br>given a confidence of 0');
      e.l0 = F.h('div', { cls: 'abs t', style: 'left:' + bx + 'px;top:590px;font-size:25px;line-height:1.3' }, wl, 'To keep them, the line<br>sits at zero.<br><b>Nothing is cleared.</b>');
    },
    draw: function (t) {
      F.show(e.h, F.rise(t, s0 - 0.1));
      var v = t < tM1 + 0.7 ? 77 : t < tM2 + 0.7 ? F.count(t, tM1 + 0.7, 0.8, 77, 83) : t < tM3 + 0.6 ? F.count(t, tM2 + 0.7, 0.8, 83, 67) : F.count(t, tM3 + 0.6, 0.8, 67, 0);
      F.txt(e.rn, Math.round(v) + '%'); F.show(e.rn, F.rise(t, s0 + 0.3)); F.show(e.rl, F.rise(t, s0 + 0.45));
      var act = t >= tChip[2] ? 2 : t >= tChip[1] ? 1 : 0;
      e.chips.forEach(function (c, k) { F.show(c, F.rise(t, tChip[k], 0.4), 12); var on = k === act; c.style.borderColor = on ? '#ffce40' : '#3a4760'; c.style.color = on ? '#e8edf4' : '#8592a8'; c.style.background = on ? '#ffce4016' : '#0f162299'; });
      var mi = 0; models.forEach(function (q, k) { if (t >= q[0]) mi = k; });
      F.txt(e.model, models[mi][1]); F.fade(e.model, Math.min(F.rise(t, s0 + 0.5), mi ? F.rise(t, models[mi][0], 0.35) : 1));
      F.fade(e.leg, F.rise(t, s0 + 0.5)); F.fade(e.note, F.rise(t, s0 + 0.6));
      var pj = F.span(t, tOr + 0.35, tM2 + 0.25, 0.35, 0.35), n = Math.floor(json.length * F.lin(t, tOr + 0.6, tM2 - 0.25));
      F.show(e.json, pj, 14); F.txt(e.json, json.slice(0, n) + (n < json.length ? '▍' : ''));
      F.fade(e.here, F.span(t, s0 + 0.9, tUse - 0.25, 0.4, 0.3));
      F.show(e.l43, F.rise(t, t43 - 0.1)); F.show(e.l0, F.rise(t, tFlat - 0.3));
    } });
});
