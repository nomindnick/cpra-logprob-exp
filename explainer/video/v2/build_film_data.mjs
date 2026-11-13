// Build the second cut's data file from the page data. Output holds anonymous numbers only: no ids, no text from any produced email.
// Run from the repo root:  node explainer/video/v2/build_film_data.mjs
import fs from 'node:fs';
import path from 'node:path';
const HERE = path.dirname(new URL(import.meta.url).pathname);
const load = (f, name) => { const window = {}; eval(fs.readFileSync(f, 'utf8')); return window[name]; };
const DATA = load(path.join(HERE, '../../data.js'), 'DATA'), FD1 = load(path.join(HERE, '../film_data.js'), 'FD');
const P = DATA.pairs;
// a written answer that could not be parsed has no score; the findings leave such rows out of the figures (5 of 12,935 rows)
const sc = (r, key, src = 's') => r[src][key];
const below = (r, key, thr, src = 's') => sc(r, key, src) != null && sc(r, key, src) < thr;
// lowest cutoff that keeps at least 98% of the responsive emails (keep if score >= cutoff)
const thr98 = (rows0, key, src = 's') => {
  const rows = rows0.filter(r => sc(r, key, src) != null);
  const pos = rows.filter(r => r.label === 1).map(r => sc(r, key, src)).sort((a, b) => b - a);
  const thr = pos[Math.ceil(0.98 * pos.length) - 1], neg = rows.filter(r => r.label === 0);
  return { thr, npos: pos.length, nneg: neg.length, cleared: neg.filter(r => below(r, key, thr, src)).length, missed: pos.filter(v => v < thr).length };
};
const A = P.filter(r => r.req === '24-409'), B = P.filter(r => r.req === '25-3152');
const lg = p => (p == null ? 0 : p <= 0 ? -9 : p >= 1 ? 9 : Math.round(Math.log10(p / (1 - p)) * 1000) / 1000);
const cut = { lp: thr98(P, 'lp27'), d: thr98(P, 'd27'), jr: thr98(P, 'jr27'), js: thr98(P, 'js9'), a: thr98(A, 'lp27'), b: thr98(B, 'lp27'), ro: thr98(B, 'lp27', 'r') };
cut.x = { thr: cut.a.thr, npos: cut.b.npos, nneg: cut.b.nneg, cleared: B.filter(r => !r.label && below(r, 'lp27', cut.a.thr)).length, missed: B.filter(r => r.label && below(r, 'lp27', cut.a.thr)).length };
for (const k in cut) cut[k].lo = lg(cut[k].thr);
const KINDS = ['real_positive', 'real_negative', 'close_call_positive', 'privileged_positive', 'exempt_other_positive', 'hard_negative', 'hard_negative_flipped'];
const RECIPES = ['same_subject_wrong_date', 'keyword_unrelated_sense', 'keyword_in_signature_or_newsletter', 'forwarded_no_content', 'same_people_different_subject'];
const RECIPE_TEXT = ['Right subject, wrong dates', 'A keyword, in another sense', 'Keyword only in a signature or newsletter', 'A forward with nothing added', 'Right people, different subject'];
let dots = P.map(r => {
  const b = r.req === '25-3152', own = b ? cut.b.thr : cut.a.thr;
  const k = KINDS.indexOf(r.kind); if (k < 0) throw new Error('kind ' + r.kind);
  return { l: r.label, q: b ? 1 : 0, k, rc: r.kind === 'hard_negative' ? RECIPES.indexOf(r.recipe) : -1,
    lp: lg(sc(r, 'lp27')), d: lg(sc(r, 'd27')), jr: lg(sc(r, 'jr27')), js: lg(sc(r, 'js9')), ro: b ? lg(sc(r, 'lp27', 'r')) : null,
    jrv: r.s.jr27 == null ? -1 : r.s.jr27, jsv: r.s.js9 == null ? -1 : r.s.js9,
    pp: +!below(r, 'lp27', cut.lp.thr), pd: +!below(r, 'd27', cut.d.thr), pj: +!below(r, 'jr27', cut.jr.thr), p9: +!below(r, 'js9', cut.js.thr),
    po: +!below(r, 'lp27', own), px: b ? +!below(r, 'lp27', cut.a.thr) : null, pr: b ? +!below(r, 'lp27', cut.ro.thr, 'r') : null };
});
// fixed shuffle, so a dot's index says nothing about the email behind it
let s = 20261112; const rnd = () => { s = (s + 0x6D2B79F5) >>> 0; let x = Math.imul(s ^ (s >>> 15), 1 | s); x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x; return ((x ^ (x >>> 14)) >>> 0) / 4294967296; };
for (let i = dots.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [dots[i], dots[j]] = [dots[j], dots[i]]; }
const configs = DATA.configs.map(c => { const t = thr98(P, c.key); return { key: c.key, family: c.family, size: c.size, sec: Math.round(c.ms) / 1000, cleared: t.cleared, nneg: t.nneg, share: Math.round(1000 * t.cleared / t.nneg) / 10, pct: Math.round(100 * t.cleared / t.nneg) }; });
const recipes = RECIPES.map((name, i) => { const rows = dots.filter(d => d.rc === i); return { text: RECIPE_TEXT[i], n: rows.length, passed: rows.filter(d => d.pp).length, cleared: rows.filter(d => !d.pp).length }; });
// the figures the narration and the screen use, checked here against the findings
const eq = (what, got, want) => { if (JSON.stringify(got) !== JSON.stringify(want)) throw new Error(`${what}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`); };
eq('pairs', [P.length, A.length, B.length], [496, 247, 249]);
eq('pooled 27B', [cut.lp.cleared, cut.lp.nneg, cut.lp.missed, cut.lp.npos], [160, 207, 5, 289]);
eq('request 1 own line', [cut.a.cleared, cut.a.nneg, cut.a.missed], [91, 101, 2]);
eq('request 2 own line', [cut.b.cleared, cut.b.nneg, cut.b.missed], [81, 106, 2]);
eq('request 1 line on request 2', [cut.x.missed, cut.x.npos, cut.x.cleared], [14, 143, 94]);
eq('roster', [cut.ro.cleared, cut.ro.nneg, cut.ro.missed], [99, 106, 2]);
eq('shares', configs.map(c => c.pct), [53, 72, 77, 55, 70, 83, 64, 10, 0, 28, 0, 0, 67]);
eq('near misses passed', recipes.map(r => [r.passed, r.n]), [[10, 20], [13, 20], [10, 20], [7, 17], [7, 10]]);
eq('real negatives passed', dots.filter(d => d.k === 1 && d.pp).length, 0);
eq('9B written zeros among responsive', dots.filter(d => d.l && d.jsv === 0).length, 43);
const y = FD1.emails.yes;
const demo = { request: FD1.request, model: FD1.model, from: y.from, to: y.to, date: y.date, subject: y.subject, body: y.body, top3: y.top3, p_yes: y.p_yes, p_no: y.p_no, score: y.score, lo: lg(y.score) };
const out = { n: dots.length, dots, cut, configs, recipes, demo };
fs.writeFileSync(path.join(HERE, 'film_data.js'), '// Anonymous scores for the film: no ids, no text of any produced email. The example email is invented.\nwindow.FD = ' + JSON.stringify(out) + ';\n');
console.log('wrote film_data.js', dots.length, 'dots');
console.log(Object.entries(cut).map(([k, c]) => `${k}: thr ${c.thr} (lo ${c.lo}) cleared ${c.cleared}/${c.nneg} missed ${c.missed}/${c.npos}`).join('\n'));
console.log(configs.map(c => `${c.key} ${c.sec}s ${c.share}%`).join(' | '));
console.log(recipes.map(r => `${r.text}: cleared ${r.cleared}/${r.n}`).join(' | '));
