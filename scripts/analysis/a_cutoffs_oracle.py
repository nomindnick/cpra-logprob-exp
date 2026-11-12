"""A1. Oracle (in-sample) 98%-recall cutoffs per request, and how far apart they are.

  uv run python scripts/analysis/a_cutoffs_oracle.py [--boot 1000]

Prints the subset sizes and tables A1a-A1d, including the roster-effect table under A1b
(docs/analysis/A-cutoffs.md). Stdlib only, deterministic.

thr98 = the highest cutoff whose recall >= 98% on that subset (golden_report.thr98). The bootstrap
interval resamples pairs with replacement within each label class of the subset (stratified), seed
fixed per (model, subset), and reports the 2.5th and 97.5th percentiles of thr98.
"""
import argparse
import math
import random
import zlib

from a_cutoffs_common import (KIND_ABBR, SCORE_MODELS, SETS, allowed_misses, apply, cutoff, fmt_cut,
                              fmt_elim, fmt_miss, load, table)


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def boot_cut(rows, n, seed, target=0.98):
    rng = random.Random(seed)
    pos = [r for r in rows if r["label"]]; neg = [r for r in rows if not r["label"]]
    cs = sorted(cutoff(rng.choices(pos, k=len(pos)) + rng.choices(neg, k=len(neg)), target) for _ in range(n))
    return cs[int(.025 * n)], cs[int(.975 * n) - 1]


def logit(p):
    return math.log(p / (1 - p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=1000)
    a = ap.parse_args()
    data = load()

    print("# A1. Oracle 98%-recall cutoffs\n")
    dropped = [f"{t} {n}" for d in data.values() for t, n in d["_unscored"].items() if n]
    print(f"Unscored rows dropped from the {2 * len(data)} score-model runs: {', '.join(dropped) or 'none'}\n")
    for s in SETS:
        d = data["4b lp"][s]
        P = sum(r["label"] for r in d)
        print(f"- {s}: {len(d)} pairs, {P} positives / {len(d) - P} negatives; 98% recall allows "
              f"{allowed_misses(P)} misses, 99% allows {allowed_misses(P, .99)}")
    print()

    print("## A1a. thr98 per subset [stratified bootstrap 95% interval of the cutoff]\n")
    out = []
    for m, _ in SCORE_MODELS:
        row = [m]
        for s in SETS:
            rows = data[m][s]
            c = cutoff(rows, .98)
            lo, hi = boot_cut(rows, a.boot, zlib.crc32(f"A1|{m}|{s}".encode()))
            row.append(f"{fmt_cut(c)} [{fmt_cut(lo)}–{fmt_cut(hi)}]")
        out.append(row)
    table(["model"] + SETS, out)

    print("## A1b. How far apart the two requests' cutoffs are\n")
    print("ratio = higher cutoff / lower cutoff. log-odds gap = |logit(c1) − logit(c2)|. 'Between' = emails of "
          "each request whose score lies between the two cutoffs (lower ≤ score < higher): the emails whose "
          "treatment depends on which request's cutoff is used (+ = positives, − = negatives).\n")
    out = []
    for m, _ in SCORE_MODELS:
        for other in ("25-3152", "25-3152+R"):
            c1, c2 = cutoff(data[m]["24-409"], .98), cutoff(data[m][other], .98)
            lo, hi = min(c1, c2), max(c1, c2)
            btw = lambda rows, lab: sum(lo <= r["score"] < hi for r in rows if r["label"] == lab)
            out.append([m, f"24-409 vs {other}", fmt_cut(c1), fmt_cut(c2), "24-409" if c1 > c2 else other,
                        f"{hi / lo:.2f}", f"{abs(logit(c1) - logit(c2)):.2f}",
                        f"+{btw(data[m]['24-409'], 1)} / −{btw(data[m]['24-409'], 0)}",
                        f"+{btw(data[m][other], 1)} / −{btw(data[m][other], 0)}"])
    table(["model", "pair of requests", "thr98 24-409", "thr98 other", "higher", "ratio", "log-odds gap",
           f"between, 24-409 (of {NP['24-409']}+ / {NN['24-409']}−)", f"between, other (of {NP['25-3152']}+ / {NN['25-3152']}−)"], out)

    print("Roster effect on the same 249 pairs (25-3152 → 25-3152+R), next to the change of request "
          "(24-409 vs 25-3152, both without the roster), as log-odds gaps:\n")
    out = []
    for m, _ in SCORE_MODELS:
        a, b, c = (cutoff(data[m][s], .98) for s in ("25-3152", "25-3152+R", "24-409"))
        out.append([m, fmt_cut(a), fmt_cut(b), f"{b / a:.2f}", f"{abs(logit(b) - logit(a)):.2f}",
                    f"{abs(logit(c) - logit(a)):.2f}", "roster" if abs(logit(b) - logit(a)) > abs(logit(c) - logit(a)) else "request"])
    table(["model", "thr98 25-3152", "thr98 25-3152+R", "ratio +R / no roster", "log-odds gap, roster",
           "log-odds gap, request", "bigger shift"], out)

    print("## A1c. The headline (pooled) cutoff, per request\n")
    print("The headline elim@98 uses one cutoff fitted on all pairs. Misses and eliminations per request at "
          "that cutoff (98% recall allows 2 misses on each request, 5 pooled).\n")
    out = []
    lopsided = {"pooled": 0, "pooled+R": 0}
    for m, _ in SCORE_MODELS:
        for pooled, parts in (("pooled", ("24-409", "25-3152")), ("pooled+R", ("24-409", "25-3152+R"))):
            c = cutoff(data[m][pooled], .98)
            ep = apply(data[m][pooled], c)
            row = [m, pooled, fmt_cut(c), fmt_miss(ep), fmt_elim(ep)]
            for p in parts:
                e = apply(data[m][p], c)
                row += [f"{fmt_miss(e)} ({e['recall']:.1%})", fmt_elim(e)]
                lopsided[pooled] += e["miss"] == ep["miss"]
            out.append(row)
    table(["model", "fitted on", "cutoff", "pooled misses", "pooled elim", "24-409 misses", "24-409 elim",
           "25-3152 (or +R) misses", "25-3152 (or +R) elim"], out)
    print("With 5 pooled misses, at least one request must take 3 or more (5 > 2 + 2), so the pooled cutoff is "
          "below 98% on one request whenever it uses all 5. Models whose pooled misses all fall on ONE request: "
          f"{lopsided['pooled']}/{len(SCORE_MODELS)} (pooled), {lopsided['pooled+R']}/{len(SCORE_MODELS)} (pooled+R).\n")

    print("## A1d. The lowest-scoring positives per request (they set the cutoff)\n")
    print("The 3 lowest positive scores in each subset, lowest first, with kind (real = county production; "
          "close/priv/exempt = synthetic positives; hn-flip = synthetic hard negative judged responsive). "
          "thr98 is the 3rd-lowest positive (2 misses allowed) unless ties intervene.\n")
    out, low3, setter = [], [], []
    for m, _ in SCORE_MODELS:
        row = [m]
        for s in ("24-409", "25-3152", "25-3152+R"):
            pos = sorted((r for r in data[m][s] if r["label"]), key=lambda r: r["score"])[:3]
            row.append(", ".join(f"{KIND_ABBR[r['kind']]} {fmt_cut(r['score'])}" for r in pos))
            low3.extend(pos)
            setter.append(pos[2])
        out.append(row)
    table(["model", "24-409", "25-3152", "25-3152+R"], out)
    # Slots repeat emails (the same email can be among the lowest for several models, and 25-3152 and
    # 25-3152+R share their pairs), so distinct emails are counted too, next to the base rate.
    # [corrected in verification: the slot counts were previously described as emails]
    real = lambda rs: sum(r["kind"] == "real_positive" for r in rs)
    dist = lambda rs: list({r["pair_id"]: r for r in rs}.values())
    base = {s: [r for r in data["4b lp"][s] if r["label"]] for s in ("24-409", "25-3152")}
    print(f"Real emails among these lowest positives: {real(low3)}/{len(low3)} slots, {real(dist(low3))}/{len(dist(low3))} "
          f"distinct emails; among the 3rd-lowest (the one at thr98): {real(setter)}/{len(setter)} slots, "
          f"{real(dist(setter))}/{len(dist(setter))} distinct emails. Base rate: real emails are "
          f"{real(base['24-409'])}/{len(base['24-409'])} of 24-409's positives and {real(base['25-3152'])}/"
          f"{len(base['25-3152'])} of 25-3152's.\n")


if __name__ == "__main__":
    main()
