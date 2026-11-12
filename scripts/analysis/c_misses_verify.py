"""Branch C verification (skeptic pass): independent recomputation of the most consequential numbers in
docs/analysis/C-misses.md, plus the method checks the analyst's scripts don't do.

  uv run python scripts/analysis/c_misses_verify.py

Imports nothing from the analyst's c_misses*.py. Loads data/golden/pairs.jsonl, emails.jsonl and the
runs/*/scores.jsonl files itself, joins label/kind/recipe from pairs.jsonl on pair_id, and implements
AUROC (all positive-negative pairs, ties count half), thr98 (the k-th highest positive score, k =
ceil(0.98 n_pos)), elim@98 (negatives with score < thr98), Fisher's exact test, Wilson intervals and
the recipient / ACPG / member heuristics from scratch. The repo helpers (analyze.auroc, golden_report.thr98)
are used only at the end as a cross-check of the from-scratch versions.

Sections:
  V1  data integrity (labels from pairs.jsonl, duplicates, stale labels in scores.jsonl, nulls)
  V2  per-model thr98 / elim@98 / AUROC from scratch, main and roster, against the repo helpers
  V3  consensus misses and consensus false positives (thr98 and 0.5)
  V4  recipient count and ACPG-named splits (own heuristics, own Fisher), and the choice of cut
  V5  roster comparability: main runs restricted to the same 249 25-3152 pairs, own thr98
  V6  Q5 (one member among many): the 7-email flip, the same rule applied to every matching
      positive, flip vs drop, and a paired bootstrap of the 7-email flip
  V7  C5a: the single-flip deltas are the denominator effect alone
  V8  truncation per model (the C4 claim rests on consensus misses only)
  V9  per-model request tests with a Bonferroni bound; pooled miss events by request
  V10 wrong-date negatives: inside the original window vs distance from the refined window
  V11 JSON contrast spot checks and the quoted 27b reasoning
Deterministic: fixed seed, sorted iteration.
"""
import collections
import json
import math
import random
import re
import sys

MODELS = [("4b lp", "golden_qwen3.5_4b_logprob_p2db"), ("9b lp", "golden_qwen3.5_9b_logprob_p2db"),
          ("27b lp", "golden_qwen3.8_27b_logprob_p2"), ("d3-4b", "golden_d3-ctx8k_4b_noul_p2"),
          ("d3-9b", "golden_d3-ctx8k_9b_noul_p2"), ("d3-27b", "golden_d3-ctx8k_27b_noul_p2"),
          ("Jev", "golden_jev-1.14.0_noul_p2")]
NAMES = [m for m, _ in MODELS]
CAP = 8000
SEED = 20261106
BOOT = 1000

P = {p["pair_id"]: p for p in map(json.loads, open("data/golden/pairs.jsonl"))}
E = {e["id"]: e for e in map(json.loads, open("data/golden/emails.jsonl"))}
ROSTER = json.load(open("data/golden/work/acpg_roster.json"))["members"]


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def load(tag):
    raw = [json.loads(l) for l in open(f"runs/{tag}/scores.jsonl")]
    rows = {}
    for r in raw:
        if r["pair_id"] not in P or r.get("score") is None or "error" in r:
            continue
        rows[r["pair_id"]] = {"score": r["score"], "label": P[r["pair_id"]]["label"], "raw": r}
    return raw, rows


def short(pid):
    rid, eid = pid.split("|", 1)
    return f"{rid} syn {eid.split(':', 2)[2]}" if eid.startswith("synth:") else f"{rid} real {eid.rsplit(':', 1)[1]}"


# ---------------- from-scratch metrics ----------------
def thr98(rows):
    pos = sorted((r["score"] for r in rows.values() if r["label"]), reverse=True)
    k = -(-98 * len(pos) // 100)  # ceil(0.98 n) in integers
    return pos[k - 1]


def elim(rows, t):
    neg = [r["score"] for r in rows.values() if not r["label"]]
    return sum(s < t for s in neg), len(neg)


def auroc(rows):
    pos = [r["score"] for r in rows.values() if r["label"]]
    neg = [r["score"] for r in rows.values() if not r["label"]]
    w = 0.0
    for p in pos:
        for n in neg:
            w += 1.0 if p > n else 0.5 if p == n else 0.0
    return w / (len(pos) * len(neg))


def relabel(rows, ids, how="flip"):
    if how == "drop":
        return {k: v for k, v in rows.items() if k not in ids}
    return {k: ({**v, "label": 1 - v["label"]} if k in ids else v) for k, v in rows.items()}


def e98(rows):
    k, n = elim(rows, thr98(rows))
    return k / n


def lchoose(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher(a, b, c, d):
    """Two-sided Fisher exact p for [[a, b], [c, d]]: sum of hypergeometric tables no more likely than observed."""
    r1, r2, c1 = a + b, c + d, a + c
    n = r1 + r2
    lp = lambda x: lchoose(r1, x) + lchoose(r2, c1 - x) - lchoose(n, c1)
    obs = lp(a)
    tot = 0.0
    for x in range(max(0, c1 - r2), min(r1, c1) + 1):
        if lp(x) <= obs + 1e-7:
            tot += math.exp(lp(x))
    return min(1.0, tot)


def wilson(k, n):
    z = 1.959964
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


def kn(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({k / n:.1%}, {lo:.1%}-{hi:.1%})"


def table(h, rows):
    print("| " + " | ".join(h) + " |")
    print("|" + "---|" * len(h))
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")
    print()


# ---------------- own heuristics ----------------
ADDR = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
ACPG = re.compile(r"(?i)\bACPG\b|alpine\s+community\s+planning(?!\s+area)|alpine\s+cpg|alpine\s+planning\s+group")
MEMBER_ADDRS = {a.lower() for m in ROSTER for a in m["email_addresses"]}


def recipients(e):
    s = " ".join(str(e.get(k) or "") for k in ("to", "cc", "bcc"))
    found = {a.lower() for a in ADDR.findall(s)}
    if found:
        return len(found)
    return len([x for x in s.split(";") if x.strip() and x.strip() != "None"])  # names only: "Last, First; ..."


def addrs(e, keys):
    return {a.lower() for k in keys for a in ADDR.findall(str(e.get(k) or ""))}


def acpg_visible(e):
    vis = (e.get("subject") or "") + "\n" + (e.get("body") or "")[:CAP] + "\n" + " ".join(e.get("attachments") or [])
    return bool(ACPG.search(vis))


def member_recipient_only(e):
    """A roster address among To/Cc/Bcc/Delivered-To and none in From."""
    rec = addrs(e, ("to", "cc", "bcc", "delivered_to"))
    frm = addrs(e, ("from",))
    return bool(rec & MEMBER_ADDRS) and not (frm & MEMBER_ADDRS)


def email(pid):
    return E[P[pid]["email_id"]]


def main():
    main_runs, ros_runs, raws = {}, {}, {}
    for m, t in MODELS:
        raws[m], main_runs[m] = load(t)
        raws[m + " +r"], ros_runs[m] = load(t + "_roster")

    # ---------------- V1 ----------------
    print("# Branch C verification\n")
    print("## V1. Data integrity\n")
    out = []
    for m, t in MODELS:
        for tag, key, rows in ((t, m, main_runs[m]), (t + "_roster", m + " +r", ros_runs[m])):
            raw = raws[key]
            ids = [r["pair_id"] for r in raw]
            dup = sum(v > 1 for v in collections.Counter(ids).values())
            stale = sum(1 for r in raw if r["pair_id"] in P and r.get("label") != P[r["pair_id"]]["label"])
            out.append([tag, len(raw), len(rows), dup, sum(r["pair_id"] not in P for r in raw), stale,
                        sum(v["label"] for v in rows.values()), sum(1 - v["label"] for v in rows.values())])
    table(["run", "rows in scores.jsonl", "rows used", "duplicate pair_ids", "not in pairs.jsonl",
           "label differs from pairs.jsonl", "positives", "negatives"], out)
    r25 = {p for p in P if p.startswith("25-3152|")}
    print(f"Roster runs cover exactly the 25-3152 pairs: "
          f"{all(set(ros_runs[m]) == r25 for m in NAMES)} ({len(r25)} pairs).\n")

    # ---------------- V2 ----------------
    print("## V2. From-scratch thr98, elim@98 and AUROC\n")
    sys.path.insert(0, "scripts")
    from analyze import auroc as repo_auroc  # cross-check only
    from golden_report import thr98 as repo_thr98
    # headline of docs/findings-golden.md §1, labels of 2026-11-11
    ref = {"4b lp": (0.922, 53), "9b lp": (0.945, 72), "27b lp": (0.977, 77), "d3-4b": (0.901, 55),
           "d3-9b": (0.957, 70), "d3-27b": (0.983, 83), "Jev": (0.917, 64)}
    out = []
    T, TR = {}, {}
    for m in NAMES:
        rows = main_runs[m]
        t = T[m] = thr98(rows)
        k, n = elim(rows, t)
        a = auroc(rows)
        nm = sum(1 for r in rows.values() if r["label"] and r["score"] < t)
        rr = list(rows.values())
        ra = repo_auroc([r["score"] for r in rr], [r["label"] for r in rr])
        rt = repo_thr98(rr)
        out.append([m, f"{t:.4f}", nm, kn(k, n), f"{a:.5f}", f"{ref[m][0]:.3f} / {ref[m][1]}%",
                    "yes" if abs(a - ra) < 1e-12 and t == rt else f"NO ({ra:.5f}, {rt})"])
    table(["model", "thr98", "positives below thr98", "elim@98 (k/n, Wilson 95%)", "AUROC (pairwise)",
           "brief headline AUROC / elim@98", "matches repo helpers"], out)
    out = []
    for m in NAMES:
        rows = ros_runs[m]
        t = TR[m] = thr98(rows)
        k, n = elim(rows, t)
        out.append([m + " +roster", f"{t:.4f}", sum(1 for r in rows.values() if r["label"] and r["score"] < t),
                    kn(k, n), f"{auroc(rows):.5f}"])
    table(["model", "thr98", "positives below thr98", "elim@98", "AUROC"], out)
    jt = sorted({round(v["score"], 6) for v in main_runs["Jev"].values()})
    jev_tie = sum(1 for v in main_runs["Jev"].values() if v["score"] == T["Jev"])
    print(f"Jev has {len(jt)} distinct scores on {N_ALL} pairs; {jev_tie} pairs score exactly its thr98 ({T['Jev']}) "
          f"and are counted as kept (score >= threshold).\n")

    # ---------------- V3 ----------------
    print("## V3. Consensus sets\n")
    pos = sorted(p for p in P if P[p]["label"])
    neg = sorted(p for p in P if not P[p]["label"])
    def miss(m, p, t): return main_runs[m][p]["score"] < t
    def kept(m, p, t): return main_runs[m][p]["score"] >= t
    cm98 = [p for p in pos if sum(miss(m, p, T[m]) for m in NAMES) >= 3]
    cm50 = [p for p in pos if sum(miss(m, p, 0.5) for m in NAMES) >= 3]
    cf98 = [p for p in neg if sum(kept(m, p, T[m]) for m in NAMES) >= 5]
    cf50 = [p for p in neg if sum(kept(m, p, 0.5) for m in NAMES) >= 5]
    ev98 = sum(miss(m, p, T[m]) for m in NAMES for p in pos)
    dist98 = len({p for p in pos if any(miss(m, p, T[m]) for m in NAMES)})
    print(f"- miss events at thr98: {ev98}; distinct positives missed: {dist98}")
    print(f"- consensus misses at thr98: {len(cm98)}: {', '.join(short(p) for p in cm98)}")
    print(f"- consensus misses at 0.5: {len(cm50)} ({sum(p.startswith('25-3152') for p in cm50)} from 25-3152): "
          f"{', '.join(short(p) for p in cm50)}")
    hn = [p for p in neg if P[p]["kind"] == "hard_negative"]
    rn = [p for p in neg if P[p]["kind"] == "real_negative"]
    print(f"- consensus FPs at thr98: {len(cf98)}, at 0.5: {len(cf50)}, at 0.5 but not thr98: {len(set(cf50) - set(cf98))}")
    print(f"- all consensus FPs are hard negatives: {all(P[p]['kind'] == 'hard_negative' for p in set(cf98) | set(cf50))}; "
          f"hard negatives that are consensus FPs at thr98: {kn(sum(p in cf98 for p in hn), len(hn))}")
    print(f"- most models keeping any one real negative at thr98: {max(sum(kept(m, p, T[m]) for m in NAMES) for p in rn)}")
    for rec in ("same_subject_wrong_date", "same_people_different_subject", "keyword_unrelated_sense"):
        g = [p for p in hn if P[p]["recipe"] == rec]
        print(f"- {rec}: {sum(p in cf98 for p in g)}/{len(g)} consensus FP at thr98")
    print()

    # ---------------- V4 ----------------
    print("## V4. Recipient count and ACPG named (own heuristics)\n")
    c50 = set(cm50)
    rc = {p: recipients(email(p)) for p in pos}
    many = [p for p in pos if rc[p] >= 10]
    few = [p for p in pos if rc[p] < 10]
    a, c = sum(p in c50 for p in many), sum(p in c50 for p in few)
    print(f"- consensus misses at 0.5 with >= 10 recipients {kn(a, len(many))} vs fewer {kn(c, len(few))}; "
          f"Fisher p = {fisher(a, len(many) - a, c, len(few) - c):.3g}")
    print(f"- recipients of the 7 'member among many' misses: "
          f"{sorted(rc[p] for p in c50 if p.startswith('25-3152') and rc[p] >= 10)}")
    p25 = [p for p in pos if p.startswith("25-3152")]
    nn = [p for p in p25 if not acpg_visible(email(p))]
    yy = [p for p in p25 if acpg_visible(email(p))]
    a, c = sum(p in c50 for p in nn), sum(p in c50 for p in yy)
    print(f"- 25-3152 positives, ACPG not named in subject/visible body/attachment names: {kn(a, len(nn))} consensus misses "
          f"vs named {kn(c, len(yy))}; Fisher p = {fisher(a, len(nn) - a, c, len(yy) - c):.3g}")
    m25 = [p for p in p25 if rc[p] >= 10]
    f25 = [p for p in p25 if rc[p] < 10]
    a, c = sum(p in c50 for p in m25), sum(p in c50 for p in f25)
    print(f"- within 25-3152: >= 10 recipients {kn(a, len(m25))} vs fewer {kn(c, len(f25))}; p = "
          f"{fisher(a, len(m25) - a, c, len(f25) - c):.3g}")
    print(f"- 25-3152 share of positives with >= 10 recipients: {len(m25)}/{len(many)}\n")
    print("The cut at 10 was chosen after the misses were read (their counts are 19-31). Other cuts, all positives:\n")
    out = []
    for cut in (3, 5, 10, 15, 20):
        g = [p for p in pos if rc[p] >= cut]; h = [p for p in pos if rc[p] < cut]
        a, c = sum(p in c50 for p in g), sum(p in c50 for p in h)
        out.append([f">= {cut}", kn(a, len(g)), kn(c, len(h)), f"{fisher(a, len(g) - a, c, len(h) - c):.3g}"])
    table(["recipients", "consensus misses at 0.5, at/above", "below", "Fisher p"], out)
    print("Per-model misses at 0.5 among 25-3152 positives, by recipient count (>= 10 vs fewer):\n")
    out = []
    for m in NAMES:
        a = sum(miss(m, p, 0.5) for p in m25); c = sum(miss(m, p, 0.5) for p in f25)
        out.append([m, kn(a, len(m25)), kn(c, len(f25)), f"{fisher(a, len(m25) - a, c, len(f25) - c):.3g}"])
    table(["model", ">= 10 recipients", "fewer", "Fisher p"], out)

    # ---------------- V5 ----------------
    print("## V5. Roster comparability: same 249 pairs, each run's own thr98\n")
    print(f"The analyst's main-set thr98 is fitted on all {N_ALL} pairs (5 misses allowed, anywhere); the roster thr98 on "
          "the 249 25-3152 pairs (2 allowed). Here the main runs are restricted to the same 249 pairs and refitted.\n")
    m249 = {m: {p: v for p, v in main_runs[m].items() if p in r25} for m in NAMES}
    T249 = {m: thr98(m249[m]) for m in NAMES}
    p249 = sorted(p for p in r25 if P[p]["label"]); n249 = sorted(p for p in r25 if not P[p]["label"])
    def cons(runs, thr, ids, k, is_miss):
        f = (lambda m, p: runs[m][p]["score"] < thr[m]) if is_miss else (lambda m, p: runs[m][p]["score"] >= thr[m])
        return [p for p in ids if sum(f(m, p) for m in NAMES) >= k]
    half = {m: 0.5 for m in NAMES}
    T495 = T
    rows = [
        (f"main, thr98 fitted on all {N_ALL} (analyst)", main_runs, T495),
        ("main, thr98 refitted on the 249", m249, T249),
        ("roster, thr98 fitted on the 249 (analyst)", ros_runs, TR),
        ("main, 0.5", main_runs, half),
        ("roster, 0.5", ros_runs, half),
    ]
    out = []
    for lbl, runs, thr in rows:
        cmx = cons(runs, thr, p249, 3, True)
        cfx = cons(runs, thr, n249, 5, False)
        ev = sum(runs[m][p]["score"] < thr[m] for m in NAMES for p in p249)
        el = [elim({p: runs[m][p] for p in r25}, thr[m]) for m in NAMES]
        out.append([lbl, ev, len(cmx), len(cfx), f"{sum(k for k, _ in el) / sum(n for _, n in el):.1%}"])
    table(["view (25-3152 pairs only)", "25-3152 miss events (7 models)", "consensus misses (>= 3)",
           "consensus FPs (>= 5)", f"pooled share of the {NN['25-3152']} negatives eliminated"], out)
    print("thr98 refitted on the 249 (main runs): " + ", ".join(f"{m} {T249[m]:.4f}" for m in NAMES) + "\n")
    cf249 = cons(m249, T249, n249, 5, False)
    cfr = cons(ros_runs, TR, n249, 5, False)
    print(f"- main refitted consensus FPs: {', '.join(short(p) for p in cf249)}")
    print(f"- roster consensus FPs: {', '.join(short(p) for p in cfr)} "
          f"(all 15:0x 'purely personal': {all(short(p).startswith('25-3152 syn 15:') for p in cfr)})\n")

    # ---------------- V6 ----------------
    print("## V6. Q5: the 'one member among many' reading\n")
    q5s = ["25-3152 real 48517463", "25-3152 real 48517567", "25-3152 real 48517588", "25-3152 real 48517769",
           "25-3152 real 48517957", "25-3152 real 48518005", "25-3152 syn 20:06"]
    byshort = {short(p): p for p in P}
    q5 = {byshort[s] for s in q5s}
    rule = sorted(p for p in p25 if member_recipient_only(email(p)) and not acpg_visible(email(p)) and rc[p] >= 10)
    rule_any = sorted(p for p in p25 if member_recipient_only(email(p)) and not acpg_visible(email(p)))
    print(f"- the analyst's 7 are inside the rule set (member only as recipient, ACPG not named, >= 10 recipients): "
          f"{q5 <= set(rule)}; the rule matches {len(rule)} 25-3152 positives; without the >= 10 condition, {len(rule_any)}.")
    caught = [p for p in rule if p not in q5]
    print(f"- the {len(caught)} rule matches not flipped by Q5: " + ", ".join(short(p) for p in caught))
    print(f"  models missing each at 0.5: " + ", ".join(str(sum(miss(m, p, 0.5) for m in NAMES)) for p in caught) + "\n")
    out = []
    # Q1, Q3 and Q5 were decided by the owner on 2026-11-08 (all responsive); "flip" reverses the current label.
    q4 = {byshort[f"25-3152 syn 15:0{i}"] for i in (3, 4, 5, 7, 8, 9)}
    q3 = {byshort[s] for s in ("25-3152 syn 15:01", "25-3152 syn 15:02", "25-3152 syn 15:06")}
    q1 = {byshort[s] for s in ("24-409 syn 03:01", "24-409 syn 03:09")}
    variants = [("Q1 check: 03:01, 03:09 back to non-responsive", q1, "flip"),
                ("Q3 check: 15:01, 15:02, 15:06 back to purely personal", q3, "flip"),
                ("Q4 check: the six remaining 'purely personal' 15:0x to responsive", q4, "flip"),
                ("Q5 as reported: flip the 7", q5, "flip"), ("drop the 7 instead of flipping", q5, "drop"),
                (f"flip every rule match (n={len(rule)})", set(rule), "flip"),
                (f"flip every match without the >= 10 condition (n={len(rule_any)})", set(rule_any), "flip")]
    for lbl, ids, how in variants:
        d = []
        for m in NAMES:
            base = e98(main_runs[m])
            d.append(e98(relabel(main_runs[m], ids, how)) - base)
        da = [auroc(relabel(main_runs[m], ids, how)) - auroc(main_runs[m]) for m in NAMES]
        on_roster = any(p in r25 for p in ids)
        dr = [e98(relabel(ros_runs[m], ids, how)) - e98(ros_runs[m]) for m in NAMES]
        out.append([lbl] + [f"{100 * x:+.1f}" for x in d] + [f"{100 * sum(d) / 7:+.1f}", f"{sum(da) / 7:+.4f}",
                                                             f"{100 * sum(dr) / 7:+.1f}" if on_roster else "—"])
    table(["variant"] + [f"Δelim@98 {m}" for m in NAMES] + ["mean Δelim@98", "mean ΔAUROC", "mean Δelim@98 +roster"], out)
    rng = random.Random(SEED)
    posl = [p for p in sorted(P) if P[p]["label"]]; negl = [p for p in sorted(P) if not P[p]["label"]]
    deltas = {m: [] for m in NAMES}
    meand = []
    for _ in range(BOOT):
        bs = rng.choices(posl, k=len(posl)) + rng.choices(negl, k=len(negl))
        ds = []
        for m in NAMES:
            rws = {i: main_runs[m][p] for i, p in enumerate(bs)}
            flp = {i: ({**main_runs[m][p], "label": 0} if p in q5 else main_runs[m][p]) for i, p in enumerate(bs)}
            x = e98(flp) - e98(rws)
            deltas[m].append(x); ds.append(x)
        meand.append(sum(ds) / 7)
    ci = lambda xs: (sorted(xs)[int(0.025 * len(xs))], sorted(xs)[int(0.975 * len(xs)) - 1])
    print(f"Paired stratified bootstrap ({BOOT} resamples, seed {SEED}) of the Q5 flip, Δelim@98 95% percentile interval:\n")
    table(["model", "Δelim@98 95% CI (pp)"], [[m, f"{100 * ci(deltas[m])[0]:+.1f} to {100 * ci(deltas[m])[1]:+.1f}"] for m in NAMES]
          + [["mean of 7", f"{100 * ci(meand)[0]:+.1f} to {100 * ci(meand)[1]:+.1f}"]])

    # ---------------- V7 ----------------
    print("## V7. C5a single flips: the denominator effect\n")
    pid = byshort["25-3152 syn 15:02"]
    was_neg = not P[pid]["label"]  # a negative until 2026-11-08; the owner then called it responsive
    print("Reversing the label of an email every model keeps (score >= thr98) leaves thr98 unchanged (it sits above "
          f"the cutoff either way) and {'removes' if was_neg else 'adds'} one kept negative, so elim@98 goes from k/n to "
          f"k/(n{' - ' if was_neg else ' + '}1). Predicted vs recomputed for 25-3152 syn 15:02 (now "
          f"{'non-responsive' if was_neg else 'responsive'}):\n")
    out = []
    for m in NAMES:
        k, n = elim(main_runs[m], T[m])
        pred = k / (n - 1 if was_neg else n + 1) - k / n
        act = e98(relabel(main_runs[m], {pid})) - e98(main_runs[m])
        out.append([m, f"{k}/{n}", f"{100 * pred:+.2f}", f"{100 * act:+.2f}"])
    table(["model", "eliminated at thr98", "predicted Δ (pp)", "recomputed Δ (pp)"], out)

    # ---------------- V8 ----------------
    print("## V8. Truncation, per model\n")
    tr = [p for p in pos if main_runs["27b lp"][p]["raw"]["truncated"]]
    nt = [p for p in pos if not main_runs["27b lp"][p]["raw"]["truncated"]]
    same = all(bool(main_runs[m][p]["raw"]["truncated"]) == (p in tr) for m in NAMES for p in pos)
    print(f"Truncated positives: {len(tr)} (flag identical across the 7 runs: {same}); consensus misses at 0.5 among them: "
          f"{', '.join(short(p) for p in tr if p in c50)}\n")
    out = []
    for lbl, thr in (("0.5", half), ("thr98", T)):
        for m in NAMES:
            a = sum(main_runs[m][p]["score"] < thr[m] for p in tr); c = sum(main_runs[m][p]["score"] < thr[m] for p in nt)
            out.append([lbl, m, kn(a, len(tr)), kn(c, len(nt)), f"{fisher(a, len(tr) - a, c, len(nt) - c):.3g}"])
        a = sum(main_runs[m][p]["score"] < thr[m] for m in NAMES for p in tr)
        c = sum(main_runs[m][p]["score"] < thr[m] for m in NAMES for p in nt)
        out.append([lbl, "pooled events (not independent)", kn(a, 7 * len(tr)), kn(c, 7 * len(nt)), "—"])
    table(["cutoff", "model", "missed, truncated", "missed, not truncated", "Fisher p"], out)

    # ---------------- V9 ----------------
    print("## V9. Request split per model at 0.5, with a Bonferroni bound\n")
    p24 = [p for p in pos if p.startswith("24-409")]
    out = []
    for m in NAMES:
        a = sum(miss(m, p, 0.5) for p in p25); c = sum(miss(m, p, 0.5) for p in p24)
        pv = fisher(a, len(p25) - a, c, len(p24) - c)
        out.append([m, kn(a, len(p25)), kn(c, len(p24)), f"{pv:.3g}", "yes" if pv < 0.05 / 7 else "no"])
    table(["model", "25-3152 missed", "24-409 missed", "Fisher p", "below 0.05/7"], out)
    a = sum(miss(m, p, 0.5) for m in NAMES for p in p25); c = sum(miss(m, p, 0.5) for m in NAMES for p in p24)
    print(f"Pooled miss events at 0.5 (not independent): 25-3152 {kn(a, 7 * len(p25))}, 24-409 {kn(c, 7 * len(p24))}. "
          f"Consensus misses at 0.5: 25-3152 {sum(p in c50 for p in p25)}/{len(p25)}, 24-409 {sum(p in c50 for p in p24)}/{len(p24)}, "
          f"Fisher p = {fisher(sum(p in c50 for p in p25), len(p25) - sum(p in c50 for p in p25), sum(p in c50 for p in p24), len(p24) - sum(p in c50 for p in p24)):.3g}.\n")
    print(f"C4c runs {6 + 2} consensus-miss tests and 7 per-model tests (15 in all); a Bonferroni bound for 15 is p < {0.05 / 15:.4f}.\n")

    # ---------------- V10 ----------------
    print("## V10. Wrong-date negatives: original window vs distance from the refined window\n")
    import datetime as dt
    def days_out(d, lo, hi):
        d = dt.date.fromisoformat(d)
        lo = dt.date.fromisoformat(lo); hi = dt.date.fromisoformat(hi)
        return (lo - d).days if d < lo else (d - hi).days if d > hi else 0
    out = []
    for rid, lo, hi in (("24-409", "2023-01-01", "2023-07-31"), ("25-3152", "2024-01-01", "2025-05-31")):
        for p in sorted((p for p in neg if p.startswith(rid) and P[p]["recipe"] == "same_subject_wrong_date"),
                        key=lambda p: email(p)["date"]):
            d = email(p)["date"][:10]
            orig = ("yes" if "2022-01-01" <= d <= "2024-04-16" else "no") if rid == "24-409" else "—"
            out.append([short(p), d, days_out(d, lo, hi), orig] +
                       [f"{main_runs[m][p]['score']:.2f}" for m in ("27b lp", "d3-27b")])
    table(["pair", "date", "days outside the refined window", "in original 24-409 window", "27b lp", "d3-27b"], out)
    for m in ("27b lp", "d3-27b"):
        g = lambda f: [main_runs[m][p]["score"] for p in neg if p.startswith("24-409") and P[p]["recipe"] == "same_subject_wrong_date" and f(email(p)["date"][:10])]
        ins = g(lambda d: "2022-01-01" <= d <= "2024-04-16"); outs = g(lambda d: not "2022-01-01" <= d <= "2024-04-16")
        print(f"- {m}: mean inside original window {sum(ins) / len(ins):.3f} (n={len(ins)}), outside both {sum(outs) / len(outs):.3f} (n={len(outs)})")
    print()

    # ---------------- V11 ----------------
    print("## V11. JSON spot checks\n")
    jr = {}
    for l in open("runs/golden_qwen3.8_27b_json_reason_p2/scores.jsonl"):
        r = json.loads(l)
        if r["pair_id"] in P and r.get("score") is not None:
            jr[r["pair_id"]] = r
    c25 = [p for p in cm50 if p.startswith("25-3152")]
    print(f"- 27b jsonR verdict on the {len(c25)} 25-3152 consensus misses: "
          f"{collections.Counter('yes' if jr[p]['verdict'] else 'no' for p in c25 if p in jr)}")
    jrr = {}
    for l in open("runs/golden_qwen3.8_27b_json_reason_p2_roster/scores.jsonl"):
        r = json.loads(l)
        if r["pair_id"] in P and r.get("score") is not None:
            jrr[r["pair_id"]] = r
    for lbl, J in (("without roster", jr), ("with roster", jrr)):
        ys = [short(p) for p in sorted(q5) if J[p]["verdict"]]
        mer = sum(bool(re.search(r"(?i)\bmerely\b", J[p].get("raw", ""))) for p in q5)
        print(f"- 27b jsonR {lbl}, the 7 'member among many' misses: yes on {len(ys)}/7 ({', '.join(ys) or 'none'}); "
              f"reasoning uses 'merely' in {mer}/7")
    j4 = {}
    for l in open("runs/golden_qwen3.5_4b_json_p2/scores.jsonl"):
        r = json.loads(l)
        if r["pair_id"] in P and r.get("score") is not None:
            j4[r["pair_id"]] = r
    fu = sorted(set(cf98) | set(cf50))
    print(f"- 4b json says yes on {sum(bool(j4[p]['verdict']) for p in fu if p in j4)}/{sum(p in j4 for p in fu)} consensus FPs "
          f"and {sum(bool(j4[p]['verdict']) for p in neg if p in j4)}/{sum(p in j4 for p in neg)} negatives")
    for s, pat in (("24-409 syn 04:06", r"(?i)2022|original"), ("25-3152 syn 18:07", r"(?i)known ACPG member|ACPG member")):
        raw = jr[byshort[s]].get("raw", "")
        m_ = re.search(pat, raw)
        print(f"- {s} 27b jsonR (verdict {jr[byshort[s]]['verdict']}): ..."
              f"{raw[max(0, m_.start() - 160): m_.end() + 120] if m_ else raw[:300]!r}...")
    print()

    # ---------------- V12 ----------------
    print("## V12. Label-reading spot checks (records, not statistics)\n")
    adj = json.load(open("data/golden/work/adjudications.json"))
    items = json.load(open("data/golden/work/adjudication_items.json"))
    items = items["items"] if isinstance(items, dict) and "items" in items else list(items.values()) if isinstance(items, dict) else items
    ver = {}
    for it in items:
        s = json.dumps(it)
        for k in re.findall(r"synth:24-409:\d\d:\d\d", s)[:1]:
            ver[k] = it
    out = []
    for s in ("03:01", "03:04", "03:07", "03:09", "06:01", "06:03"):
        eid = f"synth:24-409:{s}"
        a = adj.get(eid) or adj.get(f"24-409~{eid}") or {}
        v = ver.get(eid, {})
        out.append([s, P[f"24-409|{eid}"]["label"], P[f"24-409|{eid}"]["kind"], a.get("call", "—"), repr(a.get("note", "")),
                    v.get("verify_label_correct", "—")])
    table(["24-409 syn", "label", "kind", "owner call", "owner note", "verifier: label correct?"], out)
    eid = "synth:24-409:07:01"
    syn = {json.loads(l)["id"]: json.loads(l) for l in open("data/golden/work/synthetic.jsonl")}
    print(f"- 07:01 owner call: {(adj.get(eid) or adj.get('24-409~' + eid) or {}).get('call', 'none')}; verifier says "
          f"'adjudicator should confirm': {'adjudicator should confirm' in syn[eid].get('verify_problem', '')}; "
          f"07:09 call: {(adj.get('synth:24-409:07:09') or {}).get('call')}; 07:09 in pairs.jsonl: "
          f"{any(p.endswith('synth:24-409:07:09') for p in P)}")
    e = email(byshort["24-409 syn 02:01"])
    print(f"- 02:01 body length {len(e['body']):,} chars (cap {CAP:,}); truncated flag in the 27b lp run: "
          f"{main_runs['27b lp'][byshort['24-409 syn 02:01']]['raw']['truncated']}")
    names = {a.lower(): m["name"] for m in ROSTER for a in m["email_addresses"]}
    for p in sorted(q5):
        e = email(p)
        hit = sorted({(names[a], k) for k in ("from", "to", "cc", "bcc", "delivered_to") for a in addrs(e, (k,)) if a in names})
        print(f"- {short(p)}: roster members in headers {hit}; recipients {rc[p]}")
    print()


if __name__ == "__main__":
    main()
