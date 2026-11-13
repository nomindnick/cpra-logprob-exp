// Act B: the race (narration segment s4). Lanes play in real time at the 27B model's median times; then the timing chart.
(function () {
  var F = window.F, FD = window.FD, h = F.h, E = FD.emails.yes;
  var s4 = F.seg('s4'), s5 = F.seg('s5');
  var A0 = s4.start - 0.4, T0 = A0 + 0.6, LP = FD.time.lp[2], JS = FD.time.json[2];
  var T = { chart: Math.max(F.cue('s4', '2.6 to') - 0.35, T0 + JS + 0.5) };
  var RAW = E.json_raw.replace(/\s*\n\s*/g, ' ').replace(/^\{ /, '{').replace(/ \}$/, '}');
  var el = {}, lanes = [];
  var fmt = function (x) { return x.toFixed(2); };
  var ratio = function (i) { var a = FD.time.json[i] / FD.time.lp[i], b = FD.time.jsonR[i] / FD.time.lp[i]; return a.toFixed(1) + '–' + b.toFixed(1) + '×'; };
  var sw = function (c) { return '<i style="display:inline-block;width:18px;height:18px;border-radius:4px;background:' + c + ';margin-right:9px;vertical-align:-2px"></i>'; };

  F.act({
    id: 'b', start: A0, end: s5.start - 0.4,
    kick: function () { return '04 · The race'; },
    build: function (root) {
      h('div', { cls: 'abs', style: 'left:60px;top:148px;width:960px;font:500 50px/1.2 var(--display)' }, root, 'Same model, same email.<br>Two ways to get an answer.');
      el.race = h('div', { cls: 'abs', style: 'left:0;top:0;width:1080px' }, root);
      h('div', { cls: 'abs mono', style: 'left:60px;top:296px;font-size:24px;color:var(--ink3)' }, el.race, 'Real time, at the median speed of ' + FD.model);
      [['Read the odds', 350, 216, LP, true], ['Write a verdict', 590, 500, JS, false]].forEach(function (d) {
        var c = h('div', { cls: 'card', style: 'left:60px;top:' + d[1] + 'px;width:960px;height:' + d[2] + 'px;padding:28px 34px' }, el.race), o = { end: d[3], hero: d[4] };
        h('div', { cls: 'lab' + (d[4] ? ' g' : ''), style: 'font-size:25px;margin-top:8px' }, c, d[0]);
        o.clock = h('div', { cls: 'abs mono', style: 'right:34px;top:16px;font-size:60px;font-weight:600' }, c, '');
        o.track = h('div', { cls: 'abs', style: 'left:34px;right:34px;top:98px;height:8px;border-radius:4px;background:var(--sunk);overflow:hidden' }, c);
        o.fill = h('div', { style: 'height:100%;width:0;background:' + (d[4] ? 'var(--gold)' : 'var(--ink3)') }, o.track);
        o.status = h('div', { cls: 'abs mono', style: 'left:34px;top:128px;font-size:26px;color:var(--ink3)' }, c, '');
        o.out = h('div', { cls: 'abs mono', style: 'left:34px;right:34px;top:' + (d[4] ? 126 : 176) + 'px;font-size:' + (d[4] ? 32 : 27) + 'px;line-height:1.48;color:var(--ink2);word-break:break-word' }, c, '');
        lanes.push(o);
      });
      // chart: median seconds per email, three model sizes
      el.chart = h('div', { cls: 'abs', style: 'left:60px;top:306px;width:960px;height:780px' }, root);
      h('div', { style: 'display:flex;justify-content:space-between;align-items:center' }, el.chart,
        '<span class="lab" style="font-size:24px">Median seconds per email</span><span style="font-size:25px;color:var(--ink2)">' + sw('var(--gold)') + 'read the odds &nbsp;&nbsp;' + sw('var(--ink3)') + 'write a verdict</span>');
      el.bars = FD.time.sizes.map(function (sz, i) {
        var y = 78 + i * 196, sc = 700 / 7.2, o = {};
        h('div', { cls: 'abs mono', style: 'left:0;top:' + y + 'px;font-size:40px;font-weight:600' }, el.chart, sz);
        o.r = h('div', { cls: 'abs', style: 'right:0;top:' + (y - 8) + 'px;text-align:right;font:700 54px/1.1 var(--display)' }, el.chart, ratio(i) + ' <span style="font:400 25px var(--body);color:var(--ink2)">as long</span>');
        o.a = h('div', { cls: 'abs', style: 'left:0;top:' + (y + 66) + 'px;height:32px;border-radius:0 4px 4px 0;background:var(--gold)' }, el.chart);
        o.b = h('div', { cls: 'abs', style: 'left:0;top:' + (y + 104) + 'px;height:32px;border-radius:0 4px 4px 0;background:var(--ink3)' }, el.chart);
        o.b2 = h('div', { cls: 'abs', style: 'top:' + (y + 104) + 'px;height:32px;border-radius:0 4px 4px 0;background:var(--ink3);opacity:.45' }, el.chart);
        o.la = h('div', { cls: 'abs mono', style: 'top:' + (y + 65) + 'px;font-size:28px;font-weight:500;color:var(--ink)' }, el.chart, fmt(FD.time.lp[i]) + ' s');
        o.lb = h('div', { cls: 'abs mono', style: 'top:' + (y + 103) + 'px;font-size:28px;color:var(--ink2)' }, el.chart, fmt(FD.time.json[i]) + '–' + fmt(FD.time.jsonR[i]) + ' s');
        o.w = [FD.time.lp[i] * sc, FD.time.json[i] * sc, FD.time.jsonR[i] * sc];
        return o;
      });
      h('div', { cls: 'abs', style: 'left:0;top:676px;width:960px;font-size:25px;line-height:1.36;color:var(--ink3)' }, el.chart,
        'Two verdict formats: answer first, or reasons first. The 4B and 9B verdict runs used a larger batch setting, which is part of their gap.');
      F.snd(A0 + 0.1, 'whoosh', 0.6); F.snd(T0 + LP, 'chime', 0.9); F.snd(T0 + LP + 0.05, 'type', 0.45); F.snd(T0 + JS, 'thud', 0.6); F.snd(T.chart, 'pop', 0.6);
    },
    draw: function (t) {
      var rt = t - T0, dots = '...'.slice(0, 1 + Math.floor(Math.max(0, rt) * 3) % 3);
      lanes.forEach(function (o) {
        var c = F.clamp(rt, 0, o.end), done = rt >= o.end, reading = rt < LP;
        o.clock.textContent = c.toFixed(2) + ' s'; o.clock.style.color = done ? (o.hero ? 'var(--gold)' : 'var(--ink)') : 'var(--ink2)';
        o.fill.style.width = (c / JS * 100) + '%';
        if (o.hero) {
          o.status.textContent = rt < 0 ? '' : reading ? 'reading the request and the email' + dots : '';
          o.out.innerHTML = done ? '<span class="tok" style="font-size:32px;padding:5px 16px;border-color:var(--pos)">yes</span> &nbsp;score <b style="color:var(--gold)">0.9999</b> &nbsp;·&nbsp; done' : '';
        } else {
          o.status.textContent = rt < 0 ? '' : reading ? 'reading the request and the email' + dots : done ? 'done' : 'writing' + dots;
          var n = Math.round(F.lin(rt, LP, JS) * RAW.length);
          o.out.textContent = RAW.slice(0, n) + (n > 0 && !done ? '▌' : '');
        }
      });
      F.show(el.race, 1 - F.lin(t, T.chart - 0.3, T.chart), 0);
      F.show(el.chart, F.rise(t, T.chart, 0.5), 20);
      el.bars.forEach(function (o, i) {
        var g = F.rise(t, T.chart + 0.15 + i * 0.22, 0.7);
        o.a.style.width = Math.max(2, o.w[0] * g) + 'px'; o.b.style.width = Math.max(2, o.w[1] * g) + 'px';
        o.b2.style.left = (o.w[1] * g) + 'px'; o.b2.style.width = ((o.w[2] - o.w[1]) * g) + 'px';
        o.la.style.left = (o.w[0] * g + 12) + 'px'; o.lb.style.left = (o.w[2] * g + 12) + 'px';
        o.la.style.opacity = o.lb.style.opacity = g; o.r.style.opacity = F.rise(t, T.chart + 0.5 + i * 0.22, 0.4);
      });
    }
  });
})();
