#!/bin/bash
# Reinstate 24-409 synthetic 07:09 as a hard negative (owner call 2026-11-11: "RDF" meaning refuse-derived fuel is
# not responsive, since the request means the Regional Decarbonization Framework; 07:09 had been dropped 2026-10-31
# as an arguable keyword hit). Rebuilds the golden set from data/golden/work/adjudications.json, then scores the one
# new pair on every full-set run that lacks it, with that run's original settings. All scorers resume, so only 07:09
# is scored. Roster runs (25-3152 only) and the fresh60 checks (first 60 pairs) don't include it.
# Waits until Ollama is empty and no other job (the legtracker bakeoff) is running for 5 straight minutes before
# touching the golden set, and unloads each model after use; the bakeoff stops itself if Ollama holds a model.
#   runs/golden_0709.sh      (resumable; rerun after an interruption)
cd "$(dirname "$0")/.."
LOG=runs/golden.log
foreign() { pgrep -f "[1]8_model_run.py|[b]akeoff/pass" >/dev/null; }
busy() { foreign || [ -n "$(ollama ps | awk 'NR>1')" ]; }
quiet=0; waited=0
while [ $quiet -lt 5 ]; do
  if busy; then quiet=0; else quiet=$((quiet + 1)); fi
  sleep 60; waited=$((waited + 1))
  [ $waited -ge 600 ] && { echo "$(date -Is) 07:09 GAVE UP: GPU busy for 10 h" >> $LOG; exit 3; }
done
echo "$(date -Is) START 07:09 chain (waited $waited min)" >> $LOG
uv run python scripts/build_golden.py >> runs/golden_0709.log 2>&1 || { echo "build_golden failed" >> $LOG; exit 1; }
yield() { while foreign; do sleep 60; done; }
sc() {  # tag [score.py args]
  local tag="$1"; shift; yield
  uv run python scripts/score.py --pairs data/golden/pairs.jsonl --extra-emails data/golden/emails.jsonl \
    --concurrency 1 --tag "$tag" "$@" >> "runs/$tag.log" 2>&1
  echo "$(date -Is) 07:09 $tag exit $?" >> $LOG
}
s1() {  # tag [score_systemone.py args]
  local tag="$1"; shift; yield
  uv run python scripts/score_systemone.py --pairs data/golden/pairs.jsonl --extra-emails data/golden/emails.jsonl \
    --tag "$tag" "$@" >> "runs/$tag.log" 2>&1
  echo "$(date -Is) 07:09 $tag exit $?" >> $LOG
}
s1 golden_jev-1.14.0_noul_p2 --model jev-1.14.0
for m in qwen3.5:4b qwen3.5:9b; do
  t="golden_${m//:/_}"
  sc "${t}_logprob_p2" --model "$m" --mode logprob --num-batch 8192
  sc "${t}_logprob_p1o40" --model "$m" --mode logprob --num-batch 8192 --prompt 1
  sc "${t}_json_p2" --model "$m" --mode json --num-batch 8192 --schema
  sc "${t}_json_reason_p2" --model "$m" --mode json_reason --num-batch 8192
  sc "${t}_logprob_p2db" --model "$m" --mode logprob
  sc "${t}_logprob_p2dbf" --model "$m" --mode logprob --fresh
  ollama stop "$m"
done
t=golden_qwen3.8_27b
sc "${t}_logprob_p2" --model qwen3.8:27b --mode logprob
sc "${t}_logprob_p1o40" --model qwen3.8:27b --mode logprob --prompt 1
sc "${t}_json_p2" --model qwen3.8:27b --mode json
sc "${t}_json_reason_p2" --model qwen3.8:27b --mode json_reason
ollama stop qwen3.8:27b
for s in 4b 9b 27b; do
  s1 "golden_d3-ctx8k_${s}_noul_p2" --base-url http://localhost:11434 --model "d3-ctx8k:$s"
  ollama stop "d3-ctx8k:$s"
done
echo "$(date -Is) 07:09 COMPLETE" >> $LOG
