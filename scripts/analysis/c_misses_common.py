"""Shared loading and helpers for branch C (missed responsive emails, consensus false positives,
label questions). Imported by the c_misses*.py scripts; not run on its own.

Run the scripts from the project root:  uv run python scripts/analysis/c_misses.py
Stdlib only. Read-only on data/ and runs/.
"""
import json
import math
import re
import sys

sys.path.insert(0, "scripts")
from analyze import at_recall, auroc, pr_curve  # noqa: E402
from golden_report import load_runs, thr98  # noqa: E402

# The seven score models (main tables). Each has a "_roster" twin (25-3152 only, 249 pairs).
MODELS = [("4b lp", "golden_qwen3.5_4b_logprob_p2db"), ("9b lp", "golden_qwen3.5_9b_logprob_p2db"),
          ("27b lp", "golden_qwen3.8_27b_logprob_p2"), ("d3-4b", "golden_d3-ctx8k_4b_noul_p2"),
          ("d3-9b", "golden_d3-ctx8k_9b_noul_p2"), ("d3-27b", "golden_d3-ctx8k_27b_noul_p2"),
          ("Jev", "golden_jev-1.14.0_noul_p2")]
NAMES = [m for m, _ in MODELS]
# JSON verdict modes, contrast only (verdict in field 'verdict'; rows with a null score are dropped)
JSON_RUNS = [("4b json", "golden_qwen3.5_4b_json_p2"), ("9b json", "golden_qwen3.5_9b_json_p2"),
             ("27b json", "golden_qwen3.8_27b_json_p2"), ("4b jsonR", "golden_qwen3.5_4b_json_reason_p2"),
             ("9b jsonR", "golden_qwen3.5_9b_json_reason_p2"), ("27b jsonR", "golden_qwen3.8_27b_json_reason_p2")]
MAX_BODY_CHARS = 8000  # scripts/score.py MAX_BODY_CHARS; every run used it (run.json max_body_chars)
MISS_K = 3  # a "consensus miss" = a positive missed by >= 3 of the 7 models
FP_K = 5  # a "consensus false positive" = a negative kept by >= 5 of the 7 models


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def load():
    """Returns {name: rows} for the main runs, {name: rows} for the roster twins, {name: rows} for JSON
    (main), {name: rows} for JSON roster, and the count of JSON rows dropped for a null score.
    Rows come from golden_report.load_runs(): label/kind/recipe joined from data/golden/pairs.jsonl,
    rows not in pairs.jsonl dropped, rows with an error or null score dropped."""
    by_tag = {r["tag"]: r for r in load_runs()}
    main = {m: by_tag[t]["rows"] for m, t in MODELS}
    roster = {m: by_tag[t + "_roster"]["rows"] for m, t in MODELS}
    js = {m: by_tag[t]["rows"] for m, t in JSON_RUNS}
    js_roster = {m: by_tag[t + "_roster"]["rows"] for m, t in JSON_RUNS}
    bad = lambda t: [x["pair_id"] for x in by_tag[t]["all"] if "error" in x or x.get("score") is None]
    dropped = {m: bad(t) for m, t in JSON_RUNS}
    dropped.update({m + " +roster": bad(t + "_roster") for m, t in JSON_RUNS})
    for m in NAMES:  # the score models must be complete, with every row scored
        assert len(main[m]) == N_ALL and len(roster[m]) == NR["25-3152"], m
    return main, roster, js, js_roster, dropped


def pairs():
    return {p["pair_id"]: p for p in map(json.loads, open("data/golden/pairs.jsonl"))}


def emails():
    return {e["id"]: e for e in map(json.loads, open("data/golden/emails.jsonl"))}


def requests():
    return {r["request_id"]: r for r in map(json.loads, open("data/emails/sandiego.requests.jsonl"))}


def roster_members():
    return json.load(open("data/golden/work/acpg_roster.json"))["members"]


def short(pid):
    """'24-409|sandiego:24-409:33733472' -> '24-409 real 33733472'; '24-409|synth:24-409:00:03' -> '24-409 syn 00:03'."""
    rid, eid = pid.split("|", 1)
    if eid.startswith("synth:"):
        return f"{rid} syn {eid.split(':', 2)[2]}"
    return f"{rid} real {eid.rsplit(':', 1)[1]}"


def elim98(rows):
    return at_recall(pr_curve([r["score"] for r in rows], [r["label"] for r in rows]), 0.98)[3]


def auc(rows):
    return auroc([r["score"] for r in rows], [r["label"] for r in rows])


def misses(rows, thr):
    return {r["pair_id"] for r in rows if r["label"] and r["score"] < thr}


def kept_negatives(rows, thr):
    return {r["pair_id"] for r in rows if not r["label"] and r["score"] >= thr}


def wilson(k, n, z=1.96):
    """95% Wilson score interval for k/n."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def fisher_two_sided(a, b, c, d):
    """Two-sided Fisher exact p for the 2x2 table [[a, b], [c, d]] (sum of tables no more likely than observed)."""
    r1, r2, c1, n = a + b, c + d, a + c, a + b + c + d
    def pmf(x):
        return math.comb(r1, x) * math.comb(r2, c1 - x) / math.comb(n, c1)
    p0 = pmf(a)
    lo, hi = max(0, c1 - r2), min(r1, c1)
    return min(1.0, sum(pmf(x) for x in range(lo, hi + 1) if pmf(x) <= p0 * (1 + 1e-9)))


def rate(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({k / n:.0%}, {lo:.0%}–{hi:.0%})" if n else "0/0"


def table(header, rows):
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join("---" for _ in header) + "|")
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")
    print()


# ---- where the request's hook sits in the email (a keyword heuristic, used in C4) ----
# 24-409: the topic terms of refinement items 2-4 and the original request. Case-sensitive acronyms so
# that e-mail domains such as "ucsd.edu" don't count.
# Acronyms are bounded by non-letters (not \b) so "OSEJ_RWER_Fact Sheet" counts.
_A = lambda w: r"(?<![A-Za-z])" + w + r"(?![A-Za-z])"
TERMS_24409 = [r"\bHinds\b", r"\bLerner\b", _A("USP"), _A("GPS"), r"(?i:urban studies)", r"(?i:global policy)",
               _A("UCSD"), r"(?i:UC San Diego)", r"(?i:University of California,? San Diego)", _A("RWER"),
               r"(?i:water equity)", _A("RDF"), r"(?i:decarboni[sz]ation framework)", r"(?i:geosyntec)",
               r"(?i:murakawa)", r"Nathan Fletcher"]
ADDR_RE = re.compile(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+|https?://\S+|www\.\S+")  # e-mail addresses and URLs
# [corrected in verification] \s+ so a mention broken across a line ("Alpine\nCommunity Planning Group",
# 25-3152 syn 12:07) counts, and (?!\s+area) so the place name "Alpine Community Planning Area" (19:08) doesn't.
ACPG_RE = re.compile(r"(?i:alpine\s+community\s+planning(?!\s+area)|alpine\s+cpg|alpine\s+planning\s+group)|\bACPG\b")


def _any(patterns, text):
    return any(re.search(p, text or "") for p in patterns)


def member_patterns():
    pats = []
    for m in roster_members():
        pats += [re.escape(a) for a in m["email_addresses"]]
        parts = re.sub(r"\(.*?\)|\bJr\.?|\b[A-Z]\.", "", m["name"]).split()
        pats.append(r"(?i:" + re.escape(parts[0]) + r"\W+(?:\w+\W+)?" + re.escape(parts[-1]) + r")")
    return pats


def hook_24409(e):
    head = " ".join(str(e.get(k) or "") for k in ("from", "to", "cc", "bcc", "delivered_to"))
    body = e.get("body") or ""
    if _any(TERMS_24409, (e.get("subject") or "") + "\n" + body[:MAX_BODY_CHARS]):
        return "topic term in subject or visible body"
    if _any(TERMS_24409, " ".join(e.get("attachments") or [])):
        return "topic term only in attachment names"
    if _any(TERMS_24409, body[MAX_BODY_CHARS:]):
        return "topic term only past the body cap"
    if _any(TERMS_24409, head):
        return "topic term only in headers"
    return "no topic term found"


def hook_25_3152(e, mpats):
    head = " ".join(str(e.get(k) or "") for k in ("from", "to", "cc", "bcc", "delivered_to"))
    body = e.get("body") or ""
    vis = (e.get("subject") or "") + "\n" + body[:MAX_BODY_CHARS] + "\n" + " ".join(e.get("attachments") or [])
    if ACPG_RE.search(vis):
        return "ACPG named in subject, visible body or attachment names"
    if _any(mpats, head):
        return "member in headers; ACPG not named"
    if _any(mpats, body[:MAX_BODY_CHARS]):
        return "member named in visible body only; ACPG not named"
    return "no ACPG mention or member found"


def n_recipients(e):
    s = " ".join(str(e.get(k) or "") for k in ("to", "cc", "bcc"))
    return len(set(a.lower() for a in re.findall(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+", s))) or len([x for x in re.split(r"[;,]", s) if x.strip()])


def in_window(e, rid):
    d = (e.get("date") or "")[:10]
    lo, hi = ("2023-01-01", "2023-07-31") if rid == "24-409" else ("2024-01-01", "2025-05-31")
    return lo <= d <= hi if d else None


# ---- per-model misses and kept negatives, and the consensus sets ----
def per_model(runs):
    """{model: {thr98, miss98, miss50, fp98, fp50}}: positives below the model's own pooled in-sample thr98
    (or below 0.5), and negatives at or above it."""
    out = {}
    for m, rows in runs.items():
        t = thr98(rows)
        out[m] = {"thr98": t, "miss98": misses(rows, t), "miss50": misses(rows, 0.5),
                  "fp98": kept_negatives(rows, t), "fp50": kept_negatives(rows, 0.5)}
    return out


def who(per, key, pid):
    return [m for m in NAMES if pid in per[m][key]]


def consensus(per, key, k):
    ids = set().union(*(per[m][key] for m in NAMES))
    return sorted((p for p in ids if len(who(per, key, p)) >= k), key=lambda p: (-len(who(per, key, p)), p))


def reading_list(main, roster):
    """Every consensus miss and consensus false positive, main set and roster runs, at thr98 or 0.5."""
    pm, pr = per_model(main), per_model(roster)
    ms = set(consensus(pm, "miss98", MISS_K)) | set(consensus(pm, "miss50", MISS_K)) | \
        set(consensus(pr, "miss98", MISS_K)) | set(consensus(pr, "miss50", MISS_K))
    fs = set(consensus(pm, "fp98", FP_K)) | set(consensus(pm, "fp50", FP_K)) | \
        set(consensus(pr, "fp98", FP_K)) | set(consensus(pr, "fp50", FP_K))
    return sorted(ms), sorted(fs)
