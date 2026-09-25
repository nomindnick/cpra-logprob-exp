# Model sweep — five local models, same data, same prompt

**Date:** 2026-09-25 · **Status:** preliminary; raw (unadjudicated) labels
**Runs:** `runs/*_ctx8k*/metrics.json` (full set), `runs/*_lat*/` (500-pair latency subset)

Same setup as `findings-run1.md`: 9,848 (request, email) pairs from four San Diego County
productions, first-token yes/no logprobs via Ollama 0.32.14, `num_ctx=8192`, thinking off,
temperature 0. Quality runs used concurrency 4 for Qwen and single-stream for Gemma (see §4).
Latency is from the fixed 500-pair subset, single-stream, median per call.

## 1. Results

| model | params | AUROC | AUPRC | eliminated @95% recall | @98% | @99% | ms/email (median) | prefill tok/s |
|---|---|---|---|---|---|---|---|---|
| gemma4:e2b | ~2B eff. | 0.803 | 0.61 | 35% | 20% | 6% | **699** | 3,550 |
| gemma4:e4b | ~4B eff. | 0.923 | 0.84 | 63% | 42% | 33% | 862 | 2,490 |
| qwen3.5:4b | 4.7B | 0.931 | 0.88 | 57% | 40% | 19% | 973 | 2,060 |
| **qwen3.5:9b** | 9B | **0.963** | **0.93** | **80%** | **54%** | 26% | 1,452 | 1,260 |
| gemma4:12b | 12B | 0.917 | 0.82 | 72% | 49% | 0%* | 2,127 | 880 |

\* gemma4:12b's 99% threshold is 0.000 — see §3.

All Q4_K_M. Latency scales with parameter count, roughly 90–100 ms per billion
parameters per 1,500-token email on this iGPU. Every model has recall ≥ 0.95 on
every request at its 98% threshold; the differences are entirely in how much
non-responsive material each one clears.

**Per-request pattern is the same for every model:** 24-409 (UCSD/Geosyntec) and
25-4697 (Harmony Grove) screen well (60–80% eliminated); 25-3152 (Alpine CPG,
correspondent-scoped) is the recall floor at ~0.95 and eliminates only 14–40%;
25-5982 (garbled keyword request) eliminates 5–50% depending on model. The
label/prompt issues identified in `findings-run1.md` are model-independent.

## 2. How small is good enough (H2)

- **2B is not enough.** gemma4:e2b ranks poorly (AUROC 0.80) and never says yes
  with confidence — its positive median is 0.000.
- **4B is the floor for a useful screener.** Both 4B-class models land at AUROC 0.92–0.93
  and ~40% eliminated at 98% recall.
- **9B clears H2.** qwen3.5:9b eliminates 54% at 98% recall and 80% at 95%, at 1.45 s
  per email single-stream (~0.9 s at concurrency 4).
- **Bigger is not automatically better.** gemma4:12b ranks *worse* than gemma4:e4b
  (AUROC 0.917 vs 0.923) and much worse than qwen3.5:9b, at 2.5× the latency.
  Architecture and training matter more than size in this range.

## 3. Score quality, not just ranking (H3)

AUROC hides a large difference. Reliability tables (score bucket → observed positive rate):

| bucket | .0–.1 | .1–.2 | .2–.3 | .3–.4 | .4–.5 | .5–.6 | .6–.7 | .7–.8 | .8–.9 | .9–1 |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.5:9b | .02 | .13 | .31 | .52 | .60 | .78 | .89 | .95 | .97 | 1.00 |
| qwen3.5:4b | .02 | .07 | .14 | .26 | .47 | .68 | .82 | .94 | .996 | 1.00 |
| gemma4:e4b | .04 | .22 | .33 | .34 | .41 | .37 | .44 | .43 | .53 | .83 |
| gemma4:12b | .10 | .36 | .40 | .50 | .46 | .43 | .37 | .43 | .36 | .86 |

**Qwen scores are monotonic** — a higher score always means a higher chance of
being responsive, across every decile. **Gemma scores are bimodal and the middle
is meaningless:** gemma4:12b puts 66% of all pairs below 0.001 and 16% above 0.9,
and between 0.3 and 0.9 the positive rate is flat at ~0.4 regardless of score.
Its 0.9–1.0 bucket is only 86% positive. For a screening tool that works by
threshold, this is the difference between a score you can set a policy on and
one you can't. Qwen's per-request thresholds (0.03–0.13) are also usable
numbers; Gemma's are 0.000–0.007.

Both Qwen models also keep a small residual (~0.0005) on non-yes/no tokens; Gemma
puts literally zero mass elsewhere, which is consistent with a sharper, less
calibrated head.

## 4. Backend finding: Gemma 4 on Ollama silently corrupts

The first Gemma runs were unusable and had to be redone. On this Ollama build
(0.32.14, Vulkan, Strix Halo), the Gemma 4 models enter a state where the
first-token distribution becomes `<unused49>` with uniform logprobs, and stay
there until the model is unloaded. Not caused by concurrency or prompt length;
a freshly loaded model is clean. The 12b full run produced 9,842 garbage rows
of 9,848; runs that began with a Gemma model already loaded were ~100% garbage.

Worse: rows scored during a corrupted stretch that *looked* valid were not —
5.1% of gemma4:e4b's "valid" rows differed by >0.3 from a clean rescore.

Mitigation now in `scripts/score.py`: retry after unloading on any undefined
score, and every 100 calls rescore a fixed canary pair and unload on drift.
Reruns needed 3 (e2b), 123 (e4b) and 272 (12b) reloads to get 9,848 clean rows
each. Qwen 3.5 never triggered it (0 invalid rows across ~20k calls).

**Practical implication:** a screening pipeline needs a canary. Without one, this
failure produces confident-looking output for hours.

## 5. Concurrency changes individual scores on long emails

Same 500 pairs, qwen3.5:4b, concurrency 4 vs single-stream: AUROC 0.944 vs 0.942,
but 44 pairs moved by >0.1 and 5 by >0.3 (max 0.62). The moved pairs are long
(median 2,800 tokens vs 1,565; 45% truncated) and mid-scored. Batched prefill
splits long prompts into different micro-batches and the 4-bit numerics diverge
near the decision boundary. Ranking metrics are unaffected; a fixed production
threshold applied to long emails is not. Report thresholds from single-stream runs.

## 6. Hypothesis status

| | status |
|---|---|
| H1 latency ≫ JSON generation | supported (decode is 0 of 0.7–2.1 s per email) |
| H2 ≥98% recall with >50% eliminated | **met by qwen3.5:9b** (54%) on raw labels; not by any 4B model (40–42%) |
| H3 score tracks error rate | supported for Qwen; **fails for Gemma** despite similar AUROC |
| H4 reranker baseline | not run |
| H5 quantization | not run (all Q4_K_M) |
| H6 hardware | Strix Halo only so far |

## 7. Next

1. Human adjudication (`docs/spotcheck-qwen3.5-4b.md`) → corrected-label recall.
2. Prompt revision for correspondent-scoped requests; ablation with a member list for 25-3152.
3. Backend comparison: qwen3.5:9b through llama-server and vLLM on the latency subset.
4. CPU laptop: qwen3.5:4b and gemma4:e4b on the latency subset (H6).
5. Optional: Q8 variants of qwen3.5:9b (H5); a current reranker (H4).
