# E. Which model differences are real, the speed/accuracy frontier, and calibration

> **Snapshot of 2026-11-06, on the 2026-10-31 labels (495 pairs).** The labels changed afterwards: five hard
> negatives were relabeled responsive on 2026-11-08, and one email (24-409 synthetic 07:09) was put back in the set
> on 2026-11-11 (`docs/findings-golden.md` §9). The tables below are copies of script output on the old labels.
> Rerun the commands in the Reproduce section for current numbers; the scripts now read the pair counts from the
> golden set (`scripts/analysis/golden_counts.py`). `docs/findings-golden.md` carries the current figures, and
> `conclusions.md` section 0 lists what the relabeling changed.

**Date:** 2026-11-06 · **Branch:** E of the golden-set analysis · **Inputs:** saved runs only (no model, GPU or network calls)
**Scripts:** `scripts/analysis/e_comparisons_{pairwise,recipes,frontier,calibration,packaging}.py`, with shared helpers in `e_comparisons_common.py`. Every table below is pasted verbatim from their output (see Reproduce). Numbers in the prose are copied from those tables.

## The question

The golden-set report ranks seven scoring models on the same 495 (request, email) pairs. This branch asks
two things. First, which of the gaps between them are bigger than the noise you get from a 495-pair test
set? Second, given how long each takes per email, which configurations are worth running? There are five parts:

- **E1.** All 21 pairwise differences in AUROC and in elim@98, on the main set and on the 25-3152 roster set, with a correction for testing many pairs at once.
- **E2.** The hard-negative recipes, especially *same subject, wrong date*: is "d3-27b handles dates and Jev doesn't" supported, and does it depend on the cutoff?
- **E3.** Speed against accuracy: which configurations are on the Pareto frontier? Jev, the only hosted option, is treated separately.
- **E4.** Calibration: can the scores be read as probabilities?
- **E5.** Stock Qwen against d3 at each size: where d3 helps, what is confounded, and where its extra latency comes from.

## Short answer

- **Main set, AUROC: three tiers.** 27b lp and d3-27b are at the top; they can't be told apart
  (+0.004 [−0.004, +0.013]). In the middle are 9b lp, d3-9b, 4b lp and Jev: no pair among the four
  survives the multiplicity correction. d3-4b is at the bottom. **elim@98 is much noisier.** Only 8 of
  its 21 differences survive the correction, mostly the 27b models against the weakest ones.
- **"d3-27b handles wrong-date emails and Jev doesn't" holds up** at every cutoff tried, without a
  cutoff, and when the cutoff is re-estimated in every bootstrap resample. **"d3-27b handles dates
  better than the stock 27b" does not.** They tie at the 0.5 cutoff (3 vs 3 of 20 pass), and without a
  cutoff they separate wrong-date emails from responsive ones about equally well (0.988 vs 0.976,
  p 0.15). The gap at each model's 98%-recall cutoff comes from where the 27b lp's cutoff happens to
  fall.
- **Local frontier: 4b lp → 9b lp → 27b lp → d3-27b.** The JSON modes are never on it in E3c's
  2,000 main-set resamples (4 of 2,000 for 27b json in an independent check; on 25-3152, 27b json
  +roster is on the frontier in 31–48% of resamples) [corrected in verification]. Jev, the only
  hosted option, is the fastest by far: the fastest local configuration, the 4b lp, takes 4.3× its median time per email. The only local models that beat Jev
  on both metrics after the correction are the two 27b models, at 22.7× and 40.0× its median time.
- **No model's score is a calibrated probability in the strict sense.** In every model the fitted
  calibration slope is significantly different from 1. The 27b lp comes closest. The d3-27b overstates
  in its middle range. The golden set is 57.4% responsive by design, so even a score that is calibrated
  here would overstate the probability in a request where fewer emails are responsive.
- **d3 vs stock Qwen, same base model.** At 27b, d3 helps on the correspondent-scoped request 25-3152;
  with the roster it also helps at 9b and 27b. At 4b it hurts on the topical request 24-409. Elsewhere
  no difference is detectable. Quantization (Q8_0 vs Q4_K_M), runner and prompt packaging change
  together with the model, so the runs can't say which of them causes a difference.
  **Latency:** without a prefix cache, the d3 and stock calls take about the same time (median per-pair
  ratio 1.07 at 4b, 1.06 at 9b). d3's 1.67–1.76× slowdown against cached stock is mostly the lost
  cache (checked directly at 4b and 9b; there is no uncached stock 27b run). On longer prompts a
  residual gap remains.

## Data and method

### Runs and pairs

**Table E0.** Runs read by the branch-E scripts. 'scored' = rows with a score whose pair_id is in data/golden/pairs.jsonl; 'unscored' = rows with no score (JSON parse failures), dropped.

| label | run (main; the roster twin adds _roster) | model | quantization | main: scored / unscored | roster: scored / unscored |
|---|---|---|---|---|---|
| 4b lp | `golden_qwen3.5_4b_logprob_p2db` | qwen3.5:4b | Q4_K_M | 495 / 0 | 249 / 0 |
| 9b lp | `golden_qwen3.5_9b_logprob_p2db` | qwen3.5:9b | Q4_K_M | 495 / 0 | 249 / 0 |
| 27b lp | `golden_qwen3.8_27b_logprob_p2` | qwen3.8:27b | Q4_K_M | 495 / 0 | 249 / 0 |
| d3-4b | `golden_d3-ctx8k_4b_noul_p2` | d3-ctx8k:4b | Q8_0 | 495 / 0 | 249 / 0 |
| d3-9b | `golden_d3-ctx8k_9b_noul_p2` | d3-ctx8k:9b | Q8_0 | 495 / 0 | 249 / 0 |
| d3-27b | `golden_d3-ctx8k_27b_noul_p2` | d3-ctx8k:27b | Q8_0 | 495 / 0 | 249 / 0 |
| Jev | `golden_jev-1.14.0_noul_p2` | jev-1.14.0 | — (hosted) | 495 / 0 | 249 / 0 |
| 4b json | `golden_qwen3.5_4b_json_p2` | qwen3.5:4b | Q4_K_M | 495 / 0 | 249 / 0 |
| 9b json | `golden_qwen3.5_9b_json_p2` | qwen3.5:9b | Q4_K_M | 495 / 0 | 249 / 0 |
| 27b json | `golden_qwen3.8_27b_json_p2` | qwen3.8:27b | Q4_K_M | 493 / 2 | 248 / 1 |
| 4b jsonR | `golden_qwen3.5_4b_json_reason_p2` | qwen3.5:4b | Q4_K_M | 495 / 0 | 249 / 0 |
| 9b jsonR | `golden_qwen3.5_9b_json_reason_p2` | qwen3.5:9b | Q4_K_M | 494 / 1 | 249 / 0 |
| 27b jsonR | `golden_qwen3.8_27b_json_reason_p2` | qwen3.8:27b | Q4_K_M | 494 / 1 | 249 / 0 |
| 4b lp fresh | `golden_qwen3.5_4b_logprob_p2dbf` | qwen3.5:4b | Q4_K_M | 495 / 0 | 249 / 0 |
| 9b lp fresh | `golden_qwen3.5_9b_logprob_p2dbf` | qwen3.5:9b | Q4_K_M | 495 / 0 | 249 / 0 |

- main set: 24-409: 144 responsive / 102 not; 25-3152: 140 responsive / 109 not
- roster set: 25-3152: 140 responsive / 109 not

The seven **score models** are the main subject. The six **JSON verdict modes** (json = verdict first,
jsonR = reasoning first) appear only as a contrast in E3 and E4. Five JSON rows have no score (unparseable output) and are dropped:
2 + 1 in the 27b json runs, 1 each in 9b jsonR and 27b jsonR (Table E0). The two "fresh" runs, which unload the model before every call, are used only in
E5. Labels, kinds and recipes come from `data/golden/pairs.jsonl` joined on `pair_id`, through
`scripts/golden_report.py load_runs()`.

### Terms

| term | meaning here |
|---|---|
| score | the model's probability that the email is responsive (lp: first-token P(yes)/(P(yes)+P(no)); d3 and Jev: P(yes); JSON: confidence if the verdict is yes, else 1 − confidence) |
| flagged / passes | score ≥ the cutoff: the email goes on to human review. For a non-responsive email, passing means wasted review |
| thr98 | the highest cutoff that still flags at least 98% of responsive pairs, set on all pairs of the set together (both requests pooled on the main set). On the main set (284 responsive) that allows at most 5 misses; on the roster set (140 responsive), at most 2 |
| elim@98 | the share of non-responsive pairs scored below thr98, i.e. eliminated before review |
| AUROC | the chance that a randomly chosen responsive pair scores above a randomly chosen non-responsive one (ties count half). 0.5 is a coin flip, 1.0 a perfect ranking. Needs no cutoff |
| default decision | score ≥ 0.5 (JSON: the verdict) |
| paired bootstrap | redraw the set's pairs at random with replacement, keeping the number of responsive and non-responsive pairs fixed ("stratified by label"). Recompute every model's metric on the same redraw, and repeat 2,000–10,000 times. The 2.5th–97.5th percentiles of a difference give its 95% CI |
| bootstrap p | twice the share of redraws in which the difference lands on the other side of zero. The smallest possible value is about 2 ÷ (number of redraws): 2.0e-04 at 10,000 |
| normal p | a second reading of the same bootstrap: the p-value from a normal (bell) curve with the bootstrap's spread. It ignores the shape of the bootstrap's far tail, which is unreliable for small sets and near AUROC = 1, so it is more conservative there |
| Holm | a correction for running many tests at once. If 21 comparisons are each tested at the 5% level, some will look "significant" by chance. Holm raises each p-value so that the chance of even one false alarm in the family stays at 5%. "Survives Holm" = Holm-adjusted p < 0.05 |
| DeLong | an analytic (formula-based) test for the difference between two AUROCs measured on the same pairs; a cross-check on the bootstrap |
| exact McNemar | for two models scored on the same emails, it looks only at the emails where they disagree (b: A flags and B doesn't; c: the reverse). It asks how likely a split as lopsided as b vs c would be if each disagreement were a fair coin toss. Exact binomial, two-sided |
| Fisher's exact test | compares two proportions measured on different emails |
| Wilson interval | a 95% CI for a k/n proportion |
| Pareto frontier | E3 |
| Brier, ECE, calibration slope | E4 |

**What the bootstrap does not cover.** It measures the noise from which pairs happened to be in the
set. It does not include run-to-run backend noise: two runs of the same model differ by up to 4.6
points of elim@98 (Table E5g). It also does not cover label errors, or the question of whether this
designed mix (synthetic close calls and hard negatives, a 57% responsive share) resembles a real
keyword-search result; that is branch D. "Real" below means "not explained by which pairs were drawn
into this set".

## E1. Which pairwise differences are real?

### Main set (495 pairs)

**Table E1a (Main set).** Per model, with marginal 95% bootstrap CIs.

| model | AUROC [95% CI] | elim@98 [95% CI] |
|---|---|---|
| 4b lp | 0.923 [0.897–0.945] | 51.7% [40.3%–71.6%] |
| 9b lp | 0.942 [0.921–0.962] | 70.6% [63.5%–78.7%] |
| 27b lp | 0.975 [0.963–0.986] | 75.8% [70.6%–87.7%] |
| d3-4b | 0.884 [0.852–0.913] | 53.6% [42.7%–63.0%] |
| d3-9b | 0.947 [0.927–0.965] | 68.2% [61.6%–79.1%] |
| d3-27b | 0.979 [0.970–0.988] | 81.0% [74.9%–86.7%] |
| Jev | 0.916 [0.891–0.939] | 63.0% [55.0%–69.7%] |

**Table E1b (Main set).** AUROC difference, higher-scoring model first; sorted by bootstrap p. 'CI excl. 0' = the 95% CI does not contain 0; Holm = Holm-adjusted p within these 21 tests. 'normal p' = the p-value from a normal curve with the bootstrap SD of the difference (ignores the bootstrap's tail shape; a more conservative reading), Holm-adjusted.

| A − B | ΔAUROC | 95% CI | CI excl. 0 | bootstrap p | Holm p | survives Holm | normal p (Holm) | DeLong p | DeLong Holm p |
|---|---|---|---|---|---|---|---|---|---|
| d3-27b − d3-4b | +0.095 | [+0.070, +0.123] | yes | 2.0e-04 | 0.004 | **yes** | 5.2e-12 (1.1e-10) | 5.3e-12 | 1.1e-10 |
| 27b lp − d3-4b | +0.091 | [+0.065, +0.120] | yes | 2.0e-04 | 0.004 | **yes** | 7.0e-11 (1.4e-09) | 7.1e-11 | 1.4e-09 |
| d3-27b − Jev | +0.063 | [+0.044, +0.085] | yes | 2.0e-04 | 0.004 | **yes** | 1.1e-09 (2.1e-08) | 1.1e-09 | 2.1e-08 |
| d3-9b − d3-4b | +0.063 | [+0.042, +0.086] | yes | 2.0e-04 | 0.004 | **yes** | 1.9e-08 (3.4e-07) | 2.2e-08 | 3.7e-07 |
| 27b lp − Jev | +0.059 | [+0.040, +0.081] | yes | 2.0e-04 | 0.004 | **yes** | 2.2e-08 (3.8e-07) | 1.8e-08 | 3.2e-07 |
| 9b lp − d3-4b | +0.058 | [+0.030, +0.089] | yes | 2.0e-04 | 0.004 | **yes** | 1.1e-04 (0.002) | 1.2e-04 | 0.002 |
| d3-27b − 4b lp | +0.057 | [+0.035, +0.081] | yes | 2.0e-04 | 0.004 | **yes** | 1.8e-06 (2.9e-05) | 1.9e-06 | 3.0e-05 |
| 27b lp − 4b lp | +0.053 | [+0.031, +0.075] | yes | 2.0e-04 | 0.004 | **yes** | 2.3e-06 (3.4e-05) | 2.5e-06 | 3.7e-05 |
| d3-27b − 9b lp | +0.037 | [+0.018, +0.058] | yes | 2.0e-04 | 0.004 | **yes** | 3.6e-04 (0.005) | 3.0e-04 | 0.004 |
| 27b lp − 9b lp | +0.033 | [+0.015, +0.053] | yes | 2.0e-04 | 0.004 | **yes** | 6.5e-04 (0.007) | 5.6e-04 | 0.006 |
| d3-27b − d3-9b | +0.032 | [+0.015, +0.051] | yes | 2.0e-04 | 0.004 | **yes** | 4.1e-04 (0.005) | 3.6e-04 | 0.004 |
| 27b lp − d3-9b | +0.028 | [+0.011, +0.047] | yes | 6.0e-04 | 0.006 | **yes** | 0.002 (0.016) | 0.001 | 0.014 |
| 4b lp − d3-4b | +0.039 | [+0.013, +0.066] | yes | 0.004 | 0.038 | **yes** | 0.005 (0.044) | 0.005 | 0.045 |
| d3-9b − Jev | +0.031 | [+0.006, +0.056] | yes | 0.017 | 0.13 | no | 0.018 (0.14) | 0.017 | 0.14 |
| d3-9b − 4b lp | +0.024 | [+0.004, +0.045] | yes | 0.018 | 0.13 | no | 0.020 (0.14) | 0.021 | 0.14 |
| 9b lp − Jev | +0.026 | [+0.004, +0.048] | yes | 0.021 | 0.13 | no | 0.022 (0.14) | 0.021 | 0.14 |
| Jev − d3-4b | +0.032 | [+0.002, +0.063] | yes | 0.032 | 0.16 | no | 0.037 (0.18) | 0.037 | 0.18 |
| 9b lp − 4b lp | +0.020 | [-0.000, +0.041] | no | 0.053 | 0.21 | no | 0.065 (0.26) | 0.064 | 0.25 |
| d3-27b − 27b lp | +0.004 | [-0.004, +0.013] | no | 0.34 | 1 | no | 0.34 (1) | 0.33 | 1 |
| 4b lp − Jev | +0.006 | [-0.020, +0.032] | no | 0.62 | 1 | no | 0.63 (1) | 0.63 | 1 |
| d3-9b − 9b lp | +0.005 | [-0.013, +0.022] | no | 0.62 | 1 | no | 0.61 (1) | 0.61 | 1 |

**Table E1c (Main set).** elim@98 difference (percentage points), higher-scoring model first; sorted by bootstrap p. 'CI excl. 0' = the 95% CI does not contain 0; Holm = Holm-adjusted p within these 21 tests. 'normal p' = the p-value from a normal curve with the bootstrap SD of the difference (ignores the bootstrap's tail shape; a more conservative reading), Holm-adjusted.

| A − B | Δelim@98 | 95% CI | CI excl. 0 | bootstrap p | Holm p | survives Holm | normal p (Holm) |
|---|---|---|---|---|---|---|---|
| d3-27b − d3-4b | +27.5 | [+18.5, +37.9] | yes | 2.0e-04 | 0.004 | **yes** | 4.5e-08 (9.1e-07) |
| 27b lp − d3-4b | +22.3 | [+14.7, +36.5] | yes | 2.0e-04 | 0.004 | **yes** | 6.9e-05 (0.001) |
| d3-27b − Jev | +18.0 | [+12.3, +25.1] | yes | 2.0e-04 | 0.004 | **yes** | 3.4e-08 (7.1e-07) |
| 27b lp − Jev | +12.8 | [+8.5, +25.1] | yes | 2.0e-04 | 0.004 | **yes** | 0.003 (0.045) |
| d3-9b − d3-4b | +14.7 | [+7.1, +26.5] | yes | 4.0e-04 | 0.007 | **yes** | 0.003 (0.045) |
| d3-27b − 4b lp | +29.4 | [+9.0, +40.8] | yes | 6.0e-04 | 0.010 | **yes** | 4.8e-04 (0.009) |
| 9b lp − d3-4b | +17.1 | [+7.1, +29.4] | yes | 0.002 | 0.027 | **yes** | 0.002 (0.038) |
| 27b lp − 4b lp | +24.2 | [+7.1, +39.3] | yes | 0.002 | 0.031 | **yes** | 0.003 (0.045) |
| d3-27b − 9b lp | +10.4 | [+0.9, +18.0] | yes | 0.030 | 0.39 | no | 0.016 (0.19) |
| d3-27b − d3-9b | +12.8 | [+1.4, +19.9] | yes | 0.032 | 0.39 | no | 0.005 (0.068) |
| 9b lp − Jev | +7.6 | [+0.5, +17.1] | yes | 0.041 | 0.46 | no | 0.072 (0.58) |
| 9b lp − 4b lp | +19.0 | [+0.5, +31.8] | yes | 0.042 | 0.46 | no | 0.022 (0.24) |
| Jev − d3-4b | +9.5 | [-0.5, +19.4] | no | 0.072 | 0.65 | no | 0.065 (0.58) |
| d3-9b − 4b lp | +16.6 | [-1.4, +31.3] | no | 0.090 | 0.72 | no | 0.051 (0.51) |
| 27b lp − d3-9b | +7.6 | [-1.4, +19.4] | no | 0.095 | 0.72 | no | 0.14 (1) |
| d3-9b − Jev | +5.2 | [-1.4, +17.1] | no | 0.12 | 0.72 | no | 0.26 (1) |
| 27b lp − 9b lp | +5.2 | [-1.9, +17.5] | no | 0.16 | 0.78 | no | 0.30 (1) |
| Jev − 4b lp | +11.4 | [-8.5, +22.3] | no | 0.34 | 1 | no | 0.17 (1) |
| d3-27b − 27b lp | +5.2 | [-5.7, +9.0] | no | 0.48 | 1 | no | 0.17 (1) |
| 9b lp − d3-9b | +2.4 | [-7.6, +9.5] | no | 0.62 | 1 | no | 0.58 (1) |
| d3-4b − 4b lp | +1.9 | [-17.1, +15.2] | no | 0.87 | 1 | no | 0.82 (1) |

**Table E1d (Main set).** Row model minus column model; * = survives Holm (bootstrap p) within its family of 21.

AUROC:

| AUROC | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev |
|---|---|---|---|---|---|---|---|
| **4b lp** | — | -0.020 | -0.053* | +0.039* | -0.024 | -0.057* | +0.006 |
| **9b lp** | +0.020 | — | -0.033* | +0.058* | -0.005 | -0.037* | +0.026 |
| **27b lp** | +0.053* | +0.033* | — | +0.091* | +0.028* | -0.004 | +0.059* |
| **d3-4b** | -0.039* | -0.058* | -0.091* | — | -0.063* | -0.095* | -0.032 |
| **d3-9b** | +0.024 | +0.005 | -0.028* | +0.063* | — | -0.032* | +0.031 |
| **d3-27b** | +0.057* | +0.037* | +0.004 | +0.095* | +0.032* | — | +0.063* |
| **Jev** | -0.006 | -0.026 | -0.059* | +0.032 | -0.031 | -0.063* | — |

elim@98 (points):

| elim@98 | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev |
|---|---|---|---|---|---|---|---|
| **4b lp** | — | -19 | -24* | -2 | -17 | -29* | -11 |
| **9b lp** | +19 | — | -5 | +17* | +2 | -10 | +8 |
| **27b lp** | +24* | +5 | — | +22* | +8 | -5 | +13* |
| **d3-4b** | +2 | -17* | -22* | — | -15* | -27* | -9 |
| **d3-9b** | +17 | -2 | -8 | +15* | — | -13 | +5 |
| **d3-27b** | +29* | +10 | +5 | +27* | +13 | — | +18* |
| **Jev** | +11 | -8 | -13* | +9 | -5 | -18* | — |

**Table E1f (Main set).** Cross-check of the two uncertainty methods: DeLong standard error of each model's AUROC vs the standard deviation of its bootstrap AUROCs, and the skew of the bootstrap distribution (mean − median; 0 for a symmetric one).

| model | AUROC | DeLong SE | bootstrap SD | bootstrap mean − median |
|---|---|---|---|---|
| 4b lp | 0.923 | 0.0123 | 0.0122 | -0.0004 |
| 9b lp | 0.942 | 0.0105 | 0.0106 | -0.0004 |
| 27b lp | 0.975 | 0.0058 | 0.0058 | -0.0004 |
| d3-4b | 0.884 | 0.0156 | 0.0155 | -0.0005 |
| d3-9b | 0.947 | 0.0097 | 0.0098 | -0.0005 |
| d3-27b | 0.979 | 0.0046 | 0.0046 | -0.0002 |
| Jev | 0.916 | 0.0123 | 0.0123 | -0.0005 |

**What the tables show (main set).**

- **AUROC.** 17 of the 21 CIs exclude zero, and 13 survive Holm. The same 13 survive under the other
  two readings, the normal curve and DeLong (Table E1b, E1e). They sort the models into three tiers:
  - **Top: 27b lp and d3-27b.** Each beats every other model after Holm. Between the two:
    +0.004 [−0.004, +0.013], p 0.34.
  - **Middle: 9b lp, d3-9b, 4b lp, Jev.** None of the six pairs among them survives Holm. The
    closest call is 9b lp − 4b lp, +0.020 [−0.000, +0.041], p 0.053.
  - **Bottom: d3-4b.** It is below 4b lp, 9b lp, d3-9b and both 27b models after Holm. It can't be
    separated from Jev (Jev − d3-4b +0.032, Holm p 0.16).
- **elim@98.** 12 CIs exclude zero, but only 8 survive Holm, the same 8 under either reading. The
  survivors are the two 27b models against Jev, 4b lp and d3-4b, plus 9b lp and d3-9b against d3-4b.
  Gaps that look large but don't survive:
  - 9b lp − 4b lp: +19.0 [+0.5, +31.8], Holm p 0.46;
  - d3-27b − 9b lp: +10.4 [+0.9, +18.0], Holm p 0.39;
  - d3-27b − 27b lp: +5.2 [−5.7, +9.0].
- **Why elim@98 is noisier than AUROC.** elim@98 depends on where the 5 lowest-scoring responsive
  pairs fall. A redraw that duplicates or drops one of them moves the cutoff, and with it the share of
  negatives eliminated. Several per-model intervals in Table E1a are wider than 15 points; the 4b lp's
  runs from 40.3% to 71.6%.
- **The two uncertainty methods agree on the main set.** DeLong's standard error for each model's
  AUROC matches the spread of its bootstrap in every model, e.g. 0.0058 and 0.0058 for the 27b lp (E1f).

### 25-3152 roster set (249 pairs)

**Table E1a (25-3152 roster set).** Per model, with marginal 95% bootstrap CIs.

| model | AUROC [95% CI] | elim@98 [95% CI] |
|---|---|---|
| 4b lp | 0.950 [0.922–0.973] | 75.2% [56.0%–84.4%] |
| 9b lp | 0.963 [0.941–0.980] | 67.9% [56.0%–79.8%] |
| 27b lp | 0.989 [0.979–0.996] | 90.8% [85.3%–96.3%] |
| d3-4b | 0.961 [0.935–0.983] | 86.2% [79.8%–92.7%] |
| d3-9b | 0.979 [0.957–0.995] | 89.9% [84.4%–96.3%] |
| d3-27b | 0.998 [0.994–1.000] | 98.2% [95.4%–100.0%] |
| Jev | 0.968 [0.943–0.987] | 83.5% [76.1%–90.8%] |

**Table E1b (25-3152 roster set).** AUROC difference, higher-scoring model first; sorted by bootstrap p. 'CI excl. 0' = the 95% CI does not contain 0; Holm = Holm-adjusted p within these 21 tests. 'normal p' = the p-value from a normal curve with the bootstrap SD of the difference (ignores the bootstrap's tail shape; a more conservative reading), Holm-adjusted.

| A − B | ΔAUROC | 95% CI | CI excl. 0 | bootstrap p | Holm p | survives Holm | normal p (Holm) | DeLong p | DeLong Holm p |
|---|---|---|---|---|---|---|---|---|---|
| d3-27b − 4b lp | +0.048 | [+0.025, +0.076] | yes | 2.0e-04 | 0.004 | **yes** | 2.2e-04 (0.005) | 2.1e-04 | 0.004 |
| 27b lp − 4b lp | +0.039 | [+0.020, +0.062] | yes | 2.0e-04 | 0.004 | **yes** | 3.9e-04 (0.007) | 3.4e-04 | 0.006 |
| d3-27b − d3-4b | +0.036 | [+0.016, +0.061] | yes | 2.0e-04 | 0.004 | **yes** | 0.002 (0.031) | 0.002 | 0.031 |
| d3-27b − 9b lp | +0.035 | [+0.018, +0.056] | yes | 2.0e-04 | 0.004 | **yes** | 3.0e-04 (0.006) | 2.7e-04 | 0.005 |
| d3-27b − Jev | +0.030 | [+0.011, +0.054] | yes | 2.0e-04 | 0.004 | **yes** | 0.006 (0.095) | 0.006 | 0.097 |
| d3-27b − 27b lp | +0.009 | [+0.003, +0.017] | yes | 2.0e-04 | 0.004 | **yes** | 0.018 (0.21) | 0.017 | 0.21 |
| 27b lp − 9b lp | +0.026 | [+0.010, +0.046] | yes | 4.0e-04 | 0.006 | **yes** | 0.004 (0.071) | 0.004 | 0.061 |
| 27b lp − d3-4b | +0.028 | [+0.009, +0.051] | yes | 8.0e-04 | 0.011 | **yes** | 0.009 (0.12) | 0.009 | 0.12 |
| d3-9b − d3-4b | +0.017 | [+0.006, +0.031] | yes | 8.0e-04 | 0.011 | **yes** | 0.007 (0.11) | 0.007 | 0.11 |
| d3-9b − 4b lp | +0.029 | [+0.009, +0.052] | yes | 0.004 | 0.046 | **yes** | 0.009 (0.12) | 0.008 | 0.12 |
| d3-27b − d3-9b | +0.019 | [+0.004, +0.040] | yes | 0.006 | 0.062 | no | 0.041 (0.45) | 0.038 | 0.42 |
| 27b lp − Jev | +0.021 | [+0.003, +0.045] | yes | 0.018 | 0.18 | no | 0.050 (0.50) | 0.050 | 0.50 |
| d3-9b − 9b lp | +0.016 | [-0.006, +0.038] | no | 0.15 | 1 | no | 0.15 (1) | 0.15 | 1 |
| 27b lp − d3-9b | +0.010 | [-0.004, +0.029] | no | 0.18 | 1 | no | 0.21 (1) | 0.21 | 1 |
| Jev − 4b lp | +0.017 | [-0.009, +0.046] | no | 0.20 | 1 | no | 0.21 (1) | 0.21 | 1 |
| 9b lp − 4b lp | +0.013 | [-0.007, +0.034] | no | 0.21 | 1 | no | 0.23 (1) | 0.22 | 1 |
| d3-4b − 4b lp | +0.011 | [-0.012, +0.036] | no | 0.35 | 1 | no | 0.35 (1) | 0.35 | 1 |
| d3-9b − Jev | +0.011 | [-0.013, +0.038] | no | 0.42 | 1 | no | 0.40 (1) | 0.40 | 1 |
| Jev − 9b lp | +0.005 | [-0.018, +0.027] | no | 0.66 | 1 | no | 0.66 (1) | 0.66 | 1 |
| Jev − d3-4b | +0.006 | [-0.022, +0.034] | no | 0.66 | 1 | no | 0.67 (1) | 0.67 | 1 |
| 9b lp − d3-4b | +0.001 | [-0.024, +0.027] | no | 0.93 | 1 | no | 0.93 (1) | 0.93 | 1 |

**Table E1c (25-3152 roster set).** elim@98 difference (percentage points), higher-scoring model first; sorted by bootstrap p. 'CI excl. 0' = the 95% CI does not contain 0; Holm = Holm-adjusted p within these 21 tests. 'normal p' = the p-value from a normal curve with the bootstrap SD of the difference (ignores the bootstrap's tail shape; a more conservative reading), Holm-adjusted.

| A − B | Δelim@98 | 95% CI | CI excl. 0 | bootstrap p | Holm p | survives Holm | normal p (Holm) |
|---|---|---|---|---|---|---|---|
| d3-27b − 9b lp | +30.3 | [+18.3, +42.2] | yes | 2.0e-04 | 0.004 | **yes** | 3.8e-07 (8.0e-06) |
| d3-27b − 4b lp | +22.9 | [+13.8, +42.2] | yes | 2.0e-04 | 0.004 | **yes** | 0.001 (0.020) |
| d3-27b − Jev | +14.7 | [+7.3, +22.0] | yes | 2.0e-04 | 0.004 | **yes** | 8.6e-05 (0.002) |
| d3-27b − d3-4b | +11.9 | [+5.5, +18.3] | yes | 2.0e-04 | 0.004 | **yes** | 1.8e-04 (0.003) |
| 27b lp − 9b lp | +22.9 | [+11.9, +35.8] | yes | 4.0e-04 | 0.007 | **yes** | 1.1e-04 (0.002) |
| 27b lp − 4b lp | +15.6 | [+7.3, +35.8] | yes | 4.0e-04 | 0.007 | **yes** | 0.026 (0.29) |
| d3-9b − 9b lp | +22.0 | [+10.1, +34.9] | yes | 8.0e-04 | 0.012 | **yes** | 4.2e-04 (0.007) |
| d3-27b − d3-9b | +8.3 | [+2.8, +13.8] | yes | 1.0e-03 | 0.014 | **yes** | 0.003 (0.040) |
| d3-9b − 4b lp | +14.7 | [+6.4, +33.9] | yes | 0.002 | 0.023 | **yes** | 0.039 (0.39) |
| d3-27b − 27b lp | +7.3 | [+1.8, +11.9] | yes | 0.003 | 0.034 | **yes** | 0.005 (0.064) |
| d3-4b − 9b lp | +18.3 | [+6.4, +30.3] | yes | 0.005 | 0.055 | no | 0.002 (0.036) |
| Jev − 9b lp | +15.6 | [+3.7, +26.6] | yes | 0.015 | 0.15 | no | 0.007 (0.083) |
| d3-4b − 4b lp | +11.0 | [+2.8, +30.3] | yes | 0.018 | 0.16 | no | 0.12 (0.84) |
| 27b lp − Jev | +7.3 | [+0.9, +15.6] | yes | 0.027 | 0.22 | no | 0.041 (0.39) |
| d3-9b − Jev | +6.4 | [+0.0, +14.7] | no | 0.073 | 0.51 | no | 0.087 (0.70) |
| Jev − 4b lp | +8.3 | [-1.8, +27.5] | no | 0.11 | 0.64 | no | 0.26 (1) |
| 27b lp − d3-4b | +4.6 | [-0.9, +11.0] | no | 0.12 | 0.64 | no | 0.13 (0.84) |
| d3-9b − d3-4b | +3.7 | [+0.0, +9.2] | no | 0.13 | 0.64 | no | 0.14 (0.84) |
| d3-4b − Jev | +2.8 | [-4.6, +10.1] | no | 0.48 | 1 | no | 0.46 (1) |
| 4b lp − 9b lp | +7.3 | [-10.1, +18.3] | no | 0.57 | 1 | no | 0.31 (1) |
| 27b lp − d3-9b | +0.9 | [-4.6, +6.4] | no | 0.83 | 1 | no | 0.75 (1) |

**Table E1d (25-3152 roster set).** Row model minus column model; * = survives Holm (bootstrap p) within its family of 21.

AUROC:

| AUROC | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev |
|---|---|---|---|---|---|---|---|
| **4b lp** | — | -0.013 | -0.039* | -0.011 | -0.029* | -0.048* | -0.017 |
| **9b lp** | +0.013 | — | -0.026* | +0.001 | -0.016 | -0.035* | -0.005 |
| **27b lp** | +0.039* | +0.026* | — | +0.028* | +0.010 | -0.009* | +0.021 |
| **d3-4b** | +0.011 | -0.001 | -0.028* | — | -0.017* | -0.036* | -0.006 |
| **d3-9b** | +0.029* | +0.016 | -0.010 | +0.017* | — | -0.019 | +0.011 |
| **d3-27b** | +0.048* | +0.035* | +0.009* | +0.036* | +0.019 | — | +0.030* |
| **Jev** | +0.017 | +0.005 | -0.021 | +0.006 | -0.011 | -0.030* | — |

elim@98 (points):

| elim@98 | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev |
|---|---|---|---|---|---|---|---|
| **4b lp** | — | +7 | -16* | -11 | -15* | -23* | -8 |
| **9b lp** | -7 | — | -23* | -18 | -22* | -30* | -16 |
| **27b lp** | +16* | +23* | — | +5 | +1 | -7* | +7 |
| **d3-4b** | +11 | +18 | -5 | — | -4 | -12* | +3 |
| **d3-9b** | +15* | +22* | -1 | +4 | — | -8* | +6 |
| **d3-27b** | +23* | +30* | +7* | +12* | +8* | — | +15* |
| **Jev** | +8 | +16 | -7 | -3 | -6 | -15* | — |

**Table E1f (25-3152 roster set).** Cross-check of the two uncertainty methods: DeLong standard error of each model's AUROC vs the standard deviation of its bootstrap AUROCs, and the skew of the bootstrap distribution (mean − median; 0 for a symmetric one).

| model | AUROC | DeLong SE | bootstrap SD | bootstrap mean − median |
|---|---|---|---|---|
| 4b lp | 0.950 | 0.0131 | 0.0132 | -0.0008 |
| 9b lp | 0.963 | 0.0099 | 0.0099 | -0.0008 |
| 27b lp | 0.989 | 0.0043 | 0.0043 | -0.0004 |
| d3-4b | 0.961 | 0.0122 | 0.0122 | -0.0008 |
| d3-9b | 0.979 | 0.0096 | 0.0097 | -0.0009 |
| d3-27b | 0.998 | 0.0018 | 0.0018 | -0.0003 |
| Jev | 0.968 | 0.0113 | 0.0113 | -0.0009 |

For the AUROC differences where bootstrap-Holm and DeLong-Holm disagree (25-3152 roster set): the spread of the difference by each method, the share of resamples at or below zero, and the p-value a normal curve with the bootstrap SD would give.

| A − B | ΔAUROC | DeLong SE of Δ | bootstrap SD of Δ | resamples with Δ ≤ 0 | bootstrap p | normal p from bootstrap SD | DeLong p |
|---|---|---|---|---|---|---|---|
| d3-27b − 27b lp | +0.009 | 0.0037 | 0.0037 | 0.00% | 2.0e-04 | 0.018 | 0.017 |
| d3-27b − Jev | +0.030 | 0.0110 | 0.0110 | 0.00% | 2.0e-04 | 0.006 | 0.006 |
| 27b lp − 9b lp | +0.026 | 0.0091 | 0.0092 | 0.01% | 4.0e-04 | 0.004 | 0.004 |
| 27b lp − d3-4b | +0.028 | 0.0105 | 0.0105 | 0.03% | 8.0e-04 | 0.009 | 0.009 |
| d3-9b − d3-4b | +0.017 | 0.0064 | 0.0064 | 0.03% | 8.0e-04 | 0.007 | 0.007 |
| d3-9b − 4b lp | +0.029 | 0.0108 | 0.0109 | 0.18% | 0.004 | 0.009 | 0.008 |

**What the tables show (roster set).**

- **AUROC: the readings disagree here, and the cause can be pinned down.**
  - By the bootstrap percentile p, 10 differences survive Holm; by DeLong, 4; by the normal curve
    with the bootstrap's SD, the same 4 (E1e).
  - The methods agree on how *spread out* each difference is: DeLong's standard error equals the
    bootstrap SD, and the normal-curve p reproduces DeLong's p (the diagnostic table under E1f).
  - They disagree only about the far tail. For d3-27b − 27b lp (+0.009), not one of the 10,000
    redraws lands at or below zero, where a normal curve with the same spread would put roughly 1%.
    The percentile p (2.0e-04) rests on that thin tail; DeLong gives p 0.017 (Holm 0.21).
  - All six disagreeing pairs involve the 27b lp (0.989), the d3-27b (0.998) or the d3-9b (0.979),
    near the ceiling. The far tail of a bootstrap on 249 pairs is its least reliable part, so this
    write-up takes the conservative reading.
  - **The four AUROC differences that survive under every reading:** d3-27b − 4b lp,
    27b lp − 4b lp, d3-27b − d3-4b, d3-27b − 9b lp.
- **elim@98.** The d3-27b eliminates 98.2%.
  - By the percentile p it beats each of the other six models after Holm.
  - By the more conservative normal reading it beats five. Its margin over the stock 27b,
    +7.3 [+1.8, +11.9], falls just short (Holm p 0.064 against 0.034).
  - That margin is also only a little larger than the run-to-run noise measured for the stock models
    on this set (Table E5g: one 4b +roster run eliminates 75.2%, another 70.6%).

### Counts and multiplicity

**Table E1e.** How many of the 21 pairwise differences are distinguishable from zero.

| set | metric | 95% CI excludes 0 | Holm within 21 | Holm across all 84 | normal p (bootstrap SD) + Holm within 21 | DeLong + Holm within 21 |
|---|---|---|---|---|---|---|
| main (495) | AUROC | 17 | 13 | 12 | 13 | 13 |
| main (495) | elim@98 | 12 | 8 | 6 | 8 | — |
| roster (249) | AUROC | 12 | 10 | 9 | 4 | 4 |
| roster (249) | elim@98 | 14 | 10 | 8 | 8 | — |

The families are (set, metric), 21 tests each. Holm across all 84 tests together removes one or two more
survivors from each family. On the roster set the conservative readings (normal curve, DeLong)
matter more than the choice of family.

## E2. Hard-negative recipes, and dates in particular

The 91 hard negatives are synthetic near-misses. The 20 *same subject, wrong date* emails share a
responsive email's subject and participants but are dated outside the request's range (for 24-409,
January 1 – July 31, 2023); 12 of them were made from a responsive email that is also in the set.
"Passes" = score ≥ the model's own thr98 on all 495 pairs, unless stated otherwise.

**Table E2a.** Share of each recipe's hard negatives that pass the screen (score >= the model's own thr98, set on all 495 pairs). Lower is better.

| recipe | n | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev |
|---|---|---|---|---|---|---|---|---|
| thr98 | — | 0.2650 | 0.3309 | 0.0687 | 0.3507 | 0.3379 | 0.5857 | 0.3400 |
| same subject, wrong date | 20 | 20/20 (100%) | 18/20 (90%) | 10/20 (50%) | 20/20 (100%) | 17/20 (85%) | 3/20 (15%) | 19/20 (95%) |
| keyword, unrelated sense | 19 | 18/19 (95%) | 11/19 (58%) | 12/19 (63%) | 17/19 (89%) | 15/19 (79%) | 13/19 (68%) | 14/19 (74%) |
| keyword in signature/newsletter | 20 | 15/20 (75%) | 10/20 (50%) | 10/20 (50%) | 14/20 (70%) | 10/20 (50%) | 7/20 (35%) | 15/20 (75%) |
| forwarded, no content | 17 | 12/17 (71%) | 7/17 (41%) | 7/17 (41%) | 14/17 (82%) | 10/17 (59%) | 6/17 (35%) | 8/17 (47%) |
| same people, different subject | 15 | 12/15 (80%) | 11/15 (73%) | 12/15 (80%) | 15/15 (100%) | 14/15 (93%) | 11/15 (73%) | 12/15 (80%) |
| all hard negatives | 91 | 77/91 (85%) | 57/91 (63%) | 51/91 (56%) | 80/91 (88%) | 66/91 (73%) | 40/91 (44%) | 68/91 (75%) |
| real_negative (reference) | 120 | 25/120 (21%) | 5/120 (4%) | 0/120 (0%) | 18/120 (15%) | 1/120 (1%) | 0/120 (0%) | 10/120 (8%) |

**Table E2b.** Same subject, wrong date (n = 20): exact McNemar test for every pair of models at their own thr98. b = A passes and B rejects; c = A rejects and B passes. Sorted by p; Holm within these 21.

| A (passes more) | B | A passes | B passes | b | c | exact p | Holm p | survives Holm |
|---|---|---|---|---|---|---|---|---|
| 4b lp | d3-27b | 20/20 | 3/20 | 17 | 0 | 1.5e-05 | 3.2e-04 | **yes** |
| d3-4b | d3-27b | 20/20 | 3/20 | 17 | 0 | 1.5e-05 | 3.2e-04 | **yes** |
| Jev | d3-27b | 19/20 | 3/20 | 16 | 0 | 3.1e-05 | 5.8e-04 | **yes** |
| 9b lp | d3-27b | 18/20 | 3/20 | 15 | 0 | 6.1e-05 | 0.001 | **yes** |
| d3-9b | d3-27b | 17/20 | 3/20 | 14 | 0 | 1.2e-04 | 0.002 | **yes** |
| 4b lp | 27b lp | 20/20 | 10/20 | 10 | 0 | 0.002 | 0.031 | **yes** |
| d3-4b | 27b lp | 20/20 | 10/20 | 10 | 0 | 0.002 | 0.031 | **yes** |
| Jev | 27b lp | 19/20 | 10/20 | 9 | 0 | 0.004 | 0.055 | no |
| 9b lp | 27b lp | 18/20 | 10/20 | 8 | 0 | 0.008 | 0.10 | no |
| 27b lp | d3-27b | 10/20 | 3/20 | 7 | 0 | 0.016 | 0.19 | no |
| d3-9b | 27b lp | 17/20 | 10/20 | 8 | 1 | 0.039 | 0.43 | no |
| 4b lp | d3-9b | 20/20 | 17/20 | 3 | 0 | 0.25 | 1 | no |
| d3-4b | d3-9b | 20/20 | 17/20 | 3 | 0 | 0.25 | 1 | no |
| 4b lp | 9b lp | 20/20 | 18/20 | 2 | 0 | 0.50 | 1 | no |
| d3-4b | 9b lp | 20/20 | 18/20 | 2 | 0 | 0.50 | 1 | no |
| Jev | d3-9b | 19/20 | 17/20 | 2 | 0 | 0.50 | 1 | no |
| 4b lp | Jev | 20/20 | 19/20 | 1 | 0 | 1 | 1 | no |
| 9b lp | d3-9b | 18/20 | 17/20 | 2 | 1 | 1 | 1 | no |
| Jev | 9b lp | 19/20 | 18/20 | 1 | 0 | 1 | 1 | no |
| d3-4b | Jev | 20/20 | 19/20 | 1 | 0 | 1 | 1 | no |
| 4b lp | d3-4b | 20/20 | 20/20 | 0 | 0 | 1 | 1 | no |

**Table E2c.** Three headline pairs on every recipe, at each model's own thr98. Exact McNemar; Holm across the 15 recipe-level tests (the 'all hard negatives' row is a separate, single test).

| pair (x vs y) | recipe | n | x passes | y passes | x only | y only | exact p | Holm p (15) |
|---|---|---|---|---|---|---|---|---|
| d3-27b vs Jev | same subject, wrong date | 20 | 3 | 19 | 0 | 16 | 3.1e-05 | 4.6e-04 |
| d3-27b vs Jev | keyword, unrelated sense | 19 | 13 | 14 | 0 | 1 | 1 | 1 |
| d3-27b vs Jev | keyword in signature/newsletter | 20 | 7 | 15 | 0 | 8 | 0.008 | 0.10 |
| d3-27b vs Jev | forwarded, no content | 17 | 6 | 8 | 0 | 2 | 0.50 | 1 |
| d3-27b vs Jev | same people, different subject | 15 | 11 | 12 | 0 | 1 | 1 | 1 |
| d3-27b vs Jev | all hard negatives | 91 | 40 | 68 | 0 | 28 | 7.5e-09 | — |
| d3-27b vs 27b lp | same subject, wrong date | 20 | 3 | 10 | 0 | 7 | 0.016 | 0.19 |
| d3-27b vs 27b lp | keyword, unrelated sense | 19 | 13 | 12 | 2 | 1 | 1 | 1 |
| d3-27b vs 27b lp | keyword in signature/newsletter | 20 | 7 | 10 | 2 | 5 | 0.45 | 1 |
| d3-27b vs 27b lp | forwarded, no content | 17 | 6 | 7 | 2 | 3 | 1 | 1 |
| d3-27b vs 27b lp | same people, different subject | 15 | 11 | 12 | 1 | 2 | 1 | 1 |
| d3-27b vs 27b lp | all hard negatives | 91 | 40 | 51 | 7 | 18 | 0.043 | — |
| 27b lp vs Jev | same subject, wrong date | 20 | 10 | 19 | 0 | 9 | 0.004 | 0.055 |
| 27b lp vs Jev | keyword, unrelated sense | 19 | 12 | 14 | 0 | 2 | 0.50 | 1 |
| 27b lp vs Jev | keyword in signature/newsletter | 20 | 10 | 15 | 1 | 6 | 0.12 | 1 |
| 27b lp vs Jev | forwarded, no content | 17 | 7 | 8 | 1 | 2 | 1 | 1 |
| 27b lp vs Jev | same people, different subject | 15 | 12 | 12 | 2 | 2 | 1 | 1 |
| 27b lp vs Jev | all hard negatives | 91 | 51 | 68 | 4 | 21 | 9.1e-04 | — |

**Table E2d.** Within each model: does it pass wrong-date emails more or less often than the other four recipes' emails? Different emails, so Fisher's exact test (unpaired).

| model | wrong date passes | other 4 recipes pass | difference (points) | Fisher p | Holm p (7) |
|---|---|---|---|---|---|
| 4b lp | 20/20 (100%) | 57/71 (80%) | +20 | 0.034 | 0.14 |
| 9b lp | 18/20 (90%) | 39/71 (55%) | +35 | 0.004 | 0.027 |
| 27b lp | 10/20 (50%) | 41/71 (58%) | -8 | 0.61 | 0.61 |
| d3-4b | 20/20 (100%) | 60/71 (85%) | +15 | 0.11 | 0.34 |
| d3-9b | 17/20 (85%) | 49/71 (69%) | +16 | 0.26 | 0.51 |
| d3-27b | 3/20 (15%) | 37/71 (52%) | -37 | 0.004 | 0.027 |
| Jev | 19/20 (95%) | 49/71 (69%) | +26 | 0.019 | 0.097 |

### How much depends on the cutoff?

**Table E2e.** Cutoff sensitivity: wrong-date emails passing (of 20) at each model's own cutoffs for 95%, 98%, 99% and 100% recall (all 495 pairs), and at the fixed cutoff 0.5 (with its recall).

| model | @95% recall | @98% recall | @99% recall | @100% recall | @0.5 | recall @0.5 |
|---|---|---|---|---|---|---|
| 4b lp | 17 (thr 0.529) | 20 (thr 0.265) | 20 (thr 0.221) | 20 (thr 0.139) | 18 | 270/284 (95.1%) |
| 9b lp | 18 (thr 0.432) | 18 (thr 0.331) | 18 (thr 0.246) | 19 (thr 0.178) | 17 | 267/284 (94.0%) |
| 27b lp | 4 (thr 0.334) | 10 (thr 0.069) | 10 (thr 0.057) | 16 (thr 0.008) | 3 | 264/284 (93.0%) |
| d3-4b | 18 (thr 0.457) | 20 (thr 0.351) | 20 (thr 0.261) | 20 (thr 0.108) | 17 | 267/284 (94.0%) |
| d3-9b | 9 (thr 0.531) | 17 (thr 0.338) | 18 (thr 0.305) | 19 (thr 0.260) | 10 | 271/284 (95.4%) |
| d3-27b | 2 (thr 0.722) | 3 (thr 0.586) | 3 (thr 0.540) | 3 (thr 0.487) | 3 | 283/284 (99.6%) |
| Jev | 18 (thr 0.450) | 19 (thr 0.340) | 19 (thr 0.310) | 20 (thr 0.220) | 18 | 266/284 (93.7%) |

**Table E2f.** At the fixed 0.5 cutoff for both models: exact McNemar on every recipe.

| pair (x vs y) | recipe | n | x passes | y passes | x only | y only | exact p |
|---|---|---|---|---|---|---|---|
| d3-27b vs Jev | same subject, wrong date | 20 | 3 | 18 | 0 | 15 | 6.1e-05 |
| d3-27b vs Jev | keyword, unrelated sense | 19 | 13 | 14 | 0 | 1 | 1 |
| d3-27b vs Jev | keyword in signature/newsletter | 20 | 11 | 11 | 2 | 2 | 1 |
| d3-27b vs Jev | forwarded, no content | 17 | 7 | 4 | 3 | 0 | 0.25 |
| d3-27b vs Jev | same people, different subject | 15 | 11 | 10 | 2 | 1 | 1 |
| d3-27b vs Jev | all hard negatives | 91 | 45 | 57 | 7 | 19 | 0.029 |
| d3-27b vs 27b lp | same subject, wrong date | 20 | 3 | 3 | 2 | 2 | 1 |
| d3-27b vs 27b lp | keyword, unrelated sense | 19 | 13 | 7 | 6 | 0 | 0.031 |
| d3-27b vs 27b lp | keyword in signature/newsletter | 20 | 11 | 2 | 9 | 0 | 0.004 |
| d3-27b vs 27b lp | forwarded, no content | 17 | 7 | 2 | 5 | 0 | 0.062 |
| d3-27b vs 27b lp | same people, different subject | 15 | 11 | 5 | 6 | 0 | 0.031 |
| d3-27b vs 27b lp | all hard negatives | 91 | 45 | 19 | 28 | 2 | 8.7e-07 |
| 27b lp vs Jev | same subject, wrong date | 20 | 3 | 18 | 0 | 15 | 6.1e-05 |
| 27b lp vs Jev | keyword, unrelated sense | 19 | 7 | 14 | 0 | 7 | 0.016 |
| 27b lp vs Jev | keyword in signature/newsletter | 20 | 2 | 11 | 0 | 9 | 0.004 |
| 27b lp vs Jev | forwarded, no content | 17 | 2 | 4 | 0 | 2 | 0.50 |
| 27b lp vs Jev | same people, different subject | 15 | 5 | 10 | 0 | 5 | 0.062 |
| 27b lp vs Jev | all hard negatives | 91 | 19 | 57 | 0 | 38 | 7.3e-12 |

**Table E2g.** Threshold-free: AUROC of all 284 positives against one recipe's negatives (the chance that a random responsive email scores above a random email of that recipe). Higher is better. DeLong p for the key pairs on the wrong-date recipe below the table.

| recipe | n neg | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev |
|---|---|---|---|---|---|---|---|---|
| same subject, wrong date | 20 | 0.783 | 0.773 | 0.976 | 0.798 | 0.909 | 0.988 | 0.684 |
| keyword, unrelated sense | 19 | 0.861 | 0.869 | 0.873 | 0.751 | 0.906 | 0.905 | 0.741 |
| keyword in signature/newsletter | 20 | 0.899 | 0.866 | 0.976 | 0.830 | 0.902 | 0.978 | 0.888 |
| forwarded, no content | 17 | 0.873 | 0.955 | 0.965 | 0.844 | 0.923 | 0.968 | 0.944 |
| same people, different subject | 15 | 0.748 | 0.912 | 0.920 | 0.432 | 0.718 | 0.914 | 0.827 |
| all hard negatives | 91 | 0.836 | 0.870 | 0.943 | 0.744 | 0.878 | 0.952 | 0.813 |

| wrong date: A − B | ΔAUROC | DeLong p |
|---|---|---|
| d3-27b − Jev | +0.303 | 5.4e-11 |
| d3-27b − 27b lp | +0.012 | 0.15 |
| 27b lp − Jev | +0.291 | 4.0e-10 |

**Table E2h.** Wrong-date pass-through gap with the threshold re-estimated in every resample (stratified paired bootstrap of all 495 pairs, 5000 resamples, seed 303). Each resample sets each model's thr98 afresh and counts the resampled wrong-date emails above it.

| model | median wrong-date pass-through | 95% interval |
|---|---|---|
| d3-27b | 14% | [0%, 33%] |
| 27b lp | 44% | [15%, 70%] |
| Jev | 95% | [80%, 100%] |

| gap (y − x) | point | 95% CI (points) | bootstrap p |
|---|---|---|---|
| Jev − d3-27b | +80 | [+59, +95] | 4.0e-04 |
| 27b lp − d3-27b | +35 | [+4, +55] | 0.041 |
| Jev − 27b lp | +45 | [+25, +79] | 4.0e-04 |

**Table E2i.** How far would each model's cutoff have to rise to pass no more than 3 of the 20 wrong-date emails (d3-27b's count at its thr98)? Recall and elimination of all 211 negatives at that cutoff.

| model | own thr98 | cutoff needed | wrong date passes | recall at that cutoff | eliminated at that cutoff |
|---|---|---|---|---|---|
| 4b lp | 0.265 | 0.824 | 3 | 151/284 (53.2%) | 200/211 (94.8%) |
| 9b lp | 0.331 | 0.805 | 3 | 195/284 (68.7%) | 200/211 (94.8%) |
| 27b lp | 0.069 | 0.444 | 3 | 266/284 (93.7%) | 189/211 (89.6%) |
| d3-4b | 0.351 | 0.738 | 3 | 192/284 (67.6%) | 185/211 (87.7%) |
| d3-9b | 0.338 | 0.689 | 3 | 233/284 (82.0%) | 190/211 (90.0%) |
| d3-27b | 0.586 | 0.444 | 3 | 284/284 (100.0%) | 161/211 (76.3%) |
| Jev | 0.340 | 0.840 | 3 | 127/284 (44.7%) | 205/211 (97.2%) |

**Table E2j.** Matched source. Hard negatives whose source email (a real positive) is also in the set: how often the model scores the altered copy below its source, the median drop (source − copy), and an exact sign test (two-sided) that drops and rises are equally likely. 'copy passes' = copy at or above the model's thr98.

| recipe | model | pairs | copy below source | median drop | sign-test p | copy passes |
|---|---|---|---|---|---|---|
| same subject, wrong date | 4b lp | 12 | 12/12 | +0.21 | 4.9e-04 | 12/12 |
| same subject, wrong date | 9b lp | 12 | 12/12 | +0.21 | 4.9e-04 | 10/12 |
| same subject, wrong date | 27b lp | 12 | 12/12 | +0.92 | 4.9e-04 | 6/12 |
| same subject, wrong date | d3-4b | 12 | 12/12 | +0.19 | 4.9e-04 | 12/12 |
| same subject, wrong date | d3-9b | 12 | 12/12 | +0.39 | 4.9e-04 | 10/12 |
| same subject, wrong date | d3-27b | 12 | 12/12 | +0.72 | 4.9e-04 | 3/12 |
| same subject, wrong date | Jev | 12 | 12/12 | +0.16 | 4.9e-04 | 11/12 |
| keyword, unrelated sense | 4b lp | 12 | 11/12 | +0.13 | 0.006 | 12/12 |
| keyword, unrelated sense | 9b lp | 12 | 11/12 | +0.29 | 0.006 | 8/12 |
| keyword, unrelated sense | 27b lp | 12 | 12/12 | +0.34 | 4.9e-04 | 10/12 |
| keyword, unrelated sense | d3-4b | 12 | 10/12 | +0.10 | 0.039 | 11/12 |
| keyword, unrelated sense | d3-9b | 12 | 12/12 | +0.28 | 4.9e-04 | 9/12 |
| keyword, unrelated sense | d3-27b | 12 | 12/12 | +0.18 | 4.9e-04 | 10/12 |
| keyword, unrelated sense | Jev | 12 | 12/12 | +0.11 | 4.9e-04 | 11/12 |
| keyword in signature/newsletter | 4b lp | 13 | 13/13 | +0.48 | 2.4e-04 | 8/13 |
| keyword in signature/newsletter | 9b lp | 13 | 12/13 | +0.74 | 0.003 | 4/13 |
| keyword in signature/newsletter | 27b lp | 13 | 13/13 | +0.93 | 2.4e-04 | 6/13 |
| keyword in signature/newsletter | d3-4b | 13 | 11/13 | +0.25 | 0.022 | 9/13 |
| keyword in signature/newsletter | d3-9b | 13 | 12/13 | +0.47 | 0.003 | 5/13 |
| keyword in signature/newsletter | d3-27b | 13 | 13/13 | +0.44 | 2.4e-04 | 5/13 |
| keyword in signature/newsletter | Jev | 13 | 13/13 | +0.34 | 2.4e-04 | 11/13 |
| forwarded, no content | 4b lp | 14 | 13/14 | +0.42 | 0.002 | 9/14 |
| forwarded, no content | 9b lp | 14 | 14/14 | +0.56 | 1.2e-04 | 4/14 |
| forwarded, no content | 27b lp | 14 | 14/14 | +0.95 | 1.2e-04 | 4/14 |
| forwarded, no content | d3-4b | 14 | 11/14 | +0.22 | 0.057 | 11/14 |
| forwarded, no content | d3-9b | 14 | 14/14 | +0.48 | 1.2e-04 | 7/14 |
| forwarded, no content | d3-27b | 14 | 14/14 | +0.55 | 1.2e-04 | 5/14 |
| forwarded, no content | Jev | 14 | 14/14 | +0.40 | 1.2e-04 | 5/14 |
| same people, different subject | 4b lp | 12 | 11/12 | +0.27 | 0.006 | 10/12 |
| same people, different subject | 9b lp | 12 | 12/12 | +0.39 | 4.9e-04 | 10/12 |
| same people, different subject | 27b lp | 12 | 12/12 | +0.60 | 4.9e-04 | 11/12 |
| same people, different subject | d3-4b | 12 | 10/12 | +0.07 | 0.039 | 12/12 |
| same people, different subject | d3-9b | 12 | 12/12 | +0.16 | 4.9e-04 | 12/12 |
| same people, different subject | d3-27b | 12 | 12/12 | +0.20 | 4.9e-04 | 10/12 |
| same people, different subject | Jev | 12 | 12/12 | +0.21 | 4.9e-04 | 10/12 |

**Table E2k.** Wrong-date scores by model (all 20): median and range, against the model's thr98 and its median positive score.

| model | median wrong-date score | range | thr98 | median positive score | passes 24-409 / 25-3152 |
|---|---|---|---|---|---|
| 4b lp | 0.678 | 0.312–0.859 | 0.265 | 0.831 | 10/10 / 10/10 |
| 9b lp | 0.678 | 0.118–0.964 | 0.331 | 0.880 | 9/10 / 9/10 |
| 27b lp | 0.062 | 0.000–0.557 | 0.069 | 0.996 | 6/10 / 4/10 |
| d3-4b | 0.622 | 0.446–0.871 | 0.351 | 0.804 | 10/10 / 10/10 |
| d3-9b | 0.501 | 0.196–0.771 | 0.338 | 0.858 | 9/10 / 8/10 |
| d3-27b | 0.199 | 0.037–0.856 | 0.586 | 0.987 | 3/10 / 0/10 |
| Jev | 0.750 | 0.260–0.880 | 0.340 | 0.820 | 10/10 / 9/10 |

### Verdict on "d3-27b handles dates and Jev doesn't"

The claim breaks into three parts.

1. **d3-27b rejects wrong-date emails far more often than Jev. Supported.** Every check points the
   same way:
   - at each model's own thr98: 3/20 vs 19/20 pass; all 16 disagreements favour d3-27b, exact p
     3.1e-05, Holm p 5.8e-04 among the 21 pairs (E2b);
   - at the fixed 0.5 cutoff: 3 vs 18, p 6.1e-05 (E2f);
   - without any cutoff: AUROC of positives vs wrong-date emails 0.988 vs 0.684, DeLong p 5.4e-11 (E2g);
   - with both cutoffs re-estimated in every bootstrap resample: the gap is +80 points [+59, +95] (E2h).
   For Jev to let only 3 of the 20 through, its cutoff would have to rise to 0.840. At that cutoff it
   flags only 44.7% of responsive emails (E2i).
2. **Jev "doesn't handle dates". Supported, with a nuance.**
   - Jev's wrong-date emails score close to its responsive ones (median 0.750 vs 0.820; E2k), and it
     separates them from responsive emails worse than any other model (0.684; E2g).
   - It does react to the date somewhat. Each of the 12 altered copies scores below its own source
     email (12/12, median drop +0.16; E2j). But the drop is too small to matter: 11 of the 12 copies
     still pass.
   - Whether dates are a *particular* weakness for Jev, compared with its other recipes, is less
     certain: 95% vs 69% pass, Fisher p 0.019, Holm p 0.097 across the seven models (E2d).
3. **d3-27b handles dates better than the stock 27b lp. Not supported.** [disputed in verification: *not established* is the fairer reading; see Verification concern 1]
   - At their own thr98 the counts are 3 vs 10, p 0.016, but Holm p 0.19 (E2b).
   - At 0.5 they tie, 3 vs 3 (E2f). Without a cutoff: 0.988 vs 0.976, p 0.15 (E2g). On matched copies
     the 27b lp's score drops *more* (median +0.92 vs +0.72; E2j).
   - The thr98 gap comes from the cutoff. The 27b lp's thr98 is 0.069, pulled down by a few
     low-scoring responsive emails, and its wrong-date emails have a median score of 0.062, right at
     that cutoff (E2k). At a cutoff of 0.444 the 27b lp lets 3 through and still flags 93.7% of
     responsive emails (E2i).
   - The bootstrap with re-estimated cutoffs gives +35 points [+4, +55], p 0.041 (E2h): borderline,
     and it comes from the same cutoff effect.

**Other recipes.** No other recipe separates d3-27b from Jev after Holm. *Keyword in signature or
newsletter* comes closest (7 vs 15, p 0.008, Holm p 0.10; E2c). Over all 91 hard negatives, d3-27b
passes 40 and Jev 68 (p 7.5e-09), and 16 of the 28 disagreements are wrong-date emails.

*Interpretation, not shown by the data:* a date range is metadata. A records search can usually apply it
as a filter before any model sees an email, and then this weakness costs nothing. It matters when
the date filter is loose or missing, or when an in-range email quotes an out-of-range thread. The
synthetic recipe doesn't test the second case.

## E3. Speed/accuracy frontier

A configuration is on the **Pareto frontier** if no other configuration is both at least as fast and
at least as accurate, and strictly better on one of the two. Wall time is request to response as the
scorer saw it: a single stream on the Strix Halo, and for Jev including the network round trip. Jev's
own compute time is unknown.

**Table E3a.** Main set (495 pairs; JSON runs drop their unscored rows). Sorted by median wall time. Frontier flags: 'med×elim' = on the Pareto frontier of median wall ms vs elim@98, etc.; '(local)' = on the frontier only once Jev is set aside. Decode = Ollama's server-side time generating output tokens (1 token for lp; d3 and Jev report none). × Jev = median wall ÷ the fastest Jev run's median wall in the same table.

| configuration | setting | n | median wall ms | × Jev (median) | mean wall ms | p90 wall ms | median decode ms | AUROC | elim@98 | on frontier (median or mean wall × elim@98 or AUROC) |
|---|---|---|---|---|---|---|---|---|---|---|
| Jev | hosted API | 495 | 117 | 1.0 | 120 | 136 | — | 0.916 | 63.0% | med×elim, med×AUROC, mean×elim |
| 4b lp | prefix cache | 495 | 504 | 4.3 | 606 | 1,172 | 0 | 0.923 | 51.7% | med×elim (local), med×AUROC, mean×elim (local) |
| 9b lp | prefix cache | 495 | 856 | 7.3 | 1,020 | 1,996 | 0 | 0.942 | 70.6% | med×elim, med×AUROC, mean×elim |
| d3-4b | d3, no prefix reuse | 495 | 877 | 7.5 | 1,049 | 1,826 | — | 0.884 | 53.6% | — |
| d3-9b | d3, no prefix reuse | 495 | 1,426 | 12.2 | 1,636 | 2,740 | — | 0.947 | 68.2% | med×AUROC |
| 27b lp | prefix cache | 495 | 2,649 | 22.7 | 3,217 | 6,416 | 0 | 0.975 | 75.8% | med×elim, med×AUROC, mean×elim |
| 4b json | batch 8192, no prefix cache | 495 | 2,749 | 23.5 | 2,848 | 3,656 | 1,760 | 0.833 | 9.5% | — |
| 4b jsonR | batch 8192, no prefix cache | 495 | 2,909 | 24.9 | 2,992 | 3,780 | 1,898 | 0.870 | 0.0% | — |
| 9b json | batch 8192, no prefix cache | 495 | 4,435 | 38.0 | 4,611 | 5,921 | 2,912 | 0.871 | 0.0% | — |
| d3-27b | d3, no prefix reuse | 495 | 4,667 | 40.0 | 5,293 | 8,782 | — | 0.979 | 81.0% | med×elim, med×AUROC, mean×elim |
| 9b jsonR | batch 8192, no prefix cache | 494 | 5,267 | 45.1 | 5,327 | 6,737 | 3,609 | 0.879 | 0.0% | — |
| 27b json | prefix cache | 493 | 6,805 | 58.3 | 7,192 | 10,333 | 3,857 | 0.947 | 27.8% | — |
| 27b jsonR | prefix cache | 494 | 7,014 | 60.1 | 7,471 | 10,797 | 4,040 | 0.951 | 66.2% | — |

- Local frontier, median wall × elim@98: 4b lp (504 ms, 51.7%) → 9b lp (856 ms, 70.6%) → 27b lp (2,649 ms, 75.8%) → d3-27b (4,667 ms, 81.0%)
  - steps: 4b lp → 9b lp: +352 ms (1.7×) for +19.0 points; 9b lp → 27b lp: +1,793 ms (3.1×) for +5.2 points; 27b lp → d3-27b: +2,018 ms (1.8×) for +5.2 points
- Local frontier, median wall × AUROC: 4b lp (504 ms, 0.923) → 9b lp (856 ms, 0.942) → d3-9b (1,426 ms, 0.947) → 27b lp (2,649 ms, 0.975) → d3-27b (4,667 ms, 0.979)
  - steps: 4b lp → 9b lp: +352 ms (1.7×) for +0.020 AUROC; 9b lp → d3-9b: +569 ms (1.7×) for +0.005 AUROC; d3-9b → 27b lp: +1,224 ms (1.9×) for +0.028 AUROC; 27b lp → d3-27b: +2,018 ms (1.8×) for +0.004 AUROC
- Local frontier, mean wall × elim@98: 4b lp (606 ms, 51.7%) → 9b lp (1,020 ms, 70.6%) → 27b lp (3,217 ms, 75.8%) → d3-27b (5,293 ms, 81.0%)
  - steps: 4b lp → 9b lp: +414 ms (1.7×) for +19.0 points; 9b lp → 27b lp: +2,196 ms (3.2×) for +5.2 points; 27b lp → d3-27b: +2,077 ms (1.6×) for +5.2 points

**Table E3b.** 25-3152 only (249 pairs): each configuration without the roster (its main-run rows for these pairs) and with it.

| configuration | setting | n | median wall ms | × Jev (median) | mean wall ms | p90 wall ms | median decode ms | AUROC | elim@98 | on frontier (median or mean wall × elim@98 or AUROC) |
|---|---|---|---|---|---|---|---|---|---|---|
| Jev | hosted API | 249 | 118 | 1.0 | 122 | 141 | — | 0.915 | 57.8% | med×elim, med×AUROC, mean×elim |
| Jev +roster | hosted API | 249 | 125 | 1.1 | 131 | 151 | — | 0.968 | 83.5% | med×elim, med×AUROC, mean×elim |
| 4b lp +roster | prefix cache | 249 | 446 | 3.8 | 541 | 1,169 | 0 | 0.950 | 75.2% | med×elim (local), med×AUROC (local), mean×elim (local) |
| 4b lp | prefix cache | 249 | 450 | 3.8 | 554 | 1,132 | 0 | 0.883 | 29.4% | — |
| 9b lp +roster | prefix cache | 249 | 734 | 6.2 | 916 | 1,888 | 0 | 0.963 | 67.9% | med×AUROC (local) |
| 9b lp | prefix cache | 249 | 772 | 6.6 | 953 | 1,966 | 0 | 0.927 | 69.7% | — |
| d3-4b | d3, no prefix reuse | 249 | 923 | 7.8 | 1,110 | 1,835 | — | 0.889 | 45.0% | — |
| d3-9b | d3, no prefix reuse | 249 | 1,467 | 12.5 | 1,727 | 2,750 | — | 0.947 | 74.3% | — |
| d3-4b +roster | d3, no prefix reuse | 249 | 1,739 | 14.8 | 1,924 | 2,708 | — | 0.961 | 86.2% | med×elim, mean×elim |
| 27b lp +roster | prefix cache | 249 | 2,231 | 19.0 | 2,871 | 6,128 | 0 | 0.989 | 90.8% | med×elim, med×AUROC, mean×elim |
| 27b lp | prefix cache | 249 | 2,340 | 19.9 | 2,979 | 6,282 | 0 | 0.955 | 74.3% | — |
| d3-9b +roster | d3, no prefix reuse | 249 | 2,639 | 22.4 | 2,878 | 3,953 | — | 0.979 | 89.9% | — |
| 4b json | batch 8192, no prefix cache | 249 | 2,757 | 23.4 | 2,866 | 3,715 | 1,730 | 0.789 | 10.1% | — |
| 4b jsonR | batch 8192, no prefix cache | 249 | 3,011 | 25.6 | 3,055 | 3,882 | 1,939 | 0.851 | 0.0% | — |
| 4b json +roster | batch 8192, no prefix cache | 249 | 3,528 | 30.0 | 3,640 | 4,507 | 1,679 | 0.854 | 16.5% | — |
| 4b jsonR +roster | batch 8192, no prefix cache | 249 | 3,820 | 32.5 | 3,899 | 4,772 | 1,923 | 0.909 | 0.0% | — |
| 9b json | batch 8192, no prefix cache | 249 | 4,433 | 37.7 | 4,615 | 5,988 | 2,908 | 0.859 | 0.0% | — |
| d3-27b | d3, no prefix reuse | 249 | 4,758 | 40.5 | 5,563 | 8,825 | — | 0.980 | 85.3% | — |
| 9b jsonR | batch 8192, no prefix cache | 248 | 5,482 | 46.6 | 5,562 | 6,945 | 3,847 | 0.861 | 0.0% | — |
| 9b json +roster | batch 8192, no prefix cache | 249 | 5,563 | 47.3 | 5,726 | 6,998 | 2,819 | 0.890 | 0.0% | — |
| 27b json +roster | prefix cache | 248 | 6,063 | 51.5 | 6,528 | 9,888 | 3,509 | 0.989 | 56.0% | med×AUROC |
| 9b jsonR +roster | batch 8192, no prefix cache | 249 | 6,519 | 55.4 | 6,691 | 8,233 | 3,695 | 0.904 | 57.8% | — |
| 27b json | prefix cache | 247 | 6,552 | 55.7 | 7,005 | 10,326 | 3,937 | 0.924 | 11.2% | — |
| 27b jsonR +roster | prefix cache | 249 | 6,633 | 56.4 | 7,119 | 10,327 | 4,185 | 0.981 | 76.1% | — |
| 27b jsonR | prefix cache | 248 | 6,974 | 59.3 | 7,539 | 11,212 | 4,463 | 0.940 | 61.1% | — |
| d3-27b +roster | d3, no prefix reuse | 249 | 8,550 | 72.7 | 9,281 | 12,825 | — | 0.998 | 98.2% | med×elim, med×AUROC, mean×elim |

- Local frontier, median wall × elim@98: 4b lp +roster (446 ms, 75.2%) → d3-4b +roster (1,739 ms, 86.2%) → 27b lp +roster (2,231 ms, 90.8%) → d3-27b +roster (8,550 ms, 98.2%)
  - steps: 4b lp +roster → d3-4b +roster: +1,293 ms (3.9×) for +11.0 points; d3-4b +roster → 27b lp +roster: +492 ms (1.3×) for +4.6 points; 27b lp +roster → d3-27b +roster: +6,320 ms (3.8×) for +7.3 points
- Local frontier, median wall × AUROC: 4b lp +roster (446 ms, 0.950) → 9b lp +roster (734 ms, 0.963) → 27b lp +roster (2,231 ms, 0.989) → 27b json +roster (6,063 ms, 0.989) → d3-27b +roster (8,550 ms, 0.998)
  - steps: 4b lp +roster → 9b lp +roster: +288 ms (1.6×) for +0.013 AUROC; 9b lp +roster → 27b lp +roster: +1,497 ms (3.0×) for +0.026 AUROC; 27b lp +roster → 27b json +roster: +3,832 ms (2.7×) for +0.000 AUROC; 27b json +roster → d3-27b +roster: +2,488 ms (1.4×) for +0.009 AUROC
- Local frontier, mean wall × elim@98: 4b lp +roster (541 ms, 75.2%) → d3-4b +roster (1,924 ms, 86.2%) → 27b lp +roster (2,871 ms, 90.8%) → d3-27b +roster (9,281 ms, 98.2%)
  - steps: 4b lp +roster → d3-4b +roster: +1,383 ms (3.6×) for +11.0 points; d3-4b +roster → 27b lp +roster: +947 ms (1.5×) for +4.6 points; 27b lp +roster → d3-27b +roster: +6,410 ms (3.2×) for +7.3 points

**Table E3c.** Share of 2000 paired bootstrap resamples in which each local configuration is on the local frontier (median wall ms vs elim@98, and vs AUROC). Latency is resampled with the same pairs.

| set | configuration | on frontier: median wall × elim@98 | on frontier: median wall × AUROC |
|---|---|---|---|
| main | 4b lp | 100% | 100% |
| main | 9b lp | 97% | 96% |
| main | 27b lp | 87% | 100% |
| main | d3-4b | 11% | 0% |
| main | d3-9b | 27% | 71% |
| main | d3-27b | 75% | 84% |
| main | 4b json | 0% | 0% |
| main | 9b json | 0% | 0% |
| main | 27b json | 0% | 0% |
| main | 4b jsonR | 0% | 0% |
| main | 9b jsonR | 0% | 0% |
| main | 27b jsonR | 0% | 0% |
| 25-3152 | 4b lp | 40% | 40% |
| 25-3152 | 4b lp +roster | 100% | 100% |
| 25-3152 | 9b lp | 29% | 1% |
| 25-3152 | 9b lp +roster | 22% | 91% |
| 25-3152 | 27b lp | 0% | 6% |
| 25-3152 | 27b lp +roster | 93% | 100% |
| 25-3152 | d3-4b | 0% | 0% |
| 25-3152 | d3-4b +roster | 99% | 46% |
| 25-3152 | d3-9b | 34% | 8% |
| 25-3152 | d3-9b +roster | 31% | 9% |
| 25-3152 | d3-27b | 3% | 2% |
| 25-3152 | d3-27b +roster | 99% | 100% |
| 25-3152 | 27b json +roster | 31% | 48% |
| 25-3152 | 27b jsonR +roster | 0% | 1% |

(25-3152 rows that were never on the frontier are left out.)

**Table E3d.** Jev against the local configurations that are at least as good on both AUROC and elim@98 (point estimates; E1 says which of these gaps are distinguishable from noise).

| set | Jev run | local configuration | ΔAUROC vs Jev | Δelim@98 vs Jev (points) | median wall vs Jev | mean wall vs Jev |
|---|---|---|---|---|---|---|
| main | Jev | 9b lp | +0.026 | +7.6 | 7.3× | 8.5× |
| main | Jev | d3-9b | +0.031 | +5.2 | 12.2× | 13.6× |
| main | Jev | 27b lp | +0.059 | +12.8 | 22.7× | 26.8× |
| main | Jev | d3-27b | +0.063 | +18.0 | 40.0× | 44.1× |
| main | Jev | 27b jsonR | +0.035 | +3.2 | 60.1× | 62.2× |
| 25-3152 | Jev | 9b lp | +0.012 | +11.9 | 6.6× | 7.8× |
| 25-3152 | Jev | d3-9b | +0.033 | +16.5 | 12.5× | 14.2× |
| 25-3152 | Jev | 27b lp | +0.040 | +16.5 | 19.9× | 24.4× |
| 25-3152 | Jev | d3-27b | +0.065 | +27.5 | 40.5× | 45.6× |
| 25-3152 | Jev | 27b jsonR | +0.025 | +3.3 | 59.3× | 61.8× |
| 25-3152 | Jev +roster | 27b lp +roster | +0.021 | +7.3 | 17.8× | 21.9× |
| 25-3152 | Jev +roster | d3-9b +roster | +0.011 | +6.4 | 21.0× | 21.9× |
| 25-3152 | Jev +roster | d3-27b +roster | +0.030 | +14.7 | 68.2× | 70.8× |

**What the tables show.**

- **Main set.** The local frontier is 4b lp → 9b lp → 27b lp → d3-27b, by median or by mean wall
  time against elim@98. On AUROC, d3-9b also sits on it, between the 9b lp and the 27b lp (E3a).
  - In the bootstrap, 4b lp, 9b lp, 27b lp and d3-27b are on the elim@98 frontier in 100%, 97%, 87%
    and 75% of redraws. d3-9b is on it in 27% (elim@98) and 71% (AUROC); d3-4b in 11% and 0% (E3c).
- **On the main set, the JSON modes are never on the frontier in E3c's 2,000 redraws** (4 of 2,000 for
  27b json in an independent bootstrap). On 25-3152 they are: 27b json +roster sits on the AUROC frontier
  at the point estimate (E3b) and on the local frontier in 31% (elim@98) and 48% (AUROC) of redraws
  (E3c). [corrected in verification: the original said "never on the frontier, in any redraw" without
  restricting it to the main set] On the main set that isn't because the 4b and 9b JSON
  runs had no prefix cache. Their decoding alone (median 1,760–4,040 ms) takes longer than the whole
  lp call of the same model (504 / 856 / 2,649 ms), and their accuracy is lower (E3a).
- **The steps along the frontier are mostly within noise.**
  - 4b → 9b costs +352 ms for +19.0 points of elim@98. The next two steps each cost about two seconds
    for +5.2 points (E3a).
  - None of these three steps survives Holm on its own (E1c). What does survive is the full jump from
    the 4b lp to either 27b model (+24.2 and +29.4 points).
  - So frontier membership describes the point estimates. The ordering of neighbours on it is not
    established.
- **The roster on 25-3152 (E3b).**
  - The stock models' prefix cache covers the shared roster text, so adding the roster costs them
    nothing: 4b lp 450 → 446 ms median, 9b lp 772 → 734, 27b lp 2,340 → 2,231. AUROC rises in all
    three. elim@98 rises for the 4b and 27b and dips for the 9b (69.7% → 67.9%).
  - The d3 models pay for the roster on every call (d3-27b 4,758 → 8,550 ms).
  - The frontier is 4b lp +roster → d3-4b +roster → 27b lp +roster → d3-27b +roster.
  - 27b json +roster sits on the AUROC frontier only through a tie in the fourth decimal with the
    27b lp +roster (+0.000); its elim@98 is 56.0%.
- **Jev (E3a, E3d).** Jev is the fastest configuration (117 ms median, 136 ms p90) and the only one
  that isn't local. The fastest local configuration, the 4b lp, takes 4.3× as long.
  - Local configurations at least as good on both metrics: 9b lp (7.3× Jev's median time), d3-9b
    (12.2×), 27b lp (22.7×), d3-27b (40.0×) and 27b jsonR (60.1×).
  - Of these, only the 27b lp and d3-27b beat Jev on both AUROC and elim@98 after Holm (E1b, E1c).
  - With the roster, only d3-27b +roster (68.2×) beats Jev +roster after Holm: on elim@98, and on
    AUROC by bootstrap but not by DeLong.

## E4. Calibration

A score is **calibrated** if, among emails given score s, about a share s are responsive.

- **Brier score:** the mean of (score − label)², where label is 1 or 0. Lower is better; it mixes
  calibration with ranking.
- **ECE** (expected calibration error): group the scores into ten 0.1-wide bins, take the gap
  between mean score and share responsive in each bin, and average the gaps weighted by bin size.
  0 is perfect.
- **Calibration slope and intercept:** fit a logistic regression of the label on logit(score). A
  calibrated score has slope 1 and intercept 0.

**Table E4a.** Brier score and ECE with 95% bootstrap CIs (2000 resamples). 'ECE if calibrated' = the median [95th percentile] ECE when labels are redrawn from the model's own scores (2000 redraws), i.e. what bin noise alone produces; p = share of redraws at least as bad as observed. Lower is better.

| model | n | Brier [95% CI] | ECE [95% CI] | ECE if calibrated: median [95th pct] | p | mean score |
|---|---|---|---|---|---|---|
| 4b lp | 495 | 0.112 [0.098–0.127] | 0.083 [0.063–0.112] | 0.042 [0.061] | 0.002 | 0.601 |
| 9b lp | 495 | 0.090 [0.076–0.106] | 0.048 [0.042–0.080] | 0.038 [0.055] | 0.16 | 0.576 |
| 27b lp | 495 | 0.060 [0.045–0.078] | 0.030 [0.023–0.058] | 0.023 [0.032] | 0.10 | 0.565 |
| d3-4b | 495 | 0.133 [0.118–0.149] | 0.044 [0.039–0.083] | 0.041 [0.059] | 0.40 | 0.597 |
| d3-9b | 495 | 0.094 [0.081–0.107] | 0.076 [0.064–0.106] | 0.040 [0.058] | 0.001 | 0.582 |
| d3-27b | 495 | 0.070 [0.055–0.085] | 0.066 [0.051–0.087] | 0.026 [0.038] | 5.0e-04 | 0.639 |
| Jev | 495 | 0.116 [0.101–0.130] | 0.068 [0.060–0.103] | 0.042 [0.062] | 0.018 | 0.591 |
| 4b json (contrast) | 495 | 0.143 [0.115–0.172] | 0.108 [0.078–0.141] | 0.011 [0.021] | 5.0e-04 | 0.607 |
| 9b json (contrast) | 495 | 0.159 [0.128–0.192] | 0.155 [0.123–0.189] | 0.004 [0.009] | 5.0e-04 | 0.520 |
| 27b json (contrast) | 493 | 0.077 [0.055–0.100] | 0.056 [0.033–0.081] | 0.007 [0.016] | 5.0e-04 | 0.608 |
| 4b jsonR (contrast) | 495 | 0.146 [0.117–0.176] | 0.131 [0.101–0.163] | 0.007 [0.016] | 5.0e-04 | 0.566 |
| 9b jsonR (contrast) | 494 | 0.132 [0.106–0.159] | 0.118 [0.091–0.146] | 0.008 [0.016] | 5.0e-04 | 0.612 |
| 27b jsonR (contrast) | 494 | 0.098 [0.075–0.123] | 0.089 [0.065–0.116] | 0.006 [0.014] | 5.0e-04 | 0.614 |

(Mean score to compare with the share responsive, 0.574.)

**Table E4b.** Logistic recalibration (score models): fit P(responsive) = 1/(1+exp(-(a + b·logit(score)))). A calibrated score has a = 0 and b = 1. b < 1: the scores are too extreme (overconfident); b > 1: too timid. a > 0: the scores run low overall. 95% bootstrap CIs.

| model | intercept a | slope b |
|---|---|---|
| 4b lp | -0.58 [-0.88, -0.33] | 1.68 [1.43, 2.01] |
| 9b lp | -0.23 [-0.49, +0.01] | 1.42 [1.23, 1.71] |
| 27b lp | +0.26 [-0.07, +0.56] | 0.70 [0.59, 0.90] |
| d3-4b | -0.37 [-0.60, -0.17] | 1.35 [1.12, 1.64] |
| d3-9b | -0.43 [-0.74, -0.18] | 1.77 [1.51, 2.10] |
| d3-27b | -1.58 [-2.19, -1.14] | 1.36 [1.16, 1.68] |
| Jev | -0.38 [-0.61, -0.16] | 1.58 [1.37, 1.84] |

(Slope and intercept CIs use the first 1,000 of the bootstrap resamples.)

**Table E4c.** The fixed 0.5 cutoff (JSON: the verdict). Wilson 95% CIs.

| model | recall @0.5 | eliminated @0.5 | responsive missed |
|---|---|---|---|
| 4b lp | 270/284 = 95.1% [91.9%–97.0%] | 155/211 = 73.5% [67.1%–79.0%] | 14 |
| 9b lp | 267/284 = 94.0% [90.6%–96.2%] | 169/211 = 80.1% [74.2%–84.9%] | 17 |
| 27b lp | 264/284 = 93.0% [89.4%–95.4%] | 192/211 = 91.0% [86.4%–94.2%] | 20 |
| d3-4b | 267/284 = 94.0% [90.6%–96.2%] | 135/211 = 64.0% [57.3%–70.2%] | 17 |
| d3-9b | 271/284 = 95.4% [92.3%–97.3%] | 166/211 = 78.7% [72.7%–83.7%] | 13 |
| d3-27b | 283/284 = 99.6% [98.0%–99.9%] | 166/211 = 78.7% [72.7%–83.7%] | 1 |
| Jev | 266/284 = 93.7% [90.2%–96.0%] | 153/211 = 72.5% [66.1%–78.1%] | 18 |
| 4b json (contrast) | 257/284 = 90.5% [86.5%–93.4%] | 161/211 = 76.3% [70.1%–81.5%] | 27 |
| 9b json (contrast) | 231/284 = 81.3% [76.4%–85.4%] | 183/211 = 86.7% [81.5%–90.7%] | 53 |
| 27b json (contrast) | 271/284 = 95.4% [92.3%–97.3%] | 181/209 = 86.6% [81.3%–90.6%] | 13 |
| 4b jsonR (contrast) | 248/284 = 87.3% [83.0%–90.7%] | 170/211 = 80.6% [74.7%–85.3%] | 36 |
| 9b jsonR (contrast) | 262/283 = 92.6% [88.9%–95.1%] | 162/211 = 76.8% [70.6%–82.0%] | 21 |
| 27b jsonR (contrast) | 269/284 = 94.7% [91.5%–96.8%] | 172/210 = 81.9% [76.1%–86.5%] | 15 |

**Table E4d.** Reliability, score models: in each 0.1-wide score bin, mean score → observed share responsive (number of pairs). A calibrated model has the two numbers close in every well-filled bin.

| bin | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev |
|---|---|---|---|---|---|---|---|
| 0.0–0.1 | 0.08→0.00 (24) | 0.04→0.00 (93) | 0.01→0.04 (173) | 0.03→0.00 (63) | 0.03→0.00 (62) | 0.02→0.00 (127) | 0.07→0.00 (36) |
| 0.1–0.2 | 0.15→0.03 (64) | 0.14→0.03 (37) | 0.15→0.14 (14) | 0.16→0.14 (14) | 0.15→0.00 (44) | 0.16→0.00 (15) | 0.14→0.00 (48) |
| 0.2–0.3 | 0.25→0.12 (42) | 0.24→0.10 (21) | 0.26→0.40 (10) | 0.25→0.03 (32) | 0.25→0.06 (35) | 0.24→0.00 (9) | 0.24→0.05 (41) |
| 0.3–0.4 | 0.35→0.14 (22) | 0.35→0.42 (12) | 0.36→0.56 (9) | 0.35→0.20 (20) | 0.34→0.33 (18) | 0.36→0.00 (5) | 0.34→0.36 (28) |
| 0.4–0.5 | 0.44→0.24 (17) | 0.43→0.39 (23) | 0.46→0.33 (6) | 0.44→0.43 (23) | 0.45→0.25 (20) | 0.45→0.09 (11) | 0.45→0.33 (18) |
| 0.5–0.6 | 0.56→0.43 (21) | 0.55→0.58 (26) | 0.56→0.56 (9) | 0.55→0.51 (39) | 0.56→0.62 (29) | 0.55→0.50 (10) | 0.54→0.59 (27) |
| 0.6–0.7 | 0.66→0.63 (43) | 0.65→0.74 (23) | 0.64→0.75 (4) | 0.65→0.61 (57) | 0.65→0.62 (37) | 0.65→0.43 (14) | 0.64→0.64 (45) |
| 0.7–0.8 | 0.76→0.81 (73) | 0.75→0.75 (53) | 0.75→0.80 (15) | 0.75→0.79 (86) | 0.76→0.80 (60) | 0.76→0.54 (26) | 0.75→0.72 (76) |
| 0.8–0.9 | 0.85→0.90 (135) | 0.86→0.89 (95) | 0.85→0.80 (30) | 0.85→0.87 (91) | 0.85→0.94 (97) | 0.85→0.57 (28) | 0.85→0.90 (104) |
| 0.9–1.0 | 0.92→0.98 (54) | 0.94→0.98 (112) | 0.99→0.98 (225) | 0.94→0.93 (70) | 0.93→0.98 (93) | 0.98→0.97 (250) | 0.94→1.00 (72) |

**Table E4e.** Per request, score models.

| request | model | n | Brier | ECE | mean score | share responsive |
|---|---|---|---|---|---|---|
| 24-409 | 4b lp | 246 | 0.083 | 0.099 | 0.576 | 0.585 |
| 24-409 | 9b lp | 246 | 0.077 | 0.075 | 0.551 | 0.585 |
| 24-409 | 27b lp | 246 | 0.033 | 0.021 | 0.602 | 0.585 |
| 24-409 | d3-4b | 246 | 0.123 | 0.059 | 0.544 | 0.585 |
| 24-409 | d3-9b | 246 | 0.085 | 0.092 | 0.530 | 0.585 |
| 24-409 | d3-27b | 246 | 0.081 | 0.097 | 0.682 | 0.585 |
| 24-409 | Jev | 246 | 0.105 | 0.082 | 0.639 | 0.585 |
| 25-3152 | 4b lp | 249 | 0.141 | 0.079 | 0.625 | 0.562 |
| 25-3152 | 9b lp | 249 | 0.104 | 0.068 | 0.600 | 0.562 |
| 25-3152 | 27b lp | 249 | 0.088 | 0.056 | 0.528 | 0.562 |
| 25-3152 | d3-4b | 249 | 0.143 | 0.109 | 0.650 | 0.562 |
| 25-3152 | d3-9b | 249 | 0.103 | 0.104 | 0.633 | 0.562 |
| 25-3152 | d3-27b | 249 | 0.058 | 0.050 | 0.597 | 0.562 |
| 25-3152 | Jev | 249 | 0.127 | 0.106 | 0.544 | 0.562 |

**Table E4f.** Paired bootstrap differences (A − B; negative = A better calibrated), same resamples as E4a.

| A − B | ΔBrier [95% CI] | p | ΔECE [95% CI] | p |
|---|---|---|---|---|
| d3-27b − 27b lp | +0.010 [-0.005, +0.024] | 0.21 | +0.036 [+0.004, +0.051] | 0.023 |
| d3-27b − Jev | -0.046 [-0.058, -0.034] | 1.0e-03 | -0.002 [-0.041, +0.015] | 0.36 |
| 27b lp − Jev | -0.056 [-0.070, -0.040] | 1.0e-03 | -0.038 [-0.067, -0.013] | 0.003 |
| d3-4b − 4b lp | +0.021 [+0.009, +0.033] | 1.0e-03 | -0.039 [-0.058, +0.004] | 0.086 |
| d3-9b − 9b lp | +0.003 [-0.008, +0.015] | 0.57 | +0.028 [-0.002, +0.049] | 0.071 |
| 9b lp − 4b lp | -0.022 [-0.033, -0.011] | 1.0e-03 | -0.035 [-0.053, +0.002] | 0.070 |

**Table E4g.** Label shift. If the responsive share among the emails screened were lower than the golden set's 57.4%, and responsive and non-responsive emails each scored as they do here, a score s from a model calibrated on this set would correspond to these probabilities (odds rescaled by the ratio of prior odds).

| score here | at 57.4% (as here) | at 30% | at 10% | at 3% |
|---|---|---|---|---|
| 0.20 | 0.200 | 0.074 | 0.020 | 0.006 |
| 0.50 | 0.500 | 0.242 | 0.076 | 0.022 |
| 0.80 | 0.800 | 0.560 | 0.248 | 0.084 |
| 0.95 | 0.950 | 0.858 | 0.611 | 0.304 |

**What the tables show.**

- **Brier.** Lowest for the 27b lp (0.060) and d3-27b (0.070); highest for d3-4b (0.133). Both 27b
  models beat Jev (−0.056 and −0.046, p 1.0e-03, the smallest p 2,000 redraws can give). d3-27b vs
  27b lp: +0.010 [−0.005, +0.024], not distinguishable (E4a, E4f).
- **ECE against the noise floor.**
  - The 9b lp, 27b lp and d3-4b are within what bin noise alone would produce if they were
    calibrated (p 0.16, 0.10, 0.40).
  - The 4b lp, d3-9b, d3-27b and Jev are not (p 0.002, 0.001, 5.0e-04, 0.018) (E4a).
- **Slope.** No model's slope CI contains 1 (E4b).
  - **27b lp: too extreme** (0.70 [0.59, 0.90]). Of the 173 pairs it scores below 0.1 (mean 0.01),
    4% are responsive (E4d).
  - **The other six: compressed toward the middle** (slopes 1.35 to 1.77). The truth is more extreme
    than their scores. At the low end that errs on the safe side for screening: of the 48 pairs Jev
    scores 0.1–0.2, none is responsive.
- **d3-27b runs high in the middle.**
  - Of the pairs it scores 0.7–0.8 and 0.8–0.9, only 54% and 57% are responsive (n = 26, 28);
    intercept −1.58 (E4b, E4d).
  - Its 0.5 cutoff happens to give 99.6% recall here (283/284). That reflects where its scores fall
    on this set, not a calibrated meaning of "50%" (E4c).
- **The 0.5 cutoff in general.** Recall ranges from 93.0% (27b lp) to 99.6% (d3-27b), i.e. 1 to 20 of
  284 responsive emails missed. Only d3-27b reaches 98% at 0.5 on this set (E4c).
- **Calibration differs by request.** On 24-409 the d3-27b's mean score is 0.682 against a share responsive of
  0.585. The 27b lp's ECE is 0.021 on 24-409 and 0.056 on 25-3152 (E4e).
- **Which scores can be read as probabilities?** On this set, roughly the 27b lp's: ECE 0.030,
  intercept +0.26 [−0.07, +0.56], with overconfident extremes. Read the others as rankings.
  - In a real request, no model's scores should be read as probabilities without recalibrating on that
    request's data, because the golden set is 57.4% responsive by design. If responsive and
    non-responsive emails scored the same way in a request where 10% are responsive, a score that is
    calibrated here at 0.5 would mean 0.076 there (E4g).
  - That rescaling assumes each class's score distribution carries over, which the synthetic mix
    doesn't guarantee.

## E5. Same base, different packaging: stock Qwen vs d3

**Table E5a.** What differs between the runs (run.json). Prompt 2 in every run; the d3 runs send the same instructions through System One's fields instead of a system prompt.

| label | run | model | params | quantization | runner | num_batch | unload every call | Ollama |
|---|---|---|---|---|---|---|---|---|
| 4b lp | golden_qwen3.5_4b_logprob_p2db | qwen3.5:4b | 4.7B | Q4_K_M | ggml | default | no | 0.40.13 |
| 4b lp fresh | golden_qwen3.5_4b_logprob_p2dbf | qwen3.5:4b | 4.7B | Q4_K_M | ggml | default | yes | 0.40.13 |
| d3-4b | golden_d3-ctx8k_4b_noul_p2 | d3-ctx8k:4b | 4.8B | Q8_0 | llamacpp | 8192 | no | 0.40.13 |
| 9b lp | golden_qwen3.5_9b_logprob_p2db | qwen3.5:9b | 9.7B | Q4_K_M | ggml | default | no | 0.40.13 |
| 9b lp fresh | golden_qwen3.5_9b_logprob_p2dbf | qwen3.5:9b | 9.7B | Q4_K_M | ggml | default | yes | 0.40.13 |
| d3-9b | golden_d3-ctx8k_9b_noul_p2 | d3-ctx8k:9b | 9.0B | Q8_0 | llamacpp | 8192 | no | 0.40.13 |
| 27b lp | golden_qwen3.8_27b_logprob_p2 | qwen3.8:27b | 27.3B | Q4_K_M | ggml | default | no | 0.40.13 |
| d3-27b | golden_d3-ctx8k_27b_noul_p2 | d3-ctx8k:27b | 26.9B | Q8_0 | llamacpp | 8192 | no | 0.40.13 |

The stock run and the d3 run differ in more than the model: quantization (Q8_0 vs Q4_K_M), Ollama
runner (llamacpp vs ggml), batch size (8192 vs default), and how the prompt is delivered (System
One's fields vs a system prompt), on top of d3's own training and its noncausal attention. These runs
can't separate the effects. A difference below is a difference between the two *packages*.

**Table E5b.** d3 minus stock, paired bootstrap (5000 resamples, stratified by label, seed 808). elim@98 in percentage points. Holm adjusts across all 24 p-values in the table.

| size | pairs | n | AUROC stock → d3 | ΔAUROC [95% CI] | p | Holm p (24) | elim@98 stock → d3 | Δelim@98 [95% CI] | p | Holm p (24) |
|---|---|---|---|---|---|---|---|---|---|---|
| 4b | all 495 | 495 | 0.923 → 0.884 | -0.039 [-0.066, -0.014] | 0.003 | 0.053 | 51.7% → 53.6% | +1.9 [-17.5, +14.7] | 0.87 | 1 |
| 4b | 24-409 | 246 | 0.964 → 0.880 | -0.084 [-0.127, -0.045] | 4.0e-04 | 0.010 | 71.6% → 62.7% | -8.8 [-23.5, +6.9] | 0.41 | 1 |
| 4b | 25-3152 | 249 | 0.883 → 0.889 | +0.005 [-0.036, +0.045] | 0.81 | 1 | 29.4% → 45.0% | +15.6 [-26.6, +41.3] | 0.52 | 1 |
| 4b | 25-3152 +roster | 249 | 0.950 → 0.961 | +0.011 [-0.013, +0.036] | 0.35 | 1 | 75.2% → 86.2% | +11.0 [+2.8, +30.3] | 0.019 | 0.32 |
| 9b | all 495 | 495 | 0.942 → 0.947 | +0.005 [-0.013, +0.023] | 0.63 | 1 | 70.6% → 68.2% | -2.4 [-10.0, +7.6] | 0.62 | 1 |
| 9b | 24-409 | 246 | 0.962 → 0.960 | -0.002 [-0.022, +0.018] | 0.86 | 1 | 76.5% → 73.5% | -2.9 [-12.7, +6.9] | 0.59 | 1 |
| 9b | 25-3152 | 249 | 0.927 → 0.947 | +0.020 [-0.009, +0.053] | 0.17 | 1 | 69.7% → 74.3% | +4.6 [-12.8, +15.6] | 0.66 | 1 |
| 9b | 25-3152 +roster | 249 | 0.963 → 0.979 | +0.016 [-0.005, +0.038] | 0.14 | 1 | 67.9% → 89.9% | +22.0 [+10.1, +34.9] | 0.002 | 0.040 |
| 27b | all 495 | 495 | 0.975 → 0.979 | +0.004 [-0.004, +0.013] | 0.34 | 1 | 75.8% → 81.0% | +5.2 [-6.2, +9.0] | 0.48 | 1 |
| 27b | 24-409 | 246 | 0.992 → 0.992 | -0.000 [-0.005, +0.004] | 0.84 | 1 | 89.2% → 91.2% | +2.0 [-11.8, +9.8] | 1 | 1 |
| 27b | 25-3152 | 249 | 0.955 → 0.980 | +0.026 [+0.010, +0.045] | 4.0e-04 | 0.010 | 74.3% → 85.3% | +11.0 [+5.5, +25.7] | 0.002 | 0.034 |
| 27b | 25-3152 +roster | 249 | 0.989 → 0.998 | +0.009 [+0.003, +0.017] | 8.0e-04 | 0.018 | 90.8% → 98.2% | +7.3 [+1.8, +11.9] | 0.003 | 0.053 |

**Table E5c.** By kind and recipe, all 495 pairs: pairs flagged responsive, stock vs d3. For + groups this is recall (higher is better); for − groups it is pass-through (lower is better). Each model at its own pooled thr98, and both at the fixed 0.5 cutoff. Exact McNemar p (unadjusted; 36 rows × 2 cutoffs).

| size | group | label | n | @own thr98: stock vs d3 | p | @0.5: stock vs d3 | p |
|---|---|---|---|---|---|---|---|
| 4b | real_positive | + | 150 | 145 vs 146 | 1 | 139 vs 139 | 1 |
| 4b | close_call_positive | + | 50 | 50 vs 49 | 1 | 49 vs 45 | 0.22 |
| 4b | privileged_positive | + | 40 | 40 vs 40 | 1 | 39 vs 39 | 1 |
| 4b | exempt_other_positive | + | 40 | 40 vs 40 | 1 | 40 vs 40 | 1 |
| 4b | hard_negative_flipped | + | 4 | 4 vs 4 | 1 | 3 vs 4 | 1 |
| 4b | real_negative | − | 120 | 25 vs 18 | 0.30 | 4 vs 3 | 1 |
| 4b | hard_negative | − | 91 | 77 vs 80 | 0.63 | 52 vs 73 | 3.2e-04 |
| 4b |   hn/same subject, wrong date | − | 20 | 20 vs 20 | 1 | 18 vs 17 | 1 |
| 4b |   hn/keyword, unrelated sense | − | 19 | 18 vs 17 | 1 | 12 vs 15 | 0.45 |
| 4b |   hn/keyword in signature/newsletter | − | 20 | 15 vs 14 | 1 | 7 vs 13 | 0.070 |
| 4b |   hn/forwarded, no content | − | 17 | 12 vs 14 | 0.69 | 6 vs 13 | 0.016 |
| 4b |   hn/same people, different subject | − | 15 | 12 vs 15 | 0.25 | 9 vs 15 | 0.031 |
| 9b | real_positive | + | 150 | 147 vs 147 | 1 | 138 vs 143 | 0.33 |
| 9b | close_call_positive | + | 50 | 49 vs 48 | 1 | 47 vs 46 | 1 |
| 9b | privileged_positive | + | 40 | 40 vs 40 | 1 | 40 vs 39 | 1 |
| 9b | exempt_other_positive | + | 40 | 40 vs 40 | 1 | 40 vs 39 | 1 |
| 9b | hard_negative_flipped | + | 4 | 3 vs 4 | 1 | 2 vs 4 | 0.50 |
| 9b | real_negative | − | 120 | 5 vs 1 | 0.22 | 1 vs 1 | 1 |
| 9b | hard_negative | − | 91 | 57 vs 66 | 0.078 | 41 vs 44 | 0.66 |
| 9b |   hn/same subject, wrong date | − | 20 | 18 vs 17 | 1 | 17 vs 10 | 0.016 |
| 9b |   hn/keyword, unrelated sense | − | 19 | 11 vs 15 | 0.22 | 7 vs 10 | 0.38 |
| 9b |   hn/keyword in signature/newsletter | − | 20 | 10 vs 10 | 1 | 7 vs 7 | 1 |
| 9b |   hn/forwarded, no content | − | 17 | 7 vs 10 | 0.38 | 4 vs 6 | 0.62 |
| 9b |   hn/same people, different subject | − | 15 | 11 vs 14 | 0.25 | 6 vs 11 | 0.062 |
| 27b | real_positive | + | 150 | 146 vs 145 | 1 | 135 vs 149 | 1.2e-04 |
| 27b | close_call_positive | + | 50 | 50 vs 50 | 1 | 48 vs 50 | 0.50 |
| 27b | privileged_positive | + | 40 | 39 vs 40 | 1 | 39 vs 40 | 1 |
| 27b | exempt_other_positive | + | 40 | 40 vs 40 | 1 | 39 vs 40 | 1 |
| 27b | hard_negative_flipped | + | 4 | 4 vs 4 | 1 | 3 vs 4 | 1 |
| 27b | real_negative | − | 120 | 0 vs 0 | 1 | 0 vs 0 | 1 |
| 27b | hard_negative | − | 91 | 51 vs 40 | 0.043 | 19 vs 45 | 8.7e-07 |
| 27b |   hn/same subject, wrong date | − | 20 | 10 vs 3 | 0.016 | 3 vs 3 | 1 |
| 27b |   hn/keyword, unrelated sense | − | 19 | 12 vs 13 | 1 | 7 vs 13 | 0.031 |
| 27b |   hn/keyword in signature/newsletter | − | 20 | 10 vs 7 | 0.45 | 2 vs 11 | 0.004 |
| 27b |   hn/forwarded, no content | − | 17 | 7 vs 6 | 1 | 2 vs 7 | 0.062 |
| 27b |   hn/same people, different subject | − | 15 | 12 vs 11 | 1 | 5 vs 11 | 0.031 |

**Table E5d.** Score shift and rank agreement (all 495 pairs).

| size | mean score, responsive: stock → d3 | mean score, non-responsive: stock → d3 | Spearman ρ | same decision at 0.5 |
|---|---|---|---|---|
| 4b | 0.793 → 0.774 | 0.342 → 0.360 | 0.786 | 436/495 |
| 9b | 0.818 → 0.806 | 0.249 → 0.279 | 0.845 | 448/495 |
| 27b | 0.903 → 0.947 | 0.109 → 0.226 | 0.961 | 446/495 |

**Accuracy.**

- **4b.** d3 ranks worse overall (−0.039 [−0.066, −0.014], p 0.003), just short of surviving Holm
  (0.053). The whole gap comes from the topical request 24-409 (−0.084, Holm p 0.010), which does
  survive; on 25-3152 there is no difference. No elim@98 difference is detectable (E5b).
- **9b.** No difference without the roster. With the roster, d3 eliminates more (67.9% → 89.9%,
  +22.0 [+10.1, +34.9], Holm p 0.040). Its AUROC change is not distinguishable (+0.016, p 0.14), so the
  gain is concentrated around the high-recall cutoff rather than across the whole ranking (E5b).
- **27b.** Identical on 24-409 (0.992 → 0.992). Better on 25-3152: AUROC +0.026 [+0.010, +0.045],
  Holm p 0.010; elim@98 +11.0, Holm p 0.034. With the roster: AUROC +0.009 (Holm p 0.018); elim@98
  +7.3, just short of surviving Holm (0.053) (E5b).
- **Where d3 helps.** On the correspondent-scoped request, where responsiveness turns on who sent or
  received an email rather than its topic: at 27b, and at 9b and 27b once the roster is supplied.
- **d3 scores run higher.** At 27b the mean score on non-responsive pairs goes from 0.109 to 0.226
  (E5d).
  - At 0.5, d3-27b therefore flags more of everything: real positives 135 → 149 (p 1.2e-04), but also
    hard negatives 19 → 45 (p 8.7e-07).
  - At each model's own thr98, d3-27b passes fewer hard negatives (51 → 40, p 0.043), mostly
    wrong-date emails (10 → 3) (E5c).
  - The two rankings agree closely at 27b (Spearman 0.961) and less at 4b (0.786) (E5d).

**Table E5e.** Latency per email, milliseconds (single stream, Strix Halo). 'stock cached' = the main run (prefix cache on); 'stock fresh' = the same model unloaded before every call (p2dbf), so nothing is cached: prefill = Ollama's server-side prompt processing, load = model load, wall = the whole call as the scorer saw it (includes load); server total = Ollama's server-side total_ms (prefill + 1-token decode, load excluded). d3 reports only wall time. ms/1k tok = median of per-pair wall (or prefill) ÷ prompt tokens.

| size | n | prompt tok stock / d3 (median) | stock cached: median wall | mean wall | median wall − server total (client/HTTP overhead) | stock fresh: median prefill | mean prefill | median server total (no load) | median load | median wall | prefill ms/1k tok | d3: median wall | mean wall | wall ms/1k tok | d3 wall ÷ stock fresh prefill, per pair: median [IQR] | d3 wall ÷ stock cached wall, per pair: median |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4b | 495 | 1797 / 1872 | 504 | 606 | 2.7 | 836 | 907 | 845 | 1,687 | 2,503 | 463 | 877 | 1,049 | 481 | 1.07 [1.03–1.24] | 1.76 |
| 9b | 495 | 1797 / 1872 | 856 | 1,020 | 4.3 | 1,379 | 1,518 | 1,388 | 2,184 | 3,482 | 775 | 1,426 | 1,636 | 785 | 1.06 [1.01–1.11] | 1.67 |
| 27b | 495 | 1797 / 1872 | 2,649 | 3,217 | 4.1 | not run | not run | not run | not run | not run | not run | 4,667 | 5,293 | 2546 | — | 1.76 |
| 4b +roster | 249 | 3166 / 3247 | 446 | 541 | 2.7 | 1,443 | 1,528 | 1,457 | 1,692 | 3,150 | 455 | 1,739 | 1,924 | 544 | 1.23 [1.20–1.29] | 3.93 |
| 9b +roster | 249 | 3166 / 3247 | 734 | 916 | 4.5 | 2,416 | 2,560 | 2,430 | 2,192 | 4,606 | 763 | 2,639 | 2,878 | 821 | 1.11 [1.09–1.14] | 3.67 |
| 27b +roster | 249 | 3166 / 3247 | 2,231 | 2,871 | 4.5 | not run | not run | not run | not run | not run | not run | 8,550 | 9,281 | 2651 | — | 3.80 |

**Table E5f.** Latency by prompt length (bucketed on the stock prompt's token count), main set, medians in ms.

| size | stock prompt tokens | n | stock cached wall | stock fresh prefill | d3 wall |
|---|---|---|---|---|---|
| 4b | 0–1,000 | 26 | 185 | 458 | 431 |
| 4b | 1,000–2,000 | 288 | 367 | 690 | 712 |
| 4b | 2,000–3,000 | 115 | 833 | 1,106 | 1,382 |
| 4b | 3,000–5,000 | 66 | 1,263 | 1,492 | 1,891 |
| 9b | 0–1,000 | 26 | 310 | 759 | 713 |
| 9b | 1,000–2,000 | 288 | 622 | 1,157 | 1,175 |
| 9b | 2,000–3,000 | 115 | 1,420 | 1,880 | 2,091 |
| 9b | 3,000–5,000 | 66 | 2,150 | 2,495 | 2,825 |
| 27b | 0–1,000 | 26 | 984 | not run | 2,369 |
| 27b | 1,000–2,000 | 288 | 1,881 | not run | 3,886 |
| 27b | 2,000–3,000 | 115 | 4,459 | not run | 6,717 |
| 27b | 3,000–5,000 | 66 | 6,839 | not run | 9,052 |

**Table E5g.** Sanity check: stock cached vs stock fresh scores for the same pairs (should be near-identical; only speed should differ).

| size | pairs | max |Δscore| | mean |Δscore| | AUROC cached / fresh | elim@98 cached / fresh |
|---|---|---|---|---|---|
| 4b | 495 | 0.1746 | 0.01776 | 0.923 / 0.921 | 51.7% / 53.1% |
| 4b +roster | 249 | 0.1614 | 0.01994 | 0.950 / 0.950 | 75.2% / 70.6% |
| 9b | 495 | 0.1532 | 0.02286 | 0.942 / 0.945 | 70.6% / 72.0% |
| 9b +roster | 249 | 0.1272 | 0.01850 | 0.963 / 0.963 | 67.9% / 67.9% |

**Latency.**

- **Without prefix reuse, the speeds match at typical prompt lengths.** d3 wall time divided by the
  stock fresh prefill, per pair, has a median of 1.07 at 4b and 1.06 at 9b. Per 1,000 prompt tokens:
  481 vs 463 ms at 4b, 785 vs 775 ms at 9b. The d3 prompts are slightly longer (median 1,872 vs 1,797
  tokens) (E5e).
- **Against the cached stock run,** d3 takes 1.76× (4b), 1.67× (9b) and 1.76× (27b) per pair. With
  the roster (median prompt 3,166 tokens) it takes 3.93×, 3.67× and 3.80×, because the stock model's
  cache covers the roster and d3 recomputes it on every call. Most of d3's slowdown is the lost prefix
  cache (E5e).
- **But not all of it.** On longer prompts d3 is slower than stock even with no cache: the per-pair
  ratio is 1.23 (4b) and 1.11 (9b) with the roster. In the 2,000–3,000-token bucket the 4b d3 takes
  1,382 ms against a stock fresh prefill of 1,106 ms; below 2,000 tokens the two are close
  (E5e, E5f).
  - Possible causes, which these runs can't separate: noncausal attention doing more work per token as
    prompts grow, the Q8_0 weights, or the different runner.
  - Client and HTTP overhead doesn't explain it: for the stock cached runs, wall time minus Ollama's
    server-side total has a median of 2.7–4.5 ms.
- **27b has no stock run without the cache.** Its 1.76× ratio matches the smaller sizes, which is
  consistent with the same explanation but not checked directly.
- **The cached and fresh stock runs don't give identical scores** (E5g). The per-pair difference has a
  mean of 0.018–0.023 and a maximum of 0.17. AUROC moves by at most 0.003 (0.942 vs 0.945), but
  elim@98 moves by up to 4.6 points (75.2% vs 70.6%).
  - This is backend run-to-run noise. Below about that size, an elim@98 difference between two
    models shouldn't be trusted even when the bootstrap says it is real.

## Findings

| # | finding | confidence | rests on |
|---|---|---|---|
| 1 | On the main set, AUROC separates three tiers: {27b lp, d3-27b} > {9b lp, d3-9b, 4b lp, Jev} > d3-4b, except that d3-4b and Jev can't be told apart. 13 of 21 differences survive Holm under all three readings (bootstrap percentile, normal curve, DeLong). The two 27b models can't be told apart (+0.004 [−0.004, +0.013]) | high | E1b, E1d, E1e |
| 2 | elim@98 can't rank neighbouring models on this set. Only 8 of 21 differences survive Holm (the same 8 under either reading), all of them the 27b models against Jev, 4b lp and d3-4b, or the 9b models against d3-4b. The 4b → 9b gap (+19.0 [+0.5, +31.8]) and d3-27b vs 27b lp (+5.2 [−5.7, +9.0]) are not established | high (that they are not established) | E1a, E1c |
| 3 | On the 25-3152 roster set, d3-27b has the highest elim@98 (98.2%). It beats all six others after Holm by the percentile p, and five by the more conservative normal reading. Its margin over the 27b lp (+7.3 [+1.8, +11.9]) falls just short under that reading (Holm p 0.064) and is close to the backend noise seen in E5g. The AUROC ranking near the ceiling depends on the reading: 10 differences survive by the percentile p, 4 by DeLong or the normal curve, because the bootstrap's far tail is thin there (E1f) | medium | E1a–E1e (roster), E5g |
| 4 | d3-27b (and the stock 27b lp) reject *same subject, wrong date* emails far more often than Jev: at each model's thr98, at 0.5, without a cutoff (0.988 vs 0.684) and with re-estimated cutoffs (+80 [+59, +95]). Jev would have to drop to 44.7% recall to match d3-27b's 3/20 | high (on these 20 synthetic emails) | E2b, E2e–E2i |
| 5 | Jev reacts to the date (12/12 altered copies score below their source) but by too little (median drop 0.16) to cross its cutoff. That dates are a *specific* weakness, compared with its other recipes, is weak (Fisher p 0.019, Holm 0.097) | medium | E2d, E2j, E2k |
| 6 | "d3-27b handles dates better than the stock 27b" is not supported [disputed in verification: *not established*; see concern 1]. The 3 vs 10 gap at thr98 doesn't survive Holm (0.19); they tie at 0.5 (3 vs 3); threshold-free 0.988 vs 0.976 (p 0.15). The gap comes from the 27b lp's low pooled cutoff (0.069) | medium | E2b, E2e, E2f, E2g, E2i, E2k |
| 7 | On the main set, the JSON verdict modes are never on the speed/accuracy frontier in E3c's 2,000 redraws (4 of 2,000 for 27b json in an independent bootstrap). On 25-3152, 27b json +roster is on it in 31% (elim@98) and 48% (AUROC) of redraws, through a near-tie with 27b lp +roster. [corrected in verification: the original said "never ... in any bootstrap redraw" without restricting it to the main set] Their decoding alone takes longer than the whole lp call of the same model | high (main set) | E3a, E3b, E3c |
| 8 | The local frontier is 4b lp → 9b lp → 27b lp → d3-27b (plus d3-9b on AUROC). The steps between neighbours are not individually distinguishable from noise; only the jump from 4b lp to the 27b class is | medium | E3a, E3c, E1c |
| 9 | Jev is the fastest configuration: 117 ms median, and the fastest local one (4b lp) takes 4.3× as long. The only local models that beat it on both AUROC and elim@98 after Holm are the 27b lp (22.7× its median time) and d3-27b (40.0×) | high on this set; Jev's network time and run-to-run noise are unmeasured | E3d, E1b, E1c |
| 10 | With Ollama's prefix cache, adding the roster costs the stock models nothing (4b lp 450 → 446 ms) while raising AUROC. The d3 models pay for it on every call (d3-27b 4,758 → 8,550 ms) | high | E3b, E5e |
| 11 | No model's score is a calibrated probability in the strict sense (every slope CI excludes 1). The 27b lp comes closest (ECE 0.030, intercept ≈ 0) but is overconfident at the extremes. The other six are compressed toward the middle. d3-27b overstates throughout its 0.1–0.9 range | medium | E4a, E4b, E4d |
| 12 | Calibration measured on this set (57.4% responsive) would overstate probabilities in a request with fewer responsive emails; a calibrated 0.5 here would mean 0.076 at 10% | high in direction; the size depends on the real share and assumes the score distributions carry over | E4g |
| 13 | At 0.5, recall ranges from 93.0% to 99.6%. Only d3-27b reaches 98% at 0.5, because its scores run high, not because 0.5 means anything special for it | high (on this set) | E4c, E5d |
| 14 | Same base, different package: d3 helps at 27b on 25-3152 (AUROC +0.026, elim@98 +11.0) and with the roster at 9b (elim@98 +22.0) and 27b (AUROC +0.009), hurts at 4b on 24-409 (AUROC −0.084), and makes no detectable difference elsewhere. Quantization, runner and prompt delivery are confounded with the model | medium | E5a, E5b |
| 15 | d3's slowdown against stock is mostly the lost prefix cache: d3 ≈ stock with no cache (per-pair ratio 1.07 / 1.06) vs 1.67–1.76× against cached stock. A residual gap grows with prompt length (1.23 / 1.11 with the roster) | high for 4b and 9b; low for 27b (no uncached stock run) | E5e, E5f |
| 16 | Backend run-to-run noise (stock cached vs fresh) moves elim@98 by up to 4.6 points and AUROC by at most 0.003. The bootstrap doesn't include it | high | E5g |

## Caveats

- **A designed set, not a sample of real searches.** It covers two requests, is 57.4% responsive,
  and has synthetic close calls and hard negatives. "Real" differences here are robust to redrawing
  these pairs; they are not shown to hold on another request or another mix (branch D).
- **One run per configuration.** The bootstrap leaves out backend noise (E5g). Run-to-run noise for
  d3 and Jev was not measured, and Jev's scores are rounded to two decimals, which creates ties.
- **elim@98 rests on the 5 (main) or 2 (roster) lowest-scoring responsive pairs.** Percentile
  bootstraps of statistics that depend that much on the tail of a distribution are rough.
- **p-value floors.** With 10,000, 5,000 and 2,000 redraws, the smallest bootstrap p-values possible
  are 2.0e-04, 4.0e-04 and 1.0e-03. Many entries sit at the floor.
- **Near the AUROC ceiling (roster set), the percentile bootstrap p is anti-conservative.** It rests on
  a far tail that is thinner than a normal curve with the same spread (E1f). This write-up uses the
  normal or DeLong reading there. Treat the rankings among the top roster models as less certain than
  the main set's.
- **ECE.** Bootstrap CIs for ECE are biased upward, because a redraw adds noise to each bin. The
  "ECE if calibrated" redraw test is the better guide to whether a model is calibrated.
- **Multiplicity.** Holm was applied within the families named in each table. E2, E4 and E5 also
  print many unadjusted p-values (E5c alone has 72), and at 0.05 some of those will be false alarms.
- **Small groups.** Each recipe has 15–20 emails. The wrong-date emails are synthetic (Opus-written),
  and 12 of the 20 were derived from a responsive email in the set.
- **Pooled cutoffs.** thr98 is set on both requests together. Per-request or label-free cutoffs
  (branch A) would change the pass-through counts in E2.
- **Latency.** Single stream on one machine (Strix Halo). Jev's time includes the network, and its
  compute time is unknown. d3 reports wall time only. The 4b and 9b JSON runs used batch 8192, which
  disables the prefix cache. There is no uncached stock 27b run.
- **Prompt 2 was written after reading this set's misses,** so all prompt-2 results are in-sample.

## Reproduce

Run from the project root. Stdlib only, fixed seeds; two consecutive runs of all five scripts gave
byte-identical output, and each finishes in under 30 seconds.

| command | prints |
|---|---|
| `uv run python scripts/analysis/e_comparisons_pairwise.py` (`--boot 10000`) | E0, E1a–E1f (main and roster) |
| `uv run python scripts/analysis/e_comparisons_recipes.py` (`--boot 5000`) | E2a–E2k |
| `uv run python scripts/analysis/e_comparisons_frontier.py` (`--boot 2000`) | E3a–E3d |
| `uv run python scripts/analysis/e_comparisons_calibration.py` (`--boot 2000 --sims 2000`) | E4a–E4g |
| `uv run python scripts/analysis/e_comparisons_packaging.py` (`--boot 5000`) | E5a–E5g |

`scripts/analysis/e_comparisons_common.py` holds the run list, the loaders (through
`golden_report.load_runs()`), and the metric and test helpers (Brier, ECE, logistic fit, Holm, exact
McNemar, Fisher, DeLong, Wilson). These were checked against independent implementations: DeLong's
single-AUROC standard error for the 27b lp (0.0058) matches the spread of its bootstrap (Table E1f).

## Open questions

1. Does a stock Qwen at Q8_0 match d3? That would separate d3's training from its quantization (E5).
2. An uncached stock 27b run (like p2dbf) would confirm the latency explanation at 27b.
3. Repeat runs of d3 and Jev would measure their run-to-run noise, which is unknown.
4. Real (not synthetic) out-of-range emails, including in-range emails that quote old threads, would
   test date handling beyond the recipe. Does the county's search already filter by date?
5. Would recalibrating on a small labelled sample from the target request make the scores readable as
   probabilities there (branch A)?
6. Why does the d3/stock latency gap grow with prompt length?

## Verification

*Skeptic pass, 2026-11-06. It reads the same saved runs, with no model, GPU or network calls. The
independent code is `scripts/analysis/e_comparisons_verify.py` (`uv run python
scripts/analysis/e_comparisons_verify.py`, default `--boot 2000`, about 10 s; two runs gave
byte-identical output). It imports none of the `e_comparisons_*` modules. It has its own loader, which
joins labels from `data/golden/pairs.jsonl` on `pair_id`. It computes AUROC from scratch two ways
(every responsive × non-responsive pair counted, ties = ½; and a sort-and-search version), and thr98
as the k-th highest responsive score, where k is the smallest count with k/n ≥ 98%. It also has its own
elim@98, DeLong, exact McNemar, Fisher, Holm, Brier, ECE, logistic fit, Pareto frontier, resampler and
seeds. The repo helpers in `scripts/analyze.py` are imported only to cross-check. The script's full
output is pasted at the end of this section; V0–V10 below refer to it.*

### What was checked

| # | check | result |
|---|---|---|
| 1 | Re-ran the five branch-E scripts with default arguments; compared every table line in this document with their output | **Confirmed.** All 594 data-table and frontier lines (E0–E5g) match the fresh output byte for byte. The 40 lines that don't are this document's own prose tables (Terms, Findings, Reproduce) |
| 2 | Labels from pairs.jsonl, not scores.jsonl; rows whose pair_id isn't in pairs.jsonl dropped | **Confirmed** (`load_runs()` joins on pair_id). In these 30 runs no row's saved label differs from pairs.jsonl, none is missing from it, and no pair_id repeats (V0), so stale labels couldn't have affected these results |
| 3 | Right runs; denominators | **Confirmed.** Run tags match the brief (E0, V0). Main set 284 responsive / 211 not; roster set 140 / 109. The 5 unscored JSON rows (27b json 2 + 1, 9b jsonR 1, 27b jsonR 1) are dropped, and the text says so |
| 4 | Roster comparisons over the right pairs | **Confirmed.** All seven roster runs score the same 249 pairs, all from 25-3152, and these are exactly the main set's 25-3152 pairs (V0) |
| 5 | Headline numbers given in the brief (AUROC, elim@98, median wall for the seven models) | **Confirmed**, all 21 values, from scratch (V1) |
| 6 | Core metrics from scratch vs the repo helpers | **Confirmed.** My two AUROC implementations, the repo's `auroc()` and the repo's elim@98 agree exactly (largest difference 0). My thr98 equals `at_recall(pr_curve(...), 0.98)[0]` in all 14 model × set cases. A pair is flagged when score ≥ cutoff (V1). Ties (Jev's 2-decimal scores) count ½ in every implementation |
| 7 | E1 survivor counts, under an independent bootstrap (2,000 resamples, different resampler and seed) | **Confirmed with a caveat.** Main elim@98: the same 8 under both readings. Roster AUROC: 10 (percentile) and 4 (normal), the same 4. Roster elim@98: 10 and 8, the same sets. Main AUROC: 12 survive the percentile reading, not 13. The pair that drops is 4b lp − d3-4b (Holm 0.054 here vs 0.038 in E1b; normal 0.045; DeLong 0.045). Roster AUROC percentile: also 10, but one member differs (d3-27b − d3-9b in, d3-9b − 4b lp out). The counts move by about one under a reseed (V3) |
| 8 | E1 intervals computed rather than asserted | **Confirmed.** The independent CIs agree within Monte Carlo error. Example: d3-27b − 27b lp on the main set, ΔAUROC [−0.004, +0.013] in both and Δelim@98 [−5.7, +9.5] vs [−5.7, +9.0] (V3) |
| 9 | DeLong | **Confirmed.** My implementation reproduces E1b, E1f and E2g: main d3-27b − 27b lp p 0.33; roster 0.017; positives vs wrong-date 5.4e-11 / 0.15 / 4.0e-10 (V4) |
| 10 | E2 counts and tests | **Confirmed.** Wrong-date emails passing at thr98: 3, 10 and 19 of 20 (d3-27b / 27b lp / Jev); at 0.5: 3, 3 and 18. McNemar d3-27b vs Jev p 3.1e-05, Holm (21) 5.8e-04. Jev needs a 0.840 cutoff, at 127/284 = 44.7% recall; 27b lp needs 0.444, at 266/284 = 93.7%. Fisher p per model matches E2d. Bootstrap with the cutoff re-estimated in each resample: Jev − d3-27b [+59, +96]; 27b lp − d3-27b [+4, +56], p 0.045 (V2, V9) |
| 11 | "d3-27b handles wrong-date emails and Jev doesn't" | **Confirmed** at every cutoff and method checked |
| 12 | "d3-27b handles dates better than the stock 27b lp: not supported" | **Numbers confirmed; the conclusion is overstated.** See concern 1 |
| 13 | E3 frontiers, the × Jev ratios, JSON decode times | **Confirmed.** Point-estimate frontiers on the main set and on 25-3152; ratios to Jev 4.32 / 22.70 / 39.98; JSON median decode 1,760–4,040 ms (V6) |
| 14 | "The JSON modes are never on the frontier, in any redraw" | **Corrected.** This holds only for the main set, and only for E3c's seed. On 25-3152, 27b json +roster is on the frontier at the point estimate (E3b) and in 31% / 48% of E3c's redraws. In my independent redraws it is on the frontier in 604 (elim@98) and 948 (AUROC) of 2,000, and 27b json is on the main-set elim@98 frontier in 4 of 2,000 (V6). In those 4 redraws, the few responsive pairs that 27b json scores near 0 happen to be under-drawn, so its cutoff jumps |
| 15 | E4 Brier, ECE, slope, intercept, recall and elimination at 0.5, label shift | **Confirmed** (V5) |
| 16 | E5b subsets (d3 − stock) | **Confirmed.** Point estimates identical; CIs agree within Monte Carlo error (V10) |
| 17 | E5e latency ratios, and "d3's slowdown is the lost prefix cache" | **Confirmed, and backed by a second source.** The stock 4b and 9b JSON runs prefill at 471 / 798 ms per 1k tokens, against d3's 481 / 785 (V7). These runs use the same Q4_K_M weights and ggml runner as stock lp, batch 8192 like d3, are warm, and have no prefix cache |
| 18 | E5: the residual gap on long prompts comes from noncausal attention, the Q8_0 weights or the runner | **An alternative explanation is missing.** See concern 2 |
| 19 | E5g, cached vs fresh | **Numbers confirmed** (V8). For the interpretation, see concern 4 |

### Corrections made

1. **E3, "What the tables show":** "The JSON modes are never on the frontier, in any redraw" now
   applies to the main set only, and the 25-3152 exception is stated (check 14).
2. **Findings, row 7:** the same correction.
3. **Short answer, frontier bullet:** the same qualifier.

These were errors in the prose; no script produced them, so no script was changed. I checked every
other number in the prose against the tables, and they match.

### Remaining concerns (not corrected; judgments for the reader)

1. **E2, part 3 ("d3-27b handles dates better than the stock 27b lp. Not supported") overstates.**
   The data show mixed evidence, not an absence of evidence.
   - **At matched recall** (V2), d3-27b passes fewer wrong-date emails than 27b lp at every level from
     98% up: 3 vs 10 at 98% and at 99% (p 0.016), and 3 vs 16 at 100% (p 2.4e-04). At 93–95% recall
     there is no difference (3 vs 2, 4 vs 2).
   - **The "tie at 0.5" (3 vs 3) compares unlike cutoffs.** At 0.5, 27b lp's recall is 93.0% (20
     responsive emails missed) and d3-27b's is 99.6% (1 missed).
   - **E2d points the other way, and part 3 doesn't cite it.** d3-27b passes wrong-date emails much
     less often than its other recipes (15% vs 52%, Holm p 0.027). 27b lp shows no date effect (50%
     vs 58%, p 0.61).
   - **The matched-copy argument compares different scales.** That 27b lp's score drops more on
     matched copies (+0.92 vs +0.72) reflects how far its scores sit toward 0 and 1 (calibration slope
     0.70). For a screen, what counts is how many copies pass: 6/12 for 27b lp vs 3/12 for d3-27b (E2j).
   - **Holm over all 21 model pairs is the strictest family available.** If the family is only the
     three pairs the brief singles out, the thr98 test has Holm p 0.016 (V2).
   - **A fair summary:** at 98% recall or higher, d3-27b lets fewer wrong-date emails through than the
     stock 27b. The pattern is consistent, but it rests on 20 synthetic emails, doesn't survive the
     21-pair correction, and disappears at lower recall and without a cutoff. The mechanism the analyst
     names (27b lp's few very-low-scoring responsive emails force its high-recall cutoff down) explains
     the gap; it doesn't make the gap go away.
   - The recall levels in V2 were chosen after the fact (5 looks), so no single one of them settles the
     question.
2. **The residual d3 latency gap on long prompts has a cause E5 leaves out.** E5 names noncausal
   attention, the Q8_0 weights or the runner, and says these runs can't separate them. Batch size isn't
   named, although E5a lists it as one of the differences.
   - The stock JSON runs (same Q4_K_M weights and ggml runner as stock lp, batch 8192 like d3) get
     slower per token as prompts grow, exactly like d3. Stock fresh, at the default batch, does not (V7).
   - 4b, prompts of 3,500 tokens or more: d3 578, stock JSON 575, stock fresh 455 ms per 1k tokens.
   - 9b, same length: d3 856, stock JSON 878, stock fresh 762 ms per 1k tokens.
   - So the Q8_0 weights and the llamacpp runner aren't needed to explain the gap. The batch-8192
     setting is the factor d3 and the JSON runs share.
   - Caveat: the JSON prompts are worded differently, so this is a per-token comparison within length
     buckets, not pair by pair.
3. **Several survivor counts sit on the Holm boundary**, with Holm p-values between 0.034 and 0.064:
   - main AUROC, 4b lp − d3-4b: 0.038 (bootstrap), 0.044 (normal), 0.045 (DeLong);
   - main elim@98 by the normal reading: 27b lp − 4b lp, 27b lp − Jev and d3-9b − d3-4b, each 0.045;
   - roster elim@98, d3-27b − 27b lp: 0.034 by percentile, 0.064 by normal.

   A reseed moved one main-AUROC count and one roster membership (check 7). The "three tiers" result
   reproduces, but the line between the middle and bottom tiers (d3-4b vs 4b lp) sits right at 0.05.
   "High" confidence suits the top tier better than the bottom one.
4. **E5g is not pure run-to-run noise.** The cached and fresh runs take different serving paths: one
   reuses the prefix KV cache, the other reloads the model and does a full prefill. Their maximum
   per-pair difference of 0.17 shows how much the serving path moves scores, and a repeat of an
   identical run may vary less. Read the 4.6-point elim@98 swing as a rough guide to noise, not as a
   measured repeat variance.
5. **thr98 and elim@98 are in-sample.** The cutoff is chosen on the same labelled pairs it is then
   scored on (an oracle cutoff), so every elim@98 here is optimistic compared with a cutoff set
   before labels exist. The bootstrap re-picks the cutoff in each redraw, but scores it on that same
   redraw, so its intervals don't include this optimism. Branch A covers out-of-sample cutoffs. The
   caveats here mention pooled cutoffs, but not this.
6. **"The percentile bootstrap p is anti-conservative near the ceiling" is a choice, not a
   demonstration** (Caveats; E1, roster set). The bootstrap distribution may genuinely be skewed:
   AUROC is bounded at 1, and d3-27b's errors are rare. DeLong also rests on a normal approximation,
   which is known to be shaky near AUROC = 1. Taking the more conservative reading is reasonable, but
   the data don't show the other reading is wrong.
7. **27b json +roster's place on the 25-3152 AUROC frontier rests on different pairs.** It scores
   0.98911 on 248 pairs (one unscored row dropped), against 0.98906 for 27b lp +roster on 249 (V6).
8. **Finding 4's "(and the stock 27b lp)" overreaches at thr98.** Against Jev it passes 10 vs 19,
   exact p 0.004, Holm (21) 0.055. That misses the correction E2b uses, though the 0.5,
   threshold-free and re-estimated-cutoff checks all support it.
9. Minor: E2i's caption says the cutoff must "rise", but d3-27b's falls (0.586 → 0.444).

### Verification script output

Output of `uv run python scripts/analysis/e_comparisons_verify.py`, verbatim:

#### V0. Data integrity

| label | run | main rows / not in pairs.jsonl / unscored / stale label in scores.jsonl / dup | roster rows / not in pairs / unscored / stale / dup |
|---|---|---|---|
| 4b lp | golden_qwen3.5_4b_logprob_p2db | 495 / 0 / 0 / 0 / 0 | 249 / 0 / 0 / 0 / 0 |
| 9b lp | golden_qwen3.5_9b_logprob_p2db | 495 / 0 / 0 / 0 / 0 | 249 / 0 / 0 / 0 / 0 |
| 27b lp | golden_qwen3.8_27b_logprob_p2 | 495 / 0 / 0 / 0 / 0 | 249 / 0 / 0 / 0 / 0 |
| d3-4b | golden_d3-ctx8k_4b_noul_p2 | 495 / 0 / 0 / 0 / 0 | 249 / 0 / 0 / 0 / 0 |
| d3-9b | golden_d3-ctx8k_9b_noul_p2 | 495 / 0 / 0 / 0 / 0 | 249 / 0 / 0 / 0 / 0 |
| d3-27b | golden_d3-ctx8k_27b_noul_p2 | 495 / 0 / 0 / 0 / 0 | 249 / 0 / 0 / 0 / 0 |
| Jev | golden_jev-1.14.0_noul_p2 | 495 / 0 / 0 / 0 / 0 | 249 / 0 / 0 / 0 / 0 |
| 4b json | golden_qwen3.5_4b_json_p2 | 495 / 0 / 0 / 0 / 0 | 249 / 0 / 0 / 0 / 0 |
| 9b json | golden_qwen3.5_9b_json_p2 | 495 / 0 / 0 / 0 / 0 | 249 / 0 / 0 / 0 / 0 |
| 27b json | golden_qwen3.8_27b_json_p2 | 495 / 0 / 2 / 0 / 0 | 249 / 0 / 1 / 0 / 0 |
| 4b jsonR | golden_qwen3.5_4b_json_reason_p2 | 495 / 0 / 0 / 0 / 0 | 249 / 0 / 0 / 0 / 0 |
| 9b jsonR | golden_qwen3.5_9b_json_reason_p2 | 495 / 0 / 1 / 0 / 0 | 249 / 0 / 0 / 0 / 0 |
| 27b jsonR | golden_qwen3.8_27b_json_reason_p2 | 495 / 0 / 1 / 0 / 0 | 249 / 0 / 0 / 0 / 0 |
| 4b lp fresh | golden_qwen3.5_4b_logprob_p2dbf | 495 / 0 / 0 / 0 / 0 | 249 / 0 / 0 / 0 / 0 |
| 9b lp fresh | golden_qwen3.5_9b_logprob_p2dbf | 495 / 0 / 0 / 0 / 0 | 249 / 0 / 0 / 0 / 0 |

- roster pair sets identical across the 7 score models: True; request ids in roster set: ['25-3152']; roster ids == main 25-3152 ids: True
- main set: 495 pairs, 284 responsive; pair sets identical across the 7 score models: True

#### V1. Per-model metrics from scratch (main 495 / roster 249)

| model | main AUROC | main thr98 | main elim@98 | main median wall ms | roster AUROC | roster thr98 | roster elim@98 | roster median wall ms |
|---|---|---|---|---|---|---|---|---|
| 4b lp | 0.923 | 0.2650 | 109/211 = 51.7% | 504 | 0.950 | 0.5606 | 82/109 = 75.2% | 446 |
| 9b lp | 0.942 | 0.3309 | 149/211 = 70.6% | 856 | 0.963 | 0.3901 | 74/109 = 67.9% | 734 |
| 27b lp | 0.975 | 0.0687 | 160/211 = 75.8% | 2,649 | 0.989 | 0.0783 | 99/109 = 90.8% | 2,231 |
| d3-4b | 0.884 | 0.3507 | 113/211 = 53.6% | 877 | 0.961 | 0.7588 | 94/109 = 86.2% | 1,739 |
| d3-9b | 0.947 | 0.3379 | 144/211 = 68.2% | 1,426 | 0.979 | 0.8529 | 98/109 = 89.9% | 2,639 |
| d3-27b | 0.979 | 0.5857 | 171/211 = 81.0% | 4,667 | 0.998 | 0.9133 | 107/109 = 98.2% | 8,550 |
| Jev | 0.916 | 0.3400 | 133/211 = 63.0% | 117 | 0.968 | 0.4600 | 91/109 = 83.5% | 125 |

- largest disagreement between my two AUROC implementations, the repo auroc() and the repo elim@98: 0.00e+00; thr98 identical to repo at_recall(): True

#### V2. Same subject, wrong date (20 hard negatives; main set)

| model | n | thr98 | wrong-date pass @thr98 | pass @0.5 | recall @0.5 | other-4 pass @thr98 | Fisher p (wd vs other 4) |
|---|---|---|---|---|---|---|---|
| 4b lp | 20 | 0.2650 | 20/20 | 18/20 | 270/284 | 57/71 | 0.034 |
| 9b lp | 20 | 0.3309 | 18/20 | 17/20 | 267/284 | 39/71 | 0.004 |
| 27b lp | 20 | 0.0687 | 10/20 | 3/20 | 264/284 | 41/71 | 0.61 |
| d3-4b | 20 | 0.3507 | 20/20 | 17/20 | 267/284 | 60/71 | 0.11 |
| d3-9b | 20 | 0.3379 | 17/20 | 10/20 | 271/284 | 49/71 | 0.26 |
| d3-27b | 20 | 0.5857 | 3/20 | 3/20 | 283/284 | 37/71 | 0.004 |
| Jev | 20 | 0.3400 | 19/20 | 18/20 | 266/284 | 49/71 | 0.019 |

Exact McNemar at each model's own thr98, Holm over all 21 pairs and over the 3 key pairs only:

| x | y | x only | y only | exact p | Holm (21) | Holm (3 key pairs) |
|---|---|---|---|---|---|---|
| 27b lp | d3-27b | 7 | 0 | 0.016 | 0.19 | 0.016 |
| 27b lp | Jev | 0 | 9 | 0.004 | 0.055 | 0.008 |
| d3-27b | Jev | 0 | 16 | 3.1e-05 | 5.8e-04 | 9.2e-05 |

d3-27b vs 27b lp on wrong-date emails at matched recall (both models' cutoffs set to the same recall on all 495 pairs):

| recall target | cutoff 27b lp / d3-27b | wrong-date pass 27b lp / d3-27b | 27b-only / d3-only | exact p | negatives eliminated 27b lp / d3-27b |
|---|---|---|---|---|---|
| 93.0% | 0.518 / 0.775 | 3 / 2 | 2 / 1 | 1 | 193/211 / 187/211 |
| 95.0% | 0.334 / 0.722 | 4 / 2 | 3 / 1 | 0.62 | 184/211 / 183/211 |
| 98.0% | 0.069 / 0.586 | 10 / 3 | 7 / 0 | 0.016 | 160/211 / 171/211 |
| 99.0% | 0.057 / 0.540 | 10 / 3 | 7 / 0 | 0.016 | 158/211 / 166/211 |
| 100.0% | 0.008 / 0.487 | 16 / 3 | 13 / 0 | 2.4e-04 | 133/211 / 166/211 |

Cutoff each model needs to pass at most 3 of the 20 wrong-date emails, and its recall there:

| model | cutoff | wrong-date pass | recall |
|---|---|---|---|
| 4b lp | 0.824 | 3 | 151/284 = 53.2% |
| 9b lp | 0.805 | 3 | 195/284 = 68.7% |
| 27b lp | 0.444 | 3 | 266/284 = 93.7% |
| d3-4b | 0.738 | 3 | 192/284 = 67.6% |
| d3-9b | 0.689 | 3 | 233/284 = 82.0% |
| d3-27b | 0.444 | 3 | 284/284 = 100.0% |
| Jev | 0.840 | 3 | 127/284 = 44.7% |

#### V3. Paired bootstrap of all 21 differences (2000 resamples, own resampler, seed 20261106)

**main, AUROC:** CI excludes 0 in 17/21; survive Holm (percentile p) 12/21; survive Holm (normal p) 13/21.

- survivors (percentile): 27b lp − 4b lp, d3-27b − 4b lp, 27b lp − 9b lp, 9b lp − d3-4b, d3-27b − 9b lp, 27b lp − d3-4b, 27b lp − d3-9b, 27b lp − Jev, d3-9b − d3-4b, d3-27b − d3-4b, d3-27b − d3-9b, d3-27b − Jev
- survivors (normal): 27b lp − 4b lp, 4b lp − d3-4b, d3-27b − 4b lp, 27b lp − 9b lp, 9b lp − d3-4b, d3-27b − 9b lp, 27b lp − d3-4b, 27b lp − d3-9b, 27b lp − Jev, d3-9b − d3-4b, d3-27b − d3-4b, d3-27b − d3-9b, d3-27b − Jev

| A − B | ΔAUROC | 95% CI | boot p | Holm | normal p | normal Holm |
|---|---|---|---|---|---|---|
| 9b lp − 4b lp | +0.020 | [-0.001, +0.042] | 0.064 | 0.26 | 0.072 | 0.29 |
| 27b lp − 4b lp | +0.053 | [+0.032, +0.077] | 1.0e-03 | 0.021 | 3.4e-06 | 5.1e-05 |
| 4b lp − d3-4b | +0.039 | [+0.012, +0.067] | 0.006 | 0.054 | 0.005 | 0.045 |
| d3-9b − 4b lp | +0.024 | [+0.004, +0.046] | 0.021 | 0.15 | 0.023 | 0.16 |
| d3-27b − 4b lp | +0.057 | [+0.035, +0.084] | 1.0e-03 | 0.021 | 3.1e-06 | 5.0e-05 |
| d3-27b − 9b lp | +0.037 | [+0.018, +0.058] | 1.0e-03 | 0.021 | 3.5e-04 | 0.005 |
| d3-27b − 27b lp | +0.004 | [-0.004, +0.013] | 0.34 | 1 | 0.35 | 1 |
| 27b lp − Jev | +0.059 | [+0.040, +0.080] | 1.0e-03 | 0.021 | 7.6e-09 | 1.4e-07 |
| d3-27b − Jev | +0.063 | [+0.045, +0.083] | 1.0e-03 | 0.021 | 2.9e-10 | 5.6e-09 |

**main, elim@98:** CI excludes 0 in 11/21; survive Holm (percentile p) 8/21; survive Holm (normal p) 8/21.

- survivors (percentile): 27b lp − 4b lp, d3-27b − 4b lp, 9b lp − d3-4b, 27b lp − d3-4b, 27b lp − Jev, d3-9b − d3-4b, d3-27b − d3-4b, d3-27b − Jev
- survivors (normal): 27b lp − 4b lp, d3-27b − 4b lp, 9b lp − d3-4b, 27b lp − d3-4b, 27b lp − Jev, d3-9b − d3-4b, d3-27b − d3-4b, d3-27b − Jev

| A − B | Δelim@98 | 95% CI | boot p | Holm | normal p | normal Holm |
|---|---|---|---|---|---|---|
| 9b lp − 4b lp | +19.0 | [+0.5, +31.3] | 0.044 | 0.48 | 0.023 | 0.26 |
| 27b lp − 4b lp | +24.2 | [+7.1, +39.3] | 1.0e-03 | 0.021 | 0.003 | 0.048 |
| d3-9b − 4b lp | +16.6 | [-2.4, +30.8] | 0.10 | 0.74 | 0.057 | 0.57 |
| d3-27b − 4b lp | +29.4 | [+8.5, +41.7] | 1.0e-03 | 0.021 | 7.4e-04 | 0.013 |
| d3-27b − 9b lp | +10.4 | [+0.5, +18.5] | 0.039 | 0.47 | 0.019 | 0.22 |
| d3-27b − 27b lp | +5.2 | [-5.7, +9.5] | 0.48 | 1 | 0.17 | 1 |
| 27b lp − Jev | +12.8 | [+8.1, +25.1] | 1.0e-03 | 0.021 | 0.003 | 0.045 |
| d3-27b − Jev | +18.0 | [+11.8, +25.1] | 1.0e-03 | 0.021 | 1.1e-07 | 2.2e-06 |

**roster, AUROC:** CI excludes 0 in 12/21; survive Holm (percentile p) 10/21; survive Holm (normal p) 4/21.

- survivors (percentile): 27b lp − 4b lp, d3-27b − 4b lp, 27b lp − 9b lp, d3-27b − 9b lp, 27b lp − d3-4b, d3-27b − 27b lp, d3-9b − d3-4b, d3-27b − d3-4b, d3-27b − d3-9b, d3-27b − Jev
- survivors (normal): 27b lp − 4b lp, d3-27b − 4b lp, d3-27b − 9b lp, d3-27b − d3-4b

| A − B | ΔAUROC | 95% CI | boot p | Holm | normal p | normal Holm |
|---|---|---|---|---|---|---|
| 9b lp − 4b lp | +0.013 | [-0.007, +0.034] | 0.21 | 1 | 0.23 | 1 |
| 27b lp − 4b lp | +0.039 | [+0.018, +0.062] | 1.0e-03 | 0.021 | 4.4e-04 | 0.009 |
| d3-9b − 4b lp | +0.029 | [+0.009, +0.051] | 0.008 | 0.088 | 0.008 | 0.12 |
| d3-27b − 4b lp | +0.048 | [+0.023, +0.076] | 1.0e-03 | 0.021 | 2.6e-04 | 0.005 |
| d3-27b − 9b lp | +0.035 | [+0.018, +0.057] | 1.0e-03 | 0.021 | 4.8e-04 | 0.009 |
| d3-27b − 27b lp | +0.009 | [+0.003, +0.017] | 1.0e-03 | 0.021 | 0.018 | 0.21 |
| 27b lp − Jev | +0.021 | [+0.003, +0.045] | 0.018 | 0.18 | 0.051 | 0.51 |
| d3-27b − Jev | +0.030 | [+0.011, +0.053] | 1.0e-03 | 0.021 | 0.007 | 0.11 |

**roster, elim@98:** CI excludes 0 in 14/21; survive Holm (percentile p) 10/21; survive Holm (normal p) 8/21.

- survivors (percentile): 27b lp − 4b lp, d3-9b − 4b lp, d3-27b − 4b lp, 27b lp − 9b lp, d3-9b − 9b lp, d3-27b − 9b lp, d3-27b − 27b lp, d3-27b − d3-4b, d3-27b − d3-9b, d3-27b − Jev
- survivors (normal): d3-27b − 4b lp, 27b lp − 9b lp, d3-4b − 9b lp, d3-9b − 9b lp, d3-27b − 9b lp, d3-27b − d3-4b, d3-27b − d3-9b, d3-27b − Jev

| A − B | Δelim@98 | 95% CI | boot p | Holm | normal p | normal Holm |
|---|---|---|---|---|---|---|
| 27b lp − 4b lp | +15.6 | [+7.3, +34.9] | 1.0e-03 | 0.021 | 0.027 | 0.29 |
| d3-9b − 4b lp | +14.7 | [+5.5, +34.9] | 1.0e-03 | 0.021 | 0.042 | 0.42 |
| d3-27b − 4b lp | +22.9 | [+12.8, +41.3] | 1.0e-03 | 0.021 | 0.002 | 0.025 |
| d3-27b − 9b lp | +30.3 | [+17.4, +42.2] | 1.0e-03 | 0.021 | 1.4e-06 | 2.9e-05 |
| d3-27b − 27b lp | +7.3 | [+1.8, +11.9] | 0.003 | 0.036 | 0.005 | 0.060 |
| 27b lp − Jev | +7.3 | [+0.9, +15.6] | 0.032 | 0.26 | 0.042 | 0.42 |
| d3-27b − Jev | +14.7 | [+7.3, +22.0] | 1.0e-03 | 0.021 | 1.0e-04 | 0.002 |

#### V4. DeLong from scratch, key AUROC differences

| set | A − B | ΔAUROC | DeLong SE | DeLong p |
|---|---|---|---|---|
| main | d3-27b − 27b lp | +0.0041 | 0.0042 | 0.33 |
| main | d3-27b − Jev | +0.0631 | 0.0103 | 1.1e-09 |
| main | 27b lp − Jev | +0.0590 | 0.0105 | 1.8e-08 |
| main | 9b lp − 4b lp | +0.0196 | 0.0106 | 0.064 |
| main | d3-27b − 4b lp | +0.0567 | 0.0119 | 1.9e-06 |
| roster | d3-27b − 27b lp | +0.0087 | 0.0037 | 0.017 |
| roster | d3-27b − Jev | +0.0302 | 0.0110 | 0.006 |
| roster | 27b lp − Jev | +0.0215 | 0.0109 | 0.050 |
| roster | 9b lp − 4b lp | +0.0125 | 0.0103 | 0.22 |
| roster | d3-27b − 4b lp | +0.0476 | 0.0129 | 2.1e-04 |
| positives vs wrong-date | d3-27b − Jev | +0.3033 | 0.0463 | 5.4e-11 |
| positives vs wrong-date | d3-27b − 27b lp | +0.0120 | 0.0083 | 0.15 |
| positives vs wrong-date | 27b lp − Jev | +0.2914 | 0.0466 | 4.0e-10 |

#### V5. Calibration from scratch (main 495)

| model | Brier | ECE (10 bins) | intercept | slope | recall @0.5 | eliminated @0.5 | mean score, non-responsive |
|---|---|---|---|---|---|---|---|
| 4b lp | 0.112 | 0.083 | -0.58 | 1.68 | 270/284 | 155/211 | 0.342 |
| 9b lp | 0.090 | 0.048 | -0.23 | 1.42 | 267/284 | 169/211 | 0.249 |
| 27b lp | 0.060 | 0.030 | +0.26 | 0.70 | 264/284 | 192/211 | 0.109 |
| d3-4b | 0.133 | 0.044 | -0.37 | 1.35 | 267/284 | 135/211 | 0.360 |
| d3-9b | 0.094 | 0.076 | -0.43 | 1.77 | 271/284 | 166/211 | 0.279 |
| d3-27b | 0.070 | 0.066 | -1.58 | 1.36 | 283/284 | 166/211 | 0.226 |
| Jev | 0.116 | 0.068 | -0.38 | 1.58 | 266/284 | 153/211 | 0.334 |

- label shift: 0.5 at 57.4% → 0.076 at 10%

#### V6. Speed/accuracy frontier from scratch

- main, local, med wall × elim: 4b lp → 9b lp → 27b lp → d3-27b
- main, local, med wall × auc: 4b lp → 9b lp → d3-9b → 27b lp → d3-27b
- main, local, mean wall × elim: 4b lp → 9b lp → 27b lp → d3-27b
- Jev median 116.7 ms; 4b lp / Jev = 4.32; 27b lp / Jev = 22.70; d3-27b / Jev = 39.98
- JSON median decode ms vs same-size lp median wall: 4b json 1,760; 9b json 2,912; 27b json 3,857; 4b jsonR 1,898; 9b jsonR 3,609; 27b jsonR 4,040
- 25-3152, local, median wall × elim: 4b lp +roster → d3-4b +roster → 27b lp +roster → d3-27b +roster
- 25-3152, local, median wall × auc: 4b lp +roster → 9b lp +roster → 27b lp +roster → 27b json +roster → d3-27b +roster
- 27b json +roster AUROC 0.98911 (n 248) vs 27b lp +roster 0.98906 (n 249)
- main: JSON configurations on the local frontier in 2000 redraws: median wall × elim@98 {'27b json': 4}; × AUROC none
- 25-3152: JSON configurations on the local frontier in 2000 redraws: median wall × elim@98 {'27b json +roster': 604, '27b jsonR +roster': 1}; × AUROC {'27b json +roster': 948, '27b jsonR +roster': 13}

#### V7. Latency: d3 vs stock without prefix reuse

| size | d3 wall ÷ fresh prefill (per-pair median) | d3 wall ÷ cached wall (per-pair median) | d3 wall ms/1k tok | stock fresh prefill ms/1k tok | stock JSON (warm, batch 8192, no cache) prefill ms/1k tok | stock cached prefill ms/1k tok |
|---|---|---|---|---|---|---|
| 4b | 1.07 | 1.76 | 481 | 463 | 471 | 260 |
| 4b +roster | 1.23 | 3.93 | 544 | 455 | 551 | 129 |
| 9b | 1.06 | 1.67 | 785 | 775 | 798 | 435 |
| 9b +roster | 1.11 | 3.67 | 821 | 763 | 849 | 217 |

Prefill cost per 1k prompt tokens by prompt length (each run bucketed on its own prompt_tokens), main + roster rows pooled, medians. Stock JSON = same Q4_K_M weights and ggml runner as stock lp, batch 8192 like d3, warm, no prefix cache:

| size | prompt tokens | d3 wall ms/1k tok | stock fresh prefill ms/1k tok (default batch) | stock JSON prefill ms/1k tok (batch 8192) |
|---|---|---|---|---|
| 4b | 0–1,500 | 461 (n 148) | 473 (n 173) | 469 (n 167) |
| 4b | 1,500–2,500 | 475 (n 220) | 463 (n 204) | 466 (n 206) |
| 4b | 2,500–3,500 | 541 (n 265) | 454 (n 271) | 547 (n 273) |
| 4b | ≥3,500 | 578 (n 111) | 455 (n 96) | 575 (n 98) |
| 9b | 0–1,500 | 756 (n 148) | 789 (n 173) | 794 (n 167) |
| 9b | 1,500–2,500 | 777 (n 220) | 774 (n 204) | 785 (n 206) |
| 9b | 2,500–3,500 | 817 (n 265) | 762 (n 271) | 843 (n 273) |
| 9b | ≥3,500 | 856 (n 111) | 762 (n 96) | 878 (n 98) |

#### V8. Stock cached vs fresh (same model, same prompt)

| model | pairs | max |Δscore| | mean |Δscore| | elim@98 cached / fresh |
|---|---|---|---|---|
| 4b lp | 495 | 0.1746 | 0.0178 | 51.7% / 53.1% |
| 4b lp +roster | 249 | 0.1614 | 0.0199 | 75.2% / 70.6% |
| 9b lp | 495 | 0.1532 | 0.0229 | 70.6% / 72.0% |
| 9b lp +roster | 249 | 0.1272 | 0.0185 | 67.9% / 67.9% |

#### V9. Wrong-date gap with thr98 re-estimated in each resample (2000 resamples, seed 20261108)

| gap | 95% CI (points) | bootstrap p |
|---|---|---|
| Jev − d3-27b | [+59, +96] | 1.0e-03 |
| 27b lp − d3-27b | [+4, +56] | 0.045 |
| Jev − 27b lp | [+24, +80] | 0.002 |

#### V10. Stock vs d3 on request subsets (point estimates from scratch; 2000 paired resamples, seed 20261109)

| d3 − stock | pairs | n | ΔAUROC [95% CI] | Δelim@98 points [95% CI] |
|---|---|---|---|---|
| d3-27b − 27b lp | 25-3152 | 249 | +0.026 [+0.011, +0.044] | +11.0 [+4.6, +24.8] |
| d3-4b − 4b lp | 24-409 | 246 | -0.084 [-0.128, -0.044] | -8.8 [-22.5, +6.9] |
| d3-9b − 9b lp | 25-3152 +roster | 249 | +0.016 [-0.006, +0.038] | +22.0 [+9.2, +34.9] |
| d3-27b − 27b lp | 25-3152 +roster | 249 | +0.009 [+0.003, +0.018] | +7.3 [+1.8, +12.8] |

