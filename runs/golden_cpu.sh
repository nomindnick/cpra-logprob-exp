#!/bin/bash
# Golden-set reference runs on the Strix Halo's CPU (num_gpu 0): the ROCm GPU path for qwen35 models
# leaks state between calls (cached) and sometimes garbles the prompt on a fresh load; the CPU path does neither.
#   runs/golden_cpu.sh start|pause|resume|status     (resumable; logprob only for now)
cd "$(dirname "$0")/.."
PLAN="qwen3.5:4b,logprob,r qwen3.5:9b,logprob,r"
cpu_run() {  # model mode tag [score.py args]
  local m="$1" mode="$2" tag="$3"; shift 3
  echo "$(date -Is) START $tag" >> runs/golden.log
  uv run python scripts/score.py --model "$m" --mode "$mode" --num-gpu 0 --extra-emails data/golden/emails.jsonl \
    --concurrency 1 --tag "$tag" "$@" >> "runs/$tag.log" 2>&1
  echo "$(date -Is) DONE $tag" >> runs/golden.log
}
cpu_chain() {
  for item in $PLAN; do
    IFS=, read -r m mode roster <<< "$item"
    t="golden_${m//:/_}_${mode}_ngl0"
    cpu_run "$m" "$mode" "$t" --pairs data/golden/pairs.jsonl
    [ "$roster" = r ] && cpu_run "$m" "$mode" "${t}_roster" --pairs data/golden/pairs_25-3152.jsonl --roster data/golden/roster_context.txt
  done
  echo "$(date -Is) CPU COMPLETE" >> runs/golden.log
}
case "$1" in
  start|resume)
    if pgrep -f "[s]core.py" >/dev/null; then echo "a scoring run is already using the GPU:"; pgrep -fa "[s]core.py" | head -1; exit 1; fi
    export -f cpu_run cpu_chain; export PLAN
    setsid nohup bash -c cpu_chain > /dev/null 2>&1 < /dev/null &
    echo "$(date -Is) START/RESUME cpu chain" >> runs/golden.log
    echo "launched cpu chain"; ;;
  pause)
    pkill -f "bash -c [c]pu_chain"; pkill -f "[s]core.py.*--tag golden_.*_ngl0"
    sleep 2; for m in qwen3.5:4b qwen3.5:9b qwen3.8:27b; do ollama stop "$m" 2>/dev/null; done
    echo "$(date -Is) PAUSED cpu chain" >> runs/golden.log
    echo "paused; GPU freed. resume with: runs/golden_cpu.sh resume"; ;;
  status)
    if pgrep -f "[s]core.py.*--tag golden_.*_ngl0" >/dev/null; then echo "running: $(pgrep -fa '[s]core.py.*--tag golden_' | grep -o 'tag [^ ]*' | head -1)"; else echo "not running"; fi
    for item in $PLAN; do
      IFS=, read -r m mode roster <<< "$item"; t="golden_${m//:/_}_${mode}_ngl0"
      for tt in "$t" $([ "$roster" = r ] && echo "${t}_roster"); do
        n=$([ -f "runs/$tt/scores.jsonl" ] && wc -l < "runs/$tt/scores.jsonl" || echo 0)
        echo "  $tt: $n/$([[ $tt == *_roster ]] && echo 249 || echo 496)"
      done
    done
    tail -1 runs/golden.log ;;
  *) echo "usage: $0 start|pause|resume|status"; exit 1 ;;
esac
