"""First-token yes/no scoring through PyTorch, with an optional layer-looping order.

  loop/.venv/bin/python loop/score_hf.py --tag base                   # stock layer order
  loop/.venv/bin/python loop/score_hf.py --tag r12-16 --repeat 12:16  # layers 12..15 run twice

Same prompt, email rendering and yes/no token sets as scripts/score.py (imported from it), so a run
with no --repeat is the PyTorch counterpart of the Ollama logprob runs. Differences from those runs:
full-precision (bf16) weights instead of Q4_K_M, and no prefix cache (every call processes the whole
prompt), so times here compare with each other, not with the Ollama times.

--repeat a:b[:k]  run layers a..b-1 k times in a row (default 2) instead of once; several, comma-separated.
                  No weights are copied: the layer list just points at the same modules again.

Reads  data/golden/pairs.jsonl (or --pairs), data/emails/*.jsonl, data/golden/emails.jsonl
Writes loop/runs/<tag>/scores.jsonl (resumable) and run.json. Run from the repository root.
loop/sweep.py uses the same functions to score many layer orders with one model load.
"""
import argparse
import json
import math
import pathlib
import sys
import time

import torch

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import score as S  # noqa: E402  (prompt text, render_email, yes/no variants)

REVISIONS = {"Qwen/Qwen3.5-4B": "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a",
             "Qwen/Qwen3.5-9B": "c202236235762e1c871ad0ccb60c8ee5ba337b9a"}
TOP_K = 20  # Ollama runs read the top 20 logprobs; same cut here
RUNS = ROOT / "loop" / "runs"


def layer_order(n, spec):
    """'12:16' -> 0..15, 12..15, 16..n-1. Blocks must not overlap."""
    blocks = []
    for item in filter(None, (spec or "").split(",")):
        parts = [int(x) for x in item.split(":")]
        a, b = parts[0], parts[1]
        k = parts[2] if len(parts) > 2 else 2
        if not (0 <= a < b <= n and k >= 1):
            raise SystemExit(f"bad --repeat block {item!r} for {n} layers")
        blocks.append((a, b, k))
    blocks.sort()
    for (_, b0, _), (a1, _, _) in zip(blocks, blocks[1:]):
        if a1 < b0:
            raise SystemExit("--repeat blocks overlap")
    order, i = [], 0
    for a, b, k in blocks:
        order += list(range(i, a)) + list(range(a, b)) * k
        i = b
    return order + list(range(i, n))


class Scorer:
    """The model, loaded once; set_order() switches the layer sequence in place."""

    def __init__(self, model_name="Qwen/Qwen3.5-4B", dtype="bf16"):
        from transformers import AutoTokenizer
        from transformers.models.qwen3_5 import Qwen3_5ForCausalLM

        self.model_name, self.dtype, self.rev = model_name, dtype, REVISIONS.get(model_name)
        self.tok = AutoTokenizer.from_pretrained(model_name, revision=self.rev)
        t0 = time.perf_counter()
        model, info = Qwen3_5ForCausalLM.from_pretrained(
            model_name, revision=self.rev, dtype={"bf16": torch.bfloat16, "fp32": torch.float32}[dtype],
            output_loading_info=True)
        if info["missing_keys"] or info["mismatched_keys"]:
            raise SystemExit(f"weights did not load cleanly: missing {info['missing_keys'][:5]} "
                             f"mismatched {info['mismatched_keys'][:5]}")
        self.text = model.to("cuda").eval().model
        self.load_s = time.perf_counter() - t0
        self.base_layers = list(self.text.layers)
        self.base_types = list(self.text.config.layer_types)
        self.n_base = len(self.base_layers)
        self.order = list(range(self.n_base))
        # Output head in float32: bf16 logits near 20-30 step by 0.125, which collapses the scores onto a
        # few dozen values. The layers stay in the load dtype.
        self.head_w = model.lm_head.weight.detach().float()
        self.yes_ids = {self.tok(v, add_special_tokens=False)["input_ids"][0] for v in S.VARIANTS_YES}
        self.no_ids = {self.tok(v, add_special_tokens=False)["input_ids"][0] for v in S.VARIANTS_NO}
        self.yes_t = torch.tensor(sorted(self.yes_ids), device="cuda")
        self.no_t = torch.tensor(sorted(self.no_ids), device="cuda")

    def set_order(self, order):
        """Point the layer list at the given sequence of original layers (shared modules, no copies)."""
        cfg = self.text.config
        self.text.layers = torch.nn.ModuleList([self.base_layers[j] for j in order])
        cfg.num_hidden_layers = len(order)
        cfg.layer_types = [self.base_types[j] for j in order]  # the forward loop picks each layer's mask by position
        self.order = list(order)

    def tokenize(self, request_text, email):
        text, truncated = S.render_email(email)
        msgs = [{"role": "system", "content": S.SYSTEM},
                {"role": "user", "content": S.USER_TEMPLATE.format(request=request_text, email=text)}]
        prompt = self.tok.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False, tokenize=False)
        return self.tok(prompt, add_special_tokens=False, return_tensors="pt")["input_ids"], truncated

    def score_ids(self, ids):
        ids = ids.to("cuda")
        torch.cuda.synchronize()
        t = time.perf_counter()
        with torch.inference_mode():
            h = self.text(input_ids=ids, use_cache=False).last_hidden_state[0, -1].float()
            logp = torch.log_softmax(self.head_w @ h, dim=-1)
            top = torch.topk(logp, TOP_K)
            lp_yes = torch.logsumexp(logp[self.yes_t], 0).item()  # whole vocabulary, not just the top 20
            lp_no = torch.logsumexp(logp[self.no_t], 0).item()
        torch.cuda.synchronize()
        fwd_ms = (time.perf_counter() - t) * 1000
        top_ids, top_p = top.indices.tolist(), [math.exp(x) for x in top.values.tolist()]
        p_yes = sum(pr for i, pr in zip(top_ids, top_p) if i in self.yes_ids)
        p_no = sum(pr for i, pr in zip(top_ids, top_p) if i in self.no_ids)
        ok = math.isfinite(p_yes + p_no) and p_yes + p_no > 0
        return {
            # score: as in the Ollama runs (yes/no mass within the top 20); None when neither is there.
            # lp_yes / lp_no: log-probability of the yes / no variants over the whole vocabulary, always defined.
            "score": p_yes / (p_yes + p_no) if ok else None,
            "p_yes": p_yes, "p_no": p_no, "residual": 1 - p_yes - p_no,
            "lp_yes": lp_yes if math.isfinite(lp_yes) else None, "lp_no": lp_no if math.isfinite(lp_no) else None,
            "first_token": self.tok.decode(top_ids[:1]),
            "top3": [[self.tok.decode([i]), round(pr, 5)] for i, pr in zip(top_ids[:3], top_p[:3])],
            "prompt_tokens": ids.shape[1], "fwd_ms": fwd_ms,
        }

    def run_meta(self, repeat):
        return {
            "backend": "pytorch", "model": self.model_name, "revision": self.rev, "dtype": self.dtype,
            "head_dtype": "fp32", "torch": torch.__version__, "device": torch.cuda.get_device_name(0),
            "mode": "logprob", "prompt": S.PROMPT, "render": S.RENDER, "max_body_chars": S.MAX_BODY_CHARS,
            "system": S.SYSTEM, "user_template": S.USER_TEMPLATE, "top_k": TOP_K,
            "repeat": repeat, "base_layers": self.n_base, "layers_run": len(self.order), "order": self.order,
            "prefix_cache": False, "load_s": round(self.load_s, 1),
        }


def load_data(pairs_path="data/golden/pairs.jsonl", request=None):
    emails = {e["id"]: e for p in (ROOT / "data/emails").glob("*.emails.jsonl") for e in map(json.loads, p.open())}
    emails.update({e["id"]: e for e in map(json.loads, (ROOT / "data/golden/emails.jsonl").open())})
    requests = {r["request_id"]: r["request_text"] for p in (ROOT / "data/emails").glob("*.requests.jsonl")
                for r in map(json.loads, p.open())}
    pairs = [json.loads(l) for l in (ROOT / pairs_path).open()]
    if request:
        pairs = [p for p in pairs if p["request_id"] == request]
    pairs.sort(key=lambda p: (p["request_id"], p["email_id"]))
    return pairs, emails, requests


def run(scorer, tag, repeat, pairs, emails, requests, extra_meta=None, log=sys.stderr, cache=None):
    """Score `pairs` under the layer order given by `repeat`; resumable. Returns the run directory.
    `cache` (dict) keeps tokenized prompts between calls."""
    out_dir = RUNS / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "scores.jsonl"
    done = {json.loads(l)["pair_id"] for l in out_path.open()} if out_path.exists() else set()
    todo = [p for p in pairs if p["pair_id"] not in done]
    scorer.set_order(layer_order(scorer.n_base, repeat))
    json.dump({**scorer.run_meta(repeat), **(extra_meta or {})}, (out_dir / "run.json").open("w"), indent=1)
    cache = {} if cache is None else cache

    def inputs(p):
        if p["pair_id"] not in cache:
            cache[p["pair_id"]] = scorer.tokenize(requests[p["request_id"]], emails[p["email_id"]])
        return cache[p["pair_id"]]

    print(f"{tag}: {len(scorer.order)} layer passes ({scorer.n_base} layers), {len(done)} already scored, "
          f"{len(todo)} to go", file=log, flush=True)
    if todo:
        for _ in range(2):  # warm-up, not recorded
            scorer.score_ids(inputs(todo[0])[0])
    t_start = time.perf_counter()
    with out_path.open("a") as f:
        for p in todo:
            ids, truncated = inputs(p)
            row = {"pair_id": p["pair_id"], "request_id": p["request_id"], "email_id": p["email_id"],
                   "label": p["label"], "kind": p["kind"], "truncated": truncated, **scorer.score_ids(ids)}
            f.write(json.dumps(row) + "\n")
            f.flush()
    el = time.perf_counter() - t_start
    print(f"  done: {len(todo)} pairs in {el / 60:.1f} min", file=log, flush=True)
    return out_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--repeat", help="a:b[:k],... (see module docstring)")
    ap.add_argument("--pairs", default="data/golden/pairs.jsonl")
    ap.add_argument("--request", help="only this request id")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dtype", choices=["bf16", "fp32"], default="bf16")
    a = ap.parse_args()
    pairs, emails, requests = load_data(a.pairs, a.request)
    if a.limit:
        pairs = pairs[:a.limit]
    scorer = Scorer(a.model, a.dtype)
    run(scorer, a.tag, a.repeat, pairs, emails, requests, {"pairs": a.pairs, "request": a.request})


if __name__ == "__main__":
    main()
