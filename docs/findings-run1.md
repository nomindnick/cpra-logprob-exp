# Preliminary findings — first full run (qwen3.5:4b)

**Date:** 2026-09-22 · **Status:** preliminary, one model, labels not yet adjudicated
**Run:** `runs/qwen3.5_4b/` (metrics.json, metrics.dedupe.json; scores.jsonl kept local)

## Setup

- **Data:** 2,462 real produced emails from four County of San Diego CPRA requests
  (`docs/sources.md`, `data/dataset/summary.json`), paired with every request →
  9,848 (request, email) pairs: 2,462 positives (produced for that request),
  7,386 cross-request negatives (produced for a different request).
- **Model:** `qwen3.5:4b` (Q4_K_M) via Ollama 0.32.14, thinking off, temperature 0,
  `num_predict=1`, score = P(yes)/(P(yes)+P(no)) over first-token variants.
- **Prompt:** system + request text + email (headers, attachment names, body capped at
  8,000 chars) + "Is this email responsive? Answer yes or no." (`scripts/score.py`)
- **Hardware:** Strix Halo, 128 GB unified, Radeon 8060S iGPU. Single-stream, no batching.

## Latency (H1, H6)

| | value |
|---|---|
| wall per pair | **968 ms** (median total 833, p90 1,722) |
| prefill | median 614 ms at ~2,400 tok/s |
| decode | 0 ms (one token) |
| prompt length | median 1,560 tokens; 13% of emails truncated at 8k chars |
| full run | 9,848 pairs in 159 min |

Latency is linear in prompt length: ~510 ms under 1k tokens, ~770 ms at 1–2k,
~1.4 s at 2–3k, ~1.8 s at 3–4k. Roughly 200 ms per call is fixed Ollama overhead.
Real emails are ~6× longer than the phase 1 spike's toy emails, which is why this
is ~1 s rather than ~350 ms. The 2025 JSON-generation approach on the same
model would add ~1–1.4 s of decode per email (spike measurement).

## Screening quality (H2, H3)

AUROC **0.933**, AUPRC **0.883**. Residual mass outside yes/no: median 0.0007.

| recall target | threshold | precision | non-responsive eliminated |
|---|---|---|---|
| 95% | 0.132 | 0.44 | **60%** |
| 98% | 0.065 | 0.34 | **35%** |
| 99% | 0.043 | 0.29 | 20% |
| 100% | 0.015 | 0.25 | 2% |
| fixed 0.5 | — | 0.89 | 97% — but recall only 72% |

Deduplicating the 102 emails that appear in multiple mailboxes changes nothing
material (AUROC 0.935).

**Reliability** — score decile vs. observed positive rate — is strictly monotonic:

| score | 0.0–.1 | .1–.2 | .2–.3 | .3–.4 | .4–.5 | .5–.6 | .6–.7 | .7–.8 | .8–.9 | .9–1 |
|---|---|---|---|---|---|---|---|---|---|---|
| n | 3,850 | 1,891 | 1,189 | 578 | 350 | 363 | 390 | 548 | 556 | 133 |
| positive rate | .02 | .07 | .14 | .26 | .47 | .68 | .82 | .94 | .996 | 1.00 |

The raw P(yes) is not calibrated (it over-states at the low end and the model
rarely goes above 0.9), but the ordering is reliable: H3 holds.

**H2 (>50% eliminated at 98% recall) is not met on raw labels** — 35%. The
per-request breakdown and spot check below suggest much of the gap is in the
labels and the prompt, not the model.

## Per request (threshold for 98% overall recall = 0.065)

| request | topic | positives | recall | median pos score | negatives | eliminated |
|---|---|---|---|---|---|---|
| 24-409 | UCSD / Geosyntec water report | 1,204 | 0.995 | 0.72 | 1,258 | 56% |
| 25-3152 | Alpine Community Planning Group | 922 | **0.954** | 0.63 | 1,540 | 38% |
| 25-4697 | Harmony Grove Village South | 207 | 0.995 | 0.56 | 2,255 | 52% |
| 25-5982 | CAIR / Gaza custodian search | 129 | 1.000 | 0.80 | 2,333 | **6%** |

## What the spot check found (`docs/spotcheck-qwen3.5-4b.md`)

The 50 lowest-scoring positives and 50 highest-scoring negatives, read by hand.
Four things, none of which is simply "the model missed":

1. **Correspondent-scoped requests.** 25-3152 asks for *all communications between
   any Alpine CPG member and* other members / any agency / any member of the public.
   Responsiveness is defined by who is talking, not what about. The production
   therefore includes an SDG&E wildfire-fair notice, an Arthritis Foundation ride
   recap, a password reset, "RE: hi", and auto-replies — plausibly all responsive
   under the request's own terms, all scored ~0.02 because the model judges topic.
   The model cannot know who is a CPG member from the email. This is information the
   request assumes and the prompt does not supply, and it accounts for most of the
   recall tail.
2. **Missing request text.** 25-4697's portal text is "Please see the attached Public
   Records Act request." The attachment is not retrievable from the API. The model
   scored 207 emails against a request that never says what it wants and still
   reached 99.5% recall from the requester's follow-up message and subject lines —
   with the lowest positive median (0.56) of the four, which now makes sense.
3. **A garbled request hurts the screener.** 25-5982 is custodians + keywords
   ("CAIR, KARAMA, MAJDAL, GAZA") with typos. Recall is 100% but only 6% of negatives
   are eliminated: UCSD water-equity emails score 0.84 against it. A regex would
   handle this request perfectly; the model reads the garbled text as broad.
4. **Adjacency works as designed.** The highest-scoring negatives for the Alpine
   request are Harmony Grove emails from a Sheriff's deputy (0.77) — land use,
   county, community group, different community. Hard, and probably still negatives.

Also: 32 positives have empty bodies (attachment-only emails); they score ~0.59
on headers alone.

## Hypothesis status after one model

| | status |
|---|---|
| H1 latency ≫ JSON generation | supported (spike: 4.6×; full run: decode is 0 of ~970 ms) |
| H2 ≥98% recall with >50% eliminated | **not met** on raw labels (35%); label/prompt issues identified |
| H3 score tracks error rate | **supported** — monotonic reliability across all deciles |
| H4 reranker baseline | not run |
| H5 quantization | not run |
| H6 hardware | Strix Halo only so far |

## Caveats

- One model, one prompt, no adjudicated labels. The recall figures treat every
  produced email as responsive, which the spot check shows is not exactly true
  in either direction.
- Negatives are cross-request only; no synthetic hard negatives yet. Precision
  is therefore a "theoretical" number (SPEC §6).
- Single-stream latency; batched throughput not yet measured.
- 25-4697's real request text is unknown to us; its numbers are against a
  placeholder.

## Next

1. Human adjudication of the spot-check sheet → recompute recall on corrected labels.
2. Prompt revision: responsiveness follows the request's own criteria (correspondents,
   custodians, date ranges), not topic alone. Ablation: supply a custodian/member
   list for 25-3152; clean up 25-5982's text.
3. Model sweep (quality on full set, latency on a fixed 500-pair single-stream subset):
   `gemma4:e2b`, `gemma4:e4b`, `granite4.1:3b`, `qwen3.5:9b`, `gemma4:12b`.
4. Backend comparison (llama-server, vLLM) and concurrency for throughput.
