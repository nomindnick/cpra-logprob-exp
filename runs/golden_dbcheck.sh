#!/bin/bash
# Default-batch recheck on Ollama 0.40.13 (docs/findings-golden.md §7): qwen3.5 4b/9b logprob at
# Ollama's default batch size, cached and --fresh, each with the 25-3152 roster ablation. Compare against the
# batch-8192 prompt-2 runs (golden_*_logprob_p2*): if the ROCm fault is fixed upstream, the cached runs match
# within noise with no excess above 2,048 prompt tokens, and the 4b/9b can go back to the default batch (prefix cache).
#   runs/golden_dbcheck.sh start|pause|resume|status     (resumable)
cd "$(dirname "$0")/.."
PLAN="qwen3.5:4b,db qwen3.5:9b,db qwen3.5:4b,dbf qwen3.5:9b,dbf"
db_run() {  # model tag [score.py args]
  local m="$1" tag="$2"; shift 2
  echo "$(date -Is) START $tag" >> runs/golden.log
  uv run python scripts/score.py --model "$m" --mode logprob --extra-emails data/golden/emails.jsonl \
    --concurrency 1 --tag "$tag" "$@" >> "runs/$tag.log" 2>&1
  echo "$(date -Is) DONE $tag" >> runs/golden.log
}
db_chain() {
  for item in $PLAN; do
    IFS=, read -r m v <<< "$item"
    t="golden_${m//:/_}_logprob_p2${v}"
    f=$([ "$v" = dbf ] && echo --fresh)
    db_run "$m" "$t" $f --pairs data/golden/pairs.jsonl
    db_run "$m" "${t}_roster" $f --pairs data/golden/pairs_25-3152.jsonl --roster data/golden/roster_context.txt
  done
  echo "$(date -Is) DBCHECK COMPLETE" >> runs/golden.log
}
case "$1" in
  start|resume)
    if pgrep -f "[s]core.py" >/dev/null; then echo "a scoring run is already using the GPU:"; pgrep -fa "[s]core.py" | head -1; exit 1; fi
    export -f db_run db_chain; export PLAN
    setsid nohup bash -c db_chain > /dev/null 2>&1 < /dev/null &
    echo "$(date -Is) START/RESUME dbcheck chain" >> runs/golden.log
    echo "launched dbcheck chain"; ;;
  pause)
    pkill -f "bash -c [d]b_chain"; pkill -f "[s]core.py.*--tag golden_.*_p2dbf?"
    sleep 2; for m in qwen3.5:4b qwen3.5:9b; do ollama stop "$m" 2>/dev/null; done
    echo "$(date -Is) PAUSED dbcheck chain" >> runs/golden.log
    echo "paused; GPU freed. resume with: runs/golden_dbcheck.sh resume"; ;;
  status)
    if pgrep -f "[s]core.py.*--tag golden_.*_p2db" >/dev/null; then echo "running: $(pgrep -fa '[s]core.py.*--tag golden_' | grep -o 'tag [^ ]*' | head -1)"; else echo "not running"; fi
    for item in $PLAN; do
      IFS=, read -r m v <<< "$item"; t="golden_${m//:/_}_logprob_p2${v}"
      for tt in "$t" "${t}_roster"; do
        n=$([ -f "runs/$tt/scores.jsonl" ] && wc -l < "runs/$tt/scores.jsonl" || echo 0)
        echo "  $tt: $n/$([[ $tt == *_roster ]] && echo 249 || echo 495)"
      done
    done
    tail -1 runs/golden.log ;;
  *) echo "usage: $0 start|pause|resume|status"; exit 1 ;;
esac
