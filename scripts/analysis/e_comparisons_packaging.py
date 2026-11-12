"""E5. Same base, different packaging: stock Qwen (logprob) vs the d3 decision model at each size.

  uv run python scripts/analysis/e_comparisons_packaging.py [--boot 5000]

  Table E5a  what differs between the two runs at each size (from run.json): quantization, runner, batch, cache
  Table E5b  paired bootstrap of d3 − stock: AUROC and elim@98, all pairs / per request / roster set
  Table E5c  by kind and hard-negative recipe: stock vs d3 at each model's own thr98 and at 0.5 (exact McNemar)
  Table E5d  score shift: mean score on responsive and non-responsive pairs; rank agreement (Spearman)
  Table E5e  latency: stock with prefix cache, stock unloaded before every call (p2dbf), d3
  Table E5f  latency by prompt length (stock prompt tokens), medians
  Table E5g  sanity: are the stock cached and stock fresh scores the same?
Bootstrap: stratified by label, paired, seed 808. Stdlib only.
"""
import argparse
import random
import statistics

from e_comparisons_common import (FRESH, RECIPE_SHORT, RECIPES, SCORE, auroc, boot_p, ci, elim98, fp, holm, mcnemar_exact,
                                  resample, rows, runs_by_tag, strata, table, thr98)
from compare import ranks

SIZES = [("4b", "4b lp", "d3-4b", "4b lp fresh"), ("9b", "9b lp", "d3-9b", "9b lp fresh"), ("27b", "27b lp", "d3-27b", None)]
TAG = dict(SCORE + FRESH)
KINDS = ["real_positive", "close_call_positive", "privileged_positive", "exempt_other_positive", "hard_negative_flipped",
         "real_negative", "hard_negative"]


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    m = (len(x) + 1) / 2
    return sum((a - m) * (b - m) for a, b in zip(rx, ry)) / (
        sum((a - m) ** 2 for a in rx) * sum((b - m) ** 2 for b in ry)) ** 0.5


def q(xs, f):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(f * len(xs)))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=5000)
    a = ap.parse_args()
    R = runs_by_tag()
    print("## E5. Stock Qwen vs d3 at each size\n")

    print("Table E5a. What differs between the runs (run.json). Prompt 2 in every run; the d3 runs send the same "
          "instructions through System One's fields instead of a system prompt.\n")
    import json
    body = []
    for name in ["4b lp", "4b lp fresh", "d3-4b", "9b lp", "9b lp fresh", "d3-9b", "27b lp", "d3-27b"]:
        cfg = json.load(open(f"runs/{TAG[name]}/run.json"))
        det = cfg.get("details", {})
        body.append([name, TAG[name], cfg["model"], det.get("parameter_size"), det.get("quantization_level"),
                     det.get("runner"), cfg.get("num_batch") or "default", "yes" if cfg.get("fresh") else "no",
                     cfg.get("ollama_version")])
    table(["label", "run", "model", "params", "quantization", "runner", "num_batch", "unload every call", "Ollama"], body)

    print(f"Table E5b. d3 minus stock, paired bootstrap ({a.boot} resamples, stratified by label, seed 808). "
          f"elim@98 in percentage points. Holm adjusts across all 24 p-values in the table.\n")
    rng = random.Random(808)
    body = []
    for size, st, d3, _ in SIZES:
        for setname, roster, rid in ((f"all {N_ALL}", False, None), ("24-409", False, "24-409"), ("25-3152", False, "25-3152"),
                                     ("25-3152 +roster", True, None)):
            A, B = rows(TAG[st], roster), rows(TAG[d3], roster)
            ids = sorted(p for p in set(A) & set(B) if rid is None or A[p]["request_id"] == rid)
            lab = {p: A[p]["label"] for p in ids}
            pos, neg = strata(ids, lab)
            L = [lab[p] for p in ids]
            sa = [A[p]["score"] for p in ids]; sb = [B[p]["score"] for p in ids]
            da, de = [], []
            for _ in range(a.boot):
                bs = resample(pos, neg, rng); bl = [lab[p] for p in bs]
                x = [A[p]["score"] for p in bs]; y = [B[p]["score"] for p in bs]
                da.append(auroc(y, bl) - auroc(x, bl)); de.append(elim98(y, bl) - elim98(x, bl))
            body.append([size, setname, len(ids), f"{auroc(sa, L):.3f} → {auroc(sb, L):.3f}",
                         f"{auroc(sb, L) - auroc(sa, L):+.3f} [{ci(da)[0]:+.3f}, {ci(da)[1]:+.3f}]", boot_p(da),
                         f"{elim98(sa, L):.1%} → {elim98(sb, L):.1%}",
                         f"{(elim98(sb, L) - elim98(sa, L)) * 100:+.1f} [{ci(de)[0] * 100:+.1f}, {ci(de)[1] * 100:+.1f}]",
                         boot_p(de)])
    adj = holm([r[5] for r in body] + [r[8] for r in body])
    ha, he = adj[:len(body)], adj[len(body):]
    table(["size", "pairs", "n", "AUROC stock → d3", "ΔAUROC [95% CI]", "p", "Holm p (24)", "elim@98 stock → d3",
           "Δelim@98 [95% CI]", "p", "Holm p (24)"],
          [r[:5] + [fp(r[5]), fp(x)] + r[6:8] + [fp(r[8]), fp(y)] for r, x, y in zip(body, ha, he)])

    print(f"Table E5c. By kind and recipe, all {N_ALL} pairs: pairs flagged responsive, stock vs d3. For + groups this is "
          "recall (higher is better); for − groups it is pass-through (lower is better). Each model at its own pooled "
          "thr98, and both at the fixed 0.5 cutoff. Exact McNemar p (unadjusted; 36 rows × 2 cutoffs).\n")
    body = []
    for size, st, d3, _ in SIZES:
        A, B = rows(TAG[st]), rows(TAG[d3])
        ids = sorted(A)
        L = [A[p]["label"] for p in ids]
        ta = thr98([A[p]["score"] for p in ids], L); tb = thr98([B[p]["score"] for p in ids], L)
        groups = [(k, "+" if k.endswith("positive") or k == "hard_negative_flipped" else "−",
                   [p for p in ids if A[p]["kind"] == k]) for k in KINDS]
        groups += [("  hn/" + RECIPE_SHORT[r], "−", [p for p in ids if A[p]["kind"] == "hard_negative" and A[p]["recipe"] == r])
                   for r in RECIPES]
        for g, sign, ps in groups:
            row = [size, g, sign, len(ps)]
            for cut_a, cut_b in ((ta, tb), (0.5, 0.5)):
                fa = [A[p]["score"] >= cut_a for p in ps]; fb = [B[p]["score"] >= cut_b for p in ps]
                b, c, p = mcnemar_exact(fa, fb)
                row += [f"{sum(fa)} vs {sum(fb)}", fp(p)]
            body.append(row)
    table(["size", "group", "label", "n", "@own thr98: stock vs d3", "p", "@0.5: stock vs d3", "p"], body)

    print(f"Table E5d. Score shift and rank agreement (all {N_ALL} pairs).\n")
    body = []
    for size, st, d3, _ in SIZES:
        A, B = rows(TAG[st]), rows(TAG[d3])
        ids = sorted(A)
        m = lambda D, l: statistics.fmean(D[p]["score"] for p in ids if D[p]["label"] == l)
        body.append([size, f"{m(A, 1):.3f} → {m(B, 1):.3f}", f"{m(A, 0):.3f} → {m(B, 0):.3f}",
                     f"{spearman([A[p]['score'] for p in ids], [B[p]['score'] for p in ids]):.3f}",
                     f"{sum((A[p]['score'] >= .5) == (B[p]['score'] >= .5) for p in ids)}/{len(ids)}"])
    table(["size", "mean score, responsive: stock → d3", "mean score, non-responsive: stock → d3", "Spearman ρ",
           "same decision at 0.5"], body)

    print("Table E5e. Latency per email, milliseconds (single stream, Strix Halo). 'stock cached' = the main run "
          "(prefix cache on); 'stock fresh' = the same model unloaded before every call (p2dbf), so nothing is cached: "
          "prefill = Ollama's server-side prompt processing, load = model load, wall = the whole call as the scorer saw "
          "it (includes load); server total = Ollama's server-side total_ms (prefill + 1-token decode, load excluded). d3 reports only wall time. ms/1k tok = median of per-pair wall (or prefill) ÷ prompt tokens.\n")
    body = []
    for roster in (False, True):
        for size, st, d3, fr in SIZES:
            A, B = rows(TAG[st], roster), rows(TAG[d3], roster)
            F = rows(TAG[fr], roster) if fr else None
            ids = sorted(A)
            med = lambda D, f: statistics.median(D[p][f] for p in ids)
            per = lambda D, f: statistics.median(D[p][f] / D[p]["prompt_tokens"] * 1000 for p in ids)
            row = [size + (" +roster" if roster else ""), len(ids), f"{med(A, 'prompt_tokens'):.0f} / {med(B, 'prompt_tokens'):.0f}",
                   f"{med(A, 'wall_ms'):,.0f}", f"{statistics.fmean(A[p]['wall_ms'] for p in ids):,.0f}",
                   f"{statistics.median(A[p]['wall_ms'] - A[p]['total_ms'] for p in ids):.1f}"]
            if F:
                row += [f"{med(F, 'prefill_ms'):,.0f}", f"{statistics.fmean(F[p]['prefill_ms'] for p in ids):,.0f}",
                        f"{med(F, 'total_ms'):,.0f}", f"{med(F, 'load_ms'):,.0f}", f"{med(F, 'wall_ms'):,.0f}",
                        f"{per(F, 'prefill_ms'):.0f}"]
            else:
                row += ["not run"] * 6
            row += [f"{med(B, 'wall_ms'):,.0f}", f"{statistics.fmean(B[p]['wall_ms'] for p in ids):,.0f}", f"{per(B, 'wall_ms'):.0f}"]
            if F:
                r = [B[p]["wall_ms"] / F[p]["prefill_ms"] for p in ids]
                row.append(f"{statistics.median(r):.2f} [{q(r, .25):.2f}–{q(r, .75):.2f}]")
            else:
                row.append("—")
            row.append(f"{statistics.median(B[p]['wall_ms'] / A[p]['wall_ms'] for p in ids):.2f}")
            body.append(row)
    table(["size", "n", "prompt tok stock / d3 (median)", "stock cached: median wall", "mean wall",
           "median wall − server total (client/HTTP overhead)",
           "stock fresh: median prefill", "mean prefill", "median server total (no load)", "median load", "median wall",
           "prefill ms/1k tok",
           "d3: median wall", "mean wall", "wall ms/1k tok", "d3 wall ÷ stock fresh prefill, per pair: median [IQR]",
           "d3 wall ÷ stock cached wall, per pair: median"], body)

    print("Table E5f. Latency by prompt length (bucketed on the stock prompt's token count), main set, medians in ms.\n")
    body = []
    edges = [0, 1000, 2000, 3000, 5000, 10 ** 9]
    for size, st, d3, fr in SIZES:
        A, B = rows(TAG[st]), rows(TAG[d3]); F = rows(TAG[fr]) if fr else None
        for lo, hi in zip(edges, edges[1:]):
            ps = [p for p in A if lo <= A[p]["prompt_tokens"] < hi]
            if not ps:
                continue
            body.append([size, f"{lo:,}–{hi:,}" if hi < 10 ** 9 else f"≥{lo:,}", len(ps),
                         f"{statistics.median(A[p]['wall_ms'] for p in ps):,.0f}",
                         f"{statistics.median(F[p]['prefill_ms'] for p in ps):,.0f}" if F else "not run",
                         f"{statistics.median(B[p]['wall_ms'] for p in ps):,.0f}"])
    table(["size", "stock prompt tokens", "n", "stock cached wall", "stock fresh prefill", "d3 wall"], body)

    print("Table E5g. Sanity check: stock cached vs stock fresh scores for the same pairs (should be near-identical; "
          "only speed should differ).\n")
    body = []
    for size, st, _, fr in SIZES:
        if not fr:
            continue
        for roster in (False, True):
            A, F = rows(TAG[st], roster), rows(TAG[fr], roster)
            ids = sorted(set(A) & set(F))
            d = [abs(A[p]["score"] - F[p]["score"]) for p in ids]
            L = [A[p]["label"] for p in ids]
            body.append([size + (" +roster" if roster else ""), len(ids), f"{max(d):.4f}", f"{statistics.fmean(d):.5f}",
                         f"{auroc([A[p]['score'] for p in ids], L):.3f} / {auroc([F[p]['score'] for p in ids], L):.3f}",
                         f"{elim98([A[p]['score'] for p in ids], L):.1%} / {elim98([F[p]['score'] for p in ids], L):.1%}"])
    table(["size", "pairs", "max |Δscore|", "mean |Δscore|", "AUROC cached / fresh", "elim@98 cached / fresh"], body)


if __name__ == "__main__":
    main()
