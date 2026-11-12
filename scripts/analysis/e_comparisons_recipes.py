"""E2. Hard-negative recipes at each model's own pooled thr98, with exact paired tests.

  uv run python scripts/analysis/e_comparisons_recipes.py [--boot 5000]

Main set (all pairs), seven score models. A hard negative "passes through" when score >= cutoff.
  Table E2a  pass-through by recipe at each model's own pooled thr98 (k/n)
  Table E2b  same_subject_wrong_date: exact McNemar for all 21 model pairs, Holm within 21
  Table E2c  d3-27b vs Jev, d3-27b vs 27b lp, 27b lp vs Jev on every recipe: exact McNemar, Holm within 15
  Table E2d  within-model: wrong-date pass-through vs the other four recipes (Fisher exact, unpaired)
  Table E2e  cutoff sensitivity for wrong-date: recall 95/98/99/100% cutoffs and the fixed 0.5 cutoff
  Table E2f  McNemar d3-27b vs Jev and 27b lp vs Jev at the fixed 0.5 cutoff, every recipe
  Table E2g  threshold-free: AUROC of all positives vs each recipe's negatives (DeLong for the key pairs)
  Table E2h  bootstrap of the wrong-date pass-through gap with thr98 re-estimated in every resample
  Table E2i  how far each model's cutoff must move to match d3-27b's wrong-date pass-through
  Table E2j  matched source: hard negatives whose source (a real positive) is in the set: copy vs source
  Table E2k  wrong-date score distribution per model vs its thr98 and its median positive score
Stdlib only; bootstrap seed 303.
"""
import argparse
import itertools
import random
import statistics

from e_comparisons_common import (RECIPE_SHORT, RECIPES, SCORE, at_recall, auroc, binom_two_sided, boot_p, ci,
                                  delong, delong_p, fisher_two_sided, fp, holm, kn, mcnemar_exact, pr_curve,
                                  resample, rows, strata, table, thr98)
import json

WD = "same_subject_wrong_date"
KEY = [("d3-27b", "Jev"), ("d3-27b", "27b lp"), ("27b lp", "Jev")]


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=5000)
    a = ap.parse_args()
    names = [n for n, _ in SCORE]
    data = {n: rows(t) for n, t in SCORE}
    ids = sorted(set.intersection(*(set(d) for d in data.values())))
    ref = data[names[0]]
    lab = {p: ref[p]["label"] for p in ids}
    L = [lab[p] for p in ids]
    thr = {n: thr98([data[n][p]["score"] for p in ids], L) for n in names}
    groups = {r: [p for p in ids if ref[p]["kind"] == "hard_negative" and ref[p]["recipe"] == r] for r in RECIPES}
    groups["all hard negatives"] = [p for p in ids if ref[p]["kind"] == "hard_negative"]
    groups["real_negative (reference)"] = [p for p in ids if ref[p]["kind"] == "real_negative"]
    passes = lambda n, ps, t=None: [data[n][p]["score"] >= (thr[n] if t is None else t) for p in ps]

    print("## E2. Hard-negative recipes\n")
    print("Table E2a. Share of each recipe's hard negatives that pass the screen (score >= the model's own thr98, "
          f"set on all {N_ALL} pairs). Lower is better.\n")
    body = [["thr98", "—"] + [f"{thr[n]:.4f}" for n in names]]
    for g, ps in groups.items():
        body.append([RECIPE_SHORT.get(g, g), len(ps)] + [kn(sum(passes(n, ps)), len(ps)) for n in names])
    table(["recipe", "n"] + names, body)

    print("Table E2b. Same subject, wrong date (n = 20): exact McNemar test for every pair of models at their own "
          "thr98. b = A passes and B rejects; c = A rejects and B passes. Sorted by p; Holm within these 21.\n")
    res = []
    for x, y in itertools.combinations(names, 2):
        fx, fy = passes(x, groups[WD]), passes(y, groups[WD])
        A, B = (x, y) if sum(fx) >= sum(fy) else (y, x)
        fa, fb = (fx, fy) if A == x else (fy, fx)
        b, c, p = mcnemar_exact(fa, fb)
        res.append([A, B, sum(fa), sum(fb), b, c, p])
    for r, h in zip(res, holm([r[6] for r in res])):
        r.append(h)
    table(["A (passes more)", "B", "A passes", "B passes", "b", "c", "exact p", "Holm p", "survives Holm"],
          [[r[0], r[1], f"{r[2]}/20", f"{r[3]}/20", r[4], r[5], fp(r[6]), fp(r[7]), "**yes**" if r[7] < 0.05 else "no"]
           for r in sorted(res, key=lambda r: (r[6], -(r[2] - r[3])))])

    print("Table E2c. Three headline pairs on every recipe, at each model's own thr98. Exact McNemar; Holm across the "
          "15 recipe-level tests (the 'all hard negatives' row is a separate, single test).\n")
    body, ps = [], []
    for x, y in KEY:
        for g in RECIPES + ["all hard negatives"]:
            fx, fy = passes(x, groups[g]), passes(y, groups[g])
            b, c, p = mcnemar_exact(fx, fy)
            body.append([f"{x} vs {y}", RECIPE_SHORT.get(g, g), len(groups[g]), sum(fx), sum(fy), b, c, p])
            if g != "all hard negatives":
                ps.append(len(body) - 1)
    adj = holm([body[i][7] for i in ps])
    hol = {i: h for i, h in zip(ps, adj)}
    table(["pair (x vs y)", "recipe", "n", "x passes", "y passes", "x only", "y only", "exact p", "Holm p (15)"],
          [r[:7] + [fp(r[7]), fp(hol[i]) if i in hol else "—"] for i, r in enumerate(body)])

    print("Table E2d. Within each model: does it pass wrong-date emails more or less often than the other four "
          "recipes' emails? Different emails, so Fisher's exact test (unpaired).\n")
    other = [p for p in groups["all hard negatives"] if ref[p]["recipe"] != WD]
    body = []
    for n in names:
        k1, k2 = sum(passes(n, groups[WD])), sum(passes(n, other))
        body.append([n, kn(k1, 20), kn(k2, len(other)), f"{(k1 / 20 - k2 / len(other)) * 100:+.0f}",
                     fisher_two_sided(k1, 20 - k1, k2, len(other) - k2)])
    adj = holm([r[4] for r in body])
    table(["model", "wrong date passes", "other 4 recipes pass", "difference (points)", "Fisher p", "Holm p (7)"],
          [r[:4] + [fp(r[4]), fp(h)] for r, h in zip(body, adj)])

    print("Table E2e. Cutoff sensitivity: wrong-date emails passing (of 20) at each model's own cutoffs for 95%, "
          f"98%, 99% and 100% recall (all {N_ALL} pairs), and at the fixed cutoff 0.5 (with its recall).\n")
    body = []
    for n in names:
        S = [data[n][p]["score"] for p in ids]
        cur = pr_curve(S, L)
        row = [n]
        for tgt in (0.95, 0.98, 0.99, 1.0):
            t = at_recall(cur, tgt)[0]
            row.append(f"{sum(passes(n, groups[WD], t))} (thr {t:.3f})")
        rec5 = sum(1 for p in ids if lab[p] and data[n][p]["score"] >= 0.5)
        row += [sum(passes(n, groups[WD], 0.5)), f"{rec5}/{sum(L)} ({rec5 / sum(L):.1%})"]
        body.append(row)
    table(["model", "@95% recall", "@98% recall", "@99% recall", "@100% recall", "@0.5", "recall @0.5"], body)

    print("Table E2f. At the fixed 0.5 cutoff for both models: exact McNemar on every recipe.\n")
    body = []
    for x, y in KEY:
        for g in RECIPES + ["all hard negatives"]:
            fx, fy = passes(x, groups[g], 0.5), passes(y, groups[g], 0.5)
            b, c, p = mcnemar_exact(fx, fy)
            body.append([f"{x} vs {y}", RECIPE_SHORT.get(g, g), len(groups[g]), sum(fx), sum(fy), b, c, fp(p)])
    table(["pair (x vs y)", "recipe", "n", "x passes", "y passes", "x only", "y only", "exact p"], body)

    print(f"Table E2g. Threshold-free: AUROC of all {N_POS} positives against one recipe's negatives (the chance that a "
          "random responsive email scores above a random email of that recipe). Higher is better. DeLong p for the "
          "key pairs on the wrong-date recipe below the table.\n")
    pos = [p for p in ids if lab[p]]
    body = []
    for g in RECIPES + ["all hard negatives"]:
        sub = pos + groups[g]; sl = [lab[p] for p in sub]
        body.append([RECIPE_SHORT.get(g, g), len(groups[g])] +
                    [f"{auroc([data[n][p]['score'] for p in sub], sl):.3f}" for n in names])
    table(["recipe", "n neg"] + names, body)
    sub = pos + groups[WD]; sl = [lab[p] for p in sub]
    aucs, C = delong([[data[n][p]["score"] for p in sub] for n in names], sl)
    body = []
    for x, y in KEY:
        i, j = names.index(x), names.index(y)
        body.append([f"{x} − {y}", f"{aucs[i] - aucs[j]:+.3f}", fp(delong_p(aucs, C, i, j))])
    table(["wrong date: A − B", "ΔAUROC", "DeLong p"], body)

    print(f"Table E2h. Wrong-date pass-through gap with the threshold re-estimated in every resample "
          f"(stratified paired bootstrap of all {N_ALL} pairs, {a.boot} resamples, seed 303). Each resample sets each "
          f"model's thr98 afresh and counts the resampled wrong-date emails above it.\n")
    pos_ids, neg_ids = strata(ids, lab)
    rng = random.Random(303)
    gaps = {k: [] for k in KEY}; share = {n: [] for n in ("d3-27b", "27b lp", "Jev")}
    wd = set(groups[WD])
    for _ in range(a.boot):
        bs = resample(pos_ids, neg_ids, rng)
        bl = [lab[p] for p in bs]
        w = [p for p in bs if p in wd]
        sh = {}
        for n in share:
            t = thr98([data[n][p]["score"] for p in bs], bl)
            sh[n] = sum(data[n][p]["score"] >= t for p in w) / len(w)
            share[n].append(sh[n])
        for x, y in KEY:
            gaps[(x, y)].append(sh[y] - sh[x])
    body = [[n, f"{statistics.median(share[n]):.0%}", f"[{ci(share[n])[0]:.0%}, {ci(share[n])[1]:.0%}]"] for n in share]
    table(["model", "median wrong-date pass-through", "95% interval"], body)
    table(["gap (y − x)", "point", "95% CI (points)", "bootstrap p"],
          [[f"{y} − {x}", f"{(sum(passes(y, groups[WD])) - sum(passes(x, groups[WD]))) / 20 * 100:+.0f}",
            f"[{ci(gaps[(x, y)])[0] * 100:+.0f}, {ci(gaps[(x, y)])[1] * 100:+.0f}]", fp(boot_p(gaps[(x, y)]))]
           for x, y in KEY])

    print("Table E2i. How far would each model's cutoff have to rise to pass no more than 3 of the 20 wrong-date "
          f"emails (d3-27b's count at its thr98)? Recall and elimination of all {N_NEG} negatives at that cutoff.\n")
    body = []
    for n in names:
        w = sorted((data[n][p]["score"] for p in groups[WD]), reverse=True)
        t = min(s for s in set(data[n][p]["score"] for p in ids) | {1.0} if s > w[3])
        rec = sum(1 for p in ids if lab[p] and data[n][p]["score"] >= t)
        el = sum(1 for p in ids if not lab[p] and data[n][p]["score"] < t)
        body.append([n, f"{thr[n]:.3f}", f"{t:.3f}", sum(passes(n, groups[WD], t)), f"{rec}/{sum(L)} ({rec / sum(L):.1%})",
                     f"{el}/{len(L) - sum(L)} ({el / (len(L) - sum(L)):.1%})"])
    table(["model", "own thr98", "cutoff needed", "wrong date passes", "recall at that cutoff", "eliminated at that cutoff"], body)

    print("Table E2j. Matched source. Hard negatives whose source email (a real positive) is also in the set: how often "
          "the model scores the altered copy below its source, the median drop (source − copy), and an exact sign test "
          "(two-sided) that drops and rises are equally likely. 'copy passes' = copy at or above the model's thr98.\n")
    emails = {e["id"]: e for e in map(json.loads, open("data/golden/emails.jsonl"))}
    by_email = {ref[p]["email_id"]: p for p in ids}
    body = []
    for g in RECIPES:
        prs = [(p, by_email[emails[ref[p]["email_id"]]["source_id"]]) for p in groups[g]
               if emails[ref[p]["email_id"]].get("source_id") in by_email]
        assert all(lab[s] == 1 for _, s in prs)
        for n in names:
            d = [data[n][s]["score"] - data[n][c]["score"] for c, s in prs]
            k = sum(x > 0 for x in d); ties = sum(x == 0 for x in d)
            body.append([RECIPE_SHORT[g], n, len(prs), f"{k}/{len(prs)}" + (f" ({ties} tied)" if ties else ""),
                         f"{statistics.median(d):+.2f}", fp(binom_two_sided(k, len(prs) - ties)),
                         f"{sum(data[n][c]['score'] >= thr[n] for c, _ in prs)}/{len(prs)}"])
    table(["recipe", "model", "pairs", "copy below source", "median drop", "sign-test p", "copy passes"], body)

    print("Table E2k. Wrong-date scores by model (all 20): median and range, against the model's thr98 and its median positive "
          "score.\n")
    body = []
    for n in names:
        w = [data[n][p]["score"] for p in groups[WD]]
        body.append([n, f"{statistics.median(w):.3f}", f"{min(w):.3f}–{max(w):.3f}", f"{thr[n]:.3f}",
                     f"{statistics.median(data[n][p]['score'] for p in pos):.3f}",
                     " / ".join(str(sum(passes(n, [p for p in groups[WD] if ref[p]['request_id'] == r]))) + "/10"
                                for r in ("24-409", "25-3152"))])
    table(["model", "median wrong-date score", "range", "thr98", "median positive score", "passes 24-409 / 25-3152"], body)


if __name__ == "__main__":
    main()
