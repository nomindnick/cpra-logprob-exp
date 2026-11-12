"""Branch B2-B5: review workload per 10,000 keyword-search hits, under explicit scenarios.

  uv run python scripts/analysis/b_workload_review.py [--boot 1000]

A scenario is a hypothetical population of 10,000 keyword hits: a responsive share p, negatives that pass
the screen at the rate of the golden real negatives, the golden hard negatives, or a 50/50 mix of the two,
and positives that pass at the rate of all golden positives (sensitivity: real positives only). The pass
rates come from the saved runs at two cutoffs: each run's own in-sample 98%-recall threshold (thr98, chosen
on the same pairs) and the default decision (score >= 0.5; JSON: the verdict).

  flagged = 10,000 x [p x R + (1 - p) x F]      missed = 10,000 x p x (1 - R)

Prints:
  B2.1  pass rates by group (k/n, bootstrap 95% CI) at thr98 and at the default decision
  B2.2  the same rates with Wilson 95% intervals (threshold held fixed; these don't collapse at 0/n)
  B2.3  per-10,000 flagged / missed / review avoided, positives = all golden positives, at thr98
  B2.4  the same at the default decision
  B2.5  sensitivity: positives behave like the real positives only
  B3.1  reviewer hours vs machine hours, plausible scenario, both cutoffs
  B3.2  break-even review seconds per email (machine time = reviewer time), every scenario, thr98
  B4.1  25-3152 pass rates with and without the roster (same 249 pairs; thresholds chosen on those pairs)
  B4.2  25-3152 per-10,000 numbers with and without the roster, plausible scenario
  B4.3  25-3152 with the roster: flagged per 10,000 under every scenario, thr98
  B5.1  speed classes (machine hours per 10,000) and the best score model in each, main set
  B5.2  paired differences in flagged / missed per 10,000 between the class winners and like-sized models
  B5.3  takeaway table, main set
  B5.4-B5.6  the same three for 25-3152 with the roster

Bootstrap: resample pairs with replacement within each kind (so within each label), the same resampled
pair lists for every configuration (paired); at thr98 the threshold is re-chosen in every resample, as in
golden_report's elim@98 intervals. Seed SEED. Stdlib only.
"""
import argparse

from b_workload_common import (CONFIGS, N_HITS, NEG_MODELS, P_SHARES, PLAUSIBLE, SCORE_NAMES, SEED, ci,
                               kind_counts, load, mean, n0, pct, rates, resamples, scenario, table, wilson)

CUTOFFS = [("thr98", "in-sample 98%-recall threshold"), ("default", "default decision (score ≥ 0.5 / JSON verdict)")]
GROUPS = [("all_pos", "positives: all"), ("real_positive", "positives: real"),
          ("real_negative", "negatives: real"), ("hard_negative", "negatives: hard")]
RATE_OF = {"all_pos": "R_all", "real_positive": "R_real", "real_negative": "F_real", "hard_negative": "F_hard"}
NAMES = [c[0] for c in CONFIGS]
SPEED_CLASSES = [(0, 1, "under 1 h"), (1, 5, "1–5 h"), (5, 10, "5–10 h"), (10, 1e9, "over 10 h")]


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def evaluate(runs, names, n_boot, seed):
    """Point estimates and bootstrap replicates of the rates for each (config, cutoff)."""
    res = {}
    for name in names:
        for cut, _ in CUTOFFS:
            counts, t = kind_counts(runs[name], cut)
            res[(name, cut)] = {"counts": counts, "thr": t, "rates": rates(counts), "boot": []}
    universe = max((runs[n] for n in names), key=len)  # a complete run: every pair once
    idx = {name: {r["pair_id"]: r for r in runs[name]} for name in names}
    for ids in resamples(universe, n_boot, seed):
        for name in names:
            rows = [idx[name][p] for p in ids if p in idx[name]]
            for cut, _ in CUTOFFS:
                counts, _ = kind_counts(rows, cut)
                res[(name, cut)]["boot"].append(rates(counts))
    return res


def sc(rt, p, neg, pos):
    return scenario(rt, p, neg, pos)


def sc_ci(e, field, p, neg, pos):
    return ci([sc(b, p, neg, pos)[field] for b in e["boot"]])


def fmt_n(x, lohi):
    return f"{n0(x)} [{n0(lohi[0])}–{n0(lohi[1])}]"


def fmt_p(x, lohi):
    return f"{pct(x)} [{pct(lohi[0])}–{pct(lohi[1])}]"


def rate_table(res, names, cut, header_extra=""):
    out = []
    for name in names:
        e = res[(name, cut)]
        row = [name, f"{e['thr']:.4f}" if e["thr"] is not None else "0.5 / verdict"]
        for g, _ in GROUPS:
            k, n = e["counts"][g]
            lo, hi = ci([b[RATE_OF[g]] for b in e["boot"]])
            row.append(f"{k}/{n} = {pct(k / n, 1)} [{pct(lo, 1)}–{pct(hi, 1)}]")
        k, n = e["counts"]["all_neg"]
        lo, hi = ci([1 - b["F_all"] for b in e["boot"]])
        row.append(f"{n - k}/{n} = {pct((n - k) / n, 1)} [{pct(lo, 1)}–{pct(hi, 1)}]")
        out.append(row)
    table(["config", "threshold" + header_extra] + [g[1] for g in GROUPS] + ["eliminated: all negatives"], out)


def wilson_table(res, names):
    out = []
    for name in names:
        row = [name]
        for cut, _ in CUTOFFS:
            for g, _ in GROUPS:
                k, n = res[(name, cut)]["counts"][g]
                lo, hi = wilson(k, n)
                row.append(f"{pct(lo, 1)}–{pct(hi, 1)}")
        out.append(row)
    table(["config"] + [f"{c}: {g[1]}" for c, _ in CUTOFFS for g in GROUPS], out)


def grid(res, names, cut, pos):
    for p in P_SHARES:
        print(f"#### responsive share p = {pct(p)} ({n0(N_HITS * p)} responsive, {n0(N_HITS * (1 - p))} not)\n")
        out = []
        for name in names:
            e = res[(name, cut)]; rt = e["rates"]
            row = [name]
            for lab, neg in NEG_MODELS:
                f = sc(rt, p, neg, pos)["flagged"]
                row.append(fmt_n(f, sc_ci(e, "flagged", p, neg, pos)) if lab == "mix" else n0(f))
            m = sc(rt, p, "F_mix", pos)
            row += [fmt_n(m["missed"], sc_ci(e, "missed", p, "F_mix", pos)),
                    fmt_p(m["avoided"], sc_ci(e, "avoided", p, "F_mix", pos)), pct(m["queue_resp"])]
            out.append(row)
        table(["config", "flagged: neg like real", "flagged: neg 50/50 mix [95% CI]", "flagged: neg like hard",
               "missed [95% CI]", "review avoided (mix) [95% CI]", "responsive share of queue (mix)"], out)


def machine_hours(runs, name):
    return mean(r["wall_ms"] for r in runs[name]) * N_HITS / 3_600_000


def speed_class(h):
    return next(lab for lo, hi, lab in SPEED_CLASSES if lo <= h < hi)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=1000)
    a = ap.parse_args()
    main_runs, roster_runs, dropped = load()
    P, NEG, POS = PLAUSIBLE["p"], PLAUSIBLE["neg"], PLAUSIBLE["pos"]
    print("# Branch B2–B5: review workload per 10,000 keyword-search hits\n")
    print(f"Bootstrap: {a.boot} resamples, seed {SEED}. Dropped rows without a score: "
          + ", ".join(f"{t} {k}/{n}" for t, k, n in dropped) + ".\n")
    print(f"Plausible scenario used in B3 and B5: p = {pct(P)}, negatives = 50/50 mix of real-like and hard-like, "
          "positives = all golden positives.\n")

    res = evaluate(main_runs, NAMES, a.boot, SEED)

    # ---- B2.1 / B2.2 ----
    for cut, label in CUTOFFS:
        print(f"## B2.1 Pass rates at the {label}, main set ({N_ALL} pairs)\n")
        print("Share of each group flagged for review. For positives this is recall; for negatives it is the "
              "share that slips through. [bootstrap 95% CI" + (", threshold re-chosen in each resample]" if cut == "thr98" else "]") + "\n")
        rate_table(res, NAMES, cut)
    print("## B2.2 Wilson 95% intervals for the same rates (threshold held at its point value)\n")
    wilson_table(res, NAMES)

    # ---- B2.3 / B2.4 ----
    for cut, label in CUTOFFS:
        print(f"## B2.{3 if cut == 'thr98' else 4} Per 10,000 hits at the {label}; positives like all golden positives\n")
        grid(res, NAMES, cut, "R_all")

    # ---- B2.5 sensitivity: real positives only ----
    print("## B2.5 Sensitivity: positives behave like the real positives only (150 pairs)\n")
    out = []
    for name in NAMES:
        row = [name]
        for cut, _ in CUTOFFS:
            e = res[(name, cut)]
            for p in P_SHARES:
                row.append(fmt_n(sc(e["rates"], p, NEG, "R_real")["missed"], sc_ci(e, "missed", p, NEG, "R_real")))
            row.append(fmt_n(sc(e["rates"], P, NEG, "R_real")["flagged"], sc_ci(e, "flagged", P, NEG, "R_real")))
        out.append(row)
    header = ["config"]
    for cut, _ in CUTOFFS:
        header += [f"{cut}: missed, p={pct(p)}" for p in P_SHARES] + [f"{cut}: flagged, p={pct(P)}, mix"]
    table(header, out)

    # ---- B3.1 reviewer vs machine, plausible scenario ----
    print(f"## B3.1 Reviewer time vs machine time, plausible scenario (p = {pct(P)}, negatives 50/50 mix, "
          "positives all)\n")
    print(f"Reading all {n0(N_HITS)} hits: {N_HITS * 30 / 3600:.1f} h at 30 s per email, {N_HITS * 60 / 3600:.1f} h "
          "at 60 s. Machine hours are single-stream (B1.1). Bottleneck = the larger of machine hours and reviewer "
          "hours, if scoring and review overlap.\n")
    for cut, label in CUTOFFS:
        print(f"### at the {label}\n")
        out = []
        for name in NAMES:
            e = res[(name, cut)]
            mh = machine_hours(main_runs, name)
            s = sc(e["rates"], P, NEG, POS); lo, hi = sc_ci(e, "flagged", P, NEG, POS)
            row = [name, f"{mh:.1f}", fmt_n(s["flagged"], (lo, hi)), n0(s["missed"])]
            for sec in (30, 60):
                rh = s["flagged"] * sec / 3600
                row += [f"{rh:.1f} [{lo * sec / 3600:.1f}–{hi * sec / 3600:.1f}]",
                        f"{N_HITS * sec / 3600 - rh:.1f}", "machine" if mh > rh else "reviewer"]
            row.append(f"{mh * 3600 / s['flagged']:.0f}")
            out.append(row)
        table(["config", "machine h", "flagged", "missed", "reviewer h @30 s [CI]", "saved h @30 s",
               "bottleneck @30 s", "reviewer h @60 s [CI]", "saved h @60 s", "bottleneck @60 s",
               "break-even s/email"], out)
    print("Break-even s/email = machine seconds ÷ flagged emails: if a reviewer spends longer than this per "
          "flagged email, review takes longer than scoring.\n")

    # ---- B3.2 break-even across scenarios ----
    print("## B3.2 Break-even review seconds per flagged email, every scenario, at thr98 (positives all)\n")
    out = []
    for name in NAMES:
        e = res[(name, "thr98")]; mh = machine_hours(main_runs, name)
        out.append([name, f"{mh:.1f}"] + [f"{mh * 3600 / sc(e['rates'], p, neg, POS)['flagged']:.0f}"
                                         for p in P_SHARES for _, neg in NEG_MODELS])
    table(["config", "machine h"] + [f"p={pct(p)}, neg {lab}" for p in P_SHARES for lab, _ in NEG_MODELS], out)

    # ---- B4 roster ----
    sub = {n: [r for r in main_runs[n] if r["request_id"] == "25-3152"] for n in NAMES}
    res_wo = evaluate(sub, NAMES, a.boot, SEED + 1)
    res_ro = evaluate(roster_runs, NAMES, a.boot, SEED + 1)  # same seed and universe -> same resamples (paired)
    print("## B4.1 25-3152 only (249 pairs): pass rates without and with the roster\n")
    print(f"Thresholds are chosen in-sample on these {NR['25-3152']} pairs ({NP['25-3152']} positives: 98% recall allows 2 misses). "
          f"Without = the main runs restricted to 25-3152; with = the _roster runs. {NFLIP['25-3152']} hard_negative_flipped "
          "pairs in this request.\n")
    for cut, label in CUTOFFS:
        print(f"### at the {label}\n")
        out = []
        for name in NAMES:
            for tag, rr in (("without", res_wo), ("with", res_ro)):
                e = rr[(name, cut)]
                row = [name, tag, f"{e['thr']:.4f}" if e["thr"] is not None else "0.5 / verdict"]
                for g, _ in GROUPS:
                    k, n = e["counts"][g]
                    lo, hi = ci([b[RATE_OF[g]] for b in e["boot"]])
                    row.append(f"{k}/{n} = {pct(k / n, 1)} [{pct(lo, 1)}–{pct(hi, 1)}]")
                out.append(row)
        table(["config", "roster", "threshold"] + [g[1] for g in GROUPS], out)

    print(f"## B4.2 25-3152 per 10,000 hits, plausible scenario (p = {pct(P)}, mix, positives all)\n")
    print("Machine hours from the same 249 pairs. Δ = with − without roster, paired bootstrap.\n")
    for cut, label in CUTOFFS:
        print(f"### at the {label}\n")
        out = []
        for name in NAMES:
            ew, er = res_wo[(name, cut)], res_ro[(name, cut)]
            sw, sr = sc(ew["rates"], P, NEG, POS), sc(er["rates"], P, NEG, POS)
            d = [sc(b2, P, NEG, POS)["flagged"] - sc(b1, P, NEG, POS)["flagged"] for b1, b2 in zip(ew["boot"], er["boot"])]
            out.append([name, f"{machine_hours(sub, name):.1f} → {machine_hours(roster_runs, name):.1f}",
                        f"{fmt_n(sw['flagged'], sc_ci(ew, 'flagged', P, NEG, POS))} → {fmt_n(sr['flagged'], sc_ci(er, 'flagged', P, NEG, POS))}",
                        f"{sr['flagged'] - sw['flagged']:+,.0f} [{ci(d)[0]:+,.0f}, {ci(d)[1]:+,.0f}]",
                        f"{fmt_n(sw['missed'], sc_ci(ew, 'missed', P, NEG, POS))} → {fmt_n(sr['missed'], sc_ci(er, 'missed', P, NEG, POS))}",
                        f"{pct(sw['avoided'])} → {pct(sr['avoided'])}"])
        table(["config", "machine h without → with", "flagged without → with [CI]", "Δ flagged [paired CI]",
               "missed without → with [CI]", "review avoided"], out)

    print("## B4.3 25-3152 with the roster: flagged per 10,000 under every scenario, thr98 (positives all)\n")
    out = []
    for name in NAMES:
        e = res_ro[(name, "thr98")]
        out.append([name] + [n0(sc(e["rates"], p, neg, POS)["flagged"]) for p in P_SHARES for _, neg in NEG_MODELS]
                   + [n0(sc(e["rates"], p, NEG, POS)["missed"]) for p in P_SHARES])
    table(["config"] + [f"p={pct(p)}, neg {lab}" for p in P_SHARES for lab, _ in NEG_MODELS]
          + [f"missed, p={pct(p)}" for p in P_SHARES], out)

    # ---- B5 takeaway ----
    def takeaway(runs, rr, title):
        hours = {n: machine_hours(runs, n) for n in NAMES}
        flag = {n: sc(rr[(n, "thr98")]["rates"], P, NEG, POS)["flagged"] for n in NAMES}
        miss = {n: sc(rr[(n, "thr98")]["rates"], P, NEG, POS)["missed"] for n in NAMES}
        print(f"## {title}\n")
        print("Speed class by single-stream machine hours per 10,000. Best = fewest flagged at thr98 in the "
              "plausible scenario, among the seven score models. JSON modes are listed for contrast but not "
              "eligible: each is slower than the same model's lp, and its thr98 sits on a few coarse confidence "
              "values, so its recall there overshoots 98% by keeping almost everything. 'Dominated' = some other "
              "configuration is at least as fast, flags no more and misses no more (point estimates).\n")
        out, best = [], {}
        for n in sorted(NAMES, key=lambda n: hours[n]):
            cls = speed_class(hours[n])
            dom = [m for m in NAMES if m != n and hours[m] <= hours[n] and flag[m] <= flag[n] and miss[m] <= miss[n]
                   and (hours[m] < hours[n] or flag[m] < flag[n] or miss[m] < miss[n])]
            if n in SCORE_NAMES and (cls not in best or flag[n] < flag[best[cls]]):
                best[cls] = n
            out.append([n, f"{hours[n]:.2f}", cls, n0(flag[n]), n0(miss[n]), ", ".join(dom) or "—"])
        for row in out:
            row.append("yes" if best.get(row[2]) == row[0] else "")
        table(["config", "machine h", "speed class", "flagged (thr98)", "missed (thr98)", "dominated by",
               "best in class"], out)
        return hours, best

    def paired(runs, rr, comps, title):
        print(f"## {title}\n")
        print("Plausible scenario, per 10,000 hits. Δ = second − first; paired bootstrap over the same resampled "
              "pairs (threshold re-chosen in each resample at thr98). Δ reviewer hours = Δ flagged × 30 s or 60 s.\n")
        out = []
        for x, y in comps:
            for cut in ("thr98", "default"):
                ex, ey = rr[(x, cut)], rr[(y, cut)]
                fx, fy = sc(ex["rates"], P, NEG, POS), sc(ey["rates"], P, NEG, POS)
                df = [sc(by, P, NEG, POS)["flagged"] - sc(bx, P, NEG, POS)["flagged"] for bx, by in zip(ex["boot"], ey["boot"])]
                dm = [sc(by, P, NEG, POS)["missed"] - sc(bx, P, NEG, POS)["missed"] for bx, by in zip(ex["boot"], ey["boot"])]
                d = fy["flagged"] - fx["flagged"]
                out.append([f"{x} → {y}", cut, f"{n0(fx['flagged'])} → {n0(fy['flagged'])}",
                            f"{d:+,.0f} [{ci(df)[0]:+,.0f}, {ci(df)[1]:+,.0f}]",
                            f"{fy['missed'] - fx['missed']:+,.0f} [{ci(dm)[0]:+,.0f}, {ci(dm)[1]:+,.0f}]",
                            f"{d * 30 / 3600:+.1f} / {d * 60 / 3600:+.1f}",
                            f"{machine_hours(runs, x):.1f} → {machine_hours(runs, y):.1f}"])
        table(["first → second", "cutoff", "flagged", "Δ flagged [paired CI]", "Δ missed [paired CI]",
               "Δ reviewer h @30/60 s", "machine h"], out)

    def comparisons(best):
        winners = [best[c] for _, _, c in SPEED_CLASSES if c in best]
        comps = [(a_, b_) for i, a_ in enumerate(winners) for b_ in winners[i + 1:]]
        for c in [("4b lp", "d3-4b"), ("9b lp", "d3-9b"), ("27b lp", "d3-27b"), ("4b lp", "9b lp"),
                  ("27b lp", "27b json"), ("27b lp", "27b jsonR")]:
            if c not in comps and c[::-1] not in comps:
                comps.append(c)
        return comps

    def takeaway_rows(rr, hours, best, title):
        print(f"## {title}\n")
        print(f"Plausible scenario: p = {pct(P)}, negatives 50/50 mix, positives all golden positives; per 10,000 hits. "
              "thr98 is in-sample (branch A's out-of-sample cutoffs may do worse). Range = min–max flagged at thr98 over "
              "the 9 scenarios p ∈ {5, 20, 50}% × negatives ∈ {real, mix, hard}.\n")
        out = []
        for _, _, cls in SPEED_CLASSES:
            if cls not in best:
                continue
            n = best[cls]
            e, d = rr[(n, "thr98")], rr[(n, "default")]
            s, s5 = sc(e["rates"], P, NEG, POS), sc(d["rates"], P, NEG, POS)
            rng_f = [sc(e["rates"], p, neg, POS)["flagged"] for p in P_SHARES for _, neg in NEG_MODELS]
            out.append([cls, n, f"{hours[n]:.1f}", fmt_n(s["flagged"], sc_ci(e, "flagged", P, NEG, POS)),
                        fmt_n(s["missed"], sc_ci(e, "missed", P, NEG, POS)),
                        f"{s['flagged'] * 30 / 3600:.0f} / {s['flagged'] * 60 / 3600:.0f}",
                        f"{n0(min(rng_f))}–{n0(max(rng_f))}",
                        fmt_n(s5["flagged"], sc_ci(d, "flagged", P, NEG, POS)),
                        fmt_n(s5["missed"], sc_ci(d, "missed", P, NEG, POS)),
                        f"{s5['flagged'] * 30 / 3600:.0f} / {s5['flagged'] * 60 / 3600:.0f}"])
        table(["speed class", "config", "machine h", "thr98: flagged [CI]", "thr98: missed [CI]",
               "thr98: reviewer h @30/60 s", "thr98: flagged range, 9 scenarios", "0.5: flagged [CI]",
               "0.5: missed [CI]", "0.5: reviewer h @30/60 s"], out)

    hours, best = takeaway(main_runs, res, f"B5.1 Speed classes, main set ({N_ALL} pairs)")
    paired(main_runs, res, comparisons(best), "B5.2 Paired differences, main set")
    takeaway_rows(res, hours, best, "B5.3 Takeaway, main set (both requests)")

    hours_r, best_r = takeaway(roster_runs, res_ro, "B5.4 Speed classes, 25-3152 with the roster (249 pairs)")
    paired(roster_runs, res_ro, comparisons(best_r), "B5.5 Paired differences, 25-3152 with the roster")
    takeaway_rows(res_ro, hours_r, best_r, "B5.6 Takeaway, 25-3152 with the roster")

if __name__ == "__main__":
    main()
