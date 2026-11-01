# Golden set — three Qwen models; logprob vs JSON verdicts, reasoning first, roster ablation, prompt revision

**Date:** 2026-10-07; refreshed 2026-11-01 on prompt 2, the 2026-10-31 labels and Ollama 0.40.13 · **Status:** golden-set results on the Strix Halo, one run per configuration; laptop runs pending
**Runs:** `runs/golden_*` (scores committed; the runs behind each table are listed at the top of the report)
**Report:** `uv run python scripts/golden_report.py` (every table below, plus per-request and per-recipe detail); `--prompt 1` gives the same tables for the original prompt

Every table outside §7 and §8 comes from the 2026-10-31 reruns. They use prompt 2, which adds the
named-correspondent rule (§5), and the 2026-10-31 labels (§9). Email headers now include Bcc and
Delivered-To lines (render 2, §9). The runs are on Ollama 0.40.13; Ollama was upgraded from
0.32.14 after the October runs, and §8 checks what that changed (for logprob scores, little).
§7 describes the GPU backend fault in the first qwen3.5:4b and 9b runs and keeps its October
numbers. The 2026-10-07 version of this document (prompt 1, the old labels) is in git history.

## Setup

495 (request, email) pairs over two requests, one designed pair per email (SPEC §14,
`data/golden/summary.json`). Labels are human-adjudicated. Opus pre-labeled 420 real emails, and
the human checked:

- every disagreement with production membership, plus a random spot check (81 of 81 confirmed);
- every synthetic email the verifier flagged (`docs/golden-adjudication.md`);
- eight labels questioned later (§9).

| | 24-409 (topical) | 25-3152 (correspondent-scoped) |
|---|---|---|
| real_positive / real_negative | 75 / 60 | 75 / 60 |
| close_call / privileged / exempt-other positives | 25 / 20 / 20 | 25 / 20 / 20 |
| hard_negative | 42 | 49 |
| hard_negative_flipped (synthetic "hard negative" the human judged responsive) | 4 | 0 |
| positives / negatives | 144 / 102 | 140 / 109 |

Models: qwen3.5:4b, qwen3.5:9b, qwen3.8:27b (all Q4_K_M), Ollama 0.40.13 on ROCm 7.2,
`num_ctx=8192`, thinking off, temperature 0, single-stream. The 4b and 9b run with
`num_batch=8192` (§7). The 27b runs at the default batch, which keeps Ollama's prefix cache.
Three modes on identical inputs:

- **lp**: first-token P(yes)/(P(yes)+P(no)) (the sweep's method).
- **json**: the 2025 approach, a generated `{"responsive", "confidence", "reasoning"}` object
  with the verdict first. Scored as confidence if responsive, else 1 − confidence.
- **jsonR**: the same object with `reasoning` first, enforced by a JSON schema; the prompt says
  "Write the reasoning first, then decide." Every scored jsonR answer has its reasoning first.

The system prompt (`score.py`) is shown below; the user message holds the request and the email.
The bold sentence is new in prompt 2 (§5). The JSON modes replace the last sentence with the JSON
instructions.

> You are a public records analyst for a California county. You will be shown a California
> Public Records Act (CPRA) request and one email from the county's email system. Decide whether
> the email is responsive to the request, meaning it is a record the request is asking for.
> **If the request covers communications sent or received by named people or groups, an email to
> or from one of them is responsive whatever its subject, unless it is purely personal and has
> nothing to do with public business.** Do not consider whether the email might be exempt from
> disclosure; that is a separate question. Answer with a single word: yes or no.

"Default decision" = score ≥ 0.5 for lp, the verdict for json/jsonR. Unscored rows (unparseable
JSON): 5 of 6,696.

## 1. Headline

| run | AUROC [95% CI] | non-responsive eliminated @98% recall [95% CI] | default decision: recall / eliminated | s/email |
|---|---|---|---|---|
| 4b lp | 0.923 [0.896–0.945] | 47% [39–69%] | 95% / 73% | 0.89 |
| 9b lp | 0.943 [0.921–0.962] | 72% [65–78%] | 93% / 81% | 1.46 |
| **27b lp** | **0.975 [0.964–0.986]** | **76% [70–88%]** | 93% / 91% | 2.64 |
| 4b json | 0.833 [0.796–0.867] | 9% [6–14%] | 90% / 76% | 2.75 |
| 9b json | 0.871 [0.842–0.901] | 0% | 81% / 87% | 4.43 |
| 27b json | 0.947 [0.927–0.964] | 28% [22–34%] | 95% / 87% | 6.80 |
| 4b jsonR | 0.870 [0.837–0.900] | 0% | 87% / 81% | 2.91 |
| 9b jsonR | 0.879 [0.846–0.909] | 0% [0–69%] | 93% / 77% | 5.26 |
| 27b jsonR | 0.951 [0.934–0.965] | 66% [59–73%] | 95% / 82% | 7.01 |

CIs are bootstrap (1,000 resamples within each class). s/email is the median per call.

- **The 27b lp is still the clear winner:** 76% of non-responsive emails cleared at 98% recall,
  the same as with prompt 1 on this Ollama version (77%, §5).
- **The 9b leads the 4b** (72% vs 47% cleared), but the CIs still overlap. 98% recall on 284
  positives allows 5 misses, so a few emails swing the elimination number.
- **Prompt 2 moved the small models' default decision toward yes.** Default recall went up by
  12–14 points and elimination down by 7–11 (§5).
- **JSON ranks worse than lp in every model, in either order.** The 27b jsonR now reaches 98%
  recall, but only through its most confident "no" answers. The small models' JSON still can't
  reach it without keeping nearly everything (§2).
- **The golden set is harder than the sweep by design.** On its real emails alone, lp AUROC is
  0.981 / 0.997 / 1.000; the synthetic close calls and hard negatives carry the difficulty. (The
  real rows were also chosen to favor confident pre-labels, so real-only numbers flatter.)

## 2. JSON verdicts are one operating point, not a score

- **The confidence is nearly binary.** Each JSON run used 2–5 distinct confidence values
  (27b json: 0.95 ×265, 1.0 ×213, 0.98 ×15). None of the 2,966 JSON scores falls between 0.2
  and 0.8.
- **It isn't calibrated where it matters.** When the 9b json says "not responsive" with
  confidence ≥ 0.95, 22% of those 236 emails are responsive. Because some responsive emails get a
  score of 0, the 4b and 9b JSON runs can't reach 98% recall without keeping everything.
- **The 27b's 98% recall is an artifact of the confidence values.** Both of its JSON runs reach
  98% recall only at a threshold of 0.05, which keeps every "no" given with confidence 0.95. What
  they clear is the "no" answers given with confidence 0.98 or 1.0: 28% of negatives for json,
  66% for jsonR.
- **At the same operating point, lp is as good or better.** Set the lp threshold so lp says yes
  exactly as often as the JSON verdicts do. lp's recall and elimination are then 1–3 points
  higher in five of the six JSON runs and equal in the sixth. Where the two disagree, lp is right
  112 times and JSON 64. (With prompt 1 they split about evenly.)

| JSON run | JSON: recall / eliminated | lp at the same yes-rate | disagreements: lp right / JSON right |
|---|---|---|---|
| 4b json | 90.5% / 76.3% | 92.3% / 78.7% | 12 / 2 |
| 4b jsonR | 87.3% / 80.6% | 88.4% / 82.0% | 29 / 23 |
| 9b json | 81.3% / 86.7% | 83.1% / 89.1% | 18 / 8 |
| 9b jsonR | 92.6% / 76.8% | 94.3% / 79.1% | 28 / 18 |
| 27b json | 95.4% / 86.6% | 95.4% / 86.6% | 5 / 5 |
| 27b jsonR | 94.7% / 81.9% | 96.8% / 84.8% | 20 / 8 |

  So the generated verdict adds no accuracy over an lp threshold, and lp also offers every
  other operating point. The 27b json's higher default recall (95% vs lp's 93%) only reflects
  where the 0.5 cut sits; an lp threshold of 0.27 matches it exactly.
- **Cost:** JSON is 2.6–3.1× slower (lp 0.89 / 1.46 / 2.64 s vs json 2.75 / 4.43 / 6.80 s).
  Prefill is the same in every mode. The difference is decoding about 100–130 tokens at
  59 / 36 / 29 tok/s. H1 predicted an order of magnitude; on this hardware it is about 3×,
  because prefill dominates.

## 3. Does reasoning first help?

In the json runs the verdict is the first key, so the model commits before writing any
reasoning. The jsonR runs make it reason first.

| model | AUROC json → jsonR | default recall | default eliminated | verdicts agree | jsonR right where they differ |
|---|---|---|---|---|---|
| 4b | 0.833 → 0.870 | 90% → 87% | 76% → 81% | 449 / 495 | 23 of 46 |
| 9b | 0.871 → 0.879 | 81% → 93% | 87% → 77% | 425 / 494 | 40 of 69 |
| 27b | 0.947 → 0.951 | 95% → 95% | 87% → 82% | 466 / 492 | 7 of 26 |

- **Reasoning first moves the small models' cutoff.** With prompt 1 it made the 4b much stricter
  (default recall 79% → 53%). With prompt 2 that is mostly gone: 10 more hard negatives cleared
  (43 → 53) and 4 fewer real positives caught (131 → 127). The 9b still becomes more lenient: it
  catches 18 more real positives and 11 more close calls (118 → 136, 35 → 46) but clears 17 fewer
  hard negatives (63 → 46). The 27b changes little, and where its two verdicts differ the
  reasoning-first one is wrong 19 times out of 26.
- **It doesn't help them sort.** At a matched yes-rate, jsonR is no better than an lp threshold
  either (table in §2: 29/23, 28/18, 20/8). Reasoning changes where the model draws the line,
  not how well it orders the emails.
- **By email type** (matched yes-rate, both requests), there's one consistent JSON advantage,
  and only in the 27b: wrong-date hard negatives. The 27b json and jsonR each clear 18 of 19.
  lp at the same yes-rates clears 15 and 13. The advantage shows up with the verdict first too,
  so it comes from the JSON framing, not from reasoning before the answer. The small models show
  no consistent gain (of 20: 4b json 2 vs lp 5, 4b jsonR 8 vs 8, 9b json 9 vs 13, 9b jsonR 7 vs 4).
- **Reasoning first hurts the 27b on keywords in a signature or newsletter.** It clears 10 of 20,
  against 17 for verdict-first json and 17 for lp at the same yes-rate. It is also slightly worse
  on forwarded emails with no content (12 of 17 vs 14 and 14).
- **Answer:** forcing reasoning first doesn't buy accuracy on any email type consistently. It
  takes 3–19% longer than verdict-first JSON (4b 2.75 → 2.91 s, 9b 4.43 → 5.26 s, 27b
  6.80 → 7.01 s).

## 4. Where the score breaks: by kind

Share flagged responsive at each run's 98%-recall threshold, both requests. For + groups this is
recall; for − groups it is the share that slips through the screen.

| kind | label | n | 4b lp | 9b lp | 27b lp | 27b jsonR |
|---|---|---|---|---|---|---|
| real_positive | + | 150 | 97% | 98% | 97% | 99% |
| close_call_positive | + | 50 | 100% | 98% | 100% | 100% |
| privileged_positive | + | 40 | 100% | 100% | 98% | 100% |
| exempt_other_positive | + | 40 | 100% | 100% | 100% | 100% |
| hard_negative_flipped | + | 4 | 100% | 75% | 100% | 100% |
| real_negative | − | 120 | 31% | 4% | 0% | 9% |
| hard_negative | − | 91 | 82% | 60% | 56% | 67% |

- **Responsiveness is not confused with exemption.** At the default decision, the lp runs catch
  98–100% of privileged and personnel/deliberative positives, against 90–93% of ordinary real
  positives. The "don't consider exemption" instruction holds.
- **Hard negatives are where the screening cost goes.** The 27b lp clears every real
  cross-request negative, but more than half of the hard negatives still pass. By recipe
  (slip-through at the 98% threshold, 4b / 9b / 27b lp):

  | recipe | 4b | 9b | 27b |
  |---|---|---|---|
  | keyword in an unrelated sense | 95% | 53% | 63% |
  | same subject, wrong date | 100% | 90% | 50% |
  | keyword only in a signature or newsletter | 75% | 50% | 50% |
  | forwarded with no content | 59% | 35% | 41% |
  | same people, different subject | 80% | 73% | 80% |
- **Date reasoning is the clearest size effect.** At the default decision the 27b passes 15% of
  wrong-date emails; the 4b and 9b pass 90% and 80%.
- **Same people, different subject** now includes the nine purely personal 25-3152 emails that
  went back to non-responsive (§9). Prompt 2's carve-out was meant for them, and it doesn't
  work (§5).
- **The four flipped hard negatives** are 24-409 work emails that the human judged responsive:
  two forwards between the same people, an auto-reply and a meeting acceptance.

## 5. The named-correspondent rule (prompt 2)

**Why.** With prompt 1, the 27b lp's 98% threshold was very low (0.017) because a handful of
positives scored near zero. 9 of its 11 lowest-scored positives were 25-3152 emails that are
responsive only because of who sent or received them: a TAC meeting agenda, a DA event
invitation, a password reset, a SANDAG legislative update, a planning-group chair meeting hold.
The JSON modes scored them as low. Both read 25-3152 as a subject-matter request, but it asks
for communications of "any member" of the Alpine Community Planning Group, whatever the subject.
Prompt 2 adds one sentence for every request (the bold sentence in Setup). It says an email to or
from a named person or group is responsive whatever its subject, unless it is purely personal
(*City of San Jose v. Superior Court* (2017) 2 Cal.5th 608; §9).

**Effect on lp.** Both prompts were run on Ollama 0.40.13 with render 2, so only the prompt
differs (report §9). The comparison is paired over all pairs; the +roster rows cover 25-3152
only (249 pairs).

| run | AUROC | ΔAUROC [95% CI] | eliminated @98% | default recall | default eliminated |
|---|---|---|---|---|---|
| 4b lp | 0.900 → 0.923 | +0.023 [+0.008, +0.041] | 48% → 47% | 81% → 95% | 84% → 73% |
| 9b lp | 0.937 → 0.943 | +0.005 [−0.008, +0.019] | 68% → 72% | 81% → 93% | 88% → 81% |
| 27b lp | 0.974 → 0.975 | +0.002 [−0.002, +0.006] | 77% → 76% | 88% → 93% | 94% → 91% |
| 4b lp +roster | 0.911 → 0.948 | +0.037 [+0.018, +0.059] | 54% → 68% | 91% → 99% | 72% → 65% |
| 9b lp +roster | 0.943 → 0.963 | +0.020 [+0.005, +0.040] | 63% → 71% | 91% → 97% | 82% → 73% |
| **27b lp +roster** | **0.972 → 0.989** | +0.017 [+0.009, +0.027] | **80% → 91%** | 78% → 87% | 95% → 95% |

- **The rule only works when the model knows who the members are.** 25-3152 doesn't name them.
  - **Without the roster,** the 27b's AUROC doesn't move. Its correspondent-only misses stay near
    zero: a reply about the TAC agenda 0.008, the chair-meeting hold 0.050, the SANDAG
    legislative update 0.057. 11 of its 12 lowest-scored positives are still 25-3152 emails of
    this kind.
  - **With the roster,** the same emails rise: the TAC agenda reply from 0.026 to 0.17, the
    chair-meeting hold from 0.036 to 0.27. The 98% threshold on 25-3152 goes from 0.014 to
    0.078, and 91% of the non-responsive emails are cleared instead of 80%. Default recall goes
    from 78% to 87% with no loss of elimination.
- **With the roster, the 27b's lowest positives are now "one member among many" emails.** These
  are APG agendas and SANDAG meeting reports sent to 23–29 recipients, Alpine's chair among
  them. They score 0.07–0.08. Synthetic 14:02, kept in the set to test exactly this case (§9),
  scores lowest.
- **The 27b applies the rule only where it fits.** On 25-3152 (without the roster) its mean score
  rises 0.09 on positives and 0.01 on negatives. 24-409 is a topical request the rule doesn't
  address: there, scores rise slightly on both (+0.04 positives, +0.06 negatives) and AUROC is
  unchanged (0.994 → 0.992).
- **The small models take it as a general push toward yes.**
  - The 4b's mean score rises 0.09–0.16 on positives and negatives alike, in both requests.
  - The 9b's rises 0.12–0.17 on 25-3152 and about 0.04 on 24-409.
  - Their default recall jumps 12–14 points, at a cost of 7–11 points of default elimination.
  - Their ranking barely improves: without the roster, only the 4b's AUROC gain is clear of
    zero, and at 98% recall the threshold just moves up.
- **The purely-personal exception does nothing.** The nine purely personal 25-3152 emails are a
  fishing trip, a brunch reservation, a cancelled BBQ, a pet-sitting inquiry and the like. They
  have been hard negatives since §9, and they don't score lower under prompt 2. Emails passed at
  the default decision, of 9, prompt 1 → 2:

  | model | without roster | with roster |
  |---|---|---|
  | 4b | 5 → 9 | 9 → 9 |
  | 9b | 1 → 4 | 5 → 6 |
  | 27b | 4 → 4 (mean 0.46 → 0.49) | 5 → 5 |

  At its 98% threshold the 27b passes 8 of 9 under either prompt. The models apply the rule and
  skip the exception.
- **JSON modes show the same pattern.** Their prompt-1 baselines are the October runs (Ollama
  0.32.14, render 1), so these comparisons also span the upgrade (§8).
  - Without the roster, ΔAUROC is within ±0.02 except for the 9b json (+0.041 [+0.015, +0.070]).
  - With the roster, the 27b json goes from 0.956 to 0.989 (default recall 86% → 98%) and the
    27b jsonR from 0.959 to 0.981.
  - Without the roster, the small models' default recall rises 11–34 points; the largest jump
    is the 4b jsonR's, 53% → 87%.

## 6. Roster ablation (25-3152)

Same 249 pairs, with the planning-group roster (members, roles, email addresses) appended to the
request. Paired bootstrap CIs; each pair of runs uses the same backend setting.

| run | AUROC | ΔAUROC [95% CI] | eliminated @98% recall | default recall |
|---|---|---|---|---|
| 4b lp | 0.885 → 0.948 | +0.063 [+0.036, +0.097] | 27% → 68% | 95% → 99% |
| 9b lp | 0.927 → 0.963 | +0.037 [+0.015, +0.064] | 69% → 71% | 95% → 97% |
| **27b lp** | **0.955 → 0.989** | +0.034 [+0.014, +0.059] | **74% → 91%** | 89% → 87% |
| 4b json | 0.789 → 0.854 | +0.065 [+0.032, +0.100] | 10% → 17% | 91% → 96% |
| 9b json | 0.859 → 0.890 | +0.032 [−0.012, +0.073] | 0% → 0% | 81% → 94% |
| 27b json | 0.924 → 0.990 | +0.066 [+0.037, +0.097] | 11% → 57% | 92% → 98% |
| 4b jsonR | 0.851 → 0.909 | +0.058 [+0.014, +0.103] | 0% → 0% | 85% → 89% |
| 9b jsonR | 0.861 → 0.905 | +0.043 [+0.004, +0.085] | 0% → 58% | 93% → 98% |
| 27b jsonR | 0.940 → 0.980 | +0.040 [+0.020, +0.062] | 61% → 76% | 89% → 92% |

- **The roster helps every model in every mode.** The CI excludes zero in all but the 9b json.
- **Small models gain on positives; the 27b gains on negatives.** With the roster, the 4b and 9b
  lp score positives up to 0.12 higher by kind, while negatives barely move (−0.02 to +0.02). The
  27b's positives move a little (+0.03 real, +0.07 close calls). Its hard negatives drop by 0.16
  (lp and jsonR) and 0.20 (json).
- **With prompt 2, the roster is what makes the rule work** (§5).
- **Cost:** the roster adds 1,330 tokens to the shared request prefix.
  - On Ollama 0.40.13 the 27b's prefix cache covers it, so the roster costs the 27b nothing
    measurable: 2.34 → 2.23 s per email on these pairs. On 0.32.14 it added 0.9 s (§8).
  - At batch 8192 the 4b and 9b get no prefix cache (§7), so they pay for the full roster on
    every email. lp goes from 0.90 to 1.78 s (4b) and from 1.48 to 2.75 s (9b).

## 7. A GPU backend fault in the first 4b and 9b runs

*The numbers in this section are from October: prompt 1, Ollama 0.32.14, the 2026-10-07 labels,
496 pairs. On Ollama 0.40.13, see the end of the section and §8.*

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
- **On Ollama 0.40.13**, at batch 8192 the 4b and 9b reproduce their October scores more closely
  than the GPU and CPU runs agree with each other. The long prompts show no extra difference
  (§8), so the fix still holds. The default batch hasn't been retested, so it isn't known
  whether the upgrade fixed the fault itself. At batch 8192 these two models still get no prefix
  cache: their roster prompts take proportionally longer to prefill.

## 8. Ollama 0.32.14 → 0.40.13

Ollama was upgraded after the October runs and before the prompt-2 runs; the model files are
identical. To separate the upgrade from the prompt change, the six lp configurations were rerun
with prompt 1 on 0.40.13 (`runs/golden_*_logprob_p1o40*`). They are compared with the October
runs on the 480 pairs whose rendering didn't change (`golden_report.py --prompt 1`, report §8;
242 of 249 for the roster runs).

| run | AUROC 0.32.14 → 0.40.13 | eliminated @98% | mean \|Δ\|, prompts ≤ 2,048 tok | > 2,048 tok | pairs with \|Δ\| > 0.1 |
|---|---|---|---|---|---|
| 4b lp | 0.896 → 0.895 | 49% → 46% | 0.026 | 0.032 | 16 of 480 |
| 9b lp | 0.937 → 0.936 | 70% → 67% | 0.033 | 0.024 | 25 of 480 |
| 27b lp | 0.972 → 0.973 | 77% → 76% | 0.013 | 0.007 | 6 of 480 |
| 4b lp +roster | 0.909 → 0.908 | 57% → 54% | — | 0.029 | 7 of 242 |
| 9b lp +roster | 0.945 → 0.943 | 66% → 63% | — | 0.025 | 7 of 242 |
| 27b lp +roster | 0.970 → 0.971 | 80% → 80% | — | 0.008 | 3 of 242 |

- **Scores move a little; rankings don't.** For the 27b, the per-pair differences are the size of
  run-to-run noise on one version (cached vs reloaded: 0.011 / 0.008, §7). For the 4b and 9b they
  are new: on 0.32.14 their batch-8192 runs reproduced exactly. But they're smaller than GPU vs
  CPU (0.044–0.059), and the same for short and long prompts, so the fault hasn't returned.
- **It is faster.** lp per email with prompt 1: 4b 0.98 → 0.85 s, 9b 1.59 → 1.40 s, 27b
  3.32 → 2.66 s. The 27b with the roster went from 4.08 to 2.25 s, because the prefix cache now
  covers the roster (§6).
- **What isn't separated:** the JSON modes weren't rerun with prompt 1 on 0.40.13. Their prompt
  comparisons (§5) include the upgrade, and so does any latency comparison with the October
  numbers.

## 9. Labels re-checked (resolved 2026-10-31)

Readers of the model reasoning flagged these golden labels and inputs. All eight went through the
Recheck section of the adjudication page (2026-10-28). The human's call is in bold after each
entry; entries corrected on a second reading are marked.

- **25-3152 synthetic 15:05 and 15:09** (flipped to responsive): purely personal emails. 15:05 is
  SDG&E writing to the chair about the service upgrade at his own home (item 4); 15:09 is the
  chair forwarding a cookie-sale form to the members (item 2). *(Corrected: 15:05 isn't between
  members.)* Is a purely personal message a public record at all under *City of San Jose v.
  Superior Court* (2017) 2 Cal.5th 608? **No: both go back to non-responsive hard negatives.
  The same call was then applied to the other seven 25-3152 flips, which are just as personal:
  15:01 (the chair's TV interview about his own home insurance), 15:02 (misaddressed rooftop
  lease emails), 15:03 (a fishing trip between two members), 15:04 (a brunch reservation sent
  to the wrong Martha), 15:06 (phishing from the chair's hacked account), 15:07 (a pet-sitting
  inquiry) and 15:08 (the chair cancelling a backyard BBQ).**
- **25-3152 real 48518148** (responsive): the planning-group chair was bcc'd; only the
  Delivered-To header shows it, and the parser dropped it ("To: None"). **Fixed 2026-10-28:**
  `parse_emails.py` now keeps the Bcc header (66 emails) and any Delivered-To mailbox not already
  in To/Cc/Bcc (109 emails), and `score.py` renders both (`"render": 2` in run.json). This changes
  15 golden prompts, all emails from the 25-3152 production (7 positives for 25-3152, 8 negatives
  for 24-409). The October scores used the old rendering; every table in §1–§6 uses the new one.
  **Responsive, confirmed.**
- **25-3152 synthetic 14:02** (close call, responsive): the added ACPG mention is at character
  8,778, past the 8,000-character body cap, so no model sees it. *(Corrected: the chair is still
  visible as one of 27 To recipients, which makes it responsive under item 4 from the headers
  alone.)* **Kept, as a test of whether one member among many recipients is enough.**
- **24-409 synthetic 06:01** (flipped to responsive): an out-of-office reply; the call is
  debatable. **Flip confirmed: responsive.**
- **24-409 synthetic 02:01** (close call, responsive): the only hook is a quoted signature line
  ("UC San Diego - Dept of Urban Studies and Planning"). *(Corrected: it is at character 15,664,
  past the body cap, so no model sees it either; the visible part has UCSD only in email
  addresses. The verifier also asked to remove a sentence the edit invented; it is still there.)*
  **Kept, to count a miss the system would really make. The invented sentence stays.**
- **24-409 real 33732508** (responsive): the label is right but its rationale isn't; the hits are
  attachment names ("OSEJ_RWER_Fact Sheet", "UCSD_SDC RWER… Handout") about 6,200 characters in.
  **Responsive, confirmed.**
- **24-409 synthetic 07:09** (hard negative): "RDF" here means refuse-derived fuel, not the
  request's sense, but the refinement reads like search terms, so a literal hit is arguable.
  Minor. **Dropped from the golden set.**

## 10. Hypothesis status (golden set)

| | status |
|---|---|
| H1 latency ≪ JSON | supported in direction: 2.6–3.1×, not 10×, on the Strix Halo (prefill dominates) |
| H2 ≥98% recall with >50% eliminated | met by 9b lp (72%, CI 65–78%) and 27b lp (76%, CI 70–88%); 27b jsonR formally (66%, CI 59–73%), only through its confidence-1.0 "no" answers (§2); 4b lp not (47%, CI 39–69%). On 25-3152 with the roster, the 27b lp clears 91% |
| H3 score tracks error rate | lp yes (the share of positives rises with the score bucket in every model); JSON no (no scores between 0.2 and 0.8; 22% responsive among the 9b's "confident no" answers) |

## 11. Caveats

- **One run per configuration.** Elimination at 98% recall moves several points with a few
  borderline emails. With prompt 1, the 4b's GPU and CPU runs cleared 51% and 57%.
- **Prompt 2 was written after reading this set's misses,** so its gains here are in-sample.
- **The JSON prompt comparisons span the Ollama upgrade** (§8).
- **Some labels have no human check.** Real rows favor confident pre-labels. Unflagged synthetic
  emails carry Opus's intended label with verifier agreement.
- **25-3152 has 140 positives:** 98% recall there allows 2 misses.
- **Strix Halo only.** The laptop is CPU-only (the path that was clean here) but hasn't been
  checked for the fault.

## 12. Next

1. ~~Resolve the §9 labels and rebuild the golden set.~~ Done 2026-10-31.
2. ~~Prompt revision for correspondent-scoped requests.~~ Done 2026-11-01 (§5). The rule helps
   once the model has a roster; the purely-personal exception has no effect.
3. Decide how to handle purely personal emails between named people. As written, the models
   ignore the exception. The options are more prompt work (for example a worked example) or
   leaving them to human review.
4. For correspondent-scoped requests, supply the member list as part of the request. Without it
   the rule doesn't help.
5. Laptop runs, starting with the leak and garbling probes from §7.
6. Jev (API) and a Jev-like open model on the same pairs (SPEC §14.1).
7. Optional: rerun the §7 probes at the default batch on Ollama 0.40.13. If the fault is fixed
   upstream, the 4b and 9b get the prefix cache back.
