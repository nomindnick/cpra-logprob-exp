"""E3. Speed/accuracy frontier: wall time per email vs elim@98 and AUROC, for every configuration.

  uv run python scripts/analysis/e_comparisons_frontier.py [--boot 2000]

Configurations: the seven score models and the six JSON verdict modes.
  Table E3a  main set (all pairs): median / mean / p90 wall ms, AUROC, elim@98, Pareto flags
  Table E3b  25-3152 only (249 pairs): each configuration without the roster (rows of the main runs) and with it
  Table E3c  bootstrap frequency of being on the local Pareto frontier (main and 25-3152 sets)
  Table E3d  where Jev sits: the local configurations at least as accurate on both metrics, and how much slower
Pareto: a configuration is on the frontier if no other configuration is at least as fast AND at least as
accurate, and strictly better on one of the two. "Local" excludes Jev (the only hosted option); Jev's
wall time includes the network round trip. Bootstrap: stratified by label, paired, seed 404 (main) / 505 (25-3152).
Stdlib only.
"""
import argparse
import random
import statistics

from e_comparisons_common import JSON, SCORE, auroc, elim98, resample, rows, runs_by_tag, strata, table

CONFIGS = SCORE + JSON


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def setting(tag, roster):
    r = runs_by_tag()[tag + ("_roster" if roster else "")]
    if r["machine"] == "api":
        return "hosted API"
    if r["mode"] == "noul":
        return "d3, no prefix reuse"
    return "prefix cache" if not r["bigbatch"] and not r["fresh"] else "batch 8192, no prefix cache"


def measures(d, ids):
    ids = [p for p in ids if p in d]
    s = [d[p]["score"] for p in ids]; l = [d[p]["label"] for p in ids]; w = [d[p]["wall_ms"] for p in ids]
    dec = [d[p]["decode_ms"] for p in ids if d[p].get("decode_ms") is not None]
    return {"n": len(ids), "med": statistics.median(w), "mean": statistics.fmean(w),
            "dec": statistics.median(dec) if dec else None,
            "p90": sorted(w)[int(.9 * len(w))], "auroc": auroc(s, l), "elim": elim98(s, l)}


def frontier(items, lat, acc):
    """Names of non-dominated items (lower lat better, higher acc better)."""
    out = set()
    for x in items:
        dom = any((y[lat] <= x[lat] and y[acc] >= x[acc]) and (y[lat] < x[lat] or y[acc] > x[acc])
                  for y in items if y is not x)
        if not dom:
            out.add(x["name"])
    return out


def flags(items, it):
    loc = [x for x in items if not x["jev"]]
    marks = []
    for lat, acc, lab in (("med", "elim", "med×elim"), ("med", "auroc", "med×AUROC"), ("mean", "elim", "mean×elim")):
        f_loc = frontier(loc, lat, acc); f_all = frontier(items, lat, acc)
        if it["name"] in f_loc or it["name"] in f_all:
            marks.append(lab + ("" if it["jev"] else " (local)" if it["name"] not in f_all else ""))
    return ", ".join(marks) or "—"


def print_items(items, title):
    print(title)
    jev = min((x for x in items if x["jev"]), key=lambda x: x["med"])
    table(["configuration", "setting", "n", "median wall ms", "× Jev (median)", "mean wall ms", "p90 wall ms",
           "median decode ms", "AUROC", "elim@98", "on frontier (median or mean wall × elim@98 or AUROC)"],
          [[x["name"], x["setting"], x["n"], f"{x['med']:,.0f}", f"{x['med'] / jev['med']:.1f}", f"{x['mean']:,.0f}",
            f"{x['p90']:,.0f}", "—" if x["dec"] is None else f"{x['dec']:,.0f}", f"{x['auroc']:.3f}",
            f"{x['elim']:.1%}", flags(items, x)] for x in sorted(items, key=lambda x: x["med"])])
    loc = [x for x in items if not x["jev"]]
    for lat, acc in (("med", "elim"), ("med", "auroc"), ("mean", "elim")):
        f = sorted((x for x in loc if x["name"] in frontier(loc, lat, acc)), key=lambda x: x[lat])
        print(f"- Local frontier, {'median' if lat == 'med' else 'mean'} wall × {'elim@98' if acc == 'elim' else 'AUROC'}: "
              + " → ".join(f"{x['name']} ({x[lat]:,.0f} ms, {x[acc]:.1%})" if acc == "elim" else
                           f"{x['name']} ({x[lat]:,.0f} ms, {x[acc]:.3f})" for x in f))
        print("  - steps: " + "; ".join(
            f"{x['name']} → {y['name']}: +{y[lat] - x[lat]:,.0f} ms ({y[lat] / x[lat]:.1f}×) for "
            + (f"{(y[acc] - x[acc]) * 100:+.1f} points" if acc == "elim" else f"{y[acc] - x[acc]:+.3f} AUROC")
            for x, y in zip(f, f[1:])))
    print()


def boot_frontier(cfgs, ids, B, seed):
    lab = {}
    for _, d, _ in cfgs:
        for p in ids:
            if p in d:
                lab[p] = d[p]["label"]
    pos, neg = strata([p for p in ids if p in lab], lab)
    rng = random.Random(seed)
    cnt = {n: {"med×elim": 0, "med×AUROC": 0} for n, _, _ in cfgs}
    for _ in range(B):
        bs = resample(pos, neg, rng)
        items = []
        for n, d, jev in cfgs:
            if jev:
                continue
            ps = [p for p in bs if p in d]
            s = [d[p]["score"] for p in ps]; l = [d[p]["label"] for p in ps]
            items.append({"name": n, "med": statistics.median(d[p]["wall_ms"] for p in ps),
                          "elim": elim98(s, l), "auroc": auroc(s, l)})
        for f, acc in (("med×elim", "elim"), ("med×AUROC", "auroc")):
            for n in frontier(items, "med", acc):
                cnt[n][f] += 1
    return cnt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args()
    print("## E3. Speed/accuracy frontier\n")
    allids = sorted(rows(SCORE[0][1]))
    main_items, main_cfgs = [], []
    for n, t in CONFIGS:
        d = rows(t)
        main_items.append({"name": n, "setting": setting(t, False), "jev": n == "Jev", **measures(d, allids)})
        main_cfgs.append((n, d, n == "Jev"))
    print_items(main_items, f"Table E3a. Main set ({N_ALL} pairs; JSON runs drop their unscored rows). Sorted by median wall "
                            "time. Frontier flags: 'med×elim' = on the Pareto frontier of median wall ms vs elim@98, "
                            "etc.; '(local)' = on the frontier only once Jev is set aside. Decode = Ollama's server-side time "
                            "generating output tokens (1 token for lp; d3 and Jev report none). × Jev = median wall ÷ the fastest Jev "
                            "run's median wall in the same table.\n")

    sub = sorted(rows(SCORE[0][1], roster=True))
    r_items, r_cfgs = [], []
    for n, t in CONFIGS:
        for ro in (False, True):
            d = rows(t, roster=ro)
            nm = n + (" +roster" if ro else "")
            r_items.append({"name": nm, "setting": setting(t, ro), "jev": n == "Jev", **measures(d, sub)})
            r_cfgs.append((nm, d, n == "Jev"))
    print_items(r_items, "Table E3b. 25-3152 only (249 pairs): each configuration without the roster (its main-run "
                         "rows for these pairs) and with it.\n")

    print(f"Table E3c. Share of {a.boot} paired bootstrap resamples in which each local configuration is on the local "
          f"frontier (median wall ms vs elim@98, and vs AUROC). Latency is resampled with the same pairs.\n")
    cm = boot_frontier(main_cfgs, allids, a.boot, 404)
    cr = boot_frontier(r_cfgs, sub, a.boot, 505)
    body = []
    for n, _, jev in main_cfgs:
        if jev:
            continue
        body.append(["main", n, f"{cm[n]['med×elim'] / a.boot:.0%}", f"{cm[n]['med×AUROC'] / a.boot:.0%}"])
    for n, _, jev in r_cfgs:
        if jev or (cr[n]["med×elim"] == 0 and cr[n]["med×AUROC"] == 0):
            continue
        body.append(["25-3152", n, f"{cr[n]['med×elim'] / a.boot:.0%}", f"{cr[n]['med×AUROC'] / a.boot:.0%}"])
    table(["set", "configuration", "on frontier: median wall × elim@98", "on frontier: median wall × AUROC"], body)
    print("(25-3152 rows that were never on the frontier are left out.)\n")

    print("Table E3d. Jev against the local configurations that are at least as good on both AUROC and elim@98 "
          "(point estimates; E1 says which of these gaps are distinguishable from noise).\n")
    body = []
    for items, setname in ((main_items, "main"), (r_items, "25-3152")):
        for jv in [x for x in items if x["jev"]]:
            for x in sorted(items, key=lambda x: x["med"]):
                if x["jev"] or not (x["elim"] >= jv["elim"] and x["auroc"] >= jv["auroc"]):
                    continue
                if setname == "25-3152" and (" +roster" in x["name"]) != (" +roster" in jv["name"]):
                    continue
                body.append([setname, jv["name"], x["name"], f"{(x['auroc'] - jv['auroc']):+.3f}",
                             f"{(x['elim'] - jv['elim']) * 100:+.1f}", f"{x['med'] / jv['med']:.1f}×",
                             f"{x['mean'] / jv['mean']:.1f}×"])
    table(["set", "Jev run", "local configuration", "ΔAUROC vs Jev", "Δelim@98 vs Jev (points)",
           "median wall vs Jev", "mean wall vs Jev"], body)


if __name__ == "__main__":
    main()
