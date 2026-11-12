"""Self-checks for the branch-A scripts (prints PASS lines; raises on any mismatch).

  uv run python scripts/analysis/a_cutoffs_check.py

1. Subset sizes and positive counts match the golden set (data/golden/pairs.jsonl, via golden_counts).
2. Pooled thr98 and elim@98 equal golden_report.stats() on the same rows, and round to the headline
   numbers quoted in the branch brief (52/71/76/54/68/81/63%).
3. cutoff() equals a brute-force scan (highest score s with recall(score >= s) >= target) for every
   model, subset and target 0.98/0.99/1.0.
4. a_cutoffs_sample.simulate() (bisect fast path) equals a slow set-based recomputation of remainder
   recall, misses and eliminated share on every repetition of 12 cells.
5. a_cutoffs_sample.run() is deterministic (two runs with the same reps give identical results).
Stdlib only.
"""
import math

from a_cutoffs_common import SCORE_MODELS, SETS, apply, cutoff, load
from golden_report import stats
import a_cutoffs_sample as S

# elim@98 in the headline table of docs/findings-golden.md §1 (labels of 2026-11-11; before them: 52, 71, 76, 54, 68,
# 81, 63)
HEADLINE = {"4b lp": 53, "9b lp": 72, "27b lp": 77, "d3-4b": 55, "d3-9b": 70, "d3-27b": 83, "Jev": 64}


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def brute_cut(rows, target):
    P = sum(r["label"] for r in rows)
    for s in sorted({r["score"] for r in rows}, reverse=True):
        if sum(r["label"] and r["score"] >= s for r in rows) / P >= target:
            return s


def main():
    data = load()
    for m, _ in SCORE_MODELS:
        d = data[m]
        assert (len(d["24-409"]), len(d["25-3152"]), len(d["25-3152+R"])) == (NR["24-409"], NR["25-3152"], NR["25-3152"]), m
        assert [sum(r["label"] for r in d[s]) for s in ("24-409", "25-3152", "25-3152+R")] == [NP["24-409"], NP["25-3152"], NP["25-3152"]], m
        assert {r["pair_id"] for r in d["25-3152"]} == {r["pair_id"] for r in d["25-3152+R"]}, m
    print("PASS 1 subset sizes and positives")

    for m, _ in SCORE_MODELS:
        rows = data[m]["pooled"]
        st = stats(rows)
        c = cutoff(rows, .98)
        e = apply(rows, c)
        assert c == st["thr98"] and math.isclose(e["elim_rate"], st["e98"]), m
        assert round(100 * e["elim_rate"]) == HEADLINE[m], (m, e["elim_rate"])
    print("PASS 2 pooled thr98 / elim@98 match golden_report.stats and the headline")

    n = 0
    for m, _ in SCORE_MODELS:
        for s in SETS:
            for t in (.98, .99, 1.0):
                assert cutoff(data[m][s], t) == brute_cut(data[m][s], t), (m, s, t)
                n += 1
    print(f"PASS 3 cutoff() == brute force on {n} (model, subset, target) combinations")

    cells = 0
    for m in ("4b lp", "27b lp", "Jev", "d3-27b"):
        for t, design, nn in (("24-409", "as-is", 20), ("25-3152+R", "as-is", 100), ("25-3152", "20%", 50)):
            rows = data[m][t]
            by = {r["pair_id"]: r for r in rows}
            samples = S.draws(t, design, nn, by, 300)
            priors = S.priors_for(data, m, t)
            fast = S.simulate(rows, priors, design, samples, S.RULES_FOR[t])
            for i, (sp, sn) in enumerate(samples):
                sampled = set(sp) | set(sn)
                low = min(by[p]["score"] for p in sp) if sp else None
                for rule in S.RULES_FOR[t]:
                    c = S.cut_for(rule, low, priors)
                    rem_pos = [r for r in rows if r["label"] and r["pair_id"] not in sampled]
                    negs = [r for r in rows if not r["label"] and (design == "20%" or r["pair_id"] not in sampled)]
                    miss = sum(r["score"] < c for r in rem_pos)
                    elim = sum(r["score"] < c for r in negs) / len(negs)
                    rec = (len(rem_pos) - miss) / len(rem_pos)
                    f = fast[rule][i]
                    assert f[1] == miss and math.isclose(f[0], rec) and math.isclose(f[2], elim), (m, t, design, nn, i, rule)
            cells += 1
    print(f"PASS 4 fast simulation == slow recomputation on {cells} cells x 300 repetitions x all rules")

    r1, _ = S.run(data, 50)
    r2, _ = S.run(data, 50)
    assert r1 == r2
    print("PASS 5 run() deterministic")


if __name__ == "__main__":
    main()
