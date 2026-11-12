"""E4. Calibration: can the scores be read as probabilities?

  uv run python scripts/analysis/e_comparisons_calibration.py [--boot 2000 --sims 2000]

Main set (all pairs). Seven score models; the six JSON verdict modes as contrast.
  Table E4a  Brier score and ECE (10 equal-width bins) with 95% bootstrap CIs; the ECE expected from
             noise alone if the scores were perfectly calibrated; mean score vs the share responsive
  Table E4b  logistic recalibration: intercept and slope of label ~ logit(score) (score models only)
  Table E4c  the fixed 0.5 cutoff: recall and share of non-responsive eliminated, k/n with Wilson 95% CIs
  Table E4d  reliability: per 0.1-wide score bin, mean score -> observed share responsive (n)
  Table E4e  per request: Brier, ECE, mean score vs share responsive
  Table E4f  paired bootstrap differences in Brier and ECE for selected pairs
  Table E4g  what a score of 0.5 / 0.8 / 0.95 would mean at a lower share of responsive emails (label shift)
Definitions: Brier = mean (score - label)^2. ECE = sum over bins of (bin share) * |mean score - share responsive|,
bins [0, .1), ..., [.9, 1]. Noise floor: labels redrawn as Bernoulli(score) (perfect calibration by
construction), seed 707; p = share of redraws with ECE >= observed. Bootstrap: stratified by label, seed 606.
Stdlib only.
"""
import argparse
import random
import statistics

from e_comparisons_common import (JSON, SCORE, bin_of, boot_p, brier, ci, ece, fp, kn_ci, logistic_fit, logit, resample,
                                  rows, strata, table)

PAIRS = [("d3-27b", "27b lp"), ("d3-27b", "Jev"), ("27b lp", "Jev"), ("d3-4b", "4b lp"), ("d3-9b", "9b lp"),
         ("9b lp", "4b lp")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--sims", type=int, default=2000)
    a = ap.parse_args()
    cfgs = [(n, rows(t), False) for n, t in SCORE] + [(n, rows(t), True) for n, t in JSON]
    allids = sorted(cfgs[0][1])
    lab = {p: cfgs[0][1][p]["label"] for p in allids}
    pos, neg = strata(allids, lab)
    prev = len(pos) / len(allids)

    rng = random.Random(606)
    bs_list = [resample(pos, neg, rng) for _ in range(a.boot)]
    srng = random.Random(707)

    print("## E4. Calibration\n")
    print(f"Share responsive in the golden set: {len(pos)}/{len(allids)} = {prev:.1%}.\n")
    print(f"Table E4a. Brier score and ECE with 95% bootstrap CIs ({a.boot} resamples). 'ECE if calibrated' = the "
          f"median [95th percentile] ECE when labels are redrawn from the model's own scores ({a.sims} redraws), i.e. "
          f"what bin noise alone produces; p = share of redraws at least as bad as observed. Lower is better.\n")
    body = []
    boots = {}
    for n, d, js in cfgs:
        ids = [p for p in allids if p in d]
        s = [d[p]["score"] for p in ids]; l = [d[p]["label"] for p in ids]
        bb, be = [], []
        for bs in bs_list:
            ps = [p for p in bs if p in d]
            ss = [d[p]["score"] for p in ps]; ll = [d[p]["label"] for p in ps]
            bb.append(brier(ss, ll)); be.append(ece(ss, ll))
        boots[n] = (bb, be)
        sim = []
        for _ in range(a.sims):
            sim.append(ece(s, [1 if srng.random() < x else 0 for x in s]))
        sim.sort()
        e = ece(s, l)
        body.append([n + (" (contrast)" if js else ""), len(ids), f"{brier(s, l):.3f} [{ci(bb)[0]:.3f}–{ci(bb)[1]:.3f}]",
                     f"{e:.3f} [{ci(be)[0]:.3f}–{ci(be)[1]:.3f}]",
                     f"{statistics.median(sim):.3f} [{sim[int(.95 * len(sim)) - 1]:.3f}]",
                     fp((sum(x >= e for x in sim) + 1) / (len(sim) + 1)), f"{statistics.fmean(s):.3f}"])
    table(["model", "n", "Brier [95% CI]", "ECE [95% CI]", "ECE if calibrated: median [95th pct]", "p", "mean score"], body)
    print(f"(Mean score to compare with the share responsive, {prev:.3f}.)\n")

    print("Table E4b. Logistic recalibration (score models): fit P(responsive) = 1/(1+exp(-(a + b·logit(score)))). "
          "A calibrated score has a = 0 and b = 1. b < 1: the scores are too extreme (overconfident); b > 1: too timid. "
          "a > 0: the scores run low overall. 95% bootstrap CIs.\n")
    body = []
    for n, d, js in cfgs:
        if js:
            continue
        ids = [p for p in allids if p in d]
        A, Bs = logistic_fit([logit(d[p]["score"]) for p in ids], [lab[p] for p in ids])
        aa, bb = [], []
        for bs in bs_list[:min(1000, len(bs_list))]:
            x, y = logistic_fit([logit(d[p]["score"]) for p in bs], [lab[p] for p in bs])
            aa.append(x); bb.append(y)
        body.append([n, f"{A:+.2f} [{ci(aa)[0]:+.2f}, {ci(aa)[1]:+.2f}]", f"{Bs:.2f} [{ci(bb)[0]:.2f}, {ci(bb)[1]:.2f}]"])
    table(["model", "intercept a", "slope b"], body)
    print("(Slope and intercept CIs use the first 1,000 of the bootstrap resamples.)\n")

    print("Table E4c. The fixed 0.5 cutoff (JSON: the verdict). Wilson 95% CIs.\n")
    body = []
    for n, d, js in cfgs:
        ids = [p for p in allids if p in d]
        yes = lambda p: bool(d[p]["verdict"]) if js else d[p]["score"] >= 0.5
        P = [p for p in ids if lab[p]]; N = [p for p in ids if not lab[p]]
        body.append([n + (" (contrast)" if js else ""), kn_ci(sum(yes(p) for p in P), len(P)),
                     kn_ci(sum(not yes(p) for p in N), len(N)), len(P) - sum(yes(p) for p in P)])
    table(["model", "recall @0.5", "eliminated @0.5", "responsive missed"], body)

    print("Table E4d. Reliability, score models: in each 0.1-wide score bin, mean score → observed share responsive "
          "(number of pairs). A calibrated model has the two numbers close in every well-filled bin.\n")
    body = []
    for b in range(10):
        row = [f"{b / 10:.1f}–{(b + 1) / 10:.1f}"]
        for n, d, js in cfgs:
            if js:
                continue
            xs = [(d[p]["score"], lab[p]) for p in allids if p in d and bin_of(d[p]["score"]) == b]
            row.append(f"{statistics.fmean(x for x, _ in xs):.2f}→{statistics.fmean(y for _, y in xs):.2f} ({len(xs)})"
                       if xs else "— (0)")
        body.append(row)
    table(["bin"] + [n for n, _, js in cfgs if not js], body)

    print("Table E4e. Per request, score models.\n")
    body = []
    for rid in ("24-409", "25-3152"):
        for n, d, js in cfgs:
            if js:
                continue
            ids = [p for p in allids if p in d and d[p]["request_id"] == rid]
            s = [d[p]["score"] for p in ids]; l = [lab[p] for p in ids]
            body.append([rid, n, len(ids), f"{brier(s, l):.3f}", f"{ece(s, l):.3f}", f"{statistics.fmean(s):.3f}",
                         f"{sum(l) / len(l):.3f}"])
    table(["request", "model", "n", "Brier", "ECE", "mean score", "share responsive"], body)

    print("Table E4f. Paired bootstrap differences (A − B; negative = A better calibrated), same resamples as E4a.\n")
    body = []
    for x, y in PAIRS:
        db = [u - v for u, v in zip(boots[x][0], boots[y][0])]
        de = [u - v for u, v in zip(boots[x][1], boots[y][1])]
        dx, dy = dict(cfgs_by(cfgs))[x], dict(cfgs_by(cfgs))[y]
        sx = [dx[p]["score"] for p in allids]; sy = [dy[p]["score"] for p in allids]; l = [lab[p] for p in allids]
        body.append([f"{x} − {y}", f"{brier(sx, l) - brier(sy, l):+.3f} [{ci(db)[0]:+.3f}, {ci(db)[1]:+.3f}]", fp(boot_p(db)),
                     f"{ece(sx, l) - ece(sy, l):+.3f} [{ci(de)[0]:+.3f}, {ci(de)[1]:+.3f}]", fp(boot_p(de))])
    table(["A − B", "ΔBrier [95% CI]", "p", "ΔECE [95% CI]", "p"], body)

    print(f"Table E4g. Label shift. If the responsive share among the emails screened were lower than the golden set's "
          f"{prev:.1%}, and responsive and non-responsive emails each scored as they do here, a score s from a model "
          f"calibrated on this set would correspond to these probabilities (odds rescaled by the ratio of prior odds).\n")
    body = []
    for s in (0.2, 0.5, 0.8, 0.95):
        row = [f"{s:.2f}"]
        for pi in (prev, 0.30, 0.10, 0.03):
            o = s / (1 - s) * (pi / (1 - pi)) / (prev / (1 - prev))
            row.append(f"{o / (1 + o):.3f}")
        body.append(row)
    table(["score here", f"at {prev:.1%} (as here)", "at 30%", "at 10%", "at 3%"], body)


def cfgs_by(cfgs):
    return [(n, d) for n, d, _ in cfgs]


if __name__ == "__main__":
    main()
