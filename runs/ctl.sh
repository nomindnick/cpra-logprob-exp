#!/bin/bash
# Pausable model run:  runs/ctl.sh start|pause|resume|status <model>
# The scorer is resumable (already-scored pairs are skipped), so pause = kill + free the GPU,
# resume = relaunch the same chain. Chain = full set at concurrency 4, then 500-pair subset single-stream.
cd "$(dirname "$0")/.."
cmd="$1"; model="$2"; tag="${model//:/_}"
chain() {
  echo "$(date -Is) START/RESUME $model" >> runs/sweep.log
  uv run python scripts/score.py --model "$model" --concurrency 4 --tag "${tag}_ctx8k" >> "runs/${tag}_ctx8k.log" 2>&1
  uv run python scripts/score.py --model "$model" --pairs data/dataset/latency_subset.jsonl --concurrency 1 --tag "${tag}_lat" >> "runs/${tag}_lat.log" 2>&1
  echo "$(date -Is) DONE $model" >> runs/sweep.log
}
case "$cmd" in
  start|resume)
    if pgrep -f "[s]core.py --model $model" >/dev/null; then echo "already running"; exit 1; fi
    export -f chain; export model tag
    setsid nohup bash -c chain > /dev/null 2>&1 < /dev/null &
    echo "launched $model"; ;;
  pause)
    pkill -f "bash -c [c]hain"; pkill -f "[s]core.py --model $model"
    sleep 2; ollama stop "$model" 2>/dev/null
    echo "$(date -Is) PAUSED $model" >> runs/sweep.log
    echo "paused; GPU freed. resume with: runs/ctl.sh resume $model"; ;;
  status)
    if pgrep -f "[s]core.py --model $model" >/dev/null; then pgrep -fa "[s]core.py --model $model" | head -1; else echo "not running"; fi
    for f in "runs/${tag}_ctx8k.log" "runs/${tag}_lat.log"; do [ -f "$f" ] && echo "$f: $(tail -1 "$f")"; done
    [ -f "runs/${tag}_ctx8k/scores.jsonl" ] && echo "scored: $(wc -l < runs/${tag}_ctx8k/scores.jsonl)/9848 full, $( [ -f runs/${tag}_lat/scores.jsonl ] && wc -l < runs/${tag}_lat/scores.jsonl || echo 0)/500 subset" ;;
  *) echo "usage: $0 start|pause|resume|status <model>"; exit 1 ;;
esac
