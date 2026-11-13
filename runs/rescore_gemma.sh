#!/bin/bash
cd "$(dirname "$0")/.."
for m in gemma4:e2b gemma4:e4b gemma4:12b; do
  tag="${m//:/_}"
  uv run python scripts/score.py --model "$m" --concurrency 1 --tag "${tag}_ctx8k" --rescore-invalid >> "runs/${tag}_ctx8k.log" 2>&1
  uv run python scripts/score.py --model "$m" --pairs data/dataset/latency_subset.jsonl --concurrency 1 --tag "${tag}_lat" --rescore-invalid >> "runs/${tag}_lat.log" 2>&1
done
echo "$(date -Is) RESCORE COMPLETE" >> runs/sweep.log
