"""Table for a layer-looping sweep: every block against the stock layer order, per request.

  python3 loop/sweep_report.py [--name sweep4b] [--boot 2000]

Per request directory under loop/runs/<name>/: one row per finished run, with AUROC, its paired
difference from the stock order on the same pairs (bootstrap CI, resampled within class), elimination
at 98% recall, recall / eliminated at 0.5, how many pairs got no yes/no answer (neither in the top 20
tokens), and total forward time relative to the stock order. A pair with no answer counts as score 1.0
(it cannot be eliminated), as in loop/sweep.py. "AUROC, whole vocab" ranks pairs by log P(yes) - log P(no)
over the whole vocabulary instead, which is defined even when the model no longer answers.
Unfinished runs are marked. Stdlib only.
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "loop"))
from compare_runs import boot_ci, metrics, paired_auroc_diff  # noqa: E402  (puts scripts/ on the path)
from analyze import auroc  # noqa: E402


def load(run_dir, pairs):
    rows = []
    p = pathlib.Path(run_dir) / "scores.jsonl"
    for l in (p.open() if p.exists() else []):
        r = json.loads(l)
        r["label"] = pairs[r["pair_id"]]["label"]
        r["answered"] = r["score"] is not None
        if not r["answered"]:
            r["score"] = 1.0
        rows.append(r)
    return rows


def vocab_auroc(rows):
    ok = [r for r in rows if r.get("lp_yes") is not None and r.get("lp_no") is not None]
    if len(ok) < len(rows) or not rows:
        return None
    return auroc([r["lp_yes"] - r["lp_no"] for r in ok], [r["label"] for r in ok])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="sweep4b")
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args()
    pairs = {p["pair_id"]: p for p in map(json.loads, (ROOT / "data/golden/pairs.jsonl").open())}
    base_dir = ROOT / "loop/runs" / a.name
    sel_p = base_dir / "selection.json"
    sel = json.load(sel_p.open()) if sel_p.exists() else {}
    selected, confirm = sel.get("selected", []), sel.get("confirm", [])
    by_req = {}
    for req_dir in sorted(p for p in base_dir.iterdir() if p.is_dir()):
        q = req_dir.name
        n_q = sum(p["request_id"] == q for p in pairs.values())
        runs = {}
        for d in sorted(req_dir.iterdir()):
            cfg = json.load((d / "run.json").open())
            rows = load(d, pairs)
            runs[d.name] = {"cfg": cfg, "raw": rows, "rows": rows, "done": len(rows) == n_q}
        by_req[q] = runs
        stock = runs.get("base_start")
        if not stock or not stock["done"]:
            print(f"\n## {q}: stock pass not finished yet")
            continue
        t_stock = sum(r["fwd_ms"] for r in stock["raw"])
        m0 = metrics(stock["rows"])
        print(f"\n## request {q} ({n_q} pairs; stock order: AUROC {m0['auroc']:.4f}, eliminated @98% recall {m0['e98']:.0%}, "
              f"recall / eliminated at 0.5 {m0['rec50']:.0%} / {m0['elim50']:.0%}, {t_stock / 60000:.1f} min)\n")
        print("| block repeated | layer passes | AUROC | Δ vs stock [95% CI] | elim @98% | recall / elim at 0.5 | "
              "no yes/no answer | AUROC, whole vocab | time ÷ stock |")
        print("|---|---|---|---|---|---|---|---|---|")

        def key(item):
            name, r = item
            return (name.startswith("base"), -(metrics(r["rows"])["auroc"] if r["done"] and r["rows"] else 0))
        for name, r in sorted(runs.items(), key=key):
            cfg = r["cfg"]
            label = (cfg["repeat"] or "stock") + (" (end of session)" if name == "base_end" else "") \
                + (" ★" if cfg["repeat"] in selected else "") + (" ◆" if cfg["repeat"] in confirm else "")
            if not r["done"]:
                print(f"| {label} | {cfg['layers_run']} | running: {len(r['raw'])}/{n_q} | | | | | | |")
                continue
            m = metrics(r["rows"])
            lo, hi = paired_auroc_diff(r["rows"], stock["rows"], a.boot)
            lost = sum(not x["answered"] for x in r["raw"])
            t = sum(x["fwd_ms"] for x in r["raw"])
            va = vocab_auroc(r["rows"])
            print(f"| {label} | {cfg['layers_run']} | {m['auroc']:.4f} | {m['auroc'] - m0['auroc']:+.4f} [{lo:+.3f}, {hi:+.3f}] | "
                  f"{m['e98']:.0%} | {m['rec50']:.0%} / {m['elim50']:.0%} | {lost} | {'' if va is None else f'{va:.4f}'} | "
                  f"{t / t_stock:.3f}× |")
    if selected:
        print(f"\n★ = chosen for validation by the rule fixed before the sweep: {sel['rule']}")
    if confirm:
        print("◆ = block fixed before the sweep started, scored on both requests whatever its search rank")
        print("\n## blocks fixed in advance, both requests together\n")
        print("| layer order | pairs | AUROC [95% CI] | Δ vs stock [95% CI] | elim @98% [95% CI] | recall / elim at 0.5 | time ÷ stock |")
        print("|---|---|---|---|---|---|---|")

        def pooled(name):
            got = [by_req[q][name] for q in sorted(by_req) if name in by_req[q] and by_req[q][name]["done"]]
            return [r for g in got for r in g["rows"]] if len(got) == len(by_req) == 2 else None
        stock = pooled("base_start")
        for rep in [None] + confirm:
            rows = pooled("r" + rep.replace(":", "-") if rep else "base_start")
            if not stock or not rows:
                print(f"| {rep or 'stock'} | not finished | | | | | |")
                continue
            m = metrics(rows); (alo, ahi), (elo, ehi) = boot_ci(rows, a.boot)
            d = "" if rep is None else "{:+.4f} [{:+.3f}, {:+.3f}]".format(
                m["auroc"] - metrics(stock)["auroc"], *paired_auroc_diff(rows, stock, a.boot))
            t = sum(r["fwd_ms"] for r in rows) / sum(r["fwd_ms"] for r in stock)
            print(f"| {rep or 'stock'} | {m['n']} | {m['auroc']:.4f} [{alo:.3f}, {ahi:.3f}] | {d} | "
                  f"{m['e98']:.0%} [{elo:.0%}, {ehi:.0%}] | {m['rec50']:.0%} / {m['elim50']:.0%} | {t:.3f}× |")


if __name__ == "__main__":
    main()
