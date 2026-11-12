"""Branch C: missed responsive emails (C1), consensus false positives (C2), what misses track (C4),
plus the JSON verdict modes as a contrast on the same pairs.

  uv run python scripts/analysis/c_misses.py

Prints markdown tables:
  C1a per-model misses; C1b overlap at thr98; C1c overlap at 0.5; C1d consensus counts and
  sensitivity; C1e roster runs (25-3152).
  C2a consensus false positives (main set); C2b by kind and recipe; C2c roster runs.
  C2d: share of each request's negatives with a named correspondent, and how often the models keep them.
  C4a-b miss rates by request, prompt length, truncation, attachments, hook location and kind
  (at 0.5 and at thr98); C4c Fisher tests for the consensus misses.
  CJ  JSON verdicts on the consensus items (contrast only).
Definitions: thr98 = each run's pooled in-sample 98%-recall threshold (golden_report.thr98 on that run's
own rows: every main-set pair for the main runs, the 25-3152 pairs for the roster runs). A positive is "missed" when its score is
below the threshold; a negative is "kept" when its score is at or above it. Consensus miss: missed by >= 3
of the 7 score models. Consensus false positive: kept by >= 5 of the 7. Deterministic (no sampling).
"""
import collections
import re

from c_misses_common import (FP_K, MISS_K, NAMES, consensus, emails, fisher_two_sided, hook_24409, hook_25_3152,
                             load, member_patterns, n_recipients, pairs, per_model, rate, short, table, who)
from analyze import at_recall, pr_curve


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def main():
    main_runs, roster_runs, js, js_roster, dropped = load()
    P, E = pairs(), emails()
    pm, pr = per_model(main_runs), per_model(roster_runs)
    S = {m: {x["pair_id"]: x for x in rows} for m, rows in main_runs.items()}
    SR = {m: {x["pair_id"]: x for x in rows} for m, rows in roster_runs.items()}
    pos_ids = sorted(p for p in S[NAMES[0]] if S[NAMES[0]][p]["label"])
    neg_ids = sorted(p for p in S[NAMES[0]] if not S[NAMES[0]][p]["label"])
    kind = lambda p: P[p]["kind"] + (f"/{P[p]['recipe']}" if P[p]["kind"].startswith("hard_negative") else "")

    print("# Branch C tables\n")
    print(f"Main set: {len(pos_ids)} positives, {len(neg_ids)} negatives (labels from data/golden/pairs.jsonl). "
          f"Roster runs: {sum(1 for x in roster_runs[NAMES[0]] if x['label'])} positives, "
          f"{sum(1 for x in roster_runs[NAMES[0]] if not x['label'])} negatives (25-3152 only).\n")

    # ---------------- C1 ----------------
    print(f"## C1a. Per model: positives below its own thr98 and below 0.5 (main set, {N_ALL} pairs)\n")
    out = []
    for m in NAMES:
        t = pm[m]["thr98"]
        rec = sum(S[m][p]["score"] >= t for p in pos_ids)
        out.append([m, f"{t:.4f}", f"{rec}/{len(pos_ids)}", len(pm[m]["miss98"]),
                    ", ".join(short(p) for p in sorted(pm[m]["miss98"], key=lambda p: (S[m][p]["score"], p))),
                    len(pm[m]["miss50"])])
    table(["model", "thr98", "recall at thr98", "missed at thr98", "which (lowest score first)", "missed at 0.5"], out)

    def overlap(per, runs, key):
        ids = set().union(*(per[m][key] for m in NAMES))
        rows = []
        for p in sorted(ids, key=lambda p: (-len(who(per, key, p)), p)):
            cells = []
            for m in NAMES:
                s = runs[m][p]["score"]
                cells.append(f"**{s:.2f}**" if p in per[m][key] else f"{s:.2f}")
            rows.append([short(p), kind(p), len(who(per, key, p))] + cells)
        return rows

    print("## C1b. Overlap at thr98: every positive missed by at least one model\n")
    print("Cell = that model's score; **bold** = below that model's thr98 (missed). Sorted by how many models miss it.\n")
    table(["pair", "kind", "models missing"] + NAMES, overlap(pm, S, "miss98"))

    print("## C1c. Overlap at the default decision (score < 0.5): every positive missed by at least one model\n")
    print("Cell = score; **bold** = below 0.5.\n")
    table(["pair", "kind", "models missing"] + NAMES, overlap(pm, S, "miss50"))

    print("## C1d. Consensus misses (missed by >= 3 of 7 models)\n")
    dist = lambda per, key: collections.Counter(len(who(per, key, p)) for p in pos_ids)
    thr95 = {m: at_recall(pr_curve([x["score"] for x in main_runs[m]], [x["label"] for x in main_runs[m]]), 0.95)[0] for m in NAMES}
    miss95 = {m: {p for p in pos_ids if S[m][p]["score"] < thr95[m]} for m in NAMES}
    per95 = {m: {"miss95": miss95[m]} for m in NAMES}
    out = []
    for lbl, per, key in (("thr98", pm, "miss98"), ("0.5", pm, "miss50"), ("thr95 (sensitivity)", per95, "miss95")):
        d = dist(per, key)
        c = consensus(per, key, MISS_K)
        out.append([lbl, sum(len(per[m][key]) for m in NAMES), sum(v for k, v in d.items() if k >= 1),
                    " / ".join(str(d.get(k, 0)) for k in range(1, 8)), len(c), ", ".join(short(p) for p in c)])
    table(["cutoff", "miss events (sum over 7 models)", "distinct positives missed",
           "missed by exactly 1 / 2 / 3 / 4 / 5 / 6 / 7 models", "consensus (>= 3)", "consensus pairs"], out)
    u = sorted(set(consensus(pm, "miss98", MISS_K)) | set(consensus(pm, "miss50", MISS_K)))
    print(f"Union of the thr98 and 0.5 consensus misses: {len(u)} pairs "
          f"({sum(p.startswith('24-409') for p in u)} from 24-409, {sum(p.startswith('25-3152') for p in u)} from 25-3152; "
          f"{sum(P[p]['kind'] == 'real_positive' for p in u)} real, {sum(P[p]['kind'] != 'real_positive' for p in u)} synthetic). "
          f"thr95 per model: {', '.join(f'{m} {thr95[m]:.3f}' for m in NAMES)}.\n")

    print("## C1e. Roster runs (25-3152 only, 249 pairs; each run's own thr98)\n")
    out = []
    for m in NAMES:
        out.append([m, f"{pr[m]['thr98']:.4f}", len(pr[m]["miss98"]),
                    ", ".join(short(p) for p in sorted(pr[m]["miss98"], key=lambda p: (SR[m][p]["score"], p))),
                    len(pr[m]["miss50"]), ", ".join(short(p) for p in sorted(pr[m]["miss50"], key=lambda p: (SR[m][p]["score"], p)))])
    table(["model +roster", "thr98", "missed at thr98", "which", "missed at 0.5", "which"], out)
    for lbl, key in (("thr98", "miss98"), ("0.5", "miss50")):
        c = consensus(pr, key, MISS_K)
        print(f"- Roster consensus misses at {lbl}: {len(c)}" + (f" ({', '.join(short(p) for p in c)})" if c else ""))
    main_cons = [p for p in u if p.startswith("25-3152")]
    print(f"- The {len(main_cons)} main-set 25-3152 consensus misses, with the roster: missed at thr98 by "
          + "; ".join(f"{short(p)} {len(who(pr, 'miss98', p))}" for p in main_cons)
          + "; at 0.5 by " + "; ".join(f"{short(p)} {len(who(pr, 'miss50', p))}" for p in main_cons) + " models.\n")

    # ---------------- C2 ----------------
    print("## C2a. Consensus false positives: negatives kept by >= 5 of 7 models (main set)\n")
    print("'kept' = score at or above the threshold, so the email survives the screen and goes to human review. "
          "Listed if kept by >= 5 models at thr98 or at 0.5.\n")
    f98, f50 = consensus(pm, "fp98", FP_K), consensus(pm, "fp50", FP_K)
    fu = sorted(set(f98) | set(f50), key=lambda p: (p.split("|")[0], P[p]["recipe"] or "", p))
    out = []
    for p in fu:
        e = E[P[p]["email_id"]]
        out.append([short(p), P[p]["kind"], P[p]["recipe"], len(who(pm, "fp98", p)), len(who(pm, "fp50", p)),
                    (e.get("date") or "")[:10], (e.get("subject") or "")[:60].replace("|", "/")])
    table(["pair", "kind", "recipe", "kept at thr98 (of 7)", "kept at 0.5 (of 7)", "date", "subject"], out)
    print(f"Consensus false positives: {len(f98)} at thr98, {len(f50)} at 0.5, {len(fu)} in the union "
          f"({len(set(f50) - set(f98))} at 0.5 only). Kept by all 7 at thr98: {sum(len(who(pm, 'fp98', p)) == 7 for p in neg_ids)}; "
          f"at 0.5: {sum(len(who(pm, 'fp50', p)) == 7 for p in neg_ids)}.\n")

    print("## C2b. Consensus false positives by kind and recipe\n")
    groups = collections.defaultdict(list)
    for p in neg_ids:
        groups[(p.split("|")[0], kind(p))].append(p)
    out = []
    for (rid, k), ps in sorted(groups.items()):
        mx98 = max(len(who(pm, "fp98", p)) for p in ps)
        out.append([rid, k, len(ps), rate(sum(p in f98 for p in ps), len(ps)), rate(sum(p in f50 for p in ps), len(ps)), mx98])
    for k in sorted({kind(p) for p in neg_ids}):
        ps = [p for p in neg_ids if kind(p) == k]
        out.append(["both", k, len(ps), rate(sum(p in f98 for p in ps), len(ps)), rate(sum(p in f50 for p in ps), len(ps)),
                    max(len(who(pm, "fp98", p)) for p in ps)])
    table(["request", "kind/recipe", "n", "consensus FP at thr98 (k/n, 95% CI)", "consensus FP at 0.5", "most models keeping any one (thr98)"], out)
    hn = [p for p in neg_ids if P[p]["kind"] == "hard_negative"]
    print(f"All hard negatives: consensus FP at thr98 {rate(sum(p in f98 for p in hn), len(hn))}; at 0.5 "
          f"{rate(sum(p in f50 for p in hn), len(hn))}. Every consensus FP is a synthetic hard negative: "
          f"{sum(P[p]['kind'] == 'hard_negative' for p in fu)}/{len(fu)}.\n")
    rn = [p for p in neg_ids if P[p]["kind"] == "real_negative"]
    print(f"Real negatives (other productions): kept-by-k distribution at thr98 (k = 0..7): "
          f"{dict(sorted(collections.Counter(len(who(pm, 'fp98', p)) for p in rn).items()))}; at 0.5: "
          f"{dict(sorted(collections.Counter(len(who(pm, 'fp50', p)) for p in rn).items()))}.\n")

    print("## C2c. Roster runs: consensus false positives (25-3152, 249 pairs)\n")
    g98, g50 = consensus(pr, "fp98", FP_K), consensus(pr, "fp50", FP_K)
    out = []
    for p in sorted(set(g98) | set(g50)):
        out.append([short(p), kind(p), len(who(pr, "fp98", p)), len(who(pr, "fp50", p)),
                    len(who(pm, "fp98", p)), len(who(pm, "fp50", p))])
    table(["pair", "kind/recipe", "kept at thr98 +roster", "kept at 0.5 +roster", "kept at thr98 (no roster)", "kept at 0.5 (no roster)"], out)
    m25 = [p for p in fu if p.startswith("25-3152")]
    print(f"Of the {len(m25)} main-set 25-3152 consensus false positives, {sum(p in g98 for p in m25)} remain consensus at thr98 "
          f"with the roster and {sum(p in g50 for p in m25)} at 0.5.\n")

    # named correspondents in 24-409 (C2 support; mechanical)
    print("## C2d. Negatives with a named correspondent in the headers\n")
    print("24-409 item 4 names people and firms (Elise Ruiz, Murakawa, Geosyntec staff, Gaines, Benham, Snyder, "
          "Aghassi, Brukman, Baxamusa) but also requires a reference to a listed term. 25-3152 names a group "
          "(any ACPG member). Prompt 2 tells every model that an email to or from a named person or group is "
          "responsive whatever its subject. Headers = From/To/Cc/Bcc/Delivered-To. 24-409 named = the people "
          "and firms above (not the catch-all 'anyone at the County'); 25-3152 named = a roster address or name.\n")
    named24 = [r"(?i:elise\.?\s*ruiz|ruiz;?\s*elise|ruiz, elise)", r"(?i:murakawa)", r"(?i:geosyntec)", r"(?i:susill?o)",
               r"(?i:otto)", r"(?i:zinn)", r"(?i:gaines)", r"(?i:benham)", r"(?i:snyder)", r"(?i:ag+h?assi)", r"(?i:brukman)",
               r"(?i:baxamusa)"]
    mp = member_patterns()
    head = lambda e: " ".join(str(e.get(k) or "") for k in ("from", "to", "cc", "bcc", "delivered_to"))
    def named(p):
        e = E[P[p]["email_id"]]
        pats = named24 if p.startswith("24-409") else mp
        return any(re.search(x, head(e)) for x in pats)
    out = []
    for rid in ("24-409", "25-3152"):
        for lab in ("hard_negative", "real_negative"):
            for nm in (True, False):
                ps = [p for p in neg_ids if p.startswith(rid) and P[p]["kind"] == lab and named(p) == nm]
                if not ps:
                    continue
                out.append([rid, lab, "yes" if nm else "no", len(ps), rate(sum(p in f98 for p in ps), len(ps)),
                            rate(sum(p in f50 for p in ps), len(ps)),
                            f"{sum(len(who(pm, 'fp50', p)) for p in ps) / len(ps):.1f}"])
    table(["request", "kind", "named correspondent in headers", "n", "consensus FP at thr98", "consensus FP at 0.5",
           "mean models keeping at 0.5 (of 7)"], out)

    print("## C2e. Wrong-date negatives: which side of the window, and how many models keep them\n")
    print("The 24-409 request text carries both the 5/17/24 refinement (1/1/2023-7/31/2023) and the original request "
          "(1/1/2022 to the 4/16/2024 letter). 'In original window' marks dates inside the original range; the "
          "original request's subjects (Hinds, the UCSD USP department, Fletcher) still differ from the RWER/RDF "
          "topics of these emails.\n")
    out = []
    wd = [p for p in neg_ids if P[p]["recipe"] == "same_subject_wrong_date"]
    for p in sorted(wd, key=lambda p: (p.split("|")[0], E[P[p]["email_id"]]["date"])):
        e = E[P[p]["email_id"]]; d = (e.get("date") or "")[:10]
        lo = "2023-01-01" if p.startswith("24-409") else "2024-01-01"
        orig = ("yes" if "2022-01-01" <= d <= "2024-04-16" else "no") if p.startswith("24-409") else "—"
        out.append([short(p), d, "before" if d < lo else "after", orig, len(who(pm, "fp98", p)), len(who(pm, "fp50", p))]
                   + [f"{S[m][p]['score']:.2f}" for m in NAMES])
    table(["pair", "date", "side", "in original 24-409 window", "kept at thr98", "kept at 0.5"] + NAMES, out)
    for rid, flag in (("24-409", "yes"), ("24-409", "no")):
        ps = [r for r in out if r[0].startswith(rid) and r[3] == flag]
        print(f"- {rid}, in original window = {flag}: {len(ps)} emails, mean models keeping at 0.5 "
              f"{sum(r[5] for r in ps) / len(ps):.1f} of 7.")
    ps = [r for r in out if r[0].startswith("25-3152")]
    print(f"- 25-3152: {len(ps)} emails, mean models keeping at 0.5 {sum(r[5] for r in ps) / len(ps):.1f} of 7.\n")
    grp = {"24-409, inside the original window": [p for p in wd if p.startswith("24-409") and "2022-01-01" <= E[P[p]["email_id"]]["date"][:10] <= "2024-04-16"],
           "24-409, outside both windows": [p for p in wd if p.startswith("24-409") and not "2022-01-01" <= E[P[p]["email_id"]]["date"][:10] <= "2024-04-16"],
           "25-3152": [p for p in wd if p.startswith("25-3152")]}
    table(["mean score"] + NAMES, [[f"{g} (n={len(ps)})"] + [f"{sum(S[m][p]['score'] for p in ps) / len(ps):.2f}" for m in NAMES]
                                   for g, ps in grp.items()])

    # ---------------- C4 ----------------
    print(f"## C4. What the misses track (main set, {N_POS} positives)\n")
    mpats = member_patterns()
    def hook(p):
        e = E[P[p]["email_id"]]
        return hook_24409(e) if p.startswith("24-409") else hook_25_3152(e, mpats)
    def tokbucket(t):
        return "<= 2,048" if t <= 2048 else "2,049-4,096" if t <= 4096 else "> 4,096"
    factors = [
        ("request", lambda m, p: p.split("|")[0]),
        ("prompt tokens (that model's count)", lambda m, p: tokbucket(S[m][p]["prompt_tokens"])),
        ("truncated (body > 8,000 chars)", lambda m, p: "yes" if S[m][p]["truncated"] else "no"),
        ("attachments listed", lambda m, p: "yes" if E[P[p]["email_id"]].get("attachments") else "no"),
        ("hook location (keyword heuristic)", lambda m, p: hook(p)),
        ("recipients (To+Cc+Bcc)", lambda m, p: "1-9" if n_recipients(E[P[p]["email_id"]]) < 10 else ">= 10"),
        ("kind", lambda m, p: P[p]["kind"]),
    ]
    cons50 = set(consensus(pm, "miss50", MISS_K)); cons98 = set(consensus(pm, "miss98", MISS_K))
    for lbl, key in (("C4a. At the default decision (score < 0.5)", "miss50"), ("C4b. At each model's thr98", "miss98")):
        print(f"### {lbl}\n")
        print("Cell = missed / positives in that group. The last column counts consensus misses (>= 3 models) at this "
              "cutoff; for the token rows it uses the 27b lp token count (the lp models share a tokenizer).\n")
        cons = cons50 if key == "miss50" else cons98
        out = []
        for fname, f in factors:
            levels = sorted({f("27b lp", p) for p in pos_ids} | {f(m, p) for m in NAMES for p in pos_ids})
            for lv in levels:
                cells = []
                for m in NAMES:
                    ps = [p for p in pos_ids if f(m, p) == lv]
                    cells.append(f"{sum(p in pm[m][key] for p in ps)}/{len(ps)}" if ps else "—")
                ps27 = [p for p in pos_ids if f("27b lp", p) == lv]
                out.append([fname, lv] + cells + [rate(sum(p in cons for p in ps27), len(ps27)) if ps27 else "—"])
        table(["factor", "level"] + NAMES + ["consensus misses (k/n, 95% CI)"], out)

    print("### C4c. Fisher exact tests: consensus misses at 0.5 (>= 3 models) against each two-level split\n")
    print("Two-sided p. Small counts: read these as a screen for large effects, not as proof of none.\n")
    out = []
    splits = [("25-3152 vs 24-409", lambda p: p.startswith("25-3152")),
              ("> 2,048 tokens (27b lp) vs <=", lambda p: S["27b lp"][p]["prompt_tokens"] > 2048),
              ("truncated vs not", lambda p: S["27b lp"][p]["truncated"]),
              ("attachments vs none", lambda p: bool(E[P[p]["email_id"]].get("attachments"))),
              (">= 10 recipients vs fewer", lambda p: n_recipients(E[P[p]["email_id"]]) >= 10),
              ("real_positive vs synthetic positive", lambda p: P[p]["kind"] == "real_positive")]
    p25 = [p for p in pos_ids if p.startswith("25-3152")]
    splits25 = [("25-3152 only: >= 10 recipients vs fewer", lambda p: n_recipients(E[P[p]["email_id"]]) >= 10),
                ("25-3152 only: ACPG not named in visible text vs named", lambda p: not hook(p).startswith("ACPG named"))]
    for nm, f, ids in [(a, b, pos_ids) for a, b in splits] + [(a, b, p25) for a, b in splits25]:
        a = sum(f(p) and p in cons50 for p in ids); b = sum(f(p) and p not in cons50 for p in ids)
        c = sum((not f(p)) and p in cons50 for p in ids); d = sum((not f(p)) and p not in cons50 for p in ids)
        out.append([nm, rate(a, a + b), rate(c, c + d), f"{fisher_two_sided(a, b, c, d):.3g}"])
    table(["split (first vs second)", "consensus misses, first group", "second group", "Fisher p"], out)
    print("Per model, misses at 0.5 by request (Fisher two-sided p for 25-3152 vs 24-409):\n")
    out = []
    for m in NAMES:
        a = sum(p.startswith("25-3152") and p in pm[m]["miss50"] for p in pos_ids); b = sum(p.startswith("25-3152") for p in pos_ids) - a
        c = sum(p.startswith("24-409") and p in pm[m]["miss50"] for p in pos_ids); d = sum(p.startswith("24-409") for p in pos_ids) - c
        out.append([m, rate(a, a + b), rate(c, c + d), f"{fisher_two_sided(a, b, c, d):.3g}"])
    table(["model", "25-3152 misses at 0.5", "24-409 misses at 0.5", "Fisher p"], out)
    # pooled miss events (all 7 models) at 0.5 for 25-3152 positives with >= 10 recipients
    ev = lambda ps, key: (sum(p in pm[m][key] for m in NAMES for p in ps), 7 * len(ps))
    g = [p for p in pos_ids if p.startswith("25-3152") and n_recipients(E[P[p]["email_id"]]) >= 10]
    h = [p for p in pos_ids if p.startswith("25-3152") and n_recipients(E[P[p]["email_id"]]) < 10]
    print(f"25-3152 positives only, miss events at 0.5 pooled over the 7 models: >= 10 recipients {rate(*ev(g, 'miss50'))}; "
          f"fewer {rate(*ev(h, 'miss50'))}. (Pooled events are not independent; the same pairs repeat across models.)\n")

    # ---------------- JSON contrast ----------------
    print("## CJ. JSON verdict modes on the consensus items (contrast only)\n")
    drop = {k: v for k, v in dropped.items() if v}
    print(f"Rows with a null score dropped: {sum(len(v) for v in drop.values())} "
          f"({'; '.join(f'{k}: {', '.join(short(p) for p in v)}' for k, v in drop.items())}).\n")
    J = {m: {x["pair_id"]: x for x in rows} for m, rows in js.items()}
    out = []
    for p in u:
        out.append([short(p), P[p]["kind"]] + [("yes" if J[m][p]["verdict"] else "no") if p in J[m] else "(dropped)" for m in J])
    print("Consensus misses: each JSON run's verdict (the label is responsive, so 'yes' is right).\n")
    table(["pair", "kind"] + list(J), out)
    out = []
    for m in J:
        ys = [p for p in fu if p in J[m]]
        n_yes = sum(bool(J[m][p]["verdict"]) for p in ys)
        allneg = [p for p in neg_ids if p in J[m]]
        out.append([m, rate(n_yes, len(ys)), rate(sum(bool(J[m][p]["verdict"]) for p in allneg), len(allneg))])
    print("Consensus false positives: share each JSON run calls responsive (the label is non-responsive, so 'yes' is wrong), "
          "next to its rate on all negatives.\n")
    table(["JSON run", "says yes on consensus FPs", "says yes on all negatives"], out)
    # how often the 27b reasoning-first answer says "yes" while conceding the subject is off-topic
    rule = re.compile(r"(?i)regardless of|whatever (?:its|the) subject|unless (?:it is )?purely personal|"
                      r"(?:although|while|even though|though)[^.]{0,160}(?:administrative|logistical|personal|"
                      r"does not (?:explicitly )?(?:mention|reference|name|contain)|not explicitly|subject matter)")
    named = re.compile(r"(?i)named (?:individual|person|people|entit|group|in the)|explicitly (?:named|listed)|a named |"
                       r"specifically (?:named|listed|targets communications)|person whose communications")
    out = []
    for rid in ("24-409", "25-3152"):
        for lab, grp in ((0, "negatives"), (1, "positives")):
            ids = [p for p in (neg_ids if lab == 0 else pos_ids) if p.startswith(rid) and p in J["27b jsonR"]]
            yes = [p for p in ids if J["27b jsonR"][p]["verdict"]]
            raw = lambda p: J["27b jsonR"][p].get("raw", "")
            out.append([rid, grp, f"{len(yes)}/{len(ids)}", rate(sum(bool(named.search(raw(p))) for p in yes), len(yes)),
                        rate(sum(bool(rule.search(raw(p))) for p in yes), len(yes)),
                        ", ".join(short(p) for p in yes if rule.search(raw(p))) if lab == 0 else ""])
    print("27b jsonR 'yes' answers: how often the reasoning (saved first 600 characters) justifies the yes by a named "
          "person, and how often it concedes the subject is off-topic or personal but says yes anyway ('although the "
          "subject matter ... does not explicitly mention', 'regardless of', 'unless purely personal'). Regex counts; "
          "this is the reasoning-first JSON mode of the 27b, not the lp score, so it is suggestive only.\n")
    table(["request", "label", "27b jsonR says yes", "yes justified by a named person", "yes while conceding off-topic",
           "which negatives"], out)


if __name__ == "__main__":
    main()
