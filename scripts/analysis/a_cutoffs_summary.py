"""A5. How much the in-sample headline overstates out-of-sample performance, and the best label-free policy.

  uv run python scripts/analysis/a_cutoffs_summary.py [--reps 1000]

Prints tables A5a-A5e for docs/analysis/A-cutoffs.md. Stdlib only, deterministic (the sample
simulation is a_cutoffs_sample.run with its fixed seeds).

Two settings, each with two target requests:
  no roster   24-409 and 25-3152 (headline: pooled thr98 on all main-set pairs)
  roster      24-409 and 25-3152+R (headline: pooled+R)

Menu of policies that need no labels from the target request:
  fixed c          c in 0.05, 0.1, 0.2, 0.3, 0.4, 0.5 (0.5 = the default)
  previous request the other request's 98% / 99% / 100%-recall cutoff (24-409 takes 25-3152's, or
                   25-3152+R's in the roster setting; 25-3152 and 25-3152+R take 24-409's)
  sample           a4 rules at n = 50 and 100 reviewed emails, 20% prevalence design
A5e applies one stated rule per model: the largest value of the extended grid 0.01, 0.02, 0.05, 0.1, ...,
0.8 that keeps >= 98% recall on all three labeled subsets (24-409, 25-3152, 25-3152+R), then one grid step
lower for headroom. Its out-of-sample check is A2d (the same heuristic fitted on one request only).
"Safe" = recall >= 98% on BOTH target requests (deterministic policies) or >= 98% recall in >= 90% of
repetitions on both (sample policies). The best safe policy is picked AFTER seeing both requests'
outcomes, so it is an optimistic (hindsight) bound on what a label-free policy would deliver.
"""
import argparse

from a_cutoffs_common import SCORE_MODELS, apply, cutoff, load, table
from a_cutoffs_sample import run

GRID = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5]
EXT = [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
SETTINGS = {"no roster": ("24-409", "25-3152", "pooled"), "roster": ("24-409", "25-3152+R", "pooled+R")}
SAMPLE_RULES = ["lowest", "lowest/3", "lowest/10", "min(lowest, prior)"]


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def prev_source(t, setting):
    if t == "24-409":
        return "25-3152" if setting == "no roster" else "25-3152+R"
    return "24-409"


def sample_rule_for(rule, t, setting):
    return "min(lowest, prior+R)" if rule == "min(lowest, prior)" and t == "24-409" and setting == "roster" else rule


def menu(data, results, m, setting):
    """[(policy name, safe?, elim t1, elim t2, combined elim, detail)] for one model and setting."""
    t1, t2, _ = SETTINGS[setting]
    out = []
    for c in GRID:
        e1, e2 = apply(data[m][t1], c), apply(data[m][t2], c)
        out.append((f"fixed {c:g}", e1["recall"] >= .98 and e2["recall"] >= .98, e1["elim_rate"], e2["elim_rate"],
                    (e1["elim"] + e2["elim"]) / (e1["N"] + e2["N"]), f"misses {e1['miss']}, {e2['miss']}"))
    for level, name in ((.98, "98%"), (.99, "99%"), (1.0, "100%")):
        e1 = apply(data[m][t1], cutoff(data[m][prev_source(t1, setting)], level))
        e2 = apply(data[m][t2], cutoff(data[m][prev_source(t2, setting)], level))
        out.append((f"previous request's {name} cutoff", e1["recall"] >= .98 and e2["recall"] >= .98,
                    e1["elim_rate"], e2["elim_rate"], (e1["elim"] + e2["elim"]) / (e1["N"] + e2["N"]),
                    f"misses {e1['miss']}, {e2['miss']}"))
    for n in (50, 100):
        for rule in SAMPLE_RULES:
            s1 = results[(m, t1, "20%", n)][sample_rule_for(rule, t1, setting)]
            s2 = results[(m, t2, "20%", n)][sample_rule_for(rule, t2, setting)]
            out.append((f"sample n={n}, {rule}", s1["p98"] >= .9 and s2["p98"] >= .9, s1["el50"], s2["el50"],
                        (s1["el50"] + s2["el50"]) / 2, f"P(≥98%) {s1['p98']:.2f}, {s2['p98']:.2f}"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=1000)
    a = ap.parse_args()
    data = load()
    results, _ = run(data, a.reps)

    print("# A5. In-sample headline vs out-of-sample\n")
    print("## A5a. The 98%-recall promise, in and out of sample\n")
    print("Headline = cutoff fitted on all pairs of the setting (in-sample). The other columns aim at the same "
          f"98% recall without the target's labels. Misses are counts on 24-409 ({NP['24-409']} positives) and on 25-3152 "
          f"({NP['25-3152']}); 98% allows 2 on each. The `lowest` sample rule is shown at n = 50, 20% prevalence: the share "
          "of repetitions reaching 98% on each request.\n")
    out = []
    for m, _ in SCORE_MODELS:
        for setting, (t1, t2, pooled) in SETTINGS.items():
            c = cutoff(data[m][pooled], .98)
            hp = apply(data[m][pooled], c)
            p1, p2 = apply(data[m][t1], c), apply(data[m][t2], c)
            o1, o2 = (apply(data[m][t], cutoff(data[m][t], .98)) for t in (t1, t2))
            x1 = apply(data[m][t1], cutoff(data[m][prev_source(t1, setting)], .98))
            x2 = apply(data[m][t2], cutoff(data[m][prev_source(t2, setting)], .98))
            d1, d2 = apply(data[m][t1], .5), apply(data[m][t2], .5)
            s1 = results[(m, t1, "20%", 50)]["lowest"]; s2 = results[(m, t2, "20%", 50)]["lowest"]
            out.append([m, setting, f"{hp['elim']}/{hp['N']} ({hp['elim_rate']:.0%})",
                        f"{p1['miss']}, {p2['miss']}", f"{o1['elim_rate']:.0%}, {o2['elim_rate']:.0%}",
                        f"{x1['miss']}, {x2['miss']}", f"{x1['elim_rate']:.0%}, {x2['elim_rate']:.0%}",
                        f"{d1['miss']}, {d2['miss']}", f"{s1['p98']:.2f}, {s2['p98']:.2f}"])
    table(["model", "setting", "headline elim@98 (in-sample)", "headline cutoff: misses per request",
           "per-request oracle elim@98", "previous request's thr98: misses", "… eliminated",
           "default 0.5: misses", "sample `lowest`: P(≥98%)"], out)

    print("## A5b. Best safe label-free policy, picked with hindsight\n")
    print("From the menu in the script docstring (6 fixed cutoffs, 3 previous-request cutoffs, 8 sample "
          "policies). Eliminated: per request, and combined (deterministic policies: k/N over both requests' "
          "negatives; sample policies: mean of the two medians). Gap = headline − best safe combined, in "
          "percentage points.\n")
    out = []
    for m, _ in SCORE_MODELS:
        for setting, (t1, t2, pooled) in SETTINGS.items():
            pol = menu(data, results, m, setting)
            safe = [p for p in pol if p[1]]
            head = apply(data[m][pooled], cutoff(data[m][pooled], .98))["elim_rate"]
            d = next(p for p in pol if p[0] == "fixed 0.5")
            best = max(safe, key=lambda p: p[4]) if safe else None
            out.append([m, setting, f"{head:.0%}", f"{len(safe)}/{len(pol)}",
                        f"{'safe' if d[1] else 'not safe'} ({d[5]}); {d[4]:.0%}",
                        best[0] if best else "none", f"{best[2]:.0%}, {best[3]:.0%}" if best else "—",
                        f"{best[4]:.0%}" if best else "—", best[5] if best else "—",
                        f"{(head - best[4]) * 100:+.0f}" if best else "—"])
    table(["model", "setting", "headline elim@98", "safe policies", "default 0.5 (combined elim)",
           "best safe policy (hindsight)", "its elim per request", "combined", "detail", "gap (pts)"], out)

    print("## A5c. Every safe policy, per model (roster setting)\n")
    print("Combined eliminated share; policies sorted best first.\n")
    out = []
    for m, _ in SCORE_MODELS:
        pol = sorted((p for p in menu(data, results, m, "roster") if p[1]), key=lambda p: -p[4])
        out.append([m, "; ".join(f"{p[0]} {p[4]:.0%}" for p in pol) or "none"])
    table(["model", "safe policies (roster setting)"], out)
    print("## A5d. Every safe policy, per model (no-roster setting)\n")
    out = []
    for m, _ in SCORE_MODELS:
        pol = sorted((p for p in menu(data, results, m, "no roster") if p[1]), key=lambda p: -p[4])
        out.append([m, "; ".join(f"{p[0]} {p[4]:.0%}" for p in pol) or "none"])
    table(["model", "safe policies (no-roster setting)"], out)

    print("## A5e. A stated fixed-cutoff rule: largest grid value safe on all labeled subsets, minus one step\n")
    print("Cell: misses/positives · eliminated share, on 24-409; 25-3152; 25-3152+R. Both rows are fitted on "
          "these same labels (in-sample); A2d is the out-of-sample check of the same heuristic.\n")
    out = []
    subs = ("24-409", "25-3152", "25-3152+R")
    for m, _ in SCORE_MODELS:
        ok = [c for c in EXT if all(apply(data[m][t], c)["recall"] >= .98 for t in subs)]
        g = max(ok)
        h = EXT[max(EXT.index(g) - 1, 0)]
        cell = lambda c: "; ".join(f"{(e := apply(data[m][t], c))['miss']}/{e['P']} · {e['elim_rate']:.0%}" for t in subs)
        out.append([m, f"{g:g}", cell(g), f"{h:g}", cell(h)])
    table(["model", "largest safe value", "at that value", "one step lower", "at one step lower"], out)
    print(f"Headline vs the one-step-lower cutoff, eliminated share over both requests' negatives (k/{N_NEG}), in-sample:\n")
    out = []
    for m, _ in SCORE_MODELS:
        ok = [c for c in EXT if all(apply(data[m][t], c)["recall"] >= .98 for t in subs)]
        h = EXT[max(EXT.index(max(ok)) - 1, 0)]
        row = [m, f"{h:g}"]
        for pooled in ("pooled", "pooled+R"):
            head = apply(data[m][pooled], cutoff(data[m][pooled], .98))
            e = apply(data[m][pooled], h)
            row += [f"{head['elim']}/{N_NEG} ({head['elim_rate']:.0%})", f"{e['elim']}/{N_NEG} ({e['elim_rate']:.0%})",
                    f"{(head['elim_rate'] - e['elim_rate']) * 100:+.0f}"]
        out.append(row)
    table(["model", "cutoff", "headline (no roster)", "rule (no roster)", "gap, pts", "headline (roster)", "rule (roster)",
           "gap, pts"], out)


if __name__ == "__main__":
    main()
