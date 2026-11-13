// Beat 8: the close. The two requests stay for the scope line, then the dots spell the two words the whole thing turns on.
F.scene(function () {
  var W = F.world, L = F.L, sh = F.sh, e = {};
  var s0 = F.seg('s8').start, tDesk = F.cue('s8', 'desktop,') - 0.24, tLaw = F.cue('s8', 'lawyer') - 0.24, tSo = F.cue('s8', 'So:'), tNot = F.cue('s8', 'Not'), tEnd = F.seg('s8').end,
    tIn = s0 - 0.4, tW = tSo - 0.9, tTitle = tEnd + 0.75;
  var wd = L.words(268, 632), two = F.lays.two;
  W.key(tIn, F.lays.two, { dur: 0.7 });
  W.key(tW, wd, { dur: 1.5, stg: 1.0, ord: W.ord.by(function (i) { return -two.y[i] + 160 * W.u[i]; }), arc: 60, lift: 0.35 });
  W.cam(tIn, 1, 540, 675, 1.2); W.cam(tW, 1, 540, 675, 1.6); W.cam(tW + 1.8, 1.035, 540, 668, 9, F.eo);
  F.snd(s0, 'tick', 1); F.snd(tDesk, 'tick', 1); F.snd(tLaw, 'tick', 1); F.snd(tW - 0.5, 'rise', 1); F.snd(tW + 0.1, 'whoosh', 0.9); F.snd(tW + 2.4, 'chime', 0.9);
  F.snd(tNot, 'thud', 1); F.snd(tTitle, 'chime', 1);
  var chip = function (p, html) { return F.h('div', { cls: 'chip', style: 'font-size:34px;padding:17px 24px;color:var(--ink);opacity:0' }, p, html); };
  F.act({ id: 'b8', start: tIn + 0.2, end: 1e9, kick: 'The bottom line',
    build: function (el) {
      e.row = F.h('div', { cls: 'abs', style: 'left:60px;top:136px;display:flex;gap:18px' }, el);
      e.c = [chip(e.row, '2 requests'), chip(e.row, '1 desktop'), chip(e.row, '1 lawyer')];
      e.sub = F.h('div', { cls: 'abs t', style: 'left:60px;top:226px;font-size:25px' }, el, 'Test labels: an AI first pass, with the close calls decided by one lawyer.');
      e.title = F.h('div', { cls: 'abs h1', style: 'left:60px;top:132px;font-size:74px' }, el, 'One word is enough.');
      e.p1 = F.h('div', { cls: 'abs h1', style: 'left:60px;top:800px;font-size:47px;line-height:1.2;font-weight:400;color:var(--ink)' }, el, 'A promising first pass that keeps<br>the records in the building.');
      e.p2 = F.h('div', { cls: 'abs h1', style: 'left:60px;top:938px;font-size:60px' }, el, 'Not a replacement for review.');
      e.rule = F.h('div', { cls: 'abs', style: 'left:60px;top:1020px;height:4px;width:0;background:var(--gold);border-radius:2px' }, el);
      e.foot = F.h('div', { cls: 'abs note', style: 'left:60px;top:1150px;font-size:19px;white-space:normal;width:970px;line-height:1.55' }, el,
        '496 request-and-email pairs from two California public records requests.<br>qwen3.5:4b, qwen3.5:9b, qwen3.8:27b and their d3 decision models, run with Ollama on one desktop. Jev by hosted API.<br>Every email and name shown was invented for this video. The narration is a synthetic voice.');
    },
    draw: function (t) {
      var out = 1 - F.rise(t, tTitle - 0.5, 0.4);
      [s0 - 0.05, tDesk, tLaw].forEach(function (a, k) { F.show(e.c[k], F.rise(t, a, 0.35) * out, 12); });
      F.fade(e.sub, F.rise(t, tLaw + 0.6) * out); F.show(e.title, F.rise(t, tTitle, 0.7), 14);
      F.show(e.p1, F.rise(t, tSo + 0.85, 0.6)); F.show(e.p2, F.rise(t, tNot - 0.05, 0.45));
      e.rule.style.width = 880 * F.eo(F.lin(t, tNot + 0.5, tNot + 1.4)) + 'px';
      F.fade(e.foot, F.rise(t, tEnd + 0.5, 0.8));
    } });
});
