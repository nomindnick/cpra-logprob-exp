"""D4: numbers behind the limitations register.

  uv run python scripts/analysis/d_validity_limits.py [--boot 1000]

Uses the main runs (d_validity_common.SCORE_RUNS / JSON_RUNS and their _roster twins) plus, for two rows only,
other saved runs of the same models:
  - prompt 2 in-sample (L-3): the prompt-1 reruns on the same Ollama version and batch setting
    (golden_qwen3.5_{4b,9b}_logprob_p1o40 vs golden_qwen3.5_{4b,9b}_logprob_p2, both num_batch 8192;
    golden_qwen3.8_27b_logprob_p1o40 vs golden_qwen3.8_27b_logprob_p2, both default batch);
  - one run per configuration (L-4): other prompt-2 runs of the same model (4b/9b lp at batch 8192 and at the
    default batch reloaded every call; d3 rerun with a reload before every call on a 60-pair / 30-pair subset).
Everything else comes from data/golden and the run.json files. Stdlib only, deterministic (random.Random(seed)).

Prints L-1 (synthetic share), L-2 (adjudication coverage), L-3 (prompt 2 gain, in-sample), L-4 (rerun
agreement), L-5 (quantization), L-6 (Jev rounding and ties), L-7 (latency: network, prefix cache, roster),
L-8 (single machine, single stream), L-9 (truncation and attachments), L-10 (cluster bootstrap: synthetic edits
of emails that are also in the set).
"""
import argparse
import collections
import json
import random
import statistics
import sys

sys.path.insert(0, "scripts/analysis")
from d_validity_common import (ALL_RUNS, SCORE_RUNS, at_recall, auroc, ci, emails, load, pairs, point,  # noqa: E402
                               pr_curve, run_config, table)
from d_validity_realism import hit  # noqa: E402

sys.path.insert(0, "scripts")
from compare import ranks  # noqa: E402


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def spearman(x, y):
    rx, ry = ranks(x), ranks(y); n = len(x); m = (n + 1) / 2
    num = sum((a - m) * (b - m) for a, b in zip(rx, ry))
    return num / (sum((a - m) ** 2 for a in rx) * sum((b - m) ** 2 for b in ry)) ** 0.5


def q(xs, p):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(p * len(xs)))]


def pct(k, n):
    return f"{k}/{n} ({k / n:.0%})" if n else "—"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=409)
    a = ap.parse_args()
    P = pairs(); E = emails()
    runs = {n: {r["pair_id"]: r for r in load(t, P)[0]} for n, t in ALL_RUNS}
    print("# D4. Numbers for the limitations register\n")

    print("## L-1. Synthetic share of the golden set\n")
    out = []
    for grp, f in (("all pairs", lambda x: True), ("positives", lambda x: x["label"] == 1), ("negatives", lambda x: x["label"] == 0)):
        for rid in ("both", "24-409", "25-3152"):
            xs = [e for p, e in E.items() if f(P[p]) and rid in ("both", e["request_id"])]
            out.append([grp, rid, len(xs), pct(sum(e["origin"] == "synthetic" for e in xs), len(xs))])
    table(["group", "request", "n", "synthetic"], out)

    print("## L-2. Label checking: what rests on the human, and an upper bound for the rest\n")
    items = json.load(open("data/golden/work/adjudication_items.json"))["items"]
    calls = {k: v.get("call") for k, v in json.load(open("data/golden/work/adjudications.json")).items()}
    pre = {f"{p['request_id']}~{p['email_id']}": p for p in map(json.loads, open("data/golden/work/prelabels.jsonl"))}
    spot = [i for i in items if i["section"] == "spot"]
    errs = sum(calls.get(i["key"]) != pre[i["key"]]["prelabel"] for i in spot)
    ub = 1 - 0.05 ** (1 / len(spot)) if errs == 0 else None
    real_un = sum(1 for e in E.values() if e["origin"] != "synthetic" and not e["adjudicated"])
    syn_un = sum(1 for e in E.values() if e["origin"] == "synthetic" and not e["adjudicated"])
    table(["quantity", "value"], [
        ["random spot check of Opus/production agreements: human disagreed", f"{errs}/{len(spot)}"],
        ["one-sided 95% upper bound on the disagreement rate (exact, 0 events)", f"{ub:.1%}" if ub is not None else "—"],
        ["real rows with no human call (label = production membership + agreeing Opus pre-label)",
         f"{real_un}/{sum(e['origin'] != 'synthetic' for e in E.values())}"],
        ["  expected label errors among them at that upper bound", f"≤ {real_un * ub:.1f}" if ub is not None else "—"],
        ["synthetic rows with no human call (label = generator's intent + verifier agreement)",
         f"{syn_un}/{sum(e['origin'] == 'synthetic' for e in E.values())}"],
        ["adjudicators", "1 (the project owner)"],
    ])

    print("## L-3. Prompt 2 was written after reading this set's misses: its measured gain is in-sample\n")
    print("Prompt 1 → 2 on the same Ollama 0.40.13, render 2 and batch setting; paired bootstrap over pairs (stratified "
          "by label).\n")
    comps = [("4b lp (batch 8192)", "golden_qwen3.5_4b_logprob_p1o40", "golden_qwen3.5_4b_logprob_p2"),
             ("9b lp (batch 8192)", "golden_qwen3.5_9b_logprob_p1o40", "golden_qwen3.5_9b_logprob_p2"),
             ("27b lp (default batch)", "golden_qwen3.8_27b_logprob_p1o40", "golden_qwen3.8_27b_logprob_p2")]
    out = []
    rng = random.Random(a.seed)
    for lab, t1, t2 in comps:
        c1, c2 = run_config(t1), run_config(t2)
        assert (c1["prompt"], c2["prompt"]) == (1, 2) and c1.get("num_batch") == c2.get("num_batch")
        A = {r["pair_id"]: r for r in load(t1, P)[0]}; B = {r["pair_id"]: r for r in load(t2, P)[0]}
        for rid in ("both", "24-409", "25-3152"):
            ids = sorted(p for p in A if p in B and rid in ("both", P[p]["request_id"]))
            pa, pb = point([A[p] for p in ids]), point([B[p] for p in ids])
            pos = [p for p in ids if P[p]["label"]]; neg = [p for p in ids if not P[p]["label"]]
            d = []
            for _ in range(a.boot):
                bb = rng.choices(pos, k=len(pos)) + rng.choices(neg, k=len(neg)); l = [P[p]["label"] for p in bb]
                d.append(auroc([B[p]["score"] for p in bb], l) - auroc([A[p]["score"] for p in bb], l))
            lo, hi = ci(d)
            out.append([lab, rid, len(ids), f"{pa['auroc']:.3f} → {pb['auroc']:.3f}",
                        f"{pb['auroc'] - pa['auroc']:+.3f} [{lo:+.3f}, {hi:+.3f}]", f"{pa['elim']:.0%} → {pb['elim']:.0%}"])
    table(["model", "request", "pairs", "AUROC prompt 1 → 2", "ΔAUROC [paired 95% CI]", "elim@98 prompt 1 → 2"], out)

    print("## L-4. One run per configuration: how much a second run of the same model and prompt moves\n")
    print("Each row compares a main run with another saved prompt-2 run of the same model on the same pairs. The "
          "settings differ as noted (batch size, or unloading the model before every call), so this is an upper "
          "bound on pure repeat noise for those backends.\n")
    reruns = [("4b lp", "golden_qwen3.5_4b_logprob_p2db", "golden_qwen3.5_4b_logprob_p2dbf", "default batch: cached vs reloaded every call"),
              ("4b lp", "golden_qwen3.5_4b_logprob_p2db", "golden_qwen3.5_4b_logprob_p2", "default batch vs batch 8192"),
              ("9b lp", "golden_qwen3.5_9b_logprob_p2db", "golden_qwen3.5_9b_logprob_p2dbf", "default batch: cached vs reloaded every call"),
              ("9b lp", "golden_qwen3.5_9b_logprob_p2db", "golden_qwen3.5_9b_logprob_p2", "default batch vs batch 8192"),
              ("d3-4b", "golden_d3-ctx8k_4b_noul_p2", "golden_d3-ctx8k_4b_noul_p2_fresh60", "cached vs reloaded every call (60 pairs)"),
              ("d3-9b", "golden_d3-ctx8k_9b_noul_p2", "golden_d3-ctx8k_9b_noul_p2_fresh60", "cached vs reloaded every call (60 pairs)"),
              ("d3-27b", "golden_d3-ctx8k_27b_noul_p2", "golden_d3-ctx8k_27b_noul_p2_fresh60", "cached vs reloaded every call (60 pairs)"),
              ("d3-4b +roster", "golden_d3-ctx8k_4b_noul_p2_roster", "golden_d3-ctx8k_4b_noul_p2_roster_fresh30", "cached vs reloaded (30 pairs)"),
              ("d3-27b +roster", "golden_d3-ctx8k_27b_noul_p2_roster", "golden_d3-ctx8k_27b_noul_p2_roster_fresh30", "cached vs reloaded (30 pairs)")]
    out = []
    for lab, t1, t2, how in reruns:
        A = {r["pair_id"]: r for r in load(t1, P)[0]}; B = {r["pair_id"]: r for r in load(t2, P)[0]}
        ids = sorted(set(A) & set(B))
        d = [abs(A[p]["score"] - B[p]["score"]) for p in ids]
        base = lab.replace(" +roster", "")
        thr = point(list(runs[base].values()))["thr"] if base in runs and "+roster" not in lab else None
        cross = sum((A[p]["score"] >= thr) != (B[p]["score"] >= thr) for p in ids) if thr is not None else "—"
        row = [lab, how, len(ids), sum(x < 1e-6 for x in d), f"{statistics.mean(d):.4f}", f"{max(d):.3f}", cross]
        if len(ids) >= 400:
            pa, pb = point([A[p] for p in ids]), point([B[p] for p in ids])
            row += [f"{pa['auroc']:.3f} / {pb['auroc']:.3f}", f"{pa['elim']:.0%} / {pb['elim']:.0%}"]
        else:
            row += ["—", "—"]
        out.append(row)
    crosses = [r[6] for r in out if isinstance(r[6], int) and r[0].endswith("lp")]
    print(f"lp reruns: pairs crossing the main cutoff {min(crosses)}–{max(crosses)}; d3 reruns: largest mean abs Δ "
          f"{max(float(r[4]) for r in out if r[0].startswith('d3')):.4f}\n")
    table(["model", "second run", "pairs", "identical (abs Δ < 1e-6)", "mean abs Δ", "max abs Δ", "pairs crossing main thr98",
           "AUROC main / second", "elim@98 main / second"], out)

    print("## L-5. Quantization and runtime per model (run.json)\n")
    out = []
    for n, t in SCORE_RUNS:
        c = run_config(t); d = c.get("details") or {}
        out.append([n, t, d.get("parent_model") or c["model"], d.get("parameter_size", "—"), d.get("quantization_level", "— (hosted)"),
                    d.get("runner", "—"), c.get("backend", "ollama /api/chat"), c.get("ollama_version", "—"), c.get("prompt_hash")])
    table(["run", "tag", "model", "parameters", "quantization", "runner", "endpoint", "Ollama", "prompt hash"], out)

    print("## L-6. Jev's scores are rounded to 2 decimals: ties and what rounding does to AUROC and elim@98\n")
    J = list(runs["Jev"].values())
    vals = collections.Counter(r["score"] for r in J)
    dec = max(len(f"{v}".split(".")[1]) if "." in f"{v}" else 0 for v in vals)
    pos = [r["score"] for r in J if r["label"]]; neg = [r["score"] for r in J if not r["label"]]
    gt = sum(1 for x in pos for y in neg if x > y); eq = sum(1 for x in pos for y in neg if x == y); tot = len(pos) * len(neg)
    t98 = point(J)["thr"]
    table(["quantity", "value"], [
        [f"distinct score values (of {N_ALL})", len(vals)],
        ["most decimals in any score", dec],
        ["most common values", ", ".join(f"{v:g}×{n}" for v, n in vals.most_common(6))],
        ["(positive, negative) pairs tied", f"{eq}/{tot} ({eq / tot:.1%})"],
        ["AUROC with ties counted half (reported)", f"{(gt + eq / 2) / tot:.3f}"],
        ["AUROC range if ties were broken worst / best", f"{gt / tot:.3f} – {(gt + eq) / tot:.3f}"],
        ["98% cutoff; emails scored exactly at it (pos/neg)", f"{t98:g}; {sum(1 for x in pos if x == t98)}/{sum(1 for y in neg if y == t98)}"],
    ])
    print("The same rounding applied to the other score runs (score → round(score, 2)):\n")
    out = []; dmax_a = dmax_k = 0
    for n, _ in SCORE_RUNS:
        R = list(runs[n].values())
        Rr = [{**r, "score": round(r["score"], 2)} for r in R]
        p0, p1 = point(R), point(Rr)
        dmax_a = max(dmax_a, abs(p1["auroc"] - p0["auroc"])); dmax_k = max(dmax_k, abs(p1["k"] - p0["k"]))
        out.append([n, len({r['score'] for r in R}), len({r['score'] for r in Rr}), f"{p0['auroc']:.4f} → {p1['auroc']:.4f}",
                    f"{p0['elim']:.1%} ({p0['k']}) → {p1['elim']:.1%} ({p1['k']})"])
    table(["run", "distinct values", "after rounding", "AUROC", f"elim@98 (k cleared of {N_NEG})"], out)
    print(f"Largest change from rounding: AUROC {dmax_a:.4f}; negatives cleared at 98% recall {dmax_k}\n")

    print("## L-7. Latency: what is in the number\n")
    print("wall_ms = request to response as the scorer saw it (median; p10–p90). Prompt tokens are each backend's own "
          f"count. Spearman ρ = rank correlation of wall time with prompt tokens over the {N_ALL} pairs (near 1: time "
          "scales with the email; low: a fixed cost such as the network dominates).\n")
    out = []
    for n, t in SCORE_RUNS:
        R = list(runs[n].values())
        w = [r["wall_ms"] for r in R]; pt = [r["prompt_tokens"] for r in R]
        Rr = [r for r in load(t + "_roster", P)[0]]
        base25 = [r for r in R if r["request_id"] == "25-3152"]
        out.append([n, f"{statistics.median(w):.0f} ({q(w, .1):.0f}–{q(w, .9):.0f})", f"{min(w):.0f}",
                    f"{statistics.median(pt):.0f}", f"{spearman(w, pt):.2f}",
                    f"{statistics.median(r['wall_ms'] for r in base25):.0f} → {statistics.median(r['wall_ms'] for r in Rr):.0f}",
                    f"{statistics.median(r['prompt_tokens'] for r in base25):.0f} → {statistics.median(r['prompt_tokens'] for r in Rr):.0f}"])
    loc = [float(r[4]) for r in out if r[0] != "Jev"]
    print(f"ρ(wall, prompt tokens) for the six local runs: {min(loc):.2f}–{max(loc):.2f}\n")
    table(["run", "wall ms median (p10–p90)", "min wall ms", "median prompt tokens", "ρ(wall, prompt tokens)",
           "25-3152 wall ms: without → with roster", "25-3152 prompt tokens: without → with roster"], out)
    print("Ollama prefix cache (lp runs): the same model and prompt with the model kept loaded (cache can reuse the "
          "shared request prefix) vs unloaded before every call (no reuse). Server-side prefill_ms and wall_ms medians.\n")
    out = []
    for n, t1, t2 in (("4b lp", "golden_qwen3.5_4b_logprob_p2db", "golden_qwen3.5_4b_logprob_p2dbf"),
                      ("9b lp", "golden_qwen3.5_9b_logprob_p2db", "golden_qwen3.5_9b_logprob_p2dbf")):
        A = load(t1, P)[0]; B = load(t2, P)[0]
        out.append([n, f"{statistics.median(r['prefill_ms'] for r in A):.0f} → {statistics.median(r['prefill_ms'] for r in B):.0f}",
                    f"{statistics.median(r['wall_ms'] for r in A):.0f} → {statistics.median(r['wall_ms'] for r in B):.0f}"])
    table(["run", "prefill ms: cached → reloaded", "wall ms: cached → reloaded"], out)
    jr = run_config("golden_jev-1.14.0_noul_p2")
    print(f"Jev endpoint (run.json): {jr['endpoint']}; records were sent to a third-party API. Scores carry "
          f"{sum(1 for r in J if r.get('request_id_typesafe'))} TypeSafe request ids.\n")

    print("## L-8. One machine, one request at a time\n")
    out = []
    for n, t in ALL_RUNS:
        for tg in (t, t + "_roster"):
            c = run_config(tg)
            out.append([tg, c.get("concurrency"), c.get("backend", "ollama"), c.get("ollama_version", "—"), c.get("num_ctx", "—")])
    conc = collections.Counter(r[1] for r in out)
    table(["concurrency value in run.json", "runs"], [[k, v] for k, v in conc.items()])

    print("## L-9. Body truncation (8,000 characters) and attachments (names only)\n")
    trunc = {p for p, e in E.items() if len(e["body"] or "") > 8000}
    c = collections.Counter((P[p]["label"], p in trunc) for p in P)
    print(f"Bodies over 8,000 characters (the model sees the first 8,000): {len(trunc)}/{len(P)} "
          f"(positives {c[(1, True)]}/{c[(1, True)] + c[(1, False)]}, negatives {c[(0, True)]}/{c[(0, True)] + c[(0, False)]}). "
          f"Rows flagged truncated in the 27b lp scores: {sum(r['truncated'] for r in runs['27b lp'].values())}.\n")
    out = []
    for n, _ in SCORE_RUNS:
        R = runs[n]; t = point(list(R.values()))["thr"]
        tp = [R[p] for p in R if P[p]["label"] and p in trunc]; ntp = [R[p] for p in R if P[p]["label"] and p not in trunc]
        mt = sum(r["score"] < t for r in tp); mn = sum(r["score"] < t for r in ntp)
        out.append([n, f"{t:.4g}", f"{mt}/{len(tp)} ({mt / len(tp):.0%})", f"{mn}/{len(ntp)} ({mn / len(ntp):.1%})",
                    ", ".join(f"{p.split('|')[1].replace('synth:', 's:')} {R[p]['score']:.3f}{'' if R[p]['score'] >= t else ' MISSED'}"
                              for p in ("25-3152|synth:25-3152:14:02", "24-409|synth:24-409:02:01"))])
    print(f"Truncated positives missed: {min(int(r[2].split('/')[0]) for r in out)}–{max(int(r[2].split('/')[0]) for r in out)} "
          f"of {len(trunc & {p for p in P if P[p]['label']})}; other positives missed: "
          f"{min(r[3].split('(')[1].rstrip(')') for r in out)}–{max(r[3].split('(')[1].rstrip(')') for r in out)}\n")
    table(["run", "all-pairs thr98", "truncated positives missed", "other positives missed",
           "the two positives whose hook is past the cap (score)"], out)
    att = [p for p, e in E.items() if e.get("attachments")]
    pos_att_only = [p for p, e in E.items() if P[p]["label"] and e.get("attachments")
                    and hit({"attachments": e["attachments"]}, e["request_id"], headers=False)
                    and not hit({**e, "attachments": []}, e["request_id"], headers=False)]
    print(f"Emails with attachments (rendered as file names only): {len(att)}/{len(E)}. Positives whose only "
          f"keyword-proxy hit outside the headers is in an attachment name: {len(pos_att_only)} "
          f"({', '.join(p.split('|')[1] for p in pos_att_only[:8])}{' …' if len(pos_att_only) > 8 else ''}).\n")

    print("## L-10. Synthetic emails are edits of emails that are also in the set: cluster bootstrap\n")
    print("Cluster = a source email and every golden pair built from it (its own real row(s) and its synthetic edits), "
          "across both requests. Resampling clusters instead of pairs treats near-duplicates as one draw. 95% CIs, "
          f"{a.boot} resamples each.\n")
    syn = {s["id"]: s for s in map(json.loads, open("data/golden/work/synthetic.jsonl"))}
    cl = {p: (syn[e["id"]]["source_id"] if e["origin"] == "synthetic" else e["id"]) for p, e in E.items()}
    groups = collections.defaultdict(list)
    for p, c_ in cl.items():
        groups[c_].append(p)
    keys = sorted(groups)
    sizes = collections.Counter(len(v) for v in groups.values())
    print(f"Clusters: {len(keys)} for {len(P)} pairs; sizes: " + ", ".join(f"{k}×{v}" for k, v in sorted(sizes.items())) + "\n")
    rng = random.Random(a.seed + 1)
    draws_c = [rng.choices(keys, k=len(keys)) for _ in range(a.boot)]
    pos = sorted(p for p in P if P[p]["label"]); neg = sorted(p for p in P if not P[p]["label"])
    draws_p = [rng.choices(pos, k=len(pos)) + rng.choices(neg, k=len(neg)) for _ in range(a.boot)]
    out = []; wd_a = wd_e = 0.0
    for n, _ in SCORE_RUNS:
        R = runs[n]
        res = {}
        for lab, dr in (("pair", draws_p), ("cluster", [[p for k in d for p in groups[k]] for d in draws_c])):
            au, el = [], []
            for d in dr:
                s = [R[p]["score"] for p in d]; l = [P[p]["label"] for p in d]
                au.append(auroc(s, l)); el.append(at_recall(pr_curve(s, l), .98)[3])
            res[lab] = (ci(au), ci(el))
        pt = point(list(R.values()))
        (pa, pe), (ca, ce) = res["pair"], res["cluster"]
        wd_a = max(wd_a, abs((ca[1] - ca[0]) - (pa[1] - pa[0]))); wd_e = max(wd_e, abs((ce[1] - ce[0]) - (pe[1] - pe[0])))
        out.append([n, f"{pt['auroc']:.3f}", f"[{pa[0]:.3f}–{pa[1]:.3f}] ({pa[1] - pa[0]:.3f})",
                    f"[{ca[0]:.3f}–{ca[1]:.3f}] ({ca[1] - ca[0]:.3f})", f"{pt['elim']:.0%}",
                    f"[{pe[0]:.0%}–{pe[1]:.0%}] ({(pe[1] - pe[0]) * 100:.0f} pts)", f"[{ce[0]:.0%}–{ce[1]:.0%}] ({(ce[1] - ce[0]) * 100:.0f} pts)"])
    table(["run", "AUROC", "pair bootstrap CI (width)", "cluster bootstrap CI (width)", "elim@98",
           "pair bootstrap CI (width)", "cluster bootstrap CI (width)"], out)
    print(f"Largest difference in CI width, cluster vs pair: AUROC {wd_a:.3f}; elim@98 {wd_e * 100:.0f} points\n")


if __name__ == "__main__":
    main()
