// Beat 1: the result first. A pile of 496 emails; a small model sorts them; a line sets most of the non-responsive ones aside.
F.scene(function () {
  var W = F.world, L = F.L, FD = window.FD, D = FD.dots, N = FD.n, C = W.C, cut = FD.cut.lp, sh = F.sh;
  var heap = L.heap();
  var fall = W.mod(heap, function (i, o) { o.y[i] -= 380 + W.u[i] * 720 + heap.m.rows[i] * 7; o.x[i] += (W.u[(i * 7 + 3) % N] - 0.5) * 90; });
  var HO = sh.HO = { key: 'lp', cy: 772, pitch: 13, cap: 28, cut: cut.lo, pass: function (d) { return d.pp; } };
  var hC = L.hist(HO);
  var hN = W.mod(hC, function (i, o) { W.col(o, i, C.neu); o.a[i] = 0.92; });
  var hCut = W.mod(hC, function (i, o) { if (!D[i].pp) o.a[i] = 0.3; });
  F.lays.hC = hC; F.lays.hCut = hCut; var m = sh.m = hC.m;
  var tTwo = F.cue('s1', 'and two'), tSome = F.cue('s1', 'Someone'), tUnless = F.cue('s1', 'Unless'), tSorts = F.cue('s1', 'sorts'),
    tThis = F.cue('s1', 'This one'), t77 = F.cue('s1', '77'), tKept = F.cue('s1', 'kept'), t98 = F.cue('s1', '98'), end = F.seg('s2').start - 0.15;
  var fallEase = function (p) { return p < 0.8 ? (p / 0.8) * (p / 0.8) : 1 - 0.03 * Math.sin(Math.PI * (p - 0.8) / 0.2); };
  var tFly = tUnless + 0.25, tCol = tSorts + 0.2, tLine = tThis - 0.05, tDim = t77 - 0.55, axEnd = F.seg('s4').start - 0.45;
  W.key(0, fall);
  W.key(0.02, heap, { dur: 0.95, stg: 1.7, ord: W.ord.by(function (i) { return heap.m.rows[i] + W.u[i] * 7; }), ease: fallEase });
  W.key(tFly, hN, { dur: 1.7, stg: 1.5, ord: W.ord.x(hN, 260), arc: 80, lift: 0.3 });
  W.key(tCol, hC, { dur: 0.45, stg: 0.95, ord: W.ord.x(hC) });
  W.key(tDim, hCut, { dur: 0.6, stg: 0.25, ord: W.ord.x(hC) });
  W.cam(0, 1.045, 540, 700, 0.01); W.cam(0.05, 1, 540, 675, 7.5, F.eo); W.cam(tFly, 1.03, 540, 700, 12);
  F.snd(0.3, 'scatter', 1); F.snd(tFly, 'whoosh', 1); F.snd(tFly + 1.3, 'whoosh', 0.6); F.snd(tCol + 0.1, 'rise', 0.7);
  F.snd(tLine, 'thud', 1); F.snd(t77, 'pop', 1); F.snd(t98, 'chime', 0.9);
  // the cutoff line lives on one track for the whole film
  var yT = sh.lineTop = m.cy - m.band - 200, yB = sh.lineBot = m.bot + 14;
  sh.cut = F.track({ x: m.cutX, y1: yT, y2: yT, a: 0 });
  sh.cut.key(tLine - 0.02, { a: 1 }, 0.02).key(tLine, { y2: yB }, 0.5, F.eo);
  W.over.push(function (c, t) { F.cutDraw(c, sh.cut.at(t)); });
  var axis, e = {};
  W.under.push(function (c, t) { if (t < axEnd + 0.1) F.axisLine(c, m, axis, F.span(t, tFly + 1.5, axEnd, 1.0, 0.45)); });
  F.act({ id: 'ax', start: tFly + 1.5, end: axEnd, fin: 1.0, fout: 0.45,
    build: function (el, wl) { axis = F.axisBuild(wl, m, { titles: ['CHANCE OF “YES”', 'STATED CONFIDENCE'] }); },
    draw: function (t) { var p = sh.axMix ? sh.axMix(t) : 0; axis._titles[0].style.opacity = 1 - p; axis._titles[1].style.opacity = p; } });
  F.act({ id: 'b1', start: 0, end: end + 0.25, kick: 'The result first',
    build: function (el, wl) {
      e.n = F.h('div', { cls: 'abs big', style: 'left:56px;top:128px' }, el, '496');
      e.em = F.h('div', { cls: 'abs h1', style: 'left:346px;top:176px;font-size:76px' }, el, 'emails');
      e.two = F.h('div', { cls: 'abs h2', style: 'left:60px;top:282px;font-size:36px' }, el, 'from <b>two real</b> public records requests');
      e.some = F.h('div', { cls: 'abs h1', style: 'left:60px;top:356px;font-size:50px;font-weight:500' }, el, 'Someone has to read every one.');
      e.tag = F.h('div', { cls: 'abs lab g', style: 'left:60px;top:132px' }, el, 'qwen3.8:27b · one desktop · one-word score');
      e.unless = F.h('div', { cls: 'abs h1', style: 'left:60px;top:172px;white-space:normal;width:960px' }, el, 'Unless a small model sorts them first.');
      e.sa = F.h('div', { cls: 'abs', style: 'left:60px;top:170px' }, el, '<div class="mid" id="b1n77">77%</div><div class="t" style="margin-top:12px"><span class="sw" style="background:var(--neg)"></span>of non-responsive emails<br><b>set aside</b> · 160 of 207</div>');
      e.sb = F.h('div', { cls: 'abs', style: 'left:570px;top:170px' }, el, '<div class="mid" id="b1n98">98%</div><div class="t" style="margin-top:12px"><span class="sw" style="background:var(--pos)"></span>of responsive emails<br><b>kept</b> · 284 of 289</div>');
      e.leg = F.legend(el, 60, 384);
      e.note = F.h('div', { cls: 'abs note', style: 'left:60px;top:1082px' }, el, 'Cutoff set with the answers in hand.');
      e.lSet = F.h('div', { cls: 'abs lab', style: 'right:' + (F.W - m.cutX + 16) + 'px;top:' + (yT + 4) + 'px;color:var(--ink2)' }, wl, '← set aside');
      e.lKeep = F.h('div', { cls: 'abs lab g', style: 'left:' + (m.cutX + 16) + 'px;top:' + (yT + 4) + 'px' }, wl, 'keep for review →');
    },
    draw: function (t) {
      F.show(e.n, F.span(t, 0.3, tUnless - 0.1, 0.5)); F.show(e.em, F.span(t, 0.5, tUnless - 0.1, 0.5));
      F.txt(e.n, String(Math.round(F.count(t, 0.25, 2.3, 0, 496))));
      F.show(e.two, F.span(t, tTwo - 0.1, tUnless - 0.1)); F.show(e.some, F.span(t, tSome - 0.1, tUnless - 0.1));
      F.show(e.tag, F.rise(t, tUnless + 0.5)); F.show(e.unless, F.span(t, tUnless + 0.15, tThis - 0.2));
      F.show(e.sa, F.rise(t, t77 - 0.5)); F.show(e.sb, F.rise(t, tKept - 0.3));
      F.txt(document.getElementById('b1n77'), Math.round(F.count(t, t77 - 0.45, 0.9, 0, 77)) + '%');
      F.txt(document.getElementById('b1n98'), Math.round(F.count(t, tKept - 0.25, 0.9, 0, 98)) + '%');
      F.fade(e.leg, F.rise(t, tCol + 0.3)); F.fade(e.note, F.rise(t, tLine + 0.5));
      F.fade(e.lSet, F.rise(t, tLine + 0.4)); F.fade(e.lKeep, F.rise(t, tLine + 0.4));
    } });
});
