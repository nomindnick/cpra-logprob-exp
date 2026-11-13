// Core of the film: every visual is a pure function of time t (seconds), so frames render deterministically.
(function () {
  var TL = window.TL;
  var F = window.F = { W: 1080, H: 1350, acts: [], sfx: [], t: 0 };
  F.clamp = function (x, a, b) { return x < a ? a : x > b ? b : x; };
  F.lin = function (t, a, b) { return F.clamp((t - a) / (b - a), 0, 1); };
  F.eo = function (p) { return 1 - Math.pow(1 - p, 3); };
  F.eio = function (p) { return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; };
  F.back = function (p) { var c = 1.4; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); };
  F.mix = function (a, b, p) { return a + (b - a) * p; };
  F.rise = function (t, a, d) { return F.eo(F.lin(t, a, a + (d || 0.5))); };   // 0 -> 1 starting at a
  F.rng = function (seed) { var s = seed >>> 0; return function () { s = (s + 0x6D2B79F5) >>> 0; var x = Math.imul(s ^ (s >>> 15), 1 | s); x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x; return ((x ^ (x >>> 14)) >>> 0) / 4294967296; }; };
  F.h = function (tag, attrs, parent, html) {
    var e = document.createElement(tag), k;
    for (k in attrs || {}) { if (k === 'style') e.style.cssText = attrs[k]; else if (k === 'cls') e.className = attrs[k]; else e.setAttribute(k, attrs[k]); }
    if (html != null) e.innerHTML = html;
    if (parent) parent.appendChild(e);
    return e;
  };
  // show(el, p, dy): opacity p with a small rise
  F.show = function (el, p, dy) { el.style.opacity = p; el.style.transform = 'translateY(' + ((1 - p) * (dy == null ? 18 : dy)) + 'px)'; el.style.visibility = p <= 0.001 ? 'hidden' : 'visible'; };
  var norm = function (w) { return w.toLowerCase().replace(/[^a-z0-9.'-]/g, '').replace(/\.$/, ''); };
  F.seg = function (id) { return TL.segs.filter(function (s) { return s.id === id; })[0]; };
  // time at which a phrase starts being spoken in a segment
  F.cue = function (id, phrase) {
    var s = F.seg(id), want = phrase.split(' ').map(norm), i, j;
    for (i = 0; i + want.length <= s.words.length; i++) {
      for (j = 0; j < want.length && norm(s.words[i + j].w) === want[j]; j++);
      if (j === want.length) return s.words[i].s;
    }
    throw new Error('cue not found: ' + id + ' "' + phrase + '"');
  };
  F.snd = function (t, name, gain) { F.sfx.push({ t: Math.round(t * 1000) / 1000, name: name, gain: gain == null ? 1 : gain }); };
  F.act = function (o) { o.el = F.h('div', { cls: 'act', id: 'act-' + o.id }, document.getElementById('acts')); o.build(o.el); F.acts.push(o); };
  // captions: phrase-sized chunks, words light up as spoken
  var chunks = [];
  TL.segs.forEach(function (s) {
    // sentences first; a long sentence splits into near-equal parts, breaking after a comma when one is close
    var sents = [], cur = [];
    s.words.forEach(function (w) { cur.push(w); if (/[.?!]$/.test(w.w)) { sents.push(cur); cur = []; } });
    if (cur.length) sents.push(cur);
    var len = function (ws) { return ws.map(function (w) { return w.w; }).join(' ').length; };
    for (var i = 0; i < sents.length - 1; i++) if (len(sents[i]) < 22 && len(sents[i]) + len(sents[i + 1]) < 46) { sents.splice(i, 2, sents[i].concat(sents[i + 1])); i--; }
    sents.forEach(function (ws) {
      var n = Math.ceil(len(ws) / 50), start = 0, k;
      for (k = 1; k <= n; k++) {
        if (k === n) { chunks.push({ words: ws.slice(start) }); break; }
        var target = len(ws) * k / n, best = -1, bestCost = 1e9, j;
        for (j = start + 1; j < ws.length; j++) {
          var cost = Math.abs(len(ws.slice(0, j)) - target) - (/,$/.test(ws[j - 1].w) ? 9 : 0);
          if (cost < bestCost) { bestCost = cost; best = j; }
        }
        chunks.push({ words: ws.slice(start, best) }); start = best;
      }
    });
  });
  chunks.forEach(function (c, i) {
    c.s = c.words[0].s - 0.1; c.e = c.words[c.words.length - 1].e + 0.35;
    var nx = chunks[i + 1]; if (nx && nx.words[0].s - 0.1 < c.e) c.e = nx.words[0].s - 0.1;
  });
  F.chunks = chunks;
  var capEl, capCur = null, capSpans = [];
  function captions(t) {
    var c = null, i;
    for (i = 0; i < chunks.length; i++) if (t >= chunks[i].s && t < chunks[i].e) { c = chunks[i]; break; }
    if (c !== capCur) {
      capCur = c; capEl.innerHTML = ''; capSpans = [];
      if (c) { var d = F.h('div', null, capEl); c.words.forEach(function (w) { capSpans.push(F.h('span', null, d, w.w + ' ')); }); }
    }
    if (c) c.words.forEach(function (w, k) { capSpans[k].className = t >= w.s - 0.04 ? 'on' : ''; });
  }
  F.seek = function (t) {
    F.t = t;
    var kick = '';
    F.acts.forEach(function (a) {
      var on = t >= a.start && t < a.end;
      a.el.style.display = on ? 'block' : 'none';
      if (!on) return;
      var fi = a.start <= 0 ? 1 : F.eo(F.lin(t, a.start, a.start + 0.45)), fo = a.end >= TL.dur ? 1 : 1 - F.lin(t, a.end - 0.32, a.end);
      a.el.style.opacity = Math.min(fi, fo);
      a.draw(t);
      kick = a.kick ? a.kick(t) : '';
    });
    document.getElementById('kick').textContent = kick;
    document.getElementById('bar').style.width = (F.W * t / TL.dur) + 'px';
    captions(t);
    return t;
  };
  F.boot = function () {
    capEl = document.getElementById('cap');
    F.sfx.sort(function (a, b) { return a.t - b.t; });
    F.seek(0);
    if (/play/.test(location.search)) {           // simple scrubber for looking at the film in a browser
      var sc = document.getElementById('scrub'), rng = document.getElementById('rng'), tt = document.getElementById('tt'), pp = document.getElementById('pp');
      sc.style.display = 'flex'; rng.max = TL.dur; var playing = false, t0 = 0, w0 = 0;
      var s = Math.min(1, (innerHeight - 50) / F.H); document.getElementById('stage').style.cssText += ';transform-origin:0 0;transform:scale(' + s + ')';
      rng.oninput = function () { playing = false; F.seek(+rng.value); tt.textContent = (+rng.value).toFixed(2); };
      pp.onclick = function () { playing = !playing; t0 = +rng.value; w0 = performance.now(); if (playing) requestAnimationFrame(tick); };
      var tick = function () { if (!playing) return; var t = t0 + (performance.now() - w0) / 1000; if (t >= TL.dur) { playing = false; return; } rng.value = t; tt.textContent = t.toFixed(2); F.seek(t); requestAnimationFrame(tick); };
    }
  };
  F.ready = function () { return document.fonts.ready.then(function () { return document.fonts.size; }); };
})();
