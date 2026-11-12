"""Branch B verification (skeptic pass): independent recomputation of the workload numbers in
docs/analysis/B-workload.md.

  uv run python scripts/analysis/b_workload_verify.py

Does NOT import b_workload_*.py. Reads the saved runs directly, joins label/kind from
data/golden/pairs.jsonl itself, and implements thr98, elim@98 and AUROC from scratch. The repo helpers
(scripts/analyze.py auroc / pr_curve / at_recall) are imported only to cross-check the from-scratch values.
The bootstrap here is my own: stratified by LABEL (the analyst stratified by kind), a different seed and
2,000 resamples, so agreement is a check on the analyst's intervals, not a copy of them. Stdlib only,
deterministic, no GPU or network.

Prints:
  V0  every table in B-workload.md vs a fresh run of the analyst's scripts (run as subprocesses)
  V1  label join and row accounting (stale labels in scores.jsonl, rows not in pairs.jsonl, null scores)
  V2  run conditions that bear on timing: row order, request switches, retries/reloads, runner, batch, quant
  V3  machine time: mean / median / p90 wall ms and hours per 10,000, main and roster; by request
  V4  Jev billed tokens and cost; ties at Jev's thr98
  V5  from-scratch AUROC, thr98, elim@98 vs the repo helpers and the brief's headline numbers
  V6  per-kind pass counts at thr98 and 0.5, and the plausible scenario per 10,000 (p = 20%, 50/50 mix)
  V7  misses at the pooled thr98, split by request
  V8  25-3152 with / without roster: pair sets, thresholds on the 249 pairs, plausible-scenario flagged
  V9  prefix-cache check: same-pair deltas in prefill and wall time when the roster is appended
  V10 independent paired bootstrap for the headline comparisons, with 95% and Bonferroni-style intervals
"""
import json
import pathlib
import random
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze  # noqa: E402  (cross-check only)

RUNS = {
    "4b lp": "golden_qwen3.5_4b_logprob_p2db",
    "9b lp": "golden_qwen3.5_9b_logprob_p2db",
    "27b lp": "golden_qwen3.8_27b_logprob_p2",
    "d3-4b": "golden_d3-ctx8k_4b_noul_p2",
    "d3-9b": "golden_d3-ctx8k_9b_noul_p2",
    "d3-27b": "golden_d3-ctx8k_27b_noul_p2",
    "Jev": "golden_jev-1.14.0_noul_p2",
}
JSON_RUNS = {
    "4b json": "golden_qwen3.5_4b_json_p2", "9b json": "golden_qwen3.5_9b_json_p2",
    "27b json": "golden_qwen3.8_27b_json_p2", "4b jsonR": "golden_qwen3.5_4b_json_reason_p2",
    "9b jsonR": "golden_qwen3.5_9b_json_reason_p2", "27b jsonR": "golden_qwen3.8_27b_json_reason_p2",
}
# headline of docs/findings-golden.md §1 on the labels of 2026-11-11 (the brief's 2026-10-31 values were 0.923/52, 0.942/71,
# 0.975/76, 0.884/54, 0.947/68, 0.979/81, 0.916/63)
HEADLINE = {  # AUROC, elim@98 (rounded %), median wall ms
    "4b lp": (0.922, 53, 504), "9b lp": (0.945, 72, 855), "27b lp": (0.977, 77, 2639),
    "d3-4b": (0.901, 55, 876), "d3-9b": (0.957, 70, 1425), "d3-27b": (0.983, 83, 4661),
    "Jev": (0.917, 64, 117),
}
N = 10_000
P_PLAUS = 0.20
SEED = 4242
NBOOT = 2000


# ---------------------------------------------------------------- loading
from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def pairs():
    return {p["pair_id"]: p for p in map(json.loads, open(ROOT / "data/golden/pairs.jsonl"))}


PAIRS = pairs()


def raw(tag):
    return [json.loads(l) for l in open(ROOT / "runs" / tag / "scores.jsonl")]


def load(tag):
    """Rows with label/kind from pairs.jsonl; rows not in pairs.jsonl or without a score dropped."""
    out = []
    for r in raw(tag):
        if r["pair_id"] not in PAIRS or "error" in r or r.get("score") is None:
            continue
        p = PAIRS[r["pair_id"]]
        out.append({**r, "label": p["label"], "kind": p["kind"]})
    return out


# ---------------------------------------------------------------- metrics from scratch
def my_thr98(rows, target=0.98):
    """Highest t with #(pos with score >= t) / #pos >= target. That t is the k-th highest positive score,
    k = smallest integer with k / P >= target."""
    pos = sorted((r["score"] for r in rows if r["label"]), reverse=True)
    P = len(pos)
    k = next(k for k in range(1, P + 1) if k / P >= target)
    return pos[k - 1]


def my_auroc(rows):
    pos = [r["score"] for r in rows if r["label"]]
    neg = [r["score"] for r in rows if not r["label"]]
    s = 0.0
    for a in pos:
        for b in neg:
            s += 1.0 if a > b else 0.5 if a == b else 0.0
    return s / (len(pos) * len(neg))


def my_elim(rows, t):
    neg = [r["score"] for r in rows if not r["label"]]
    return sum(x < t for x in neg), len(neg)


def counts(rows, t):
    """{group: (k flagged, n)} with flagged = score >= t (t=None: the default 0.5 / JSON verdict)."""
    out = {}
    for r in rows:
        f = (bool(r["verdict"]) if "verdict" in r else r["score"] >= 0.5) if t is None else r["score"] >= t
        for g in (r["kind"], "POS" if r["label"] else "NEG"):
            k, n = out.get(g, (0, 0))
            out[g] = (k + f, n + 1)
    return out


def scen(c, p=P_PLAUS):
    R = c["POS"][0] / c["POS"][1]
    Fr = c["real_negative"][0] / c["real_negative"][1]
    Fh = c["hard_negative"][0] / c["hard_negative"][1]
    F = (Fr + Fh) / 2
    return N * (p * R + (1 - p) * F), N * p * (1 - R)


def q(xs, a):
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, int(a * len(s))))]


def h(ms):
    return ms * N / 3_600_000


def table(header, rows):
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join("---" for _ in header) + "|")
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")
    print()


def check_tables():
    """V0: run the analyst's two scripts (as subprocesses, not imports) and compare every table row they print
    with the table rows in docs/analysis/B-workload.md above its '## Verification' section."""
    import subprocess
    out_rows = []
    for script, args in (("b_workload_time.py", []), ("b_workload_review.py", ["--boot", "1000"])):
        res = subprocess.run([sys.executable, str(ROOT / "scripts/analysis" / script), *args], cwd=ROOT,
                             capture_output=True, text=True, check=True)
        out_rows += [l for l in res.stdout.splitlines() if l.startswith("|") and not l.startswith("|---")]
    md = open(ROOT / "docs/analysis/B-workload.md").read().split("\n## Verification")[0]
    md_rows = [l for l in md.splitlines() if l.startswith("|") and not l.startswith("|---")]
    out_set = set(out_rows)
    from_out = [l for l in md_rows if l in out_set]
    data_out = [l for l in out_rows if not l.startswith("| config") and not l.startswith("| JSON run")
                and not l.startswith("| set |") and not l.startswith("| pair |")
                and not l.startswith("| first") and not l.startswith("| speed")]
    md_data = [l for l in from_out if l in set(data_out)]
    print("## V0 Tables in B-workload.md vs a fresh run of the analyst's scripts\n")
    print(f"- table rows printed by the scripts: {len(out_rows)} ({len(data_out)} data rows, the rest headers)")
    print(f"- md table rows (above Verification): {len(md_rows)}; found verbatim in the output: {len(from_out)}; "
          f"not in the output: {len(md_rows) - len(from_out)} (the hand-written tables: run list, scenario "
          "dimensions, findings, reproduce)")
    # the indented B4 summary table repeats B4.2 thr98 values with typographic minus signs
    ok = bad = 0
    for l in md.splitlines():
        if not l.startswith("  | ") or l.startswith("  |---") or l.startswith("  | config"):
            continue
        cfg, fl, d = [c.strip() for c in l.strip().strip("|").split("|")]
        a, b = fl.split(" → ")
        d = d.replace("−", "-")
        hit = any(r.startswith(f"| {cfg} | ") and f"| {a} [" in r and f"→ {b} [" in r and f"| {d} |" in r
                  for r in out_rows)
        ok, bad = ok + hit, bad + (not hit)
    print(f"- indented B4 summary rows matching a B4.2 output row: {ok} of {ok + bad}")
    print(f"- every output data row appears in the md: {'yes' if set(data_out) <= set(md_rows) else 'NO'}; "
          f"data rows in the same order: {'yes' if md_data == data_out else 'NO'}\n")


def main():
    print("# Branch B verification\n")
    check_tables()

    # ---- V1 label join ----
    print("## V1 Label join and row accounting\n")
    out = []
    for name, tag in list(RUNS.items()) + list(JSON_RUNS.items()):
        for t in (tag, tag + "_roster"):
            rr = raw(t)
            notin = sum(r["pair_id"] not in PAIRS for r in rr)
            stale = sum(r["pair_id"] in PAIRS and r.get("label") != PAIRS[r["pair_id"]]["label"] for r in rr)
            stalek = sum(r["pair_id"] in PAIRS and r.get("kind") != PAIRS[r["pair_id"]]["kind"] for r in rr)
            null = sum(r["pair_id"] in PAIRS and (r.get("score") is None or "error" in r) for r in rr)
            req = sorted({r["request_id"] for r in rr})
            out.append([name, "roster" if t.endswith("_roster") else "main", len(rr), notin, stale, stalek, null,
                        len(load(t)), ",".join(req)])
    table(["config", "set", "rows in file", "not in pairs.jsonl", "label differs from pairs.jsonl",
           "kind differs", "null score", "rows used", "requests"], out)
    kinds = {}
    for p in PAIRS.values():
        kinds[(p["request_id"], p["kind"])] = kinds.get((p["request_id"], p["kind"]), 0) + 1
    print("pairs.jsonl by request and kind: " + ", ".join(f"{r} {k} {n}" for (r, k), n in sorted(kinds.items())))
    print()

    # ---- V2 run conditions ----
    print("## V2 Run conditions that bear on timing\n")
    out = []
    for name, tag in list(RUNS.items()) + list(JSON_RUNS.items()):
        cfg = json.load(open(ROOT / "runs" / tag / "run.json"))
        rr = raw(tag)
        keys = [(r["request_id"], r["email_id"]) for r in rr]
        sw = sum(a[0] != b[0] for a, b in zip(keys, keys[1:]))
        d = cfg.get("details") or {}
        out.append([name, cfg.get("ollama_version") or "—", cfg.get("num_batch") or "default",
                    d.get("quantization_level", "—"), d.get("runner", "—"), cfg.get("endpoint") or "/api/chat",
                    cfg.get("concurrency"), "yes" if keys == sorted(keys) else "by request only" if sw == 1 else "no",
                    sw, max((r.get("retries") or 0) for r in rr), max((r.get("reloads") or 0) for r in rr)])
    table(["config", "ollama", "num_batch", "quant", "runner", "endpoint", "concurrency",
           "rows sorted by (request, email)", "request switches", "max retries", "max reloads"], out)

    # ---- V3 machine time ----
    print("## V3 Machine time (single-stream), hours per 10,000 = mean wall_ms x 10,000 / 3.6e6\n")
    out = []
    for name, tag in RUNS.items():
        for label, t in (("main", tag), ("roster", tag + "_roster")):
            w = [r["wall_ms"] for r in load(t)]
            row = [name, label, len(w), f"{statistics.mean(w):,.0f}", f"{statistics.median(w):,.0f}",
                   f"{q(w, 0.9):,.0f}", f"{h(statistics.mean(w)):.2f}"]
            if label == "main":
                for req in ("24-409", "25-3152"):
                    wr = [r["wall_ms"] for r in load(t) if r["request_id"] == req]
                    row.append(f"{h(statistics.mean(wr)):.2f}")
            else:
                row += ["—", "—"]
            out.append(row)
    table(["config", "set", "n", "mean ms", "median ms", "p90 ms (s[int(.9n)])", "h / 10,000",
           "h / 10,000, 24-409 only", "h / 10,000, 25-3152 only"], out)

    # ---- V4 Jev cost and ties ----
    print("## V4 Jev: billed tokens, cost, output tokens, ties\n")
    for label, t in (("main", RUNS["Jev"]), ("roster", RUNS["Jev"] + "_roster")):
        rr = load(t)
        tok = [r["prompt_tokens"] for r in rr]
        outt = sorted({r.get("output_tokens") for r in rr})
        print(f"- {label}: {len(rr)} calls, {sum(tok):,} input tokens, mean {statistics.mean(tok):,.1f}; "
              f"cost of run ${sum(tok) / 1e6 * 0.042:.4f}; per 10,000 at the mean ${statistics.mean(tok) * N / 1e6 * 0.042:.3f}; "
              f"output_tokens values reported by the API: {outt}")
    rr = load(RUNS["Jev"])
    t = my_thr98(rr)
    at = [r for r in rr if r["score"] == t]
    print(f"- Jev distinct score values: {len({r['score'] for r in rr})}; thr98 = {t}; pairs with score exactly "
          f"{t}: {len(at)} ({sum(r['label'] for r in at)} positive, {sum(1 - r['label'] for r in at)} negative). "
          f"Flagging uses >=, so all of them are flagged.\n")

    # ---- V5 from-scratch metrics ----
    print(f"## V5 From-scratch AUROC, thr98, elim@98 (main set, {N_ALL} pairs) vs repo helpers and the brief\n")
    out = []
    for name, tag in RUNS.items():
        rr = load(tag)
        sc, lb = [r["score"] for r in rr], [r["label"] for r in rr]
        a_me, a_repo = my_auroc(rr), analyze.auroc(sc, lb)
        t_me = my_thr98(rr)
        t_repo = analyze.at_recall(analyze.pr_curve(sc, lb), 0.98)[0]
        k, n = my_elim(rr, t_me)
        ha, he, hm = HEADLINE[name]
        out.append([name, f"{a_me:.4f}", f"{a_repo:.4f}", ha, f"{t_me:.4f}", f"{t_repo:.4f}",
                    f"{k}/{n} = {100 * k / n:.1f}%", f"{he}%", "ok" if abs(a_me - a_repo) < 1e-12 and t_me == t_repo
                    and round(a_me, 3) == ha and round(100 * k / n) == he else "MISMATCH"])
    table(["config", "AUROC (mine)", "AUROC (analyze.auroc)", "brief", "thr98 (mine)", "thr98 (at_recall)",
           "elim@98 (mine)", "brief", "agree"], out)
    out = []
    for name, tag in JSON_RUNS.items():
        rr = load(tag)
        pos = [r["score"] for r in rr if r["label"]]
        k98 = next(k for k in range(1, len(pos) + 1) if k / len(pos) >= 0.98)
        out.append([name, len(rr), f"{my_thr98(rr):.4f}", sum(x == 0 for x in pos), len(pos), len(pos) - k98])
    table(["JSON config", "rows", "thr98 (mine)", "positives with score exactly 0", "positives",
           "misses allowed at 98%"], out)

    # ---- V6 per-kind counts and plausible scenario ----
    print("## V6 Per-kind pass counts and the plausible scenario (p = 20%, negatives 50/50 real/hard)\n")
    out = []
    for name, tag in RUNS.items():
        rr = load(tag)
        for cut, t in (("thr98", my_thr98(rr)), ("0.5", None)):
            c = counts(rr, t)
            f, m = scen(c)
            out.append([name, cut, f"{c['POS'][0]}/{c['POS'][1]}", f"{c['real_positive'][0]}/{c['real_positive'][1]}",
                        f"{c['real_negative'][0]}/{c['real_negative'][1]}",
                        f"{c['hard_negative'][0]}/{c['hard_negative'][1]}", f"{f:,.0f}", f"{m:,.0f}",
                        f"{100 * (1 - f / N):.0f}%", f"{f * 30 / 3600:.1f}"])
    table(["config", "cutoff", "positives flagged", "real pos", "real neg slipped", "hard neg slipped",
           "flagged / 10,000", "missed / 10,000", "review avoided", "reviewer h @30 s"], out)

    # ---- V7 misses by request at the pooled threshold ----
    print("## V7 Misses at the pooled (both-request) thr98, by request\n")
    out = []
    for name, tag in RUNS.items():
        rr = load(tag)
        t = my_thr98(rr)
        row = [name, f"{t:.4f}"]
        for req in ("24-409", "25-3152"):
            pos = [r for r in rr if r["label"] and r["request_id"] == req]
            miss = sum(r["score"] < t for r in pos)
            row.append(f"{miss}/{len(pos)} missed (recall {100 * (1 - miss / len(pos)):.1f}%); "
                       f"{N * P_PLAUS * miss / len(pos):.0f} missed per 10,000 at p = 20%")
        out.append(row)
    table(["config", "pooled thr98", "24-409", "25-3152"], out)
    kmax = N_POS - -(-98 * N_POS // 100)  # misses the pooled 98% cutoff allows
    print(f"A 10,000-hit batch belongs to one request. The pooled figure ({kmax}/{N_POS}, {N * P_PLAUS * kmax / N_POS:.0f} per 10,000 at p = 20%) is the "
          "positive-weighted average of the two requests' miss rates, not what either request gets.\n")

    # ---- V8 roster ----
    print("## V8 25-3152: without vs with the roster (thresholds chosen on the 249 pairs)\n")
    out = []
    for name, tag in RUNS.items():
        wo = [r for r in load(tag) if r["request_id"] == "25-3152"]
        wi = load(tag + "_roster")
        same = {r["pair_id"] for r in wo} == {r["pair_id"] for r in wi}
        row = [name, len(wo), len(wi), "yes" if same else "NO", ",".join(sorted({r["request_id"] for r in wi}))]
        for rows in (wo, wi):
            t = my_thr98(rows)
            c = counts(rows, t)
            f, m = scen(c)
            row += [f"{t:.4f}", f"{c['real_negative'][0]}/{c['real_negative'][1]}",
                    f"{c['hard_negative'][0]}/{c['hard_negative'][1]}", f"{f:,.0f}"]
        out.append(row)
    table(["config", "pairs without", "pairs with", "same pair_ids", "requests in roster run",
           "thr98 without", "real neg without", "hard neg without", "flagged without",
           "thr98 with", "real neg with", "hard neg with", "flagged with"], out)

    # ---- V9 prefix cache ----
    print("## V9 Prefix-cache check: same 249 pairs, roster run minus main run\n")
    out = []
    for name, tag in RUNS.items():
        A = {r["pair_id"]: r for r in load(tag) if r["request_id"] == "25-3152"}
        B = {r["pair_id"]: r for r in load(tag + "_roster")}
        ids = sorted(set(A) & set(B))
        dt = sorted({B[i]["prompt_tokens"] - A[i]["prompt_tokens"] for i in ids})
        dw = [B[i]["wall_ms"] - A[i]["wall_ms"] for i in ids]
        dp = [B[i]["prefill_ms"] - A[i]["prefill_ms"] for i in ids] if "prefill_ms" in A[ids[0]] else None
        mA = statistics.mean(A[i]["wall_ms"] for i in ids)
        out.append([name, len(ids), dt, f"{statistics.mean(dw):+,.0f}", f"{100 * statistics.mean(dw) / mA:+.1f}%",
                    f"{statistics.median(dw):+,.0f}",
                    f"{statistics.median(dp):+,.0f}" if dp else "—", f"{h(statistics.mean(dw)):+.2f}"])
    table(["config", "pairs", "token deltas seen", "mean Δwall ms", "mean Δwall as % of mean without",
           "median Δwall ms", "median Δprefill ms", "Δ h / 10,000"], out)

    # ---- V10 independent paired bootstrap ----
    print(f"## V10 Independent paired bootstrap: Δ flagged per 10,000, plausible scenario, thr98 re-chosen each "
          f"resample\n\nStratified by label (not kind), seed {SEED}, {NBOOT} resamples. 'Bonferroni' = the "
          "1 − 0.05/11 percentile interval, for the 11 thr98 comparisons the analyst ran on the main set.\n")

    def boot(runs, comps, seed):
        rng = random.Random(seed)
        idx = {n: {r["pair_id"]: r for r in rows} for n, rows in runs.items()}
        ids = sorted(next(iter(idx.values())))
        pos = [i for i in ids if PAIRS[i]["label"]]
        neg = [i for i in ids if not PAIRS[i]["label"]]
        reps = {c: [] for c in comps}
        for _ in range(NBOOT):
            s = rng.choices(pos, k=len(pos)) + rng.choices(neg, k=len(neg))
            fl = {}
            for n in {x for c in comps for x in c}:
                rows = [idx[n][i] for i in s]
                fl[n] = scen(counts(rows, my_thr98(rows)))[0]
            for c in comps:
                reps[c].append(fl[c[1]] - fl[c[0]])
        return reps

    def report(runs, comps, seed, bonf_k):
        reps = boot(runs, comps, seed)
        out = []
        for c in comps:
            pt = {}
            for n in c:
                rows = runs[n]
                pt[n] = scen(counts(rows, my_thr98(rows)))[0]
            r = reps[c]
            a = 0.05 / bonf_k
            out.append([f"{c[0]} → {c[1]}", f"{pt[c[1]] - pt[c[0]]:+,.0f}", f"[{q(r, .025):+,.0f}, {q(r, .975):+,.0f}]",
                        f"[{q(r, a / 2):+,.0f}, {q(r, 1 - a / 2):+,.0f}]",
                        f"{sum(x >= 0 for x in r) / len(r):.3f}"])
        table(["first → second", "Δ flagged (point)", "95% CI (mine)", f"Bonferroni CI (k={bonf_k})",
               "share of resamples with Δ ≥ 0"], out)

    main_runs = {n: load(t) for n, t in RUNS.items()}
    report(main_runs, [("Jev", "9b lp"), ("Jev", "27b lp"), ("Jev", "d3-27b"), ("9b lp", "27b lp"),
                       ("9b lp", "d3-27b"), ("27b lp", "d3-27b"), ("4b lp", "d3-4b"), ("9b lp", "d3-9b"),
                       ("4b lp", "9b lp")], SEED, 11)
    print("25-3152 with the roster (249 pairs):\n")
    ro = {n: load(t + "_roster") for n, t in RUNS.items()}
    report(ro, [("27b lp", "d3-27b"), ("Jev", "d3-27b"), ("4b lp", "d3-4b"), ("9b lp", "d3-9b")], SEED + 1, 11)
    print("25-3152, without → with the roster (same 249 pairs; paired by pair_id):\n")
    both = {}
    for n in ("27b lp", "d3-27b"):
        both[n + " (no roster)"] = [r for r in main_runs[n] if r["request_id"] == "25-3152"]
        both[n + " (roster)"] = ro[n]
    report(both, [("27b lp (no roster)", "27b lp (roster)"), ("d3-27b (no roster)", "d3-27b (roster)")], SEED + 2, 7)

    # ---- V11 mechanism check: does num_batch 8192 alone stop prefix reuse? ----
    print("## V11 Mechanism check (outside the main tables): stock Qwen lp at num_batch 8192\n")
    print("Same model, mode, prompt and Ollama version as the main 4b/9b lp runs, but num_batch 8192 (the earlier "
          "golden_qwen3.5_{4b,9b}_logprob_p2 runs and their _roster twins). Used here only to test what stops "
          "prefix reuse; no workload number comes from them. If the roster costs about tokens x per-token rate here "
          "too, num_batch 8192 by itself disables reuse, and the d3 runs (also num_batch 8192) can't show whether "
          "noncausal attention matters.\n")
    out = []
    for name, tag, ref in (("4b lp", "golden_qwen3.5_4b_logprob_p2", RUNS["4b lp"]),
                           ("9b lp", "golden_qwen3.5_9b_logprob_p2", RUNS["9b lp"])):
        for label, t in (("default batch (main run)", ref), ("num_batch 8192", tag)):
            cfg = json.load(open(ROOT / "runs" / t / "run.json"))
            A = {r["pair_id"]: r for r in raw(t) if r["request_id"] == "25-3152"}
            B = {r["pair_id"]: r for r in raw(t + "_roster")}
            ids = sorted(set(A) & set(B))
            dp = [B[i]["prefill_ms"] - A[i]["prefill_ms"] for i in ids]
            dw = [B[i]["wall_ms"] - A[i]["wall_ms"] for i in ids]
            out.append([name, label, cfg.get("num_batch") or "default", cfg.get("ollama_version"), len(ids),
                        f"{statistics.median(dp):+,.0f}", f"{statistics.median(dw):+,.0f}"])
    table(["model", "run", "num_batch", "ollama", "pairs", "median Δprefill ms (roster − none)",
           "median Δwall ms"], out)

    # ---- V12 canary overlap in the lp runs ----
    print("## V12 Canary calls in the lp runs (score.py: every 100 rows, logprob mode only)\n")
    print("score.py re-scores the first pair after every 100 written rows, from the main thread, while the single "
          "worker thread is already scoring the next row (ThreadPoolExecutor.map submits all rows up front). The "
          "overlapping timed row waits for the canary. 'Excess' = server time not in prefill or decode "
          "(total_ms − prefill_ms − decode_ms) above the run's median, summed over rows at index 100/101, 200/201, "
          "300/301, 400/401.\n")
    out = []
    for name in ("4b lp", "9b lp", "27b lp"):
        for label, t in (("main", RUNS[name]), ("roster", RUNS[name] + "_roster")):
            rr = load(t)
            oth = [r["total_ms"] - r["prefill_ms"] - r["decode_ms"] for r in rr]
            med = statistics.median(oth)
            near = [i for i in range(len(rr)) if i >= 100 and i % 100 in (0, 1)]
            ex = sum(max(0.0, oth[i] - med) for i in near)
            w = statistics.mean(r["wall_ms"] for r in rr)
            out.append([name, label, len(near), f"{ex:,.0f}", f"{ex / len(rr):.1f}",
                        f"{100 * ex / len(rr) / w:.1f}%", f"{h(ex / len(rr)):.2f}"])
    table(["config", "set", "rows checked", "excess ms, total", "excess ms per call", "share of mean wall",
           "h / 10,000"], out)


if __name__ == "__main__":
    main()
