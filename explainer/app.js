/* CPRA logprob experiment explainer.
   Draws every figure on the page. Interactive figures are computed live from data.js
   (the 496 scored pairs). Bootstrap intervals and the earlier-phase numbers are constants
   copied from docs/findings-golden.md, docs/findings-sweep.md and docs/findings-run1.md.
   check.mjs recomputes the live numbers and compares them with those constants. */
(function () {
'use strict';
var D = window.DATA;
if (!D) return;
var P = D.pairs;
/* an email can be paired with both requests, so a pair is keyed by request and email id */
P.forEach(function (p) { p.uid = p.req + '|' + p.id; });
var CFG = {};
D.configs.forEach(function (c) { CFG[c.key] = c; });
var SCORE_KEYS = ['lp4', 'lp9', 'lp27', 'd4', 'd9', 'd27', 'jev'];
var JSON_KEYS = ['js4', 'js9', 'js27', 'jr4', 'jr9', 'jr27'];
var ALL_KEYS = SCORE_KEYS.concat(JSON_KEYS);
var REQ_A = '24-409', REQ_B = '25-3152';

/* ---------- metrics (ports of scripts/analyze.py) ---------- */
function rowsFor(key, filter, roster) {
  var out = [];
  for (var i = 0; i < P.length; i++) {
    var p = P[i];
    if (filter && !filter(p)) continue;
    var v = roster ? p.r[key] : p.s[key];
    if (v == null) continue;
    if (roster && p.s[key] == null) continue; /* the roster comparison is paired */
    out.push({ p: p, s: v });
  }
  return out;
}
function auroc(rs) {
  var a = rs.slice().sort(function (x, y) { return x.s - y.s; });
  var i = 0, rankSum = 0, nPos = 0;
  while (i < a.length) {
    var j = i;
    while (j < a.length && a[j].s === a[i].s) j++;
    var avg = (i + 1 + j) / 2;
    for (var k = i; k < j; k++) if (a[k].p.label) { rankSum += avg; nPos++; }
    i = j;
  }
  var nNeg = a.length - nPos;
  return (rankSum - nPos * (nPos + 1) / 2) / (nPos * nNeg);
}
function prCurve(rs) {
  var a = rs.slice().sort(function (x, y) { return y.s - x.s; });
  var nPos = 0;
  for (var q = 0; q < a.length; q++) nPos += a[q].p.label;
  var nNeg = a.length - nPos, tp = 0, fp = 0, i = 0, out = [];
  while (i < a.length) {
    var thr = a[i].s;
    while (i < a.length && a[i].s === thr) { if (a[i].p.label) tp++; else fp++; i++; }
    out.push({ thr: thr, recall: tp / nPos, precision: tp / (tp + fp), elim: (nNeg - fp) / nNeg });
  }
  return out;
}
function atRecall(curve, target) {
  for (var i = 0; i < curve.length; i++) if (curve[i].recall >= target) return curve[i];
  return curve[curve.length - 1];
}
function confusion(rs, cut) {
  var c = { tp: 0, fn: 0, fp: 0, tn: 0 };
  for (var i = 0; i < rs.length; i++) {
    var f = rs[i].s >= cut;
    if (rs[i].p.label) { if (f) c.tp++; else c.fn++; } else { if (f) c.fp++; else c.tn++; }
  }
  return c;
}
function thr98(rs) { return atRecall(prCurve(rs), 0.98); }
var isA = function (p) { return p.req === REQ_A; };
var isB = function (p) { return p.req === REQ_B; };

/* ---------- constants from the findings ---------- */
var HEAD = { /* findings-golden section 1: AUROC, CI, cleared at 98% recall, CI, median seconds */
  lp4:  { auc: 0.922, aci: [0.898, 0.945], el: 53, eci: [41, 70], sec: 0.50, thr: 0.2650 },
  lp9:  { auc: 0.945, aci: [0.923, 0.965], el: 72, eci: [65, 81], sec: 0.86, thr: 0.3309 },
  lp27: { auc: 0.977, aci: [0.965, 0.987], el: 77, eci: [72, 89], sec: 2.64, thr: 0.0687 },
  d4:   { auc: 0.901, aci: [0.872, 0.924], el: 55, eci: [43, 64], sec: 0.88, thr: 0.3507 },
  d9:   { auc: 0.957, aci: [0.941, 0.973], el: 70, eci: [63, 80], sec: 1.43, thr: 0.3379 },
  d27:  { auc: 0.983, aci: [0.974, 0.990], el: 83, eci: [76, 87], sec: 4.66, thr: 0.5857 },
  jev:  { auc: 0.917, aci: [0.890, 0.940], el: 64, eci: [56, 71], sec: 0.12, thr: 0.34 },
  js4:  { auc: 0.831, aci: [0.796, 0.868], el: 10, eci: [6, 14], sec: 2.75 },
  js9:  { auc: 0.869, aci: [0.838, 0.897], el: 0, eci: null, sec: 4.44 },
  js27: { auc: 0.950, aci: [0.931, 0.967], el: 28, eci: [22, 35], sec: 6.81 },
  jr4:  { auc: 0.873, aci: [0.839, 0.906], el: 0, eci: null, sec: 2.91 },
  jr9:  { auc: 0.888, aci: [0.857, 0.918], el: 0, eci: [0, 71], sec: 5.26 },
  jr27: { auc: 0.954, aci: [0.937, 0.967], el: 67, eci: [60, 74], sec: 7.01 }
};
var ROSTER = { /* section 6, request 25-3152, 249 pairs: [no roster, roster] */
  lp4:  { auc: [0.885, 0.961], el: [30, 77] }, lp9:  { auc: [0.931, 0.967], el: [72, 70] },
  lp27: { auc: [0.961, 0.994], el: [76, 93] }, d4:   { auc: [0.909, 0.976], el: [46, 89] },
  d9:   { auc: [0.963, 0.991], el: [76, 92] }, d27:  { auc: [0.988, 1.000], el: [88, 100] },
  jev:  { auc: [0.921, 0.972], el: [59, 86] }, js4:  { auc: [0.792, 0.864], el: [10, 17] },
  js9:  { auc: [0.857, 0.903], el: [0, 0] },   js27: { auc: [0.929, 0.993], el: [12, 59] },
  jr4:  { auc: [0.864, 0.912], el: [0, 0] },   jr9:  { auc: [0.871, 0.916], el: [0, 59] },
  jr27: { auc: [0.947, 0.986], el: [63, 78] }
};
var THR_INT = [ /* section 11: fitted 98% cutoff per request with 95% interval */
  { key: 'lp27', rows: [['24-409', 0.3623, 0.2529, 0.7206], ['25-3152', 0.0566, 0.0079, 0.1030], ['25-3152 + roster', 0.0783, 0.0730, 0.2164]] },
  { key: 'd27', rows: [['24-409', 0.8542, 0.7504, 0.9115], ['25-3152', 0.5405, 0.4870, 0.6115], ['25-3152 + roster', 0.9060, 0.8722, 0.9220]] },
  { key: 'jev', rows: [['24-409', 0.57, 0.42, 0.63], ['25-3152', 0.31, 0.22, 0.35], ['25-3152 + roster', 0.46, 0.39, 0.52]] }
];
var VALID = { /* section 14: cleared at 98% recall on three versions of the test */
  all:  { lp4: 53, lp9: 72, lp27: 77, d4: 55, d9: 70, d27: 83, jev: 64 },
  real: { lp4: 71, lp9: 96, lp27: 100, d4: 84, d9: 99, d27: 100, jev: 91 },
  hard: { lp4: 19, lp9: 48, lp27: 45, d4: 16, d9: 33, d27: 43, jev: 30 }
};
var WORK = [ /* section 12: per 10,000 hits. [label, machine hours, reviewer hours] */
  ['Jev', 0.3, 43.7], ['4b lp', 1.7, 51.3], ['9b lp', 2.8, 38.1], ['27b lp', 8.9, 34.4], ['d3-27b', 14.7, 30.2]
];
var FAULT = [ /* section 7: AUROC on the 249 roster pairs, October runs */
  ['Qwen 4B with roster', [['Default batch', 0.805], ['Default batch, reloaded', 0.529], ['CPU only, reference', 0.954], ['Batch 8192, the fix', 0.955]]],
  ['Qwen 9B with roster', [['Default batch', 0.839], ['Default batch, reloaded', 0.563], ['CPU only, reference', 0.950], ['Batch 8192, the fix', 0.949]]]
];
var REL = [ /* findings-sweep: share responsive in each tenth of the score range */
  ['qwen3.5:9b', 'AUROC 0.963', [0.02, 0.13, 0.31, 0.52, 0.60, 0.78, 0.89, 0.95, 0.97, 1.00]],
  ['qwen3.5:4b', 'AUROC 0.931', [0.02, 0.07, 0.14, 0.26, 0.47, 0.68, 0.82, 0.94, 0.996, 1.00]],
  ['gemma4:e4b', 'AUROC 0.923', [0.04, 0.22, 0.33, 0.34, 0.41, 0.37, 0.44, 0.43, 0.53, 0.83]],
  ['gemma4:12b', 'AUROC 0.917', [0.10, 0.36, 0.40, 0.50, 0.46, 0.43, 0.37, 0.43, 0.36, 0.86]]
];
var KINDS = [
  ['real_positive', 'Real, produced for this request', 'Real responsive'],
  ['close_call_positive', 'Close call', 'Close call'],
  ['privileged_positive', 'Privileged', 'Privileged'],
  ['exempt_other_positive', 'Other exempt', 'Other exempt'],
  ['hard_negative_flipped', 'Flipped hard negative', 'Flipped hard negative'],
  ['real_negative', 'Real, produced for another request', 'Real non-responsive'],
  ['hard_negative', 'Hard negative', 'Hard negative']
];
var KIND_NAME = {}, KIND_SHORT = {};
KINDS.forEach(function (k) { KIND_NAME[k[0]] = k[1]; KIND_SHORT[k[0]] = k[2]; });
var RECIPES = [
  ['same_subject_wrong_date', 'Same subject, wrong date'],
  ['keyword_unrelated_sense', 'Keyword in an unrelated sense'],
  ['keyword_in_signature_or_newsletter', 'Keyword only in a signature or newsletter'],
  ['forwarded_no_content', 'Forwarded with no content'],
  ['same_people_different_subject', 'Same people, different subject']
];
var RECIPE_NAME = { marginal_mention: 'Marginal mention', attorney_client: 'Attorney–client content', personnel_or_deliberative: 'Personnel or deliberative content' };
RECIPES.forEach(function (r) { RECIPE_NAME[r[0]] = r[1]; });

/* share of each kind flagged at each score model's pooled 98% cutoff (figures 15 and 16) */
function kindTable() {
  var out = { cols: SCORE_KEYS, kinds: [], recipes: [], thr: {} };
  var flagged = {};
  SCORE_KEYS.forEach(function (k) {
    var rs = rowsFor(k), t = thr98(rs).thr;
    out.thr[k] = t;
    flagged[k] = {};
    rs.forEach(function (r) { flagged[k][r.p.uid] = r.s >= t; });
  });
  function share(filter) {
    var ps = P.filter(filter);
    return { n: ps.length, v: SCORE_KEYS.map(function (k) { return ps.filter(function (p) { return flagged[k][p.uid]; }).length / ps.length; }) };
  }
  KINDS.forEach(function (kd) {
    var s = share(function (p) { return p.kind === kd[0]; });
    out.kinds.push({ id: kd[0], name: kd[1], n: s.n, v: s.v, pos: kd[0] !== 'real_negative' && kd[0] !== 'hard_negative' });
  });
  RECIPES.forEach(function (rc) {
    var s = share(function (p) { return p.kind === 'hard_negative' && p.recipe === rc[0]; });
    out.recipes.push({ id: rc[0], name: rc[1], n: s.n, v: s.v, pos: false });
  });
  return out;
}

window.CPRA = { rowsFor: rowsFor, auroc: auroc, prCurve: prCurve, atRecall: atRecall, confusion: confusion, thr98: thr98,
  kindTable: kindTable, HEAD: HEAD, ROSTER: ROSTER, THR_INT: THR_INT, VALID: VALID, SCORE_KEYS: SCORE_KEYS, ALL_KEYS: ALL_KEYS, isA: isA, isB: isB };
if (typeof document === 'undefined') return;

/* ---------- DOM helpers ---------- */
var $ = function (id) { return document.getElementById(id); };
function h(tag, cls, text) {
  var e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}
var NS = 'http://www.w3.org/2000/svg';
function sv(tag, attrs, text) {
  var e = document.createElementNS(NS, tag);
  for (var k in attrs) e.setAttribute(k, attrs[k]);
  if (text != null) e.textContent = text;
  return e;
}
function clear(e) { while (e.firstChild) e.removeChild(e.firstChild); }
function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
function fmtCut(v) {
  if (v <= 0) return '0';
  if (v >= 1) return '1';
  return (v < 0.0995 || v > 0.9005) ? v.toFixed(4).replace(/0$/, '') : v.toFixed(3).replace(/0$/, '');
}
function fmtScore(v) { return v == null ? 'none' : (v < 0.001 && v > 0 ? v.toExponential(0) : v.toFixed(3)); }
function pc(x, d) { return (x * 100).toFixed(d || 0) + '%'; }
function label(key) { return CFG[key].label; }
function raf(fn) { var q = false; return function () { if (q) return; q = true; requestAnimationFrame(function () { q = false; fn(); }); }; }

/* tooltip */
var tipEl = $('tip');
function showTip(x, y, title, lines) {
  if (!tipEl) return;
  clear(tipEl);
  tipEl.appendChild(h('b', null, title));
  (lines || []).forEach(function (l) { tipEl.appendChild(h('span', null, l)); });
  tipEl.hidden = false;
  var r = tipEl.getBoundingClientRect();
  var left = clamp(x + 14, 8, window.innerWidth - r.width - 8);
  var top = y - r.height - 14;
  if (top < 8) top = y + 18;
  tipEl.style.left = left + 'px';
  tipEl.style.top = top + 'px';
}
function hideTip() { if (tipEl) tipEl.hidden = true; }
function tipOn(node, title, lines) {
  node.addEventListener('pointerenter', function (e) { showTip(e.clientX, e.clientY, title, typeof lines === 'function' ? lines() : lines); });
  node.addEventListener('pointermove', function (e) { if (!tipEl.hidden) showTip(e.clientX, e.clientY, title, typeof lines === 'function' ? lines() : lines); });
  node.addEventListener('pointerleave', hideTip);
}

/* chips */
function chips(host, items, value, onPick) {
  clear(host);
  var btns = items.map(function (it) {
    var b = h('button', 'chip', it[1]);
    b.type = 'button';
    b.setAttribute('aria-pressed', String(it[0] === value));
    b.addEventListener('click', function () { set(it[0]); onPick(it[0]); });
    host.appendChild(b);
    return b;
  });
  function set(v) { btns.forEach(function (b, i) { b.setAttribute('aria-pressed', String(items[i][0] === v)); }); }
  return { set: set };
}

/* readout tiles */
function tile(k, v, l, sw) {
  var d = h('div'), kk = h('div', 'tile-k');
  if (sw) { var i = h('i'); i.style.background = 'var(--' + sw + ')'; kk.appendChild(i); }
  kk.appendChild(document.createTextNode(k));
  d.appendChild(kk); d.appendChild(h('div', 'tile-v', v)); d.appendChild(h('div', 'tile-l', l));
  return d;
}

/* row charts */
function rw(host, o) {
  var r = h('div', 'rw' + (o.cls ? ' ' + o.cls : ''));
  var lab = h('div', 'lab', o.lab);
  if (o.sub) { lab.appendChild(document.createTextNode(' ')); lab.appendChild(h('small', null, o.sub)); }
  r.appendChild(lab);
  var trk = h('div', 'trk');
  (o.marks || []).forEach(function (m) {
    var e = h('i', m.c);
    e.style.display = 'block';
    if (m.left != null) e.style.left = (typeof m.left === 'number' ? m.left + '%' : m.left);
    if (m.width != null) e.style.width = (typeof m.width === 'number' ? m.width + '%' : m.width);
    if (m.style) e.style.cssText += ';' + m.style;
    trk.appendChild(e);
  });
  r.appendChild(trk);
  r.appendChild(h('div', 'val', o.val == null ? '' : o.val));
  if (o.tip) tipOn(r, o.tip[0], o.tip[1]);
  host.appendChild(r);
  return r;
}
function rwGroup(host, text) { var r = h('div', 'rw grp'); r.appendChild(h('div', 'lab', text)); host.appendChild(r); }
function rwAxis(host, ticks) {
  var r = h('div', 'rw axis');
  r.appendChild(h('div', 'lab'));
  var trk = h('div', 'trk');
  ticks.forEach(function (t) { var s = h('span', null, t[1]); s.style.left = t[0] + '%'; trk.appendChild(s); });
  r.appendChild(trk); r.appendChild(h('div', 'val'));
  host.appendChild(r);
}

/* ---------- strip chart: one dot per email, placed by score ---------- */
var LO = 0.001, HI = 0.999;
function logit(p) { return Math.log(p / (1 - p)); }
var L0 = logit(LO), L1 = logit(HI);
function tOf(s, axis) { return axis === 'linear' ? clamp(s, 0, 1) : (logit(clamp(s, LO, HI)) - L0) / (L1 - L0); }
function sOf(t, axis) {
  if (t <= 0) return 0;
  if (t >= 1) return 1;
  if (axis === 'linear') return t;
  return 1 / (1 + Math.exp(-(L0 + t * (L1 - L0))));
}
/* Column for each dot. A dot sits in the column its score maps to. Where more dots share a column
   than fit, the pile spreads into neighbouring columns, keeping score order from left to right. */
function layLane(items, nCols, cap, axis) {
  var n = items.length, want = new Array(n), col = new Array(n), tc = new Array(n), i = 0, k;
  for (k = 0; k < n; k++) tc[k] = Math.min(nCols - 1, Math.floor(tOf(items[k].s, axis) * nCols));
  while (i < n) {
    var j = i;
    while (j < n && tc[j] === tc[i]) j++;
    var m = j - i, w = Math.ceil(m / cap), per = Math.ceil(m / w), start = tc[i] - Math.floor((w - 1) / 2);
    for (k = i; k < j; k++) want[k] = start + Math.floor((k - i) / per);
    i = j;
  }
  for (k = 0; k < n; k++) {
    var v = Math.max(want[k], 0);
    if (k > 0 && col[k - 1] > v) v = col[k - 1];
    if (k >= cap && col[k - cap] + 1 > v) v = col[k - cap] + 1;
    col[k] = v;
  }
  for (k = n - 1; k >= 0; k--) {
    var u = Math.min(col[k], nCols - 1);
    if (k < n - 1 && col[k + 1] < u) u = col[k + 1];
    if (k + cap < n && col[k + cap] - 1 < u) u = col[k + cap] - 1;
    col[k] = Math.max(u, 0);
  }
  var out = new Array(n), row = 0;
  for (k = 0; k < n; k++) { row = (k > 0 && col[k] === col[k - 1]) ? row + 1 : 0; out[k] = { col: col[k], row: row }; }
  return out;
}
var TICKS = {
  logit: [[0.001, '0.001'], [0.01, '0.01'], [0.1, '0.1'], [0.5, '0.5'], [0.9, '0.9'], [0.99, '0.99'], [0.999, '0.999']],
  linear: [[0, '0'], [0.25, '0.25'], [0.5, '0.5'], [0.75, '0.75'], [1, '1']]
};
function kindLine(p) { return KIND_SHORT[p.kind] + ' · request ' + p.req; }

function Strip(host, opt) {
  opt = opt || {};
  var me = { cut: opt.cut == null ? null : opt.cut, axis: opt.axis || 'logit', items: [], sel: null };
  var live = !!opt.interactive;
  var W = 0, g = null, dots = [], svgEl = null, lineEl = null, shadeEl = null, capL = null, capR = null, handle = null, st = null;

  function build() {
    W = host.clientWidth || 640;
    var pitch = W < 520 ? 6 : 7, nCols = Math.max(20, Math.floor((W - 8) / pitch));
    var plotW = nCols * pitch, x0 = (W - plotW) / 2;
    var pos = [], neg = [];
    me.items.forEach(function (r) { (r.p.label ? pos : neg).push(r); });
    var cap = clamp(Math.ceil(3.2 * Math.max(pos.length, neg.length, 1) / nCols), opt.minRows || 12, opt.maxRows || 24);
    var top = live ? 42 : 6, laneH = cap * pitch;
    var yTop = top + laneH + 3, yBot = yTop + 20, H = yBot + 3 + laneH + 4;
    g = { x0: x0, plotW: plotW, nCols: nCols, pitch: pitch, top: top, H: H };
    clear(host);
    svgEl = sv('svg', { 'class': 'strip-svg', viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img',
      'aria-label': (opt.label || 'Emails placed by score') + '. ' + pos.length + ' responsive above the axis, ' + neg.length + ' not responsive below.' });
    svgEl.style.touchAction = 'pan-y';
    if (live) { shadeEl = sv('rect', { 'class': 'shade', x: 0, y: top - 8, width: 0, height: H - top + 8 }); svgEl.appendChild(shadeEl); }
    svgEl.appendChild(sv('line', { 'class': 'ax', x1: x0, x2: x0 + plotW, y1: yTop, y2: yTop }));
    svgEl.appendChild(sv('line', { 'class': 'ax', x1: x0, x2: x0 + plotW, y1: yBot, y2: yBot }));
    var ticks = TICKS[me.axis];
    if (W < 520 && me.axis !== 'linear') ticks = ticks.filter(function (t, i) { return i % 2 === 0 || i === 3; }).filter(function (t) { return t[0] !== 0.1 && t[0] !== 0.9 || W >= 360; });
    ticks.forEach(function (t, i) {
      var x = x0 + tOf(t[0], me.axis) * plotW;
      var a = i === 0 ? 'start' : i === ticks.length - 1 ? 'end' : 'middle';
      svgEl.appendChild(sv('text', { 'class': 'tk', x: x, y: yTop + 14, 'text-anchor': a }, t[1]));
    });
    var gd = sv('g', {});
    dots = [];
    function lane(items, up) {
      var lay = layLane(items, nCols, cap, me.axis);
      items.forEach(function (r, i) {
        var cx = x0 + (lay[i].col + 0.5) * pitch;
        var cy = up ? yTop - 3 - (lay[i].row + 0.5) * pitch : yBot + 3 + (lay[i].row + 0.5) * pitch;
        var c = sv('circle', { cx: cx, cy: cy, r: pitch / 2 - 0.6 });
        gd.appendChild(c);
        dots.push({ r: r, cx: cx, cy: cy, el: c, cls: '' });
      });
    }
    lane(pos, true); lane(neg, false);
    svgEl.appendChild(gd);
    var halo = 'paint-order:stroke;stroke:var(--surface);stroke-width:4px;stroke-linejoin:round';
    svgEl.appendChild(sv('text', { 'class': 'lbl', x: x0 + 2, y: top + 11, style: halo }, pos.length + ' responsive'));
    svgEl.appendChild(sv('text', { 'class': 'lbl', x: x0 + plotW - 2, y: H - 6, 'text-anchor': 'end', style: halo }, neg.length + ' not responsive'));
    if (live) {
      lineEl = sv('line', { 'class': 'cut-line', x1: 0, x2: 0, y1: top - 8, y2: H });
      capL = sv('text', { 'class': 'cap-t', y: 21, 'text-anchor': 'end' }, '◀ screened out');
      capR = sv('text', { 'class': 'cap-t', y: 21, 'text-anchor': 'start' }, 'sent to review ▶');
      svgEl.appendChild(lineEl); svgEl.appendChild(capL); svgEl.appendChild(capR);
    }
    host.appendChild(svgEl);
    if (live) {
      handle = h('button', 'cut-h');
      handle.type = 'button';
      handle.setAttribute('role', 'slider');
      handle.setAttribute('aria-label', 'Cutoff score');
      handle.setAttribute('aria-valuemin', '0');
      handle.setAttribute('aria-valuemax', '1');
      host.appendChild(handle);
      handle.addEventListener('pointerdown', function (e) { handle.setPointerCapture(e.pointerId); handle._d = true; e.preventDefault(); handle.focus(); });
      handle.addEventListener('pointermove', function (e) { if (handle._d) me.setCut(fromClient(e)); });
      handle.addEventListener('pointerup', function () { handle._d = false; });
      handle.addEventListener('pointercancel', function () { handle._d = false; });
      handle.addEventListener('keydown', function (e) {
        var t = tOf(me.cut, me.axis), stp = 1 / nCols;
        if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') t -= stp;
        else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') t += stp;
        else if (e.key === 'PageDown') t -= 5 * stp;
        else if (e.key === 'PageUp') t += 5 * stp;
        else if (e.key === 'Home') t = 0;
        else if (e.key === 'End') t = 1;
        else return;
        e.preventDefault();
        me.setCut(sOf(clamp(t, 0, 1), me.axis));
      });
    }
    svgEl.addEventListener('pointerdown', function (e) {
      if (e.button) return;
      st = { x: e.clientX, y: e.clientY, drag: false };
      if (live) { try { svgEl.setPointerCapture(e.pointerId); } catch (err) {} }
    });
    svgEl.addEventListener('pointermove', function (e) {
      if (st && live) {
        var dx = Math.abs(e.clientX - st.x);
        if (!st.drag && dx > 5 && dx > Math.abs(e.clientY - st.y)) st.drag = true;
        if (st.drag) { hideTip(); me.setCut(fromClient(e)); return; }
      }
      if (e.pointerType === 'touch') return;
      var d = nearest(e);
      svgEl.style.cursor = d ? 'pointer' : (live ? 'ew-resize' : 'default');
      if (d) showTip(e.clientX, e.clientY, fmtScore(d.r.s), [d.r.p.subj || '(no subject)', kindLine(d.r.p)]);
      else hideTip();
    });
    svgEl.addEventListener('pointerup', function (e) {
      if (!st) return;
      var was = st; st = null;
      if (was.drag) return;
      var d = nearest(e);
      if (d && opt.onPick) { me.select(d.r.p.uid); opt.onPick(d.r.p); }
      else if (live) me.setCut(fromClient(e));
    });
    svgEl.addEventListener('pointercancel', function () { st = null; });
    svgEl.addEventListener('pointerleave', hideTip);
    paint();
  }
  function local(e) {
    var r = svgEl.getBoundingClientRect(), k = W / (r.width || W);
    return { x: (e.clientX - r.left) * k, y: (e.clientY - r.top) * k };
  }
  function fromClient(e) { return sOf(clamp((local(e).x - g.x0) / g.plotW, 0, 1), me.axis); }
  function nearest(e) {
    var q = local(e), best = null, bd = 12 * 12;
    for (var i = 0; i < dots.length; i++) {
      var dx = dots[i].cx - q.x, dy = dots[i].cy - q.y, dd = dx * dx + dy * dy;
      if (dd < bd) { bd = dd; best = dots[i]; }
    }
    return best;
  }
  function paint() {
    var cut = me.cut;
    for (var i = 0; i < dots.length; i++) {
      var d = dots[i], c = 'dot ' + (d.r.p.label ? 'pos' : 'neg');
      if (live && cut != null && d.r.s < cut) c += d.r.p.label ? ' miss' : ' gone';
      if (me.sel && d.r.p.uid === me.sel) c += ' sel';
      if (d.cls !== c) { d.el.setAttribute('class', c); d.cls = c; }
    }
    if (!live || cut == null || !g) return;
    var x = g.x0 + tOf(cut, me.axis) * g.plotW;
    lineEl.setAttribute('x1', x); lineEl.setAttribute('x2', x);
    shadeEl.setAttribute('width', Math.max(0, x));
    handle.style.left = clamp(x, 26, W - 26) + 'px';
    handle.textContent = fmtCut(cut);
    handle.setAttribute('aria-valuenow', cut.toFixed(4));
    capL.setAttribute('x', x - 38); capL.style.display = x - 38 > 104 ? '' : 'none';
    capR.setAttribute('x', x + 38); capR.style.display = x + 38 < W - 118 ? '' : 'none';
  }
  me.setData = function (items, axis) {
    me.items = items.slice().sort(function (a, b) { return a.s - b.s; });
    if (axis) me.axis = axis;
    build();
  };
  me.setCut = function (v, silent) { me.cut = v; paint(); if (!silent && opt.onChange) opt.onChange(v); };
  me.select = function (id) {
    me.sel = id; paint();
    for (var i = 0; i < dots.length; i++) if (dots[i].r.p.uid === id) dots[i].el.parentNode.appendChild(dots[i].el);
  };
  if (window.ResizeObserver) {
    new ResizeObserver(function () { var w = host.clientWidth; if (g && w && Math.abs(w - W) > 1) build(); }).observe(host);
  } else {
    window.addEventListener('resize', function () { if (g && host.clientWidth !== W) build(); });
  }
  return me;
}

/* ---------- email card ---------- */
var THR = {};
SCORE_KEYS.forEach(function (k) { THR[k] = thr98(rowsFor(k)).thr; });
function fmtDate(d) {
  if (!d) return '';
  var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(d);
  if (!m) return d;
  return ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][+m[2] - 1] + ' ' + (+m[3]) + ', ' + m[1];
}
function mailCard(host, p, focusKey) {
  clear(host);
  var m = h('div', 'mail'), tags = h('div', 'tags');
  tags.appendChild(h('span', 'tag ' + (p.label ? 'pos' : 'neg'), p.label ? 'Responsive' : 'Not responsive'));
  tags.appendChild(h('span', 'tag', 'Request ' + p.req));
  tags.appendChild(h('span', 'tag', KIND_NAME[p.kind]));
  if (p.recipe && RECIPE_NAME[p.recipe]) tags.appendChild(h('span', 'tag', RECIPE_NAME[p.recipe]));
  tags.appendChild(h('span', 'tag', p.real ? 'Real email' : 'Synthetic'));
  m.appendChild(tags);
  var hd = h('div', 'hd');
  function line(k, v, strong) { var d = h('div'); d.appendChild(document.createTextNode(k + ': ')); d.appendChild(h(strong ? 'b' : 'span', null, v)); hd.appendChild(d); }
  line('Subject', p.subj || '(no subject)', true);
  line('From', p.from || '(unknown)');
  line('Date', fmtDate(p.date) + (p.nrec != null ? ' · ' + p.nrec + (p.nrec === 1 ? ' recipient' : ' recipients') : ''));
  m.appendChild(hd);
  m.appendChild(h('div', 'body', p.snip || '(empty body)'));
  var sub = h('p', 'subh', 'Score from each model. The red tick is that model’s 98% recall cutoff.');
  sub.style.margin = '16px 0 8px';
  m.appendChild(sub);
  var rows = h('div', 'rows');
  rows.style.setProperty('--labw', '3.9rem'); rows.style.setProperty('--valw', '5.2rem');
  SCORE_KEYS.forEach(function (k) {
    var s = p.s[k], kept = s >= THR[k];
    rw(rows, { lab: label(k), cls: k === focusKey ? 'hl' : '', val: fmtScore(s) + (kept ? ' kept' : ' cut'),
      marks: [{ c: 'bar thin ' + (p.label ? 'pos' : 'neg'), width: Math.max(0.5, s * 100) }, { c: 'refl', left: THR[k] * 100 }] });
  });
  m.appendChild(rows);
  host.appendChild(m);
}

/* ---------- hero ---------- */
(function () {
  if (!$('hero-strip')) return;
  var key = 'd27', rs = rowsFor(key);
  var strip = Strip($('hero-strip'), { interactive: true, label: 'All 496 pairs placed by score',
    onChange: raf(read), onPick: function (p) { mailCard($('hero-mail'), p, key); } });
  function read() {
    var c = confusion(rs, strip.cut), host = $('hero-read');
    clear(host);
    host.appendChild(tile('Cutoff', fmtCut(strip.cut), 'Emails scoring below this are screened out.'));
    host.appendChild(tile('Responsive screened out', c.fn + ' of ' + (c.tp + c.fn), 'Recall ' + pc(c.tp / (c.tp + c.fn), 1) + '. These are the misses.', 'pos'));
    host.appendChild(tile('Non-responsive cleared', pc(c.tn / (c.tn + c.fp)), c.tn + ' of ' + (c.tn + c.fp) + ' never reach a reviewer.', 'neg'));
  }
  function load(k) { key = k; rs = rowsFor(k); strip.setData(rs); strip.setCut(thr98(rs).thr); }
  chips($('hero-models'), [['d27', 'd3-27b'], ['lp27', '27b lp'], ['jev', 'Jev']], key, load);
  $('hero-98').addEventListener('click', function () { strip.setCut(thr98(rs).thr); });
  $('hero-50').addEventListener('click', function () { strip.setCut(0.5); });
  load(key);
})();

var BY_ID = {};
P.forEach(function (p) { BY_ID[p.uid] = p; });
var NARROW = window.innerWidth < 620;

var AUC_TICKS = NARROW ? [[0, '0.75'], [60, '0.90'], [100, '1.00']] : [[0, '0.75'], [20, '0.80'], [40, '0.85'], [60, '0.90'], [80, '0.95'], [100, '1.00']];

/* ---------- fig 2: token demo ---------- */
(function () {
  var host = $('tok-chips');
  if (!host) return;
  var EX = [['24-409|24-409:32980329', 'A clear yes'], ['24-409|25-3152:48518074', 'A clear no'], ['24-409|24-409:33733472', 'A torn one']];
  var NOTE = {
    '24-409|24-409:32980329': 'A reply on the water report’s budget, inside the date window. The label is responsive.',
    '24-409|25-3152:48518074': 'A sales pitch from the other request’s production. The label is not responsive.',
    '24-409|24-409:33733472': 'A one-line reply on a covered thread. The label is responsive, and the model’s top token is no by a hair.'
  };
  function block(parent, cls, text) { var d = h('div', cls, text); d.style.whiteSpace = 'pre-wrap'; parent.appendChild(d); return d; }
  function show(id) {
    var p = BY_ID[id];
    if (!p) return;
    var pr = $('tok-prompt');
    clear(pr);
    pr.appendChild(h('span', 'role', 'System'));
    block(pr, 'dim', 'You are a public records analyst for a California county. You will be shown a California Public Records Act (CPRA) request and one email from the county’s email system. Decide whether the email is responsive to the request … Answer with a single word: yes or no.');
    pr.appendChild(h('span', 'role', 'User'));
    block(pr, null, 'CPRA request:');
    block(pr, 'dim', '(1) total time range of January 1, 2023 through July 31, 2023 … (3) Anything related to the regional water equity report or RDF …  [request 24-409, abridged]');
    var body = (p.snip || '').replace(/\s+/g, ' ').slice(0, 150);
    block(pr, null, '\nEmail:\nFrom: ' + (p.from || '') + '\nDate: ' + (p.date || '') + '\nSubject: ' + (p.subj || '') + '\n\n' + body + ' …');
    block(pr, null, '\nIs this email responsive to the request? Answer yes or no.');
    pr.appendChild(h('span', 'role', 'Model, first token'));
    block(pr, null, p.top3[0][0] + ' ▮');
    var bars = $('tok-bars');
    clear(bars);
    p.top3.forEach(function (t) {
      var r = h('div', 'tokrow'), lc = t[0].toLowerCase();
      r.appendChild(h('span', 't', t[0]));
      var b = h('span', 'b' + (lc === 'yes' ? ' pos' : lc === 'no' ? ' neg' : ''));
      b.style.display = 'block'; b.style.width = Math.max(0.5, t[1] * 100) + '%';
      var wrap = h('span'); wrap.style.display = 'block'; wrap.appendChild(b);
      r.appendChild(wrap);
      r.appendChild(h('span', 'v', t[1].toFixed(4)));
      bars.appendChild(r);
    });
    var f = $('tok-formula');
    clear(f);
    var sc = p.pyn[0] / (p.pyn[0] + p.pyn[1]);
    f.appendChild(document.createTextNode('all spellings of yes ' + p.pyn[0].toFixed(5) + ' ÷ (yes ' + p.pyn[0].toFixed(5) + ' + no ' + p.pyn[1].toFixed(5) + ')'));
    f.appendChild(h('br'));
    f.appendChild(document.createTextNode('score = '));
    f.appendChild(h('b', null, sc.toFixed(4)));
    var n = h('div', null, NOTE[id]);
    n.style.cssText = 'font-family:var(--body);font-size:.86rem;color:var(--ink2);margin-top:8px';
    f.appendChild(n);
  }
  chips(host, EX, EX[0][0], show);
  show(EX[0][0]);
})();

/* ---------- fig 3: seconds per email ---------- */
(function () {
  var host = $('time-bars');
  if (!host) return;
  [['Qwen 4B', 'lp4', 'js4', 'jr4'], ['Qwen 9B', 'lp9', 'js9', 'jr9'], ['Qwen 27B', 'lp27', 'js27', 'jr27']].forEach(function (g) {
    rwGroup(host, g[0]);
    [[g[1], 'Yes/no score', 'bar'], [g[2], 'JSON, verdict first', 'bar soft'], [g[3], 'JSON, reasons first', 'bar soft']].forEach(function (r) {
      var s = HEAD[r[0]].sec;
      rw(host, { lab: r[1], val: s.toFixed(2) + ' s', marks: [{ c: r[2], width: s / 8 * 100 }] });
    });
  });
  rwAxis(host, [[0, '0'], [25, '2'], [50, '4'], [75, '6'], [100, '8 s']]);
})();

/* ---------- fig 6: reliability small multiples ---------- */
(function () {
  var host = $('rel');
  if (!host) return;
  REL.forEach(function (m) {
    var d = h('div');
    d.appendChild(h('h5', null, m[0]));
    d.appendChild(h('p', null, m[1]));
    var bars = h('div', 'relbars');
    bars.setAttribute('role', 'img');
    bars.setAttribute('aria-label', m[0] + ': share responsive by score tenth, ' + m[2].join(', '));
    m[2].forEach(function (v, i) {
      var b = h('i');
      b.style.height = Math.max(1, v * 100) + '%';
      tipOn(b, pc(v, v > 0.99 && v < 1 ? 1 : 0) + ' responsive', ['Scores from ' + (i / 10).toFixed(1) + ' to ' + ((i + 1) / 10).toFixed(1)]);
      bars.appendChild(b);
    });
    d.appendChild(bars);
    var ax = h('div', 'relax');
    ax.appendChild(h('span', null, 'score 0')); ax.appendChild(h('span', null, '1'));
    d.appendChild(ax);
    host.appendChild(d);
  });
  var det = h('details');
  det.style.cssText = 'grid-column:1/-1;font-size:.84rem;color:var(--ink2)';
  det.appendChild(h('summary', null, 'Show the values'));
  var wrap = h('div', 'tbl-wrap'), t = h('table'), hr = h('tr');
  hr.appendChild(h('th', null, 'Score'));
  for (var i = 0; i < 10; i++) hr.appendChild(h('th', 'n', (i / 10).toFixed(1) + '–' + ((i + 1) / 10).toFixed(1)));
  var th = h('thead'); th.appendChild(hr); t.appendChild(th);
  var tb = h('tbody');
  REL.forEach(function (m) {
    var tr = h('tr');
    tr.appendChild(h('td', null, m[0]));
    m[2].forEach(function (v) { tr.appendChild(h('td', 'n', v === 0.996 ? '.996' : v.toFixed(2).replace(/^0/, ''))); });
    tb.appendChild(tr);
  });
  t.appendChild(tb); wrap.appendChild(t); det.appendChild(wrap);
  host.appendChild(det);
})();

/* ---------- fig 7: unit grid ---------- */
(function () {
  var host = $('ugrid');
  if (!host) return;
  var cur = null;
  [[REQ_A, '24-409 · the water report'], [REQ_B, '25-3152 · Alpine planning group']].forEach(function (rq) {
    var col = h('div'), ps = P.filter(function (p) { return p.req === rq[0]; });
    col.appendChild(h('p', 'subh', rq[1] + ' · ' + ps.length + ' pairs'));
    KINDS.forEach(function (kd) {
      var sub = ps.filter(function (p) { return p.kind === kd[0]; });
      if (!sub.length) return;
      var b = h('div', 'ublock'), ul = h('div', 'ul');
      ul.appendChild(h('b', null, kd[1])); ul.appendChild(h('span', null, String(sub.length)));
      var sq = h('div', 'usq');
      sub.forEach(function (p) {
        var bt = h('button', p.label ? '' : 'neg');
        bt.type = 'button';
        bt.setAttribute('data-id', p.uid);
        bt.setAttribute('aria-label', (p.label ? 'Responsive: ' : 'Not responsive: ') + (p.subj || '(no subject)'));
        sq.appendChild(bt);
      });
      b.appendChild(ul); b.appendChild(sq); col.appendChild(b);
    });
    host.appendChild(col);
  });
  host.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('button[data-id]') : null;
    if (!b) return;
    if (cur) cur.removeAttribute('aria-pressed');
    b.setAttribute('aria-pressed', 'true'); cur = b;
    mailCard($('golden-mail'), BY_ID[b.getAttribute('data-id')]);
  });
  host.addEventListener('pointerover', function (e) {
    var b = e.target.closest ? e.target.closest('button[data-id]') : null;
    if (!b || e.pointerType === 'touch') { hideTip(); return; }
    var p = BY_ID[b.getAttribute('data-id')];
    showTip(e.clientX, e.clientY, p.subj || '(no subject)', [KIND_NAME[p.kind], fmtDate(p.date)]);
  });
  host.addEventListener('pointerleave', hideTip);
})();

/* ---------- fig 8: backend fault ---------- */
(function () {
  var host = $('fault');
  if (!host) return;
  if (NARROW) host.style.setProperty('--labw', '9.4rem');
  FAULT.forEach(function (g) {
    rwGroup(host, g[0]);
    g[1].forEach(function (r, i) {
      var x = (r[1] - 0.5) / 0.5 * 100;
      rw(host, { lab: r[0], val: r[1].toFixed(3), cls: i === 3 ? 'hl' : '', marks: [{ c: 'bar thin soft', width: x }, { c: 'pt', left: x }] });
    });
  });
  rwAxis(host, NARROW ? [[0, '0.5'], [40, '0.7'], [80, '0.9']] : [[0, '0.5 coin flip'], [20, '0.6'], [40, '0.7'], [60, '0.8'], [80, '0.9'], [100, '1.0']]);
})();

/* ---------- fig 9: forest plots ---------- */
(function () {
  var ha = $('forest-auc'), he = $('forest-elim');
  if (!ha || !he) return;
  var GROUPS = [['Stock Qwen, yes/no score', ['lp4', 'lp9', 'lp27'], ''], ['Decision models, yes/no score', ['d4', 'd9', 'd27', 'jev'], ''],
    ['JSON, verdict first', ['js4', 'js9', 'js27'], 'dim'], ['JSON, reasoning first', ['jr4', 'jr9', 'jr27'], 'dim']];
  var ax = function (v) { return (v - 0.75) / 0.25 * 100; };
  GROUPS.forEach(function (g) {
    rwGroup(ha, g[0]); rwGroup(he, g[0]);
    g[1].forEach(function (k) {
      var d = HEAD[k];
      rw(ha, { lab: label(k), cls: g[2], val: d.auc.toFixed(3),
        marks: [{ c: 'ci', left: ax(d.aci[0]), width: ax(d.aci[1]) - ax(d.aci[0]) }, { c: 'pt', left: ax(d.auc) }],
        tip: [label(k) + ' · AUROC ' + d.auc.toFixed(3), ['95% interval ' + d.aci[0].toFixed(3) + ' to ' + d.aci[1].toFixed(3)]] });
      var marks = [{ c: 'refl', left: 50, style: 'border-left-style:dashed' }];
      if (d.eci) marks.push({ c: 'ci', left: d.eci[0], width: d.eci[1] - d.eci[0] });
      marks.push({ c: 'pt', left: d.el });
      rw(he, { lab: label(k), cls: g[2], val: d.el + '%', marks: marks,
        tip: [label(k) + ' · ' + d.el + '% cleared', [d.eci ? '95% interval ' + d.eci[0] + ' to ' + d.eci[1] + '%' : 'No interval reported']] });
    });
  });
  rwAxis(ha, AUC_TICKS);
  rwAxis(he, [[0, '0%'], [25, '25'], [50, '50'], [75, '75'], [100, '100%']]);
})();

/* ---------- fig 10: explorer ---------- */
(function () {
  if (!$('ex-strip')) return;
  var S = { key: 'd27', req: 'all', axis: 'logit', sel: null }, rs = [];
  var kh = $('ex-kinds');
  kh.style.setProperty('--labw', NARROW ? '8.6rem' : '10.5rem');
  kh.style.setProperty('--valw', NARROW ? '2.8rem' : '6.8rem');
  var strip = Strip($('ex-strip'), { interactive: true, label: 'Emails placed by score', onChange: raf(render), onPick: function (p) { pick(p.uid); } });
  function filt() { return S.req === 'A' ? isA : S.req === 'all' ? null : isB; }
  function load(keepCut) {
    var c = strip.cut;
    rs = rowsFor(S.key, filt(), S.req === 'BR');
    strip.setData(rs, S.axis);
    if (S.sel) strip.select(S.sel);
    strip.setCut(keepCut && c != null ? c : thr98(rs).thr);
  }
  var mC, jC;
  function setKey(k) { S.key = k; mC.set(k); jC.set(k); load(false); if (S.sel) mailCard($('ex-mail'), BY_ID[S.sel], S.key); }
  mC = chips($('ex-models'), SCORE_KEYS.map(function (k) { return [k, label(k)]; }), S.key, setKey);
  jC = chips($('ex-json'), JSON_KEYS.map(function (k) { return [k, label(k)]; }), S.key, setKey);
  chips($('ex-req'), [['all', 'Both'], ['A', '24-409'], ['B', '25-3152'], ['BR', '25-3152 with roster']], S.req, function (v) { S.req = v; load(false); });
  chips($('ex-axis'), [['logit', 'Stretched'], ['linear', 'Linear']], S.axis, function (v) { S.axis = v; load(true); });
  $('ex-98').addEventListener('click', function () { strip.setCut(thr98(rs).thr); });
  $('ex-50').addEventListener('click', function () { strip.setCut(0.5); });
  function fill(ul, list, empty) {
    clear(ul);
    if (!list.length) { ul.appendChild(h('li', 'mlist-empty', empty)); return; }
    list.slice(0, 120).forEach(function (r) {
      var li = h('li'), b = h('button');
      b.type = 'button';
      b.setAttribute('data-id', r.p.uid);
      if (r.p.uid === S.sel) b.setAttribute('aria-pressed', 'true');
      b.appendChild(h('span', 'sc', fmtScore(r.s)));
      var d = h('span');
      d.style.cssText = 'display:block;min-width:0';
      var sj = h('span', 'sj', r.p.subj || '(no subject)'); sj.style.display = 'block';
      d.appendChild(sj); d.appendChild(h('span', 'kd', kindLine(r.p)));
      b.appendChild(d); li.appendChild(b); ul.appendChild(li);
    });
    if (list.length > 120) ul.appendChild(h('li', 'mlist-empty', 'and ' + (list.length - 120) + ' more'));
  }
  function render() {
    var cut = strip.cut, c = confusion(rs, cut), nP = c.tp + c.fn, nN = c.fp + c.tn, host = $('ex-read');
    clear(host);
    host.appendChild(tile('Cutoff', fmtCut(cut), label(S.key) + ', ' + rs.length + ' pairs scored.'));
    host.appendChild(tile('Responsive screened out', c.fn + ' of ' + nP, 'Recall ' + pc(c.tp / nP, 1) + '.', 'pos'));
    host.appendChild(tile('Non-responsive cleared', pc(c.tn / nN), c.tn + ' of ' + nN + '.', 'neg'));
    host.appendChild(tile('Sent to review', (c.tp + c.fp) + ' of ' + rs.length, (c.tp + c.fp) ? pc(c.tp / (c.tp + c.fp)) + ' of them responsive.' : 'Nothing is flagged.'));
    clear(kh);
    KINDS.forEach(function (kd) {
      var sub = rs.filter(function (r) { return r.p.kind === kd[0]; });
      if (!sub.length) return;
      var f = sub.filter(function (r) { return r.s >= cut; }).length;
      rw(kh, { lab: kd[2], val: NARROW ? pc(f / sub.length) : f + '/' + sub.length + ' · ' + pc(f / sub.length),
        marks: [{ c: 'bar ' + (sub[0].p.label ? 'pos' : 'neg'), width: f / sub.length * 100 }] });
    });
    rwAxis(kh, [[0, '0%'], [50, '50%'], [100, '100%']]);
    var miss = rs.filter(function (r) { return r.p.label && r.s < cut; }).sort(function (a, b) { return a.s - b.s; });
    var kept = rs.filter(function (r) { return !r.p.label && r.s >= cut; }).sort(function (a, b) { return b.s - a.s; });
    $('ex-miss-h').textContent = 'Responsive emails screened out (' + miss.length + ')';
    $('ex-kept-h').textContent = 'Non-responsive emails still sent to review (' + kept.length + ')';
    fill($('ex-miss'), miss, 'No responsive email is screened out at this cutoff.');
    fill($('ex-kept'), kept, 'No non-responsive email reaches review at this cutoff.');
  }
  function pick(id) {
    S.sel = id;
    strip.select(id);
    mailCard($('ex-mail'), BY_ID[id], S.key);
    ['ex-miss', 'ex-kept'].forEach(function (u) {
      var bs = $(u).querySelectorAll('button[data-id]');
      for (var i = 0; i < bs.length; i++) bs[i].setAttribute('aria-pressed', String(bs[i].getAttribute('data-id') === id));
    });
  }
  ['ex-miss', 'ex-kept'].forEach(function (u) {
    $(u).addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('button[data-id]') : null;
      if (b) pick(b.getAttribute('data-id'));
    });
  });
  load(false);
})();

/* ---------- fig 11: speed against clearance ---------- */
(function () {
  var host = $('scatter');
  if (!host) return;
  var LAB = { jev: [2, -11, 'start'], lp4: [-10, 5, 'end'], d4: [10, 5, 'start'], lp9: [-2, -11, 'middle'], d9: [10, 5, 'start'], lp27: [-10, -7, 'end'], d27: [0, -12, 'middle'],
    js4: [-10, 4, 'end'], jr4: [-10, -6, 'end'], js9: [0, -11, 'middle'], jr9: [10, -7, 'start'], js27: [-10, 4, 'end'], jr27: [-10, 4, 'end'] };
  var FRONT = ['jev', 'lp9', 'lp27', 'd27'];
  var lg = h('div', 'legend');
  [['background:var(--ink)', 'Yes/no score'], ['background:var(--surface);box-shadow:inset 0 0 0 1.6px var(--ink3)', 'JSON verdict']].forEach(function (l) {
    var s = h('span'), i = h('i'); i.style.cssText = l[0]; s.appendChild(i); s.appendChild(document.createTextNode(l[1])); lg.appendChild(s);
  });
  lg.appendChild(h('span', null, 'Line: nothing faster clears more'));
  var box = h('div', 'svgc');
  host.appendChild(lg); host.appendChild(box);
  var W = 0;
  function draw() {
    W = box.clientWidth || 640;
    var narrow = W < 560, H = narrow ? 330 : 410, m = { l: 44, r: 20, t: 24, b: 44 }, pw = W - m.l - m.r, ph = H - m.t - m.b;
    var x = function (s) { return m.l + (Math.log(s) / Math.LN10 + 1) / 2 * pw; };
    var y = function (v) { return m.t + (1 - v / 100) * ph; };
    clear(box);
    var s = sv('svg', { viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img',
      'aria-label': 'Median seconds per email against share of non-responsive email cleared at 98% recall, for 13 configurations' });
    s.style.cssText = 'display:block;width:100%;height:auto;overflow:visible';
    [0, 25, 50, 75, 100].forEach(function (v) {
      s.appendChild(sv('line', { 'class': v ? 'grid' : 'axl', x1: m.l, x2: W - m.r, y1: y(v), y2: y(v) }));
      s.appendChild(sv('text', { 'class': 'tl', x: m.l - 8, y: y(v) + 4, 'text-anchor': 'end' }, v + '%'));
    });
    [0.1, 0.2, 0.5, 1, 2, 5, 10].forEach(function (v) {
      s.appendChild(sv('line', { 'class': 'grid', x1: x(v), x2: x(v), y1: m.t, y2: m.t + ph }));
      s.appendChild(sv('text', { 'class': 'tl', x: x(v), y: m.t + ph + 16, 'text-anchor': 'middle' }, String(v)));
    });
    s.appendChild(sv('text', { 'class': 'al', x: m.l + pw / 2, y: H - 6, 'text-anchor': 'middle' }, 'median seconds per email, log scale'));
    s.appendChild(sv('text', { 'class': 'al', x: 0, y: 12 }, 'non-responsive cleared at 98% recall'));
    s.appendChild(sv('line', { 'class': 'ref', x1: m.l, x2: W - m.r, y1: y(50), y2: y(50), 'stroke-dasharray': '4 4' }));
    s.appendChild(sv('text', { 'class': 'tl', x: m.l + 6, y: y(50) + 14, 'text-anchor': 'start' }, 'target: more than half'));
    s.appendChild(sv('polyline', { 'class': 'front', points: FRONT.map(function (k) { return x(HEAD[k].sec === 0.12 ? 0.117 : HEAD[k].sec) + ',' + y(HEAD[k].el); }).join(' ') }));
    ALL_KEYS.forEach(function (k) {
      var d = HEAD[k], sec = CFG[k].ms / 1000, cx = x(sec), cy = y(d.el), js = CFG[k].family.indexOf('json') === 0, fr = FRONT.indexOf(k) >= 0;
      s.appendChild(sv('circle', { 'class': 'mk' + (js ? ' hollow' : ''), cx: cx, cy: cy, r: 5 }));
      if (!narrow || fr) {
        var L = LAB[k];
        s.appendChild(sv('text', { 'class': 'pl' + (fr ? '' : ' dim'), x: cx + L[0], y: cy + L[1], 'text-anchor': L[2] }, label(k)));
      }
      var hit = sv('circle', { cx: cx, cy: cy, r: 14, fill: 'transparent' });
      tipOn(hit, label(k), [d.sec.toFixed(2) + ' s per email', d.el + '% cleared at 98% recall']);
      s.appendChild(hit);
    });
    box.appendChild(s);
  }
  draw();
  if (window.ResizeObserver) new ResizeObserver(function () { if (Math.abs(box.clientWidth - W) > 1) draw(); }).observe(box);
})();

/* ---------- fig 12: first-token score against written confidence ---------- */
(function () {
  if (!$('js-strip-lp')) return;
  Strip($('js-strip-lp'), { label: '27b lp first-token scores' }).setData(rowsFor('lp27'));
  Strip($('js-strip-js'), { label: '27b json written confidences' }).setData(rowsFor('js27'));
})();

/* ---------- figs 15 and 16: heat tables ---------- */
(function () {
  var a = $('kind-heat'), b = $('recipe-heat');
  if (!a || !b) return;
  var T = kindTable();
  function heat(tbl, rows, head) {
    clear(tbl);
    var th = h('thead'), tr = h('tr');
    tr.appendChild(h('th', null, head)); tr.appendChild(h('th', 'n', 'Emails'));
    SCORE_KEYS.forEach(function (k) { var c = h('th', null, label(k)); c.style.textAlign = 'center'; tr.appendChild(c); });
    th.appendChild(tr); tbl.appendChild(th);
    var tb = h('tbody');
    rows.forEach(function (r) {
      var row = h('tr'), nm = h('td', null, NARROW && KIND_SHORT[r.id] ? KIND_SHORT[r.id] : r.name);
      nm.style.minWidth = NARROW ? '7.5rem' : '11rem';
      row.appendChild(nm); row.appendChild(h('td', 'n', String(r.n)));
      r.v.forEach(function (v) {
        var td = h('td', 'h', Math.round(v * 100) + '%');
        td.style.background = 'color-mix(in oklab, var(--' + (r.pos ? 'pos' : 'neg') + ') ' + Math.round(4 + v * 72) + '%, var(--surface))';
        row.appendChild(td);
      });
      tb.appendChild(row);
    });
    tbl.appendChild(tb);
  }
  heat(a, T.kinds, 'Kind');
  heat(b, T.recipes, 'Recipe');
})();

/* ---------- fig 17: roster dumbbells ---------- */
(function () {
  var he = $('roster-elim'), ha = $('roster-auc');
  if (!he || !ha) return;
  ha.style.setProperty('--div', '5');
  var ax = function (v) { return (v - 0.75) / 0.25 * 100; };
  [['Yes/no score', SCORE_KEYS, ''], ['JSON, verdict first', ['js4', 'js9', 'js27'], 'dim'], ['JSON, reasoning first', ['jr4', 'jr9', 'jr27'], 'dim']].forEach(function (g) {
    rwGroup(he, g[0]); rwGroup(ha, g[0]);
    g[1].forEach(function (k) {
      var e = ROSTER[k].el, a = ROSTER[k].auc;
      rw(he, { lab: label(k), cls: g[2], val: e[0] + ' → ' + e[1] + '%',
        marks: [{ c: 'ci', left: Math.min(e[0], e[1]), width: Math.abs(e[1] - e[0]) }, { c: 'pt hollow', left: e[0] }, { c: 'pt', left: e[1] }] });
      rw(ha, { lab: label(k), cls: g[2], val: a[0].toFixed(3) + ' → ' + a[1].toFixed(3),
        marks: [{ c: 'ci', left: ax(Math.min(a[0], a[1])), width: Math.abs(ax(a[1]) - ax(a[0])) }, { c: 'pt hollow', left: ax(a[0]) }, { c: 'pt', left: ax(a[1]) }] });
    });
  });
  rwAxis(he, [[0, '0%'], [25, '25'], [50, '50'], [75, '75'], [100, '100%']]);
  rwAxis(ha, AUC_TICKS);
})();

/* ---------- fig 18: fitted cutoffs with intervals ---------- */
(function () {
  var host = $('thr-int');
  if (!host) return;
  THR_INT.forEach(function (g) {
    rwGroup(host, label(g.key));
    g.rows.forEach(function (r) {
      var dp = g.key === 'jev' ? 2 : 3;
      rw(host, { lab: r[0], val: r[1].toFixed(dp), marks: [{ c: 'ci', left: r[2] * 100, width: (r[3] - r[2]) * 100 }, { c: r[0].indexOf('roster') > 0 ? 'pt hollow' : 'pt', left: r[1] * 100 }],
        tip: [label(g.key) + ' · ' + r[0], ['Cutoff ' + r[1], '95% interval ' + r[2] + ' to ' + r[3]]] });
    });
  });
  rwAxis(host, NARROW ? [[0, '0'], [40, '0.4'], [80, '0.8']] : [[0, '0'], [20, '0.2'], [40, '0.4'], [60, '0.6'], [80, '0.8'], [100, '1.0']]);
})();

/* ---------- fig 19: cutoff transfer ---------- */
(function () {
  if (!$('tr-stripA')) return;
  var key = 'd27', rsA = [], rsB = [], cut = 0.5, fit = 'A';
  var render = raf(function () {
    var a = confusion(rsA, cut), b = confusion(rsB, cut), host = $('tr-read');
    clear(host);
    host.appendChild(tile('Shared cutoff', fmtCut(cut), fit === 'A' ? 'Fitted on 24-409 for 98% recall.' : fit === 'B' ? 'Fitted on 25-3152 for 98% recall.' : 'Set by hand.'));
    host.appendChild(tile('24-409 screened out', a.fn + ' of ' + (a.tp + a.fn), 'Recall ' + pc(a.tp / (a.tp + a.fn), 1) + '. ' + pc(a.tn / (a.tn + a.fp)) + ' of non-responsive cleared.', 'pos'));
    host.appendChild(tile('25-3152 screened out', b.fn + ' of ' + (b.tp + b.fn), 'Recall ' + pc(b.tp / (b.tp + b.fn), 1) + '. ' + pc(b.tn / (b.tn + b.fp)) + ' of non-responsive cleared.', 'pos'));
    host.appendChild(tile('Both together', (a.fn + b.fn) + ' of ' + (a.tp + a.fn + b.tp + b.fn), pc((a.tn + b.tn) / (a.tn + a.fp + b.tn + b.fp)) + ' of non-responsive cleared.'));
    $('tr-fitA').setAttribute('aria-pressed', String(fit === 'A'));
    $('tr-fitB').setAttribute('aria-pressed', String(fit === 'B'));
  });
  var sA, sB;
  function setCut(v, src) { cut = v; if (src !== sA) sA.setCut(v, true); if (src !== sB) sB.setCut(v, true); render(); }
  sA = Strip($('tr-stripA'), { interactive: true, minRows: 9, maxRows: 16, label: 'Request 24-409 emails by score', onChange: function (v) { fit = null; setCut(v, sA); } });
  sB = Strip($('tr-stripB'), { interactive: true, minRows: 9, maxRows: 16, label: 'Request 25-3152 emails by score', onChange: function (v) { fit = null; setCut(v, sB); } });
  function doFit(w) { fit = w; setCut(thr98(w === 'A' ? rsA : rsB).thr); }
  function load(k) {
    key = k; rsA = rowsFor(k, isA); rsB = rowsFor(k, isB);
    sA.setData(rsA); sB.setData(rsB);
    doFit(fit || 'A');
  }
  chips($('tr-models'), [['d27', 'd3-27b'], ['jev', 'Jev'], ['lp27', '27b lp']], key, load);
  $('tr-fitA').addEventListener('click', function () { doFit('A'); });
  $('tr-fitB').addEventListener('click', function () { doFit('B'); });
  load(key);
})();

/* ---------- fig 21: three versions of the test ---------- */
(function () {
  [['val-all', VALID.all], ['val-real', VALID.real], ['val-hard', VALID.hard]].forEach(function (pn) {
    var host = $(pn[0]);
    if (!host) return;
    SCORE_KEYS.forEach(function (k) {
      rw(host, { lab: label(k), val: pn[1][k] + '%', marks: [{ c: 'bar', width: pn[1][k] }, { c: 'refl', left: 50, style: 'border-left-style:dashed' }] });
    });
    rwAxis(host, [[0, '0%'], [50, '50'], [100, '100%']]);
  });
})();

/* ---------- fig 22: workload ---------- */
(function () {
  var host = $('work');
  if (!host) return;
  if (NARROW) host.style.setProperty('--valw', '3.6rem');
  rw(host, { lab: 'Read everything', val: '83.3 h', marks: [{ c: 'bar', width: 83.3 }] });
  WORK.forEach(function (w) {
    var tot = (w[1] + w[2]).toFixed(1);
    rw(host, { lab: w[0], val: NARROW ? tot + ' h' : w[2].toFixed(1) + ' + ' + w[1].toFixed(1) + ' = ' + tot + ' h',
      marks: [{ c: 'bar', width: w[2], style: 'border-radius:0' }, { c: 'bar soft', left: 'calc(' + w[2] + '% + 2px)', width: w[1] }],
      tip: [w[0], [w[2].toFixed(1) + ' reviewer hours', w[1].toFixed(1) + ' machine hours']] });
  });
  rwAxis(host, NARROW ? [[0, '0'], [40, '40'], [80, '80 h']] : [[0, '0'], [20, '20'], [40, '40'], [60, '60'], [80, '80'], [100, '100 h']]);
})();

/* ---------- contents ---------- */
(function () {
  var toc = $('toc'), tm = $('toc-m');
  if (!toc && !tm) return;
  var nodes = document.querySelectorAll('.part-rule, section[data-t]'), links = [];
  for (var i = 0; i < nodes.length; i++) {
    var n = nodes[i];
    if (n.className.indexOf('part-rule') >= 0) {
      if (toc) { var pl = h('li', 'part', n.lastElementChild.textContent); pl.style.lineHeight = '1.4'; toc.appendChild(pl); }
      continue;
    }
    var num = n.id.slice(1), t = n.getAttribute('data-t');
    [toc, tm].forEach(function (list) {
      if (!list) return;
      var li = h('li'), a = h('a');
      a.href = '#' + n.id;
      a.appendChild(h('span', null, num));
      a.appendChild(document.createTextNode(t));
      li.appendChild(a); list.appendChild(li);
      if (list === toc) links.push({ sec: n, a: a });
    });
  }
  if (tm) tm.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('a')) tm.parentNode.removeAttribute('open'); });
  var spy = raf(function () {
    var on = null;
    for (var j = 0; j < links.length; j++) if (links[j].sec.getBoundingClientRect().top <= 140) on = links[j];
    links.forEach(function (l) { l.a.className = l === on ? 'on' : ''; });
  });
  window.addEventListener('scroll', spy, { passive: true });
  spy();
})();

})();
