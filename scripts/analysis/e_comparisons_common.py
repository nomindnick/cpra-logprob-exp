"""Shared helpers for branch E (scripts/analysis/e_comparisons_*.py). Stdlib only.

Loads the saved golden-set runs through scripts/golden_report.py load_runs(), so label, kind and
recipe come from data/golden/pairs.jsonl (joined on pair_id) and rows without a score are dropped.
No model, GPU or network calls: everything is read from runs/<tag>/scores.jsonl.
"""
import math
import os
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
os.chdir(ROOT)  # golden_report.load_runs() reads relative paths
sys.path.insert(0, str(ROOT / "scripts"))

from analyze import at_recall, auroc, pr_curve  # noqa: E402
from golden_report import load_runs  # noqa: E402

# The seven models that produce a usable probability (the report's main tables), in canonical order.
SCORE = [
    ("4b lp", "golden_qwen3.5_4b_logprob_p2db"),
    ("9b lp", "golden_qwen3.5_9b_logprob_p2db"),
    ("27b lp", "golden_qwen3.8_27b_logprob_p2"),
    ("d3-4b", "golden_d3-ctx8k_4b_noul_p2"),
    ("d3-9b", "golden_d3-ctx8k_9b_noul_p2"),
    ("d3-27b", "golden_d3-ctx8k_27b_noul_p2"),
    ("Jev", "golden_jev-1.14.0_noul_p2"),
]
# JSON verdict modes (contrast only). json = verdict first, jsonR = reasoning first.
JSON = [
    ("4b json", "golden_qwen3.5_4b_json_p2"),
    ("9b json", "golden_qwen3.5_9b_json_p2"),
    ("27b json", "golden_qwen3.8_27b_json_p2"),
    ("4b jsonR", "golden_qwen3.5_4b_json_reason_p2"),
    ("9b jsonR", "golden_qwen3.5_9b_json_reason_p2"),
    ("27b jsonR", "golden_qwen3.8_27b_json_reason_p2"),
]
# Stock-Qwen logprob runs that unload the model before every call (no prefix cache); E5 only.
FRESH = [("4b lp fresh", "golden_qwen3.5_4b_logprob_p2dbf"), ("9b lp fresh", "golden_qwen3.5_9b_logprob_p2dbf")]

RECIPES = ["same_subject_wrong_date", "keyword_unrelated_sense", "keyword_in_signature_or_newsletter",
           "forwarded_no_content", "same_people_different_subject"]
RECIPE_SHORT = {"same_subject_wrong_date": "same subject, wrong date",
                "keyword_unrelated_sense": "keyword, unrelated sense",
                "keyword_in_signature_or_newsletter": "keyword in signature/newsletter",
                "forwarded_no_content": "forwarded, no content",
                "same_people_different_subject": "same people, different subject"}

_RUNS = None


def runs_by_tag():
    global _RUNS
    if _RUNS is None:
        _RUNS = {r["tag"]: r for r in load_runs()}
    return _RUNS


def rows(tag, roster=False):
    """Scored rows of a run, keyed by pair_id (label/kind/recipe from pairs.jsonl)."""
    r = runs_by_tag()[tag + ("_roster" if roster else "")]
    return {x["pair_id"]: x for x in r["rows"]}


def n_unscored(tag, roster=False):
    r = runs_by_tag()[tag + ("_roster" if roster else "")]
    return len(r["all"]) - len(r["rows"])


# ---------- metrics ----------

def elim98(scores, labels):
    return at_recall(pr_curve(scores, labels), 0.98)[3]


def thr98(scores, labels):
    return at_recall(pr_curve(scores, labels), 0.98)[0]


def brier(scores, labels):
    return statistics.fmean((s - l) ** 2 for s, l in zip(scores, labels))


def bin_of(s, nb=10):
    return min(int(s * nb), nb - 1)  # [0, .1), ..., [.9, 1.0]


def ece(scores, labels, nb=10):
    """Expected calibration error with nb equal-width bins (the last bin includes 1.0)."""
    n = len(scores)
    tot = [0.0] * nb; pos = [0] * nb; cnt = [0] * nb
    for s, l in zip(scores, labels):
        b = bin_of(s, nb); tot[b] += s; pos[b] += l; cnt[b] += 1
    return sum(abs(tot[b] / cnt[b] - pos[b] / cnt[b]) * cnt[b] / n for b in range(nb) if cnt[b])


def logistic_fit(x, y, iters=50):
    """Two-parameter logistic regression y ~ a + b*x by Newton-Raphson; returns (a, b)."""
    a = b = 0.0
    for _ in range(iters):
        ga = gb = haa = hab = hbb = 0.0
        for xi, yi in zip(x, y):
            p = 1 / (1 + math.exp(-(a + b * xi)))
            w = p * (1 - p)
            ga += yi - p; gb += (yi - p) * xi
            haa += w; hab += w * xi; hbb += w * xi * xi
        det = haa * hbb - hab * hab
        da = (hbb * ga - hab * gb) / det; db = (haa * gb - hab * ga) / det
        a += da; b += db
        if abs(da) < 1e-10 and abs(db) < 1e-10:
            break
    return a, b


def logit(s, eps=1e-6):
    s = min(max(s, eps), 1 - eps)
    return math.log(s / (1 - s))


# ---------- bootstrap ----------

def strata(ids, label_of):
    ids = sorted(ids)
    return [p for p in ids if label_of[p]], [p for p in ids if not label_of[p]]


def resample(pos, neg, rng):
    """One stratified-by-label bootstrap resample of pair ids (class sizes fixed)."""
    return rng.choices(pos, k=len(pos)) + rng.choices(neg, k=len(neg))


def ci(xs):
    """95% percentile interval, same convention as golden_report.boot()."""
    xs = sorted(xs); n = len(xs)
    return xs[int(.025 * n)], xs[int(.975 * n) - 1]


def boot_p(deltas):
    """Two-sided bootstrap p-value for H0: delta = 0, by inverting the percentile interval.
    Resamples with delta exactly 0 count in both tails (conservative)."""
    B = len(deltas)
    lo = sum(d <= 0 for d in deltas); hi = sum(d >= 0 for d in deltas)
    return min(1.0, 2 * (min(lo, hi) + 1) / (B + 1))


def holm(ps):
    """Holm step-down adjusted p-values, in the input order."""
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj = [0.0] * m; run = 0.0
    for k, i in enumerate(order):
        run = max(run, min(1.0, (m - k) * ps[i]))
        adj[i] = run
    return adj


# ---------- exact and analytic tests ----------

def binom_two_sided(k, n):
    """Exact two-sided sign test: 2 * P(X <= min(k, n-k)), X ~ Bin(n, 1/2), capped at 1."""
    if n == 0:
        return 1.0
    m = min(k, n - k)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(m + 1)) / 2 ** n)


def mcnemar_exact(a_flags, b_flags):
    """Exact McNemar on paired booleans. Returns (b, c, p): b = A yes & B no, c = A no & B yes."""
    b = sum(1 for x, y in zip(a_flags, b_flags) if x and not y)
    c = sum(1 for x, y in zip(a_flags, b_flags) if y and not x)
    return b, c, binom_two_sided(b, b + c)


def fisher_two_sided(a, b, c, d):
    """Fisher's exact test for the 2x2 table [[a, b], [c, d]]; sums tables no more likely than observed."""
    r1, r2, c1, n = a + b, c + d, a + c, a + b + c + d
    def pr(x):
        return math.comb(r1, x) * math.comb(r2, c1 - x) / math.comb(n, c1)
    p0 = pr(a)
    return min(1.0, sum(pr(x) for x in range(max(0, c1 - r2), min(r1, c1) + 1) if pr(x) <= p0 * (1 + 1e-9)))


def delong(score_lists, labels):
    """DeLong et al. (1988) for correlated AUROCs on the same cases.
    score_lists: list of score vectors (same case order); labels: 0/1 vector.
    Returns (aucs, cov) where cov is the covariance matrix of the AUROC estimates."""
    P = [i for i, l in enumerate(labels) if l]; N = [i for i, l in enumerate(labels) if not l]
    m, n = len(P), len(N)
    V10, V01, aucs = [], [], []
    for s in score_lists:
        xs = [s[i] for i in P]; ys = [s[j] for j in N]
        v10 = [sum(1.0 if x > y else 0.5 if x == y else 0.0 for y in ys) / n for x in xs]
        v01 = [sum(1.0 if x > y else 0.5 if x == y else 0.0 for x in xs) / m for y in ys]
        V10.append(v10); V01.append(v01); aucs.append(statistics.fmean(v10))
    k = len(score_lists)
    def cov(A, B):
        ma, mb = statistics.fmean(A), statistics.fmean(B)
        return sum((a - ma) * (b - mb) for a, b in zip(A, B)) / (len(A) - 1)
    C = [[cov(V10[i], V10[j]) / m + cov(V01[i], V01[j]) / n for j in range(k)] for i in range(k)]
    return aucs, C


def delong_p(aucs, C, i, j):
    var = C[i][i] + C[j][j] - 2 * C[i][j]
    if var <= 0:
        return 1.0
    z = (aucs[i] - aucs[j]) / math.sqrt(var)
    return math.erfc(abs(z) / math.sqrt(2))


def wilson(k, n, z=1.959964):
    if n == 0:
        return (float("nan"), float("nan"))
    c = (k + z * z / 2) / (n + z * z)
    h = z * math.sqrt(k * (n - k) / n + z * z / 4) / (n + z * z)
    return max(0.0, c - h), min(1.0, c + h)


# ---------- formatting ----------

def table(header, body):
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join("---" for _ in header) + "|")
    for r in body:
        print("| " + " | ".join(str(x) for x in r) + " |")
    print()


def fp(p):
    """Format a p-value."""
    if p >= 0.995:
        return "1"
    if p >= 0.1:
        return f"{p:.2f}"
    if p >= 0.001:
        return f"{p:.3f}"
    return f"{p:.1e}"


def kn(k, n):
    return f"{k}/{n} ({k / n:.0%})"


def kn_ci(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k / n:.1%} [{lo:.1%}–{hi:.1%}]"
