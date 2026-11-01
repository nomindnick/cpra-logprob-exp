#!/bin/bash
# Golden-set reruns with prompt 2 (score.py PROMPT = 2: the named-correspondent rule) and render 2 (Bcc and
# Delivered-To), on the 2026-10-31 labels: every model and mode, each followed by the 25-3152 roster ablation.
# Settings match the runs in the prompt-1 tables: qwen3.5 4b/9b at --num-batch 8192 (cached = fresh there,
# docs/findings-golden.md §7) with --schema in json mode; the 27b at the default batch, no --schema (its
# prompt-1 json run had none). The 27b jsonR runs cached this time (prompt 1 ran it --fresh by accident).
#   runs/golden_p2.sh start|pause|resume|status     (resumable)
cd "$(dirname "$0")/.."
PLAN="qwen3.8:27b,logprob qwen3.5:9b,logprob qwen3.5:4b,logprob \
qwen3.8:27b,json qwen3.5:9b,json qwen3.5:4b,json \
qwen3.8:27b,json_reason qwen3.5:9b,json_reason qwen3.5:4b,json_reason"
p2_run() {  # model mode tag [score.py args]
  local m="$1" mode="$2" tag="$3"; shift 3
  local opts=""
  [ "$m" != qwen3.8:27b ] && opts="--num-batch 8192 $([ "$mode" = json ] && echo --schema)"
  echo "$(date -Is) START $tag" >> runs/golden.log
  uv run python scripts/score.py --model "$m" --mode "$mode" $opts --extra-emails data/golden/emails.jsonl \
    --concurrency 1 --tag "$tag" "$@" >> "runs/$tag.log" 2>&1
  echo "$(date -Is) DONE $tag" >> runs/golden.log
}
p2_chain() {
  for item in $PLAN; do
    IFS=, read -r m mode <<< "$item"
    t="golden_${m//:/_}_${mode}_p2"
    p2_run "$m" "$mode" "$t" --pairs data/golden/pairs.jsonl
    p2_run "$m" "$mode" "${t}_roster" --pairs data/golden/pairs_25-3152.jsonl --roster data/golden/roster_context.txt
  done
  echo "$(date -Is) P2 COMPLETE" >> runs/golden.log
}
case "$1" in
  start|resume)
    if pgrep -f "[s]core.py" >/dev/null; then echo "a scoring run is already using the GPU:"; pgrep -fa "[s]core.py" | head -1; exit 1; fi
    export -f p2_run p2_chain; export PLAN
    setsid nohup bash -c p2_chain > /dev/null 2>&1 < /dev/null &
    echo "$(date -Is) START/RESUME p2 chain" >> runs/golden.log
    echo "launched p2 chain"; ;;
  pause)
    pkill -f "bash -c [p]2_chain"; pkill -f "[s]core.py.*--tag golden_.*_p2"
    sleep 2; for m in qwen3.5:4b qwen3.5:9b qwen3.8:27b; do ollama stop "$m" 2>/dev/null; done
    echo "$(date -Is) PAUSED p2 chain" >> runs/golden.log
    echo "paused; GPU freed. resume with: runs/golden_p2.sh resume"; ;;
  status)
    if pgrep -f "[s]core.py.*--tag golden_.*_p2" >/dev/null; then echo "running: $(pgrep -fa '[s]core.py.*--tag golden_' | grep -o 'tag [^ ]*' | head -1)"; else echo "not running"; fi
    for item in $PLAN; do
      IFS=, read -r m mode <<< "$item"; t="golden_${m//:/_}_${mode}_p2"
      for tt in "$t" "${t}_roster"; do
        n=$([ -f "runs/$tt/scores.jsonl" ] && wc -l < "runs/$tt/scores.jsonl" || echo 0)
        echo "  $tt: $n/$([[ $tt == *_roster ]] && echo 249 || echo 495)"
      done
    done
    tail -1 runs/golden.log ;;
  *) echo "usage: $0 start|pause|resume|status"; exit 1 ;;
esac
