#!/bin/bash
# Golden-set runs in the clean GPU setting for qwen3.5 4b/9b: --fresh (unload before every call: no
# cross-request state leak) + --num-batch 8192 (prefill in one batch: no state corruption across 2,048-token
# batches). Verified against CPU reference runs (num_gpu 0). json mode adds --schema.
#   runs/golden_clean.sh start|pause|resume|status     (resumable)
cd "$(dirname "$0")/.."
PLAN="qwen3.5:9b,logprob,r qwen3.5:4b,logprob,r qwen3.5:4b,json,r qwen3.5:9b,json,r qwen3.5:4b,json_reason,r qwen3.5:9b,json_reason,r"
clean_run() {  # model mode tag [score.py args]
  local m="$1" mode="$2" tag="$3"; shift 3
  echo "$(date -Is) START $tag" >> runs/golden.log
  uv run python scripts/score.py --model "$m" --mode "$mode" --fresh --num-batch 8192 $([ "$mode" = json ] && echo --schema) --extra-emails data/golden/emails.jsonl \
    --concurrency 1 --tag "$tag" "$@" >> "runs/$tag.log" 2>&1
  echo "$(date -Is) DONE $tag" >> runs/golden.log
}
clean_chain() {
  for item in $PLAN; do
    IFS=, read -r m mode roster <<< "$item"
    t="golden_${m//:/_}_${mode}_clean"
    clean_run "$m" "$mode" "$t" --pairs data/golden/pairs.jsonl
    [ "$roster" = r ] && clean_run "$m" "$mode" "${t}_roster" --pairs data/golden/pairs_25-3152.jsonl --roster data/golden/roster_context.txt
  done
  echo "$(date -Is) CLEAN COMPLETE" >> runs/golden.log
}
case "$1" in
  start|resume)
    if pgrep -f "[s]core.py" >/dev/null; then echo "a scoring run is already using the GPU:"; pgrep -fa "[s]core.py" | head -1; exit 1; fi
    export -f clean_run clean_chain; export PLAN
    setsid nohup bash -c clean_chain > /dev/null 2>&1 < /dev/null &
    echo "$(date -Is) START/RESUME clean chain" >> runs/golden.log
    echo "launched clean chain"; ;;
  pause)
    pkill -f "bash -c [c]lean_chain"; pkill -f "[s]core.py.*--tag golden_.*_clean"
    sleep 2; for m in qwen3.5:4b qwen3.5:9b qwen3.8:27b; do ollama stop "$m" 2>/dev/null; done
    echo "$(date -Is) PAUSED clean chain" >> runs/golden.log
    echo "paused; GPU freed. resume with: runs/golden_clean.sh resume"; ;;
  status)
    if pgrep -f "[s]core.py.*--tag golden_.*_clean" >/dev/null; then echo "running: $(pgrep -fa '[s]core.py.*--tag golden_' | grep -o 'tag [^ ]*' | head -1)"; else echo "not running"; fi
    for item in $PLAN; do
      IFS=, read -r m mode roster <<< "$item"; t="golden_${m//:/_}_${mode}_clean"
      for tt in "$t" $([ "$roster" = r ] && echo "${t}_roster"); do
        n=$([ -f "runs/$tt/scores.jsonl" ] && wc -l < "runs/$tt/scores.jsonl" || echo 0)
        echo "  $tt: $n/$([[ $tt == *_roster ]] && echo 249 || echo 496)"
      done
    done
    tail -1 runs/golden.log ;;
  *) echo "usage: $0 start|pause|resume|status"; exit 1 ;;
esac
