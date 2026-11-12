# B. Workload per 10,000 keyword-search hits

> **Snapshot of 2026-11-06, on the 2026-10-31 labels (495 pairs).** The labels changed afterwards: five hard
> negatives were relabeled responsive on 2026-11-08, and one email (24-409 synthetic 07:09) was put back in the set
> on 2026-11-11 (`docs/findings-golden.md` §9). The tables below are copies of script output on the old labels.
> Rerun the commands in the Reproduce section for current numbers; the scripts now read the pair counts from the
> golden set (`scripts/analysis/golden_counts.py`). `docs/findings-golden.md` carries the current figures, and
> `conclusions.md` section 0 lists what the relabeling changed.

**Branch B of the golden-set analysis** · 2026-11-06 · scripts: `scripts/analysis/b_workload_time.py`,
`scripts/analysis/b_workload_review.py` (shared code in `b_workload_common.py`) · every table below is
pasted verbatim from those scripts' output; see [Reproduce](#reproduce). Checked by an independent
skeptic pass (`scripts/analysis/b_workload_verify.py`); see [Verification](#verification).

## The question

An agency runs a keyword search for a CPRA request and gets 10,000 hits. What would each screening
configuration mean in practice?

- **Machine time:** how long scoring the 10,000 takes.
- **Review workload:** how many emails a person still has to read.
- **Misses:** how many responsive emails the screen drops.

**Short answer (details in [Findings](#findings)):**

- Single-stream scoring of 10,000 emails takes 0.33 h (Jev, API), and 1.68 h (4b lp) to 14.70 h (d3-27b)
  locally.
- Under the scenario judged most plausible (20% of hits responsive, negatives halfway between the easy
  and hard golden negatives), the best local screens (9b lp, 27b lp, d3-27b) still leave 3,723–4,637 of
  the 10,000 for a person to read.
- At those cutoffs about 35 of the 2,000 responsive emails are missed. That figure is optimistic: the
  cutoffs were tuned on the same pairs they are scored on.
- Reviewer time (31.0–51.5 h at 30 s per email for the seven score models; 41.8–83.3 h for the JSON
  modes [corrected in verification]) is larger than machine time for every configuration.
  So accuracy, not speed, sets the total effort.

## Data and method

**Runs.** These are the main-table runs of the golden report (prompt 2, Ollama 0.40.13, Strix Halo),
each with a `_roster` twin covering 25-3152 only:

| name | run directory (`runs/…`) | score | setting | reuses the request prefix? |
|---|---|---|---|---|
| 4b lp, 9b lp | `golden_qwen3.5_{4b,9b}_logprob_p2db` | first-token P(yes)/(P(yes)+P(no)) | Q4_K_M, default batch | yes (B1.3) |
| 27b lp | `golden_qwen3.8_27b_logprob_p2` | same | Q4_K_M, default batch | yes |
| d3-4b, d3-9b, d3-27b | `golden_d3-ctx8k_{4b,9b,27b}_noul_p2` | the model's P(yes), via `/v1/systemone` | Q8_0, num_batch 8192 | no: noncausal attention |
| Jev | `golden_jev-1.14.0_noul_p2` | P(yes), rounded to 2 decimals | TypeSafe API; wall time includes the network | — |
| 4b/9b json, jsonR | `golden_qwen3.5_{4b,9b}_json_p2`, `…_json_reason_p2` | confidence if verdict yes, else 1 − confidence | Q4_K_M, num_batch 8192 | no (B1.3) |
| 27b json, jsonR | `golden_qwen3.8_27b_json_p2`, `…_json_reason_p2` | same | Q4_K_M, default batch | yes |

("json" asks for the verdict first; "jsonR" asks for the reasoning first.)

**Pairs.**

- **Main set:** 495 (request, email) pairs, both requests.
- **Roster set:** 249 pairs, 25-3152 only, with the committee roster appended to the request.
- **Labels:** label, kind and recipe come from `data/golden/pairs.jsonl`, joined on `pair_id`
  (`golden_report.load_runs`).
- **Dropped rows:** five JSON rows have no score and are left out: 27b json 2 of 495, 27b json +roster
  1 of 249, 9b jsonR 1 of 495, 27b jsonR 1 of 495. No score-model row is dropped.

**Definitions.**

- **Flagged:** a pair is flagged for human review when score ≥ threshold. Two cutoffs are used:
  - **thr98:** the highest threshold that keeps recall ≥ 98% on the pooled 495 pairs of that run. It is
    *in-sample*: chosen on the same pairs it is then evaluated on. In B4 it is chosen on the 249
    25-3152 pairs of each run.
  - **Default:** score ≥ 0.5; for the JSON modes, the verdict.
- **Pass rate of a group:** the share of the group flagged. For positives it is recall. For negatives
  it is the slip-through rate, which is 1 − the eliminated share.
  - **R_all:** the pass rate over all 284 golden positives (real, close-call, privileged,
    exempt-other, and the 4 flipped hard negatives).
  - **R_real:** the same over the 150 real positives.
  - **F_real:** over the 120 real negatives.
  - **F_hard:** over the 91 hard negatives.
  - **F_mix:** (F_real + F_hard) / 2.
- **Per 10,000 hits,** for a population whose responsive share is p:
  - flagged = 10,000 × [p × R + (1 − p) × F];
  - missed = 10,000 × p × (1 − R);
  - review avoided = 1 − flagged / 10,000;
  - responsive share of the review queue = p·R / (p·R + (1 − p)·F).
- **Machine hours per 10,000** = mean wall_ms × 10,000 / 3,600,000, single-stream (one call at a time,
  as the runs were made).
- **Reviewer hours** = flagged × s / 3,600, with an *assumed* s = 30 or 60 seconds per email.
- **Break-even seconds per email** = machine seconds ÷ flagged. Above it, review takes longer than
  scoring.

**Scenarios (B2).** In the golden mix 284 of the 495 pairs are positive, and 91 of the 211 negatives are synthetic near-misses. It was
built to be hard; it is not a sample of anyone's keyword hits. A scenario states the population
explicitly, along three dimensions:

| dimension | values | what it stands for |
|---|---|---|
| responsive share p | 5%, 20%, 50% | a broad search, a middling one, a tight one |
| negatives behave like | real (F_real), 50/50 mix (F_mix), hard (F_hard) | easy cross-request emails … deliberate near-misses |
| positives behave like | all golden positives (R_all); sensitivity: real positives only (R_real) | — |

The scenario judged most plausible is **p = 20%, negatives = 50/50 mix, positives = all**. The
justification is in [B5](#b5-takeaway). It is the "plausible scenario" in B3 and B5.

**Intervals.**

- **Bootstrap:** 1,000 resamples of the pairs, drawn with replacement within each kind (so within each
  label).
  - The resampled pair lists are the same for every configuration, so differences between
    configurations are paired.
  - At thr98 the threshold is chosen again in every resample, as in the golden report's elim@98
    intervals. The intervals therefore include the cutoff's own instability.
  - Percentile 95% intervals. Seeds: 20261106 (main set) and 20261107 (25-3152).
- **Wilson intervals:** a bootstrap interval collapses to [0, 0] when a group has no flagged pairs
  (e.g. 0/120). B2.2 therefore also gives Wilson 95% intervals (threshold held fixed), which don't
  collapse.
- **Machine-hour intervals** resample pairs within each label and cover only which emails were
  sampled, not run-to-run variation (there is one run per configuration).

## B1. Machine time

### B1.1–B1.2 Wall time per call and hours per 10,000

Main set (495 pairs):

| config | tier | n | mean wall ms | median | p90 | mean prompt tok | body truncated | hours / 10,000 (mean) [95% CI] |
|---|---|---|---|---|---|---|---|---|
| 4b lp | 4B | 495 | 606 | 504 | 1,172 | 1,966 | 55/495 | 1.68 [1.59–1.79] |
| 9b lp | 9B | 495 | 1,020 | 856 | 1,996 | 1,966 | 55/495 | 2.83 [2.67–2.99] |
| 27b lp | 27B | 495 | 3,217 | 2,649 | 6,416 | 1,966 | 55/495 | 8.93 [8.43–9.48] |
| d3-4b | 4B | 495 | 1,049 | 877 | 1,826 | 2,050 | 55/495 | 2.91 [2.79–3.04] |
| d3-9b | 9B | 495 | 1,636 | 1,426 | 2,740 | 2,050 | 55/495 | 4.54 [4.38–4.73] |
| d3-27b | 27B | 495 | 5,293 | 4,667 | 8,782 | 2,050 | 55/495 | 14.70 [14.15–15.23] |
| Jev | API | 495 | 120 | 117 | 136 | 2,214 | 55/495 | 0.33 [0.33–0.34] |
| 4b json | 4B | 495 | 2,848 | 2,749 | 3,656 | 1,991 | 55/495 | 7.91 [7.78–8.05] |
| 9b json | 9B | 495 | 4,611 | 4,435 | 5,921 | 1,991 | 55/495 | 12.81 [12.59–13.02] |
| 27b json | 27B | 493 | 7,192 | 6,805 | 10,333 | 1,993 | 55/493 | 19.98 [19.46–20.51] |
| 4b jsonR | 4B | 495 | 2,992 | 2,909 | 3,780 | 1,999 | 55/495 | 8.31 [8.17–8.45] |
| 9b jsonR | 9B | 494 | 5,327 | 5,267 | 6,737 | 1,999 | 55/494 | 14.80 [14.56–15.05] |
| 27b jsonR | 27B | 494 | 7,471 | 7,014 | 10,797 | 2,000 | 55/494 | 20.75 [20.21–21.30] |

Roster set (249 pairs of 25-3152, roster appended):

| config | tier | n | mean wall ms | median | p90 | mean prompt tok | body truncated | hours / 10,000 (mean) [95% CI] |
|---|---|---|---|---|---|---|---|---|
| 4b lp | 4B | 249 | 541 | 446 | 1,169 | 3,355 | 16/249 | 1.50 [1.38–1.64] |
| 9b lp | 9B | 249 | 916 | 734 | 1,888 | 3,355 | 16/249 | 2.55 [2.34–2.75] |
| 27b lp | 27B | 249 | 2,871 | 2,231 | 6,128 | 3,355 | 16/249 | 7.97 [7.30–8.71] |
| d3-4b | 4B | 249 | 1,924 | 1,739 | 2,708 | 3,447 | 16/249 | 5.34 [5.18–5.51] |
| d3-9b | 9B | 249 | 2,878 | 2,639 | 3,953 | 3,447 | 16/249 | 8.00 [7.75–8.25] |
| d3-27b | 27B | 249 | 9,281 | 8,550 | 12,825 | 3,447 | 16/249 | 25.78 [25.05–26.56] |
| Jev | API | 249 | 131 | 125 | 151 | 3,670 | 16/249 | 0.36 [0.36–0.38] |
| 4b json | 4B | 249 | 3,640 | 3,528 | 4,507 | 3,380 | 16/249 | 10.11 [9.90–10.32] |
| 9b json | 9B | 249 | 5,726 | 5,563 | 6,998 | 3,380 | 16/249 | 15.91 [15.60–16.23] |
| 27b json | 27B | 248 | 6,528 | 6,063 | 9,888 | 3,383 | 16/248 | 18.13 [17.43–18.83] |
| 4b jsonR | 4B | 249 | 3,899 | 3,820 | 4,772 | 3,388 | 16/249 | 10.83 [10.61–11.06] |
| 9b jsonR | 9B | 249 | 6,691 | 6,519 | 8,233 | 3,388 | 16/249 | 18.59 [18.24–18.99] |
| 27b jsonR | 27B | 249 | 7,119 | 6,633 | 10,327 | 3,388 | 16/249 | 19.77 [19.09–20.49] |

What the tables show:

- **Measured single-stream time per 10,000 emails:**
  - Jev: 0.33 h.
  - 4B class: 1.68 h (4b lp), 2.91 h (d3-4b).
  - 9B class: 2.83 h (9b lp), 4.54 h (d3-9b).
  - 27B class: 8.93 h (27b lp), 14.70 h (d3-27b).
  - JSON modes: 7.91–20.75 h.
- **Means sit above medians** because long emails take longer: 4b lp has a median of 504 ms and a p90
  of 1,172 ms; 27b lp 2,649 and 6,416 ms.

### B1.3 The prefix-cache effect

Every prompt has the same shape: system instructions, then the request text, then the email. Qwen's
attention is causal: each token's processed state depends only on the tokens before it. So when
consecutive calls start with the same system prompt and request, Ollama can keep that processed prefix
and compute only the new email.

`score.py` and `score_systemone.py` sort pairs by (request, email), so in the runs every call after the
first in a request follows a call with the same prefix. A real batch of 10,000 hits for one request
would look the same. The measured lp times therefore already reflect the reuse a deployment would get.

The direct test: append the 1,330-token roster to 25-3152's request and score the same 249 emails
again. If the prefix is reused, the roster costs almost nothing. If it is reprocessed on every call, it
costs about (tokens added) × (the run's own per-token rate from B1.6), shown as "expected Δ if
reprocessed".

| config | pairs | tokens added by roster | expected Δ ms if reprocessed | mean wall ms without | with | mean Δwall ms | median Δwall ms | median Δprefill ms | Δ hours / 10,000 |
|---|---|---|---|---|---|---|---|---|---|
| 4b lp | 249 | 1330–1330 | +618 | 554 | 541 | -13 | +10 | +7 | -0.04 |
| 9b lp | 249 | 1330–1330 | +1,028 | 953 | 916 | -36 | -13 | -2 | -0.10 |
| 27b lp | 249 | 1330–1330 | +3,399 | 2,979 | 2,871 | -108 | +10 | +12 | -0.30 |
| d3-4b | 249 | 1333–1333 | +837 | 1,110 | 1,924 | +814 | +806 | — | +2.26 |
| d3-9b | 249 | 1333–1333 | +1,184 | 1,727 | 2,878 | +1,151 | +1,138 | — | +3.20 |
| d3-27b | 249 | 1333–1333 | +3,753 | 5,563 | 9,281 | +3,718 | +3,634 | — | +10.33 |
| Jev | 249 | 1394–1394 | +8 | 122 | 131 | +9 | +9 | — | +0.03 |
| 4b json | 249 | 1330–1330 | +850 | 2,866 | 3,640 | +775 | +797 | +858 | +2.15 |
| 9b json | 249 | 1330–1330 | +1,341 | 4,615 | 5,726 | +1,111 | +1,161 | +1,230 | +3.09 |
| 27b json | 246 | 1330–1330 | +3,400 | 7,014 | 6,536 | -477 | -368 | +8 | -1.33 |
| 4b jsonR | 249 | 1330–1330 | +812 | 3,055 | 3,899 | +844 | +848 | +863 | +2.34 |
| 9b jsonR | 248 | 1330–1330 | +1,358 | 5,562 | 6,685 | +1,123 | +1,166 | +1,232 | +3.12 |
| 27b jsonR | 248 | 1330–1330 | +3,548 | 7,539 | 7,131 | -408 | -316 | +7 | -1.13 |

- **The stock-Qwen lp runs reuse the prefix.** The roster changed their median prefill by −2 to +12 ms
  per call. Reprocessing it would have cost +618 / +1,028 / +3,399 ms. The 27b JSON runs (default
  batch) behave the same (+8 / +7 ms).
- **d3 reprocesses the prefix on every call:** +814 / +1,151 / +3,718 ms per call measured, against
  +837 / +1,184 / +3,753 ms expected. The d3 models use noncausal attention, so a token's state also
  depends on the tokens after it, and a processed prefix can't be reused once the email changes.
  *[Verification note: the d3 runs also used num_batch 8192, and on this Ollama build num_batch 8192
  by itself stops prefix reuse for the stock 4b/9b lp models (Verification, V11). So this measurement
  shows that d3 reprocesses the prefix, but not why.]*
- **The 4b/9b JSON runs (num_batch 8192) also reprocess it** (+858 / +863 / +1,230 / +1,232 ms
  prefill).
- **Jev's wall time barely moves** (+9 ms for 1,394 added tokens).

### B1.4 What the batch-8192 setting costs the small JSON runs

| JSON run | lp run | pairs | lp median prefill ms | JSON median prefill ms | median Δprefill ms | mean Δprefill ms | Δprefill hours / 10,000 | JSON mean decode ms | decode hours / 10,000 |
|---|---|---|---|---|---|---|---|---|---|
| 4b json | 4b lp | 495 | 466 | 856 | +459 | +454 | +1.26 | 1,804 | 5.01 |
| 4b jsonR | 4b lp | 495 | 466 | 859 | +464 | +460 | +1.28 | 1,941 | 5.39 |
| 9b json | 9b lp | 495 | 774 | 1,430 | +704 | +681 | +1.89 | 2,948 | 8.19 |
| 9b jsonR | 9b lp | 494 | 777 | 1,432 | +711 | +688 | +1.91 | 3,657 | 10.16 |
| 27b json | 27b lp | 493 | 2,562 | 2,605 | +26 | +50 | +0.14 | 3,940 | 10.94 |
| 27b jsonR | 27b lp | 494 | 2,553 | 2,610 | +26 | +50 | +0.14 | 4,223 | 11.73 |

The 4b/9b JSON runs used num_batch 8192, the workaround for the ROCm fault on older Ollama builds. The
lp runs of the same models use the default batch, rechecked clean on 0.40.13. Two things follow:

- **The batch setting adds prefill time.** Their prefill is 454–688 ms per call longer than lp's on the
  same email, or +1.26 to +1.91 h per 10,000. A default-batch JSON run would probably not pay this, but
  that wasn't measured.
- **Even without it, JSON is slower than lp.** Decoding the JSON answer alone takes 5.01–10.16 h per
  10,000 for the 4b/9b runs and 10.94–11.73 h for the 27b. That is more than the whole lp run of the
  same model (1.68 / 2.83 / 8.93 h).

### B1.5 Jev cost

| set | calls | input tokens, total | mean per call | max | cost of this run | cost per 10,000 |
|---|---|---|---|---|---|---|
| main set (495) | 495 | 1,096,093 | 2,214 | 4,699 | $0.0460 | $0.93 |
| roster set (249) | 249 | 913,747 | 3,670 | 6,093 | $0.0384 | $1.54 |

- **Cost:** at $0.042 per million input tokens, 10,000 calls cost $0.93 at the
  golden set's mean prompt (2,214 billed tokens) and $1.54 with the roster (3,670). The 495-pair run
  cost $0.046. That is the input price only: Jev also reports 20 output tokens per call, and the repo
  doesn't record whether or at what rate those are billed [corrected in verification; the earlier text
  said "output not billed", which nothing in the repo supports]. [Resolved after verification: TypeSafe's
  models page (docs.typesafe.ai/models.md, read 2026-11-04) says "You pay per input token. Output tokens
  are free." See conclusions.md section 7.]
- **Speed:** Jev's wall time hardly depends on prompt length (+6 ms per 1,000 tokens, Pearson r 0.24,
  B1.6). Most of its 117–120 ms is probably network and fixed overhead, though that is an
  interpretation; the scorer only sees end-to-end time.

### B1.6 Scaling to longer or shorter emails

| config | prompt tokens range | a (ms) | b (ms per +1,000 tokens) | Pearson r | +hours / 10,000 per +1,000 mean tokens |
|---|---|---|---|---|---|
| 4b lp | 788–4,386 | -306 | 464 | 0.94 | 1.29 |
| 9b lp | 788–4,386 | -498 | 773 | 0.95 | 2.15 |
| 27b lp | 788–4,386 | -1,807 | 2,555 | 0.94 | 7.10 |
| d3-4b | 841–4,519 | -239 | 628 | 0.99 | 1.74 |
| d3-9b | 841–4,519 | -186 | 889 | 1.00 | 2.47 |
| d3-27b | 841–4,519 | -478 | 2,815 | 1.00 | 7.82 |
| Jev | 1,020–4,699 | +108 | 6 | 0.24 | 0.02 |
| 4b json | 813–4,411 | +1,576 | 639 | 0.86 | 1.78 |
| 9b json | 813–4,411 | +2,604 | 1,008 | 0.85 | 2.80 |
| 27b json | 813–4,411 | +2,097 | 2,557 | 0.93 | 7.10 |
| 4b jsonR | 821–4,419 | +1,771 | 611 | 0.83 | 1.70 |
| 9b jsonR | 821–4,419 | +3,285 | 1,021 | 0.77 | 2.84 |
| 27b jsonR | 821–4,419 | +2,136 | 2,668 | 0.89 | 7.41 |

- **Per-call time is bounded:** email bodies are capped at 8,000 characters (55 of 495 golden emails
  hit the cap).
- **Scaling rule:** if a real hit population's mean prompt is 1,000 tokens longer than the golden set's
  (1,966 for lp), add roughly the last column. That is 1.29 h per 10,000 for the 4b lp and 7.10 h for
  the 27b lp, up to 7.82 h for d3-27b.

### B1.7 Warm-up row

| config | set | first row wall ms | mean | mean without first row | Δ mean ms |
|---|---|---|---|---|---|
| 4b lp | main | 48 | 606 | 608 | +1.1 |
| 4b lp | roster | 58 | 541 | 543 | +1.9 |
| 9b lp | main | 60 | 1,020 | 1,022 | +1.9 |
| 9b lp | roster | 77 | 916 | 920 | +3.4 |
| 27b lp | main | 154 | 3,217 | 3,223 | +6.2 |
| 27b lp | roster | 159 | 2,871 | 2,882 | +10.9 |
| d3-4b | main | 863 | 1,049 | 1,049 | +0.4 |
| d3-4b | roster | 2,653 | 1,924 | 1,921 | -2.9 |
| d3-9b | main | 1,360 | 1,636 | 1,636 | +0.6 |
| d3-9b | roster | 3,937 | 2,878 | 2,874 | -4.3 |
| d3-27b | main | 4,386 | 5,293 | 5,295 | +1.8 |
| d3-27b | roster | 12,612 | 9,281 | 9,268 | -13.4 |
| Jev | main | 182 | 120 | 120 | -0.1 |
| Jev | roster | 134 | 131 | 131 | -0.0 |
| 4b json | main | 1,491 | 2,848 | 2,851 | +2.7 |
| 4b json | roster | 1,903 | 3,640 | 3,647 | +7.0 |
| 9b json | main | 2,971 | 4,611 | 4,615 | +3.3 |
| 9b json | roster | 3,440 | 5,726 | 5,735 | +9.2 |
| 27b json | main | 3,900 | 7,192 | 7,198 | +6.7 |
| 27b json | roster | 3,379 | 6,528 | 6,541 | +12.8 |
| 4b jsonR | main | 1,507 | 2,992 | 2,995 | +3.0 |
| 4b jsonR | roster | 1,955 | 3,899 | 3,907 | +7.8 |
| 9b jsonR | main | 2,319 | 5,327 | 5,333 | +6.1 |
| 9b jsonR | roster | 3,833 | 6,691 | 6,703 | +11.5 |
| 27b jsonR | main | 3,522 | 7,471 | 7,479 | +8.0 |
| 27b jsonR | roster | 3,739 | 7,119 | 7,132 | +13.6 |

Each local run made an untimed warm-up call on its first pair; the lp runs made two (a warm-up and a
canary reference), and also re-scored that pair after every 100 rows, which overlaps and slows the next
timed row (Verification, V12: 0.7–1.6% of the lp means) [corrected in verification]. In the cached runs
the warm-up makes the first timed row unrealistically fast (48–159 ms). Removing it changes any run's mean
by at most 13.6 ms, so it is ignored.

### B1.8 Same-size stock Qwen vs d3

| pair | main: lp h | main: d3 h | main: d3 / lp | roster: lp h | roster: d3 h | roster: d3 / lp | per-token slope b, d3 / lp |
|---|---|---|---|---|---|---|---|
| 4b lp vs d3-4b | 1.68 | 2.91 | 1.73× | 1.50 | 5.34 | 3.56× | 1.35× |
| 9b lp vs d3-9b | 2.83 | 4.54 | 1.60× | 2.55 | 8.00 | 3.14× | 1.15× |
| 27b lp vs d3-27b | 8.93 | 14.70 | 1.65× | 7.97 | 25.78 | 3.23× | 1.10× |

- **d3 takes 1.60–1.73× as long as the stock Qwen model of the same size**, and 3.14–3.56× with the
  roster.
- **At least four differences separate the pairs** [corrected in verification; the earlier text named
  two]: d3 can't reuse the prefix (B1.3); its weights are Q8_0, not Q4_K_M; its runs used num_batch
  8192, not the default; and it runs on Ollama's llamacpp runner through `/v1/systemone`, not the ggml
  runner through `/api/chat` (Verification, V2). These runs don't separate them. Each extra token costs
  d3 1.10–1.35× what it costs lp, which is one rough indication.

### Not measured

- **Local parallelism:** several requests at once through Ollama's parallel slots, and whether the
  prefix cache survives it.
- **Jev API concurrency or rate limits.**

Every hour figure here is one call at a time. Jev's time is from this machine's network location.

## B2. Review workload per 10,000 hits

### B2.1 Pass rates by group (the inputs to every scenario)

*At thr98, the in-sample 98%-recall threshold (bootstrap CI with the threshold re-chosen in each resample):*

| config | threshold | positives: all | positives: real | negatives: real | negatives: hard | eliminated: all negatives |
|---|---|---|---|---|---|---|
| 4b lp | 0.2650 | 279/284 = 98.2% [98.2%–98.9%] | 145/150 = 96.7% [96.7%–98.7%] | 25/120 = 20.8% [3.3%–37.5%] | 77/91 = 84.6% [59.3%–92.3%] | 109/211 = 51.7% [40.8%–71.6%] |
| 9b lp | 0.3309 | 279/284 = 98.2% [98.2%–98.9%] | 147/150 = 98.0% [96.7%–100.0%] | 5/120 = 4.2% [0.8%–7.5%] | 57/91 = 62.6% [48.4%–73.6%] | 149/211 = 70.6% [64.9%–77.7%] |
| 27b lp | 0.0687 | 279/284 = 98.2% [98.2%–98.9%] | 146/150 = 97.3% [96.7%–98.7%] | 0/120 = 0.0% [0.0%–0.0%] | 51/91 = 56.0% [28.6%–64.8%] | 160/211 = 75.8% [72.0%–87.7%] |
| d3-4b | 0.3507 | 279/284 = 98.2% [98.2%–99.3%] | 146/150 = 97.3% [96.7%–99.3%] | 18/120 = 15.0% [5.0%–29.2%] | 80/91 = 87.9% [80.2%–94.5%] | 113/211 = 53.6% [44.5%–61.1%] |
| d3-9b | 0.3379 | 279/284 = 98.2% [98.2%–98.9%] | 147/150 = 98.0% [96.7%–99.3%] | 1/120 = 0.8% [0.0%–2.5%] | 66/91 = 72.5% [47.3%–82.4%] | 144/211 = 68.2% [64.0%–79.1%] |
| d3-27b | 0.5857 | 279/284 = 98.2% [98.2%–99.3%] | 145/150 = 96.7% [96.7%–98.7%] | 0/120 = 0.0% [0.0%–0.0%] | 40/91 = 44.0% [31.9%–57.1%] | 171/211 = 81.0% [75.4%–86.3%] |
| Jev | 0.3400 | 279/284 = 98.2% [98.2%–99.3%] | 146/150 = 97.3% [96.7%–99.3%] | 10/120 = 8.3% [2.5%–14.2%] | 68/91 = 74.7% [65.9%–84.6%] | 133/211 = 63.0% [56.9%–68.7%] |
| 4b json | 0.0500 | 283/284 = 99.6% [98.9%–100.0%] | 149/150 = 99.3% [98.0%–100.0%] | 101/120 = 84.2% [77.5%–90.8%] | 90/91 = 98.9% [96.7%–100.0%] | 20/211 = 9.5% [5.7%–13.3%] |
| 9b json | 0.0000 | 284/284 = 100.0% [100.0%–100.0%] | 150/150 = 100.0% [100.0%–100.0%] | 120/120 = 100.0% [100.0%–100.0%] | 91/91 = 100.0% [100.0%–100.0%] | 0/211 = 0.0% [0.0%–0.0%] |
| 27b json | 0.0500 | 284/284 = 100.0% [100.0%–100.0%] | 150/150 = 100.0% [100.0%–100.0%] | 64/120 = 53.3% [43.3%–61.7%] | 87/89 = 97.8% [93.3%–100.0%] | 58/209 = 27.8% [22.7%–33.8%] |
| 4b jsonR | 0.0000 | 284/284 = 100.0% [100.0%–100.0%] | 150/150 = 100.0% [100.0%–100.0%] | 120/120 = 100.0% [100.0%–100.0%] | 91/91 = 100.0% [100.0%–100.0%] | 0/211 = 0.0% [0.0%–0.0%] |
| 9b jsonR | 0.0000 | 283/283 = 100.0% [98.2%–100.0%] | 150/150 = 100.0% [98.0%–100.0%] | 120/120 = 100.0% [7.5%–100.0%] | 91/91 = 100.0% [61.5%–100.0%] | 0/211 = 0.0% [0.0%–68.7%] |
| 27b jsonR | 0.0500 | 282/284 = 99.3% [98.2%–100.0%] | 148/150 = 98.7% [96.7%–100.0%] | 11/120 = 9.2% [4.2%–15.0%] | 60/90 = 66.7% [55.1%–77.0%] | 139/210 = 66.2% [60.7%–72.0%] |

*At the default decision (score ≥ 0.5; JSON: the verdict):*

| config | threshold | positives: all | positives: real | negatives: real | negatives: hard | eliminated: all negatives |
|---|---|---|---|---|---|---|
| 4b lp | 0.5 / verdict | 270/284 = 95.1% [92.6%–97.5%] | 139/150 = 92.7% [88.7%–96.7%] | 4/120 = 3.3% [0.8%–6.7%] | 52/91 = 57.1% [47.3%–68.1%] | 155/211 = 73.5% [69.2%–77.7%] |
| 9b lp | 0.5 / verdict | 267/284 = 94.0% [91.5%–96.8%] | 138/150 = 92.0% [87.3%–96.0%] | 1/120 = 0.8% [0.0%–2.5%] | 41/91 = 45.1% [34.1%–54.9%] | 169/211 = 80.1% [75.8%–84.8%] |
| 27b lp | 0.5 / verdict | 264/284 = 93.0% [90.1%–95.8%] | 135/150 = 90.0% [85.3%–94.7%] | 0/120 = 0.0% [0.0%–0.0%] | 19/91 = 20.9% [13.2%–29.7%] | 192/211 = 91.0% [87.2%–94.3%] |
| d3-4b | 0.5 / verdict | 267/284 = 94.0% [90.8%–96.5%] | 139/150 = 92.7% [88.0%–96.7%] | 3/120 = 2.5% [0.0%–5.8%] | 73/91 = 80.2% [71.4%–89.0%] | 135/211 = 64.0% [60.2%–68.2%] |
| d3-9b | 0.5 / verdict | 271/284 = 95.4% [92.6%–97.5%] | 143/150 = 95.3% [91.3%–98.7%] | 1/120 = 0.8% [0.0%–2.5%] | 44/91 = 48.4% [38.5%–59.3%] | 166/211 = 78.7% [73.9%–83.4%] |
| d3-27b | 0.5 / verdict | 283/284 = 99.6% [98.9%–100.0%] | 149/150 = 99.3% [98.0%–100.0%] | 0/120 = 0.0% [0.0%–0.0%] | 45/91 = 49.5% [39.6%–60.4%] | 166/211 = 78.7% [73.9%–82.9%] |
| Jev | 0.5 / verdict | 266/284 = 93.7% [90.8%–96.5%] | 136/150 = 90.7% [86.0%–95.3%] | 1/120 = 0.8% [0.0%–2.5%] | 57/91 = 62.6% [52.7%–73.6%] | 153/211 = 72.5% [67.8%–77.3%] |
| 4b json | 0.5 / verdict | 257/284 = 90.5% [87.3%–93.7%] | 131/150 = 87.3% [82.0%–92.7%] | 2/120 = 1.7% [0.0%–4.2%] | 48/91 = 52.7% [42.9%–62.6%] | 161/211 = 76.3% [72.0%–80.6%] |
| 9b json | 0.5 / verdict | 231/284 = 81.3% [76.8%–85.6%] | 118/150 = 78.7% [72.0%–84.7%] | 0/120 = 0.0% [0.0%–0.0%] | 28/91 = 30.8% [20.9%–40.7%] | 183/211 = 86.7% [82.5%–91.0%] |
| 27b json | 0.5 / verdict | 271/284 = 95.4% [93.0%–97.5%] | 140/150 = 93.3% [89.3%–97.3%] | 0/120 = 0.0% [0.0%–0.0%] | 28/89 = 31.5% [22.5%–42.0%] | 181/209 = 86.6% [82.2%–90.4%] |
| 4b jsonR | 0.5 / verdict | 248/284 = 87.3% [83.5%–90.8%] | 127/150 = 84.7% [79.3%–90.0%] | 3/120 = 2.5% [0.0%–5.8%] | 38/91 = 41.8% [31.9%–51.6%] | 170/211 = 80.6% [76.3%–85.3%] |
| 9b jsonR | 0.5 / verdict | 262/283 = 92.6% [89.4%–95.4%] | 136/150 = 90.7% [86.0%–94.7%] | 4/120 = 3.3% [0.8%–6.7%] | 45/91 = 49.5% [39.6%–59.3%] | 162/211 = 76.8% [72.5%–81.5%] |
| 27b jsonR | 0.5 / verdict | 269/284 = 94.7% [92.3%–97.2%] | 138/150 = 92.0% [87.3%–96.0%] | 0/120 = 0.0% [0.0%–0.0%] | 38/90 = 42.2% [32.2%–52.8%] | 172/210 = 81.9% [77.5%–86.2%] |

For positives the rate is recall; for negatives it is the share that slips through. The last column is the golden set's own eliminated share (1 − slip-through over all 211 negatives).

### B2.2 Wilson intervals (threshold fixed)

| config | thr98: positives: all | thr98: positives: real | thr98: negatives: real | thr98: negatives: hard | default: positives: all | default: positives: real | default: negatives: real | default: negatives: hard |
|---|---|---|---|---|---|---|---|---|
| 4b lp | 95.9%–99.2% | 92.4%–98.6% | 14.5%–28.9% | 75.8%–90.6% | 91.9%–97.0% | 87.3%–95.9% | 1.3%–8.3% | 46.9%–66.8% |
| 9b lp | 95.9%–99.2% | 94.3%–99.3% | 1.8%–9.4% | 52.4%–71.9% | 90.6%–96.2% | 86.5%–95.4% | 0.1%–4.6% | 35.2%–55.3% |
| 27b lp | 95.9%–99.2% | 93.3%–99.0% | 0.0%–3.1% | 45.8%–65.8% | 89.4%–95.4% | 84.2%–93.8% | 0.0%–3.1% | 13.8%–30.3% |
| d3-4b | 95.9%–99.2% | 93.3%–99.0% | 9.7%–22.5% | 79.6%–93.1% | 90.6%–96.2% | 87.3%–95.9% | 0.9%–7.1% | 70.9%–87.1% |
| d3-9b | 95.9%–99.2% | 94.3%–99.3% | 0.1%–4.6% | 62.6%–80.6% | 92.3%–97.3% | 90.7%–97.7% | 0.1%–4.6% | 38.4%–58.5% |
| d3-27b | 95.9%–99.2% | 92.4%–98.6% | 0.0%–3.1% | 34.2%–54.2% | 98.0%–99.9% | 96.3%–99.9% | 0.0%–3.1% | 39.4%–59.5% |
| Jev | 95.9%–99.2% | 93.3%–99.0% | 4.6%–14.7% | 64.9%–82.5% | 90.2%–96.0% | 84.9%–94.4% | 0.1%–4.6% | 52.4%–71.9% |
| 4b json | 98.0%–99.9% | 96.3%–99.9% | 76.6%–89.6% | 94.0%–99.8% | 86.5%–93.4% | 81.1%–91.7% | 0.5%–5.9% | 42.6%–62.7% |
| 9b json | 98.7%–100.0% | 97.5%–100.0% | 96.9%–100.0% | 95.9%–100.0% | 76.4%–85.4% | 71.4%–84.5% | 0.0%–3.1% | 22.2%–40.9% |
| 27b json | 98.7%–100.0% | 97.5%–100.0% | 44.4%–62.0% | 92.2%–99.4% | 92.3%–97.3% | 88.2%–96.3% | 0.0%–3.1% | 22.8%–41.7% |
| 4b jsonR | 98.7%–100.0% | 97.5%–100.0% | 96.9%–100.0% | 95.9%–100.0% | 83.0%–90.7% | 78.0%–89.6% | 0.9%–7.1% | 32.2%–52.0% |
| 9b jsonR | 98.7%–100.0% | 97.5%–100.0% | 96.9%–100.0% | 95.9%–100.0% | 88.9%–95.1% | 84.9%–94.4% | 1.3%–8.3% | 39.4%–59.5% |
| 27b jsonR | 97.5%–99.8% | 95.3%–99.6% | 5.2%–15.7% | 56.4%–75.5% | 91.5%–96.8% | 86.5%–95.4% | 0.0%–3.1% | 32.5%–52.5% |

What the rate tables show:

- **At thr98 every score model keeps 279 of 284 positives.** That is the 98% target, met in-sample by
  construction. Real positives alone: 96.7–98.0%.
- **Negatives decide the workload.**
  - Real-negative slip-through runs from 0/120 (27b lp, d3-27b) to 25/120 (4b lp).
  - Hard-negative slip-through runs from 40/91 (d3-27b) to 80/91 (d3-4b).
  - The bootstrap intervals for hard negatives are wide (27b lp: 28.6%–64.8%) because the threshold
    itself moves between resamples.
  - Where the count is 0/120, the Wilson upper bound is 3.1%.
- **At the default cutoff:**
  - Six of the seven score models keep 93.0–95.4% of positives.
  - d3-27b keeps 283/284 (99.6%), since its threshold for 98% recall is above 0.5 (0.5857).
- **JSON at thr98:**
  - 9b json, 4b jsonR and 9b jsonR reach 98% only at a threshold of 0, which flags every email.
  - 4b json and 27b json flag 84% and 53% of real negatives.

### B2.3 Per 10,000 hits at thr98 (positives like all golden positives)

*responsive share p = 5% (500 responsive, 9,500 not)*

| config | flagged: neg like real | flagged: neg 50/50 mix [95% CI] | flagged: neg like hard | missed [95% CI] | review avoided (mix) [95% CI] | responsive share of queue (mix) |
|---|---|---|---|---|---|---|
| 4b lp | 2,470 | 5,500 [3,547–6,434] | 8,530 | 9 [5–9] | 45% [36%–65%] | 9% |
| 9b lp | 887 | 3,664 [2,919–4,264] | 6,442 | 9 [5–9] | 63% [57%–71%] | 13% |
| 27b lp | 491 | 3,153 [1,848–3,574] | 5,815 | 9 [5–9] | 68% [64%–82%] | 16% |
| d3-4b | 1,916 | 5,380 [4,660–6,200] | 8,843 | 9 [4–9] | 46% [38%–53%] | 9% |
| d3-9b | 570 | 3,976 [2,788–4,451] | 7,381 | 9 [5–9] | 60% [55%–72%] | 12% |
| d3-27b | 491 | 2,579 [2,007–3,205] | 4,667 | 9 [4–9] | 74% [68%–80%] | 19% |
| Jev | 1,283 | 4,436 [3,861–5,027] | 7,590 | 9 [4–9] | 56% [50%–61%] | 11% |
| 4b json | 8,494 | 9,194 [8,866–9,509] | 9,894 | 2 [0–5] | 8% [5%–11%] | 5% |
| 9b json | 10,000 | 10,000 [10,000–10,000] | 10,000 | 0 [0–0] | 0% [0%–0%] | 5% |
| 27b json | 5,567 | 7,677 [7,167–8,100] | 9,787 | 0 [0–0] | 23% [19%–28%] | 7% |
| 4b jsonR | 10,000 | 10,000 [10,000–10,000] | 10,000 | 0 [0–0] | 0% [0%–0%] | 5% |
| 9b jsonR | 10,000 | 10,000 [3,803–10,000] | 10,000 | 0 [0–9] | 0% [0%–62%] | 5% |
| 27b jsonR | 1,367 | 4,099 [3,490–4,668] | 6,830 | 4 [0–9] | 59% [53%–65%] | 12% |

*responsive share p = 20% (2,000 responsive, 8,000 not)*

| config | flagged: neg like real | flagged: neg 50/50 mix [95% CI] | flagged: neg like hard | missed [95% CI] | review avoided (mix) [95% CI] | responsive share of queue (mix) |
|---|---|---|---|---|---|---|
| 4b lp | 3,631 | 6,183 [4,538–6,969] | 8,734 | 35 [21–35] | 38% [30%–55%] | 32% |
| 9b lp | 2,298 | 4,637 [4,009–5,147] | 6,976 | 35 [21–35] | 54% [49%–60%] | 42% |
| 27b lp | 1,965 | 4,207 [3,108–4,572] | 6,448 | 35 [21–35] | 58% [54%–69%] | 47% |
| d3-4b | 3,165 | 6,081 [5,479–6,781] | 8,998 | 35 [14–35] | 39% [32%–45%] | 32% |
| d3-9b | 2,031 | 4,899 [3,899–5,309] | 7,767 | 35 [21–35] | 51% [47%–61%] | 40% |
| d3-27b | 1,965 | 3,723 [3,247–4,251] | 5,481 | 35 [14–35] | 63% [57%–68%] | 53% |
| Jev | 2,631 | 5,287 [4,802–5,795] | 7,943 | 35 [14–35] | 47% [42%–52%] | 37% |
| 4b json | 8,726 | 9,316 [9,038–9,579] | 9,905 | 7 [0–21] | 7% [4%–10%] | 21% |
| 9b json | 10,000 | 10,000 [10,000–10,000] | 10,000 | 0 [0–0] | 0% [0%–0%] | 20% |
| 27b json | 6,267 | 8,043 [7,614–8,400] | 9,820 | 0 [0–0] | 20% [16%–24%] | 25% |
| 4b jsonR | 10,000 | 10,000 [10,000–10,000] | 10,000 | 0 [0–0] | 0% [0%–0%] | 20% |
| 9b jsonR | 10,000 | 10,000 [4,760–10,000] | 10,000 | 0 [0–35] | 0% [0%–52%] | 20% |
| 27b jsonR | 2,719 | 5,019 [4,501–5,504] | 7,319 | 14 [0–35] | 50% [45%–55%] | 40% |

*responsive share p = 50% (5,000 responsive, 5,000 not)*

| config | flagged: neg like real | flagged: neg 50/50 mix [95% CI] | flagged: neg like hard | missed [95% CI] | review avoided (mix) [95% CI] | responsive share of queue (mix) |
|---|---|---|---|---|---|---|
| 4b lp | 5,954 | 7,548 [6,535–8,061] | 9,143 | 88 [53–88] | 25% [19%–35%] | 65% |
| 9b lp | 5,120 | 6,582 [6,201–6,916] | 8,044 | 88 [53–88] | 34% [31%–38%] | 75% |
| 27b lp | 4,912 | 6,313 [5,626–6,560] | 7,714 | 88 [53–88] | 37% [34%–44%] | 78% |
| d3-4b | 5,662 | 7,485 [7,117–7,945] | 9,308 | 88 [35–88] | 25% [21%–29%] | 66% |
| d3-9b | 4,954 | 6,746 [6,121–7,017] | 8,538 | 88 [53–88] | 33% [30%–39%] | 73% |
| d3-27b | 4,912 | 6,011 [5,726–6,341] | 7,110 | 88 [35–88] | 40% [37%–43%] | 82% |
| Jev | 5,329 | 6,988 [6,685–7,328] | 8,648 | 88 [35–88] | 30% [27%–33%] | 70% |
| 4b json | 9,191 | 9,559 [9,375–9,723] | 9,927 | 18 [0–53] | 4% [3%–6%] | 52% |
| 9b json | 10,000 | 10,000 [10,000–10,000] | 10,000 | 0 [0–0] | 0% [0%–0%] | 50% |
| 27b json | 7,667 | 8,777 [8,509–9,000] | 9,888 | 0 [0–0] | 12% [10%–15%] | 57% |
| 4b jsonR | 10,000 | 10,000 [10,000–10,000] | 10,000 | 0 [0–0] | 0% [0%–0%] | 50% |
| 9b jsonR | 10,000 | 10,000 [6,672–10,000] | 10,000 | 0 [0–88] | 0% [0%–33%] | 50% |
| 27b jsonR | 5,423 | 6,861 [6,537–7,163] | 8,298 | 35 [0–88] | 31% [28%–35%] | 72% |

### B2.4 Per 10,000 hits at the default cutoff (positives like all golden positives)

*responsive share p = 5% (500 responsive, 9,500 not)*

| config | flagged: neg like real | flagged: neg 50/50 mix [95% CI] | flagged: neg like hard | missed [95% CI] | review avoided (mix) [95% CI] | responsive share of queue (mix) |
|---|---|---|---|---|---|---|
| 4b lp | 792 | 3,348 [2,891–3,827] | 5,904 | 25 [12–37] | 67% [62%–71%] | 14% |
| 9b lp | 549 | 2,650 [2,147–3,087] | 4,750 | 30 [16–42] | 74% [69%–79%] | 18% |
| 27b lp | 465 | 1,457 [1,091–1,865] | 2,448 | 35 [21–49] | 85% [81%–89%] | 32% |
| d3-4b | 708 | 4,399 [3,956–4,811] | 8,091 | 30 [18–46] | 56% [52%–60%] | 11% |
| d3-9b | 556 | 2,813 [2,311–3,342] | 5,071 | 23 [12–37] | 72% [67%–77%] | 17% |
| d3-27b | 498 | 2,847 [2,377–3,367] | 5,196 | 2 [0–5] | 72% [66%–76%] | 17% |
| Jev | 547 | 3,483 [2,972–4,014] | 6,419 | 32 [18–46] | 65% [60%–70%] | 13% |
| 4b json | 611 | 3,037 [2,557–3,525] | 5,463 | 48 [32–63] | 70% [65%–74%] | 15% |
| 9b json | 407 | 1,868 [1,416–2,336] | 3,330 | 93 [72–116] | 81% [77%–86%] | 22% |
| 27b json | 477 | 1,971 [1,543–2,473] | 3,466 | 23 [12–35] | 80% [75%–85%] | 24% |
| 4b jsonR | 674 | 2,539 [2,033–3,030] | 4,404 | 63 [46–83] | 75% [70%–80%] | 17% |
| 9b jsonR | 780 | 2,970 [2,464–3,442] | 5,161 | 37 [23–53] | 70% [66%–75%] | 16% |
| 27b jsonR | 474 | 2,479 [2,002–2,980] | 4,485 | 26 [14–39] | 75% [70%–80%] | 19% |

*responsive share p = 20% (2,000 responsive, 8,000 not)*

| config | flagged: neg like real | flagged: neg 50/50 mix [95% CI] | flagged: neg like hard | missed [95% CI] | review avoided (mix) [95% CI] | responsive share of queue (mix) |
|---|---|---|---|---|---|---|
| 4b lp | 2,168 | 4,320 [3,927–4,725] | 6,473 | 99 [49–148] | 57% [53%–61%] | 44% |
| 9b lp | 1,947 | 3,716 [3,278–4,090] | 5,485 | 120 [63–169] | 63% [59%–67%] | 51% |
| 27b lp | 1,859 | 2,694 [2,387–3,028] | 3,529 | 141 [85–197] | 73% [70%–76%] | 69% |
| d3-4b | 2,080 | 5,189 [4,813–5,534] | 8,298 | 120 [70–183] | 48% [45%–52%] | 36% |
| d3-9b | 1,975 | 3,876 [3,449–4,326] | 5,777 | 92 [49–148] | 61% [57%–66%] | 49% |
| d3-27b | 1,993 | 3,971 [3,575–4,403] | 5,949 | 7 [0–21] | 60% [56%–64%] | 50% |
| Jev | 1,940 | 4,412 [3,980–4,848] | 6,884 | 127 [70–183] | 56% [52%–60%] | 42% |
| 4b json | 1,943 | 3,986 [3,577–4,398] | 6,030 | 190 [127–254] | 60% [56%–64%] | 45% |
| 9b json | 1,627 | 2,858 [2,483–3,258] | 4,088 | 373 [289–465] | 71% [67%–75%] | 57% |
| 27b json | 1,908 | 3,167 [2,800–3,581] | 4,425 | 92 [49–141] | 68% [64%–72%] | 60% |
| 4b jsonR | 1,946 | 3,517 [3,088–3,930] | 5,087 | 254 [183–331] | 65% [61%–69%] | 50% |
| 9b jsonR | 2,118 | 3,963 [3,516–4,368] | 5,808 | 148 [92–211] | 60% [56%–65%] | 47% |
| 27b jsonR | 1,894 | 3,583 [3,184–4,002] | 5,272 | 106 [56–155] | 64% [60%–68%] | 53% |

*responsive share p = 50% (5,000 responsive, 5,000 not)*

| config | flagged: neg like real | flagged: neg 50/50 mix [95% CI] | flagged: neg like hard | missed [95% CI] | review avoided (mix) [95% CI] | responsive share of queue (mix) |
|---|---|---|---|---|---|---|
| 4b lp | 4,920 | 6,265 [5,979–6,556] | 7,611 | 246 [123–370] | 37% [34%–40%] | 76% |
| 9b lp | 4,742 | 5,848 [5,552–6,122] | 6,953 | 299 [158–423] | 42% [39%–44%] | 80% |
| 27b lp | 4,648 | 5,170 [4,927–5,437] | 5,692 | 352 [211–493] | 48% [46%–51%] | 90% |
| d3-4b | 4,826 | 6,769 [6,502–7,018] | 8,712 | 299 [176–458] | 32% [30%–35%] | 69% |
| d3-9b | 4,813 | 6,001 [5,697–6,284] | 7,189 | 229 [123–370] | 40% [37%–43%] | 80% |
| d3-27b | 4,982 | 6,219 [5,971–6,484] | 7,455 | 18 [0–53] | 38% [35%–40%] | 80% |
| Jev | 4,725 | 6,270 [5,988–6,583] | 7,815 | 317 [176–458] | 37% [34%–40%] | 75% |
| 4b json | 4,608 | 5,885 [5,564–6,192] | 7,162 | 475 [317–634] | 41% [38%–44%] | 77% |
| 9b json | 4,067 | 4,836 [4,523–5,150] | 5,605 | 933 [722–1,162] | 52% [49%–55%] | 84% |
| 27b json | 4,771 | 5,558 [5,294–5,838] | 6,344 | 229 [123–352] | 44% [42%–47%] | 86% |
| 4b jsonR | 4,491 | 5,473 [5,141–5,795] | 6,454 | 634 [458–827] | 45% [42%–49%] | 80% |
| 9b jsonR | 4,796 | 5,949 [5,633–6,233] | 7,102 | 371 [229–528] | 41% [38%–44%] | 78% |
| 27b jsonR | 4,736 | 5,791 [5,507–6,080] | 6,847 | 264 [141–387] | 42% [39%–45%] | 82% |

### B2.5 Sensitivity: positives like the real positives only

| config | thr98: missed, p=5% | thr98: missed, p=20% | thr98: missed, p=50% | thr98: flagged, p=20%, mix | default: missed, p=5% | default: missed, p=20% | default: missed, p=50% | default: flagged, p=20%, mix |
|---|---|---|---|---|---|---|---|---|
| 4b lp | 17 [7–17] | 67 [27–67] | 167 [67–167] | 6,151 [4,542–6,940] | 37 [17–57] | 147 [67–227] | 367 [167–567] | 4,272 [3,867–4,691] |
| 9b lp | 10 [0–17] | 40 [0–67] | 100 [0–167] | 4,632 [4,021–5,168] | 40 [20–63] | 160 [80–253] | 400 [200–633] | 3,676 [3,239–4,057] |
| 27b lp | 13 [7–17] | 53 [27–67] | 133 [67–167] | 4,188 [3,090–4,553] | 50 [27–73] | 200 [107–293] | 500 [267–733] | 2,635 [2,314–2,992] |
| d3-4b | 13 [3–17] | 53 [13–67] | 133 [33–167] | 6,063 [5,463–6,751] | 37 [17–60] | 147 [67–240] | 367 [167–600] | 5,162 [4,796–5,519] |
| d3-9b | 10 [3–17] | 40 [13–67] | 100 [33–167] | 4,894 [3,907–5,297] | 23 [7–43] | 93 [27–173] | 233 [67–433] | 3,874 [3,445–4,319] |
| d3-27b | 17 [7–17] | 67 [27–67] | 167 [67–167] | 3,692 [3,235–4,219] | 3 [0–10] | 13 [0–40] | 33 [0–100] | 3,965 [3,569–4,391] |
| Jev | 13 [3–17] | 53 [13–67] | 133 [33–167] | 5,269 [4,781–5,782] | 47 [23–70] | 187 [93–280] | 467 [233–700] | 4,352 [3,915–4,800] |
| 4b json | 3 [0–10] | 13 [0–40] | 33 [0–100] | 9,309 [9,029–9,573] | 63 [37–90] | 253 [147–360] | 633 [367–900] | 3,923 [3,492–4,345] |
| 9b json | 0 [0–0] | 0 [0–0] | 0 [0–0] | 10,000 [10,000–10,000] | 107 [77–140] | 427 [307–560] | 1,067 [767–1,400] | 2,804 [2,399–3,213] |
| 27b json | 0 [0–0] | 0 [0–0] | 0 [0–0] | 8,043 [7,614–8,400] | 33 [13–53] | 133 [53–213] | 333 [133–533] | 3,125 [2,756–3,538] |
| 4b jsonR | 0 [0–0] | 0 [0–0] | 0 [0–0] | 10,000 [10,000–10,000] | 77 [50–103] | 307 [200–413] | 767 [500–1,033] | 3,464 [3,021–3,898] |
| 9b jsonR | 0 [0–10] | 0 [0–40] | 0 [0–100] | 10,000 [4,753–10,000] | 47 [27–70] | 187 [107–280] | 467 [267–700] | 3,925 [3,476–4,323] |
| 27b jsonR | 7 [0–17] | 27 [0–67] | 67 [0–167] | 5,007 [4,482–5,480] | 40 [20–63] | 160 [80–253] | 400 [200–633] | 3,529 [3,124–3,964] |

What the per-10,000 tables show:

- **Plausible scenario (p = 20%, mix) at thr98:** the seven score models leave 3,723 (d3-27b) to
  6,183 (4b lp) of 10,000 hits for review. That avoids 38%–63% of a full read.
- **Review avoided is smaller than the golden "eliminated" share at thr98 (51.7%–81.0% of all 211
  negatives, B2.1).** Two reasons: the
  2,000 responsive emails must be read anyway, and half the negatives behave like hard negatives.
- **What the negatives look like matters more than which model screens them.** For the 27b lp at p =
  20%, flagged goes from 1,965 (negatives like real ones) through 4,207 (mix) to 6,448 (like hard
  ones). That spread is wider than the spread between models at the mix (3,723–6,183).
- **Misses at thr98:**
  - With positives like all golden positives, every score model misses 35 per 10,000 at p = 20%
    (9 at 5%, 88 at 50%). That is the 2% that thr98 allows, by construction.
  - With positives like real positives only (B2.5), 40–67 are missed at p = 20%.
  - The upper ends of these intervals equal the point value because the threshold is re-tuned to 98%
    in every resample, so they say nothing about out-of-sample misses (branch A).
- **At the default cutoff (p = 20%, mix):**
  - Flagged: 2,694 (27b lp) to 5,189 (d3-4b).
  - Six of the seven score models miss 92–141 of the 2,000 responsive emails.
  - d3-27b misses 7 [0–21] while flagging 3,971.
  - The JSON modes miss 92–373.

## B3. Reviewer time vs machine time

### B3.1 Reviewer hours vs machine hours, plausible scenario

Reading all 10,000 hits takes 83.3 h at 30 s per email and 166.7 h at 60 s. "Saved" = that minus the reviewer hours. "Bottleneck" = the larger of machine hours and reviewer hours, which applies if scoring and review overlap. Run back to back, the elapsed time is the sum. The "missed" intervals are in B2.3/B2.4.

*at the in-sample 98%-recall threshold*

| config | machine h | flagged | missed | reviewer h @30 s [CI] | saved h @30 s | bottleneck @30 s | reviewer h @60 s [CI] | saved h @60 s | bottleneck @60 s | break-even s/email |
|---|---|---|---|---|---|---|---|---|---|---|
| 4b lp | 1.7 | 6,183 [4,538–6,969] | 35 | 51.5 [37.8–58.1] | 31.8 | reviewer | 103.0 [75.6–116.2] | 63.6 | reviewer | 1 |
| 9b lp | 2.8 | 4,637 [4,009–5,147] | 35 | 38.6 [33.4–42.9] | 44.7 | reviewer | 77.3 [66.8–85.8] | 89.4 | reviewer | 2 |
| 27b lp | 8.9 | 4,207 [3,108–4,572] | 35 | 35.1 [25.9–38.1] | 48.3 | reviewer | 70.1 [51.8–76.2] | 96.6 | reviewer | 8 |
| d3-4b | 2.9 | 6,081 [5,479–6,781] | 35 | 50.7 [45.7–56.5] | 32.7 | reviewer | 101.4 [91.3–113.0] | 65.3 | reviewer | 2 |
| d3-9b | 4.5 | 4,899 [3,899–5,309] | 35 | 40.8 [32.5–44.2] | 42.5 | reviewer | 81.7 [65.0–88.5] | 85.0 | reviewer | 3 |
| d3-27b | 14.7 | 3,723 [3,247–4,251] | 35 | 31.0 [27.1–35.4] | 52.3 | reviewer | 62.1 [54.1–70.8] | 104.6 | reviewer | 14 |
| Jev | 0.3 | 5,287 [4,802–5,795] | 35 | 44.1 [40.0–48.3] | 39.3 | reviewer | 88.1 [80.0–96.6] | 78.5 | reviewer | 0 |
| 4b json | 7.9 | 9,316 [9,038–9,579] | 7 | 77.6 [75.3–79.8] | 5.7 | reviewer | 155.3 [150.6–159.6] | 11.4 | reviewer | 3 |
| 9b json | 12.8 | 10,000 [10,000–10,000] | 0 | 83.3 [83.3–83.3] | 0.0 | reviewer | 166.7 [166.7–166.7] | 0.0 | reviewer | 5 |
| 27b json | 20.0 | 8,043 [7,614–8,400] | 0 | 67.0 [63.4–70.0] | 16.3 | reviewer | 134.1 [126.9–140.0] | 32.6 | reviewer | 9 |
| 4b jsonR | 8.3 | 10,000 [10,000–10,000] | 0 | 83.3 [83.3–83.3] | 0.0 | reviewer | 166.7 [166.7–166.7] | 0.0 | reviewer | 3 |
| 9b jsonR | 14.8 | 10,000 [4,760–10,000] | 0 | 83.3 [39.7–83.3] | 0.0 | reviewer | 166.7 [79.3–166.7] | 0.0 | reviewer | 5 |
| 27b jsonR | 20.8 | 5,019 [4,501–5,504] | 14 | 41.8 [37.5–45.9] | 41.5 | reviewer | 83.7 [75.0–91.7] | 83.0 | reviewer | 15 |

*at the default decision (score ≥ 0.5 / JSON verdict)*

| config | machine h | flagged | missed | reviewer h @30 s [CI] | saved h @30 s | bottleneck @30 s | reviewer h @60 s [CI] | saved h @60 s | bottleneck @60 s | break-even s/email |
|---|---|---|---|---|---|---|---|---|---|---|
| 4b lp | 1.7 | 4,320 [3,927–4,725] | 99 | 36.0 [32.7–39.4] | 47.3 | reviewer | 72.0 [65.4–78.7] | 94.7 | reviewer | 1 |
| 9b lp | 2.8 | 3,716 [3,278–4,090] | 120 | 31.0 [27.3–34.1] | 52.4 | reviewer | 61.9 [54.6–68.2] | 104.7 | reviewer | 3 |
| 27b lp | 8.9 | 2,694 [2,387–3,028] | 141 | 22.5 [19.9–25.2] | 60.9 | reviewer | 44.9 [39.8–50.5] | 121.8 | reviewer | 12 |
| d3-4b | 2.9 | 5,189 [4,813–5,534] | 120 | 43.2 [40.1–46.1] | 40.1 | reviewer | 86.5 [80.2–92.2] | 80.2 | reviewer | 2 |
| d3-9b | 4.5 | 3,876 [3,449–4,326] | 92 | 32.3 [28.7–36.0] | 51.0 | reviewer | 64.6 [57.5–72.1] | 102.1 | reviewer | 4 |
| d3-27b | 14.7 | 3,971 [3,575–4,403] | 7 | 33.1 [29.8–36.7] | 50.2 | reviewer | 66.2 [59.6–73.4] | 100.5 | reviewer | 13 |
| Jev | 0.3 | 4,412 [3,980–4,848] | 127 | 36.8 [33.2–40.4] | 46.6 | reviewer | 73.5 [66.3–80.8] | 93.1 | reviewer | 0 |
| 4b json | 7.9 | 3,986 [3,577–4,398] | 190 | 33.2 [29.8–36.6] | 50.1 | reviewer | 66.4 [59.6–73.3] | 100.2 | reviewer | 7 |
| 9b json | 12.8 | 2,858 [2,483–3,258] | 373 | 23.8 [20.7–27.2] | 59.5 | reviewer | 47.6 [41.4–54.3] | 119.0 | reviewer | 16 |
| 27b json | 20.0 | 3,167 [2,800–3,581] | 92 | 26.4 [23.3–29.8] | 56.9 | reviewer | 52.8 [46.7–59.7] | 113.9 | reviewer | 23 |
| 4b jsonR | 8.3 | 3,517 [3,088–3,930] | 254 | 29.3 [25.7–32.7] | 54.0 | reviewer | 58.6 [51.5–65.5] | 108.1 | reviewer | 9 |
| 9b jsonR | 14.8 | 3,963 [3,516–4,368] | 148 | 33.0 [29.3–36.4] | 50.3 | reviewer | 66.0 [58.6–72.8] | 100.6 | reviewer | 13 |
| 27b jsonR | 20.8 | 3,583 [3,184–4,002] | 106 | 29.9 [26.5–33.4] | 53.5 | reviewer | 59.7 [53.1–66.7] | 106.9 | reviewer | 21 |

### B3.2 Break-even review seconds per flagged email, every scenario, thr98

Machine seconds ÷ flagged emails. If a reviewer spends longer than this per flagged email, review takes longer than scoring.

| config | machine h | p=5%, neg real | p=5%, neg mix | p=5%, neg hard | p=20%, neg real | p=20%, neg mix | p=20%, neg hard | p=50%, neg real | p=50%, neg mix | p=50%, neg hard |
|---|---|---|---|---|---|---|---|---|---|---|
| 4b lp | 1.7 | 2 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 |
| 9b lp | 2.8 | 12 | 3 | 2 | 4 | 2 | 1 | 2 | 2 | 1 |
| 27b lp | 8.9 | 65 | 10 | 6 | 16 | 8 | 5 | 7 | 5 | 4 |
| d3-4b | 2.9 | 5 | 2 | 1 | 3 | 2 | 1 | 2 | 1 | 1 |
| d3-9b | 4.5 | 29 | 4 | 2 | 8 | 3 | 2 | 3 | 2 | 2 |
| d3-27b | 14.7 | 108 | 21 | 11 | 27 | 14 | 10 | 11 | 9 | 7 |
| Jev | 0.3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 4b json | 7.9 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| 9b json | 12.8 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| 27b json | 20.0 | 13 | 9 | 7 | 11 | 9 | 7 | 9 | 8 | 7 |
| 4b jsonR | 8.3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| 9b jsonR | 14.8 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| 27b jsonR | 20.8 | 55 | 18 | 11 | 27 | 15 | 10 | 14 | 11 | 9 |

- **In the plausible scenario the reviewer is the bottleneck for every configuration**, at both cutoffs
  and both assumed reading speeds.
  - At thr98, reviewer hours are 31.0 (d3-27b) to 51.5 (4b lp) at 30 s per email, and 62.1 to 103.0 at
    60 s.
  - Machine hours are 0.3 to 14.7 for the score models, and up to 20.8 for JSON.
  - Reading all 10,000 hits would take 83.3 h at 30 s or 166.7 h at 60 s.
- **The machine is the bottleneck only when the review queue is small and the model is slow.** In
  B3.2, the break-even exceeds 30 s per email in one scenario only (p = 5%, negatives like real ones),
  for three configurations:
  - 27b lp: 65 s;
  - d3-27b: 108 s;
  - 27b jsonR: 55 s.

  It exceeds 60 s only for 27b lp and d3-27b, again in that one scenario. Everywhere else a person
  reading at 30 s per email takes longer than the screen.
- **Interpretation:** machine speed sets turnaround, for example whether a 10,000-hit batch finishes
  overnight. Accuracy sets the paid human hours. The machine's 0.3–14.7 h runs unattended; the
  reviewer's 31.0–51.5 h (at 30 s) don't.
- **Several reviewers:** with k reviewers working in parallel, elapsed review time is divided by k.
  The machine then becomes the bottleneck when the per-email reading time is below k × break-even, so the
  break-even column also answers the team case.

## B4. The correspondent-scoped request with the roster (25-3152)

**Machine time.**

- **The roster is free for the stock-Qwen lp runs** (B1.3): 1.50 / 2.55 / 7.97 h per 10,000 with it
  (B1.2).
- **It is expensive for d3:** +2.26 / +3.20 / +10.33 h per 10,000. With the roster, d3-27b needs 25.78 h
  per 10,000.
- **Jev:** +0.03 h.

### B4.1 Pass rates without and with the roster (same 249 pairs)

*at the in-sample 98%-recall threshold*

| config | roster | threshold | positives: all | positives: real | negatives: real | negatives: hard |
|---|---|---|---|---|---|---|
| 4b lp | without | 0.2210 | 138/140 = 98.6% [98.6%–100.0%] | 73/75 = 97.3% [97.3%–100.0%] | 30/60 = 50.0% [5.0%–86.7%] | 47/49 = 95.9% [69.4%–100.0%] |
| 4b lp | with | 0.5606 | 138/140 = 98.6% [98.6%–100.0%] | 73/75 = 97.3% [97.3%–100.0%] | 2/60 = 3.3% [0.0%–18.3%] | 25/49 = 51.0% [32.7%–77.6%] |
| 9b lp | without | 0.4196 | 138/140 = 98.6% [98.6%–100.0%] | 73/75 = 97.3% [97.3%–100.0%] | 3/60 = 5.0% [0.0%–11.7%] | 30/49 = 61.2% [42.9%–77.6%] |
| 9b lp | with | 0.3901 | 138/140 = 98.6% [98.6%–100.0%] | 73/75 = 97.3% [97.3%–100.0%] | 2/60 = 3.3% [0.0%–10.0%] | 33/49 = 67.3% [46.9%–85.7%] |
| 27b lp | without | 0.0566 | 138/140 = 98.6% [98.6%–100.0%] | 73/75 = 97.3% [97.3%–100.0%] | 0/60 = 0.0% [0.0%–5.0%] | 28/49 = 57.1% [40.8%–83.7%] |
| 27b lp | with | 0.0783 | 138/140 = 98.6% [98.6%–100.0%] | 74/75 = 98.7% [97.3%–100.0%] | 0/60 = 0.0% [0.0%–0.0%] | 10/49 = 20.4% [8.2%–30.6%] |
| d3-4b | without | 0.3507 | 138/140 = 98.6% [98.6%–100.0%] | 73/75 = 97.3% [97.3%–100.0%] | 18/60 = 30.0% [8.3%–85.0%] | 42/49 = 85.7% [75.5%–95.9%] |
| d3-4b | with | 0.7588 | 138/140 = 98.6% [98.6%–100.0%] | 75/75 = 100.0% [97.3%–100.0%] | 0/60 = 0.0% [0.0%–0.0%] | 15/49 = 30.6% [16.3%–44.9%] |
| d3-9b | without | 0.5427 | 138/140 = 98.6% [98.6%–100.0%] | 73/75 = 97.3% [97.3%–100.0%] | 0/60 = 0.0% [0.0%–3.3%] | 28/49 = 57.1% [38.8%–87.8%] |
| d3-9b | with | 0.8529 | 138/140 = 98.6% [98.6%–100.0%] | 74/75 = 98.7% [97.3%–100.0%] | 0/60 = 0.0% [0.0%–0.0%] | 11/49 = 22.4% [10.2%–32.7%] |
| d3-27b | without | 0.5405 | 138/140 = 98.6% [98.6%–100.0%] | 73/75 = 97.3% [97.3%–100.0%] | 0/60 = 0.0% [0.0%–0.0%] | 16/49 = 32.7% [16.3%–44.9%] |
| d3-27b | with | 0.9133 | 138/140 = 98.6% [98.6%–100.0%] | 73/75 = 97.3% [97.3%–100.0%] | 0/60 = 0.0% [0.0%–0.0%] | 2/49 = 4.1% [0.0%–10.2%] |
| Jev | without | 0.3100 | 138/140 = 98.6% [98.6%–100.0%] | 74/75 = 98.7% [97.3%–100.0%] | 14/60 = 23.3% [10.0%–60.0%] | 32/49 = 65.3% [49.0%–83.7%] |
| Jev | with | 0.4600 | 138/140 = 98.6% [98.6%–100.0%] | 73/75 = 97.3% [97.3%–100.0%] | 0/60 = 0.0% [0.0%–0.0%] | 18/49 = 36.7% [20.4%–53.1%] |
| 4b json | without | 0.0500 | 139/140 = 99.3% [98.6%–100.0%] | 74/75 = 98.7% [97.3%–100.0%] | 49/60 = 81.7% [71.7%–100.0%] | 49/49 = 100.0% [100.0%–100.0%] |
| 4b json | with | 0.0500 | 140/140 = 100.0% [98.6%–100.0%] | 75/75 = 100.0% [97.3%–100.0%] | 44/60 = 73.3% [0.0%–83.3%] | 47/49 = 95.9% [53.1%–100.0%] |
| 9b json | without | 0.0000 | 140/140 = 100.0% [100.0%–100.0%] | 75/75 = 100.0% [100.0%–100.0%] | 60/60 = 100.0% [100.0%–100.0%] | 49/49 = 100.0% [100.0%–100.0%] |
| 9b json | with | 0.0000 | 140/140 = 100.0% [100.0%–100.0%] | 75/75 = 100.0% [100.0%–100.0%] | 60/60 = 100.0% [100.0%–100.0%] | 49/49 = 100.0% [100.0%–100.0%] |
| 27b json | without | 0.0500 | 140/140 = 100.0% [100.0%–100.0%] | 75/75 = 100.0% [100.0%–100.0%] | 50/60 = 83.3% [73.3%–91.7%] | 45/47 = 95.7% [88.9%–100.0%] |
| 27b json | with | 0.0500 | 139/139 = 100.0% [98.6%–100.0%] | 75/75 = 100.0% [97.3%–100.0%] | 8/60 = 13.3% [0.0%–20.0%] | 40/49 = 81.6% [6.1%–89.8%] |
| 4b jsonR | without | 0.0000 | 140/140 = 100.0% [100.0%–100.0%] | 75/75 = 100.0% [100.0%–100.0%] | 60/60 = 100.0% [100.0%–100.0%] | 49/49 = 100.0% [100.0%–100.0%] |
| 4b jsonR | with | 0.0000 | 140/140 = 100.0% [98.6%–100.0%] | 75/75 = 100.0% [98.7%–100.0%] | 60/60 = 100.0% [5.0%–100.0%] | 49/49 = 100.0% [57.1%–100.0%] |
| 9b jsonR | without | 0.0000 | 139/139 = 100.0% [98.6%–100.0%] | 75/75 = 100.0% [97.3%–100.0%] | 60/60 = 100.0% [8.3%–100.0%] | 49/49 = 100.0% [63.3%–100.0%] |
| 9b jsonR | with | 0.0500 | 140/140 = 100.0% [98.6%–100.0%] | 75/75 = 100.0% [97.3%–100.0%] | 9/60 = 15.0% [1.7%–23.3%] | 37/49 = 75.5% [40.8%–85.7%] |
| 27b jsonR | without | 0.0500 | 138/140 = 98.6% [98.6%–100.0%] | 73/75 = 97.3% [97.3%–100.0%] | 11/60 = 18.3% [10.0%–100.0%] | 31/48 = 64.6% [51.1%–100.0%] |
| 27b jsonR | with | 0.0500 | 140/140 = 100.0% [100.0%–100.0%] | 75/75 = 100.0% [100.0%–100.0%] | 1/60 = 1.7% [0.0%–5.0%] | 25/49 = 51.0% [36.7%–65.3%] |

*at the default decision (score ≥ 0.5 / JSON verdict)*

| config | roster | threshold | positives: all | positives: real | negatives: real | negatives: hard |
|---|---|---|---|---|---|---|
| 4b lp | without | 0.5 / verdict | 133/140 = 95.0% [91.4%–98.6%] | 69/75 = 92.0% [85.3%–97.3%] | 4/60 = 6.7% [1.7%–13.3%] | 34/49 = 69.4% [57.1%–81.6%] |
| 4b lp | with | 0.5 / verdict | 139/140 = 99.3% [97.9%–100.0%] | 74/75 = 98.7% [96.0%–100.0%] | 4/60 = 6.7% [1.7%–13.3%] | 32/49 = 65.3% [51.0%–77.6%] |
| 9b lp | without | 0.5 / verdict | 135/140 = 96.4% [92.9%–99.3%] | 70/75 = 93.3% [86.7%–98.7%] | 1/60 = 1.7% [0.0%–5.0%] | 26/49 = 53.1% [38.8%–65.3%] |
| 9b lp | with | 0.5 / verdict | 135/140 = 96.4% [92.9%–99.3%] | 71/75 = 94.7% [89.3%–98.7%] | 0/60 = 0.0% [0.0%–0.0%] | 27/49 = 55.1% [40.8%–69.4%] |
| 27b lp | without | 0.5 / verdict | 125/140 = 89.3% [84.3%–93.6%] | 62/75 = 82.7% [74.7%–90.7%] | 0/60 = 0.0% [0.0%–0.0%] | 13/49 = 26.5% [14.3%–38.8%] |
| 27b lp | with | 0.5 / verdict | 122/140 = 87.1% [81.4%–92.1%] | 63/75 = 84.0% [76.0%–92.0%] | 0/60 = 0.0% [0.0%–0.0%] | 5/49 = 10.2% [2.0%–18.4%] |
| d3-4b | without | 0.5 / verdict | 132/140 = 94.3% [90.0%–97.9%] | 69/75 = 92.0% [85.3%–97.3%] | 3/60 = 5.0% [0.0%–11.7%] | 40/49 = 81.6% [69.4%–91.8%] |
| d3-4b | with | 0.5 / verdict | 140/140 = 100.0% [100.0%–100.0%] | 75/75 = 100.0% [100.0%–100.0%] | 0/60 = 0.0% [0.0%–0.0%] | 25/49 = 51.0% [34.7%–63.3%] |
| d3-9b | without | 0.5 / verdict | 138/140 = 98.6% [96.4%–100.0%] | 73/75 = 97.3% [93.3%–100.0%] | 1/60 = 1.7% [0.0%–5.0%] | 30/49 = 61.2% [46.9%–73.5%] |
| d3-9b | with | 0.5 / verdict | 140/140 = 100.0% [100.0%–100.0%] | 75/75 = 100.0% [100.0%–100.0%] | 0/60 = 0.0% [0.0%–0.0%] | 23/49 = 46.9% [32.7%–59.2%] |
| d3-27b | without | 0.5 / verdict | 139/140 = 99.3% [97.9%–100.0%] | 74/75 = 98.7% [96.0%–100.0%] | 0/60 = 0.0% [0.0%–0.0%] | 16/49 = 32.7% [20.4%–44.9%] |
| d3-27b | with | 0.5 / verdict | 140/140 = 100.0% [100.0%–100.0%] | 75/75 = 100.0% [100.0%–100.0%] | 0/60 = 0.0% [0.0%–0.0%] | 8/49 = 16.3% [6.1%–26.5%] |
| Jev | without | 0.5 / verdict | 123/140 = 87.9% [82.1%–92.9%] | 62/75 = 82.7% [73.3%–90.7%] | 0/60 = 0.0% [0.0%–0.0%] | 22/49 = 44.9% [30.6%–57.1%] |
| Jev | with | 0.5 / verdict | 135/140 = 96.4% [93.6%–99.3%] | 70/75 = 93.3% [88.0%–98.7%] | 0/60 = 0.0% [0.0%–0.0%] | 17/49 = 34.7% [20.4%–46.9%] |
| 4b json | without | 0.5 / verdict | 128/140 = 91.4% [86.4%–95.7%] | 67/75 = 89.3% [81.3%–96.0%] | 2/60 = 3.3% [0.0%–8.3%] | 33/49 = 67.3% [55.1%–79.6%] |
| 4b json | with | 0.5 / verdict | 134/140 = 95.7% [92.1%–98.6%] | 70/75 = 93.3% [86.7%–98.7%] | 1/60 = 1.7% [0.0%–5.0%] | 27/49 = 55.1% [40.8%–67.3%] |
| 9b json | without | 0.5 / verdict | 114/140 = 81.4% [75.0%–87.9%] | 57/75 = 76.0% [66.7%–85.3%] | 0/60 = 0.0% [0.0%–0.0%] | 18/49 = 36.7% [22.4%–49.0%] |
| 9b json | with | 0.5 / verdict | 131/140 = 93.6% [89.3%–97.1%] | 68/75 = 90.7% [82.7%–96.0%] | 0/60 = 0.0% [0.0%–0.0%] | 20/49 = 40.8% [26.5%–53.1%] |
| 27b json | without | 0.5 / verdict | 129/140 = 92.1% [87.9%–96.4%] | 65/75 = 86.7% [78.7%–93.3%] | 0/60 = 0.0% [0.0%–0.0%] | 15/47 = 31.9% [18.8%–44.7%] |
| 27b json | with | 0.5 / verdict | 136/139 = 97.8% [95.7%–100.0%] | 73/75 = 97.3% [93.3%–100.0%] | 0/60 = 0.0% [0.0%–0.0%] | 6/49 = 12.2% [4.1%–22.4%] |
| 4b jsonR | without | 0.5 / verdict | 119/140 = 85.0% [78.6%–90.0%] | 60/75 = 80.0% [70.7%–89.3%] | 3/60 = 5.0% [0.0%–11.7%] | 22/49 = 44.9% [30.6%–59.2%] |
| 4b jsonR | with | 0.5 / verdict | 125/140 = 89.3% [83.6%–93.6%] | 66/75 = 88.0% [80.0%–94.7%] | 1/60 = 1.7% [0.0%–5.0%] | 17/49 = 34.7% [22.4%–49.0%] |
| 9b jsonR | without | 0.5 / verdict | 129/139 = 92.8% [88.5%–97.1%] | 68/75 = 90.7% [84.0%–96.0%] | 4/60 = 6.7% [1.7%–13.3%] | 29/49 = 59.2% [44.9%–71.4%] |
| 9b jsonR | with | 0.5 / verdict | 137/140 = 97.9% [95.0%–100.0%] | 72/75 = 96.0% [90.7%–100.0%] | 3/60 = 5.0% [0.0%–10.0%] | 28/49 = 57.1% [42.9%–71.4%] |
| 27b jsonR | without | 0.5 / verdict | 125/140 = 89.3% [84.3%–93.6%] | 63/75 = 84.0% [76.0%–92.0%] | 0/60 = 0.0% [0.0%–0.0%] | 14/48 = 29.2% [16.7%–42.9%] |
| 27b jsonR | with | 0.5 / verdict | 129/140 = 92.1% [87.9%–96.4%] | 69/75 = 92.0% [85.3%–97.3%] | 0/60 = 0.0% [0.0%–0.0%] | 6/49 = 12.2% [4.1%–22.4%] |

### B4.2 Per 10,000 hits, plausible scenario

*at the in-sample 98%-recall threshold*

| config | machine h without → with | flagged without → with [CI] | Δ flagged [paired CI] | missed without → with [CI] | review avoided |
|---|---|---|---|---|---|
| 4b lp | 1.5 → 1.5 | 7,808 [5,110–9,467] → 4,146 [3,359–5,754] | -3,663 [-5,277, -1,195] | 29 [0–29] → 29 [0–29] | 22% → 59% |
| 9b lp | 2.6 → 2.5 | 4,620 [3,767–5,392] → 4,799 [3,849–5,717] | +178 [-741, +965] | 29 [0–29] → 29 [0–29] | 54% → 52% |
| 27b lp | 8.3 → 8.0 | 4,257 [3,604–5,532] → 2,788 [2,298–3,196] | -1,469 [-2,812, -898] | 29 [0–29] → 29 [0–29] | 57% → 72% |
| d3-4b | 3.1 → 5.3 | 6,600 [5,539–9,267] → 3,196 [2,624–3,767] | -3,404 [-6,174, -2,249] | 29 [0–29] → 29 [0–29] | 34% → 68% |
| d3-9b | 4.8 → 8.0 | 4,257 [3,522–5,592] → 2,869 [2,380–3,306] | -1,388 [-2,856, -653] | 29 [0–29] → 29 [0–29] | 57% → 71% |
| d3-27b | 15.5 → 25.8 | 3,278 [2,624–3,796] → 2,135 [1,971–2,380] | -1,143 [-1,647, -490] | 29 [0–29] → 29 [0–29] | 67% → 79% |
| Jev | 0.3 → 0.4 | 5,517 [4,434–7,644] → 3,441 [2,802–4,094] | -2,076 [-4,182, -1,038] | 29 [0–29] → 29 [0–29] | 45% → 66% |
| 4b json | 8.0 → 10.1 | 9,252 [8,852–10,000] → 8,770 [4,161–9,237] | -482 [-5,106, -82] | 14 [0–29] → 0 [0–29] | 7% → 12% |
| 9b json | 12.8 → 15.9 | 10,000 [10,000–10,000] → 10,000 [10,000–10,000] | +0 [+0, +0] | 0 [0–0] → 0 [0–0] | 0% → 0% |
| 27b json | 19.5 → 18.1 | 9,163 [8,718–9,533] → 5,799 [2,216–6,273] | -3,364 [-7,138, -2,843] | 0 [0–0] → 0 [0–29] | 8% → 42% |
| 4b jsonR | 8.5 → 10.8 | 10,000 [10,000–10,000] → 10,000 [4,457–10,000] | +0 [-5,543, +0] | 0 [0–0] → 0 [0–29] | 0% → 0% |
| 9b jsonR | 15.5 → 18.6 | 10,000 [5,005–10,000] → 5,620 [3,819–6,132] | -4,380 [-6,099, +519] | 0 [0–29] → 0 [0–29] | 0% → 44% |
| 27b jsonR | 20.9 → 19.8 | 5,288 [4,713–10,000] → 4,107 [3,536–4,664] | -1,181 [-6,301, -771] | 29 [0–29] → 0 [0–0] | 47% → 59% |

*at the default decision (score ≥ 0.5 / JSON verdict)*

| config | machine h without → with | flagged without → with [CI] | Δ flagged [paired CI] | missed without → with [CI] | review avoided |
|---|---|---|---|---|---|
| 4b lp | 1.5 → 1.5 | 4,942 [4,358–5,481] → 4,865 [4,227–5,429] | -78 [-605, +412] | 100 [29–171] → 14 [0–43] | 51% → 51% |
| 9b lp | 2.6 → 2.5 | 4,118 [3,518–4,650] → 4,133 [3,547–4,651] | +15 [-518, +587] | 71 [14–143] → 71 [14–143] | 59% → 59% |
| 27b lp | 8.3 → 8.0 | 2,847 [2,357–3,376] → 2,151 [1,820–2,492] | -696 [-1,214, -231] | 214 [129–314] → 257 [157–371] | 72% → 78% |
| d3-4b | 3.1 → 5.3 | 5,351 [4,795–5,824] → 4,041 [3,388–4,531] | -1,310 [-1,971, -731] | 114 [43–200] → 0 [0–0] | 46% → 60% |
| d3-9b | 4.8 → 8.0 | 4,487 [3,931–4,991] → 3,878 [3,306–4,367] | -610 [-1,210, +44] | 29 [0–71] → 0 [0–0] | 55% → 61% |
| d3-27b | 15.5 → 25.8 | 3,292 [2,802–3,796] → 2,653 [2,245–3,061] | -639 [-1,196, -120] | 14 [0–43] → 0 [0–0] | 67% → 73% |
| Jev | 0.3 → 0.4 | 3,553 [2,971–4,100] → 3,316 [2,769–3,831] | -237 [-804, +292] | 243 [143–357] → 71 [14–129] | 64% → 67% |
| 4b json | 8.0 → 10.1 | 4,656 [4,095–5,160] → 4,185 [3,561–4,754] | -471 [-960, -39] | 171 [86–271] → 86 [29–157] | 53% → 58% |
| 9b json | 12.8 → 15.9 | 3,098 [2,565–3,620] → 3,504 [2,961–4,051] | +406 [+22, +829] | 371 [243–500] → 129 [57–214] | 69% → 65% |
| 27b json | 19.5 → 18.1 | 3,119 [2,595–3,640] → 2,447 [2,116–2,854] | -673 [-1,171, -223] | 157 [71–243] → 43 [0–87] | 69% → 76% |
| 4b jsonR | 8.5 → 10.8 | 3,696 [3,111–4,294] → 3,240 [2,673–3,812] | -456 [-1,146, +254] | 300 [200–429] → 214 [129–329] | 63% → 68% |
| 9b jsonR | 15.5 → 18.6 | 4,490 [3,861–5,077] → 4,443 [3,805–5,012] | -47 [-724, +589] | 144 [58–230] → 43 [0–100] | 55% → 56% |
| 27b jsonR | 20.9 → 19.8 | 2,952 [2,439–3,486] → 2,333 [1,992–2,712] | -620 [-1,082, -233] | 214 [129–314] → 157 [71–243] | 70% → 77% |

### B4.3 With the roster: every scenario at thr98

| config | p=5%, neg real | p=5%, neg mix | p=5%, neg hard | p=20%, neg real | p=20%, neg mix | p=20%, neg hard | p=50%, neg real | p=50%, neg mix | p=50%, neg hard | missed, p=5% | missed, p=20% | missed, p=50% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4b lp | 810 | 3,075 | 5,340 | 2,238 | 4,146 | 6,053 | 5,095 | 6,287 | 7,480 | 7 | 29 | 71 |
| 9b lp | 810 | 3,850 | 6,891 | 2,238 | 4,799 | 7,359 | 5,095 | 6,696 | 8,296 | 7 | 29 | 71 |
| 27b lp | 493 | 1,462 | 2,432 | 1,971 | 2,788 | 3,604 | 4,929 | 5,439 | 5,949 | 7 | 29 | 71 |
| d3-4b | 493 | 1,947 | 3,401 | 1,971 | 3,196 | 4,420 | 4,929 | 5,694 | 6,459 | 7 | 29 | 71 |
| d3-9b | 493 | 1,559 | 2,626 | 1,971 | 2,869 | 3,767 | 4,929 | 5,490 | 6,051 | 7 | 29 | 71 |
| d3-27b | 493 | 687 | 881 | 1,971 | 2,135 | 2,298 | 4,929 | 5,031 | 5,133 | 7 | 29 | 71 |
| Jev | 493 | 2,238 | 3,983 | 1,971 | 3,441 | 4,910 | 4,929 | 5,847 | 6,765 | 7 | 29 | 71 |
| 4b json | 7,467 | 8,539 | 9,612 | 7,867 | 8,770 | 9,673 | 8,667 | 9,231 | 9,796 | 0 | 0 | 0 |
| 9b json | 10,000 | 10,000 | 10,000 | 10,000 | 10,000 | 10,000 | 10,000 | 10,000 | 10,000 | 0 | 0 | 0 |
| 27b json | 1,767 | 5,011 | 8,255 | 3,067 | 5,799 | 8,531 | 5,667 | 7,374 | 9,082 | 0 | 0 | 0 |
| 4b jsonR | 10,000 | 10,000 | 10,000 | 10,000 | 10,000 | 10,000 | 10,000 | 10,000 | 10,000 | 0 | 0 | 0 |
| 9b jsonR | 1,925 | 4,799 | 7,673 | 3,200 | 5,620 | 8,041 | 5,750 | 7,263 | 8,776 | 0 | 0 | 0 |
| 27b jsonR | 658 | 3,003 | 5,347 | 2,133 | 4,107 | 6,082 | 5,083 | 6,317 | 7,551 | 0 | 0 | 0 |

What the 25-3152 tables show:

- **The roster cuts slip-through at thr98 for six of the seven score models.**
  - d3-27b: hard negatives 16/49 → 2/49.
  - 27b lp: 28/49 → 10/49.
  - d3-4b: real negatives 18/60 → 0/60.
  - The exception is 9b lp (hard 30/49 → 33/49).
- **Flagged per 10,000 in the plausible scenario (B4.2), without → with the roster:**

  | config | flagged | Δ [95% CI] |
  |---|---|---|
  | 27b lp | 4,257 → 2,788 | −1,469 [−2,812, −898] |
  | d3-27b | 3,278 → 2,135 | −1,143 [−1,647, −490] |
  | Jev | 5,517 → 3,441 | −2,076 [−4,182, −1,038] |
  | 4b lp | 7,808 → 4,146 | −3,663 [−5,277, −1,195] |
  | 9b lp | 4,620 → 4,799 | +178 [−741, +965] |
- **At the default cutoff with the roster, d3-4b, d3-9b and d3-27b keep 140/140 positives** (0 missed
  per 10,000). The 27b lp keeps 122/140 and misses 257 [157–371] per 10,000.
- **Interpretation:** a search scoped to named correspondents (their names or addresses) probably
  returns a higher responsive share than a topical search. At p = 50% with the roster (B4.3):
  - d3-27b flags 5,031 (mix); 27b lp flags 5,439.
  - Missed: 71 per 10,000 for every score model, at the 98% in-sample cutoff.

## B5. Takeaway

**Why this scenario is the plausible one (judgment, not measurement).** This repo has no sample of a
real keyword-hit population, so every value below is an assumption.

- **p = 20%.** CPRA keyword searches are deliberately broad. 24-409's refined scope, for instance, is a
  list of names and terms "in conjunction with" others over a seven-month window. Most hits are
  therefore not responsive. 20% sits between a broad search (5%) and a tight one (50%).
- **Negatives halfway between real and hard.**
  - The golden real negatives were produced for *other* requests. Most share neither topic nor people
    with this request, so most wouldn't be keyword hits at all; they are easier than real false hits.
  - The hard negatives are near-misses written to fool the screen. Real false hits include these
    patterns (a keyword in a signature or newsletter, a keyword in an unrelated sense, the same people
    on a different subject). But not every false hit is that hard, and the wrong-date recipe would
    usually be excluded by the search's date range.
  - Real hits probably fall between the two, so the midpoint is the working assumption.
- **Positives like all golden positives.** Close calls, privileged and exempt-category positives are
  real kinds of responsive records. The real-only sensitivity is B2.5.
- **Cutoff:** the in-sample thr98, with the default 0.5 alongside. Branch A's label-free,
  out-of-sample cutoffs may do worse.

### B5.1 Speed classes, main set

| config | machine h | speed class | flagged (thr98) | missed (thr98) | dominated by | best in class |
|---|---|---|---|---|---|---|
| Jev | 0.33 | under 1 h | 5,287 | 35 | — | yes |
| 4b lp | 1.68 | 1–5 h | 6,183 | 35 | Jev |  |
| 9b lp | 2.83 | 1–5 h | 4,637 | 35 | — | yes |
| d3-4b | 2.91 | 1–5 h | 6,081 | 35 | 9b lp, Jev |  |
| d3-9b | 4.54 | 1–5 h | 4,899 | 35 | 9b lp |  |
| 4b json | 7.91 | 5–10 h | 9,316 | 7 | — |  |
| 4b jsonR | 8.31 | 5–10 h | 10,000 | 0 | — |  |
| 27b lp | 8.93 | 5–10 h | 4,207 | 35 | — | yes |
| 9b json | 12.81 | over 10 h | 10,000 | 0 | 4b jsonR |  |
| d3-27b | 14.70 | over 10 h | 3,723 | 35 | — | yes |
| 9b jsonR | 14.80 | over 10 h | 10,000 | 0 | 9b json, 4b jsonR |  |
| 27b json | 19.98 | over 10 h | 8,043 | 0 | — |  |
| 27b jsonR | 20.75 | over 10 h | 5,019 | 14 | — |  |

### B5.2 Paired differences between the class winners and like-sized models

| first → second | cutoff | flagged | Δ flagged [paired CI] | Δ missed [paired CI] | Δ reviewer h @30/60 s | machine h |
|---|---|---|---|---|---|---|
| Jev → 9b lp | thr98 | 5,287 → 4,637 | -650 [-1,434, -99] | +0 [-14, +21] | -5.4 / -10.8 | 0.3 → 2.8 |
| Jev → 9b lp | default | 4,412 → 3,716 | -696 [-1,174, -237] | -7 [-77, +70] | -5.8 / -11.6 | 0.3 → 2.8 |
| Jev → 27b lp | thr98 | 5,287 → 4,207 | -1,081 [-2,174, -653] | +0 [-14, +21] | -9.0 / -18.0 | 0.3 → 8.9 |
| Jev → 27b lp | default | 4,412 → 2,694 | -1,718 [-2,149, -1,287] | +14 [-35, +70] | -14.3 / -28.6 | 0.3 → 8.9 |
| Jev → d3-27b | thr98 | 5,287 → 3,723 | -1,564 [-2,126, -1,049] | +0 [-14, +21] | -13.0 / -26.1 | 0.3 → 14.7 |
| Jev → d3-27b | default | 4,412 → 3,971 | -441 [-909, -14] | -120 [-176, -63] | -3.7 / -7.4 | 0.3 → 14.7 |
| 9b lp → 27b lp | thr98 | 4,637 → 4,207 | -430 [-1,543, +208] | +0 [-14, +14] | -3.6 / -7.2 | 2.8 → 8.9 |
| 9b lp → 27b lp | default | 3,716 → 2,694 | -1,021 [-1,412, -599] | +21 [-49, +92] | -8.5 / -17.0 | 2.8 → 8.9 |
| 9b lp → d3-27b | thr98 | 4,637 → 3,723 | -914 [-1,575, -104] | +0 [-14, +14] | -7.6 / -15.2 | 2.8 → 14.7 |
| 9b lp → d3-27b | default | 3,716 → 3,971 | +255 [-276, +781] | -113 [-162, -63] | +2.1 / +4.3 | 2.8 → 14.7 |
| 27b lp → d3-27b | thr98 | 4,207 → 3,723 | -484 [-842, +564] | +0 [-14, +14] | -4.0 / -8.1 | 8.9 → 14.7 |
| 27b lp → d3-27b | default | 2,694 → 3,971 | +1,277 [+865, +1,688] | -134 [-190, -77] | +10.6 / +21.3 | 8.9 → 14.7 |
| 4b lp → d3-4b | thr98 | 6,183 → 6,081 | -101 [-1,050, +1,441] | +0 [-14, +14] | -0.8 / -1.7 | 1.7 → 2.9 |
| 4b lp → d3-4b | default | 4,320 → 5,189 | +869 [+362, +1,329] | +21 [-35, +85] | +7.2 / +14.5 | 1.7 → 2.9 |
| 9b lp → d3-9b | thr98 | 4,637 → 4,899 | +262 [-710, +900] | +0 [-14, +14] | +2.2 / +4.4 | 2.8 → 4.5 |
| 9b lp → d3-9b | default | 3,716 → 3,876 | +160 [-272, +580] | -28 [-92, +35] | +1.3 / +2.7 | 2.8 → 4.5 |
| 4b lp → 9b lp | thr98 | 6,183 → 4,637 | -1,546 [-2,496, -65] | +0 [-14, +14] | -12.9 / -25.8 | 1.7 → 2.8 |
| 4b lp → 9b lp | default | 4,320 → 3,716 | -605 [-1,034, -207] | +21 [-28, +77] | -5.0 / -10.1 | 1.7 → 2.8 |
| 27b lp → 27b json | thr98 | 4,207 → 8,043 | +3,837 [+3,195, +4,891] | -35 [-35, -14] | +32.0 / +63.9 | 8.9 → 20.0 |
| 27b lp → 27b json | default | 2,694 → 3,167 | +473 [+178, +782] | -49 [-92, -14] | +3.9 / +7.9 | 8.9 → 20.0 |
| 27b lp → 27b jsonR | thr98 | 4,207 → 5,019 | +813 [+415, +2,002] | -21 [-35, +7] | +6.8 / +13.5 | 8.9 → 20.8 |
| 27b lp → 27b jsonR | default | 2,694 → 3,583 | +889 [+467, +1,311] | -35 [-85, +14] | +7.4 / +14.8 | 8.9 → 20.8 |

### B5.3 Takeaway table, main set (both requests)

| speed class | config | machine h | thr98: flagged [CI] | thr98: missed [CI] | thr98: reviewer h @30/60 s | thr98: flagged range, 9 scenarios | 0.5: flagged [CI] | 0.5: missed [CI] | 0.5: reviewer h @30/60 s |
|---|---|---|---|---|---|---|---|---|---|
| under 1 h | Jev | 0.3 | 5,287 [4,802–5,795] | 35 [14–35] | 44 / 88 | 1,283–8,648 | 4,412 [3,980–4,848] | 127 [70–183] | 37 / 74 |
| 1–5 h | 9b lp | 2.8 | 4,637 [4,009–5,147] | 35 [21–35] | 39 / 77 | 887–8,044 | 3,716 [3,278–4,090] | 120 [63–169] | 31 / 62 |
| 5–10 h | 27b lp | 8.9 | 4,207 [3,108–4,572] | 35 [21–35] | 35 / 70 | 491–7,714 | 2,694 [2,387–3,028] | 141 [85–197] | 22 / 45 |
| over 10 h | d3-27b | 14.7 | 3,723 [3,247–4,251] | 35 [14–35] | 31 / 62 | 491–7,110 | 3,971 [3,575–4,403] | 7 [0–21] | 33 / 66 |

**How to read it:**

- **Jev:** fastest by far (0.3 h), but it leaves 650 [99–1,434] more emails to read than 9b lp, and
  1,564 [1,049–2,126] more than d3-27b. It also sends the records to a third party.
- **9b lp:** the 1–5 h class winner (2.8 h). It is clearly ahead of 4b lp (−1,546 [−2,496, −65]
  flagged) but not separable from d3-9b, which flags +262 [−710, +900] more.
- **27b lp and d3-27b:** both are overnight-scale.
  - At thr98 their workloads can't be told apart: d3-27b flags 484 fewer, but the paired CI is
    [−842, +564].
  - d3-27b takes 14.7 h against 8.9 h.
  - At the default 0.5 they differ sharply. The 27b lp flags the fewest emails (2,694) but misses 141
    of 2,000 responsive ones. d3-27b misses 7 and flags 3,971.
  - So d3-27b gives high recall without a tuned threshold, which bears on branch A.
- **Within each size class**, stock lp and d3 aren't distinguishable at thr98 (all three paired CIs
  include zero), and d3 takes 1.60–1.73× as long (B1.8).

### B5.4–B5.6 The same for 25-3152 with the roster

*B5.4 Speed classes (machine hours from the roster runs)*

| config | machine h | speed class | flagged (thr98) | missed (thr98) | dominated by | best in class |
|---|---|---|---|---|---|---|
| Jev | 0.36 | under 1 h | 3,441 | 29 | — | yes |
| 4b lp | 1.50 | 1–5 h | 4,146 | 29 | Jev | yes |
| 9b lp | 2.55 | 1–5 h | 4,799 | 29 | 4b lp, Jev |  |
| d3-4b | 5.34 | 5–10 h | 3,196 | 29 | — |  |
| 27b lp | 7.97 | 5–10 h | 2,788 | 29 | — | yes |
| d3-9b | 8.00 | 5–10 h | 2,869 | 29 | 27b lp |  |
| 4b json | 10.11 | over 10 h | 8,770 | 0 | — |  |
| 4b jsonR | 10.83 | over 10 h | 10,000 | 0 | 4b json |  |
| 9b json | 15.91 | over 10 h | 10,000 | 0 | 4b json, 4b jsonR |  |
| 27b json | 18.13 | over 10 h | 5,799 | 0 | — |  |
| 9b jsonR | 18.59 | over 10 h | 5,620 | 0 | — |  |
| 27b jsonR | 19.77 | over 10 h | 4,107 | 0 | — |  |
| d3-27b | 25.78 | over 10 h | 2,135 | 29 | — | yes |

*B5.5 Paired differences*

| first → second | cutoff | flagged | Δ flagged [paired CI] | Δ missed [paired CI] | Δ reviewer h @30/60 s | machine h |
|---|---|---|---|---|---|---|
| Jev → 4b lp | thr98 | 3,441 → 4,146 | +705 [-141, +2,439] | +0 [-29, +29] | +5.9 / +11.7 | 0.4 → 1.5 |
| Jev → 4b lp | default | 3,316 → 4,865 | +1,548 [+786, +2,335] | -57 [-129, +0] | +12.9 / +25.8 | 0.4 → 1.5 |
| Jev → 27b lp | thr98 | 3,441 → 2,788 | -653 [-1,320, -135] | +0 [-29, +29] | -5.4 / -10.9 | 0.4 → 8.0 |
| Jev → 27b lp | default | 3,316 → 2,151 | -1,165 [-1,708, -633] | +186 [+86, +286] | -9.7 / -19.4 | 0.4 → 8.0 |
| Jev → d3-27b | thr98 | 3,441 → 2,135 | -1,306 [-1,892, -720] | +0 [-29, +29] | -10.9 / -21.8 | 0.4 → 25.8 |
| Jev → d3-27b | default | 3,316 → 2,653 | -663 [-1,206, -116] | -71 [-129, -14] | -5.5 / -11.1 | 0.4 → 25.8 |
| 4b lp → 27b lp | thr98 | 4,146 → 2,788 | -1,358 [-2,989, -653] | +0 [-29, +29] | -11.3 / -22.6 | 1.5 → 8.0 |
| 4b lp → 27b lp | default | 4,865 → 2,151 | -2,714 [-3,389, -2,114] | +243 [+143, +343] | -22.6 / -45.2 | 1.5 → 8.0 |
| 4b lp → d3-27b | thr98 | 4,146 → 2,135 | -2,011 [-3,582, -1,276] | +0 [-29, +29] | -16.8 / -33.5 | 1.5 → 25.8 |
| 4b lp → d3-27b | default | 4,865 → 2,653 | -2,212 [-2,917, -1,603] | -14 [-43, +0] | -18.4 / -36.9 | 1.5 → 25.8 |
| 27b lp → d3-27b | thr98 | 2,788 → 2,135 | -653 [-1,061, -163] | +0 [-29, +29] | -5.4 / -10.9 | 8.0 → 25.8 |
| 27b lp → d3-27b | default | 2,151 → 2,653 | +502 [+253, +829] | -257 [-371, -157] | +4.2 / +8.4 | 8.0 → 25.8 |
| 4b lp → d3-4b | thr98 | 4,146 → 3,196 | -950 [-2,631, -230] | +0 [-29, +29] | -7.9 / -15.8 | 1.5 → 5.3 |
| 4b lp → d3-4b | default | 4,865 → 4,041 | -824 [-1,506, -171] | -14 [-43, +0] | -6.9 / -13.7 | 1.5 → 5.3 |
| 9b lp → d3-9b | thr98 | 4,799 → 2,869 | -1,929 [-3,056, -898] | +0 [-29, +29] | -16.1 / -32.2 | 2.5 → 8.0 |
| 9b lp → d3-9b | default | 4,133 → 3,878 | -255 [-965, +465] | -71 [-143, -14] | -2.1 / -4.3 | 2.5 → 8.0 |
| 4b lp → 9b lp | thr98 | 4,146 → 4,799 | +653 [-807, +1,580] | +0 [-29, +29] | +5.4 / +10.9 | 1.5 → 2.5 |
| 4b lp → 9b lp | default | 4,865 → 4,133 | -732 [-1,288, -205] | +57 [+14, +114] | -6.1 / -12.2 | 1.5 → 2.5 |
| 27b lp → 27b json | thr98 | 2,788 → 5,799 | +3,011 [-327, +3,561] | -29 [-29, +0] | +25.1 / +50.2 | 8.0 → 18.1 |
| 27b lp → 27b json | default | 2,151 → 2,447 | +296 [+143, +502] | -214 [-314, -128] | +2.5 / +4.9 | 8.0 → 18.1 |
| 27b lp → 27b jsonR | thr98 | 2,788 → 4,107 | +1,320 [+733, +1,988] | -29 [-29, +0] | +11.0 / +22.0 | 8.0 → 19.8 |
| 27b lp → 27b jsonR | default | 2,151 → 2,333 | +182 [-116, +484] | -100 [-214, +14] | +1.5 / +3.0 | 8.0 → 19.8 |

*B5.6 Takeaway table, 25-3152 with the roster*

| speed class | config | machine h | thr98: flagged [CI] | thr98: missed [CI] | thr98: reviewer h @30/60 s | thr98: flagged range, 9 scenarios | 0.5: flagged [CI] | 0.5: missed [CI] | 0.5: reviewer h @30/60 s |
|---|---|---|---|---|---|---|---|---|---|
| under 1 h | Jev | 0.4 | 3,441 [2,802–4,094] | 29 [0–29] | 29 / 57 | 493–6,765 | 3,316 [2,769–3,831] | 71 [14–129] | 28 / 55 |
| 1–5 h | 4b lp | 1.5 | 4,146 [3,359–5,754] | 29 [0–29] | 35 / 69 | 810–7,480 | 4,865 [4,227–5,429] | 14 [0–43] | 41 / 81 |
| 5–10 h | 27b lp | 8.0 | 2,788 [2,298–3,196] | 29 [0–29] | 23 / 46 | 493–5,949 | 2,151 [1,820–2,492] | 257 [157–371] | 18 / 36 |
| over 10 h | d3-27b | 25.8 | 2,135 [1,971–2,380] | 29 [0–29] | 18 / 36 | 493–5,133 | 2,653 [2,245–3,061] | 0 [0–0] | 22 / 44 |

**With the roster:**

- **d3 moves ahead of stock Qwen:**
  - 9b lp → d3-9b: −1,929 [−3,056, −898] flagged;
  - 4b lp → d3-4b: −950 [−2,631, −230];
  - 27b lp → d3-27b: −653 [−1,061, −163].
- **But d3 pays for the roster on every call.** d3-27b needs 25.8 h per 10,000, against 8.0 h for the
  27b lp. d3-9b at 8.0 h flags about as many as the 27b lp (2,869 vs 2,788).
- **The small-model class winner flips to 4b lp** (4,146 flagged), but its lead over 9b lp (4,799) is
  inside the noise: 4b lp → 9b lp +653 [−807, +1,580].

## Findings

| # | finding | confidence | rests on |
|---|---|---|---|
| 1 | Single-stream on the Strix Halo, scoring 10,000 golden-like emails takes 1.68 h (4b lp), 2.83 h (9b lp), 8.93 h (27b lp), 2.91 / 4.54 / 14.70 h (d3-4b / 9b / 27b) and 0.33 h for Jev through its API. The JSON modes take 7.91–20.75 h. | high for this hardware, email-length mix and one run each | B1.1 |
| 2 | The stock-Qwen lp runs reuse the processed system prompt and request across consecutive calls, so the measured times are what a one-request batch gets. Appending a 1,330-token roster changed their median prefill by −2 to +12 ms, against +618 to +3,399 ms if it were reprocessed. d3 reprocesses it every call: measured +814 / +1,151 / +3,718 ms, expected +837 / +1,184 / +3,753 ms. | high | B1.3 |
| 3 | d3 takes 1.60–1.73× the machine time of the same-size stock lp (3.14–3.56× with the roster). This mixes at least four differences, no prefix reuse, Q8_0 vs Q4_K_M weights, num_batch 8192 vs default, and a different runner and endpoint, which these runs don't separate [corrected in verification]. | high (ratio); low (attribution) | B1.8 |
| 4 | Jev costs $0.93 per 10,000 golden-like emails ($1.54 with the roster) at $0.042 per million input tokens. Its time barely depends on prompt length. | high | B1.5, B1.6 |
| 5 | In the plausible scenario (p = 20%, negatives a 50/50 real/hard mix) at the in-sample 98%-recall cutoff, the score models leave 3,723 (d3-27b) to 6,183 (4b lp) of 10,000 hits for review: 38–63% of the reading avoided. About 35 of 2,000 responsive emails are missed by construction; 40–67 if positives behave like real positives only. | medium: rests on assumed p and negative mix, and on in-sample cutoffs | B2.3, B2.5 |
| 6 | What the negatives look like moves the workload more than the choice of model. For the 27b lp at p = 20%, flagged runs from 1,965 (real-like negatives) to 6,448 (hard-like). Across models at the mix it runs 3,723–6,183. | high as arithmetic on these rates; the real mix is unknown | B2.3 |
| 7 | At the default 0.5 cutoff, six of seven score models miss 92–141 of 2,000 responsive emails (p = 20%). d3-27b misses 7 [0–21] (283/284 recall) and flags 3,971, so its untuned default is already a high-recall cutoff. | medium: one 284-positive test set | B2.1, B2.4 |
| 8 | Reviewer time exceeds machine time for every configuration in the plausible scenario, JSON included. For the score models at 30 s per email, 31.0–51.5 h of reading against 0.3–14.7 h of scoring. The machine is the bottleneck only with few responsive hits and easy negatives (p = 5%, real-like) for three of the four 27B-class configurations (27b lp, d3-27b, 27b jsonR; 27b json's break-even is 13 s) [corrected in verification], where break-even is 55–108 s per email. | high in direction; magnitudes depend on the assumed reading speed | B3.1, B3.2 |
| 9 | Jev is the fastest and cheapest to run but leaves more to read. 9b lp flags 650 [99–1,434] fewer per 10,000 and d3-27b 1,564 [1,049–2,126] fewer (about 5.4 and 13.0 reviewer hours at 30 s). | medium | B5.2 |
| 10 | At thr98, stock lp and d3 of the same size aren't distinguishable on workload (all three paired CIs include zero), while d3 takes 1.60–1.73× as long. Between the two 27B options: d3-27b −484 [−842, +564] flagged, at 14.7 vs 8.9 machine hours. | medium | B5.2, B1.8 |
| 11 | For the correspondent-scoped request, the roster cuts the 98%-recall workload for six of seven score models (e.g. 27b lp 4,257 → 2,788; d3-27b 3,278 → 2,135), at no machine cost for stock lp but +2.26 to +10.33 h per 10,000 for d3. With the roster, d3-27b is the most accurate (2,135 flagged; −653 [−1,061, −163] vs 27b lp) and the slowest (25.8 h). | medium: 249 pairs, one request, in-sample cutoffs | B4.2, B5.5, B1.3 |
| 12 | The JSON modes aren't worth their machine time. Each is slower than the same model's lp: decoding alone costs 5.0–11.7 h per 10,000. At thr98 three of the six flag every email, and 27b json still flags 8,043 vs 4,207 for 27b lp in the plausible scenario. | high (time); medium (accuracy, see findings-golden §2 for the matched-rate comparison) | B1.4, B2.3, B5.2 |
| 13 | Among small local models, 9b lp beats 4b lp on workload (−1,546 [−2,496, −65] flagged), at 2.8 vs 1.7 machine hours. On these point estimates Jev dominates the 4b lp. | medium | B5.1, B5.2 |

## Caveats

- **The scenarios are constructed, not observed.** The responsive share and the makeup of real false
  hits are assumptions. The per-kind pass rates come mostly from synthetic emails: all hard negatives
  and all close-call, privileged and exempt positives.
- **thr98 is in-sample,** so misses at thr98 are ≤ 2% of golden positives by construction. Their
  bootstrap intervals can't show out-of-sample risk. Branch A's cutoffs, chosen without the target
  request's labels, may miss more or flag more.
- **Zero counts:** where a group has 0 flagged (e.g. 27b lp real negatives 0/120), the bootstrap
  interval is [0, 0]. The Wilson upper bound (3.1% for 0/120) is the better guide (B2.2).
- **One timing run per configuration,** single-stream, on one machine.
  - Parallel local requests and API concurrency weren't measured.
  - The 4b/9b JSON times include prefill a default-batch run might avoid (B1.4).
  - The d3 comparison mixes the cache effect with quantization, batch size and runner (B1.8)
    [corrected in verification].
- **Golden-like email lengths.** Real hits may be longer or shorter; B1.6 gives the per-token scaling,
  and the 8,000-character body cap bounds the worst case.
- **Jev:** times include the network from this location. Using it sends the records to a third party,
  the privacy cost this experiment exists to avoid.
- **Reviewer seconds per email are assumptions.** Flagged emails are the harder ones and may take
  longer than average. Exemption review of the responsive emails, needed in any case, isn't counted.
- **"Missed" counts only the screen's misses,** not human review errors.
- **Local hardware and electricity costs weren't measured.** "Unattended" machine hours still need the
  machine.
- **Labels and set construction:** labels are one adjudicator's calls. The real rows favor confident
  pre-labels (findings-golden §11). 25-3152 has 140 positives, so its 98% target allows 2 misses.
- **Speed-class boundaries (1, 5, 10 h) are a presentation choice.** The "best in class" picks are point
  estimates, and several aren't separable from the runner-up (B5.2, B5.5).

## Reproduce

From the project root (stdlib only, deterministic, no GPU or network):

| command | prints | time |
|---|---|---|
| `uv run python scripts/analysis/b_workload_time.py` | B1.1 and B1.2 (wall time and hours per 10,000, main and roster sets), B1.3 (prefix-cache test), B1.4 (JSON prefill and decode), B1.5 (Jev cost), B1.6 (per-token slope), B1.7 (warm-up row), B1.8 (lp vs d3) | < 1 s |
| `uv run python scripts/analysis/b_workload_review.py [--boot 1000]` | B2.1–B2.5, B3.1–B3.2, B4.1–B4.3, B5.1–B5.6 | ≈ 7 s |
| `uv run python scripts/analysis/b_workload_verify.py` | V0–V12 of the [Verification](#verification) section (independent; re-runs the two scripts above for V0) | ≈ 11 s |

The two analyst scripts import `scripts/analysis/b_workload_common.py`, which holds the run list, the label join
(`golden_report.load_runs`), the scenario formulas, the bootstrap and the constants: seed 20261106,
1,000 resamples, $0.042 per million Jev input tokens, 10,000 hits. The verification script
doesn't import it.

## Verification

A skeptic pass on 2026-11-06, by a second agent that didn't write the scripts above. Script:
`scripts/analysis/b_workload_verify.py`, deterministic, about 11 s. It doesn't import the `b_workload_*`
scripts. It reads the runs itself, joins label and kind from `data/golden/pairs.jsonl` itself, and
computes AUROC, thr98 and elim@98 from scratch. Those are cross-checked against `scripts/analyze.py`.
Its paired bootstrap is also its own: stratified by label (the analyst stratified by kind), seed 4242,
2,000 resamples. Every number in this section is pasted from that script's output (sections V0–V12).

### Checks and results

| # | check | result |
|---|---|---|
| 1 | Re-ran both analyst scripts and compared each table row in this file with their output (V0) | **Confirmed.** All 427 data rows and all headers of the script tables appear verbatim, in the same order. The five rows of the indented B4 summary match B4.2. The only script edits in this pass are prose lines (see Corrections); no table changed. |
| 2 | Labels from `pairs.jsonl`, not `scores.jsonl` (V1) | **Confirmed.** Done through `golden_report.load_runs`. In the 26 runs used, 0 rows carry a label or kind that differs from `pairs.jsonl` and 0 rows are missing from it, so here the rule changes nothing. The 5 null JSON rows are as stated. |
| 3 | Right runs and pairs (V1, V2, V8) | **Confirmed.** The 13 tags and their `_roster` twins are the brief's. Each roster run holds only 25-3152, with the same 249 pair_ids as the main runs' 25-3152 rows. All local runs: Ollama 0.40.13, concurrency 1, rows in (request, email) order with one request switch, 0 retries, 0 reloads. |
| 4 | Core metrics from scratch (V5) | **Confirmed.** For all seven score models, AUROC, thr98 and elim@98 equal `analyze.py` exactly and match the brief's headline numbers. Nothing conflicts with the headline numbers. |
| 5 | Threshold direction and ties (V4, V5) | **Confirmed.** Flagged = score ≥ threshold throughout. thr98 is the k-th highest positive score (k = 279 of 284; 138 of 140 on 25-3152). Jev has 94 distinct score values; 1 pair sits exactly on its thr98 (0.34) and is flagged. Ties move no number. |
| 6 | Per-kind counts and the plausible scenario (V6) | **Confirmed.** Recomputed for the seven score models at both cutoffs: every count in B2.1, and every p = 20% flagged, missed, review-avoided and reviewer-hour figure in B2.3, B2.4 and B3.1. |
| 7 | Machine time and cost (V3, V4, V9) | **Confirmed.** Mean, median, p90 and hours per 10,000; Jev tokens and cost; the same-pair roster deltas. They reproduce B1.1–B1.3 and B1.5. |
| 8 | Roster numbers (V8) | **Confirmed.** With and without the roster, the thresholds re-chosen on the 249 pairs, the per-kind counts and the plausible-scenario flagged numbers match B4.1/B4.2. |
| 9 | Intervals computed rather than asserted (V10) | **Confirmed.** The independent bootstrap gives paired 95% intervals close to those in B5.2, B5.5 and B4.2 (compare the V10 tables below with them). One difference matters: 4b lp → 9b lp ends at +0 here, against −65 in B5.2 (see concern 3). |
| 10 | JSON thr98 = 0 (V5) | **Confirmed.** 9b json, 4b jsonR and 9b jsonR have 40, 18 and 10 positives scored exactly 0 (verdict "no" at confidence 1). That is more than the 5 misses 98% recall allows, so the cutoff must fall to 0 and flag everything. |
| 11 | "The d3 models use noncausal attention, so they can't reuse the prefix" (V2, V11) | **Unverifiable from these runs.** d3 does reprocess the prefix (B1.3). But the d3 runs also used num_batch 8192, and at num_batch 8192 the *stock* 4b/9b lp runs reprocess it too. See concern 1. |
| 12 | "Output not billed" (Jev) (V4) | **Refuted as unsupported.** Nothing in the repo states it, and Jev reports 20 output tokens per call. Corrected. |
| 13 | B1.7: "one untimed warm-up call" (V12) | **Corrected.** The lp runs also made a canary call after every 100 rows that overlaps the next timed row. |
| 14 | B1.8: "two differences" between d3 and stock lp (V2) | **Corrected.** There are at least four: prefix reuse, Q8_0 vs Q4_K_M, num_batch 8192 vs default, and the llamacpp runner through `/v1/systemone` vs ggml through `/api/chat`. |
| 15 | Finding 8: "for the 27B-class models" | **Corrected.** Three of the four 27B-class configurations; 27b json's break-even at p = 5%, real-like negatives is 13 s (B3.2). |
| 16 | "Clearly", "beats" and "leaves more to read" claims in B5 (V10) | **Plausible but overstated.** Concern 3. |

V5 (from-scratch metrics vs the repo helpers and the brief):

| config | AUROC (mine) | AUROC (analyze.auroc) | brief | thr98 (mine) | thr98 (at_recall) | elim@98 (mine) | brief | agree |
|---|---|---|---|---|---|---|---|---|
| 4b lp | 0.9228 | 0.9228 | 0.923 | 0.2650 | 0.2650 | 109/211 = 51.7% | 52% | ok |
| 9b lp | 0.9424 | 0.9424 | 0.942 | 0.3309 | 0.3309 | 149/211 = 70.6% | 71% | ok |
| 27b lp | 0.9754 | 0.9754 | 0.975 | 0.0687 | 0.0687 | 160/211 = 75.8% | 76% | ok |
| d3-4b | 0.8842 | 0.8842 | 0.884 | 0.3507 | 0.3507 | 113/211 = 53.6% | 54% | ok |
| d3-9b | 0.9470 | 0.9470 | 0.947 | 0.3379 | 0.3379 | 144/211 = 68.2% | 68% | ok |
| d3-27b | 0.9795 | 0.9795 | 0.979 | 0.5857 | 0.5857 | 171/211 = 81.0% | 81% | ok |
| Jev | 0.9164 | 0.9164 | 0.916 | 0.3400 | 0.3400 | 133/211 = 63.0% | 63% | ok |

### Corrections made in this file

Each is marked "[corrected in verification]" where it appears.

1. **Short answer:** the 31.0–51.5 h reviewer range covers the seven score models only. The JSON
   modes need 41.8–83.3 h (B3.1). The scope is now stated.
2. **B1.5 (Jev cost):** removed "output not billed" and said the $0.93 / $1.54 figures are the
   input-token cost only.
3. **B1.7:** the description of the untimed calls now includes the lp runs' canary calls.
4. **B1.8, Finding 3 and the d3 caveat:** "two differences" is now "at least four", per the run configs
   (V2).
5. **Finding 8:** "the 27B-class models" is now "three of the four 27B-class configurations".
6. **B1.3:** a verification note (not a correction) on the num_batch confound; see concern 1.

**Script edits:** three printed lead-in lines in `b_workload_time.py` (B1.5 price, B1.7 warm-up, B1.8
differences) and one comment in `b_workload_common.py`. No computed value changed: both scripts were
re-run and every table is identical.

### Remaining concerns

**1. These runs don't show why d3 reprocesses the prefix.** All d3 runs used num_batch 8192 (V2). At that
setting, the stock 4b/9b lp runs (same Ollama build) reprocess the roster just as d3 does. At the default
batch they reuse it. The num_batch 8192 runs below come from outside the main tables and are used only
for this mechanism test:

| model | run | num_batch | ollama | pairs | median Δprefill ms (roster − none) | median Δwall ms |
|---|---|---|---|---|---|---|
| 4b lp | default batch (main run) | default | 0.40.13 | 249 | +7 | +10 |
| 4b lp | num_batch 8192 | 8192 | 0.40.13 | 249 | +855 | +847 |
| 9b lp | default batch (main run) | default | 0.40.13 | 249 | -2 | -13 |
| 9b lp | num_batch 8192 | 8192 | 0.40.13 | 249 | +1,222 | +1,216 |

Noncausal attention may still be the reason d3 can't reuse the prefix. Until a default-batch d3 run
exists, though, the d3 roster penalty (+2.26 to +10.33 h per 10,000) and part of the 1.60–1.73× gap are
measured *for this setting*, not shown to be inherent to d3. This supports the B1.4 reading for the JSON
runs: the batch setting, not the JSON mode, stops reuse.

**2. "35 missed per 10,000" averages over two requests; a single request can see about twice that.** A
10,000-hit batch belongs to one request. At the pooled in-sample thr98, the misses aren't spread evenly
(V7):

| config | pooled thr98 | 24-409 | 25-3152 |
|---|---|---|---|
| 4b lp | 0.2650 | 2/144 missed (recall 98.6%); 28 missed per 10,000 at p = 20% | 3/140 missed (recall 97.9%); 43 missed per 10,000 at p = 20% |
| 9b lp | 0.3309 | 5/144 missed (recall 96.5%); 69 missed per 10,000 at p = 20% | 0/140 missed (recall 100.0%); 0 missed per 10,000 at p = 20% |
| 27b lp | 0.0687 | 0/144 missed (recall 100.0%); 0 missed per 10,000 at p = 20% | 5/140 missed (recall 96.4%); 71 missed per 10,000 at p = 20% |
| d3-4b | 0.3507 | 3/144 missed (recall 97.9%); 42 missed per 10,000 at p = 20% | 2/140 missed (recall 98.6%); 29 missed per 10,000 at p = 20% |
| d3-9b | 0.3379 | 4/144 missed (recall 97.2%); 56 missed per 10,000 at p = 20% | 1/140 missed (recall 99.3%); 14 missed per 10,000 at p = 20% |
| d3-27b | 0.5857 | 0/144 missed (recall 100.0%); 0 missed per 10,000 at p = 20% | 5/140 missed (recall 96.4%); 71 missed per 10,000 at p = 20% |
| Jev | 0.3400 | 0/144 missed (recall 100.0%); 0 missed per 10,000 at p = 20% | 5/140 missed (recall 96.4%); 71 missed per 10,000 at p = 20% |

Three of the four takeaway configurations (27b lp, d3-27b, Jev) put all 5 of their misses in 25-3152.
The fourth, 9b lp, puts all 5 in 24-409. So even in-sample, one cutoff for both requests gives one
request about 70 misses per 10,000 at p = 20%. B4 tunes on 25-3152's own labels and gets back to 2/140,
but that needs labels for the request at hand. This adds to branch A's out-of-sample caveat. It doesn't
contradict any number in B2, which describes the pooled positive mix.

**3. Several comparisons between class winners don't survive the number of comparisons made.** B5.2
makes 11 thr98 comparisons on the main set (22 with the default cutoff), and the winners were picked on
the same data. An independent bootstrap with a Bonferroni-style interval (1 − 0.05/11) gives (V10):

| first → second | Δ flagged (point) | 95% CI (mine) | Bonferroni CI (k=11) | share of resamples with Δ ≥ 0 |
|---|---|---|---|---|
| Jev → 9b lp | -650 | [-1,490, -25] | [-1,795, +354] | 0.022 |
| Jev → 27b lp | -1,081 | [-2,173, -683] | [-2,595, -417] | 0.001 |
| Jev → d3-27b | -1,564 | [-2,147, -1,037] | [-2,412, -796] | 0.000 |
| 9b lp → 27b lp | -430 | [-1,588, +264] | [-1,994, +743] | 0.093 |
| 9b lp → d3-27b | -914 | [-1,573, -53] | [-1,923, +318] | 0.019 |
| 27b lp → d3-27b | -484 | [-867, +523] | [-1,086, +917] | 0.231 |
| 4b lp → d3-4b | -101 | [-1,058, +1,436] | [-1,466, +2,001] | 0.440 |
| 9b lp → d3-9b | +262 | [-604, +924] | [-943, +1,193] | 0.758 |
| 4b lp → 9b lp | -1,546 | [-2,516, +0] | [-3,211, +304] | 0.025 |

- **Robust:** Jev flags more than 27b lp and d3-27b.
- **Suggestive only:** "9b lp is clearly ahead of 4b lp" (B5.3, Finding 13, and the summary's "9b lp
  clearly beats 4b lp"), and Jev → 9b lp (Finding 9). My 95% interval for 4b lp → 9b lp reaches +0, and
  2.5% of resamples show no gain.
- **On 25-3152 with the roster** (V10, second and third tables), these hold under the same correction:
  27b lp → d3-27b (−653), Jev → d3-27b, 9b lp → d3-9b, and both without → with deltas. 4b lp → d3-4b
  (−950) does not.

**4. Machine-hour intervals are too narrow for comparing runs.** They cover only which emails were
sampled.

- **Run-to-run noise:** on the same 249 emails, the roster runs of the stock lp models were 2.4–3.8%
  *faster* on average than the main runs, though the roster can only add work (V9). That is noise
  between runs, so time differences of a few percent in B1 are not meaningful.
- **Which request:** hours per 10,000 also depend on the request's emails. 27b lp takes 9.60 h on
  24-409 and 8.28 h on 25-3152; d3-27b takes 13.94 h and 15.45 h (V3).

**5. The lp timings include a small canary artifact.** `score.py` re-scores the first pair after every
100 rows. It does this from the main thread while the worker thread is already timing the next row,
because `ThreadPoolExecutor.map` submits every row up front. The overlapped row waits. Measured as
server time outside prefill and decode (V12), this adds 0.7–1.6% to the lp means: at most 0.12 h per
10,000 (27b lp, roster). It slightly favours d3 and Jev, which have no canary, and changes no conclusion.

**6. Jev's cost covers input tokens only.** The API reports 20 output tokens per call (V4), and their
price isn't in the repo.

**7. The review count is a floor in one respect.** A screen defended on recall usually needs a human
check of a sample of the emails it discards, to estimate how many responsive ones it dropped. B3
counts no such sample. (Interpretation.)

**8. One point in d3-27b's favour.** The 0.5 cutoff is the only cutoff in branch B not set from these
labels. d3-27b's 283/284 there (Wilson 98.0%–99.9%, B2.2) is the nearest thing in this branch to an
out-of-sample recall figure. It still rests on one set with 284 positives.

**What stands:** every table, every machine-time figure, the Jev cost (input-only) and the
scenario arithmetic. Also the direction of the main conclusions: reviewer time dominates machine time in
the plausible scenario, the negative mix moves workload more than model choice, JSON modes cost more
machine time for no workload gain at thr98, and the roster helps 6 of 7 score models on 25-3152.
