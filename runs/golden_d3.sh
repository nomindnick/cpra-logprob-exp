#!/bin/bash
# Golden set on the d3 decision models (vLLM Semantic Router; Qwen3.5-4B / Qwen3.5-9B / Qwen3.8-27B bases, the
# same as the stock Qwen runs) through Ollama's /v1/systemone, with the same state and Noul question as the Jev
# run (scripts/score_systemone.py). d3-ctx8k:* are the library d3 packages (num_ctx 4096, num_batch 4096) with
# num_ctx 8192 and num_batch 8192: d3's attention is noncausal, so the whole prompt has to fit in one batch, and
# 56 golden/roster prompts exceed 4,096 tokens. Each size: golden pairs and the 25-3152 roster ablation with the model
# loaded, then a --fresh identity check (unload after every request) on the first 60 golden / 30 roster pairs.
#   runs/golden_d3.sh start|pause|resume|status     (resumable)
cd "$(dirname "$0")/.."
PLAN="4b 9b 27b"
d3_run() {  # model tag [score_systemone.py args]
  local m="$1" tag="$2"; shift 2
  echo "$(date -Is) START $tag" >> runs/golden.log
  uv run python scripts/score_systemone.py --base-url http://localhost:11434 --model "$m" \
    --extra-emails data/golden/emails.jsonl --tag "$tag" "$@" >> "runs/$tag.log" 2>&1
  echo "$(date -Is) DONE $tag" >> runs/golden.log
}
d3_chain() {
  for s in $PLAN; do
    m="d3-ctx8k:$s"; t="golden_d3-ctx8k_${s}_noul_p2"
    d3_run "$m" "$t" --pairs data/golden/pairs.jsonl
    d3_run "$m" "${t}_roster" --pairs data/golden/pairs_25-3152.jsonl --roster data/golden/roster_context.txt
    d3_run "$m" "${t}_fresh60" --fresh --limit 60 --pairs data/golden/pairs.jsonl
    d3_run "$m" "${t}_roster_fresh30" --fresh --limit 30 --pairs data/golden/pairs_25-3152.jsonl \
      --roster data/golden/roster_context.txt
    ollama stop "$m" 2>/dev/null
  done
  echo "$(date -Is) D3 COMPLETE" >> runs/golden.log
}
case "$1" in
  start|resume)
    if pgrep -f "[s]core(_systemone)?.py" >/dev/null; then echo "a scoring run is already using the GPU:"; pgrep -fa "[s]core(_systemone)?.py" | head -1; exit 1; fi
    export -f d3_run d3_chain; export PLAN
    setsid nohup bash -c d3_chain > /dev/null 2>&1 < /dev/null &
    echo "$(date -Is) START/RESUME d3 chain" >> runs/golden.log
    echo "launched d3 chain"; ;;
  pause)
    pkill -f "bash -c [d]3_chain"; pkill -f "[s]core_systemone.py.*--tag golden_d3"
    sleep 2; for s in $PLAN; do ollama stop "d3-ctx8k:$s" 2>/dev/null; done
    echo "$(date -Is) PAUSED d3 chain" >> runs/golden.log
    echo "paused; GPU freed. resume with: runs/golden_d3.sh resume"; ;;
  status)
    if pgrep -f "[s]core_systemone.py.*--tag golden_d3" >/dev/null; then echo "running: $(pgrep -fa '[s]core_systemone.py.*--tag golden_d3' | grep -o 'tag [^ ]*' | head -1)"; else echo "not running"; fi
    for s in $PLAN; do
      t="golden_d3-ctx8k_${s}_noul_p2"
      for tt in "$t:495" "${t}_roster:249" "${t}_fresh60:60" "${t}_roster_fresh30:30"; do
        n=$([ -f "runs/${tt%:*}/scores.jsonl" ] && wc -l < "runs/${tt%:*}/scores.jsonl" || echo 0)
        echo "  ${tt%:*}: $n/${tt#*:}"
      done
    done
    tail -1 runs/golden.log ;;
  *) echo "usage: $0 start|pause|resume|status"; exit 1 ;;
esac
