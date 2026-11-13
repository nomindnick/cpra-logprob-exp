// Act C: the sort and the cautions (narration segments s5, s6). 496 anonymous dots: label and two scores each.
(function () {
  var F = window.F, FD = window.FD, h = F.h, D = FD.dots;
  var s5 = F.seg('s5'), s6 = F.seg('s6'), s7 = F.seg('s7');
  var A0 = s5.start - 0.4;
  var T = {
    table: F.cue('s5', 'sorted the pile') + 0.5, round: F.cue('s5', 'a few round') - 0.2, spread: F.cue('s5', 'The odds spread'), first: F.cue('s5', 'likeliest first'),
    tableOut: s6.start - 0.35, cut: F.cue('s6', 'A good ranking'), unsafe: F.cue('s6', 'safe cutoff') + 0.25, call: F.cue('s6', "lawyer's call"),
    lim: F.cue('s6', 'And this was') - 0.1, c1: F.cue('s6', 'one family'), c2: F.cue('s6', 'two requests'), c3: F.cue('s6', 'one lawyer settling')
  };
  var CW = 1000, CH = 500, PADX = 30, P = 11, R = 4.6, L = 11.5, UP = 258, DOWN = 304, CAP = [16, 22], NC = Math.floor((CW - 2 * PADX) / P) + 1;
  var lg = function (s) { s = F.clamp(s, 1e-5, 1 - 1e-5); return F.clamp(Math.log(s / (1 - s)), -L, L); };
  var xOf = function (s) { return PADX + (lg(s) + L) / (2 * L) * (CW - 2 * PADX); };
  function layout(k) {
    var pos = new Array(D.length), fill = [{}, {}];
    D.map(function (d, i) { return i; }).filter(function (i) { return D[i][k] != null; })
      .sort(function (a, b) { return D[a][k] - D[b][k] || a - b; })
      .forEach(function (i) {
        var lab = D[i][0], c0 = Math.round((xOf(D[i][k]) - PADX) / P), f = fill[lab], c = c0, n;
        for (n = 0; n < 2 * NC; n++) { c = c0 + (n % 2 ? 1 : -1) * Math.ceil(n / 2); if (c >= 0 && c < NC && (f[c] || 0) < CAP[lab]) break; }
        var row = f[c] || 0; f[c] = row + 1;
        pos[i] = [PADX + c * P, lab ? UP - R - row * P : DOWN + R + row * P];
      });
    return pos;
  }
  var LA = layout(1), LB = layout(2), el = {}, cv, ctx, rnd = [], r = F.rng(5);
  D.forEach(function () { rnd.push(r()); });
  var KF = [[T.cut, 0.5], [T.unsafe + 0.9, 0.99], [T.call + 0.2, 0.0687]];
  var cutAt = function (t) {
    if (t <= KF[0][0]) return KF[0][1];
    for (var i = 1; i < KF.length; i++) if (t < KF[i][0]) { var p = F.eio(F.lin(t, KF[i - 1][0] + (i === 1 ? 0.5 : 0.35), KF[i][0])), a = lg(KF[i - 1][1]), b = lg(KF[i][1]), v = F.mix(a, b, p); return 1 / (1 + Math.exp(-v)); }
    return KF[KF.length - 1][1];
  };
  var NPOS = D.filter(function (d) { return d[0] === 1; }).length, NNEG = D.length - NPOS;

  F.act({
    id: 'c', start: A0, end: s7.start - 0.4,
    kick: function (t) { return t < T.tableOut ? '05 · The sort' : '06 · Two cautions'; },
    build: function (root) {
      h('div', { cls: 'abs lab g', style: 'left:60px;top:136px;font-size:24px' }, root, '496 test pairs, scored two ways by ' + FD.model);
      h('div', { cls: 'abs', style: 'left:60px;top:174px;font-size:27px;color:var(--ink2)' }, root,
        '<i style="display:inline-block;width:18px;height:18px;border-radius:9px;background:var(--pos);margin-right:9px;vertical-align:-1px"></i>responsive (' + NPOS + ') &nbsp;&nbsp;&nbsp;<i style="display:inline-block;width:18px;height:18px;border-radius:9px;background:var(--neg);margin-right:9px;vertical-align:-1px"></i>not responsive (' + NNEG + ')');
      el.tA = h('div', { cls: 'abs', style: 'left:60px;top:224px;width:960px;font:500 46px/1.2 var(--display)' }, root, 'Sorted by written confidence');
      el.tB = h('div', { cls: 'abs', style: 'left:60px;top:224px;width:960px;font:500 46px/1.2 var(--display)' }, root, 'Sorted by first-word odds');
      cv = h('canvas', { width: CW, height: CH, style: 'left:40px;top:300px' }, root); ctx = cv.getContext('2d');
      el.ends = h('div', { cls: 'abs mono', style: 'left:60px;top:806px;width:960px;display:flex;justify-content:space-between;font-size:24px;color:var(--ink3)' }, root, '<span>← less likely responsive</span><span>more likely responsive →</span>');
      el.start = h('div', { cls: 'abs mono', style: 'right:60px;top:306px;font-size:27px;font-weight:600;color:var(--gold)' }, root, 'start reading here ↓');
      // ranking-quality table
      el.table = h('div', { cls: 'abs', style: 'left:60px;top:862px;width:960px' }, root);
      h('div', { cls: 'lab', style: 'margin-bottom:14px;font-size:23px' }, el.table, 'Ranking quality (AUROC) · 1.00 is a perfect sort');
      el.trows = FD.auroc.sizes.map(function (sz, i) {
        return h('div', { cls: 'mono', style: 'display:grid;grid-template-columns:120px 500px 1fr;align-items:baseline;font-size:35px;height:64px;border-top:1px solid var(--rule);padding-top:11px' }, el.table,
          '<b>' + sz + '</b><span style="color:var(--ink2)">' + FD.auroc.json[i].toFixed(3) + ' – ' + FD.auroc.jsonR[i].toFixed(3) + ' <span style="font-size:24px;color:var(--ink3)">written</span></span><span><b style="color:var(--gold)">' + FD.auroc.lp[i].toFixed(3) + '</b> <span style="font-size:24px;color:var(--ink3)">odds</span></span>');
      });
      // cutoff counters
      el.stats = h('div', { cls: 'abs', style: 'left:60px;top:858px;width:960px' }, root);
      h('div', { style: 'display:grid;grid-template-columns:1fr 1fr;gap:20px' }, el.stats,
        '<div class="card" style="position:static;padding:20px 24px"><div class="lab" style="font-size:23px">Set aside, unread</div><div class="mono" style="font-size:50px;font-weight:600;margin-top:10px;white-space:nowrap"><span id="nAside">0</span> <span style="font-size:23px;font-weight:400;color:var(--ink3)">of ' + NNEG + ' not responsive</span></div></div>' +
        '<div class="card" style="position:static;padding:20px 24px"><div class="lab" style="font-size:23px;color:var(--stamp)">Responsive, missed</div><div class="mono" style="font-size:50px;font-weight:600;margin-top:10px;color:var(--stamp);white-space:nowrap"><span id="nMiss">0</span> <span style="font-size:23px;font-weight:400;color:var(--ink3)">of ' + NPOS + ' responsive</span></div></div>');
      el.note = h('div', { style: 'margin-top:18px;font-size:28px;line-height:1.34;color:var(--ink2)' }, el.stats, 'This line was placed with the answers in hand. A new request has none, and the right cutoff differed between the two requests tested.');
      // limits
      el.lims = [['1', 'model family', 'stock Qwen in three sizes: 4B, 9B, 27B'], ['2', 'records requests', '496 request and email test pairs'], ['1', 'lawyer', 'AI pre-labels, with the close calls decided by one lawyer']].map(function (d, i) {
        return h('div', { cls: 'abs', style: 'left:60px;top:' + (858 + i * 84) + 'px;width:960px;display:flex;align-items:center;gap:28px;height:74px' }, root,
          '<span style="font:700 68px/1 var(--display);color:var(--gold);width:56px;text-align:center">' + d[0] + '</span><span><span style="font:600 33px/1.15 var(--body);display:block">' + d[1] + '</span><span style="font-size:26px;color:var(--ink2)">' + d[2] + '</span></span>');
      });
      F.snd(A0 + 0.15, 'whoosh', 0.6); F.snd(T.spread - 0.05, 'rise', 0.8); F.snd(T.cut, 'pop', 0.6); F.snd(T.call + 0.2, 'thud', 0.6);
      F.snd(T.c1, 'pop', 0.5); F.snd(T.c2, 'pop', 0.5); F.snd(T.c3, 'pop', 0.5);
    },
    draw: function (t) {
      var i, m = F.lin(t, T.spread, T.spread + 0.5);
      el.tA.style.opacity = 1 - m; el.tB.style.opacity = m;
      el.start.style.opacity = F.rise(t, T.first - 0.1, 0.35) * (1 - F.lin(t, T.cut - 0.4, T.cut));
      var cutOn = F.rise(t, T.cut, 0.4), cut = cutAt(t), cx = xOf(cut), aside = 0, miss = 0;
      ctx.clearRect(0, 0, CW, CH);
      // axis band
      ctx.strokeStyle = '#3a4760'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(PADX - 8, UP + 4.5); ctx.lineTo(CW - PADX + 8, UP + 4.5); ctx.moveTo(PADX - 8, DOWN - 4.5); ctx.lineTo(CW - PADX + 8, DOWN - 4.5); ctx.stroke();
      ctx.font = '500 22px "IBM Plex Mono"'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      var band = (UP + DOWN) / 2 + 1, ra = F.rise(t, T.round, 0.4);
      ctx.fillStyle = '#b1bccd'; ctx.globalAlpha = (1 - m) * F.rise(t, A0 + 0.9, 0.4);
      [[0.00001, '0', 'left'], [0.035, '0.02 – 0.05', 'center'], [0.95, '0.95', 'center'], [0.99999, '1.0', 'right']].forEach(function (d) { ctx.textAlign = d[2]; ctx.fillText(d[1], xOf(d[0]) + (d[2] === 'left' ? -6 : d[2] === 'right' ? 6 : 0), band); });
      ctx.textAlign = 'center'; ctx.globalAlpha = (1 - m) * ra; ctx.fillStyle = '#ffce40'; ctx.font = '600 25px "IBM Plex Mono"';
      ctx.fillText('nothing', xOf(0.5), UP - 118); ctx.fillText('in between', xOf(0.5), UP - 86);
      ctx.strokeStyle = '#ffce40'; ctx.setLineDash([5, 5]); ctx.beginPath(); ctx.lineWidth = 2; ctx.moveTo(xOf(0.05) + 50, UP - 58); ctx.lineTo(xOf(0.95) - 44, UP - 58); ctx.stroke(); ctx.setLineDash([]);
      ctx.globalAlpha = m; ctx.fillStyle = '#b1bccd'; ctx.font = '500 22px "IBM Plex Mono"';
      [[0.0001, '0.0001'], [0.01, '0.01'], [0.5, '0.5'], [0.99, '0.99'], [0.9999, '0.9999']].forEach(function (d) { ctx.fillText(d[1], xOf(d[0]), band); });
      ctx.globalAlpha = 1;
      // dots
      for (i = 0; i < D.length; i++) {
        var a = LA[i], b = LB[i], mv = F.eio(F.lin(t, T.spread + rnd[i] * 0.7, T.spread + rnd[i] * 0.7 + 1.1));
        var x = a ? F.mix(a[0], b[0], mv) : b[0], y = a ? F.mix(a[1], b[1], mv) : b[1];
        var al = F.rise(t, A0 + 0.35 + rnd[i] * 0.6, 0.35) * (a ? 1 : mv), lab = D[i][0], below = cutOn > 0 && D[i][2] < cut;
        if (below) { if (lab) miss++; else aside++; }
        if (al <= 0) continue;
        ctx.globalAlpha = al * (below && !lab ? F.mix(1, 0.28, cutOn) : 1);
        ctx.fillStyle = lab ? '#3987e5' : '#d95926';
        ctx.beginPath(); ctx.arc(x, y, R, 0, 6.2832); ctx.fill();
        if (below && lab) { ctx.globalAlpha = cutOn; ctx.strokeStyle = '#f08a80'; ctx.lineWidth = 2.2; ctx.beginPath(); ctx.arc(x, y, R + 2.4, 0, 6.2832); ctx.stroke(); }
      }
      ctx.globalAlpha = 1;
      if (cutOn > 0) {
        ctx.globalAlpha = cutOn; ctx.fillStyle = 'rgba(11,16,25,.34)'; ctx.fillRect(0, 0, cx, CH);
        ctx.strokeStyle = '#ffce40'; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(cx, 6); ctx.lineTo(cx, CH - 6); ctx.stroke();
        ctx.fillStyle = '#ffce40'; ctx.font = '600 26px "IBM Plex Mono"'; ctx.textAlign = cx > CW - 260 ? 'right' : 'left';
        ctx.fillText('cutoff ' + (cut >= 0.1 ? cut.toFixed(2) : cut.toFixed(3)), cx + (cx > CW - 260 ? -12 : 12), CH - 20);
        ctx.globalAlpha = 1;
      }
      // table
      F.show(el.table, Math.min(F.rise(t, T.table, 0.45), 1 - F.lin(t, T.tableOut, T.tableOut + 0.3)), 16);
      el.trows.forEach(function (rw, k) { rw.style.opacity = F.rise(t, T.table + 0.15 + k * 0.18, 0.35); });
      // counters and note
      var so = 1 - F.lin(t, T.lim - 0.3, T.lim);
      F.show(el.stats, Math.min(cutOn, so), 16);
      document.getElementById('nAside').textContent = aside; document.getElementById('nMiss').textContent = miss;
      el.note.style.opacity = F.rise(t, T.call + 0.3, 0.45);
      el.lims.forEach(function (c, k) { F.show(c, F.rise(t, [T.c1, T.c2, T.c3][k] - 0.1, 0.4), 16); });
    }
  });
  F.cutCheck = function (c) { var a = 0, m = 0; D.forEach(function (d) { if (d[2] < c) { if (d[0]) m++; else a++; } }); return [a, m]; };
})();
