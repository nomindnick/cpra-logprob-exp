// Beat 2: the trick. One invented email, one question; the model's odds on its first word are the score.
F.scene(function () {
  var W = F.world, FD = window.FD, dm = FD.demo, sh = F.sh, m = sh.m, e = {};
  var s0 = F.seg('s2').start, tAsk = F.cue('s2', 'Ask'), tYes = F.cue('s2', 'yes or no'), tBefore = F.cue('s2', 'Before'), tOdds = F.cue('s2', 'put odds'),
    tRead = F.cue('s2', 'Read the odds'), tStop = F.cue('s2', 'stop'), tThats = F.cue('s2', "That's"), end = F.seg('s3').start - 0.3;
  var CS = 0.66, CX = 540, CY = 398, tB = tBefore - 0.35;
  W.cam(s0 - 0.4, CS, CX, CY, 1.5);
  F.snd(s0 - 0.35, 'whoosh', 0.8); F.snd(tAsk, 'type', 0.9, 1.4); F.snd(tB + 0.1, 'whoosh', 0.5);
  [0, 1, 2, 3].forEach(function (k) { F.snd(tOdds + k * 0.14, 'tick', 0.9); });
  F.snd(tStop, 'thud', 0.8); F.snd(tThats + 0.15, 'whoosh', 0.7); F.snd(tThats + 1.05, 'chime', 1);
  // where the example email lands on the histogram: on top of its column, like a 497th dot
  var col = Math.min(m.ncol - 1, Math.floor((dm.lo - m.lo) / (m.hi - m.lo) * m.ncol)), tx = m.x0 + (col + 0.5) * m.pitch, ty = m.cy - m.band - (m.hUp[col] + 0.5) * m.pitch;
  var sx = 262, sy = 600, tFly = tThats + 0.12, tLand = tFly + 0.95, tGone = F.cue('s3', 'Use') - 0.2;
  sh.demoDot = { x: tx, y: ty };
  W.over.push(function (c, t) {
    if (t < tFly || t > tGone + 0.6) return;
    var p = F.eio(F.lin(t, tFly, tLand)), st = F.toWorld(t, sx, sy), cam = W.camAt(t), a = 1 - F.lin(t, tGone, tGone + 0.5);
    var x = F.mix(st[0], tx, p), y = F.mix(st[1], ty, p) - Math.sin(Math.PI * p) * 150, r = F.mix(30 / cam.s, 8.5, F.eo(F.lin(t, tFly, tLand)));
    c.shadowColor = '#ffce40'; c.shadowBlur = 22; W.disc(c, x, y, r, '#ffce40', a); c.shadowBlur = 0;
    [0, 0.5].forEach(function (d) { var q = F.lin(t, tLand + d, tLand + d + 1.1); if (q > 0 && q < 1) W.ring(c, tx, ty, 9 + q * 60, '#ffce40', (1 - q) * 0.8, 3); });
    W.ring(c, tx, ty, 15, '#ffce40', a * F.lin(t, tLand, tLand + 0.3) * 0.9, 2.5);
  });
  var esc = function (s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;'); };
  var bars = [['yes', dm.top3[0][1], '97.7%'], ['Yes', dm.top3[1][1], '1.8%'], ['The', dm.top3[2][1], '0.3%'], ['no', dm.p_no, '&lt; 0.01%']];
  F.act({ id: 'b2', start: s0 - 0.3, end: end, kick: 'The trick',
    build: function (el) {
      e.A = F.h('div', { cls: 'abs', style: 'left:0;top:0;width:1080px;height:800px' }, el);
      F.h('div', { cls: 'abs lab', style: 'left:60px;top:132px' }, e.A, 'A records request');
      F.h('div', { cls: 'abs pill', style: 'right:60px;top:122px;color:var(--gold);border-color:#ffce4077' }, e.A, 'Invented example');
      F.h('div', { cls: 'card', style: 'white-space:normal;left:60px;top:164px;width:960px;padding:18px 28px;font:400 26px/1.4 var(--body);color:var(--ink)' }, e.A, esc(dm.request));
      F.h('div', { cls: 'abs lab', style: 'left:60px;top:364px' }, e.A, 'One email from the keyword search');
      var body = dm.body.split('\n\n')[1];
      F.h('div', { cls: 'card', style: 'white-space:normal;left:60px;top:396px;width:960px;padding:16px 28px' }, e.A,
        '<div class="mono" style="font-size:20px;line-height:1.6;color:var(--ink3)">FROM&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:var(--ink2)">' + esc(dm.from) + '</span><br>DATE&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:var(--ink2)">' + dm.date + '</span><br>SUBJECT&nbsp;<span style="color:var(--ink)">' + esc(dm.subject) + '</span></div>' +
        '<div style="height:1px;background:var(--rule);margin:14px 0"></div><div style="font:400 25px/1.4 var(--body);color:var(--ink2)">' + esc(body) + '</div>');
      e.q = F.h('div', { cls: 'abs h1', style: 'left:60px;top:0;font-size:50px' }, el, 'Is this email responsive?');
      e.yn = F.h('div', { cls: 'abs', style: 'left:792px;top:647px' }, el, '<span class="chip mono" style="font-size:28px;color:var(--ink);padding:8px 18px">yes</span><span class="t" style="margin:0 12px;font-size:24px">or</span><span class="chip mono" style="font-size:28px;color:var(--ink);padding:8px 18px">no</span>');
      e.B = F.h('div', { cls: 'abs', style: 'left:0;top:0;width:1080px;height:800px' }, el);
      F.h('div', { cls: 'abs lab', style: 'left:60px;top:226px' }, e.B, 'Next word');
      e.slot = F.h('div', { cls: 'abs', style: 'left:60px;top:262px;width:300px;height:176px;border:2px solid var(--rule2);border-radius:18px;background:var(--sunk)' }, e.B);
      e.caret = F.h('div', { cls: 'abs', style: 'left:36px;top:42px;width:5px;height:92px;background:var(--gold);border-radius:2px' }, e.slot);
      e.stopd = F.h('div', { cls: 'abs lab', style: 'left:0;top:70px;width:296px;text-align:center;color:var(--ink2);font-size:24px' }, e.slot, '■ stopped here');
      F.h('div', { cls: 'abs lab', style: 'left:410px;top:226px' }, e.B, 'The model’s odds on it');
      e.rows = bars.map(function (b, k) {
        var r = F.h('div', { cls: 'abs', style: 'left:410px;top:' + (262 + k * 46) + 'px;width:610px;height:38px' }, e.B);
        F.h('div', { cls: 'abs mono', style: 'left:0;top:0;font-size:30px;line-height:38px;color:var(--ink)' }, r, b[0]);
        F.h('div', { cls: 'abs', style: 'left:84px;top:8px;width:360px;height:22px;border-radius:6px;background:var(--sunk);border:1px solid var(--rule)' }, r);
        r._f = F.h('div', { cls: 'abs', style: 'left:84px;top:8px;width:0;height:22px;border-radius:6px;background:' + (k ? 'var(--ink3)' : 'var(--gold)') }, r);
        F.h('div', { cls: 'abs mono', style: 'right:0;top:0;font-size:26px;line-height:38px;color:var(--ink2)' }, r, b[2]);
        r._w = Math.max(4, b[1] * 360); return r;
      });
      e.form = F.h('div', { cls: 'abs mono', style: 'left:60px;top:484px;font-size:28px;color:var(--ink2)' }, e.B, 'score = odds of yes ÷ (odds of yes + odds of no)');
      e.score = F.h('div', { cls: 'abs big', style: 'left:56px;top:536px;color:var(--gold)' }, e.B, '0.9999');
      e.sl = F.h('div', { cls: 'abs t', style: 'left:500px;top:566px;white-space:normal;width:500px' }, e.B, 'No answer written.<br><b>One step of the model’s work.</b>');
    },
    draw: function (t) {
      var pb = F.eio(F.lin(t, tB, tB + 0.8));
      F.fade(e.A, 1 - F.lin(t, tB, tB + 0.45));
      F.show(e.q, F.rise(t, tAsk - 0.15)); e.q.style.top = F.mix(644, 128, pb) + 'px';
      F.show(e.yn, F.span(t, tYes - 0.15, tB + 0.1, 0.4, 0.3));
      F.fade(e.B, F.span(t, tB + 0.4, tThats + 0.7, 0.5, 0.5));
      e.caret.style.opacity = t < tStop ? (Math.floor(t * 2.4) % 2 ? 1 : 0.12) : 0; F.fade(e.stopd, F.rise(t, tStop, 0.3));
      e.slot.style.borderColor = t >= tStop ? '#ffce40' : '#3a4760';
      e.rows.forEach(function (r, k) { var p = F.rise(t, tOdds - 0.1 + k * 0.14, 0.6); F.show(r, p, 10); r._f.style.width = (r._w * p) + 'px'; });
      F.show(e.form, F.rise(t, tRead - 0.1));
      var ps = F.rise(t, tStop + 0.1, 0.45), pg = F.lin(t, tFly - 0.1, tFly + 0.25);
      e.score.style.opacity = ps * (1 - pg); e.score.style.transform = 'scale(' + (0.9 + 0.1 * ps - 0.5 * pg) + ')'; e.score.style.transformOrigin = '206px 64px';
      F.show(e.sl, F.rise(t, tStop + 0.5));
    } });
});
