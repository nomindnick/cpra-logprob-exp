// Recompute the page's numbers from data.js through app.js's own metric code and compare with the findings.
import fs from 'node:fs';
import vm from 'node:vm';
const dir = new URL('.', import.meta.url).pathname;
globalThis.window = {};
vm.runInThisContext(fs.readFileSync(dir + 'data.js', 'utf8'));
vm.runInThisContext(fs.readFileSync(dir + 'app.js', 'utf8'));
const C = window.CPRA, D = window.DATA;
let bad = 0;
const eq = (name, got, want, tol = 0) => { if (Math.abs(got - want) > tol) { bad++; console.log('MISMATCH', name, 'got', got, 'want', want); } };
console.log('pairs', D.pairs.length, 'pos', D.pairs.filter(p => p.label).length);
for (const k of C.ALL_KEYS) {
  const rs = C.rowsFor(k), a = C.auroc(rs), t = C.thr98(rs), H = C.HEAD[k];
  eq(k + ' auroc', +a.toFixed(3), H.auc, 0.0005);
  eq(k + ' elim98', Math.round(t.elim * 100), H.el, 0.5);
  if (H.thr != null) eq(k + ' thr98', t.thr, H.thr, 0.0051);
  const c = C.confusion(rs, 0.5);
  console.log(k.padEnd(5), a.toFixed(3), 'thr', t.thr, 'elim', (t.elim * 100).toFixed(1), 'recall98', (t.recall * 100).toFixed(1),
    '| default recall', (100 * c.tp / (c.tp + c.fn)).toFixed(1), 'elim', (100 * c.tn / (c.tn + c.fp)).toFixed(1));
}
// roster rows: 25-3152 only, without and with the roster
for (const k of C.ALL_KEYS) {
  const b = C.rowsFor(k, C.isB, true), R = C.ROSTER[k];
  const keep = new Set(b.map(r => r.p.uid)), a = C.rowsFor(k, p => C.isB(p) && keep.has(p.uid)); // paired: drop a pair that either run failed to parse
  eq(k + ' roster auc no', +C.auroc(a).toFixed(3), R.auc[0], 0.0006);
  eq(k + ' roster auc with', +C.auroc(b).toFixed(3), R.auc[1], 0.0006);
  eq(k + ' roster el no', Math.round(C.thr98(a).elim * 100), R.el[0], 0.5);
  eq(k + ' roster el with', Math.round(C.thr98(b).elim * 100), R.el[1], 0.5);
}
// by-kind and recipe tables against findings section 4
const T = C.kindTable();
const K4 = { real_positive: [97, 98, 97, 97, 98, 97, 97], close_call_positive: [100, 98, 100, 98, 96, 100, 98], privileged_positive: [100, 100, 98, 100, 100, 100, 100],
  exempt_other_positive: [100, 100, 100, 100, 100, 100, 100], hard_negative_flipped: [100, 89, 100, 100, 100, 100, 100], real_negative: [21, 4, 0, 15, 1, 0, 8], hard_negative: [84, 61, 54, 87, 71, 41, 74] };
const R4 = { same_subject_wrong_date: [100, 90, 50, 100, 85, 15, 95], keyword_unrelated_sense: [95, 60, 65, 90, 80, 70, 75], keyword_in_signature_or_newsletter: [75, 50, 50, 70, 50, 35, 75],
  forwarded_no_content: [71, 41, 41, 82, 59, 35, 47], same_people_different_subject: [70, 60, 70, 100, 90, 60, 70] };
for (const r of T.kinds) K4[r.id].forEach((w, i) => eq('kind ' + r.id + ' ' + T.cols[i], Math.round(r.v[i] * 100), w, 0.5));
for (const r of T.recipes) R4[r.id].forEach((w, i) => eq('recipe ' + r.id + ' ' + T.cols[i], Math.round(r.v[i] * 100), w, 0.5));
// transfer: cutoff fitted on 24-409, misses on 25-3152
for (const [k, want] of [['d27', 31], ['jev', 28], ['lp27', 14]]) {
  const cut = C.thr98(C.rowsFor(k, C.isA)).thr, c = C.confusion(C.rowsFor(k, C.isB), cut);
  eq('transfer ' + k, c.fn, want);
  console.log('transfer', k, 'cut', cut, 'misses on 25-3152', c.fn, 'of', c.tp + c.fn);
}
// pooled cutoff: where the five misses fall
for (const k of ['lp27', 'd27', 'jev']) {
  const cut = C.thr98(C.rowsFor(k)).thr, a = C.confusion(C.rowsFor(k, C.isA), cut), b = C.confusion(C.rowsFor(k, C.isB), cut);
  console.log('pooled', k, 'misses 24-409', a.fn, '25-3152', b.fn);
}
console.log(bad ? bad + ' MISMATCHES' : 'ALL MATCH');
process.exit(bad ? 1 : 0);
