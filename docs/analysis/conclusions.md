# Golden-set analysis: conclusions

> **Snapshot of 2026-11-06, on the 2026-10-31 labels (495 pairs).** Section 0 below, added 2026-11-11, lists the
> owner's later label decisions and what they changed. Everything after section 0 is as written on 2026-11-06.
> `docs/findings-golden.md` carries the current figures.

**Date:** 2026-11-06 · **Scope:** this file pulls together the five analysis branches in `docs/analysis/`, each checked by an
independent skeptic pass, plus `docs/findings-golden.md` §10–12. **New numbers:** only those cited as [F1]–[F4],
from `scripts/analysis/f_followups.py` (section 7), added after a completeness critique of this file. Every other
figure is copied from a branch file and cited to the table that prints it. The scripts that reproduce each table
are listed in that branch's Reproduce section. Where a branch's analyst and its skeptic disagree, this file uses
the skeptic's verified figure and says so (section 5).

| branch | file | question |
|---|---|---|
| A | `docs/analysis/A-cutoffs.md` | Can the cutoff be set without the target request's labels? |
| B | `docs/analysis/B-workload.md` | Machine time, review load and misses per 10,000 keyword-search hits |
| C | `docs/analysis/C-misses.md` | Which emails the models miss or wrongly keep; label questions |
| D | `docs/analysis/D-validity.md` | Real vs synthetic emails, the two requests, limitations register |
| E | `docs/analysis/E-comparisons.md` | Which model differences are real; speed/accuracy frontier; calibration |

## 0. Update 2026-11-11: the owner's label decisions

The label questions this file left open (section 5b item 4, conclusion 9) were decided on 2026-11-08 and
2026-11-11. The calls and the reasoning are in `docs/findings-golden.md` §9. In short:

- **"One member among many recipients"** (the 19 positives of section 1, conclusion 5): **responsive**. The request
  asks for every communication between a member and the public or another agency, and the requester chose that
  wide net.
- **Geosyntec only in the addresses** (24-409 synthetic 03:01, 03:09): **responsive**, consistent with the four
  earlier flips.
- **Purely personal by extension** (25-3152 synthetic 15:01, 15:02, 15:06): **responsive**. Copying the chair
  brings an email in. Six emails stay purely personal.
- **RDF and GPS in another sense** (24-409 synthetic 07:01, 07:02, 07:03): **not responsive**, read by the
  requester's evident intent. 07:09, dropped on 2026-10-31 for the same ambiguity, is back in the set as a
  non-responsive hard negative.

The set is now 496 pairs, 289 responsive and 207 not (58.3% responsive). The scripts were rerun on the new labels;
the main changes:

| claim in this file | 2026-11-06 (labels of 2026-10-31) | 2026-11-11 | source |
|---|---|---|---|
| headline AUROC / elim@98: 4b lp, 9b lp, 27b lp | 0.923 / 51.7%, 0.942 / 70.6%, 0.975 / 75.8% | 0.922 / 52.7%, 0.945 / 72.0%, 0.977 / 77.3% | E1a |
| headline AUROC / elim@98: d3-4b, d3-9b, d3-27b, Jev | 0.884 / 53.6%, 0.947 / 68.2%, 0.979 / 81.0%, 0.916 / 63.0% | 0.901 / 54.6%, 0.957 / 69.6%, 0.983 / 82.6%, 0.917 / 64.3% | E1a |
| AUROC tiers | 13 of 21 differences survive Holm; {27b lp, d3-27b} > middle > d3-4b | still 13, but 27b lp vs d3-9b no longer survives (Holm 0.086) and d3-27b vs d3-9b now does, so d3-9b sits between the tiers | E1b |
| d3-27b − 27b lp, main set | AUROC +0.004, elim@98 +5.2 | +0.006 [−0.002, +0.015], +5.3 [−5.8, +9.2]; still not established | E1b, E1c |
| d3-27b vs 27b lp on 25-3152 with the roster | 98.2% vs 90.8% (+7.3), Holm 0.034 | 100.0% vs 93.4% (+6.6 [+1.9, +11.3]), Holm 0.088 among the 21 model pairs; d3-27b's AUROC is 1.000 | E1c roster set, E5b |
| that edge's dependence on the scope reading (F2) | open | settled: the 19 stay responsive, so the edge stands as measured | findings-golden §9 |
| d3-27b's default 0.5 | 0/144 and 1/140 missed; 72%, 85%, 93% eliminated; pooled recall 283/284 | 0/146 and 1/143; 72%, 88%, 95%; 288/289 | A3a, E4c |
| recommended cutoffs (in-sample, 24-409; 25-3152; +roster) | d3-27b 0.4: 69%; 79%; 89%. 27b lp 0.02: 68%; 1 miss, 65%; 84% | d3-27b 0.4: 69%; 81%; 92%. 27b lp 0.02: 68%; 1 miss, 67%; 87% | A5e |
| flagged per 10,000 at the recommended cutoffs (50/50 mix – in-window bound) | d3-27b 0.4: 4,418–7,408; 0.5: 3,971–6,725; 27b lp 0.02: 5,103–8,303 | 4,345–7,254; 3,878–6,530; 5,061–8,202 | F1 |
| flagged per 10,000 at thr98, plausible scenario | Jev 5,287, 9b lp 4,637, 27b lp 4,207, d3-27b 3,723 | 5,241, 4,569, 4,126, 3,621 | B3.1 |
| in-window hard negatives, subset (f) | 71 emails; elim@98 15–45%; 9b lp, 27b lp, d3-27b 45%, 42%, 41% | 67 emails; 16–48%; 48%, 45%, 43% | D1-2 |
| transfer failures | d3-27b 31/140, Jev 28/140, 27b lp 14/140; d3-9b roster → 24-409 82/144 | 31/143, 28/143, 14/143; 84/146 | A2b |
| sample margin ÷10 at n = 50, 20% responsive | 27b lp reaches 98% in 0.549 / 0.648 / 0.719 of repetitions | 0.605 / 0.640 / 0.711 | A·V V9 |
| consensus false positives | 57; labels: 51 hold, 5 arguable, 1 likely wrong | 53; all hold under the owner's calls | C2b, C3b |
| roster effect on consensus false positives, like for like | 26 → 8 at thr98, 21 → 11 at 0.5 | 23 → 5, 18 → 8; the 5 left are all purely personal | C·V V5 |
| ECE within bin noise | 9b lp, 27b lp, d3-4b | 27b lp, d3-4b | E4a |
| d3-27b flags fewer than Jev, per 10,000 | 1,564 | 1,621 [1,085–2,260] | B5.2 |

Unchanged in substance: conclusions 1–4 and 6–10, the recommended setup in section 3, and the claims in
section 4 (with the numbers above). Resolved: the scope and label questions in conclusion 9, section 5b item 4, and
the "narrower reading" row of section 3's "What would change" table.

## How to read this file

- **Citations.** `[A3a]` means table A3a in `A-cutoffs.md`, and the same pattern holds for B, C and E.
  `[D1-2]` means the D1-2 table in `D-validity.md`. D's Verification section maps these labels to its headings.
  `[L-7]` is a register appendix table in D. `[A·V check 8]` is row 8 of the checks table in A's
  "## Verification" section, `[A·V concern 3]` is item 3 of its remaining concerns, and `[C·V correction 3]` is
  item 3 of its corrections. `[B·V V5]` is section V5 of that branch's `*_verify.py` output, as quoted in its
  Verification section.
- **Confidence.** *High* means several independent checks agree and the claim doesn't depend on a knife-edge
  count. *Medium* means it is supported, but rests on one request, small groups, synthetic emails, or a
  correction that sits near its threshold. *Low* means it is an interpretation or a policy the data can't test.
- **Data vs interpretation.** Each conclusion separates what the tables show from what the analysis infers.

### Terms

| term | meaning |
|---|---|
| pair | one (request, email) combination. The golden set has 495: 246 for request 24-409 (topical) and 249 for 25-3152 (correspondent-scoped: communications of named people) |
| positive / negative | the human label: responsive (284 pairs) or not responsive (211) |
| score | the model's probability that the email is responsive |
| lp | "logprob": the stock Qwen model's first-token P(yes)/(P(yes)+P(no)). Labeled 4b lp, 9b lp, 27b lp |
| d3-4b, d3-9b, d3-27b | decision models (vLLM Semantic Router) built on the same Qwen bases, run locally at Q8_0 |
| Jev | TypeSafe's hosted decision model (jev-1.14.0), reached through its API. Its time includes the network |
| json / jsonR | the model writes a JSON verdict with a confidence, verdict first (json) or reasoning first (jsonR) |
| cutoff, flagged, eliminated | a pair is flagged for human review when score ≥ cutoff, and eliminated otherwise |
| recall, miss | recall = flagged positives ÷ all positives. A miss is a positive that wasn't flagged |
| thr98 | the highest cutoff that keeps recall ≥ 98%. On 284 positives that allows 5 misses; on one request's 140 or 144, 2 |
| elim@98 | share of negatives scored below thr98 |
| in-sample (oracle) | the cutoff is chosen on the same labeled pairs it is scored on. Every elim@98 in this project is in-sample |
| AUROC | the chance that a random positive scores above a random negative. 0.5 = coin flip, 1.0 = perfect ordering. Needs no cutoff |
| Holm | a correction for testing many comparisons at once. "Survives Holm" = still significant after it |
| roster | the planning group's member list (names, roles, addresses), appended to 25-3152's request text |
| hard negative | a synthetic near-miss non-responsive email, built by one of five recipes (e.g. same subject, wrong date) |
| plausible scenario | branch B's assumed population of hits: 20% responsive, negatives halfway between the easy real ones and the hard synthetic ones |
| prefix cache | Ollama reuses the processed system prompt and request text when consecutive calls share them |

## Short answer

- **The logprob score is a usable and fast ranking signal.** The 27b lp ranks a random responsive email above a
  random non-responsive one 97.5% of the time (AUROC 0.975), at a median of 2,649 ms per email on one machine
  [E1a, E3a]. The "98% recall" figure, though, belongs to a cutoff chosen with the labels in hand.
- **Setting the cutoff in advance is the weak point.** Reusing one request's cutoff on the other missed up to
  31/140 responsive emails with the same prompt, and 82/144 when the source request's prompt included the roster
  [A2b]. Only d3-27b's default 0.5 kept 98% recall on both requests, and it was singled out after seven models
  were compared [A3a, A·V concern 7].
- **Bigger helps, and JSON verdicts don't.** The two 27B models form the top tier, and they can't be told apart
  on the main set [E1b]. JSON verdicts are slower than the logprob read and rank worse at every size [E3a].
- **The roster matters for the correspondent-scoped request.** It raised AUROC for every score model on 25-3152
  [D3-4]. It costs stock Qwen no time, but it costs d3 time on every call [B1.3].
- **d3-27b's edge on the correspondent-scoped request depends on an open scope question.** Its lead over 27b lp
  there comes largely from the 19 emails where a member is one of many recipients. Read those as not responsive,
  and with the roster the elim@98 gap goes from +7.3 to +0.8 points [F2].
- **Most of the headline elimination comes from easy emails.** Real negatives are records from other requests,
  almost all outside the date window [D2-2]. Against in-window hard negatives, elim@98 is 15–45% rather than
  52–81% [D1-2]. If the search applies the date window, plan on a review load between the plausible scenario and
  up to about twice it [F1].
- **Reviewer time, not machine time, sets the total effort** [B3.1].

## 1. Conclusions

| # | conclusion | confidence | main evidence |
|---|---|---|---|
| 1 | The first-token score ranks emails well and quickly, but its 98%-recall headline is an in-sample upper bound | high | E1a, E3a, B1.1, A1c, D1-1 |
| 2 | The 27B class is clearly better at ranking. Neighbouring sizes, and the two 27B models, can't be separated on elimination | high | E1b–E1e, E3a, E3c |
| 3 | JSON verdicts are slower than the logprob read and worse at every size | high | E3a, E3c, B1.4, B2.1, A3c, CJ |
| 4 | The roster is the biggest single gain for the correspondent-scoped request. It is free for stock Qwen and costly for d3, and it needs its own cutoff | medium | D3-4, B1.3, B4.2, A1a–A1b, C1e, C2c |
| 5 | d3-27b ties the stock 27b overall. It is better on 25-3152, though that edge depends on an open scope reading, and its default cutoff held, but it is slower. Without the roster smaller d3 adds nothing; with it, d3-9b beats 9b lp. Jev is fastest but mid-tier and not local | medium | E1, E5b, F2, A3a, E4c, B1.8, E5e, E2b, B5.2, B5.5 |
| 6 | The real negatives are easy and supply most of the headline elimination. The synthetic hard negatives carry the difficulty, and the synthetic positives behave like real ones | high | D1-1, D1-2, D1-7, D2-2, D2-8, C2b |
| 7 | No label-free cutoff policy tested can be shown to keep 98% recall on a new request | high | A1a, A2b, A3a, A4a–A4e, A5e |
| 8 | Reviewer time dominates machine time. What the negatives look like moves the workload more than which model screens | medium | B2.3, B3.1, B3.2 |
| 9 | Shared errors are model errors of recognizable kinds. The one label question with a real effect is a scope reading | medium | C1d, C2b, C3b, C4c, C5b |
| 10 | No model's score is a calibrated probability, and probabilities measured here wouldn't carry to a request with fewer responsive emails | medium | E4a, E4b, E4d, E4g |

### 1. The logprob score ranks well and fast; "98% recall" comes from a cutoff chosen with hindsight

**What the data show**

| model | AUROC [95% CI] | elim@98, in-sample | median ms per email | hours per 10,000 |
|---|---|---|---|---|
| 4b lp | 0.923 [0.897–0.945] | 109/211 (51.7%) | 504 | 1.68 |
| 9b lp | 0.942 [0.921–0.962] | 149/211 (70.6%) | 856 | 2.83 |
| 27b lp | 0.975 [0.963–0.986] | 160/211 (75.8%) | 2,649 | 8.93 |

Sources: [E1a], [B·V V5], [E3a], [B1.1]. All times are single-stream (one email at a time) on the Strix Halo.

- On real emails alone (real positives against real negatives), lp AUROC is 0.982, 0.997 and 1.000 [D1-1, (a)].
- The 98% recall is met by construction, because thr98 is fitted on the same 495 labels. At that pooled cutoff
  every run misses 3 or more responsive emails on one of the two requests, which puts that request below 98%
  [A1c]. With 5 misses allowed in total, that outcome is forced by arithmetic (5 > 2 + 2) [A·V concern 1]. What
  carries information is how the misses bunch up. For 27b lp all 5 fall on 25-3152, so recall there is 5/140
  missed, 96.4% [A1c]. At 20% prevalence that is 71 missed per 10,000 on that request, against the 35 averaged
  over both [B·V concern 2].

**Interpretation.** The score orders emails well enough to serve as a screen. Whether it delivers 98% recall on a
new request depends on how the cutoff is set (conclusion 7), and these data can't certify that.

### 2. Size: the 27B class is clearly better; neighbours can't be ranked on elimination

**What the data show**

- **AUROC falls into three tiers** [E1b, E1d, E1e]: {27b lp, d3-27b} > {9b lp, d3-9b, 4b lp, Jev} > d3-4b.
  13 of 21 pairwise differences survive Holm under the bootstrap, the normal curve and DeLong. An independent
  reseed gives 12, because 4b lp − d3-4b moves to Holm p 0.054 [E·V check 7]. So the line between the middle and
  bottom tiers sits at p ≈ 0.05 [E·V concern 3]. The two 27B models differ by +0.004 [−0.004, +0.013], p 0.34
  [E1b].
- **elim@98 is noisier.** Only 8 of 21 differences survive Holm, all of them the 27B models against Jev, 4b lp
  and d3-4b, or a 9B model against d3-4b [E1c]. Not established: 9b lp − 4b lp, +19.0 points [+0.5, +31.8],
  Holm p 0.46; and d3-27b − 27b lp, +5.2 [−5.7, +9.0] [E1c]. What does survive is the jump from 4b lp to either
  27B model: +24.2 and +29.4 points [E1c].
- **The local speed/accuracy frontier is 4b lp → 9b lp → 27b lp → d3-27b** [E3a]. Going from 4b to 9b costs
  +352 ms for +19.0 points. Going from 9b lp to 27b lp costs +1,793 ms for +5.2 points, and from 27b lp to d3-27b
  +2,018 ms for +5.2 [E3a]. None of these three steps survives Holm on its own [E1c, E3 text]. In bootstrap
  redraws the four sit on the frontier in 100%, 97%, 87% and 75% of cases [E3c].
- **On workload,** 4b lp → 9b lp flags 1,546 fewer per 10,000 [−2,496, −65] [B5.2]. Under a Bonferroni-style
  correction the interval reaches +304 [B·V concern 3].
- **Noise not in the bootstrap.** Cached and fresh runs of the same stock model differ by up to 4.6 points of
  elim@98 [E5g], a rough guide because the two runs take different serving paths [E·V concern 4]. A second 4b lp
  run with a different batch setting gave 52% vs 47% at the same AUROC [L-4].

**Interpretation.** Moving to 27B buys a real ranking gain, and against the 4B a real elimination gain. 9B is
probably better than 4B, but on elimination the difference is not established.

### 3. JSON verdicts: slower and worse than reading the probability

**What the data show**

- **Slower.** Decoding the JSON answer alone (median 1,760–4,040 ms) takes longer than the whole lp call of the
  same model (504 / 856 / 2,649 ms) [E3a]. Per 10,000 emails, decoding alone costs 5.01–11.73 h [B1.4]. Whole JSON
  runs take 7.91–20.75 h [B1.1].
- **Worse at ranking.** AUROC, all pairs: 4b 0.923 (lp) vs 0.833 (json) and 0.870 (jsonR); 9b 0.942 vs 0.871 and
  0.879; 27b 0.975 vs 0.947 and 0.951 [D1-1, (e)].
- **Unusable at high recall for the small models.** 9b json, 4b jsonR and 9b jsonR reach 98% recall only at a
  cutoff of 0, which flags every email [B2.1]. That happens because 40, 18 and 10 positives are scored exactly 0
  [B·V check 10]. 27b json flags 8,043 per 10,000 in the plausible scenario against 4,207 for 27b lp [B2.3].
- **Never on the main-set frontier** in 2,000 redraws (4 of 2,000 for 27b json in an independent check). On
  25-3152, 27b json +roster reaches the AUROC frontier only through a near-tie: 0.98911 on 248 pairs against
  0.98906 on 249 [E3c, E·V check 14, E·V concern 7].
- **At the verdict itself,** no JSON run keeps 98% recall on 25-3152, with or without the roster [A3c]. 27b json
  +roster misses by one email (3/139) [A·V concern 8].
- **No rescue on shared errors.** 27b jsonR says no to all 8 25-3152 consensus misses. On the emails five or more
  models wrongly keep, the JSON runs say yes 47–75% of the time, against 13–24% on all negatives [CJ].

**Interpretation.** A generated verdict adds time and loses the ability to choose an operating point.
`findings-golden.md` §2 reaches the same answer from a matched-yes-rate comparison.

### 4. The roster: the biggest single gain for the correspondent-scoped request

**What the data show** (25-3152, the same 249 pairs without and with the roster)

| model | AUROC without → with [paired ΔCI] | elim@98 without → with | median ms without → with |
|---|---|---|---|
| 4b lp | 0.883 → 0.950 [+0.034, +0.102] | 29% → 75% | 450 → 446 |
| 9b lp | 0.927 → 0.963 [+0.012, +0.061] | 70% → 68% | 772 → 734 |
| 27b lp | 0.955 → 0.989 [+0.014, +0.060] | 74% → 91% | 2,340 → 2,231 |
| d3-4b | 0.889 → 0.961 [+0.043, +0.105] | 45% → 86% | 923 → 1,739 |
| d3-9b | 0.947 → 0.979 [+0.011, +0.055] | 74% → 90% | 1,467 → 2,639 |
| d3-27b | 0.980 → 0.998 [+0.008, +0.031] | 85% → 98% | 4,758 → 8,550 |
| Jev | 0.915 → 0.968 [+0.027, +0.083] | 58% → 83% | 118 → 125 |

Sources: [D3-4], [L-7]. All seven AUROC gains stay above zero after a Bonferroni correction [D·V check 13].

- **Workload** in the plausible scenario at thr98: for example 27b lp 4,257 → 2,788 flagged per 10,000
  (−1,469 [−2,812, −898]) and d3-27b 3,278 → 2,135 [B4.2]. 9b lp is the exception (+178 [−741, +965]) [B4.2].
- **Shared errors, like for like.** Consensus misses at 0.5 fall from 8 to 2. At thr98 the miss budget alone takes
  them to 0 [C·V correction 3]. Consensus false positives fall from 26 to 8 at thr98 and from 21 to 11 at 0.5. The
  8 that remain are all "purely personal" emails, so the models still don't apply that exception
  [C·V correction 4, C2c].
- **Cost.** For stock lp, the roster's 1,330 tokens changed median prefill by −2 to +12 ms. Reprocessing them
  would cost +618 to +3,399 ms [B1.3]. d3 reprocesses them on every call: +814 / +1,151 / +3,718 ms, or +2.26 to
  +10.33 h per 10,000 [B1.3].
- **It shifts the cutoff.** On the same pairs the roster moves thr98 from 0.5427 to 0.8529 (d3-9b) and from
  0.5405 to 0.9133 (d3-27b) [A1a]. A roster-prompt cutoff reused on 24-409 missed 82/144 (d3-9b) and 76/144
  (d3-4b) [A2b].

**Limits.** The roster was tested on one request, and it was compiled partly from that request's own production
[D4 row 15]. For the same reason, the keyword-proxy check is circular for 25-3152 [D·V check 16]. d3's roster
penalty was measured only at num_batch 8192. At that setting the stock 4b and 9b also stop reusing the prefix
(+855 and +1,222 ms median Δprefill), so the runs show *that* d3 reprocesses the roster, not *why*
[B·V concern 1].

**Interpretation.** For a request scoped by correspondents, put the member list in the request. Treat a prompt
with a roster as a new configuration that needs its own cutoff.

### 5. Decision models (d3 and Jev) against stock Qwen

**What the data show**

- **d3-27b vs 27b lp, main set: no detectable difference.** AUROC +0.004 [−0.004, +0.013] [E1b]; elim@98 +5.2
  [−5.7, +9.0] [E1c]; flagged per 10,000 −484 [−842, +564] [B5.2].
- **On 25-3152, d3-27b is better.** AUROC +0.026 [+0.010, +0.045], Holm p 0.010; elim@98 +11.0, Holm p 0.034
  [E5b]. With the roster, elim@98 is 98.2% vs 90.8%, +7.3 [+1.8, +11.9]. That is borderline: Holm p 0.034 among
  the 21 model pairs, 0.053 among the 24 package comparisons, and 0.064 by the normal reading [E1c roster set,
  E5b]. On workload it is −653 [−1,061, −163], which survives a Bonferroni-style bound [B5.5, B·V concern 3].
- **That edge depends on the scope reading.** Most of it comes from the 19 positives where an ACPG member is only
  one of 10 or more recipients and the group isn't named. With the roster, the elim@98 gap is +7.3 as labeled,
  +4.6 with those 19 dropped, and +0.8 [−10.9, +6.2] with them relabeled non-responsive. Without the roster it
  is +11.0, +5.5 and +7.0 [F2]. The AUROC gap without the roster stays near +0.02 under every reading [F2].
- **Smaller d3: nothing without the roster, a gain at 9b with it.** Without the roster, d3-4b ranks worse on
  24-409 (−0.084, Holm p 0.010), and there is no detectable difference elsewhere. With the roster, d3-9b eliminates
  more than 9b lp (+22.0, Holm p 0.040) [E5b] and flags 1,929 fewer per 10,000 [−3,056, −898], which survives the
  Bonferroni bound [B5.5, B·V concern 3]. On workload d3-9b + roster (8.0 h) matches 27b lp + roster (2,869 vs
  2,788 flagged) [B4.2, B5.5].
- **d3-27b's default held.** At 0.5 it missed 0/144 and 1/140 (0/140 with the roster) and eliminated 72%, 85% and
  93% [A3a]. Pooled, recall at 0.5 is 283/284 [98.0%–99.9%], against 93.0–95.4% for the other score models
  [E4c]. That reflects where its scores sit: the mean score on non-responsive pairs is 0.226 against 0.109 for
  27b lp [E5d]. It doesn't reflect calibration (conclusion 10). The cutoff fails above 0.5405 on 25-3152, and it
  was picked out after seeing seven models [A3b, A·V concern 7].
- **d3 is slower.** It takes 1.60–1.73× the machine time of the same-size stock lp (ratio of mean times), and
  3.14–3.56× with the roster [B1.8]. Per 10,000 emails: d3-27b 14.70 h (25.78 h with the roster) against 27b lp
  8.93 h (7.97 h) [B1.1, B1.2]. As a median of per-pair ratios, d3 takes 1.76× / 1.67× / 1.76× the cached stock
  lp at 4b / 9b / 27b [F4], but only 1.07× / 1.06× the stock runs with no prefix cache at 4b / 9b [E5e]. Most of
  the slowdown is the lost cache. A residual gap on long prompts (1.23 / 1.11 with the roster) is matched
  by the stock JSON runs, which share d3's batch-8192 setting [E5e, E·V concern 2].
- **The packages differ in at least four ways:** Q8_0 vs Q4_K_M weights, the llamacpp vs ggml runner, num_batch
  8192 vs default, and how the prompt is delivered [E5a, B1.8, L-5]. So a difference between d3 and stock is a
  difference between packages, not proof that d3's training or architecture is better.
- **Jev.**
  - **Speed and cost.** It is the fastest configuration: 117 ms median, network included. The fastest local one,
    4b lp, takes 4.3× as long [E3a]. Per 10,000 emails it takes 0.33 h and costs $0.93 [B1.1, B1.5]. The price
    is from TypeSafe's models page (docs.typesafe.ai/models.md, read 2026-11-04): $0.042 per million input
    tokens, "Output tokens are free". That settles B·V concern 6, as of that date.
  - **Ranking.** It sits in the middle AUROC tier (0.916). Only 27b lp and d3-27b beat it on both AUROC and
    elim@98 after Holm [E1b, E1c, E3d]. d3-27b flags 1,564 fewer emails per 10,000 [1,049–2,126]; that holds
    under a Bonferroni-style bound. The 650 fewer flagged by 9b lp do not hold under it [B5.2, B·V concern 3].
  - **Dates.** At its thr98, Jev passes 19/20 synthetic wrong-date emails against 3/20 for d3-27b (exact p
    3.1e-05, Holm 5.8e-04). Without a cutoff, the separation is 0.684 vs 0.988 [E2b, E2g].
  - **Data terms.** Using it sends the records to a third party, and the repo has no record of a review of its
    data terms [D4 row 12].

**Verified correction carried here.** E's analyst wrote that "d3-27b handles dates better than the stock 27b"
is *not supported*. The skeptic found the evidence mixed instead. At every recall level of 98% or more, d3-27b
passes fewer wrong-date emails (3 vs 10 at 98%; 3 vs 16 at 100%, p 2.4e-04), and E2d shows a date-specific
advantage for d3-27b (Holm p 0.027). The 21-pair Holm correction is not met (0.19), and the gap disappears at
93–95% recall [E·V concern 1]. This file uses the fairer reading: *not established*. It does not say *not
supported*.

**Interpretation.** Among local options, d3-27b and 27b lp are the candidates (section 3). Jev is ruled out by
the local-only constraint before accuracy comes into it.

### 6. Real vs synthetic: easy real negatives, hard synthetic negatives

**What the data show**

- **The real negatives aren't search hits.** 118/120 fall outside the target request's date window, 0/120 hit
  the keyword proxy, and the Opus pre-label rationale cites the window for 118/120 [D2-2]. They are 70–90% of the
  negatives cleared at each score model's thr98 [D1-7], against a base share of 120/211 (56.9%) of all negatives
  [D·V check 6].
- **On real emails alone the task is nearly solved:** AUROC 0.982–1.000, elim@98 71–100% [D1-1, D1-2 (a)]. That
  figure pools both requests. On 25-3152 alone, 4b lp clears only 23/60 of the real negatives, d3-4b 38/60 and
  Jev 46/60 [D3-3, D·V concerns].
- **The synthetic positives score like real ones.** P(synthetic+ > real+) is 0.47–0.57; close calls score lower
  (0.34–0.54) and privileged emails higher (0.54–0.67) [D2-8].
- **The hard negatives carry the difficulty.** P(hard− > real−) is 0.87–0.99 [D2-8]. Every consensus false
  positive is a synthetic hard negative (57/57), and no real negative is kept by more than 3 of the 7 models
  [C2b].
- **Against in-window hard negatives** (subset f: real positives vs the 71 hard negatives dated inside the
  window), elim@98 is 15–45%, against 52–81% in the headline [D1-2]. 9b lp, 27b lp and d3-27b are level there
  (45%, 42%, 41%), and no order among them holds [D·V check 15]. A stricter subset, in window *and* hitting the
  keyword proxy (35 emails), gives 9–34% [D·V check 17].
- **d3-27b's lead over 27b lp is mostly wrong-date emails.** Of its 171 vs 160 negatives cleared, 7 of the 11
  extra are wrong-date emails, which a date-limited search would remove [D·V check 8].
- **The cutoff is set mostly by real positives.** 16 of the 19 distinct emails sitting at thr98 are real, against
  a base rate of 75/144 and 75/140 [A1d, as corrected].
- **Realism and labels.** In the spot-read, 9 of 10 hard negatives and 7 of 10 synthetic positives read as real.
  That coding is judgment [D2 spot-read]. The verifier's style tell was mild for 104/225 and obvious for 2/225
  [D2-5]. 192 of 225 synthetic rows and 185 of 270 real rows have no human call. The random spot check found
  0/81 disagreements, with a 95% upper bound of 3.6% [L-2]. The 225 synthetic emails come from 130 sources, mostly
  real positives in the set, so the hard negatives are largely minimal pairs [D2-7].
- **These checks aren't independent of the generator.** Opus wrote the synthetic emails and the pre-labels. The
  realism codes (D) and the re-reads of the 68 consensus items (C) were made by AI analysts of the same model
  family. The human spot check was done on an adjudication page that showed the Opus pre-label and its rationale
  (`docs/golden-adjudication.md`, local only). So 0/81 measures agreement with a visible suggestion, and 3.6% is an upper
  bound on disagreement with the pre-label, not on the label error rate. A blind second human adjudication of a
  sample would fix this [D4 rows 3 and 5].

**Interpretation.** The headline (subset e) is an optimistic bound. Subset (f) is a more conservative proxy, but it
is not the floor. The data can't place a real deployment between the two, because the real mix of easy and
near-miss non-responsive hits is unknown [D2, D·V concern on (f)].

### 7. Cutoffs can't be set in advance with assurance from these data

**What the data show**

- **The two requests want different cutoffs for some models.** 27b lp 0.3623 [0.2529–0.7792] vs 0.0566
  [0.0079–0.1030]; d3-27b 0.8542 [0.7504–0.9201] vs 0.5405 [0.4870–0.6115]; Jev 0.57 [0.42–0.63] vs 0.31
  [0.22–0.35]. Each pair of intervals is disjoint [A1a]. A direct test of the difference finds no gap for d3-4b
  or 4b lp, and only a nominal one for 9b lp [A·V concern 3].
- **Transfer fails whenever the target needs a lower cutoff,** which by arithmetic is one of each pair of
  opposite directions. The failures are large: d3-27b, 24-409 → 25-3152, 31/140 missed; Jev 28/140; 27b lp 14/140;
  d3-9b, 25-3152+roster → 24-409, 82/144 [A2b]. Using the source request's 99% or 100% cutoff as a margin rescues
  one more direction only for d3-4b and Jev [A2c].
- **The default 0.5 holds on both requests only for d3-27b** (conclusion 5). Every other model misses at least 5
  on one request at 0.5 [A3a, A3c].
- **A small labeled sample can't certify 98%.** One rule sets the cutoff at the lowest-scoring responsive email in
  a random sample. At n = 50 it reaches 98% recall on the rest in 0.496 / 0.491 of repetitions at the golden
  prevalence and 0.194 / 0.200 at 20% prevalence. The exact rates are the same for every model without ties
  [A·V check 8]. 90% assurance needs about 114 responsive emails in the sample, a large-pool figure [A4a,
  A·V concern 4].
- **A margin restores recall at a model-specific cost.** Dividing the odds at the lowest sampled score by 10 (n =
  50, 20% prevalence) reaches 98% in at least 0.903 of repetitions for six models. 27b lp gets 0.549 / 0.648 /
  0.719 [A·V check 9]. Elimination on 25-3152 then falls to 4% (4b lp), 2% (d3-4b) and 0% (Jev), while d3-27b keeps
  73% / 62% / 93% [A4e].
- **A stated fixed-cutoff rule** (the largest grid value safe on all labeled subsets, minus one step) misses at
  most 1 per request. It eliminates 7–56 points less than the headline [A5e]. It is fitted on these same two
  requests, so the gap is not an out-of-sample estimate [A·V concern 6]. Fitted on one request and applied to the
  other, the same heuristic keeps 98% in 2–3 of 4 directions with one step of headroom [A2d].

**Interpretation.** These data can't show any cutoff policy to be safe on a third request. The best-supported
policy is a fixed cutoff per model *and per prompt*, fitted on every labeled request and stepped down, plus a
random-sample check on each new request (section 3) [A5 recommendation; confidence low].

### 8. Workload: reviewer time dominates, and the negative mix matters more than the model

**What the data show** (per 10,000 hits, plausible scenario: 20% responsive, 50/50 mix of real-like and hard-like negatives)

| config | machine h | flagged at in-sample thr98 [CI] | reviewer h at 30 s | flagged at 0.5 | missed at 0.5 [CI] |
|---|---|---|---|---|---|
| Jev | 0.3 | 5,287 [4,802–5,795] | 44.1 | 4,412 | 127 [70–183] |
| 9b lp | 2.8 | 4,637 [4,009–5,147] | 38.6 | 3,716 | 120 [63–169] |
| 27b lp | 8.9 | 4,207 [3,108–4,572] | 35.1 | 2,694 | 141 [85–197] |
| d3-27b | 14.7 | 3,723 [3,247–4,251] | 31.0 | 3,971 | 7 [0–21] |

Sources: [B2.3], [B2.4], [B3.1]. Reading all 10,000 takes 83.3 h at 30 s per email [B3.1].

- **Reviewer hours exceed machine hours** for every configuration in this scenario: 31.0–51.5 h of reading for the
  score models, against 0.3–14.7 h of scoring [B3.1]. The machine is the bottleneck only at 5% prevalence with
  easy negatives, for 27b lp (break-even 65 s per email), d3-27b (108 s) and 27b jsonR (55 s) [B3.2].
- **The negatives drive it.** For 27b lp, flagged runs from 1,965 (negatives like the real ones) to 6,448 (like
  the hard ones). Across models at the mix it runs 3,723–6,183 [B2.3].
- **Misses at thr98** are 35 per 10,000 by construction, averaged over two requests. A single request sees 0 to 71
  [B·V concern 2]. The bootstrap intervals on misses collapse when the count is small. Wilson intervals are the
  better guide: d3-27b at 0.5 misses 7 [1–39] per 10,000, and every model at its thr98 misses 35 [15–81] [F1].
- **If the search applies the date window,** the easy out-of-window negatives disappear. As a pessimistic bound,
  with every negative as hard as the synthetic in-window near misses, flagged per 10,000 rises to 6,134–7,486 at
  thr98 for these four models (27b lp 6,585, d3-27b 6,134) [F1].
- **The reviewer hours are a floor in one respect.** They don't count a quality-control sample of the discarded
  emails [B·V concern 7].

**Interpretation.** Speed decides turnaround, such as whether a batch finishes overnight. Accuracy decides how
many paid human hours follow [B3]. The scenario inputs are assumptions, not measurements [B5].

### 9. Errors are recognizable model errors; one scope reading is the label lever

**What the data show**

- **Misses rarely overlap.** At thr98, the 35 misses fall on 23 different positives. Only 3 are missed by 3 or
  more models, all of them real 25-3152 emails. At 0.5 there are 11 such consensus misses [C1d].
- **The shared miss is a passive recipient.** 7 of the 11 consensus misses at 0.5 are 25-3152 emails on which the
  planning-group chair is one of 19–31 recipients and the group isn't named. With 10 or more recipients the
  consensus-miss rate is 7/40, against 4/244 with fewer (Fisher p 0.000144) [C4c]. Within 25-3152, it is 8/58
  where the group isn't named vs 0/82 where it is (p 0.000642) [C4c, as corrected]. The recipient factor was
  chosen after reading the misses, and it is clear for 27b lp, 4b lp and Jev but not for d3-9b or d3-27b
  [C·V check 7, C·V concern 2].
- **The wrongly kept emails fall into kinds.** By recipe, consensus false positives are wrong-date 17/20, same
  people on a different subject 12/15, and keyword in an unrelated sense 13/19 [C2b]. The models also ignore the
  purely-personal exception (8 consensus false positives) and count a named correspondent as enough on 24-409,
  where item 4 also needs a listed term [C3b, CJ; low confidence].
- **Labels.** All 68 consensus items were read in full: 62 labels hold, 5 are arguable and 1 is likely wrong. This
  is one reader's judgment [C3b]. One real inconsistency stands out: six synthetic 24-409 emails share the
  "Geosyntec only in the addresses" pattern, and the owner flipped four to responsive and kept two
  non-responsive [C3c].
- **Effect of label fixes.** Any single questioned label moves mean elim@98 by +0.3 points, and that shift is
  mechanical: the same happens for any negative every model keeps [C5a, C·V check 10]. Making all nine purely
  personal emails responsive adds 1.8 points (5.2 on the roster runs) [C5b]. The narrower reading of
  "communications between" (a member who is only one of many recipients doesn't count) is the bigger lever. Applied
  consistently to all 19 matching positives, it changes mean elim@98 by +3.7 points, −4.0 on the roster runs
  [C·V concern 1].

**Verified correction carried here.** C's analyst reported +5.0 points (+18.1 for 4b lp) by flipping only the 7
emails the models miss. The skeptic's consistent version (+3.7 overall; −5.8 to +14.4 per model) is the one used
here. The 4b lp's 7-email figure has a bootstrap interval of −1.0 to +29.7 [C·V concern 1].

### 10. Calibration: the scores rank; they aren't probabilities

**What the data show**

- **Every score model's calibration slope differs from 1** [E4b]. 27b lp comes closest: Brier 0.060, ECE 0.030,
  intercept +0.26 [−0.07, +0.56], but it is overconfident at the extremes (slope 0.70 [0.59, 0.90]). The other six
  are compressed toward the middle, with slopes from 1.35 to 1.77 [E4a, E4b].
- **ECE is within bin noise only for 9b lp, 27b lp and d3-4b** (p 0.16, 0.10, 0.40) [E4a].
- **d3-27b overstates in its middle range.** Of the pairs it scores 0.7–0.8 and 0.8–0.9, only 0.54 and 0.57 are
  responsive (n = 26 and 28) [E4d].
- **JSON confidences are far from calibrated.** ECE is 0.056–0.155, against a noise floor with medians of
  0.004–0.011 (all p 5.0e-04) [E4a].
- **The golden set is 57.4% responsive by design.** If a request has 10% responsive emails and each class scores as
  it does here, a score calibrated here at 0.5 would mean 0.076 there [E4g].

**Interpretation.** Read the scores as rankings. A cutoff has to be set by policy (conclusion 7), not by reading
the score as a probability.

## 2. Hypotheses H1–H3: updated status

| hypothesis | status in `findings-golden.md` §10 | updated status | evidence |
|---|---|---|---|
| **H1** latency ≪ JSON | "supported in direction: 2.6–3.1×, not 10×" (earlier runs, 4b/9b lp at batch 8192) | **Supported, but not by an order of magnitude.** With 4b/9b lp now at the default batch (prefix cache on), the lp medians are 504 / 856 / 2,649 ms against json 2,749 / 4,435 / 6,805 and jsonR 2,909 / 5,267 / 7,014 ms. Each JSON median is under 10× its lp median. Decoding the JSON alone takes longer than the whole lp call at every size. For 4b/9b the comparison also includes the JSON runs' batch-8192 prefill penalty (+454 to +688 ms per call); at 27b both use the default batch | E3a, B1.4 |
| **H2** ≥98% recall with >50% eliminated | met by 9b lp and 27b lp; not by 4b lp; 27b jsonR formally | **Met in-sample on the designed set. Not shown for a cutoff set in advance.** In-sample, all seven score models clear 50% at the point estimate (52–81%), and the CI lower bound is above 50% for 9b lp, 27b lp, d3-9b, d3-27b and Jev. Per request with its own cutoff, 4b lp (29%) and d3-4b (45%) fall short on 25-3152 without the roster. The pooled cutoff leaves one request below 98% for every model. Label-free: only d3-27b's default (0/144, 1/140 missed; 72% and 85% eliminated) met both conditions on both requests, and it was picked after the fact. Without the roster, the stated fixed rule clears 66% combined for 27b lp and 74% for d3-27b. d3-9b sits at 106/211 (50%) and the other four lower (11–44%). The rule is fitted in-sample. Against in-window hard negatives no model reaches 50% (15–45%) | E1a, D3-1, A1c, A3a, A5e, D1-2 |
| **H3** score tracks error rate | lp yes; JSON no | **Partly.** Higher lp and d3 scores mean a higher share responsive, broadly, with dips in thinly filled bins. But no score is a calibrated probability: every slope CI excludes 1, and only 9b lp, 27b lp and d3-4b pass the ECE noise test. JSON confidences are far off (ECE 0.056–0.155). Calibration on this 57.4%-responsive set wouldn't carry to a request with fewer responsive emails | E4a, E4b, E4d, E4g |

## 3. Recommended setup for an agency under the local-only constraint

This is a recommendation (interpretation). It rests on two requests from one county. None of its cutoffs is
shown safe on a third request [A caveats, D4 row 1].

### The setup

| component | recommendation | why | evidence |
|---|---|---|---|
| model | **d3-27b** (decision model on the Qwen3.8-27B base, Q8_0, local through Ollama) | Top AUROC tier, statistically tied with 27b lp on the main set. The edge that holds up is the sample margin: with ÷10 at n = 50 it keeps 62–93% elimination, while 27b lp reaches 98% recall in only 0.55–0.72 of repetitions. It is also better on the correspondent-scoped request (AUROC +0.026), though that edge depends on the scope reading [F2]. Its default 0.5 held on both requests, but that was selected after comparing seven models on an in-sample prompt, by 1/140 on 25-3152 (Wilson upper bound 3.9%) | E1b, A4e, A·V check 9, E5b, F2, A3a, A·V concern 7, L-3, F5 |
| cutoff | **fixed 0.4** (0.5 also held), the same for every request of a given prompt | Stepped down one grid value from the largest cutoff safe on both requests. In-sample: 0/144 · 69%; 0/140 · 79%; 0/140 · 89% (24-409; 25-3152; 25-3152 + roster). Its headroom to the 25-3152 failure point (0.5405) is 0.57 in log-odds, less than 27b lp's 0.02 has to its own (1.08) | A5 recommendation table, A5e, F5 |
| sample check | review a random sample of the hits and lower the cutoff if any responsive email in it scores below the cutoff | A screen for large failures only. At 20% responsive, n = 50 catches a cutoff that misses 10% of responsive emails with probability 0.64, and one that misses 5% with probability 0.39. n = 200 raises these to 0.98 and 0.87. It can't certify 98% | A4, A5 policy step 3, F3 |
| roster | for correspondent-scoped requests, append the member list (names, roles, addresses) to the request | Raised AUROC for every model on 25-3152 | D3-4, B4.2 |
| search | apply the request's date window in the search, before scoring | The wrong-date recipe is the largest share of consensus false positives (17 of 57). A date filter removes the case where the models differ most | C3b, E2 (interpretation) |
| purely personal emails | leave to human review | The models don't apply the exception, even with the roster | C2c; `findings-golden.md` §12 item 3 |
| batching | score each request's hits together, one request at a time | That ordering gives stock Qwen its prefix cache. For d3 it makes no difference at the measured setting | B1.3 |
| backend | validate before use (cross-request probe, reloaded vs cached check, CPU reference) | The ROCm fault in `findings-golden.md` §7 wasn't caught by the canary | findings-golden §7 |
| first deployment | label at least one of the agency's own requests of each type and check the cutoff on it | Cutoffs depend on model, prompt and request | A1, A2 |

**Fallback if turnaround matters more than cutoff robustness: 27b lp** (stock Qwen3.8-27B, Q4_K_M, default batch).
It is in the same AUROC tier [E1b] and takes 8.93 h per 10,000, or 7.97 h with the roster, which costs it nothing
[B1.1, B1.2, B1.3]. It needs a low fixed cutoff: 0.02 or lower, in-sample 0/144 · 68%; 1/140 · 65%; 0/140 · 84%
[A5 recommendation table]. One real responsive email scores 0.0079 [A1d]. A sample check protects it poorly: with
the ÷10 margin at n = 50 and 20% prevalence it reaches 98% in only 0.549–0.719 of repetitions [A·V check 9]. At 0.5
it misses 141 per 10,000 [B2.4].

### Expected machine time and review load per 10,000 hits

Single stream on the Strix Halo, golden-like email lengths, 20% of hits responsive. Review load is given as a
range. The low end is B's plausible scenario: a 50/50 mix of easy real-like and hard negatives. That mix assumes
out-of-window emails that the recommended date filter would remove. The high end is a pessimistic bound in which
every negative is as hard as the synthetic in-window near misses. A real date-filtered search lies between
them [F1]. The inputs are assumptions [B5]. Misses use Wilson intervals, because bootstrap intervals collapse on
counts this small. A "0" means none was seen among 140–284 responsive emails, not that none will be missed.
Machine hours are point estimates: run-to-run variation (2.4–3.8%) and request-to-request variation (about ±8%)
are larger than their sampling intervals [B·V concern 4].

| configuration | machine h per 10,000 | flagged per 10,000: 50/50 mix – in-window hard | missed per 10,000 [Wilson 95%] | reviewer h at 30 s | source |
|---|---|---|---|---|---|
| d3-27b, cutoff 0.4 (recommended) | 14.7 | 4,418 – 7,408 | 0 [0–27] (0/284) | 36.8 – 61.7 | B1.1, F1 |
| d3-27b, cutoff 0.5 | 14.7 | 3,971 – 6,725 | 7 [1–39] (1/284) | 33.1 – 56.0 | B1.1, F1 |
| d3-27b + roster, cutoff 0.5, 25-3152 | 25.8 | 2,653 (50/50 mix) | 0 [0–53] (0/140) | 22 | B1.2, B4.2, B5.6, F6 |
| 27b lp, cutoff 0.02 (fallback) | 8.9 | 5,103 – 8,303 | 7 [1–39] (1/284) | 42.5 – 69.2 | B1.1, F1 |
| 27b lp, in-sample thr98 (optimistic bound) | 8.9 | 4,207 – 6,585 | 35 [15–81] (5/284) | 35.1 – 54.9 | B1.1, F1 |
| 27b lp + roster, in-sample thr98, 25-3152 | 8.0 | 2,788 (50/50 mix) | 29 [8–101] (2/140) | 23 | B1.2, B4.2, B5.6, F6 |
| no screen (read everything) | 0 | 10,000 | 0 | 83.3 | B3.1 |

The two roster rows are for 25-3152 only, and their in-window bound isn't computed. Their misses come from F6.
At 0.4 and 0.02 with the roster, both models miss 0/140 [F6]. With real positives only (the production, without the
synthetic close calls and exempt emails), d3-27b at 0.4 misses 0/150 and at 0.5 1/150; 27b lp at 0.02 misses
1/150 [F1, last column]. At their recommended cutoffs, the gap between d3-27b (0.4) and 27b lp (0.02) is 685
flagged per 10,000 under the 50/50 mix and about 900 under the in-window bound [F1].

Notes on the table:

- **Machine hours vary by request.** 27b lp takes 9.60 h on 24-409 and 8.28 h on 25-3152; d3-27b takes 13.94 h
  and 15.45 h [B·V concern 4]. Each +1,000 tokens of mean prompt length adds about 7.82 h for d3-27b and 7.10 h for
  27b lp [B1.6].
- **Add the sample check and a quality-control sample of the eliminated pile** to the review load. Neither is in
  B's figures [B·V concern 7].
- **Parallel scoring and other hardware weren't measured** [B "Not measured", L-8].

### What would change the recommendation

| if … | then … | evidence |
|---|---|---|
| a third or fourth labeled request shows d3-27b's fixed cutoff failing | fall back to per-request sample cutoffs with a margin, or larger samples. Fitted on 24-409 alone, the stepped-down heuristic would have picked 0.7 for d3-27b and missed 12/140 on 25-3152 | A2d |
| a 15–26 h single-stream turnaround per 10,000 is too slow | use 27b lp (8.93 h, roster free) with a cutoff of 0.02 or lower and a larger sample check | B1.1, B1.2, A4e |
| the search applies the date window strictly | d3-27b's wrong-date advantage stops mattering. On in-window hard negatives, 9b lp, 27b lp and d3-27b are level (45%, 42%, 41%), so 9b lp (2.83 h) becomes a candidate. But its safe fixed cutoff (0.1) eliminates only 29% and 25% on 25-3152 | D1-2 (f), D·V check 15, A5 recommendation table |
| a default-batch d3 run shows it can reuse the prefix | d3's roster penalty (+10.33 h per 10,000 at 27B) and part of its 1.60–1.73× slowdown would shrink | B·V concern 1, E·V concern 2 |
| stock Qwen 27B at Q8_0 matches d3-27b on 25-3152 | the d3 advantage is quantization, and stock at Q8_0 with the prefix cache would be preferred | E5a, D4 row 10 |
| a labeled sample of a real search result gives the actual prevalence and negative mix | recompute B's workload. For 27b lp the flagged range across negative mixes alone is 1,965–6,448 | B2.3 |
| counsel approves a hosted service's data terms | Jev becomes an option at 0.33 h, but it flags 1,564 [1,049–2,126] more per 10,000 than d3-27b | B5.2, B·V concern 3, D4 row 12 |
| the owner adopts the narrower "one member among many recipients" reading | the cutoffs move (those emails set them for several models), so refit them. d3-27b's advantage on 25-3152 also shrinks: with the roster, from +7.3 to +0.8 [−10.9, +6.2] points of elim@98, and AUROC from +0.009 to −0.007. Without the roster it shrinks from +11.0 to +7.0, while AUROC stays near +0.02. The case for d3-27b over 27b lp would then rest on the sample-margin result (A4e) and the main-set AUROC tie | C5b, C·V concern 1, F2 |
| repeat runs show d3 or Jev noise larger than measured | widen the stepped-down margin. d3's cached-vs-reloaded check on 60 pairs (30 with the roster) found it near-deterministic: mean \|Δscore\| ≤ 0.0056, 0–1 pairs crossing thr98. Jev's repeat noise is unmeasured | L-4, E caveats |

## 4. What can and can't be claimed publicly

### Claims the data support, with the caveat that must travel with each

| claim | careful wording | caveat that must travel with it | evidence |
|---|---|---|---|
| ranking works | "On a 495-email test set built from two San Diego County records requests, a 27-billion-parameter open model running locally ranked a randomly chosen responsive email above a non-responsive one about 97.5% of the time (AUROC 0.975)." | Two requests, one county. 225 of the 495 emails are synthetic edits written by another AI model. Labels are one reviewer's. Most non-responsive emails were easy (other requests' records, outside the date range). Against realistic in-range near misses the same model scored AUROC about 0.92 | E1a, L-1, L-2, D1-7, D1-2 (f) |
| how much it could set aside | "With a cutoff picked after seeing the answers, it would have set aside 76% of the non-responsive emails while keeping 98% of the responsive ones across the two requests combined (96.4% on one of them)." | That cutoff used the answers. Set in advance, cutoffs did worse: reusing one request's cutoff on the other missed 14 of 140 responsive emails for this model. Most emails set aside were easy, records from other requests and outside the date range. Against in-range near misses, the best models set aside about 41–42% | B·V V5, A1c, A2b, D1-7, D1-2 (f) |
| speed | "About 2.6 s per email (median; 3.2 s mean), one email at a time, on one desktop-class machine; about 9 hours per 10,000 emails (from the mean)." | Single stream, this hardware (AMD Strix Halo), this email-length mix. Parallel scoring not measured | E3a, B1.1 |
| JSON vs probability | "Asking the model for a written JSON verdict was slower than reading its yes/no probability, and it ranked worse at every model size tested." | One model family, these prompts | E3a, B1.4, D1-1 |
| the member list | "For a request defined by who sent or received the email, giving the model the member list raised every model's ranking accuracy (AUROC) on the one such request tested." | One request. The list was compiled partly from that request's own production. Elimination didn't rise for every model: 9b lp went from 70% to 68% | D3-4, D4 row 15, B4.2 |
| human time dominates | "Under stated assumptions (20% of hits responsive, 30 s per email), reading the flagged emails took 31.0–51.5 hours per 10,000 hits; scoring them took 0.3–14.7 hours." | The prevalence and the email mix are assumptions, not measured on a real search | B3.1, B5 |
| hosted vs local | "A hosted decision-model API was the fastest option tested (117 ms per email including the network), but it ranked mid-field and would have left more emails to review than the best local models." | One version (jev-1.14.0), our prompt, our network; its scores are rounded to 2 decimals. Using it sends records to a third party. If the vendor is named, give the version and the test date | E3a, E1b, B5.2, L-6, D4 row 12 |
| errors are recognizable | "The emails the models wrongly kept were near misses of recognizable kinds: wrong dates, a keyword used in another sense, the right people writing about something personal." | All of them were synthetic emails designed to be hard | C2b, C3b |
| cutoffs don't travel | "A cutoff that worked on one request could miss many responsive emails on the other: up to 31 of 140 for one model with the same prompt, and 82 of 144 when the first request's prompt included a member list." | Two requests; one of each type | A2b |

### Claims to avoid

| don't say | why | evidence |
|---|---|---|
| "The system achieves 98% recall" or "safe for CPRA compliance" | 98% is in-sample by construction; no label-free policy is shown safe on a new request; the screen's recall isn't a legal standard | A1c, A5, A·V concern 6 |
| "Eliminates 81% of non-responsive email" without qualification | In-sample, on a designed mix whose real negatives are mostly out-of-window records from other requests. Against in-window hard negatives the figure is 15–45% | D1-2, D1-7 |
| "Model X beats model Y" for neighbours | 9b vs 4b on elimination and d3-27b vs 27b lp overall are not established | E1c, B·V concern 3 |
| "Decision-model training beats stock Qwen" | quantization, runner, batch size and prompt delivery change together with the model | E5a, B1.8 |
| "A score of 0.8 means an 80% chance" | no model is calibrated; the set is 57.4% responsive by design | E4b, E4g |
| "The default 0.5 cutoff works" | only for d3-27b, picked after comparing seven models, on two requests | A3a, A·V concern 7 |
| "X hours per 10,000 on your machine" | one machine, single stream | B1.1, L-8 |
| "The prompt change improved accuracy by …" | prompt 2 was written after reading this set's misses | L-3, findings-golden §11 |
| "Real emails are nearly solved" | real negatives here aren't what a search returns; per request, small models struggle on 25-3152 | D2-2, D·V concerns |
| "Jev doesn't handle dates" as a general verdict | supported on 20 synthetic emails at this version. If it is said at all: "in our test it let 19 of 20 synthetic wrong-date emails through at its 98% cutoff" | E2b, E caveats |

### A short summary that stays within the evidence

> I tested whether a local open model could pre-screen emails for a public records request by reading its
> probability of answering "yes". On a 495-email test set built from two San Diego County requests (about half
> the emails synthetic, labels by one reviewer), the best local models ranked responsive above non-responsive
> emails with AUROC 0.975–0.979 at a median of about 2.6–4.7 s per email on one machine. With a cutoff picked
> after seeing the answers, they would have set aside 76–81% of non-responsive emails while keeping 98% of
> responsive ones across the two requests combined (96.4% on one of them). Most of the emails set aside were
> easy: records produced for other requests, outside the date range. Against realistic in-range near misses,
> the best models set aside about 41–42%. Cutoffs set in advance were less reliable. Asking for a written JSON
> verdict was slower and ranked worse. For a request defined by correspondents, giving the model the member list
> raised every model's ranking accuracy (the list was compiled partly from that request's records). Under stated
> assumptions, human review time far exceeded machine time. Two requests are too few to say how this
> generalizes.

Sources: [E1a], [E3a], [B·V V5], [A1c], [D1-7], [D1-2 (f)], [A2b], [D3-4], [D4 row 15], [B3.1].

## 5. Disagreements and unresolved concerns

### 5a. Where branches, or a branch's analyst and its skeptic, disagree

The verified reading is the one used in this file.

| topic | first reading | verified or other-branch reading | where it matters |
|---|---|---|---|
| d3-27b vs 27b lp on wrong dates | E analyst: "not supported" (Holm 0.19; tie at 0.5) | E skeptic: *not established*. At every recall level of 98% or more, d3-27b passes fewer (3 vs 10; 3 vs 16 at 100%). The 0.5 "tie" compares 93.0% vs 99.6% recall. E2d shows a date-specific d3-27b effect. D: 7 of d3-27b's 11 extra clears are wrong-date | how much d3-27b's edge depends on an unfiltered date range (E·V concern 1, D·V check 8) |
| the "passive recipient" label flip | C analyst: +5.0 mean elim@98 (4b lp +18.1, roster −0.8) | C skeptic, flipping all 19 matching positives: +3.7 (roster −4.0); 4b lp 7-email CI −1.0 to +29.7 | size of the scope question (C·V concern 1) |
| each request needs its own cutoff | A and D: yes, for all models | A skeptic: clear for 27b lp, d3-27b and Jev; nominal for 9b lp; no gap for d3-4b and 4b lp | how far the "per request" warning generalizes (A·V concern 3) |
| shortfall at the pooled cutoff | A analyst: "partly arithmetic" | A skeptic: wholly arithmetic; the bunching is what's informative (null probability 0.060 per model against 4/7 observed) | how to word conclusion 1 (A·V concern 1) |
| the stated fixed rule is "label-free" | A analyst's Short answer and Findings: "label-free", 7–56 points below the headline | A skeptic: fitted in-sample; the only out-of-sample evidence is A2d (2–3 of 4 directions) | planning numbers for H2 (A·V concern 6) |
| why d3 can't reuse the prefix | B1.3, D, E5: noncausal attention (from the brief) | B skeptic: num_batch 8192 alone stops reuse for stock 4b/9b. E skeptic: the batch-8192 stock JSON runs reproduce d3's per-token rise | d3's roster penalty; whether d3 could be faster (B·V concern 1, E·V concern 2) |
| roster effect on consensus misses | C analyst: "removes the consensus at thr98" | C skeptic: the miss budget does that; like for like at 0.5, 8 → 2; consensus false positives 26 → 8 (not 29 → 8) | conclusion 4 (C·V corrections 3–4) |
| JSON never on the frontier | E analyst: "in any redraw" | E skeptic: main set only; 27b json +roster sits on the 25-3152 frontier through a near-tie on different pair counts | conclusion 3 (E·V check 14, concern 7) |
| d3-27b vs 27b lp with the roster | B: −653 [−1,061, −163] flagged, robust under Bonferroni | E: elim@98 +7.3, Holm 0.034 (percentile) vs 0.064 (normal), close to backend noise; d3 repeat noise unmeasured | how firmly to prefer d3-27b on correspondent requests (B·V concern 3, E1c) |
| winner comparisons in B | B analyst: 9b lp "clearly ahead" of 4b lp; Jev leaves more to read than 9b lp | B skeptic: neither survives a Bonferroni bound; E agrees that 9b − 4b elim@98 is not established | conclusion 2 (B·V concern 3, E1c) |
| stock Qwen does worse on 25-3152, d3 doesn't | D Short answer | D skeptic: holds at 4b and 27b, not at 9b; d3-27b sits near the AUROC ceiling | conclusion 6 (D·V check 10) |
| real-only "nearly solved" | D, pooled over both requests | D skeptic: on 25-3152 alone, 4b lp clears 23/60 real negatives, d3-4b 38/60, Jev 46/60 | public claims (D·V concerns) |
| subset (f) as the conservative proxy | D analyst | D skeptic: a stricter search-like subset gives 9–34%; (f) isn't the floor | deployment estimates (D·V check 17) |
| misses don't track truncation | C analyst | C skeptic: "no large effect found with 38 truncated positives"; small models 4/38 vs 3.7–5.3% untruncated isn't ruled out | attachment and long-thread risk (C·V concern 4) |
| cutoff set by real emails vs difficulty in synthetic emails | A1d: the emails at thr98 are mostly real (16/19) | D: the difficulty is in the synthetic hard negatives | No conflict. Positives (mostly real) set the cutoff; negatives (the synthetic hard ones) decide how much is eliminated above it |
| near-ceiling AUROC rankings (roster set) | E percentile p: 10 differences survive Holm | E DeLong / normal: 4. The skeptic notes the choice of the conservative reading is reasonable but not demonstrated | ranking among the top roster models (E1e, E·V concern 6) |
| whether the model choice depends on the scope reading | first draft of this file: "the model choice doesn't depend on it" | critique, then F2: d3-27b's 25-3152 edge with the roster falls from +7.3 to +0.8 points of elim@98 when the 19 passive-recipient positives are relabeled | the recommendation's case for d3-27b (section 3, F2) |
| how the review load was presented | first draft: B's 50/50 mix only, with "at least" bounds for the recommended cutoffs | critique, then F1: computed at the recommended cutoffs and given as a range up to an in-window-only bound, because the recommended date filter removes the easy negatives the mix assumes | section 3 table (F1) |

### 5b. Unresolved concerns

**Design and data**

1. Two requests from one county, one of each type. Request type can't be separated from the particular request,
   and there is no estimate of request-to-request spread [D4 row 1, A·V concern 9].
2. The real negatives aren't search hits, and the repo has no real in-window near misses to substitute. The only
   real near misses are 7 + 3 over-produced emails, which the build excluded [D2-4, D2-4b].
3. Every hard negative was written by one generator family (Opus). No human-written or second-generator check
   exists [D4 row 3].
4. One adjudicator. 192/225 synthetic and 185/270 real rows have no human call. The legal scope questions are
   open: "communications between", purely personal by extension, the Geosyntec pattern, and 07:01 RDF
   [L-2, C open questions].
5. Real emails from the same thread aren't clustered in the bootstrap (84/150 real positives quote a thread)
   [D·V concerns].
6. The keyword proxy is circular for 25-3152, and the roster was built partly from that production
   [D·V check 16, D4 row 15].
7. Prompt 2 is in-sample [L-3].

**Measurement**

8. Every elim@98 is in-sample, and the bootstrap doesn't capture that optimism [E·V concern 5, A].
9. One run per configuration. d3's cached-vs-reloaded check (60 pairs, 30 with the roster) shows it near-
   deterministic (mean |Δscore| ≤ 0.0056) [L-4]. Jev's repeat noise is unmeasured. The stock cached-vs-fresh gap
   (up to 4.6 points) is a serving-path difference, not a pure repeat [E5g, E·V concern 4].
10. The d3 comparison is confounded (Q8_0, runner, num_batch 8192, prompt delivery). There is no default-batch d3
    run, no stock Q8_0 run and no uncached stock 27b run [E5a, E open questions].
11. Several Holm results sit at 0.034–0.064 and move under a reseed [E·V concern 3].
12. The recipient-count factor is post hoc, and the wrong-date "two windows" effect is confounded with distance from
    the window [C·V concerns 2–3].
13. The attachment content was never tested; the models see file names only [D4 row 16].

**Deployment**

14. Workload rests on an assumed prevalence and negative mix, and it omits quality-control sampling [B5, B·V concern 7].
15. Strix Halo only, single stream. The laptop, concurrency and Jev rate limits are untested [B "Not measured", L-8].
16. Jev's data terms are unreviewed [D4 row 12]. Its price is input tokens only, with output tokens free, per
    TypeSafe's models page as read on 2026-11-04 (this settles B·V concern 6, as of that date).
17. The models ignore the purely-personal exception. Whether to fix this in the prompt or leave it to review is
    open [C2c, findings-golden §12 item 3].
18. The named-correspondent rule may leak into topical requests (24-409 item 4 needs a listed term as well).
    Testing a narrower rule needs a held-out request [CJ, C open question 5].
19. The sample check is weak against moderate failures. At n = 50 and 20% responsive, it catches a cutoff that
    misses 5% of responsive emails with probability 0.39 [F3]. The workload figures don't include it.

## 6. Plan for refreshing `docs/findings-golden.md`

The edits are described here; `findings-golden.md` itself isn't changed by this branch. Numbers should come from
`scripts/golden_report.py` or a `scripts/analysis/` script, as now.

| section | change | content and source |
|---|---|---|
| header and status | update the date and status; list the runs | Main 4b/9b lp runs are now `_p2db` (default batch, prefix cache on, rechecked clean on 0.40.13 [B1.4]); add the d3 and Jev runs; link `docs/analysis/` and this file; state once that every elim@98 is in-sample |
| Setup | add the d3 and Jev configurations; correct the batch note | d3: Q8_0, llamacpp, `/v1/systemone`, num_batch 8192; Jev: hosted, 2-decimal scores, network in wall time [E0, E5a, L-5, L-6]. 4b/9b lp now at the default batch; 4b/9b JSON still at 8192 [B1.4] |
| §1 Headline | replace the 4b/9b lp rows; add four rows; relabel a column; rewrite the bullets | The current rows (47% / 72%, 0.89 / 1.46 s) are the batch-8192 runs; use 0.923 / 52% and 0.942 / 71%, medians 504 / 856 ms [E1a, E3a]. Add d3-4b, d3-9b, d3-27b and Jev [E1a, E3a]. Relabel elim@98 as "in-sample". Bullets: three AUROC tiers [E1b]; elim@98 neighbours not established [E1c]; per-request shortfall at the pooled cutoff [A1c, A·V concern 1]; real-only figures with D's caveat that the real negatives aren't search hits [D1-1, D2-2] |
| §2 JSON | keep the matched-yes-rate table; add | decode alone exceeds the whole lp call [E3a, B1.4]; three JSON runs need cutoff 0 at 98% recall [B2.1, B·V check 10]; frontier result with the 25-3152 exception [E3c, E·V check 14]; JSON doesn't rescue the consensus misses [CJ] |
| §3 Reasoning first | keep | no new evidence beyond §2 |
| §4 By kind | add d3 and Jev columns; add three bullets | recipe pass-through for all seven [E2a]; where the headline elimination comes from [D1-7]; subset (f) [D1-2]; consensus false positives all synthetic [C2b]; the wrong-date verdict in the verified wording [E2, E·V concern 1] |
| §5 Named-correspondent rule | add | the 24-409 side effect (low confidence) [CJ, C2d]; prompt 2's gain is in-sample [L-3]; open question on limiting the rule to correspondent-scoped requests [C open question 5] |
| §6 Roster | add d3 and Jev rows; replace the cost bullet; add two bullets | rows [D3-4]. The "batch 8192, no prefix cache, 0.90 → 1.78 s" bullet is stale for the `_p2db` runs; replace with −2 to +12 ms for stock and +814 / +1,151 / +3,718 ms for d3, with the num_batch caveat [B1.3, B·V concern 1]. Cutoff shift [A1a, A1b]; like-for-like consensus effects [C·V corrections 3–4, C2c] |
| §7 Backend fault | add one closing sentence | the default batch was rechecked on 0.40.13 and the main 4b/9b lp runs now use it [B1.4]; replace "The default batch hasn't been retested". Keep the October numbers as history |
| §8 Ollama upgrade | keep; add a pointer | cached vs fresh score differences on 0.40.13 [E5g, L-4] |
| §9 Labels | add a "pending owner decisions" list | 03:01 / 03:09 vs the four Geosyntec flips [C3c]; 07:01 RDF [C5a]; 15:01 / 15:02 / 15:06 purely personal by extension [C5a]; the "one member among many" scope question with the verified effect (+3.7 points; −4.0 roster) [C·V concern 1] |
| new §: Decision models | add | E1 tiers; E5b where d3 helps or hurts; d3-27b's default and why it held [A3a, E4c, E5d]; time and its causes [B1.8, E5e, E·V concern 2]; Jev speed, cost, dates and data terms [E3a, B1.5, E2b, D4 row 12]; the package confounds [E5a] |
| new §: Setting the cutoff without labels | add | A1a/A1b (with the skeptic's narrowing), A2b, A3a, A4 (exact rates from A·V check 8), A5e marked in-sample, the recommended policy marked as interpretation |
| new §: Workload per 10,000 hits | add | B2.3, B2.4, B3.1, B4.2 with the scenario assumptions; B·V concerns 2, 3 and 7 |
| new §: Calibration | add | E4a, E4b, E4d, E4g |
| new §: Validity | add | a short version of D's register (D4), the subset table (D1-2), the realism checks (D2-5 to D2-8, spot-read) |
| §10 Hypotheses | replace | the table in section 2 of this file |
| §11 Caveats | add | in-sample cutoffs; real negatives aren't search hits; one generator, and the label/realism checks aren't independent of it (section 1, conclusion 6); keyword proxy circular for 25-3152; backend noise not in the bootstrap; d3 confounds; d3-27b's 25-3152 edge depends on the scope reading [F2]; Jev data terms; reviewer hours omit quality-control sampling |
| §12 Next | add items | a third and fourth labeled request (one of each type); a labeled sample of a real search result (prevalence, negative mix, real near misses); a default-batch d3 run; stock 27B at Q8_0; an uncached stock 27b run; repeat runs of Jev (and a larger d3 repeat); elusion-sample design sized from F3; the owner's label decisions (§9 list); a narrower named-correspondent rule tested on a held-out request; attachment text extraction |
| report script | optional | have `golden_report.py` print per-request misses at the pooled cutoff (A1c) and lp/JSON latency ratios, so §1 and H1 can cite them directly |

## 7. Critique follow-ups (F1–F6)

A completeness critic read this file and the five branch files as a hostile reviewer. It reproduced the headline,
the per-request misses at the pooled cutoff (A1c), subset (f) and B's scenario workloads with its own code, and
found no arithmetic errors. Its main objections, and how they were handled:

| objection | resolution | where |
|---|---|---|
| The public summary dropped the easy-negatives caveat, and "98% of responsive" hid the 96.4% on one request | Both added to the short summary and the claims table | section 4 |
| "The model choice doesn't depend on" the passive-recipient scope reading | Wrong. With the roster, d3-27b's elim@98 edge over 27b lp falls from +7.3 to +0.8 when the 19 such positives are relabeled [F2] | sections 3, 5 |
| The review-load table assumed the easy negatives that the recommended date filter removes | Review load is now a range from B's 50/50 mix to an in-window-only bound [F1] | section 3 |
| The recommended cutoffs had no workload figures, only "at least" bounds | Computed: d3-27b at 0.4 flags 4,418–7,408; 27b lp at 0.02 flags 5,103–8,303 [F1] | section 3 |
| The bootstrap miss intervals collapse to [0–0] | Wilson intervals replace them [F1, F6] | sections 1 (8), 3 |
| The case for d3-27b leaned on its default 0.5, which was chosen post hoc, with less headroom than claimed | The "why" cell leads with the sample-margin result and states the post-hoc selection and the headroom [F5] | section 3 |
| The sample check's detection power was never computed | 0.39 at n = 50 for a 5% shortfall; 0.87 at n = 200 [F3] | sections 3, 5b |
| The validation checks were presented as independent | They are AI-on-AI, and the human spot check wasn't blind to the pre-label | conclusion 6 |
| "Smaller d3 adds nothing" contradicts d3-9b + roster | Reworded | conclusions table row 5, conclusion 5 |
| Holm p quoted only from the favourable family; d3 repeat noise called unmeasured; latency ratios mixed statistics; Jev price unsourced | Fixed: both Holm families quoted; L-4 cited; statistic named in each ratio [F4]; price sourced to TypeSafe's models page | conclusion 5, section 5b |
| The branch files still carry two analyst sentences their skeptics disputed | Marked inline in `A-cutoffs.md` and `E-comparisons.md` | branch files |

`scripts/analysis/f_followups.py` prints F1 (workload at the recommended cutoffs under three negative mixes, Wilson
misses, real-positive sensitivity), F2 (scope dependence of d3-27b vs 27b lp, paired bootstrap), F3 (sample-check
power), F4 (latency ratios with the statistic named), F5 (cutoff headroom on 25-3152) and F6 (roster-run misses
with Wilson intervals). It is stdlib only and finishes in a few seconds. F2 uses the passive-recipient rule from
`scripts/analysis/c_misses_verify.py`.

## Sources

- Branch files, each with a "## Verification" section: `docs/analysis/A-cutoffs.md`, `docs/analysis/B-workload.md`,
  `docs/analysis/C-misses.md`, `docs/analysis/D-validity.md`, `docs/analysis/E-comparisons.md`.
- Scripts that print every cited table: `scripts/analysis/a_cutoffs_*.py`, `b_workload_*.py`, `c_misses*.py`,
  `d_validity_*.py`, `e_comparisons_*.py` and `f_followups.py`. The independent checks are in `*_verify.py` (and
  `a_cutoffs_check.py`). Each branch's Reproduce table gives the commands; all are stdlib only, deterministic, and
  run from the project root with `uv run python`.
- `docs/findings-golden.md` §10–12 for the earlier hypothesis status, caveats and next steps.
- Jev's price: docs.typesafe.ai/models.md, read 2026-11-04.
