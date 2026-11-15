# Layer looping — repeating middle layers of stock Qwen3.5-4B and -9B

**Date:** 2026-11-14 · **Status:** complete. A side experiment: nothing in `docs/findings-golden.md` depends on it.
**Runs:** `loop/runs/` (scores committed; they carry no email text)
**Report:** `python3 loop/sweep_report.py` prints the §4 tables and `python3 loop/sweep_report.py --name sweep9b` the §5 tables; the §2 table comes from `loop/compare_runs.py` (commands in §8)

**Question.** Does running some of a model's layers twice improve first-token yes/no screening on the golden
set, and what does it cost in time?

**Answer.** The time cost is the share of layers repeated: about 5% for two layers and 12% for four. The
accuracy gain is not dependable. On the 4B, repeating layers 12–15 or 14–15 raised AUROC by 0.012 to 0.016 on
the held-out request, with confidence intervals that include zero. On the 9B the same two blocks, fixed in
advance, changed AUROC by +0.003 over all 496 pairs and lowered elimination at 98% recall. For comparison,
moving from the 4B to the 9B raised AUROC by 0.029 for 1.6 times the time.

## 1. What "looping" means here

Two different things are called looped transformers.

- **Models trained to loop.** One block of weights is reused several times by design, and training teaches the
  block to read its own output. ByteDance's Ouro models are built this way (<https://arxiv.org/abs/2510.25741>),
  and <https://arxiv.org/abs/2511.07384> retrofits a loop into a pretrained model by further training. Not
  tested here.
- **A stock model looped at inference.** No training: a block of consecutive layers is simply run twice in a
  row. This is the idea in David Noel Ng's "RYS" posts (<https://dnhkng.github.io/posts/rys-ii>), which report
  gains on math and emotional-intelligence probes from repeating mid-stack blocks of Qwen3.5-27B. This is what
  was tested.

Notation: `a:b` means layers a to b−1 run twice, so `12:16` is layers 12, 13, 14 and 15. Every block in this
experiment gets exactly one extra pass. Both models have 32 layers in eight groups of four: three
linear-attention layers followed by one full-attention layer (full attention at layers 3, 7, …, 31). The 9B is
wider (hidden size 4096 against 2560), not deeper, so the same blocks apply to both.

## 2. Harness, and how closely it matches the Ollama runs

Ollama cannot reorder layers, so `loop/score_hf.py` scores through PyTorch (torch 2.14.1+rocm7.2, transformers
5.23.0, Radeon 8060S). It imports the prompt, the email rendering and the yes/no token sets from
`scripts/score.py`, so the inputs are the same by construction: prompt 2, render 2, and the token count equals
Ollama's on all 496 pairs for both models. Looping is done by pointing the model's layer list at the same
modules twice; no weights are copied.

Three differences from the Ollama runs:

- **Weights** are the published bf16 checkpoints (`Qwen/Qwen3.5-4B`, `Qwen/Qwen3.5-9B`, revisions in
  `loop/score_hf.py`), not the Q4_K_M quantizations.
- **The output head runs in float32.** bf16 logits of the size seen here (20 to 30) move in steps of 0.125,
  which collapses the scores onto a few dozen values. The layers themselves stay in bf16.
- **Times are not comparable with Ollama's.** There is no prefix cache, and the linear-attention layers run on
  the reference PyTorch implementation. Times here compare only with each other.

Stock layer order, PyTorch against Ollama (`(ref)` rows), all 496 pairs:

| run | n | layer passes | AUROC [95% CI] | eliminated @98% recall [95% CI] | recall / eliminated at 0.5 | 24-409: AUROC · elim@98 | 25-3152: AUROC · elim@98 | median ms | ms ÷ first run |
|---|---|---|---|---|---|---|---|---|---|
| qwen3.5_4b_base | 496 | 32 | 0.920 [0.894–0.944] | 64% [50%–72%] | 93% / 75% | 0.952 · 79% | 0.899 · 50% | 1244 | 1.00× |
| golden_qwen3.5_4b_logprob_p2db (ref) | 496 |  | 0.922 [0.896–0.946] | 53% [42%–70%] | 94% / 74% | 0.961 · 72% | 0.885 · 30% | 504 | n/a (Ollama, prefix cache) |
| qwen3.5_9b_base | 496 | 32 | 0.949 [0.928–0.967] | 76% [67%–83%] | 94% / 81% | 0.965 · 83% | 0.931 · 66% | 1968 | 1.00× |
| golden_qwen3.5_9b_logprob_p2db (ref) | 496 |  | 0.945 [0.922–0.964] | 72% [65%–81%] | 94% / 82% | 0.962 · 77% | 0.931 · 72% | 855 | n/a (Ollama, prefix cache) |

The paired 95% interval for the AUROC difference between PyTorch and Ollama is [−0.016, +0.012] for the 4B and
[−0.005, +0.014] for the 9B, so the harness reproduces both models. The elimination figure at 98% recall is
much less stable: it differs by 11 points between the two builds of the 4B. That gap is the yardstick for any
change in that column below.

## 3. Protocol

- **Search** on request 24-409 (247 pairs: 146 responsive, 101 not): the stock order and 25 blocks. The blocks
  are the eight groups (`0:4` … `28:32`), eight single layers (9, 11, 13, 15, 17, 19, 21, 23), four two-layer
  blocks (`10:12`, `14:16`, `18:20`, `22:24`) and five two-group blocks (`4:12` … `20:28`).
- **Validation** on request 25-3152 (249 pairs: 143 responsive, 106 not): the stock order and the three blocks
  with the highest AUROC on 24-409, ties to the block with fewer layer passes. The rule was fixed before any
  block was chosen, and 25-3152 was used for nothing else.
- **9B only:** blocks `12:16` and `14:16`, the two that kept their direction on the 4B's held-out request,
  were fixed before the 9B sweep started and scored on both requests whatever their search rank. Nothing in the
  9B data chose them, so their result over all 496 pairs is a clean test (§5).
- **A pair with no answer** (neither yes nor no among the top 20 tokens) counts as score 1.0: an email the
  screen cannot score cannot be eliminated. This was added after the first 4B launch stopped on block `0:4`,
  and before any block was selected.
- **Scores are deterministic.** The stock order was scored at the start and the end of each session and gave
  identical scores; forward time drifted by less than 1%.
- **Intervals** are 95% bootstrap intervals, resampled within class (2,000 resamples); the Δ column is paired
  (same pairs, both layer orders). "Eliminated at 98% recall" uses an in-sample cutoff, as in
  `docs/findings-golden.md`.

In the tables, ★ marks the three blocks chosen by the rule and ◆ the blocks fixed in advance. "AUROC, whole
vocab" ranks pairs by log P(yes) − log P(no) over the whole vocabulary, which is defined even when the model no
longer answers.

## 4. Qwen3.5-4B

**Search, request 24-409** (247 pairs; stock order: AUROC 0.9519, eliminated @98% recall 79%, recall / eliminated at 0.5 93% / 84%, 5.2 min):

| block repeated | layer passes | AUROC | Δ vs stock [95% CI] | elim @98% | recall / elim at 0.5 | no yes/no answer | AUROC, whole vocab | time ÷ stock |
|---|---|---|---|---|---|---|---|---|
| 12:16 ★ | 36 | 0.9698 | +0.0179 [+0.001, +0.037] | 77% | 95% / 89% | 0 | 0.9698 | 1.118× |
| 15:16 ★ | 33 | 0.9687 | +0.0168 [-0.000, +0.035] | 71% | 90% / 87% | 0 | 0.9687 | 1.012× |
| 14:16 ★ | 34 | 0.9632 | +0.0113 [-0.002, +0.025] | 81% | 95% / 85% | 0 | 0.9632 | 1.047× |
| 8:12 | 36 | 0.9604 | +0.0085 [-0.003, +0.022] | 77% | 88% / 87% | 0 | 0.9604 | 1.118× |
| 4:12 | 40 | 0.9586 | +0.0066 [-0.008, +0.024] | 75% | 94% / 86% | 0 | 0.9586 | 1.241× |
| 16:20 | 36 | 0.9578 | +0.0058 [-0.001, +0.013] | 78% | 94% / 85% | 0 | 0.9578 | 1.118× |
| 10:12 | 34 | 0.9564 | +0.0045 [-0.010, +0.019] | 72% | 92% / 87% | 0 | 0.9564 | 1.047× |
| 8:16 | 40 | 0.9559 | +0.0039 [-0.011, +0.021] | 76% | 92% / 85% | 0 | 0.9559 | 1.240× |
| 12:20 | 40 | 0.9554 | +0.0035 [-0.006, +0.013] | 70% | 95% / 86% | 0 | 0.9554 | 1.241× |
| 18:20 | 34 | 0.9540 | +0.0021 [-0.002, +0.007] | 79% | 94% / 85% | 0 | 0.9540 | 1.047× |
| 16:24 | 40 | 0.9531 | +0.0012 [-0.002, +0.004] | 80% | 95% / 83% | 0 | 0.9531 | 1.241× |
| 19:20 | 33 | 0.9528 | +0.0009 [-0.003, +0.005] | 80% | 98% / 80% | 0 | 0.9528 | 1.011× |
| 17:18 | 33 | 0.9527 | +0.0007 [-0.005, +0.007] | 78% | 88% / 86% | 0 | 0.9527 | 1.030× |
| 24:28 | 36 | 0.9525 | +0.0005 [-0.001, +0.002] | 79% | 93% / 84% | 0 | 0.9525 | 1.118× |
| 23:24 | 33 | 0.9524 | +0.0005 [-0.002, +0.003] | 80% | 90% / 85% | 0 | 0.9524 | 1.011× |
| 20:28 | 40 | 0.9522 | +0.0003 [-0.002, +0.002] | 79% | 95% / 81% | 0 | 0.9522 | 1.241× |
| 21:22 | 33 | 0.9519 | -0.0001 [-0.002, +0.002] | 79% | 94% / 83% | 0 | 0.9519 | 1.030× |
| 22:24 | 34 | 0.9519 | -0.0001 [-0.002, +0.002] | 79% | 87% / 87% | 0 | 0.9519 | 1.047× |
| 13:14 | 33 | 0.9517 | -0.0002 [-0.012, +0.012] | 77% | 96% / 81% | 0 | 0.9517 | 1.030× |
| 20:24 | 36 | 0.9508 | -0.0012 [-0.003, +0.001] | 79% | 86% / 87% | 0 | 0.9508 | 1.118× |
| 4:8 | 36 | 0.9429 | -0.0090 [-0.025, +0.007] | 70% | 88% / 86% | 0 | 0.9429 | 1.118× |
| 9:10 | 33 | 0.9386 | -0.0133 [-0.029, +0.002] | 74% | 63% / 95% | 0 | 0.9386 | 1.030× |
| 28:32 | 36 | 0.9336 | -0.0183 [-0.038, -0.001] | 71% | 0% / 100% | 0 | 0.9344 | 1.118× |
| 11:12 | 33 | 0.8585 | -0.0934 [-0.134, -0.053] | 44% | 92% / 62% | 0 | 0.8585 | 1.011× |
| 0:4 | 36 | 0.5000 | -0.4519 [-0.476, -0.422] | 0% | 100% / 0% | 247 | 0.5197 | 1.117× |
| stock (end of session) | 32 | 0.9519 | +0.0000 [+0.000, +0.000] | 79% | 93% / 84% | 0 | 0.9519 | 0.995× |
| stock | 32 | 0.9519 | +0.0000 [+0.000, +0.000] | 79% | 93% / 84% | 0 | 0.9519 | 1.000× |

**Validation, request 25-3152** (249 pairs; stock order: AUROC 0.8985, eliminated @98% recall 50%, recall / eliminated at 0.5 94% / 66%, 5.5 min):

| block repeated | layer passes | AUROC | Δ vs stock [95% CI] | elim @98% | recall / elim at 0.5 | no yes/no answer | AUROC, whole vocab | time ÷ stock |
|---|---|---|---|---|---|---|---|---|
| 14:16 ★ | 34 | 0.9146 | +0.0160 [-0.005, +0.035] | 47% | 94% / 71% | 0 | 0.9146 | 1.048× |
| 12:16 ★ | 36 | 0.9101 | +0.0115 [-0.012, +0.037] | 39% | 85% / 82% | 0 | 0.9101 | 1.119× |
| 15:16 ★ | 33 | 0.8990 | +0.0005 [-0.033, +0.034] | 57% | 82% / 83% | 0 | 0.8990 | 1.013× |
| stock (end of session) | 32 | 0.8985 | +0.0000 [+0.000, +0.000] | 50% | 94% / 66% | 0 | 0.8985 | 0.996× |
| stock | 32 | 0.8985 | +0.0000 [+0.000, +0.000] | 50% | 94% / 66% | 0 | 0.8985 | 1.000× |

- **Search:** the largest gains were in layers 12–15, and blocks in layers 16–27 changed AUROC by less than
  0.006. Repeating the first group stopped the model answering yes or no on all 247 pairs, repeating layer 11
  alone cost 0.093, and repeating the last group cost 0.018 and made it answer "no" to everything at a 0.5
  cutoff.
- **Validation:** two of the three chosen blocks moved in the right direction, and no interval excludes zero.
  The single-layer block that looked good in the search (+0.017) gave nothing. Elimination at 98% recall moved
  from 50% to 47%, 39% and 57%, which is inside the 11-point yardstick of §2.

## 5. Qwen3.5-9B

**Search, request 24-409** (247 pairs; stock order: AUROC 0.9655, eliminated @98% recall 83%, recall / eliminated at 0.5 97% / 84%, 9.0 min):

| block repeated | layer passes | AUROC | Δ vs stock [95% CI] | elim @98% | recall / elim at 0.5 | no yes/no answer | AUROC, whole vocab | time ÷ stock |
|---|---|---|---|---|---|---|---|---|
| 12:16 ★ ◆ | 36 | 0.9816 | +0.0161 [-0.002, +0.036] | 85% | 97% / 90% | 0 | 0.9816 | 1.120× |
| 16:20 ★ | 36 | 0.9760 | +0.0105 [+0.003, +0.019] | 83% | 97% / 89% | 0 | 0.9760 | 1.117× |
| 14:16 ★ ◆ | 34 | 0.9758 | +0.0103 [-0.001, +0.024] | 85% | 92% / 92% | 0 | 0.9758 | 1.051× |
| 17:18 | 33 | 0.9744 | +0.0089 [+0.002, +0.017] | 82% | 97% / 83% | 0 | 0.9744 | 1.028× |
| 18:20 | 34 | 0.9691 | +0.0036 [+0.000, +0.007] | 80% | 87% / 89% | 0 | 0.9691 | 1.051× |
| 16:24 | 40 | 0.9690 | +0.0035 [+0.000, +0.008] | 82% | 98% / 84% | 0 | 0.9690 | 1.241× |
| 12:20 | 40 | 0.9685 | +0.0031 [-0.003, +0.010] | 80% | 97% / 84% | 0 | 0.9685 | 1.241× |
| 22:24 | 34 | 0.9678 | +0.0023 [+0.000, +0.005] | 82% | 99% / 82% | 0 | 0.9678 | 1.051× |
| 20:24 | 36 | 0.9672 | +0.0018 [-0.000, +0.004] | 82% | 97% / 84% | 0 | 0.9672 | 1.118× |
| 20:28 | 40 | 0.9664 | +0.0009 [-0.001, +0.003] | 82% | 100% / 78% | 0 | 0.9664 | 1.241× |
| 8:12 | 36 | 0.9664 | +0.0009 [-0.011, +0.013] | 83% | 99% / 82% | 0 | 0.9664 | 1.117× |
| 23:24 | 33 | 0.9661 | +0.0006 [-0.001, +0.002] | 83% | 99% / 81% | 0 | 0.9661 | 1.018× |
| 19:20 | 33 | 0.9653 | -0.0001 [-0.003, +0.003] | 81% | 98% / 84% | 0 | 0.9653 | 1.017× |
| 24:28 | 36 | 0.9648 | -0.0007 [-0.002, +0.001] | 82% | 99% / 81% | 0 | 0.9648 | 1.118× |
| 21:22 | 33 | 0.9644 | -0.0011 [-0.003, +0.000] | 83% | 92% / 88% | 0 | 0.9644 | 1.028× |
| 28:32 | 36 | 0.9643 | -0.0012 [-0.004, +0.002] | 81% | 85% / 90% | 0 | 0.9643 | 1.118× |
| 13:14 | 33 | 0.9629 | -0.0026 [-0.013, +0.008] | 78% | 99% / 75% | 0 | 0.9629 | 1.028× |
| 8:16 | 40 | 0.9601 | -0.0054 [-0.020, +0.007] | 79% | 97% / 80% | 0 | 0.9601 | 1.241× |
| 15:16 | 33 | 0.9590 | -0.0064 [-0.021, +0.007] | 65% | 100% / 50% | 0 | 0.9590 | 1.017× |
| 9:10 | 33 | 0.9559 | -0.0096 [-0.029, +0.007] | 76% | 97% / 81% | 0 | 0.9559 | 1.028× |
| 4:8 | 36 | 0.9553 | -0.0102 [-0.023, +0.001] | 76% | 92% / 88% | 0 | 0.9553 | 1.120× |
| 10:12 | 34 | 0.9435 | -0.0220 [-0.040, -0.006] | 79% | 93% / 83% | 0 | 0.9435 | 1.051× |
| 4:12 | 40 | 0.9427 | -0.0228 [-0.040, -0.008] | 75% | 96% / 82% | 0 | 0.9427 | 1.241× |
| 0:4 | 36 | 0.8360 | -0.1295 [-0.176, -0.087] | 29% | 92% / 56% | 0 | 0.8360 | 1.123× |
| 11:12 | 33 | 0.8152 | -0.1503 [-0.204, -0.100] | 32% | 95% / 46% | 0 | 0.8152 | 1.017× |
| stock (end of session) | 32 | 0.9655 | +0.0000 [+0.000, +0.000] | 83% | 97% / 84% | 0 | 0.9655 | 0.995× |
| stock | 32 | 0.9655 | +0.0000 [+0.000, +0.000] | 83% | 97% / 84% | 0 | 0.9655 | 1.000× |

**Validation, request 25-3152** (249 pairs; stock order: AUROC 0.9313, eliminated @98% recall 66%, recall / eliminated at 0.5 92% / 78%, 9.5 min):

| block repeated | layer passes | AUROC | Δ vs stock [95% CI] | elim @98% | recall / elim at 0.5 | no yes/no answer | AUROC, whole vocab | time ÷ stock |
|---|---|---|---|---|---|---|---|---|
| 16:20 ★ | 36 | 0.9375 | +0.0062 [-0.000, +0.014] | 70% | 89% / 87% | 0 | 0.9375 | 1.124× |
| 14:16 ★ ◆ | 34 | 0.9268 | -0.0045 [-0.025, +0.014] | 68% | 70% / 92% | 0 | 0.9268 | 1.056× |
| 12:16 ★ ◆ | 36 | 0.9157 | -0.0156 [-0.043, +0.009] | 41% | 80% / 90% | 0 | 0.9157 | 1.124× |
| stock (end of session) | 32 | 0.9313 | +0.0000 [+0.000, +0.000] | 66% | 92% / 78% | 0 | 0.9313 | 1.000× |
| stock | 32 | 0.9313 | +0.0000 [+0.000, +0.000] | 66% | 92% / 78% | 0 | 0.9313 | 1.000× |

**The two blocks fixed in advance, both requests together:**

| layer order | pairs | AUROC [95% CI] | Δ vs stock [95% CI] | elim @98% [95% CI] | recall / elim at 0.5 | time ÷ stock |
|---|---|---|---|---|---|---|
| stock | 496 | 0.9488 [0.928, 0.967] |  | 76% [67%, 83%] | 94% / 81% | 1.000× |
| 12:16 | 496 | 0.9513 [0.933, 0.968] | +0.0025 [-0.013, +0.018] | 59% [50%, 75%] | 88% / 90% | 1.122× |
| 14:16 | 496 | 0.9513 [0.933, 0.969] | +0.0025 [-0.009, +0.015] | 71% [64%, 81%] | 81% / 92% | 1.054× |

- **The gain did not replicate.** Over all 496 pairs both pre-specified blocks changed AUROC by +0.003, with
  intervals centred near zero. Elimination at 98% recall went down (76% to 59% and 71%), and recall at a 0.5
  cutoff fell from 94% to 88% and 81%.
- **One small candidate.** `16:20` was the only block above stock on both requests (+0.011 on the search
  request, +0.006 [−0.000, +0.014] on the held-out one). It was not validated on the 4B's held-out request, so
  it is a lead and not a finding.

## 6. Reading the two sweeps together

**The gain depends on the request.** Change in AUROC against the stock order:

| block | 4B, 24-409 | 4B, 25-3152 | 9B, 24-409 | 9B, 25-3152 |
|---|---|---|---|---|
| `12:16` | +0.0179 | +0.0115 | +0.0161 | −0.0156 |
| `14:16` | +0.0113 | +0.0160 | +0.0103 | −0.0045 |

On 24-409 the two models agree closely. On 25-3152 the 4B went up and the 9B went down, and none of those four
intervals excludes zero. Looping seems to shift how a model handles one particular request, not to make it
better at the task in general.

**The depth profile replicated.** In both models, repeating layer 11 alone or the first group does serious
damage (on the 9B the first group still answers, at AUROC 0.836), layers 20–27 change almost nothing, and
anything useful in both models sits in layers 12–19.

**Looping pushes scores toward "no".** At a 0.5 cutoff every validated block eliminated more than the stock
order, on both requests and both models (66% to 82% for `12:16` on the 4B's held-out request). On the
held-out request five of the six also lost recall: 94% to 85% and 82% on the 4B, 92% to 89%, 80% and 70% on
the 9B. A cutoff set on the stock model does not carry over to a looped one.

**The time cost follows the layers repeated,** and is the same on both models: about 3% for one
linear-attention layer, 1 to 2% for one full-attention layer, 5% for a two-layer block, 12% for a whole group
and 24% for two groups.

**A bigger model is the dependable lever.** In this harness the stock 9B scores AUROC 0.949 against 0.920 for
the stock 4B (paired interval for the difference [+0.010, +0.048]), on both requests, for 1.6 times the time
(18.5 against 11.7 minutes for the 496 pairs).

## 7. Limits

- **Two requests.** With one request for search and one for validation, a request-dependent effect cannot be
  separated from noise. This is the main limit.
- **One extra pass only.** Three or more passes of a block were not run. Longer blocks did worse than shorter
  ones in the same region (`12:20` and `8:16` against `12:16`), which suggests more would not help, but that
  is not the same test.
- **Contiguous blocks, one at a time.** No combinations of blocks.
- **The 4B's whole-set figures are selected.** Over both requests `12:16` reads 0.944 and `14:16` 0.939 against
  0.920 for stock, but half of those pairs chose the blocks. The 9B's whole-set figures in §5 are not affected.
- **98% recall cutoffs are in-sample**, as elsewhere in this repository.

## 8. Reproduce

The tables need only the committed scores:

    python3 loop/sweep_report.py
    python3 loop/sweep_report.py --name sweep9b
    python3 loop/compare_runs.py loop/runs/qwen3.5_4b_base --ref runs/golden_qwen3.5_4b_logprob_p2db --boot 2000
    python3 loop/compare_runs.py loop/runs/qwen3.5_9b_base loop/runs/qwen3.5_4b_base --ref runs/golden_qwen3.5_9b_logprob_p2db --boot 2000

Scoring needs the local email text (README, "Data") and a GPU that PyTorch can use. `loop/` is its own uv
project; the pinned torch build is the ROCm 7.2 wheel. From the repository root:

    (cd loop && uv sync)
    loop/.venv/bin/python loop/score_hf.py --tag qwen3.5_4b_base
    loop/.venv/bin/python loop/sweep.py
    loop/.venv/bin/python loop/sweep.py --model Qwen/Qwen3.5-9B --name sweep9b --confirm 12:16,14:16

Both sweeps are resumable. `loop/runs/qwen3.5_9b_base` is the 9B sweep's two stock passes put together
(`run.json` says so). A single layer order can be scored with `--repeat`, for example
`loop/score_hf.py --tag r12-16 --repeat 12:16`; `--repeat 12:16:3` runs the block three times.
