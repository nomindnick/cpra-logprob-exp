# D. Real vs synthetic emails, generalization, and a limitations register

> **Snapshot of 2026-11-06, on the 2026-10-31 labels (495 pairs).** The labels changed afterwards: five hard
> negatives were relabeled responsive on 2026-11-08, and one email (24-409 synthetic 07:09) was put back in the set
> on 2026-11-11 (`docs/findings-golden.md` §9). The tables below are copies of script output on the old labels.
> Rerun the commands in the Reproduce section for current numbers; the scripts now read the pair counts from the
> golden set (`scripts/analysis/golden_counts.py`). `docs/findings-golden.md` carries the current figures, and
> `conclusions.md` section 0 lists what the relabeling changed.

**Date:** 2026-11-06 · **Branch:** D of the golden-set analysis (A cutoffs, B workload, C misses, D validity, E comparisons)
**Scripts:** `scripts/analysis/d_validity_*.py` (stdlib only, fixed seeds; commands in [Reproduce](#reproduce)). Every table below is pasted from their output.
**Inputs:** the saved golden-set runs and `data/golden/`. No model, GPU or network calls were made.

## The question

How much of the golden-set results comes from the synthetic emails? Which part of the set best approximates a
real deployment, and what can't this experiment show?

## Short answer

What the data shows:

- **The real negatives aren't what a screen would see in practice.** All 120 were produced for other requests.
  118 of them fall outside the target request's date window, and none contains the target's search terms (by
  the keyword proxy defined below). A date-limited keyword search would not return them. Yet they make up
  70–90% of the negatives each score model clears at its 98%-recall cutoff (D1-7, D2-2).
- **On real emails alone, the task is nearly solved.** Real positives vs real negatives: AUROC 0.982–1.000 and
  71–100% of negatives eliminated (96–100% for the 9b lp, 27b lp, d3-9b and d3-27b). Most of the difficulty sits
  in the synthetic hard negatives. The synthetic positives score about like the real ones (D1, D2-8).
- **Against hard negatives a date-limited search could return** (subset f), the share eliminated at 98% recall is
  15–45%, against 52–81% in the headline. On that subset the 9b lp, 27b lp and d3-27b are level (45%, 42%, 41%).
  d3-27b's headline lead over 27b lp comes mostly from wrong-date emails (D1-2, D1-7, D1-8).
- **The two requests behave differently.** The stock Qwen models do worse on the correspondent-scoped request,
  the 4b most (4b lp AUROC 0.964 vs 0.883; 27b lp 0.992 vs 0.955). The d3 models and Jev show no clear gap. The
  model ranking agrees only weakly between the two requests (Kendall tau 0.43). The roster helps every model on
  25-3152 (D3).

Interpretation (judgment): the headline numbers describe this test set, not a deployment. A conservative proxy
for elimination in deployment is real positives against in-window hard negatives (subset f), with the headline as
an optimistic upper bound. Two requests are too few to estimate how much results vary from one request to the
next.

An independent check of these numbers is at the end, in [Verification](#verification). It lists the
corrections, the claims that hold only in part, and the concerns that remain.

## Data and method

**Runs** (prompt 2, Ollama 0.40.13 on the Strix Halo unless noted; each has a `_roster` twin with 249 pairs, 25-3152 only):

| label | run directory | score |
|---|---|---|
| 4b lp, 9b lp, 27b lp | `golden_qwen3.5_4b_logprob_p2db`, `golden_qwen3.5_9b_logprob_p2db`, `golden_qwen3.8_27b_logprob_p2` | first-token P(yes)/(P(yes)+P(no)), stock Qwen Q4_K_M |
| d3-4b, d3-9b, d3-27b | `golden_d3-ctx8k_{4b,9b,27b}_noul_p2` | the d3 decision model's P(yes) via Ollama `/v1/systemone`, Q8_0 |
| Jev | `golden_jev-1.14.0_noul_p2` | P(yes) from TypeSafe's API, rounded to 2 decimals |
| 4b/9b/27b json, jsonR | `golden_qwen3.5_{4b,9b}_json_p2`, `golden_qwen3.8_27b_json_p2`, `..._json_reason_p2` | confidence if the verdict is yes, else 1 − confidence (contrast only) |

**Pairs and labels.** 495 (request, email) pairs from `data/golden/pairs.jsonl`. Label, kind and recipe always
come from `pairs.jsonl`, joined on `pair_id`, as in `golden_report.py load_runs()`. Rows with no score are
dropped (the JSON parse failures):

- 27b json (golden_qwen3.8_27b_json_p2): 2 unscored row(s) dropped: 25-3152|synth:25-3152:15:09 (hard_negative), 25-3152|synth:25-3152:16:01 (hard_negative)
- 9b jsonR (golden_qwen3.5_9b_json_reason_p2): 1 unscored row(s) dropped: 25-3152|synth:25-3152:20:06 (privileged_positive)
- 27b jsonR (golden_qwen3.8_27b_json_reason_p2): 1 unscored row(s) dropped: 25-3152|synth:25-3152:16:05 (hard_negative)
- 27b json roster run (golden_qwen3.8_27b_json_p2_roster): 1 unscored row dropped: 25-3152|synth:25-3152:12:03
  (close_call_positive). That's why D3-4 compares the 27b json over 246 pairs. Five unscored rows in all
  (`d_validity_verify.py` V0). [corrected in verification]

Two other run sets appear in one register row each: the prompt-1 reruns (row 7) and second runs of the same
model (row 9). Both are named in `d_validity_limits.py`.

**Definitions.**

- *Responsive / positive* = label 1. A pair is *flagged* when score ≥ cutoff.
- *Recall* = share of positives flagged.
- *thr98* = the highest cutoff with recall ≥ 98% (`at_recall(pr_curve(...), 0.98)`).
- *elim@98* = share of negatives scoring below thr98. That is the non-responsive mail a reviewer would not have to
  read. In every subset table, thr98 is chosen inside that subset.
- *AUROC* = the probability that a random positive outscores a random negative (ties count half). 0.5 is chance,
  1.0 is perfect ordering.
- *Bootstrap CI* = 95% percentile interval over 1,000 resamples. Resampling is stratified by label, and every run
  gets the same resampled pairs (paired); fixed seeds.
- *Kendall tau* = agreement between two rankings of the seven score models. +1 = same order, 0 = unrelated.
- *P(best)* = share of bootstrap resamples in which a model has the top value.

**Subsets** (D1). "real+" = the 150 `real_positive` emails (the county's production). "all+" = all 284 positives,
including the 4 `hard_negative_flipped`. "real−" = the 120 `real_negative`. "hard−" = the 91 `hard_negative`.
Subset (f) is my addition: real+ vs the 71 hard negatives other than `same_subject_wrong_date`. Those 71 are
exactly the hard negatives dated inside the request's window (D2-3, recipe table), so they are the ones a
date-limited search could return.

**Keyword-search proxy** (D2; my construction, because the county's actual search terms aren't published):

- **24-409:** any of the refinement's terms, matched in the subject, body, attachment names or address headers:
  Hinds, Lerner, urban studies, USP, global policy, GPS, UCSD / UC San Diego, water equity, RWER, RDF,
  decarbonization framework, Geosyntec, Murakawa. Acronyms are case-sensitive.
- **25-3152:** the group's name (Alpine Community Planning Group, ACPG, Alpine CPG / planning group, alpinecpg) or
  any roster member's name or email address.
- **Check:** the proxy finds 147 of the 150 real positives (D2-3), so it roughly tracks what the productions
  contain.
- *In window* = the email's date is within the request's date range: 24-409 2023-01-01..2023-07-31;
  25-3152 2024-01-01..2025-05-31.

## D1. How much of the result comes from synthetic emails

| subset | pairs | positives | negatives | misses allowed at 98% recall |
|---|---|---|---|---|
| (a) real+ vs real− | 270 | 150 | 120 | 3 |
| (b) real+ vs hard− | 241 | 150 | 91 | 3 |
| (c) all+ vs real− | 404 | 284 | 120 | 5 |
| (d) all+ vs hard− | 375 | 284 | 91 | 5 |
| (e) everything | 495 | 284 | 211 | 5 |
| (f) real+ vs in-window hard− | 221 | 150 | 71 | 3 |

### AUROC by subset [95% CI]

| run | (a) real+ vs real− | (b) real+ vs hard− | (c) all+ vs real− | (d) all+ vs hard− | (e) everything | (f) real+ vs in-window hard− |
|---|---|---|---|---|---|---|
| 4b lp | 0.982 [0.968–0.994] | 0.827 [0.770–0.878] | 0.989 [0.981–0.995] | 0.836 [0.783–0.882] | 0.923 [0.898–0.947] | 0.842 [0.784–0.894] |
| 9b lp | 0.997 [0.994–1.000] | 0.860 [0.813–0.906] | 0.997 [0.994–0.999] | 0.870 [0.827–0.909] | 0.942 [0.922–0.962] | 0.889 [0.840–0.930] |
| 27b lp | 1.000 [1.000–1.000] | 0.933 [0.901–0.960] | 1.000 [1.000–1.000] | 0.943 [0.915–0.964] | 0.975 [0.963–0.985] | 0.925 [0.888–0.956] |
| d3-4b | 0.987 [0.975–0.996] | 0.718 [0.652–0.783] | 0.991 [0.983–0.996] | 0.744 [0.685–0.800] | 0.884 [0.853–0.915] | 0.703 [0.625–0.776] |
| d3-9b | 0.999 [0.998–1.000] | 0.874 [0.824–0.917] | 0.999 [0.998–1.000] | 0.878 [0.834–0.916] | 0.947 [0.927–0.965] | 0.865 [0.811–0.912] |
| d3-27b | 1.000 [1.000–1.000] | 0.935 [0.902–0.960] | 1.000 [1.000–1.000] | 0.952 [0.931–0.969] | 0.979 [0.970–0.987] | 0.923 [0.887–0.954] |
| Jev | 0.992 [0.986–0.998] | 0.782 [0.724–0.836] | 0.995 [0.990–0.998] | 0.813 [0.768–0.858] | 0.916 [0.890–0.939] | 0.821 [0.762–0.875] |
| 4b json | 0.935 [0.906–0.961] | 0.665 [0.604–0.722] | 0.950 [0.930–0.968] | 0.678 [0.620–0.735] | 0.833 [0.798–0.865] | 0.718 [0.652–0.779] |
| 9b json | 0.911 [0.878–0.942] | 0.781 [0.723–0.838] | 0.927 [0.906–0.947] | 0.798 [0.744–0.844] | 0.871 [0.840–0.903] | 0.811 [0.752–0.865] |
| 27b json | 0.982 [0.970–0.992] | 0.881 [0.839–0.920] | 0.988 [0.980–0.994] | 0.891 [0.851–0.925] | 0.947 [0.927–0.964] | 0.868 [0.820–0.912] |
| 4b jsonR | 0.949 [0.922–0.974] | 0.748 [0.685–0.808] | 0.958 [0.939–0.974] | 0.755 [0.695–0.812] | 0.870 [0.838–0.901] | 0.782 [0.712–0.846] |
| 9b jsonR | 0.966 [0.946–0.986] | 0.761 [0.699–0.820] | 0.969 [0.952–0.985] | 0.760 [0.700–0.819] | 0.879 [0.847–0.910] | 0.777 [0.706–0.837] |
| 27b jsonR | 0.990 [0.977–0.998] | 0.877 [0.837–0.912] | 0.994 [0.988–0.999] | 0.894 [0.862–0.922] | 0.951 [0.935–0.966] | 0.851 [0.805–0.895] |

### Eliminated at 98% recall, cutoff chosen within the subset: share (k/n) [95% CI]

| run | (a) real+ vs real− | (b) real+ vs hard− | (c) all+ vs real− | (d) all+ vs hard− | (e) everything | (f) real+ vs in-window hard− |
|---|---|---|---|---|---|---|
| 4b lp | 71% (85/120) [51%–96%] | 14% (13/91) [8%–35%] | 79% (95/120) [62%–97%] | 15% (14/91) [9%–40%] | 52% (109/211) [41%–72%] | 18% (13/71) [10%–46%] |
| 9b lp | 96% (115/120) [92%–99%] | 37% (34/91) [27%–54%] | 96% (115/120) [92%–99%] | 37% (34/91) [26%–52%] | 71% (149/211) [64%–79%] | 45% (32/71) [32%–65%] |
| 27b lp | 100% (120/120) [100%–100%] | 44% (40/91) [31%–67%] | 100% (120/120) [100%–100%] | 44% (40/91) [34%–71%] | 76% (160/211) [71%–88%] | 42% (30/71) [28%–65%] |
| d3-4b | 84% (101/120) [50%–94%] | 12% (11/91) [3%–20%] | 85% (102/120) [70%–95%] | 12% (11/91) [5%–19%] | 54% (113/211) [42%–63%] | 15% (11/71) [6%–24%] |
| d3-9b | 99% (119/120) [96%–100%] | 27% (25/91) [14%–59%] | 99% (119/120) [98%–100%] | 27% (25/91) [18%–52%] | 68% (144/211) [62%–79%] | 31% (22/71) [15%–59%] |
| d3-27b | 100% (120/120) [100%–100%] | 51% (46/91) [41%–65%] | 100% (120/120) [100%–100%] | 56% (51/91) [44%–67%] | 81% (171/211) [75%–86%] | 41% (29/71) [31%–58%] |
| Jev | 91% (109/120) [82%–97%] | 23% (21/91) [13%–34%] | 92% (110/120) [84%–97%] | 25% (23/91) [15%–34%] | 63% (133/211) [55%–69%] | 28% (20/71) [17%–41%] |
| 4b json | 16% (19/120) [8%–22%] | 1% (1/91) [0%–3%] | 16% (19/120) [10%–22%] | 1% (1/91) [0%–3%] | 9% (20/211) [6%–13%] | 1% (1/71) [0%–4%] |
| 9b json | 0% (0/120) [0%–0%] | 0% (0/91) [0%–0%] | 0% (0/120) [0%–0%] | 0% (0/91) [0%–0%] | 0% (0/211) [0%–0%] | 0% (0/71) [0%–0%] |
| 27b json | 47% (56/120) [38%–56%] | 2% (2/89) [0%–6%] | 47% (56/120) [38%–57%] | 2% (2/89) [0%–7%] | 28% (58/209) [22%–36%] | 3% (2/70) [0%–7%] |
| 4b jsonR | 0% (0/120) [0%–0%] | 0% (0/91) [0%–0%] | 0% (0/120) [0%–0%] | 0% (0/91) [0%–0%] | 0% (0/211) [0%–0%] | 0% (0/71) [0%–0%] |
| 9b jsonR | 0% (0/120) [0%–94%] | 0% (0/91) [0%–43%] | 0% (0/120) [0%–93%] | 0% (0/91) [0%–36%] | 0% (0/211) [0%–70%] | 0% (0/71) [0%–45%] |
| 27b jsonR | 91% (109/120) [0%–96%] | 33% (30/90) [0%–43%] | 91% (109/120) [84%–96%] | 33% (30/90) [22%–44%] | 66% (139/210) [58%–72%] | 23% (16/71) [0%–34%] |

Positives set the 98% cutoff: thr98 is the same in (a), (b) and (f), and the same in (c), (d) and (e). So
moving between those subsets changes only which negatives are counted:

| run | (a) real+ vs real− | (b) real+ vs hard− | (c) all+ vs real− | (d) all+ vs hard− | (e) everything | (f) real+ vs in-window hard− |
|---|---|---|---|---|---|---|
| 4b lp | 0.2373 (3/150) | 0.2373 (3/150) | 0.265 (5/284) | 0.265 (5/284) | 0.265 (5/284) | 0.2373 (3/150) |
| 9b lp | 0.3309 (3/150) | 0.3309 (3/150) | 0.3309 (5/284) | 0.3309 (5/284) | 0.3309 (5/284) | 0.3309 (3/150) |
| 27b lp | 0.06213 (3/150) | 0.06213 (3/150) | 0.06874 (5/284) | 0.06874 (5/284) | 0.06874 (5/284) | 0.06213 (3/150) |
| d3-4b | 0.3323 (3/150) | 0.3323 (3/150) | 0.3507 (5/284) | 0.3507 (5/284) | 0.3507 (5/284) | 0.3323 (3/150) |
| d3-9b | 0.3379 (3/150) | 0.3379 (3/150) | 0.3379 (5/284) | 0.3379 (5/284) | 0.3379 (5/284) | 0.3379 (3/150) |
| d3-27b | 0.5415 (3/150) | 0.5415 (3/150) | 0.5857 (5/284) | 0.5857 (5/284) | 0.5857 (5/284) | 0.5415 (3/150) |
| Jev | 0.33 (2/150) | 0.33 (2/150) | 0.34 (5/284) | 0.34 (5/284) | 0.34 (5/284) | 0.33 (2/150) |
| 4b json | 0.05 (1/150) | 0.05 (1/150) | 0.05 (1/284) | 0.05 (1/284) | 0.05 (1/284) | 0.05 (1/150) |
| 9b json | 0 (0/150) | 0 (0/150) | 0 (0/284) | 0 (0/284) | 0 (0/284) | 0 (0/150) |
| 27b json | 0.05 (0/150) | 0.05 (0/150) | 0.05 (0/284) | 0.05 (0/284) | 0.05 (0/284) | 0.05 (0/150) |
| 4b jsonR | 0 (0/150) | 0 (0/150) | 0 (0/284) | 0 (0/284) | 0 (0/284) | 0 (0/150) |
| 9b jsonR | 0 (0/150) | 0 (0/150) | 0 (0/283) | 0 (0/283) | 0 (0/283) | 0 (0/150) |
| 27b jsonR | 0.05 (2/150) | 0.05 (2/150) | 0.05 (2/284) | 0.05 (2/284) | 0.05 (2/284) | 0.05 (2/150) |

### Where the headline elimination comes from

| run | all-pairs thr98 | elim@98 (all) | real− cleared | hard− cleared |   of which wrong-date |   of which in-window | share of cleared that are real− |
|---|---|---|---|---|---|---|---|
| 4b lp | 0.265 | 52% (109/211) | 95/120 (79%) | 14/91 (15%) | 0/20 | 14/71 (20%) | 87% |
| 9b lp | 0.3309 | 71% (149/211) | 115/120 (96%) | 34/91 (37%) | 2/20 | 32/71 (45%) | 77% |
| 27b lp | 0.06874 | 76% (160/211) | 120/120 (100%) | 40/91 (44%) | 10/20 | 30/71 (42%) | 75% |
| d3-4b | 0.3507 | 54% (113/211) | 102/120 (85%) | 11/91 (12%) | 0/20 | 11/71 (15%) | 90% |
| d3-9b | 0.3379 | 68% (144/211) | 119/120 (99%) | 25/91 (27%) | 3/20 | 22/71 (31%) | 83% |
| d3-27b | 0.5857 | 81% (171/211) | 120/120 (100%) | 51/91 (56%) | 17/20 | 34/71 (48%) | 70% |
| Jev | 0.34 | 63% (133/211) | 110/120 (92%) | 23/91 (25%) | 1/20 | 22/71 (31%) | 83% |
| 4b json | 0.05 | 9% (20/211) | 19/120 (16%) | 1/91 (1%) | 0/20 | 1/71 (1%) | 95% |
| 9b json | 0 | 0% (0/211) | 0/120 (0%) | 0/91 (0%) | 0/20 | 0/71 (0%) | — |
| 27b json | 0.05 | 28% (58/209) | 56/120 (47%) | 2/89 (2%) | 0/19 | 2/70 (3%) | 97% |
| 4b jsonR | 0 | 0% (0/211) | 0/120 (0%) | 0/91 (0%) | 0/20 | 0/71 (0%) | — |
| 9b jsonR | 0 | 0% (0/211) | 0/120 (0%) | 0/91 (0%) | 0/20 | 0/71 (0%) | — |
| 27b jsonR | 0.05 | 66% (139/210) | 109/120 (91%) | 30/90 (33%) | 14/19 | 16/71 (23%) | 78% |

### Hard negatives by recipe at the headline cutoff

The recipes are roughly equal in number by design; a real keyword-search result would mix them in unknown proportions, so elimination on hard negatives could fall anywhere between the min and max.

| run | forwarded_no_content | keyword_in_signature_or_newsletter | keyword_unrelated_sense | same_people_different_subject | same_subject_wrong_date | min–max |
|---|---|---|---|---|---|---|
| 4b lp | 5/17 (29%) | 5/20 (25%) | 1/19 (5%) | 3/15 (20%) | 0/20 (0%) | 0%–29% |
| 9b lp | 10/17 (59%) | 10/20 (50%) | 8/19 (42%) | 4/15 (27%) | 2/20 (10%) | 10%–59% |
| 27b lp | 10/17 (59%) | 10/20 (50%) | 7/19 (37%) | 3/15 (20%) | 10/20 (50%) | 20%–59% |
| d3-4b | 3/17 (18%) | 6/20 (30%) | 2/19 (11%) | 0/15 (0%) | 0/20 (0%) | 0%–30% |
| d3-9b | 7/17 (41%) | 10/20 (50%) | 4/19 (21%) | 1/15 (7%) | 3/20 (15%) | 7%–50% |
| d3-27b | 11/17 (65%) | 13/20 (65%) | 6/19 (32%) | 4/15 (27%) | 17/20 (85%) | 27%–85% |
| Jev | 9/17 (53%) | 5/20 (25%) | 5/19 (26%) | 3/15 (20%) | 1/20 (5%) | 5%–53% |

### Does the model ranking change?

| metric | run | (a) | (b) | (c) | (d) | (e) | (f) |
|---|---|---|---|---|---|---|---|
| AUROC | 4b lp | 7 | 5 | 7 | 5 | 5 | 5 |
| AUROC | 9b lp | 4 | 4 | 4 | 4 | 4 | 3 |
| AUROC | 27b lp | 2 | 2 | 2 | 2 | 2 | 1 |
| AUROC | d3-4b | 6 | 7 | 6 | 7 | 7 | 7 |
| AUROC | d3-9b | 3 | 3 | 3 | 3 | 3 | 4 |
| AUROC | d3-27b | 1 | 1 | 1 | 1 | 1 | 2 |
| AUROC | Jev | 5 | 6 | 5 | 6 | 6 | 6 |
| elim@98 | 4b lp | 7 | 6 | 7 | 6 | 7 | 6 |
| elim@98 | 9b lp | 4 | 3 | 4 | 3 | 3 | 1 |
| elim@98 | 27b lp | 1= | 2 | 1= | 2 | 2 | 2 |
| elim@98 | d3-4b | 6 | 7 | 6 | 7 | 6 | 7 |
| elim@98 | d3-9b | 3 | 4 | 3 | 4 | 4 | 4 |
| elim@98 | d3-27b | 1= | 1 | 1= | 1 | 1 | 3 |
| elim@98 | Jev | 5 | 5 | 5 | 5 | 5 | 5 |

| metric | run | (a) | (b) | (c) | (d) | (e) | (f) |
|---|---|---|---|---|---|---|---|
| AUROC | 4b lp | 0% | 0% | 0% | 0% | 0% | 0% |
| AUROC | 9b lp | 0% | 0% | 0% | 0% | 0% | 3% |
| AUROC | 27b lp | 22% | 45% | 23% | 16% | 17% | 53% |
| AUROC | d3-4b | 0% | 0% | 0% | 0% | 0% | 0% |
| AUROC | d3-9b | 2% | 0% | 3% | 0% | 0% | 0% |
| AUROC | d3-27b | 75% | 55% | 75% | 84% | 83% | 43% |
| AUROC | Jev | 0% | 0% | 0% | 0% | 0% | 0% |
| elim@98 | 4b lp | 0% | 0% | 0% | 0% | 0% | 1% |
| elim@98 | 9b lp | 1% | 6% | 0% | 3% | 1% | 44% |
| elim@98 | 27b lp | 44% | 13% | 44% | 21% | 23% | 19% |
| elim@98 | d3-4b | 0% | 0% | 0% | 0% | 0% | 0% |
| elim@98 | d3-9b | 11% | 8% | 12% | 1% | 1% | 14% |
| elim@98 | d3-27b | 45% | 73% | 44% | 75% | 75% | 22% |
| elim@98 | Jev | 0% | 0% | 0% | 0% | 0% | 0% |

| metric | (a) vs (e) | (b) vs (e) | (c) vs (e) | (d) vs (e) | (e) vs (e) | (f) vs (e) |
|---|---|---|---|---|---|---|
| AUROC | +0.81 | +1.00 | +0.81 | +1.00 | +1.00 | +0.81 |
| elim@98 | +0.86 | +0.90 | +0.86 | +0.90 | +1.00 | +0.62 |

| subset | metric | order (best first) |
|---|---|---|
| (a) real+ vs real− | AUROC | d3-27b 1.000 > 27b lp 1.000 > d3-9b 0.999 > 9b lp 0.997 > Jev 0.992 > d3-4b 0.987 > 4b lp 0.982 |
| (a) real+ vs real− | elim@98 | 27b lp 100% > d3-27b 100% > d3-9b 99% > 9b lp 96% > Jev 91% > d3-4b 84% > 4b lp 71% |
| (b) real+ vs hard− | AUROC | d3-27b 0.935 > 27b lp 0.933 > d3-9b 0.874 > 9b lp 0.860 > 4b lp 0.827 > Jev 0.782 > d3-4b 0.718 |
| (b) real+ vs hard− | elim@98 | d3-27b 51% > 27b lp 44% > 9b lp 37% > d3-9b 27% > Jev 23% > 4b lp 14% > d3-4b 12% |
| (c) all+ vs real− | AUROC | d3-27b 1.000 > 27b lp 1.000 > d3-9b 0.999 > 9b lp 0.997 > Jev 0.995 > d3-4b 0.991 > 4b lp 0.989 |
| (c) all+ vs real− | elim@98 | 27b lp 100% > d3-27b 100% > d3-9b 99% > 9b lp 96% > Jev 92% > d3-4b 85% > 4b lp 79% |
| (d) all+ vs hard− | AUROC | d3-27b 0.952 > 27b lp 0.943 > d3-9b 0.878 > 9b lp 0.870 > 4b lp 0.836 > Jev 0.813 > d3-4b 0.744 |
| (d) all+ vs hard− | elim@98 | d3-27b 56% > 27b lp 44% > 9b lp 37% > d3-9b 27% > Jev 25% > 4b lp 15% > d3-4b 12% |
| (e) everything | AUROC | d3-27b 0.979 > 27b lp 0.975 > d3-9b 0.947 > 9b lp 0.942 > 4b lp 0.923 > Jev 0.916 > d3-4b 0.884 |
| (e) everything | elim@98 | d3-27b 81% > 27b lp 76% > 9b lp 71% > d3-9b 68% > Jev 63% > d3-4b 54% > 4b lp 52% |
| (f) real+ vs in-window hard− | AUROC | 27b lp 0.925 > d3-27b 0.923 > 9b lp 0.889 > d3-9b 0.865 > 4b lp 0.842 > Jev 0.821 > d3-4b 0.703 |
| (f) real+ vs in-window hard− | elim@98 | 9b lp 45% > 27b lp 42% > d3-27b 41% > d3-9b 31% > Jev 28% > 4b lp 18% > d3-4b 15% |

| subset | AUROC range | elim@98 range |
|---|---|---|
| (a) real+ vs real− | 0.982–1.000 | 71%–100% |
| (b) real+ vs hard− | 0.718–0.935 | 12%–51% |
| (c) all+ vs real− | 0.989–1.000 | 79%–100% |
| (d) all+ vs hard− | 0.744–0.952 | 12%–56% |
| (e) everything | 0.884–0.979 | 52%–81% |
| (f) real+ vs in-window hard− | 0.703–0.925 | 15%–45% |
| JSON runs, (a) | 0.911–0.990 | 0%–91% |
| JSON runs, (b) | 0.665–0.881 | 0%–33% |
| JSON runs, (c) | 0.927–0.994 | 0%–91% |
| JSON runs, (d) | 0.678–0.894 | 0%–33% |
| JSON runs, (e) | 0.833–0.951 | 0%–66% |
| JSON runs, (f) | 0.718–0.868 | 0%–23% |

Largest |AUROC (c) − AUROC (a)| over the seven score models: 0.007; |AUROC (d) − AUROC (b)|: 0.031

Share of negatives cleared at the headline cutoff that are real negatives, seven score models: 70%–90%

**What the data shows**

- **Real emails alone separate almost perfectly.** On (a), every score model's AUROC is 0.982 or higher, and 9b
  lp, 27b lp, d3-9b and d3-27b clear 96–100% of real negatives. Adding the synthetic positives changes little:
  (c) is within 0.007 AUROC of (a) for every score model.
- **The hard negatives carry the difficulty.** AUROC falls to 0.718–0.935 on (b) and elim@98 to 12–51%. Most of
  each headline elim@98 is real negatives: 70% (d3-27b) to 90% (d3-4b) of the negatives cleared.
- **In-window hard negatives (f) are harder still for the d3-27b.** Its elim@98 falls from 51% (46/91) on (b) to
  41% (29/71) on (f). At the headline cutoff it clears 17 of the 20 wrong-date emails, against 10 for 27b lp,
  and 34 vs 30 of the 71 in-window ones.
- **The top two hold, the order beneath them shifts.** d3-27b and 27b lp lead on AUROC in every subset. On (f),
  27b lp is nominally first (0.925 vs 0.923), and the 9b lp has the highest elim@98 (45%, best in 44% of
  resamples).
- **The bottom three swap places.** By AUROC, Jev ranks above d3-4b and 4b lp on real emails. On every subset
  with hard negatives, 4b lp ranks above Jev and d3-4b is last. By elim@98, Jev stays above 4b lp throughout.
- **Recipes split the field widely** (D1-8). The 27b lp clears 20–59% depending on the recipe, the d3-27b
  27–85%. The recipes are about equal in number by design, so elimination on hard negatives is a weighted average
  with unknown real-world weights.
- **The JSON modes follow the same pattern** (AUROC 0.911–0.990 on (a), 0.665–0.881 on (b); D1-9). Because their
  confidences are coarse, the 4b and 9b JSON runs clear 0–16% at 98% recall on every subset. Only the 27b JSON
  runs clear more.

Pairwise significance of these model differences is branch E's subject; here the point is that the ranking among
close models depends on which negatives are in the set.

## D2. What the emails are

### How the set was built

- **Real rows** (`scripts/build_golden.py`; SPEC §7.3, §14). Opus pre-labeled 210 real emails per request: 120
  produced and 90 from other productions (D2-0, `data/golden/work/candidate_plan.json`). The human adjudicated the
  disagreements, a random 20% spot check, and later rechecks (`docs/golden-adjudication.md`). The build keeps 75
  positives and 60 negatives per request, preferring adjudicated rows, then high-confidence pre-labels, then a
  seeded random order. Positives come from the request's own production, negatives from other productions. The
  build would also admit an other-production email the human called responsive, but none is in the set: all 150
  real positives have origin `produced` (`d_validity_verify.py` V0). [corrected in verification]
  So produced emails the human judged not responsive (over-production) are left out (D2-4b).
- **Synthetic rows** (SPEC §14). Per the spec, these are *edits of real emails*: real sender, signature and thread
  shape, changed substance, written by Opus subagents (not a Qwen, to avoid grading the candidates on their own
  text). Each carries its recipe and source email id (`data/golden/work/gen/job_*.json`,
  `data/golden/work/synthetic.jsonl`).
- **Verifier.** A verifier pass recorded label-ok, recipe-ok and style-tell verdicts. The repo doesn't record
  which model the verifier was.
- **Flags.** A flagged email stays in the set only if the human adjudicated it (K keep, F flip, D drop).

| request | produced candidates | other-production candidates | pre-labeled by Opus | kept as real+ | kept as real− |
|---|---|---|---|---|---|
| 24-409 | 120 | 90 | 210 | 75 | 60 |
| 25-3152 | 120 | 90 | 210 | 75 | 60 |

| kind / recipe | asked for (both requests) | kept in golden set | recipe description (verbatim) |
|---|---|---|---|
| close_call_positive / marginal_mention | 50 | 50 | Responsive only because of a brief, passing reference that meets a request criterion (e.g. one line in an otherwise unrelated email); the rest of the email is about something else. |
| exempt_other_positive / personnel_or_deliberative | 40 | 40 | Responsive and containing personnel matters, a deliberative pre-decisional draft, or student/medical details; sensitive but squarely within the request. |
| hard_negative / forwarded_no_content | 20 | 19 | A forward or reply that contains only 'FYI', 'see below', a calendar acceptance, or an out-of-office, addressed to relevant people but with no responsive substance and not from/to anyone the request scopes on. |
| hard_negative / keyword_in_signature_or_newsletter | 20 | 20 | A mass newsletter, announcement, or auto-generated notice where the request's key terms appear only in a signature block, footer, boilerplate, or link roundup. |
| hard_negative / keyword_unrelated_sense | 20 | 19 | The request's key terms appear in an unrelated sense (a different project with a similar name, a common word used differently, a person with the same surname). |
| hard_negative / same_people_different_subject | 20 | 17 | Keep the same sender/recipients (people the request names or roster members); change the subject matter entirely to something personal or administrative that the request does not cover. |
| hard_negative / same_subject_wrong_date | 20 | 20 | Keep the subject matter squarely on topic; move the date clearly outside the request's date window and make the content consistent with that date. |
| privileged_positive / attorney_client | 40 | 40 | Responsive and clearly marked attorney-client privileged / confidential legal advice from County Counsel or outside counsel, on the request's subject. |

Generated: 230; dropped by build_golden.py (flagged and not kept, or D): 5; in the golden set: 225 (of which flipped to responsive by the human: 4)

### The real negatives

| scored against | produced for | n | date range | date unknown | in the target's date window | keyword-search hit (proxy) | in window + keyword hit | mentions 'Alpine' anywhere |
|---|---|---|---|---|---|---|---|---|
| 24-409 | 25-3152 | 40 | 2024-01-04 .. 2025-05-22 | 0 | 0/40 (0%) | 0/40 (0%) | 0/40 (0%) | 24/40 (60%) |
| 24-409 | 25-4697 | 14 | 2024-06-26 .. 2025-10-03 | 0 | 0/14 (0%) | 0/14 (0%) | 0/14 (0%) | 0/14 (0%) |
| 24-409 | 25-5982 | 6 | 2024-04-03 .. 2025-10-08 | 1 | 0/6 (0%) | 0/6 (0%) | 0/6 (0%) | 0/6 (0%) |
| 25-3152 | 24-409 | 46 | 2021-09-08 .. 2023-07-28 | 0 | 0/46 (0%) | 0/46 (0%) | 0/46 (0%) | 0/46 (0%) |
| 25-3152 | 25-4697 | 9 | 2025-06-10 .. 2025-09-28 | 0 | 0/9 (0%) | 0/9 (0%) | 0/9 (0%) | 0/9 (0%) |
| 25-3152 | 25-5982 | 5 | 2024-10-25 .. 2025-10-27 | 0 | 2/5 (40%) | 0/5 (0%) | 0/5 (0%) | 0/5 (0%) |

- Opus pre-label rationale for the real negatives cites the date window ('window', 'predates', 'outside the', 'before the', 'after the'): 118/120 (98%)
- 24-409 real positives: dates 2023-01-05 .. 2023-07-31; window 2023-01-01 .. 2023-07-31
- 25-3152 real positives: dates 2024-01-19 .. 2025-05-30; window 2024-01-01 .. 2025-05-31

### Features by kind

| kind | n | median body chars | body > 8,000 chars (truncated) | has attachments | median recipients | quoted thread | in date window | keyword hit (any field) | keyword hit (subject/body/attachments only) |
|---|---|---|---|---|---|---|---|---|---|
| real_positive | 150 | 2216 | 21/150 (14%) | 86/150 (57%) | 3 | 84/150 (56%) | 150/150 (100%) | 147/150 (98%) | 118/150 (79%) |
| close_call_positive | 50 | 1556 | 5/50 (10%) | 29/50 (58%) | 2 | 25/50 (50%) | 50/50 (100%) | 50/50 (100%) | 44/50 (88%) |
| privileged_positive | 40 | 3922 | 8/40 (20%) | 12/40 (30%) | 2 | 34/40 (85%) | 40/40 (100%) | 40/40 (100%) | 38/40 (95%) |
| exempt_other_positive | 40 | 2510 | 4/40 (10%) | 26/40 (65%) | 2 | 22/40 (55%) | 40/40 (100%) | 40/40 (100%) | 31/40 (78%) |
| hard_negative_flipped | 4 | 600 | 0/4 (0%) | 2/4 (50%) | 2 | 2/4 (50%) | 4/4 (100%) | 4/4 (100%) | 2/4 (50%) |
| real_negative | 120 | 2304 | 9/120 (8%) | 69/120 (57%) | 2 | 72/120 (60%) | 2/120 (2%) | 0/120 (0%) | 0/120 (0%) |
| hard_negative | 91 | 1701 | 8/91 (9%) | 48/91 (53%) | 1 | 46/91 (51%) | 71/91 (78%) | 55/91 (60%) | 53/91 (58%) |

Hard negatives by recipe (in window / keyword hit, any field):

| request | recipe | n | in window | keyword hit | in window + keyword hit |
|---|---|---|---|---|---|
| 24-409 | forwarded_no_content | 7 | 7/7 (100%) | 0/7 (0%) | 0/7 (0%) |
| 24-409 | keyword_in_signature_or_newsletter | 10 | 10/10 (100%) | 7/10 (70%) | 7/10 (70%) |
| 24-409 | keyword_unrelated_sense | 9 | 9/9 (100%) | 5/9 (56%) | 5/9 (56%) |
| 24-409 | same_people_different_subject | 6 | 6/6 (100%) | 2/6 (33%) | 2/6 (33%) |
| 24-409 | same_subject_wrong_date | 10 | 0/10 (0%) | 10/10 (100%) | 0/10 (0%) |
| 25-3152 | forwarded_no_content | 10 | 10/10 (100%) | 2/10 (20%) | 2/10 (20%) |
| 25-3152 | keyword_in_signature_or_newsletter | 10 | 10/10 (100%) | 10/10 (100%) | 10/10 (100%) |
| 25-3152 | keyword_unrelated_sense | 10 | 10/10 (100%) | 0/10 (0%) | 0/10 (0%) |
| 25-3152 | same_people_different_subject | 9 | 9/9 (100%) | 9/9 (100%) | 9/9 (100%) |
| 25-3152 | same_subject_wrong_date | 10 | 0/10 (0%) | 10/10 (100%) | 0/10 (0%) |

All hard negatives, in window + keyword hit: 35/91 (38%)

### Is there real material for harder real negatives?

These are real emails a keyword search for the target request could return although another request produced them. They are unlabeled (some could be responsive); they are the material a real-negative hard set could be built from.

| target request | production | emails | in target window | in window + keyword hit | distinct bodies among those | already a golden real negative |
|---|---|---|---|---|---|---|
| 24-409 | 25-3152 | 922 | 0 | 0 | 0 | 0 |
| 24-409 | 25-4697 | 207 | 0 | 0 | 0 | 0 |
| 24-409 | 25-5982 | 129 | 0 | 0 | 0 | 0 |
| 25-3152 | 24-409 | 1204 | 0 | 0 | 0 | 0 |
| 25-3152 | 25-4697 | 207 | 24 | 0 | 0 | 0 |
| 25-3152 | 25-5982 | 129 | 64 | 0 | 0 | 0 |

Final call = the human's call where one exists, else the Opus pre-label. build_golden.py keeps negatives only from other productions, so these real in-window near misses are not in the set.

| request | produced emails pre-labeled | final R | final N (over-produced) | final ? (unclear, dropped) |
|---|---|---|---|---|
| 24-409 | 120 | 113 | 7 | 0 |
| 25-3152 | 120 | 117 | 3 | 0 |

### Checks on the synthetic emails and the labels

| kind | kept | style tell: none | mild | obvious | verifier: label wrong | verifier: recipe not followed | human-adjudicated |
|---|---|---|---|---|---|---|---|
| close_call_positive | 50 | 34 | 16 | 0 | 0 | 16 | 18 |
| privileged_positive | 40 | 21 | 19 | 0 | 0 | 0 | 0 |
| exempt_other_positive | 40 | 18 | 22 | 0 | 0 | 0 | 0 |
| hard_negative | 91 | 45 | 45 | 1 | 11 | 0 | 11 |
| hard_negative_flipped | 4 | 1 | 2 | 1 | 4 | 3 | 4 |
| all synthetic | 225 | 119 | 104 | 2 | 15 | 19 | 33 |

| adjudication-page section | items | human calls | note |
|---|---|---|---|
| spot | 81 | N×30, R×51 | 81/81 calls equal the Opus pre-label |
| disagree | 12 | N×10, R×2 |  |
| synth | 32 | D×4, F×3, K×25 |  |
| recheck | 8 | D×1, F×1, K×4, R×2 |  |

| kind | n | human-adjudicated (any section) |
|---|---|---|
| real_positive | 150 | 55/150 (37%) |
| close_call_positive | 50 | 18/50 (36%) |
| privileged_positive | 40 | 0/40 (0%) |
| exempt_other_positive | 40 | 0/40 (0%) |
| hard_negative_flipped | 4 | 4/4 (100%) |
| real_negative | 120 | 30/120 (25%) |
| hard_negative | 91 | 11/91 (12%) |

| origin | pre-label confidence | in golden set | in the 420 pre-labeled candidates |
|---|---|---|---|
| other_production | high | 120 | 180 |
| produced | high | 137 | 185 |
| produced | low | 2 | 8 |
| produced | medium | 11 | 47 |

difflib.SequenceMatcher ratio on the first 8,000 characters (what the models see); 1.0 = identical.

| kind | n | median similarity to source | interquartile range | visible body identical to source | same subject as source | same sender | source email is also a real row in the set |
|---|---|---|---|---|---|---|---|
| close_call_positive | 50 | 0.89 | 0.56–0.97 | 1/50 (2%) | 15/50 (30%) | 50/50 (100%) | 34/50 (68%) |
| privileged_positive | 40 | 0.65 | 0.46–0.78 | 0/40 (0%) | 13/40 (32%) | 16/40 (40%) | 37/40 (92%) |
| exempt_other_positive | 40 | 0.94 | 0.86–0.97 | 0/40 (0%) | 39/40 (98%) | 40/40 (100%) | 26/40 (65%) |
| hard_negative | 91 | 0.84 | 0.31–0.98 | 4/91 (4%) | 28/91 (31%) | 69/91 (76%) | 63/91 (69%) |
| hard_negative_flipped | 4 | 0.43 | 0.18–0.70 | 0/4 (0%) | 0/4 (0%) | 4/4 (100%) | 4/4 (100%) |

What the source email is, where it is also a real row in the golden set:

| synthetic kind | source is a ... | n |
|---|---|---|
| close_call_positive | real_positive | 34 |
| exempt_other_positive | real_positive | 26 |
| hard_negative | real_positive | 63 |
| hard_negative_flipped | real_positive | 4 |
| privileged_positive | real_positive | 37 |

Distinct source emails behind the 225 kept synthetic emails: 130; sources used more than once: 63

P(synthetic > real) = AUROC with synthetic as the 'positive' class: the probability that a random synthetic email outscores a random real one of the same label (0.5 = no difference; ties count half).

| run | median real+ | median synthetic+ | P(synthetic+ > real+) | median real− | median hard− | P(hard− > real−) |
|---|---|---|---|---|---|---|
| 4b lp | 0.832 | 0.829 | 0.48 | 0.167 | 0.562 | 0.87 |
| 9b lp | 0.880 | 0.879 | 0.50 | 0.063 | 0.446 | 0.90 |
| 27b lp | 0.997 | 0.995 | 0.47 | 0.000 | 0.081 | 0.96 |
| d3-4b | 0.786 | 0.819 | 0.55 | 0.122 | 0.644 | 0.94 |
| d3-9b | 0.861 | 0.852 | 0.49 | 0.103 | 0.476 | 0.95 |
| d3-27b | 0.987 | 0.987 | 0.53 | 0.011 | 0.483 | 0.99 |
| Jev | 0.810 | 0.840 | 0.57 | 0.140 | 0.610 | 0.92 |

By synthetic positive kind: P(kind > real+)

| run | close_call_positive (n=50) | privileged_positive (n=40) | exempt_other_positive (n=40) | hard_negative_flipped (n=4) |
|---|---|---|---|---|
| 4b lp | 0.38 | 0.55 | 0.55 | 0.22 |
| 9b lp | 0.37 | 0.65 | 0.56 | 0.17 |
| 27b lp | 0.34 | 0.62 | 0.50 | 0.23 |
| d3-4b | 0.54 | 0.59 | 0.52 | 0.57 |
| d3-9b | 0.43 | 0.54 | 0.52 | 0.51 |
| d3-27b | 0.42 | 0.65 | 0.55 | 0.39 |
| Jev | 0.50 | 0.67 | 0.56 | 0.45 |

### Spot-read (judgment)

I read a fixed random sample: 10 real negatives, 10 hard negatives (one per recipe per request) and 10 synthetic
positives (`d_validity_spotread.py`; `--full` prints the bodies, and the synthetic ones show the lines the edit
added). Codes: *real* = reads like an ordinary email of its kind; *tell* = plausible, but with a detail that reads
as generated; *contrived* = unusual in a real mailbox.

| group | pair | kind / recipe | date | subject | code | note |
|---|---|---|---|---|---|---|
| real negative | `24-409 · sandiego:25-3152:48517858` | real_negative | 2024-03-01T20:36:56+00:00 | March 12th Board Hearing on Socially Equitable Cannabis Program | real | County staff invite to a 2024 cannabis-program stakeholder meeting. Ordinary email; 2024 date and no 24-409 term, so a 24-409 search would never return it. |
| real negative | `24-409 · sandiego:25-5982:55059062` | real_negative | — | [External] [ABMoC California] Fwd: Sign On Request: Letter Demanding R | real | Advocacy mailing-list forward (2025, per the body). Unrelated topic, no date header, no 24-409 term. |
| real negative | `24-409 · sandiego:25-3152:48518074` | real_negative | 2025-02-20T19:47:19+05:00 | Construction _ Estimates! | real | Construction-estimate spam bcc'd to the ACPG chair. Trivially non-responsive to 24-409. |
| real negative | `24-409 · sandiego:25-5982:55058924` | real_negative | Wednesday, October 8, 202 | FW: Sponsorship Opportunity: CAIR-SD’s 18th Annual Banquet | real | 2025 CAIR banquet sponsorship thread from another custodian search. Off topic, out of window. |
| real negative | `24-409 · sandiego:25-5982:55059129` | real_negative | Thursday, May 15, 2025 10 | FW: [External] FINAL Comments on Report | real | 2025 equity-office report comments. Off topic, out of window. |
| real negative | `25-3152 · sandiego:25-4697:52663416` | real_negative | 2025-09-05T14:57:40-07:00 | RE: HGVS Maps  | real | Internal PDS graphics request on another project (Sept 2025). No ACPG member, after the window. |
| real negative | `25-3152 · sandiego:24-409:33733067` | real_negative | 2023-04-07T18:55:44.30516 | RE: CBO Contacts | real | Internal County thread (April 2023) about community-group contacts. No ACPG member, before the window. |
| real negative | `25-3152 · sandiego:24-409:33733023` | real_negative | 2023-02-07T17:47:10-08:00 | Re: [External] Invitation to join new Ag Workforce Initiative in San D | real | Food-system nonprofit to County staff, Feb 2023. No ACPG member, before the window. |
| real negative | `25-3152 · sandiego:24-409:33733134` | real_negative | 2023-03-27T09:23:54-07:00 | RE: Flood Control District Advisory Commission (FCDAC) Meeting | real | Internal flood-control scheduling, March 2023. No ACPG member, before the window. |
| real negative | `25-3152 · sandiego:25-4697:52663454` | real_negative | 2025-09-15T11:19:40-07:00 | WORD copies of Resolutions and Ordinance | real | Internal PDS docketing note, Sept 2025. No ACPG member, after the window. |
| hard negative | `24-409 · synth:24-409:06:07` | hard_negative / forwarded_no_content | 2023-03-14T13:20:52-07:00 | FW: PollEverywhere subscription | real | 'See below' forward of a software-subscription notice to Elise Ruiz. Convincing, but it has no 24-409 term, so only a sweep of Ruiz's whole mailbox would return it. |
| hard negative | `25-3152 · synth:25-3152:18:03` | hard_negative / forwarded_no_content | 2025-02-04T20:02:15+00:00 | FW: Park Fee Changes Starting February 18, 2025 | real | Staff FYI forward of a Parks notice sent to another planning group. Convincing; no ACPG member on it, so a member-address search would not return it. |
| hard negative | `24-409 · synth:24-409:05:02` | hard_negative / keyword_in_signature_or_newsletter | 2023-06-23T11:06:26-07:00 | [External] Structural BMP Owners: Annual Maintenance Verification Due  | real | GovDelivery stormwater bulletin; a named County PM appears only as the 'sent to' address. Convincing bulk notice; no 24-409 term in the content. |
| hard negative | `25-3152 · synth:25-3152:17:08` | hard_negative / keyword_in_signature_or_newsletter | 2025-01-21T14:10:00-08:00 | This Week at the Alpine Community Center | real | Community-center weekly newsletter to a member of the public; the ACPG meeting is one line in the events list. Convincing. |
| hard negative | `24-409 · synth:24-409:07:07` | hard_negative / keyword_unrelated_sense | 2023-04-18T18:16:50-07:00 | [External] RE: Tree Equity - 2nd Community Forum Planning | real | The real water-equity planning thread rewritten as a 'Tree Equity' forum with the same consultant and staff. Convincing; a genuine near miss for a reader. |
| hard negative | `25-3152 · synth:25-3152:19:09` | hard_negative / keyword_unrelated_sense | 2024-01-18T22:18:12+00:00 | PDS2023-TPM-21444 Scoping Letter | real | Body identical to a real 25-3152-production email (a scoping letter to another planning group); 'synthetic' only in its label. |
| hard negative | `24-409 · synth:24-409:03:01` | hard_negative / same_people_different_subject | 2023-06-14T16:23:09-07:00 | [External] RE: COC Visitor Lot Closure | tell | Named consultant and County PM chatting about a parking-lot closure. Plausible, but the thread repeats a near-identical 'no dates posted yet' message, which reads as generated. The verifier called it responsive (Geosyntec in the address); the owner kept it negative. |
| hard negative | `25-3152 · synth:25-3152:15:02` | hard_negative / same_people_different_subject | 2024-10-15T13:49:27+00:00 | RE: Rooftop Lease Amendment - CAL02204 | real | Misaddressed vendor lease emails to the chair. Realistic; responsive under the request's literal 'any member and the public' wording, negative only under the owner's purely-personal call (findings-golden §9). The label is a legal judgment. |
| hard negative | `24-409 · synth:24-409:04:07` | hard_negative / same_subject_wrong_date | 2025-03-20T12:13:07-07:00 | [External] RE: Regional Water Equity - Team Introduction | real | The real RWER kickoff thread with every date moved to 2025. Convincing; a date-limited search would exclude it before review. |
| hard negative | `25-3152 · synth:25-3152:16:04` | hard_negative / same_subject_wrong_date | 2023-05-18T19:27:32+00:00 | Re: Loveland Letters of Support | real | Real member-public thread moved back one year (two quoted 'wrote' lines and the header date). Convincing; a date-limited search would exclude it. |
| synthetic positive | `24-409 · synth:24-409:00:04` | close_call_positive / marginal_mention | 2023-04-11T11:10:06-07:00 | [External] RE: CASQA Abstracts | real | One natural sentence ('hold off on anything RWER') added to a real consultant thread; 'RWER' removed from the subject. Reads as real. |
| synthetic positive | `24-409 · synth:24-409:00:02` | close_call_positive / marginal_mention | 2023-07-05T12:04:12-07:00 | Friday's quarterly meeting | real | One sentence changed to mention reviewing the RWER. Reads as real. |
| synthetic positive | `25-3152 · synth:25-3152:13:07` | close_call_positive / marginal_mention | 2025-03-26T00:02:09+00:00 | RE: [External] Building records question | real | County staff answering the chair's personal building-records question, plus a one-line agenda note. Plausible; responsive from the headers alone (staff to a member), so the 'marginal mention' adds nothing for this request. |
| synthetic positive | `25-3152 · synth:25-3152:14:02` | close_call_positive / marginal_mention | 2025-02-01T15:32:17-08:00 | Report on SANDAG's January 2025 Meetings to the Association of Plannin | real | Real APG report with one thank-you line added; the line sits past the 8,000-character cap, so the model sees only the chair as one of many recipients. |
| synthetic positive | `24-409 · synth:24-409:08:01` | privileged_positive / attorney_client | 2023-04-13T12:51:37-07:00 | RE: UCSD Role for Water Assembly (Attorney Client Communication) | tell | New Deputy County Counsel email under a privilege banner that names UCSD, Geosyntec, 'JB' and Dr. Lerner in one paragraph. Plausible, but denser in request terms than most real emails. |
| synthetic positive | `24-409 · synth:24-409:09:02` | privileged_positive / attorney_client | 2023-06-26T09:14:00-07:00 | RE: Regional Water Equity - Deep Dives Flyer | tell | Staff forwarding numbered County Counsel advice on the RWER flyer, Murakawa's registrant list and GovDelivery. Tidy and on-topic in a way that reads as written to order. |
| synthetic positive | `25-3152 · synth:25-3152:21:04` | privileged_positive / attorney_client | 2024-04-02T15:47:31-07:00 | RE: [External] Fwd: PDS2023-MUP-23-015-Scoping Letter & attachments -  | tell | County Counsel memo to the chair citing Gov. Code 54956 and 47 U.S.C. 332 under a privilege / work-product banner. Fluent and polished; plausible but likely easier than a real privileged email. |
| synthetic positive | `24-409 · synth:24-409:11:09` | exempt_other_positive / personnel_or_deliberative | 2023-06-23T09:41:22.14366 | RE: Regional Water Equity - Deep Dives Flyer | real | One sentence about reduced hours after surgery added to a real RWER thread. Reads as real; otherwise a copy of a real positive. |
| synthetic positive | `25-3152 · synth:25-3152:22:05` | exempt_other_positive / personnel_or_deliberative | 2024-03-13T23:01:07+00:00 | Maggie/ Greg SDGE Loveland Progress! | real | A few sentences about a ranger complaint added to a real member-public email. Reads as real. |
| synthetic positive | `25-3152 · synth:25-3152:22:00` | exempt_other_positive / personnel_or_deliberative | 2024-07-15T17:00:58+00:00 | RE: Objective Design Standards (ODS) Checklist - Alpine | real | One 'still a working draft' caveat added to a real County-to-chair email. Reads as real. |

| group | real | tell | contrived |
|---|---|---|---|
| real negative | 10 | 0 | 0 |
| hard negative | 9 | 1 | 0 |
| synthetic positive | 7 | 3 | 0 |

**What the data shows**

- **Real negatives are off-topic and out of window.** They come from three other productions. The bulk for each
  request is the other golden request's production (40 of 60 for 24-409, 46 of 60 for 25-3152). Only 2 of 120 fall
  in the target's window, none hits the keyword proxy, and the Opus pre-label rationale cites the date window for
  118 of 120. All 10 I read were ordinary emails that a date-limited search for the target would not return.
- **The repo has no real in-window keyword hits from other productions** (D2-4: zero in all six combinations).
  The only real near misses in hand are the over-produced emails: 7 for 24-409 and 3 for 25-3152 (D2-4b). They
  aren't in the set.
- **Hard negatives are near misses, but many aren't search hits.** 71 of 91 are in window (all but the wrong-date
  recipe), 55 of 91 hit the keyword proxy, and 35 of 91 (38%) are both. Some recipes rarely hit the proxy:
  forwarded-no-content (0/7 for 24-409, 2/10 for 25-3152) and keyword-in-unrelated-sense for 25-3152 (0/10).
  Those test the model's reading of the request, not a search's false hits.
- **The synthetic emails read as real, and most edits are small.**
  - Spot-read: 9 of 10 hard negatives and 7 of 10 synthetic positives read as real. All three tells among the
    synthetic positives were privileged emails: fluent counsel emails dense in request terms.
  - Verifier: style tell "mild" for 104 of 225 and "obvious" for 2.
  - Median body similarity to the source email is 0.84–0.94 for close calls, exempt positives and hard
    negatives, 0.65 for privileged positives, and 0.43 for the 4 flipped. 4 hard negatives and 1 close call have
    a visible body identical to their source.
- **Synthetic positives score like real ones on average** (P(synthetic+ > real+) 0.47–0.57). The kinds offset
  each other: close calls score lower (0.34–0.54) and privileged emails higher (0.54–0.67). This finds no
  evidence that the models detect "generated" style in a way that lowers responsive scores. It can't rule out
  offsetting effects.
- **The set is built from overlapping emails.** The 225 synthetic emails come from 130 source emails, and most
  of those sources are real positives in the set (34/50 close calls, 37/40 privileged, 26/40 exempt, 63/91 hard
  negatives). The hard negatives are therefore mostly *minimal pairs*: a real positive and a rewritten copy of it
  that is not responsive. That is a strict test, and not how non-responsive mail arises in a search.
- **Most synthetic labels rest on the generator's intent.** 192 of 225 synthetic rows and 185 of 270 real rows
  have no human call. The random spot check of Opus/production agreements found 0 disagreements in 81 (L-2).
  Real positives favor confident pre-labels: 137 of 150 were high-confidence.

**Which subset is the better deployment proxy (judgment).** A deployed screen sees the output of the agency's
search: emails in the request's date range that contain the search terms or involve the named people.

- **Positives:** the real production (real+) is the right population. The synthetic positives add privileged and
  sensitive mail that a production under-represents, because fully withheld records aren't in it. They score
  about the same overall.
- **Negatives:** the real negatives are the wrong population. They are other requests' records, nearly all
  outside the window and without the terms. Elimination measured on them (a, c) is mostly what a date filter
  would already do, so it is an optimistic upper bound and not a deployment estimate.
- **Hard negatives** are the right *kind* of email: same mailboxes, same people, near-miss content. But they are
  synthetic and spread about evenly over five recipes by design. One recipe (wrong date) would be removed by
  the search itself, and only 55 of 91 contain the search terms (by the proxy).
- **My pick:** subset (f), real positives vs in-window hard negatives, as the conservative proxy. It probably
  understates elimination, because real search results also hold many easy non-responsive emails (bulk mail and
  newsletters with a stray term) that would be cleared like the real negatives here. The headline (e) is the
  optimistic bound.
- **Where the truth lies:** somewhere between (f) and (e). This data can't place it, because the real mix of easy
  and near-miss non-responsive hits is unknown. Branch B's workload estimates should be read with this range in
  mind.

## D3. Topical (24-409) vs correspondent-scoped (25-3152)

| kind | 24-409 | 25-3152 |
|---|---|---|
| close_call_positive | 25 | 25 |
| exempt_other_positive | 20 | 20 |
| privileged_positive | 20 | 20 |
| real_positive | 75 | 75 |
| hard_negative | 42 | 49 |
| hard_negative_flipped | 4 | 0 |
| real_negative | 60 | 60 |
| positives / negatives | 144 / 102 | 140 / 109 |

| hard-negative recipe | 24-409 | 25-3152 |
|---|---|---|
| forwarded_no_content | 7 | 10 |
| keyword_in_signature_or_newsletter | 10 | 10 |
| keyword_unrelated_sense | 9 | 10 |
| same_people_different_subject | 6 | 9 |
| same_subject_wrong_date | 10 | 10 |

### Per request

| run | 24-409 AUROC | 24-409 elim@98 | 24-409 thr98 | 25-3152 AUROC | 25-3152 elim@98 | 25-3152 thr98 |
|---|---|---|---|---|---|---|
| 4b lp | 0.964 [0.942–0.982] | 72% (73/102) [55%–87%] | 0.3002 (2/144 missed) | 0.883 [0.837–0.924] | 29% (32/109) [8%–65%] | 0.221 (2/140 missed) |
| 9b lp | 0.962 [0.940–0.981] | 76% (78/102) [68%–86%] | 0.2463 (2/144 missed) | 0.927 [0.893–0.958] | 70% (76/109) [60%–81%] | 0.4196 (2/140 missed) |
| 27b lp | 0.992 [0.985–0.998] | 89% (91/102) [81%–97%] | 0.3623 (2/144 missed) | 0.955 [0.927–0.975] | 74% (81/109) [61%–83%] | 0.05664 (2/140 missed) |
| d3-4b | 0.880 [0.835–0.922] | 63% (64/102) [54%–73%] | 0.3323 (2/144 missed) | 0.889 [0.846–0.929] | 45% (49/109) [10%–61%] | 0.3507 (2/140 missed) |
| d3-9b | 0.960 [0.938–0.979] | 74% (75/102) [64%–83%] | 0.3051 (2/144 missed) | 0.947 [0.917–0.973] | 74% (81/109) [57%–83%] | 0.5427 (2/140 missed) |
| d3-27b | 0.992 [0.985–0.997] | 91% (93/102) [76%–98%] | 0.8542 (2/144 missed) | 0.980 [0.967–0.992] | 85% (93/109) [78%–93%] | 0.5405 (2/140 missed) |
| Jev | 0.936 [0.905–0.960] | 69% (70/102) [57%–77%] | 0.57 (2/144 missed) | 0.915 [0.880–0.946] | 58% (63/109) [30%–71%] | 0.31 (2/140 missed) |
| 4b json | 0.880 [0.840–0.920] | 9% (9/102) [4%–16%] | 0.05 (0/144 missed) | 0.789 [0.736–0.840] | 10% (11/109) [0%–17%] | 0.05 (1/140 missed) |
| 9b json | 0.886 [0.840–0.926] | 0% (0/102) [0%–0%] | 0 (0/144 missed) | 0.859 [0.815–0.901] | 0% (0/109) [0%–0%] | 0 (0/140 missed) |
| 27b json | 0.964 [0.941–0.982] | 87% (89/102) [38%–92%] | 0.95 (2/144 missed) | 0.924 [0.889–0.952] | 11% (12/107) [6%–18%] | 0.05 (0/140 missed) |
| 4b jsonR | 0.894 [0.847–0.936] | 0% (0/102) [0%–76%] | 0 (0/144 missed) | 0.851 [0.803–0.893] | 0% (0/109) [0%–0%] | 0 (0/140 missed) |
| 9b jsonR | 0.904 [0.862–0.940] | 0% (0/102) [0%–0%] | 0 (0/144 missed) | 0.861 [0.815–0.906] | 0% (0/109) [0%–66%] | 0 (0/139 missed) |
| 27b jsonR | 0.962 [0.943–0.978] | 76% (78/102) [68%–84%] | 0.95 (0/144 missed) | 0.940 [0.912–0.963] | 61% (66/108) [0%–69%] | 0.05 (2/140 missed) |

| run | ΔAUROC (24-409 − 25-3152) | Δelim@98 | AUROC CI excludes 0 |
|---|---|---|---|
| 4b lp | +0.081 [+0.032, +0.131] | +42% [+3%, +67%] | yes |
| 9b lp | +0.035 [-0.001, +0.075] | +7% [-7%, +20%] | no |
| 27b lp | +0.038 [+0.016, +0.066] | +15% [+3%, +31%] | yes |
| d3-4b | -0.008 [-0.071, +0.054] | +18% [-1%, +53%] | no |
| d3-9b | +0.013 [-0.023, +0.050] | -1% [-14%, +18%] | no |
| d3-27b | +0.012 [-0.002, +0.027] | +6% [-11%, +15%] | no |
| Jev | +0.021 [-0.024, +0.065] | +11% [-8%, +38%] | no |
| 4b json | +0.091 [+0.026, +0.157] | -1% [-10%, +10%] | yes |
| 9b json | +0.028 [-0.033, +0.089] | +0% [+0%, +0%] | no |
| 27b json | +0.040 [+0.004, +0.081] | +76% [+25%, +84%] | yes |
| 4b jsonR | +0.043 [-0.019, +0.111] | +0% [+0%, +76%] | no |
| 9b jsonR | +0.042 [-0.016, +0.102] | +0% [-66%, +0%] | no |
| 27b jsonR | +0.022 [-0.008, +0.055] | +15% [+5%, +83%] | no |

### Where the difference sits

| run | 24-409 (a) real+ vs real− | 24-409 (b) real+ vs hard− | 24-409 (f) real+ vs in-window hard− | 25-3152 (a) real+ vs real− | 25-3152 (b) real+ vs hard− | 25-3152 (f) real+ vs in-window hard− |
|---|---|---|---|---|---|---|
| 4b lp | 0.996 / 87% (52/60) | 0.907 / 26% (11/42) | 0.926 / 34% (11/32) | 0.964 / 38% (23/60) | 0.759 / 4% (2/49) | 0.773 / 5% (2/39) |
| 9b lp | 1.000 / 100% (60/60) | 0.907 / 48% (20/42) | 0.942 / 59% (19/32) | 0.996 / 93% (56/60) | 0.821 / 35% (17/49) | 0.846 / 41% (16/39) |
| 27b lp | 1.000 / 100% (60/60) | 0.986 / 83% (35/42) | 0.983 / 81% (26/32) | 1.000 / 100% (60/60) | 0.878 / 39% (19/49) | 0.862 / 36% (14/39) |
| d3-4b | 0.999 / 100% (60/60) | 0.695 / 10% (4/42) | 0.672 / 12% (4/32) | 0.971 / 63% (38/60) | 0.740 / 12% (6/49) | 0.733 / 15% (6/39) |
| d3-9b | 1.000 / 100% (60/60) | 0.907 / 29% (12/42) | 0.916 / 34% (11/32) | 1.000 / 98% (59/60) | 0.862 / 37% (18/49) | 0.843 / 36% (14/39) |
| d3-27b | 1.000 / 100% (60/60) | 0.979 / 79% (33/42) | 0.974 / 75% (24/32) | 1.000 / 100% (60/60) | 0.937 / 67% (33/49) | 0.921 / 59% (23/39) |
| Jev | 1.000 / 98% (59/60) | 0.823 / 19% (8/42) | 0.855 / 25% (8/32) | 0.975 / 77% (46/60) | 0.801 / 35% (17/49) | 0.845 / 41% (16/39) |

Sizes (positives / negatives): 24-409 (a) 75/60; 24-409 (b) 75/42; 24-409 (f) 75/32; 25-3152 (a) 75/60; 25-3152 (b) 75/49; 25-3152 (f) 75/39

### With the roster (25-3152)

| run | pairs | AUROC without → with | ΔAUROC [paired 95% CI] | elim@98 without → with | Δelim@98 [95% CI] | 24-409 AUROC (for comparison) |
|---|---|---|---|---|---|---|
| 4b lp | 249 | 0.883 → 0.950 | +0.067 [+0.034, +0.102] | 29% (32/109) → 75% (82/109) | +46% [+15%, +67%] | 0.964 |
| 9b lp | 249 | 0.927 → 0.963 | +0.035 [+0.012, +0.061] | 70% (76/109) → 68% (74/109) | -2% [-12%, +9%] | 0.962 |
| 27b lp | 249 | 0.955 → 0.989 | +0.034 [+0.014, +0.060] | 74% (81/109) → 91% (99/109) | +17% [+8%, +30%] | 0.992 |
| d3-4b | 249 | 0.889 → 0.961 | +0.073 [+0.043, +0.105] | 45% (49/109) → 86% (94/109) | +41% [+27%, +78%] | 0.880 |
| d3-9b | 249 | 0.947 → 0.979 | +0.031 [+0.011, +0.055] | 74% (81/109) → 90% (98/109) | +16% [+7%, +32%] | 0.960 |
| d3-27b | 249 | 0.980 → 0.998 | +0.017 [+0.008, +0.031] | 85% (93/109) → 98% (107/109) | +13% [+6%, +19%] | 0.992 |
| Jev | 249 | 0.915 → 0.968 | +0.053 [+0.027, +0.083] | 58% (63/109) → 83% (91/109) | +26% [+12%, +52%] | 0.936 |
| 4b json | 249 | 0.789 → 0.854 | +0.065 [+0.031, +0.102] | 10% (11/109) → 17% (18/109) | +6% [+1%, +66%] | 0.880 |
| 9b json | 249 | 0.859 → 0.890 | +0.032 [-0.014, +0.074] | 0% (0/109) → 0% (0/109) | +0% [+0%, +0%] | 0.886 |
| 27b json | 246 | 0.924 → 0.990 | +0.066 [+0.036, +0.099] | 11% (12/107) → 57% (61/107) | +46% [+38%, +90%] | 0.964 |
| 4b jsonR | 249 | 0.851 → 0.909 | +0.058 [+0.015, +0.101] | 0% (0/109) → 0% (0/109) | +0% [+0%, +73%] | 0.894 |
| 9b jsonR | 248 | 0.861 → 0.905 | +0.043 [+0.001, +0.086] | 0% (0/109) → 58% (63/109) | +58% [-6%, +79%] | 0.904 |
| 27b jsonR | 248 | 0.940 → 0.980 | +0.040 [+0.021, +0.062] | 61% (66/108) → 76% (82/108) | +15% [+9%, +82%] | 0.962 |

### Rankings and cutoffs per request

| metric | run | 24-409 | 25-3152 | 25-3152 +roster |
|---|---|---|---|---|
| AUROC | 4b lp | 3 (0.964) | 7 (0.883) | 7 (0.950) |
| AUROC | 9b lp | 4 (0.962) | 4 (0.927) | 5 (0.963) |
| AUROC | 27b lp | 1 (0.992) | 2 (0.955) | 2 (0.989) |
| AUROC | d3-4b | 7 (0.880) | 6 (0.889) | 6 (0.961) |
| AUROC | d3-9b | 5 (0.960) | 3 (0.947) | 3 (0.979) |
| AUROC | d3-27b | 2 (0.992) | 1 (0.980) | 1 (0.998) |
| AUROC | Jev | 6 (0.936) | 5 (0.915) | 4 (0.968) |
| elim@98 | 4b lp | 5 (72%) | 7 (29%) | 6 (75%) |
| elim@98 | 9b lp | 3 (76%) | 4 (70%) | 7 (68%) |
| elim@98 | 27b lp | 2 (89%) | 2= (74%) | 2 (91%) |
| elim@98 | d3-4b | 7 (63%) | 6 (45%) | 4 (86%) |
| elim@98 | d3-9b | 4 (74%) | 2= (74%) | 3 (90%) |
| elim@98 | d3-27b | 1 (91%) | 1 (85%) | 1 (98%) |
| elim@98 | Jev | 6 (69%) | 5 (58%) | 5 (83%) |

| metric | Kendall tau 24-409 vs 25-3152 | 24-409 vs 25-3152 +roster |
|---|---|---|
| AUROC | +0.43 | +0.33 |
| elim@98 | +0.67 | +0.33 |

Share of bootstrap resamples in which the 24-409 AUROC exceeds the 25-3152 AUROC, per model: 4b lp 100%, 9b lp 97%, 27b lp 100%, d3-4b 40%, d3-9b 75%, d3-27b 96%, Jev 84%

| run | pooled thr98 | 24-409 own thr98 | 24-409 at pooled thr: recall / cleared | 25-3152 own thr98 | 25-3152 at pooled thr: recall / cleared |
|---|---|---|---|---|---|
| 4b lp | 0.265 | 0.3002 | 98.6% (142/144) / 66/102 | 0.221 | 97.9% (137/140) / 43/109 |
| 9b lp | 0.3309 | 0.2463 | 96.5% (139/144) / 81/102 | 0.4196 | 100.0% (140/140) / 68/109 |
| 27b lp | 0.06874 | 0.3623 | 100.0% (144/144) / 78/102 | 0.05664 | 96.4% (135/140) / 82/109 |
| d3-4b | 0.3507 | 0.3323 | 97.9% (141/144) / 64/102 | 0.3507 | 98.6% (138/140) / 49/109 |
| d3-9b | 0.3379 | 0.3051 | 97.2% (140/144) / 78/102 | 0.5427 | 99.3% (139/140) / 66/109 |
| d3-27b | 0.5857 | 0.8542 | 100.0% (144/144) / 74/102 | 0.5405 | 96.4% (135/140) / 97/109 |
| Jev | 0.34 | 0.57 | 100.0% (144/144) / 61/102 | 0.31 | 96.4% (135/140) / 72/109 |
| 4b json | 0.05 | 0.05 | 100.0% (144/144) / 9/102 | 0.05 | 99.3% (139/140) / 11/109 |
| 9b json | 0 | 0 | 100.0% (144/144) / 0/102 | 0 | 100.0% (140/140) / 0/109 |
| 27b json | 0.05 | 0.95 | 100.0% (144/144) / 46/102 | 0.05 | 100.0% (140/140) / 12/107 |
| 4b jsonR | 0 | 0 | 100.0% (144/144) / 0/102 | 0 | 100.0% (140/140) / 0/109 |
| 9b jsonR | 0 | 0 | 100.0% (144/144) / 0/102 | 0 | 100.0% (139/139) / 0/109 |
| 27b jsonR | 0.05 | 0.95 | 100.0% (144/144) / 73/102 | 0.05 | 98.6% (138/140) / 66/108 |

**What the data shows**

- **The correspondent-scoped request is harder for the stock Qwen models.** The CI for the AUROC
  gap excludes zero for the 4b lp (+0.081 [+0.032, +0.131]) and the 27b lp (+0.038 [+0.016, +0.066]). The 9b lp's
  gap is borderline (+0.035 [−0.001, +0.075]). For the d3 models and Jev the gap is small and not distinguishable
  from zero (d3-4b −0.008, d3-27b +0.012, Jev +0.021).
- **The gap is mostly in the hard negatives and correspondent-only positives. For the 4b lp and d3-4b, the real
  negatives also score higher on 25-3152.** [corrected in verification] Real-only AUROC is 0.964 or higher in
  both requests for every score model. But real-only elim@98 falls from 87% (52/60) to 38% (23/60) for the 4b lp
  and from 100% (60/60) to 63% (38/60) for the d3-4b ("Where the difference sits", D3-3). Their median real-negative score rises from
  0.136 to 0.224 and from 0.030 to 0.275 (`d_validity_verify.py` V9). On real+ vs hard−, the 27b lp drops from
  0.986 (24-409) to 0.878 (25-3152), the d3-27b from 0.979 to 0.937.
- **The roster closes the gap.**
  - ΔAUROC is +0.017 (d3-27b) to +0.073 (d3-4b), with every score model's CI above zero.
  - With the roster, 25-3152 AUROC comes close to or exceeds the 24-409 value for every score model (D3-4, last
    column): 27b lp 0.989 vs 0.992, d3-27b 0.998 vs 0.992, Jev 0.968 vs 0.936, d3-4b 0.961 vs 0.880, 4b lp 0.950
    vs 0.964.
  - elim@98 on 25-3152 rises to 91% (99/109) for the 27b lp and 98% (107/109) for the d3-27b. The 9b lp is the
    exception: 70% → 68%, Δ −2% [−12%, +9%].
- **Rankings move between requests.** Kendall tau between the 24-409 and 25-3152 rankings is +0.43 for AUROC
  (+0.33 with the roster). The 4b lp is 3rd of seven on 24-409 and 7th on 25-3152. The d3-27b and 27b lp are the
  top two in all three columns.
- **Each request wants a different cutoff.** The 27b lp's 98% cutoff is 0.3623 on 24-409 and 0.05664 on 25-3152;
  the d3-27b's is 0.8542 vs 0.5405; Jev's 0.57 vs 0.31. At the pooled cutoff, recall on 25-3152 is 96.4%
  (135/140) for the 27b lp, d3-27b and Jev, below the 98% target. Branch A treats setting a cutoff without the
  target's labels.

**What this implies for generalizing (interpretation).**

- **Request type is a factor of its own.** The two requests differ in kind: a topical request whose items name
  terms and custodians, against a request scoped by correspondents whose names the request doesn't list. The
  difference between them is as large as many of the model differences (for the 4b lp, larger), and it changes
  the ranking.
- **Two requests can't estimate request-to-request spread.** With one request of each type, there is no estimate
  of how much results vary between requests of the same type. Every model-level claim ("model X clears Y%") is
  conditional on these two requests.
- **The roster finding needs a second request.** It shows that correspondent-scoped requests need the names in
  the prompt, but it rests on one request, with a roster compiled partly from that request's own production
  (`data/golden/work/acpg_roster.json` lists the production among its sources).

## D4. Limitations register

Severity is my judgment of how much the limitation could change a conclusion someone would act on. "L-n" and
"Dn-n" point to the evidence tables in this document.

| # | limitation | evidence | conclusions it threatens | severity | what would fix it |
|---|---|---|---|---|---|
| 1 | Two requests, one county (San Diego), one of each type | D3-2: 4b lp AUROC 0.964 vs 0.883 (Δ +0.081 [+0.032, +0.131]); D3-5: Kendall tau 0.43 between the requests' rankings; D3-6: pooled cutoff gives 96.4% recall on 25-3152 for three models | any general claim about elimination, model ranking or cutoffs; H2 | high | more requests (SPEC §7.1 targeted ≥ 8) from several agencies, several of each type; report the per-request spread |
| 2 | Real negatives aren't search hits: other requests' records, almost all out of window, without the terms | D2-2/D2-3: 2/120 in window, 0/120 keyword-proxy hits, 118/120 pre-label rationales cite the window; D1-7: 70–90% of negatives cleared at the headline cutoff are real negatives | headline elim@98 (e); every "real-only" number (a, c), e.g. 27b lp 100% (120/120) | high | label a real search result set (in-window keyword or custodian hits, including unproduced mail); at least add the over-produced emails (D2-4b: 7 + 3) |
| 3 | Synthetic share; who wrote them | L-1: 225/495 synthetic, 91/211 negatives, every hard negative; written by Opus subagents (SPEC §14); verifier style tell mild 104/225, obvious 2/225 (D2-5) | elimination on hard negatives (b, d, f); recipe-level findings; anything that depends on how one model writes near misses | high | real near-miss negatives (row 2); some human-written edits; a second generator family to check that results don't depend on Opus's style |
| 4 | Hard-negative mix fixed by design (15–20 per recipe) | D1-8: the 27b lp clears 20–59% by recipe, the d3-27b 27–85%; the wrong-date recipe (20) is removable by a date filter | the level of elim@98 on hard negatives; the d3-27b vs 27b lp ordering (D1-7: 17/20 vs 10/20 wrong-date cleared) | medium | estimate the real recipe mix from a labeled search result set and reweight |
| 5 | One human adjudicator; model pre-labels; legal judgment calls | L-2: 0/81 disagreements in the spot check (one-sided 95% upper bound 3.6%; ≤ 6.7 expected errors among 185 unchecked real rows); 192/225 synthetic rows have no human call; 0 of 40 privileged and 0 of 40 exempt positives checked (D2-6); the owner's purely-personal call (findings-golden §9) decides several 25-3152 hard negatives | rates at 98% recall (5 misses allowed on 284 positives, so a few label errors move the cutoff); 25-3152 hard-negative results | medium | a second independent adjudicator on a sample (hard negatives, close calls, emails near each cutoff); report agreement |
| 6 | Real rows chosen for confident pre-labels | D2-6: 137/150 real positives high-confidence, against 185 high / 47 medium / 8 low among the pre-labeled production candidates; all 120 real negatives high-confidence | real-only metrics; real-positive recall (the easier positives were kept) | medium | a random sample of the production, adjudicated |
| 7 | Prompt 2 written after reading this set's misses (in-sample) | L-3: 4b lp ΔAUROC +0.023 [+0.008, +0.039] overall and +0.039 [+0.012, +0.065] on 25-3152; 27b lp +0.002 [−0.002, +0.006] overall, +0.011 [+0.003, +0.022] on 25-3152; d3 and Jev runs use the same prompt-2 rule | prompt-2 absolute numbers, mainly on 25-3152; the small models' default decisions | medium | held-out requests for prompt development (SPEC §7.6) |
| 8 | Cutoffs chosen on the same labels they're scored on | branch A quantifies; D3-6: per-request thr98 differ (27b lp 0.3623 vs 0.05664) | every elim@98 and the "98% recall" itself | high | branch A (cutoffs set without the target's labels) |
| 9 | One run per configuration | L-4: a second run with a different backend setting moves 4b lp scores by mean abs Δ 0.022 (max 0.171) and elim@98 52% → 47% at the same AUROC (0.923); 4–15 pairs cross the cutoff across the lp reruns; d3 is near-deterministic (mean abs Δ ≤ 0.0056); no second prompt-2 run of the 27b lp or Jev | elim@98 differences of a few points between close models | medium | repeat runs; report the run-to-run spread next to the bootstrap CI |
| 10 | Quantization and interface confound: d3 at Q8_0, stock Qwen at Q4_K_M | L-5: Q8_0 vs Q4_K_M; different runners (llamacpp vs ggml), endpoints (`/v1/systemone` vs chat logprobs) and prompt hashes; parameter counts 4.8B/9.0B/26.9B vs 4.7B/9.7B/27.3B | "the d3 architecture beats/loses to stock Qwen" (SPEC §14.1). d3-4b is worse than 4b lp despite the higher precision, so lower precision isn't what holds it back; d3-27b's small edge could be partly precision | medium | stock Qwen at Q8_0, or d3 at Q4_K_M (H5); same prompt wrapper |
| 11 | Jev scores rounded to 2 decimals | L-6: 94 distinct values; 308 of 59,924 (0.5%) positive–negative pairs tied; AUROC 0.914–0.919 under worst/best tie-breaking (reported 0.916); rounding the other runs to 2 decimals changes AUROC by at most 0.0002 and elim@98 by at most 1 email | little; only cutoffs finer than 0.01 are unavailable | low | none needed; ask the vendor for unrounded values if fine cutoffs matter |
| 12 | Jev's latency includes the network; records leave the agency | L-7: Jev median 117 ms (p10–p90 105–136), minimum 98 ms; correlation with prompt length ρ 0.37, against 0.92–1.00 for the local runs; network and compute can't be separated; all 495 golden emails were sent to `api.typesafe.ai`; SPEC §14.1 asks for a check of retention and training terms, and the repo has no record of one | Jev vs local latency comparisons; any deployment conclusion about Jev | medium (experiment); high for a deployment decision | timing from the same network position, or vendor server timing; legal review of the data terms before any real records are sent |
| 13 | Strix Halo only, one request at a time | L-8: concurrency 1 in all 26 run.json files; one machine | latency and throughput on other hardware; batched throughput (H6) | medium | laptop and batched runs (pending in findings-golden §12) |
| 14 | Latency depends on Ollama's prefix cache | L-7: without cache reuse (model reloaded every call), 4b lp prefill median 466 → 836 ms and 9b 774 → 1379 ms. The roster raises median prompt tokens 1836 → 3166, yet lp wall time doesn't rise (4b 450 → 446 ms, 27b 2340 → 2231 ms); d3 (no prefix reuse) nearly doubles (923 → 1739 ms; 4758 → 8550 ms) | lp vs d3 latency; roster cost; any deployment that interleaves requests or runs concurrently | medium | report cached and uncached latency; score emails grouped by request |
| 15 | Roster tested on one request; roster built partly from that request's production | D3-4: ΔAUROC +0.017 to +0.073 on 25-3152 (all score-model CIs above zero); `acpg_roster.json` sources include the 25-3152 production | "supply the member list" as a general recommendation | medium | a second correspondent-scoped request with a roster built only from the agency's own records |
| 16 | Body cut at 8,000 characters; attachments shown only by file name | L-9: 55/495 bodies over the cap (38 positives); truncated positives missed at the headline cutoff 0–2 of 38, other positives 1.2–2.0%; 272/495 have attachments; the adjudication sheet shows the full body and a link to the original file (`scripts/adjudication_sheet.py`), while the models saw only the first 8,000 characters | recall on long threads and attachment-borne records; the set has few such records, so the low miss rate may not carry over | low (measured); unknown for attachment content | chunk long bodies; extract attachment text (SPEC phase 2) |
| 17 | Synthetic emails are edits of emails also in the set (pairs not independent) | D2-7: 225 synthetic from 130 sources; L-10: 293 clusters; cluster-bootstrap CI widths equal to the pair bootstrap's within 0.002 AUROC and 2 points of elim@98 | the width of the bootstrap CIs | low | already checked (L-10); keep cluster resampling in future comparisons |
| 18 | Class balance unlike a search result | 284 positives of 495; the share of responsive emails among real search hits is unknown | precision and reviewer workload (branch B) | medium | measure prevalence in a real search result (row 2) |

## Findings

1. **Most of each model's headline elimination comes from real negatives that a date-limited search would not
   return.** 118 of 120 are outside the target's date window, 0 of 120 hit the keyword proxy, and they are 70–90%
   of the negatives cleared at each score model's 98% cutoff. *Confidence: high.* Tables D2-2, D2-3, D1-7.
2. **On real emails alone, the larger models separate almost perfectly** (9b lp, 27b lp, d3-9b, d3-27b: AUROC
   0.997–1.000, 96–100% of real negatives cleared). This measures date and topic separation, not screening a
   search result. *Confidence: high.* Tables D1-1, D1-2 (a).
3. **The synthetic hard negatives carry the difficulty; the synthetic positives don't.** (c) is within 0.007
   AUROC of (a); P(synthetic+ > real+) is 0.47–0.57; hard negatives outscore real negatives with probability
   0.87–0.99. *Confidence: high.* Tables D1-1, D2-8.
4. **Against in-window hard negatives** (subset f, 71 emails), elim@98 is 15–45%, against 52–81% in the headline.
   No score model clears 50% at the point estimate (best: 9b lp 45% [32–65%]). *Confidence: medium* (synthetic
   negatives, n = 71, 3 misses allowed). Table D1-2 (f).
5. **The model ranking depends on which negatives are counted.** d3-27b and 27b lp are the top two by AUROC in
   every subset. d3-27b's headline lead comes mostly from wrong-date emails (17/20 cleared vs 10/20), and on (f)
   the two are level (AUROC 0.923 vs 0.925, elim@98 41% vs 42%). The bottom three reorder between real-only and
   hard-negative subsets. *Confidence: medium* (point estimates; significance in branch E). Tables D1-4 to D1-8.
6. **The correspondent-scoped request is harder for the stock Qwen models, and the ranking moves between
   requests.** 4b lp ΔAUROC +0.081 [+0.032, +0.131] and 27b lp +0.038 [+0.016, +0.066]; d3 and Jev gaps are
   indistinguishable from zero; Kendall tau between the requests' rankings is 0.43. *Confidence: medium.* Tables
   D3-1, D3-2, D3-5.
7. **The roster helps every model on 25-3152** (ΔAUROC +0.017 to +0.073, all CIs above zero). It brings the large
   models to about their 24-409 level (27b lp 0.989 vs 0.992) or above it (d3-27b 0.998 vs 0.992). It was tested on one request, with a roster drawn partly from that
   request's production. *Confidence: medium.* Table D3-4.
8. **The 98% cutoff is request-specific.** 27b lp 0.3623 vs 0.05664; the pooled cutoff gives 96.4% recall (135/140)
   on 25-3152 for three models. *Confidence: high* for the fact; branch A for the remedy. Table D3-6.
9. **The synthetic emails read as real, are mostly small edits of real emails in the set, and their labels mostly
   rest on the generator's intent.** 9 of 10 hard negatives and 7 of 10 synthetic positives read as real on
   spot-read (judgment). The 3 tells among the synthetic positives were privileged emails. Median similarity to the
   source is 0.84–0.94 for close calls, exempt positives and hard negatives (privileged 0.65). 192 of 225 have no human call. *Confidence: medium.* Tables D2-5, D2-6, D2-7, spot-read.
10. **The repo has no real near-miss negatives to substitute.** No other production has an in-window keyword hit
    for either request (D2-4). The over-produced emails (7 and 3) were left out by the build (D2-4b).
    *Confidence: high* for the proxy as defined; a broader search definition could find some.
11. **Several suspected limitations are small here.**
    - Jev's rounding: AUROC 0.914–0.919 under any tie-breaking; rounding other runs moves AUROC by ≤ 0.0002.
    - Near-duplicate clustering: cluster-bootstrap CIs are barely wider (≤ 0.002 AUROC, ≤ 2 points of elim@98).
    - Truncation: 0–2 of 38 truncated positives missed.

    *Confidence: high* for rounding and clustering; medium for truncation, because attachment content was never
    tested. Tables L-6, L-10, L-9.
12. **A second run moves elim@98 by a few points.** 4b lp 52% vs 47% at an unchanged AUROC of 0.923 with a
    different batch setting; d3 reruns are near-identical. *Confidence: medium.* Table L-4.
13. **Latency depends on caching.**
    - The lp runs absorb the roster at no wall-time cost through Ollama's prefix cache; the d3 runs nearly double.
    - Jev's 117 ms barely depends on prompt length (ρ 0.37), consistent with a fixed overhead such as the
      network. It can't be compared directly with local compute times.

    *Confidence: medium.* Table L-7.

## Caveats

- **The keyword proxy and the date-window logic are mine,** not the county's search. Both requests specify date
  windows; whether a real search applies them strictly is an assumption. The proxy finds 147 of 150 real
  positives, but a broader real search (for example, whole custodian mailboxes) would return emails the proxy
  misses.
- **Proxy choice and spot-read are judgment.** Subset (f) as the deployment proxy and the realism codes are my
  calls, recorded in the scripts so they can be checked and disputed.
- **Small subsets.** (f) has 71 negatives, and 98% recall on 150 real positives allows 3 misses, so elim@98 on
  the small subsets moves in steps of a few emails. The intervals in D1-2 are wide.
- **Results are conditional on the setup.** Everything comes from the saved runs: one prompt (2), one Ollama
  version (0.40.13), one machine.
- **The Jev data-terms row reports an absence:** the repo has no record of the terms check that SPEC §14.1 asks
  for. I didn't review the vendor's terms.
- **The d3 statements about noncausal attention and no prefix-cache reuse come from the branch brief.** Table
  L-7's d3 roster timings are consistent with them.
- **Scope.** Pairwise significance of model differences (branch E), cutoff transfer (branch A) and reviewer
  workload (branch B) are referenced, not redone.

## Reproduce

Run from the project root; each finishes in under 20 seconds on the Strix Halo (timed, in table order: 10.4 s,
16.5 s, 0.1 s, 4.8 s, 5.7 s).

| command | prints |
|---|---|
| `uv run python scripts/analysis/d_validity_subsets.py [--boot 1000]` | D1-0 … D1-9 (subset sizes, AUROC, elim@98, cutoffs, ranks, P(best), Kendall tau, headline split, recipes, ranges) |
| `uv run python scripts/analysis/d_validity_realism.py` | D2-0 … D2-8 (real candidates, recipes, real-negative sources, features by kind, keyword-hit pool, over-production, verifier, label checks, edit size, synthetic vs real scores) |
| `uv run python scripts/analysis/d_validity_spotread.py [--full \| --notes]` | the 30-email spot-read sample with my notes and the tally (`--notes`: the table above) |
| `uv run python scripts/analysis/d_validity_requests.py [--boot 1000]` | D3-0 … D3-6 (composition, per request, difference, request × subset, roster, ranks, cutoffs) |
| `uv run python scripts/analysis/d_validity_limits.py [--boot 1000]` | L-1 … L-10 (the register's evidence) |

`scripts/analysis/d_validity_common.py` holds the run list, subset definitions, date parsing and bootstrap helpers
shared by the scripts.

## Appendix: register evidence tables

### L-1. Synthetic share

| group | request | n | synthetic |
|---|---|---|---|
| all pairs | both | 495 | 225/495 (45%) |
| all pairs | 24-409 | 246 | 111/246 (45%) |
| all pairs | 25-3152 | 249 | 114/249 (46%) |
| positives | both | 284 | 134/284 (47%) |
| positives | 24-409 | 144 | 69/144 (48%) |
| positives | 25-3152 | 140 | 65/140 (46%) |
| negatives | both | 211 | 91/211 (43%) |
| negatives | 24-409 | 102 | 42/102 (41%) |
| negatives | 25-3152 | 109 | 49/109 (45%) |

### L-2. Label checking

| quantity | value |
|---|---|
| random spot check of Opus/production agreements: human disagreed | 0/81 |
| one-sided 95% upper bound on the disagreement rate (exact, 0 events) | 3.6% |
| real rows with no human call (label = production membership + agreeing Opus pre-label) | 185/270 |
|   expected label errors among them at that upper bound | ≤ 6.7 |
| synthetic rows with no human call (label = generator's intent + verifier agreement) | 192/225 |
| adjudicators | 1 (the project owner) |

### L-3. Prompt 1 → 2 (in-sample gain)

Prompt 1 → 2 on the same Ollama 0.40.13, render 2 and batch setting; paired bootstrap over pairs (stratified by label).

| model | request | pairs | AUROC prompt 1 → 2 | ΔAUROC [paired 95% CI] | elim@98 prompt 1 → 2 |
|---|---|---|---|---|---|
| 4b lp (batch 8192) | both | 495 | 0.900 → 0.923 | +0.023 [+0.008, +0.039] | 48% → 47% |
| 4b lp (batch 8192) | 24-409 | 246 | 0.953 → 0.964 | +0.011 [-0.002, +0.024] | 71% → 63% |
| 4b lp (batch 8192) | 25-3152 | 249 | 0.846 → 0.885 | +0.039 [+0.012, +0.065] | 34% → 27% |
| 9b lp (batch 8192) | both | 495 | 0.937 → 0.943 | +0.005 [-0.008, +0.019] | 68% → 72% |
| 9b lp (batch 8192) | 24-409 | 246 | 0.957 → 0.964 | +0.007 [-0.003, +0.018] | 75% → 80% |
| 9b lp (batch 8192) | 25-3152 | 249 | 0.916 → 0.927 | +0.011 [-0.010, +0.031] | 60% → 69% |
| 27b lp (default batch) | both | 495 | 0.974 → 0.975 | +0.002 [-0.002, +0.006] | 77% → 76% |
| 27b lp (default batch) | 24-409 | 246 | 0.994 → 0.992 | -0.001 [-0.004, +0.002] | 87% → 89% |
| 27b lp (default batch) | 25-3152 | 249 | 0.943 → 0.955 | +0.011 [+0.003, +0.022] | 71% → 74% |

### L-4. Second runs

Each row compares a main run with another saved prompt-2 run of the same model on the same pairs. The settings differ as noted (batch size, or unloading the model before every call), so this is an upper bound on pure repeat noise for those backends.

lp reruns: pairs crossing the main cutoff 4–15; d3 reruns: largest mean abs Δ 0.0056

| model | second run | pairs | identical (abs Δ < 1e-6) | mean abs Δ | max abs Δ | pairs crossing main thr98 | AUROC main / second | elim@98 main / second |
|---|---|---|---|---|---|---|---|---|
| 4b lp | default batch: cached vs reloaded every call | 495 | 29 | 0.0178 | 0.175 | 11 | 0.923 / 0.921 | 52% / 53% |
| 4b lp | default batch vs batch 8192 | 495 | 36 | 0.0221 | 0.171 | 15 | 0.923 / 0.923 | 52% / 47% |
| 9b lp | default batch: cached vs reloaded every call | 495 | 8 | 0.0229 | 0.153 | 6 | 0.942 / 0.945 | 71% / 72% |
| 9b lp | default batch vs batch 8192 | 495 | 4 | 0.0223 | 0.299 | 4 | 0.942 / 0.943 | 71% / 72% |
| d3-4b | cached vs reloaded every call (60 pairs) | 60 | 36 | 0.0021 | 0.016 | 0 | — | — |
| d3-9b | cached vs reloaded every call (60 pairs) | 60 | 36 | 0.0016 | 0.022 | 1 | — | — |
| d3-27b | cached vs reloaded every call (60 pairs) | 60 | 36 | 0.0002 | 0.004 | 0 | — | — |
| d3-4b +roster | cached vs reloaded (30 pairs) | 30 | 0 | 0.0056 | 0.027 | — | — | — |
| d3-27b +roster | cached vs reloaded (30 pairs) | 30 | 0 | 0.0001 | 0.001 | — | — | — |

### L-5. Quantization and runtime

| run | tag | model | parameters | quantization | runner | endpoint | Ollama | prompt hash |
|---|---|---|---|---|---|---|---|---|
| 4b lp | golden_qwen3.5_4b_logprob_p2db | qwen3.5:4b | 4.7B | Q4_K_M | ggml | ollama /api/chat | 0.40.13 | a3f2517bf66116f0 |
| 9b lp | golden_qwen3.5_9b_logprob_p2db | qwen3.5:9b | 9.7B | Q4_K_M | ggml | ollama /api/chat | 0.40.13 | a3f2517bf66116f0 |
| 27b lp | golden_qwen3.8_27b_logprob_p2 | qwen3.8:27b-q4_K_M | 27.3B | Q4_K_M | ggml | ollama /api/chat | 0.40.13 | a3f2517bf66116f0 |
| d3-4b | golden_d3-ctx8k_4b_noul_p2 | d3:4b | 4.8B | Q8_0 | llamacpp | ollama | 0.40.13 | 7007d3770b272b10 |
| d3-9b | golden_d3-ctx8k_9b_noul_p2 | d3:9b | 9.0B | Q8_0 | llamacpp | ollama | 0.40.13 | 7007d3770b272b10 |
| d3-27b | golden_d3-ctx8k_27b_noul_p2 | d3:27b | 26.9B | Q8_0 | llamacpp | ollama | 0.40.13 | 7007d3770b272b10 |
| Jev | golden_jev-1.14.0_noul_p2 | jev-1.14.0 | — | — (hosted) | — | typesafe-api | — | 7007d3770b272b10 |

### L-6. Jev rounding

| quantity | value |
|---|---|
| distinct score values (of 495) | 94 |
| most decimals in any score | 2 |
| most common values | 0.86×15, 0.95×14, 0.83×14, 0.78×13, 0.84×13, 0.92×12 |
| (positive, negative) pairs tied | 308/59924 (0.5%) |
| AUROC with ties counted half (reported) | 0.916 |
| AUROC range if ties were broken worst / best | 0.914 – 0.919 |
| 98% cutoff; emails scored exactly at it (pos/neg) | 0.34; 1/0 |

The same rounding applied to the other score runs (score → round(score, 2)):

| run | distinct values | after rounding | AUROC | elim@98 (k cleared of 211) |
|---|---|---|---|---|
| 4b lp | 495 | 88 | 0.9228 → 0.9231 | 51.7% (109) → 51.7% (109) |
| 9b lp | 495 | 93 | 0.9424 → 0.9423 | 70.6% (149) → 70.6% (149) |
| 27b lp | 495 | 73 | 0.9754 → 0.9752 | 75.8% (160) → 75.8% (160) |
| d3-4b | 494 | 90 | 0.8842 → 0.8840 | 53.6% (113) → 53.1% (112) |
| d3-9b | 494 | 95 | 0.9470 → 0.9471 | 68.2% (144) → 68.2% (144) |
| d3-27b | 494 | 78 | 0.9795 → 0.9796 | 81.0% (171) → 81.0% (171) |
| Jev | 94 | 94 | 0.9164 → 0.9164 | 63.0% (133) → 63.0% (133) |

Largest change from rounding: AUROC 0.0002; negatives cleared at 98% recall 1

### L-7. Latency

wall_ms = request to response as the scorer saw it (median; p10–p90). Prompt tokens are each backend's own count. Spearman ρ = rank correlation of wall time with prompt tokens over the 495 pairs (near 1: time scales with the email; low: a fixed cost such as the network dominates).

ρ(wall, prompt tokens) for the six local runs: 0.92–1.00

| run | wall ms median (p10–p90) | min wall ms | median prompt tokens | ρ(wall, prompt tokens) | 25-3152 wall ms: without → with roster | 25-3152 prompt tokens: without → with roster |
|---|---|---|---|---|---|---|
| 4b lp | 504 (191–1172) | 48 | 1797 | 0.92 | 450 → 446 | 1836 → 3166 |
| 9b lp | 856 (340–1996) | 60 | 1797 | 0.93 | 772 → 734 | 1836 → 3166 |
| 27b lp | 2649 (1045–6416) | 154 | 1797 | 0.93 | 2340 → 2231 | 1836 → 3166 |
| d3-4b | 877 (530–1826) | 390 | 1872 | 0.99 | 923 → 1739 | 1914 → 3247 |
| d3-9b | 1426 (871–2740) | 642 | 1872 | 1.00 | 1467 → 2639 | 1914 → 3247 |
| d3-27b | 4667 (2934–8782) | 2061 | 1872 | 1.00 | 4758 → 8550 | 1914 → 3247 |
| Jev | 117 (105–136) | 98 | 2037 | 0.37 | 118 → 125 | 2079 → 3473 |

Ollama prefix cache (lp runs): the same model and prompt with the model kept loaded (cache can reuse the shared request prefix) vs unloaded before every call (no reuse). Server-side prefill_ms and wall_ms medians.

| run | prefill ms: cached → reloaded | wall ms: cached → reloaded |
|---|---|---|
| 4b lp | 466 → 836 | 504 → 2503 |
| 9b lp | 774 → 1379 | 856 → 3482 |

Jev endpoint (run.json): https://api.typesafe.ai/v1/systemone; records were sent to a third-party API. Scores carry 495 TypeSafe request ids.

### L-8. Concurrency

| concurrency value in run.json | runs |
|---|---|
| 1 | 26 |

### L-9. Truncation and attachments

Bodies over 8,000 characters (the model sees the first 8,000): 55/495 (positives 38/284, negatives 17/211). Rows flagged truncated in the 27b lp scores: 55.

Truncated positives missed: 0–2 of 38; other positives missed: 1.2%–2.0%

| run | all-pairs thr98 | truncated positives missed | other positives missed | the two positives whose hook is past the cap (score) |
|---|---|---|---|---|
| 4b lp | 0.265 | 2/38 (5%) | 3/246 (1.2%) | s:25-3152:14:02 0.754, s:24-409:02:01 0.747 |
| 9b lp | 0.3309 | 2/38 (5%) | 3/246 (1.2%) | s:25-3152:14:02 0.948, s:24-409:02:01 0.588 |
| 27b lp | 0.06874 | 0/38 (0%) | 5/246 (2.0%) | s:25-3152:14:02 0.651, s:24-409:02:01 0.266 |
| d3-4b | 0.3507 | 2/38 (5%) | 3/246 (1.2%) | s:25-3152:14:02 0.530, s:24-409:02:01 0.261 MISSED |
| d3-9b | 0.3379 | 0/38 (0%) | 5/246 (2.0%) | s:25-3152:14:02 0.888, s:24-409:02:01 0.355 |
| d3-27b | 0.5857 | 0/38 (0%) | 5/246 (2.0%) | s:25-3152:14:02 0.720, s:24-409:02:01 0.750 |
| Jev | 0.34 | 0/38 (0%) | 5/246 (2.0%) | s:25-3152:14:02 0.620, s:24-409:02:01 0.630 |

Emails with attachments (rendered as file names only): 272/495. Positives whose only keyword-proxy hit outside the headers is in an attachment name: 2 (sandiego:24-409:33733308, sandiego:25-3152:48517842).

### L-10. Cluster bootstrap

Cluster = a source email and every golden pair built from it (its own real row(s) and its synthetic edits), across both requests. Resampling clusters instead of pairs treats near-duplicates as one draw. 95% CIs, 1000 resamples each.

Clusters: 293 for 495 pairs; sizes: 1×171, 2×69, 3×34, 4×13, 5×4, 6×2

| run | AUROC | pair bootstrap CI (width) | cluster bootstrap CI (width) | elim@98 | pair bootstrap CI (width) | cluster bootstrap CI (width) |
|---|---|---|---|---|---|---|
| 4b lp | 0.923 | [0.897–0.946] (0.050) | [0.898–0.946] (0.049) | 52% | [40%–72%] (32 pts) | [41%–73%] (32 pts) |
| 9b lp | 0.942 | [0.919–0.961] (0.041) | [0.920–0.962] (0.042) | 71% | [64%–79%] (15 pts) | [64%–79%] (15 pts) |
| 27b lp | 0.975 | [0.963–0.987] (0.024) | [0.963–0.985] (0.022) | 76% | [71%–88%] (18 pts) | [71%–88%] (17 pts) |
| d3-4b | 0.884 | [0.853–0.912] (0.059) | [0.853–0.912] (0.059) | 54% | [43%–63%] (20 pts) | [43%–63%] (20 pts) |
| d3-9b | 0.947 | [0.925–0.965] (0.039) | [0.926–0.965] (0.039) | 68% | [62%–79%] (18 pts) | [61%–81%] (20 pts) |
| d3-27b | 0.979 | [0.969–0.988] (0.019) | [0.970–0.987] (0.018) | 81% | [74%–87%] (12 pts) | [75%–87%] (12 pts) |
| Jev | 0.916 | [0.889–0.938] (0.049) | [0.890–0.941] (0.051) | 63% | [55%–69%] (14 pts) | [55%–70%] (15 pts) |

Largest difference in CI width, cluster vs pair: AUROC 0.002; elim@98 2 points

## Verification

**Skeptic's pass, 2026-11-06.** Script: `scripts/analysis/d_validity_verify.py` (run with
`uv run python scripts/analysis/d_validity_verify.py`; about 4 s; two runs gave byte-identical output). It imports
nothing from the `d_validity_*` scripts. It has its own run loader and label join, its own AUROC (counting every
positive–negative pair), thr98 (the m-th highest positive score, m = ceil(0.98 × positives), in integers) and
elim@98, its own date parser and keyword proxy, and its own bootstrap with different seeds and 2,000 resamples. The
repo helpers in `scripts/analyze.py` are imported only to cross-check those metrics. Labels "V0"–"V14" refer to
sections of its output.

### Checks

| # | claim or method point | how checked | result |
|---|---|---|---|
| 1 | Every table matches the scripts | Reran the five scripts and compared every table line in this document with their output | **Confirmed.** Outputs are byte-identical to the analyst's saved outputs, and every data-table line appears verbatim. The run list, the register (D4) and the Reproduce table are hand-written; each register number matches L-1…L-10 or D1–D3. |
| 2 | Labels from `pairs.jsonl`; the right runs | V0: own loader | **Confirmed.** No main or roster run has a stale label or an unknown `pair_id`, so the join rule changes nothing here. The run tags match the brief. |
| 3 | Unscored JSON rows dropped and reported | V0 | **Corrected.** There are 5 unscored rows, not 4: the list in "Data and method" omitted the 27b json roster row. |
| 4 | AUROC, thr98, elim@98; flagged = score ≥ cutoff | V1: from-scratch metrics vs the repo helpers | **Confirmed.** Identical to 4 decimals for all seven score models. The headline AUROC/elim@98 match the brief (0.923/52% … 0.916/63%). |
| 5 | Subsets (a) and (f); (f) = the in-window hard negatives | V2 | **Confirmed.** Point estimates reproduce D1-1/D1-2. My own date parse picks the same 71 hard negatives as the recipe rule. |
| 6 | Real negatives are 70–90% of the negatives cleared at the headline cutoff | V3 | **Confirmed** (70.2%–90.3%). For context: real negatives are 120/211 (56.9%) of all negatives, so a model that cleared both kinds at the same rate would show 57%. Only the excess over 57% shows that real negatives are easier. |
| 7 | 118/120 real negatives fall outside the window | V4 | **Confirmed, with a precision note.** 117 are dated outside, 2 inside, and 1 has no date (24-409\|sandiego:25-5982:55059062; its body mentions only 2025). The 118 counts that one by its body. |
| 8 | d3-27b's headline lead over 27b lp comes mostly from wrong-date emails | V3 | **Confirmed.** 171 vs 160 cleared: real 120 vs 120, wrong-date 17 vs 10, in-window 34 vs 30. So 7 of the 11-email lead is wrong-date. |
| 9 | Request gap (D3-2): 4b lp and 27b lp CIs exclude 0 | V5: independent bootstrap; Bonferroni correction for 7 tests | **Confirmed.** Own intervals agree within 0.003. Both still exclude 0 at 99.29%: 4b lp [+0.020, +0.146], 27b lp [+0.005, +0.075]. |
| 10 | "Stock Qwen do worse on 25-3152; d3 and Jev show no clear gap" | V6b: difference of the two models' gaps, same resamples | **Partly supported.** The gap is larger for stock Qwen than for d3 at 4b (+0.089 [+0.034, +0.148]) and at 27b (+0.026 [+0.010, +0.045]), but not at 9b (+0.022 [−0.013, +0.059]). The 9b lp's own gap isn't significant. The document calls the 9b lp's gap "borderline" (97% of resamples positive, D3-5) and the d3-27b's "not distinguishable from zero" (96%), but the two are equally borderline. |
| 11 | Model rankings agree only weakly between requests (Kendall tau 0.43) | V6: interval and a noise baseline | **Confirmed, with an interval.** tau +0.43 [+0.24, +0.81]. Two independent resamples of the same request give a median tau of +0.81, and only 0.1% (24-409) and 0.8% (25-3152) of such pairs fall at or below 0.43. So the change in ranking is more than resampling noise. Single-rank statements are not supported, though: "4b lp is 3rd on 24-409" rests on 4b lp 0.9643 vs 9b lp 0.9619 vs d3-9b 0.9600. |
| 12 | "The gap is in the hard negatives and correspondent-only positives, not the real negatives" (D3) | V9 | **Refuted for the 4b lp and d3-4b; corrected in place.** On 25-3152 their median real-negative score is higher (0.136 → 0.224; 0.030 → 0.275). At the 24-409 real-only cutoff, they would clear only 34/60 and 41/60 of the 25-3152 real negatives. For Jev the drop comes from the positives: its 24-409 cutoff would clear 60/60. |
| 13 | The roster helps every model, compared over the right pairs | V7 | **Confirmed.** All 249 roster pairs are 25-3152 pairs and are shared with the main runs. Deltas and CIs reproduce, and all seven stay above zero after Bonferroni (lowest lower bound +0.005, for the 9b lp and the d3-27b). |
| 14 | Jev ties | V8 | **Confirmed.** 94 distinct values; 308/59,924 tied pairs; AUROC 0.9164 (ties half), 0.9138 to 0.9190 (worst/best). |
| 15 | On (f), the 9b lp, 27b lp and d3-27b are "level" | V10: cutoff at 2, 3 or 4 allowed misses | **Confirmed as "level"; no order among them holds.** One more allowed miss moves elim by up to 6 emails (d3-9b 22 → 28 of 71). At 4 misses, the 9b lp and d3-27b tie at 33/71, ahead of the 27b lp's 30. |
| 16 | The proxy finds 147/150 real positives, "so it roughly tracks what the productions contain" | V11 | **Concern (circular for 25-3152).** All 75 of the 25-3152 real positives contain a roster email address, and the roster's sources include the 25-3152 production itself. The group name alone finds 41/75. For 25-3152 the 147/150 figure is largely true by construction, not an independent check. My own reimplementation of the proxy reproduces 147/150 and 35/91 (V12). |
| 17 | Subset (f) is the conservative deployment proxy | V12: a stricter search-like subset | **Judgment unchanged, but (f) isn't a floor.** Against the 35 hard negatives that are in window *and* hit the proxy, elim@98 is 9%–34% (3/35 to 12/35) and AUROC 0.608–0.914. That's below (f)'s 15–45%, on a subset too small to rank models. |
| 18 | Synthetic positives score like real ones; hard negatives carry the difficulty | V2 | **Confirmed.** Largest \|AUROC (c) − AUROC (a)\| is 0.0068; P(synthetic+ > real+) 0.47–0.57; P(hard− > real−) 0.87–0.99. Caveat: on (a) and (c) AUROC is near its ceiling (≥ 0.982), so "within 0.007" says little on its own. The P(synthetic+ > real+) comparison carries that claim. |
| 19 | L-3 and L-4 compare like with like | V13: run.json | **Confirmed.** Prompt 1 vs 2 pairs share Ollama 0.40.13, render 2 and num_batch. The d3 reruns differ from the main runs only in the reload (`fresh`). |
| 20 | Spot-read notes | V14: three factual notes checked | **Confirmed:** 19:09's body is identical to its source; 14:02's first edit is at character 8,768 (past the 8,000 cap); 03:01 has verifier label_correct = False and Geosyntec in the headers. The realism codes are judgment: **unverifiable** by script. |
| 21 | How the set was built (D2) | `scripts/build_golden.py` | **Corrected.** The positive-source rule has an exception (an other-production email the human called responsive), which no row uses. |
| 22 | SPEC and code facts | Read SPEC §7.1, §7.3, §14, §14.1; `scripts/score.py`; `acpg_roster.json` | **Confirmed.** Opus subagents wrote the synthetic emails (§14); §7.1 asks for about 8 or more requests; `MAX_BODY_CHARS = 8000`; the roster's sources include the 25-3152 production. |
| 23 | The repo has no record of the Jev terms check | grep of the repo's Markdown | **Confirmed for the repo.** A copy of the vendor's legal index page sits in this session's scratchpad (not in the repo). It points to a data processing agreement and a privacy policy, mentions a commitment not to train on user data, and says zero data retention is offered to enterprise customers. I didn't review those terms either, so row 12 stands. SPEC §14.1 also notes that the golden set is public records plus synthetic edits; the data-terms issue is about deployment, not this experiment. |
| 24 | Multiple comparisons | V5, V7 | **Confirmed for the claims made.** The document reports many CIs (13 runs × 6 subsets × 2 metrics) without correction, but only two kinds of claim are significance claims (the D3-2 request gap and the D3-4 roster deltas). Both survive Bonferroni. |
| 25 | In-sample cutoffs | — | **Applies throughout.** Every elim@98 here, (f) and V12 included, uses a cutoff chosen on the labels it's scored on (register row 8; branch A). |

### Corrections made in this document

1. **Data and method:** added the fifth unscored row (27b json roster, 25-3152|synth:25-3152:12:03).
2. **D2, How the set was built:** the positive-source rule now notes the build's exception, which no row uses.
3. **D3, What the data shows:** the bullet that put the 25-3152 gap "not in the real negatives" now says that, for the
   4b lp and d3-4b, the real negatives also score higher on 25-3152, with the numbers.

No script caused these errors. The tables were right, and the three statements were prose written around them.
I changed no conclusion I merely disagree with; those are listed below.

### Remaining concerns

- **"Real emails alone nearly solved" is a pooled result.** Subset (a) pools both requests. For 25-3152 alone,
  the 4b lp clears 23/60 of the real negatives, the d3-4b 38/60 and Jev 46/60 (D3-3). For small models, a
  correspondent-scoped request isn't easy even on real negatives, because they can't tell members from non-members.
- **The stock Qwen vs d3 contrast holds at 4b and 27b, not at 9b** (check 10). The d3-27b's AUROC is near its
  ceiling (0.992 and 0.980), which leaves little room for a gap. The short answer's "the stock Qwen models do worse"
  should be read as "the 4b lp and 27b lp do".
- **The keyword proxy is circular for 25-3152** (check 16). The real negatives' 0/120 proxy hits are unaffected, but
  the 147/150 check doesn't validate the proxy for that request.
- **Subset (f) is one defensible proxy, not the conservative end** (check 17). A stricter search-like subset gives
  lower elimination, on only 35 emails. Both (f) and that subset were defined after looking at the data.
- **The cluster bootstrap (L-10) clusters only synthetic edits with their source emails.** Real emails from the
  same thread aren't grouped, and 84/150 real positives quote a thread (D2-3). The "pairs are nearly independent"
  conclusion covers the synthetic-source link only.
- **Prefix-cache attribution (L-7).** The "reloaded" runs unload the model before every call, so their slower
  prefill may include cold-start costs as well as lost prefix reuse. The data doesn't separate the two.
- **Table labels.** The text cites D1-n, D2-n and D3-n, but those labels exist only in the script output; the D1–D3
  tables here carry plain headings. The mapping, by heading:

| label | table in this document |
|---|---|
| D1-0 … D1-3 | subset sizes; AUROC by subset; Eliminated at 98% recall; the cutoff table ("Positives set the 98% cutoff") |
| D1-7, D1-8 | Where the headline elimination comes from; Hard negatives by recipe |
| D1-4, D1-5, D1-6 | under "Does the model ranking change?": ranks; P(best); Kendall tau and the best-first orders |
| D1-9 | the ranges table |
| D2-0, D2-1 | the candidates table and the recipe table under "How the set was built" |
| D2-2, D2-3 | The real negatives; Features by kind (with the recipe table) |
| D2-4, D2-4b | the two tables under "Is there real material for harder real negatives?" |
| D2-5 … D2-8 | under "Checks on the synthetic emails and the labels": verifier; the three label-check tables; similarity and source tables; the P(synthetic > real) tables |
| D3-0 … D3-2 | composition tables; Per request (first and second tables) |
| D3-3, D3-4 | Where the difference sits; With the roster |
| D3-5, D3-6 | under "Rankings and cutoffs per request": ranks, Kendall tau and resample shares; the pooled vs own cutoff table |
