"""Branch B1 (and the timing half of B4): machine time per 10,000 emails, from the saved runs.

  uv run python scripts/analysis/b_workload_time.py

Prints:
  B1.1  wall time per call (mean, median, p90) and hours per 10,000 emails, main set (all pairs)
  B1.2  the same for the roster runs (249 pairs of 25-3152, roster appended to the request)
  B1.3  prefix-cache check: what appending the 1,3xx-token roster to the request costs per call, by config
  B1.4  4b/9b JSON runs (batch 8192) vs the lp runs (default batch): prefill re-done on every call
  B1.5  Jev input tokens and cost per 10,000
  B1.6  how wall time grows with prompt length (least-squares slope), for scaling to longer emails
  B1.7  warm-up artifact: effect of the first row on each run's mean
  B1.8  stock Qwen lp vs d3 of the same size: hours per 10,000 and the ratio

Single-stream throughout: one call at a time, as the runs were made. Hours per 10,000 = mean wall_ms
x 10,000 / 3,600,000. Bootstrap CIs for the mean: 1,000 resamples within each label, seed SEED. Stdlib only.
"""
import random
import statistics

from b_workload_common import (CONFIGS, JEV_USD_PER_MTOK, N_BOOT, N_HITS, SEED, ci, load, mean, n0, p90,
                               table)

H = N_HITS / 3_600_000  # ms per call -> hours per 10,000 calls


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def mean_ci(rows, field, rng):
    pos = [r[field] for r in rows if r["label"]]
    neg = [r[field] for r in rows if not r["label"]]
    ms = []
    for _ in range(N_BOOT):
        b = rng.choices(pos, k=len(pos)) + rng.choices(neg, k=len(neg))
        ms.append(sum(b) / len(b))
    return ci(ms)


def slope(rows):
    """Least-squares fit wall_ms = a + b * prompt_tokens; returns (a, b, Pearson r)."""
    x = [r["prompt_tokens"] for r in rows]; y = [r["wall_ms"] for r in rows]
    mx, my = mean(x), mean(y)
    b = sum((u - mx) * (v - my) for u, v in zip(x, y)) / sum((u - mx) ** 2 for u in x)
    return my - b * mx, b, statistics.correlation(x, y)


def time_table(runs, rng, label):
    out = []
    for name, _, fam, tier in CONFIGS:
        rows = runs[name]
        w = [r["wall_ms"] for r in rows]
        lo, hi = mean_ci(rows, "wall_ms", rng)
        trunc = sum(bool(r["truncated"]) for r in rows)
        out.append([name, tier, len(rows), n0(mean(w)), n0(statistics.median(w)), n0(p90(w)),
                    n0(mean(r["prompt_tokens"] for r in rows)), f"{trunc}/{len(rows)}",
                    f"{mean(w) * H:.2f} [{lo * H:.2f}–{hi * H:.2f}]"])
    print(f"### {label}\n")
    table(["config", "tier", "n", "mean wall ms", "median", "p90", "mean prompt tok", "body truncated",
           "hours / 10,000 (mean) [95% CI]"], out)


def main():
    main_runs, roster_runs, dropped = load()
    rng = random.Random(SEED)
    print("# Branch B1: machine time\n")
    print("Rows without a score (JSON parse failures), dropped everywhere: "
          + ", ".join(f"{t} {k} of {n}" for t, k, n in dropped) + f"; total {sum(k for _, k, _ in dropped)}\n")

    time_table(main_runs, rng, f"B1.1 Main set ({N_ALL} pairs, both requests)")
    time_table(roster_runs, rng, "B1.2 Roster set (249 pairs of 25-3152, roster appended to the request)")

    # ---- B1.3 prefix cache: same 249 pairs with and without the roster ----
    print("### B1.3 Prefix-cache check: cost of appending the roster to the request (same 249 pairs)\n")
    print("Δ = with-roster minus without-roster for the same pair. 'Prefill' is Ollama's server-side prompt "
          "processing time (absent for the System One endpoints). Every row in a run is scored in "
          "(request, email) order, so in a cached run each call can reuse the processed system prompt + "
          "request from the call before it. 'Expected if reprocessed' = tokens added × the run's own per-token "
          "slope b from B1.6: what the roster would cost per call if every added token were processed every call.\n")
    out = []
    for name, _, fam, tier in CONFIGS:
        A = {r["pair_id"]: r for r in main_runs[name] if r["request_id"] == "25-3152"}
        B = {r["pair_id"]: r for r in roster_runs[name]}
        ids = sorted(set(A) & set(B))
        dtok = [B[p]["prompt_tokens"] - A[p]["prompt_tokens"] for p in ids]
        dwall = [B[p]["wall_ms"] - A[p]["wall_ms"] for p in ids]
        has_pf = all("prefill_ms" in A[p] and "prefill_ms" in B[p] for p in ids)
        dpf = [B[p]["prefill_ms"] - A[p]["prefill_ms"] for p in ids] if has_pf else None
        _, b, _ = slope(main_runs[name])
        out.append([name, len(ids), f"{min(dtok)}–{max(dtok)}", f"{mean(dtok) * b:+,.0f}",
                    n0(mean(A[p]["wall_ms"] for p in ids)), n0(mean(B[p]["wall_ms"] for p in ids)),
                    f"{mean(dwall):+,.0f}", f"{statistics.median(dwall):+,.0f}",
                    f"{statistics.median(dpf):+,.0f}" if dpf else "—",
                    f"{mean(dwall) * H:+.2f}"])
    table(["config", "pairs", "tokens added by roster", "expected Δ ms if reprocessed", "mean wall ms without",
           "with", "mean Δwall ms",
           "median Δwall ms", "median Δprefill ms", "Δ hours / 10,000"], out)

    # ---- B1.4 JSON at batch 8192 vs lp at default batch, same model and email ----
    print(f"### B1.4 Prefill per call, JSON vs lp runs of the same model (same {N_ALL} pairs)\n")
    print("The 4b/9b JSON runs used num_batch 8192 (the older workaround, which also disables reuse of the "
          "request prefix); the lp runs and the 27b JSON runs used the default batch. Δ = JSON prefill − lp "
          "prefill for the same pair (the JSON system prompt is ~25 tokens longer).\n")
    out = []
    for js, lp in (("4b json", "4b lp"), ("4b jsonR", "4b lp"), ("9b json", "9b lp"), ("9b jsonR", "9b lp"),
                   ("27b json", "27b lp"), ("27b jsonR", "27b lp")):
        J = {r["pair_id"]: r for r in main_runs[js]}; L = {r["pair_id"]: r for r in main_runs[lp]}
        ids = sorted(set(J) & set(L))
        d = [J[p]["prefill_ms"] - L[p]["prefill_ms"] for p in ids]
        dec = [J[p]["decode_ms"] for p in ids]
        out.append([js, lp, len(ids), n0(statistics.median(L[p]["prefill_ms"] for p in ids)),
                    n0(statistics.median(J[p]["prefill_ms"] for p in ids)), f"{statistics.median(d):+,.0f}",
                    f"{mean(d):+,.0f}", f"{mean(d) * H:+.2f}", n0(mean(dec)), f"{mean(dec) * H:.2f}"])
    table(["JSON run", "lp run", "pairs", "lp median prefill ms", "JSON median prefill ms", "median Δprefill ms",
           "mean Δprefill ms", "Δprefill hours / 10,000", "JSON mean decode ms", "decode hours / 10,000"], out)

    # ---- B1.5 Jev cost ----
    print("### B1.5 Jev: billed input tokens and cost per 10,000 calls\n")
    print(f"Price: ${JEV_USD_PER_MTOK} per million input tokens, the only price given for this analysis; Jev also reports "
          "20 output tokens per call, whose price, if any, isn't recorded in the repo [corrected in verification]. "
          "Tokens are the API's own usage.input_tokens, saved as prompt_tokens.\n")
    out = []
    for label, runs in ((f"main set ({N_ALL})", main_runs), ("roster set (249)", roster_runs)):
        rows = runs["Jev"]
        tok = [r["prompt_tokens"] for r in rows]
        out.append([label, len(rows), n0(sum(tok)), n0(mean(tok)), n0(max(tok)),
                    f"${sum(tok) / 1e6 * JEV_USD_PER_MTOK:.4f}",
                    f"${mean(tok) * N_HITS / 1e6 * JEV_USD_PER_MTOK:.2f}"])
    table(["set", "calls", "input tokens, total", "mean per call", "max", "cost of this run", "cost per 10,000"], out)

    # ---- B1.6 slope ----
    print("### B1.6 Wall time vs prompt length (least squares, main set)\n")
    print("wall_ms ≈ a + b × prompt_tokens. For the cached runs (lp, 27b JSON) most of the request prefix is "
          "reused, so b is close to the cost of an extra email token; for d3 and the batch-8192 JSON runs every "
          "token is processed. Email bodies are capped at 8,000 characters, so prompt length is bounded.\n")
    out = []
    for name, _, _, _ in CONFIGS:
        rows = main_runs[name]
        x = [r["prompt_tokens"] for r in rows]
        a, b, r = slope(rows)
        out.append([name, f"{min(x):,}–{max(x):,}", f"{a:+,.0f}", f"{b * 1000:,.0f}", f"{r:.2f}",
                    f"{b * 1000 * H:.2f}"])
    table(["config", "prompt tokens range", "a (ms)", "b (ms per +1,000 tokens)", "Pearson r",
           "+hours / 10,000 per +1,000 mean tokens"], out)

    # ---- B1.7 warm-up row ----
    print("### B1.7 First row of each run\n")
    print("Each local run made an untimed warm-up call on its first pair before timing began (the lp runs two: a "
          "warm-up and a canary reference; they also re-scored that pair after every 100 rows, overlapping the next "
          "timed row, see the Verification section) [corrected in verification]. For the cached runs the "
          "first timed row reuses that whole prompt and is unrealistically fast. Effect on the mean:\n")
    out = []
    for name, _, _, _ in CONFIGS:
        for label, runs in (("main", main_runs), ("roster", roster_runs)):
            rows = runs[name]
            w = [r["wall_ms"] for r in rows]
            out.append([name, label, n0(w[0]), n0(mean(w)), n0(mean(w[1:])), f"{mean(w[1:]) - mean(w):+.1f}"])
    table(["config", "set", "first row wall ms", "mean", "mean without first row", "Δ mean ms"], out)

    # ---- B1.8 same-size lp vs d3 ----
    print("### B1.8 Stock Qwen lp vs d3 at the same size: machine hours per 10,000\n")
    print("At least four differences between the pairs: d3 can't reuse the request prefix (B1.3); the d3 models are "
          "Q8_0 while the stock Qwen models are Q4_K_M; the d3 runs used num_batch 8192 (the lp runs the default); and "
          "d3 runs on Ollama's llamacpp runner through /v1/systemone, the lp runs on the ggml runner through /api/chat "
          "[corrected in verification]. These runs don't separate them.\n")
    out = []
    for lp, d3 in (("4b lp", "d3-4b"), ("9b lp", "d3-9b"), ("27b lp", "d3-27b")):
        row = [f"{lp} vs {d3}"]
        for runs in (main_runs, roster_runs):
            hl, hd = mean(r["wall_ms"] for r in runs[lp]) * H, mean(r["wall_ms"] for r in runs[d3]) * H
            row += [f"{hl:.2f}", f"{hd:.2f}", f"{hd / hl:.2f}×"]
        _, bl, _ = slope(main_runs[lp]); _, bd, _ = slope(main_runs[d3])
        row.append(f"{bd / bl:.2f}×")
        out.append(row)
    table(["pair", "main: lp h", "main: d3 h", "main: d3 / lp", "roster: lp h", "roster: d3 h", "roster: d3 / lp",
           "per-token slope b, d3 / lp"], out)


if __name__ == "__main__":
    main()
