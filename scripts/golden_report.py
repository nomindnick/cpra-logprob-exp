"""Golden-set report (SPEC §14): every runs/golden_*/ run, side by side.

  uv run python scripts/golden_report.py [--boot 1000]

Prints markdown tables: headline ranking metrics with bootstrap 95% CIs; per request;
by kind and by hard-negative recipe (share flagged responsive at each run's 98%-recall
threshold and at its default decision); Brier score by kind; reliability; JSON verdict
vs logprob (confidence granularity, rank correlation, decision agreement and who is
right when they disagree); latency (prefill/decode split); the 25-3152 roster ablation;
each backend setting against the clean reference run.

Run identity comes from run.json (model, mode, roster, fresh, num_gpu, num_batch); a tag containing
"_cpu" is a laptop run. With the default batch size, the ROCm GPU path for the qwen3.5 4b/9b models
(qwen35 architecture) carries recurrent state across 2,048-token prefill batches and between calls,
so those runs are unreliable. Each (model, mode, roster) appears once in the main tables. For the
4b/9b, in this order: a GPU run with num_batch >= 8192 (the clean GPU setting); a CPU run on the
Strix Halo (num_gpu 0); a default-batch GPU run. For qwen3.8:27b, which is unaffected, the
default-batch GPU run comes first (it keeps Ollama's prefix cache, so its latency is the realistic
one). Within each, a cached run (model stays loaded) beats a --fresh one (unload before every call).
Names carry a backend label only when the run isn't clean ("CPU", or "(fresh)"/"(cached)" for an
affected model at the default batch). §8 compares every other run with the chosen one, split by
prompt length (the in-prompt corruption only appears above 2,048 tokens).
Modes: lp = logprob, json = verdict first, jsonR = reasoning first.
Default decision: logprob score >= 0.5; JSON verdict == true. Stdlib only.
"""
import argparse
import collections
import json
import pathlib
import random
import statistics

from analyze import at_recall, auprc, auroc, pr_curve
from compare import ranks

KINDS = ["real_positive", "close_call_positive", "privileged_positive", "exempt_other_positive",
         "hard_negative_flipped", "real_negative", "hard_negative"]
MODELS = ["qwen3.5:4b", "qwen3.5:9b", "qwen3.8:27b"]
MODES = ["logprob", "json", "json_reason"]
AFFECTED = {"qwen3.5:4b", "qwen3.5:9b"}  # corrupted at the default batch size on ROCm (see docstring)
ABBR = {"logprob": "lp", "json": "json", "json_reason": "jsonR"}


def load_runs():
    recipe = {p["pair_id"]: p["recipe"] for p in map(json.loads, open("data/golden/pairs.jsonl"))}
    n_roster = sum(1 for _ in open("data/golden/pairs_25-3152.jsonl"))
    runs = []
    for d in sorted(pathlib.Path("runs").glob("golden_*/")):
        cfg = json.load((d / "run.json").open())
        rows = [json.loads(l) for l in (d / "scores.jsonl").open()]
        for r in rows:
            r["recipe"] = recipe.get(r["pair_id"])
        runs.append({"tag": d.name, "model": cfg["model"], "mode": cfg["mode"], "roster": bool(cfg.get("roster")),
                     "fresh": bool(cfg.get("fresh")), "cpu": cfg.get("num_gpu") == 0,
                     "bigbatch": (cfg.get("num_batch") or 0) >= 8192,
                     "machine": "laptop" if "_cpu" in d.name else "strix", "all": rows,
                     "complete": len(rows) >= (n_roster if cfg.get("roster") else len(recipe)),
                     "rows": [r for r in rows if "error" not in r and r.get("score") is not None]})
    order = lambda r: (r["machine"] != "strix", r["roster"], MODES.index(r["mode"]),
                       MODELS.index(r["model"]) if r["model"] in MODELS else 99, not r["fresh"])
    return sorted(runs, key=order)


def key(run):
    return (run["model"], run["mode"], run["roster"], run["machine"])


def best(runs):
    """One run per (model, mode, roster, machine), best rank() first (complete runs only)."""
    groups = collections.defaultdict(list)
    for r in runs:
        if r["complete"] and len(r["rows"]) >= 0.95 * len(r["all"]):  # skip runs with >5% unscored rows
            groups[key(r)].append(r)
    keep = []
    for g in groups.values():
        keep.append(min(g, key=rank))
    return [r for r in runs if any(r is k for k in keep)]


def rank(run):
    if run["model"] in AFFECTED:  # batch 8192 > CPU > default batch
        return (not run["bigbatch"], not run["cpu"], run["fresh"])
    return (run["cpu"], run["bigbatch"], run["fresh"])  # default batch > batch 8192 > CPU


def clean(run):
    return run["bigbatch"] or run["cpu"] or run["model"] not in AFFECTED


def setting(run):
    return ("CPU" if run["cpu"] else "batch 8192" if run["bigbatch"] else "default batch") + (", fresh" if run["fresh"] else "")


def name(run):
    s = f"{run['model'].split(':')[1]} {ABBR[run['mode']]}"
    return (s + (" +roster" if run["roster"] else "") + (" laptop" if run["machine"] == "laptop" else "")
            + (" CPU" if run["cpu"] else "" if clean(run) else " (fresh)" if run["fresh"] else " (cached)"))


def decide(r):
    return bool(r["verdict"]) if "verdict" in r else r["score"] >= 0.5


def thr98(rows):
    return at_recall(pr_curve([r["score"] for r in rows], [r["label"] for r in rows]), 0.98)[0]


def stats(rows):
    s = [r["score"] for r in rows]; l = [r["label"] for r in rows]
    c = pr_curve(s, l)
    neg = [r for r in rows if not r["label"]]; pos = [r for r in rows if r["label"]]
    return {"auroc": auroc(s, l), "auprc": auprc(c), "e95": at_recall(c, 0.95)[3], "e98": at_recall(c, 0.98)[3],
            "thr98": at_recall(c, 0.98)[0],
            "d_recall": sum(decide(r) for r in pos) / len(pos), "d_elim": sum(not decide(r) for r in neg) / len(neg)}


def boot(rows, n, rng):
    """95% percentile CI for AUROC and eliminated@98%, resampling pairs within each class."""
    pos = [r for r in rows if r["label"]]; neg = [r for r in rows if not r["label"]]
    a, e = [], []
    for _ in range(n):
        b = rng.choices(pos, k=len(pos)) + rng.choices(neg, k=len(neg))
        s = [r["score"] for r in b]; l = [r["label"] for r in b]
        a.append(auroc(s, l)); e.append(at_recall(pr_curve(s, l), 0.98)[3])
    ci = lambda xs: (sorted(xs)[int(.025 * n)], sorted(xs)[int(.975 * n) - 1])
    return ci(a), ci(e)


def boot_delta(a_rows, b_rows, n, rng):
    """Paired 95% CI for AUROC(b) - AUROC(a) over the same pairs, resampling within each class."""
    A = {r["pair_id"]: r for r in a_rows}; B = {r["pair_id"]: r for r in b_rows}
    ids = sorted(set(A) & set(B))
    pos = [p for p in ids if A[p]["label"]]; neg = [p for p in ids if not A[p]["label"]]
    d = []
    for _ in range(n):
        b = rng.choices(pos, k=len(pos)) + rng.choices(neg, k=len(neg))
        l = [A[p]["label"] for p in b]
        d.append(auroc([B[p]["score"] for p in b], l) - auroc([A[p]["score"] for p in b], l))
    d.sort()
    return d[int(.025 * n)], d[int(.975 * n) - 1]


def table(header, rows):
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join("---" for _ in header) + "|")
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")
    print()


def pct(x): return "—" if x is None else f"{x:.0%}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=1000)
    a = ap.parse_args()
    rng = random.Random(7)
    all_runs = load_runs()
    runs = best(all_runs)
    main_runs = [r for r in runs if not r["roster"]]

    print("# Golden-set report\n")
    print(f"Runs in the main tables: {', '.join(r['tag'] for r in runs)}\n")
    partial = [f"{r['tag']} ({len(r['all'])} rows, {len(r['rows'])} scored)" for r in all_runs
               if not r["complete"] or len(r["rows"]) < 0.95 * len(r["all"])]
    if partial:
        print(f"Incomplete or >5% unscored runs (left out of the main tables): {', '.join(partial)}\n")
    for r in all_runs:
        bad = len(r["all"]) - len(r["rows"])
        if bad:
            print(f"- {r['tag']}: {bad} rows without a score (errors / JSON parse failures)")
    print(f"Unscored rows (errors, JSON parse failures): "
          f"{sum(len(r['all']) - len(r['rows']) for r in all_runs)} of {sum(len(r['all']) for r in all_runs)}\n")
    for r in all_runs:
        if r["mode"] == "json_reason":
            first = sum(x.get("raw", "").lstrip("{ \n").startswith('"reasoning"') for x in r["rows"])
            print(f"- {r['tag']}: reasoning written first in {first}/{len(r['rows'])}")
    print()

    # ---- 1. headline ----
    print("## 1. Headline (all pairs)\n")
    out = []
    for r in main_runs:
        s = stats(r["rows"]); (alo, ahi), (elo, ehi) = boot(r["rows"], a.boot, rng)
        real = [x for x in r["rows"] if x["kind"] in ("real_positive", "real_negative")]
        out.append([name(r), len(r["rows"]), f"{s['auroc']:.3f} [{alo:.3f}–{ahi:.3f}]", f"{s['auprc']:.3f}",
                    pct(s["e95"]), f"{s['e98']:.0%} [{elo:.0%}–{ehi:.0%}]", f"{s['thr98']:.4f}",
                    pct(s["d_recall"]), pct(s["d_elim"]), f"{auroc([x['score'] for x in real], [x['label'] for x in real]):.3f}"])
    table(["run", "n", "AUROC [95% CI]", "AUPRC", "elim@95", "elim@98 [95% CI]", "thr@98",
           "default: recall", "default: elim", "AUROC real-only"], out)

    # ---- 2. per request ----
    print("## 2. Per request\n")
    out = []
    for r in main_runs:
        row = [name(r)]
        for rid in ("24-409", "25-3152"):
            s = stats([x for x in r["rows"] if x["request_id"] == rid])
            row += [f"{s['auroc']:.3f}", pct(s["e98"]), pct(s["d_recall"])]
        out.append(row)
    table(["run", "24-409 AUROC", "elim@98", "default recall", "25-3152 AUROC", "elim@98", "default recall"], out)

    # ---- 3. by kind ----
    def by_kind(title, flag, key=lambda x: x["kind"], keys=None):
        print(title)
        groups = keys or sorted({key(x) for x in main_runs[0]["rows"]})
        out = []
        for rid in ("24-409", "25-3152", "both"):
            for k in groups:
                n = sum(1 for x in main_runs[0]["rows"] if key(x) == k and rid in ("both", x["request_id"]))
                if not n:
                    continue
                lab = next(x["label"] for x in main_runs[0]["rows"] if key(x) == k)
                row = [rid, k, "+" if lab else "−", n]
                for r in main_runs:
                    t = thr98(r["rows"])
                    xs = [x for x in r["rows"] if key(x) == k and rid in ("both", x["request_id"])]
                    row.append(pct(sum(flag(x, t) for x in xs) / len(xs)))
                out.append(row)
        table(["request", "group", "label", "n"] + [name(r) for r in main_runs], out)

    print("## 3. By kind\n")
    print("Share flagged responsive. For a + group that is recall; for a − group it is the share that slips "
          "through the screen. Each run uses its own 98%-recall threshold (all pairs).\n")
    by_kind("### 3a. At each run's 98%-recall threshold\n", lambda x, t: x["score"] >= t, keys=KINDS)
    by_kind("### 3b. At the default decision (score ≥ 0.5 / JSON verdict)\n", lambda x, t: decide(x), keys=KINDS)
    hn = lambda x: x["kind"].replace("hard_negative", "hn") + "/" + str(x["recipe"]) if x["kind"].startswith("hard_negative") else "—"
    recipes = sorted({hn(x) for x in main_runs[0]["rows"]} - {"—"})
    by_kind("### 3c. Hard-negative recipes, at the 98% threshold\n", lambda x, t: x["score"] >= t, key=hn, keys=recipes)
    by_kind("### 3d. Hard-negative recipes, at the default decision\n", lambda x, t: decide(x), key=hn, keys=recipes)

    print("### 3e. Median score by kind\n")
    out = []
    for k in KINDS:
        out.append([k] + [f"{statistics.median(x['score'] for x in r['rows'] if x['kind'] == k):.3f}" for r in main_runs])
    table(["kind"] + [name(r) for r in main_runs], out)

    # ---- 4. reliability ----
    print("## 4. Score quality\n")
    print("### 4a. Brier score by kind (mean squared error of the score vs the label; lower is better)\n")
    out = []
    for k in KINDS + ["all"]:
        row = [k]
        for r in main_runs:
            xs = [x for x in r["rows"] if k in ("all", x["kind"])]
            row.append(f"{statistics.mean((x['score'] - x['label']) ** 2 for x in xs):.3f}")
        out.append(row)
    table(["kind"] + [name(r) for r in main_runs], out)
    print("### 4b. Reliability (score bucket: n / observed positive rate)\n")
    edges = [0, .05, .2, .5, .8, .95, 1.0001]
    out = []
    for r in main_runs:
        row = [name(r)]
        for lo, hi in zip(edges, edges[1:]):
            b = [x["label"] for x in r["rows"] if lo <= x["score"] < hi]
            row.append(f"{len(b)} / {sum(b) / len(b):.2f}" if b else "0")
        out.append(row)
    table(["run"] + [f"{lo:g}–{min(hi, 1):g}" for lo, hi in zip(edges, edges[1:])], out)

    # ---- 5. JSON vs logprob ----
    print("## 5. JSON verdicts vs logprob, same model\n")
    print("Default = lp score ≥ 0.5. Matched = lp threshold set so lp says yes as often as the JSON "
          "verdicts do, which compares the two at the same operating point.\n")
    out, dis = [], []
    for m in MODELS:
        lp = next((r for r in main_runs if r["model"] == m and r["mode"] == "logprob"), None)
        for jm in ("json", "json_reason"):
            js = next((r for r in main_runs if r["model"] == m and r["mode"] == jm), None)
            if not lp or not js:
                continue
            L = {x["pair_id"]: x for x in lp["rows"]}; J = {x["pair_id"]: x for x in js["rows"]}
            shared = sorted(set(L) & set(J))
            conf = collections.Counter(J[p]["confidence"] for p in shared)
            rl, rj = ranks([L[p]["score"] for p in shared]), ranks([J[p]["score"] for p in shared])
            mr = (len(shared) + 1) / 2
            rho = sum((x - mr) * (y - mr) for x, y in zip(rl, rj)) / (
                sum((x - mr) ** 2 for x in rl) * sum((y - mr) ** 2 for y in rj)) ** 0.5
            nyes = sum(decide(J[p]) for p in shared)
            t = sorted((L[p]["score"] for p in shared), reverse=True)[max(nyes - 1, 0)]
            lpm = {p: L[p]["score"] >= t for p in shared}
            pos = [p for p in shared if L[p]["label"]]; neg = [p for p in shared if not L[p]["label"]]
            rec = lambda d: sum(d(p) for p in pos) / len(pos); eli = lambda d: sum(not d(p) for p in neg) / len(neg)
            dd = [p for p in shared if decide(L[p]) != decide(J[p])]
            dm = [p for p in shared if lpm[p] != decide(J[p])]
            right = lambda ps, d: sum(d(p) == bool(L[p]["label"]) for p in ps)
            out.append([name(js), len(conf), ", ".join(f"{c:g}×{n}" for c, n in conf.most_common(3)), f"{rho:.3f}",
                        f"{len(dd)}: {right(dd, lambda p: decide(L[p]))}/{right(dd, lambda p: decide(J[p]))}",
                        f"{t:.3f}", f"{rec(lambda p: decide(J[p])):.1%} / {rec(lambda p: lpm[p]):.1%}",
                        f"{eli(lambda p: decide(J[p])):.1%} / {eli(lambda p: lpm[p]):.1%}",
                        f"{len(dm)}: {right(dm, lambda p: lpm[p])}/{right(dm, lambda p: decide(J[p]))}"])
            by = collections.Counter((L[p]["kind"], lpm[p] == bool(L[p]["label"])) for p in dm)
            dis.append([name(js)] + [f"{by[(k, True)]}/{by[(k, False)]}" for k in KINDS])
    table(["JSON run", "distinct confidences", "most common", "Spearman ρ vs lp",
           "default disagreements: lp right/JSON right", "matched lp thr", "matched recall JSON/lp",
           "matched elim JSON/lp", "matched disagreements: lp right/JSON right"], out)
    print("Matched-rate disagreements by kind (lp right / JSON right):\n")
    table(["JSON run"] + KINDS, dis)

    print("### 5b. Reasoning first vs verdict first (default decisions)\n")
    out = []
    for m in MODELS:
        js = next((r for r in main_runs if r["model"] == m and r["mode"] == "json"), None)
        jr = next((r for r in main_runs if r["model"] == m and r["mode"] == "json_reason"), None)
        if not js or not jr:
            continue
        J = {x["pair_id"]: x for x in js["rows"]}; R = {x["pair_id"]: x for x in jr["rows"]}
        shared = sorted(set(J) & set(R))
        d = [p for p in shared if decide(J[p]) != decide(R[p])]
        row = [m, f"{len(shared) - len(d)}/{len(shared)}", f"{sum(decide(R[p]) == bool(R[p]['label']) for p in d)}/{len(d)}"]
        for k in KINDS:
            ks = [p for p in shared if J[p]["kind"] == k]
            ok = lambda dec: sum(dec(p) == bool(J[p]["label"]) for p in ks)
            row.append(f"{ok(lambda p: decide(J[p]))} → {ok(lambda p: decide(R[p]))}")
        out.append(row)
    table(["model", "verdicts agree", "reasoning-first right when they differ"] +
          [f"{k} (correct: json → jsonR)" for k in KINDS], out)

    # ---- 6. latency ----
    print("## 6. Latency (median per call; single-stream)\n")
    out = []
    for r in runs:
        xs = r["rows"]; med = lambda f: statistics.median(x[f] for x in xs if x.get(f) is not None)
        tot = sorted(x["total_ms"] for x in xs)
        gen = [x["gen_tokens"] for x in xs if x.get("gen_tokens")]
        dec = sum(x["decode_ms"] for x in xs if x.get("gen_tokens"))
        out.append([name(r), r["machine"] + ", " + setting(r), f"{med('prompt_tokens'):.0f}", f"{med('prefill_ms'):.0f}",
                    f"{med('decode_ms'):.0f}", f"{statistics.median(gen):.0f}" if gen else "1",
                    f"{sum(gen) / dec * 1000:.1f}" if gen else "—", f"{med('total_ms'):.0f}",
                    f"{tot[int(.9 * len(tot))]:.0f}"])
    table(["run", "machine, setting", "prompt tok", "prefill ms", "decode ms", "gen tok", "decode tok/s", "total ms", "p90 total"], out)

    # ---- 7. roster ablation ----
    print("## 7. Roster ablation (25-3152 only)\n")
    out, kout, ft = [], [], []
    for r in [x for x in runs if x["roster"]]:
        # baseline with the same cache policy as the roster run, so the comparison isn't cached vs fresh
        cands = [x for x in all_runs if not x["roster"] and x["model"] == r["model"] and x["mode"] == r["mode"]
                 and x["machine"] == r["machine"]]
        base = next((x for x in cands if rank(x) == rank(r)), None)
        if base is None:
            continue
        rids = {x["pair_id"] for x in r["rows"]} & {x["pair_id"] for x in base["rows"]}
        B = [x for x in base["rows"] if x["pair_id"] in rids]; R = [x for x in r["rows"] if x["pair_id"] in rids]
        sb, sr = stats(B), stats(R)
        mean = lambda xs, lab: statistics.mean(x["score"] for x in xs if x["label"] == lab)
        lo, hi = boot_delta(B, R, a.boot, rng)
        out.append([name(base), f"{sb['auroc']:.3f} → {sr['auroc']:.3f}", f"{sr['auroc'] - sb['auroc']:+.3f} [{lo:+.3f}, {hi:+.3f}]",
                    f"{sb['e98']:.0%} → {sr['e98']:.0%}",
                    f"{sb['d_recall']:.0%} → {sr['d_recall']:.0%}", f"{sb['d_elim']:.0%} → {sr['d_elim']:.0%}",
                    f"{mean(B, 1):.2f} → {mean(R, 1):.2f}", f"{mean(B, 0):.2f} → {mean(R, 0):.2f}"])
        Bk = {x["pair_id"]: x for x in B}
        row = [name(base)]
        for k in KINDS:
            ks = [x for x in R if x["kind"] == k]
            if ks:
                row.append(f"{statistics.mean(x['score'] - Bk[x['pair_id']]['score'] for x in ks):+.2f}")
            else:
                row.append("—")
        kout.append(row)
        if r["mode"] == "logprob":
            for lbl, xs in (("without", B), ("with", R)):
                c = collections.Counter(x["first_token"] for x in xs)
                ft.append([name(base), lbl, ", ".join(f"{t!r}×{n}" for t, n in c.most_common()),
                           f"{statistics.median(x['residual'] for x in xs):.4f}", f"{max(x['residual'] for x in xs):.3f}"])
    table(["run", "AUROC", "ΔAUROC [paired 95% CI]", "elim@98", "default recall", "default elim", "mean score +", "mean score −"], out)
    print("Mean score change from adding the roster, by kind:\n")
    table(["run"] + KINDS, kout)
    print("First token and residual mass (logprob runs):\n")
    table(["run", "roster", "first tokens", "residual median", "residual max"], ft)


    # ---- 8. backend settings ----
    print("## 8. Backend settings: each run vs the chosen run of the same model and mode\n")
    print("Δ = run − reference score for the same pair; the reference is the run in the main tables. "
          "Prompts above 2,048 tokens span more than one default prefill batch. 'Identical' = |Δ| < 1e-6.\n")
    out = []
    for f in runs:
        for c in sorted([r for r in all_runs if key(r) == key(f) and r is not f and r["complete"]], key=rank):
            F = {x["pair_id"]: x for x in f["rows"]}
            cs = {x["pair_id"]: x for x in c["rows"]}
            shared = [p for p in F if p in cs]
            if len(shared) < 20:
                continue
            d = {p: abs(cs[p]["score"] - F[p]["score"]) for p in shared}
            short = [d[p] for p in shared if F[p]["prompt_tokens"] <= 2048]
            long = [d[p] for p in shared if F[p]["prompt_tokens"] > 2048]
            m = lambda xs: f"{statistics.mean(xs):.3f} (n={len(xs)})" if xs else "—"
            sc, sf = stats([cs[p] for p in shared]), stats([F[p] for p in shared])
            t = thr98([F[p] for p in shared])
            cross = sum((cs[p]["score"] >= t) != (F[p]["score"] >= t) for p in shared)
            out.append([f"{f['model'].split(':')[1]} {ABBR[f['mode']]}{' +roster' if f['roster'] else ''}",
                        f"{setting(c)} vs {setting(f)}", len(shared), sum(x < 1e-6 for x in d.values()),
                        f"{sc['auroc']:.3f} → {sf['auroc']:.3f}", f"{sc['e98']:.0%} → {sf['e98']:.0%}",
                        m(short), m(long), sum(x > 0.1 for x in d.values()), cross])
    table(["model, mode", "run vs reference", "pairs", "identical", "AUROC run → reference", "elim@98 run → reference",
           "mean |Δ| ≤2,048 tok", "mean |Δ| >2,048 tok", "|Δ| > 0.1", "cross ref thr98"], out)

if __name__ == "__main__":
    main()
