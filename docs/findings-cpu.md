# CPU laptop vs Strix Halo — qwen3.5:4b (H6)

**Date:** 2026-10-01 · **Status:** preliminary; raw (unadjudicated) labels
**Runs:** `runs/qwen3.5_4b_lat` (Strix), `runs/qwen3.5_4b_lat_cpu` (CPU, 500 pairs, power-saver),
`runs/qwen3.5_4b_lat_cpu_perf` (CPU, 50-pair slice, performance profile)
**Compare:** `uv run python scripts/compare.py runs/qwen3.5_4b_lat runs/qwen3.5_4b_lat_cpu`

CPU box: Framework 13, Ryzen 7 7840U, 30 GB, Ollama 0.33.3, `100% CPU` (no iGPU offload),
8 threads. Same model digest, prompt hash, `num_ctx=8192`, single-stream. Strix runs were on
Ollama 0.32.14, so backend and version are confounded.

`data/dataset/latency_slice50.jsonl` is every 10th pair of the latency subset (12–13 per
request, median 1,674 prompt tokens; power-saver median on it 21.5 s vs 20.9 s on all 500).

## 1. Latency

| | median total_ms | p90 | prefill tok/s |
|---|---|---|---|
| Strix Halo (50-pair slice) | 988 | 1,829 | 2,098 |
| CPU, power-saver (slice) | 21,464 | 50,907 | 71 |
| CPU, performance (slice) | **12,902** | 27,970 | **123** |

The 500-pair power-saver run gave 20,902 ms median (21.5× Strix); it was
accidentally run on the `power-saver` profile. On `performance` the CPU is 1.7× faster
(1.45–1.75× in every prompt-length bucket), i.e. **~13× slower than Strix**. Entirely
prefill-bound and linear in length: 7.5 s (<1k tok) to 32 s (>3k tok) on performance.
A full 9,848-pair run would take ~40 h.

## 2. Ranking quality is unchanged (500 pairs, power-saver)

| | AUROC | AUPRC | eliminated @98% | @95% |
|---|---|---|---|---|
| Strix | 0.942 | 0.887 | 50.3% | 65.4% |
| CPU | 0.945 | 0.894 | 54.2% | 60.9% |

Differences are within noise (98% recall on 116 positives = at most 2 misses).

## 3. Individual scores move — and the CPU is not run-to-run deterministic

Strix vs CPU on 500 pairs: mean |Δ| 0.050 (median 0.026, max 0.64); 70 pairs > 0.1,
10 > 0.3; first token differs on 21/500; 44–49 pairs cross a 98% threshold. Movement grows
with length (mean |Δ| 0.033 under 1k tokens, 0.111 over 3k; moved pairs median 2,400 tokens,
31% truncated) — the same pattern as concurrency in `findings-sweep.md` §5.

The two CPU runs (same machine, version, model, threads, temperature 0; only the power
profile differed) also disagree on the 50-pair slice:

| same 50 pairs | mean \|Δ\| | > 0.05 | > 0.1 | max |
|---|---|---|---|---|
| CPU vs CPU (repeat) | 0.025 | 7 | 1 | 0.13 |
| Strix vs CPU power-saver | 0.046 | 15 | 6 | 0.34 |
| Strix vs CPU performance | 0.040 | 10 | 3 | 0.34 |

About half the cross-machine movement is CPU run-to-run noise. The Strix repeat-run noise
floor is unmeasured — rerun `latency_slice50.jsonl` there to get it.

**Implication:** ranking transfers across hardware; a fixed threshold does not, and even on
one machine a threshold needs margin for run-to-run variation on long emails.
