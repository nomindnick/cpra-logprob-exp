"""Paired comparison of two scoring runs over the same pairs (e.g. same model, two machines).

  uv run python scripts/compare.py runs/qwen3.5_4b_lat runs/qwen3.5_4b_lat_cpu

Joins on pair_id and reports: run config differences, latency side by side,
per-pair score agreement (|delta| distribution, first-token agreement, rank
correlation), ranking metrics for each run on the shared pairs, and how many
pairs change side of each run's 98%-recall threshold. Stdlib only.
"""
import argparse
import json
import pathlib
import statistics

from analyze import at_recall, auprc, auroc, pr_curve


def load(run):
    rows = [json.loads(l) for l in (run / "scores.jsonl").open()]
    return {r["pair_id"]: r for r in rows if "error" not in r and r.get("score") is not None}


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    rk = [0.0] * len(xs); i = 0
    while i < len(order):
        j = i
        while j < len(order) and xs[order[j]] == xs[order[i]]:
            j += 1
        for k in range(i, j):
            rk[order[k]] = (i + j + 1) / 2
        i = j
    return rk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_a")
    ap.add_argument("run_b")
    a = ap.parse_args()
    runs = [pathlib.Path(a.run_a), pathlib.Path(a.run_b)]
    cfg = [json.load((r / "run.json").open()) for r in runs]
    data = [load(r) for r in runs]
    shared = sorted(set(data[0]) & set(data[1]))
    A = [data[0][p] for p in shared]; B = [data[1][p] for p in shared]
    names = [r.name for r in runs]
    w = max(map(len, names))

    print(f"== {names[0]}  vs  {names[1]}")
    print(f"rows: {len(data[0])} / {len(data[1])}, shared {len(shared)}")
    for k in ("model", "digest", "prompt_hash", "num_ctx", "concurrency", "ollama_version"):
        va, vb = cfg[0].get(k), cfg[1].get(k)
        if va != vb:
            print(f"  config differs: {k}: {va} vs {vb}")

    print("\nlatency (median / p90 over shared pairs)")
    def q(xs, p): xs = sorted(xs); return xs[min(len(xs) - 1, int(p * len(xs)))]
    lat = {}
    for n, rows in zip(names, (A, B)):
        tot = [r["total_ms"] for r in rows]; wall = [r["wall_ms"] for r in rows]
        tps = sum(r["prompt_tokens"] for r in rows) / (sum(r["prefill_ms"] for r in rows) / 1000)
        lat[n] = statistics.median(tot)
        print(f"  {n:{w}}  total {statistics.median(tot):8.0f} / {q(tot, .9):8.0f} ms   "
              f"wall {statistics.median(wall):8.0f} ms   prefill {tps:7.0f} tok/s")
    print(f"  ratio (b/a, median total): {lat[names[1]] / lat[names[0]]:.1f}x")
    tok_diff = sum(ra["prompt_tokens"] != rb["prompt_tokens"] for ra, rb in zip(A, B))
    if tok_diff:
        print(f"  WARNING: prompt_tokens differ on {tok_diff} pairs (prompt/tokenizer mismatch?)")

    print("\nscore agreement")
    d = [abs(ra["score"] - rb["score"]) for ra, rb in zip(A, B)]
    sa = [r["score"] for r in A]; sb = [r["score"] for r in B]
    ra_, rb_ = ranks(sa), ranks(sb)
    mr = (len(shared) + 1) / 2
    cov = sum((x - mr) * (y - mr) for x, y in zip(ra_, rb_))
    spearman = cov / (sum((x - mr) ** 2 for x in ra_) * sum((y - mr) ** 2 for y in rb_)) ** 0.5
    print(f"  |delta| mean {statistics.mean(d):.4f}  median {statistics.median(d):.4f}  max {max(d):.3f}")
    for t in (0.01, 0.05, 0.1, 0.3):
        print(f"  |delta| > {t}: {sum(x > t for x in d)}")
    print(f"  first token agrees: {sum(ra['first_token'] == rb['first_token'] for ra, rb in zip(A, B))}/{len(shared)}")
    print(f"  Spearman rho {spearman:.4f}")
    big = sorted(zip(d, A, B), key=lambda t: -t[0])[:5]
    if big and big[0][0] > 0.1:
        print("  largest moves:")
        for x, ra, rb in big:
            print(f"    {ra['pair_id']}  label {ra['label']}  {ra['score']:.3f} -> {rb['score']:.3f}  "
                  f"({ra['prompt_tokens']} tok{', truncated' if ra['truncated'] else ''})")

    print("\nranking metrics on shared pairs")
    labels = [r["label"] for r in A]
    if sum(labels) in (0, len(labels)):
        print("  skipped: shared pairs are all one class (partial run?)")
        return
    thr = {}
    for n, s in zip(names, (sa, sb)):
        c = pr_curve(s, labels)
        t98 = at_recall(c, 0.98)
        thr[n] = t98[0]
        print(f"  {n:{w}}  AUROC {auroc(s, labels):.4f}  AUPRC {auprc(c):.4f}  "
              f"@98%: thr {t98[0]:.3f} eliminated {t98[3]:.1%}")
    for n in names:
        flips = sum((x >= thr[n]) != (y >= thr[n]) for x, y in zip(sa, sb))
        print(f"  pairs changing side of {n}'s 98% threshold: {flips}")


if __name__ == "__main__":
    main()
