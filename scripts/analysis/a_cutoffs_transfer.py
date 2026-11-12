"""A2. Transfer: choose the cutoff on one request, apply it to the other.

  uv run python scripts/analysis/a_cutoffs_transfer.py

Prints tables A2a (one block per direction), A2b (summary), A2c (count of passing directions) and
A2d (grid heuristic) for docs/analysis/A-cutoffs.md.
Stdlib only, deterministic (no resampling).

Source cutoffs: the highest cutoff with recall >= 98%, >= 99% and 100% on the source request (the 99% and
100% versions are safety margins: on about 140-150 positives they allow 1 and 0 source misses). The cutoff is
applied unchanged to the target request's scores. "Oracle elim@98" is what the target's own thr98 would
have eliminated (the in-sample number the transfer is trying to match).

A2d tests a grid heuristic out of sample: on the source request take the largest value of the grid
0.01, 0.02, 0.05, 0.1, 0.2, ..., 0.8 that keeps >= 98% recall there, step down 0, 1 or 2 grid values for
headroom, and apply that cutoff to the target.
"""
from a_cutoffs_common import (SCORE_MODELS, allowed_misses, apply, cutoff, fmt_cut, fmt_elim, fmt_miss, load,
                              table)

DIRECTIONS = [("24-409", "25-3152"), ("25-3152", "24-409"), ("24-409", "25-3152+R"), ("25-3152+R", "24-409")]
LEVELS = [(.98, "98%"), (.99, "99%"), (1.0, "100%")]
GRID = [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]


def transfer(data, m, src, tgt, level):
    c = cutoff(data[m][src], level)
    return c, apply(data[m][tgt], c), apply(data[m][tgt], cutoff(data[m][tgt], .98))


def main():
    data = load()
    print("# A2. Transfer of cutoffs between requests\n")
    for src, tgt in DIRECTIONS:
        P = sum(r["label"] for r in data["4b lp"][tgt])
        print(f"## A2a. {src} → {tgt} (target: {P} positives; 98% recall allows {allowed_misses(P)} misses)\n")
        out = []
        for m, _ in SCORE_MODELS:
            for level, name in LEVELS:
                c, e, o = transfer(data, m, src, tgt, level)
                real = sum(r["kind"] == "real_positive" for r in e["missed"])
                out.append([m, name, fmt_cut(c), f"{fmt_miss(e)} ({e['recall']:.1%})", real,
                            "yes" if e["recall"] >= .98 else "**no**", fmt_elim(e), fmt_elim(o)])
        table(["model", "source recall level", "cutoff", "target misses (recall)", "of which real emails",
               "≥98% on target?", "target eliminated", "oracle elim@98 on target"], out)

    print("## A2b. Summary at the 98% source level and the 100% (safety-margin) level\n")
    print("Each cell: target misses / target eliminated share. Bold = target recall below 98%.\n")
    out = []
    for m, _ in SCORE_MODELS:
        row = [m]
        for level in (.98, 1.0):
            for src, tgt in DIRECTIONS:
                _, e, _ = transfer(data, m, src, tgt, level)
                cell = f"{e['miss']} / {e['elim_rate']:.0%}"
                row.append(f"**{cell}**" if e["recall"] < .98 else cell)
        out.append(row)
    table(["model"] + [f"{lv}: {s} → {t}" for lv in ("98%", "100%") for s, t in DIRECTIONS], out)

    print("## A2c. Count of directions (of 4) where the transferred cutoff keeps ≥ 98% recall on the target\n")
    out = []
    for m, _ in SCORE_MODELS:
        row = [m]
        for level, _ in LEVELS:
            ok = sum(transfer(data, m, s, t, level)[1]["recall"] >= .98 for s, t in DIRECTIONS)
            row.append(f"{ok}/4")
        out.append(row)
    table(["model"] + [f"source level {n}" for _, n in LEVELS], out)

    print("## A2d. Grid heuristic out of sample: largest grid value safe on the source, minus 0/1/2 steps\n")
    print("Cell: cutoff → target misses / target eliminated share. Bold = target recall below 98%.\n")
    start = lambda m, src: max(j for j, c in enumerate(GRID) if apply(data[m][src], c)["recall"] >= .98)
    out = []
    for m, _ in SCORE_MODELS:
        row = [m]
        for src, tgt in DIRECTIONS:
            cells = []
            for step in (0, 1, 2):
                c = GRID[max(start(m, src) - step, 0)]
                e = apply(data[m][tgt], c)
                txt = f"{c:g} → {e['miss']} / {e['elim_rate']:.0%}"
                cells.append(f"**{txt}**" if e["recall"] < .98 else txt)
            row.append("; ".join(cells))
        out.append(row)
    table(["model"] + [f"{s} → {t} (−0; −1; −2 steps)" for s, t in DIRECTIONS], out)
    out = []
    for m, _ in SCORE_MODELS:
        row = [m]
        for step in (0, 1, 2):
            ok = sum(apply(data[m][tgt], GRID[max(start(m, src) - step, 0)])["recall"] >= .98 for src, tgt in DIRECTIONS)
            row.append(f"{ok}/4")
        out.append(row)
    table(["model", "−0 steps: directions ≥ 98%", "−1 step", "−2 steps"], out)


if __name__ == "__main__":
    main()
