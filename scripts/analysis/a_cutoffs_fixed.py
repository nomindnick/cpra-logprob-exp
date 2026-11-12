"""A3. Fixed cutoffs that need no labels: 0.5 (the default) and a grid; JSON default verdicts as contrast.

  uv run python scripts/analysis/a_cutoffs_fixed.py

Prints tables A3a (per model, the grid), A3b (one cutoff for both requests), A3c (JSON verdicts) for
docs/analysis/A-cutoffs.md. Stdlib only, deterministic.

Grid: 0.05, 0.1, 0.2, 0.3, 0.4, 0.5 (the specified grid). A3a adds extra rows 0.01 and 0.02 (for models
whose responsive emails can score far below 0.05) and 0.6, 0.7, 0.8 (for runs whose scores sit high).
A3b also scans 0.01 steps from 0.01 to 0.99 to find the largest single cutoff that keeps >= 98% recall
on both requests; that cutoff is chosen with both requests' labels, so it is an in-sample best case, not
a label-free rule. "Fails above" = the lower of the two requests' thr98: any fixed cutoff above it
drops one request below 98% recall.
"""
from a_cutoffs_common import (JSON_MODELS, SCORE_MODELS, SETS, apply, cutoff, fmt_cut, fmt_elim, fmt_miss, load,
                              table)

GRID = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5]
EXTRA = [0.01, 0.02, 0.6, 0.7, 0.8]
FINE = [round(0.01 * i, 2) for i in range(1, 100)]
PAIRINGS = [("24-409", "25-3152"), ("24-409", "25-3152+R")]


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def cell(e):
    s = f"{fmt_miss(e)} · {e['elim_rate']:.0%}"
    return f"**{s}**" if e["recall"] < .98 else s


def main():
    data = load()
    print("# A3. Fixed cutoffs\n")
    print("## A3a. Grid of fixed cutoffs, per model\n")
    print("Cell: misses/positives · share of negatives eliminated. Bold = recall below 98% (more than 2 misses "
          f"on a request, more than 5 pooled). Negatives per subset: 24-409 {NN['24-409']}, 25-3152 {NN['25-3152']}, pooled {N_NEG}.\n")
    for m, _ in SCORE_MODELS:
        print(f"### {m}\n")
        out = []
        for c in sorted(GRID + EXTRA):
            tag = " (default)" if c == 0.5 else " (extra)" if c in EXTRA else ""
            out.append([f"{c:g}{tag}"] + [cell(apply(data[m][s], c)) for s in SETS])
        table(["cutoff"] + SETS, out)

    print("## A3b. One fixed cutoff for both requests\n")
    print("'Largest grid value' = the largest of 0.05–0.5 with ≥ 98% recall on both requests. 'Best 0.01 step' = "
          "the largest multiple of 0.01 with ≥ 98% recall on both (chosen with both requests' labels: in-sample). "
          "Eliminated shown per request as k/N (%).\n")
    out = []
    for m, _ in SCORE_MODELS:
        for a, b in PAIRINGS:
            ok = lambda c: apply(data[m][a], c)["recall"] >= .98 and apply(data[m][b], c)["recall"] >= .98
            g = max((c for c in GRID if ok(c)), default=None)
            f = max((c for c in FINE if ok(c)), default=None)
            row = [m, f"{a} + {b}", fmt_cut(min(cutoff(data[m][a], .98), cutoff(data[m][b], .98)))]
            for c in (g, f):
                if c is None:
                    row += ["none", "—", "—"]
                else:
                    ea, eb = apply(data[m][a], c), apply(data[m][b], c)
                    row += [f"{c:g}", f"{fmt_miss(ea)} · {fmt_elim(ea)}", f"{fmt_miss(eb)} · {fmt_elim(eb)}"]
            out.append(row)
    table(["model", "requests", "fails above", "largest grid value", "24-409 misses · elim", "other misses · elim",
           "best 0.01 step", "24-409 misses · elim", "other misses · elim"], out)

    print("## A3c. Contrast: JSON verdict modes at their default verdict (no cutoff to set)\n")
    jd = load(JSON_MODELS)
    dropped = [f"{t}: {n}" for d in jd.values() for t, n in d["_unscored"].items() if n]
    print(f"Rows with a null score (unparseable JSON) dropped: {sum(n for d in jd.values() for n in d['_unscored'].values())} "
          f"({'; '.join(dropped)}).\n")
    print("Cell: misses/positives · eliminated k/N (%). Bold = recall below 98%. The lp rows at 0.5 (A3a) are the "
          "matching default for the score models.\n")
    out = []
    for m, _ in JSON_MODELS:
        row = [m]
        for s in SETS:
            e = apply(jd[m][s], None, flag=lambda r: bool(r["verdict"]))
            txt = f"{fmt_miss(e)} · {fmt_elim(e)}"
            row.append(f"**{txt}**" if e["recall"] < .98 else txt)
        out.append(row)
    for m, _ in SCORE_MODELS:
        row = [f"{m} @0.5"]
        for s in SETS:
            e = apply(data[m][s], 0.5)
            txt = f"{fmt_miss(e)} · {fmt_elim(e)}"
            row.append(f"**{txt}**" if e["recall"] < .98 else txt)
        out.append(row)
    table(["run"] + SETS, out)


if __name__ == "__main__":
    main()
