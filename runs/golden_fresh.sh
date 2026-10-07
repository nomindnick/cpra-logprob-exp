#!/bin/bash
# Golden-set reruns with no prompt-cache carry-over (score.py --fresh: model unloaded before every call),
# after Ollama 0.32.14 was found leaking the previous prompt's content on qwen35 models.
#   runs/golden_fresh.sh start|pause|resume|status
# Order: clean logprob for 4b/9b (+ roster) and a 27b check; reasoning-first JSON for all three (+ roster);
# clean JSON for 4b/9b (+ roster). Resumable like golden.sh.
# Superseded: at the default batch size, a freshly loaded qwen3.5 4b/9b garbles prompts over 2,048 tokens, so
# these runs are worse than the cached ones (docs/findings-golden.md §7). Kept as evidence; clean runs come from
# runs/golden_clean.sh (--num-batch 8192). The 27b runs here are fine.
cd "$(dirname "$0")/.."
PLAN="qwen3.5:4b,logprob,r qwen3.5:9b,logprob,r qwen3.8:27b,logprob,- \
qwen3.5:4b,json_reason,r qwen3.5:9b,json_reason,r qwen3.8:27b,json_reason,r \
qwen3.5:4b,json,r qwen3.5:9b,json,r"
fresh_run() {  # model mode tag [score.py args]
  local m="$1" mode="$2" tag="$3"; shift 3
  echo "$(date -Is) START $tag" >> runs/golden.log
  uv run python scripts/score.py --model "$m" --mode "$mode" --fresh --extra-emails data/golden/emails.jsonl \
    --concurrency 1 --tag "$tag" "$@" >> "runs/$tag.log" 2>&1
  echo "$(date -Is) DONE $tag" >> runs/golden.log
}
fresh_chain() {
  for item in $PLAN; do
    IFS=, read -r m mode roster <<< "$item"
    t="golden_${m//:/_}_${mode}_fresh"
    fresh_run "$m" "$mode" "$t" --pairs data/golden/pairs.jsonl
    [ "$roster" = r ] && fresh_run "$m" "$mode" "${t}_roster" --pairs data/golden/pairs_25-3152.jsonl --roster data/golden/roster_context.txt
  done
  echo "$(date -Is) FRESH COMPLETE" >> runs/golden.log
}
case "$1" in
  start|resume)
    if pgrep -f "[s]core.py" >/dev/null; then echo "a scoring run is already using the GPU:"; pgrep -fa "[s]core.py" | head -1; exit 1; fi
    export -f fresh_run fresh_chain; export PLAN
    setsid nohup bash -c fresh_chain > /dev/null 2>&1 < /dev/null &
    echo "$(date -Is) START/RESUME fresh chain" >> runs/golden.log
    echo "launched fresh chain"; ;;
  pause)
    pkill -f "bash -c [f]resh_chain"; pkill -f "[s]core.py.*--tag golden_.*_fresh"
    sleep 2; for m in qwen3.5:4b qwen3.5:9b qwen3.8:27b; do ollama stop "$m" 2>/dev/null; done
    echo "$(date -Is) PAUSED fresh chain" >> runs/golden.log
    echo "paused; GPU freed. resume with: runs/golden_fresh.sh resume"; ;;
  status)
    if pgrep -f "[s]core.py.*--tag golden_.*_fresh" >/dev/null; then echo "running: $(pgrep -fa '[s]core.py.*--tag golden_' | grep -o 'tag [^ ]*' | head -1)"; else echo "not running"; fi
    for item in $PLAN; do
      IFS=, read -r m mode roster <<< "$item"; t="golden_${m//:/_}_${mode}_fresh"
      for tt in "$t" $([ "$roster" = r ] && echo "${t}_roster"); do
        n=$([ -f "runs/$tt/scores.jsonl" ] && wc -l < "runs/$tt/scores.jsonl" || echo 0)
        echo "  $tt: $n/$([[ $tt == *_roster ]] && echo 249 || echo 496)"
      done
    done
    tail -1 runs/golden.log ;;
  *) echo "usage: $0 start|pause|resume|status"; exit 1 ;;
esac
