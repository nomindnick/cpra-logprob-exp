# Golden set — stock Qwen, decision models and a hosted API on two CPRA requests

**Date:** 2026-10-07; refreshed 2026-11-01 (prompt 2) and 2026-11-11 (final labels, d3 and Jev, default-batch 4b/9b, the analysis in `docs/analysis/`) · **Status:** golden-set comparison complete on the Strix Halo; one run per configuration
**Runs:** `runs/golden_*` (scores committed; the runs behind each table are listed at the top of the report)
**Report:** `uv run python scripts/golden_report.py` (§1–§9 tables, plus per-request and per-recipe detail); `--prompt 1` gives the same tables for the original prompt
**Analysis:** `scripts/analysis/*.py` print every table cited as [A1a], [B2.3], [E1b] and so on (branches A–E, follow-ups F1–F6). `docs/analysis/conclusions.md` explains the citation scheme; the branch files there explain each table but hold their numbers on the 2026-10-31 labels, so rerun the script for the current figure

Every table uses prompt 2 (§5), the labels as they stood on 2026-11-11 (§9), render 2 (Bcc and Delivered-To
headers) and Ollama 0.40.13, except §7 and §8, which keep their October numbers. The labels changed twice after
the 2026-11-01 version: five hard negatives were relabeled responsive on 2026-11-08, and one email was put back
in the set on 2026-11-11 (§9). **Every "eliminated at 98% recall" figure is in-sample:** the cutoff is chosen on
the same labels it is scored on. §11 asks what happens when it has to be set in advance. Earlier versions of this
document are in git history.

## Setup

496 (request, email) pairs over two requests, one designed pair per email (SPEC §14,
`data/golden/summary.json`). Labels are human-adjudicated. Opus pre-labeled 420 real emails, and
the human checked:

- every disagreement with production membership, plus a random spot check (81 of 81 confirmed);
- every synthetic email the verifier flagged (`docs/golden-adjudication.md`, local only);
- the labels questioned later by readers of the model reasoning and by the misses analysis (§9).

| | 24-409 (topical) | 25-3152 (correspondent-scoped) |
|---|---|---|
| real_positive / real_negative | 75 / 60 | 75 / 60 |
| close_call / privileged / exempt-other positives | 25 / 20 / 20 | 25 / 20 / 20 |
| hard_negative | 41 | 46 |
| hard_negative_flipped (synthetic "hard negative" the human judged responsive) | 6 | 3 |
| positives / negatives | 146 / 101 | 143 / 106 |

**Stock Qwen:** qwen3.5:4b, qwen3.5:9b, qwen3.8:27b (all Q4_K_M), Ollama 0.40.13 on ROCm 7.2,
`num_ctx=8192`, thinking off, temperature 0, single-stream. The logprob runs use Ollama's default batch,
which keeps the prefix cache. (The 4b/9b fault of §7 is gone on 0.40.13.) The 4b and 9b JSON runs use
`num_batch=8192`, so they get no prefix cache; the 27b JSON runs use the default. Three modes on identical inputs:

- **lp**: first-token P(yes)/(P(yes)+P(no)) (the sweep's method).
- **json**: the 2025 approach, a generated `{"responsive", "confidence", "reasoning"}` object
  with the verdict first. Scored as confidence if responsive, else 1 − confidence.
- **jsonR**: the same object with `reasoning` first, enforced by a JSON schema; the prompt says
  "Write the reasoning first, then decide." Every scored jsonR answer has its reasoning first.

**Decision models (§10):**

- **d3-4b, d3-9b, d3-27b**: the vLLM Semantic Router decision models built on the same bases (Qwen3.5-4B,
  Qwen3.5-9B, Qwen3.8-27B), at Q8_0, served locally through Ollama's `/v1/systemone` endpoint
  (`scripts/score_systemone.py`) with `num_ctx=8192` and `num_batch=8192`. Their attention is noncausal, so the
  whole prompt has to fit in one batch, and they don't reuse the request prefix. They return P(yes) directly.
- **Jev**: TypeSafe's hosted decision model (jev-1.14.0) through its API. Its scores have two decimals, and its
  wall time includes the network.
- Both get the request and the email as state fields (`cpra_request`, `email`) and the prompt-2 instructions as
  the question. Mode label: `noul`.

The system prompt for the stock models (`score.py`) is shown below; the user message holds the request and the
email. The bold sentence is new in prompt 2 (§5). The JSON modes replace the last sentence with the JSON
instructions.

> You are a public records analyst for a California county. You will be shown a California
> Public Records Act (CPRA) request and one email from the county's email system. Decide whether
> the email is responsive to the request, meaning it is a record the request is asking for.
> **If the request covers communications sent or received by named people or groups, an email to
> or from one of them is responsive whatever its subject, unless it is purely personal and has
> nothing to do with public business.** Do not consider whether the email might be exempt from
> disclosure; that is a separate question. Answer with a single word: yes or no.

"Default decision" = score ≥ 0.5 for lp, d3 and Jev; the verdict for json/jsonR. Unscored rows (unparseable
JSON): 5 of the 12,935 prompt-2 rows.

## 1. Headline

| run | AUROC [95% CI] | non-responsive eliminated @98% recall, in-sample [95% CI] | default decision: recall / eliminated | median s/email |
|---|---|---|---|---|
| 4b lp | 0.922 [0.898–0.945] | 53% [41–70%] | 94% / 74% | 0.50 |
| 9b lp | 0.945 [0.923–0.965] | 72% [65–81%] | 94% / 82% | 0.86 |
| **27b lp** | **0.977 [0.965–0.987]** | **77% [72–89%]** | 93% / 92% | 2.64 |
| d3-4b | 0.901 [0.872–0.924] | 55% [43–64%] | 94% / 66% | 0.88 |
| d3-9b | 0.957 [0.941–0.973] | 70% [63–80%] | 96% / 81% | 1.43 |
| **d3-27b** | **0.983 [0.974–0.990]** | **83% [76–87%]** | 99.7% / 80% | 4.66 |
| Jev | 0.917 [0.890–0.940] | 64% [56–71%] | 94% / 74% | 0.12 (network included) |
| 4b json | 0.831 [0.796–0.868] | 10% [6–14%] | 90% / 77% | 2.75 |
| 9b json | 0.869 [0.838–0.897] | 0% | 80% / 87% | 4.44 |
| 27b json | 0.950 [0.931–0.967] | 28% [22–35%] | 96% / 88% | 6.81 |
| 4b jsonR | 0.873 [0.839–0.906] | 0% | 87% / 82% | 2.91 |
| 9b jsonR | 0.888 [0.857–0.918] | 0% [0–71%] | 93% / 79% | 5.26 |
| 27b jsonR | 0.954 [0.937–0.967] | 67% [60–74%] | 95% / 83% | 7.01 |

CIs are bootstrap (1,000 resamples within each class). s/email is the median wall time per call, one email at a
time.

- **The two 27B models lead, and they can't be told apart.** d3-27b minus 27b lp: AUROC +0.006 [−0.002, +0.015],
  elim@98 +5.3 points [−5.8, +9.2] [E1b, E1c]. After a Holm correction over the 21 model pairs, d3-27b ranks above
  each of the other five, and 27b lp above all but d3-9b (Holm p 0.086). Below them, d3-9b ranks above 4b lp, Jev
  and d3-4b, and 9b lp above d3-4b. 4b lp, Jev and d3-4b can't be separated [E1b].
- **Elimination is noisier than ranking.** 98% recall on 289 positives allows 5 misses, so a few emails swing it.
  Only 8 of the 21 elim@98 differences survive Holm. 9b lp minus 4b lp (+19.3 points [+2.9, +32.4], Holm p 0.21)
  is not one of them. What does survive is the jump from 4b lp to either 27B model (+24.6 and +30.0) [E1c].
- **The pooled cutoff leaves one request short.** At the cutoff fitted on both requests together, every model
  misses 3 or more responsive emails on one request, where 98% allows 2. For 27b lp, d3-27b and Jev all five
  misses fall on 25-3152, so recall there is 96.5% [A1c]. The shortfall itself is arithmetic (5 > 2 + 2); how the
  misses bunch up is what carries information.
- **Real emails alone are nearly solved, but the real negatives are easy.** Real positives against real
  negatives give AUROC 0.982–1.000 [D1-1 (a)]. The real negatives are other requests' records, 118 of 120 outside
  the target's date window [D2-2]. Against in-window near misses the best models eliminate 43–48% (§14).
- **Prompt 2 moved the small stock models' default decision toward yes** (§5). **JSON ranks worse than lp in
  every model, in either order** (§2).

## 2. JSON verdicts are one operating point, not a score

- **The confidence is nearly binary.** Each JSON run used 2–5 distinct confidence values
  (27b json: 0.95 ×266, 1.0 ×213, 0.98 ×15). None of the 2,972 JSON scores falls between 0.2
  and 0.8.
- **It isn't calibrated where it matters.** When the 9b json says "not responsive" with
  confidence ≥ 0.95, 24% of those 237 emails are responsive. Some responsive emails get a score of
  exactly 0 (43 in the 9b json run, 20 in the 4b jsonR, 10 in the 9b jsonR), so those three runs reach 98% recall
  only at a cutoff of 0, which keeps every email [B2.1].
- **The 27b's 98% recall is an artifact of the confidence values.** Both of its JSON runs reach
  98% recall only at a threshold of 0.05, which keeps every "no" given with confidence 0.95. What
  they clear is the "no" answers given with confidence 0.98 or 1.0: 28% of negatives for json,
  67% for jsonR.
- **At the same operating point, lp is as good or better.** Set the lp threshold so lp says yes
  exactly as often as the JSON verdicts do. lp's recall and elimination are then 0.3–3 points
  higher in five of the six JSON runs and equal in the sixth. Where the two disagree, lp is right
  105 times and JSON 61.

| JSON run | JSON: recall / eliminated | lp at the same yes-rate | disagreements: lp right / JSON right |
|---|---|---|---|
| 4b json | 89.6% / 76.8% | 91.7% / 79.7% | 14 / 2 |
| 4b jsonR | 86.9% / 81.6% | 87.2% / 82.1% | 25 / 23 |
| 9b json | 80.3% / 87.0% | 81.7% / 88.9% | 15 / 7 |
| 9b jsonR | 92.7% / 78.7% | 94.4% / 81.2% | 26 / 16 |
| 27b json | 95.5% / 88.3% | 95.5% / 88.3% | 5 / 5 |
| 27b jsonR | 94.8% / 83.5% | 96.9% / 86.4% | 20 / 8 |

  So the generated verdict adds no accuracy over an lp threshold, and lp also offers every
  other operating point. The 27b json's higher default recall (96% vs lp's 93%) only reflects
  where the 0.5 cut sits; an lp threshold of 0.27 matches it exactly.
- **Cost.** Decoding the JSON answer alone (median 1,760–4,040 ms) takes longer than the whole lp call of the
  same model (504 / 855 / 2,639 ms) [E3a]. Median per email, lp 0.50 / 0.86 / 2.64 s against json
  2.75 / 4.44 / 6.81 s and jsonR 2.91 / 5.26 / 7.01 s: 2.6–2.7× slower at 27b and 5.2–6.2× at 4b and 9b. Part of the
  small models' gap is the JSON runs' batch-8192 prefill (855 vs 466 ms for the 4b, 1,430 vs 774 ms for the 9b);
  at 27b both use the default batch. Per 10,000 emails, a JSON run takes 7.9–20.7 h [B1.1].
- **Never on the speed/accuracy frontier.** In 2,000 bootstrap redraws no JSON run lies on the main-set frontier
  of median time against elimination, except the 27b json in 1% of them [E3c].
- **No rescue on shared errors.** The 27b jsonR says no to all 8 of the 25-3152 positives that three or more
  score models miss at 0.5. On the 53 negatives that five or more score models wrongly keep, the JSON runs say yes
  47–77% of the time, against 12–23% on all negatives [CJ].

## 3. Does reasoning first help?

In the json runs the verdict is the first key, so the model commits before writing any
reasoning. The jsonR runs make it reason first.

| model | AUROC json → jsonR | default recall | default eliminated | verdicts agree | jsonR right where they differ |
|---|---|---|---|---|---|
| 4b | 0.831 → 0.873 | 90% → 87% | 77% → 82% | 450 / 496 | 24 of 46 |
| 9b | 0.869 → 0.888 | 80% → 93% | 87% → 79% | 426 / 495 | 44 of 69 |
| 27b | 0.950 → 0.954 | 96% → 95% | 88% → 83% | 467 / 493 | 7 of 26 |

- **Reasoning first moves the small models' cutoff.** With prompt 1 it made the 4b much stricter
  (default recall 78% → 53%). With prompt 2 that is mostly gone: 11 more hard negatives cleared
  (41 → 52) and 4 fewer real positives caught (131 → 127). The 9b still becomes more lenient: it
  catches 18 more real positives and 11 more close calls (118 → 136, 35 → 46) but clears 13 fewer
  hard negatives (60 → 47). The 27b changes little, and where its two verdicts differ the
  reasoning-first one is wrong 19 times out of 26.
- **It doesn't help them sort.** At a matched yes-rate, jsonR is no better than an lp threshold
  either (table in §2: 25/23, 26/16, 20/8). Reasoning changes where the model draws the line,
  not how well it orders the emails.
- **By email type** (matched yes-rate, both requests), there's one consistent JSON advantage,
  and only in the 27b: wrong-date hard negatives. The 27b json and jsonR each clear 18 of 19.
  lp at the same yes-rates clears 15 and 13. The advantage shows up with the verdict first too,
  so it comes from the JSON framing, not from reasoning before the answer. The small models show
  no consistent gain (of 20: 4b json 2 vs lp 6, 4b jsonR 8 vs 9, 9b json 9 vs 11, 9b jsonR 7 vs 3).
- **Reasoning first hurts the 27b on keywords in a signature or newsletter.** It clears 10 of 20,
  against 17 for verdict-first json and 17 for lp at the same yes-rate. It is also slightly worse
  on forwarded emails with no content (12 of 17 vs 14 and 14).
- **Answer:** forcing reasoning first doesn't buy accuracy on any email type consistently. It
  takes 3–19% longer than verdict-first JSON (4b 2.75 → 2.91 s, 9b 4.44 → 5.26 s, 27b
  6.81 → 7.01 s).

## 4. Where the score breaks: by kind

Share flagged responsive at each run's 98%-recall threshold, both requests. For + groups this is
recall; for − groups it is the share that slips through the screen.

| kind | label | n | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev |
|---|---|---|---|---|---|---|---|---|---|
| real_positive | + | 150 | 97% | 98% | 97% | 97% | 98% | 97% | 97% |
| close_call_positive | + | 50 | 100% | 98% | 100% | 98% | 96% | 100% | 98% |
| privileged_positive | + | 40 | 100% | 100% | 98% | 100% | 100% | 100% | 100% |
| exempt_other_positive | + | 40 | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| hard_negative_flipped | + | 9 | 100% | 89% | 100% | 100% | 100% | 100% | 100% |
| real_negative | − | 120 | 21% | 4% | 0% | 15% | 1% | 0% | 8% |
| hard_negative | − | 87 | 84% | 61% | 54% | 87% | 71% | 41% | 74% |

- **Responsiveness is not confused with exemption.** At the default decision, the lp runs catch
  98–100% of privileged and personnel/deliberative positives, against 90–93% of ordinary real
  positives. The "don't consider exemption" instruction holds.
- **Hard negatives are where the screening cost goes.** 27b lp and d3-27b clear every real cross-request
  negative, but 54% and 41% of the hard negatives still pass. Slip-through by recipe at each model's 98%
  threshold [E2a]:

  | recipe | n | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev |
  |---|---|---|---|---|---|---|---|---|
  | same subject, wrong date | 20 | 100% | 90% | 50% | 100% | 85% | 15% | 95% |
  | keyword in an unrelated sense | 20 | 95% | 60% | 65% | 90% | 80% | 70% | 75% |
  | keyword only in a signature or newsletter | 20 | 75% | 50% | 50% | 70% | 50% | 35% | 75% |
  | forwarded with no content | 17 | 71% | 41% | 41% | 82% | 59% | 35% | 47% |
  | same people, different subject | 10 | 70% | 60% | 70% | 100% | 90% | 60% | 70% |
- **Date reasoning is the clearest size effect.** At the default decision the 27b lp and d3-27b each pass 15% of
  wrong-date emails; the 4b and 9b lp pass 90% and 85%, Jev 90%. At its 98% threshold d3-27b passes 3 of 20,
  against 19 for Jev (Holm p 5.8e-04) and 10 for 27b lp (exact p 0.016, Holm 0.19, so not established) [E2b].
- **Where the headline elimination comes from.** Real negatives are 70–90% of the negatives each score model
  clears at its 98% threshold, against 58% of all negatives [D1-7].
- **The emails most models wrongly keep are all synthetic.** 53 hard negatives are kept by five or more of the
  seven score models at their 98% thresholds; no real negative is kept by more than three [C2b]. By recipe:
  wrong date 17 of 20, keyword in an unrelated sense 14 of 20, same people 7 of 10, signature or newsletter
  9 of 20, forwarded 6 of 17. Every one of the 53 labels holds on a full re-read [C3b].
- **Same people, different subject** includes the six 25-3152 emails that are still purely personal (§9).
  Prompt 2's carve-out was meant for them, and no model applies it reliably (§5).
- **The nine flipped hard negatives** are emails the human judged responsive. Six are 24-409 work emails with a
  Geosyntec address on the thread: two forwards, meeting logistics, a team volunteer outing, an auto-reply and
  a meeting acceptance. Three are 25-3152 emails to or from the chair (§9). Every score model flags all nine at
  its 98% threshold except the 9b lp (8).

## 5. The named-correspondent rule (prompt 2)

**Why.** With prompt 1, the 27b lp's 98% threshold was very low (0.017 in October) because a handful of
positives scored near zero. 9 of its 11 lowest-scored positives were 25-3152 emails that are
responsive only because of who sent or received them: a TAC meeting agenda, a DA event
invitation, a password reset, a SANDAG legislative update, a planning-group chair meeting hold.
The JSON modes scored them as low. Both read 25-3152 as a subject-matter request, but it asks
for communications of "any member" of the Alpine Community Planning Group, whatever the subject.
Prompt 2 adds one sentence for every request (the bold sentence in Setup). It says an email to or
from a named person or group is responsive whatever its subject, unless it is purely personal
(*City of San Jose v. Superior Court* (2017) 2 Cal.5th 608; §9).

**Effect on lp.** Both prompts were run on Ollama 0.40.13 with render 2 and the same batch setting, so only the
prompt differs. The 4b and 9b rows compare their batch-8192 runs of both prompts, because no default-batch
prompt-1 run exists; the main tables use their default-batch prompt-2 runs (§7). Paired over all pairs; the
+roster rows cover 25-3152 only (249 pairs).

| run | AUROC | ΔAUROC [95% CI] | eliminated @98% | default recall | default eliminated |
|---|---|---|---|---|---|
| 4b lp | 0.897 → 0.924 | +0.027 [+0.012, +0.044] | 45% → 48% | 80% → 95% | 84% → 73% |
| 9b lp | 0.937 → 0.946 | +0.008 [−0.006, +0.021] | 69% → 73% | 80% → 93% | 88% → 83% |
| 27b lp | 0.975 → 0.977 | +0.002 [−0.002, +0.006] | 78% → 77% | 87% → 93% | 95% → 92% |
| 4b lp +roster | 0.921 → 0.956 | +0.035 [+0.014, +0.056] | 56% → 70% | 92% → 99% | 75% → 67% |
| 9b lp +roster | 0.949 → 0.968 | +0.019 [+0.004, +0.038] | 65% → 73% | 90% → 97% | 83% → 75% |
| **27b lp +roster** | **0.978 → 0.994** | +0.016 [+0.008, +0.027] | **82% → 93%** | 78% → 87% | 97% → 98% |

- **The rule only works when the model knows who the members are.** 25-3152 doesn't name them.
  - **Without the roster,** the 27b's AUROC on 25-3152 rises only a little (0.950 → 0.961, +0.012
    [+0.003, +0.022]) [L-3]. Its correspondent-only misses stay near zero: a reply about the TAC
    agenda 0.008, the chair-meeting hold 0.050, the SANDAG legislative update 0.057. 11 of its 12
    lowest-scored positives are still 25-3152 emails of this kind: TAC and APG agendas, SANDAG
    reports, a chair-meeting hold, a password reset.
  - **With the roster,** the same emails rise: the TAC agenda reply from 0.026 to 0.17, the
    chair-meeting hold from 0.036 to 0.27. The 98% threshold on 25-3152 goes from 0.014 to
    0.078, and 93% of the non-responsive emails are cleared instead of 82%. Default recall goes
    from 78% to 87% with no loss of elimination.
- **With the roster, the 27b's lowest positives are "one member among many" emails.** These
  are APG agendas and SANDAG meeting reports sent to 23–27 recipients, Alpine's chair among
  them. They score 0.07–0.08. Synthetic 14:02, kept in the set to test exactly this case (§9),
  scores lowest.
- **The 27b applies the rule only where it fits.** On 25-3152 (without the roster) its mean score
  rises 0.09 on positives and 0.01 on negatives. 24-409 is a topical request the rule doesn't
  address: there, scores rise slightly on both (+0.04 positives, +0.05 negatives) and AUROC is
  unchanged (0.992 → 0.991).
- **The small models take it as a general push toward yes.**
  - The 4b's mean score rises 0.09–0.16 on positives and negatives alike, in both requests.
  - The 9b's rises 0.12–0.17 on 25-3152 and about 0.04 on 24-409.
  - Their default recall jumps 13–15 points, at a cost of 5–11 points of default elimination.
  - Their ranking barely improves: without the roster, only the 4b's AUROC gain is clear of
    zero, and at 98% recall the threshold just moves up.
- **The purely-personal exception does nothing.** The six emails that are still purely personal (§9) are a
  fishing trip, a brunch reservation, an SDG&E notice about the chair's home, a pet-sitting inquiry, a cancelled
  BBQ and a cookie-sale form. Emails passed at the default decision, of 6, prompt 1 → 2:

  | model | without roster | with roster |
  |---|---|---|
  | 4b | 4 → 6 | 6 → 6 |
  | 9b | 0 → 1 | 3 → 3 |
  | 27b | 1 → 1 (mean 0.36 → 0.33) | 3 → 2 |

  At its 98% threshold the 27b passes 5 of 6 under either prompt, with or without the roster. The decision models
  fare no better at 0.5: d3-27b passes 3 of 6 without the roster and 5 with it, Jev 2 and 3. The models apply
  the rule and skip the exception.
- **It may leak into topical requests** (low confidence). 24-409's item 4 needs a listed term as well as a named
  correspondent. The 27b jsonR says yes to 23 of the 101 24-409 negatives, and its reasoning cites a named person
  for every one of them; in 8 it concedes the subject is off-topic [CJ]. Three of the 53 emails most models
  wrongly keep are 24-409 emails with a named correspondent and no listed term [C3b]. Limiting the rule to
  correspondent-scoped requests would need a held-out request to test.
- **Its gains are in-sample.** Prompt 2 was written after reading this set's misses [L-3].
- **JSON modes show the same pattern.** Their prompt-1 baselines are the October runs (Ollama
  0.32.14, render 1), so these comparisons also span the upgrade (§8).
  - Without the roster, ΔAUROC is within ±0.03 except for the 9b json (+0.042 [+0.014, +0.072]).
  - With the roster, the 27b json goes from 0.960 to 0.992 (default recall 86% → 98%) and the
    27b jsonR from 0.971 to 0.986.
  - Without the roster, the small models' default recall rises 12–34 points; the largest jump
    is the 4b jsonR's, 53% → 87%.

## 6. Roster ablation (25-3152)

Same 249 pairs, with the planning-group roster (members, roles, email addresses) appended to the
request. Paired bootstrap CIs; each pair of runs uses the same backend setting.

| run | AUROC | ΔAUROC [95% CI] | eliminated @98% recall | default recall |
|---|---|---|---|---|
| 4b lp | 0.885 → 0.961 | +0.076 [+0.042, +0.109] | 30% → 77% | 95% → 99% |
| 9b lp | 0.931 → 0.967 | +0.035 [+0.013, +0.062] | 72% → 70% | 97% → 97% |
| **27b lp** | **0.961 → 0.994** | +0.033 [+0.012, +0.057] | **76% → 93%** | 90% → 87% |
| d3-4b | 0.909 → 0.976 | +0.067 [+0.038, +0.096] | 46% → 89% | 94% → 100% |
| d3-9b | 0.963 → 0.991 | +0.028 [+0.010, +0.052] | 76% → 92% | 99% → 100% |
| **d3-27b** | **0.988 → 1.000** | +0.012 [+0.005, +0.022] | **88% → 100%** | 99% → 100% |
| Jev | 0.921 → 0.972 | +0.051 [+0.026, +0.078] | 59% → 86% | 88% → 97% |
| 4b json | 0.792 → 0.864 | +0.072 [+0.041, +0.106] | 10% → 17% | 91% → 96% |
| 9b json | 0.857 → 0.903 | +0.046 [+0.006, +0.089] | 0% → 0% | 80% → 94% |
| 27b json | 0.929 → 0.993 | +0.064 [+0.038, +0.096] | 12% → 59% | 92% → 98% |
| 4b jsonR | 0.864 → 0.912 | +0.049 [+0.006, +0.095] | 0% → 0% | 85% → 89% |
| 9b jsonR | 0.871 → 0.916 | +0.045 [+0.004, +0.087] | 0% → 59% | 93% → 98% |
| 27b jsonR | 0.947 → 0.986 | +0.039 [+0.020, +0.061] | 63% → 78% | 90% → 92% |

- **The roster raises AUROC for every model in every mode;** all 13 CIs exclude zero. Elimination doesn't rise
  for every model: the 9b lp goes from 72% to 70%, and the 9b json and 4b jsonR stay at 0%.
- **With the roster, d3-27b separates the 249 pairs perfectly** (AUROC 1.000; every non-responsive email scores
  below every responsive one). That is in-sample, on one request.
- **Small models gain on positives; the 27B models gain on negatives.** With the roster, the 4b and 9b lp score
  positives up to 0.18 higher by kind, while negatives move −0.06 to +0.01. The 27b lp's positives move a little
  (+0.03 real, +0.07 close calls). Its hard negatives drop by 0.17 (0.22 for json, 0.17 for jsonR), and d3-27b's
  by 0.14.
- **Shared errors, like for like** (main runs restricted to these pairs, each run's own cutoff). The positives
  three or more models miss at 0.5 fall from 8 to 2. The negatives five or more keep fall from 23 to 5 at each
  run's 98% threshold and from 18 to 8 at 0.5. The 5 left at the threshold are all purely personal emails, so even
  with the roster the models don't apply that exception [C·V V5].
- **With prompt 2, the roster is what makes the rule work** (§5).
- **It shifts the cutoff.** On the same pairs the roster moves the 98% threshold from 0.3507 to 0.7588 (d3-4b),
  0.5427 to 0.8529 (d3-9b) and 0.5405 to 0.9060 (d3-27b) [A1a]. A roster-prompt cutoff reused on 24-409 missed
  84 of 146 responsive emails (d3-9b) and 76 (d3-4b) [A2b]. A prompt with a roster is a new configuration that
  needs its own cutoff.
- **Cost:** the roster adds 1,330 tokens to the shared request prefix.
  - **Stock Qwen reuses it.** Median prefill changed by −2 to +12 ms, against +618 to +3,401 ms if it had been
    reprocessed. Per email the 27b took 2.34 → 2.23 s (median) on these pairs [B1.3, E3b]. On 0.32.14 it added
    0.9 s (§8).
  - **d3 reprocesses it on every call:** +814 / +1,151 / +3,718 ms (4b / 9b / 27b), or +2.26 to +10.33 h per
    10,000 emails [B1.3]. The d3 runs use `num_batch=8192`, and at that setting the stock 4b and 9b JSON runs
    also stop reusing the prefix (4b jsonR +844 ms), so the runs show *that* d3 reprocesses the roster, not
    *why* [B·V concern 1].
  - **Jev:** +9 ms.
- **Limits.** One request, and the roster was compiled partly from that request's own production [D4 row 15].

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
  (§8), so the fix still holds.
- **The fault is gone on 0.40.13** (rechecked 2026-11-04, `runs/golden_dbcheck.sh`). At the default batch, cached
  and reloaded-every-call runs agree as closely on long prompts as on short ones: mean |Δ| 0.019 (≤ 2,048 tokens)
  vs 0.015 (longer) for the 4b, 0.023 vs 0.022 for the 9b. Their default-batch runs differ from the batch-8192 runs
  by mean |Δ| 0.017–0.031 (report §8). So the main 4b and 9b lp runs now use the default batch, which restores
  the prefix cache: 0.50 s vs 0.89 s per email (median) for the 4b, 0.86 s vs 1.47 s for the 9b. The October
  numbers above stay as the record of the fault. The batch setting alone moved the 4b's elimination at 98%
  recall from 48% to 53% at the same AUROC, a reminder of how much one run can vary (§16).

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
- **Noise on 0.40.13 itself.** Cached and reloaded-every-call runs of the same stock model differ by mean |Δ|
  0.018–0.023 and by up to 4.8 points of elimination at 98% recall (4b +roster: 77% vs 73%) [E5g, L-4]. The two
  runs take different serving paths, so this is an upper bound on pure repeat noise.

## 9. Labels re-checked (resolved 2026-10-31, 2026-11-08 and 2026-11-11)

Readers of the model reasoning, and later the misses analysis (`docs/analysis/C-misses.md`), flagged these golden
labels and inputs. The human's call is in bold after each entry; entries corrected on a second reading are marked.
The calls follow two rules:

- **Read the scope literally where the requester set it.** When a request covers the communications of named
  people or a named group, every such communication is in, including ones the requester plainly wasn't after.
  The requester chose the wide net; the agency's job is to use it.
- **Read an ambiguous term by the requester's evident intent.** A term the request uses in one sense ("RDF" for
  the Regional Decarbonization Framework, "GPS" for UCSD's Global Policy & Strategy) doesn't bring in emails that
  use it in another. The CPRA allows reasonable interpretation and puts a duty on the agency to help the requester
  clarify the request; producing wrong-sense keyword hits without asking would come close to bad faith.

The entries:

- **25-3152 synthetic 15:05 and 15:09** (flipped to responsive): purely personal emails. 15:05 is
  SDG&E writing to the chair about the service upgrade at his own home (item 4); 15:09 is the
  chair forwarding a cookie-sale form to the members (item 2). *(Corrected: 15:05 isn't between
  members.)* Is a purely personal message a public record at all under *City of San Jose v.
  Superior Court* (2017) 2 Cal.5th 608? **No: both go back to non-responsive hard negatives
  (2026-10-31). The same call was then applied to the other seven 25-3152 flips.** Four of them stay purely
  personal: 15:03 (a fishing trip between two members), 15:04 (a brunch reservation sent to the wrong Martha),
  15:07 (a pet-sitting inquiry) and 15:08 (the chair cancelling a backyard BBQ). The other three were revised
  (next entry).
- **25-3152 synthetic 15:01, 15:02 and 15:06** (purely personal by extension, 2026-10-31): 15:01 is the chair
  arranging a TV interview about his family's home insurance, signing as ACPG Chair; 15:02 is rooftop-lease mail
  from md7, an applicant before the group, misaddressed to him; 15:06 is the chair warning a County planner and
  an applicant's representative that his ACPG account was hacked. **Responsive (2026-11-08). Copying the chair
  brings an email in even when its subject would otherwise keep it out.**
- **One member among many recipients (19 positives of 25-3152).** On these the chair is one of 15–32 recipients,
  no roster member sends, and the group isn't named in the text the model sees: mostly Association of Planning
  Groups mailings, SANDAG meeting reports, Lakeside Planning Group threads and County TAC agendas. 15 are in the
  County's own production. Does a mass mailing count as a communication "between" a member and the sender?
  **Yes (2026-11-08), under the literal rule.** These emails set the 98% threshold for several models, and 7 of
  the 11 positives that three or more models miss at 0.5 are of this kind [C1d, C3b]. Under the narrower reading,
  d3-27b's lead over 27b lp on 25-3152 with the roster would have gone from +6.6 points of elimination to
  −0.8 [−12.0, +5.6] [F2].
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
  alone.)* **Kept, as a test of whether one member among many recipients is enough; confirmed with the 19 above.**
- **24-409 synthetic 03:01 and 03:09** (hard negatives, kept 2026-10-02). Geosyntec's Megan Otto thanks Gaines for
  a heads-up about a County parking-lot closure; Otto organizes a team food-bank volunteer shift. They share a
  pattern with four emails flipped earlier (03:04, 03:07, 06:01, 06:03): a Geosyntec address on the thread, a
  named County person, a date in the window, and no listed term [C3c]. Item 4 asks for anything "sent to or from
  … anyone at Geosyntec". **Responsive (2026-11-08), for consistency under the literal rule.**
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
- **24-409 synthetic 07:01, 07:02 and 07:03** (hard negatives, not adjudicated before). An OSEJ Zero Waste agenda
  among named County staff where "RDF proposal" means refuse-derived fuel; a heat-mapping flyer about
  GPS-linked temperature sensors; a meeting invite about GPS coordinates for storm-drain outfalls. **Not
  responsive (2026-11-11), under the intent rule.**
- **24-409 synthetic 07:09** (hard negative): "RDF" here means refuse-derived fuel, in a Fallbrook Climate Action
  Team invitation to Ruiz. **Dropped 2026-10-31 as an arguable literal hit; reinstated 2026-11-11 as a
  non-responsive hard negative under the intent rule.** It was scored on every full-set run on 2026-11-11
  (`runs/golden_0709.sh`).

The calls are in the adjudication page's database and exported to `data/golden/work/adjudications.json`;
`scripts/build_golden.py` rebuilds the set from them. Relabeled emails keep their scores, which come from the
models, not the labels.

## 10. Decision models: d3 and Jev against stock Qwen

- **What differs.** The d3 and stock packages differ in at least four ways at once: Q8_0 vs Q4_K_M weights, the
  serving runner, `num_batch` 8192 vs the default, and how the prompt is delivered (state fields and a question vs
  a system prompt and a user message) [E5a, B1.8]. A difference between d3 and stock is a difference between
  packages, not proof that d3's training or architecture is better.
- **d3-27b vs 27b lp, main set: no detectable difference.** AUROC +0.006 [−0.002, +0.015]; elim@98 +5.3
  [−5.8, +9.2] [E1b, E1c]; flagged per 10,000 hits −506 [−920, +552] in the workload scenario of §12 [B5.2].
- **On 25-3152, d3-27b is better.** Without the roster: AUROC 0.961 → 0.988 (+0.027 [+0.010, +0.046], Holm p
  0.010 among 24 package comparisons) and elim@98 76% → 88% (+11.3 [+4.7, +25.5], Holm 0.048) [E5b]. With the
  roster: AUROC 0.994 → 1.000 (Holm 0.034) and elim@98 93% → 100% (+6.6 [+1.9, +11.3], Holm 0.12 among the 24 and
  0.088 among the 21 model pairs) [E5b, E1c roster set]. On workload with the roster it flags 609 fewer per
  10,000 [146–1,029] [B5.5]. Part of the edge comes from the 19 "one member among many" positives; they stay
  responsive (§9), so it stands as measured.
- **On 24-409, no difference at 27B** (AUROC +0.001). d3-4b ranks worse than 4b lp there (−0.067, Holm 0.010)
  [E5b].
- **With the roster, d3-9b beats 9b lp:** +22.6 points of elimination [+10.4, +35.8], Holm 0.018 [E5b], and 2,046
  fewer flagged per 10,000 [929–3,144] [B5.5]. d3-9b + roster (8.0 h per 10,000) about matches 27b lp + roster
  (2,668 vs 2,581 flagged) [B4.2].
- **Wrong dates.** d3-27b passes 3 of 20 wrong-date emails at its 98% threshold, against 10 for 27b lp and 19 for
  Jev [E2b]. Within d3-27b, wrong-date emails pass less often than the other recipes' (15% vs 49%, Holm 0.053)
  [E2d]. Without a cutoff, its AUROC against the wrong-date emails is 0.988, against 0.975 for 27b lp (DeLong
  p 0.14) and 0.679 for Jev [E2g]. So d3-27b's date advantage over Jev is clear, and over the stock 27b it is not
  established. Of the 11 more negatives d3-27b clears than 27b lp at their 98% thresholds, 7 are wrong-date
  emails, which a date-limited search would remove anyway [D1-7].
- **d3-27b's default cutoff held.** At 0.5 it missed 0 of 146 and 1 of 143 responsive emails (0 of 143 with the
  roster), eliminating 72%, 88% and 95% [A3a]. Pooled, its recall at 0.5 is 288/289 [98.1%–99.9%], against
  92.7–95.5% for the other score models [E4c]. That reflects where its scores sit, not calibration (§13): its
  mean score on non-responsive emails is 0.213, against 0.098 for 27b lp [E5d]. The cutoff fails above 0.5405 on
  25-3152, and 0.5 was singled out after comparing seven models.
- **d3 is slower.** It takes 1.60–1.73× the machine time of the same-size stock lp (ratio of mean times), and
  3.14–3.56× with the roster [B1.8]. Per 10,000 emails: d3-27b 14.7 h (25.8 h with the roster), 27b lp 8.9 h
  (8.0 h) [B1.1, B1.2]. Most of the gap is the lost prefix cache. Against stock runs that reload the model before
  every call, so nothing is cached, d3 takes 1.07× (4b) and 1.06× (9b) as long, as a median of per-pair ratios;
  1.23× and 1.11× on roster prompts [E5e].
- **d3 repeats closely.** Cached against reloaded-every-call, on 60 pairs (30 with the roster): mean |Δscore|
  ≤ 0.0056 [L-4].
- **Jev.**
  - **Speed and cost.** The fastest configuration: 117 ms median, network included; the fastest local one, 4b lp,
    takes 4.3× as long [E3a]. Per 10,000 emails, 0.33 h and $0.93 [B1.1, B1.5], at $0.042 per million input tokens
    with output tokens free (TypeSafe's models page, docs.typesafe.ai/models.md, read 2026-11-04).
  - **Ranking.** Middle of the field: AUROC 0.917. Only 27b lp and d3-27b beat it on both AUROC and elim@98 after
    Holm [E1b, E1c]. d3-27b flags 1,621 fewer emails per 10,000 [1,085–2,260]; 9b lp, 672 fewer [19–1,562]
    [B5.2].
  - **Dates.** At its 98% threshold it passes 19 of 20 wrong-date emails [E2b].
  - **Limits.** One version (jev-1.14.0), our prompt and network; scores rounded to two decimals; repeat noise
    unmeasured. Using it sends the records to a third party, and there is no record of a review of its data terms
    [D4 row 12].

## 11. Setting the cutoff without labels

Every elimination figure above uses a cutoff chosen with the labels in hand. A deployment has to set it before
the answers are known.

- **The two requests want different cutoffs for some models** [A1a]. The 98% thresholds, 24-409 vs 25-3152, with
  bootstrap intervals:

  | model | 24-409 | 25-3152 | 25-3152 + roster |
  |---|---|---|---|
  | 27b lp | 0.3623 [0.2529–0.7206] | 0.0566 [0.0079–0.1030] | 0.0783 [0.0730–0.2164] |
  | d3-27b | 0.8542 [0.7504–0.9115] | 0.5405 [0.4870–0.6115] | 0.9060 [0.8722–0.9220] |
  | Jev | 0.57 [0.42–0.63] | 0.31 [0.22–0.35] | 0.46 [0.39–0.52] |

  For these three the intervals are disjoint. For the other four they overlap, and a direct test finds at most a
  nominal gap [A·V concern 3].
- **Reusing one request's cutoff on the other fails whenever the target needs a lower one,** which by arithmetic is
  one of each pair of opposite directions. The failures are large [A2b]:
  - same prompt, 24-409 → 25-3152: d3-27b misses 31 of 143 responsive emails, Jev 28, 27b lp 14;
  - from a roster prompt, 25-3152 → 24-409: d3-9b misses 84 of 146 and d3-4b 76.

  Using the source request's 100% cutoff as a margin rescues one more direction only for d3-4b and Jev [A2c].
- **The default 0.5 holds on both requests only for d3-27b** (§10). Every other score model misses at least 5 on
  one request at 0.5, and no JSON verdict keeps 98% recall on 25-3152 [A3a, A3c].
- **A small labeled sample can't certify 98%.** One rule sets the cutoff at the lowest-scoring responsive email in
  a random sample. At n = 50 it reaches 98% recall on the rest in 0.49 of repetitions at the golden prevalence and
  0.19–0.20 at 20% responsive, for every model without ties [A·V V9]. 90% assurance needs about 114 responsive
  emails in the sample [A4a].
- **A margin restores recall at a model-specific cost.** Dividing the odds at the lowest sampled score by 10 (n =
  50, 20% responsive) reaches 98% in at least 0.91 of repetitions for six models; 27b lp gets 0.61 / 0.64 / 0.71
  (24-409 / 25-3152 / 25-3152 + roster). Elimination on 25-3152 then falls to 4% for 4b lp, 2% for d3-4b and 0%
  for Jev, while d3-27b keeps 72% / 64% / 95% [A·V V9].
- **A stated fixed-cutoff rule** takes the largest grid value safe on every labeled subset and steps down one
  value. On these data it misses at most 1 per request, and it eliminates 7–41 points less than the headline
  without the roster, 12–54 with it [A5e]. It is fitted on these same two requests, so the gap is not an
  out-of-sample estimate. Fitted on one request and applied to the other, the same heuristic kept 98% in 2–3 of 4
  directions with one step of headroom; fitted on 24-409 alone it would have picked 0.7 for d3-27b and missed 12
  of 143 on 25-3152 [A2d].

  | model | rule's cutoff | 24-409: misses · eliminated | 25-3152 | 25-3152 + roster |
  |---|---|---|---|---|
  | d3-27b | 0.4 | 0/146 · 69% | 0/143 · 81% | 0/143 · 92% |
  | 27b lp | 0.02 | 0/146 · 68% | 1/143 · 67% | 0/143 · 87% |
  | 9b lp | 0.1 | 0/146 · 60% | 0/143 · 30% | 0/143 · 25% |

- **A random-sample check catches large failures only.** At 20% responsive, a sample of 50 hits catches a cutoff
  that misses 10% of responsive emails with probability 0.64, and one that misses 5% with probability 0.39. A
  sample of 200 raises these to 0.98 and 0.87 [F3].
- **Headroom.** d3-27b's 0.4 sits 0.57 log-odds below its 25-3152 failure point (0.5405), and 0.5 sits 0.16
  below it. 27b lp's 0.02 has 1.08 [F5].

**Interpretation (low confidence).** These data can't show any cutoff policy to be safe on a third request. The
best-supported policy is a fixed cutoff per model *and per prompt*, fitted on every labeled request and stepped
down, plus a random-sample check on each new request. Before first use, label at least one of the agency's own
requests of each type and check the cutoff on it.

## 12. Workload per 10,000 hits

A scenario, not a measurement [B5]: a keyword search returns 10,000 hits, 20% responsive; the non-responsive half
are like the real negatives here and half like the hard ones; a reviewer reads each flagged email in 30 s.
Machine time is single-stream on the Strix Halo at golden-like email lengths. Reading all 10,000 takes 83.3 h.

| config | machine h | flagged at in-sample thr98 [CI] | reviewer h at 30 s | flagged at 0.5 | missed at 0.5 [CI] |
|---|---|---|---|---|---|
| Jev | 0.3 | 5,241 [4,813–5,798] | 43.7 | 4,346 | 125 [76–180] |
| 4b lp | 1.7 | 6,155 [4,807–7,006] | 51.3 | 4,321 | 111 [62–159] |
| 9b lp | 2.8 | 4,569 [3,859–5,095] | 38.1 | 3,571 | 118 [69–166] |
| 27b lp | 8.9 | 4,126 [3,030–4,540] | 34.4 | 2,590 | 145 [90–208] |
| d3-27b | 14.7 | 3,621 [3,115–4,172] | 30.2 | 3,878 | 7 [0–21] |

Sources: [B3.1], [B2.4].

- **Reviewer time dominates machine time** for every configuration: 30.2–51.3 h of reading against 0.3–14.7 h of
  scoring [B3.1]. Speed decides turnaround, such as whether a batch finishes overnight; accuracy decides how many
  paid human hours follow.
- **The negatives drive the load more than the model does.** For 27b lp at its 98% threshold, flagged emails run
  from 1,965 (every negative like the real ones) to 6,287 (every one like the hard ones). Across the score models
  at the 50/50 mix they run 3,621–6,155 [B2.3].
- **Misses at the in-sample threshold** are 35 per 10,000 by construction, averaged over the two requests
  (Wilson 15–80); a single request sees between 0 and 70 [F1, A1c].
- **If the search applies the date window,** the easy out-of-window negatives disappear. As a pessimistic bound,
  with every negative as hard as the synthetic in-window near misses, flagged per 10,000 at the in-sample
  threshold rises to 5,906 (d3-27b), 6,145 (9b lp), 6,383 (27b lp) and 7,339 (Jev) [F1].
- **At the cutoffs §11 would pick,** as a range from the 50/50 mix to the in-window bound [F1, F6, B5.5]:

  | configuration | machine h | flagged per 10,000 | missed per 10,000 [Wilson 95%] | reviewer h at 30 s |
  |---|---|---|---|---|
  | d3-27b, cutoff 0.4 | 14.7 | 4,345 – 7,254 | 0 [0–26] (0/289) | 36.2 – 60.4 |
  | d3-27b, cutoff 0.5 | 14.7 | 3,878 – 6,530 | 7 [1–39] (1/289) | 32.3 – 54.4 |
  | 27b lp, cutoff 0.02 | 8.9 | 5,061 – 8,202 | 7 [1–39] (1/289) | 42.2 – 68.4 |
  | d3-27b + roster, cutoff 0.5, 25-3152 only | 25.8 | 2,435 (50/50 mix) | 0 [0–52] (0/143) | 20.3 |
  | 27b lp + roster, cutoff 0.02, 25-3152 only | 8.0 | 3,217 (50/50 mix) | 0 [0–52] (0/143) | 26.8 |
  | no screen (read everything) | 0 | 10,000 | 0 | 83.3 |

  A "0" means none was seen among 143–289 responsive emails, not that none will be missed. The roster rows
  cover 25-3152 only, and their in-window bound isn't computed. The 27b lp + roster row applies B's scenario
  formula to its run directly; no script prints it.
- **The reviewer hours are a floor in one respect:** they leave out the sample check and any quality-control
  sample of the discarded emails [B·V concern 7]. Machine hours also vary by request (27b lp 9.6 h on 24-409 and
  8.3 h on 25-3152) and by email length (+7.1 h per +1,000 tokens of mean prompt for 27b lp, +7.8 h for d3-27b)
  [B·V concern 4, B1.6].

## 13. Calibration: the scores rank; they aren't probabilities

- **Every score model's calibration slope differs from 1** [E4b]. 27b lp has the lowest Brier score and ECE
  (0.057 and 0.029), but it is overconfident at the extremes (slope 0.72 [0.61, 0.92]) and runs low overall
  (intercept +0.40 [+0.07, +0.73]). The other six are compressed toward the middle, with slopes from 1.45 to 1.94.
- **ECE is within bin noise only for 27b lp and d3-4b** (p 0.16 and 0.17) [E4a].
- **d3-27b overstates in its middle range.** Of the pairs it scores 0.7–0.8 and 0.8–0.9, only 54% and 62% are
  responsive (n = 26 and 29) [E4d]; its intercept is −1.57.
- **JSON confidences are far from calibrated:** ECE 0.047–0.161, against a noise floor with medians of
  0.004–0.009 (all p 5.0e-04) [E4a].
- **The golden set is 58.3% responsive by design.** If a request has 10% responsive emails and each class scores
  as it does here, a score calibrated here at 0.5 would mean 0.074 there [E4g].
- **Higher scores do mean more responsive emails, broadly.** Across the report's six score buckets the share
  responsive rises for every lp and decision-model run (report §4b); finer 0.1-wide bins show dips where few
  emails fall [E4d].

Read the scores as rankings. A cutoff has to be set by policy (§11), not by reading the score as a probability.

## 14. Validity: easy real negatives, hard synthetic negatives

| subset | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev |
|---|---|---|---|---|---|---|---|
| everything (the headline) | 53% | 72% | 77% | 55% | 70% | 83% | 64% |
| real positives vs real negatives | 71% | 96% | 100% | 84% | 99% | 100% | 91% |
| real positives vs in-window hard negatives (67) | 19% | 48% | 45% | 16% | 33% | 43% | 30% |
| AUROC, real positives vs in-window hard negatives | 0.844 | 0.898 | 0.929 | 0.740 | 0.892 | 0.932 | 0.822 |

Eliminated at 98% recall, cutoff chosen within each subset [D1-1, D1-2].

- **The real negatives aren't search hits.** 118 of 120 fall outside the target request's date window, none hits
  the keyword proxy, and the pre-label rationale cites the window for 118 of 120 [D2-2]. They supply 70–90% of the
  negatives each score model clears (§4).
- **Against in-window near misses** (real positives against the 67 hard negatives dated inside the window), the
  best models eliminate 43–48% rather than 72–83% in the headline; 9b lp, 27b lp and d3-27b are level there.
  The headline is an optimistic bound and this subset a conservative proxy, but not the floor; a real date-filtered search lies
  somewhere between, and these data can't say where [D1-2, D·V concerns].
- **On real emails of one request the small models struggle.** On 25-3152 alone, 4b lp clears only 23 of the 60
  real negatives at 98% recall, d3-4b 38 and Jev 46 [D3-3].
- **The synthetic positives score like real ones:** P(synthetic+ > real+) is 0.46–0.56. **The hard negatives
  carry the difficulty:** P(hard− > real−) is 0.87–0.99 [D2-8].
- **Realism.** In a 30-email spot read on 2026-11-06 (one reader, judgment, on the 2026-10-31 labels), 9 of the
  10 sampled hard negatives and 7 of the 10 synthetic positives read as real [D2 spot-read in `D-validity.md`].
  Two of those hard negatives have since been relabeled, so a rerun on the current labels draws two new ones. The
  verifier's style tell was mild for 105 of 226 synthetic emails and obvious for 2 [D2-5]. The synthetic emails
  are edits of 130 source emails, mostly real positives in the set, so the hard negatives are largely minimal
  pairs [D2-7].
- **Labels.** One adjudicator. 185 of 270 real rows and 189 of 226 synthetic rows have no human call; the random
  spot check found 0 disagreements in 81, a 95% upper bound of 3.6% [L-2].
- **These checks aren't independent of the generator.** Opus wrote the synthetic emails and the pre-labels; the
  realism codes and the re-reads of the shared errors were made by AI analysts of the same family; and the human
  spot check was done on a page that showed the Opus pre-label. So 3.6% bounds disagreement with a visible
  suggestion, not the label error rate. A blind second human adjudication of a sample would fix this [D4 rows 3
  and 5].

## 15. Hypothesis status (golden set)

| | status |
|---|---|
| H1 latency ≪ JSON | **Supported, but not by an order of magnitude.** lp medians are 504 / 855 / 2,639 ms against json 2,747 / 4,435 / 6,805 and jsonR 2,908 / 5,263 / 7,011 ms: 2.6–6.2× slower, never 10×. Decoding the JSON alone takes longer than the whole lp call at every size. At 4b and 9b the gap includes the JSON runs' batch-8192 prefill (median +458 to +711 ms per call) [E3a, B1.4] |
| H2 ≥98% recall with >50% eliminated | **Met in-sample on the designed set; not shown for a cutoff set in advance.** In-sample, all seven score models clear 50% (53–83%), and the CI lower bound is above 50% for 9b lp, 27b lp, d3-9b, d3-27b and Jev. Per request with its own cutoff, 4b lp (30%) and d3-4b (46%) fall short on 25-3152 without the roster. The pooled cutoff leaves one request below 98% for every model. Label-free, only d3-27b's default 0.5 met both conditions on both requests (0/146 and 1/143 missed; 72% and 88% eliminated), and it was picked after the fact. Without the roster the stated fixed rule (§11) clears 75% combined for d3-27b and 68% for 27b lp; d3-9b 51%, 9b lp 45%, Jev 41%, d3-4b 36%, 4b lp 12%. Against in-window hard negatives no model reaches 50% (16–48%) [E1a, E5b, A1c, A3a, A5e, D1-2] |
| H3 score tracks error rate | **Partly.** Higher lp and d3 scores mean a higher share responsive, broadly. But no score is a calibrated probability: every slope CI excludes 1, only 27b lp and d3-4b pass the ECE noise test, and JSON confidences are far off (ECE 0.047–0.161). Calibration on this 58%-responsive set wouldn't carry to a request with fewer responsive emails [E4a, E4b, E4g] |

## 16. Caveats

- **One run per configuration.** Elimination at 98% recall moves several points with a few borderline emails.
  The 4b lp gave 53% at the default batch and 48% at batch 8192 with the same AUROC, and cached and reloaded runs
  differ by up to 4.8 points [L-4, E5g]. Jev's repeat noise is unmeasured.
- **Every elim@98 is in-sample,** and the bootstrap doesn't capture that optimism. Cutoffs set in advance did
  worse (§11).
- **Two requests from one county,** one of each type, so request type can't be separated from the particular
  request [D4 row 1].
- **The real negatives aren't search hits,** and the repo has no real in-window near misses to replace them
  (§14).
- **One generator wrote every synthetic email, and the checks aren't independent of it** (§14).
- **Prompt 2 was written after reading this set's misses,** so its gains here are in-sample [L-3].
- **The JSON prompt comparisons span the Ollama upgrade** (§8).
- **The d3 comparison is confounded** (§10). There is no default-batch d3 run, no stock Q8_0 run and no uncached
  stock 27b run.
- **Backend noise isn't in the bootstrap,** and several Holm results sit between 0.03 and 0.09, close enough to
  move under a reseed [E·V concern 3].
- **Labels.** One adjudicator, and some labels have no human check (§14). The scope calls in §9 are one lawyer's
  reading. Under the narrower "one member among many" reading the cutoffs, and d3-27b's edge on 25-3152, would
  move [F2].
- **The keyword proxy is circular for 25-3152,** and the roster was compiled partly from that request's own
  production [D·V check 16, D4 row 15].
- **Small positive counts per request:** 146 (24-409) and 143 (25-3152), so 98% recall allows 2 misses on each.
- **Attachments:** the models see file names, never attachment text [D4 row 16].
- **The workload figures** rest on an assumed prevalence and negative mix, and leave out quality-control
  sampling (§12).
- **Strix Halo only, single stream.** Parallel scoring and other hardware weren't measured; the laptop runs were
  dropped on 2026-11-04.

## 17. Next

Done:

1. ~~Resolve the questioned labels and rebuild the golden set.~~ Done 2026-10-31, 2026-11-08 and 2026-11-11 (§9).
2. ~~Prompt revision for correspondent-scoped requests.~~ Done 2026-11-01 (§5). The rule helps once the model has
   a roster; the purely-personal exception has no effect.
3. ~~Decide how to handle purely personal emails between named people.~~ Decided 2026-11-04: no more prompt work,
   because the test measures out-of-the-box performance. Leave them to human review.
4. ~~Jev (API) and a Jev-like open model on the same pairs (SPEC §14.1).~~ Done 2026-11-05 (§10).
5. ~~Rerun the §7 probes at the default batch on Ollama 0.40.13.~~ Done 2026-11-04 (§7): the fault is gone, and
   the 4b and 9b lp runs use the default batch again.
6. ~~Laptop runs.~~ Dropped 2026-11-04; the Strix Halo is the only hardware in the golden comparison.

Open:

1. A third and a fourth labeled request, one of each type, to test the fixed-cutoff policy out of sample (§11).
2. A labeled sample of a real keyword-search result: its prevalence, its mix of easy and near-miss negatives, and
   real near misses to stand in for the synthetic ones (§12, §14).
3. Separate the d3 package differences: a default-batch d3 run, a stock 27B run at Q8_0, and an uncached stock 27b
   run (§10).
4. Repeat runs of Jev, and a larger d3 repeat.
5. A sample-check design sized from F3 (§11).
6. A narrower named-correspondent rule, tested on a held-out request (§5).
7. Attachment text extraction.
8. A blind second adjudication of a label sample (§14).
