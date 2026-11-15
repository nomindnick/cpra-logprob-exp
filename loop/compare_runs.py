"""Compare looping runs with each other and with an Ollama reference run.

  python3 loop/compare_runs.py loop/runs/qwen3.5_4b_base [more run dirs ...] [--ref runs/golden_qwen3.5_4b_logprob_p2db]

For each run: AUROC, non-responsive eliminated at 98% recall (in-sample cutoff), both overall and per
request, recall / eliminated at 0.5, and median forward time. Labels come from the current
data/golden/pairs.jsonl. With --ref, also how closely the first run's scores track the reference's.
Stdlib only; run from the repository root.
"""
import argparse
import json
import pathlib
import random
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from analyze import at_recall, auroc, pr_curve  # noqa: E402
from compare import ranks  # noqa: E402


def load(run_dir, pairs):
    rows = []
    for l in (pathlib.Path(run_dir) / "scores.jsonl").open():
        r = json.loads(l)
        if r["pair_id"] in pairs and r.get("score") is not None:
            r["label"] = pairs[r["pair_id"]]["label"]
            rows.append(r)
    return rows


def metrics(rows):
    s = [r["score"] for r in rows]; l = [r["label"] for r in rows]
    c = pr_curve(s, l)
    pos = [x for x, y in zip(s, l) if y]; neg = [x for x, y in zip(s, l) if not y]
    return {"n": len(rows), "auroc": auroc(s, l), "e98": at_recall(c, 0.98)[3], "thr98": at_recall(c, 0.98)[0],
            "rec50": sum(x >= 0.5 for x in pos) / len(pos), "elim50": sum(x < 0.5 for x in neg) / len(neg)}


def boot_ci(rows, n_boot, seed=0):
    rng = random.Random(seed)
    pos = [r for r in rows if r["label"]]; neg = [r for r in rows if not r["label"]]
    a, e = [], []
    for _ in range(n_boot):
        samp = rng.choices(pos, k=len(pos)) + rng.choices(neg, k=len(neg))
        m = metrics(samp); a.append(m["auroc"]); e.append(m["e98"])
    a.sort(); e.sort()
    lo, hi = int(0.025 * n_boot), int(0.975 * n_boot) - 1
    return (a[lo], a[hi]), (e[lo], e[hi])


def pearson(x, y):
    mx, my = statistics.fmean(x), statistics.fmean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    return num / (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5


def paired_auroc_diff(rows_a, rows_b, n_boot, seed=0):
    """Bootstrap CI for AUROC(a) - AUROC(b) on the same pairs (resampled together, within class)."""
    b = {r["pair_id"]: r for r in rows_b}
    both = [(r, b[r["pair_id"]]) for r in rows_a if r["pair_id"] in b]
    pos = [t for t in both if t[0]["label"]]; neg = [t for t in both if not t[0]["label"]]
    rng = random.Random(seed); d = []
    for _ in range(n_boot):
        samp = rng.choices(pos, k=len(pos)) + rng.choices(neg, k=len(neg))
        l = [t[0]["label"] for t in samp]
        d.append(auroc([t[0]["score"] for t in samp], l) - auroc([t[1]["score"] for t in samp], l))
    d.sort()
    return d[int(0.025 * n_boot)], d[int(0.975 * n_boot) - 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--ref", help="Ollama run directory to compare the first run against")
    ap.add_argument("--boot", type=int, default=1000)
    a = ap.parse_args()
    pairs = {p["pair_id"]: p for p in map(json.loads, (ROOT / "data/golden/pairs.jsonl").open())}
    reqs = sorted({p["request_id"] for p in pairs.values()})

    loaded = [(pathlib.Path(d).name, load(d, pairs)) for d in a.runs]
    if a.ref:
        loaded.append((pathlib.Path(a.ref).name + " (ref)", load(a.ref, pairs)))
    print("| run | n | layer passes | AUROC [95% CI] | eliminated @98% recall [95% CI] | recall / eliminated at 0.5 | "
          + " | ".join(f"{q}: AUROC · elim@98" for q in reqs) + " | median ms | ms ÷ first run |")
    print("|---|---|---|---|---|---|" + "---|" * len(reqs) + "---|---|")
    base_ms = None
    for (name, rows), d in zip(loaded, a.runs + ([a.ref] if a.ref else [])):
        cfg_p = pathlib.Path(d) / "run.json"
        cfg = json.load(cfg_p.open()) if cfg_p.exists() else {}
        m = metrics(rows); (alo, ahi), (elo, ehi) = boot_ci(rows, a.boot)
        per = []
        for q in reqs:
            mq = metrics([r for r in rows if r["request_id"] == q])
            per.append(f"{mq['auroc']:.3f} · {mq['e98']:.0%}")
        key = "fwd_ms" if rows and "fwd_ms" in rows[0] else "wall_ms"
        ms = statistics.median(r[key] for r in rows)
        if base_ms is None:
            base_ms = ms
        same = key == "fwd_ms"
        print(f"| {name} | {m['n']} | {cfg.get('layers_run', '')} | {m['auroc']:.3f} [{alo:.3f}–{ahi:.3f}] | "
              f"{m['e98']:.0%} [{elo:.0%}–{ehi:.0%}] | {m['rec50']:.0%} / {m['elim50']:.0%} | " + " | ".join(per)
              + f" | {ms:.0f} | {(f'{ms / base_ms:.2f}×' if same else 'n/a (Ollama, prefix cache)')} |")

    first_name, first = loaded[0]
    for name, rows in loaded[1:]:
        o = {r["pair_id"]: r for r in rows}
        both = [(r, o[r["pair_id"]]) for r in first if r["pair_id"] in o]
        x = [t[0]["score"] for t in both]; y = [t[1]["score"] for t in both]
        lo, hi = paired_auroc_diff(first, rows, a.boot)
        flips = sum((p >= 0.5) != (q >= 0.5) for p, q in zip(x, y))
        print(f"\n{first_name} vs {name}: {len(both)} shared pairs; Pearson {pearson(x, y):.3f}, "
              f"Spearman {pearson(ranks(x), ranks(y)):.3f}; mean |Δscore| {statistics.fmean(abs(p - q) for p, q in zip(x, y)):.3f}; "
              f"{flips} decisions differ at 0.5; AUROC difference (first − this) 95% CI [{lo:+.3f}, {hi:+.3f}]")


if __name__ == "__main__":
    main()
