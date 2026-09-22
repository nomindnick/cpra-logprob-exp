#!/bin/bash
# detached launcher: runs/launch.sh <model> ; log in runs/<tag>.log
cd "$(dirname "$0")/.."
tag="${1//:/_}"
setsid nohup uv run python scripts/score.py --model "$1" >> "runs/$tag.log" 2>&1 < /dev/null &
echo "launched $1 pid $!"
