// Act A: the pile, the shortcut, the trick (narration segments s1, s2, s3).
(function () {
  var F = window.F, FD = window.FD, h = F.h, E = FD.emails.yes;
  var s1 = F.seg('s1'), s2 = F.seg('s2'), s3 = F.seg('s3'), s4 = F.seg('s4');
  var T = {
    fill: F.cue('s1', 'sweep in'), decide: F.cue('s1', 'Someone has'),
    toMail: s2.start - 0.45, model: F.cue('s2', 'small AI model') - 0.15, ask: F.cue('s2', 'ask a single'), yn: F.cue('s2', 'Yes or no'),
    toOdds: s3.start - 0.4, bars: F.cue('s3', 'put odds') - 0.25, stop: F.cue('s3', "don't let it"), read: F.cue('s3', 'Read the odds'),
    yes: F.cue('s3', 'yes against'), no: F.cue('s3', 'no and'), halt: F.cue('s3', 'stop'), score: F.cue('s3', "That's the score")
  };
  var COLS = 125, ROWS = 80, N = COLS * ROWS, PW = 960, PH = 480, PAD = 16, PTOP = 606, order, decided, pile, pctx, el = {};
  var QUESTION = 'Is this email responsive to the request? Answer yes or no.';
  var ROWSPEC = [['yes', E.top3[0][1], 'pos'], ['Yes', E.top3[1][1], 'pos'], ['The', E.top3[2][1], 'off'], ['no', E.p_no, 'neg']];
  var pct = function (p) { return p >= 0.1 ? (p * 100).toFixed(1) + '%' : p >= 0.001 ? (p * 100).toFixed(2) + '%' : (p * 100).toFixed(3) + '%'; };

  F.act({
    id: 'a', start: 0, end: s4.start - 0.4,
    kick: function (t) { return t < T.toMail ? '01 · The pile' : t < T.toOdds ? '02 · The shortcut' : '03 · The trick'; },
    build: function (root) {
      // request, full and shortened
      el.req = h('div', { cls: 'card', style: 'left:60px;top:150px;width:960px;height:386px;padding:32px 38px' }, root);
      h('div', { style: 'display:flex;justify-content:space-between;align-items:center;margin-bottom:20px' }, el.req, '<span class="lab g">Public records request</span><span class="pill">invented example</span>');
      h('div', { cls: 'disp', style: 'font:500 35px/1.33 var(--display)' }, el.req, FD.request);
      el.reqMini = h('div', { cls: 'card', style: 'left:60px;top:150px;width:960px;height:152px;padding:22px 30px' }, root);
      h('div', { cls: 'lab g', style: 'margin-bottom:12px' }, el.reqMini, 'The request, shortened');
      h('div', { style: 'font:500 29px/1.3 var(--display);color:var(--ink2)' }, el.reqMini, 'All emails, January to June 2024, concerning the Mill Creek Bridge repair project …');
      // the pile
      el.pileHead = h('div', { cls: 'abs', style: 'left:60px;top:548px;width:960px;display:flex;justify-content:space-between;align-items:baseline' }, root,
        '<span class="lab">What the search returns</span><span class="mono" style="font-size:42px;font-weight:600"><span id="pcount">0</span> <span style="font-size:22px;color:var(--ink3);font-weight:400">emails</span></span>');
      pile = h('canvas', { width: PW + 2 * PAD, height: PH + 2 * PAD, style: 'left:' + (60 - PAD) + 'px;top:' + (PTOP - PAD) + 'px' }, root); pctx = pile.getContext('2d');
      el.tag = h('div', { cls: 'abs mono', style: 'font-size:25px;font-weight:600;color:var(--paper);background:var(--gold);border-radius:9px;padding:8px 14px;white-space:nowrap' }, root, '');
      var r = F.rng(11), i; order = new Float32Array(N); decided = new Uint8Array(N);
      for (i = 0; i < N; i++) { order[i] = (Math.floor(i / COLS) / ROWS) * 0.72 + r() * 0.28; decided[i] = r() < 0.22 ? 1 : 2; }
      // the email
      el.mail = h('div', { cls: 'card', style: 'left:60px;top:322px;width:960px;height:410px;padding:28px 36px' }, root);
      h('div', { style: 'display:flex;justify-content:space-between;align-items:center;margin-bottom:18px' }, el.mail, '<span class="lab">One email</span><span class="pill">invented example</span>');
      var esc = function (s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;'); };
      h('div', { cls: 'mono', style: 'font-size:25px;color:var(--ink3)' }, el.mail, esc(E.from.split(' <')[0]) + ' → ' + esc(E.to.split(' <')[0]) + ' · ' + E.date);
      h('div', { style: 'font:600 35px/1.25 var(--body);margin:14px 0 16px' }, el.mail, esc(E.subject));
      h('div', { style: 'font:400 30px/1.42 var(--body);color:var(--ink2);border-top:1px solid var(--rule);padding-top:16px' }, el.mail,
        esc(E.body.split('\n\nCan you')[0]).replace(/\n\n/g, '<br>') + ' …');
      el.mailMini = h('div', { cls: 'card', style: 'left:60px;top:322px;width:960px;height:118px;padding:20px 30px' }, root);
      h('div', { cls: 'lab', style: 'margin-bottom:10px' }, el.mailMini, 'One email · invented example');
      h('div', { style: 'font:600 33px/1.25 var(--body)' }, el.mailMini, esc(E.subject));
      // the model and the question
      el.model = h('div', { cls: 'card', style: 'left:60px;top:752px;width:960px;height:132px;padding:0 34px;display:flex;align-items:center;gap:28px' }, root);
      h('div', { style: 'width:70px;height:78px;border:2px solid var(--ink2);border-radius:9px;position:relative;flex:none' }, el.model,
        '<i style="position:absolute;left:12px;right:12px;top:13px;height:3px;background:var(--ink2)"></i><i style="position:absolute;left:12px;right:12px;top:25px;height:3px;background:var(--ink2)"></i><i style="position:absolute;right:12px;bottom:12px;width:9px;height:9px;border-radius:9px;background:var(--gold)"></i>');
      h('div', null, el.model, '<div class="mono" style="font-size:37px;font-weight:600">' + FD.model + '</div><div style="font-size:26px;color:var(--ink2);margin-top:4px">a local model on one desktop · nothing leaves the building</div>');
      el.ask = h('div', { cls: 'card', style: 'left:60px;top:904px;width:960px;height:186px;padding:22px 34px;background:var(--sunk)' }, root);
      el.askQ = h('div', { cls: 'mono', style: 'font-size:29px;line-height:1.3;height:76px;color:var(--ink)' }, el.ask, '');
      el.askA = h('div', { style: 'margin-top:12px;display:flex;align-items:center;gap:14px' }, el.ask,
        '<span class="lab">answer</span><span class="tok" style="font-size:28px;padding:7px 16px">yes</span><span class="lab" style="letter-spacing:0">or</span><span class="tok" style="font-size:28px;padding:7px 16px">no</span>');
      // the odds
      el.odds = h('div', { cls: 'card', style: 'left:60px;top:460px;width:960px;height:634px;padding:28px 36px' }, root);
      h('div', { style: 'display:flex;justify-content:space-between;align-items:baseline' }, el.odds, '<span class="lab g">The first word: the model\'s odds</span><span class="lab" style="letter-spacing:.04em;text-transform:none">' + FD.model + '</span>');
      el.rows = ROWSPEC.map(function (r, i) {
        var row = h('div', { cls: 'abs', style: 'left:36px;top:' + (78 + i * 80) + 'px;width:888px;height:66px' }, el.odds);
        var o = { row: row };
        o.tok = h('span', { cls: 'tok abs', style: 'left:0;top:2px;width:132px;text-align:center;font-size:36px' }, row, r[0]);
        o.track = h('div', { cls: 'abs', style: 'left:160px;top:14px;width:520px;height:36px;background:var(--sunk);border-radius:6px' }, row);
        o.bar = h('div', { cls: 'abs', style: 'left:160px;top:14px;height:36px;border-radius:6px;background:var(--ink2)' }, row);
        o.val = h('div', { cls: 'abs mono', style: 'right:0;top:8px;font-size:35px;font-weight:500;text-align:right' }, row, '');
        return o;
      });
      el.stamp = h('div', { cls: 'abs mono', style: 'right:236px;top:238px;font-size:30px;font-weight:600;letter-spacing:.1em;color:var(--stamp);border:3px solid var(--stamp);border-radius:10px;padding:10px 16px;background:rgba(11,16,25,.82)' }, el.odds, 'STOP AFTER ONE WORD');
      el.form = h('div', { cls: 'abs', style: 'left:36px;top:410px;width:888px;height:200px;border-top:1px solid var(--rule)' }, el.odds);
      el.py = h('div', { cls: 'abs mono', style: 'left:0;top:26px;font-size:30px' }, el.form, '<span style="color:var(--pos);font-weight:600">yes</span> <span style="color:var(--ink3);font-size:23px">all spellings</span> &nbsp;<b id="pyv"></b>');
      el.pn = h('div', { cls: 'abs mono', style: 'left:0;top:76px;font-size:30px' }, el.form, '<span style="color:var(--neg);font-weight:600">no</span>&nbsp; <span style="color:var(--ink3);font-size:23px">all spellings</span> &nbsp;<b id="pnv"></b>');
      el.eq = h('div', { cls: 'abs mono', style: 'left:0;top:142px;font-size:26px;color:var(--ink2)' }, el.form, 'score = yes ÷ (yes + no)');
      el.big = h('div', { cls: 'abs', style: 'right:0;top:22px;text-align:right' }, el.form, '<div class="lab" style="margin-bottom:8px">score</div><div id="bigv" style="font:700 112px/1 var(--display);color:var(--gold);letter-spacing:-.01em">0.9999</div>');
      // sounds
      F.snd(0.15, 'whoosh', 0.7); F.snd(T.fill - 0.05, 'scatter', 0.8);
      [0, 1, 2, 3, 4, 5].forEach(function (k) { F.snd(T.decide + 0.3 + k * 0.5, 'tick', 0.5); });
      F.snd(T.toMail + 0.1, 'whoosh', 0.7); F.snd(T.model, 'pop', 0.6); F.snd(T.ask, 'type', 0.5);
      F.snd(T.toOdds + 0.1, 'whoosh', 0.6); F.snd(T.bars, 'pop', 0.6); F.snd(T.stop + 0.15, 'thud', 0.8); F.snd(T.halt + 0.25, 'chime', 0.8);
    },
    draw: function (t) {
      var p, i;
      // request cards
      p = 1 - F.lin(t, T.toMail, T.toMail + 0.4); F.show(el.req, Math.min(F.rise(t, 0.15, 0.6), p), 24);
      F.show(el.reqMini, F.rise(t, T.toMail + 0.25, 0.45), 0);
      // pile
      var pv = F.rise(t, T.fill - 0.5, 0.4) * (1 - F.lin(t, T.toMail, T.toMail + 0.45));
      el.pileHead.style.opacity = pv; pile.style.opacity = pv;
      if (pv > 0) {
        var prog = F.lin(t, T.fill, T.fill + 1.55), nd = Math.floor(F.clamp((t - T.decide - 0.3) / 0.5, 0, 99) + (t > T.decide + 0.3 ? 1 : 0)), shown = 0;
        pctx.clearRect(0, 0, PW + 2 * PAD, PH + 2 * PAD);
        var cw = PW / COLS, rh = PH / ROWS;
        for (i = 0; i < N; i++) {
          var a = F.clamp((prog * 1.12 - order[i]) / 0.12, 0, 1); if (a <= 0) continue; shown++;
          var x = PAD + (i % COLS) * cw, y = PAD + Math.floor(i / COLS) * rh - (1 - a) * 14;
          pctx.globalAlpha = a; pctx.fillStyle = i < nd ? (decided[i] === 1 ? '#3987e5' : '#d95926') : '#3a4760';
          pctx.fillRect(x + 0.8, y + 0.8, cw - 1.6, rh - 1.6);
        }
        pctx.globalAlpha = 1;
        document.getElementById('pcount').textContent = (Math.round(shown / N * 10000 / 10) * 10).toLocaleString('en-US');
        var tp = F.rise(t, T.decide + 0.1, 0.35) * pv; el.tag.style.opacity = tp;
        if (nd > 0 || tp > 0) {
          var cx = PAD + Math.max(0, nd - 1) * cw + cw / 2;
          pctx.strokeStyle = '#ffce40'; pctx.lineWidth = 2.5; pctx.globalAlpha = tp; pctx.beginPath(); pctx.arc(cx, PAD + rh / 2, 12, 0, 6.2832); pctx.stroke(); pctx.globalAlpha = 1;
          el.tag.style.left = (60 - PAD + cx + 22) + 'px'; el.tag.style.top = (PTOP + 14) + 'px';
          el.tag.textContent = 'decided by hand: ' + nd + ' of 10,000';
        }
      }
      // email, full then shortened
      F.show(el.mail, Math.min(F.rise(t, T.toMail + 0.2, 0.55), 1 - F.lin(t, T.toOdds, T.toOdds + 0.35)), 40);
      F.show(el.mailMini, F.rise(t, T.toOdds + 0.2, 0.45), 0);
      var out = 1 - F.lin(t, T.toOdds, T.toOdds + 0.35);
      F.show(el.model, Math.min(F.rise(t, T.model, 0.5), out), 24);
      F.show(el.ask, Math.min(F.rise(t, T.ask - 0.1, 0.4), out), 24);
      el.askQ.textContent = QUESTION.slice(0, Math.round(F.lin(t, T.ask, T.ask + 1.5) * QUESTION.length)) + (t < T.ask + 1.5 && t > T.ask ? '▌' : '');
      el.askA.style.opacity = F.rise(t, T.yn - 0.1, 0.3);
      // odds
      F.show(el.odds, F.rise(t, T.toOdds + 0.3, 0.5), 30);
      var merge = F.rise(t, T.read, 0.5);
      el.rows.forEach(function (o, i) {
        var r = ROWSPEC[i], g = F.rise(t, T.bars + i * 0.16, 0.7), isYes = r[2] === 'pos', isNo = r[2] === 'neg';
        o.row.style.opacity = F.rise(t, T.bars - 0.3 + i * 0.08, 0.3) * (r[2] === 'off' ? F.mix(1, 0.35, merge) : 1);
        o.bar.style.width = Math.max(4, 520 * r[1] * g) + 'px';
        var lit = isYes ? F.rise(t, T.yes - 0.1, 0.3) : isNo ? F.rise(t, T.no - 0.1, 0.3) : 0;
        o.bar.style.background = lit > 0.5 ? (isYes ? 'var(--pos)' : 'var(--neg)') : 'var(--ink2)';
        o.tok.style.borderColor = lit > 0.5 ? (isYes ? 'var(--pos)' : 'var(--neg)') : 'var(--rule2)';
        o.val.textContent = pct(r[1] * g);
      });
      var sp = F.lin(t, T.stop + 0.1, T.stop + 0.45);
      el.stamp.style.opacity = sp; el.stamp.style.transform = 'rotate(-5deg) scale(' + F.mix(1.5, 1, F.eo(sp)) + ')';
      el.form.style.opacity = F.rise(t, T.read - 0.1, 0.4);
      el.py.style.opacity = F.rise(t, T.yes - 0.1, 0.3); el.pn.style.opacity = F.rise(t, T.no - 0.1, 0.3);
      document.getElementById('pyv').textContent = pct(E.p_yes); document.getElementById('pnv').textContent = pct(E.p_no);
      el.eq.style.opacity = F.rise(t, T.no + 0.25, 0.35);
      var bp = F.lin(t, T.halt, T.halt + 0.55);
      el.big.style.opacity = F.rise(t, T.halt - 0.05, 0.25);
      document.getElementById('bigv').textContent = (Math.floor(F.mix(0.5, E.score, F.eo(bp)) * 10000) / 10000).toFixed(4);
      var pulse = Math.sin(F.lin(t, T.score, T.score + 0.6) * Math.PI);
      el.big.style.transform = 'scale(' + (1 + 0.06 * pulse) + ')'; el.big.style.transformOrigin = '100% 50%';
    }
  });
})();
