// Core of the second cut: every visual is a pure function of time t (seconds), so frames render deterministically.
(function () {
  var TL = window.TL;
  var F = window.F = { W: 1080, H: 1350, acts: [], sfx: [], scenes: [], t: 0 };
  F.clamp = function (x, a, b) { return x < a ? a : x > b ? b : x; };
  F.lin = function (t, a, b) { return F.clamp((t - a) / (b - a), 0, 1); };
  F.eo = function (p) { return 1 - Math.pow(1 - p, 3); };
  F.ei = function (p) { return p * p * p; };
  F.eio = function (p) { return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; };
  F.back = function (p) { var c = 1.4; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); };
  F.mix = function (a, b, p) { return a + (b - a) * p; };
  F.rise = function (t, a, d) { return F.eo(F.lin(t, a, a + (d || 0.5))); };          // 0 -> 1 starting at a
  F.span = function (t, a, b, di, dn) { return Math.min(F.rise(t, a, di || 0.5), 1 - F.lin(t, b - (dn || 0.4), b)); };   // on between a and b
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
  F.fade = function (el, p) { el.style.opacity = p; el.style.visibility = p <= 0.001 ? 'hidden' : 'visible'; };
  F.txt = function (el, s) { if (el._s !== s) { el._s = s; el.textContent = s; } };
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
  F.snd = function (t, name, gain, len) { F.sfx.push({ t: Math.round(t * 1000) / 1000, name: name, gain: gain == null ? 1 : gain, len: len || 0 }); };
  F.scene = function (fn) { F.scenes.push(fn); };
  F.act = function (o) {
    o.el = F.h('div', { cls: 'act', id: 'act-' + o.id }, document.getElementById('hud'));
    o.wl = F.h('div', { cls: 'act', id: 'wl-' + o.id }, document.getElementById('wl'));
    o.build(o.el, o.wl); F.acts.push(o);
  };
  // captions: phrase-sized chunks, words light up as spoken
  var chunks = [];
  TL.segs.forEach(function (s) {
    var sents = [], cur = [];
    s.words.forEach(function (w) { cur.push(w); if (/[.?!:]$/.test(w.w)) { sents.push(cur); cur = []; } });
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
      a.el.style.display = a.wl.style.display = on ? 'block' : 'none';
      if (!on) return;
      var fi = a.start <= 0 ? 1 : F.eo(F.lin(t, a.start, a.start + (a.fin || 0.45))), fo = a.end >= TL.dur ? 1 : 1 - F.lin(t, a.end - (a.fout || 0.4), a.end);
      a.el.style.opacity = a.wl.style.opacity = Math.min(fi, fo);
      a.draw(t);
      if (a.kick) kick = typeof a.kick === 'function' ? a.kick(t) : a.kick;
    });
    document.getElementById('kick').textContent = kick;
    document.getElementById('bar').style.width = (F.W * t / TL.dur) + 'px';
    F.world.draw(t);
    captions(t);
    return t;
  };
  var booted = null;
  F.boot = function () {
    capEl = document.getElementById('cap');
    var faces = ['700 60px Besley', '500 60px Besley', 'italic 500 60px Besley', '400 20px "Public Sans"', '600 20px "Public Sans"', '700 20px "Public Sans"', 'italic 400 20px "Public Sans"', '400 20px "IBM Plex Mono"', '500 20px "IBM Plex Mono"', '600 20px "IBM Plex Mono"'];
    booted = Promise.all(faces.map(function (f) { return document.fonts.load(f, 'yes no 0123'); })).then(function () { return document.fonts.ready; }).then(function () {
      F.world.init();
      F.scenes.forEach(function (fn) { fn(); });
      F.world.finish();
      F.sfx.sort(function (a, b) { return a.t - b.t; });
      F.seek(0);
      if (/play/.test(location.search)) scrubber();
      return document.fonts.size;
    });
    return booted;
  };
  function scrubber() {            // simple player for looking at the film in a browser
    var sc = document.getElementById('scrub'), rng = document.getElementById('rng'), tt = document.getElementById('tt'), pp = document.getElementById('pp');
    sc.style.display = 'flex'; rng.max = TL.dur; var playing = false, t0 = 0, w0 = 0;
    var s = Math.min(1, (innerHeight - 50) / F.H); document.getElementById('stage').style.cssText += ';transform-origin:0 0;transform:scale(' + s + ')';
    rng.oninput = function () { playing = false; F.seek(+rng.value); tt.textContent = (+rng.value).toFixed(2); };
    pp.onclick = function () { playing = !playing; t0 = +rng.value; w0 = performance.now(); if (playing) requestAnimationFrame(tick); };
    var tick = function () { if (!playing) return; var t = t0 + (performance.now() - w0) / 1000; if (t >= TL.dur) { playing = false; return; } rng.value = t; tt.textContent = t.toFixed(2); F.seek(t); requestAnimationFrame(tick); };
  }
  F.ready = function () { return booted; };
})();
