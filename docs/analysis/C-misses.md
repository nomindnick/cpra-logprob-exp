# C. Missed responsive emails, consensus false positives, and label questions

> **Snapshot of 2026-11-06, on the 2026-10-31 labels (495 pairs).** The labels changed afterwards: five hard
> negatives were relabeled responsive on 2026-11-08, and one email (24-409 synthetic 07:09) was put back in the set
> on 2026-11-11 (`docs/findings-golden.md` §9). The tables below are copies of script output on the old labels.
> Rerun the commands in the Reproduce section for current numbers; the scripts now read the pair counts from the
> golden set (`scripts/analysis/golden_counts.py`). `docs/findings-golden.md` carries the current figures, and
> `conclusions.md` section 0 lists what the relabeling changed.

**Date:** 2026-11-06 · **Branch:** C of the golden-set analysis · **Scripts:** `scripts/analysis/c_misses*.py` (see Reproduce)

## The question

Which responsive emails do the seven score models miss, which non-responsive emails do they all keep, and are
some of those label problems rather than model errors?

**Short answer.** The models' misses are mostly *different* emails; the few they share are one kind: a
25-3152 email on which the planning-group chair is one of many recipients of another group's thread. The
negatives they all keep are all synthetic hard negatives: chiefly wrong-date emails (17 of 57), a keyword in
another sense or a near-name (12), the "purely personal" 25-3152 emails (8) and keywords only in footers (8).
On reading every one, almost all labels hold; one is inconsistent with the owner's own calls on emails of the
same pattern, and five more are arguable. Fixing any single questioned label moves the headline by well under
one percentage point; what moves it is how the owner reads "communications between" a member and others when
the member is only one of many recipients.

## Data and method

**Runs (main tables).** The seven score models, each on all 495 golden pairs, and each one's `_roster` twin on
the 249 pairs of 25-3152 (roster appended to the request text):

| name | run | score |
|---|---|---|
| 4b lp, 9b lp, 27b lp | `golden_qwen3.5_4b_logprob_p2db`, `golden_qwen3.5_9b_logprob_p2db`, `golden_qwen3.8_27b_logprob_p2` | first-token P(yes)/(P(yes)+P(no)) |
| d3-4b, d3-9b, d3-27b | `golden_d3-ctx8k_{4b,9b,27b}_noul_p2` | the model's P(yes) |
| Jev | `golden_jev-1.14.0_noul_p2` | P(yes), rounded to 2 decimals |

JSON verdict runs (`golden_qwen3.5_{4b,9b}_json_p2`, `golden_qwen3.8_27b_json_p2` and the `_json_reason_p2` twins)
appear only as a contrast (section CJ); their 5 rows with a null score are dropped (listed in CJ).

**Labels.** Label, kind and recipe come from `data/golden/pairs.jsonl`, joined on `pair_id` by
`golden_report.load_runs()` (rows not in the golden set are dropped). Main set: 284 positives, 211 negatives.
Roster runs: 140 positives, 109 negatives.

**Definitions.**

- **thr98**: for each run, the highest score threshold at which at least 98% of that run's positives score at or
  above it (`golden_report.thr98`), computed on the run's own pairs ("pooled, in-sample": both requests together,
  using the labels being evaluated). With 284 positives this allows 5 misses per model; with 140 (roster runs), 2.
- **Missed**: a positive scoring below the cutoff (thr98, or 0.5 for the default decision).
- **Kept**: a negative scoring at or above the cutoff; it survives the screen and goes to a human reviewer.
- **Consensus miss**: a positive missed by at least 3 of the 7 models. **Consensus false positive**: a negative kept
  by at least 5 of the 7.
- **elim@98**: share of negatives below thr98. **AUROC**: probability that a random positive outscores a random
  negative (ties count half).
- **Rates** are shown as k/n with a 95% Wilson interval. Fisher exact tests are two-sided and uncorrected for the
  number of tests.
- **Hook location** (section C4) is a keyword heuristic. For 24-409 it looks for the request's listed terms
  (Hinds, Lerner, USP, GPS, Urban Studies, Global Policy, UCSD, RWER, Water Equity, RDF, Decarbonization Framework,
  Geosyntec, Murakawa, Fletcher) in the subject or the first 8,000 body characters, then attachment names, then
  past the cap, then headers. For 25-3152 it asks whether the ACPG is named in the visible text, and otherwise
  whether a roster member's address or name is in the headers.
- **Recipients**: distinct e-mail addresses in To, Cc and Bcc. **Prompt tokens**: each run's own count.

**Reading (C3).** `c_misses_read.py` prints every consensus miss and consensus false positive in full: the
request text and roster, every header, attachment names, the whole body (marked where the 8,000-character cap
cuts it), the stored rationale, the generator's and verifier's notes, the Opus pre-label, the human adjudication
call and note, each model's score and the JSON verdicts. All 68 were read. The analyst's judgment of each label
(right / arguable / likely wrong) and the model error type are coded in `c_misses_labels.py`; every count built
on them is computed there. "Right" means the label follows from the request text and the owner's recorded rules;
"arguable" means a careful reader could reach the other label on the same record; "likely wrong" means the label
conflicts with the owner's own calls on materially identical emails. The legal calls (scope of "communications
between", *City of San Jose v. Superior Court* (2017) 2 Cal.5th 608) remain the owner's.

## C1. Which responsive emails the models miss

### C1a. Per model

| model | thr98 | recall at thr98 | missed at thr98 | which (lowest score first) | missed at 0.5 |
|---|---|---|---|---|---|
| 4b lp | 0.2650 | 279/284 | 5 | 25-3152 real 48518202, 25-3152 real 48517588, 25-3152 real 48518005, 24-409 real 33733127, 24-409 real 33733077 | 14 |
| 9b lp | 0.3309 | 279/284 | 5 | 24-409 syn 00:03, 24-409 syn 03:07, 24-409 real 33733085, 24-409 real 32980197, 24-409 real 33733127 | 17 |
| 27b lp | 0.0687 | 279/284 | 5 | 25-3152 real 48517769, 25-3152 real 48517588, 25-3152 real 48517567, 25-3152 real 48517463, 25-3152 syn 20:06 | 20 |
| d3-4b | 0.3507 | 279/284 | 5 | 24-409 real 33733472, 25-3152 real 48517463, 24-409 syn 02:01, 25-3152 real 48517567, 24-409 real 33733077 | 17 |
| d3-9b | 0.3379 | 279/284 | 5 | 24-409 real 33733472, 24-409 real 33733426, 24-409 syn 00:03, 25-3152 real 48517463, 24-409 syn 01:01 | 13 |
| d3-27b | 0.5857 | 279/284 | 5 | 25-3152 real 48518125, 25-3152 real 48517567, 25-3152 real 48517666, 25-3152 real 48517769, 25-3152 real 48517998 | 1 |
| Jev | 0.3400 | 279/284 | 5 | 25-3152 real 48518005, 25-3152 syn 14:03, 25-3152 real 48517769, 25-3152 real 48517350, 25-3152 real 48517957 | 18 |

### C1b. Overlap at thr98

Cell = that model's score; **bold** = below that model's thr98 (missed). Sorted by how many models miss it.

| pair | kind | models missing | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev |
|---|---|---|---|---|---|---|---|---|---|
| 25-3152 real 48517463 | real_positive | 3 | 0.28 | 0.67 | **0.06** | **0.19** | **0.32** | 0.59 | 0.36 |
| 25-3152 real 48517567 | real_positive | 3 | 0.42 | 0.60 | **0.06** | **0.32** | 0.62 | **0.51** | 0.35 |
| 25-3152 real 48517769 | real_positive | 3 | 0.38 | 0.81 | **0.01** | 0.56 | 0.74 | **0.54** | **0.31** |
| 24-409 real 33733077 | real_positive | 2 | **0.25** | 0.52 | 0.82 | **0.33** | 0.54 | 0.88 | 0.62 |
| 24-409 real 33733127 | real_positive | 2 | **0.24** | **0.32** | 0.93 | 0.61 | 0.61 | 0.92 | 0.74 |
| 24-409 real 33733472 | real_positive | 2 | 0.30 | 0.40 | 0.48 | **0.11** | **0.26** | 0.77 | 0.42 |
| 24-409 syn 00:03 | close_call_positive | 2 | 0.47 | **0.18** | 0.78 | 0.75 | **0.31** | 0.93 | 0.78 |
| 25-3152 real 48517588 | real_positive | 2 | **0.19** | 0.52 | **0.05** | 0.54 | 0.64 | 0.64 | 0.34 |
| 25-3152 real 48518005 | real_positive | 2 | **0.22** | 0.40 | 0.18 | 0.54 | 0.71 | 0.72 | **0.22** |
| 24-409 real 32980197 | real_positive | 1 | 0.80 | **0.30** | 1.00 | 0.75 | 0.73 | 1.00 | 0.89 |
| 24-409 real 33733085 | real_positive | 1 | 0.42 | **0.25** | 0.99 | 0.72 | 0.59 | 0.97 | 0.80 |
| 24-409 real 33733426 | real_positive | 1 | 0.69 | 0.54 | 0.36 | 0.62 | **0.27** | 0.92 | 0.57 |
| 24-409 syn 01:01 | close_call_positive | 1 | 0.67 | 0.59 | 0.25 | 0.67 | **0.33** | 0.94 | 0.72 |
| 24-409 syn 02:01 | close_call_positive | 1 | 0.75 | 0.59 | 0.27 | **0.26** | 0.35 | 0.75 | 0.63 |
| 24-409 syn 03:07 | hard_negative_flipped/same_people_different_subject | 1 | 0.36 | **0.24** | 0.78 | 0.69 | 0.58 | 0.95 | 0.82 |
| 25-3152 real 48517350 | real_positive | 1 | 0.87 | 0.95 | 0.83 | 0.86 | 0.84 | 0.78 | **0.33** |
| 25-3152 real 48517666 | real_positive | 1 | 0.82 | 0.84 | 0.24 | 0.73 | 0.77 | **0.54** | 0.67 |
| 25-3152 real 48517957 | real_positive | 1 | 0.66 | 0.49 | 0.07 | 0.56 | 0.56 | 0.79 | **0.33** |
| 25-3152 real 48517998 | real_positive | 1 | 0.68 | 0.53 | 0.33 | 0.60 | 0.88 | **0.57** | 0.70 |
| 25-3152 real 48518125 | real_positive | 1 | 0.76 | 0.90 | 0.10 | 0.75 | 0.90 | **0.49** | 0.64 |
| 25-3152 real 48518202 | real_positive | 1 | **0.14** | 0.54 | 0.25 | 0.41 | 0.73 | 0.84 | 0.47 |
| 25-3152 syn 14:03 | close_call_positive | 1 | 0.78 | 0.83 | 0.84 | 0.87 | 0.80 | 0.86 | **0.29** |
| 25-3152 syn 20:06 | privileged_positive | 1 | 0.27 | 0.68 | **0.06** | 0.43 | 0.60 | 0.63 | 0.57 |

### C1c. Overlap at the default decision (score below 0.5)

Rows for positives missed by at least 2 models, copied from the script output; the script also prints the 35
positives that exactly one model misses.

Cell = score; **bold** = below 0.5.

| pair | kind | models missing | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev |
|---|---|---|---|---|---|---|---|---|---|
| 24-409 real 33733472 | real_positive | 6 | **0.30** | **0.40** | **0.48** | **0.11** | **0.26** | 0.77 | **0.42** |
| 25-3152 real 48517463 | real_positive | 5 | **0.28** | 0.67 | **0.06** | **0.19** | **0.32** | 0.59 | **0.36** |
| 25-3152 real 48517567 | real_positive | 4 | **0.42** | 0.60 | **0.06** | **0.32** | 0.62 | 0.51 | **0.35** |
| 25-3152 real 48518005 | real_positive | 4 | **0.22** | **0.40** | **0.18** | 0.54 | 0.71 | 0.72 | **0.22** |
| 25-3152 real 48518202 | real_positive | 4 | **0.14** | 0.54 | **0.25** | **0.41** | 0.73 | 0.84 | **0.47** |
| 24-409 syn 00:03 | close_call_positive | 3 | **0.47** | **0.18** | 0.78 | 0.75 | **0.31** | 0.93 | 0.78 |
| 24-409 syn 02:01 | close_call_positive | 3 | 0.75 | 0.59 | **0.27** | **0.26** | **0.35** | 0.75 | 0.63 |
| 25-3152 real 48517588 | real_positive | 3 | **0.19** | 0.52 | **0.05** | 0.54 | 0.64 | 0.64 | **0.34** |
| 25-3152 real 48517769 | real_positive | 3 | **0.38** | 0.81 | **0.01** | 0.56 | 0.74 | 0.54 | **0.31** |
| 25-3152 real 48517957 | real_positive | 3 | 0.66 | **0.49** | **0.07** | 0.56 | 0.56 | 0.79 | **0.33** |
| 25-3152 syn 20:06 | privileged_positive | 3 | **0.27** | 0.68 | **0.06** | **0.43** | 0.60 | 0.63 | 0.57 |
| 24-409 real 33733047 | real_positive | 2 | **0.48** | **0.33** | 0.96 | 0.57 | 0.59 | 0.91 | 0.83 |
| 24-409 real 33733077 | real_positive | 2 | **0.25** | 0.52 | 0.82 | **0.33** | 0.54 | 0.88 | 0.62 |
| 24-409 real 33733085 | real_positive | 2 | **0.42** | **0.25** | 0.99 | 0.72 | 0.59 | 0.97 | 0.80 |
| 24-409 real 33733127 | real_positive | 2 | **0.24** | **0.32** | 0.93 | 0.61 | 0.61 | 0.92 | 0.74 |
| 24-409 real 33733426 | real_positive | 2 | 0.69 | 0.54 | **0.36** | 0.62 | **0.27** | 0.92 | 0.57 |
| 24-409 syn 01:01 | close_call_positive | 2 | 0.67 | 0.59 | **0.25** | 0.67 | **0.33** | 0.94 | 0.72 |
| 24-409 syn 01:04 | close_call_positive | 2 | 0.59 | **0.42** | 0.89 | 0.64 | **0.38** | 0.96 | 0.67 |
| 24-409 syn 03:07 | hard_negative_flipped/same_people_different_subject | 2 | **0.36** | **0.24** | 0.78 | 0.69 | 0.58 | 0.95 | 0.82 |
| 25-3152 real 48517577 | real_positive | 2 | 0.62 | 0.56 | **0.34** | 0.84 | 0.78 | 0.81 | **0.36** |
| 25-3152 real 48518046 | real_positive | 2 | 0.64 | 0.90 | **0.46** | 0.78 | 0.75 | 0.82 | **0.35** |
| 25-3152 real 48518125 | real_positive | 2 | 0.76 | 0.90 | **0.10** | 0.75 | 0.90 | **0.49** | 0.64 |
| 25-3152 syn 23:08 | exempt_other_positive | 2 | 0.62 | 0.53 | **0.32** | 0.85 | 0.75 | 0.79 | **0.41** |

### C1d. Consensus misses

| cutoff | miss events (sum over 7 models) | distinct positives missed | missed by exactly 1 / 2 / 3 / 4 / 5 / 6 / 7 models | consensus (>= 3) | consensus pairs |
|---|---|---|---|---|---|
| thr98 | 35 | 23 | 14 / 6 / 3 / 0 / 0 / 0 / 0 | 3 | 25-3152 real 48517463, 25-3152 real 48517567, 25-3152 real 48517769 |
| 0.5 | 100 | 58 | 35 / 12 / 6 / 3 / 1 / 1 / 0 | 11 | 24-409 real 33733472, 25-3152 real 48517463, 25-3152 real 48517567, 25-3152 real 48518005, 25-3152 real 48518202, 24-409 syn 00:03, 24-409 syn 02:01, 25-3152 real 48517588, 25-3152 real 48517769, 25-3152 real 48517957, 25-3152 syn 20:06 |
| thr95 (sensitivity) | 98 | 54 | 31 / 13 / 3 / 4 / 2 / 1 / 0 | 10 | 25-3152 real 48517463, 24-409 real 33733472, 25-3152 real 48517567, 25-3152 real 48517588, 25-3152 real 48517769, 25-3152 real 48518005, 25-3152 syn 20:06, 24-409 syn 00:03, 24-409 syn 02:01, 25-3152 real 48518202 |

Union of the thr98 and 0.5 consensus misses: 11 pairs (3 from 24-409, 8 from 25-3152; 8 real, 3 synthetic). thr95 per model: 4b lp 0.529, 9b lp 0.432, 27b lp 0.334, d3-4b 0.457, d3-9b 0.531, d3-27b 0.722, Jev 0.450.

### C1e. With the roster (25-3152 only)

| model +roster | thr98 | missed at thr98 | which | missed at 0.5 | which |
|---|---|---|---|---|---|
| 4b lp | 0.5606 | 2 | 25-3152 real 48517588, 25-3152 real 48517463 | 1 | 25-3152 real 48517588 |
| 9b lp | 0.3901 | 2 | 25-3152 real 48518005, 25-3152 real 48517957 | 5 | 25-3152 real 48518005, 25-3152 real 48517957, 25-3152 real 48517588, 25-3152 syn 20:06, 25-3152 real 48517463 |
| 27b lp | 0.0783 | 2 | 25-3152 syn 14:02, 25-3152 real 48518125 | 18 | 25-3152 syn 14:02, 25-3152 real 48518125, 25-3152 real 48517398, 25-3152 real 48517374, 25-3152 syn 22:05, 25-3152 real 48517769, 25-3152 syn 23:06, 25-3152 real 48517463, 25-3152 real 48517859, 25-3152 real 48517957, 25-3152 syn 20:05, 25-3152 real 48517588, 25-3152 real 48517596, 25-3152 real 48518148, 25-3152 syn 20:06, 25-3152 real 48517865, 25-3152 syn 23:08, 25-3152 real 48517567 |
| d3-4b | 0.7588 | 2 | 25-3152 syn 20:07, 25-3152 syn 22:09 | 0 |  |
| d3-9b | 0.8529 | 2 | 25-3152 syn 12:08, 25-3152 real 48517581 | 0 |  |
| d3-27b | 0.9133 | 2 | 25-3152 real 48517768, 25-3152 real 48517463 | 0 |  |
| Jev | 0.4600 | 2 | 25-3152 real 48517398, 25-3152 real 48518005 | 5 | 25-3152 real 48517398, 25-3152 real 48518005, 25-3152 real 48517769, 25-3152 real 48517957, 25-3152 real 48518125 |

- Roster consensus misses at thr98: 0
- Roster consensus misses at 0.5: 2 (25-3152 real 48517588, 25-3152 real 48517957)
- The 8 main-set 25-3152 consensus misses, with the roster: missed at thr98 by 25-3152 real 48517463 2; 25-3152 real 48517567 0; 25-3152 real 48517588 1; 25-3152 real 48517769 0; 25-3152 real 48517957 1; 25-3152 real 48518005 2; 25-3152 real 48518202 0; 25-3152 syn 20:06 0; at 0.5 by 25-3152 real 48517463 2; 25-3152 real 48517567 1; 25-3152 real 48517588 3; 25-3152 real 48517769 2; 25-3152 real 48517957 3; 25-3152 real 48518005 2; 25-3152 real 48518202 0; 25-3152 syn 20:06 2 models.

**What the data shows.** At thr98 the seven models miss 23 different positives, and only 3 are missed by three
or more models; all three are real 25-3152 emails (C1b, C1d). At the default decision, 11 positives are consensus
misses: 8 from 25-3152 and 3 from 24-409. The d3-27b misses only 1 positive at 0.5: its thr98 (0.5857) sits
above 0.5, so for it the default decision is the more lenient cutoff. With the roster, no positive is a
consensus miss at thr98 and two are at 0.5 (C1e). [corrected in verification: only the 0.5 figure is a like-for-like
comparison. Without the roster, the same 249 pairs have 8 consensus misses at 0.5. With thr98 refitted on those
pairs (2 misses allowed, as for the roster runs), they have 0 at thr98 too (`c_misses_verify.py` V5).]

## C2. Negatives the models all keep

### C2a. The list

'kept' = score at or above the threshold, so the email survives the screen and goes to human review. Listed if kept by >= 5 models at thr98 or at 0.5.

| pair | kind | recipe | kept at thr98 (of 7) | kept at 0.5 (of 7) | date | subject |
|---|---|---|---|---|---|---|
| 24-409 syn 06:04 | hard_negative | forwarded_no_content | 5 | 5 | 2023-02-10 | FW: OSEJ SharePoint Access |
| 24-409 syn 06:06 | hard_negative | forwarded_no_content | 7 | 5 | 2023-03-31 | Automatic reply: IRWM contact list |
| 24-409 syn 06:09 | hard_negative | forwarded_no_content | 5 | 4 | 2023-01-17 | RE: Climate Action Research Grant - Letter of Intent (LOI) D |
| 24-409 syn 05:00 | hard_negative | keyword_in_signature_or_newsletter | 7 | 5 | 2023-04-27 | [External] Office-to-Residential Conversions: What Pencils i |
| 24-409 syn 05:05 | hard_negative | keyword_in_signature_or_newsletter | 6 | 4 | 2023-07-10 | [External] Brukman, Eden left a comment in "OSEJ_Summer Inte |
| 24-409 syn 05:06 | hard_negative | keyword_in_signature_or_newsletter | 5 | 2 | 2023-06-21 | FW: [External] IAP2 USA Southern California Chapter - June N |
| 24-409 syn 05:07 | hard_negative | keyword_in_signature_or_newsletter | 6 | 3 | 2023-04-13 | FW: [External] Creek to Bay Cleanup is April 22 - Volunteer  |
| 24-409 syn 07:00 | hard_negative | keyword_unrelated_sense | 7 | 5 | 2023-06-05 | [External] RE: Regional Fair Housing Report - Affordable Hou |
| 24-409 syn 07:01 | hard_negative | keyword_unrelated_sense | 7 | 7 | 2023-01-30 | RE: OSEJ/Zero Waste Steering Committee Agenda |
| 24-409 syn 07:02 | hard_negative | keyword_unrelated_sense | 5 | 3 | 2023-06-23 | RE: Heat Mapping - Volunteer Flyer |
| 24-409 syn 07:03 | hard_negative | keyword_unrelated_sense | 6 | 5 | 2023-04-24 | Data request smaller jurisdictions - GPS outfall locations |
| 24-409 syn 07:04 | hard_negative | keyword_unrelated_sense | 7 | 6 | 2023-01-12 | RE: Murakawa Logistics - Questions |
| 24-409 syn 07:06 | hard_negative | keyword_unrelated_sense | 5 | 4 | 2023-04-14 | RE: Tree Equity - Community Forum April 26th  |
| 24-409 syn 07:07 | hard_negative | keyword_unrelated_sense | 7 | 7 | 2023-04-18 | [External] RE: Tree Equity - 2nd Community Forum Planning |
| 24-409 syn 07:08 | hard_negative | keyword_unrelated_sense | 5 | 3 | 2023-04-11 | RE: CASQA Abstracts - WQE |
| 24-409 syn 03:01 | hard_negative | same_people_different_subject | 7 | 6 | 2023-06-14 | [External] RE: COC Visitor Lot Closure |
| 24-409 syn 03:02 | hard_negative | same_people_different_subject | 7 | 3 | 2023-06-12 | FW: Announcement: Welcome Bethany Facendini, OSEJ GPM Commun |
| 24-409 syn 03:05 | hard_negative | same_people_different_subject | 5 | 3 | 2023-06-23 | RE: LUEG Summer Picnic Flyer |
| 24-409 syn 03:09 | hard_negative | same_people_different_subject | 7 | 5 | 2023-06-30 | RE: Volunteer Shift |
| 24-409 syn 04:00 | hard_negative | same_subject_wrong_date | 5 | 5 | 2025-04-10 | UCSD Role for Water Assembly  |
| 24-409 syn 04:02 | hard_negative | same_subject_wrong_date | 5 | 2 | 2025-01-14 | RE: Climate Action Research Grant - Letter of Intent (LOI) D |
| 24-409 syn 04:03 | hard_negative | same_subject_wrong_date | 6 | 4 | 2023-10-12 | RE: RWER Task 3.B - Facilities Inventory and Screening Submi |
| 24-409 syn 04:04 | hard_negative | same_subject_wrong_date | 6 | 5 | 2023-10-30 | RE: OSEJ/RDF Steering Committee Agenda |
| 24-409 syn 04:05 | hard_negative | same_subject_wrong_date | 5 | 3 | 2025-04-11 | RE: Regional Water Equity - Water Assembly April 23rd  |
| 24-409 syn 04:06 | hard_negative | same_subject_wrong_date | 7 | 7 | 2022-11-14 | FW: For your review: City of SD PUC interview agenda  |
| 24-409 syn 04:07 | hard_negative | same_subject_wrong_date | 5 | 4 | 2025-03-20 | [External] RE: Regional Water Equity - Team Introduction |
| 24-409 syn 04:08 | hard_negative | same_subject_wrong_date | 7 | 5 | 2022-11-04 | [External] RE: Standing Meeting Acton Items |
| 24-409 syn 04:09 | hard_negative | same_subject_wrong_date | 7 | 6 | 2022-10-14 | RE: Standing Meeting Acton Items |
| 25-3152 syn 18:03 | hard_negative | forwarded_no_content | 6 | 3 | 2025-02-04 | FW: Park Fee Changes Starting February 18, 2025 |
| 25-3152 syn 18:07 | hard_negative | forwarded_no_content | 7 | 7 | 2024-04-03 | FW: PDS2024-MUP-24-003 Major Use Permit |
| 25-3152 syn 18:08 | hard_negative | forwarded_no_content | 6 | 5 | 2025-03-25 | Automatic reply: FW: ACPG Regular Meeting Agenda - March 27, |
| 25-3152 syn 17:00 | hard_negative | keyword_in_signature_or_newsletter | 6 | 4 | 2025-03-14 | Feasibility Study Interview Request - California State Water |
| 25-3152 syn 17:01 | hard_negative | keyword_in_signature_or_newsletter | 7 | 7 | 2024-07-10 | Planning group meeting inquiry |
| 25-3152 syn 17:02 | hard_negative | keyword_in_signature_or_newsletter | 6 | 5 | 2024-09-24 | PDS2024-MUP-24-003 Major Use Permit - Scoping Letter |
| 25-3152 syn 17:05 | hard_negative | keyword_in_signature_or_newsletter | 6 | 7 | 2024-01-10 | Re: Just cause to attend remotely  |
| 25-3152 syn 17:06 | hard_negative | keyword_in_signature_or_newsletter | 5 | 5 | 2025-02-25 | APG Standing Rules for Review |
| 25-3152 syn 19:00 | hard_negative | keyword_unrelated_sense | 6 | 6 | 2024-04-25 | Re: APG April 4, 2024 - DRAFT Meeting Minutes |
| 25-3152 syn 19:01 | hard_negative | keyword_unrelated_sense | 7 | 7 | 2024-07-15 | RE: Objective Design Standards (ODS) Checklist - Alpine |
| 25-3152 syn 19:02 | hard_negative | keyword_unrelated_sense | 6 | 4 | 2024-03-13 | Maggie/ Greg SDGE Loveland Progress! |
| 25-3152 syn 19:03 | hard_negative | keyword_unrelated_sense | 7 | 6 | 2024-03-15 | Fw: Loveland Community  Powerpoint. and Thoughts. |
| 25-3152 syn 19:08 | hard_negative | keyword_unrelated_sense | 7 | 7 | 2024-02-23 | Fwd: ODS DRB Presentation 2-22-24 |
| 25-3152 syn 15:01 | hard_negative | same_people_different_subject | 7 | 7 | 2024-02-11 | Re: [EXTERNAL] Re: TV Interview on Home Insurance! |
| 25-3152 syn 15:02 | hard_negative | same_people_different_subject | 7 | 7 | 2024-10-15 | RE: Rooftop Lease Amendment - CAL02204 |
| 25-3152 syn 15:03 | hard_negative | same_people_different_subject | 5 | 3 | 2025-05-28 | Re: Fishing Friday |
| 25-3152 syn 15:04 | hard_negative | same_people_different_subject | 7 | 4 | 2024-05-08 | RE: [External] Sunday brunch |
| 25-3152 syn 15:05 | hard_negative | same_people_different_subject | 5 | 3 | 2024-03-25 | Service upgrade - Lyon residence - Service Order Confirmatio |
| 25-3152 syn 15:06 | hard_negative | same_people_different_subject | 7 | 7 | 2024-03-28 | Re: Travis Lyon shared "Payment Remittance 03-24.pdf" with y |
| 25-3152 syn 15:08 | hard_negative | same_people_different_subject | 7 | 7 | 2025-05-29 | CANCELLED - Saturday BBQ - May 31, 2025 |
| 25-3152 syn 15:09 | hard_negative | same_people_different_subject | 7 | 5 | 2025-02-25 | Fwd: Cookie Order Forms (Action Required Please) |
| 25-3152 syn 16:00 | hard_negative | same_subject_wrong_date | 5 | 5 | 2023-04-13 | ACPG Loveland Letter's of Support; Sunrise to Sunset & SDGE  |
| 25-3152 syn 16:01 | hard_negative | same_subject_wrong_date | 6 | 5 | 2025-09-25 | Absent tonight |
| 25-3152 syn 16:02 | hard_negative | same_subject_wrong_date | 6 | 5 | 2025-12-05 | Re: PDS2024-MUP-24-003 Major Use Permit - CAL02204 |
| 25-3152 syn 16:04 | hard_negative | same_subject_wrong_date | 5 | 3 | 2023-05-18 | Re: Loveland Letters of Support |
| 25-3152 syn 16:05 | hard_negative | same_subject_wrong_date | 6 | 5 | 2025-09-17 | Alpine Community Planning Group meeting inquiry |
| 25-3152 syn 16:06 | hard_negative | same_subject_wrong_date | 5 | 5 | 2025-09-05 | HOLD: Community Planning Group Chair Meeting |
| 25-3152 syn 16:07 | hard_negative | same_subject_wrong_date | 5 | 4 | 2023-06-21 | Re: Sunrise to Sunset Discussion at Alpine Community Plannin |
| 25-3152 syn 16:08 | hard_negative | same_subject_wrong_date | 6 | 5 | 2025-12-18 | Updates to Alpine CPG - Vacancies and Roster  |

Consensus false positives: 57 at thr98, 36 at 0.5, 57 in the union (0 at 0.5 only). Kept by all 7 at thr98: 23; at 0.5: 12.

### C2b. By kind and recipe

| request | kind/recipe | n | consensus FP at thr98 (k/n, 95% CI) | consensus FP at 0.5 | most models keeping any one (thr98) |
|---|---|---|---|---|---|
| 24-409 | hard_negative/forwarded_no_content | 7 | 3/7 (43%, 16%–75%) | 2/7 (29%, 8%–64%) | 7 |
| 24-409 | hard_negative/keyword_in_signature_or_newsletter | 10 | 4/10 (40%, 17%–69%) | 1/10 (10%, 2%–40%) | 7 |
| 24-409 | hard_negative/keyword_unrelated_sense | 9 | 8/9 (89%, 56%–98%) | 5/9 (56%, 27%–81%) | 7 |
| 24-409 | hard_negative/same_people_different_subject | 6 | 4/6 (67%, 30%–90%) | 2/6 (33%, 10%–70%) | 7 |
| 24-409 | hard_negative/same_subject_wrong_date | 10 | 9/10 (90%, 60%–98%) | 5/10 (50%, 24%–76%) | 7 |
| 24-409 | real_negative | 60 | 0/60 (0%, 0%–6%) | 0/60 (0%, 0%–6%) | 2 |
| 25-3152 | hard_negative/forwarded_no_content | 10 | 3/10 (30%, 11%–60%) | 2/10 (20%, 6%–51%) | 7 |
| 25-3152 | hard_negative/keyword_in_signature_or_newsletter | 10 | 5/10 (50%, 24%–76%) | 4/10 (40%, 17%–69%) | 7 |
| 25-3152 | hard_negative/keyword_unrelated_sense | 10 | 5/10 (50%, 24%–76%) | 4/10 (40%, 17%–69%) | 7 |
| 25-3152 | hard_negative/same_people_different_subject | 9 | 8/9 (89%, 56%–98%) | 5/9 (56%, 27%–81%) | 7 |
| 25-3152 | hard_negative/same_subject_wrong_date | 10 | 8/10 (80%, 49%–94%) | 6/10 (60%, 31%–83%) | 6 |
| 25-3152 | real_negative | 60 | 0/60 (0%, 0%–6%) | 0/60 (0%, 0%–6%) | 3 |
| both | hard_negative/forwarded_no_content | 17 | 6/17 (35%, 17%–59%) | 4/17 (24%, 10%–47%) | 7 |
| both | hard_negative/keyword_in_signature_or_newsletter | 20 | 9/20 (45%, 26%–66%) | 5/20 (25%, 11%–47%) | 7 |
| both | hard_negative/keyword_unrelated_sense | 19 | 13/19 (68%, 46%–85%) | 9/19 (47%, 27%–68%) | 7 |
| both | hard_negative/same_people_different_subject | 15 | 12/15 (80%, 55%–93%) | 7/15 (47%, 25%–70%) | 7 |
| both | hard_negative/same_subject_wrong_date | 20 | 17/20 (85%, 64%–95%) | 11/20 (55%, 34%–74%) | 7 |
| both | real_negative | 120 | 0/120 (0%, 0%–3%) | 0/120 (0%, 0%–3%) | 3 |

All hard negatives: consensus FP at thr98 57/91 (63%, 52%–72%); at 0.5 36/91 (40%, 30%–50%). Every consensus FP is a synthetic hard negative: 57/57.

Real negatives (other productions): kept-by-k distribution at thr98 (k = 0..7): {0: 77, 1: 30, 2: 10, 3: 3}; at 0.5: {0: 111, 1: 8, 2: 1}.

### C2c. With the roster

| pair | kind/recipe | kept at thr98 +roster | kept at 0.5 +roster | kept at thr98 (no roster) | kept at 0.5 (no roster) |
|---|---|---|---|---|---|
| 25-3152 syn 15:01 | hard_negative/same_people_different_subject | 6 | 7 | 7 | 7 |
| 25-3152 syn 15:02 | hard_negative/same_people_different_subject | 7 | 7 | 7 | 7 |
| 25-3152 syn 15:03 | hard_negative/same_people_different_subject | 5 | 6 | 5 | 3 |
| 25-3152 syn 15:04 | hard_negative/same_people_different_subject | 5 | 5 | 7 | 4 |
| 25-3152 syn 15:05 | hard_negative/same_people_different_subject | 6 | 6 | 5 | 3 |
| 25-3152 syn 15:06 | hard_negative/same_people_different_subject | 7 | 7 | 7 | 7 |
| 25-3152 syn 15:08 | hard_negative/same_people_different_subject | 5 | 7 | 7 | 7 |
| 25-3152 syn 15:09 | hard_negative/same_people_different_subject | 5 | 5 | 7 | 5 |
| 25-3152 syn 16:05 | hard_negative/same_subject_wrong_date | 4 | 5 | 6 | 5 |
| 25-3152 syn 16:08 | hard_negative/same_subject_wrong_date | 4 | 5 | 6 | 5 |
| 25-3152 syn 19:08 | hard_negative/keyword_unrelated_sense | 3 | 5 | 7 | 7 |

Of the 29 main-set 25-3152 consensus false positives, 8 remain consensus at thr98 with the roster and 11 at 0.5.

### C2d. Named correspondents

24-409 item 4 names people and firms (Elise Ruiz, Murakawa, Geosyntec staff, Gaines, Benham, Snyder, Aghassi, Brukman, Baxamusa) but also requires a reference to a listed term. 25-3152 names a group (any ACPG member). Prompt 2 tells every model that an email to or from a named person or group is responsive whatever its subject. Headers = From/To/Cc/Bcc/Delivered-To. 24-409 named = the people and firms above (not the catch-all 'anyone at the County'); 25-3152 named = a roster address or name.

| request | kind | named correspondent in headers | n | consensus FP at thr98 | consensus FP at 0.5 | mean models keeping at 0.5 (of 7) |
|---|---|---|---|---|---|---|
| 24-409 | hard_negative | yes | 38 | 28/38 (74%, 58%–85%) | 15/38 (39%, 26%–55%) | 3.9 |
| 24-409 | hard_negative | no | 4 | 0/4 (0%, 0%–49%) | 0/4 (0%, 0%–49%) | 0.2 |
| 24-409 | real_negative | yes | 1 | 0/1 (0%, 0%–79%) | 0/1 (0%, 0%–79%) | 1.0 |
| 24-409 | real_negative | no | 59 | 0/59 (0%, 0%–6%) | 0/59 (0%, 0%–6%) | 0.0 |
| 25-3152 | hard_negative | yes | 19 | 16/19 (84%, 62%–94%) | 11/19 (58%, 36%–77%) | 4.6 |
| 25-3152 | hard_negative | no | 30 | 13/30 (43%, 27%–61%) | 10/30 (33%, 19%–51%) | 3.1 |
| 25-3152 | real_negative | no | 60 | 0/60 (0%, 0%–6%) | 0/60 (0%, 0%–6%) | 0.1 |

The 24-409 comparison is confounded: the generator kept the same people on 38 of the 42 24-409 hard negatives,
and the real negatives come from unrelated productions. Within 25-3152 hard negatives, where the generator
sometimes removed the member, the contrast is cleaner (16/19 against 13/30 at thr98).

### C2e. Wrong-date negatives

The 24-409 request text carries both the 5/17/24 refinement (1/1/2023-7/31/2023) and the original request (1/1/2022 to the 4/16/2024 letter). 'In original window' marks dates inside the original range; the original request's subjects (Hinds, the UCSD USP department, Fletcher) still differ from the RWER/RDF topics of these emails.

| pair | date | side | in original 24-409 window | kept at thr98 | kept at 0.5 | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 24-409 syn 04:09 | 2022-10-14 | before | yes | 7 | 6 | 0.68 | 0.56 | 0.30 | 0.63 | 0.71 | 0.86 | 0.88 |
| 24-409 syn 04:08 | 2022-11-04 | before | yes | 7 | 5 | 0.68 | 0.74 | 0.43 | 0.71 | 0.35 | 0.66 | 0.78 |
| 24-409 syn 04:06 | 2022-11-14 | before | yes | 7 | 7 | 0.82 | 0.79 | 0.56 | 0.51 | 0.53 | 0.81 | 0.81 |
| 24-409 syn 04:03 | 2023-10-12 | after | yes | 6 | 4 | 0.68 | 0.80 | 0.13 | 0.66 | 0.47 | 0.41 | 0.83 |
| 24-409 syn 04:04 | 2023-10-30 | after | yes | 6 | 5 | 0.62 | 0.90 | 0.24 | 0.73 | 0.66 | 0.17 | 0.87 |
| 24-409 syn 04:01 | 2024-09-24 | after | no | 4 | 3 | 0.55 | 0.23 | 0.01 | 0.50 | 0.35 | 0.44 | 0.78 |
| 24-409 syn 04:02 | 2025-01-14 | after | no | 5 | 2 | 0.55 | 0.45 | 0.08 | 0.45 | 0.20 | 0.18 | 0.70 |
| 24-409 syn 04:07 | 2025-03-20 | after | no | 5 | 4 | 0.44 | 0.52 | 0.04 | 0.74 | 0.54 | 0.19 | 0.73 |
| 24-409 syn 04:00 | 2025-04-10 | after | no | 5 | 5 | 0.69 | 0.80 | 0.02 | 0.60 | 0.75 | 0.31 | 0.79 |
| 24-409 syn 04:05 | 2025-04-11 | after | no | 5 | 3 | 0.51 | 0.54 | 0.00 | 0.45 | 0.41 | 0.16 | 0.69 |
| 25-3152 syn 16:03 | 2023-04-03 | before | — | 4 | 4 | 0.56 | 0.69 | 0.00 | 0.61 | 0.32 | 0.05 | 0.50 |
| 25-3152 syn 16:00 | 2023-04-13 | before | — | 5 | 5 | 0.61 | 0.72 | 0.00 | 0.86 | 0.68 | 0.17 | 0.69 |
| 25-3152 syn 16:04 | 2023-05-18 | before | — | 5 | 3 | 0.75 | 0.60 | 0.01 | 0.87 | 0.47 | 0.09 | 0.35 |
| 25-3152 syn 16:07 | 2023-06-21 | before | — | 5 | 4 | 0.60 | 0.59 | 0.05 | 0.74 | 0.46 | 0.16 | 0.56 |
| 25-3152 syn 16:09 | 2023-06-22 | before | — | 2 | 1 | 0.31 | 0.12 | 0.00 | 0.53 | 0.27 | 0.04 | 0.26 |
| 25-3152 syn 16:06 | 2025-09-05 | after | — | 5 | 5 | 0.84 | 0.70 | 0.02 | 0.51 | 0.59 | 0.22 | 0.61 |
| 25-3152 syn 16:05 | 2025-09-17 | after | — | 6 | 5 | 0.76 | 0.66 | 0.11 | 0.64 | 0.60 | 0.18 | 0.79 |
| 25-3152 syn 16:01 | 2025-09-25 | after | — | 6 | 5 | 0.81 | 0.66 | 0.55 | 0.48 | 0.63 | 0.21 | 0.77 |
| 25-3152 syn 16:02 | 2025-12-05 | after | — | 6 | 5 | 0.86 | 0.89 | 0.55 | 0.64 | 0.48 | 0.42 | 0.68 |
| 25-3152 syn 16:08 | 2025-12-18 | after | — | 6 | 5 | 0.84 | 0.96 | 0.07 | 0.53 | 0.77 | 0.42 | 0.84 |

- 24-409, in original window = yes: 5 emails, mean models keeping at 0.5 5.4 of 7.
- 24-409, in original window = no: 5 emails, mean models keeping at 0.5 3.4 of 7.
- 25-3152: 10 emails, mean models keeping at 0.5 4.2 of 7.

| mean score | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev |
|---|---|---|---|---|---|---|---|
| 24-409, inside the original window (n=5) | 0.70 | 0.75 | 0.33 | 0.65 | 0.54 | 0.58 | 0.83 |
| 24-409, outside both windows (n=5) | 0.55 | 0.51 | 0.03 | 0.55 | 0.45 | 0.26 | 0.74 |
| 25-3152 (n=10) | 0.69 | 0.66 | 0.14 | 0.64 | 0.53 | 0.20 | 0.60 |

**What the data shows.** Every consensus false positive is a synthetic hard negative: 57 of the 91 hard negatives
are kept by at least 5 models at thr98, and no real negative is kept by more than 3 (C2b). By recipe, wrong-date
(17/20), same-people (12/15) and unrelated-sense (13/19) emails are kept most often. With the roster, the 25-3152
consensus false positives fall from 29 to 8 at thr98, and the 8 that remain are the "purely personal" emails
(C2c). [corrected in verification: the 29 uses the main runs' thr98 fitted on all 495 pairs. Refitted on the same
249 pairs as the roster runs, the like-for-like drop is 26 to 8, and at 0.5 it is 21 to 11 (`c_misses_verify.py`
V5).] On wrong dates, the 27b lp scores the five 24-409 emails that fall inside the *original* request's
2022-2024 range higher than the five outside both ranges (mean 0.33 against 0.03; d3-27b 0.58 against 0.26;
C2e).

## C3. Reading every consensus miss and consensus false positive

### C3a. One row per email

#### Consensus misses (label: responsive)

Models = how many of the 7 miss it (misses) or keep it (false positives) at thr98 / at 0.5, main set; '+roster' = the same for the roster runs (25-3152 only). Human call: R/N = real row confirmed responsive/not; K = synthetic label kept; F = flipped; blank = no human check. Date, in window (the refined 24-409 window 1/1-7/31/2023 or the 25-3152 window 1/1/2024-5/31/2025), recipients (distinct To/Cc/Bcc addresses) and first hook (body offset of the first listed 24-409 term, or of the first ACPG mention for 25-3152; the models see offsets below 8,000) are computed. The text columns are the analyst's reading.

| pair | kind/recipe | models (thr98 / 0.5) | +roster | human call | date | in window | recipients | first hook at char | what it is | why this label | label judgment | model error type | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 24-409 syn 02:01 | close_call | 1 / 3 | — | K | 2023-01-17 | yes | 3 | 10,080 | Climate Action Research Grant thread with UCSD's Lawrence Frank; the 'UC San Diego - Dept of Urban Studies and Planning' signature lies past the body cap. | Item 2 via the signature; the owner kept it (findings §9) to count a miss the system would really make. | right | hook only past the 8,000-char body cap | No model sees the hook; the visible text has UCSD only in addresses and a Zoom URL. |
| 24-409 real 33733472 | real | 2 / 6 | — |  | 2023-06-12 | yes | 1 | 993 | OSEJ staff thread on the Governor's energy plan; one message gives a section-by-section 'alignment with RDF' summary. | County production; item 3 (related to the RDF); in window. | right | topic carried by one acronym or one line | The subject never names a request term; RDF appears only as an acronym in the body. |
| 24-409 syn 00:03 | close_call | 2 / 3 | — |  | 2023-06-23 | yes | 2 | 648 | Rain-barrel flyer thread; one added line says Elise may have a contact list 'from the RWER outreach'. | Item 4: from Gaines (named) and refers to the RWER; in window. Marginal by design. | right | topic carried by one acronym or one line |  |
| 25-3152 real 48518202 | real | 1 / 4 | 0 / 0 | R | 2025-03-31 | yes | 1 | — | Automated password-reset email from the Clerk of the Board's eFile (Form 700) system to Lyon. | County production; item 3 read literally (County to a member); owner confirmed R. | right | automated notice to a member | Trivial content; relates to his filing duty as a member. |
| 25-3152 real 48517463 | real | 3 / 5 | 2 / 2 | R | 2024-10-28 | yes | 25 | — | Lakeside CPG chair's reply-all 'Excellent report Robin!' on an APG report about SANDAG; ACPG chair Lyon is one of many Cc's. | County production; items 3/4 read literally (a member received it); owner confirmed R. | right | member is one of many recipients | Narrower reading possible: Lyon is a passive recipient and nothing concerns ACPG business. |
| 25-3152 real 48517567 | real | 3 / 4 | 0 / 1 | R | 2025-04-01 | yes | 27 | — | Lakeside chair's 'Great news!!' reply-all on a forwarded SANDAG legislative update; Lyon one of many Cc's. | County production; items 3/4; owner confirmed R. | right | member is one of many recipients | Same narrower-reading question. |
| 25-3152 real 48517588 | real | 2 / 3 | 1 / 3 |  | 2024-09-23 | yes | 19 | — | Lakeside chair asks 'Is this meeting still today?' on a County hold for the CPG chairs' meeting; Lyon first in a long Cc line. | County production; item 3 (County staff on the thread). Not human-adjudicated (Opus R, high). | right | member is one of many recipients |  |
| 25-3152 real 48517769 | real | 3 / 3 | 0 / 2 | R | 2025-01-29 | yes | 31 | — | Lakeside chair's 'I plan to attend' on a County DPW Traffic Advisory Committee agenda thread; Lyon one of many Cc's. | County production; items 3/4; owner confirmed R. | right | member is one of many recipients |  |
| 25-3152 real 48517957 | real | 1 / 3 | 1 / 3 |  | 2024-11-13 | yes | 25 | — | Fallbrook PG chair forwards her BESS meeting comments to all CPG chairs; 'Travis Lyon (Alpine)' one of many Cc's. | County production; items 3/4. Not human-adjudicated (Opus R, high). | right | member is one of many recipients |  |
| 25-3152 real 48518005 | real | 2 / 4 | 2 / 2 |  | 2025-03-15 | yes | 28 | — | Fallbrook PG chair sends her cannabis DEIR comment draft to the countywide planning-group chairs, Lyon among them. | County production; items 3/4. Not human-adjudicated (Opus R, high). | right | member is one of many recipients |  |
| 25-3152 syn 20:06 | privileged | 1 / 3 | 0 / 2 |  | 2024-09-23 | yes | 19 | — | Synthetic copy of 48517588 with County Counsel's privileged Form 700 advice quoted. | Item 3; privilege does not affect responsiveness. | right | member is one of many recipients |  |

#### Consensus false positives (label: not responsive)

Models = how many of the 7 miss it (misses) or keep it (false positives) at thr98 / at 0.5, main set; '+roster' = the same for the roster runs (25-3152 only). Human call: R/N = real row confirmed responsive/not; K = synthetic label kept; F = flipped; blank = no human check. Date, in window (the refined 24-409 window 1/1-7/31/2023 or the 25-3152 window 1/1/2024-5/31/2025), recipients (distinct To/Cc/Bcc addresses) and first hook (body offset of the first listed 24-409 term, or of the first ACPG mention for 25-3152; the models see offsets below 8,000) are computed. The text columns are the analyst's reading.

| pair | kind/recipe | models (thr98 / 0.5) | +roster | human call | date | in window | recipients | first hook at char | what it is | why this label | label judgment | model error type | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 24-409 syn 04:00 | hn/same_subject_wrong_date | 5 / 5 | — |  | 2025-04-10 | no | 4 | 105 | Ruiz tells Geosyntec that its staff will present for UCSD at the Water Assembly. | On topic but after both the refined (1/1-7/31/2023) and original (2022 to 4/16/2024) windows. | right | date outside the request window |  |
| 24-409 syn 04:02 | hn/same_subject_wrong_date | 5 / 2 | — |  | 2025-01-14 | no | 1 | 3,043 | Lynch and Baxamusa on the UCSD climate grant and RDF. | Outside both windows. | right | date outside the request window |  |
| 24-409 syn 04:03 | hn/same_subject_wrong_date | 6 / 4 | — |  | 2023-10-12 | no | 4 | 537 | Geosyntec RWER Task 3.B deliverable to Gaines. | Outside the refined window. Inside the original window, but the original request does not cover RWER. | right | date outside the request window |  |
| 24-409 syn 04:04 | hn/same_subject_wrong_date | 6 / 5 | — |  | 2023-10-30 | no | 3 | 278 | OSEJ/RDF steering-committee follow-ups (Murakawa, RWER). | Outside the refined window; the original request's subjects (Hinds, UCSD USP, Fletcher) are absent. | right | date outside the request window |  |
| 24-409 syn 04:05 | hn/same_subject_wrong_date | 5 / 3 | — |  | 2025-04-11 | no | 1 | 906 | Board-office staff help promote the Water Equity assembly. | Outside both windows. | right | date outside the request window |  |
| 24-409 syn 04:06 | hn/same_subject_wrong_date | 7 / 7 | — |  | 2022-11-14 | no | 2 | 976 | Ruiz forwards Geosyntec's RWER interview agenda to Gaines. | Outside the refined window; the original request does not cover RWER. | right | date outside the request window | The 27b jsonR answer applied the original request's 2022 window. |
| 24-409 syn 04:07 | hn/same_subject_wrong_date | 5 / 4 | — |  | 2025-03-20 | no | 6 | 246 | RWER interview scheduling between Geosyntec and County agriculture staff. | Outside both windows. | right | date outside the request window |  |
| 24-409 syn 04:08 | hn/same_subject_wrong_date | 7 / 5 | — |  | 2022-11-04 | no | 2 | 377 | RWER standing-meeting action items between Geosyntec and Ruiz. | Outside the refined window; mentions UCSD studies but not the USP department. | right | date outside the request window |  |
| 24-409 syn 04:09 | hn/same_subject_wrong_date | 7 / 6 | — |  | 2022-10-14 | no | 2 | 72 | Earlier message of the same RWER thread. | Same as 04:08. | right | date outside the request window |  |
| 24-409 syn 06:04 | hn/forwarded_no_content | 5 / 5 | — |  | 2023-02-10 | yes | 4 | — | Ruiz forwards an IT 'SharePoint access' notice to Gaines and Benham with 'FYI'. | Named people only; no listed term. | right | forward or auto-reply with no content |  |
| 24-409 syn 06:06 | hn/forwarded_no_content | 7 / 5 | — |  | 2023-03-31 | yes | 1 | — | Ruiz's out-of-office auto-reply to a County colleague ('IRWM contact list'). | No listed term and no Geosyntec address (unlike flipped 06:01, sent to Geosyntec). | right | forward or auto-reply with no content |  |
| 24-409 syn 06:09 | hn/forwarded_no_content | 5 / 4 | — |  | 2023-01-17 | yes | 1 | — | Lynch tells Baxamusa she will call him; subject 'Climate Action Research Grant'. | Named people only; no listed term. | right | forward or auto-reply with no content |  |
| 24-409 syn 03:02 | hn/same_people_different_subject | 7 / 3 | — |  | 2023-06-12 | yes | 5 | — | OSEJ team plans a welcome lunch for a new hire; quotes Brukman's all-staff announcement (Aghassi, Baxamusa, Snyder, Ruiz copied). | County staff only; no listed term. | right | named correspondent, no listed term (24-409 item 4 needs both) |  |
| 24-409 syn 03:05 | hn/same_people_different_subject | 5 / 3 | — |  | 2023-06-23 | yes | 2 | — | Gaines and a colleague promote the LUEG summer picnic flyer (from Elise Ruiz). | County staff only; no listed term. | right | named correspondent, no listed term (24-409 item 4 needs both) |  |
| 24-409 syn 05:05 | hn/keyword_in_signature_or_newsletter | 6 / 4 | — |  | 2023-07-10 | yes | 1 | — | SharePoint notice that Brukman commented on an intern onboarding checklist, sent to Ruiz. | Named people only; no listed term. | right | named correspondent, no listed term (24-409 item 4 needs both) |  |
| 24-409 syn 03:01 | hn/same_people_different_subject | 7 / 6 | — | K | 2023-06-14 | yes | 1 | — | Megan Otto (Geosyntec) thanks Gaines for a heads-up about a County parking-lot closure. | No listed term in the content; Geosyntec only in the addresses. Owner kept it (K). | likely wrong | named correspondent; Geosyntec only in the addresses | The owner flipped 03:04, 03:07, 06:01 and 06:03 to responsive on the same pattern (C3c); 03:07 is likewise logistics for in-person project meetings. |
| 24-409 syn 03:09 | hn/same_people_different_subject | 7 / 5 | — | K | 2023-06-30 | yes | 5 | — | Megan Otto (Geosyntec) organizes a team volunteer shift at a food bank; Zinn (Geosyntec), Gaines and Ruiz reply. | No listed term in the content; Geosyntec only in the addresses. Owner kept it (K). | arguable | named correspondent; Geosyntec only in the addresses | Same address pattern as the four flips (C3c), but the content is a team social outing, nearer the 'purely personal' line drawn for 25-3152. |
| 24-409 syn 07:00 | hn/keyword_unrelated_sense | 7 / 5 | — |  | 2023-06-05 | yes | 3 | — | LeSar consultant schedules a Regional Fair Housing interview; Ruiz copied. | 'Regional ... Report' and 'equity' are not the RWER. | right | term in an unrelated sense, or a near-name |  |
| 24-409 syn 07:01 | hn/keyword_unrelated_sense | 7 / 7 | — |  | 2023-01-30 | yes | 3 | 217 | OSEJ Zero Waste steering agenda: 'RDF proposal' means refuse-derived fuel; Appel, Baxamusa, Ruiz. | Not the Regional Decarbonization Framework. Not human-adjudicated; the verifier asked the adjudicator to confirm. | arguable | term in an unrelated sense, or a near-name | The owner dropped 07:09 for this same RDF ambiguity (findings §9). |
| 24-409 syn 07:02 | hn/keyword_unrelated_sense | 5 / 3 | — |  | 2023-06-23 | yes | 2 | 5,103 | Heat-mapping volunteer flyer; 'GPS-linked temperature sensors'; Gaines, Ruiz. | The request defines GPS as global policy & strategy. | right | term in an unrelated sense, or a near-name |  |
| 24-409 syn 07:03 | hn/keyword_unrelated_sense | 6 / 5 | — |  | 2023-04-24 | yes | 2 | 221 | Meeting invite on collecting GPS coordinates for outfalls; from Gaines. | Same: GPS in its navigation sense. | right | term in an unrelated sense, or a near-name |  |
| 24-409 syn 07:04 | hn/keyword_unrelated_sense | 7 / 6 | — |  | 2023-01-12 | yes | 3 | 82 | Murakawa event logistics naming 'Dr. Steven Lerner' as a speaker; Baxamusa, Ruiz. | A different Lerner from Dr. Amy Lerner. | right | term in an unrelated sense, or a near-name | A string search for 'Lerner' would hit it. |
| 24-409 syn 07:06 | hn/keyword_unrelated_sense | 5 / 4 | — |  | 2023-04-14 | yes | 1 | — | Board-office staff help promote a Tree Equity forum (to Ruiz). | 'Equity' alone is not the RWER. | right | term in an unrelated sense, or a near-name |  |
| 24-409 syn 07:07 | hn/keyword_unrelated_sense | 7 / 7 | — |  | 2023-04-18 | yes | 6 | 535 | Murakawa's poll question for a Tree Equity forum; Ruiz, Gaines. | No listed term; Murakawa as a correspondent is not enough. | right | term in an unrelated sense, or a near-name |  |
| 24-409 syn 07:08 | hn/keyword_unrelated_sense | 5 / 3 | — |  | 2023-04-11 | yes | 2 | — | County staff on a CASQA abstract about Regional Water Quality Equivalency (WQE). | A different program from the RWER. | right | term in an unrelated sense, or a near-name |  |
| 24-409 syn 05:00 | hn/keyword_in_signature_or_newsletter | 7 / 5 | — |  | 2023-04-27 | yes | 1 | 2,412 | Zoom webinar confirmation to Ruiz from ULI; 'UC San Diego' only in an academic-partner footer. | Items 2/4 count UCSD only together with Hinds, Lerner, USP or GPS. | right | term only in a footer, signature or link list |  |
| 24-409 syn 05:06 | hn/keyword_in_signature_or_newsletter | 5 / 2 | — |  | 2023-06-21 | yes | 1 | 2,123 | IAP2 newsletter forwarded to Ruiz; 'UC San Diego Extended Studies' in the footer. | UCSD alone is not enough. | right | term only in a footer, signature or link list |  |
| 24-409 syn 05:07 | hn/keyword_in_signature_or_newsletter | 6 / 3 | — |  | 2023-04-13 | yes | 3 | 1,641 | Gaines forwards a Creek to Bay cleanup blast; UC San Diego in the sponsor footer. | UCSD alone is not enough. | right | term only in a footer, signature or link list |  |
| 25-3152 syn 16:00 | hn/same_subject_wrong_date | 5 / 5 | 3 / 3 |  | 2023-04-13 | no | 10 | 17 | Member of the public asks Lyon for ACPG Loveland support letters. | Before 1/1/2024. | right | date outside the request window |  |
| 25-3152 syn 16:01 | hn/same_subject_wrong_date | 6 / 5 | 2 / 3 |  | 2025-09-25 | no | 1 | 311 | A member sends Lyon her apology for missing a meeting. | After 5/31/2025. | right | date outside the request window |  |
| 25-3152 syn 16:02 | hn/same_subject_wrong_date | 6 / 5 | 4 / 4 |  | 2025-12-05 | no | 1 | 1,005 | Member replies to Lyon's forward of an MUP scoping letter. | After 5/31/2025. | right | date outside the request window |  |
| 25-3152 syn 16:04 | hn/same_subject_wrong_date | 5 / 3 | 3 / 3 |  | 2023-05-18 | no | 11 | 136 | Loveland support-letter follow-up to Lyon. | Before 1/1/2024. | right | date outside the request window |  |
| 25-3152 syn 16:05 | hn/same_subject_wrong_date | 6 / 5 | 4 / 5 |  | 2025-09-17 | no | 1 | 276 | Nonprofit intern asks Lyon to present at an ACPG meeting. | After 5/31/2025. | right | date outside the request window |  |
| 25-3152 syn 16:06 | hn/same_subject_wrong_date | 5 / 5 | 3 / 4 |  | 2025-09-05 | no | 18 | — | County hold for a CPG chairs' meeting, Lyon a recipient. | After 5/31/2025. | right | date outside the request window |  |
| 25-3152 syn 16:07 | hn/same_subject_wrong_date | 5 / 4 | 3 / 4 |  | 2023-06-21 | no | 25 | 854 | Loveland 'Sunrise to Sunset' thread copying three members. | Before 1/1/2024. | right | date outside the request window |  |
| 25-3152 syn 16:08 | hn/same_subject_wrong_date | 6 / 5 | 4 / 5 |  | 2025-12-18 | no | 1 | 49 | County PDS to Lyon on ACPG vacancies and roster. | After 5/31/2025. | right | date outside the request window |  |
| 25-3152 syn 18:03 | hn/forwarded_no_content | 6 / 3 | 1 / 2 |  | 2025-02-04 | yes | 1 | — | County-to-County FYI forward of a Parks fee notice sent to the Pine Valley group. | No member is a party. | right | forward or auto-reply with no content |  |
| 25-3152 syn 18:08 | hn/forwarded_no_content | 6 / 5 | 3 / 3 |  | 2025-03-25 | yes | 1 | — | County planner's out-of-office reply; subject quotes 'ACPG Regular Meeting Agenda'. | Not an agenda; no member is a party. | right | forward or auto-reply with no content |  |
| 25-3152 syn 18:07 | hn/forwarded_no_content | 7 / 7 | 1 / 2 |  | 2024-04-03 | yes | 1 | — | Curt Dean (Alpine Design Review Board) forwards a PDS MUP notice to md7. | Dean is not on the ACPG roster. | right | non-member taken for a member | The 27b jsonR answer called Dean 'a known ACPG member'. |
| 25-3152 syn 19:02 | hn/keyword_unrelated_sense | 6 / 4 | 1 / 2 |  | 2024-03-13 | yes | 4 | — | Member of the public to County staff, copying Patrick Brown (Julian), not member Kim Brown. | No member is a party. | right | non-member taken for a member | The 27b jsonR answer called the sender 'a known ACPG member'. |
| 25-3152 syn 15:01 | hn/same_people_different_subject | 7 / 7 | 6 / 7 | K | 2024-02-11 | yes | 1 | 1,833 | Lyon schedules a TV interview about his family's home-insurance non-renewal; signs as ACPG Chair. | Owner: purely personal, not a public record (San Jose), applied 2026-10-31. | arguable | purely-personal exception not applied | He corresponds with the press under his official title; 'purely personal' is debatable. |
| 25-3152 syn 15:02 | hn/same_people_different_subject | 7 / 7 | 7 / 7 | K | 2024-10-15 | yes | 4 | 2,931 | md7 writes to Lyon about a rooftop cell-site lease on a building he does not own; he says 'wrong Travis'. | Owner: purely personal (applied by extension). | arguable | purely-personal exception not applied | Not personal either: misdirected business mail from md7, the applicant on a real MUP before the group (verifier). |
| 25-3152 syn 15:03 | hn/same_people_different_subject | 5 / 3 | 5 / 6 | K | 2025-05-28 | yes | 1 | 306 | Two members arrange a fishing trip. | Owner: purely personal (San Jose). | right | purely-personal exception not applied |  |
| 25-3152 syn 15:04 | hn/same_people_different_subject | 7 / 4 | 5 / 5 | K | 2024-05-08 | yes | 4 | 736 | Lyon's Mother's Day brunch reservation sent to the wrong Martha (a County planner). | Owner: purely personal. | right | purely-personal exception not applied | The verifier called the synthetic implausible (applicant's consultants copied). |
| 25-3152 syn 15:05 | hn/same_people_different_subject | 5 / 3 | 6 / 6 | K | 2024-03-25 | yes | 4 | — | SDG&E service-order confirmation for Lyon's home panel upgrade. | Owner: purely personal (decided directly). | right | purely-personal exception not applied |  |
| 25-3152 syn 15:06 | hn/same_people_different_subject | 7 / 7 | 7 / 7 | K | 2024-03-28 | yes | 3 | 2,036 | Lyon warns a County planner and an applicant's representative that his ACPG account was hacked; signs as Chair. | Owner: purely personal (applied by extension). | arguable | purely-personal exception not applied | It concerns the account he uses for group business, sent to a County planner and an applicant's rep. |
| 25-3152 syn 15:08 | hn/same_people_different_subject | 7 / 7 | 5 / 7 | K | 2025-05-29 | yes | 1 | 191 | Lyon cancels a backyard BBQ at his house (bcc list). | Owner: purely personal. | right | purely-personal exception not applied |  |
| 25-3152 syn 15:09 | hn/same_people_different_subject | 7 / 5 | 5 / 5 | K | 2025-02-25 | yes | 13 | 151 | Lyon sends his daughter's Girl Scout cookie order form to all members. | Owner: purely personal (decided directly). | right | purely-personal exception not applied |  |
| 25-3152 syn 19:00 | hn/keyword_unrelated_sense | 6 / 6 | 2 / 4 |  | 2024-04-25 | yes | 1 | — | APG (Association of Planning Groups) draft minutes between two non-members. | APG is not the ACPG. | right | term in an unrelated sense, or a near-name |  |
| 25-3152 syn 19:01 | hn/keyword_unrelated_sense | 7 / 7 | 3 / 4 |  | 2024-07-15 | yes | 1 | — | County planner sends the Alpine ODS checklist to Curt Dean of the Alpine Design Review Board. | The DRB is a separate body. | right | term in an unrelated sense, or a near-name |  |
| 25-3152 syn 19:03 | hn/keyword_unrelated_sense | 7 / 6 | 2 / 2 |  | 2024-03-15 | yes | 1 | — | Member of the public writes to the APG chair about speaking at APG. | APG is not the ACPG; no member is a party. | right | term in an unrelated sense, or a near-name |  |
| 25-3152 syn 19:08 | hn/keyword_unrelated_sense | 7 / 7 | 3 / 5 |  | 2024-02-23 | yes | 1 | — | Curt Dean self-forwards the County's Design Review Board presentation. | The DRB is a separate body. | right | term in an unrelated sense, or a near-name |  |
| 25-3152 syn 17:00 | hn/keyword_in_signature_or_newsletter | 6 / 4 | 2 / 2 |  | 2025-03-14 | yes | 2 | 2,725 | State Water Board consultant writes to the Descanso and Pine Valley groups; ACPG only in a link list. | No ACPG member is a party; not an agenda or minutes. | right | term only in a footer, signature or link list |  |
| 25-3152 syn 17:01 | hn/keyword_in_signature_or_newsletter | 7 / 7 | 2 / 3 |  | 2024-07-10 | yes | 3 | 822 | Nonprofit intern writes to three other planning groups; ACPG named in her signature footer. | No member is a party. | right | term only in a footer, signature or link list | The 27b jsonR answer took svcpg4@gmail.com (Spring Valley) for the ACPG address. |
| 25-3152 syn 17:02 | hn/keyword_in_signature_or_newsletter | 6 / 5 | 3 / 3 |  | 2024-09-24 | yes | 4 | 470 | PDS scoping-letter notice to the applicant (md7); ACPG only in the Board Policy I-1 boilerplate. | No member is a party. | right | term only in a footer, signature or link list |  |
| 25-3152 syn 17:05 | hn/keyword_in_signature_or_newsletter | 6 / 7 | 3 / 4 |  | 2024-01-10 | yes | 29 | 685 | Campo PG list reply on remote attendance; ACPG in a resources link list (Lyon removed from the Cc). | No member is a party. | right | term only in a footer, signature or link list |  |
| 25-3152 syn 17:06 | hn/keyword_in_signature_or_newsletter | 5 / 5 | 1 / 2 |  | 2025-02-25 | yes | 9 | 247 | APG sends draft standing rules to other groups; 'Alpine CPG Standing Rules' in a reference list. | No member is a party. | right | term only in a footer, signature or link list |  |

### C3b. Tallies

| group | category | count |
|---|---|---|
| consensus misses | label right | 11/11 |
| consensus misses | automated notice to a member | 1/11 (24-409 0, 25-3152 1) |
| consensus misses | hook only past the 8,000-char body cap | 1/11 (24-409 1, 25-3152 0) |
| consensus misses | member is one of many recipients | 7/11 (24-409 0, 25-3152 7) |
| consensus misses | topic carried by one acronym or one line | 2/11 (24-409 2, 25-3152 0) |
| consensus false positives | label right | 51/57 |
| consensus false positives | label arguable | 5/57 |
| consensus false positives | label likely wrong | 1/57 |
| consensus false positives | date outside the request window | 17/57 (24-409 9, 25-3152 8) |
| consensus false positives | forward or auto-reply with no content | 5/57 (24-409 3, 25-3152 2) |
| consensus false positives | named correspondent, no listed term (24-409 item 4 needs both) | 3/57 (24-409 3, 25-3152 0) |
| consensus false positives | named correspondent; Geosyntec only in the addresses | 2/57 (24-409 2, 25-3152 0) |
| consensus false positives | non-member taken for a member | 2/57 (24-409 0, 25-3152 2) |
| consensus false positives | purely-personal exception not applied | 8/57 (24-409 0, 25-3152 8) |
| consensus false positives | term in an unrelated sense, or a near-name | 12/57 (24-409 8, 25-3152 4) |
| consensus false positives | term only in a footer, signature or link list | 8/57 (24-409 3, 25-3152 5) |

### C3c. A consistency check: Geosyntec only in the addresses

Mechanical filter over all 246 24-409 pairs: 'geosyntec' appears in an e-mail address (headers or quoted headers in the body), and once addresses and URLs are removed, no listed 24-409 term (Hinds, Lerner, USP, GPS, Urban Studies, Global Policy, UCSD, RWER, Water Equity, RDF, Decarbonization Framework, Geosyntec, Murakawa, Fletcher) appears in the subject or the first 8,000 body characters.

| pair | label | kind | human call | date | subject | models saying yes at 0.5 |
|---|---|---|---|---|---|---|
| 24-409 syn 03:01 | 0 | hard_negative | K | 2023-06-14 | [External] RE: COC Visitor Lot Closure | 6/7 |
| 24-409 syn 03:04 | 1 | hard_negative_flipped | F | 2023-04-18 | FW: Out of Office 4/24 - 5/5 | 6/7 |
| 24-409 syn 03:07 | 1 | hard_negative_flipped | F | 2023-04-17 | FW: For your review: lunch options for Wednesday  | 5/7 |
| 24-409 syn 03:09 | 0 | hard_negative | K | 2023-06-30 | RE: Volunteer Shift | 5/7 |
| 24-409 syn 06:01 | 1 | hard_negative_flipped | F | 2023-06-30 | Automatic reply: [External] June Accrual Estimate | 6/7 |
| 24-409 syn 06:03 | 1 | hard_negative_flipped | F | 2023-01-23 | [External] Accepted: Scope Review Discussion | 7/7 |

The six synthetic 24-409 emails above share one pattern: a Geosyntec address on the thread (in the headers or a
quoted header), a named County person on it too, a date in the window, and no listed term in the text. The owner flipped four of them to
responsive (03:04, 03:07, 06:01, 06:03) and kept two as non-responsive (03:01, 03:09). Item 4 of the
refinement reads "Anything containing a reference to ... Geosyntec ... sent to or from ... anyone at Geosyntec",
and the verifier flagged all six on that literal reading.

### CJ. The JSON verdict modes on the same emails (contrast)

Rows with a null score dropped: 5 (27b json: 25-3152 syn 15:09, 25-3152 syn 16:01; 9b jsonR: 25-3152 syn 20:06; 27b jsonR: 25-3152 syn 16:05; 27b json +roster: 25-3152 syn 12:03).

Consensus misses: each JSON run's verdict (the label is responsive, so 'yes' is right).

| pair | kind | 4b json | 9b json | 27b json | 4b jsonR | 9b jsonR | 27b jsonR |
|---|---|---|---|---|---|---|---|
| 24-409 real 33733472 | real_positive | no | no | yes | no | no | yes |
| 24-409 syn 00:03 | close_call_positive | no | no | yes | no | no | yes |
| 24-409 syn 02:01 | close_call_positive | yes | no | no | yes | yes | yes |
| 25-3152 real 48517463 | real_positive | no | yes | no | no | yes | no |
| 25-3152 real 48517567 | real_positive | no | no | no | no | no | no |
| 25-3152 real 48517588 | real_positive | no | no | no | no | yes | no |
| 25-3152 real 48517769 | real_positive | no | no | no | no | no | no |
| 25-3152 real 48517957 | real_positive | yes | no | no | no | yes | no |
| 25-3152 real 48518005 | real_positive | no | no | no | no | yes | no |
| 25-3152 real 48518202 | real_positive | no | no | yes | no | no | no |
| 25-3152 syn 20:06 | privileged_positive | no | yes | no | no | (dropped) | no |

Consensus false positives: share each JSON run calls responsive (the label is non-responsive, so 'yes' is wrong), next to its rate on all negatives.

| JSON run | says yes on consensus FPs | says yes on all negatives |
|---|---|---|
| 4b json | 43/57 (75%, 63%–85%) | 50/211 (24%, 18%–30%) |
| 9b json | 27/57 (47%, 35%–60%) | 28/211 (13%, 9%–19%) |
| 27b json | 28/55 (51%, 38%–64%) | 28/209 (13%, 9%–19%) |
| 4b jsonR | 36/57 (63%, 50%–74%) | 41/211 (19%, 15%–25%) |
| 9b jsonR | 36/57 (63%, 50%–74%) | 49/211 (23%, 18%–29%) |
| 27b jsonR | 32/56 (57%, 44%–69%) | 38/210 (18%, 13%–24%) |

27b jsonR 'yes' answers: how often the reasoning (saved first 600 characters) justifies the yes by a named person, and how often it concedes the subject is off-topic or personal but says yes anyway ('although the subject matter ... does not explicitly mention', 'regardless of', 'unless purely personal'). Regex counts; this is the reasoning-first JSON mode of the 27b, not the lp score, so it is suggestive only.

| request | label | 27b jsonR says yes | yes justified by a named person | yes while conceding off-topic | which negatives |
|---|---|---|---|---|---|
| 24-409 | negatives | 24/102 | 24/24 (100%, 86%–100%) | 9/24 (38%, 21%–57%) | 24-409 syn 03:00, 24-409 syn 03:01, 24-409 syn 03:05, 24-409 syn 05:07, 24-409 syn 06:04, 24-409 syn 06:09, 24-409 syn 07:02, 24-409 syn 07:03, 24-409 syn 07:07 |
| 24-409 | positives | 144/144 | 136/144 (94%, 89%–97%) | 2/144 (1%, 0%–5%) |  |
| 25-3152 | negatives | 14/108 | 0/14 (0%, 0%–22%) | 2/14 (14%, 4%–40%) | 25-3152 syn 15:01, 25-3152 syn 15:08 |
| 25-3152 | positives | 125/140 | 3/125 (2%, 1%–7%) | 5/125 (4%, 2%–9%) |  |

**What the reading shows.**

- **Consensus misses (11).** All labels hold. Seven are one pattern: the ACPG chair is one of 19-31 recipients
  (C3a-1, recipients column) of a reply-all from another planning group or the County, and nothing in the email
  names the ACPG. The County produced all six real ones, and the owner confirmed three of them. The 27b's
  reasoning-first answers without the roster say no to all seven and call the content another group's
  business. [corrected in verification: this read "with and without the roster ... 'merely CC'd' ... 'not ACPG
  business'". With the roster, the 27b jsonR says yes to 4 of the 7 (48517463, 48517567, 48517957, 48518005).
  Of its three no answers, two call the chair "merely" copied (`c_misses_verify.py` V11).]
  The rest: an automated password reset to the chair, two 24-409 emails whose only hook is one acronym or one
  line (an "alignment with RDF" summary; "from the RWER outreach"), and 02:01, whose only hook lies past the body
  cap, so no model sees it.
- **Consensus false positives (57).** 51 labels are right, 5 arguable, 1 likely wrong (C3b). The errors are model
  errors of recognizable kinds: dates outside the window (17), a term in another sense or a near-name such as
  APG for ACPG or "Tree Equity" for the water equity report (12), the purely-personal exception (8), a term only
  in a footer or link list (8), forwards and auto-replies with no content (5), named correspondents with no
  listed term (3), non-members taken for members (2), and the two Geosyntec-address emails.
- **On 24-409 the models treat named people as enough.** Item 4 of the 24-409 refinement needs both a listed
  term and a named correspondent. When the 27b's reasoning-first answer says yes to a 24-409 negative, it
  concedes the subject is off-topic in 9 of 24, against 2 of 144 for 24-409 positives (CJ), which fits the
  prompt-2 rule ("an email to or from one of them is responsive whatever its subject") being applied to a request
  it was not written for. This is the JSON mode's reasoning, not the lp score, so it is suggestive only.

## C4. What the misses track

### C4a. At the default decision

Cell = missed / positives in that group. The last column counts consensus misses (>= 3 models) at this cutoff; for the token rows it uses the 27b lp token count (the lp models share a tokenizer).

| factor | level | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev | consensus misses (k/n, 95% CI) |
|---|---|---|---|---|---|---|---|---|---|
| request | 24-409 | 7/144 | 12/144 | 5/144 | 9/144 | 11/144 | 0/144 | 1/144 | 3/144 (2%, 1%–6%) |
| request | 25-3152 | 7/140 | 5/140 | 15/140 | 8/140 | 2/140 | 1/140 | 17/140 | 8/140 (6%, 3%–11%) |
| prompt tokens (that model's count) | 2,049-4,096 | 7/106 | 8/106 | 8/106 | 7/111 | 8/111 | 1/111 | 9/145 | 5/106 (5%, 2%–11%) |
| prompt tokens (that model's count) | <= 2,048 | 7/176 | 9/176 | 12/176 | 10/171 | 5/171 | 0/171 | 9/136 | 6/176 (3%, 2%–7%) |
| prompt tokens (that model's count) | > 4,096 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/3 | 0/2 (0%, 0%–66%) |
| truncated (body > 8,000 chars) | no | 10/246 | 13/246 | 19/246 | 14/246 | 9/246 | 1/246 | 18/246 | 10/246 (4%, 2%–7%) |
| truncated (body > 8,000 chars) | yes | 4/38 | 4/38 | 1/38 | 3/38 | 4/38 | 0/38 | 0/38 | 1/38 (3%, 0%–13%) |
| attachments listed | no | 6/129 | 6/129 | 8/129 | 7/129 | 5/129 | 0/129 | 7/129 | 6/129 (5%, 2%–10%) |
| attachments listed | yes | 8/155 | 11/155 | 12/155 | 10/155 | 8/155 | 1/155 | 11/155 | 5/155 (3%, 1%–7%) |
| hook location (keyword heuristic) | ACPG named in subject, visible body or attachment names | 0/82 | 2/82 | 0/82 | 2/82 | 0/82 | 0/82 | 0/82 | 0/82 (0%, 0%–4%) |
| hook location (keyword heuristic) | member in headers; ACPG not named | 7/58 | 3/58 | 15/58 | 6/58 | 2/58 | 1/58 | 17/58 | 8/58 (14%, 7%–25%) |
| hook location (keyword heuristic) | no topic term found | 0/1 | 0/1 | 1/1 | 0/1 | 1/1 | 0/1 | 0/1 | 0/1 (0%, 0%–79%) |
| hook location (keyword heuristic) | topic term in subject or visible body | 7/138 | 12/138 | 2/138 | 8/138 | 9/138 | 0/138 | 1/138 | 2/138 (1%, 0%–5%) |
| hook location (keyword heuristic) | topic term only in attachment names | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 (0%, 0%–66%) |
| hook location (keyword heuristic) | topic term only in headers | 0/2 | 0/2 | 1/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 (0%, 0%–66%) |
| hook location (keyword heuristic) | topic term only past the body cap | 0/1 | 0/1 | 1/1 | 1/1 | 1/1 | 0/1 | 0/1 | 1/1 (100%, 21%–100%) |
| recipients (To+Cc+Bcc) | 1-9 | 8/244 | 14/244 | 8/244 | 11/244 | 12/244 | 0/244 | 9/244 | 4/244 (2%, 1%–4%) |
| recipients (To+Cc+Bcc) | >= 10 | 6/40 | 3/40 | 12/40 | 6/40 | 1/40 | 1/40 | 9/40 | 7/40 (18%, 9%–32%) |
| kind | close_call_positive | 1/50 | 3/50 | 2/50 | 5/50 | 4/50 | 0/50 | 3/50 | 2/50 (4%, 1%–13%) |
| kind | exempt_other_positive | 0/40 | 0/40 | 1/40 | 0/40 | 1/40 | 0/40 | 1/40 | 0/40 (0%, 0%–9%) |
| kind | hard_negative_flipped | 1/4 | 2/4 | 1/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 (0%, 0%–49%) |
| kind | privileged_positive | 1/40 | 0/40 | 1/40 | 1/40 | 1/40 | 0/40 | 0/40 | 1/40 (2%, 0%–13%) |
| kind | real_positive | 11/150 | 12/150 | 15/150 | 11/150 | 7/150 | 1/150 | 14/150 | 8/150 (5%, 3%–10%) |

[corrected in verification] The two 25-3152 hook-location rows read 0/81 and 8/59 before. The ACPG regex in
`c_misses_common.py` missed a mention broken across a line ("Alpine\nCommunity Planning Group", 25-3152 syn
12:07, a positive no model misses), so 12:07 was filed under "ACPG not named". The regex now allows any
whitespace and excludes the place name "Alpine Community Planning Area". The same fix applies to C4b and C4c. No
consensus count changes.

### C4b. At each model's thr98

Cell = missed / positives in that group. The last column counts consensus misses (>= 3 models) at this cutoff; for the token rows it uses the 27b lp token count (the lp models share a tokenizer).

| factor | level | 4b lp | 9b lp | 27b lp | d3-4b | d3-9b | d3-27b | Jev | consensus misses (k/n, 95% CI) |
|---|---|---|---|---|---|---|---|---|---|
| request | 24-409 | 2/144 | 5/144 | 0/144 | 3/144 | 4/144 | 0/144 | 0/144 | 0/144 (0%, 0%–3%) |
| request | 25-3152 | 3/140 | 0/140 | 5/140 | 2/140 | 1/140 | 5/140 | 5/140 | 3/140 (2%, 1%–6%) |
| prompt tokens (that model's count) | 2,049-4,096 | 2/106 | 4/106 | 2/106 | 4/111 | 2/111 | 3/111 | 3/145 | 2/106 (2%, 1%–7%) |
| prompt tokens (that model's count) | <= 2,048 | 3/176 | 1/176 | 3/176 | 1/171 | 3/171 | 2/171 | 2/136 | 1/176 (1%, 0%–3%) |
| prompt tokens (that model's count) | > 4,096 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/3 | 0/2 (0%, 0%–66%) |
| truncated (body > 8,000 chars) | no | 3/246 | 3/246 | 5/246 | 3/246 | 5/246 | 5/246 | 5/246 | 3/246 (1%, 0%–4%) |
| truncated (body > 8,000 chars) | yes | 2/38 | 2/38 | 0/38 | 2/38 | 0/38 | 0/38 | 0/38 | 0/38 (0%, 0%–9%) |
| attachments listed | no | 2/129 | 2/129 | 4/129 | 2/129 | 1/129 | 2/129 | 1/129 | 2/129 (2%, 0%–5%) |
| attachments listed | yes | 3/155 | 3/155 | 1/155 | 3/155 | 4/155 | 3/155 | 4/155 | 1/155 (1%, 0%–4%) |
| hook location (keyword heuristic) | ACPG named in subject, visible body or attachment names | 0/82 | 0/82 | 0/82 | 0/82 | 0/82 | 0/82 | 0/82 | 0/82 (0%, 0%–4%) |
| hook location (keyword heuristic) | member in headers; ACPG not named | 3/58 | 0/58 | 5/58 | 2/58 | 1/58 | 5/58 | 5/58 | 3/58 (5%, 2%–14%) |
| hook location (keyword heuristic) | no topic term found | 0/1 | 0/1 | 0/1 | 0/1 | 1/1 | 0/1 | 0/1 | 0/1 (0%, 0%–79%) |
| hook location (keyword heuristic) | topic term in subject or visible body | 2/138 | 5/138 | 0/138 | 2/138 | 3/138 | 0/138 | 0/138 | 0/138 (0%, 0%–3%) |
| hook location (keyword heuristic) | topic term only in attachment names | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 (0%, 0%–66%) |
| hook location (keyword heuristic) | topic term only in headers | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 (0%, 0%–66%) |
| hook location (keyword heuristic) | topic term only past the body cap | 0/1 | 0/1 | 0/1 | 1/1 | 0/1 | 0/1 | 0/1 | 0/1 (0%, 0%–79%) |
| recipients (To+Cc+Bcc) | 1-9 | 3/244 | 5/244 | 0/244 | 3/244 | 4/244 | 1/244 | 2/244 | 0/244 (0%, 0%–2%) |
| recipients (To+Cc+Bcc) | >= 10 | 2/40 | 0/40 | 5/40 | 2/40 | 1/40 | 4/40 | 3/40 | 3/40 (8%, 3%–20%) |
| kind | close_call_positive | 0/50 | 1/50 | 0/50 | 1/50 | 2/50 | 0/50 | 1/50 | 0/50 (0%, 0%–7%) |
| kind | exempt_other_positive | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 (0%, 0%–9%) |
| kind | hard_negative_flipped | 0/4 | 1/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 (0%, 0%–49%) |
| kind | privileged_positive | 0/40 | 0/40 | 1/40 | 0/40 | 0/40 | 0/40 | 0/40 | 0/40 (0%, 0%–9%) |
| kind | real_positive | 5/150 | 3/150 | 4/150 | 4/150 | 3/150 | 5/150 | 4/150 | 3/150 (2%, 1%–6%) |

### C4c. Tests

Two-sided p. Small counts: read these as a screen for large effects, not as proof of none.

| split (first vs second) | consensus misses, first group | second group | Fisher p |
|---|---|---|---|
| 25-3152 vs 24-409 | 8/140 (6%, 3%–11%) | 3/144 (2%, 1%–6%) | 0.134 |
| > 2,048 tokens (27b lp) vs <= | 5/108 (5%, 2%–10%) | 6/176 (3%, 2%–7%) | 0.753 |
| truncated vs not | 1/38 (3%, 0%–13%) | 10/246 (4%, 2%–7%) | 1 |
| attachments vs none | 5/155 (3%, 1%–7%) | 6/129 (5%, 2%–10%) | 0.554 |
| >= 10 recipients vs fewer | 7/40 (18%, 9%–32%) | 4/244 (2%, 1%–4%) | 0.000144 |
| real_positive vs synthetic positive | 8/150 (5%, 3%–10%) | 3/134 (2%, 1%–6%) | 0.226 |
| 25-3152 only: >= 10 recipients vs fewer | 7/34 (21%, 10%–37%) | 1/106 (1%, 0%–5%) | 0.000197 |
| 25-3152 only: ACPG not named in visible text vs named | 8/58 (14%, 7%–25%) | 0/82 (0%, 0%–4%) | 0.000642 |

[corrected in verification] This row read 8/59 vs 0/81, p = 0.000743, before the ACPG regex fix (see C4a).

Per model, misses at 0.5 by request (Fisher two-sided p for 25-3152 vs 24-409):

| model | 25-3152 misses at 0.5 | 24-409 misses at 0.5 | Fisher p |
|---|---|---|---|
| 4b lp | 7/140 (5%, 2%–10%) | 7/144 (5%, 2%–10%) | 1 |
| 9b lp | 5/140 (4%, 2%–8%) | 12/144 (8%, 5%–14%) | 0.132 |
| 27b lp | 15/140 (11%, 7%–17%) | 5/144 (3%, 1%–8%) | 0.0202 |
| d3-4b | 8/140 (6%, 3%–11%) | 9/144 (6%, 3%–11%) | 1 |
| d3-9b | 2/140 (1%, 0%–5%) | 11/144 (8%, 4%–13%) | 0.0197 |
| d3-27b | 1/140 (1%, 0%–4%) | 0/144 (0%, 0%–3%) | 0.493 |
| Jev | 17/140 (12%, 8%–19%) | 1/144 (1%, 0%–4%) | 3.89e-05 |

25-3152 positives only, miss events at 0.5 pooled over the 7 models: >= 10 recipients 37/238 (16%, 11%–21%); fewer 18/742 (2%, 2%–4%). (Pooled events are not independent; the same pairs repeat across models.)

**What the data shows.**

- **Recipient count is the one strong signal.** Positives with at least 10 recipients are consensus misses at
  0.5 in 7 of 40 cases, against 4 of 244 with fewer (Fisher p = 0.000144); within 25-3152, 7 of 34 against 1 of
  106. Positives where the ACPG is named in the visible text are never consensus misses (0 of 82
  [corrected in verification; was 0 of 81]).
- **Length, truncation and attachments show no large effect.** Consensus misses at 0.5: over 2,048 tokens 5 of
  108 against 6 of 176 at or under; truncated 1 of 38 against 10 of 246; with attachments 5 of 155 against 6 of
  129 (all p above 0.5). Only 2 positives exceed 4,096 tokens (27b lp count), so that mark can't be tested here.
  Content found only in attachment names: 2 positives, no consensus misses. Truncation causes exactly one
  consensus miss (02:01), by design.
- **The request matters per model, in opposite directions.** The 27b lp and Jev miss mostly 25-3152 positives
  (15/140 against 5/144, p = 0.0202; 17/140 against 1/144, p = 3.89e-05); the d3-9b misses mostly 24-409 ones
  (11/144 against 2/140, p = 0.0197). For consensus misses (>= 3 models), the request difference is not clear
  (8/140 against 3/144, p = 0.134). Pooled miss events at 0.5 are 55/980 against 45/1008; these are not
  independent. [corrected in verification: 8/140 and 3/144 were labeled "pooled over models", but they are
  consensus-miss counts. The pooled event counts come from `c_misses_verify.py` V9.]

## C5. Labels for the owner to re-check

No label or data file was changed. Each candidate below is flipped in memory and every model's thr98, elim@98 and
AUROC are recomputed on all 495 pairs.

### C5a. Single labels

Each row flips one label and recomputes every model's thr98, elim@98 (percentage points) and AUROC on all 495 pairs. '+roster' = the same flip on the 25-3152 roster runs (249 pairs). Ordered by |mean Δelim@98|, then |mean ΔAUROC|. Δelim@98 is in percentage points.

| candidate | Δelim@98 4b lp | Δelim@98 9b lp | Δelim@98 27b lp | Δelim@98 d3-4b | Δelim@98 d3-9b | Δelim@98 d3-27b | Δelim@98 Jev | mean Δelim@98 | mean ΔAUROC | ΔAUROC range | mean Δelim@98 +roster |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 25-3152 syn 15:02 (arguable; label 0 → 1) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0016 | -0.0001 to +0.0041 | +0.8 |
| 24-409 syn 07:01 (arguable; label 0 → 1) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0015 | +0.0004 to +0.0030 | — |
| 25-3152 syn 15:01 (arguable; label 0 → 1) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0013 | -0.0003 to +0.0037 | +0.7 |
| 25-3152 syn 15:06 (arguable; label 0 → 1) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0012 | -0.0005 to +0.0037 | +0.8 |
| 24-409 syn 03:01 (likely wrong; label 0 → 1) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0008 | -0.0011 to +0.0034 | — |
| 24-409 syn 03:09 (arguable; label 0 → 1) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0002 | -0.0012 to +0.0013 | — |

### C5b. Label questions that cover several emails

| candidate | Δelim@98 4b lp | Δelim@98 9b lp | Δelim@98 27b lp | Δelim@98 d3-4b | Δelim@98 d3-9b | Δelim@98 d3-27b | Δelim@98 Jev | mean Δelim@98 | mean ΔAUROC | ΔAUROC range | mean Δelim@98 +roster |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 Geosyntec only in the addresses: 03:01, 03:09 to responsive (consistency with the owner's flips) (n=2) | +0.5 | +0.7 | +0.7 | +0.5 | +0.7 | +0.8 | +0.6 | +0.6 | +0.0011 | -0.0023 to +0.0047 | — |
| Q2 RDF = refuse-derived fuel: 07:01 to responsive (n=1) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0015 | +0.0004 to +0.0030 | — |
| Q2' RDF = refuse-derived fuel: 07:01 dropped (as 07:09 was) (n=1) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0015 | +0.0005 to +0.0028 | — |
| Q3 'purely personal', the three arguable ones to responsive (n=3) | +0.7 | +1.0 | +1.1 | +0.8 | +1.0 | +1.2 | +0.9 | +1.0 | +0.0042 | +0.0007 to +0.0115 | +2.3 |
| Q4 all nine 'purely personal' 25-3152 emails to responsive (the pre-2026-10-31 labels) (n=9) | +2.3 | +2.2 | +2.9 | +2.4 | +3.0 | -0.3 | +0.3 | +1.8 | +0.0074 | -0.0050 to +0.0274 | +5.2 |
| Q5 one member among many recipients: the 7 such consensus misses to non-responsive (a narrower reading) (n=7) | +18.1 | -2.3 | +10.4 | +3.3 | -0.4 | +2.0 | +3.9 | +5.0 | +0.0056 | +0.0004 to +0.0101 | -0.8 |

### C5c. Every consensus item, one flip at a time

Rows for the 11 consensus misses first, then the 57 consensus false positives; each group ordered as in C5a.

| candidate | Δelim@98 4b lp | Δelim@98 9b lp | Δelim@98 27b lp | Δelim@98 d3-4b | Δelim@98 d3-9b | Δelim@98 d3-27b | Δelim@98 Jev | mean Δelim@98 | mean ΔAUROC | ΔAUROC range | mean Δelim@98 +roster |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 25-3152 real 48517463 (right) | -0.2 | -0.3 | +2.9 | +1.2 | +1.6 | +0.1 | -0.3 | +0.7 | +0.0011 | -0.0002 to +0.0024 | -0.5 |
| 25-3152 real 48517588 (right) | +1.6 | -0.3 | +2.9 | -0.3 | -0.3 | -0.4 | +0.2 | +0.5 | +0.0009 | -0.0001 to +0.0022 | -0.2 |
| 25-3152 real 48517567 (right) | -0.2 | -0.3 | +2.9 | +1.2 | -0.3 | +0.1 | -0.3 | +0.4 | +0.0008 | +0.0000 to +0.0018 | -0.8 |
| 25-3152 syn 20:06 (right) | +1.6 | -0.3 | +2.9 | -0.3 | -0.3 | -0.4 | -0.3 | +0.4 | +0.0007 | -0.0002 to +0.0017 | -0.8 |
| 25-3152 real 48517769 (right) | -0.2 | -0.3 | +2.9 | -0.3 | -0.3 | +0.1 | +0.2 | +0.3 | +0.0005 | -0.0013 to +0.0015 | -0.5 |
| 25-3152 real 48517957 (right) | -0.2 | -0.3 | +2.9 | -0.3 | -0.3 | -0.4 | +0.2 | +0.2 | +0.0005 | +0.0000 to +0.0014 | -0.4 |
| 24-409 real 33733472 (right) | -0.2 | -0.3 | -0.4 | +1.2 | +1.6 | -0.4 | -0.3 | +0.2 | +0.0011 | +0.0000 to +0.0026 | — |
| 24-409 syn 00:03 (right) | -0.2 | +1.1 | -0.4 | -0.3 | +1.6 | -0.4 | -0.3 | +0.2 | -0.0000 | -0.0014 to +0.0015 | — |
| 24-409 syn 02:01 (right) | -0.2 | -0.3 | -0.4 | +1.2 | -0.3 | -0.4 | -0.3 | -0.1 | +0.0004 | -0.0007 to +0.0020 | — |
| 25-3152 real 48518202 (right) | +1.6 | -0.3 | -0.4 | -0.3 | -0.3 | -0.4 | -0.3 | -0.0 | +0.0007 | -0.0007 to +0.0028 | -0.6 |
| 25-3152 real 48518005 (right) | +1.6 | -0.3 | -0.4 | -0.3 | -0.3 | -0.4 | +0.2 | +0.0 | +0.0008 | -0.0005 to +0.0020 | -0.1 |

| candidate | Δelim@98 4b lp | Δelim@98 9b lp | Δelim@98 27b lp | Δelim@98 d3-4b | Δelim@98 d3-9b | Δelim@98 d3-27b | Δelim@98 Jev | mean Δelim@98 | mean ΔAUROC | ΔAUROC range | mean Δelim@98 +roster |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 24-409 syn 03:05 (right) | -4.5 | -0.6 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | -0.5 | -0.0006 | -0.0028 to +0.0006 | — |
| 24-409 syn 06:04 (right) | -4.5 | -0.6 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | -0.5 | -0.0004 | -0.0021 to +0.0007 | — |
| 25-3152 syn 15:02 (arguable) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0016 | -0.0001 to +0.0041 | +0.8 |
| 24-409 syn 07:01 (arguable) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0015 | +0.0004 to +0.0030 | — |
| 25-3152 syn 15:01 (arguable) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0013 | -0.0003 to +0.0037 | +0.7 |
| 25-3152 syn 15:06 (arguable) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0012 | -0.0005 to +0.0037 | +0.8 |
| 24-409 syn 07:07 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0012 | -0.0001 to +0.0034 | — |
| 25-3152 syn 19:08 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0011 | -0.0007 to +0.0031 | +0.3 |
| 25-3152 syn 15:08 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0011 | -0.0005 to +0.0041 | +0.5 |
| 24-409 syn 07:04 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0010 | -0.0008 to +0.0022 | — |
| 25-3152 syn 19:01 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0010 | -0.0007 to +0.0023 | +0.3 |
| 25-3152 syn 17:01 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0008 | -0.0002 to +0.0031 | -0.0 |
| 24-409 syn 03:01 (likely wrong) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0008 | -0.0011 to +0.0034 | — |
| 24-409 syn 04:06 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0005 | -0.0011 to +0.0019 | — |
| 24-409 syn 04:09 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0005 | -0.0003 to +0.0032 | — |
| 24-409 syn 05:00 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | -0.0005 | -0.0014 to +0.0001 | — |
| 25-3152 syn 15:09 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0005 | -0.0008 to +0.0023 | +0.5 |
| 25-3152 syn 15:04 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0004 | -0.0011 to +0.0032 | +0.4 |
| 24-409 syn 03:02 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | -0.0004 | -0.0016 to +0.0014 | — |
| 25-3152 syn 18:07 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0004 | -0.0005 to +0.0015 | -0.3 |
| 24-409 syn 07:00 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0003 | -0.0013 to +0.0028 | — |
| 25-3152 syn 19:03 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | -0.0003 | -0.0015 to +0.0005 | -0.0 |
| 24-409 syn 03:09 (arguable) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0002 | -0.0012 to +0.0013 | — |
| 24-409 syn 04:08 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | +0.0002 | -0.0010 to +0.0014 | — |
| 24-409 syn 06:06 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.3 | -0.0001 | -0.0010 to +0.0015 | — |
| 24-409 syn 07:03 (right) | +0.2 | -0.1 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.2 | +0.0002 | -0.0010 to +0.0019 | — |
| 25-3152 syn 17:05 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | -0.6 | +0.3 | +0.2 | +0.0021 | -0.0007 to +0.0041 | +0.1 |
| 25-3152 syn 16:08 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | -0.6 | +0.3 | +0.2 | +0.0011 | -0.0010 to +0.0044 | +0.4 |
| 24-409 syn 04:04 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | -0.6 | +0.3 | +0.2 | +0.0007 | -0.0012 to +0.0030 | — |
| 25-3152 syn 16:02 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | -0.6 | +0.3 | +0.2 | +0.0006 | -0.0009 to +0.0028 | +0.4 |
| 25-3152 syn 18:03 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | -0.6 | +0.3 | +0.2 | -0.0005 | -0.0012 to +0.0004 | -0.3 |
| 24-409 syn 05:05 (right) | +0.2 | +0.3 | +0.4 | +0.3 | -0.6 | +0.4 | +0.3 | +0.2 | -0.0005 | -0.0012 to +0.0005 | — |
| 25-3152 syn 18:08 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | -0.6 | +0.3 | +0.2 | +0.0004 | -0.0010 to +0.0023 | +0.1 |
| 25-3152 syn 17:00 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | -0.6 | +0.3 | +0.2 | -0.0004 | -0.0013 to +0.0015 | -0.0 |
| 24-409 syn 04:03 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | -0.6 | +0.3 | +0.2 | +0.0002 | -0.0009 to +0.0023 | — |
| 25-3152 syn 16:01 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | -0.6 | +0.3 | +0.2 | +0.0001 | -0.0011 to +0.0017 | -0.5 |
| 25-3152 syn 19:02 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | -0.6 | +0.3 | +0.2 | -0.0001 | -0.0008 to +0.0011 | -1.2 |
| 25-3152 syn 16:05 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | -0.6 | +0.3 | +0.2 | +0.0001 | -0.0012 to +0.0016 | +0.4 |
| 25-3152 syn 17:02 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | -0.6 | +0.3 | +0.2 | -0.0000 | -0.0008 to +0.0014 | +0.3 |
| 25-3152 syn 19:00 (right) | +0.2 | -0.6 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.2 | +0.0004 | -0.0011 to +0.0018 | -0.0 |
| 24-409 syn 05:07 (right) | +0.2 | -0.6 | +0.4 | +0.3 | +0.3 | +0.4 | +0.3 | +0.2 | -0.0004 | -0.0021 to +0.0018 | — |
| 24-409 syn 04:05 (right) | +0.2 | +0.3 | -0.1 | +0.3 | +0.3 | -0.6 | +0.3 | +0.1 | -0.0008 | -0.0014 to +0.0004 | — |
| 25-3152 syn 16:07 (right) | +0.2 | +0.3 | -0.1 | +0.3 | +0.3 | -0.6 | +0.3 | +0.1 | -0.0004 | -0.0013 to +0.0011 | -0.8 |
| 24-409 syn 04:07 (right) | +0.2 | +0.3 | -0.1 | +0.3 | +0.3 | -0.6 | +0.3 | +0.1 | -0.0003 | -0.0012 to +0.0010 | — |
| 24-409 syn 07:08 (right) | +0.2 | +0.3 | -0.1 | +0.3 | -0.6 | +0.4 | +0.3 | +0.1 | -0.0003 | -0.0013 to +0.0011 | — |
| 24-409 syn 04:00 (right) | +0.2 | +0.3 | -0.1 | +0.3 | +0.3 | -0.6 | +0.3 | +0.1 | +0.0002 | -0.0012 to +0.0016 | — |
| 25-3152 syn 16:00 (right) | +0.2 | +0.3 | -0.1 | +0.3 | +0.3 | -0.6 | +0.3 | +0.1 | +0.0002 | -0.0014 to +0.0029 | -0.9 |
| 25-3152 syn 16:04 (right) | +0.2 | +0.3 | -0.1 | +0.3 | +0.3 | -0.6 | +0.3 | +0.1 | -0.0002 | -0.0014 to +0.0030 | -0.9 |
| 25-3152 syn 16:06 (right) | +0.2 | +0.3 | -0.1 | +0.3 | +0.3 | -0.6 | +0.3 | +0.1 | -0.0001 | -0.0011 to +0.0025 | -0.8 |
| 25-3152 syn 15:03 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | -0.6 | -1.6 | -0.1 | +0.0006 | -0.0019 to +0.0036 | +0.4 |
| 25-3152 syn 15:05 (right) | +0.2 | +0.3 | +0.4 | +0.3 | +0.3 | -0.6 | -1.6 | -0.1 | -0.0000 | -0.0017 to +0.0031 | +0.7 |
| 24-409 syn 04:02 (right) | +0.2 | +0.3 | +0.4 | +0.3 | -0.6 | -0.6 | +0.3 | +0.0 | -0.0008 | -0.0019 to +0.0005 | — |
| 25-3152 syn 17:06 (right) | +0.2 | +0.3 | +0.4 | -0.7 | +0.3 | -0.6 | +0.3 | +0.0 | -0.0003 | -0.0018 to +0.0024 | -0.1 |
| 24-409 syn 05:06 (right) | +0.2 | -0.6 | +0.4 | +0.3 | -0.6 | +0.4 | +0.3 | +0.0 | -0.0010 | -0.0019 to -0.0003 | — |
| 24-409 syn 07:02 (right) | +0.2 | -0.6 | +0.4 | +0.3 | -0.6 | +0.4 | +0.3 | +0.0 | -0.0004 | -0.0015 to +0.0010 | — |
| 24-409 syn 06:09 (right) | +0.2 | -0.6 | +0.4 | +0.3 | -0.6 | +0.4 | +0.3 | +0.0 | +0.0004 | -0.0012 to +0.0022 | — |
| 24-409 syn 07:06 (right) | +0.2 | -0.6 | +0.4 | +0.3 | -0.6 | +0.4 | +0.3 | +0.0 | -0.0003 | -0.0012 to +0.0008 | — |

- consensus misses (n=11), one flip each: mean Δelim@98 from -0.1 to +0.7 pp; single-model Δelim@98 from -0.4 to +2.9 pp; mean ΔAUROC from -0.0000 to +0.0011.
- consensus false positives (n=57), one flip each: mean Δelim@98 from -0.5 to +0.3 pp; single-model Δelim@98 from -4.5 to +0.4 pp; mean ΔAUROC from -0.0010 to +0.0021.

Baseline (current labels): 4b lp elim@98 51.7%, AUROC 0.9228; 9b lp elim@98 70.6%, AUROC 0.9424; 27b lp elim@98 75.8%, AUROC 0.9754; d3-4b elim@98 53.6%, AUROC 0.8842; d3-9b elim@98 68.2%, AUROC 0.9470; d3-27b elim@98 81.0%, AUROC 0.9795; Jev elim@98 63.0%, AUROC 0.9164.

**The re-check list, in order** (C5a ties on mean elim@98, so the order follows mean ΔAUROC):

1. **25-3152 syn 15:02** (rooftop-lease emails misaddressed to the chair): not personal, but misdirected business
   mail from md7, which the verifier identifies as the applicant on a real permit before the group. The "purely
   personal" label was applied to it by extension from the 15:05/15:09 calls.
2. **24-409 syn 07:01** ("RDF proposal" meaning refuse-derived fuel, among named County staff): never
   human-adjudicated; the same ambiguity led the owner to drop 07:09. Dropping 07:01 moves the headline the same
   as flipping it (C5b, Q2 and Q2').
3. **25-3152 syn 15:01** (TV interview about the chair's own insurance, signed as Chair) and
4. **25-3152 syn 15:06** (the chair's warning to a County planner and an applicant's representative that his ACPG
   account was hacked): both labeled "purely personal" by extension; both carry his official title and touch
   group business at the edges.
5. **24-409 syn 03:01** (likely wrong) and 6. **24-409 syn 03:09** (arguable): the Geosyntec-address pattern of
   C3c. 03:01 is logistics for project meetings, like the flipped 03:07; 03:09 is a team volunteer outing.

Each of these moves mean elim@98 by +0.3 percentage points and mean AUROC by at most +0.0016 (C5a). The label
questions that cover groups move it more: making all nine "purely personal" emails responsive again adds 1.8
points on the main set and 5.2 on the roster runs (Q4); a narrower reading of the seven one-member-among-many
misses adds 5.0 points on average, 18.1 for the 4b lp and 10.4 for the 27b lp, because those emails set the
thresholds (Q5). The narrower reading cuts the other way with the roster (-0.8), where the models already catch
those emails.

## Findings

1. **Model misses rarely overlap.** At thr98 the 7 models' 35 misses fall on 23 different positives; 3 are
   consensus misses, all real 25-3152 emails. At 0.5 there are 11 (8 from 25-3152). *Confidence: high.* (C1b,
   C1d)
2. **The shared miss is the passive recipient.** 7 of the 11 consensus misses are 25-3152 emails on which the ACPG
   chair is one of 19-31 recipients and the ACPG is not named. Recipient count and whether the ACPG is named are
   the only factors tested that track consensus misses (7/40 with 10 or more recipients against 4/244,
   p = 0.000144; within 25-3152, 8/58 where the ACPG is not named against 0/82 [corrected in verification;
   was 8/59 against 0/81]). *High.* (C3a-1, C4a, C4c)
3. **The roster cuts the consensus misses at the default decision.** At 0.5, 25-3152 consensus misses fall from
   8 to 2 with the roster. [corrected in verification: this finding was headed "The roster removes the consensus
   at thr98". That compared different miss budgets: the main-set thr98 allows 5 misses anywhere in 495 pairs,
   the roster thr98 allows 2 in 249. With thr98 refitted on the same 249 pairs, the main runs also have 0
   consensus misses at thr98, so thr98 shows no roster effect on consensus misses (`c_misses_verify.py` V5).]
   Each roster run still has its own 2 misses. *Medium* (one run each). (C1e)
4. **Misses don't track prompt length, truncation or attachments.** No split shows a large effect; one consensus
   miss is a truncation case built to be one. The 4,096-token mark can't be tested (2 positives above it).
   *Medium* (small counts). (C4a-c)
5. **Which request a model misses on depends on the model.** The 27b lp and Jev miss mainly 25-3152 positives,
   the d3-9b mainly 24-409 ones. *Medium* (per-model tests, uncorrected). (C4c)
6. **Every consensus false positive is a synthetic hard negative.** 57 of 91 hard negatives are kept by 5 or more
   models at thr98 (36 at 0.5); no real negative is kept by more than 3. *High.* (C2b)
7. **The roster removes most 25-3152 false positives, but not the personal ones.** 25-3152
   consensus false positives fall from 29 to 8 at thr98 with the roster; the 8 left are all "purely personal"
   emails. [corrected in verification: like for like, with thr98 refitted on the same 249 pairs, the drop is
   26 to 8; at 0.5 it is 21 to 11 (`c_misses_verify.py` V5).] *High.* (C2c)
8. **Date errors cluster where the request text holds two windows.** The 27b lp and d3-27b score 24-409 wrong-date
   emails inside the original request's 2022-2024 range well above those outside both ranges (0.33 vs 0.03;
   0.58 vs 0.26); one 27b reasoning answer says it applied the original window. *Medium* (5 emails per group).
   (C2e, C3a-2)
9. **On 24-409, models accept a named correspondent without a listed term.** The 27b's reasoning-first yes answers
   on 24-409 negatives concede an off-topic subject 9 of 24 times against 2 of 144 on positives, consistent with
   the prompt-2 rule being applied to a request whose item 4 needs a term as well. *Medium-low* (JSON-mode
   reasoning, regex count, confounded design). (CJ, C2d)
10. **Most shared errors are model errors, not label errors.** Of 68 consensus items read in full, 62 labels hold,
    5 are arguable and 1 is likely wrong. *Medium* (one reader; the legal calls are the owner's). (C3b)
11. **One label question is an internal inconsistency.** Six synthetic 24-409 emails share the
    "Geosyntec only in the addresses" pattern; four were flipped to responsive and two kept non-responsive.
    *High* for the inconsistency; which way to resolve it is the owner's call. (C3c)
12. **Single label fixes barely move the headline; the scope reading does.** Each re-check candidate changes mean
    elim@98 by +0.3 points; the narrower "passive recipient" reading of the seven consensus misses changes it by
    +5.0 on average and +18.1 for the 4b lp. *High* (arithmetic on saved scores). (C5a, C5b)
13. **The JSON verdicts don't rescue the shared misses.** The 27b's reasoning-first answer says no to all 8
    25-3152 consensus misses; on the consensus false positives the JSON runs say yes 47-75% of the time, against
    13-24% on all negatives. *High* for these runs. (CJ)

## Caveats

- **thr98 is in-sample and tight.** It is fitted on the labels being scored and allows only 5 misses per model
  (2 on the roster runs), so "consensus at thr98" can hold only a handful of emails. The 0.5 and thr95 views
  (C1d) are there to show the pattern doesn't depend on that cutoff.
- **One run per configuration.** A few borderline scores can change which positives a model misses.
- **The false-positive picture is the generator's.** All consensus false positives are synthetic emails built to
  be hard; the real negatives come from other requests' productions and are easy. The rates here say nothing
  about how often such emails turn up in a real keyword-search hit list (see branches B and D).
- **The reading is one reader's.** The judgments were made by an AI analyst (Claude) reading the full records; the
  owner adjudicated most of the items in question and his calls stand. Several synthetic emails are implausible
  in ways the verifier noted (for example 15:04), which a real record would not be.
- **Real positives are the County's production**, which may over-produce; "label right" for those means the
  production and the request text agree, not that a court would agree.
- **The heuristics are rough.** Hook location, recipient count and the named-correspondent flag are regex rules;
  the 27b reasoning counts use the first 600 saved characters of each answer. "First hook at char" in C3a gives
  the first listed term of any kind, so for 02:01 it is a UCSD mention (10,080) rather than the USP signature.
- **Tests are uncorrected** for multiple comparisons, and pooled miss events (C4c) are not independent.
- **JSON contrast**: 5 rows with a null score are dropped (CJ).

## Open questions for the owner

1. For correspondent-scoped requests, is an email on which the member is one of many recipients of someone
   else's reply-all a "communication between" the member and others? This is the single biggest lever on the
   headline (C5b, Q5), and the County's production says yes.
2. Should 03:01 and 03:09 follow the four Geosyntec-address flips (C3c)?
3. Should 07:01 be dropped like 07:09?
4. Should the "purely personal" call, applied by extension, be revisited for 15:01, 15:02 and 15:06?
5. Should the named-correspondent sentence in the prompt be limited to correspondent-scoped requests, given
   finding 9? (Prompt work is outside this branch; it would need a held-out request to test.)
6. Should the 24-409 request text say which of its two date windows governs (finding 8)?

## Reproduce

From the project root (stdlib only; no GPU, Ollama or network; each finishes in a few seconds; the output is
identical across runs and hash seeds):

| command | prints |
|---|---|
| `uv run python scripts/analysis/c_misses.py` | C1a-C1e, C2a-C2e, C4a-C4c, CJ |
| `uv run python scripts/analysis/c_misses_labels.py` | C3a-C3c (with the coded judgments), C5a-C5c |
| `uv run python scripts/analysis/c_misses_read.py [--only misses\|fps] [--pair PAIR_ID ...]` | the full records read for C3 (no statistics) |

`scripts/analysis/c_misses_common.py` holds the shared loading (`golden_report.load_runs`), the run list,
the consensus rules and the heuristics. Every table in this file is copied from the first two commands.

## Verification

**Date:** 2026-11-06. A skeptic pass over this branch. It re-ran the analyst's scripts and recomputed the
consequential numbers in a separate script that imports none of the analyst's code:
`uv run python scripts/analysis/c_misses_verify.py` (sections V1-V12; stdlib only; deterministic, with the same
output under different hash seeds). That script has its own loader (label, kind and recipe joined from
`data/golden/pairs.jsonl`). It computes AUROC over every positive-negative pair (ties count half), thr98 as the
k-th highest positive score (k = ceil(0.98 × positives)), elim@98, Fisher's exact test, Wilson intervals and the
recipient / ACPG / member heuristics from scratch. It checks its AUROC and thr98 against the repo helpers.
Every number in this section is printed by that script.

### Checks

| # | check | result |
|---|---|---|
| 1 | Every table in this file against the script output | **Confirmed.** Every data-table row matched `c_misses.py` / `c_misses_labels.py` output exactly. After the regex fix (correction 1), five rows changed and were updated. |
| 2 | Labels from `pairs.jsonl`, not `scores.jsonl`; dropped rows | **Confirmed.** All 14 score runs: 0 duplicate pair_ids, 0 rows outside `pairs.jsonl`, 0 stale labels, no null scores; 495 rows (284 positives / 211 negatives) or 249 (140 / 109) (V1). The 5 null JSON rows are the 5 listed in CJ. |
| 3 | The right runs | **Confirmed.** The seven score runs and their `_roster` twins named in the brief. The roster runs cover exactly the 249 25-3152 pairs (V1). |
| 4 | Headline numbers, from scratch | **Confirmed.** thr98 / elim@98 / AUROC: 4b lp 0.2650 / 109/211 / 0.92282; 9b lp 0.3309 / 149/211 / 0.94243; 27b lp 0.0687 / 160/211 / 0.97542; d3-4b 0.3507 / 113/211 / 0.88417; d3-9b 0.3379 / 144/211 / 0.94702; d3-27b 0.5857 / 171/211 / 0.97949; Jev 0.3400 / 133/211 / 0.91641. All match the repo helpers and the brief's headline (V2). |
| 5 | Threshold direction and Jev's 2-decimal ties | **Confirmed.** Kept = score >= threshold throughout. Jev has 94 distinct scores; 1 pair sits exactly at its thr98 (0.34), and it counts as kept (V2). |
| 6 | Consensus counts | **Confirmed** (V3). 35 miss events at thr98 on 23 positives; 3 consensus misses at thr98, 11 at 0.5 (8 from 25-3152); 57 consensus FPs at thr98, 36 at 0.5, all hard negatives (57/91); no real negative is kept by more than 3 models; recipes 17/20, 12/15, 13/19. |
| 7 | Recipient count vs consensus misses | **Confirmed** with an independent recipient counter: 7/40 vs 4/244, p = 0.000144; within 25-3152, 7/34 vs 1/106 (V4). The cut at 10 was chosen after reading the misses, but other cuts give the same answer: >= 3, p = 0.0279; >= 5, p = 0.00126; >= 15, p = 1.41e-05; >= 20, p = 0.000154. The effect is model-specific: clear for the 27b lp (12/34 vs 3/106), 4b lp (6/34 vs 1/106) and Jev (9/34 vs 8/106), not the d3-9b (1/34 vs 1/106) or d3-27b (1/34 vs 0/106). |
| 8 | ACPG-named split | **Corrected** (correction 1): 8/58 vs 0/82, p = 0.000642. The conclusion stands. |
| 9 | Roster compared over the right pairs | **Corrected** (corrections 3 and 4). The main-set thr98 was fitted on 495 pairs (5 misses anywhere), the roster thr98 on 249 (2 misses). V5 refits the main runs on the same 249 pairs. |
| 10 | C5a single flips | **Confirmed, and they are mechanical.** Flipping any negative that every model keeps leaves thr98 unchanged and moves elim@98 from k/211 to k/210. That predicts the reported +0.25 to +0.39 points exactly (V7). The equal +0.3 across all six candidates says nothing about which label matters more. |
| 11 | C5b group flips | **Confirmed.** Q1 +0.6, Q3 +1.0 (roster +2.3), Q4 +1.8 (roster +5.2, mean ΔAUROC +0.0074), Q5 +5.0 (4b lp +18.1, 27b lp +10.4, roster -0.8) (V6). Q5 has a selection problem (concern 1). |
| 12 | Truncation | **Numbers confirmed; claim weaker than stated** (concern 4). |
| 13 | Request split per model | **Numbers confirmed; only Jev survives a multiple-comparison bound** (concern 5). |
| 14 | Wrong-date means | **Confirmed:** 27b lp 0.331 vs 0.031, d3-27b 0.582 vs 0.255. **The interpretation has an untested confound** (concern 3). |
| 15 | JSON contrast | **Confirmed:** 27b jsonR says no to all 8 25-3152 consensus misses; 4b json says yes on 43/57 consensus FPs and 50/211 negatives. The 04:06 quote ("falls within the original request's time range") and the 18:07 quote ("Curt Dean (a known ACPG member)") are in the saved answers (V11). **Corrected:** the with-roster description of the 27b's reasoning (correction 5). |
| 16 | Records behind the label calls | **Confirmed** (V12). The six Geosyntec-address emails: owner calls K, F, F, K, F, F (03:01, 03:04, 03:07, 03:09, 06:01, 06:03), no notes, and the verifier marked all six "label correct: False". 07:01 has no owner call, and its verifier note asks the adjudicator to confirm. 07:09 was dropped (call D; not in `pairs.jsonl`). 02:01's body is 15,960 characters (cap 8,000) and is flagged truncated; it is the only truncated consensus miss (V8). On each of the 7 "one of many" misses, Lyon is the only roster member in the headers, always as a To/Cc recipient, with 19-31 recipients. |

### Corrections made in this file

1. **ACPG regex (C4a, C4b, C4c, finding 2, C4 prose).** `ACPG_RE` in `c_misses_common.py` missed "Alpine\nCommunity
   Planning Group" broken across a line (25-3152 syn 12:07). It now allows any whitespace and excludes the place
   name "Alpine Community Planning Area" (25-3152 syn 19:08). The "ACPG not named / named" positives go from
   59/81 to 58/82, and the C4c test from p = 0.000743 to 0.000642. No consensus count or C3 table changes.
2. **"Pooled over models" (C4 prose).** 8/140 vs 3/144 are consensus-miss counts. Pooled miss events at 0.5
   are 55/980 vs 45/1008 (V9).
3. **Finding 3 and the C1 summary.** "The roster removes the consensus at thr98" compared a 5-miss budget over
   495 pairs with a 2-miss budget over 249. Like for like:

   | view (25-3152 pairs only) | 25-3152 miss events (7 models) | consensus misses (>= 3) | consensus FPs (>= 5) | pooled share of the 109 negatives eliminated |
   |---|---|---|---|---|
   | main, thr98 fitted on 495 (analyst) | 21 | 3 | 29 | 62.5% |
   | main, thr98 refitted on the 249 | 14 | 0 | 26 | 62.3% |
   | roster, thr98 fitted on the 249 (analyst) | 14 | 0 | 8 | 84.5% |
   | main, 0.5 | 55 | 8 | 21 | 75.1% |
   | roster, 0.5 | 29 | 2 | 11 | 81.5% |

   The roster does reduce consensus misses at 0.5 (8 to 2). At thr98 the budget alone takes them to 0.
4. **Finding 7 and the C2 summary.** The like-for-like fall in 25-3152 consensus false positives is 26 to 8 at
   thr98 (not 29 to 8), and 21 to 11 at 0.5. The 8 left are still all "purely personal" emails (V5).
5. **C3 reading, first bullet.** Without the roster, the 27b jsonR says no to all 7 "one member among many"
   misses. With the roster it says yes to 4 of 7 (48517463, 48517567, 48517957, 48518005), and the word
   "merely" appears in 2 of 7 answers (V11). The old text said both runs described the chair as "merely CC'd".

### Remaining concerns (not corrected; the analyst's text stands)

1. **Q5 flips only the emails the models miss.** A reading of "communications between" applies to every email of
   the pattern, not just the misses. Applied the same way to all 19 25-3152 positives that match it (a member
   only as a recipient, the ACPG not named, >= 10 recipients), it changes mean elim@98 by +3.7 points, not +5.0.
   That is -4.0 on the roster runs, not -0.8, and the mean ΔAUROC is -0.0005, not +0.0056. Per model it ranges
   from -5.8 (9b lp) to +14.4 (4b lp) (V6). The Q5 numbers are also unstable. A paired, label-stratified
   bootstrap (1,000 resamples) of the 7-email flip gives 95% intervals of -1.0 to +29.7 points for the 4b lp,
   +0.2 to +15.6 for the 27b lp and +0.5 to +7.6 for the mean of 7. "+18.1 for the 4b lp" is one draw of a
   threshold set by 5 emails. The scope question is still a large lever on the main set (+3.7 vs Q4's +1.8). On
   the roster runs, Q4 (+5.2) and the consistent Q5 (-4.0) are about the same size, in opposite directions.
2. **Recipient count is a post-hoc factor.** The "one of many" category came from reading the misses, so the p
   values overstate the evidence. The cut doesn't drive the result (check 7), but the factor is confounded with
   the request (34 of the 40 positives with >= 10 recipients are 25-3152) and with each model's handling of
   25-3152.
3. **The wrong-date contrast (finding 8) has an obvious alternative.** The five 24-409 emails "inside the original
   window" are all 48-91 days outside the refined window. The five "outside both" are 421-620 days outside (V10).
   Closeness to the window and the second window are fully confounded, so this data can't separate "the model
   used the original window" from "the model is lenient near the boundary". The 04:06 reasoning supports the
   first for that one email. The 25-3152 wrong-date emails (97-273 days out, one window) get a 27b lp mean of
   0.14, between the two groups.
4. **"Misses don't track truncation" rests on 11 consensus misses.** Per model at 0.5, the 4b lp, 9b lp and d3-9b
   miss 4/38 truncated positives against 10/246, 13/246 and 9/246 untruncated (p = 0.101, 0.259, 0.0799). The
   intervals (4.2%-24.1% for 4/38) leave room for an effect as large as the point estimates in the small
   models: 10.5% truncated against 3.7%-5.3% untruncated. "No large effect found with 38 truncated positives"
   is supported; "misses don't track truncation" is not.
5. **Multiple comparisons.** C4c runs 15 tests. Of the per-model request splits, only Jev's (p = 3.89e-05)
   clears 0.05/7. The 27b lp (0.0202) and d3-9b (0.0197) do not, so "in opposite directions" rests on two
   uncorrected p values near 0.02.
6. **03:01 "likely wrong".** The inconsistency among the six Geosyntec-address emails is real (check 16). Which way
   it should be resolved is open: un-flipping 03:07 (lunch logistics) would also make the set consistent, and
   the owner's calls carry no notes. "Likely wrong" is one reader's call.
7. **Consensus at thr98 depends on the miss budget.** As V5 shows, the count of consensus misses at thr98 mostly
   reflects how many misses each in-sample threshold allows. The 0.5 and thr95 views are the better guide to
   overlap.

Reproduce the verification: `uv run python scripts/analysis/c_misses_verify.py`.
