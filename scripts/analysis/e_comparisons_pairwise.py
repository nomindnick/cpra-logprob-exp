"""E1. Which model differences are real? Paired bootstrap of AUROC and elim@98 differences.

  uv run python scripts/analysis/e_comparisons_pairwise.py [--boot 10000]

  Table E0   inventory of every run the branch-E scripts read (scored / unscored rows), pair counts
For the seven score models, on the main set and on the 25-3152 roster set:
  Table E1a  per-model AUROC and elim@98 with marginal 95% bootstrap CIs
  Table E1b  all 21 pairwise AUROC differences: paired bootstrap 95% CI and p, Holm, DeLong cross-check
  Table E1c  all 21 pairwise elim@98 differences: paired bootstrap 95% CI and p, Holm
  Table E1d  7x7 matrices of the differences (row minus column), * = survives Holm in its family of 21
  Table E1e  counts: CI excludes 0 / Holm within family / Holm across all 84 tests
  Table E1f  cross-check: DeLong SE vs bootstrap SD of each model's AUROC, and bootstrap skew
Bootstrap: resample pairs within each label class (class sizes fixed); the same resample is used for
every model, so differences are paired. Seeds are fixed (main 101, roster 202). Stdlib only.
"""
import argparse
import collections
import itertools
import json
import math
import random
import statistics
import sys
import time

from e_comparisons_common import (FRESH, JSON, SCORE, auroc, boot_p, ci, delong, delong_p, elim98, fp, holm, resample,
                                  rows, runs_by_tag, strata, table)


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def run_set(name, roster, B, seed):
    data = [rows(tag, roster) for _, tag in SCORE]
    names = [n for n, _ in SCORE]
    ids = sorted(set.intersection(*(set(d) for d in data)))
    lab = {p: data[0][p]["label"] for p in ids}
    for d in data:  # every run carries the same label for a pair (all come from pairs.jsonl)
        assert all(d[p]["label"] == lab[p] for p in ids)
    pos, neg = strata(ids, lab)
    L = [lab[p] for p in ids]
    S = [[d[p]["score"] for p in ids] for d in data]
    pt_a = [auroc(s, L) for s in S]
    pt_e = [elim98(s, L) for s in S]

    rng = random.Random(seed)
    ba = [[] for _ in SCORE]; be = [[] for _ in SCORE]
    t0 = time.time()
    for _ in range(B):
        bs = resample(pos, neg, rng)
        bl = [lab[p] for p in bs]
        for k, d in enumerate(data):
            sc = [d[p]["score"] for p in bs]
            ba[k].append(auroc(sc, bl)); be[k].append(elim98(sc, bl))
    secs = time.time() - t0

    print(f"[{name}: bootstrap took {secs:.0f} s]", file=sys.stderr)
    print(f"### {name}: {len(ids)} pairs ({len(pos)} responsive / {len(neg)} not), {B} paired resamples "
          f"(seed {seed})\n")
    print(f"Table E1a ({name}). Per model, with marginal 95% bootstrap CIs.\n")
    table(["model", "AUROC [95% CI]", "elim@98 [95% CI]"],
          [[names[k], f"{pt_a[k]:.3f} [{ci(ba[k])[0]:.3f}–{ci(ba[k])[1]:.3f}]",
            f"{pt_e[k]:.1%} [{ci(be[k])[0]:.1%}–{ci(be[k])[1]:.1%}]"] for k in range(len(SCORE))])

    aucs, C = delong(S, L)
    assert all(abs(a - b) < 1e-12 for a, b in zip(aucs, pt_a))
    out = {}
    for metric, pt, bd in (("AUROC", pt_a, ba), ("elim@98", pt_e, be)):
        res = []
        for i, j in itertools.combinations(range(len(SCORE)), 2):
            a, b = (i, j) if (pt[i], -i) >= (pt[j], -j) else (j, i)  # orient so the point estimate is >= 0
            d = [x - y for x, y in zip(bd[a], bd[b])]
            lo, hi = ci(d)
            res.append({"a": a, "b": b, "delta": pt[a] - pt[b], "lo": lo, "hi": hi, "p": boot_p(d),
                        "dl": delong_p(aucs, C, a, b) if metric == "AUROC" else None,
                        "sd": statistics.stdev(d), "le0": sum(x <= 0 for x in d) / len(d),
                        "se_dl": max(C[a][a] + C[b][b] - 2 * C[a][b], 0) ** 0.5})
            sd = res[-1]["sd"]
            res[-1]["pn"] = math.erfc(abs(res[-1]["delta"]) / sd / math.sqrt(2)) if sd > 0 else 1.0
        for r, h in zip(res, holm([r["p"] for r in res])):
            r["holm"] = h
        for r, h in zip(res, holm([r["pn"] for r in res])):
            r["pnholm"] = h
        if metric == "AUROC":
            for r, h in zip(res, holm([r["dl"] for r in res])):
                r["dlholm"] = h
        out[metric] = res
        tab = "E1b" if metric == "AUROC" else "E1c"
        fmt = (lambda x: f"{x:+.3f}") if metric == "AUROC" else (lambda x: f"{x * 100:+.1f}")
        unit = "" if metric == "AUROC" else " (percentage points)"
        print(f"Table {tab} ({name}). {metric} difference{unit}, higher-scoring model first; sorted by bootstrap p. "
              f"'CI excl. 0' = the 95% CI does not contain 0; Holm = Holm-adjusted p within these 21 tests. "
              f"'normal p' = the p-value from a normal curve with the bootstrap SD of the difference (ignores the "
              f"bootstrap's tail shape; a more conservative reading), Holm-adjusted.\n")
        hdr = ["A − B", f"Δ{metric}", "95% CI", "CI excl. 0", "bootstrap p", "Holm p", "survives Holm",
               "normal p (Holm)"]
        if metric == "AUROC":
            hdr += ["DeLong p", "DeLong Holm p"]
        body = []
        for r in sorted(res, key=lambda r: (r["p"], -abs(r["delta"]))):
            excl = r["lo"] > 0 or r["hi"] < 0
            row = [f"{names[r['a']]} − {names[r['b']]}", fmt(r["delta"]), f"[{fmt(r['lo'])}, {fmt(r['hi'])}]",
                   "yes" if excl else "no", fp(r["p"]), fp(r["holm"]), "**yes**" if r["holm"] < 0.05 else "no",
                   f"{fp(r['pn'])} ({fp(r['pnholm'])})"]
            if metric == "AUROC":
                row += [fp(r["dl"]), fp(r["dlholm"])]
            body.append(row)
        table(hdr, body)

    print(f"Table E1d ({name}). Row model minus column model; * = survives Holm (bootstrap p) within its family of 21.\n")
    for metric, pt in (("AUROC", pt_a), ("elim@98", pt_e)):
        sig = {(r["a"], r["b"]): r["holm"] < 0.05 for r in out[metric]}
        sig.update({(b, a): s for (a, b), s in list(sig.items())})
        fmt = (lambda x: f"{x:+.3f}") if metric == "AUROC" else (lambda x: f"{x * 100:+.0f}")
        body = []
        for i in range(len(SCORE)):
            body.append([f"**{names[i]}**"] + ["—" if i == j else fmt(pt[i] - pt[j]) + ("*" if sig[(i, j)] else "")
                                              for j in range(len(SCORE))])
        print(f"{metric}{' (points)' if metric != 'AUROC' else ''}:\n")
        table([metric] + names, body)

    print(f"Table E1f ({name}). Cross-check of the two uncertainty methods: DeLong standard error of each model's AUROC "
          f"vs the standard deviation of its bootstrap AUROCs, and the skew of the bootstrap distribution (mean − median; "
          f"0 for a symmetric one).\n")
    table(["model", "AUROC", "DeLong SE", "bootstrap SD", "bootstrap mean − median"],
          [[names[k], f"{pt_a[k]:.3f}", f"{C[k][k] ** 0.5:.4f}", f"{statistics.stdev(ba[k]):.4f}",
            f"{statistics.fmean(ba[k]) - statistics.median(ba[k]):+.4f}"] for k in range(len(SCORE))])
    dis = [r for r in out["AUROC"] if (r["holm"] < 0.05) != (r["dlholm"] < 0.05)]
    if dis:
        print(f"For the AUROC differences where bootstrap-Holm and DeLong-Holm disagree ({name}): the spread of the "
              f"difference by each method, the share of resamples at or below zero, and the p-value a normal curve with "
              f"the bootstrap SD would give.\n")
        table(["A − B", "ΔAUROC", "DeLong SE of Δ", "bootstrap SD of Δ", "resamples with Δ ≤ 0", "bootstrap p",
               "normal p from bootstrap SD", "DeLong p"],
              [[f"{names[r['a']]} − {names[r['b']]}", f"{r['delta']:+.3f}", f"{r['se_dl']:.4f}", f"{r['sd']:.4f}",
                f"{r['le0']:.2%}", fp(r["p"]), fp(math.erfc(abs(r["delta"]) / r["sd"] / math.sqrt(2))), fp(r["dl"])]
               for r in sorted(dis, key=lambda r: r["p"])])
    return out


def inventory():
    """Table E0: the runs every branch-E table reads, with scored and unscored row counts."""
    R = runs_by_tag()
    print("## E0. Runs used\n")
    print("Table E0. Runs read by the branch-E scripts. 'scored' = rows with a score whose pair_id is in "
          "data/golden/pairs.jsonl; 'unscored' = rows with no score (JSON parse failures), dropped.\n")
    body = []
    for n, t in SCORE + JSON + FRESH:
        cfg = json.load(open(f"runs/{t}/run.json"))
        row = [n, f"`{t}`", cfg["model"], cfg.get("details", {}).get("quantization_level", "— (hosted)")]
        for ro in (False, True):
            r = R[t + ("_roster" if ro else "")]
            row.append(f"{len(r['rows'])} / {len(r['all']) - len(r['rows'])}")
        body.append(row)
    table(["label", "run (main; the roster twin adds _roster)", "model", "quantization", "main: scored / unscored",
           "roster: scored / unscored"], body)
    for ro, name in ((False, "main"), (True, "roster")):
        P = rows(SCORE[0][1], ro)
        k = collections.Counter((P[p]["request_id"], P[p]["label"]) for p in P)
        print(f"- {name} set: " + "; ".join(f"{rid}: {k[(rid, 1)]} responsive / {k[(rid, 0)]} not"
                                            for rid in ("24-409", "25-3152") if k[(rid, 1)] + k[(rid, 0)]))
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=10000)
    a = ap.parse_args()
    inventory()
    print("## E1. Pairwise differences among the seven score models\n")
    res = {"main": run_set("Main set", False, a.boot, 101), "roster": run_set("25-3152 roster set", True, a.boot, 202)}
    allp = [(s, m, i, r["p"]) for s in res for m in res[s] for i, r in enumerate(res[s][m])]
    adj = holm([x[3] for x in allp])
    across = {(s, m, i): h for (s, m, i, _), h in zip(allp, adj)}
    print("Table E1e. How many of the 21 pairwise differences are distinguishable from zero.\n")
    body = []
    for s in res:
        for m in res[s]:
            rs = res[s][m]
            body.append([{"main": f"main ({N_ALL})", "roster": f"roster ({NR['25-3152']})"}[s], m,
                         sum(r["lo"] > 0 or r["hi"] < 0 for r in rs), sum(r["holm"] < 0.05 for r in rs),
                         sum(across[(s, m, i)] < 0.05 for i in range(len(rs))),
                         sum(r["pnholm"] < 0.05 for r in rs),
                         sum(r["dlholm"] < 0.05 for r in rs) if m == "AUROC" else "—"])
    table(["set", "metric", "95% CI excludes 0", "Holm within 21", "Holm across all 84",
           "normal p (bootstrap SD) + Holm within 21", "DeLong + Holm within 21"], body)


if __name__ == "__main__":
    main()
