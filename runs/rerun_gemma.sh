#!/bin/bash
# Gemma 4 reruns, single-stream with reload-on-invalid + canary guards (sticky prompt-cache corruption).
cd "$(dirname "$0")/.."
for m in gemma4:e4b gemma4:12b gemma4:e2b; do
  tag="${m//:/_}"
  echo "$(date -Is) START $m full (guarded, c=1)" >> runs/sweep.log
  rm -rf "runs/${tag}_ctx8k_v2"
  uv run python scripts/score.py --model "$m" --concurrency 1 --tag "${tag}_ctx8k_v2" >> "runs/${tag}_ctx8k_v2.log" 2>&1
  echo "$(date -Is) DONE $m" >> runs/sweep.log
done
echo "$(date -Is) GEMMA RERUN COMPLETE" >> runs/sweep.log
