"""D3: topical (24-409) vs correspondent-scoped (25-3152), with and without the roster.

  uv run python scripts/analysis/d_validity_requests.py [--boot 1000]

For the seven score runs and the six JSON runs: AUROC and elim@98 per request (98% cutoff chosen within the
request), with 95% bootstrap CIs (stratified by label, random.Random(seed), the same resamples for every run);
the 24-409 minus 25-3152 difference with a CI from independent resamples of each request; the same per request on
the real-only and real+ vs hard− subsets; the 25-3152 roster ablation (the "_roster" twin of each run, 249 pairs)
with paired CIs for the change; the per-request ranking of the score models; and the pooled vs per-request 98%
cutoffs (branch A treats cutoff transfer).

Prints D3-0 (composition), D3-1 (per request), D3-2 (difference), D3-3 (per request x subset), D3-4 (roster),
D3-5 (ranks), D3-6 (cutoffs). Stdlib only, deterministic.
"""
import argparse
import collections
import random
import sys

sys.path.insert(0, "scripts/analysis")
from d_validity_common import (ALL_RUNS, SCORE_RUNS, SUBSETS, auroc, at_recall, ci, fa, fe, in_subset,  # noqa: E402
                               kendall_tau, load, pairs, paired_boot, point, pr_curve, ranks_desc, table)

REQS = ("24-409", "25-3152")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=3152)
    a = ap.parse_args()
    P = pairs()
    runs, roster = {}, {}
    for name, tag in ALL_RUNS:
        runs[name] = {r["pair_id"]: r for r in load(tag, P)[0]}
        roster[name] = {r["pair_id"]: r for r in load(tag + "_roster", P)[0]}
    print("# D3. Per request\n")
    print("Roster twins: " + ", ".join(f"{n} → {t}_roster ({len(roster[n])} scored rows)" for n, t in ALL_RUNS) + "\n")

    print("## D3-0. Composition per request\n")
    c = collections.Counter((x["request_id"], x["kind"]) for x in P.values())
    kinds = sorted({k for _, k in c}, key=lambda k: (k.startswith("hard") or k == "real_negative", k))
    table(["kind"] + list(REQS), [[k] + [c[(r, k)] for r in REQS] for k in kinds] +
          [["positives / negatives"] + [f"{sum(x['label'] for x in P.values() if x['request_id'] == r)} / "
                                        f"{sum(1 - x['label'] for x in P.values() if x['request_id'] == r)}" for r in REQS]])
    rc = collections.Counter((x["request_id"], x["recipe"]) for x in P.values() if x["kind"] == "hard_negative")
    table(["hard-negative recipe"] + list(REQS),
          [[k] + [rc[(r, k)] for r in REQS] for k in sorted({k for _, k in rc})])

    # per request, all pairs of that request
    res, boots = {}, {}
    for i, rid in enumerate(REQS):
        ids = sorted(p for p, x in P.items() if x["request_id"] == rid)
        sub = {m: {p: R[p] for p in ids if p in R} for m, R in runs.items()}
        boots[rid] = paired_boot(sub, ids, a.boot, a.seed + i)
        for m in runs:
            res[(rid, m)] = point(list(sub[m].values()))

    print(f"## D3-1. Per request: AUROC and elim@98 (98% cutoff chosen within the request) [95% CI, {a.boot} resamples]\n")
    out = []
    for m, _ in ALL_RUNS:
        row = [m]
        for rid in REQS:
            b = boots[rid][m]; p = res[(rid, m)]
            row += [fa(p["auroc"], *ci(b["auroc"])), fe(p, *ci(b["elim"])), f"{p['thr']:.4g} ({p['missed']}/{p['n_pos']} missed)"]
        out.append(row)
    table(["run", "24-409 AUROC", "24-409 elim@98", "24-409 thr98", "25-3152 AUROC", "25-3152 elim@98", "25-3152 thr98"], out)

    print("## D3-2. 24-409 minus 25-3152 (CI from the two requests' independent resamples, paired by resample index)\n")
    out = []
    for m, _ in ALL_RUNS:
        da = [x - y for x, y in zip(boots["24-409"][m]["auroc"], boots["25-3152"][m]["auroc"])]
        de = [x - y for x, y in zip(boots["24-409"][m]["elim"], boots["25-3152"][m]["elim"])]
        pa = res[("24-409", m)]["auroc"] - res[("25-3152", m)]["auroc"]
        pe = res[("24-409", m)]["elim"] - res[("25-3152", m)]["elim"]
        lo, hi = ci(da); elo, ehi = ci(de)
        out.append([m, f"{pa:+.3f} [{lo:+.3f}, {hi:+.3f}]", f"{pe:+.0%} [{elo:+.0%}, {ehi:+.0%}]",
                    "yes" if lo > 0 or hi < 0 else "no"])
    table(["run", "ΔAUROC (24-409 − 25-3152)", "Δelim@98", "AUROC CI excludes 0"], out)

    print("## D3-3. Per request and subset (cutoff chosen within each request × subset; point estimates, AUROC / elim@98 k/n)\n")
    subs = [s for s in SUBSETS if s[0] in ("a", "b", "f")]
    out = []
    for m, _ in SCORE_RUNS:
        row = [m]
        for rid in REQS:
            for s in subs:
                xs = [r for r in runs[m].values() if r["request_id"] == rid and in_subset(r, s)]
                p = point(xs)
                row.append(f"{p['auroc']:.3f} / {p['elim']:.0%} ({p['k']}/{p['n_neg']})")
        out.append(row)
    table(["run"] + [f"{rid} ({s[0]}) {s[1]}" for rid in REQS for s in subs], out)
    n_sub = {(rid, s[0]): (sum(1 for x in P.values() if x["request_id"] == rid and in_subset(x, s) and x["label"]),
                           sum(1 for x in P.values() if x["request_id"] == rid and in_subset(x, s) and not x["label"]))
             for rid in REQS for s in subs}
    print("Sizes (positives / negatives): " + "; ".join(f"{rid} ({s}) {p}/{n}" for (rid, s), (p, n) in n_sub.items()) + "\n")

    print("## D3-4. 25-3152 without → with the roster (same 249 pairs; paired bootstrap of the change)\n")
    ids = sorted(p for p, x in P.items() if x["request_id"] == "25-3152")
    rng = random.Random(a.seed + 99)
    pos = [p for p in ids if P[p]["label"]]; neg = [p for p in ids if not P[p]["label"]]
    draws = [rng.choices(pos, k=len(pos)) + rng.choices(neg, k=len(neg)) for _ in range(a.boot)]
    out = []
    for m, _ in ALL_RUNS:
        B = runs[m]; R = roster[m]
        shared = [p for p in ids if p in B and p in R]
        pb = point([B[p] for p in shared]); pr = point([R[p] for p in shared])
        dA, dE = [], []
        for d in draws:
            d = [p for p in d if p in B and p in R]
            l = [P[p]["label"] for p in d]
            sb = [B[p]["score"] for p in d]; sr = [R[p]["score"] for p in d]
            dA.append(auroc(sr, l) - auroc(sb, l))
            dE.append(at_recall(pr_curve(sr, l), .98)[3] - at_recall(pr_curve(sb, l), .98)[3])
        lo, hi = ci(dA); elo, ehi = ci(dE)
        out.append([m, len(shared), f"{pb['auroc']:.3f} → {pr['auroc']:.3f}", f"{pr['auroc'] - pb['auroc']:+.3f} [{lo:+.3f}, {hi:+.3f}]",
                    f"{pb['elim']:.0%} ({pb['k']}/{pb['n_neg']}) → {pr['elim']:.0%} ({pr['k']}/{pr['n_neg']})",
                    f"{pr['elim'] - pb['elim']:+.0%} [{elo:+.0%}, {ehi:+.0%}]",
                    f"{res[('24-409', m)]['auroc']:.3f}"])
    table(["run", "pairs", "AUROC without → with", "ΔAUROC [paired 95% CI]", "elim@98 without → with", "Δelim@98 [95% CI]",
           "24-409 AUROC (for comparison)"], out)

    print("## D3-5. Rank of the seven score models per request (1 = best)\n")
    names = [m for m, _ in SCORE_RUNS]
    cols = [("24-409", runs), ("25-3152", runs), ("25-3152 +roster", roster)]
    vals = {}
    for lab, src in cols:
        rid = lab.split()[0]
        for m in names:
            vals[(lab, m)] = point([r for r in src[m].values() if r["request_id"] == rid])
    out = []
    for metric, ml in (("auroc", "AUROC"), ("elim", "elim@98")):
        rk = {lab: ranks_desc([vals[(lab, m)][metric] for m in names]) for lab, _ in cols}
        for j, m in enumerate(names):
            out.append([ml, m] + [f"{rk[lab][j]} ({vals[(lab, m)][metric]:.3f})" if metric == "auroc"
                                  else f"{rk[lab][j]} ({vals[(lab, m)][metric]:.0%})" for lab, _ in cols])
    table(["metric", "run"] + [lab for lab, _ in cols], out)
    out = []
    for metric, ml in (("auroc", "AUROC"), ("elim", "elim@98")):
        v = {lab: [vals[(lab, m)][metric] for m in names] for lab, _ in cols}
        out.append([ml, f"{kendall_tau(v['24-409'], v['25-3152']):+.2f}", f"{kendall_tau(v['24-409'], v['25-3152 +roster']):+.2f}"])
    table(["metric", "Kendall tau 24-409 vs 25-3152", "24-409 vs 25-3152 +roster"], out)
    print("Share of bootstrap resamples in which the 24-409 AUROC exceeds the 25-3152 AUROC, per model: "
          + ", ".join(f"{m} {sum(x > y for x, y in zip(boots['24-409'][m]['auroc'], boots['25-3152'][m]['auroc'])) / a.boot:.0%}"
                      for m in names) + "\n")

    print("## D3-6. The 98% cutoff: pooled (both requests) vs chosen within each request\n")
    out = []
    for m, _ in ALL_RUNS:
        rows = list(runs[m].values())
        t_all = point(rows)["thr"]
        row = [m, f"{t_all:.4g}"]
        for rid in REQS:
            xs = [r for r in rows if r["request_id"] == rid]
            pos_ = [r for r in xs if r["label"]]; neg_ = [r for r in xs if not r["label"]]
            rec = sum(r["score"] >= t_all for r in pos_) / len(pos_)
            el = sum(r["score"] < t_all for r in neg_)
            row += [f"{res[(rid, m)]['thr']:.4g}", f"{rec:.1%} ({sum(r['score'] >= t_all for r in pos_)}/{len(pos_)}) / {el}/{len(neg_)}"]
        out.append(row)
    table(["run", "pooled thr98", "24-409 own thr98", "24-409 at pooled thr: recall / cleared", "25-3152 own thr98",
           "25-3152 at pooled thr: recall / cleared"], out)


if __name__ == "__main__":
    main()
