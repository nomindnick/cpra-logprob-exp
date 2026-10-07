# Golden set — three Qwen models; logprob vs JSON verdicts, reasoning first, roster ablation

**Date:** 2026-10-07 · **Status:** golden-set results on the Strix Halo, one run per configuration; laptop runs pending
**Runs:** `runs/golden_*` (scores committed; the runs behind each table are listed at the top of the report)
**Report:** `uv run python scripts/golden_report.py` (every table below, plus per-request and per-recipe detail)

The qwen3.5:4b and 9b numbers here come from the clean GPU setting described in §7. The first
golden runs of those two models (2026-10-05) hit a GPU backend fault; §7 describes it, the fix,
and what it changed.

## Setup

496 (request, email) pairs over two requests, one designed pair per email (SPEC §14,
`data/golden/summary.json`). Labels are human-adjudicated: Opus pre-labeled 420 real emails, the
human checked every disagreement with production membership plus a random spot check (81 of 81
confirmed), and every synthetic email the verifier flagged (`docs/golden-adjudication.md`).

| | 24-409 (topical) | 25-3152 (correspondent-scoped) |
|---|---|---|
| real_positive / real_negative | 75 / 60 | 75 / 60 |
| close_call / privileged / exempt-other positives | 25 / 20 / 20 | 25 / 20 / 20 |
| hard_negative | 43 | 40 |
| hard_negative_flipped (synthetic "hard negative" the human judged responsive) | 4 | 9 |

Models: qwen3.5:4b, qwen3.5:9b, qwen3.8:27b (all Q4_K_M), Ollama 0.32.14 on ROCm 7.2,
`num_ctx=8192`, thinking off, temperature 0, single-stream. The 4b and 9b run with
`num_batch=8192` (§7). Three modes on identical inputs:

- **lp**: first-token P(yes)/(P(yes)+P(no)) (the sweep's method).
- **json**: the 2025 approach, a generated `{"responsive", "confidence", "reasoning"}` object
  with the verdict first. Scored as confidence if responsive, else 1 − confidence.
- **jsonR**: the same object with `reasoning` first, enforced by a JSON schema; the prompt says
  "Write the reasoning first, then decide." Every scored jsonR answer has its reasoning first.

"Default decision" = score ≥ 0.5 for lp, the verdict for json/jsonR. Unscored rows (unparseable
JSON): 3 of 2,980 in the clean 4b/9b JSON runs, none in the 27b's.

## 1. Headline

| run | AUROC [95% CI] | non-responsive eliminated @98% recall [95% CI] | default decision: recall / eliminated | s/email |
|---|---|---|---|---|
| 4b lp | 0.916 [0.890–0.939] | 53% [41–62%] | 79% / 87% | 0.98 |
| 9b lp | 0.934 [0.910–0.952] | 67% [47–75%] | 81% / 86% | 1.59 |
| **27b lp** | **0.976 [0.963–0.985]** | **79% [71–86%]** | 86% / 95% | 3.32 |
| 4b json | 0.831 [0.797–0.862] | 4% [2–7%] | 78% / 88% | 2.76 |
| 9b json | 0.821 [0.787–0.853] | 0% | 66% / 94% | 4.62 |
| 27b json | 0.956 [0.939–0.971] | 45% [38–53%] | 93% / 94% | 8.35 |
| 4b jsonR | 0.857 [0.823–0.888] | 0% | 53% / 95% | 3.32 |
| 9b jsonR | 0.878 [0.845–0.908] | 0% | 76% / 89% | 5.31 |
| 27b jsonR | 0.950 [0.932–0.966] | 0% | 92% / 90% | ~8* |

CIs are bootstrap (1,000 resamples within each class). \* The 27b jsonR run reloaded the model
before every call, so its prefill wasn't cached: measured 10.1 s, of which 4.8 s is decoding;
with the cached 3.0 s prefill of the other 27b runs it would be about 8 s.

- **The 27b is the clear winner:** 79% of non-responsive emails cleared at 98% recall.
- **4b vs 9b is not settled.** 98% recall on 293 positives allows 5 misses, so a few emails
  swing the elimination number: the 9b's CPU reference run (same model, AUROC 0.930) eliminates
  57%, not 67%. The CIs overlap almost entirely.
- **JSON ranks worse than lp in every model, in either order**, and the small models' JSON
  can't reach 98% recall without keeping nearly everything (§2).
- **The golden set is harder than the sweep by design.** On its real emails alone, lp AUROC is
  0.973 / 0.994 / 1.000; the synthetic close calls and hard negatives carry the difficulty. (The
  real rows were also chosen to favor confident pre-labels, so real-only numbers flatter.)

## 2. JSON verdicts are one operating point, not a score

- **The confidence is nearly binary.** Each JSON run used 2–5 distinct confidence values
  (27b json: 0.95 ×320, 1.0 ×149, 0.98 ×27). 2 of 2,974 JSON scores fall between 0.2 and 0.8.
- **It isn't calibrated where it matters.** When the 9b json says "not responsive" with
  confidence ≥ 0.95, 35% of those 289 emails are responsive. Because some responsive emails get a
  score of 0, no threshold reaches 98% recall without keeping everything.
- **At the same operating point, JSON and lp make the same calls.** Set the lp threshold so lp
  says yes exactly as often as the JSON verdicts do. Recall and elimination then agree within
  about one point in all six JSON runs, and where the two disagree each is right about half
  the time:

| JSON run | JSON: recall / eliminated | lp at the same yes-rate | disagreements: lp right / JSON right |
|---|---|---|---|
| 4b json | 78.2% / 87.7% | 77.5% / 86.7% | 14 / 18 |
| 4b jsonR | 52.9% / 94.6% | 53.9% / 96.1% | 49 / 43 |
| 9b json | 65.9% / 93.6% | 66.6% / 94.6% | 18 / 14 |
| 9b jsonR | 76.1% / 89.1% | 76.1% / 89.1% | 31 / 31 |
| 27b json | 92.8% / 93.6% | 92.5% / 93.1% | 3 / 5 |
| 27b jsonR | 92.5% / 90.1% | 93.2% / 91.1% | 18 / 14 |

  So the generated verdict adds no accuracy over an lp threshold, and lp also offers every
  other operating point. The 27b json's better default decision (93% recall vs lp's 86%) only
  reflects that 0.5 is a conservative cut for the lp score: lp at 0.27 matches it.
- **Cost:** JSON is 2.4–3.4× slower (lp 0.98 / 1.59 / 3.32 s vs json 2.76 / 4.62 / 8.35 s).
  Prefill is the same in every mode; the difference is decoding 100–130 tokens at
  58 / 36 / 24 tok/s. H1 predicted an order of magnitude; on this hardware it is about 3×,
  because prefill dominates.

## 3. Does reasoning first help?

In the json runs the verdict is the first key, so the model commits before writing any
reasoning. The jsonR runs make it reason first.

| model | AUROC json → jsonR | default recall | default eliminated | verdicts agree | jsonR right where they differ |
|---|---|---|---|---|---|
| 4b | 0.831 → 0.857 | 78% → 53% | 88% → 95% | 386 / 496 | 25 of 110 |
| 9b | 0.821 → 0.878 | 66% → 76% | 94% → 89% | 424 / 495 | 46 of 71 |
| 27b | 0.956 → 0.950 | 93% → 92% | 94% → 90% | 470 / 496 | 9 of 26 |

- **Reasoning first moves the small models' cutoff, in opposite directions.** The 4b becomes
  much stricter (37 fewer real positives caught, 13 more hard negatives cleared); the 9b becomes
  more lenient (14 more real positives and 9 more close calls caught, 8 fewer hard negatives
  cleared). The 27b barely changes, and is slightly worse where it does.
- **It doesn't help them sort.** At a matched yes-rate, jsonR is no better than an lp threshold
  either (table in §2: 49/43, 31/31, 18/14). Reasoning changes where the model draws the line,
  not how well it orders the emails.
- **By email type** (matched yes-rate, both requests), there's one consistent JSON advantage,
  and only in the 27b: wrong-date hard negatives. The 27b json and jsonR each clear 20 of 20,
  lp at the same rate 17 and 15. It shows up with the verdict first too, so it comes from the
  JSON framing, not from reasoning before the answer. The small models show no consistent gain
  (of 19–20: 4b json 7 vs lp 8, 4b jsonR 15 vs 16, 9b json 13 vs 14, 9b jsonR 11 vs 9).
- **Reasoning first hurts the 27b on two traps:** forwarded emails with no content (12 of 17
  cleared vs 16 verdict-first and 15 lp) and keywords used in an unrelated sense (9 of 20 vs 13
  and 12). Its reasoning works through a checklist (inside the date window? a named person
  involved? then responsive) instead of reading what the email is about.
- **Answer:** forcing reasoning first doesn't buy accuracy on any email type consistently, and
  it takes 15–20% longer than verdict-first JSON for the 4b and 9b.

## 4. Where the score breaks: by kind

Share flagged responsive at each run's 98%-recall threshold, both requests. For + groups this is
recall; for − groups it is the share that slips through the screen.

| kind | label | n | 4b lp | 9b lp | 27b lp | 27b json |
|---|---|---|---|---|---|---|
| real_positive | + | 150 | 97% | 99% | 97% | 100% |
| close_call_positive | + | 50 | 98% | 100% | 98% | 100% |
| privileged_positive | + | 40 | 100% | 100% | 100% | 100% |
| exempt_other_positive | + | 40 | 100% | 100% | 100% | 100% |
| hard_negative_flipped | + | 13 | 100% | 69% | 100% | 92% |
| real_negative | − | 120 | 28% | 11% | 1% | 30% |
| hard_negative | − | 83 | 76% | 65% | 49% | 90% |

- **Responsiveness is not confused with exemption.** Privileged and personnel/deliberative
  positives are caught 100% of the time at threshold and 88–98% at the default decision, more
  than ordinary real positives (77–86%) in every lp run. The "don't consider exemption"
  instruction holds.
- **Hard negatives are where the screening cost goes.** The 27b clears all but 1% of real
  cross-request negatives; half of the hard negatives still pass. By recipe (slip-through at the
  98% threshold, 4b / 9b / 27b lp): keyword in an unrelated sense 85 / 90 / 65%; same subject,
  wrong date 95 / 95 / 55%; keyword only in a signature or newsletter 65 / 45 / 35%; forwarded
  with no content 71 / 35 / 47%.
- **Date reasoning is the clearest size effect.** At the default decision the 27b passes 10% of
  wrong-date emails; the 4b and 9b pass 60% and 65%.
- **The flipped hard negatives** (13) are mostly 25-3152 emails between planning-group members
  on a personal subject. The human judged them responsive (the request covers any communication
  between members); the models score them by subject. At the default decision the 9b catches 3
  of 13. Three of them are on the list of labels to re-check (§9).

## 5. What the best model misses

The 27b lp's 98% threshold is low (0.017) because of a handful of positives scored near zero.
9 of its 11 lowest-scored positives are 25-3152 emails that are responsive only because of who
sent or received them: a TAC meeting agenda, a DA event invitation, a password reset, a SANDAG
legislative update, a planning-group chair meeting hold. The 27b json scores all 11 at 0.05 or
less too. Both modes read the request as a subject-matter request. This is a
request-interpretation problem, not a scoring problem, and no threshold fixes it.

## 6. Roster ablation (25-3152)

Same 249 pairs, with the planning-group roster (members, roles, email addresses) appended to the
request. Paired bootstrap CIs; each pair of runs uses the same backend setting.

| run | AUROC | ΔAUROC [95% CI] | eliminated @98% recall | default recall |
|---|---|---|---|---|
| 4b lp | 0.877 → 0.955 | +0.079 [+0.048, +0.116] | 39% → 62% | 74% → 93% |
| 9b lp | 0.905 → 0.949 | +0.044 [+0.022, +0.069] | 59% → 71% | 77% → 87% |
| **27b lp** | **0.953 → 0.983** | +0.030 [+0.012, +0.054] | **72% → 82%** | 77% → 77% |
| 4b json | 0.791 → 0.864 | +0.073 [+0.025, +0.125] | 6% → 9% | 72% → 93% |
| 9b json | 0.770 → 0.877 | +0.107 [+0.062, +0.153] | 0% → 0% | 60% → 84% |
| 27b json | 0.927 → 0.971 | +0.044 [+0.020, +0.070] | 30% → 64% | 89% → 85% |
| 4b jsonR | 0.828 → 0.931 | +0.103 [+0.062, +0.146] | 0% → 0% | 53% → 82% |
| 9b jsonR | 0.859 → 0.935 | +0.077 [+0.040, +0.116] | 0% → 74% | 74% → 95% |
| 27b jsonR | 0.942 → 0.979 | +0.037 [+0.018, +0.061] | 0% → 81% | 86% → 81% |

- **The roster helps every model in every mode.** This corrects the first draft, which found it
  hurt the 4b and 9b lp. That was the GPU fault: every roster prompt is over 2,048 tokens.
- **Small models gain on positives; the 27b gains on negatives.** With the roster, the 4b and 9b
  score positives higher in every mode (mean lp score +0.06 to +0.25 by kind; default recall up
  10–29 points) while negatives barely move (+0.02 to +0.06 for lp). The 27b's positives barely
  move; its hard negatives drop by 0.14–0.19.
- **The 27b's correspondent-only misses (§5) stay near zero.** The roster tells the model who
  the members are; the prompt still doesn't get it to treat "sent by a member" as sufficient.
- **Cost:** the roster adds 1,330 tokens to the shared request prefix. The 27b keeps that
  prefix cached, so it adds about 0.9 s per email (3.2 → 4.1 s on these pairs). At batch 8192
  the 4b and 9b get no prefix cache (§7), so they pay for the full roster on every email: lp goes
  from 1.02 to 1.83 s (4b) and from 1.65 to 2.88 s (9b) on these pairs.

## 7. A GPU backend fault in the first 4b and 9b runs

The first golden runs of qwen3.5:4b and 9b (2026-10-05) used Ollama's default batch size. On
this ROCm build that corrupts these models' internal state in two ways.

1. **State leaks between requests.** After the model scored email A, asking it to list email
   B's attachments returned A's attachment file name; with nothing scored first, it answered
   "none". The 9b scored one email 0.19 when nothing came before it and 0.90 right after another
   email. This was found because the JSON reasoning sometimes described an email scored 1–4 rows
   earlier.
2. **Long prompts are garbled.** Reloading the model before every call stops the leak but
   exposes a second fault: prompts over 2,048 tokens come out corrupted. In those reloaded runs
   the 9b described its input as garbled (for example "a series of '!' characters") in up to a
   third of long prompts (56 of 172 in the reasoning-first run), and never in short ones.

Both symptoms match open upstream reports for this model architecture on ROCm
(ollama/ollama#18528, ggml-org/llama.cpp#29092). The workaround suggested there (keep the first
layer on the CPU) broke the model on this build: the 9b named Prague as the capital of France.

**Fix:** `num_batch=8192` (`score.py --num-batch 8192`), which processes the whole prompt in one
batch. Checks:

- **No leak:** with the fix, the 9b's scores are identical on all 496 pairs whether or not the
  model is reloaded before each call, and so are the 4b's.
- **No garbling:** none of the 2,980 JSON answers in the clean runs describes garbled input.
- **Matches a CPU reference** (`--num-gpu 0`, same box): AUROC 0.916 vs 0.916 (4b) and 0.934 vs
  0.930 (9b). Per-pair differences (mean |Δ| 0.04–0.06) are the same for short and long prompts,
  so they're ordinary GPU-vs-CPU arithmetic, not the fault.

Each setting against the clean run (lp, all 496 pairs; Δ = per-pair score difference):

| run | AUROC | eliminated @98% | mean \|Δ\| vs clean, prompts ≤ 2,048 tok (n=327) | > 2,048 tok (n=169) |
|---|---|---|---|---|
| 4b, default batch (the 2026-10-05 run) | 0.906 | 48% | 0.019 | 0.071 |
| 4b, default batch, reloaded every call | 0.823 | 33% | 0.021 | 0.280 |
| 4b, CPU | 0.916 | 55% | 0.044 | 0.047 |
| **4b, batch 8192 (clean)** | **0.916** | **53%** | — | — |
| 9b, default batch (the 2026-10-05 run) | 0.924 | 64% | 0.022 | 0.071 |
| 9b, default batch, reloaded every call | 0.859 | 41% | 0.017 | 0.331 |
| 9b, CPU | 0.930 | 57% | 0.059 | 0.054 |
| **9b, batch 8192 (clean)** | **0.934** | **67%** | — | — |

On the 249 roster pairs, all over 2,048 tokens, the damage was much larger. lp AUROC on those pairs:

| | default batch (2026-10-05) | default batch, reloaded | CPU | batch 8192 (clean) |
|---|---|---|---|---|
| 4b + roster | 0.805 | 0.529 | 0.954 | 0.955 |
| 9b + roster | 0.839 | 0.563 | 0.950 | 0.949 |

**What this changes:**

- The 2026-10-05 runs ranked roughly right (AUROC about 0.01 low), but individual scores were
  off, and the roster runs were badly wrong; that is where the "roster hurts small models"
  conclusion came from. The reloaded runs, first taken as the clean baseline, were the worst of
  all.
- **The 27b is not affected**, though Ollama lists it in the same architecture family. At the
  default batch its cached and reloaded runs agree (mean |Δ| 0.011 short, 0.008 long; AUROC 0.976
  both), none of its 745 reasoning-first answers describes garbled input, and a batch-8192 run
  matches it (AUROC 0.977 vs 0.976, 79% eliminated in both; mean |Δ| 0.010 on short prompts,
  0.009 on long). Its tables use the default batch, which keeps the prefix cache (3.3 s per email
  vs 5.1 s at batch 8192).
- **Cost of the fix:** at batch 8192 the 4b and 9b lose Ollama's prefix cache (prefill takes
  the same time with or without a reload: 9b 1,569 vs 1,575 ms). lp goes from 0.80 to 0.98 s per
  email for the 4b and from 1.16 to 1.59 s for the 9b.
- **Earlier docs:** the sweep's qwen3.5 rows, `findings-run1.md`, and the Strix side of
  `findings-cpu.md` were all default-batch runs. Each now has a correction note. The sweep won't
  be rerun: this golden set is the clean comparison of the qwen3.5 models.
- **Lesson for deployment:** the canary check in `score.py` didn't catch this, because it
  compares against a reference taken in the same faulty state. What caught it was reading the
  model's reasoning, then a cross-request content probe, a reloaded-vs-cached identity check,
  and a CPU reference run. Validating the backend should be part of any local deployment.

## 8. Hypothesis status (golden set)

| | status |
|---|---|
| H1 latency ≪ JSON | supported in direction: 2.4–3.4×, not 10×, on the Strix Halo (prefill dominates) |
| H2 ≥98% recall with >50% eliminated | met by 9b lp (67%, CI 47–75%) and 27b lp (79%, CI 71–86%); 4b lp borderline (53%, CI 41–62%); no JSON run |
| H3 score tracks error rate | lp yes (monotonic in every model); JSON no (near-binary confidence; 35% responsive among the 9b's "confident no" answers) |

## 9. Labels to re-check

Readers of the model reasoning flagged these golden labels and inputs:

- **25-3152 synthetic 15:05 and 15:09** (flipped to responsive): purely personal emails between
  members (a utility matter; a cookie sale). Is a purely personal message a public record at all
  under *City of San Jose v. Superior Court* (2017) 2 Cal.5th 608?
- **25-3152 real 48518148** (responsive): the planning-group chair received it, but only a
  delivery header shows that, and the renderer doesn't show it ("To: None"). Rendering bug; may
  affect other emails.
- **25-3152 synthetic 14:02** (close call, responsive): the only ACPG mention is past the
  8,000-character body cap, so no model sees it.
- **24-409 synthetic 06:01** (flipped to responsive): an out-of-office reply; the call is
  debatable.
- **24-409 synthetic 02:01** (close call, responsive): the only hook is a signature line.
- **24-409 real 33732508** (responsive): the label is right but its rationale isn't; the hits are
  attachment names ("OSEJ_RWER_Fact Sheet", "UCSD_SDC RWER… Handout") about 6,200 characters in.
- **24-409 synthetic 07:09** (hard negative): "RDF" here means refuse-derived fuel, not the
  request's sense, but the refinement reads like search terms, so a literal hit is arguable.
  Minor.

## 10. Caveats

- One run per configuration. Elimination at 98% recall moves several points with a few
  borderline emails (the 9b's GPU and CPU runs: 67% vs 57%).
- Real rows favor confident pre-labels; unflagged synthetic emails carry Opus's intended label
  with verifier agreement, not a human check.
- 25-3152 has 149 positives: 98% recall there allows 3 misses.
- Strix Halo only. The laptop is CPU-only (the path that was clean here) but hasn't been checked
  for the fault.

## 11. Next

1. Resolve the labels in §9 and fix the bcc rendering bug.
2. Prompt revision for correspondent-scoped requests: state that a communication sent or
   received by a named person is responsive regardless of subject; rerun 25-3152 with and
   without the roster.
3. Laptop runs, starting with the leak and garbling probes from §7.
4. Jev (API) and a Jev-like open model on the same pairs (SPEC §14.1).
5. Optional: a newer Ollama, to see whether the fault is fixed upstream (which would also bring
   back the prefix cache).
