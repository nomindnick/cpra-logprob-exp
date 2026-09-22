# Phase 1 spike results — 2026-09-22

**Setup:** `qwen3.5:4b` (Q4_K_M) via Ollama 0.32.14 chat API on the Strix Halo
box; `think: false`, `logprobs: true`, `top_logprobs: 20`, `num_predict: 1`,
`temperature: 0`. Ten hand-written emails against one made-up request
(`spike/logprob_spike.py`). One warm-up call before timing.

## Gate: passed
- Ollama returns the first-token distribution with all case/space variants
  visible. Summing `yes`/`Yes`/` yes` etc. works; the residual mass outside
  yes+no is ~0.001 on every email, so the model is answering the question.
- `<think>` appears in the distribution at ~-8.6 logprob (negligible) with
  thinking off. Ollama exposes prefill and decode durations separately.

## Scores
| id | label | score | kind |
|----|------:|------:|------|
| pos-01 | 1 | 0.950 | clear positive |
| pos-02 | 1 | 0.905 | clear positive |
| pos-04 | 1 | 0.892 | exemption-flavored (privileged) positive |
| pos-05 | 1 | 0.877 | short positive |
| pos-03 | 1 | 0.853 | indirect positive, no request keywords |
| neg-05 | 0 | 0.552 | "bridge" in unrelated (network) sense |
| neg-04 | 0 | 0.359 | keyword in newsletter |
| neg-02 | 0 | 0.288 | same people, different subject |
| neg-01 | 0 | 0.029 | different project |
| neg-03 | 0 | 0.028 | same project, outside date window |

- Ranking is perfectly separated: every positive above every negative.
- At threshold 0.5: 9/10. The one miss (neg-05, "network bridge") is the
  hardest case by design; the JSON-reasoning baseline got it right, which is
  the expected trade — reasoning helps on lexical traps, at ~5x the cost.
- The privileged email (pos-04) scores as high as the clear positives:
  no sign of conflating "sensitive" with "not responsive" (n=1).
- The date-window negative (neg-03) is the most confident "no" — the model
  is reading dates against the request, not just topic-matching.

## Latency (per email, ~250 prompt tokens)
| mode | prefill ms | decode ms | total ms | gen tokens |
|------|-----------:|----------:|---------:|-----------:|
| logprob | ~150–185 | 0 | **~340** | 1 |
| JSON generation | ~150–200 | ~1000–1400 | **~1585** | 60–85 |

- 4.6x faster end to end on this hardware. Prefill is identical in both
  modes, as predicted (H1); the entire gain is removed decode.
- ~190 ms of the logprob total is Ollama per-request overhead beyond
  prefill+decode. At ~340 ms/email single-stream that's ~10k emails/hour;
  the overhead and request concurrency (`OLLAMA_NUM_PARALLEL`) are the
  levers to investigate in phase 4, not the model.
- pos-01's 41 ms prefill on the timed run is a KV-cache hit from the warm-up
  (identical prompt). Whether the shared system+request prefix is cached
  across *different* emails is not established by this run.

## Caveats
- n=10, hand-written, one model. Nothing here is a result; it is a check
  that the mechanism works and the numbers are not absurd.
- Whether Ollama's reported logprobs are pre- or post-sampler (temperature,
  presence_penalty defaults on this model) is not verified. Temperature 0
  still yields a spread distribution, so they are not post-argmax, but a
  cross-check against llama.cpp `n_probs` on the same prompt is worth doing
  before phase 4.

## Decisions
- Primary backend: Ollama (open question in SPEC §12 resolved for phase 3–4;
  llama.cpp cross-check retained as a validation step).
- Proceed to phase 2 (source verification).
