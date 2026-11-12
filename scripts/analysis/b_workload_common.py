"""Shared helpers for branch B (workload per 10,000 keyword-search hits). Stdlib only.

Imported by b_workload_time.py and b_workload_review.py; not run directly.

Labels, kinds and recipes come from data/golden/pairs.jsonl joined on pair_id (golden_report.load_runs),
never from the copies saved in scores.jsonl. Rows without a score (5 JSON parse failures) are dropped.
"""
import math
import pathlib
import random
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze import at_recall, pr_curve  # noqa: E402
from golden_report import load_runs  # noqa: E402

N_HITS = 10_000          # population size every per-10,000 number refers to
JEV_USD_PER_MTOK = 0.042  # Jev price per million input tokens (the only price given; output-token price unknown)
SEED = 20261106           # fixed seed for every bootstrap in branch B
N_BOOT = 1000

# (name, run tag, mode family, size tier). Each tag has a "_roster" twin (25-3152 only).
CONFIGS = [
    ("4b lp", "golden_qwen3.5_4b_logprob_p2db", "score", "4B"),
    ("9b lp", "golden_qwen3.5_9b_logprob_p2db", "score", "9B"),
    ("27b lp", "golden_qwen3.8_27b_logprob_p2", "score", "27B"),
    ("d3-4b", "golden_d3-ctx8k_4b_noul_p2", "score", "4B"),
    ("d3-9b", "golden_d3-ctx8k_9b_noul_p2", "score", "9B"),
    ("d3-27b", "golden_d3-ctx8k_27b_noul_p2", "score", "27B"),
    ("Jev", "golden_jev-1.14.0_noul_p2", "score", "API"),
    ("4b json", "golden_qwen3.5_4b_json_p2", "json", "4B"),
    ("9b json", "golden_qwen3.5_9b_json_p2", "json", "9B"),
    ("27b json", "golden_qwen3.8_27b_json_p2", "json", "27B"),
    ("4b jsonR", "golden_qwen3.5_4b_json_reason_p2", "json", "4B"),
    ("9b jsonR", "golden_qwen3.5_9b_json_reason_p2", "json", "9B"),
    ("27b jsonR", "golden_qwen3.8_27b_json_reason_p2", "json", "27B"),
]
SCORE_NAMES = [c[0] for c in CONFIGS if c[2] == "score"]
TIER = {c[0]: c[3] for c in CONFIGS}

POS_KINDS = ["real_positive", "close_call_positive", "privileged_positive", "exempt_other_positive",
             "hard_negative_flipped"]
NEG_KINDS = ["real_negative", "hard_negative"]


def load():
    """Returns ({name: rows}, {name: rows}) for the main and roster runs, plus a drop log."""
    by_tag = {r["tag"]: r for r in load_runs()}
    main, roster, dropped = {}, {}, []
    for name, tag, _, _ in CONFIGS:
        for t, out in ((tag, main), (tag + "_roster", roster)):
            run = by_tag[t]
            out[name] = run["rows"]
            if len(run["all"]) != len(run["rows"]):
                dropped.append((t, len(run["all"]) - len(run["rows"]), len(run["all"])))
    return main, roster, dropped


def decide_default(r):
    """Default decision: score >= 0.5, or the JSON verdict."""
    return bool(r["verdict"]) if "verdict" in r else r["score"] >= 0.5


def thr98(rows):
    """Highest threshold with recall >= 98% on these rows (in-sample)."""
    return at_recall(pr_curve([r["score"] for r in rows], [r["label"] for r in rows]), 0.98)[0]


def flags(rows, cutoff):
    """cutoff 'thr98' (re-chosen on these rows) or 'default'. Returns (list of bools, threshold or None)."""
    if cutoff == "default":
        return [decide_default(r) for r in rows], None
    t = thr98(rows)
    return [r["score"] >= t for r in rows], t


def kind_counts(rows, cutoff):
    """{group: (k flagged, n)} for each kind plus pooled groups 'all_pos' and 'all_neg'."""
    f, t = flags(rows, cutoff)
    out = {}
    for r, x in zip(rows, f):
        for g in (r["kind"], "all_pos" if r["label"] else "all_neg"):
            k, n = out.get(g, (0, 0))
            out[g] = (k + x, n + 1)
    return out, t


def rates(counts):
    """Pass rates used by the scenarios: R_all, R_real (positives), F_real, F_hard, F_mix (negatives);
    F_all (all negatives pooled, golden mix) is reported only, 1 - F_all being the golden eliminated share."""
    q = lambda g: counts[g][0] / counts[g][1]
    f_real, f_hard = q("real_negative"), q("hard_negative")
    return {"R_all": q("all_pos"), "R_real": q("real_positive"),
            "F_real": f_real, "F_hard": f_hard, "F_mix": 0.5 * f_real + 0.5 * f_hard, "F_all": q("all_neg")}


NEG_MODELS = [("real", "F_real"), ("mix", "F_mix"), ("hard", "F_hard")]
POS_MODELS = [("all", "R_all"), ("real-only", "R_real")]
P_SHARES = [0.05, 0.20, 0.50]
PLAUSIBLE = {"p": 0.20, "neg": "F_mix", "pos": "R_all"}


def scenario(rt, p, neg, pos, n=N_HITS):
    """Per-n numbers for a population with responsive share p whose negatives pass at rate rt[neg]
    and positives at rate rt[pos]."""
    resp = n * p
    flagged_pos = resp * rt[pos]
    flagged_neg = (n - resp) * rt[neg]
    flagged = flagged_pos + flagged_neg
    return {"flagged": flagged, "missed": resp - flagged_pos, "avoided": 1 - flagged / n,
            "queue_resp": flagged_pos / flagged if flagged else float("nan")}


def strata(rows):
    """pair_ids grouped by kind (the bootstrap strata; finer than label)."""
    g = {}
    for r in rows:
        g.setdefault(r["kind"], []).append(r["pair_id"])
    return {k: sorted(v) for k, v in sorted(g.items())}


def resamples(rows, n_boot, seed):
    """Yields n_boot lists of pair_ids, resampled with replacement within each kind. The same lists are
    used for every configuration, so comparisons between configurations are paired."""
    rng = random.Random(seed)
    st = strata(rows)
    for _ in range(n_boot):
        ids = []
        for k in st:
            ids += rng.choices(st[k], k=len(st[k]))
        yield ids


def ci(xs):
    """95% percentile interval, same convention as golden_report.boot."""
    s = sorted(xs)
    n = len(s)
    return s[int(.025 * n)], s[int(.975 * n) - 1]


def wilson(k, n, z=1.96):
    """Wilson 95% interval for k/n (does not collapse at 0/n or n/n)."""
    if n == 0:
        return float("nan"), float("nan")
    c = (k + z * z / 2) / (n + z * z)
    h = z * math.sqrt(k * (n - k) / n + z * z / 4) / (n + z * z)
    return max(0.0, c - h), min(1.0, c + h)


def p90(xs):
    s = sorted(xs)
    return s[int(.9 * len(s))]  # same convention as golden_report §6


def mean(xs):
    return statistics.mean(xs)


def table(header, rows):
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join("---" for _ in header) + "|")
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")
    print()


def pct(x, d=0):
    return f"{100 * x:.{d}f}%"


def n0(x):
    return f"{x:,.0f}"
