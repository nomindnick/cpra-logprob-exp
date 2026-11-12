"""Independent verification of docs/analysis/A-cutoffs.md (branch A, cutoffs). Skeptic's script.

  uv run python scripts/analysis/a_cutoffs_verify.py

Stdlib only, deterministic. It does NOT import the analyst's a_cutoffs_*.py scripts or the repo helpers
(analyze.py, golden_report.py). It reads data/golden/pairs.jsonl and runs/<tag>/scores.jsonl itself and
implements every metric from scratch:

  thr98 (and the 99% / 100% versions) as an order statistic: with P positives and m = the largest number
      of misses that keeps recall >= target (integer arithmetic), the cutoff is the (m+1)-th lowest
      positive score. A pair is flagged when score >= cutoff, so ties at the cutoff are flagged. This is
      a different algorithm from the repo's PR-curve scan.
  elim  = negatives with score < cutoff, divided by all negatives.
  AUROC = Mann-Whitney: the share of (positive, negative) pairs where the positive scores higher, ties 1/2.

The A4 `lowest` and `lowest/10` sample rules are checked EXACTLY (no simulation) from the distribution of
the lowest sampled responsive email: given k responsive emails sampled at random from the P positives,
P(lowest sampled is in tie-group g) = [C(A_g, k) - C(A_g+, k)] / C(P, k), where A_g counts positives
scoring >= the group's score and A_g+ those scoring above it. k is hypergeometric (as-is design: n drawn
from the request's pool) or Binomial(n, 0.2) (the analyst's 20% design). The misses for that outcome are
the positives scoring below the rule's cutoff (all of them unsampled). This needs no random numbers.

Sections V1-V12 print the recomputed value next to what the md states.
"""
import json
import math
import os
import pathlib
import random
import statistics
import zlib

os.chdir(pathlib.Path(__file__).resolve().parents[2])  # reads data/ and runs/ by relative path
PAIRS = {p["pair_id"]: p for p in map(json.loads, open("data/golden/pairs.jsonl"))}
MODELS = [
    ("4b lp", "golden_qwen3.5_4b_logprob_p2db"),
    ("9b lp", "golden_qwen3.5_9b_logprob_p2db"),
    ("27b lp", "golden_qwen3.8_27b_logprob_p2"),
    ("d3-4b", "golden_d3-ctx8k_4b_noul_p2"),
    ("d3-9b", "golden_d3-ctx8k_9b_noul_p2"),
    ("d3-27b", "golden_d3-ctx8k_27b_noul_p2"),
    ("Jev", "golden_jev-1.14.0_noul_p2"),
]
JSON = [("4b json", "golden_qwen3.5_4b_json_p2"), ("9b json", "golden_qwen3.5_9b_json_p2"),
        ("27b json", "golden_qwen3.8_27b_json_p2"), ("4b jsonR", "golden_qwen3.5_4b_json_reason_p2"),
        ("9b jsonR", "golden_qwen3.5_9b_json_reason_p2"), ("27b jsonR", "golden_qwen3.8_27b_json_reason_p2")]
# headline of docs/findings-golden.md §1 on the labels of 2026-11-11 (the brief's 2026-10-31 values were 0.923/52, 0.942/71,
# 0.975/76, 0.884/54, 0.947/68, 0.979/81, 0.916/63)
HEADLINE = {"4b lp": (0.922, 53, 504), "9b lp": (0.945, 72, 855), "27b lp": (0.977, 77, 2639),
            "d3-4b": (0.901, 55, 876), "d3-9b": (0.957, 70, 1425), "d3-27b": (0.983, 83, 4661),
            "Jev": (0.917, 64, 117)}


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def read(tag):
    """Rows of one run, label/kind from pairs.jsonl; drop pair_ids not in the golden set and null scores."""
    out, dropped = [], 0
    for line in open(f"runs/{tag}/scores.jsonl"):
        r = json.loads(line)
        if r["pair_id"] not in PAIRS:
            continue
        if r.get("score") is None or "error" in r:
            dropped += 1
            continue
        p = PAIRS[r["pair_id"]]
        out.append({"id": r["pair_id"], "req": p["request_id"], "y": p["label"], "kind": p["kind"],
                    "s": float(r["score"]), "verdict": r.get("verdict"), "wall": r.get("wall_ms")})
    return out, dropped


def subsets(tag):
    base, _ = read(tag)
    ros, _ = read(tag + "_roster")
    a = [r for r in base if r["req"] == "24-409"]
    b = [r for r in base if r["req"] == "25-3152"]
    return {"24-409": a, "25-3152": b, "25-3152+R": ros, "pooled": a + b, "pooled+R": a + ros, "_base": base}


def allowed(P, target):
    # largest m with (P - m) / P >= target, in integers: P - m >= ceil(target * P)
    need = math.ceil(round(target * P, 9))
    return P - need


def thr(rows, target=0.98):
    pos = sorted(r["s"] for r in rows if r["y"])
    return pos[allowed(len(pos), target)]


def ev(rows, c):
    P = sum(r["y"] for r in rows)
    N = len(rows) - P
    miss = sum(1 for r in rows if r["y"] and r["s"] < c)
    el = sum(1 for r in rows if not r["y"] and r["s"] < c)
    return miss, P, el, N


def auroc(rows):
    pos = [r["s"] for r in rows if r["y"]]
    neg = [r["s"] for r in rows if not r["y"]]
    w = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
    return w / (len(pos) * len(neg))


def logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def shrink(p, f):
    return 1 / (1 + math.exp(-(logit(p) - math.log(f))))


def pct(a, b):
    return f"{a}/{b} ({a / b:.0%})"


def head(t):
    print(f"\n## {t}\n")


def exact_rule(rows, n, design, rule):
    """Exact P(remainder recall >= 98%) and, for the 20% design, the exact median eliminated share."""
    pos = sorted(r["s"] for r in rows if r["y"])
    neg = sorted(r["s"] for r in rows if not r["y"])
    P, N = len(pos), len(neg)
    M = len(rows)
    groups = sorted(set(pos))
    ge = {g: sum(1 for x in pos if x >= g) for g in groups}
    gt = {g: sum(1 for x in pos if x > g) for g in groups}
    if design == "as-is":
        pk = {k: math.comb(P, k) * math.comb(M - P, n - k) / math.comb(M, n) for k in range(0, min(n, P) + 1)}
    else:
        pk = {k: math.comb(n, k) * 0.2 ** k * 0.8 ** (n - k) for k in range(0, n + 1)}
    p98, dist = 0.0, []
    for k, w in pk.items():
        if w == 0:
            continue
        if k == 0:  # nothing to set the cutoff from: review everything
            p98 += w
            dist.append((0.0, w))
            continue
        a = math.floor(0.02 * (P - k) + 1e-9)
        tot = math.comb(P, k)
        for g in groups:
            pg = (math.comb(ge[g], k) - math.comb(gt[g], k)) / tot
            if pg == 0:
                continue
            c = g if rule == "lowest" else shrink(g, 10)
            miss = sum(1 for x in pos if x < c)
            if miss <= a:
                p98 += w * pg
            dist.append((sum(1 for x in neg if x < c) / N, w * pg))
    dist.sort()
    cum, med = 0.0, None
    for v, w in dist:
        cum += w
        if cum > 0.5 - 1e-12:
            med = v
            break
    return p98, med


def boot_gap(r1, r2, reps, seed):
    """Stratified bootstrap of logit(thr98 on r1) - logit(thr98 on r2), resampling each request separately."""
    rng = random.Random(seed)
    split = lambda rows: ([r for r in rows if r["y"]], [r for r in rows if not r["y"]])
    p1, n1 = split(r1)
    p2, n2 = split(r2)
    ds = []
    for _ in range(reps):
        a = rng.choices(p1, k=len(p1)) + rng.choices(n1, k=len(n1))
        b = rng.choices(p2, k=len(p2)) + rng.choices(n2, k=len(n2))
        ds.append(logit(thr(a)) - logit(thr(b)))
    ds.sort()
    return ds[int(0.025 * reps)], ds[int(0.975 * reps) - 1], sum(d > 0 for d in ds) / reps


def main():
    D = {m: subsets(t) for m, t in MODELS}

    head("V1. Data integrity")
    for m, t in MODELS:
        d = D[m]
        ids_b = [r["id"] for r in d["_base"]]
        ids_r = [r["id"] for r in d["25-3152+R"]]
        print(f"- {m}: 24-409 {len(d['24-409'])} pairs ({sum(r['y'] for r in d['24-409'])}+), 25-3152 "
              f"{len(d['25-3152'])} ({sum(r['y'] for r in d['25-3152'])}+), 25-3152+R {len(d['25-3152+R'])} "
              f"({sum(r['y'] for r in d['25-3152+R'])}+); duplicate ids: {len(ids_b) - len(set(ids_b))}/"
              f"{len(ids_r) - len(set(ids_r))}; roster ids == 25-3152 ids: "
              f"{set(ids_r) == {r['id'] for r in d['25-3152']}}")
    for lab in ("24-409", "25-3152"):
        ps = [p for p in PAIRS.values() if p["request_id"] == lab and p["label"]]
        print(f"- real_positive share of {lab} positives: {pct(sum(p['kind'] == 'real_positive' for p in ps), len(ps))}")

    head("V2. Headline: pooled AUROC, thr98, elim@98, median wall ms (from scratch) vs the brief")
    print("| model | AUROC (brief) | pooled thr98 | elim@98 (brief) | median wall ms (brief) |")
    print("|---|---|---|---|---|")
    for m, _ in MODELS:
        rows = D[m]["pooled"]
        c = thr(rows)
        mi, P, el, N = ev(rows, c)
        a, e, w = HEADLINE[m]
        wall = statistics.median(r["wall"] for r in D[m]["_base"])
        print(f"| {m} | {auroc(rows):.3f} ({a}) | {c:.4f} | {pct(el, N)} misses {mi}/{P} ({e}%) | {wall:.0f} ({w}) |")

    head("V3. Per-request oracle thr98 (md A1a point estimates)")
    print("| model | 24-409 | 25-3152 | 25-3152+R | pooled | pooled+R |")
    print("|---|---|---|---|---|---|")
    for m, _ in MODELS:
        print(f"| {m} | " + " | ".join(f"{thr(D[m][s]):.4f}" for s in ("24-409", "25-3152", "25-3152+R", "pooled", "pooled+R")) + " |")

    head("V4. Headline cutoff per request (md A1c), and a null model for how lopsided the 5 misses are")
    lop = {"pooled": 0, "pooled+R": 0}
    for m, _ in MODELS:
        for pooled, parts in (("pooled", ("24-409", "25-3152")), ("pooled+R", ("24-409", "25-3152+R"))):
            c = thr(D[m][pooled])
            r = [ev(D[m][p], c) for p in parts]
            tot = ev(D[m][pooled], c)[0]
            lop[pooled] += any(x[0] == tot for x in r)
            print(f"- {m} {pooled}: cutoff {c:.4f}, misses {tot} pooled = {r[0][0]} on 24-409 + {r[1][0]} on {parts[1]}")
    # If the 5 pooled misses were 5 positives drawn at random from all positives, how often would all 5 land on one request?
    p_one = (math.comb(NP["24-409"], 5) + math.comb(NP["25-3152"], 5)) / math.comb(N_POS, 5)
    print(f"\nModels with all pooled misses on one request: {lop['pooled']}/7 (pooled), {lop['pooled+R']}/7 (pooled+R).")
    print(f"Null: P(all 5 on one request | misses spread at random over the {N_POS} positives) = {p_one:.3f} "
          f"(expected {7 * p_one:.2f} of 7 models).")

    head("V5. Is the between-request gap in thr98 bigger than resampling noise? (bootstrap of the difference)")
    print("Stratified bootstrap, 2,000 resamples, each request resampled on its own; d = logit(thr98 24-409) - "
          "logit(thr98 other). This tests the difference directly instead of comparing two intervals.\n")
    print("| model | other | d (point) | 95% interval of d | share of resamples with d > 0 | two-sided p | below 0.05/14 (Bonferroni over 14)? |")
    print("|---|---|---|---|---|---|---|")
    for m, _ in MODELS:
        for other in ("25-3152", "25-3152+R"):
            d0 = logit(thr(D[m]["24-409"])) - logit(thr(D[m][other]))
            lo, hi, share = boot_gap(D[m]["24-409"], D[m][other], 2000, zlib.crc32(f"V5|{m}|{other}".encode()))
            flag = "excludes 0" if lo > 0 or hi < 0 else "includes 0"
            p2 = 2 * min(share, 1 - share)  # two-sided bootstrap p-value
            bonf = "yes" if p2 < 0.05 / 14 else "no"
            print(f"| {m} | {other} | {d0:+.2f} | [{lo:+.2f}, {hi:+.2f}] ({flag}) | {share:.3f} | {p2:.3f} | {bonf} |")

    head("V6. The lowest positives (md A1d): slots vs distinct emails")
    slots, ids = [], set()
    for m, _ in MODELS:
        for s in ("24-409", "25-3152", "25-3152+R"):
            low = sorted((r for r in D[m][s] if r["y"]), key=lambda r: r["s"])[:3]
            slots += low
            ids |= {r["id"] for r in low}
    real_ids = {i for i in ids if PAIRS[i]["kind"] == "real_positive"}
    print(f"- slots: {len(slots)}, real in slots: {sum(r['kind'] == 'real_positive' for r in slots)}")
    print(f"- distinct emails in those slots: {len(ids)}, of which real: {len(real_ids)}")
    low27 = sorted((r["s"] for r in D["27b lp"]["25-3152"] if r["y"]))[:4]
    print(f"- 27b lp, 25-3152, four lowest positives: {', '.join(f'{x:.4f}' for x in low27)}; misses at 0.05: "
          f"{ev(D['27b lp']['25-3152'], 0.05)[0]}; at 0.0565: {ev(D['27b lp']['25-3152'], 0.0565)[0]}; at 0.0567: "
          f"{ev(D['27b lp']['25-3152'], 0.0567)[0]} (2 allowed)")

    head("V7. Transfer (md A2b/A2c): target misses / eliminated, and the real share of the misses")
    dirs = [("24-409", "25-3152"), ("25-3152", "24-409"), ("24-409", "25-3152+R"), ("25-3152+R", "24-409")]
    print("| model | level | " + " | ".join(f"{a} → {b}" for a, b in dirs) + " | passing |")
    print("|---|---|" + "---|" * len(dirs) + "---|")
    forced_ok = True
    for m, _ in MODELS:
        for lv in (0.98, 1.0):
            cells, ok = [], 0
            for a, b in dirs:
                c = thr(D[m][a], lv)
                mi, P, el, N = ev(D[m][b], c)
                passed = mi <= allowed(P, 0.98)
                ok += passed
                real = sum(1 for r in D[m][b] if r["y"] and r["s"] < c and r["kind"] == "real_positive")
                cells.append(f"{mi}/{P} (real {real}) · {el / N:.0%}" + ("" if passed else " FAIL"))
                if lv == 0.98 and passed:  # forced: a passing transfer can't eliminate more than the target's oracle
                    forced_ok &= el <= ev(D[m][b], thr(D[m][b]))[2]
            print(f"| {m} | {lv:.0%} | " + " | ".join(cells) + f" | {ok}/4 |")
    print(f"\nEvery passing 98% transfer eliminates <= the target's own oracle elim@98: {forced_ok}")

    head("V8. Fixed cutoffs (md A3a-A3c): misses at 0.5, JSON verdicts, largest safe grid value")
    grid = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5]
    for m, _ in MODELS:
        e = {s: ev(D[m][s], 0.5) for s in ("24-409", "25-3152", "25-3152+R")}
        safe = [c for c in grid if all(ev(D[m][s], c)[0] <= 2 for s in ("24-409", "25-3152"))]
        fail = min(thr(D[m]["24-409"]), thr(D[m]["25-3152"]))
        print(f"- {m} @0.5: misses {e['24-409'][0]}/{NP['24-409']}, {e['25-3152'][0]}/{NP['25-3152']}, +R {e['25-3152+R'][0]}/{NP['25-3152']}; elim "
              f"{e['24-409'][2]}/{NN['24-409']}, {e['25-3152'][2]}/{NN['25-3152']}, +R {e['25-3152+R'][2]}/{NN['25-3152']}; largest grid value safe on "
              f"24-409 + 25-3152: {max(safe) if safe else None} (fails above {fail:.4f})")
    dropped = 0
    for m, t in JSON:
        base, d1 = read(t)
        ros, d2 = read(t + "_roster")
        dropped += d1 + d2
        out = []
        for name, rows in (("24-409", [r for r in base if r["req"] == "24-409"]),
                           ("25-3152", [r for r in base if r["req"] == "25-3152"]), ("25-3152+R", ros),
                           ("pooled+R", [r for r in base if r["req"] == "24-409"] + ros)):
            P = sum(r["y"] for r in rows)
            mi = sum(1 for r in rows if r["y"] and not r["verdict"])
            el = sum(1 for r in rows if not r["y"] and not r["verdict"])
            out.append(f"{name} {mi}/{P} miss, elim {el}/{len(rows) - P}" + ("" if mi <= allowed(P, 0.98) else " FAIL"))
        print(f"- {m}: " + "; ".join(out))
    print(f"- JSON rows dropped for a null score: {dropped}")

    head("V9. Sample rules (md A4), computed exactly instead of simulated")
    print("P(recall >= 98% on the unreviewed positives) at n = 50, and for the 20% design the exact median "
          "eliminated share. md (simulated, 1,000 reps) states: `lowest` 0.46-0.63 as-is and 0.17-0.24 at 20%; "
          "`lowest/10` at 20% >= 0.90 except 27b lp 0.54/0.64/0.71; `lowest/10` 20% median elim on 25-3152 "
          "4b lp 4%, d3-4b 2%, Jev 0%; d3-27b 73%/62%/93%.\n")
    print("| model | request | lowest as-is | lowest 20% | lowest/10 as-is | lowest/10 20% | lowest/10 20% median elim |")
    print("|---|---|---|---|---|---|---|")
    lo_as, lo_20 = [], []
    for m, _ in MODELS:
        for s in ("24-409", "25-3152", "25-3152+R"):
            a, _ = exact_rule(D[m][s], 50, "as-is", "lowest")
            b, _ = exact_rule(D[m][s], 50, "20%", "lowest")
            c, _ = exact_rule(D[m][s], 50, "as-is", "lowest/10")
            d, med = exact_rule(D[m][s], 50, "20%", "lowest/10")
            lo_as.append(a)
            lo_20.append(b)
            print(f"| {m} | {s} | {a:.3f} | {b:.3f} | {c:.3f} | {d:.3f} | {med:.0%} |")
    print(f"\nExact `lowest` range at n = 50: as-is {min(lo_as):.3f}-{max(lo_as):.3f}; 20% {min(lo_20):.3f}-{max(lo_20):.3f}")
    print(f"Beta(1,k) theory 1 - 0.98^k: k=29 {1 - 0.98 ** 29:.3f}, k=10 {1 - 0.98 ** 10:.3f}; "
          f"k for 90%: {math.ceil(math.log(0.1) / math.log(0.98))}")

    head("V10. A5e: largest value of the extended grid safe on all three subsets, one step lower, gap to headline")
    ext = [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    gaps = {"pooled": [], "pooled+R": []}
    for m, _ in MODELS:
        ok = [c for c in ext if all(ev(D[m][s], c)[0] <= 2 for s in ("24-409", "25-3152", "25-3152+R"))]
        h = ext[max(ext.index(max(ok)) - 1, 0)]
        cells = []
        for pooled in ("pooled", "pooled+R"):
            hd = ev(D[m][pooled], thr(D[m][pooled]))[2]
            rl = ev(D[m][pooled], h)[2]
            gaps[pooled].append(round((hd - rl) / N_NEG * 100))
            cells.append(f"{pooled}: headline {hd}/{N_NEG}, rule {rl}/{N_NEG}, gap {(hd - rl) / N_NEG * 100:+.0f}")
        mx = max(ev(D[m][s], h)[0] for s in ("24-409", "25-3152", "25-3152+R"))
        print(f"- {m}: largest safe {max(ok):g}, one step lower {h:g} (max misses per request {mx}); " + "; ".join(cells))
    print(f"\nGap range: no roster {min(gaps['pooled'])}-{max(gaps['pooled'])} pts; roster "
          f"{min(gaps['pooled+R'])}-{max(gaps['pooled+R'])} pts")

    head("V11. Jev ties")
    for s in ("24-409", "25-3152", "25-3152+R"):
        rows = D["Jev"][s]
        c = thr(rows)
        print(f"- {s}: {len({r['s'] for r in rows})} distinct scores over {len(rows)} pairs; thr98 {c:.2f}; positives "
              f"tied at thr98: {sum(1 for r in rows if r['y'] and r['s'] == c)}; negatives tied: "
              f"{sum(1 for r in rows if not r['y'] and r['s'] == c)}")

    head("V12. Ratio of needed n at 20% vs the golden prevalence implied by the design alone")
    for s, P, M in (("24-409", NP["24-409"], NR["24-409"]), ("25-3152", NP["25-3152"], NR["25-3152"])):
        N = M - P
        lit = round(N / 4)  # positives kept if all negatives stay and the pool is to be 20% responsive
        print(f"- {s}: golden prevalence {P}/{M} = {P / M:.3f}; ratio to 20% = {P / M / 0.2:.2f}; a literal "
              f"subsample to 20% keeping all {N} negatives keeps {lit} positives, so 98% recall on them allows "
              f"{allowed(lit, 0.98)} misses")

    head("V13. Checks of two explanations in the md")
    print("(a) 'because the roster raised their 25-3152 scores' (A2): median score on the same 249 pairs\n")
    for m, _ in MODELS:
        cells = []
        for y, nm in ((1, "positives"), (0, "negatives")):
            a = statistics.median(r["s"] for r in D[m]["25-3152"] if r["y"] == y)
            b = statistics.median(r["s"] for r in D[m]["25-3152+R"] if r["y"] == y)
            cells.append(f"{nm} {a:.3f} -> {b:.3f}")
        print(f"- {m}: " + "; ".join(cells))
    print("\n(b) 'their negatives score just below their positives' (A4, lowest/10 at 20% on 25-3152)\n")
    for m in ("4b lp", "d3-4b", "Jev", "d3-27b"):
        rows = D[m]["25-3152"]
        neg = sorted(r["s"] for r in rows if not r["y"])
        pos = sorted(r["s"] for r in rows if r["y"])
        low10 = statistics.median(shrink(x, 10) for x in pos)  # cutoff if the median positive were the lowest sampled
        print(f"- {m}: negatives' 10th/50th pct {neg[len(neg) // 10]:.3f}/{statistics.median(neg):.3f}; lowest 3 positives "
              f"{', '.join(f'{x:.3f}' for x in pos[:3])}; negatives below 0.05: {sum(x < 0.05 for x in neg)}/{len(neg)}, "
              f"below 0.10: {sum(x < 0.10 for x in neg)}/{len(neg)}; negatives above the 3rd-lowest positive: "
              f"{sum(x >= pos[2] for x in neg)}/{len(neg)}")

    head("V14. Does the between-request gap survive with only the real (county-produced) positives?")
    print("thr98 recomputed with each request's synthetic positives removed (75 real positives per request; "
          "98% then allows 1 miss). Negatives unchanged.\n")
    print("| model | 24-409 all | 24-409 real only | 25-3152 all | 25-3152 real only | 25-3152+R all | 25-3152+R real only |")
    print("|---|---|---|---|---|---|---|")
    for m, _ in MODELS:
        cells = []
        for s in ("24-409", "25-3152", "25-3152+R"):
            real = [r for r in D[m][s] if not r["y"] or r["kind"] == "real_positive"]
            cells += [f"{thr(D[m][s]):.4f}", f"{thr(real):.4f}"]
        print(f"| {m} | " + " | ".join(cells) + " |")

    head("V15. Independent bootstrap intervals for the three 'disjoint' claims (md A1a), own seeds, 2,000 resamples")
    for m in ("27b lp", "d3-27b", "Jev", "9b lp"):
        out = []
        for s in ("24-409", "25-3152"):
            rng = random.Random(zlib.crc32(f"V15|{m}|{s}".encode()))
            pos = [r for r in D[m][s] if r["y"]]
            neg = [r for r in D[m][s] if not r["y"]]
            cs = sorted(thr(rng.choices(pos, k=len(pos)) + rng.choices(neg, k=len(neg))) for _ in range(2000))
            out.append(f"{s} {thr(D[m][s]):.4f} [{cs[50]:.4f}-{cs[1949]:.4f}]")
        print(f"- {m}: " + "; ".join(out))
    setters = []
    for m, _ in MODELS:
        for s in ("24-409", "25-3152", "25-3152+R"):
            setters.append(sorted((r for r in D[m][s] if r["y"]), key=lambda r: r["s"])[2])
    ids = {r["id"] for r in setters}
    print(f"\n3rd-lowest positives (md A1d 'at thr98'): {len(setters)} slots, {sum(r['kind'] == 'real_positive' for r in setters)} "
          f"real; {len(ids)} distinct emails, {sum(PAIRS[i]['kind'] == 'real_positive' for i in ids)} real")


if __name__ == "__main__":
    main()
