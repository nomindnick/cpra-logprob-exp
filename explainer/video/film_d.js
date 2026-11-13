// Act D: the close (narration segment s7).
(function () {
  var F = window.F, FD = window.FD, h = F.h, TL = window.TL, E = FD.emails.yes;
  var s7 = F.seg('s7'), A0 = s7.start - 0.4;
  var T = { l1: F.cue('s7', 'a promising') - 0.1, l2: F.cue('s7', 'not a replacement') - 0.1, emb: F.cue('s7', 'But for'), big: F.cue('s7', 'one word is') - 0.15 };
  T.foot = T.big + 1.0;
  var el = {};
  F.act({
    id: 'd', start: A0, end: TL.dur + 1,
    kick: function () { return '07 · The upshot'; },
    build: function (root) {
      el.l1 = h('div', { cls: 'abs', style: 'left:60px;top:196px;width:960px;font:500 60px/1.2 var(--display)' }, root, 'A promising pre-screen.');
      el.l2 = h('div', { cls: 'abs', style: 'left:60px;top:276px;width:960px;font:500 60px/1.2 var(--display);color:var(--ink3)' }, root, 'Not a replacement for review.');
      el.emb = h('div', { cls: 'abs', style: 'left:60px;top:424px;width:960px;height:100px' }, root);
      el.by = h('div', { cls: 'abs', style: 'left:0;top:0;height:42px;border-radius:0 6px 6px 0;background:var(--pos)' }, el.emb);
      el.bn = h('div', { cls: 'abs', style: 'left:0;top:56px;height:42px;width:5px;border-radius:0 6px 6px 0;background:var(--neg)' }, el.emb);
      el.ty = h('div', { cls: 'abs mono', style: 'top:1px;font-size:31px;font-weight:600' }, el.emb, 'yes');
      el.tn = h('div', { cls: 'abs mono', style: 'left:22px;top:57px;font-size:31px;font-weight:600' }, el.emb, 'no');
      el.big = h('div', { cls: 'abs', style: 'left:56px;top:556px;width:968px;font:700 140px/1.04 var(--display);letter-spacing:-.02em' }, root, 'One word<br>is enough.');
      el.rule = h('div', { cls: 'abs', style: 'left:60px;top:868px;height:8px;border-radius:4px;background:var(--gold)' }, root);
      el.foot = h('div', { cls: 'abs', style: 'left:60px;top:916px;width:960px;font-size:27px;line-height:1.34;color:var(--ink2)' }, root,
        '<div style="display:grid;grid-template-columns:196px 1fr;row-gap:14px;align-items:baseline">' +
        '<span class="lab" style="white-space:nowrap">The test</span><span>496 request and email pairs from two California public records requests</span>' +
        '<span class="lab" style="white-space:nowrap">The models</span><span><span class="mono" style="font-size:25px">qwen3.5:4b, qwen3.5:9b, qwen3.8:27b</span>, run with Ollama on one desktop</span>' +
        '<span class="lab" style="white-space:nowrap">On screen</span><span>every email and name shown was invented for this video</span></div>');
      F.snd(A0 + 0.1, 'whoosh', 0.5); F.snd(T.big, 'chime', 0.9);
    },
    draw: function (t) {
      F.show(el.l1, F.rise(t, T.l1, 0.5)); F.show(el.l2, F.rise(t, T.l2, 0.5));
      var g = F.rise(t, T.emb, 0.8); el.emb.style.opacity = F.rise(t, T.emb - 0.05, 0.3);
      el.by.style.width = Math.max(5, 840 * E.p_yes * g) + 'px'; el.ty.style.left = (840 * E.p_yes * g + 18) + 'px';
      var b = F.lin(t, T.big, T.big + 0.6); el.big.style.opacity = F.eo(b); el.big.style.transform = 'translateY(' + (1 - F.back(b)) * 46 + 'px)';
      el.rule.style.width = (F.rise(t, T.big + 0.35, 0.8) * 600) + 'px';
      F.show(el.foot, F.rise(t, T.foot, 0.6), 14);
    }
  });
})();
