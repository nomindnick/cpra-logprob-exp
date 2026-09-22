# CPRA Responsiveness Screening via First-Token Logprobs

**Status:** draft v0.1 — 2026-09-22
**Type:** exploratory experiment (not a product)

---

## 1. Problem

When a California Public Records Act (CPRA) request arrives, an agency's search is
usually a broad keyword query over email and document stores. Broad terms are
necessary to capture the full universe of responsive records, but they return a
large volume of non-responsive material that staff must sort by hand *before*
exemption review even begins. This hand-sort is the bottleneck.

Prior attempts (2025) at LLM-assisted relevance review used small local models
generating JSON (decision + confidence + reasoning). On a CPU-only laptop this
took 30–60 s per document — functionally useless at production volumes.

## 2. Idea

Skip generation. Prompt a local model with the request and the document, ask
"Is this document responsive to the request? Answer yes or no," and read the
probability mass on the *yes* vs *no* tokens from the first decoding step.

- One prefill + one decode step per document instead of prefill + ~100–300
  decode steps.
- The score is the model's actual next-token distribution, not a
  self-reported confidence.
- Runs entirely on local hardware, so sensitive records (student files,
  attorney–client material, personnel records) never leave the agency.

This is the same mechanism used by LLM-based rerankers (e.g. Qwen3-Reranker),
which is both validation of the approach and a natural baseline.

## 3. Goals and non-goals

**Goals**
1. Measure per-document latency and batch throughput of yes/no-logprob scoring
   across model sizes, quantizations, and two hardware targets.
2. Measure screening quality: recall, precision, and how observed error rate
   tracks the score (calibration / reliability).
3. Find the operating point: at ≥98% (and ≥99%) recall, what fraction of
   non-responsive documents is eliminated?
4. Identify "how small is good enough."

**Non-goals**
- Exemption / disclosability determinations. This classifies *responsiveness*
  only. Exempt records are responsive; they are a separate downstream step.
- Fine-tuning (possible follow-up; this experiment is zero-shot prompting).
- Long documents / scanned PDFs (phase 2). Phase 1 is emails only.
- A production tool. Output is a report and a reproducible harness.

## 4. Hypotheses

| # | Hypothesis | How we test it |
|---|-----------|----------------|
| H1 | Logprob scoring cuts per-doc latency by an order of magnitude vs. JSON generation on the same model/hardware, dominated by removed decode cost. | Time prefill and decode separately for both modes on identical inputs. |
| H2 | Small (≤4B) instruct models achieve ≥98% recall at a threshold that removes a substantial share (>50%) of non-responsive emails. | Precision/recall curves per model. |
| H3 | Score correlates with error rate well enough that a threshold is meaningful, even though raw P(yes) is not calibrated. | Reliability diagram; AUROC / AUPRC. |
| H4 | A purpose-built reranker (Qwen3-Reranker 0.6B/4B) matches or beats prompted general chat models at lower cost. | Same metrics, same data. |
| H5 | Quantization (Q4 vs Q8 vs bf16) shifts scores but not the ranking enough to change the operating point. | Rank correlation of scores; recall at fixed threshold. |
| H6 | Strix Halo iGPU batching gives a large throughput gain over CPU-only; the CPU laptop is viable for small models. | Docs/hour on each platform. |

## 5. Scoring method

**Prompt layout** (order matters for KV-cache reuse):

```
[system: role + task definition + output constraint]
[CPRA request text]                      ← shared prefix, cached across docs
[document: headers + body]               ← varies
[question: "Is this document responsive to the request? Answer yes or no."]
[assistant turn begins]
```

**Score** = P(yes) / (P(yes) + P(no)), where each side sums the probability of
all token variants ("yes", " yes", "Yes", " Yes", "YES", …) that the tokenizer
treats distinctly. Also log the raw P(yes), P(no), and the residual mass on
other tokens (a large residual means the prompt/model isn't behaving).

**Rules**
- Thinking / reasoning mode must be disabled (Qwen3 `/no_think` or equivalent).
  A `<think>` first token makes the score meaningless.
- Use the model's chat template. The score is read at the first assistant token.
- Prefer full-vocabulary logits (transformers, llama.cpp `n_probs`) over
  API top-k logprobs where possible. Ollama is acceptable if its logprobs
  support (believed added late 2025 — verify against installed version)
  exposes the needed tokens with `num_predict=1`.
- Same prompt text for every model; per-model differences are chat template
  only. Record prompt hash with every run.

**Baseline for H1:** the same model generating `{"responsive": ..., "confidence": ..., "reason": ...}`
(the 2025 approach), timed identically.

## 6. Metrics

**Latency / throughput** (per model × quant × hardware × backend)
- Prefill time and decode time per document, separately.
- Wall time per document (single-stream) and documents/hour (batched).
- Tokens/sec prefill. Document length distribution reported alongside.
- Text extraction / preprocessing time reported separately and *excluded*
  from model latency.

**Quality**
- Recall and precision at a sweep of thresholds; the headline is
  **non-responsive-eliminated at 98% and 99% recall**.
- AUROC, AUPRC.
- Reliability diagram: score decile vs. observed positive rate, with counts.
- Confusion matrix at the chosen operating point.
- Breakdown by negative type (cross-request real negatives vs. synthetic
  hard negatives) — these will behave differently and should be shown
  separately.

**Caveat carried into any report:** precision is computed against a
negative set that is partly synthetic, so it is a *theoretical* review-burden
reduction, not a field measurement. Recall is against real productions and is
the number that carries legal weight.

## 7. Dataset

**Unit:** one email (headers + body; attachments excluded in phase 1).
**Label:** responsive (1) / not responsive (0) to a specific request.
**Instance:** (request, email) pair.

### 7.1 Sources — to be verified before build
- **NextRequest portals** (many CA cities: Oakland, Sacramento, Long Beach,
  others). Public request text + released documents.
- **MuckRock** — API access; filterable to California / CPRA; request text
  and responsive files.
- Agencies that post CPRA logs and productions directly on their sites.

Selection criteria: request is reasonably specific; production includes
email (not just reports/contracts); at least 3–5 requests from the same
agency to enable in-agency negatives; some topical adjacency between requests.

Verification step: confirm at least two sources yield ≥ ~200 real email
positives across ≥ ~8 requests before proceeding.

### 7.2 Positives
Emails actually produced in response to the paired request. Note the known
noise: agencies sometimes over-produce marginally responsive items.

### 7.3 Negatives
1. **Cross-request (real):** production for request B, scored against request A,
   same agency. Realistic vocabulary (names, departments, projects). Only "hard"
   when A and B are topically adjacent — track adjacency as metadata.
2. **Synthetic hard negatives:** generated from real positives by a larger
   model, targeting the failure modes that keyword search actually produces:
   - same project / subject, wrong time window;
   - same people, different subject;
   - CC'd or forwarded to the relevant department, no responsive content;
   - keyword hit in a signature block, quoted thread, or newsletter;
   - same request keywords used in an unrelated sense.
   Each carries its generation recipe as metadata.

### 7.4 Synthetic positives (exemption-flavored)
Emails that *are* responsive but read as sensitive (privileged legal advice,
personnel matters, student records, deliberative drafts). Labeled **positive**.
Purpose: confirm the model doesn't conflate "sensitive" with "not responsive."

### 7.5 Synthetic-data risks
- Generator style leakage: the model may learn to detect "LLM-written" rather
  than "non-responsive." Mitigate by conditioning generation on real emails
  (rewrite / minimal edit) rather than free generation, and by reporting real
  and synthetic negatives separately.
- Circularity: don't use a candidate model as the generator.

### 7.6 Splits
No training in phase 1, so no train/test split — but hold out one or two
requests entirely for prompt development so prompt iteration doesn't overfit
to the evaluation set.

## 8. Model matrix

The matrix will be finalized at phase 4 from (a) what is installed and
(b) a check of current releases at that time — not from prior knowledge,
which is stale for this space (Qwen 4 imminent, Gemma 4 current, Meta's
"muse" line replacing Llama, etc.).

**Installed on the Strix Halo box (Ollama 0.32.14, as of 2026-09-22)** —
candidates for the small-model sweep:

| Model | Size on disk | Role |
|-------|-------------|------|
| gemma4:e2b, gemma4:e4b | 7–10 GB | smallest tier |
| granite4.1:3b | 2 GB | smallest tier |
| qwen3.5:4b | 3.4 GB | smallest tier (Qwen 4 to replace when released) |
| lfm2.5:8b, granite4.1:8b, qwen3.5:9b | 5–7 GB | mid tier |
| gemma4:12b | 7.6 GB | mid tier |
| qwen3.5:27b, gemma4:26b/31b, qwen3.6:27b | ~17 GB | upper bound for "is bigger better" |

Other installed models relevant to the pipeline, **excluded from the sweep**:
- Synthetic-data generation (§7.3–7.4): gpt-oss:120b, qwen3.5:122b,
  mistral-medium-3.5:128b — one of these; never a sweep candidate.
- OCR / extraction (§10 step 2): glm-ocr, deepseek-ocr.

Still to source: a purpose-built reranker for H4 (the current
generation of LLM-based rerankers, whichever is current at phase 4), and the
CPU-laptop subset (smallest tier only).

Quantizations: whatever the installed tags are, plus Q8/bf16 variants pulled
as needed for H5. Record the exact tag and digest with every run.

## 9. Hardware and backends

| Target | Role |
|--------|------|
| Strix Halo desktop, 128 GB unified, Radeon 8060S iGPU | main sweep; batched throughput |
| CPU-only laptop (2025 baseline machine) | comparison for H6; small models only |

Backends to evaluate (pick one primary after the spike):
- llama.cpp / `llama-server` (Vulkan on Strix Halo; CPU on laptop) — full
  logits, batching, prefix caching.
- Ollama — if logprobs are exposed; most relatable for the target audience.
- transformers (PyTorch, ROCm or CPU) — reference implementation for exact
  full-vocab scoring; may be awkward on gfx1151.

## 10. Pipeline

1. **Acquire** — download request text + productions; record source, URL,
   date, agency.
2. **Extract** — PDF/EML → text; OCR where needed; parse email headers.
   Timed separately. Store as JSONL.
3. **Label** — positives by production pairing; cross-request negatives by
   pairing; synthetic sets generated and stored with recipe metadata.
4. **Score** — for each (model, quant, backend, hardware): run every
   (request, email) pair; log score components, timings, prompt hash.
5. **Analyze** — metrics in §6; per-negative-type breakdown; plots.
6. **Report** — write-up with reliability diagram, recall-vs-eliminated
   curve, latency table.

Everything in step 4 is deterministic given (model, quant, prompt), so runs
are reproducible and resumable.

## 11. Phases

| Phase | Deliverable | Gate |
|-------|-------------|------|
| 0 | This spec | reviewed |
| 1 | Logprob extraction spike: one model, one backend, ten hand-written emails, correct yes/no mass with thinking off | scores make sense; token variants handled |
| 2 | Source verification: confirm real email productions exist at sufficient volume | ≥200 positives / ≥8 requests reachable |
| 3 | Dataset build (real + synthetic) with metadata | manual spot-check of ~50 labels |
| 4 | Model × quant × backend sweep on Strix Halo | all runs logged |
| 5 | CPU laptop comparison (subset) | |
| 6 | Analysis + write-up | |

## 12. Open questions

- ~~Which backend is primary?~~ Ollama (phase 1). Backend comparison is a
  phase 4 sub-experiment: same model, same pairs through `llama-server`
  (less per-call overhead, `--parallel` batching) and vLLM (nightly ROCm
  build exists on this machine; gfx1151 is visible to ROCm). If the gap is
  large that is a finding; if small, it validates Ollama as the practical
  choice for an agency IT shop.
- Email truncation: cap at N tokens, or drop over-length emails in phase 1?
  Proposed: cap at ~2k tokens of body, log truncation rate.
- Should the request be passed verbatim or lightly normalized (strip
  boilerplate, portal metadata)? Proposed: verbatim, with the option as an
  ablation.
- How much synthetic data relative to real? Proposed: synthetic negatives ≤
  real negatives in count so they don't dominate precision.
- Is there any source that publishes the *search terms* used, so we could
  build real keyword-hit-but-non-responsive negatives instead of synthetic
  ones? Worth an hour of looking.

## 13. Risks

- Sources turn out to be mostly scanned PDFs of reports, not emails → phase 1
  scope shrinks or shifts to a different document type.
- Ollama logprobs insufficient → fall back to llama.cpp; small loss of
  audience relatability, no loss of results.
- Models refuse / hedge instead of answering yes/no → shows up as large
  residual mass; fix by prompt, or exclude model.
- Synthetic negatives are too easy or too "LLM-flavored" → reported
  separately so the real-negative numbers stand on their own.
