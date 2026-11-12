"""Independent verification of branch D (docs/analysis/D-validity.md). Skeptic's script.

  uv run python scripts/analysis/d_validity_verify.py [--boot 2000]

Does NOT import any d_validity_* module. Loads the runs itself, joins labels from data/golden/pairs.jsonl, and
implements AUROC (all positive-negative pairs, ties count half), thr98 (the m-th highest positive score, m =
ceil(0.98 * positives), integer arithmetic) and elim@98 (negatives with score < thr98) from scratch. The repo's
scripts/analyze.py helpers are imported only to cross-check those three implementations.

Prints V0 (join hygiene: stale labels in scores.jsonl), V1 (own metrics vs repo helpers, headline numbers),
V2 (subsets a and f; f re-derived from dates, not recipes), V3 (where headline elimination comes from),
V4 (real negatives' dates), V5 (per-request gap with an independent bootstrap and a Bonferroni interval),
V6 (Kendall tau between requests vs a resampling-noise baseline), V6b (is the request gap larger for stock Qwen
than for d3 of the same size?), V7 (roster: pair coverage and paired delta),
V8 (Jev ties), V9 (25-3152 real-only drop: positives or negatives?), V10 (subset f sensitivity to the miss
allowance), V11 (keyword-proxy circularity on 25-3152), V12 (a stricter search-like hard-negative subset, with my
own keyword proxy), V13 (run.json settings behind L-3 and L-4), V14 (three spot-read notes checked against the data).
Stdlib only, deterministic (random.Random with fixed seeds).
"""
import argparse
import collections
import datetime
import difflib
import json
import random
import re
import sys

RUNS = [("4b lp", "golden_qwen3.5_4b_logprob_p2db"), ("9b lp", "golden_qwen3.5_9b_logprob_p2db"),
        ("27b lp", "golden_qwen3.8_27b_logprob_p2"), ("d3-4b", "golden_d3-ctx8k_4b_noul_p2"),
        ("d3-9b", "golden_d3-ctx8k_9b_noul_p2"), ("d3-27b", "golden_d3-ctx8k_27b_noul_p2"),
        ("Jev", "golden_jev-1.14.0_noul_p2")]
JSON_TAGS = ["golden_qwen3.5_4b_json_p2", "golden_qwen3.5_9b_json_p2", "golden_qwen3.8_27b_json_p2",
             "golden_qwen3.5_4b_json_reason_p2", "golden_qwen3.5_9b_json_reason_p2", "golden_qwen3.8_27b_json_reason_p2"]
# headline of docs/findings-golden.md §1 on the labels of 2026-11-11 (the brief's 2026-10-31 values were 0.923/52, 0.942/71,
# 0.975/76, 0.884/54, 0.947/68, 0.979/81, 0.916/63)
HEADLINE = {"4b lp": (0.922, 53), "9b lp": (0.945, 72), "27b lp": (0.977, 77), "d3-4b": (0.901, 55),
            "d3-9b": (0.957, 70), "d3-27b": (0.983, 83), "Jev": (0.917, 64)}
# date windows read from data/emails/sandiego.requests.jsonl request texts
WIN = {"24-409": (datetime.date(2023, 1, 1), datetime.date(2023, 7, 31)),
       "25-3152": (datetime.date(2024, 1, 1), datetime.date(2025, 5, 31))}


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def jl(path):
    with open(path) as f:
        return [json.loads(x) for x in f]


P = {p["pair_id"]: p for p in jl("data/golden/pairs.jsonl")}
EM = {f"{e['request_id']}|{e['id']}": e for e in jl("data/golden/emails.jsonl")}
NULLS = {}


def load(tag):
    """pair_id -> dict(score, label, kind, recipe, rid) with labels from pairs.jsonl. Also returns hygiene counts."""
    out, stale, unknown, null = {}, 0, 0, 0
    NULLS.setdefault(tag, [])
    for r in jl(f"runs/{tag}/scores.jsonl"):
        p = P.get(r["pair_id"])
        if p is None:
            unknown += 1
            continue
        if r.get("label") is not None and r["label"] != p["label"]:
            stale += 1
        if r.get("error") or r.get("score") is None:
            null += 1
            if r["pair_id"] not in NULLS[tag]:
                NULLS[tag].append(r["pair_id"])
            continue
        out[r["pair_id"]] = {"score": float(r["score"]), "label": p["label"], "kind": p["kind"],
                             "recipe": p["recipe"], "rid": p["request_id"], "wall": r.get("wall_ms")}
    return out, stale, unknown, null


# ---------------- metrics from scratch ----------------
def my_auroc(pos, neg):
    """P(random positive > random negative), ties half. O(n_pos * n_neg), no sorting tricks."""
    gt = eq = 0
    for x in pos:
        for y in neg:
            if x > y:
                gt += 1
            elif x == y:
                eq += 1
    return (gt + 0.5 * eq) / (len(pos) * len(neg))


def my_thr98(pos):
    m = -(-98 * len(pos) // 100)  # ceil(0.98 n) in integers
    return sorted(pos, reverse=True)[m - 1], len(pos) - m


def my_elim(pos, neg):
    t, allowed = my_thr98(pos)
    k = sum(1 for y in neg if y < t)
    return k, len(neg), t, allowed


def split(rows):
    pos = [r["score"] for r in rows if r["label"] == 1]
    neg = [r["score"] for r in rows if r["label"] == 0]
    return pos, neg


def metrics(rows):
    pos, neg = split(rows)
    k, n, t, allowed = my_elim(pos, neg)
    return {"auroc": my_auroc(pos, neg), "k": k, "n": n, "thr": t, "allowed": allowed, "npos": len(pos)}


def fast_auroc(pos, neg):
    """Sort-based AUROC for the bootstraps (checked against my_auroc in V1)."""
    allv = sorted([(x, 1) for x in pos] + [(y, 0) for y in neg])
    rank_sum = 0.0; i = 0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        r = (i + 1 + j) / 2
        rank_sum += r * sum(1 for a in allv[i:j] if a[1])
        i = j
    n1, n0 = len(pos), len(neg)
    return (rank_sum - n1 * (n1 + 1) / 2) / (n1 * n0)


def pctl(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))]


def parse_date(s):
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)", s)
    if m:
        return datetime.date(*map(int, m.groups()))
    m = re.search(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})", s)
    if m:
        try:
            return datetime.datetime.strptime(" ".join(m.groups()), "%B %d %Y").date()
        except ValueError:
            return None
    return None


def kendall(a, b):
    n = len(a); s = 0
    for i in range(n):
        for j in range(i + 1, n):
            s += ((a[i] > a[j]) - (a[i] < a[j])) * ((b[i] > b[j]) - (b[i] < b[j]))
    return s / (n * (n - 1) / 2)


def table(h, rows):
    print("| " + " | ".join(h) + " |")
    print("|" + "---|" * len(h))
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args()
    R = {}
    print("# Branch D verification (independent recomputation)\n")

    print("## V0. Join hygiene: labels in scores.jsonl vs data/golden/pairs.jsonl\n")
    out = []
    for name, tag in RUNS + [(t, t) for t in JSON_TAGS]:
        rows, stale, unknown, null = load(tag)
        if name in dict(RUNS):
            R[name] = rows
        rr, s2, u2, n2 = load(tag + "_roster")
        out.append([name, len(rows), stale, unknown, null, len(rr), s2, u2, n2])
    table(["run", "scored rows", "stale label in scores.jsonl", "pair_id not in pairs.jsonl", "null/error",
           "roster rows", "roster stale", "roster unknown", "roster null"], out)
    ko = collections.Counter((e["kind"], e["origin"]) for e in EM.values())
    print("Kind × origin in data/golden/emails.jsonl: " + ", ".join(f"{k} / {o}: {n}" for (k, o), n in sorted(ko.items())) + "\n")
    nl = [(t, p) for t, ps in NULLS.items() for p in ps]
    print(f"Unscored rows across main and roster runs: {len(nl)}")
    for t, p in nl:
        print(f"- {t}: {p} ({P[p]['kind']})")
    print()

    print(f"## V1. Own AUROC / thr98 / elim@98 vs the repo helpers (scripts/analyze.py), all {N_ALL} pairs\n")
    sys.path.insert(0, "scripts")
    from analyze import at_recall, auroc, pr_curve  # cross-check only
    out = []
    for name, _ in RUNS:
        rows = list(R[name].values())
        m = metrics(rows)
        s = [r["score"] for r in rows]; l = [r["label"] for r in rows]
        ra = auroc(s, l); rt, _, _, re_ = at_recall(pr_curve(s, l), 0.98)
        fa = fast_auroc(*split(rows))
        hl = HEADLINE[name]
        ok = abs(round(m["auroc"], 3) - hl[0]) < 1e-9 and round(100 * m["k"] / m["n"]) == hl[1]
        out.append([name, f"{m['auroc']:.4f}", f"{ra:.4f}", f"{fa:.4f}", f"{m['thr']:.4g}", f"{rt:.4g}",
                    f"{m['k']}/{m['n']} ({m['k'] / m['n']:.1%})", f"{re_:.1%}", f"{m['npos'] - m['allowed']}/{m['npos']}",
                    "match" if ok else "MISMATCH"])
    table(["run", "AUROC (own pairwise)", "AUROC (repo)", "AUROC (own sort)", "thr98 (own)", "thr98 (repo)",
           "elim@98 (own)", "elim@98 (repo)", "positives flagged", "vs brief headline"], out)

    def in_win(pid):
        d = parse_date(EM[pid].get("date"))
        if d is None:
            return None
        lo, hi = WIN[P[pid]["request_id"]]
        return lo <= d <= hi

    print("## V2. Subsets (a) real+ vs real− and (f) real+ vs in-window hard−\n")
    hn = [p for p, x in P.items() if x["kind"] == "hard_negative"]
    f_date = {p for p in hn if in_win(p)}
    f_recipe = {p for p in hn if P[p]["recipe"] != "same_subject_wrong_date"}
    unk = [p for p in hn if in_win(p) is None]
    print(f"Hard negatives: {len(hn)}; in window by my own date parse: {len(f_date)}; non-wrong-date recipe: "
          f"{len(f_recipe)}; the two sets identical: {f_date == f_recipe}; hard negatives with unparseable date: {len(unk)}\n")
    out = []
    for name, _ in RUNS:
        rows = R[name].values()
        ra = [r for r in rows if r["kind"] in ("real_positive", "real_negative")]
        rf = [r for p, r in R[name].items() if r["kind"] == "real_positive" or p in f_date]
        ma, mf = metrics(ra), metrics(rf)
        out.append([name, f"{ma['auroc']:.3f}", f"{ma['k']}/{ma['n']} ({ma['k'] / ma['n']:.0%})",
                    f"{mf['auroc']:.3f}", f"{mf['k']}/{mf['n']} ({mf['k'] / mf['n']:.0%})", f"{mf['thr']:.4g}"])
    table(["run", "(a) AUROC", "(a) elim@98", "(f) AUROC", "(f) elim@98", "(f) thr98"], out)
    gap_ca = max(abs(metrics([r for r in R[n].values() if r["label"] == 1 or r["kind"] == "real_negative"])["auroc"]
                     - metrics([r for r in R[n].values() if r["kind"] in ("real_positive", "real_negative")])["auroc"])
                 for n, _ in RUNS)
    ps, ph = [], []
    for n, _ in RUNS:
        rows = R[n].values()
        rp_ = [r["score"] for r in rows if r["kind"] == "real_positive"]
        sp_ = [r["score"] for r in rows if r["label"] == 1 and r["kind"] != "real_positive"]
        rn_ = [r["score"] for r in rows if r["kind"] == "real_negative"]
        hn_ = [r["score"] for r in rows if r["kind"] == "hard_negative"]
        ps.append(my_auroc(sp_, rp_)); ph.append(my_auroc(hn_, rn_))
    print(f"Largest |AUROC (c) − AUROC (a)| over the seven: {gap_ca:.4f}. P(synthetic+ > real+) range "
          f"{min(ps):.2f}–{max(ps):.2f}; P(hard− > real−) range {min(ph):.2f}–{max(ph):.2f}\n")

    print("## V3. Negatives cleared at the all-pairs thr98: real vs hard (wrong-date / in-window)\n")
    out = []; shares = []
    for name, _ in RUNS:
        rows = list(R[name].values())
        t = metrics(rows)["thr"]
        cl = [r for r in rows if r["label"] == 0 and r["score"] < t]
        nr = sum(r["kind"] == "real_negative" for r in cl)
        wd = sum(r["kind"] == "hard_negative" and r["recipe"] == "same_subject_wrong_date" for r in cl)
        iw = sum(r["kind"] == "hard_negative" and r["recipe"] != "same_subject_wrong_date" for r in cl)
        shares.append(nr / len(cl))
        out.append([name, len(cl), nr, wd, iw, f"{nr / len(cl):.1%}"])
    table(["run", "negatives cleared", "real−", "hard− wrong-date", "hard− in-window", "real− share of cleared"], out)
    print(f"Real− share range: {min(shares):.1%}–{max(shares):.1%}. Real− share of all negatives: "
          f"{sum(P[p]['kind'] == 'real_negative' for p in P)}/{sum(P[p]['label'] == 0 for p in P)} "
          f"({sum(P[p]['kind'] == 'real_negative' for p in P) / sum(P[p]['label'] == 0 for p in P):.1%}): "
          f"the share a model that cleared real and hard negatives at the same rate would show.\n")

    print("## V4. Real negatives: dates against the target request's window (own parser)\n")
    rn = [p for p, x in P.items() if x["kind"] == "real_negative"]
    c = collections.Counter((P[p]["request_id"], {True: "in", False: "out", None: "unknown"}[in_win(p)]) for p in rn)
    table(["request", "in window", "out of window", "date unparseable"],
          [[rid, c[(rid, "in")], c[(rid, "out")], c[(rid, "unknown")]] for rid in WIN])
    for p in rn:
        if in_win(p) is None:
            print(f"- unparseable date: {p}: date field {EM[p].get('date')!r}; years in the body: "
                  f"{sorted(set(re.findall(r'20[12][0-9]', EM[p].get('body') or '')))}")
    print()

    print(f"## V5. Per-request AUROC gap (24-409 − 25-3152): own bootstrap, {a.boot} resamples, seed 99\n")
    print("Each request resampled independently, stratified by label. 95% interval and a Bonferroni interval for 7 "
          "simultaneous tests (99.29%).\n")
    rng = random.Random(99)
    ids = {rid: sorted(p for p in P if P[p]["request_id"] == rid) for rid in WIN}
    draws = {}
    for rid in WIN:
        pos = [p for p in ids[rid] if P[p]["label"]]; neg = [p for p in ids[rid] if not P[p]["label"]]
        draws[rid] = [(rng.choices(pos, k=len(pos)), rng.choices(neg, k=len(neg))) for _ in range(a.boot)]
    boot_au = {}
    out = []
    for name, _ in RUNS:
        pt = {}
        for rid in WIN:
            rows = [r for r in R[name].values() if r["rid"] == rid]
            pt[rid] = metrics(rows)["auroc"]
            S = R[name]
            boot_au[(name, rid)] = [fast_auroc([S[p]["score"] for p in bp], [S[p]["score"] for p in bn])
                                    for bp, bn in draws[rid]]
        d = [x - y for x, y in zip(boot_au[(name, "24-409")], boot_au[(name, "25-3152")])]
        alpha = 0.05 / 7
        out.append([name, f"{pt['24-409']:.3f}", f"{pt['25-3152']:.3f}", f"{pt['24-409'] - pt['25-3152']:+.3f}",
                    f"[{pctl(d, .025):+.3f}, {pctl(d, .975):+.3f}]",
                    f"[{pctl(d, alpha / 2):+.3f}, {pctl(d, 1 - alpha / 2):+.3f}]",
                    "yes" if pctl(d, alpha / 2) > 0 or pctl(d, 1 - alpha / 2) < 0 else "no"])
    table(["run", "24-409", "25-3152", "Δ", "95% CI", "Bonferroni 99.29% CI", "excludes 0 after Bonferroni"], out)

    print("## V6. Kendall tau between the two requests' AUROC rankings vs a resampling-noise baseline\n")
    names = [n for n, _ in RUNS]
    full = {rid: [metrics([r for r in R[n].values() if r["rid"] == rid])["auroc"] for n in names] for rid in WIN}
    tau_obs = kendall(full["24-409"], full["25-3152"])
    tb = [kendall([boot_au[(n, "24-409")][i] for n in names], [boot_au[(n, "25-3152")][i] for n in names])
          for i in range(a.boot)]
    self_ = {rid: [kendall(full[rid], [boot_au[(n, rid)][i] for n in names]) for i in range(a.boot)] for rid in WIN}
    table(["quantity", "value"], [
        ["tau, 24-409 vs 25-3152 rankings (point estimates)", f"{tau_obs:+.2f}"],
        ["  95% bootstrap interval (each request resampled)", f"[{pctl(tb, .025):+.2f}, {pctl(tb, .975):+.2f}]"],
        ["noise baseline: tau of 24-409's ranking with its own resamples, median [2.5%–97.5%]",
         f"{pctl(self_['24-409'], .5):+.2f} [{pctl(self_['24-409'], .025):+.2f}, {pctl(self_['24-409'], .975):+.2f}]"],
        ["noise baseline: tau of 25-3152's ranking with its own resamples, median [2.5%–97.5%]",
         f"{pctl(self_['25-3152'], .5):+.2f} [{pctl(self_['25-3152'], .025):+.2f}, {pctl(self_['25-3152'], .975):+.2f}]"],
        ["share of 24-409 self-resamples with tau <= the observed between-request tau",
         f"{sum(x <= tau_obs + 1e-12 for x in self_['24-409']) / a.boot:.1%}"],
    ] + [[f"noise baseline: tau between two independent resamples of {rid}, median [2.5%–97.5%]; share <= observed",
          (lambda xs: f"{pctl(xs, .5):+.2f} [{pctl(xs, .025):+.2f}, {pctl(xs, .975):+.2f}]; "
                      f"{sum(x <= tau_obs + 1e-12 for x in xs) / len(xs):.1%}")(
              [kendall([boot_au[(n, rid)][i] for n in names], [boot_au[(n, rid)][i + a.boot // 2] for n in names])
               for i in range(a.boot // 2)])] for rid in WIN])
    print("24-409 AUROC by model: " + ", ".join(f"{n} {v:.4f}" for n, v in zip(names, full["24-409"])) + "\n")

    print("## V6b. Is the request gap larger for stock Qwen than for d3 of the same size? (difference of gaps)\n")
    print("gap = AUROC(24-409) − AUROC(25-3152); the same resamples for both models (V5 draws), so the difference "
          "of gaps is paired within each request. 95% interval.\n")
    out = []
    for s_, d_ in (("4b lp", "d3-4b"), ("9b lp", "d3-9b"), ("27b lp", "d3-27b"), ("27b lp", "Jev"), ("d3-27b", "Jev")):
        gs = [x - y for x, y in zip(boot_au[(s_, "24-409")], boot_au[(s_, "25-3152")])]
        gd = [x - y for x, y in zip(boot_au[(d_, "24-409")], boot_au[(d_, "25-3152")])]
        dd = [x - y for x, y in zip(gs, gd)]
        pt = lambda n: full["24-409"][names.index(n)] - full["25-3152"][names.index(n)]
        out.append([f"{s_} − {d_}", f"{pt(s_) - pt(d_):+.3f}", f"[{pctl(dd, .025):+.3f}, {pctl(dd, .975):+.3f}]",
                    "yes" if pctl(dd, .025) > 0 or pctl(dd, .975) < 0 else "no"])
    table(["gap difference", "point", "95% CI", "excludes 0"], out)

    print(f"## V7. Roster: coverage and paired ΔAUROC on 25-3152 (own bootstrap, {a.boot} resamples, seed 7)\n")
    ids25 = set(ids["25-3152"])
    rng = random.Random(7)
    pos = sorted(p for p in ids25 if P[p]["label"]); neg = sorted(p for p in ids25 if not P[p]["label"])
    dr = [(rng.choices(pos, k=len(pos)), rng.choices(neg, k=len(neg))) for _ in range(a.boot)]
    out = []
    for name, tag in RUNS:
        Rr = load(tag + "_roster")[0]; B = R[name]
        shared = sorted(set(Rr) & set(B))
        base = metrics([B[p] for p in shared]); ros = metrics([Rr[p] for p in shared])
        d = [fast_auroc([Rr[p]["score"] for p in bp], [Rr[p]["score"] for p in bn])
             - fast_auroc([B[p]["score"] for p in bp], [B[p]["score"] for p in bn]) for bp, bn in dr]
        al = 0.05 / 7
        out.append([name, len(Rr), set(Rr) <= ids25, len(shared), f"{base['auroc']:.3f} → {ros['auroc']:.3f}",
                    f"{ros['auroc'] - base['auroc']:+.3f} [{pctl(d, .025):+.3f}, {pctl(d, .975):+.3f}]",
                    f"[{pctl(d, al / 2):+.3f}, {pctl(d, 1 - al / 2):+.3f}]",
                    f"{base['k']}/{base['n']} → {ros['k']}/{ros['n']}"])
    table(["run", "roster rows", "all roster pairs are 25-3152", "shared pairs", "AUROC without → with",
           "ΔAUROC [95% CI]", "Bonferroni 99.29% CI", "elim@98 without → with"], out)

    print("## V8. Jev's 2-decimal scores: distinct values and ties\n")
    pos, neg = split(R["Jev"].values())
    gt = sum(1 for x in pos for y in neg if x > y); eq = sum(1 for x in pos for y in neg if x == y)
    tot = len(pos) * len(neg)
    decs = max(len(repr(s).split(".")[1]) if "." in repr(s) else 0 for s in pos + neg)
    table(["quantity", "value"], [
        ["distinct values", len(set(pos + neg))], ["most decimals", decs],
        ["tied positive-negative pairs", f"{eq}/{tot}"],
        ["AUROC ties half / worst / best", f"{(gt + eq / 2) / tot:.4f} / {gt / tot:.4f} / {(gt + eq) / tot:.4f}"]])

    print("## V9. 25-3152 real-only (a): is the small models' elim@98 drop driven by positives or negatives?\n")
    print("thr98 is set by real positives alone; 'cleared at the 24-409 cutoff' applies the 24-409 (a) cutoff to "
          "25-3152 real negatives (in-sample, diagnostic only).\n")
    out = []
    for name, _ in RUNS:
        row = [name]
        th = {}
        for rid in WIN:
            rows = [r for r in R[name].values() if r["rid"] == rid and r["kind"] in ("real_positive", "real_negative")]
            pp, nn = split(rows)
            k, n, t, _ = my_elim(pp, nn)
            th[rid] = t
            row += [f"{t:.4g}", f"{sorted(nn)[len(nn) // 2]:.3f}", f"{k}/{n}"]
        nn25 = split([r for r in R[name].values() if r["rid"] == "25-3152" and r["kind"] == "real_negative"])[1]
        row.append(f"{sum(y < th['24-409'] for y in nn25)}/{len(nn25)}")
        out.append(row)
    table(["run", "24-409 thr98", "24-409 median real−", "24-409 cleared", "25-3152 thr98", "25-3152 median real−",
           "25-3152 cleared", "25-3152 real− cleared at the 24-409 cutoff"], out)

    print("## V10. Subset (f): elim@98 when 2, 3 (the rule) or 4 of the 150 real positives may be missed\n")
    out = []
    for name, _ in RUNS:
        rows = [r for p, r in R[name].items() if r["kind"] == "real_positive" or p in f_date]
        pp, nn = split(rows)
        sp = sorted(pp, reverse=True)
        row = [name]
        for miss in (2, 3, 4):
            t = sp[len(sp) - miss - 1]
            k = sum(y < t for y in nn)
            row.append(f"{k}/{len(nn)} ({k / len(nn):.0%})")
        out.append(row)
    table(["run", "2 misses (98.7% recall)", "3 misses (98.0%)", "4 misses (97.3%)"], out)

    print("## V11. Keyword-proxy circularity on 25-3152: group-name patterns alone vs with the roster\n")
    grp = [re.compile(r"alpine community planning group", re.I), re.compile(r"\bACPG\b"),
           re.compile(r"alpine\s+(cpg|planning group)", re.I), re.compile(r"alpinecpg", re.I)]
    roster = json.load(open("data/golden/work/acpg_roster.json"))["members"]
    addrs = [x.lower() for m in roster for x in m.get("email_addresses", [])]

    def fields(e):
        return "\n".join([e.get(k) or "" for k in ("subject", "body", "from", "to", "cc", "bcc", "delivered_to")]
                         + [" ".join(e.get("attachments") or [])])
    rp = [p for p in P if P[p]["request_id"] == "25-3152" and P[p]["kind"] == "real_positive"]
    g = sum(any(x.search(fields(EM[p])) for x in grp) for p in rp)
    ad = sum(any(x in fields(EM[p]).lower() for x in addrs) for p in rp)
    either = sum(any(x.search(fields(EM[p])) for x in grp) or any(x in fields(EM[p]).lower() for x in addrs) for p in rp)
    srcs = json.load(open("data/golden/work/acpg_roster.json"))["sources"]
    table(["quantity", "value"], [
        ["25-3152 real positives", len(rp)], ["hit by group-name patterns alone", g],
        ["hit by a roster email address", ad], ["either", either],
        ["roster sources that cite the 25-3152 production", sum("25-3152" in s for s in srcs)]])

    print("## V12. A stricter search-like subset: real+ vs hard negatives in window AND hitting my own keyword proxy\n")
    t24 = [re.compile(x, re.I) for x in (r"\bhinds\b", r"\blerner\b", r"urban studies", r"global policy",
                                         r"\buc san diego\b", r"water equity", r"decarboni[sz]ation framework",
                                         r"geosyntec", r"murakawa")] + \
          [re.compile(x) for x in (r"\bUSP\b", r"\bGPS\b", r"\bUCSD\b", r"\bRWER\b", r"\bRDF\b")]
    names25 = []
    for m in roster:
        tok = m["name"].replace(" Jr.", "").replace(",", "").split()
        names25 += [re.compile(re.escape(m["name"]), re.I),
                    re.compile(rf"\b{re.escape(tok[0])}\s+{re.escape(tok[-1])}\b", re.I),
                    re.compile(rf"\b{re.escape(tok[-1])},\s*{re.escape(tok[0])}\b", re.I)]

    def kw(pid):
        t = fields(EM[pid])
        if P[pid]["request_id"] == "24-409":
            return any(x.search(t) for x in t24)
        return any(x.search(t) for x in grp + names25) or any(x in t.lower() for x in addrs)
    srch = {p for p in f_date if kw(p)}
    rp_all = [p for p in P if P[p]["kind"] == "real_positive"]
    print(f"Hard negatives in window and hitting the proxy: {len(srch)}/{len(hn)}; real positives hitting the proxy: "
          f"{sum(kw(p) for p in rp_all)}/{len(rp_all)}\n")
    out = []
    for name, _ in RUNS:
        rows = [r for p, r in R[name].items() if r["kind"] == "real_positive" or p in srch]
        m = metrics(rows)
        out.append([name, f"{m['auroc']:.3f}", f"{m['k']}/{m['n']} ({m['k'] / m['n']:.0%})"])
    table(["run", "AUROC", "elim@98"], out)

    print("## V13. run.json settings behind the L-3 (prompt 1 vs 2) and L-4 (second run) comparisons\n")
    out = []
    for t in ("golden_qwen3.5_4b_logprob_p1o40", "golden_qwen3.5_4b_logprob_p2", "golden_qwen3.5_4b_logprob_p2db",
              "golden_qwen3.5_4b_logprob_p2dbf", "golden_qwen3.5_9b_logprob_p1o40", "golden_qwen3.5_9b_logprob_p2",
              "golden_qwen3.5_9b_logprob_p2db", "golden_qwen3.5_9b_logprob_p2dbf", "golden_qwen3.8_27b_logprob_p1o40",
              "golden_qwen3.8_27b_logprob_p2", "golden_d3-ctx8k_4b_noul_p2", "golden_d3-ctx8k_4b_noul_p2_fresh60",
              "golden_d3-ctx8k_27b_noul_p2_roster", "golden_d3-ctx8k_27b_noul_p2_roster_fresh30"):
        c = json.load(open(f"runs/{t}/run.json"))
        out.append([t] + [c.get(k) for k in ("prompt", "render", "ollama_version", "num_batch", "fresh")])
    table(["run", "prompt", "render", "Ollama", "num_batch", "fresh"], out)

    print("## V14. Three spot-read notes checked against the data\n")
    S = {s["id"]: s for s in jl("data/golden/work/synthetic.jsonl")}
    allm = {}
    with open("data/emails/sandiego.emails.jsonl") as f:
        for line in f:
            e = json.loads(line)
            allm[e["id"]] = e
    e = EM["25-3152|synth:25-3152:19:09"]; src = allm[S["synth:25-3152:19:09"]["source_id"]]
    print(f"- synth:25-3152:19:09 body identical to its source ({src['id']}, production {src['request_id']}): "
          f"{(e['body'] or '') == (src['body'] or '')}")
    e = EM["25-3152|synth:25-3152:14:02"]; src = allm[S["synth:25-3152:14:02"]["source_id"]]
    sm = difflib.SequenceMatcher(None, src["body"] or "", e["body"] or "", autojunk=False)
    first_change = min((j1 for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"), default=None)
    print(f"- synth:25-3152:14:02 body length {len(e['body'] or '')}; first character that differs from the source "
          f"at offset {first_change} (cap 8000): edit past the cap = {first_change is not None and first_change >= 8000}")
    s = S["synth:24-409:03:01"]
    print(f"- synth:24-409:03:01 verifier label_correct = {s['verify_label_correct']}; golden label = "
          f"{P['24-409|synth:24-409:03:01']['label']}; 'geosyntec' in from/to/cc = "
          f"{'geosyntec' in ' '.join(str(EM['24-409|synth:24-409:03:01'].get(k) or '') for k in ('from', 'to', 'cc')).lower()}")
    print()


if __name__ == "__main__":
    main()
