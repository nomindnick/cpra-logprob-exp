"""Layer-looping sweep: search block positions on one request, validate on the other.

  loop/.venv/bin/python loop/sweep.py                                   # Qwen3.5-4B -> loop/runs/sweep4b
  loop/.venv/bin/python loop/sweep.py --model Qwen/Qwen3.5-9B --name sweep9b --confirm 12:16,14:16

Resumable; log in loop/runs/<name>/sweep.log.

Phase 1 (search): every block in GRID, plus the stock order at the start and the end of the session
(scores are deterministic, so the second stock pass only shows whether the box slowed down over the
session), on request SEARCH only.
Phase 2 (validate): the stock order, the --confirm blocks and the TOP_N blocks by AUROC on SEARCH, scored on
request HOLDOUT. The selection rule is fixed here, before any block is chosen: rank looped blocks by AUROC
on SEARCH, ties to the block with fewer layer passes; no other look at HOLDOUT.

--confirm names blocks fixed before the sweep starts (for the 9B: the two blocks that held their direction
on the 4B's held-out request). They are scored on HOLDOUT whatever their search rank, and because nothing
in this sweep chose them, their result over both requests together is a clean test.

A pair with no score (neither yes nor no in the top 20 tokens) counts as score 1.0 everywhere in the sweep:
an email the screen cannot score cannot be eliminated and goes to review. A block that never answers
therefore gets AUROC 0.5. (Added after the first 4B launch stopped on block 0:4, which answers on no pair.)

Qwen3.5-4B and -9B both have 32 layers in groups of four: three linear-attention layers, then one
full-attention layer (full attention at 3, 7, ..., 31). a:b means layers a..b-1.
"""
import argparse
import json
import pathlib
import sys
import traceback

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import score_hf as H  # noqa: E402
from analyze import auroc  # noqa: E402  (scripts/ is on the path via score_hf)

SEARCH, HOLDOUT, TOP_N = "24-409", "25-3152", 3
GRID = (
    [f"{a}:{a + 4}" for a in range(0, 32, 4)]             # one group, across the whole depth (0:4 and 28:32 are the edge controls)
    + [f"{l}:{l + 1}" for l in (9, 11, 13, 15, 17, 19, 21, 23)]  # single layers: linear at 9/13/17/21, full attention at 11/15/19/23
    + [f"{a}:{a + 8}" for a in (4, 8, 12, 16, 20)]        # two groups
    + [f"{a}:{a + 2}" for a in (10, 14, 18, 22)]          # last linear layer + the full-attention layer of a group
)


def kept_score(r):
    return 1.0 if r["score"] is None else r["score"]


def run_auroc(run_dir):
    rows = [json.loads(l) for l in (run_dir / "scores.jsonl").open()]
    return auroc([kept_score(r) for r in rows], [r["label"] for r in rows]), sum(r["score"] is None for r in rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--name", default="sweep4b")
    ap.add_argument("--confirm", default="", help="comma-separated blocks fixed in advance, e.g. 12:16,14:16")
    a = ap.parse_args()
    confirm = [c for c in a.confirm.split(",") if c]
    if set(confirm) - set(GRID):
        raise SystemExit(f"--confirm blocks must be in GRID: {sorted(set(confirm) - set(GRID))}")
    out = H.RUNS / a.name
    out.mkdir(parents=True, exist_ok=True)
    log = (out / "sweep.log").open("a")
    scorer = H.Scorer(a.model)
    if scorer.n_base != 32:
        raise SystemExit(f"GRID is written for 32 layers; {a.model} has {scorer.n_base}")
    cache = {}

    def tag(rep, request):
        return f"{a.name}/{request}/" + ("r" + rep.replace(":", "-") if rep else "base")

    def go(rep, request, name=None, phase=None):
        pairs, emails, requests = data[request]
        t = name or tag(rep, request)
        d = H.run(scorer, t, rep, pairs, emails, requests, {"request": request, "phase": phase}, log=log, cache=cache)
        au, lost = run_auroc(d)
        print(f"  {t}: AUROC {au:.4f}, {lost} of {len(pairs)} pairs without a yes/no answer", file=log, flush=True)
        return au

    def go_safe(rep):
        try:
            return go(rep, SEARCH, phase="search")
        except Exception:  # one bad block must not cost the rest of the session
            print(f"  FAILED {rep}:\n{traceback.format_exc()}", file=log, flush=True)
            return None

    data = {q: H.load_data(request=q) for q in (SEARCH, HOLDOUT)}
    print(f"== {a.model}: search on {SEARCH}, {len(GRID)} blocks; fixed in advance for {HOLDOUT}: {confirm}",
          file=log, flush=True)
    go(None, SEARCH, tag(None, SEARCH) + "_start", "search")
    found = {rep: go_safe(rep) for rep in GRID}
    go(None, SEARCH, tag(None, SEARCH) + "_end", "search")

    passes = {rep: len(H.layer_order(scorer.n_base, rep)) for rep in GRID}
    top = sorted((rep for rep in GRID if found[rep] is not None), key=lambda rep: (-found[rep], passes[rep]))[:TOP_N]
    json.dump({"rule": f"top {TOP_N} looped blocks by AUROC on {SEARCH} (a pair with no yes/no answer counts as "
                       f"score 1.0), ties to fewer layer passes",
               "search_auroc": found, "selected": top, "confirm": confirm}, (out / "selection.json").open("w"), indent=1)
    todo = confirm + [rep for rep in top if rep not in confirm]  # the pre-specified blocks first
    print(f"== validate on {HOLDOUT}: {todo}", file=log, flush=True)
    go(None, HOLDOUT, tag(None, HOLDOUT) + "_start", "validate")
    for rep in todo:
        go(rep, HOLDOUT, phase="validate")
    go(None, HOLDOUT, tag(None, HOLDOUT) + "_end", "validate")
    print("== sweep complete", file=log, flush=True)


if __name__ == "__main__":
    main()
