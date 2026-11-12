# A. Setting the cutoff without the target request's labels

> **Snapshot of 2026-11-06, on the 2026-10-31 labels (495 pairs).** The labels changed afterwards: five hard
> negatives were relabeled responsive on 2026-11-08, and one email (24-409 synthetic 07:09) was put back in the set
> on 2026-11-11 (`docs/findings-golden.md` §9). The tables below are copies of script output on the old labels.
> Rerun the commands in the Reproduce section for current numbers; the scripts now read the pair counts from the
> golden set (`scripts/analysis/golden_counts.py`). `docs/findings-golden.md` carries the current figures, and
> `conclusions.md` section 0 lists what the relabeling changed.

Branch A of the golden-set analysis (2026-11-06). Scripts: `scripts/analysis/a_cutoffs_*.py`, stdlib
only, deterministic. Every number in this file is printed by one of them; the tables are pasted from
their output (see [Reproduce](#reproduce)). Nothing was rescored: all numbers come from saved runs.

## The question

The headline metric in `docs/findings-golden.md` is "non-responsive emails eliminated at 98% recall"
(elim@98). To compute it, each model's cutoff is chosen on the same 495 emails it is then measured on,
with their labels known. An agency screening a new request can't do that. It learns which emails are
responsive only by reviewing them, which is the work the screen is supposed to save.

This branch asks how well cutoffs hold up when they're set **without the target request's labels**. It
tests the three ways an agency could set one:

1. **Transfer** (A2): reuse the cutoff that worked on a previous request that has already been reviewed.
2. **Fixed** (A3): use one number for every request, such as the default 0.5.
3. **Sample** (A4): review a small random sample of the new request's emails, then set the cutoff from
   what the sample shows.

A1 measures how far apart the two requests' own best cutoffs are. A5 sums up how much the in-sample
headline overstates what these policies deliver.

## Short answer

- **Even the headline's cutoff misses on one request.** The pooled cutoff gets 98% recall over both
  requests together, but on one of the two requests every model misses 3 to 5 responsive emails. That
  is below 98% for that request. Some of this is arithmetic: 5 pooled misses can't split as 2 + 2. But
  the misses also bunch up. For 4 of the 7 models, all 5 fall on one request (A1c).
- **Each request needs its own cutoff, and reusing one can go badly.** A reused cutoff keeps 98% recall
  only if the new request's own 98% cutoff is at least as high as the reused one. Otherwise it fails,
  and by a lot. Without
  the roster, the worst case misses 31 of 140 responsive emails (d3-27b, 24-409 → 25-3152). With the
  roster run as the source, the worst case misses 82 of 144 (d3-9b). Taking the previous request's
  100%-recall cutoff as a margin rescues one more direction for only 2 of 7 models (A2).
- **The default 0.5 works only for d3-27b.** Its misses are 0/144 and 1/140, and it eliminates 72% and
  85% of the negatives. Every other model misses at least 5 on one request at 0.5. So do the JSON
  verdicts (A3).
- **A small labeled sample can't certify 98% recall.** One rule sets the cutoff at the lowest-scoring
  responsive email in the sample. With 50 emails reviewed, that rule reaches 98% recall on the rest in
  about half the repetitions at the golden set's prevalence (144 of 246 and 140 of 249 responsive). At a
  more realistic 20% it does so in about one in five. The rate is nearly the same for every model. One
  margin divides the model's odds by 10. With it, 6 of the 7 models reach 98% in at least 90% of
  repetitions at 20% prevalence. For some models, though, it eliminates almost nothing (A4).
- **The headline overstates what a label-free policy delivers.** [disputed in verification: the rule is fitted on these two requests' labels, so the gap below is not an out-of-sample estimate; see concern 6] Take a fixed per-model cutoff with one
  grid step of headroom, fitted on all the labeled pairs. It eliminates 7 to 56 points less than the
  headline (A5e). Even the best safe policy, picked with hindsight from a menu of 17, falls between 1
  point above and 14 points below the headline (A5b).

## Data and method

### Runs

The seven score models, each with its `_roster` twin (the 249 pairs of 25-3152, with the
planning-group roster appended to the request text). Rows come from `golden_report.load_runs()`, which
takes label, kind and recipe from `data/golden/pairs.jsonl` joined on `pair_id`. It drops rows not in
the golden set and rows without a score.

| label | main run (495 pairs) | roster twin (249 pairs) | score |
|---|---|---|---|
| 4b lp | `runs/golden_qwen3.5_4b_logprob_p2db` | `…_p2db_roster` | first-token P(yes)/(P(yes)+P(no)) |
| 9b lp | `runs/golden_qwen3.5_9b_logprob_p2db` | `…_p2db_roster` | same |
| 27b lp | `runs/golden_qwen3.8_27b_logprob_p2` | `…_p2_roster` | same |
| d3-4b | `runs/golden_d3-ctx8k_4b_noul_p2` | `…_p2_roster` | the d3 decision model's P(yes) |
| d3-9b | `runs/golden_d3-ctx8k_9b_noul_p2` | `…_p2_roster` | same |
| d3-27b | `runs/golden_d3-ctx8k_27b_noul_p2` | `…_p2_roster` | same |
| Jev | `runs/golden_jev-1.14.0_noul_p2` | `…_p2_roster` | Jev's P(yes), rounded to 2 decimals (so ties are common) |

JSON verdict runs appear only as a contrast at their default verdict (A3c):
`runs/golden_qwen3.5_{4b,9b}_json_p2`, `runs/golden_qwen3.8_27b_json_p2` ("json") and the same with
`_json_reason_p2` ("jsonR"), plus their roster twins. Rows with a null score are dropped. A3c prints the
count.

### Subsets

Unscored rows dropped from the 14 score-model runs: none

- 24-409: 246 pairs, 144 positives / 102 negatives; 98% recall allows 2 misses, 99% allows 1
- 25-3152: 249 pairs, 140 positives / 109 negatives; 98% recall allows 2 misses, 99% allows 1
- 25-3152+R: 249 pairs, 140 positives / 109 negatives; 98% recall allows 2 misses, 99% allows 1
- pooled: 495 pairs, 284 positives / 211 negatives; 98% recall allows 5 misses, 99% allows 2
- pooled+R: 495 pairs, 284 positives / 211 negatives; 98% recall allows 5 misses, 99% allows 2

"Pooled" is the headline's 495 pairs. "25-3152+R" means the roster runs. 24-409 is topical and has no
roster variant. "Pooled+R" is 24-409 plus 25-3152+R, the setting in which the roster is used for the
correspondent-scoped request (as `findings-golden.md` §12, item 4, recommends; §6 has the ablation
behind it) [corrected in verification: the original cited §6 as the recommendation].

### Terms

- **Label**: the human-adjudicated answer for a pair. 1 = responsive (a *positive*); 0 = not responsive
  (a *negative*).
- **Cutoff** (threshold): a pair is *flagged* for human review when its score is ≥ the cutoff. Otherwise
  it is *eliminated*.
- **Recall**: flagged positives ÷ all positives. **Misses**: positives not flagged, always given as a
  count. **Eliminated share**: negatives scoring below the cutoff ÷ all negatives.
- **thr98**: the highest cutoff that keeps recall ≥ 98% on a given set of pairs (`golden_report.thr98`).
  On 140 or 144 positives that allows 2 misses; on the 284 pooled positives it allows 5. "99%" and
  "100%" cutoffs are defined the same way (1 and 0 misses per request).
- **Oracle** or **in-sample** cutoff: thr98 computed on the same pairs it is scored on, as the headline
  does. **Out-of-sample**: the cutoff is set without the scored pairs' labels.
- **Odds** = p/(1 − p). **Log-odds** = ln(odds). These measure the distance between two cutoffs on a
  scale that doesn't compress near 0 and 1. For example, dividing the odds by 10 moves a cutoff of 0.5
  to 0.091, but a cutoff of 0.05 to 0.005 (A4a).
- **Bootstrap interval** (A1a): resample each request's pairs with replacement, within each label class,
  1,000 times with a fixed seed. Recompute thr98 each time and report the 2.5th–97.5th percentile range.
  This shows how much the cutoff would move with a different draw of similar emails from the same
  request.

## A1. Per-request oracle cutoffs

### A1a. thr98 on each request, the roster run, and pooled

| model | 24-409 | 25-3152 | 25-3152+R | pooled | pooled+R |
|---|---|---|---|---|---|
| 4b lp | 0.3002 [0.2373–0.4804] | 0.2210 [0.1387–0.5287] | 0.5606 [0.3626–0.6700] | 0.2650 [0.2210–0.4230] | 0.4230 [0.3002–0.5606] |
| 9b lp | 0.2463 [0.1783–0.4010] | 0.4196 [0.3578–0.5211] | 0.3901 [0.2743–0.5796] | 0.3309 [0.2463–0.4135] | 0.3212 [0.2463–0.4010] |
| 27b lp | 0.3623 [0.2529–0.7792] | 0.0566 [0.0079–0.1030] | 0.0783 [0.0730–0.2164] | 0.0687 [0.0566–0.2529] | 0.1728 [0.0783–0.2619] |
| d3-4b | 0.3323 [0.1076–0.4609] | 0.3507 [0.1904–0.4539] | 0.7588 [0.7520–0.8032] | 0.3507 [0.2608–0.4258] | 0.4299 [0.3323–0.5374] |
| d3-9b | 0.3051 [0.2598–0.4096] | 0.5427 [0.3177–0.6257] | 0.8529 [0.8311–0.8785] | 0.3379 [0.3051–0.4725] | 0.3548 [0.3051–0.5017] |
| d3-27b | 0.8542 [0.7504–0.9201] | 0.5405 [0.4870–0.6115] | 0.9133 [0.8794–0.9220] | 0.5857 [0.5405–0.6656] | 0.8819 [0.8542–0.9213] |
| Jev | 0.5700 [0.4200–0.6300] | 0.3100 [0.2200–0.3500] | 0.4600 [0.3900–0.5200] | 0.3400 [0.3100–0.3900] | 0.4900 [0.4500–0.5700] |

### A1b. How far apart the two requests' cutoffs are

ratio = higher cutoff / lower cutoff. log-odds gap = |logit(c1) − logit(c2)|. 'Between' = emails of each request whose score lies between the two cutoffs (lower ≤ score < higher): the emails whose treatment depends on which request's cutoff is used (+ = positives, − = negatives).

| model | pair of requests | thr98 24-409 | thr98 other | higher | ratio | log-odds gap | between, 24-409 (of 144+ / 102−) | between, other (of 140+ / 109−) |
|---|---|---|---|---|---|---|---|---|
| 4b lp | 24-409 vs 25-3152 | 0.3002 | 0.2210 | 24-409 | 1.36 | 0.41 | +2 / −10 | +3 / −18 |
| 4b lp | 24-409 vs 25-3152+R | 0.3002 | 0.5606 | 25-3152+R | 1.87 | 1.09 | +7 / −16 | +2 / −28 |
| 9b lp | 24-409 vs 25-3152 | 0.2463 | 0.4196 | 25-3152 | 1.70 | 0.79 | +8 / −7 | +2 / −14 |
| 9b lp | 24-409 vs 25-3152+R | 0.2463 | 0.3901 | 25-3152+R | 1.58 | 0.67 | +4 / −6 | +2 / −10 |
| 27b lp | 24-409 vs 25-3152 | 0.3623 | 0.0566 | 24-409 | 6.40 | 2.25 | +2 / −14 | +12 / −13 |
| 27b lp | 24-409 vs 25-3152+R | 0.3623 | 0.0783 | 24-409 | 4.63 | 1.90 | +2 / −11 | +13 / −4 |
| d3-4b | 24-409 vs 25-3152 | 0.3323 | 0.3507 | 25-3152 | 1.06 | 0.08 | +1 / −0 | +0 / −1 |
| d3-4b | 24-409 vs 25-3152+R | 0.3323 | 0.7588 | 25-3152+R | 2.28 | 1.84 | +74 / −30 | +2 / −24 |
| d3-9b | 24-409 vs 25-3152 | 0.3051 | 0.5427 | 25-3152 | 1.78 | 0.99 | +15 / −16 | +2 / −17 |
| d3-9b | 24-409 vs 25-3152+R | 0.3051 | 0.8529 | 25-3152+R | 2.80 | 2.58 | +80 / −27 | +2 / −28 |
| d3-27b | 24-409 vs 25-3152 | 0.8542 | 0.5405 | 24-409 | 1.58 | 1.61 | +2 / −20 | +29 / −12 |
| d3-27b | 24-409 vs 25-3152+R | 0.8542 | 0.9133 | 25-3152+R | 1.07 | 0.59 | +4 / −4 | +2 / −1 |
| Jev | 24-409 vs 25-3152 | 0.5700 | 0.3100 | 24-409 | 1.84 | 1.08 | +2 / −9 | +26 / −27 |
| Jev | 24-409 vs 25-3152+R | 0.5700 | 0.4600 | 24-409 | 1.24 | 0.44 | +1 / −6 | +8 / −7 |

Roster effect on the same 249 pairs (25-3152 → 25-3152+R), next to the change of request (24-409 vs 25-3152, both without the roster), as log-odds gaps:

| model | thr98 25-3152 | thr98 25-3152+R | ratio +R / no roster | log-odds gap, roster | log-odds gap, request | bigger shift |
|---|---|---|---|---|---|---|
| 4b lp | 0.2210 | 0.5606 | 2.54 | 1.50 | 0.41 | roster |
| 9b lp | 0.4196 | 0.3901 | 0.93 | 0.12 | 0.79 | request |
| 27b lp | 0.0566 | 0.0783 | 1.38 | 0.35 | 2.25 | request |
| d3-4b | 0.3507 | 0.7588 | 2.16 | 1.76 | 0.08 | roster |
| d3-9b | 0.5427 | 0.8529 | 1.57 | 1.59 | 0.99 | roster |
| d3-27b | 0.5405 | 0.9133 | 1.69 | 2.19 | 1.61 | roster |
| Jev | 0.3100 | 0.4600 | 1.48 | 0.64 | 1.08 | request |

### A1c. The headline cutoff, request by request

The headline elim@98 uses one cutoff fitted on all pairs. Misses and eliminations per request at that cutoff (98% recall allows 2 misses on each request, 5 pooled).

| model | fitted on | cutoff | pooled misses | pooled elim | 24-409 misses | 24-409 elim | 25-3152 (or +R) misses | 25-3152 (or +R) elim |
|---|---|---|---|---|---|---|---|---|
| 4b lp | pooled | 0.2650 | 5/284 | 109/211 (52%) | 2/144 (98.6%) | 66/102 (65%) | 3/140 (97.9%) | 43/109 (39%) |
| 4b lp | pooled+R | 0.4230 | 5/284 | 147/211 (70%) | 4/144 (97.2%) | 80/102 (78%) | 1/140 (99.3%) | 67/109 (61%) |
| 9b lp | pooled | 0.3309 | 5/284 | 149/211 (71%) | 5/144 (96.5%) | 81/102 (79%) | 0/140 (100.0%) | 68/109 (62%) |
| 9b lp | pooled+R | 0.3212 | 5/284 | 147/211 (70%) | 4/144 (97.2%) | 80/102 (78%) | 1/140 (99.3%) | 67/109 (61%) |
| 27b lp | pooled | 0.0687 | 5/284 | 160/211 (76%) | 0/144 (100.0%) | 78/102 (76%) | 5/140 (96.4%) | 82/109 (75%) |
| 27b lp | pooled+R | 0.1728 | 5/284 | 185/211 (88%) | 0/144 (100.0%) | 84/102 (82%) | 5/140 (96.4%) | 101/109 (93%) |
| d3-4b | pooled | 0.3507 | 5/284 | 113/211 (54%) | 3/144 (97.9%) | 64/102 (63%) | 2/140 (98.6%) | 49/109 (45%) |
| d3-4b | pooled+R | 0.4299 | 5/284 | 145/211 (69%) | 5/144 (96.5%) | 64/102 (63%) | 0/140 (100.0%) | 81/109 (74%) |
| d3-9b | pooled | 0.3379 | 5/284 | 144/211 (68%) | 4/144 (97.2%) | 78/102 (76%) | 1/140 (99.3%) | 66/109 (61%) |
| d3-9b | pooled+R | 0.3548 | 5/284 | 157/211 (74%) | 5/144 (96.5%) | 79/102 (77%) | 0/140 (100.0%) | 78/109 (72%) |
| d3-27b | pooled | 0.5857 | 5/284 | 171/211 (81%) | 0/144 (100.0%) | 74/102 (73%) | 5/140 (96.4%) | 97/109 (89%) |
| d3-27b | pooled+R | 0.8819 | 5/284 | 203/211 (96%) | 4/144 (97.2%) | 96/102 (94%) | 1/140 (99.3%) | 107/109 (98%) |
| Jev | pooled | 0.3400 | 5/284 | 133/211 (63%) | 0/144 (100.0%) | 61/102 (60%) | 5/140 (96.4%) | 72/109 (66%) |
| Jev | pooled+R | 0.4900 | 5/284 | 158/211 (75%) | 1/144 (99.3%) | 66/102 (65%) | 4/140 (97.1%) | 92/109 (84%) |

With 5 pooled misses, at least one request must take 3 or more (5 > 2 + 2), so the pooled cutoff is below 98% on one request whenever it uses all 5. Models whose pooled misses all fall on ONE request: 4/7 (pooled), 3/7 (pooled+R).

### A1d. Which emails set the cutoff

The 3 lowest positive scores in each subset, lowest first, with kind (real = county production; close/priv/exempt = synthetic positives; hn-flip = synthetic hard negative judged responsive). thr98 is the 3rd-lowest positive (2 misses allowed) unless ties intervene.

| model | 24-409 | 25-3152 | 25-3152+R |
|---|---|---|---|
| 4b lp | real 0.2373, real 0.2494, real 0.3002 | real 0.1387, real 0.1889, real 0.2210 | real 0.3626, real 0.5066, real 0.5606 |
| 9b lp | close 0.1783, hn-flip 0.2398, real 0.2463 | real 0.3578, real 0.4047, real 0.4196 | real 0.2743, real 0.3744, real 0.3901 |
| 27b lp | close 0.2529, close 0.2663, real 0.3623 | real 0.0079, real 0.0501, real 0.0566 | close 0.0730, real 0.0779, real 0.0783 |
| d3-4b | real 0.1076, close 0.2608, real 0.3323 | real 0.1904, real 0.3158, real 0.3507 | priv 0.7520, exempt 0.7578, real 0.7588 |
| d3-9b | real 0.2598, real 0.2745, close 0.3051 | real 0.3177, real 0.4725, real 0.5427 | close 0.8311, real 0.8423, priv 0.8529 |
| d3-27b | close 0.7504, real 0.7747, real 0.8542 | real 0.4870, real 0.5095, real 0.5405 | real 0.8794, real 0.9060, close 0.9133 |
| Jev | real 0.4200, real 0.5100, real 0.5700 | real 0.2200, close 0.2900, real 0.3100 | real 0.3900, real 0.4500, real 0.4600 |

Real emails among these lowest positives: 49/63 slots, 24/35 distinct emails; among the 3rd-lowest (the one at thr98): 18/21 slots, 16/19 distinct emails. Base rate: real emails are 75/144 of 24-409's positives and 75/140 of 25-3152's. [corrected in verification: the earlier line gave only the slot counts, 49/63 and 18/21, which count an email again each time it recurs across models or in the roster twin]

**What the data shows**

- **The two requests want different cutoffs.** The higher cutoff is 1.06 times the lower one for d3-4b
  and 6.40 times for 27b lp (A1b). For three models the two bootstrap intervals don't overlap: 27b lp
  (0.3623 [0.2529–0.7792] vs 0.0566 [0.0079–0.1030]), d3-27b (0.8542 [0.7504–0.9201] vs 0.5405
  [0.4870–0.6115]) and Jev (0.5700 [0.4200–0.6300] vs 0.3100 [0.2200–0.3500]). For the 4b lp, 9b lp,
  d3-4b and d3-9b they overlap (A1a).
- **Which request needs the lower cutoff depends on the model.** 25-3152 needs the lower one for 4b lp,
  27b lp, d3-27b and Jev. 24-409 needs the lower one for 9b lp, d3-4b and d3-9b (A1b, "higher" column).
- **The roster moves some models' cutoffs more than the change of request does.** On the same 249
  pairs, adding the roster moves thr98 from 0.3507 to 0.7588 (d3-4b), from 0.5427 to 0.8529 (d3-9b),
  from 0.5405 to 0.9133 (d3-27b) and from 0.2210 to 0.5606 (4b lp). For these four models that is a
  bigger shift in log-odds than the change of request: 1.76 vs 0.08, 1.59 vs 0.99, 2.19 vs 1.61, and
  1.50 vs 0.41. For 9b lp, 27b lp and Jev the request matters more (0.12 vs 0.79, 0.35 vs 2.25, and
  0.64 vs 1.08) (A1b, roster-effect table). Between the d3-9b's 24-409 cutoff and its 25-3152+R cutoff
  lie 80 of 24-409's 144 positives (A1b).
- **The pooled cutoff hides a per-request shortfall.** At it, every model misses more than 2 on one
  request: 3 to 5 without the roster, 4 to 5 with it (A1c). Part of this is arithmetic. 5 pooled misses
  can't split as 2 + 2, so a pooled 98% always leaves one request below 98% when it uses all 5. The
  split is also lopsided: all 5 misses fall on one request for 4 of 7 models without the roster and 3
  of 7 with it (A1c).
- **The cutoff is set mostly by real emails.** The 63 entries in A1d are 35 distinct emails, because the
  same email recurs across models and in the roster twin. 24 of the 35 are real county-produced emails
  (69%), against 52–54% real among all of each request's positives. Of the 19 distinct emails sitting
  exactly at thr98 (21 entries), 16 are real. [corrected in verification: the original said "49 of the
  63 lowest-scoring positives" and "18 of the 21 positives", counting entries as if they were distinct
  emails]

**Interpretation.** A cutoff belongs to a combination of model, prompt and request type, not to a model
alone. The difference between the two requests isn't only resampling noise: for three models the
intervals are disjoint. It also isn't an artifact of the synthetic emails, because the emails that set
the cutoff are mostly real. Any change to the prompt (here, adding the roster) needs its own cutoff
check.

## A2. Transfer: set the cutoff on one request, apply it to the other

Four directions: 24-409 → 25-3152, 25-3152 → 24-409, 24-409 → 25-3152+R and 25-3152+R → 24-409. The
source's 98% cutoff is applied unchanged to the target. As safety margins, the source's 99% and 100%
cutoffs are tried too (1 and 0 source misses). The full per-direction tables, with cutoff values and
the misses that are real emails, are in the [appendix](#appendix-a2a-transfer-per-direction).

### A2b. Summary

Each cell: target misses / target eliminated share. Bold = target recall below 98%.

| model | 98%: 24-409 → 25-3152 | 98%: 25-3152 → 24-409 | 98%: 24-409 → 25-3152+R | 98%: 25-3152+R → 24-409 | 100%: 24-409 → 25-3152 | 100%: 25-3152 → 24-409 | 100%: 24-409 → 25-3152+R | 100%: 25-3152+R → 24-409 |
|---|---|---|---|---|---|---|---|---|
| 4b lp | **5 / 46%** | 0 / 62% | 0 / 50% | **9 / 87%** | **3 / 32%** | 0 / 40% | 0 / 39% | **3 / 75%** |
| 9b lp | 0 / 57% | **10 / 83%** | 0 / 59% | **6 / 82%** | 0 / 50% | **6 / 80%** | 0 / 49% | **3 / 77%** |
| 27b lp | **14 / 86%** | 0 / 75% | **15 / 94%** | 0 / 78% | **11 / 85%** | 0 / 64% | **10 / 94%** | 0 / 77% |
| d3-4b | 2 / 44% | **3 / 63%** | 0 / 64% | **76 / 92%** | 0 / 3% | 1 / 61% | 0 / 28% | **76 / 92%** |
| d3-9b | 0 / 59% | **17 / 89%** | 0 / 64% | **82 / 100%** | 0 / 52% | **3 / 75%** | 0 / 60% | **78 / 100%** |
| d3-27b | **31 / 96%** | 0 / 72% | 0 / 97% | **6 / 95%** | **15 / 93%** | 0 / 72% | 0 / 96% | **4 / 94%** |
| Jev | **28 / 83%** | 0 / 60% | **10 / 90%** | 1 / 63% | **13 / 75%** | 0 / 55% | 1 / 81% | 0 / 60% |

### A2c. How often transfer keeps 98% recall

| model | source level 98% | source level 99% | source level 100% |
|---|---|---|---|
| 4b lp | 2/4 | 2/4 | 2/4 |
| 9b lp | 2/4 | 2/4 | 2/4 |
| 27b lp | 2/4 | 2/4 | 2/4 |
| d3-4b | 2/4 | 3/4 | 3/4 |
| d3-9b | 2/4 | 2/4 | 2/4 |
| d3-27b | 2/4 | 2/4 | 2/4 |
| Jev | 2/4 | 2/4 | 3/4 |

### A2d. A coarser rule tested the same way

This is the grid heuristic that A5e later applies to all the labeled data. On the source request, take
the largest grid value that keeps 98% recall there. Step down 0, 1 or 2 grid values, then apply the
result to the target.

Cell: cutoff → target misses / target eliminated share. Bold = target recall below 98%.

| model | 24-409 → 25-3152 (−0; −1; −2 steps) | 25-3152 → 24-409 (−0; −1; −2 steps) | 24-409 → 25-3152+R (−0; −1; −2 steps) | 25-3152+R → 24-409 (−0; −1; −2 steps) |
|---|---|---|---|---|
| 4b lp | **0.3 → 5 / 46%**; 0.2 → 2 / 26%; 0.1 → 0 / 2% | 0.2 → 0 / 57%; 0.1 → 0 / 22%; 0.05 → 0 / 2% | 0.3 → 0 / 50%; 0.2 → 0 / 34%; 0.1 → 0 / 6% | **0.5 → 7 / 82%**; **0.4 → 4 / 77%**; 0.3 → 2 / 72% |
| 9b lp | 0.2 → 0 / 51%; 0.1 → 0 / 29%; 0.05 → 0 / 12% | **0.4 → 7 / 82%**; **0.3 → 3 / 78%**; 0.2 → 1 / 72% | 0.2 → 0 / 53%; 0.1 → 0 / 25%; 0.05 → 0 / 7% | **0.3 → 3 / 78%**; 0.2 → 1 / 72%; 0.1 → 0 / 60% |
| 27b lp | **0.3 → 11 / 85%**; **0.2 → 9 / 85%**; **0.1 → 7 / 79%** | 0.05 → 0 / 75%; 0.02 → 0 / 68%; 0.01 → 0 / 64% | **0.3 → 13 / 94%**; **0.2 → 6 / 93%**; **0.1 → 3 / 93%** | 0.05 → 0 / 75%; 0.02 → 0 / 68%; 0.01 → 0 / 64% |
| d3-4b | 0.3 → 1 / 39%; 0.2 → 1 / 12%; 0.1 → 0 / 2% | 0.3 → 2 / 63%; 0.2 → 1 / 61%; 0.1 → 0 / 60% | 0.3 → 0 / 61%; 0.2 → 0 / 51%; 0.1 → 0 / 23% | **0.7 → 53 / 84%**; **0.6 → 22 / 74%**; **0.5 → 9 / 68%** |
| d3-9b | 0.3 → 0 / 59%; 0.2 → 0 / 36%; 0.1 → 0 / 4% | **0.5 → 11 / 86%**; **0.4 → 7 / 79%**; 0.3 → 2 / 74% | 0.3 → 0 / 63%; 0.2 → 0 / 46%; 0.1 → 0 / 6% | **0.8 → 66 / 100%**; **0.7 → 40 / 95%**; **0.6 → 26 / 91%** |
| d3-27b | **0.8 → 24 / 94%**; **0.7 → 12 / 91%**; **0.6 → 6 / 89%** | 0.5 → 0 / 72%; 0.4 → 0 / 69%; 0.3 → 0 / 67% | 0.8 → 0 / 97%; 0.7 → 0 / 95%; 0.6 → 0 / 93% | 0.8 → 2 / 86%; 0.7 → 0 / 78%; 0.6 → 0 / 73% |
| Jev | **0.5 → 17 / 80%**; **0.4 → 12 / 73%**; 0.3 → 2 / 57% | 0.3 → 0 / 60%; 0.2 → 0 / 54%; 0.1 → 0 / 34% | **0.5 → 5 / 84%**; 0.4 → 1 / 81%; 0.3 → 0 / 74% | 0.4 → 0 / 60%; 0.3 → 0 / 60%; 0.2 → 0 / 54% |

| model | −0 steps: directions ≥ 98% | −1 step | −2 steps |
|---|---|---|---|
| 4b lp | 2/4 | 3/4 | 4/4 |
| 9b lp | 2/4 | 3/4 | 4/4 |
| 27b lp | 2/4 | 2/4 | 2/4 |
| d3-4b | 3/4 | 3/4 | 3/4 |
| d3-9b | 2/4 | 2/4 | 3/4 |
| d3-27b | 3/4 | 3/4 | 3/4 |
| Jev | 2/4 | 3/4 | 4/4 |

**What the data shows**

- **At the 98% level, transfer works in exactly 2 of 4 directions for every model** (A2c). That count is
  forced by arithmetic. A transferred thr98 keeps 98% exactly when the source's cutoff is at or below
  the target's own, so in each pair of opposite directions one works and one fails (compare A1b, "higher"
  column). What carries information is the size of each failure, and whether a margin rescues it.
- **The failures can be large** (A2b). Going 24-409 → 25-3152, 27b lp misses 14/140, Jev 28/140 and
  d3-27b 31/140. Going 25-3152+R → 24-409, d3-4b misses 76/144 and d3-9b 82/144, because the roster
  raised their 25-3152 scores. Most missed emails are real county emails: 25 of d3-27b's 31, and 17 of
  Jev's 28 (A2a, appendix).
- **The 99% and 100% margins rarely help.** They add a passing direction only for d3-4b (3/4 at 99% and
  100%) and Jev (3/4 at 100%) (A2c). The gap between the two requests is bigger than the gap between
  one request's 98% and 100% cutoffs.
- **When transfer keeps recall, it gives up elimination.** 25-3152 → 24-409 eliminates 77/102 (75%) for
  27b lp against the target's oracle 91/102 (89%), and 73/102 (72%) for d3-27b against 93/102 (91%)
  (A2a, appendix).
- **Grid headroom helps some models.** Two grid steps of headroom keep 98% in all 4 directions for 4b
  lp, 9b lp and Jev, in 3 of 4 for d3-4b, d3-9b and d3-27b, and in 2 of 4 for 27b lp (A2d). 27b lp still
  misses 7/140 on 25-3152 at 0.1, two steps below the 0.3 that 24-409 alone suggests.

**Interpretation.** One previous request isn't enough to set a cutoff for the next one, for any model
tested. The two requests differ in kind (topical vs correspondent-scoped), and each model puts them on
a different part of its score scale. The heuristic that survives transfer for 4b lp, 9b lp and Jev does
so by stepping down to cutoffs that eliminate much less (A2d).

## A3. Fixed cutoffs that need no labels

### A3a. Misses and eliminated share at each fixed cutoff

The specified grid is 0.05–0.5. The rows marked "(extra)" are added: 0.01 and 0.02 for 27b lp, whose
responsive emails can score far below 0.05, and 0.6–0.8 for runs whose scores sit high.

Cell: misses/positives · share of negatives eliminated. Bold = recall below 98% (more than 2 misses on a request, more than 5 pooled). Negatives per subset: 24-409 102, 25-3152 109, pooled 211.

#### 4b lp

| cutoff | 24-409 | 25-3152 | 25-3152+R | pooled | pooled+R |
|---|---|---|---|---|---|
| 0.01 (extra) | 0/144 · 0% | 0/140 · 0% | 0/140 · 0% | 0/284 · 0% | 0/284 · 0% |
| 0.02 (extra) | 0/144 · 0% | 0/140 · 0% | 0/140 · 0% | 0/284 · 0% | 0/284 · 0% |
| 0.05 | 0/144 · 2% | 0/140 · 0% | 0/140 · 0% | 0/284 · 1% | 0/284 · 1% |
| 0.1 | 0/144 · 22% | 0/140 · 2% | 0/140 · 6% | 0/284 · 11% | 0/284 · 13% |
| 0.2 | 0/144 · 57% | 2/140 · 26% | 0/140 · 34% | 2/284 · 41% | 0/284 · 45% |
| 0.3 | 2/144 · 72% | **5/140 · 46%** | 0/140 · 50% | **7/284 · 58%** | 2/284 · 60% |
| 0.4 | **4/144 · 77%** | **6/140 · 58%** | 1/140 · 60% | **10/284 · 67%** | 5/284 · 68% |
| 0.5 (default) | **7/144 · 82%** | **7/140 · 65%** | 1/140 · 67% | **14/284 · 73%** | **8/284 · 74%** |
| 0.6 (extra) | **13/144 · 87%** | **10/140 · 72%** | **4/140 · 76%** | **23/284 · 79%** | **17/284 · 82%** |
| 0.7 (extra) | **24/144 · 93%** | **26/140 · 81%** | **9/140 · 83%** | **50/284 · 87%** | **33/284 · 88%** |
| 0.8 (extra) | **53/144 · 98%** | **56/140 · 89%** | **25/140 · 91%** | **109/284 · 93%** | **78/284 · 94%** |

#### 9b lp

| cutoff | 24-409 | 25-3152 | 25-3152+R | pooled | pooled+R |
|---|---|---|---|---|---|
| 0.01 (extra) | 0/144 · 10% | 0/140 · 0% | 0/140 · 0% | 0/284 · 5% | 0/284 · 5% |
| 0.02 (extra) | 0/144 · 17% | 0/140 · 0% | 0/140 · 1% | 0/284 · 8% | 0/284 · 9% |
| 0.05 | 0/144 · 41% | 0/140 · 12% | 0/140 · 7% | 0/284 · 26% | 0/284 · 24% |
| 0.1 | 0/144 · 60% | 0/140 · 29% | 0/140 · 25% | 0/284 · 44% | 0/284 · 42% |
| 0.2 | 1/144 · 72% | 0/140 · 51% | 0/140 · 53% | 1/284 · 61% | 1/284 · 62% |
| 0.3 | **3/144 · 78%** | 0/140 · 62% | 1/140 · 59% | 3/284 · 70% | 4/284 · 68% |
| 0.4 | **7/144 · 82%** | 1/140 · 65% | **3/140 · 70%** | **8/284 · 73%** | **10/284 · 76%** |
| 0.5 (default) | **12/144 · 85%** | **5/140 · 75%** | **5/140 · 75%** | **17/284 · 80%** | **17/284 · 80%** |
| 0.6 (extra) | **17/144 · 91%** | **15/140 · 80%** | **8/140 · 79%** | **32/284 · 85%** | **25/284 · 85%** |
| 0.7 (extra) | **27/144 · 91%** | **22/140 · 85%** | **10/140 · 82%** | **49/284 · 88%** | **37/284 · 86%** |
| 0.8 (extra) | **43/144 · 97%** | **46/140 · 92%** | **16/140 · 89%** | **89/284 · 94%** | **59/284 · 93%** |

#### 27b lp

| cutoff | 24-409 | 25-3152 | 25-3152+R | pooled | pooled+R |
|---|---|---|---|---|---|
| 0.01 (extra) | 0/144 · 64% | 1/140 · 62% | 0/140 · 81% | 1/284 · 63% | 0/284 · 73% |
| 0.02 (extra) | 0/144 · 68% | 1/140 · 65% | 0/140 · 84% | 1/284 · 66% | 0/284 · 76% |
| 0.05 | 0/144 · 75% | 1/140 · 72% | 0/140 · 89% | 1/284 · 73% | 0/284 · 82% |
| 0.1 | 0/144 · 78% | **7/140 · 79%** | **3/140 · 93%** | **7/284 · 79%** | 3/284 · 86% |
| 0.2 | 0/144 · 83% | **9/140 · 85%** | **6/140 · 93%** | **9/284 · 84%** | **6/284 · 88%** |
| 0.3 | 2/144 · 89% | **11/140 · 85%** | **13/140 · 94%** | **13/284 · 87%** | **15/284 · 92%** |
| 0.4 | **4/144 · 91%** | **14/140 · 87%** | **16/140 · 95%** | **18/284 · 89%** | **20/284 · 93%** |
| 0.5 (default) | **5/144 · 94%** | **15/140 · 88%** | **18/140 · 95%** | **20/284 · 91%** | **23/284 · 95%** |
| 0.6 (extra) | **5/144 · 95%** | **20/140 · 91%** | **21/140 · 96%** | **25/284 · 93%** | **26/284 · 96%** |
| 0.7 (extra) | **5/144 · 95%** | **23/140 · 92%** | **23/140 · 97%** | **28/284 · 93%** | **28/284 · 96%** |
| 0.8 (extra) | **8/144 · 96%** | **32/140 · 94%** | **25/140 · 98%** | **40/284 · 95%** | **33/284 · 97%** |

#### d3-4b

| cutoff | 24-409 | 25-3152 | 25-3152+R | pooled | pooled+R |
|---|---|---|---|---|---|
| 0.01 (extra) | 0/144 · 0% | 0/140 · 0% | 0/140 · 0% | 0/284 · 0% | 0/284 · 0% |
| 0.02 (extra) | 0/144 · 16% | 0/140 · 0% | 0/140 · 0% | 0/284 · 8% | 0/284 · 8% |
| 0.05 | 0/144 · 50% | 0/140 · 0% | 0/140 · 1% | 0/284 · 24% | 0/284 · 25% |
| 0.1 | 0/144 · 60% | 0/140 · 2% | 0/140 · 23% | 0/284 · 30% | 0/284 · 41% |
| 0.2 | 1/144 · 61% | 1/140 · 12% | 0/140 · 51% | 2/284 · 36% | 1/284 · 56% |
| 0.3 | 2/144 · 63% | 1/140 · 39% | 0/140 · 61% | 3/284 · 50% | 2/284 · 62% |
| 0.4 | **3/144 · 63%** | **4/140 · 53%** | 0/140 · 71% | **7/284 · 58%** | 3/284 · 67% |
| 0.5 (default) | **9/144 · 68%** | **8/140 · 61%** | 0/140 · 77% | **17/284 · 64%** | **9/284 · 73%** |
| 0.6 (extra) | **22/144 · 74%** | **15/140 · 72%** | 0/140 · 83% | **37/284 · 73%** | **22/284 · 79%** |
| 0.7 (extra) | **53/144 · 84%** | **19/140 · 83%** | 0/140 · 84% | **72/284 · 83%** | **53/284 · 84%** |
| 0.8 (extra) | **93/144 · 94%** | **47/140 · 90%** | **7/140 · 88%** | **140/284 · 92%** | **100/284 · 91%** |

#### d3-9b

| cutoff | 24-409 | 25-3152 | 25-3152+R | pooled | pooled+R |
|---|---|---|---|---|---|
| 0.01 (extra) | 0/144 · 2% | 0/140 · 0% | 0/140 · 0% | 0/284 · 1% | 0/284 · 1% |
| 0.02 (extra) | 0/144 · 19% | 0/140 · 0% | 0/140 · 0% | 0/284 · 9% | 0/284 · 9% |
| 0.05 | 0/144 · 52% | 0/140 · 0% | 0/140 · 2% | 0/284 · 25% | 0/284 · 26% |
| 0.1 | 0/144 · 57% | 0/140 · 4% | 0/140 · 6% | 0/284 · 29% | 0/284 · 31% |
| 0.2 | 0/144 · 66% | 0/140 · 36% | 0/140 · 46% | 0/284 · 50% | 0/284 · 55% |
| 0.3 | 2/144 · 74% | 0/140 · 59% | 0/140 · 63% | 2/284 · 66% | 2/284 · 68% |
| 0.4 | **7/144 · 79%** | 1/140 · 64% | 0/140 · 73% | **8/284 · 72%** | **7/284 · 76%** |
| 0.5 (default) | **11/144 · 86%** | 2/140 · 72% | 0/140 · 79% | **13/284 · 79%** | **11/284 · 82%** |
| 0.6 (extra) | **26/144 · 91%** | **5/140 · 77%** | 0/140 · 82% | **31/284 · 84%** | **26/284 · 86%** |
| 0.7 (extra) | **40/144 · 95%** | **14/140 · 86%** | 0/140 · 85% | **54/284 · 91%** | **40/284 · 90%** |
| 0.8 (extra) | **66/144 · 100%** | **36/140 · 93%** | 0/140 · 88% | **102/284 · 96%** | **66/284 · 94%** |

#### d3-27b

| cutoff | 24-409 | 25-3152 | 25-3152+R | pooled | pooled+R |
|---|---|---|---|---|---|
| 0.01 (extra) | 0/144 · 54% | 0/140 · 3% | 0/140 · 44% | 0/284 · 27% | 0/284 · 49% |
| 0.02 (extra) | 0/144 · 59% | 0/140 · 32% | 0/140 · 53% | 0/284 · 45% | 0/284 · 56% |
| 0.05 | 0/144 · 61% | 0/140 · 51% | 0/140 · 63% | 0/284 · 56% | 0/284 · 62% |
| 0.1 | 0/144 · 62% | 0/140 · 59% | 0/140 · 72% | 0/284 · 60% | 0/284 · 67% |
| 0.2 | 0/144 · 66% | 0/140 · 69% | 0/140 · 81% | 0/284 · 67% | 0/284 · 73% |
| 0.3 | 0/144 · 67% | 0/140 · 76% | 0/140 · 85% | 0/284 · 72% | 0/284 · 76% |
| 0.4 | 0/144 · 69% | 0/140 · 79% | 0/140 · 89% | 0/284 · 74% | 0/284 · 79% |
| 0.5 (default) | 0/144 · 72% | 1/140 · 85% | 0/140 · 93% | 1/284 · 79% | 0/284 · 82% |
| 0.6 (extra) | 0/144 · 73% | **6/140 · 89%** | 0/140 · 93% | **6/284 · 81%** | 0/284 · 83% |
| 0.7 (extra) | 0/144 · 78% | **12/140 · 91%** | 0/140 · 95% | **12/284 · 85%** | 0/284 · 87% |
| 0.8 (extra) | 2/144 · 86% | **24/140 · 94%** | 0/140 · 97% | **26/284 · 91%** | 2/284 · 92% |

#### Jev

| cutoff | 24-409 | 25-3152 | 25-3152+R | pooled | pooled+R |
|---|---|---|---|---|---|
| 0.01 (extra) | 0/144 · 0% | 0/140 · 0% | 0/140 · 0% | 0/284 · 0% | 0/284 · 0% |
| 0.02 (extra) | 0/144 · 0% | 0/140 · 0% | 0/140 · 0% | 0/284 · 0% | 0/284 · 0% |
| 0.05 | 0/144 · 3% | 0/140 · 0% | 0/140 · 0% | 0/284 · 1% | 0/284 · 1% |
| 0.1 | 0/144 · 34% | 0/140 · 1% | 0/140 · 22% | 0/284 · 17% | 0/284 · 28% |
| 0.2 | 0/144 · 54% | 0/140 · 27% | 0/140 · 58% | 0/284 · 40% | 0/284 · 56% |
| 0.3 | 0/144 · 60% | 2/140 · 57% | 0/140 · 74% | 2/284 · 58% | 0/284 · 67% |
| 0.4 | 0/144 · 60% | **12/140 · 73%** | 1/140 · 81% | **12/284 · 67%** | 1/284 · 71% |
| 0.5 (default) | 1/144 · 65% | **17/140 · 80%** | **5/140 · 84%** | **18/284 · 73%** | **6/284 · 75%** |
| 0.6 (extra) | **4/144 · 71%** | **30/140 · 84%** | **12/140 · 93%** | **34/284 · 78%** | **16/284 · 82%** |
| 0.7 (extra) | **12/144 · 76%** | **51/140 · 94%** | **25/140 · 94%** | **63/284 · 85%** | **37/284 · 86%** |
| 0.8 (extra) | **35/144 · 91%** | **83/140 · 99%** | **44/140 · 97%** | **118/284 · 95%** | **79/284 · 94%** |

### A3b. One fixed cutoff for both requests

'Largest grid value' = the largest of 0.05–0.5 with ≥ 98% recall on both requests. 'Best 0.01 step' = the largest multiple of 0.01 with ≥ 98% recall on both (chosen with both requests' labels: in-sample). Eliminated shown per request as k/N (%).

| model | requests | fails above | largest grid value | 24-409 misses · elim | other misses · elim | best 0.01 step | 24-409 misses · elim | other misses · elim |
|---|---|---|---|---|---|---|---|---|
| 4b lp | 24-409 + 25-3152 | 0.2210 | 0.2 | 0/144 · 58/102 (57%) | 2/140 · 28/109 (26%) | 0.22 | 0/144 · 62/102 (61%) | 2/140 · 32/109 (29%) |
| 4b lp | 24-409 + 25-3152+R | 0.3002 | 0.3 | 2/144 · 73/102 (72%) | 0/140 · 54/109 (50%) | 0.3 | 2/144 · 73/102 (72%) | 0/140 · 54/109 (50%) |
| 9b lp | 24-409 + 25-3152 | 0.2463 | 0.2 | 1/144 · 73/102 (72%) | 0/140 · 56/109 (51%) | 0.24 | 2/144 · 78/102 (76%) | 0/140 · 62/109 (57%) |
| 9b lp | 24-409 + 25-3152+R | 0.2463 | 0.2 | 1/144 · 73/102 (72%) | 0/140 · 58/109 (53%) | 0.24 | 2/144 · 78/102 (76%) | 0/140 · 63/109 (58%) |
| 27b lp | 24-409 + 25-3152 | 0.0566 | 0.05 | 0/144 · 76/102 (75%) | 1/140 · 79/109 (72%) | 0.05 | 0/144 · 76/102 (75%) | 1/140 · 79/109 (72%) |
| 27b lp | 24-409 + 25-3152+R | 0.0783 | 0.05 | 0/144 · 76/102 (75%) | 0/140 · 97/109 (89%) | 0.07 | 0/144 · 78/102 (76%) | 0/140 · 98/109 (90%) |
| d3-4b | 24-409 + 25-3152 | 0.3323 | 0.3 | 2/144 · 64/102 (63%) | 1/140 · 42/109 (39%) | 0.33 | 2/144 · 64/102 (63%) | 2/140 · 48/109 (44%) |
| d3-4b | 24-409 + 25-3152+R | 0.3323 | 0.3 | 2/144 · 64/102 (63%) | 0/140 · 67/109 (61%) | 0.33 | 2/144 · 64/102 (63%) | 0/140 · 70/109 (64%) |
| d3-9b | 24-409 + 25-3152 | 0.3051 | 0.3 | 2/144 · 75/102 (74%) | 0/140 · 64/109 (59%) | 0.3 | 2/144 · 75/102 (74%) | 0/140 · 64/109 (59%) |
| d3-9b | 24-409 + 25-3152+R | 0.3051 | 0.3 | 2/144 · 75/102 (74%) | 0/140 · 69/109 (63%) | 0.3 | 2/144 · 75/102 (74%) | 0/140 · 69/109 (63%) |
| d3-27b | 24-409 + 25-3152 | 0.5405 | 0.5 | 0/144 · 73/102 (72%) | 1/140 · 93/109 (85%) | 0.54 | 0/144 · 73/102 (72%) | 2/140 · 93/109 (85%) |
| d3-27b | 24-409 + 25-3152+R | 0.8542 | 0.5 | 0/144 · 73/102 (72%) | 0/140 · 101/109 (93%) | 0.85 | 2/144 · 93/102 (91%) | 0/140 · 106/109 (97%) |
| Jev | 24-409 + 25-3152 | 0.3100 | 0.3 | 0/144 · 61/102 (60%) | 2/140 · 62/109 (57%) | 0.31 | 0/144 · 61/102 (60%) | 2/140 · 63/109 (58%) |
| Jev | 24-409 + 25-3152+R | 0.4600 | 0.4 | 0/144 · 61/102 (60%) | 1/140 · 88/109 (81%) | 0.46 | 1/144 · 64/102 (63%) | 2/140 · 91/109 (83%) |

### A3c. Contrast: JSON verdicts and the lp default

Rows with a null score (unparseable JSON) dropped: 5 (golden_qwen3.8_27b_json_p2: 2; golden_qwen3.8_27b_json_p2_roster: 1; golden_qwen3.5_9b_json_reason_p2: 1; golden_qwen3.8_27b_json_reason_p2: 1).

Cell: misses/positives · eliminated k/N (%). Bold = recall below 98%. The lp rows at 0.5 (A3a) are the matching default for the score models.

| run | 24-409 | 25-3152 | 25-3152+R | pooled | pooled+R |
|---|---|---|---|---|---|
| 4b json | **15/144 · 87/102 (85%)** | **12/140 · 74/109 (68%)** | **6/140 · 81/109 (74%)** | **27/284 · 161/211 (76%)** | **21/284 · 168/211 (80%)** |
| 9b json | **27/144 · 92/102 (90%)** | **26/140 · 91/109 (83%)** | **9/140 · 89/109 (82%)** | **53/284 · 183/211 (87%)** | **36/284 · 181/211 (86%)** |
| 27b json | 2/144 · 89/102 (87%) | **11/140 · 92/107 (86%)** | **3/139 · 103/109 (94%)** | **13/284 · 181/209 (87%)** | 5/283 · 192/211 (91%) |
| 4b jsonR | **15/144 · 86/102 (84%)** | **21/140 · 84/109 (77%)** | **15/140 · 91/109 (83%)** | **36/284 · 170/211 (81%)** | **30/284 · 177/211 (84%)** |
| 9b jsonR | **11/144 · 86/102 (84%)** | **10/139 · 76/109 (70%)** | **3/140 · 78/109 (72%)** | **21/283 · 162/211 (77%)** | **14/284 · 164/211 (78%)** |
| 27b jsonR | 0/144 · 78/102 (76%) | **15/140 · 94/108 (87%)** | **11/140 · 103/109 (94%)** | **15/284 · 172/210 (82%)** | **11/284 · 181/211 (86%)** |
| 4b lp @0.5 | **7/144 · 84/102 (82%)** | **7/140 · 71/109 (65%)** | 1/140 · 73/109 (67%) | **14/284 · 155/211 (73%)** | **8/284 · 157/211 (74%)** |
| 9b lp @0.5 | **12/144 · 87/102 (85%)** | **5/140 · 82/109 (75%)** | **5/140 · 82/109 (75%)** | **17/284 · 169/211 (80%)** | **17/284 · 169/211 (80%)** |
| 27b lp @0.5 | **5/144 · 96/102 (94%)** | **15/140 · 96/109 (88%)** | **18/140 · 104/109 (95%)** | **20/284 · 192/211 (91%)** | **23/284 · 200/211 (95%)** |
| d3-4b @0.5 | **9/144 · 69/102 (68%)** | **8/140 · 66/109 (61%)** | 0/140 · 84/109 (77%) | **17/284 · 135/211 (64%)** | **9/284 · 153/211 (73%)** |
| d3-9b @0.5 | **11/144 · 88/102 (86%)** | 2/140 · 78/109 (72%) | 0/140 · 86/109 (79%) | **13/284 · 166/211 (79%)** | **11/284 · 174/211 (82%)** |
| d3-27b @0.5 | 0/144 · 73/102 (72%) | 1/140 · 93/109 (85%) | 0/140 · 101/109 (93%) | 1/284 · 166/211 (79%) | 0/284 · 174/211 (82%) |
| Jev @0.5 | 1/144 · 66/102 (65%) | **17/140 · 87/109 (80%)** | **5/140 · 92/109 (84%)** | **18/284 · 153/211 (73%)** | **6/284 · 158/211 (75%)** |

**What the data shows**

- **At 0.5, only d3-27b keeps 98% recall on both requests.** It misses 0/144 and 1/140, or 0/140 with
  the roster, and eliminates 72%, 85% and 93% (A3a, A3c). At 0.5 the others miss: 4b lp 7 and 7; 9b lp
  12 and 5; 27b lp 5 and 15 (18 with the roster); d3-4b 9 and 8; d3-9b 11 and 2; Jev 1 and 17 (5 with
  the roster) (A3c).
- **No JSON run keeps 98% recall on 25-3152, with or without the roster** (A3c). The 27b json and jsonR
  do hold on 24-409 (2/144 and 0/144 missed).
- **Each model has a grid value that holds on both requests, but only just** (A3b). Here are the largest
  safe grid value and the cutoff above which recall fails, for each model: 4b lp 0.2 and 0.2210; 9b lp
  0.2 and 0.2463; 27b lp 0.05 and 0.0566; d3-4b 0.3 and 0.3323; d3-9b 0.3 and 0.3051; d3-27b 0.5 and
  0.5405; Jev 0.3 and 0.3100. For 27b lp, 0.05 holds because 25-3152's third-lowest positive scores
  0.0566, just above it; any cutoff above 0.0566 misses 3 (A1d). [corrected in verification: the
  original credited the second-lowest positive (0.0501). That email doesn't decide it: with 2 misses
  allowed, 0.05 would still hold if it scored below 0.05]
- **27b lp can't reach 100% recall on 25-3152 at any cutoff of 0.01 or above** (A3a). One real
  responsive email scores 0.0079 (A1d).

**Interpretation.** The default 0.5 suits d3-27b alone. All but 1 of its 284 responsive emails score at
or above 0.5 (A3a, pooled); no other model comes close. For every other model, a fixed cutoff "that works on both requests" can be found
only by looking at both requests' labels. Even then it sits close to the point where it fails, so it is
a fitted number, not a label-free one.

## A4. Set the cutoff from a small labeled sample of the target request

### Design

- **Sampling.** The agency reviews n emails drawn by **simple random sampling** (without replacement)
  from the request's pool, with n = 20, 50, 100 (and 10–300 for the sample-size table). Stratifying by
  label is impossible before review. Stratifying by score is possible, but it is not tested here (see
  open questions). Each repetition draws the same pairs for every model and rule, so the comparisons are
  paired. There are 1,000 repetitions per cell, with fixed seeds.
- **Rules.** Let k be the number of responsive emails found in the sample.
  - `lowest`: the cutoff is the lowest score among the k responsive emails. This is the natural rule: it
    is the highest cutoff that would have flagged every responsive email the reviewers actually saw.
  - `lowest/3` and `lowest/10`: the same, with a safety margin. The model's odds at that score are
    divided by 3 or by 10. The margin is defined on odds, so it means the same thing whether the cutoff
    lands near 0.05 or near 0.9. The factors 3 and 10 are round illustrative values, not tuned.
  - `min(lowest, prior)`: the lower of `lowest` and the other request's thr98, which combines a
    previous request with the sample. For 24-409 in the roster setting the prior is 25-3152+R's thr98
    (`min(lowest, prior+R)`).
  - If k = 0, every rule reviews everything (cutoff 0). A4b shows how often this happens.
- **Two prevalence designs.**
  - *As-is*: the golden pool itself (24-409: 144 of 246 responsive; 25-3152: 140 of 249). Recall and
    elimination are measured on the emails that weren't sampled.
  - *20%*: a large pool in which 20% of the emails are responsive, closer to a real keyword search. The
    sample holds k ~ Binomial(n, 0.2) responsive emails, drawn without replacement from the request's
    positives. Recall is measured on the positives that weren't sampled, and elimination on all of the
    request's negatives. Only responsive emails set the cutoff, so the sampled negatives don't need to
    be simulated.
- **Reported per cell**: the median and 5th percentile of recall on the remainder; the 95th-percentile
  miss count; the median and 5th percentile of the eliminated share; and the share of repetitions that
  reach ≥ 98% recall. A "5th percentile" is the value that 5% of repetitions fall below.

### A4a. The `lowest` rule in theory

If the k sampled responsive emails are a random draw from all responsive emails and scores have no ties, the share of responsive emails scoring below the lowest sampled one follows a Beta(1, k) distribution: expected recall k/(k+1), median recall 0.5^(1/k), and P(recall ≥ 98%) = 1 − 0.98^k.

| responsive in sample (k) | expected recall | median recall | P(recall ≥ 98%) |
|---|---|---|---|
| 5 | 83.3% | 87.1% | 0.10 |
| 10 | 90.9% | 93.3% | 0.18 |
| 12 | 92.3% | 94.4% | 0.22 |
| 20 | 95.2% | 96.6% | 0.33 |
| 29 | 96.7% | 97.6% | 0.44 |
| 35 | 97.2% | 98.0% | 0.51 |
| 50 | 98.0% | 98.6% | 0.64 |
| 57 | 98.3% | 98.8% | 0.68 |
| 100 | 99.0% | 99.3% | 0.87 |
| 114 | 99.1% | 99.4% | 0.90 |
| 149 | 99.3% | 99.5% | 0.95 |

- k needed for P(recall ≥ 98%) ≥ 50%: 35
- k needed for P(recall ≥ 98%) ≥ 90%: 114
- k needed for P(recall ≥ 98%) ≥ 95%: 149

Margin examples (odds = p / (1 − p)): lowest 0.9 → lowest/3 0.750, lowest/10 0.474; lowest 0.5 → lowest/3 0.250, lowest/10 0.091; lowest 0.3 → lowest/3 0.125, lowest/10 0.041; lowest 0.05 → lowest/3 0.017, lowest/10 0.005

### A4b. How many responsive emails a sample holds

| request | design | n reviewed | mean k | k, 5th–95th pct | reps with k = 0 (review all) |
|---|---|---|---|---|---|
| 24-409 | as-is | 10 | 5.9 | 3–8 | 0/1000 |
| 24-409 | as-is | 20 | 11.7 | 8–15 | 0/1000 |
| 24-409 | as-is | 30 | 17.6 | 14–22 | 0/1000 |
| 24-409 | as-is | 50 | 29.3 | 24–34 | 0/1000 |
| 24-409 | as-is | 75 | 43.9 | 38–50 | 0/1000 |
| 24-409 | as-is | 100 | 58.3 | 52–64 | 0/1000 |
| 24-409 | 20% | 10 | 2.0 | 0–4 | 122/1000 |
| 24-409 | 20% | 20 | 4.0 | 1–7 | 11/1000 |
| 24-409 | 20% | 30 | 6.1 | 3–10 | 1/1000 |
| 24-409 | 20% | 50 | 10.0 | 6–15 | 0/1000 |
| 24-409 | 20% | 75 | 14.9 | 9–21 | 0/1000 |
| 24-409 | 20% | 100 | 20.1 | 14–27 | 0/1000 |
| 24-409 | 20% | 150 | 30.1 | 22–39 | 0/1000 |
| 24-409 | 20% | 200 | 39.9 | 31–49 | 0/1000 |
| 24-409 | 20% | 300 | 59.8 | 49–71 | 0/1000 |
| 25-3152 | as-is | 10 | 5.6 | 3–8 | 0/1000 |
| 25-3152 | as-is | 20 | 11.1 | 8–15 | 0/1000 |
| 25-3152 | as-is | 30 | 16.7 | 13–21 | 0/1000 |
| 25-3152 | as-is | 50 | 28.2 | 23–33 | 0/1000 |
| 25-3152 | as-is | 75 | 42.2 | 36–48 | 0/1000 |
| 25-3152 | as-is | 100 | 56.2 | 50–63 | 0/1000 |
| 25-3152 | 20% | 10 | 2.0 | 0–5 | 109/1000 |
| 25-3152 | 20% | 20 | 4.0 | 1–7 | 4/1000 |
| 25-3152 | 20% | 30 | 6.0 | 2–10 | 1/1000 |
| 25-3152 | 20% | 50 | 9.9 | 5–15 | 0/1000 |
| 25-3152 | 20% | 75 | 15.1 | 10–21 | 0/1000 |
| 25-3152 | 20% | 100 | 20.0 | 14–27 | 0/1000 |
| 25-3152 | 20% | 150 | 29.9 | 21–39 | 0/1000 |
| 25-3152 | 20% | 200 | 40.0 | 31–50 | 0/1000 |
| 25-3152 | 20% | 300 | 60.2 | 49–72 | 0/1000 |

25-3152+R draws the same pairs as 25-3152.

### A4c. Results at the golden set's prevalence

Cell: recall median / 5th percentile · misses at the 95th percentile (count) · eliminated median / 5th
percentile · share of repetitions with recall ≥ 98%. The 20%-prevalence versions of these tables are in
the [appendix](#appendix-a4c-at-20-prevalence).

#### 24-409

| model | n | lowest | lowest/3 | lowest/10 | min(lowest, prior) | min(lowest, prior+R) |
|---|---|---|---|---|---|---|
| 4b lp | 20 | 94.6% / 76.3% · ≤32 · 84% / 61% · 0.24 | 98.5% / 94.8% · ≤7 · 68% / 19% · 0.56 | 100.0% / 100.0% · ≤0 · 21% / 0% · 0.99 | 100.0% / 100.0% · ≤0 · 62% / 60% · 1.00 | 94.6% / 93.1% · ≤9 · 84% / 61% · 0.24 |
| 4b lp | 50 | 98.2% / 90.0% · ≤12 · 73% / 59% · 0.51 | 100.0% / 97.4% · ≤3 · 36% / 17% · 0.90 | 100.0% / 100.0% · ≤0 · 1% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 62% / 58% · 1.00 | 98.2% / 92.2% · ≤9 · 73% / 59% · 0.51 |
| 4b lp | 100 | 98.8% / 94.1% · ≤5 · 65% / 56% · 0.63 | 100.0% / 100.0% · ≤0 · 23% / 15% · 0.98 | 100.0% / 100.0% · ≤0 · 0% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 62% / 55% · 1.00 | 98.8% / 94.1% · ≤5 · 65% / 56% · 0.63 |
| 9b lp | 20 | 94.6% / 75.0% · ≤33 · 83% / 70% · 0.23 | 99.3% / 90.8% · ≤12 · 71% / 51% · 0.66 | 100.0% / 99.2% · ≤1 · 49% / 22% · 0.96 | 94.6% / 92.3% · ≤10 · 82% / 70% · 0.23 | 95.6% / 95.4% · ≤6 · 81% / 70% · 0.23 |
| 9b lp | 50 | 98.2% / 89.6% · ≤12 · 77% / 69% · 0.53 | 100.0% / 97.4% · ≤3 · 62% / 49% · 0.94 | 100.0% / 100.0% · ≤0 · 35% / 20% · 1.00 | 98.2% / 91.4% · ≤10 · 77% / 69% · 0.53 | 98.2% / 94.7% · ≤6 · 77% / 69% · 0.53 |
| 9b lp | 100 | 98.8% / 94.1% · ≤5 · 75% / 66% · 0.64 | 100.0% / 100.0% · ≤0 · 58% / 46% · 1.00 | 100.0% / 100.0% · ≤0 · 30% / 18% · 1.00 | 98.8% / 94.1% · ≤5 · 75% / 66% · 0.64 | 98.8% / 94.1% · ≤5 · 75% / 66% · 0.64 |
| 27b lp | 20 | 94.1% / 75.8% · ≤32 · 97% / 86% · 0.23 | 96.2% / 85.4% · ≤19 · 95% / 78% · 0.35 | 98.5% / 90.2% · ≤13 · 88% / 71% · 0.62 | 100.0% / 100.0% · ≤0 · 76% / 74% · 1.00 | 100.0% / 100.0% · ≤0 · 78% / 77% · 1.00 |
| 27b lp | 50 | 97.5% / 89.5% · ≤12 · 90% / 84% · 0.50 | 100.0% / 94.8% · ≤6 · 82% / 76% · 0.69 | 100.0% / 96.5% · ≤4 · 76% / 69% · 0.93 | 100.0% / 100.0% · ≤0 · 76% / 72% · 1.00 | 100.0% / 100.0% · ≤0 · 78% / 75% · 1.00 |
| 27b lp | 100 | 98.9% / 94.0% · ≤5 · 88% / 82% · 0.65 | 100.0% / 95.2% · ≤4 · 80% / 74% · 0.93 | 100.0% / 100.0% · ≤0 · 73% / 66% · 0.99 | 100.0% / 100.0% · ≤0 · 75% / 69% · 1.00 | 100.0% / 100.0% · ≤0 · 78% / 73% · 1.00 |
| d3-4b | 20 | 94.0% / 75.4% · ≤33 · 68% / 60% · 0.23 | 99.2% / 97.7% · ≤3 · 61% / 37% · 0.86 | 100.0% / 99.2% · ≤1 · 58% / 1% · 1.00 | 97.7% / 97.7% · ≤3 · 63% / 60% · 0.23 | 94.0% / 75.4% · ≤33 · 68% / 60% · 0.23 |
| d3-4b | 50 | 98.2% / 89.7% · ≤12 · 63% / 57% · 0.51 | 99.1% / 98.2% · ≤2 · 60% / 34% · 0.99 | 100.0% / 100.0% · ≤0 · 52% / 1% · 1.00 | 98.2% / 97.3% · ≤3 · 62% / 57% · 0.51 | 98.2% / 89.7% · ≤12 · 63% / 57% · 0.51 |
| d3-4b | 100 | 98.9% / 94.1% · ≤5 · 62% / 54% · 0.65 | 100.0% / 98.8% · ≤1 · 56% / 32% · 0.99 | 100.0% / 100.0% · ≤0 · 33% / 0% · 1.00 | 98.9% / 96.4% · ≤3 · 61% / 54% · 0.65 | 98.9% / 94.1% · ≤5 · 62% / 54% · 0.65 |
| d3-9b | 20 | 94.1% / 74.4% · ≤34 · 82% / 69% · 0.24 | 100.0% / 94.9% · ≤7 · 66% / 57% · 0.83 | 100.0% / 100.0% · ≤0 · 54% / 40% · 1.00 | 94.1% / 87.1% · ≤17 · 82% / 69% · 0.24 | 94.1% / 74.4% · ≤34 · 82% / 69% · 0.24 |
| d3-9b | 50 | 97.5% / 89.5% · ≤12 · 75% / 67% · 0.50 | 100.0% / 99.1% · ≤1 · 61% / 54% · 0.99 | 100.0% / 100.0% · ≤0 · 49% / 38% · 1.00 | 97.5% / 89.5% · ≤12 · 75% / 67% · 0.50 | 97.5% / 89.5% · ≤12 · 75% / 67% · 0.50 |
| d3-9b | 100 | 98.8% / 94.2% · ≤5 · 72% / 64% · 0.64 | 100.0% / 100.0% · ≤0 · 59% / 52% · 1.00 | 100.0% / 100.0% · ≤0 · 43% / 35% · 1.00 | 98.8% / 94.2% · ≤5 · 72% / 64% · 0.64 | 98.8% / 94.2% · ≤5 · 72% / 64% · 0.64 |
| d3-27b | 20 | 94.7% / 75.0% · ≤34 · 96% / 81% · 0.21 | 98.5% / 88.4% · ≤16 · 86% / 71% · 0.71 | 100.0% / 98.5% · ≤2 · 72% / 65% · 0.96 | 100.0% / 100.0% · ≤0 · 72% / 70% · 1.00 | 95.6% / 95.4% · ≤6 · 95% / 81% · 0.21 |
| d3-27b | 50 | 98.2% / 88.8% · ≤13 · 93% / 79% · 0.51 | 100.0% / 98.1% · ≤2 · 76% / 69% · 0.95 | 100.0% / 100.0% · ≤0 · 68% / 63% · 1.00 | 100.0% / 100.0% · ≤0 · 71% / 68% · 1.00 | 98.2% / 94.6% · ≤6 · 93% / 79% · 0.51 |
| d3-27b | 100 | 98.9% / 93.8% · ≤6 · 83% / 76% · 0.65 | 100.0% / 98.8% · ≤2 · 73% / 66% · 0.95 | 100.0% / 100.0% · ≤0 · 67% / 60% · 1.00 | 100.0% / 100.0% · ≤0 · 71% / 65% · 1.00 | 98.9% / 93.8% · ≤6 · 83% / 76% · 0.65 |
| Jev | 20 | 95.4% / 76.1% · ≤32 · 72% / 61% · 0.30 | 100.0% / 98.5% · ≤2 · 61% / 54% · 0.96 | 100.0% / 100.0% · ≤0 · 50% / 19% · 1.00 | 100.0% / 100.0% · ≤0 · 60% / 57% · 1.00 | 99.2% / 99.2% · ≤1 · 63% / 60% · 1.00 |
| Jev | 50 | 98.3% / 90.4% · ≤11 · 68% / 59% · 0.63 | 100.0% / 100.0% · ≤0 · 59% / 52% · 1.00 | 100.0% / 100.0% · ≤0 · 40% / 17% · 1.00 | 100.0% / 100.0% · ≤0 · 60% / 56% · 1.00 | 99.1% / 99.1% · ≤1 · 62% / 58% · 1.00 |
| Jev | 100 | 98.9% / 94.0% · ≤5 · 65% / 56% · 0.65 | 100.0% / 100.0% · ≤0 · 57% / 49% · 1.00 | 100.0% / 100.0% · ≤0 · 33% / 15% · 1.00 | 100.0% / 100.0% · ≤0 · 60% / 53% · 1.00 | 98.9% / 98.8% · ≤1 · 62% / 55% · 1.00 |

#### 25-3152

| model | n | lowest | lowest/3 | lowest/10 | min(lowest, prior) |
|---|---|---|---|---|---|
| 4b lp | 20 | 93.7% / 73.6% · ≤35 · 68% / 10% · 0.21 | 96.8% / 94.6% · ≤7 · 42% / 0% · 0.42 | 100.0% / 98.4% · ≤3 · 2% / 0% · 0.95 | 96.2% / 96.0% · ≤5 · 45% / 10% · 0.21 |
| 4b lp | 50 | 97.4% / 89.0% · ≤12 · 35% / 9% · 0.49 | 100.0% / 95.5% · ≤5 · 1% / 0% · 0.80 | 100.0% / 99.1% · ≤1 · 0% / 0% · 1.00 | 97.4% / 95.4% · ≤5 · 35% / 9% · 0.49 |
| 4b lp | 100 | 98.8% / 93.8% · ≤5 · 22% / 7% · 0.62 | 100.0% / 98.8% · ≤1 · 0% / 0% · 0.95 | 100.0% / 100.0% · ≤0 · 0% / 0% · 1.00 | 98.8% / 94.3% · ≤5 · 22% / 7% · 0.62 |
| 9b lp | 20 | 93.8% / 72.5% · ≤36 · 75% / 63% · 0.21 | 100.0% / 93.7% · ≤9 · 60% / 46% · 0.85 | 100.0% / 100.0% · ≤0 · 30% / 13% · 1.00 | 100.0% / 100.0% · ≤0 · 57% / 55% · 1.00 |
| 9b lp | 50 | 97.4% / 88.8% · ≤13 · 72% / 62% · 0.49 | 100.0% / 100.0% · ≤0 · 54% / 44% · 0.99 | 100.0% / 100.0% · ≤0 · 22% / 12% · 1.00 | 100.0% / 100.0% · ≤0 · 57% / 53% · 1.00 |
| 9b lp | 100 | 98.8% / 94.0% · ≤5 · 68% / 59% · 0.61 | 100.0% / 100.0% · ≤0 · 50% / 42% · 1.00 | 100.0% / 100.0% · ≤0 · 16% / 10% · 1.00 | 100.0% / 100.0% · ≤0 · 57% / 51% · 1.00 |
| 27b lp | 20 | 93.7% / 72.9% · ≤35 · 84% / 63% · 0.20 | 96.1% / 84.7% · ≤20 · 76% / 58% · 0.47 | 99.2% / 90.7% · ≤12 · 67% / 50% · 0.70 | 93.7% / 89.0% · ≤14 · 84% / 63% · 0.20 |
| 27b lp | 50 | 97.4% / 89.6% · ≤12 · 74% / 61% · 0.49 | 99.1% / 92.9% · ≤8 · 66% / 56% · 0.84 | 100.0% / 99.1% · ≤1 · 62% / 47% · 0.97 | 97.4% / 89.6% · ≤12 · 74% / 61% · 0.49 |
| 27b lp | 100 | 98.8% / 93.8% · ≤5 · 71% / 59% · 0.62 | 98.9% / 98.7% · ≤1 · 63% / 54% · 0.98 | 100.0% / 100.0% · ≤0 · 59% / 44% · 1.00 | 98.8% / 93.8% · ≤5 · 71% / 59% · 0.62 |
| d3-4b | 20 | 93.9% / 72.7% · ≤36 · 61% / 11% · 0.21 | 99.2% / 93.7% · ≤8 · 30% / 2% · 0.73 | 100.0% / 99.2% · ≤1 · 2% / 0% · 1.00 | 98.4% / 98.4% · ≤2 · 44% / 11% · 1.00 |
| d3-4b | 50 | 97.6% / 89.5% · ≤12 · 46% / 9% · 0.50 | 100.0% / 99.1% · ≤1 · 5% / 1% · 0.98 | 100.0% / 100.0% · ≤0 · 0% / 0% · 1.00 | 98.3% / 98.1% · ≤2 · 43% / 9% · 1.00 |
| d3-4b | 100 | 98.8% / 94.0% · ≤5 · 39% / 7% · 0.63 | 100.0% / 100.0% · ≤0 · 3% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 0% / 0% · 1.00 | 98.8% / 97.5% · ≤2 · 38% / 7% · 0.63 |
| d3-9b | 20 | 93.9% / 75.6% · ≤32 · 79% / 60% · 0.22 | 99.2% / 97.7% · ≤3 · 62% / 12% · 0.91 | 100.0% / 100.0% · ≤0 · 14% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 59% / 56% · 1.00 |
| d3-9b | 50 | 98.1% / 88.6% · ≤13 · 75% / 58% · 0.51 | 100.0% / 99.1% · ≤1 · 58% / 10% · 1.00 | 100.0% / 100.0% · ≤0 · 5% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 59% / 55% · 1.00 |
| d3-9b | 100 | 98.8% / 94.0% · ≤5 · 69% / 55% · 0.63 | 100.0% / 98.9% · ≤1 · 43% / 8% · 1.00 | 100.0% / 100.0% · ≤0 · 1% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 59% / 52% · 1.00 |
| d3-27b | 20 | 93.8% / 72.7% · ≤35 · 90% / 84% · 0.23 | 100.0% / 90.7% · ≤12 · 77% / 73% · 0.80 | 100.0% / 100.0% · ≤0 · 63% / 56% · 0.97 | 93.8% / 76.3% · ≤31 · 90% / 84% · 0.23 |
| d3-27b | 50 | 97.3% / 89.5% · ≤12 · 87% / 83% · 0.47 | 100.0% / 100.0% · ≤0 · 76% / 72% · 0.99 | 100.0% / 100.0% · ≤0 · 60% / 54% · 1.00 | 97.3% / 89.5% · ≤12 · 87% / 83% · 0.47 |
| d3-27b | 100 | 98.8% / 93.3% · ≤6 · 86% / 81% · 0.62 | 100.0% / 100.0% · ≤0 · 75% / 70% · 1.00 | 100.0% / 100.0% · ≤0 · 58% / 51% · 1.00 | 98.8% / 93.3% · ≤6 · 86% / 81% · 0.62 |
| Jev | 20 | 93.8% / 75.6% · ≤32 · 67% / 33% · 0.21 | 100.0% / 93.9% · ≤8 · 17% / 0% · 0.91 | 100.0% / 100.0% · ≤0 · 0% / 0% · 1.00 | 93.8% / 78.5% · ≤28 · 67% / 33% · 0.21 |
| Jev | 50 | 97.4% / 88.5% · ≤13 · 61% / 30% · 0.49 | 100.0% / 100.0% · ≤0 · 11% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 0% / 0% · 1.00 | 97.4% / 88.5% · ≤13 · 61% / 30% · 0.49 |
| Jev | 100 | 98.8% / 93.9% · ≤5 · 55% / 29% · 0.63 | 100.0% / 100.0% · ≤0 · 6% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 0% / 0% · 1.00 | 98.8% / 93.9% · ≤5 · 55% / 29% · 0.63 |

#### 25-3152+R

| model | n | lowest | lowest/3 | lowest/10 | min(lowest, prior) |
|---|---|---|---|---|---|
| 4b lp | 20 | 93.9% / 72.3% · ≤36 · 83% / 59% · 0.21 | 99.2% / 95.3% · ≤6 · 61% / 20% · 0.83 | 100.0% / 100.0% · ≤0 · 27% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 50% / 47% · 1.00 |
| 4b lp | 50 | 97.4% / 88.5% · ≤13 · 76% / 57% · 0.48 | 100.0% / 99.1% · ≤1 · 51% / 18% · 0.99 | 100.0% / 100.0% · ≤0 · 8% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 49% / 46% · 1.00 |
| 4b lp | 100 | 98.8% / 93.8% · ≤5 · 67% / 54% · 0.65 | 100.0% / 100.0% · ≤0 · 42% / 16% · 1.00 | 100.0% / 100.0% · ≤0 · 3% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 50% / 43% · 1.00 |
| 9b lp | 20 | 93.8% / 71.2% · ≤38 · 79% / 60% · 0.19 | 99.2% / 92.1% · ≤10 · 64% / 32% · 0.56 | 100.0% / 96.9% · ≤4 · 38% / 3% · 0.92 | 100.0% / 100.0% · ≤0 · 59% / 56% · 1.00 |
| 9b lp | 50 | 97.4% / 89.3% · ≤12 · 69% / 57% · 0.48 | 100.0% / 94.6% · ≤6 · 51% / 30% · 0.89 | 100.0% / 100.0% · ≤0 · 11% / 2% · 1.00 | 100.0% / 100.0% · ≤0 · 59% / 55% · 1.00 |
| 9b lp | 100 | 98.8% / 94.1% · ≤5 · 65% / 55% · 0.65 | 100.0% / 100.0% · ≤0 · 45% / 27% · 0.99 | 100.0% / 100.0% · ≤0 · 8% / 1% · 1.00 | 100.0% / 100.0% · ≤0 · 59% / 52% · 1.00 |
| 27b lp | 20 | 93.8% / 72.3% · ≤36 · 93% / 90% · 0.22 | 97.7% / 79.1% · ≤27 · 92% / 85% · 0.44 | 100.0% / 82.3% · ≤23 · 85% / 77% · 0.74 | 93.8% / 88.2% · ≤15 · 93% / 90% · 0.22 |
| 27b lp | 50 | 97.3% / 88.5% · ≤13 · 92% / 89% · 0.46 | 100.0% / 96.6% · ≤4 · 88% / 83% · 0.79 | 100.0% / 100.0% · ≤0 · 81% / 75% · 0.97 | 97.3% / 88.5% · ≤13 · 92% / 89% · 0.46 |
| 27b lp | 100 | 98.8% / 94.0% · ≤5 · 91% / 87% · 0.64 | 100.0% / 100.0% · ≤0 · 86% / 81% · 0.97 | 100.0% / 100.0% · ≤0 · 79% / 73% · 1.00 | 98.8% / 94.0% · ≤5 · 91% / 87% · 0.64 |
| d3-4b | 20 | 93.8% / 73.1% · ≤35 · 89% / 84% · 0.23 | 100.0% / 86.2% · ≤18 · 82% / 76% · 0.92 | 100.0% / 100.0% · ≤0 · 62% / 54% · 1.00 | 100.0% / 100.0% · ≤0 · 64% / 62% · 1.00 |
| d3-4b | 50 | 97.4% / 87.8% · ≤14 · 87% / 83% · 0.49 | 100.0% / 100.0% · ≤0 · 79% / 75% · 1.00 | 100.0% / 100.0% · ≤0 · 57% / 53% · 1.00 | 100.0% / 100.0% · ≤0 · 64% / 60% · 1.00 |
| d3-4b | 100 | 98.8% / 93.8% · ≤5 · 86% / 81% · 0.63 | 100.0% / 100.0% · ≤0 · 78% / 72% · 1.00 | 100.0% / 100.0% · ≤0 · 56% / 50% · 1.00 | 100.0% / 100.0% · ≤0 · 64% / 58% · 1.00 |
| d3-9b | 20 | 93.8% / 74.6% · ≤34 · 93% / 89% · 0.22 | 100.0% / 98.5% · ≤2 · 85% / 82% · 0.96 | 100.0% / 100.0% · ≤0 · 75% / 69% · 1.00 | 100.0% / 100.0% · ≤0 · 64% / 62% · 1.00 |
| d3-9b | 50 | 97.4% / 88.6% · ≤13 · 91% / 88% · 0.47 | 100.0% / 100.0% · ≤0 · 85% / 80% · 1.00 | 100.0% / 100.0% · ≤0 · 72% / 67% · 1.00 | 100.0% / 100.0% · ≤0 · 64% / 61% · 1.00 |
| d3-9b | 100 | 98.8% / 93.8% · ≤5 · 90% / 86% · 0.63 | 100.0% / 100.0% · ≤0 · 84% / 78% · 1.00 | 100.0% / 100.0% · ≤0 · 70% / 64% · 1.00 | 100.0% / 100.0% · ≤0 · 64% / 58% · 1.00 |
| d3-27b | 20 | 93.8% / 73.5% · ≤34 · 99% / 98% · 0.23 | 100.0% / 99.2% · ≤1 · 97% / 95% · 0.96 | 100.0% / 100.0% · ≤0 · 93% / 90% · 0.99 | 100.0% / 100.0% · ≤0 · 97% / 97% · 1.00 |
| d3-27b | 50 | 98.1% / 89.5% · ≤12 · 98% / 98% · 0.51 | 100.0% / 100.0% · ≤0 · 97% / 94% · 1.00 | 100.0% / 100.0% · ≤0 · 92% / 89% · 1.00 | 100.0% / 100.0% · ≤0 · 97% / 96% · 1.00 |
| d3-27b | 100 | 98.8% / 94.1% · ≤5 · 98% / 97% · 0.64 | 100.0% / 100.0% · ≤0 · 97% / 94% · 1.00 | 100.0% / 100.0% · ≤0 · 92% / 87% · 1.00 | 100.0% / 100.0% · ≤0 · 97% / 95% · 1.00 |
| Jev | 20 | 93.1% / 74.6% · ≤33 · 88% / 80% · 0.21 | 100.0% / 96.9% · ≤4 · 74% / 57% · 0.92 | 100.0% / 100.0% · ≤0 · 29% / 4% · 1.00 | 93.1% / 92.1% · ≤10 · 88% / 80% · 0.21 |
| Jev | 50 | 97.3% / 89.3% · ≤12 · 84% / 78% · 0.47 | 100.0% / 100.0% · ≤0 · 66% / 54% · 1.00 | 100.0% / 100.0% · ≤0 · 11% / 3% · 1.00 | 97.3% / 91.2% · ≤10 · 84% / 78% · 0.47 |
| Jev | 100 | 98.8% / 94.1% · ≤5 · 82% / 76% · 0.64 | 100.0% / 100.0% · ≤0 · 60% / 52% · 1.00 | 100.0% / 100.0% · ≤0 · 6% / 2% · 1.00 | 98.8% / 94.1% · ≤5 · 82% / 76% · 0.64 |

### A4d. Sample size needed, and the effect of lower prevalence

Smallest n reviewed (from the grid as-is: 10, 20, 30, 50, 75, 100; 20%: also 150, 200, 300) at which the MEDIAN repetition reaches ≥ 98% recall on the remainder / at which 90% of repetitions do. '>max' = not reached on the grid.

#### Rule: lowest

| model | 24-409 as-is | 24-409 20% | 25-3152 as-is | 25-3152 20% | 25-3152+R as-is | 25-3152+R 20% |
|---|---|---|---|---|---|---|
| 4b lp | 50 / >100 | 200 / >300 | 75 / >100 | 200 / >300 | 75 / >100 | 150 / >300 |
| 9b lp | 50 / >100 | 150 / >300 | 75 / >100 | 150 / >300 | 75 / >100 | 200 / >300 |
| 27b lp | 75 / >100 | 200 / >300 | 75 / >100 | 150 / >300 | 75 / >100 | 200 / >300 |
| d3-4b | 50 / >100 | 200 / >300 | 75 / >100 | 150 / >300 | 75 / >100 | 150 / >300 |
| d3-9b | 75 / >100 | 150 / >300 | 50 / >100 | 150 / >300 | 75 / >100 | 200 / >300 |
| d3-27b | 50 / >100 | 200 / >300 | 75 / >100 | 200 / >300 | 50 / >100 | 150 / >300 |
| Jev | 50 / >100 | 150 / >300 | 75 / >100 | 150 / >300 | 75 / >100 | 150 / >300 |

#### Rule: lowest/3

| model | 24-409 as-is | 24-409 20% | 25-3152 as-is | 25-3152 20% | 25-3152+R as-is | 25-3152+R 20% |
|---|---|---|---|---|---|---|
| 4b lp | 20 / 75 | 75 / 200 | 30 / 75 | 75 / 300 | 10 / 30 | 30 / 75 |
| 9b lp | 20 / 50 | 50 / 150 | 10 / 30 | 30 / 75 | 20 / 75 | 50 / 150 |
| 27b lp | 50 / 100 | 100 / 300 | 30 / 75 | 75 / 200 | 30 / 75 | 75 / 200 |
| d3-4b | 10 / 30 | 30 / 100 | 10 / 50 | 30 / 100 | 10 / 20 | 20 / 75 |
| d3-9b | 10 / 30 | 30 / 100 | 10 / 20 | 20 / 75 | 10 / 20 | 10 / 50 |
| d3-27b | 20 / 50 | 50 / 150 | 10 / 30 | 30 / 100 | 10 / 20 | 10 / 50 |
| Jev | 10 / 20 | 20 / 50 | 10 / 20 | 20 / 75 | 10 / 20 | 20 / 75 |

#### Rule: lowest/10

| model | 24-409 as-is | 24-409 20% | 25-3152 as-is | 25-3152 20% | 25-3152+R as-is | 25-3152+R 20% |
|---|---|---|---|---|---|---|
| 4b lp | 10 / 10 | 10 / 30 | 10 / 20 | 10 / 50 | 10 / 10 | 10 / 20 |
| 9b lp | 10 / 20 | 10 / 50 | 10 / 10 | 10 / 30 | 10 / 20 | 20 / 75 |
| 27b lp | 20 / 50 | 50 / 150 | 20 / 50 | 30 / 150 | 10 / 30 | 30 / 100 |
| d3-4b | 10 / 10 | 10 / 20 | 10 / 10 | 10 / 30 | 10 / 10 | 10 / 30 |
| d3-9b | 10 / 10 | 10 / 30 | 10 / 10 | 10 / 10 | 10 / 10 | 10 / 20 |
| d3-27b | 10 / 20 | 10 / 50 | 10 / 20 | 10 / 50 | 10 / 10 | 10 / 30 |
| Jev | 10 / 10 | 10 / 20 | 10 / 10 | 10 / 20 | 10 / 10 | 10 / 20 |

#### Rule: min(lowest, prior)

| model | 24-409 as-is (prior +R) | 24-409 20% (prior +R) | 24-409 as-is | 24-409 20% | 25-3152 as-is | 25-3152 20% | 25-3152+R as-is | 25-3152+R 20% |
|---|---|---|---|---|---|---|---|---|
| 4b lp | 50 / >100 | 200 / >300 | 10 / 10 | 10 / 10 | 75 / >100 | 200 / >300 | 10 / 10 | 10 / 10 |
| 9b lp | 50 / >100 | 150 / >300 | 50 / >100 | 150 / >300 | 10 / 10 | 10 / 10 | 10 / 10 | 10 / 10 |
| 27b lp | 10 / 10 | 10 / 10 | 10 / 10 | 10 / 10 | 75 / >100 | 150 / >300 | 75 / >100 | 200 / >300 |
| d3-4b | 50 / >100 | 200 / >300 | 50 / >100 | 200 / >300 | 10 / 10 | 10 / 10 | 10 / 10 | 10 / 10 |
| d3-9b | 75 / >100 | 150 / >300 | 75 / >100 | 150 / >300 | 10 / 10 | 10 / 10 | 10 / 10 | 10 / 10 |
| d3-27b | 50 / >100 | 200 / >300 | 10 / 10 | 10 / 10 | 75 / >100 | 200 / >300 | 10 / 10 | 10 / 10 |
| Jev | 10 / 10 | 10 / 10 | 10 / 10 | 10 / 10 | 75 / >100 | 150 / >300 | 75 / >100 | 150 / >300 |

#### How much the 20% design raises the needed n

needed n at 20% / needed n as-is, over the 7 models x 3 requests where both are reached on the grid (median-98% and 90%-of-repetitions criteria).

| rule | criterion | cells reached in both designs | ratio range | median ratio |
|---|---|---|---|---|
| lowest | median ≥ 98% | 21/21 | 2.0–4.0 | 2.7 |
| lowest | 90% of reps ≥ 98% | 0/21 | — | — |
| lowest/3 | median ≥ 98% | 21/21 | 1.0–3.8 | 2.5 |
| lowest/3 | 90% of reps ≥ 98% | 21/21 | 2.0–4.0 | 3.0 |
| lowest/10 | median ≥ 98% | 21/21 | 1.0–3.0 | 1.0 |
| lowest/10 | 90% of reps ≥ 98% | 21/21 | 1.0–3.8 | 2.5 |
| min(lowest, prior) | median ≥ 98% | 21/21 | 1.0–4.0 | 1.0 |
| min(lowest, prior) | 90% of reps ≥ 98% | 12/21 | 1.0–1.0 | 1.0 |

### A4e. What the margin costs (n = 50)

Next to the in-sample oracle elim@98 for the same request (A1).

| model | request | oracle elim@98 | as-is: lowest | as-is: lowest/3 | as-is: lowest/10 | as-is: min(lowest, prior) | as-is: min(lowest, prior+R) | 20%: lowest | 20%: lowest/3 | 20%: lowest/10 | 20%: min(lowest, prior) | 20%: min(lowest, prior+R) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4b lp | 24-409 | 72% | 73% (0.51) | 36% (0.90) | 1% (1.00) | 62% (1.00) | 73% (0.51) | 87% (0.17) | 72% (0.48) | 29% (0.99) | 62% (1.00) | 87% (0.17) |
| 4b lp | 25-3152 | 29% | 35% (0.49) | 1% (0.80) | 0% (1.00) | 35% (0.49) | — | 70% (0.19) | 46% (0.39) | 4% (0.93) | 46% (0.19) | — |
| 4b lp | 25-3152+R | 75% | 76% (0.48) | 51% (0.99) | 8% (1.00) | 49% (1.00) | — | 83% (0.20) | 63% (0.79) | 34% (1.00) | 50% (1.00) | — |
| 9b lp | 24-409 | 76% | 77% (0.53) | 62% (0.94) | 35% (1.00) | 77% (0.53) | 77% (0.53) | 83% (0.20) | 72% (0.58) | 51% (0.93) | 83% (0.20) | 82% (0.20) |
| 9b lp | 25-3152 | 70% | 72% (0.49) | 54% (0.99) | 22% (1.00) | 57% (1.00) | — | 75% (0.20) | 60% (0.81) | 30% (1.00) | 57% (1.00) | — |
| 9b lp | 25-3152+R | 68% | 69% (0.48) | 51% (0.89) | 11% (1.00) | 59% (1.00) | — | 80% (0.19) | 67% (0.51) | 46% (0.90) | 59% (1.00) | — |
| 27b lp | 24-409 | 89% | 90% (0.50) | 82% (0.69) | 76% (0.93) | 76% (1.00) | 78% (1.00) | 97% (0.20) | 95% (0.29) | 89% (0.54) | 75% (1.00) | 78% (1.00) |
| 27b lp | 25-3152 | 74% | 74% (0.49) | 66% (0.84) | 62% (0.97) | 74% (0.49) | — | 85% (0.20) | 79% (0.44) | 71% (0.64) | 85% (0.20) | — |
| 27b lp | 25-3152+R | 91% | 92% (0.46) | 88% (0.79) | 81% (0.97) | 92% (0.46) | — | 94% (0.19) | 93% (0.39) | 85% (0.71) | 94% (0.19) | — |
| d3-4b | 24-409 | 63% | 63% (0.51) | 60% (0.99) | 52% (1.00) | 62% (0.51) | 63% (0.51) | 70% (0.18) | 63% (0.80) | 60% (1.00) | 63% (0.18) | 70% (0.18) |
| d3-4b | 25-3152 | 45% | 46% (0.50) | 5% (0.98) | 0% (1.00) | 43% (1.00) | — | 63% (0.20) | 32% (0.70) | 2% (0.99) | 44% (1.00) | — |
| d3-4b | 25-3152+R | 86% | 87% (0.49) | 79% (1.00) | 57% (1.00) | 64% (1.00) | — | 89% (0.19) | 83% (0.89) | 63% (0.99) | 64% (1.00) | — |
| d3-9b | 24-409 | 74% | 75% (0.50) | 61% (0.99) | 49% (1.00) | 75% (0.50) | 75% (0.50) | 84% (0.19) | 68% (0.75) | 57% (0.99) | 84% (0.19) | 84% (0.19) |
| d3-9b | 25-3152 | 74% | 75% (0.51) | 58% (1.00) | 5% (1.00) | 59% (1.00) | — | 80% (0.21) | 62% (0.88) | 17% (1.00) | 59% (1.00) | — |
| d3-9b | 25-3152+R | 90% | 91% (0.47) | 85% (1.00) | 72% (1.00) | 64% (1.00) | — | 94% (0.20) | 85% (0.92) | 74% (1.00) | 64% (1.00) | — |
| d3-27b | 24-409 | 91% | 93% (0.51) | 76% (0.95) | 68% (1.00) | 71% (1.00) | 93% (0.51) | 96% (0.19) | 88% (0.62) | 73% (0.93) | 72% (1.00) | 95% (0.19) |
| d3-27b | 25-3152 | 85% | 87% (0.47) | 76% (0.99) | 60% (1.00) | 87% (0.47) | — | 90% (0.19) | 77% (0.74) | 62% (0.95) | 90% (0.19) | — |
| d3-27b | 25-3152+R | 98% | 98% (0.51) | 97% (1.00) | 92% (1.00) | 97% (1.00) | — | 98% (0.18) | 97% (0.93) | 93% (0.99) | 97% (1.00) | — |
| Jev | 24-409 | 69% | 68% (0.63) | 59% (1.00) | 40% (1.00) | 60% (1.00) | 62% (1.00) | 75% (0.24) | 60% (0.91) | 51% (1.00) | 60% (1.00) | 63% (1.00) |
| Jev | 25-3152 | 58% | 61% (0.49) | 11% (1.00) | 0% (1.00) | 61% (0.49) | — | 67% (0.20) | 17% (0.90) | 0% (1.00) | 67% (0.20) | — |
| Jev | 25-3152+R | 83% | 84% (0.47) | 66% (1.00) | 11% (1.00) | 84% (0.47) | — | 90% (0.19) | 74% (0.88) | 32% (1.00) | 90% (0.19) | — |

Cell: median eliminated (share of repetitions with recall ≥ 98%).

**What the data shows**

- **`lowest` is a coin flip at n = 50, and worse at lower prevalence.** At the golden prevalence it
  reaches 98% recall on the remainder in 0.46–0.63 of repetitions, depending on model and request. At
  20% prevalence the range is 0.17–0.24 (A4c, appendix, A4e). The rate is nearly the same for every
  model, because the rule depends only on the order of the responsive emails' scores, not on their
  values. Theory predicts 0.44 for k = 29 and 0.18 for k = 10. Those are close to the mean k at n = 50:
  28.2–29.3 at the golden prevalence and 9.9–10.0 at 20% (A4a, A4b).
- **To make 98% recall likely (90% of repetitions), `lowest` needs about 114 responsive emails in the
  sample** (A4a). No n on the grid reaches that, in either design (A4d).
- **Margins restore recall, at a model-specific cost.** With `lowest/10` at n = 50, at least 0.93 of
  repetitions reach 98% for every model and request at the golden prevalence (A4e). At 20% prevalence,
  at least 0.90 do for every model except 27b lp (0.54, 0.64, 0.71). But elimination on 25-3152 at 20%
  falls to 4% for 4b lp, 2% for d3-4b and 0% for Jev. On that request almost none of their negatives
  score below 0.1 (2, 2 and 1 of 109), and 46–77 of the 109 score above the third-lowest positive. The
  margin pushes the cutoff below nearly all of the negatives. d3-27b keeps 73%, 62% and 93% (A4e).
  [corrected in verification: the original said "their negatives score just below their positives".
  In fact they overlap the positives and sit high in absolute terms. Counts from
  `a_cutoffs_verify.py` V13b]
- **27b lp is the hard case for sample rules.** Its responsive emails' scores span orders of magnitude
  (lowest 0.0079 on 25-3152, A1d), so a fixed odds margin is too small at small n (A4e).
- **`min(lowest, prior)` is only as good as its prior.** When the other request's thr98 is low enough,
  1.00 of repetitions reach 98%. When it isn't, the rule behaves like `lowest` (A4c).
- **Lower prevalence multiplies the needed n.** Going from the golden prevalence to 20%, the n needed
  for `lowest` to reach 98% in the median repetition rises by a factor of 2.0–4.0 (median 2.7). The n
  for `lowest/3` to reach 98% in 90% of repetitions rises by 2.0–4.0 (median 3.0) (A4d, "How much the
  20% design raises the needed n"). Ratios of 1.0 occur when both designs already pass at the smallest
  n tested (10).

**Interpretation.** A sample from the target request is the only label-based check this branch tests
that doesn't depend on another request. But a sample can certify recall only through the number of
responsive emails it contains. In a 20%-responsive pool, a sample with about 114 responsive emails
means reviewing several hundred emails. Below that, the margin is doing the work, and the right margin
is model-specific. A margin that protects 27b lp is far too wide for Jev on 25-3152.

## A5. Takeaway

### A5a. The 98% promise in sample and out of sample

Headline = cutoff fitted on all pairs of the setting (in-sample). The other columns aim at the same 98% recall without the target's labels. Misses are counts on 24-409 (144 positives) and on 25-3152 (140); 98% allows 2 on each. The `lowest` sample rule is shown at n = 50, 20% prevalence: the share of repetitions reaching 98% on each request.

| model | setting | headline elim@98 (in-sample) | headline cutoff: misses per request | per-request oracle elim@98 | previous request's thr98: misses | … eliminated | default 0.5: misses | sample `lowest`: P(≥98%) |
|---|---|---|---|---|---|---|---|---|
| 4b lp | no roster | 109/211 (52%) | 2, 3 | 72%, 29% | 0, 5 | 62%, 46% | 7, 7 | 0.17, 0.19 |
| 4b lp | roster | 147/211 (70%) | 4, 1 | 72%, 75% | 9, 0 | 87%, 50% | 7, 1 | 0.17, 0.20 |
| 9b lp | no roster | 149/211 (71%) | 5, 0 | 76%, 70% | 10, 0 | 83%, 57% | 12, 5 | 0.20, 0.20 |
| 9b lp | roster | 147/211 (70%) | 4, 1 | 76%, 68% | 6, 0 | 82%, 59% | 12, 5 | 0.20, 0.19 |
| 27b lp | no roster | 160/211 (76%) | 0, 5 | 89%, 74% | 0, 14 | 75%, 86% | 5, 15 | 0.20, 0.20 |
| 27b lp | roster | 185/211 (88%) | 0, 5 | 89%, 91% | 0, 15 | 78%, 94% | 5, 18 | 0.20, 0.19 |
| d3-4b | no roster | 113/211 (54%) | 3, 2 | 63%, 45% | 3, 2 | 63%, 44% | 9, 8 | 0.18, 0.20 |
| d3-4b | roster | 145/211 (69%) | 5, 0 | 63%, 86% | 76, 0 | 92%, 64% | 9, 0 | 0.18, 0.19 |
| d3-9b | no roster | 144/211 (68%) | 4, 1 | 74%, 74% | 17, 0 | 89%, 59% | 11, 2 | 0.19, 0.21 |
| d3-9b | roster | 157/211 (74%) | 5, 0 | 74%, 90% | 82, 0 | 100%, 64% | 11, 0 | 0.19, 0.20 |
| d3-27b | no roster | 171/211 (81%) | 0, 5 | 91%, 85% | 0, 31 | 72%, 96% | 0, 1 | 0.19, 0.19 |
| d3-27b | roster | 203/211 (96%) | 4, 1 | 91%, 98% | 6, 0 | 95%, 97% | 0, 0 | 0.19, 0.18 |
| Jev | no roster | 133/211 (63%) | 0, 5 | 69%, 58% | 0, 28 | 60%, 83% | 1, 17 | 0.24, 0.20 |
| Jev | roster | 158/211 (75%) | 1, 4 | 69%, 83% | 1, 10 | 63%, 90% | 1, 5 | 0.24, 0.19 |

### A5b. Best safe label-free policy, picked with hindsight

From the menu in the script docstring (6 fixed cutoffs, 3 previous-request cutoffs, 8 sample policies). Eliminated: per request, and combined (deterministic policies: k/N over both requests' negatives; sample policies: mean of the two medians). Gap = headline − best safe combined, in percentage points.

| model | setting | headline elim@98 | safe policies | default 0.5 (combined elim) | best safe policy (hindsight) | its elim per request | combined | detail | gap (pts) |
|---|---|---|---|---|---|---|---|---|---|
| 4b lp | no roster | 52% | 5/17 | not safe (misses 7, 7); 73% | fixed 0.2 | 57%, 26% | 41% | misses 0, 2 | +11 |
| 4b lp | roster | 70% | 6/17 | not safe (misses 7, 1); 74% | fixed 0.3 | 72%, 50% | 60% | misses 2, 0 | +9 |
| 9b lp | no roster | 71% | 5/17 | not safe (misses 12, 5); 80% | fixed 0.2 | 72%, 51% | 61% | misses 1, 0 | +9 |
| 9b lp | roster | 70% | 4/17 | not safe (misses 12, 5); 80% | fixed 0.2 | 72%, 53% | 62% | misses 1, 0 | +8 |
| 27b lp | no roster | 76% | 1/17 | not safe (misses 5, 15); 91% | fixed 0.05 | 75%, 72% | 73% | misses 0, 1 | +2 |
| 27b lp | roster | 88% | 1/17 | not safe (misses 5, 18); 95% | fixed 0.05 | 75%, 89% | 82% | misses 0, 0 | +6 |
| d3-4b | no roster | 54% | 9/17 | not safe (misses 9, 8); 64% | fixed 0.3 | 63%, 39% | 50% | misses 2, 1 | +3 |
| d3-4b | roster | 69% | 7/17 | not safe (misses 9, 0); 73% | sample n=100, lowest/3 | 61%, 78% | 69% | P(≥98%) 0.97, 0.99 | -1 |
| d3-9b | no roster | 68% | 7/17 | not safe (misses 11, 2); 79% | fixed 0.3 | 74%, 59% | 66% | misses 2, 0 | +2 |
| d3-9b | roster | 74% | 7/17 | not safe (misses 11, 0); 82% | sample n=100, lowest/3 | 62%, 85% | 74% | P(≥98%) 0.94, 0.99 | +1 |
| d3-27b | no roster | 81% | 8/17 | safe (misses 0, 1); 79% | fixed 0.5 | 72%, 85% | 79% | misses 0, 1 | +2 |
| d3-27b | roster | 96% | 8/17 | safe (misses 0, 0); 82% | sample n=50, lowest/10 | 73%, 93% | 83% | P(≥98%) 0.93, 0.99 | +14 |
| Jev | no roster | 63% | 7/17 | not safe (misses 1, 17); 73% | fixed 0.3 | 60%, 57% | 58% | misses 0, 2 | +5 |
| Jev | roster | 75% | 9/17 | not safe (misses 1, 5); 75% | fixed 0.4 | 60%, 81% | 71% | misses 0, 1 | +4 |

### A5c–d. Every safe policy

Combined eliminated share; policies sorted best first.

| model | safe policies (roster setting) |
|---|---|
| 4b lp | fixed 0.3 60%; fixed 0.2 45%; sample n=50, lowest/10 32%; fixed 0.1 13%; sample n=100, lowest/10 10%; fixed 0.05 1% |
| 9b lp | fixed 0.2 62%; fixed 0.1 42%; sample n=100, lowest/10 26%; fixed 0.05 24% |
| 27b lp | fixed 0.05 82% |
| d3-4b | sample n=100, lowest/3 69%; fixed 0.3 62%; sample n=50, lowest/10 62%; sample n=100, lowest/10 56%; fixed 0.2 56%; fixed 0.1 41%; fixed 0.05 25% |
| d3-9b | sample n=100, lowest/3 74%; fixed 0.3 68%; sample n=50, lowest/10 66%; sample n=100, lowest/10 63%; fixed 0.2 55%; fixed 0.1 31%; fixed 0.05 26% |
| d3-27b | sample n=50, lowest/10 83%; fixed 0.5 82%; sample n=100, lowest/10 81%; fixed 0.4 79%; fixed 0.3 76%; fixed 0.2 73%; fixed 0.1 67%; fixed 0.05 62% |
| Jev | fixed 0.4 71%; previous request's 100% cutoff 71%; fixed 0.3 67%; sample n=100, lowest/3 64%; fixed 0.2 56%; sample n=50, lowest/10 42%; sample n=100, lowest/10 30%; fixed 0.1 28%; fixed 0.05 1% |

| model | safe policies (no-roster setting) |
|---|---|
| 4b lp | fixed 0.2 41%; sample n=50, lowest/10 17%; fixed 0.1 11%; sample n=100, lowest/10 4%; fixed 0.05 1% |
| 9b lp | fixed 0.2 61%; fixed 0.1 44%; sample n=50, lowest/10 41%; sample n=100, lowest/10 32%; fixed 0.05 26% |
| 27b lp | fixed 0.05 73% |
| d3-4b | fixed 0.3 50%; previous request's 99% cutoff 46%; fixed 0.2 36%; sample n=100, lowest/3 35%; sample n=50, lowest/10 31%; previous request's 100% cutoff 31%; fixed 0.1 30%; sample n=100, lowest/10 29%; fixed 0.05 24% |
| d3-9b | fixed 0.3 66%; sample n=100, lowest/3 60%; fixed 0.2 50%; sample n=50, lowest/10 37%; fixed 0.1 29%; sample n=100, lowest/10 29%; fixed 0.05 25% |
| d3-27b | fixed 0.5 79%; fixed 0.4 74%; fixed 0.3 72%; sample n=50, lowest/10 67%; fixed 0.2 67%; sample n=100, lowest/10 66%; fixed 0.1 60%; fixed 0.05 56% |
| Jev | fixed 0.3 58%; fixed 0.2 40%; sample n=100, lowest/3 36%; sample n=50, lowest/10 25%; sample n=100, lowest/10 24%; fixed 0.1 17%; fixed 0.05 1% |

### A5e. A stated fixed-cutoff rule, and the gap to the headline

Cell: misses/positives · eliminated share, on 24-409; 25-3152; 25-3152+R. Both rows are fitted on these same labels (in-sample); A2d is the out-of-sample check of the same heuristic.

| model | largest safe value | at that value | one step lower | at one step lower |
|---|---|---|---|---|
| 4b lp | 0.2 | 0/144 · 57%; 2/140 · 26%; 0/140 · 34% | 0.1 | 0/144 · 22%; 0/140 · 2%; 0/140 · 6% |
| 9b lp | 0.2 | 1/144 · 72%; 0/140 · 51%; 0/140 · 53% | 0.1 | 0/144 · 60%; 0/140 · 29%; 0/140 · 25% |
| 27b lp | 0.05 | 0/144 · 75%; 1/140 · 72%; 0/140 · 89% | 0.02 | 0/144 · 68%; 1/140 · 65%; 0/140 · 84% |
| d3-4b | 0.3 | 2/144 · 63%; 1/140 · 39%; 0/140 · 61% | 0.2 | 1/144 · 61%; 1/140 · 12%; 0/140 · 51% |
| d3-9b | 0.3 | 2/144 · 74%; 0/140 · 59%; 0/140 · 63% | 0.2 | 0/144 · 66%; 0/140 · 36%; 0/140 · 46% |
| d3-27b | 0.5 | 0/144 · 72%; 1/140 · 85%; 0/140 · 93% | 0.4 | 0/144 · 69%; 0/140 · 79%; 0/140 · 89% |
| Jev | 0.3 | 0/144 · 60%; 2/140 · 57%; 0/140 · 74% | 0.2 | 0/144 · 54%; 0/140 · 27%; 0/140 · 58% |

Headline vs the one-step-lower cutoff, eliminated share over both requests' negatives (k/211), in-sample:

| model | cutoff | headline (no roster) | rule (no roster) | gap, pts | headline (roster) | rule (roster) | gap, pts |
|---|---|---|---|---|---|---|---|
| 4b lp | 0.1 | 109/211 (52%) | 24/211 (11%) | +40 | 147/211 (70%) | 28/211 (13%) | +56 |
| 9b lp | 0.1 | 149/211 (71%) | 93/211 (44%) | +27 | 147/211 (70%) | 88/211 (42%) | +28 |
| 27b lp | 0.02 | 160/211 (76%) | 140/211 (66%) | +9 | 185/211 (88%) | 161/211 (76%) | +11 |
| d3-4b | 0.2 | 113/211 (54%) | 75/211 (36%) | +18 | 145/211 (69%) | 118/211 (56%) | +13 |
| d3-9b | 0.2 | 144/211 (68%) | 106/211 (50%) | +18 | 157/211 (74%) | 117/211 (55%) | +19 |
| d3-27b | 0.4 | 171/211 (81%) | 156/211 (74%) | +7 | 203/211 (96%) | 167/211 (79%) | +17 |
| Jev | 0.2 | 133/211 (63%) | 84/211 (40%) | +23 | 158/211 (75%) | 118/211 (56%) | +19 |

**What the data shows**

- **On recall, the headline overstates what label-free policies deliver** (A5a). The headline promises
  98%. Its closest label-free analogs miss more. The previous request's thr98 misses up to 31 (no
  roster) or 82 (roster) on one request. The default 0.5 misses up to 17 (no roster) or 18 (roster). At
  n = 50 and 20% prevalence, the `lowest` sample rule reaches 98% in only 0.17–0.24 of repetitions.
- **On elimination, the gap depends on how much hindsight you allow.** The best safe policy, picked
  with hindsight from 17, lands between 1 point above and 14 points below the headline (A5b, "gap"
  column). A stated rule (the largest grid value safe on all labeled subsets, minus one step) misses at
  most 1 responsive email per request. It eliminates 7 to 40 points less than the headline without the
  roster, and 11 to 56 points less with it (A5e). Both are still fitted on these same two requests. The
  out-of-sample test of the same heuristic (A2d, one step) keeps 98% in only 2 or 3 of 4 directions.
- **27b lp has only one safe policy on the menu, fixed 0.05, in either setting** (A5c, A5d). d3-27b and
  Jev have the most safe options in the roster setting (8 and 9), and d3-27b's default 0.5 is one of
  them.

### Recommended cutoff policy per model (interpretation)

None of these policies is shown to be safe on a new request; two requests can't show that. If a model
is deployed, this is the policy the data best supports. Cells give misses/positives · eliminated share
on 24-409; 25-3152; 25-3152+R, from A5e (in-sample).

| model | policy | in-sample result | same heuristic out of sample (A2d, −1 step) | note |
|---|---|---|---|---|
| d3-27b | fixed 0.4 (the default 0.5 also holds) | 0/144 · 69%; 0/140 · 79%; 0/140 · 89% | 3/4 directions | the only model whose default holds on both requests (A3) |
| 27b lp | fixed 0.02 or lower | 0/144 · 68%; 1/140 · 65%; 0/140 · 84% | 2/4 | the two requests' cutoffs are 6.4× apart (A1b); one real responsive email scores 0.0079 |
| 9b lp | fixed 0.1 | 0/144 · 60%; 0/140 · 29%; 0/140 · 25% | 3/4 | |
| d3-9b | fixed 0.2 | 0/144 · 66%; 0/140 · 36%; 0/140 · 46% | 2/4 | the roster shifts its scores up (A1a), so a roster-prompt cutoff is too high for 24-409 |
| Jev | fixed 0.2 | 0/144 · 54%; 0/140 · 27%; 0/140 · 58% | 3/4 | |
| d3-4b | fixed 0.2 | 1/144 · 61%; 1/140 · 12%; 0/140 · 51% | 3/4 | same roster shift as d3-9b |
| 4b lp | fixed 0.1 | 0/144 · 22%; 0/140 · 2%; 0/140 · 6% | 3/4 | eliminates little at a safe cutoff |

The same policy applies to every model:

1. Fit a fixed cutoff per model **and per prompt** on every labeled request available. Then step down
   for headroom. Don't use one previous request (A2), and don't use 0.5 for any model except d3-27b
   (A3).
2. Use the stepped-down cutoff's elimination (A5e), not the headline elim@98, as the planning number.
   Branch B converts it to workload.
3. On each new request, also review a random sample. Lower the cutoff if any responsive email in the
   sample scores below it. Size the sample by how many responsive emails it has to contain (A4a, A4d).
   This catches gross failures, like the 82-miss transfer. It doesn't certify 98%.
4. Report the in-sample headline as an upper bound ("what a cutoff fitted with hindsight would
   eliminate").

## Findings

| # | finding | confidence | rests on |
|---|---|---|---|
| 1 | At the headline (pooled) cutoff, every model misses more than 2 responsive emails on one of the two requests (3–5 without the roster, 4–5 with it): below 98% on that request. This is partly arithmetic (5 pooled misses can't split as 2 + 2), but the misses also bunch up: all 5 fall on one request for 4 of 7 models (3 of 7 with the roster) | high | A1c |
| 2 | Each request needs a different cutoff: the ratio of the two cutoffs runs from 1.06 to 6.40, and the bootstrap intervals are disjoint for 27b lp, d3-27b and Jev | high for these two requests; medium as a general claim | A1a, A1b |
| 3 | Adding the roster moves the 25-3152 cutoff more than the change of request does for 4b lp and the three d3 models (d3-4b 0.3507 → 0.7588, d3-9b 0.5427 → 0.8529, d3-27b 0.5405 → 0.9133; log-odds shifts 1.50–2.19). It moves little for 9b lp (0.12) and 27b lp (0.35). A prompt change needs its own cutoff check | high | A1a, A1b |
| 4 | Reusing the other request's thr98 fails whenever the target needs a lower cutoff (by arithmetic, one of each pair of opposite directions). The failures are large: up to 31/140 misses without the roster and 82/144 with it. The 99% and 100% margins add a passing direction only for d3-4b and Jev | high | A2b, A2c |
| 5 | The default 0.5 keeps 98% recall on both requests only for d3-27b (0/144, 1/140; eliminates 72%, 85%). No JSON verdict run holds on 25-3152 | high | A3a, A3c |
| 6 | Each model has a fixed grid cutoff that holds on both requests, but it is found with hindsight and sits just below the point of failure. The same heuristic fitted on one request keeps 98% in only 2–3 of 4 directions with one step of headroom (2–4 of 4 with two steps) | medium | A3b, A2d |
| 7 | Setting the cutoff at the lowest-scoring responsive email in a random sample reaches 98% recall on the rest with probability about 1 − 0.98^k (k = responsive emails sampled), nearly the same for every model. At n = 50 that is 0.46–0.63 (golden prevalence) and 0.17–0.24 (20%). 90% assurance needs k ≈ 114 | high (theory matches simulation) | A4a, A4c, A4e |
| 8 | An odds margin of ÷10 at n = 50 gets ≥ 90% of repetitions to 98% recall for 6 of 7 models at 20% prevalence (not 27b lp), but eliminates 0–4% on 25-3152 for Jev, d3-4b and 4b lp | medium | A4e |
| 9 | Going from the golden set's prevalence to 20% multiplies the sample size needed by 2.0–4.0 (median 2.7 for `lowest`, median criterion; median 3.0 for `lowest/3`, 90% criterion) | medium | A4d |
| 10 | A stated label-free rule [disputed in verification: fitted in-sample; see concern 6] (largest safe grid value, minus one step) eliminates 7–56 points less than the headline. The best safe policy picked with hindsight comes within −1 to +14 points of it. The headline is an upper bound | medium | A5b, A5e |

## Caveats

- **Two requests.** Transfer has 4 directions over 2 requests, and two of those reuse the same 249
  pairs with and without the roster. That is far too few to estimate how cutoffs spread across requests.
  Every "safe on both requests" statement can fail on a third request.
- **Knife-edge counts.** 98% recall allows 2 misses per request, so one email moves a cell from pass to
  fail. Most "largest safe" cutoffs sit right at such an edge (A3b).
- **The golden pool isn't a keyword-search pool.** Its negatives are a designed mix of real emails
  produced for other requests and synthetic hard negatives. So the eliminated shares here measure
  difficulty, not workload. Branch B covers workload. Its positives include synthetic close calls,
  although the emails that set the cutoffs are mostly real (A1d).
- **The 20% design is an approximation.** It reweights prevalence. It reuses the same 140–144 positives,
  so large samples leave a small remainder: at n = 300, the 95th percentile of k is 71–72 (A4b), about
  half the positives. Elimination is measured on all negatives.
- **The margin rules weren't tuned,** and only odds margins were tried. A rank-based margin (say,
  "also review the next 5% of emails below the lowest responsive one") wasn't tested.
- **Hindsight in A5b and A5e.** Picking the best of 17 policies, or the largest safe grid value, after
  seeing both requests' outcomes is optimistic by construction.
- **In-sample prompt.** Prompt 2 was written after reading this set's misses (`findings-golden.md` §11).
- **One run per configuration.** Rerun noise in the scores isn't captured; the findings report notes
  that elim@98 moves several points between reruns.
- **One adjudicator.** Labels come from one person checking Opus pre-labels and verifier flags.
- **Recall on the remainder** leaves out the responsive emails found in the sample itself. Those are
  found by review, so overall recall would be slightly higher.
- **Jev scores are rounded to 2 decimals.** The resulting ties make its cutoffs move in steps of 0.01.

## Open questions

- How do cutoffs vary across more requests? A third and fourth labeled request, ideally of each type
  (topical and correspondent-scoped), would turn A2 into a real cross-validation.
- Would **score-stratified sampling** give more assurance per reviewed email than simple random
  sampling? So would an **elusion test**: a random sample from the eliminated pile, as in e-discovery
  practice.
- Does a **rank-based cutoff** transfer better than a raw score? For example, "flag the top X% of hits",
  or a margin defined as a share of the pool.
- How much do cutoffs move between reruns of the same configuration, and after future prompt changes?
- d3-27b's default works on both requests here. Is that because its scores are calibrated (a score of
  p means about p of such emails are responsive), or is it luck with two requests? Branch E covers
  calibration.

## Reproduce

From the project root (each finishes in a few seconds):

| command | prints |
|---|---|
| `uv run python scripts/analysis/a_cutoffs_oracle.py` | subsets; A1a–A1d |
| `uv run python scripts/analysis/a_cutoffs_transfer.py` | A2a (4 directions), A2b, A2c, A2d |
| `uv run python scripts/analysis/a_cutoffs_fixed.py` | A3a, A3b, A3c |
| `uv run python scripts/analysis/a_cutoffs_sample.py` | A4a–A4e (1,000 repetitions per cell; `--reps N` to change) |
| `uv run python scripts/analysis/a_cutoffs_summary.py` | A5a–A5e (reruns the A4 simulation) |
| `uv run python scripts/analysis/a_cutoffs_check.py` | self-checks: subset sizes; pooled thr98 and elim@98 equal `golden_report.stats` and the headline; `cutoff()` equals a brute-force scan; the fast simulation equals a slow recomputation; determinism |

| `uv run python scripts/analysis/a_cutoffs_verify.py` | the skeptic's independent recomputation, V1–V15 (see [Verification](#verification)); added in verification |

`scripts/analysis/a_cutoffs_common.py` holds the shared loader and helpers (not run directly).
Self-check output at the time of writing:

```
PASS 1 subset sizes and positives
PASS 2 pooled thr98 / elim@98 match golden_report.stats and the headline
PASS 3 cutoff() == brute force on 105 (model, subset, target) combinations
PASS 4 fast simulation == slow recomputation on 12 cells x 300 repetitions x all rules
PASS 5 run() deterministic
```

## Appendix: A2a, transfer per direction

### 24-409 → 25-3152

| model | source recall level | cutoff | target misses (recall) | of which real emails | ≥98% on target? | target eliminated | oracle elim@98 on target |
|---|---|---|---|---|---|---|---|
| 4b lp | 98% | 0.3002 | 5/140 (96.4%) | 4 | **no** | 50/109 (46%) | 32/109 (29%) |
| 4b lp | 99% | 0.2494 | 3/140 (97.9%) | 3 | **no** | 37/109 (34%) | 32/109 (29%) |
| 4b lp | 100% | 0.2373 | 3/140 (97.9%) | 3 | **no** | 35/109 (32%) | 32/109 (29%) |
| 9b lp | 98% | 0.2463 | 0/140 (100.0%) | 0 | yes | 62/109 (57%) | 76/109 (70%) |
| 9b lp | 99% | 0.2398 | 0/140 (100.0%) | 0 | yes | 62/109 (57%) | 76/109 (70%) |
| 9b lp | 100% | 0.1783 | 0/140 (100.0%) | 0 | yes | 54/109 (50%) | 76/109 (70%) |
| 27b lp | 98% | 0.3623 | 14/140 (90.0%) | 12 | **no** | 94/109 (86%) | 81/109 (74%) |
| 27b lp | 99% | 0.2663 | 11/140 (92.1%) | 10 | **no** | 93/109 (85%) | 81/109 (74%) |
| 27b lp | 100% | 0.2529 | 11/140 (92.1%) | 10 | **no** | 93/109 (85%) | 81/109 (74%) |
| d3-4b | 98% | 0.3323 | 2/140 (98.6%) | 2 | yes | 48/109 (44%) | 49/109 (45%) |
| d3-4b | 99% | 0.2608 | 1/140 (99.3%) | 1 | yes | 34/109 (31%) | 49/109 (45%) |
| d3-4b | 100% | 0.1076 | 0/140 (100.0%) | 0 | yes | 3/109 (3%) | 49/109 (45%) |
| d3-9b | 98% | 0.3051 | 0/140 (100.0%) | 0 | yes | 64/109 (59%) | 81/109 (74%) |
| d3-9b | 99% | 0.2745 | 0/140 (100.0%) | 0 | yes | 62/109 (57%) | 81/109 (74%) |
| d3-9b | 100% | 0.2598 | 0/140 (100.0%) | 0 | yes | 57/109 (52%) | 81/109 (74%) |
| d3-27b | 98% | 0.8542 | 31/140 (77.9%) | 25 | **no** | 105/109 (96%) | 93/109 (85%) |
| d3-27b | 99% | 0.7747 | 18/140 (87.1%) | 15 | **no** | 103/109 (94%) | 93/109 (85%) |
| d3-27b | 100% | 0.7504 | 15/140 (89.3%) | 12 | **no** | 101/109 (93%) | 93/109 (85%) |
| Jev | 98% | 0.5700 | 28/140 (80.0%) | 17 | **no** | 90/109 (83%) | 63/109 (58%) |
| Jev | 99% | 0.5100 | 19/140 (86.4%) | 15 | **no** | 88/109 (81%) | 63/109 (58%) |
| Jev | 100% | 0.4200 | 13/140 (90.7%) | 9 | **no** | 82/109 (75%) | 63/109 (58%) |

### 25-3152 → 24-409

| model | source recall level | cutoff | target misses (recall) | of which real emails | ≥98% on target? | target eliminated | oracle elim@98 on target |
|---|---|---|---|---|---|---|---|
| 4b lp | 98% | 0.2210 | 0/144 (100.0%) | 0 | yes | 63/102 (62%) | 73/102 (72%) |
| 4b lp | 99% | 0.1889 | 0/144 (100.0%) | 0 | yes | 56/102 (55%) | 73/102 (72%) |
| 4b lp | 100% | 0.1387 | 0/144 (100.0%) | 0 | yes | 41/102 (40%) | 73/102 (72%) |
| 9b lp | 98% | 0.4196 | 10/144 (93.1%) | 5 | **no** | 85/102 (83%) | 78/102 (76%) |
| 9b lp | 99% | 0.4047 | 8/144 (94.4%) | 5 | **no** | 85/102 (83%) | 78/102 (76%) |
| 9b lp | 100% | 0.3578 | 6/144 (95.8%) | 4 | **no** | 82/102 (80%) | 78/102 (76%) |
| 27b lp | 98% | 0.0566 | 0/144 (100.0%) | 0 | yes | 77/102 (75%) | 91/102 (89%) |
| 27b lp | 99% | 0.0501 | 0/144 (100.0%) | 0 | yes | 76/102 (75%) | 91/102 (89%) |
| 27b lp | 100% | 0.0079 | 0/144 (100.0%) | 0 | yes | 65/102 (64%) | 91/102 (89%) |
| d3-4b | 98% | 0.3507 | 3/144 (97.9%) | 2 | **no** | 64/102 (63%) | 64/102 (63%) |
| d3-4b | 99% | 0.3158 | 2/144 (98.6%) | 1 | yes | 64/102 (63%) | 64/102 (63%) |
| d3-4b | 100% | 0.1904 | 1/144 (99.3%) | 1 | yes | 62/102 (61%) | 64/102 (63%) |
| d3-9b | 98% | 0.5427 | 17/144 (88.2%) | 7 | **no** | 91/102 (89%) | 75/102 (74%) |
| d3-9b | 99% | 0.4725 | 10/144 (93.1%) | 5 | **no** | 86/102 (84%) | 75/102 (74%) |
| d3-9b | 100% | 0.3177 | 3/144 (97.9%) | 2 | **no** | 76/102 (75%) | 75/102 (74%) |
| d3-27b | 98% | 0.5405 | 0/144 (100.0%) | 0 | yes | 73/102 (72%) | 93/102 (91%) |
| d3-27b | 99% | 0.5095 | 0/144 (100.0%) | 0 | yes | 73/102 (72%) | 93/102 (91%) |
| d3-27b | 100% | 0.4870 | 0/144 (100.0%) | 0 | yes | 73/102 (72%) | 93/102 (91%) |
| Jev | 98% | 0.3100 | 0/144 (100.0%) | 0 | yes | 61/102 (60%) | 70/102 (69%) |
| Jev | 99% | 0.2900 | 0/144 (100.0%) | 0 | yes | 61/102 (60%) | 70/102 (69%) |
| Jev | 100% | 0.2200 | 0/144 (100.0%) | 0 | yes | 56/102 (55%) | 70/102 (69%) |

### 24-409 → 25-3152+R

| model | source recall level | cutoff | target misses (recall) | of which real emails | ≥98% on target? | target eliminated | oracle elim@98 on target |
|---|---|---|---|---|---|---|---|
| 4b lp | 98% | 0.3002 | 0/140 (100.0%) | 0 | yes | 54/109 (50%) | 82/109 (75%) |
| 4b lp | 99% | 0.2494 | 0/140 (100.0%) | 0 | yes | 46/109 (42%) | 82/109 (75%) |
| 4b lp | 100% | 0.2373 | 0/140 (100.0%) | 0 | yes | 43/109 (39%) | 82/109 (75%) |
| 9b lp | 98% | 0.2463 | 0/140 (100.0%) | 0 | yes | 64/109 (59%) | 74/109 (68%) |
| 9b lp | 99% | 0.2398 | 0/140 (100.0%) | 0 | yes | 63/109 (58%) | 74/109 (68%) |
| 9b lp | 100% | 0.1783 | 0/140 (100.0%) | 0 | yes | 53/109 (49%) | 74/109 (68%) |
| 27b lp | 98% | 0.3623 | 15/140 (89.3%) | 10 | **no** | 103/109 (94%) | 99/109 (91%) |
| 27b lp | 99% | 0.2663 | 11/140 (92.1%) | 7 | **no** | 102/109 (94%) | 99/109 (91%) |
| 27b lp | 100% | 0.2529 | 10/140 (92.9%) | 7 | **no** | 102/109 (94%) | 99/109 (91%) |
| d3-4b | 98% | 0.3323 | 0/140 (100.0%) | 0 | yes | 70/109 (64%) | 94/109 (86%) |
| d3-4b | 99% | 0.2608 | 0/140 (100.0%) | 0 | yes | 64/109 (59%) | 94/109 (86%) |
| d3-4b | 100% | 0.1076 | 0/140 (100.0%) | 0 | yes | 30/109 (28%) | 94/109 (86%) |
| d3-9b | 98% | 0.3051 | 0/140 (100.0%) | 0 | yes | 70/109 (64%) | 98/109 (90%) |
| d3-9b | 99% | 0.2745 | 0/140 (100.0%) | 0 | yes | 65/109 (60%) | 98/109 (90%) |
| d3-9b | 100% | 0.2598 | 0/140 (100.0%) | 0 | yes | 65/109 (60%) | 98/109 (90%) |
| d3-27b | 98% | 0.8542 | 0/140 (100.0%) | 0 | yes | 106/109 (97%) | 107/109 (98%) |
| d3-27b | 99% | 0.7747 | 0/140 (100.0%) | 0 | yes | 106/109 (97%) | 107/109 (98%) |
| d3-27b | 100% | 0.7504 | 0/140 (100.0%) | 0 | yes | 105/109 (96%) | 107/109 (98%) |
| Jev | 98% | 0.5700 | 10/140 (92.9%) | 6 | **no** | 98/109 (90%) | 91/109 (83%) |
| Jev | 99% | 0.5100 | 5/140 (96.4%) | 5 | **no** | 93/109 (85%) | 91/109 (83%) |
| Jev | 100% | 0.4200 | 1/140 (99.3%) | 1 | yes | 88/109 (81%) | 91/109 (83%) |

### 25-3152+R → 24-409

| model | source recall level | cutoff | target misses (recall) | of which real emails | ≥98% on target? | target eliminated | oracle elim@98 on target |
|---|---|---|---|---|---|---|---|
| 4b lp | 98% | 0.5606 | 9/144 (93.8%) | 7 | **no** | 89/102 (87%) | 73/102 (72%) |
| 4b lp | 99% | 0.5066 | 7/144 (95.1%) | 5 | **no** | 85/102 (83%) | 73/102 (72%) |
| 4b lp | 100% | 0.3626 | 3/144 (97.9%) | 3 | **no** | 76/102 (75%) | 73/102 (72%) |
| 9b lp | 98% | 0.3901 | 6/144 (95.8%) | 4 | **no** | 84/102 (82%) | 78/102 (76%) |
| 9b lp | 99% | 0.3744 | 6/144 (95.8%) | 4 | **no** | 83/102 (81%) | 78/102 (76%) |
| 9b lp | 100% | 0.2743 | 3/144 (97.9%) | 1 | **no** | 79/102 (77%) | 78/102 (76%) |
| 27b lp | 98% | 0.0783 | 0/144 (100.0%) | 0 | yes | 80/102 (78%) | 91/102 (89%) |
| 27b lp | 99% | 0.0779 | 0/144 (100.0%) | 0 | yes | 80/102 (78%) | 91/102 (89%) |
| 27b lp | 100% | 0.0730 | 0/144 (100.0%) | 0 | yes | 79/102 (77%) | 91/102 (89%) |
| d3-4b | 98% | 0.7588 | 76/144 (47.2%) | 40 | **no** | 94/102 (92%) | 64/102 (63%) |
| d3-4b | 99% | 0.7578 | 76/144 (47.2%) | 40 | **no** | 94/102 (92%) | 64/102 (63%) |
| d3-4b | 100% | 0.7520 | 76/144 (47.2%) | 40 | **no** | 94/102 (92%) | 64/102 (63%) |
| d3-9b | 98% | 0.8529 | 82/144 (43.1%) | 40 | **no** | 102/102 (100%) | 75/102 (74%) |
| d3-9b | 99% | 0.8423 | 79/144 (45.1%) | 40 | **no** | 102/102 (100%) | 75/102 (74%) |
| d3-9b | 100% | 0.8311 | 78/144 (45.8%) | 39 | **no** | 102/102 (100%) | 75/102 (74%) |
| d3-27b | 98% | 0.9133 | 6/144 (95.8%) | 4 | **no** | 97/102 (95%) | 93/102 (91%) |
| d3-27b | 99% | 0.9060 | 5/144 (96.5%) | 3 | **no** | 96/102 (94%) | 93/102 (91%) |
| d3-27b | 100% | 0.8794 | 4/144 (97.2%) | 2 | **no** | 96/102 (94%) | 93/102 (91%) |
| Jev | 98% | 0.4600 | 1/144 (99.3%) | 1 | yes | 64/102 (63%) | 70/102 (69%) |
| Jev | 99% | 0.4500 | 1/144 (99.3%) | 1 | yes | 64/102 (63%) | 70/102 (69%) |
| Jev | 100% | 0.3900 | 0/144 (100.0%) | 0 | yes | 61/102 (60%) | 70/102 (69%) |

## Appendix: A4c at 20% prevalence

#### 24-409

| model | n | lowest | lowest/3 | lowest/10 | min(lowest, prior) | min(lowest, prior+R) |
|---|---|---|---|---|---|---|
| 4b lp | 20 | 84.8% / 35.7% · ≤91 · 92% / 62% · 0.09 | 97.1% / 87.9% · ≤17 · 78% / 22% · 0.23 | 100.0% / 97.2% · ≤4 · 52% / 0% · 0.83 | 100.0% / 100.0% · ≤0 · 62% / 62% · 1.00 | 93.6% / 93.5% · ≤9 · 87% / 62% · 0.09 |
| 4b lp | 50 | 93.3% / 70.1% · ≤41 · 87% / 62% · 0.17 | 97.8% / 94.2% · ≤8 · 72% / 19% · 0.48 | 100.0% / 98.5% · ≤2 · 29% / 0% · 0.99 | 100.0% / 100.0% · ≤0 · 62% / 62% · 1.00 | 93.5% / 93.1% · ≤9 · 87% / 62% · 0.17 |
| 4b lp | 100 | 96.8% / 83.6% · ≤21 · 78% / 62% · 0.36 | 100.0% / 96.7% · ≤4 · 57% / 19% · 0.77 | 100.0% / 100.0% · ≤0 · 8% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 62% / 62% · 1.00 | 96.8% / 92.6% · ≤9 · 78% / 62% · 0.36 |
| 9b lp | 20 | 84.2% / 36.2% · ≤91 · 91% / 76% · 0.09 | 95.6% / 74.6% · ≤36 · 81% / 60% · 0.32 | 100.0% / 91.4% · ≤12 · 70% / 32% · 0.66 | 92.9% / 92.8% · ≤10 · 83% / 76% · 0.09 | 95.7% / 95.6% · ≤6 · 82% / 76% · 0.09 |
| 9b lp | 50 | 93.2% / 71.0% · ≤40 · 83% / 71% · 0.20 | 99.2% / 89.0% · ≤15 · 72% / 51% · 0.58 | 100.0% / 97.8% · ≤3 · 51% / 22% · 0.93 | 93.2% / 92.4% · ≤10 · 83% / 71% · 0.20 | 95.6% / 95.4% · ≤6 · 82% / 71% · 0.20 |
| 9b lp | 100 | 96.9% / 84.4% · ≤20 · 78% / 71% · 0.40 | 100.0% / 95.2% · ≤6 · 70% / 51% · 0.84 | 100.0% / 100.0% · ≤0 · 38% / 22% · 1.00 | 96.9% / 91.9% · ≤10 · 78% / 71% · 0.40 | 96.9% / 95.0% · ≤6 · 78% / 71% · 0.40 |
| 27b lp | 20 | 85.5% / 36.4% · ≤90 · 99% / 86% · 0.09 | 89.9% / 59.4% · ≤58 · 99% / 78% · 0.14 | 95.7% / 75.7% · ≤34 · 95% / 72% · 0.29 | 100.0% / 100.0% · ≤0 · 75% / 75% · 1.00 | 100.0% / 100.0% · ≤0 · 78% / 78% · 1.00 |
| 27b lp | 50 | 93.2% / 70.2% · ≤40 · 97% / 86% · 0.20 | 96.2% / 78.6% · ≤29 · 95% / 78% · 0.29 | 98.5% / 87.5% · ≤17 · 89% / 72% · 0.54 | 100.0% / 100.0% · ≤0 · 75% / 75% · 1.00 | 100.0% / 100.0% · ≤0 · 78% / 78% · 1.00 |
| 27b lp | 100 | 96.8% / 85.7% · ≤18 · 93% / 86% · 0.38 | 100.0% / 90.4% · ≤12 · 84% / 78% · 0.52 | 100.0% / 95.9% · ≤5 · 78% / 72% · 0.82 | 100.0% / 100.0% · ≤0 · 75% / 75% · 1.00 | 100.0% / 100.0% · ≤0 · 78% / 78% · 1.00 |
| d3-4b | 20 | 83.9% / 34.8% · ≤92 · 77% / 63% · 0.08 | 97.9% / 87.9% · ≤17 · 63% / 60% · 0.49 | 99.3% / 98.6% · ≤2 · 61% / 34% · 0.97 | 97.9% / 97.8% · ≤3 · 63% / 63% · 0.08 | 83.9% / 46.5% · ≤76 · 77% / 63% · 0.08 |
| d3-4b | 50 | 93.2% / 68.7% · ≤43 · 70% / 60% · 0.18 | 98.6% / 97.7% · ≤3 · 63% / 36% · 0.80 | 100.0% / 99.2% · ≤1 · 60% / 1% · 1.00 | 97.8% / 97.7% · ≤3 · 63% / 60% · 0.18 | 93.2% / 68.7% · ≤43 · 70% / 60% · 0.18 |
| d3-4b | 100 | 96.7% / 85.8% · ≤18 · 63% / 60% · 0.37 | 99.2% / 98.3% · ≤2 · 61% / 36% · 0.97 | 100.0% / 99.2% · ≤1 · 56% / 1% · 1.00 | 97.7% / 97.5% · ≤3 · 63% / 60% · 0.37 | 96.7% / 85.8% · ≤18 · 63% / 60% · 0.37 |
| d3-9b | 20 | 84.3% / 36.6% · ≤90 · 90% / 71% · 0.09 | 97.8% / 72.5% · ≤39 · 75% / 59% · 0.43 | 100.0% / 95.0% · ≤7 · 60% / 42% · 0.89 | 88.0% / 87.7% · ≤17 · 89% / 71% · 0.09 | 84.3% / 42.7% · ≤82 · 90% / 71% · 0.09 |
| d3-9b | 50 | 93.2% / 70.1% · ≤41 · 84% / 70% · 0.19 | 100.0% / 92.9% · ≤10 · 68% / 57% · 0.75 | 100.0% / 100.0% · ≤0 · 57% / 40% · 0.99 | 93.2% / 87.2% · ≤17 · 84% / 70% · 0.19 | 93.2% / 70.1% · ≤41 · 84% / 70% · 0.19 |
| d3-9b | 100 | 96.7% / 84.6% · ≤20 · 76% / 70% · 0.38 | 100.0% / 97.7% · ≤3 · 62% / 57% · 0.94 | 100.0% / 100.0% · ≤0 · 52% / 40% · 1.00 | 96.7% / 86.6% · ≤17 · 76% / 70% · 0.38 | 96.7% / 84.6% · ≤20 · 76% / 70% · 0.38 |
| d3-27b | 20 | 84.8% / 37.1% · ≤89 · 99% / 82% · 0.09 | 96.4% / 60.7% · ≤55 · 94% / 72% · 0.34 | 100.0% / 82.3% · ≤25 · 80% / 66% · 0.68 | 100.0% / 100.0% · ≤0 · 72% / 72% · 1.00 | 95.7% / 95.6% · ≤6 · 95% / 82% · 0.09 |
| d3-27b | 50 | 93.2% / 70.3% · ≤41 · 96% / 80% · 0.19 | 98.5% / 87.3% · ≤18 · 88% / 72% · 0.62 | 100.0% / 97.8% · ≤3 · 73% / 66% · 0.93 | 100.0% / 100.0% · ≤0 · 72% / 72% · 1.00 | 95.6% / 95.4% · ≤6 · 95% / 80% · 0.19 |
| d3-27b | 100 | 96.7% / 86.0% · ≤18 · 94% / 80% · 0.37 | 100.0% / 96.2% · ≤5 · 80% / 72% · 0.89 | 100.0% / 100.0% · ≤0 · 70% / 66% · 1.00 | 100.0% / 100.0% · ≤0 · 72% / 72% · 1.00 | 96.7% / 95.0% · ≤6 · 94% / 80% · 0.37 |
| Jev | 20 | 85.0% / 34.8% · ≤92 · 83% / 66% · 0.12 | 99.3% / 75.2% · ≤35 · 65% / 59% · 0.67 | 100.0% / 98.6% · ≤2 · 57% / 34% · 0.96 | 100.0% / 100.0% · ≤0 · 60% / 60% · 1.00 | 99.3% / 99.3% · ≤1 · 63% / 63% · 1.00 |
| Jev | 50 | 92.6% / 68.9% · ≤42 · 75% / 61% · 0.24 | 100.0% / 97.0% · ≤4 · 60% / 54% · 0.91 | 100.0% / 100.0% · ≤0 · 51% / 19% · 1.00 | 100.0% / 100.0% · ≤0 · 60% / 60% · 1.00 | 99.3% / 99.2% · ≤1 · 63% / 61% · 1.00 |
| Jev | 100 | 96.7% / 86.8% · ≤16 · 71% / 61% · 0.44 | 100.0% / 99.2% · ≤1 · 60% / 54% · 1.00 | 100.0% / 100.0% · ≤0 · 47% / 19% · 1.00 | 100.0% / 100.0% · ≤0 · 60% / 60% · 1.00 | 99.2% / 99.2% · ≤1 · 63% / 61% · 1.00 |

#### 25-3152

| model | n | lowest | lowest/3 | lowest/10 | min(lowest, prior) |
|---|---|---|---|---|---|
| 4b lp | 20 | 83.1% / 32.1% · ≤94 · 81% / 23% · 0.09 | 95.0% / 81.2% · ≤26 · 61% / 0% · 0.18 | 99.3% / 95.6% · ≤6 · 22% / 0% · 0.64 | 96.4% / 96.2% · ≤5 · 46% / 23% · 0.09 |
| 4b lp | 50 | 93.0% / 69.9% · ≤39 · 70% / 9% · 0.19 | 96.2% / 94.5% · ≤7 · 46% / 0% · 0.39 | 100.0% / 97.7% · ≤3 · 4% / 0% · 0.93 | 96.2% / 96.0% · ≤5 · 46% / 9% · 0.19 |
| 4b lp | 100 | 96.7% / 84.6% · ≤19 · 40% / 9% · 0.39 | 100.0% / 95.1% · ≤6 · 4% / 0% · 0.68 | 100.0% / 99.2% · ≤1 · 0% / 0% · 0.99 | 96.7% / 95.7% · ≤5 · 40% / 9% · 0.39 |
| 9b lp | 20 | 83.2% / 33.8% · ≤92 · 85% / 67% · 0.07 | 97.8% / 74.6% · ≤35 · 71% / 50% · 0.48 | 100.0% / 96.4% · ≤5 · 50% / 16% · 0.88 | 100.0% / 100.0% · ≤0 · 57% / 57% · 1.00 |
| 9b lp | 50 | 93.0% / 69.5% · ≤40 · 75% / 63% · 0.20 | 100.0% / 91.9% · ≤11 · 60% / 46% · 0.81 | 100.0% / 100.0% · ≤0 · 30% / 13% · 1.00 | 100.0% / 100.0% · ≤0 · 57% / 57% · 1.00 |
| 9b lp | 100 | 96.6% / 85.2% · ≤18 · 74% / 63% · 0.36 | 100.0% / 99.2% · ≤1 · 57% / 46% · 0.97 | 100.0% / 100.0% · ≤0 · 27% / 13% · 1.00 | 100.0% / 100.0% · ≤0 · 57% / 57% · 1.00 |
| 27b lp | 20 | 83.3% / 33.8% · ≤90 · 92% / 72% · 0.08 | 89.6% / 44.9% · ≤75 · 87% / 65% · 0.23 | 93.5% / 57.7% · ≤58 · 84% / 62% · 0.35 | 89.9% / 89.6% · ≤14 · 86% / 72% · 0.08 |
| 27b lp | 50 | 92.7% / 69.4% · ≤40 · 85% / 62% · 0.20 | 94.7% / 83.1% · ≤22 · 79% / 58% · 0.44 | 99.2% / 89.4% · ≤14 · 71% / 49% · 0.64 | 92.7% / 89.1% · ≤14 · 85% / 62% · 0.20 |
| 27b lp | 100 | 96.7% / 84.9% · ≤18 · 75% / 62% · 0.36 | 99.2% / 90.1% · ≤12 · 66% / 58% · 0.71 | 100.0% / 93.3% · ≤8 · 62% / 49% · 0.89 | 96.7% / 88.5% · ≤14 · 75% / 62% · 0.36 |
| d3-4b | 20 | 82.6% / 34.3% · ≤92 · 84% / 40% · 0.08 | 94.2% / 81.8% · ≤30 · 60% / 4% · 0.38 | 99.3% / 94.2% · ≤8 · 17% / 0% · 0.87 | 98.5% / 98.5% · ≤2 · 44% / 40% · 1.00 |
| d3-4b | 50 | 93.7% / 69.2% · ≤41 · 63% / 10% · 0.20 | 99.2% / 91.9% · ≤11 · 32% / 2% · 0.70 | 100.0% / 99.2% · ≤1 · 2% / 0% · 0.99 | 98.5% / 98.4% · ≤2 · 44% / 10% · 1.00 |
| d3-4b | 100 | 96.7% / 83.5% · ≤20 · 53% / 10% · 0.38 | 100.0% / 94.2% · ≤7 · 8% / 2% · 0.92 | 100.0% / 99.2% · ≤1 · 2% / 0% · 1.00 | 98.4% / 98.2% · ≤2 · 44% / 10% · 1.00 |
| d3-9b | 20 | 83.1% / 33.3% · ≤92 · 91% / 71% · 0.09 | 98.5% / 83.1% · ≤23 · 72% / 44% · 0.55 | 100.0% / 98.6% · ≤2 · 49% / 1% · 0.98 | 100.0% / 100.0% · ≤0 · 59% / 59% · 1.00 |
| d3-9b | 50 | 93.0% / 69.8% · ≤41 · 80% / 60% · 0.21 | 99.2% / 96.2% · ≤5 · 62% / 11% · 0.88 | 100.0% / 100.0% · ≤0 · 17% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 59% / 59% · 1.00 |
| d3-9b | 100 | 96.7% / 85.3% · ≤18 · 76% / 60% · 0.38 | 100.0% / 98.4% · ≤2 · 59% / 11% · 0.98 | 100.0% / 100.0% · ≤0 · 6% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 59% / 59% · 1.00 |
| d3-27b | 20 | 84.8% / 33.3% · ≤92 · 94% / 85% · 0.09 | 97.1% / 56.8% · ≤60 · 87% / 74% · 0.46 | 100.0% / 76.1% · ≤33 · 74% / 58% · 0.72 | 84.8% / 77.0% · ≤31 · 94% / 85% · 0.09 |
| d3-27b | 50 | 93.0% / 69.9% · ≤40 · 90% / 85% · 0.19 | 100.0% / 82.6% · ≤23 · 77% / 74% · 0.74 | 100.0% / 98.5% · ≤2 · 62% / 56% · 0.95 | 93.0% / 76.6% · ≤31 · 90% / 85% · 0.19 |
| d3-27b | 100 | 96.6% / 84.7% · ≤19 · 89% / 85% · 0.38 | 100.0% / 96.9% · ≤4 · 76% / 74% · 0.95 | 100.0% / 100.0% · ≤0 · 61% / 56% · 1.00 | 96.6% / 84.7% · ≤19 · 89% / 85% · 0.38 |
| Jev | 20 | 84.7% / 37.2% · ≤86 · 81% / 57% · 0.10 | 99.3% / 78.7% · ≤29 · 57% / 6% · 0.60 | 100.0% / 98.5% · ≤2 · 2% / 0% · 0.95 | 84.7% / 79.3% · ≤28 · 81% / 57% · 0.10 |
| Jev | 50 | 93.8% / 74.8% · ≤32 · 67% / 32% · 0.20 | 100.0% / 93.7% · ≤8 · 17% / 0% · 0.90 | 100.0% / 100.0% · ≤0 · 0% / 0% · 1.00 | 93.8% / 78.8% · ≤28 · 67% / 32% · 0.20 |
| Jev | 100 | 97.5% / 85.0% · ≤19 · 63% / 32% · 0.36 | 100.0% / 99.2% · ≤1 · 13% / 0% · 0.99 | 100.0% / 100.0% · ≤0 · 0% / 0% · 1.00 | 97.5% / 85.0% · ≤19 · 63% / 32% · 0.36 |

#### 25-3152+R

| model | n | lowest | lowest/3 | lowest/10 | min(lowest, prior) |
|---|---|---|---|---|---|
| 4b lp | 20 | 82.4% / 31.2% · ≤95 · 91% / 68% · 0.09 | 97.8% / 79.4% · ≤29 · 75% / 43% · 0.47 | 100.0% / 97.1% · ≤4 · 48% / 4% · 0.94 | 100.0% / 100.0% · ≤0 · 50% / 50% · 1.00 |
| 4b lp | 50 | 93.1% / 69.7% · ≤41 · 83% / 59% · 0.20 | 99.2% / 94.7% · ≤7 · 63% / 19% · 0.79 | 100.0% / 100.0% · ≤0 · 34% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 50% / 50% · 1.00 |
| 4b lp | 100 | 96.7% / 84.2% · ≤19 · 78% / 59% · 0.39 | 100.0% / 98.3% · ≤2 · 57% / 19% · 0.96 | 100.0% / 100.0% · ≤0 · 13% / 0% · 1.00 | 100.0% / 100.0% · ≤0 · 50% / 50% · 1.00 |
| 9b lp | 20 | 83.0% / 31.7% · ≤94 · 94% / 67% · 0.09 | 93.4% / 69.3% · ≤42 · 80% / 48% · 0.27 | 99.3% / 92.6% · ≤10 · 63% / 9% · 0.60 | 100.0% / 100.0% · ≤0 · 59% / 59% · 1.00 |
| 9b lp | 50 | 93.0% / 69.1% · ≤41 · 80% / 59% · 0.19 | 99.2% / 91.1% · ≤12 · 67% / 31% · 0.51 | 100.0% / 96.2% · ≤5 · 46% / 3% · 0.90 | 100.0% / 100.0% · ≤0 · 59% / 59% · 1.00 |
| 9b lp | 100 | 96.7% / 85.1% · ≤18 · 70% / 59% · 0.38 | 100.0% / 93.4% · ≤8 · 53% / 31% · 0.79 | 100.0% / 99.2% · ≤1 · 14% / 3% · 1.00 | 100.0% / 100.0% · ≤0 · 59% / 59% · 1.00 |
| 27b lp | 20 | 84.2% / 32.1% · ≤93 · 96% / 91% · 0.11 | 90.2% / 48.2% · ≤71 · 94% / 85% · 0.20 | 97.1% / 60.9% · ≤54 · 93% / 78% · 0.42 | 89.1% / 88.8% · ≤15 · 94% / 91% · 0.11 |
| 27b lp | 50 | 93.0% / 69.7% · ≤40 · 94% / 90% · 0.19 | 97.7% / 74.8% · ≤34 · 93% / 85% · 0.39 | 100.0% / 81.9% · ≤24 · 85% / 77% · 0.71 | 93.0% / 88.3% · ≤15 · 94% / 90% · 0.19 |
| 27b lp | 100 | 96.6% / 85.5% · ≤18 · 93% / 90% · 0.34 | 100.0% / 92.2% · ≤10 · 89% / 85% · 0.67 | 100.0% / 97.5% · ≤3 · 84% / 77% · 0.94 | 96.6% / 87.8% · ≤15 · 93% / 90% · 0.34 |
| d3-4b | 20 | 83.9% / 35.5% · ≤89 · 92% / 86% · 0.08 | 100.0% / 75.9% · ≤33 · 84% / 78% · 0.61 | 100.0% / 94.9% · ≤7 · 73% / 56% · 0.88 | 100.0% / 100.0% · ≤0 · 64% / 64% · 1.00 |
| d3-4b | 50 | 93.1% / 68.2% · ≤42 · 89% / 84% · 0.19 | 100.0% / 83.8% · ≤21 · 83% / 77% · 0.89 | 100.0% / 100.0% · ≤0 · 63% / 56% · 0.99 | 100.0% / 100.0% · ≤0 · 64% / 64% · 1.00 |
| d3-4b | 100 | 96.7% / 83.9% · ≤20 · 87% / 84% · 0.38 | 100.0% / 100.0% · ≤0 · 78% / 77% · 0.99 | 100.0% / 100.0% · ≤0 · 57% / 56% · 1.00 | 100.0% / 100.0% · ≤0 · 64% / 64% · 1.00 |
| d3-9b | 20 | 83.8% / 36.2% · ≤88 · 96% / 90% · 0.07 | 100.0% / 74.6% · ≤35 · 88% / 84% · 0.66 | 100.0% / 99.3% · ≤1 · 80% / 70% · 0.97 | 100.0% / 100.0% · ≤0 · 64% / 64% · 1.00 |
| d3-9b | 50 | 93.1% / 68.9% · ≤42 · 94% / 89% · 0.20 | 100.0% / 96.3% · ≤5 · 85% / 82% · 0.92 | 100.0% / 100.0% · ≤0 · 74% / 69% · 1.00 | 100.0% / 100.0% · ≤0 · 64% / 64% · 1.00 |
| d3-9b | 100 | 96.6% / 83.1% · ≤21 · 92% / 89% · 0.34 | 100.0% / 100.0% · ≤0 · 85% / 82% · 0.99 | 100.0% / 100.0% · ≤0 · 73% / 69% · 1.00 | 100.0% / 100.0% · ≤0 · 64% / 64% · 1.00 |
| d3-27b | 20 | 85.3% / 37.2% · ≤87 · 99% / 98% · 0.08 | 100.0% / 65.0% · ≤48 · 97% / 97% · 0.68 | 100.0% / 89.9% · ≤14 · 94% / 93% · 0.85 | 100.0% / 100.0% · ≤0 · 97% / 97% · 1.00 |
| d3-27b | 50 | 92.9% / 70.8% · ≤38 · 98% / 98% · 0.18 | 100.0% / 96.1% · ≤5 · 97% / 95% · 0.93 | 100.0% / 100.0% · ≤0 · 93% / 90% · 0.99 | 100.0% / 100.0% · ≤0 · 97% / 97% · 1.00 |
| d3-27b | 100 | 96.7% / 85.7% · ≤17 · 98% / 98% · 0.40 | 100.0% / 100.0% · ≤0 · 97% / 95% · 1.00 | 100.0% / 100.0% · ≤0 · 93% / 90% · 1.00 | 100.0% / 100.0% · ≤0 · 97% / 97% · 1.00 |
| Jev | 20 | 83.5% / 37.0% · ≤87 · 94% / 83% · 0.09 | 99.3% / 76.1% · ≤33 · 81% / 61% · 0.58 | 100.0% / 99.3% · ≤1 · 56% / 6% · 0.96 | 92.7% / 92.5% · ≤10 · 90% / 83% · 0.09 |
| Jev | 50 | 92.3% / 70.5% · ≤39 · 90% / 80% · 0.19 | 100.0% / 92.5% · ≤10 · 74% / 56% · 0.88 | 100.0% / 100.0% · ≤0 · 32% / 4% · 1.00 | 92.6% / 92.1% · ≤10 · 90% / 80% · 0.19 |
| Jev | 100 | 96.5% / 85.0% · ≤18 · 84% / 80% · 0.34 | 100.0% / 100.0% · ≤0 · 69% / 56% · 0.99 | 100.0% / 100.0% · ≤0 · 13% / 4% · 1.00 | 96.5% / 91.5% · ≤10 · 84% / 80% · 0.34 |

## Verification

Skeptic's pass, 2026-11-06. Script: `uv run python scripts/analysis/a_cutoffs_verify.py` (stdlib,
deterministic, a few seconds). It doesn't import the analyst's `a_cutoffs_*.py` scripts or the repo
helpers (`analyze.py`, `golden_report.py`). It reads `pairs.jsonl` and the `scores.jsonl` files itself and
computes thr98 as an order statistic: the (m+1)-th lowest positive score, where m is the number of misses
allowed. AUROC is computed as Mann–Whitney and elimination from scratch. It computes the A4 sample rules
exactly instead of by simulation. Its sections are cited below as V1–V15.

### Checks and results

| # | check | result |
|---|---|---|
| 1 | Re-ran all six analyst scripts; compared every table row in this file with their output, block by block and under the matching heading | **Confirmed.** All data tables reproduce verbatim. `a_cutoffs_check.py` PASS 1–5. The hand-written tables (runs, recommendations, findings) agree with the tables they cite |
| 2 | Headline (brief): pooled AUROC, elim@98 and median wall ms, recomputed from scratch | **Confirmed** for all 7 models: 0.923/52%, 0.942/71%, 0.975/76%, 0.884/54%, 0.947/68%, 0.979/81%, 0.916/63%; 504, 856, 2649, 877, 1426, 4667, 117 ms (V2) |
| 3 | thr98 for all 35 model × subset cells (A1a point estimates) | **Confirmed** (V3) |
| 4 | A1a bootstrap intervals were actually computed | **Confirmed.** Redrawn with my own seeds and 2,000 resamples, the endpoints agree to a few thousandths (27b lp 25-3152: [0.0079–0.0954] vs [0.0079–0.1030]). The three disjoint pairs stay disjoint (V15) |
| 5 | A1c: misses per request at the pooled cutoff; "all 5 on one request" for 4/7 and 3/7 | **Confirmed** (V4) |
| 6 | A2b/A2c transfer: misses, eliminated share and pass counts at the 98% and 100% levels, plus the real-email counts in the appendix | **Confirmed** (V7) |
| 7 | A3: 0.5 default per model, JSON verdicts, largest safe grid value, 5 null JSON rows | **Confirmed** (V8) |
| 8 | A4 `lowest` at n = 50: "0.46–0.63" (golden prevalence) and "0.17–0.24" (20%) | **Confirmed within simulation error.** Exact values: 0.496 on 24-409 and 0.491 on 25-3152 for every model except Jev; Jev on 24-409 is 0.600, because of ties. At 20% prevalence: 0.194/0.200, and Jev on 24-409 0.251 (V9). At 1,000 repetitions the simulation noise is about ±0.03 |
| 9 | A4 `lowest/10` at 20%, n = 50: 27b lp 0.54/0.64/0.71, others ≥ 0.90; median elimination on 25-3152 of 4%, 2%, 0% (4b lp, d3-4b, Jev) and 73%/62%/93% for d3-27b | **Confirmed** exactly: 0.549/0.648/0.719; the lowest other model is 0.903 (9b lp, 25-3152+R); 4%, 2%, 0%; 73%, 62%, 93% (V9) |
| 10 | A5e: largest safe values, one-step-lower cutoffs, at most 1 miss per request, gaps of 7–40 and 11–56 points | **Confirmed** (V10) |
| 11 | Labels come from `pairs.jsonl`, not `scores.jsonl` | **Confirmed** in the loader. In these 26 runs the copies in `scores.jsonl` agree with `pairs.jsonl` anyway (0 stale labels or kinds), so this rule changes no number here. No pair_id falls outside the golden set, and there are no duplicate pair_ids (V1) |
| 12 | Right runs; roster comparisons over the same pairs | **Confirmed.** Only the brief's runs are used. 25-3152+R has exactly the 249 pair_ids of 25-3152, and pooled+R = 24-409 from the main run + 25-3152+R (V1) |
| 13 | Threshold direction and denominators | **Confirmed.** A pair is flagged when score ≥ cutoff everywhere, and my independent code agrees. Denominators are 144/102, 140/109 and 284/211. JSON denominators shrink by the dropped null rows (e.g. 27b json: 107 negatives on 25-3152, 139 positives on 25-3152+R) |
| 14 | Ties (Jev) | Jev has 68–80 distinct scores per request. At thr98, 1–2 positives and 1–4 negatives tie with the cutoff, and all of them are flagged. Ties account for Jev's higher `lowest` rate on 24-409 (V9, V11) |
| 15 | "Not an artifact of the synthetic emails" | **Supported, and more strongly than the md showed.** With synthetic positives removed (75 real positives per request), the gap remains: 27b lp 0.4843 vs 0.0501, d3-27b 0.8542 vs 0.5095, Jev 0.51 vs 0.31 (V14). The md's original evidence (slot counts) was weaker; see correction 2 |
| 16 | "Because the roster raised their 25-3152 scores" (A2) | **Supported.** On the same pairs, the median positive score rises from 0.849 to 0.972 (d3-4b) and from 0.878 to 0.973 (d3-9b) (V13a) |

### Corrections made in this file

1. **A3, 27b lp at 0.05.** The text credited 25-3152's second-lowest positive (0.0501). With 2 misses
   allowed, the email that decides it is the third-lowest (0.0566). At 0.0565, 2 are missed and the cutoff
   still holds; at 0.0567, 3 are missed (V6). Fixed in place. The analyst's summary (key finding 6)
   repeats the error.
2. **A1d, "49 of the 63 lowest-scoring positives" and "18 of the 21".** These count entries, and the
   same email recurs across models and in the roster twin. Distinct emails: 24 of 35 are real, and 16 of
   19 at thr98 (base rate: 52–54% of positives are real). Fixed in the text and in
   `a_cutoffs_oracle.py`, whose A1d line now prints both counts. The rest of that script's output is
   unchanged (checked with diff).
3. **A4, "their negatives score just below their positives".** The data show the opposite. On 25-3152,
   46–77 of 109 negatives score above the third-lowest positive for 4b lp, d3-4b and Jev, and only
   1–2 of 109 score below 0.1. Elimination collapses because the margin cutoff falls below nearly all
   negatives (V13b). Fixed in place.
4. **Data and method, citation.** The recommendation to supply the roster is `findings-golden.md` §12,
   item 4. §6 only reports the ablation. Fixed in place.

### Remaining concerns (numbers unaffected; conclusions to read with care)

1. **The headline-cutoff shortfall is wholly arithmetic, not "partly".** Every one of the 14 runs uses
   all 5 pooled misses, so some request must take 3 or more. "Every model misses more than 2 on one
   request" (Short answer, Finding 1) follows from that alone. The informative part is the bunching. If
   the 5 misses fell at random among the 284 positives, all 5 would land on one request with
   probability 0.060, or 0.42 of 7 models expected. 4 of 7 and 3 of 7 are observed (V4). The models
   share emails, so this is not an independent test, but the bunching looks real.
2. **Other statements that hold by construction:**
   - A transfer that keeps recall can never eliminate more than the target's own oracle cutoff does
     (true in every case, V7). So "when transfer keeps recall, it gives up elimination" is forced; only
     its size carries information.
   - The largest safe grid value always sits within one grid step of the failure point. So "but only
     just" in A3b is a property of the grid.
   - The 20% design changes only the number of responsive emails in the sample. The needed n should
     therefore scale by the prevalence ratio, 2.81–2.93 (V12). The reported 2.0–4.0 (median 2.7 or 3.0)
     is that ratio rounded by the coarse n grid. It is not a finding about the models.
3. **"Each request needs a different cutoff" (Finding 2) overgeneralizes.** d3-4b's two cutoffs are
   0.3323 and 0.3507. A direct bootstrap of their difference gives −0.08 [−1.56, +1.09] in log-odds,
   and the 4b lp interval also includes 0 (V5). Checking whether two intervals overlap is also a
   conservative test. Testing the difference directly also separates 9b lp: −0.79 [−1.45, −0.08],
   though only nominally. Its two-sided p of 0.023 would not survive a Bonferroni correction for the 14
   comparisons (threshold 0.05/14). d3-9b is borderline at [−1.40, +0.06], p = 0.067. Without the roster, the gap is clear for 3 models (27b lp, d3-27b,
   Jev), nominal for 1 (9b lp), and absent or unclear for 3. Percentile bootstraps of an extreme order
   statistic (the third-lowest of about 140) are also rough, because they can only land on observed
   low scores.
4. **Per-model variation in A4 `lowest` is simulation noise.** The exact rate is the same for every
   model without ties (V9). "Depending on model and request" in A4 overstates the variation. At the
   golden prevalence, the observed ~0.49 sits above the Beta(1, k) theory (0.44 at k = 29) because the
   sample takes about 29 of only 144 or 140 positives (mean k 29.3 and 28.2, A4b): the population of
   positives is finite. So "about 114 responsive emails for 90%"
   is a large-pool figure.
5. **The 20% design is not the brief's "positives subsampled".** It keeps all 140–144 positives as the
   population and draws k ~ Binomial(n, 0.2). A literal subsample to 20% that keeps all negatives
   keeps 26 positives (24-409) or 27 (25-3152). Then 98% recall allows 0 misses (V12), and the results
   would look worse. The analyst's choice
   models a large pool better and is disclosed, but it is a modeling choice.
6. **"Label-free" is used loosely.** The A5e rule, called a "stated label-free rule" in Finding 10 and
   the Short answer, is fitted on the same two requests' labels. It is label-free only for a future
   request. The 7–56 point gap measures the cost of a coarser in-sample rule with headroom, including
   the stricter per-request recall target (the headline only needs 98% pooled). It is not an
   out-of-sample estimate. The only out-of-sample evidence here is A2/A2d, where the heuristic held in
   2–3 of 4 directions. A5's bullets say so, but the Short answer and the Findings table don't.
7. **d3-27b at 0.5 is the one pre-specified cutoff that held on both requests.** But it was singled out
   after seeing 7 models. It holds with 1/140 missed, and it fails above 0.5405 on 25-3152. The
   recommendation "d3-27b 0.4 (or the default 0.5)" rests on two requests.
8. **JSON verdicts are a knife-edge fail.** 27b json with the roster misses 3/139 on 25-3152+R, one
   email short of 98%. On pooled+R it meets 98% (5/283 missed) and eliminates 192/211 (91%) (A3c, V8).
9. **Attributions that two requests can't support.** "The two requests differ in kind (topical vs
   correspondent-scoped)" and "a cutoff belongs to a combination of model, prompt and request type"
   can't separate the request type from the particular request: there is one request of each type.
   Another explanation goes unexamined. The lowest-scoring real positives are emails the county
   produced, and some may have been produced more broadly than the request required. That is a label
   question (one adjudicator), not a model question.
10. **Analyst's summary (not this file).** Key finding 4 says the 82/144 d3-9b misses are "most of them
    real emails". 40 of the 82 are real (49%), near the 52% base rate (V7). Of the other large failures,
    Jev's 28 misses include 17 real (61%). Only 27b lp (12/14) and d3-27b (25/31) clearly exceed the
    base rate. This file itself states only the d3-27b and Jev counts, and those are correct.

**Verdict:** sound with corrections. The numbers reproduce, and an independent implementation of
the core metrics agrees. Four factual statements were fixed. The main conclusions hold: transfer
fails large, only d3-27b's default holds, a small sample can't certify 98%, and the headline is an
upper bound. Several framing points above should temper how they're read.
