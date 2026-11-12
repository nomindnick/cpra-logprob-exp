"""Shared loading, subsets and bootstrap helpers for branch D (validity) scripts.

Imported by scripts/analysis/d_validity_*.py; not run on its own. Run the scripts from the project root:

  uv run python scripts/analysis/d_validity_subsets.py

Labels, kinds and recipes come from data/golden/pairs.jsonl joined on pair_id (the copies saved in
scores.jsonl can predate re-adjudication); rows whose pair_id is not in pairs.jsonl are dropped, and so are
rows with an error or a null score (5 JSON rows). This is the same join as scripts/golden_report.py
load_runs(). Metric helpers are the repo's own (scripts/analyze.py). Stdlib only.
"""
import json
import random
import sys

sys.path.insert(0, "scripts")
from analyze import at_recall, auroc, pr_curve  # noqa: E402

# the seven runs that produce a usable probability, then the JSON verdict modes (contrast only)
SCORE_RUNS = [
    ("4b lp", "golden_qwen3.5_4b_logprob_p2db"),
    ("9b lp", "golden_qwen3.5_9b_logprob_p2db"),
    ("27b lp", "golden_qwen3.8_27b_logprob_p2"),
    ("d3-4b", "golden_d3-ctx8k_4b_noul_p2"),
    ("d3-9b", "golden_d3-ctx8k_9b_noul_p2"),
    ("d3-27b", "golden_d3-ctx8k_27b_noul_p2"),
    ("Jev", "golden_jev-1.14.0_noul_p2"),
]
JSON_RUNS = [
    ("4b json", "golden_qwen3.5_4b_json_p2"),
    ("9b json", "golden_qwen3.5_9b_json_p2"),
    ("27b json", "golden_qwen3.8_27b_json_p2"),
    ("4b jsonR", "golden_qwen3.5_4b_json_reason_p2"),
    ("9b jsonR", "golden_qwen3.5_9b_json_reason_p2"),
    ("27b jsonR", "golden_qwen3.8_27b_json_reason_p2"),
]
ALL_RUNS = SCORE_RUNS + JSON_RUNS

POS_KINDS = ["real_positive", "close_call_positive", "privileged_positive", "exempt_other_positive",
             "hard_negative_flipped"]
NEG_KINDS = ["real_negative", "hard_negative"]

# (key, description, positive kinds or None = all positives, negative kinds or None = all negatives)
SUBSETS = [
    ("a", "real+ vs real−", {"real_positive"}, {"real_negative"}),
    ("b", "real+ vs hard−", {"real_positive"}, {"hard_negative"}),
    ("c", "all+ vs real−", None, {"real_negative"}),
    ("d", "all+ vs hard−", None, {"hard_negative"}),
    ("e", "everything", None, None),
    # added in this branch: the hard negatives a date-limited search could return (all but the wrong-date recipe)
    ("f", "real+ vs in-window hard−", {"real_positive"}, {"hard_negative_in_window"}),
]

WINDOWS = {"24-409": ("2023-01-01", "2023-07-31"), "25-3152": ("2024-01-01", "2025-05-31")}


def iso_date(s):
    """'YYYY-MM-DD' from an email date: ISO ('2023-05-10T11:57:47-07:00') or the 25-5982 production's
    'Wednesday, April 3, 2024 1:28 PM'. None if missing or unparseable."""
    import datetime
    import re
    if not s:
        return None
    if re.match(r"\d{4}-\d\d-\d\d", s):
        return s[:10]
    for fmt in ("%A, %B %d, %Y %I:%M %p", "%A, %B %d, %Y"):
        try:
            return datetime.datetime.strptime(s.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return None


def in_window(e, rid):
    """True/False if the email's date is inside/outside the request's window; None if the date is unknown."""
    d = iso_date(e.get("date"))
    if d is None:
        return None
    lo, hi = WINDOWS[rid]
    return lo <= d <= hi


def pairs():
    return {p["pair_id"]: p for p in map(json.loads, open("data/golden/pairs.jsonl"))}


def emails():
    """Golden emails keyed by pair_id (one row per designed pair)."""
    return {f"{e['request_id']}|{e['id']}": e for e in map(json.loads, open("data/golden/emails.jsonl"))}


def load(tag, P=None):
    """Return (rows, dropped): rows with label/kind/recipe from pairs.jsonl; dropped = unscored rows."""
    P = P or pairs()
    rows, dropped = [], []
    for r in map(json.loads, open(f"runs/{tag}/scores.jsonl")):
        if r["pair_id"] not in P:
            continue
        r = {**r, **{k: P[r["pair_id"]][k] for k in ("label", "kind", "recipe")}}
        if "error" in r or r.get("score") is None:
            dropped.append(r)
        else:
            rows.append(r)
    return rows, dropped


def run_config(tag):
    return json.load(open(f"runs/{tag}/run.json"))


def in_subset(row, sub):
    _, _, pk, nk = sub
    if row["label"]:
        return pk is None or row["kind"] in pk
    if nk is not None and "hard_negative_in_window" in nk:
        return row["kind"] == "hard_negative" and row["recipe"] != "same_subject_wrong_date"
    return nk is None or row["kind"] in nk


def point(rows):
    """AUROC, elim@98 (share of negatives with score < thr98), thr98, k eliminated, n negatives."""
    s = [r["score"] for r in rows]; l = [r["label"] for r in rows]
    thr, rec, prec, elim = at_recall(pr_curve(s, l), 0.98)
    n_neg = len(l) - sum(l)
    k = sum(1 for x, y in zip(s, l) if not y and x < thr)
    return {"auroc": auroc(s, l), "elim": elim, "thr": thr, "k": k, "n_neg": n_neg, "n_pos": sum(l),
            "recall": rec, "missed": sum(1 for x, y in zip(s, l) if y and x < thr)}


def ci(xs):
    xs = sorted(xs); n = len(xs)
    return xs[int(.025 * n)], xs[int(.975 * n) - 1]


def paired_boot(run_rows, ids, n, seed):
    """Stratified-by-label bootstrap over pair ids, the same resample for every run (paired).

    run_rows: {name: {pair_id: row}}; ids: the pair ids in the subset (labels from any run's rows / pairs).
    Returns {name: {"auroc": [..], "elim": [..]}}. A run missing a resampled pair (unscored JSON row) just
    leaves it out of that resample.
    """
    rng = random.Random(seed)
    P = pairs()
    pos = sorted(p for p in ids if P[p]["label"]); neg = sorted(p for p in ids if not P[p]["label"])
    out = {m: {"auroc": [], "elim": []} for m in run_rows}
    for _ in range(n):
        b = rng.choices(pos, k=len(pos)) + rng.choices(neg, k=len(neg))
        for m, R in run_rows.items():
            xs = [R[p] for p in b if p in R]
            s = [x["score"] for x in xs]; l = [x["label"] for x in xs]
            out[m]["auroc"].append(auroc(s, l))
            out[m]["elim"].append(at_recall(pr_curve(s, l), 0.98)[3])
    return out


def kendall_tau(a, b):
    """Kendall tau-a between two score lists (same order of items); ties count as 0."""
    n = len(a); c = d = 0
    for i in range(n):
        for j in range(i + 1, n):
            x = (a[i] > a[j]) - (a[i] < a[j]); y = (b[i] > b[j]) - (b[i] < b[j])
            if x * y > 0: c += 1
            elif x * y < 0: d += 1
    return (c - d) / (n * (n - 1) / 2)


def ranks_desc(vals):
    """Rank 1 = highest; ties share the best rank ("1=")."""
    out = []
    for v in vals:
        r = 1 + sum(1 for w in vals if w > v + 1e-12)
        tied = sum(1 for w in vals if abs(w - v) <= 1e-12) > 1
        out.append(f"{r}{'=' if tied else ''}")
    return out


def table(header, rows):
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join("---" for _ in header) + "|")
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")
    print()


def fa(x, lo=None, hi=None):
    s = "—" if x is None else f"{x:.3f}"
    return s if lo is None else f"{s} [{lo:.3f}–{hi:.3f}]"


def fe(p, lo=None, hi=None):
    s = f"{p['elim']:.0%} ({p['k']}/{p['n_neg']})"
    return s if lo is None else f"{s} [{lo:.0%}–{hi:.0%}]"
