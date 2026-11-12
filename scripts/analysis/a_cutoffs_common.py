"""Shared loading and helpers for the branch-A cutoff analyses (docs/analysis/A-cutoffs.md).

Not run directly. The a_cutoffs_*.py scripts import it. Stdlib only.

Rows come from scripts/golden_report.py load_runs(): label, kind and recipe are taken from
data/golden/pairs.jsonl joined on pair_id (not the copies saved in scores.jsonl), rows whose pair_id
isn't in pairs.jsonl are dropped, and rows with an error or a null score are left out.

Subsets of each score model's runs:
  24-409      the pairs of 24-409 from the main run
  25-3152     the pairs of 25-3152 from the main run
  25-3152+R   the same 249 pairs from the "_roster" twin (roster appended to the request text)
  pooled      24-409 + 25-3152 (all main-set pairs, behind the headline)
  pooled+R    24-409 + 25-3152+R

A pair is flagged responsive when score >= cutoff. "Eliminated" = negatives with score < cutoff.
"""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
os.chdir(ROOT)  # load_runs() reads data/ and runs/ by relative path
sys.path.insert(0, str(ROOT / "scripts"))

from analyze import at_recall, pr_curve  # noqa: E402
from golden_report import load_runs  # noqa: E402

SCORE_MODELS = [  # (label, main run tag); each has a tag + "_roster" twin
    ("4b lp", "golden_qwen3.5_4b_logprob_p2db"),
    ("9b lp", "golden_qwen3.5_9b_logprob_p2db"),
    ("27b lp", "golden_qwen3.8_27b_logprob_p2"),
    ("d3-4b", "golden_d3-ctx8k_4b_noul_p2"),
    ("d3-9b", "golden_d3-ctx8k_9b_noul_p2"),
    ("d3-27b", "golden_d3-ctx8k_27b_noul_p2"),
    ("Jev", "golden_jev-1.14.0_noul_p2"),
]
JSON_MODELS = [
    ("4b json", "golden_qwen3.5_4b_json_p2"),
    ("9b json", "golden_qwen3.5_9b_json_p2"),
    ("27b json", "golden_qwen3.8_27b_json_p2"),
    ("4b jsonR", "golden_qwen3.5_4b_json_reason_p2"),
    ("9b jsonR", "golden_qwen3.5_9b_json_reason_p2"),
    ("27b jsonR", "golden_qwen3.8_27b_json_reason_p2"),
]
REQS = ["24-409", "25-3152", "25-3152+R"]
SETS = REQS + ["pooled", "pooled+R"]

_RUNS = None


def _runs():
    global _RUNS
    if _RUNS is None:
        _RUNS = {r["tag"]: r for r in load_runs()}
    return _RUNS


def load(models=SCORE_MODELS):
    """{label: {subset: rows, "_unscored": {tag: count}}} for each model."""
    runs = _runs()
    out = {}
    for label, tag in models:
        base, ros = runs[tag], runs[tag + "_roster"]
        assert base["complete"] and ros["complete"], tag
        assert all(x["request_id"] == "25-3152" for x in ros["rows"]), tag
        r24 = [x for x in base["rows"] if x["request_id"] == "24-409"]
        r25 = [x for x in base["rows"] if x["request_id"] == "25-3152"]
        r25r = list(ros["rows"])
        out[label] = {"24-409": r24, "25-3152": r25, "25-3152+R": r25r, "pooled": r24 + r25,
                      "pooled+R": r24 + r25r,
                      "_unscored": {tag: len(base["all"]) - len(base["rows"]),
                                    tag + "_roster": len(ros["all"]) - len(ros["rows"])},
                      "_tags": (tag, tag + "_roster")}
    return out


def cutoff(rows, target):
    """Highest threshold whose recall on rows is >= target (golden_report.thr98 for target 0.98)."""
    return at_recall(pr_curve([r["score"] for r in rows], [r["label"] for r in rows]), target)[0]


def apply(rows, cut, flag=None):
    """Misses and eliminations when pairs with score >= cut are flagged (or by flag(row) if given)."""
    flag = flag or (lambda r: r["score"] >= cut)
    pos = [r for r in rows if r["label"]]
    neg = [r for r in rows if not r["label"]]
    missed = [r for r in pos if not flag(r)]
    elim = sum(not flag(r) for r in neg)
    return {"miss": len(missed), "P": len(pos), "elim": elim, "N": len(neg), "missed": missed,
            "recall": (len(pos) - len(missed)) / len(pos), "elim_rate": elim / len(neg)}


def allowed_misses(P, target=0.98):
    """Largest number of misses that still leaves recall >= target."""
    m = 0
    while (P - (m + 1)) / P >= target - 1e-12:
        m += 1
    return m


def fmt_miss(e):
    return f"{e['miss']}/{e['P']}"


def fmt_rec(e):
    return f"{e['recall']:.1%}"


def fmt_elim(e):
    return f"{e['elim']}/{e['N']} ({e['elim_rate']:.0%})"


def fmt_cut(c):
    return f"{c:.4f}" if c >= 0.001 else f"{c:.2e}"


def table(header, rows):
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join("---" for _ in header) + "|")
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")
    print()


def pctile(sorted_xs, p):
    """Nearest-rank lower percentile: element at index floor(p * n), clamped."""
    return sorted_xs[min(len(sorted_xs) - 1, int(p * len(sorted_xs)))]


KIND_ABBR = {"real_positive": "real", "close_call_positive": "close", "privileged_positive": "priv",
             "exempt_other_positive": "exempt", "hard_negative_flipped": "hn-flip"}
