// Shared chart furniture: value tracks, the log-odds axis, the cutoff line, the legend and number helpers.
(function () {
  var F = window.F, W = F.world;
  F.lays = {}; F.sh = {};
  // a track: named values that ease from one keyed state to the next (a pure function of t)
  F.track = function (init) {
    var ks = [], tr = {
      key: function (t, to, dur, ease) { ks.push({ t: t, to: to, dur: dur || 0.6, ease: ease || F.eio }); ks.sort(function (a, b) { return a.t - b.t; }); return tr; },
      at: function (t) { var s = {}, f, j, k, e; for (f in init) s[f] = init[f]; for (j = 0; j < ks.length && ks[j].t < t; j++) { k = ks[j]; e = k.ease(F.lin(t, k.t, k.t + k.dur)); for (f in k.to) s[f] += (k.to[f] - s[f]) * e; } return s; }
    };
    return tr;
  };
  var TICKS = [[-2, '1%'], [0, '50%'], [2, '99%'], [4, '99.99%']];
  // HTML labels for the axis of a histogram layout (world layer): titles at the left end and four ticks, all in the band
  F.axisBuild = function (parent, m, o) {
    o = o || {}; var g = F.h('div', { style: 'position:absolute;left:0;top:0' }, parent), fs = o.fs || 21, titles = o.titles || ['CHANCE OF “YES”'];
    g._gaps = []; g._titles = [];
    var put = function (x, txt, left, wchars) {
      var w = (wchars || txt.length) * fs * (left ? 0.72 : 0.605) + 16, l = left ? x : x - w / 2;
      var e = F.h('div', { cls: 'abs tick', style: 'left:' + l + 'px;top:' + (m.cy - fs / 2) + 'px;width:' + w + 'px;text-align:' + (left ? 'left' : 'center') + ';font-size:' + fs + 'px;letter-spacing:' + (left ? '.1em' : '0') }, g, txt);
      return [e, l - 2, l + w + 2];
    };
    var wmax = Math.max.apply(null, titles.map(function (s) { return s.length; }));
    titles.forEach(function (s, i) { var r = put(m.x0, s, true, wmax); g._titles.push(r[0]); if (!i) g._gaps.push([r[1], r[2]]); else r[0].style.opacity = 0; });
    (o.ticks || TICKS).forEach(function (t) { var r = put(m.X(t[0]), t[1]); g._gaps.push([r[1], r[2]]); });
    return g;
  };
  // the axis rule, broken where the labels sit
  F.axisLine = function (c, m, g, a) {
    var segs = g._gaps.slice().sort(function (p, q) { return p[0] - q[0]; }), x = m.x0, i;
    for (i = 0; i < segs.length; i++) { if (segs[i][0] > x) W.line(c, x, m.cy, segs[i][0], m.cy, '#3a4760', a, 1.5); x = Math.max(x, segs[i][1]); }
    if (x < m.x1) W.line(c, x, m.cy, m.x1, m.cy, '#3a4760', a, 1.5);
  };
  // a cutoff line from a track state {x, y1, y2, a}
  F.cutDraw = function (c, s, col) {
    if (s.a <= 0.003 || s.y2 - s.y1 < 1) return;
    c.shadowColor = col || '#ffce40'; c.shadowBlur = 14;
    W.line(c, s.x, s.y1, s.x, s.y2, col || '#ffce40', s.a, 3.5);
    c.shadowBlur = 0;
  };
  F.legend = function (parent, x, y) {
    return F.h('div', { cls: 'abs t', style: 'left:' + x + 'px;top:' + y + 'px;font-size:25px' }, parent,
      '<span class="sw" style="background:var(--pos)"></span>responsive<span style="display:inline-block;width:34px"></span><span class="sw" style="background:var(--neg)"></span>not responsive');
  };
  F.count = function (t, a, dur, from, to) { return from + (to - from) * F.eo(F.lin(t, a, a + dur)); };
  // screen position -> world position under the camera at time t
  F.toWorld = function (t, sx, sy) { var c = W.camAt(t); return [(sx - F.W / 2) / c.s + c.x, (sy - F.H / 2) / c.s + c.y]; };
})();
