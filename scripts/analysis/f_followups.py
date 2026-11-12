"""Follow-ups from the completeness critique of docs/analysis/conclusions.md. Stdlib only.

  uv run python scripts/analysis/f_followups.py

Prints:
  F1  workload at the recommended fixed cutoffs (d3-27b 0.4 / 0.5, 27b lp 0.02) and at the pooled in-sample thr98,
      per 10,000 hits at 20% responsive, under three negative mixes: B's plausible 50/50 real/hard mix, all hard
      negatives, and in-window hard negatives only (what a search that applies the date window leaves).
      Misses with Wilson 95% intervals, per-request misses, and the real-positives-only sensitivity.
  F2  scope dependence of d3-27b vs 27b lp on 25-3152: the 19 positives where an ACPG member is only one of
      >= 10 recipients and the group isn't named (c_misses_verify.py's rule), kept as labeled, dropped, or
      relabeled non-responsive; main runs and roster runs; paired bootstrap of the gap.
  F3  detection power of a random-sample check: the chance that a sample of n hits holds at least one
      responsive email scoring below a cutoff that misses a share f of responsive emails, at 20% responsive.
  F4  d3 / stock latency ratios on the same pairs, with the statistic named.

Labels, kinds and recipes come from data/golden/pairs.jsonl (golden_report.load_runs), never from scores.jsonl.
"""
import math
import pathlib
import random
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import c_misses_verify as cv  # noqa: E402  (rule helpers; its main is guarded)
from analyze import at_recall, auroc, pr_curve  # noqa: E402
from golden_report import load_runs  # noqa: E402

SEED = 20261106
N_BOOT = 1000
P_RESP = 0.20  # responsive share among hits (B's plausible scenario)
WRONG_DATE = "same_subject_wrong_date"
TAGS = {
    "27b lp": "golden_qwen3.8_27b_logprob_p2", "d3-27b": "golden_d3-ctx8k_27b_noul_p2",
    "9b lp": "golden_qwen3.5_9b_logprob_p2db", "Jev": "golden_jev-1.14.0_noul_p2",
    "4b lp": "golden_qwen3.5_4b_logprob_p2db", "d3-4b": "golden_d3-ctx8k_4b_noul_p2",
    "d3-9b": "golden_d3-ctx8k_9b_noul_p2",
}
RUNS = {r["tag"]: r["rows"] for r in load_runs()}


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def thr98(rows):
    return at_recall(pr_curve([r["score"] for r in rows], [r["label"] for r in rows]), 0.98)[0]


def rate(rows, t):
    return sum(r["score"] >= t for r in rows) / len(rows)


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), c + h


def groups(rows, positives="all"):
    pos = [r for r in rows if r["label"] == 1 and (positives == "all" or r["kind"] == "real_positive")]
    real = [r for r in rows if r["kind"] == "real_negative"]
    hard = [r for r in rows if r["kind"] == "hard_negative"]
    inwin = [r for r in hard if r["recipe"] != WRONG_DATE]
    return pos, real, hard, inwin


def flagged(pos, real, hard, inwin, t, mix):
    neg = {"50/50": (rate(real, t) + rate(hard, t)) / 2, "hard": rate(hard, t), "in-window hard": rate(inwin, t)}[mix]
    return 10_000 * (P_RESP * rate(pos, t) + (1 - P_RESP) * neg)


def f1():
    print("## F1. Workload at the recommended fixed cutoffs, per 10,000 hits at 20% responsive\n")
    print("Flagged = emails a person reads. [CI] = 2.5-97.5% of a bootstrap that resamples each group (positives, "
          "real negatives, hard negatives) separately. Misses use a Wilson 95% interval on the miss rate.\n")
    print("| config | cutoff | flagged: 50/50 mix [CI] | flagged: all hard | flagged: in-window hard [CI] | "
          "reviewer h at 30 s (50/50 - in-window) | missed per 10,000 [Wilson] | misses 24-409 / 25-3152 | "
          "real positives only: missed per 10,000 [Wilson] |")
    print("|---|---|---|---|---|---|---|---|---|")
    rng = random.Random(SEED)
    for name, cut in [("d3-27b", 0.4), ("d3-27b", 0.5), ("d3-27b", None), ("27b lp", 0.02), ("27b lp", None),
                      ("9b lp", None), ("Jev", None)]:
        rows = RUNS[TAGS[name]]
        t = thr98(rows) if cut is None else cut
        pos, real, hard, inwin = groups(rows)
        boot = {"50/50": [], "in-window hard": []}
        for _ in range(N_BOOT):
            b = [rng.choices(g, k=len(g)) for g in (pos, real, hard)]
            bi = [r for r in b[2] if r["recipe"] != WRONG_DATE]
            for mix in boot:
                boot[mix].append(flagged(b[0], b[1], b[2], bi, t, mix))
        ci = {m: sorted(v) for m, v in boot.items()}
        lo_hi = lambda m: f"[{ci[m][int(.025 * N_BOOT)]:,.0f}-{ci[m][int(.975 * N_BOOT) - 1]:,.0f}]"
        f_mix, f_hard, f_in = (flagged(pos, real, hard, inwin, t, m) for m in ("50/50", "hard", "in-window hard"))
        k = sum(r["score"] < t for r in pos); lo, hi = wilson(k, len(pos))
        rp = [r for r in pos if r["kind"] == "real_positive"]; kr = sum(r["score"] < t for r in rp); rlo, rhi = wilson(kr, len(rp))
        per_req = " / ".join(f"{sum(r['score'] < t for r in pos if r['request_id'] == q)}/"
                             f"{sum(r['request_id'] == q for r in pos)}" for q in ("24-409", "25-3152"))
        label = f"{cut}" if cut is not None else f"thr98 = {t:.4f} (in-sample)"
        print(f"| {name} | {label} | {f_mix:,.0f} {lo_hi('50/50')} | {f_hard:,.0f} | {f_in:,.0f} {lo_hi('in-window hard')} | "
              f"{f_mix * 30 / 3600:.1f} - {f_in * 30 / 3600:.1f} | {2000 * k / len(pos):.0f} [{2000 * lo:.0f}-{2000 * hi:.0f}] "
              f"({k}/{len(pos)}) | {per_req} | {2000 * kr / len(rp):.0f} [{2000 * rlo:.0f}-{2000 * rhi:.0f}] ({kr}/{len(rp)}) |")
    print("\nReading all 10,000 takes 83.3 h at 30 s per email. The in-window column assumes every non-responsive hit "
          f"is as hard as the synthetic in-window near misses ({len(inwin)} of them), so it is a pessimistic bound; a real "
          "date-filtered search also returns easy emails.\n")


def f2():
    print("## F2. d3-27b vs 27b lp on 25-3152, depending on the 'one member among many recipients' reading\n")
    p25 = [pid for pid, p in cv.P.items() if p["request_id"] == "25-3152" and p["label"] == 1]
    rule = {pid for pid in p25 if cv.member_recipient_only(cv.email(pid)) and not cv.acpg_visible(cv.email(pid))
            and cv.recipients(cv.email(pid)) >= 10}
    print(f"Rule positives (member only a recipient, ACPG not named, >= 10 recipients): {len(rule)} of {len(p25)}.\n")
    print("| runs | reading | 27b lp AUROC / elim@98 | d3-27b AUROC / elim@98 | d3-27b - 27b lp: AUROC, elim@98 points "
          "| paired bootstrap 95% CI of the elim@98 gap (share of resamples <= 0) |")
    print("|---|---|---|---|---|---|")

    def variant(rows, how):
        out = []
        for r in rows:
            if r["pair_id"] in rule:
                if how == "dropped":
                    continue
                if how == "relabeled non-responsive":
                    r = {**r, "label": 0}
            out.append(r)
        return out

    def metrics(rows):
        s = [r["score"] for r in rows]; l = [r["label"] for r in rows]
        return auroc(s, l), at_recall(pr_curve(s, l), 0.98)[3]

    for runs, a_tag, b_tag in [("main, 25-3152 rows", TAGS["27b lp"], TAGS["d3-27b"]),
                               ("roster", TAGS["27b lp"] + "_roster", TAGS["d3-27b"] + "_roster")]:
        A = [r for r in RUNS[a_tag] if r["request_id"] == "25-3152"]
        B = {r["pair_id"]: r for r in RUNS[b_tag] if r["request_id"] == "25-3152"}
        for how in ("as labeled", "dropped", "relabeled non-responsive"):
            a = variant(A, how); b = [B[r["pair_id"]] if how != "relabeled non-responsive" or r["pair_id"] not in rule
                                      else {**B[r["pair_id"]], "label": 0} for r in a]
            ma, mb = metrics(a), metrics(b)
            rng = random.Random(SEED); pos = [i for i, r in enumerate(a) if r["label"]]; neg = [i for i, r in enumerate(a) if not r["label"]]
            ds = []
            for _ in range(N_BOOT):
                idx = rng.choices(pos, k=len(pos)) + rng.choices(neg, k=len(neg))
                ds.append(100 * (metrics([b[i] for i in idx])[1] - metrics([a[i] for i in idx])[1]))
            ds.sort()
            print(f"| {runs} | {how} | {ma[0]:.3f} / {ma[1]:.1%} | {mb[0]:.3f} / {mb[1]:.1%} | {mb[0] - ma[0]:+.3f}, "
                  f"{100 * (mb[1] - ma[1]):+.1f} | [{ds[int(.025 * N_BOOT)]:+.1f}, {ds[int(.975 * N_BOOT) - 1]:+.1f}] "
                  f"({sum(d <= 0 for d in ds) / N_BOOT:.3f}) |")
    print()


def f3():
    print("## F3. Detection power of a random-sample check (20% of hits responsive)\n")
    # reference failures: the 24-409 thr98 applied to 25-3152 (A2b's transfer), for 27b lp and d3-27b
    tm = {}
    for m in ("27b lp", "d3-27b"):
        rows = RUNS[TAGS[m]]; t = thr98([r for r in rows if r["request_id"] == "24-409"])
        pos = [r for r in rows if r["request_id"] == "25-3152" and r["label"]]
        tm[m] = (sum(r["score"] < t for r in pos), len(pos))
    f27, fd3 = (tm[m][0] / tm[m][1] for m in ("27b lp", "d3-27b"))
    print("P(the sample holds >= 1 responsive email scoring below the cutoff) = 1 - (1 - 0.2 f)^n, for a cutoff that "
          f"misses a share f of responsive emails. Reference failures: 27b lp 24-409 -> 25-3152 transfer misses "
          f"{tm['27b lp'][0]}/{tm['27b lp'][1]} (f = {f27:.3f}); d3-27b's {tm['d3-27b'][0]}/{tm['d3-27b'][1]} ({fd3:.3f}).\n")
    fs = (0.02, 0.03, 0.05, 0.10, round(fd3, 3))
    print("| n | " + " | ".join(f"f = {f:g}" for f in fs) + " |")
    print("|---|" + "---|" * len(fs))
    for n in (50, 100, 200, 400):
        print(f"| {n} | " + " | ".join(f"{1 - (1 - P_RESP * f) ** n:.2f}" for f in fs) + " |")
    print()


def f4():
    print("## F4. d3 / stock latency on the same pairs (wall ms)\n")
    print("| pair | ratio of means (B1.8's statistic) | ratio of medians | median of per-pair ratios (E5e's statistic) |")
    print("|---|---|---|---|")
    for a, b in (("4b lp", "d3-4b"), ("9b lp", "d3-9b"), ("27b lp", "d3-27b")):
        A = {r["pair_id"]: r["wall_ms"] for r in RUNS[TAGS[a]]}; B = {r["pair_id"]: r["wall_ms"] for r in RUNS[TAGS[b]]}
        ids = sorted(set(A) & set(B))
        print(f"| {b} / {a} | {statistics.mean(B[i] for i in ids) / statistics.mean(A[i] for i in ids):.2f} | "
              f"{statistics.median(B[i] for i in ids) / statistics.median(A[i] for i in ids):.2f} | "
              f"{statistics.median(B[i] / A[i] for i in ids):.2f} |")
    print()


def f5():
    print("## F5. Headroom of the recommended fixed cutoffs on 25-3152\n")
    print(f"Failure point = the third-lowest 25-3152 positive score (above it, more than 2 of {NP['25-3152']} are missed). "
          "Headroom = logit(failure point) - logit(cutoff).\n")
    print("| model | cutoff | 25-3152 failure point | log-odds headroom | misses on 25-3152 at the cutoff [Wilson 95% of the rate] |")
    print("|---|---|---|---|---|")
    logit = lambda p: math.log(p / (1 - p))
    for name, cut in (("d3-27b", 0.4), ("d3-27b", 0.5), ("27b lp", 0.02), ("27b lp", 0.05)):
        pos = sorted(r["score"] for r in RUNS[TAGS[name]] if r["label"] == 1 and r["request_id"] == "25-3152")
        fail = pos[2]; k = sum(s < cut for s in pos); lo, hi = wilson(k, len(pos))
        print(f"| {name} | {cut} | {fail:.4f} | {logit(fail) - logit(cut):.2f} | {k}/{len(pos)} [{lo:.1%}-{hi:.1%}] |")
    print()


def f6():
    print("## F6. Roster runs (25-3152): misses with Wilson intervals, per 10,000 hits at 20% responsive\n")
    print("| run | cutoff | misses | missed per 10,000 [Wilson 95%] |")
    print("|---|---|---|---|")
    for name, cut in (("d3-27b", 0.5), ("d3-27b", 0.4), ("27b lp", None), ("27b lp", 0.02)):
        rows = RUNS[TAGS[name] + "_roster"]
        t = thr98(rows) if cut is None else cut
        pos = [r for r in rows if r["label"] == 1]; k = sum(r["score"] < t for r in pos); lo, hi = wilson(k, len(pos))
        label = f"{cut}" if cut is not None else f"thr98 = {t:.4f} (in-sample)"
        print(f"| {name} + roster | {label} | {k}/{len(pos)} | {2000 * k / len(pos):.0f} [{2000 * lo:.0f}-{2000 * hi:.0f}] |")
    print()


if __name__ == "__main__":
    f1(); f2(); f3(); f4(); f5(); f6()
