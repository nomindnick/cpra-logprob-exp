"""D1: how much of each model's result comes from the synthetic emails? Metrics on five subsets.

  uv run python scripts/analysis/d_validity_subsets.py [--boot 1000]

Subsets (labels from data/golden/pairs.jsonl; "all+" includes the 4 hard_negative_flipped, which are positives):
  a real+ vs real−   b real+ vs hard−   c all+ vs real−   d all+ vs hard−   e everything
  f real+ vs in-window hard− (added here: the hard negatives other than same_subject_wrong_date, i.e. the ones
    a search limited to the request's date window could return)
For every run (the seven score models and the six JSON verdict runs): AUROC and elim@98 with the 98%-recall
cutoff chosen inside the subset, each with a 95% bootstrap CI (stratified by label, the same resamples for every
run, random.Random(seed)). Then the ranking of the seven score models per subset, Kendall tau against the
everything ranking, the share of bootstrap resamples in which each model is the best, and where each model's
headline elimination comes from (real vs hard negatives at its all-pairs cutoff).

Prints: D1-0 (subset sizes), D1-1 (AUROC), D1-2 (elim@98), D1-3 (98% cutoff and misses), D1-4 (ranks),
D1-5 (P(best)), D1-6 (rank agreement), D1-7 (headline elimination split), D1-8 (recipes), D1-9 (ranges).
Stdlib only, deterministic.
"""
import argparse
import collections
import sys

sys.path.insert(0, "scripts/analysis")
from d_validity_common import (ALL_RUNS, JSON_RUNS, SCORE_RUNS, SUBSETS, ci, fa, fe, in_subset,  # noqa: E402
                               kendall_tau, load, pairs, paired_boot, point, ranks_desc, table)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261106)
    a = ap.parse_args()
    P = pairs()
    runs = {}
    print("# D1. Metrics by subset\n")
    for name, tag in ALL_RUNS:
        rows, dropped = load(tag, P)
        runs[name] = {r["pair_id"]: r for r in rows}
        if dropped:
            print(f"- {name} ({tag}): {len(dropped)} unscored row(s) dropped: "
                  + ", ".join(f"{d['pair_id']} ({d['kind']})" for d in dropped))
    print()

    print("## D1-0. Subset sizes (pairs in data/golden/pairs.jsonl)\n")
    out = []
    for sub in SUBSETS:
        ids = [p for p, x in P.items() if in_subset(x, sub)]
        npos = sum(P[p]["label"] for p in ids)
        nneg = len(ids) - npos
        allowed = npos - -(-98 * npos // 100)  # misses allowed at 98% recall = npos - ceil(.98 npos)
        out.append([f"({sub[0]}) {sub[1]}", len(ids), npos, nneg, allowed])
    table(["subset", "pairs", "positives", "negatives", "misses allowed at 98% recall"], out)

    res = {}  # (subset key, run name) -> (point, (alo, ahi), (elo, ehi))
    boots = {}
    for i, sub in enumerate(SUBSETS):
        ids = sorted(p for p, x in P.items() if in_subset(x, sub))
        sub_rows = {m: {p: R[p] for p in ids if p in R} for m, R in runs.items()}
        b = paired_boot(sub_rows, ids, a.boot, a.seed + i)
        boots[sub[0]] = b
        for m in runs:
            pt = point(list(sub_rows[m].values()))
            res[(sub[0], m)] = (pt, ci(b[m]["auroc"]), ci(b[m]["elim"]))

    hdr = ["run"] + [f"({s[0]}) {s[1]}" for s in SUBSETS]
    print(f"## D1-1. AUROC [95% CI], {a.boot} paired bootstrap resamples\n")
    table(hdr, [[m] + [fa(res[(s[0], m)][0]["auroc"], *res[(s[0], m)][1]) for s in SUBSETS] for m, _ in ALL_RUNS])

    print("## D1-2. Non-responsive eliminated at 98% recall, cutoff chosen within the subset: share (k/n) [95% CI]\n")
    table(hdr, [[m] + [fe(res[(s[0], m)][0], *res[(s[0], m)][2]) for s in SUBSETS] for m, _ in ALL_RUNS])

    print("## D1-3. The within-subset 98% cutoff (thr98) and positives missed at it (missed/positives)\n")
    table(hdr, [[m] + [f"{res[(s[0], m)][0]['thr']:.4g} ({res[(s[0], m)][0]['missed']}/{res[(s[0], m)][0]['n_pos']})"
                       for s in SUBSETS] for m, _ in ALL_RUNS])

    names = [m for m, _ in SCORE_RUNS]
    print("## D1-4. Rank of the seven score models within each subset (1 = best; '=' a tie)\n")
    out = []
    for metric, lab in (("auroc", "AUROC"), ("elim", "elim@98")):
        rk = {s[0]: ranks_desc([res[(s[0], m)][0][metric] for m in names]) for s in SUBSETS}
        for j, m in enumerate(names):
            out.append([lab, m] + [rk[s[0]][j] for s in SUBSETS])
    table(["metric", "run"] + [f"({s[0]})" for s in SUBSETS], out)

    print("## D1-5. Share of bootstrap resamples in which each score model is best (ties split evenly)\n")
    out = []
    for metric, lab in (("auroc", "AUROC"), ("elim", "elim@98")):
        for m in names:
            row = [lab, m]
            for s in SUBSETS:
                b = boots[s[0]]; win = 0.0
                for it in range(a.boot):
                    vals = {x: b[x][metric][it] for x in names}
                    top = max(vals.values())
                    best = [x for x in names if vals[x] >= top - 1e-12]
                    if m in best:
                        win += 1 / len(best)
                row.append(f"{win / a.boot:.0%}")
            out.append(row)
    table(["metric", "run"] + [f"({s[0]})" for s in SUBSETS], out)

    print("## D1-6. Agreement of each subset's model ranking with the everything ranking (Kendall tau-a, 7 models)\n")
    out = []
    for metric, lab in (("auroc", "AUROC"), ("elim", "elim@98")):
        ref = [res[("e", m)][0][metric] for m in names]
        row = [lab]
        for s in SUBSETS:
            v = [res[(s[0], m)][0][metric] for m in names]
            row.append(f"{kendall_tau(v, ref):+.2f}")
        out.append(row)
    table(["metric"] + [f"({s[0]}) vs (e)" for s in SUBSETS], out)
    out = []
    for s in SUBSETS:
        for metric, lab in (("auroc", "AUROC"), ("elim", "elim@98")):
            order = sorted(names, key=lambda m: -res[(s[0], m)][0][metric])
            out.append([f"({s[0]}) {s[1]}", lab, " > ".join(
                f"{m} {res[(s[0], m)][0][metric]:.3f}" if metric == "auroc" else f"{m} {res[(s[0], m)][0][metric]:.0%}"
                for m in order)])
    table(["subset", "metric", "order (best first)"], out)

    print("## D1-7. Where the headline elim@98 comes from: negatives cleared at each run's all-pairs 98% cutoff\n")
    out = []
    for m, _ in ALL_RUNS:
        pt = res[("e", m)][0]; t = pt["thr"]
        R = runs[m].values()
        c = collections.Counter((r["kind"], r["score"] < t) for r in R if not r["label"])
        n_real = c[("real_negative", True)] + c[("real_negative", False)]
        n_hard = c[("hard_negative", True)] + c[("hard_negative", False)]
        cleared = c[("real_negative", True)] + c[("hard_negative", True)]
        hw = [r for r in R if r["kind"] == "hard_negative" and r["recipe"] == "same_subject_wrong_date"]
        hi_ = [r for r in R if r["kind"] == "hard_negative" and r["recipe"] != "same_subject_wrong_date"]
        kw = sum(r["score"] < t for r in hw); ki = sum(r["score"] < t for r in hi_)
        out.append([m, f"{t:.4g}", f"{pt['elim']:.0%} ({pt['k']}/{pt['n_neg']})",
                    f"{c[('real_negative', True)]}/{n_real} ({c[('real_negative', True)] / n_real:.0%})",
                    f"{c[('hard_negative', True)]}/{n_hard} ({c[('hard_negative', True)] / n_hard:.0%})",
                    f"{kw}/{len(hw)}", f"{ki}/{len(hi_)} ({ki / len(hi_):.0%})" if hi_ else "—",
                    f"{c[('real_negative', True)] / cleared:.0%}" if cleared else "—"])
    table(["run", "all-pairs thr98", "elim@98 (all)", "real− cleared", "hard− cleared", "  of which wrong-date",
           "  of which in-window", "share of cleared that are real−"], out)

    print("## D1-8. Hard negatives cleared at each run's all-pairs 98% cutoff, by recipe (k/n), and the spread\n")
    print("The recipes are roughly equal in number by design; a real keyword-search result would mix them in "
          "unknown proportions, so elimination on hard negatives could fall anywhere between the min and max.\n")
    recipes = sorted({x["recipe"] for x in P.values() if x["kind"] == "hard_negative"})
    out = []
    for m, _ in SCORE_RUNS:
        t = res[("e", m)][0]["thr"]
        row = [m]; shares = []
        for rc in recipes:
            xs = [r for r in runs[m].values() if r["kind"] == "hard_negative" and r["recipe"] == rc]
            k = sum(r["score"] < t for r in xs)
            row.append(f"{k}/{len(xs)} ({k / len(xs):.0%})"); shares.append(k / len(xs))
        row.append(f"{min(shares):.0%}–{max(shares):.0%}")
        out.append(row)
    table(["run"] + recipes + ["min–max"], out)

    print("## D1-9. Ranges across the seven score models (min–max of the point estimates above)\n")
    out = []
    for sub in SUBSETS:
        au = [res[(sub[0], m)][0]["auroc"] for m in names]; el = [res[(sub[0], m)][0]["elim"] for m in names]
        out.append([f"({sub[0]}) {sub[1]}", f"{min(au):.3f}–{max(au):.3f}", f"{min(el):.0%}–{max(el):.0%}"])
    jn = [m for m, _ in JSON_RUNS]
    for sub in SUBSETS:
        au = [res[(sub[0], m)][0]["auroc"] for m in jn]; el = [res[(sub[0], m)][0]["elim"] for m in jn]
        out.append([f"JSON runs, ({sub[0]})", f"{min(au):.3f}–{max(au):.3f}", f"{min(el):.0%}–{max(el):.0%}"])
    table(["subset", "AUROC range", "elim@98 range"], out)
    gap = lambda x, y: max(abs(res[(x, m)][0]["auroc"] - res[(y, m)][0]["auroc"]) for m in names)
    print(f"Largest |AUROC (c) − AUROC (a)| over the seven score models: {gap('c', 'a'):.3f}; "
          f"|AUROC (d) − AUROC (b)|: {gap('d', 'b'):.3f}\n")
    sh = []
    for m in names:
        t = res[("e", m)][0]["thr"]
        cl = [r for r in runs[m].values() if not r["label"] and r["score"] < t]
        sh.append(sum(r["kind"] == "real_negative" for r in cl) / len(cl))
    print(f"Share of negatives cleared at the headline cutoff that are real negatives, seven score models: "
          f"{min(sh):.0%}–{max(sh):.0%}\n")


if __name__ == "__main__":
    main()
