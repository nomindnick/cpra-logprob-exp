#!/bin/bash
# Model sweep: full-set quality at concurrency 4, then fixed 500-pair latency subset single-stream.
# Detached: runs/sweep.sh ; progress in runs/sweep.log and runs/<tag>.log
cd "$(dirname "$0")/.."
MODELS="gemma4:e2b gemma4:e4b qwen3.5:4b qwen3.5:9b gemma4:12b"
for m in $MODELS; do
  tag="${m//:/_}"
  echo "$(date -Is) START $m full" >> runs/sweep.log
  uv run python scripts/score.py --model "$m" --concurrency 4 --tag "${tag}_ctx8k" >> "runs/${tag}_ctx8k.log" 2>&1
  echo "$(date -Is) START $m latency subset" >> runs/sweep.log
  uv run python scripts/score.py --model "$m" --pairs data/dataset/latency_subset.jsonl --concurrency 1 --tag "${tag}_lat" >> "runs/${tag}_lat.log" 2>&1
  echo "$(date -Is) DONE $m" >> runs/sweep.log
done
echo "$(date -Is) SWEEP COMPLETE" >> runs/sweep.log
