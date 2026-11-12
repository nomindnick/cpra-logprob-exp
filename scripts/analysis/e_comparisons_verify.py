"""Branch E verification (skeptic pass). Independent recomputation of the most consequential numbers
in docs/analysis/E-comparisons.md.

  uv run python scripts/analysis/e_comparisons_verify.py [--boot 2000]

Does NOT import any scripts/analysis/e_comparisons_*.py module. It has its own loader (labels, kinds
and recipes from data/golden/pairs.jsonl joined on pair_id; rows without a score dropped) and its own
from-scratch AUROC (two implementations: an O(n*m) pair count and a sorted/bisect count, ties = 1/2),
thr98 (the k-th highest responsive score, k = the smallest count with k/n >= 0.98), elim@98, DeLong,
exact McNemar, Fisher, Holm, Brier, ECE, logistic calibration fit and Pareto frontier. The repo helpers
in scripts/analyze.py are imported only to cross-check the from-scratch metrics.

  V0  data integrity: rows dropped, stale labels inside scores.jsonl, duplicate pair_ids, roster pair set
  V1  per-model AUROC / thr98 / elim@98 / median wall, main and roster, from scratch vs repo helpers
  V2  wrong-date recipe: pass-through at own thr98, at 0.5 and at matched recall; exact McNemar; Holm
  V3  paired bootstrap of all 21 pairwise differences (own resampler, own seed); Holm survivor counts
  V4  DeLong from scratch for the key AUROC differences
  V5  calibration: Brier, ECE, logistic slope/intercept
  V6  speed/accuracy frontier from scratch (main and 25-3152)
  V7  latency: d3 vs stock without prefix reuse, incl. the warm batch-8192 stock JSON runs
  V8  cached vs fresh stock scores
  V9  wrong-date gap with thr98 re-estimated in each resample
  V10 stock vs d3 on request subsets
Stdlib only. Bootstrap seed 20261106.
"""
import argparse
import bisect
import itertools
import json
import math
import pathlib
import random
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

SCORE = [("4b lp", "golden_qwen3.5_4b_logprob_p2db"), ("9b lp", "golden_qwen3.5_9b_logprob_p2db"),
         ("27b lp", "golden_qwen3.8_27b_logprob_p2"), ("d3-4b", "golden_d3-ctx8k_4b_noul_p2"),
         ("d3-9b", "golden_d3-ctx8k_9b_noul_p2"), ("d3-27b", "golden_d3-ctx8k_27b_noul_p2"),
         ("Jev", "golden_jev-1.14.0_noul_p2")]
JSONM = [("4b json", "golden_qwen3.5_4b_json_p2"), ("9b json", "golden_qwen3.5_9b_json_p2"),
         ("27b json", "golden_qwen3.8_27b_json_p2"), ("4b jsonR", "golden_qwen3.5_4b_json_reason_p2"),
         ("9b jsonR", "golden_qwen3.5_9b_json_reason_p2"), ("27b jsonR", "golden_qwen3.8_27b_json_reason_p2")]
FRESH = [("4b lp fresh", "golden_qwen3.5_4b_logprob_p2dbf"), ("9b lp fresh", "golden_qwen3.5_9b_logprob_p2dbf")]
WD = "same_subject_wrong_date"


# ---------------- loading ----------------

from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def load_pairs():
    return {p["pair_id"]: p for p in map(json.loads, open(ROOT / "data/golden/pairs.jsonl"))}


def load_run(tag, pairs):
    out, st = {}, {"rows": 0, "not_in_pairs": 0, "unscored": 0, "stale_label": 0, "dup": 0}
    for line in open(ROOT / "runs" / tag / "scores.jsonl"):
        r = json.loads(line)
        st["rows"] += 1
        pid = r["pair_id"]
        if pid not in pairs:
            st["not_in_pairs"] += 1
            continue
        if "label" in r and r["label"] != pairs[pid]["label"]:
            st["stale_label"] += 1
        if r.get("score") is None or "error" in r:
            st["unscored"] += 1
            continue
        if pid in out:
            st["dup"] += 1
        p = pairs[pid]
        out[pid] = {"s": float(r["score"]), "wall": r.get("wall_ms"), "prefill": r.get("prefill_ms"),
                    "tok": r.get("prompt_tokens"), "decode": r.get("decode_ms"), "total": r.get("total_ms"),
                    "verdict": r.get("verdict"), "y": p["label"], "kind": p["kind"], "recipe": p.get("recipe"),
                    "rid": p["request_id"]}
    return out, st


# ---------------- metrics from scratch ----------------

def auc_pairs(pos, neg):
    """O(n*m) definition: share of (responsive, non-responsive) pairs ranked correctly; ties count 1/2."""
    w = 0.0
    for x in pos:
        for y in neg:
            w += 1.0 if x > y else (0.5 if x == y else 0.0)
    return w / (len(pos) * len(neg))


def auc_fast(pos, neg):
    """Same quantity via one sort of the negatives and binary search."""
    ns = sorted(neg)
    w = 0.0
    for x in pos:
        lo = bisect.bisect_left(ns, x)
        hi = bisect.bisect_right(ns, x)
        w += lo + 0.5 * (hi - lo)
    return w / (len(pos) * len(neg))


def cutoff_at(pos, recall):
    """Highest cutoff t with share(pos >= t) >= recall: the k-th highest responsive score."""
    n = len(pos)
    k = next(k for k in range(1, n + 1) if k / n >= recall)
    return sorted(pos, reverse=True)[k - 1]


def elim_at(pos, neg, recall=0.98):
    t = cutoff_at(pos, recall)
    return sum(y < t for y in neg) / len(neg), t


def split(d, ids):
    return [d[p]["s"] for p in ids if d[p]["y"]], [d[p]["s"] for p in ids if not d[p]["y"]]


def holm(ps):
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj, run = [0.0] * m, 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * ps[i]))
        adj[i] = run
    return adj


def binom2(k, n):
    if n == 0:
        return 1.0
    m = min(k, n - k)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(m + 1)) / 2 ** n)


def mcnemar(fa, fb):
    b = sum(x and not y for x, y in zip(fa, fb))
    c = sum(y and not x for x, y in zip(fa, fb))
    return b, c, binom2(b, b + c)


def fisher(a, b, c, d):
    r1, r2, c1, n = a + b, c + d, a + c, a + b + c + d
    pr = lambda x: math.comb(r1, x) * math.comb(r2, c1 - x) / math.comb(n, c1)
    p0 = pr(a)
    return min(1.0, sum(pr(x) for x in range(max(0, c1 - r2), min(r1, c1) + 1) if pr(x) <= p0 * (1 + 1e-9)))


def delong_diff(sa, sb, y):
    """DeLong (1988) for AUROC(a) - AUROC(b) on the same cases. Returns (delta, se, p)."""
    P = [i for i in range(len(y)) if y[i]]
    N = [i for i in range(len(y)) if not y[i]]
    def comps(s):
        ns = sorted(s[j] for j in N); ps = sorted(s[i] for i in P)
        v10 = [(bisect.bisect_left(ns, s[i]) + 0.5 * (bisect.bisect_right(ns, s[i]) - bisect.bisect_left(ns, s[i]))) / len(N) for i in P]
        v01 = [(len(P) - bisect.bisect_right(ps, s[j]) + 0.5 * (bisect.bisect_right(ps, s[j]) - bisect.bisect_left(ps, s[j]))) / len(P) for j in N]
        return v10, v01
    a10, a01 = comps(sa); b10, b01 = comps(sb)
    d10 = [u - v for u, v in zip(a10, b10)]; d01 = [u - v for u, v in zip(a01, b01)]
    var = statistics.variance(d10) / len(P) + statistics.variance(d01) / len(N)
    delta = statistics.fmean(a10) - statistics.fmean(b10)
    se = math.sqrt(var)
    return delta, se, math.erfc(abs(delta) / se / math.sqrt(2))


def ece10(s, y):
    cnt = [0] * 10; ss = [0.0] * 10; yy = [0] * 10
    for a, b in zip(s, y):
        k = min(9, int(math.floor(a * 10)))
        cnt[k] += 1; ss[k] += a; yy[k] += b
    n = len(s)
    return sum(abs(ss[k] - yy[k]) / n for k in range(10) if cnt[k])  # = sum (cnt/n)*|mean s - mean y|


def logit_fit(s, y):
    """Logistic regression y ~ a + b*logit(s), plain Newton (IRLS) on the 2x2 system."""
    x = [math.log(v / (1 - v)) for v in s]
    a = b = 0.0
    for _ in range(100):
        g0 = g1 = h00 = h01 = h11 = 0.0
        for xi, yi in zip(x, y):
            p = 1 / (1 + math.exp(-(a + b * xi)))
            w = p * (1 - p)
            g0 += yi - p; g1 += (yi - p) * xi
            h00 += w; h01 += w * xi; h11 += w * xi * xi
        det = h00 * h11 - h01 * h01
        da, db = (h11 * g0 - h01 * g1) / det, (h00 * g1 - h01 * g0) / det
        a += da; b += db
        if max(abs(da), abs(db)) < 1e-12:
            break
    return a, b


def pareto(items, lat, acc):
    keep = []
    for x in items:
        if not any(y[lat] <= x[lat] and y[acc] >= x[acc] and (y[lat] < x[lat] or y[acc] > x[acc]) for y in items if y is not x):
            keep.append(x["name"])
    return keep


def qtl(xs, f):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, max(0, int(math.floor(f * len(xs)))))]


def tab(h, rows):
    print("| " + " | ".join(h) + " |")
    print("|" + "|".join("---" for _ in h) + "|")
    for r in rows:
        print("| " + " | ".join(str(c) for c in r) + " |")
    print()


def fp(p):
    return "1" if p >= 0.995 else f"{p:.2f}" if p >= 0.1 else f"{p:.3f}" if p >= 0.001 else f"{p:.1e}"


# ---------------- sections ----------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=2000)
    B = ap.parse_args().boot
    pairs = load_pairs()
    names = [n for n, _ in SCORE]
    M, R, ST = {}, {}, []
    for n, t in SCORE + JSONM + FRESH:
        M[n], s1 = load_run(t, pairs)
        R[n], s2 = load_run(t + "_roster", pairs)
        ST.append((n, t, s1, s2))

    print("#### V0. Data integrity\n")
    tab(["label", "run", "main rows / not in pairs.jsonl / unscored / stale label in scores.jsonl / dup",
         "roster rows / not in pairs / unscored / stale / dup"],
        [[n, t] + [" / ".join(str(s[k]) for k in ("rows", "not_in_pairs", "unscored", "stale_label", "dup")) for s in (s1, s2)]
         for n, t, s1, s2 in ST])
    rset = [set(R[n]) for n in names]
    print(f"- roster pair sets identical across the 7 score models: {all(x == rset[0] for x in rset)}; "
          f"request ids in roster set: {sorted(set(R['4b lp'][p]['rid'] for p in R['4b lp']))}; "
          f"roster ids == main 25-3152 ids: {rset[0] == set(p for p in M['4b lp'] if M['4b lp'][p]['rid'] == '25-3152')}")
    mids = sorted(M["4b lp"])
    print(f"- main set: {len(mids)} pairs, {sum(M['4b lp'][p]['y'] for p in mids)} responsive; "
          f"pair sets identical across the 7 score models: {all(set(M[n]) == set(mids) for n in names)}\n")

    print(f"#### V1. Per-model metrics from scratch (main {N_ALL} / roster {NR['25-3152']})\n")
    sys.path.insert(0, str(ROOT / "scripts"))
    from analyze import at_recall, auroc as repo_auroc, pr_curve  # cross-check only
    body = []
    maxdiff = 0.0; thrmatch = True
    for n in names:
        row = [n]
        for D in (M, R):
            ids = sorted(D[n])
            pos, neg = split(D[n], ids)
            a1, a2 = auc_pairs(pos, neg), auc_fast(pos, neg)
            e, t = elim_at(pos, neg)
            ra = repo_auroc([D[n][p]["s"] for p in ids], [D[n][p]["y"] for p in ids])
            rr = at_recall(pr_curve([D[n][p]["s"] for p in ids], [D[n][p]["y"] for p in ids]), 0.98)
            maxdiff = max(maxdiff, abs(a1 - a2), abs(a1 - ra), abs(e - rr[3]))
            thrmatch &= (t == rr[0])
            k = sum(y < t for y in neg)
            row += [f"{a1:.3f}", f"{t:.4f}", f"{k}/{len(neg)} = {e:.1%}", f"{statistics.median(D[n][p]['wall'] for p in ids):,.0f}"]
        body.append(row)
    tab(["model", "main AUROC", "main thr98", "main elim@98", "main median wall ms", "roster AUROC", "roster thr98",
         "roster elim@98", "roster median wall ms"], body)
    print(f"- largest disagreement between my two AUROC implementations, the repo auroc() and the repo elim@98: "
          f"{maxdiff:.2e}; thr98 identical to repo at_recall(): {thrmatch}\n")

    print("#### V2. Same subject, wrong date (20 hard negatives; main set)\n")
    wd = [p for p in mids if M["4b lp"][p]["kind"] == "hard_negative" and M["4b lp"][p]["recipe"] == WD]
    hn = [p for p in mids if M["4b lp"][p]["kind"] == "hard_negative"]
    other = [p for p in hn if p not in set(wd)]
    thr = {n: cutoff_at(split(M[n], mids)[0], 0.98) for n in names}
    passes = lambda n, ps, t: [M[n][p]["s"] >= t for p in ps]
    body = []
    for n in names:
        npos = sum(M[n][p]["y"] for p in mids)
        r5 = sum(M[n][p]["s"] >= 0.5 for p in mids if M[n][p]["y"])
        k1, k2 = sum(passes(n, wd, thr[n])), sum(passes(n, other, thr[n]))
        body.append([n, len(wd), f"{thr[n]:.4f}", f"{k1}/20", f"{sum(passes(n, wd, 0.5))}/20", f"{r5}/{npos}",
                     f"{k2}/{len(other)}", fp(fisher(k1, 20 - k1, k2, len(other) - k2))])
    tab(["model", "n", "thr98", "wrong-date pass @thr98", "pass @0.5", "recall @0.5", "other-4 pass @thr98",
         "Fisher p (wd vs other 4)"], body)
    res = []
    for x, y in itertools.combinations(names, 2):
        b, c, p = mcnemar(passes(x, wd, thr[x]), passes(y, wd, thr[y]))
        res.append((x, y, b, c, p))
    adj = holm([r[4] for r in res])
    key = {("27b lp", "d3-27b"), ("d3-27b", "Jev"), ("27b lp", "Jev")}
    print("Exact McNemar at each model's own thr98, Holm over all 21 pairs and over the 3 key pairs only:\n")
    k3 = [i for i, r in enumerate(res) if (r[0], r[1]) in key]
    adj3 = dict(zip(k3, holm([res[i][4] for i in k3])))
    tab(["x", "y", "x only", "y only", "exact p", "Holm (21)", "Holm (3 key pairs)"],
        [[r[0], r[1], r[2], r[3], fp(r[4]), fp(adj[i]), fp(adj3[i])] for i, r in enumerate(res) if i in adj3])
    print("d3-27b vs 27b lp on wrong-date emails at matched recall (both models' cutoffs set to the same recall on "
          f"all {N_ALL} pairs):\n")
    body = []
    npos = N_POS
    rec27 = sum(M["27b lp"][q]["s"] >= .5 for q in mids if M["27b lp"][q]["y"]) / npos  # 27b lp's recall at 0.5
    for rec in (rec27, 0.95, 0.98, 0.99, 1.0):
        ta, tb = cutoff_at(split(M["27b lp"], mids)[0], rec), cutoff_at(split(M["d3-27b"], mids)[0], rec)
        fa, fb = passes("27b lp", wd, ta), passes("d3-27b", wd, tb)
        b, c, p = mcnemar(fa, fb)
        ea = sum(M["27b lp"][q]["s"] < ta for q in mids if not M["27b lp"][q]["y"])
        eb = sum(M["d3-27b"][q]["s"] < tb for q in mids if not M["d3-27b"][q]["y"])
        body.append([f"{rec:.1%}", f"{ta:.3f} / {tb:.3f}", f"{sum(fa)} / {sum(fb)}", f"{b} / {c}", fp(p),
                     f"{ea}/{N_NEG} / {eb}/{N_NEG}"])
    tab(["recall target", "cutoff 27b lp / d3-27b", "wrong-date pass 27b lp / d3-27b", "27b-only / d3-only", "exact p",
         "negatives eliminated 27b lp / d3-27b"], body)
    print("Cutoff each model needs to pass at most 3 of the 20 wrong-date emails, and its recall there:\n")
    body = []
    for n in names:
        w = sorted((M[n][p]["s"] for p in wd), reverse=True)
        t = min(s for s in {M[n][p]["s"] for p in mids} | {1.0} if s > w[3])
        rec = sum(M[n][p]["s"] >= t for p in mids if M[n][p]["y"])
        body.append([n, f"{t:.3f}", sum(passes(n, wd, t)), f"{rec}/{N_POS} = {rec / N_POS:.1%}"])
    tab(["model", "cutoff", "wrong-date pass", "recall"], body)

    print(f"#### V3. Paired bootstrap of all 21 differences ({B} resamples, own resampler, seed 20261106)\n")
    for setname, D in (("main", M), ("roster", R)):
        ids = sorted(D[names[0]])
        P = [p for p in ids if D[names[0]][p]["y"]]; N = [p for p in ids if not D[names[0]][p]["y"]]
        rng = random.Random(20261106 if setname == "main" else 20261107)
        ba = {n: [] for n in names}; be = {n: [] for n in names}
        for _ in range(B):
            bp = [P[rng.randrange(len(P))] for _ in P]; bn = [N[rng.randrange(len(N))] for _ in N]
            for n in names:
                ps = [D[n][p]["s"] for p in bp]; ns = [D[n][p]["s"] for p in bn]
                ba[n].append(auc_fast(ps, ns)); be[n].append(elim_at(ps, ns)[0])
        pos0 = {n: split(D[n], ids) for n in names}
        pt_a = {n: auc_fast(*pos0[n]) for n in names}; pt_e = {n: elim_at(*pos0[n])[0] for n in names}
        for metric, pt, bd, scale, fmt in (("AUROC", pt_a, ba, 1, "+.3f"), ("elim@98", pt_e, be, 100, "+.1f")):
            rows = []
            for x, y in itertools.combinations(names, 2):
                a, b = (x, y) if pt[x] >= pt[y] else (y, x)
                d = [u - v for u, v in zip(bd[a], bd[b])]
                lo, hi = qtl(d, 0.025), qtl(d, 0.975)
                p = min(1.0, 2 * (min(sum(v <= 0 for v in d), sum(v >= 0 for v in d)) + 1) / (B + 1))
                sd = statistics.stdev(d)
                pn = math.erfc(abs(pt[a] - pt[b]) / sd / math.sqrt(2)) if sd > 0 else 1.0
                rows.append([a, b, (pt[a] - pt[b]) * scale, lo * scale, hi * scale, p, pn])
            h = holm([r[5] for r in rows]); hn_ = holm([r[6] for r in rows])
            surv = [f"{r[0]} − {r[1]}" for r, q in zip(rows, h) if q < 0.05]
            survn = [f"{r[0]} − {r[1]}" for r, q in zip(rows, hn_) if q < 0.05]
            print(f"**{setname}, {metric}:** CI excludes 0 in {sum(r[3] > 0 or r[4] < 0 for r in rows)}/21; "
                  f"survive Holm (percentile p) {len(surv)}/21; survive Holm (normal p) {len(survn)}/21.\n")
            print(f"- survivors (percentile): {', '.join(surv)}")
            print(f"- survivors (normal): {', '.join(survn)}\n")
            focus = {("d3-27b", "27b lp"), ("9b lp", "4b lp"), ("27b lp", "4b lp"), ("d3-27b", "4b lp"), ("d3-27b", "Jev"),
                     ("27b lp", "Jev"), ("4b lp", "d3-4b"), ("d3-27b", "9b lp"), ("d3-9b", "4b lp")}
            tab(["A − B", f"Δ{metric}", "95% CI", "boot p", "Holm", "normal p", "normal Holm"],
                [[f"{r[0]} − {r[1]}", f"{r[2]:{fmt}}", f"[{r[3]:{fmt}}, {r[4]:{fmt}}]", fp(r[5]), fp(q), fp(r[6]), fp(qn)]
                 for r, q, qn in zip(rows, h, hn_) if (r[0], r[1]) in focus])

    print("#### V4. DeLong from scratch, key AUROC differences\n")
    body = []
    for setname, D in (("main", M), ("roster", R)):
        ids = sorted(D[names[0]])
        y = [D[names[0]][p]["y"] for p in ids]
        for x, z in (("d3-27b", "27b lp"), ("d3-27b", "Jev"), ("27b lp", "Jev"), ("9b lp", "4b lp"), ("d3-27b", "4b lp")):
            d, se, p = delong_diff([D[x][q]["s"] for q in ids], [D[z][q]["s"] for q in ids], y)
            body.append([setname, f"{x} − {z}", f"{d:+.4f}", f"{se:.4f}", fp(p)])
    sub = [p for p in mids if M["4b lp"][p]["y"]] + wd
    y = [M["4b lp"][p]["y"] for p in sub]
    for x, z in (("d3-27b", "Jev"), ("d3-27b", "27b lp"), ("27b lp", "Jev")):
        d, se, p = delong_diff([M[x][q]["s"] for q in sub], [M[z][q]["s"] for q in sub], y)
        body.append(["positives vs wrong-date", f"{x} − {z}", f"{d:+.4f}", f"{se:.4f}", fp(p)])
    tab(["set", "A − B", "ΔAUROC", "DeLong SE", "DeLong p"], body)

    print(f"#### V5. Calibration from scratch (main {N_ALL})\n")
    body = []
    for n in names:
        s = [M[n][p]["s"] for p in mids]; yy = [M[n][p]["y"] for p in mids]
        a, b = logit_fit(s, yy)
        r5 = sum(v >= .5 for v, l in zip(s, yy) if l)
        body.append([n, f"{statistics.fmean((v - l) ** 2 for v, l in zip(s, yy)):.3f}", f"{ece10(s, yy):.3f}",
                     f"{a:+.2f}", f"{b:.2f}", f"{r5}/{N_POS}", f"{sum(v < .5 for v, l in zip(s, yy) if not l)}/{N_NEG}",
                     f"{statistics.fmean(v for v, l in zip(s, yy) if not l):.3f}"])
    tab(["model", "Brier", "ECE (10 bins)", "intercept", "slope", "recall @0.5", "eliminated @0.5",
         "mean score, non-responsive"], body)
    prev = N_POS / N_ALL
    o = 1 * (0.1 / 0.9) / (prev / (1 - prev))
    print(f"- label shift: 0.5 at {prev:.1%} → {o / (1 + o):.3f} at 10%\n")

    print("#### V6. Speed/accuracy frontier from scratch\n")
    items = []
    for n in names + [m for m, _ in JSONM]:
        ids = sorted(M[n])
        pos, neg = split(M[n], ids)
        items.append({"name": n, "med": statistics.median(M[n][p]["wall"] for p in ids),
                      "mean": statistics.fmean(M[n][p]["wall"] for p in ids),
                      "auc": auc_fast(pos, neg), "elim": elim_at(pos, neg)[0], "n": len(ids),
                      "dec": statistics.median(M[n][p]["decode"] for p in ids) if M[n][ids[0]]["decode"] is not None else None})
    loc = [x for x in items if x["name"] != "Jev"]
    for lat, acc in (("med", "elim"), ("med", "auc"), ("mean", "elim")):
        print(f"- main, local, {lat} wall × {acc}: {' → '.join(pareto(sorted(loc, key=lambda x: x[lat]), lat, acc))}")
    jev = next(x for x in items if x["name"] == "Jev")
    print(f"- Jev median {jev['med']:.1f} ms; 4b lp / Jev = {next(x for x in items if x['name'] == '4b lp')['med'] / jev['med']:.2f}; "
          f"27b lp / Jev = {next(x for x in items if x['name'] == '27b lp')['med'] / jev['med']:.2f}; "
          f"d3-27b / Jev = {next(x for x in items if x['name'] == 'd3-27b')['med'] / jev['med']:.2f}")
    print("- JSON median decode ms vs same-size lp median wall: " + "; ".join(
        f"{x['name']} {x['dec']:,.0f}" for x in items if x["dec"] and "json" in x["name"]))
    sub = sorted(R["4b lp"])
    ritems = []
    for n in names + [m for m, _ in JSONM]:
        for ro, D in ((False, M), (True, R)):
            ids = [p for p in sub if p in D[n]]
            pos, neg = split(D[n], ids)
            ritems.append({"name": n + (" +roster" if ro else ""), "med": statistics.median(D[n][p]["wall"] for p in ids),
                           "auc": auc_fast(pos, neg), "elim": elim_at(pos, neg)[0], "n": len(ids)})
    rloc = [x for x in ritems if not x["name"].startswith("Jev")]
    for acc in ("elim", "auc"):
        print(f"- 25-3152, local, median wall × {acc}: {' → '.join(pareto(sorted(rloc, key=lambda x: x['med']), 'med', acc))}")
    a1 = next(x for x in ritems if x["name"] == "27b json +roster"); a2 = next(x for x in ritems if x["name"] == "27b lp +roster")
    print(f"- 27b json +roster AUROC {a1['auc']:.5f} (n {a1['n']}) vs 27b lp +roster {a2['auc']:.5f} (n {a2['n']})")
    # bootstrap: how often is any JSON mode on the local frontier (median wall x elim@98 / x AUROC)?
    for setname, ids0, cfgs in (("main", mids, [(n, M[n]) for n in names + [m for m, _ in JSONM] if n != "Jev"]),
                                ("25-3152", sub, [(n + (" +roster" if ro else ""), (R if ro else M)[n]) for n in names + [m for m, _ in JSONM]
                                                  if n != "Jev" for ro in (False, True)])):
        P = [p for p in ids0 if M["4b lp"][p]["y"]]; N = [p for p in ids0 if not M["4b lp"][p]["y"]]
        rng = random.Random(20261110)
        hit = {"elim": {}, "auc": {}}
        for _ in range(B):
            bp = [P[rng.randrange(len(P))] for _ in P]; bn = [N[rng.randrange(len(N))] for _ in N]
            its = []
            for n, D in cfgs:
                ps = [D[p]["s"] for p in bp if p in D]; ns = [D[p]["s"] for p in bn if p in D]
                its.append({"name": n, "med": statistics.median(D[p]["wall"] for p in bp + bn if p in D),
                            "elim": elim_at(ps, ns)[0], "auc": auc_fast(ps, ns)})
            for acc in ("elim", "auc"):
                for n in pareto(its, "med", acc):
                    if "json" in n:
                        hit[acc][n] = hit[acc].get(n, 0) + 1
        print(f"- {setname}: JSON configurations on the local frontier in {B} redraws: median wall × elim@98 "
              f"{hit['elim'] or 'none'}; × AUROC {hit['auc'] or 'none'}")
    print()

    print("#### V7. Latency: d3 vs stock without prefix reuse\n")
    body = []
    for size, st, d3, fr, js in (("4b", "4b lp", "d3-4b", "4b lp fresh", "4b json"), ("9b", "9b lp", "d3-9b", "9b lp fresh", "9b json")):
        for ro, D in ((False, M), (True, R)):
            ids = sorted(D[st])
            ratio_f = statistics.median(D[d3][p]["wall"] / D[fr][p]["prefill"] for p in ids)
            ratio_c = statistics.median(D[d3][p]["wall"] / D[st][p]["wall"] for p in ids)
            per = lambda X, f: statistics.median(X[p][f] / X[p]["tok"] * 1000 for p in X if X[p][f])
            body.append([size + (" +roster" if ro else ""), f"{ratio_f:.2f}", f"{ratio_c:.2f}", f"{per(D[d3], 'wall'):.0f}",
                         f"{per(D[fr], 'prefill'):.0f}", f"{per(D[js], 'prefill'):.0f}", f"{per(D[st], 'prefill'):.0f}"])
    tab(["size", "d3 wall ÷ fresh prefill (per-pair median)", "d3 wall ÷ cached wall (per-pair median)",
         "d3 wall ms/1k tok", "stock fresh prefill ms/1k tok", "stock JSON (warm, batch 8192, no cache) prefill ms/1k tok",
         "stock cached prefill ms/1k tok"], body)

    print("Prefill cost per 1k prompt tokens by prompt length (each run bucketed on its own prompt_tokens), main + "
          "roster rows pooled, medians. Stock JSON = same Q4_K_M weights and ggml runner as stock lp, batch 8192 like d3, "
          "warm, no prefix cache:\n")
    body = []
    edges = [0, 1500, 2500, 3500, 10 ** 9]
    for size, d3, fr, js in (("4b", "d3-4b", "4b lp fresh", "4b json"), ("9b", "d3-9b", "9b lp fresh", "9b json")):
        for lo, hi in zip(edges, edges[1:]):
            row = [size, f"{lo:,}–{hi:,}" if hi < 10 ** 9 else f"≥{lo:,}"]
            for n, f in ((d3, "wall"), (fr, "prefill"), (js, "prefill")):
                xs = [D[n][p][f] / D[n][p]["tok"] * 1000 for D in (M, R) for p in D[n] if lo <= D[n][p]["tok"] < hi and D[n][p][f]]
                row.append(f"{statistics.median(xs):.0f} (n {len(xs)})" if xs else "—")
            body.append(row)
    tab(["size", "prompt tokens", "d3 wall ms/1k tok", "stock fresh prefill ms/1k tok (default batch)",
         "stock JSON prefill ms/1k tok (batch 8192)"], body)

    print("#### V8. Stock cached vs fresh (same model, same prompt)\n")
    body = []
    for st, fr in (("4b lp", "4b lp fresh"), ("9b lp", "9b lp fresh")):
        for ro, D in ((False, M), (True, R)):
            ids = sorted(set(D[st]) & set(D[fr]))
            d = [abs(D[st][p]["s"] - D[fr][p]["s"]) for p in ids]
            e1 = elim_at(*split(D[st], ids))[0]; e2 = elim_at(*split(D[fr], ids))[0]
            body.append([st + (" +roster" if ro else ""), len(ids), f"{max(d):.4f}", f"{statistics.fmean(d):.4f}",
                         f"{e1:.1%} / {e2:.1%}"])
    tab(["model", "pairs", "max |Δscore|", "mean |Δscore|", "elim@98 cached / fresh"], body)


    print(f"#### V9. Wrong-date gap with thr98 re-estimated in each resample ({B} resamples, seed 20261108)\n")
    P = [p for p in mids if M["4b lp"][p]["y"]]; N = [p for p in mids if not M["4b lp"][p]["y"]]
    wds = set(wd)
    rng = random.Random(20261108)
    share = {n: [] for n in ("d3-27b", "27b lp", "Jev")}
    for _ in range(B):
        bp = [P[rng.randrange(len(P))] for _ in P]; bn = [N[rng.randrange(len(N))] for _ in N]
        w = [p for p in bn if p in wds]
        for n in share:
            t = cutoff_at([M[n][p]["s"] for p in bp], 0.98)
            share[n].append(sum(M[n][p]["s"] >= t for p in w) / len(w))
    body = []
    for a, b in (("Jev", "d3-27b"), ("27b lp", "d3-27b"), ("Jev", "27b lp")):
        d = [u - v for u, v in zip(share[a], share[b])]
        p = min(1.0, 2 * (min(sum(v <= 0 for v in d), sum(v >= 0 for v in d)) + 1) / (B + 1))
        body.append([f"{a} − {b}", f"[{qtl(d, .025) * 100:+.0f}, {qtl(d, .975) * 100:+.0f}]", fp(p)])
    tab(["gap", "95% CI (points)", "bootstrap p"], body)

    print(f"#### V10. Stock vs d3 on request subsets (point estimates from scratch; {B} paired resamples, seed 20261109)\n")
    rng = random.Random(20261109)
    body = []
    for st, d3, rid, D in (("27b lp", "d3-27b", "25-3152", M), ("4b lp", "d3-4b", "24-409", M), ("9b lp", "d3-9b", None, R),
                           ("27b lp", "d3-27b", None, R)):
        ids = sorted(p for p in D[st] if rid is None or D[st][p]["rid"] == rid)
        P = [p for p in ids if D[st][p]["y"]]; N = [p for p in ids if not D[st][p]["y"]]
        pa, pb = split(D[st], ids), split(D[d3], ids)
        da, de = [], []
        for _ in range(B):
            bp = [P[rng.randrange(len(P))] for _ in P]; bn = [N[rng.randrange(len(N))] for _ in N]
            xa = ([D[st][p]["s"] for p in bp], [D[st][p]["s"] for p in bn])
            xb = ([D[d3][p]["s"] for p in bp], [D[d3][p]["s"] for p in bn])
            da.append(auc_fast(*xb) - auc_fast(*xa)); de.append(elim_at(*xb)[0] - elim_at(*xa)[0])
        body.append([f"{d3} − {st}", rid or "25-3152 +roster", len(ids),
                     f"{auc_fast(*pb) - auc_fast(*pa):+.3f} [{qtl(da, .025):+.3f}, {qtl(da, .975):+.3f}]",
                     f"{(elim_at(*pb)[0] - elim_at(*pa)[0]) * 100:+.1f} [{qtl(de, .025) * 100:+.1f}, {qtl(de, .975) * 100:+.1f}]"])
    tab(["d3 − stock", "pairs", "n", "ΔAUROC [95% CI]", "Δelim@98 points [95% CI]"], body)


if __name__ == "__main__":
    main()
