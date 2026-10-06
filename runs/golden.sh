#!/bin/bash
# Golden-set runs on Strix Halo (SPEC §14):  runs/golden.sh start|pause|resume|status
# Logprob runs for every model first, then JSON-verdict runs; each followed by the 25-3152
# roster ablation. All single-stream. The scorer is resumable (already-scored pairs are
# skipped), so pause = kill + free the GPU, resume = relaunch the same chain.
cd "$(dirname "$0")/.."
MODELS="qwen3.5:4b qwen3.5:9b qwen3.8:27b"
golden_run() {  # model mode tag [score.py args]
  local m="$1" mode="$2" tag="$3"; shift 3
  echo "$(date -Is) START $tag" >> runs/golden.log
  uv run python scripts/score.py --model "$m" --mode "$mode" --extra-emails data/golden/emails.jsonl \
    --concurrency 1 --tag "$tag" "$@" >> "runs/$tag.log" 2>&1
  echo "$(date -Is) DONE $tag" >> runs/golden.log
}
golden_chain() {
  for mode in logprob json; do
    for m in $MODELS; do
      t="golden_${m//:/_}_$mode"
      golden_run "$m" "$mode" "$t" --pairs data/golden/pairs.jsonl
      golden_run "$m" "$mode" "${t}_roster" --pairs data/golden/pairs_25-3152.jsonl --roster data/golden/roster_context.txt
    done
  done
  echo "$(date -Is) GOLDEN COMPLETE" >> runs/golden.log
}
case "$1" in
  start|resume)
    if pgrep -f "[s]core.py" >/dev/null; then echo "a scoring run is already using the GPU:"; pgrep -fa "[s]core.py" | head -1; exit 1; fi
    export -f golden_run golden_chain; export MODELS
    setsid nohup bash -c golden_chain > /dev/null 2>&1 < /dev/null &
    echo "$(date -Is) START/RESUME chain" >> runs/golden.log
    echo "launched golden chain"; ;;
  pause)
    pkill -f "bash -c [g]olden_chain"; pkill -f "[s]core.py.*--tag golden_"
    sleep 2; for m in $MODELS; do ollama stop "$m" 2>/dev/null; done
    echo "$(date -Is) PAUSED" >> runs/golden.log
    echo "paused; GPU freed. resume with: runs/golden.sh resume"; ;;
  status)
    if pgrep -f "[s]core.py.*--tag golden_" >/dev/null; then echo "running: $(pgrep -fa '[s]core.py.*--tag golden_' | grep -o 'tag [^ ]*' | head -1)"; else echo "not running"; fi
    for mode in logprob json; do for m in $MODELS; do for suf in "" _roster; do
      t="golden_${m//:/_}_$mode$suf"; n=$([ -f "runs/$t/scores.jsonl" ] && wc -l < "runs/$t/scores.jsonl" || echo 0)
      echo "  $t: $n/$([ -z "$suf" ] && echo 496 || echo 249)"
    done; done; done
    tail -1 runs/golden.log 2>/dev/null ;;
  *) echo "usage: $0 start|pause|resume|status"; exit 1 ;;
esac
