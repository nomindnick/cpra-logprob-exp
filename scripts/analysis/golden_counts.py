"""Pair counts of the current golden set (data/golden/pairs.jsonl), so the analysis scripts don't hard-code them.

  NP, NN, NR   positives, negatives and pairs per request (main set; the roster set is the 25-3152 pairs)
  NFLIP        hard negatives the owner flipped to responsive, per request
  N_ALL, N_POS, N_NEG   the whole main set
"""
import json
import pathlib

_PAIRS = [json.loads(line) for line in (pathlib.Path(__file__).resolve().parents[2] / "data/golden/pairs.jsonl").open()]
REQUESTS = ("24-409", "25-3152")
NP = {r: sum(p["label"] for p in _PAIRS if p["request_id"] == r) for r in REQUESTS}
NN = {r: sum(1 - p["label"] for p in _PAIRS if p["request_id"] == r) for r in REQUESTS}
NR = {r: NP[r] + NN[r] for r in REQUESTS}
NFLIP = {r: sum(p["kind"] == "hard_negative_flipped" for p in _PAIRS if p["request_id"] == r) for r in REQUESTS}
N_ALL = len(_PAIRS)
N_POS = sum(NP.values())
N_NEG = sum(NN.values())
