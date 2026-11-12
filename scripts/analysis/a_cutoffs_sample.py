"""A4. Set the cutoff from a small labeled random sample of the target request, then screen the rest.

  uv run python scripts/analysis/a_cutoffs_sample.py [--reps 1000]

Prints tables A4a-A4e for docs/analysis/A-cutoffs.md. Stdlib only, deterministic: every cell's random
draws come from random.Random(crc32 of "A4|<request>|<design>|<n>"), so all models, rules and the
roster/no-roster twins of 25-3152 see the same sampled pairs in each repetition (paired comparisons).

Workflow simulated: the agency reviews n emails drawn by SIMPLE RANDOM SAMPLING (without replacement)
from the target request's pool, notes the scores of the ones it finds responsive, sets the cutoff by a
rule, and screens the unreviewed remainder (flag = score >= cutoff).

Rules (k = responsive emails found in the sample):
  lowest       cutoff = the lowest score among the k sampled responsive emails
  lowest/3     the same cutoff with the model's odds of "yes" divided by 3: sigmoid(logit(lowest) - ln 3)
  lowest/10    odds divided by 10: sigmoid(logit(lowest) - ln 10)
  min(lowest, prior)  the lower of `lowest` and the other request's thr98 (a prior from a past request:
               24-409 uses 25-3152's thr98; 25-3152 and 25-3152+R use 24-409's)
  min(lowest, prior+R) 24-409 only: the same with 25-3152+R's thr98 as the prior (the roster setting)
If k = 0 every rule falls back to cutoff 0 (review everything); A4b counts how often that happens.

Designs:
  as-is  the golden pool itself (24-409 about 59% responsive, 25-3152 about 57%). Recall
         and eliminated share are measured on the unsampled remainder of the pool.
  20%    a pool where 20% of emails are responsive, standing in for a real keyword search's lower
         prevalence. The number of responsive emails in the sample is k ~ Binomial(n, 0.2) (a large
         pool); those k are drawn without replacement from the request's positives. Recall is measured on
         the positives not sampled; the eliminated share on all of the request's negatives (in a large
         pool the sampled negatives are a negligible share). Only positives set the cutoff, so the
         sampled negatives need not be simulated.

Percentiles: p5 = the value at index floor(0.05 * reps) of the sorted results (5% of repetitions do
worse), p50 the median the same way; misses p95 = index floor(0.95 * reps) of sorted miss counts.
"""
import argparse
import bisect
import math
import random
import zlib

from a_cutoffs_common import SCORE_MODELS, cutoff, load, pctile, table

PRIOR_SOURCE = {"24-409": "25-3152", "25-3152": "24-409", "25-3152+R": "24-409"}
RULES = ["lowest", "lowest/3", "lowest/10", "min(lowest, prior)"]
RULES_FOR = {"24-409": RULES + ["min(lowest, prior+R)"], "25-3152": RULES, "25-3152+R": RULES}
DESIGNS = {"as-is": [10, 20, 30, 50, 75, 100], "20%": [10, 20, 30, 50, 75, 100, 150, 200, 300]}
MAIN_NS = [20, 50, 100]
TARGETS = ["24-409", "25-3152", "25-3152+R"]


def shrink_odds(p, f):
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    return 1 / (1 + math.exp(-(math.log(p / (1 - p)) - math.log(f))))


def cut_for(rule, lowest, priors):
    if lowest is None:
        return 0.0
    if rule.startswith("min("):
        return min(lowest, priors[rule])
    return {"lowest": lowest, "lowest/3": shrink_odds(lowest, 3), "lowest/10": shrink_odds(lowest, 10)}[rule]


def priors_for(data, m, t):
    p = {"min(lowest, prior)": cutoff(data[m][PRIOR_SOURCE[t]], .98)}
    if t == "24-409":
        p["min(lowest, prior+R)"] = cutoff(data[m]["25-3152+R"], .98)
    return p


def draws(req, design, n, rows_by_id, reps):
    """Yield (sampled positive ids, sampled negative ids) per repetition, identical across models."""
    rng = random.Random(zlib.crc32(f"A4|{req.replace('+R', '')}|{design}|{n}".encode()))
    ids = sorted(rows_by_id)
    pos = [p for p in ids if rows_by_id[p]["label"]]
    out = []
    for _ in range(reps):
        if design == "as-is":
            s = rng.sample(ids, n)
            out.append(([p for p in s if rows_by_id[p]["label"]], [p for p in s if not rows_by_id[p]["label"]]))
        else:
            k = sum(rng.random() < 0.2 for _ in range(n))
            out.append((rng.sample(pos, k), []))
    return out


def simulate(rows, priors, design, samples, rules):
    """Per rule: list of (remainder recall, remainder misses, eliminated share) over repetitions."""
    by = {r["pair_id"]: r for r in rows}
    ps = sorted(r["score"] for r in rows if r["label"]); ns = sorted(r["score"] for r in rows if not r["label"])
    P, N = len(ps), len(ns)
    res = {rule: [] for rule in rules}
    for sp, sn in samples:
        sps = [by[p]["score"] for p in sp]; sns = [by[p]["score"] for p in sn]
        lowest = min(sps) if sps else None
        for rule in rules:
            c = cut_for(rule, lowest, priors)
            rem_pos = P - len(sps)
            flagged = (P - bisect.bisect_left(ps, c)) - sum(s >= c for s in sps)
            miss = rem_pos - flagged
            if design == "as-is":
                elim = (bisect.bisect_left(ns, c) - sum(s < c for s in sns)) / (N - len(sns))
            else:
                elim = bisect.bisect_left(ns, c) / N
            res[rule].append(((rem_pos - miss) / rem_pos, miss, elim))
    return res


def summarize(xs):
    rec = sorted(x[0] for x in xs); miss = sorted(x[1] for x in xs); el = sorted(x[2] for x in xs)
    return {"rec50": pctile(rec, .5), "rec5": pctile(rec, .05), "miss95": pctile(miss, .95), "miss50": pctile(miss, .5),
            "el50": pctile(el, .5), "el5": pctile(el, .05), "p98": sum(r >= .98 - 1e-12 for r in rec) / len(rec)}


def fmt(s):
    return (f"{s['rec50']:.1%} / {s['rec5']:.1%} · ≤{s['miss95']} · {s['el50']:.0%} / {s['el5']:.0%} · "
            f"{s['p98']:.2f}")


def run(data, reps):
    """results[(model, target, design, n)] = {rule: summary}; kstats[(target, design, n)] = (mean k, #k=0, ks)."""
    results, kstats = {}, {}
    for t in TARGETS:
        by_id = {r["pair_id"]: r for r in data["4b lp"][t]}
        for design, ns in DESIGNS.items():
            for n in ns:
                samples = draws(t, design, n, by_id, reps)
                ks = [len(sp) for sp, _ in samples]
                kstats[(t, design, n)] = (sum(ks) / len(ks), sum(k == 0 for k in ks), sorted(ks))
                for m, _ in SCORE_MODELS:
                    sim = simulate(data[m][t], priors_for(data, m, t), design, samples, RULES_FOR[t])
                    results[(m, t, design, n)] = {rule: summarize(v) for rule, v in sim.items()}
    return results, kstats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=1000)
    a = ap.parse_args()
    data = load()
    results, kstats = run(data, a.reps)

    print(f"# A4. Cutoff from a small labeled sample ({a.reps} repetitions per cell)\n")

    print("## A4a. What the `lowest` rule can promise, whatever the model (distribution-free)\n")
    print("If the k sampled responsive emails are a random draw from all responsive emails and scores have no "
          "ties, the share of responsive emails scoring below the lowest sampled one follows a Beta(1, k) "
          "distribution: expected recall k/(k+1), median recall 0.5^(1/k), and P(recall ≥ 98%) = 1 − 0.98^k.\n")
    out = []
    for k in (5, 10, 12, 20, 29, 35, 50, 57, 100, 114, 149):
        out.append([k, f"{k / (k + 1):.1%}", f"{0.5 ** (1 / k):.1%}", f"{1 - 0.98 ** k:.2f}"])
    table(["responsive in sample (k)", "expected recall", "median recall", "P(recall ≥ 98%)"], out)
    for p in (.5, .9, .95):
        print(f"- k needed for P(recall ≥ 98%) ≥ {p:.0%}: {math.ceil(math.log(1 - p) / math.log(0.98))}")
    print()
    print("Margin examples (odds = p / (1 − p)): " + "; ".join(
        f"lowest {p:g} → lowest/3 {shrink_odds(p, 3):.3f}, lowest/10 {shrink_odds(p, 10):.3f}" for p in (0.9, 0.5, 0.3, 0.05))
        + "\n")

    print("## A4b. Responsive emails in the sample (k)\n")
    out = []
    for t in TARGETS[:2]:
        for design, ns in DESIGNS.items():
            for n in ns:
                mean, zero, ks = kstats[(t, design, n)]
                out.append([t, design, n, f"{mean:.1f}", f"{pctile(ks, .05)}–{pctile(ks, .95)}", f"{zero}/{a.reps}"])
    table(["request", "design", "n reviewed", "mean k", "k, 5th–95th pct", "reps with k = 0 (review all)"], out)
    print("25-3152+R draws the same pairs as 25-3152.\n")

    print("## A4c. Achieved recall and eliminated share on the unreviewed remainder\n")
    print("Cell: recall median / 5th percentile · misses at the 95th percentile (count) · eliminated median / "
          "5th percentile · share of repetitions with recall ≥ 98%.\n")
    for design in DESIGNS:
        for t in TARGETS:
            print(f"### {t}, {design} prevalence\n")
            out = []
            for m, _ in SCORE_MODELS:
                for n in MAIN_NS:
                    out.append([m, n] + [fmt(results[(m, t, design, n)][rule]) for rule in RULES_FOR[t]])
            table(["model", "n"] + RULES_FOR[t], out)

    print("## A4d. Sample size needed\n")
    print("Smallest n reviewed (from the grid as-is: 10, 20, 30, 50, 75, 100; 20%: also 150, 200, 300) at which "
          "the MEDIAN repetition reaches ≥ 98% recall on the remainder / at which 90% of repetitions do. "
          "'>max' = not reached on the grid.\n")
    for rule in RULES:
        print(f"### Rule: {rule}\n")
        cols = [(t, d, rule) for t in TARGETS for d in DESIGNS]
        if rule == "min(lowest, prior)":
            cols = [("24-409", d, "min(lowest, prior+R)") for d in DESIGNS] + cols
        out = []
        for m, _ in SCORE_MODELS:
            row = [m]
            for t, design, r in cols:
                ns = DESIGNS[design]
                need = lambda ok: next((str(n) for n in ns if ok(results[(m, t, design, n)][r])), f">{ns[-1]}")
                row.append(f"{need(lambda s: s['rec50'] >= .98 - 1e-12)} / {need(lambda s: s['p98'] >= .9)}")
            out.append(row)
        table(["model"] + [f"{t} {d}" + (" (prior +R)" if r.endswith("+R)") else "") for t, d, r in cols], out)

    print("### How much the 20% design raises the needed n\n")
    print("needed n at 20% / needed n as-is, over the 7 models x 3 requests where both are reached on the grid "
          "(median-98% and 90%-of-repetitions criteria).\n")
    out = []
    for rule in RULES:
        for crit, ok in (("median ≥ 98%", lambda s: s["rec50"] >= .98 - 1e-12), ("90% of reps ≥ 98%", lambda s: s["p98"] >= .9)):
            ratios = []
            for m, _ in SCORE_MODELS:
                for t in TARGETS:
                    na = next((n for n in DESIGNS["as-is"] if ok(results[(m, t, "as-is", n)][rule])), None)
                    nb = next((n for n in DESIGNS["20%"] if ok(results[(m, t, "20%", n)][rule])), None)
                    if na and nb:
                        ratios.append(nb / na)
            ratios.sort()
            out.append([rule, crit, f"{len(ratios)}/21", f"{ratios[0]:.1f}–{ratios[-1]:.1f}" if ratios else "—",
                        f"{pctile(ratios, .5):.1f}" if ratios else "—"])
    table(["rule", "criterion", "cells reached in both designs", "ratio range", "median ratio"], out)

    print("## A4e. Cost of the margin: median eliminated share at n = 50, by rule\n")
    print("Next to the in-sample oracle elim@98 for the same request (A1).\n")
    out = []
    for m, _ in SCORE_MODELS:
        for t in TARGETS:
            rows = data[m][t]
            c = cutoff(rows, .98)
            neg = [r for r in rows if not r["label"]]
            oracle = sum(r["score"] < c for r in neg) / len(neg)
            row = [m, t, f"{oracle:.0%}"]
            for design in DESIGNS:
                for rule in RULES + ["min(lowest, prior+R)"]:
                    s = results[(m, t, design, 50)].get(rule)
                    row.append(f"{s['el50']:.0%} ({s['p98']:.2f})" if s else "—")
            out.append(row)
    table(["model", "request", "oracle elim@98"] + [f"{d}: {r}" for d in DESIGNS for r in RULES + ["min(lowest, prior+R)"]], out)
    print("Cell: median eliminated (share of repetitions with recall ≥ 98%).\n")


if __name__ == "__main__":
    main()
