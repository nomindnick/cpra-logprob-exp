"""Score (request, email) pairs with first-token yes/no logprobs via Ollama.

  uv run python scripts/score.py --model qwen3.5:4b [--limit N] [--concurrency 1]

Reads  data/dataset/pairs.jsonl, data/emails/*.emails.jsonl, *.requests.jsonl
Writes runs/<model-tag>/scores.jsonl   one row per pair (resumable: existing
                                       pair_ids are skipped)
       runs/<model-tag>/run.json       model digest, prompt hash, settings

Pairs are processed grouped by request so consecutive calls share the
system+request prefix (SPEC §5 prompt layout) and Ollama's prompt cache can
reuse it. Timing fields come from Ollama: prompt_eval_duration (prefill) and
eval_duration (decode). Stdlib + nothing else.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import math
import pathlib
import sys
import time
import urllib.request

OLLAMA = "http://localhost:11434"
MAX_BODY_CHARS = 8000  # ~2k tokens; SPEC §12 truncation cap. Truncation is logged per row.
NUM_CTX = 8192
EXTRA_OPTIONS = {}  # Ollama options from --num-gpu / --num-batch, merged into every request
CANARY_EVERY = 100  # single-stream only: rescore a fixed pair and compare to its reference  # explicit context so no backend default silently truncates long prompts

SYSTEM = (
    "You are a public records analyst for a California county. You will be shown a "
    "California Public Records Act (CPRA) request and one email from the county's "
    "email system. Decide whether the email is responsive to the request, meaning "
    "it is a record the request is asking for. Do not consider whether the email "
    "might be exempt from disclosure; that is a separate question. "
    "Answer with a single word: yes or no."
)
USER_TEMPLATE = (
    "CPRA request:\n{request}\n\n"
    "Email:\n{email}\n\n"
    "Is this email responsive to the request? Answer yes or no."
)
SYSTEM_JSON = SYSTEM.replace(
    "Answer with a single word: yes or no.",
    'Respond only with a JSON object: {"responsive": true or false, '
    '"confidence": a number from 0 to 1, "reasoning": "two or three sentences"}')
USER_TEMPLATE_JSON = USER_TEMPLATE.replace("Answer yes or no.", "Respond in JSON.")
# json_reason: same as json but the reasoning is written before the verdict (enforced by a schema)
SYSTEM_JSON_REASON = SYSTEM.replace(
    "Answer with a single word: yes or no.",
    'Respond only with a JSON object: {"reasoning": "two or three sentences", '
    '"responsive": true or false, "confidence": a number from 0 to 1}. '
    'Write the reasoning first, then decide.')
SCHEMA_JSON = {"type": "object", "required": ["responsive", "confidence", "reasoning"],  # --schema (json mode)
               "properties": {"responsive": {"type": "boolean"}, "confidence": {"type": "number"},
                              "reasoning": {"type": "string"}}}
SCHEMA_JSON_REASON = {"type": "object", "required": ["reasoning", "responsive", "confidence"],
                      "properties": {"reasoning": {"type": "string"}, "responsive": {"type": "boolean"},
                                     "confidence": {"type": "number"}}}

VARIANTS_YES = {"yes", " yes", "Yes", " Yes", "YES", " YES"}
VARIANTS_NO = {"no", " no", "No", " No", "NO", " NO"}


def render_email(e):
    body = e["body"] or ""
    truncated = len(body) > MAX_BODY_CHARS
    if truncated:
        body = body[:MAX_BODY_CHARS] + "\n[... truncated]"
    hdr = [f"From: {e.get('from') or ''}", f"To: {e.get('to') or ''}"]
    if e.get("cc"):
        hdr.append(f"Cc: {e['cc']}")
    hdr += [f"Date: {e.get('date') or ''}", f"Subject: {e.get('subject') or ''}"]
    if e.get("attachments"):
        hdr.append("Attachments: " + ", ".join(e["attachments"]))
    return "\n".join(hdr) + "\n\n" + body, truncated


def post(path, body):
    req = urllib.request.Request(f"{OLLAMA}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def score_one(model, request_text, email):
    text, truncated = render_email(email)
    t0 = time.perf_counter()
    r = post("/api/chat", {
        "model": model, "stream": False, "think": False,
        "logprobs": True, "top_logprobs": 20,
        "options": {"num_predict": 1, "temperature": 0, "num_ctx": NUM_CTX, **EXTRA_OPTIONS},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": USER_TEMPLATE.format(request=request_text, email=text)}],
    })
    wall = time.perf_counter() - t0
    top = r["logprobs"][0]["top_logprobs"] if r.get("logprobs") else []
    p = {t["token"]: math.exp(t["logprob"]) for t in top}
    p_yes = sum(v for k, v in p.items() if k in VARIANTS_YES)
    p_no = sum(v for k, v in p.items() if k in VARIANTS_NO)
    return {
        "score": p_yes / (p_yes + p_no) if p_yes + p_no else None,
        "p_yes": p_yes, "p_no": p_no, "residual": 1 - p_yes - p_no,
        "first_token": r["message"]["content"],
        "top3": [[t["token"], round(math.exp(t["logprob"]), 5)] for t in top[:3]],
        "truncated": truncated,
        "prompt_tokens": r.get("prompt_eval_count"),
        "prefill_ms": r.get("prompt_eval_duration", 0) / 1e6,
        "decode_ms": r.get("eval_duration", 0) / 1e6,
        "total_ms": (r.get("total_duration", 0) - r.get("load_duration", 0)) / 1e6,
        "load_ms": r.get("load_duration", 0) / 1e6,
        "wall_ms": wall * 1000,
    }


def unload(model, settle=3.0):
    """Force Ollama to drop the model (and its prompt cache); next call reloads it."""
    try:
        post("/api/generate", {"model": model, "keep_alive": 0})
        t0 = time.time()
        while time.time() - t0 < 30 and any(
                m["name"] == model for m in json.load(urllib.request.urlopen(f"{OLLAMA}/api/ps"))["models"]):
            time.sleep(0.05)
    except Exception:
        pass
    time.sleep(settle)


def score_guarded(model, request_text, email, reloads):
    """score_one with reload-and-retry when the backend returns an undefined score
    (Gemma 4 on this Ollama build: sticky prompt-cache corruption -> <unused*> tokens)."""
    for attempt in range(3):
        s = score_one(model, request_text, email)
        if s["score"] is not None and s["residual"] < 0.5:
            s["reloads"] = reloads[0]
            return s
        reloads[0] += 1
        print(f"  invalid score (attempt {attempt+1}); unloading {model} and retrying", file=sys.stderr)
        unload(model)
    s["reloads"] = reloads[0]
    return s


def score_json(model, request_text, email, reason_first=False, schema=False):
    """The 2025 approach: generate a JSON verdict with self-reported confidence.
    score = P(responsive) = confidence if responsive else 1 - confidence.
    reason_first: the schema puts "reasoning" before "responsive", so the verdict follows the reasoning."""
    text, truncated = render_email(email)
    t0 = time.perf_counter()
    r = post("/api/chat", {
        "model": model, "stream": False, "think": False,
        "format": SCHEMA_JSON_REASON if reason_first else SCHEMA_JSON if schema else "json",
        "options": {"num_predict": 500 if reason_first else 300, "temperature": 0, "num_ctx": NUM_CTX,
                    **EXTRA_OPTIONS},
        "messages": [{"role": "system", "content": SYSTEM_JSON_REASON if reason_first else SYSTEM_JSON},
                     {"role": "user", "content": USER_TEMPLATE_JSON.format(request=request_text, email=text)}],
    })
    wall = time.perf_counter() - t0
    content = r["message"]["content"]
    verdict = conf = None
    try:
        j = json.loads(content)
        verdict = j.get("responsive")
        if isinstance(verdict, str):
            verdict = verdict.strip().lower() in ("true", "yes")
        conf = float(j.get("confidence"))
        conf = min(max(conf, 0.0), 1.0)
    except Exception:
        pass
    score = None
    if verdict is not None and conf is not None:
        score = conf if verdict else 1.0 - conf
    return {
        "score": score, "verdict": verdict, "confidence": conf,
        "raw": content[:600], "truncated": truncated,
        "prompt_tokens": r.get("prompt_eval_count"), "gen_tokens": r.get("eval_count"),
        "prefill_ms": r.get("prompt_eval_duration", 0) / 1e6,
        "decode_ms": r.get("eval_duration", 0) / 1e6,
        "total_ms": (r.get("total_duration", 0) - r.get("load_duration", 0)) / 1e6,
        "load_ms": r.get("load_duration", 0) / 1e6,
        "wall_ms": wall * 1000,
    }


def model_digest(model):
    for m in post("/api/tags", {}).get("models", []) if False else json.load(
            urllib.request.urlopen(f"{OLLAMA}/api/tags"))["models"]:
        if m["name"] == model or m["model"] == model:
            return m.get("digest"), m.get("details", {})
    return None, {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--pairs", default="data/dataset/pairs.jsonl")
    ap.add_argument("--emails-dir", default="data/emails", help="directory of *.emails.jsonl / *.requests.jsonl")
    ap.add_argument("--extra-emails", help="additional emails jsonl (e.g. data/golden/emails.jsonl)")
    ap.add_argument("--roster", help="text file appended to request 25-3152's text (roster ablation)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--tag", help="run directory name (default: model name, ':' -> '_')")
    ap.add_argument("--mode", choices=["logprob", "json", "json_reason"], default="logprob",
                    help="json = generate a JSON verdict with self-reported confidence (2025 baseline); "
                         "json_reason = the same with the reasoning written before the verdict")
    ap.add_argument("--num-gpu", type=int,
                    help="layers to offload (Ollama num_gpu); 0 = CPU only (reference runs). The upstream "
                         "workaround for the ROCm qwen35 state bug (all but layer 0) broke the model on 0.32.14")
    ap.add_argument("--schema", action="store_true",
                    help="json mode: constrain output to the responsive/confidence/reasoning schema (json_reason "
                         "always uses its schema); without it, format=json lets the model pick its own keys")
    ap.add_argument("--num-batch", type=int,
                    help="prompt-processing batch size (Ollama num_batch); >= the longest prompt keeps prefill in one "
                         "batch (on ROCm, qwen35 state is corrupted across 2,048-token batch boundaries)")
    ap.add_argument("--fresh", action="store_true",
                    help="unload the model before every call, so no state carries over between pairs (at the "
                         "default batch size, Ollama 0.32.14 on ROCm leaks the previous prompt into qwen3.5 4b/9b)")
    ap.add_argument("--rescore-invalid", action="store_true",
                    help="drop rows whose score is None or errored, then resume (backend glitches)")
    a = ap.parse_args()

    tag = a.tag or a.model.replace(":", "_").replace("/", "_")
    out_dir = pathlib.Path("runs") / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "scores.jsonl"

    emails = {e["id"]: e for p in pathlib.Path(a.emails_dir).glob("*.emails.jsonl")
              for e in map(json.loads, p.open())}
    if a.extra_emails:
        emails.update({e["id"]: e for e in map(json.loads, open(a.extra_emails))})
    requests = {r["request_id"]: r["request_text"] for p in pathlib.Path(a.emails_dir).glob("*.requests.jsonl")
                for r in map(json.loads, p.open())}
    if a.roster:
        requests["25-3152"] = requests["25-3152"] + "\n\n" + open(a.roster).read()
    pairs = [json.loads(l) for l in open(a.pairs)]
    done = set()
    if out_path.exists():
        existing = [json.loads(l) for l in out_path.open()]
        if a.rescore_invalid:
            valid = [r for r in existing if "error" not in r and r.get("score") is not None]
            print(f"dropping {len(existing) - len(valid)} invalid rows", file=sys.stderr)
            with out_path.open("w") as f:
                for r in valid:
                    f.write(json.dumps(r) + "\n")
            existing = valid
        done = {r["pair_id"] for r in existing}
    todo = [p for p in pairs if p["pair_id"] not in done]
    todo.sort(key=lambda p: (p["request_id"], p["email_id"]))  # group by request for prefix cache
    if a.limit:
        todo = todo[:a.limit]

    digest, details = model_digest(a.model)
    if a.num_gpu is not None:
        EXTRA_OPTIONS["num_gpu"] = a.num_gpu
    if a.num_batch is not None:
        EXTRA_OPTIONS["num_batch"] = a.num_batch
    if a.fresh and a.concurrency != 1:
        sys.exit("--fresh needs --concurrency 1")
    if details.get("family") == "qwen35" and a.num_batch is None and a.num_gpu != 0:
        print("warning: qwen35 model at the default batch size; on the Strix Halo (ROCm) qwen3.5 4b/9b scores are "
              "corrupted this way. Use --num-batch 8192 (docs/findings-golden.md §7).", file=sys.stderr)
    system, template = {"logprob": (SYSTEM, USER_TEMPLATE), "json": (SYSTEM_JSON, USER_TEMPLATE_JSON),
                        "json_reason": (SYSTEM_JSON_REASON, USER_TEMPLATE_JSON)}[a.mode]
    prompt_hash = hashlib.sha256((system + "\n" + template).encode()).hexdigest()[:16]
    json.dump({
        "model": a.model, "digest": digest, "details": details,
        "mode": a.mode, "prompt_hash": prompt_hash,
        "system": system, "user_template": template,
        "max_body_chars": MAX_BODY_CHARS, "num_ctx": NUM_CTX, "concurrency": a.concurrency,
        "pairs": a.pairs, "extra_emails": a.extra_emails, "roster": a.roster, "fresh": a.fresh,
        "num_gpu": a.num_gpu, "num_batch": a.num_batch, "schema": a.schema or a.mode == "json_reason",
        "ollama_version": json.load(urllib.request.urlopen(f"{OLLAMA}/api/version"))["version"],
    }, (out_dir / "run.json").open("w"), indent=1)

    print(f"{a.model}: {len(done)} already scored, {len(todo)} to go, concurrency {a.concurrency}",
          file=sys.stderr)
    # warm-up so model load time doesn't land on the first row

    reloads = [0]
    canary = todo[0] if todo else None
    canary_ref = [None]

    def check_canary():
        s = score_one(a.model, requests[canary["request_id"]], emails[canary["email_id"]])
        if s["score"] is None:
            return False
        if canary_ref[0] is None:
            canary_ref[0] = s["score"]
            return True
        return abs(s["score"] - canary_ref[0]) < 0.05

    def work(p):
        try:
            if a.fresh:
                unload(a.model, settle=0)
            if a.mode in ("json", "json_reason"):
                s = score_json(a.model, requests[p["request_id"]], emails[p["email_id"]],
                               reason_first=a.mode == "json_reason", schema=a.schema)
            else:
                s = score_guarded(a.model, requests[p["request_id"]], emails[p["email_id"]], reloads)
        except Exception as ex:
            return {"pair_id": p["pair_id"], "error": f"{type(ex).__name__}: {ex}"}
        return {"pair_id": p["pair_id"], "request_id": p["request_id"], "email_id": p["email_id"],
                "label": p["label"], "kind": p["kind"], **s}

    # warm-up so model load time doesn't land on the first row; set the canary reference
    # (--fresh: every call starts from a freshly loaded model, so neither applies)
    if a.fresh:
        pass
    elif todo and a.mode != "logprob":
        score_json(a.model, requests[todo[0]["request_id"]], emails[todo[0]["email_id"]],
                   reason_first=a.mode == "json_reason", schema=a.schema)
    elif todo:
        score_one(a.model, requests[todo[0]["request_id"]], emails[todo[0]["email_id"]])
        if not check_canary():
            unload(a.model); check_canary()

    t_start = time.perf_counter()
    n = 0
    with out_path.open("a") as f, cf.ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        for row in ex.map(work, todo):
            f.write(json.dumps(row) + "\n")
            n += 1
            if a.mode == "logprob" and not a.fresh and a.concurrency == 1 and n % CANARY_EVERY == 0 and not check_canary():
                print(f"  canary drifted at {n}; unloading {a.model}", file=sys.stderr)
                reloads[0] += 1
                unload(a.model)
                if not check_canary():
                    print("  canary still drifted after reload", file=sys.stderr)
            if n % 200 == 0:
                f.flush()
                el = time.perf_counter() - t_start
                print(f"  {n}/{len(todo)}  {el/n*1000:.0f} ms/pair  eta {(len(todo)-n)*el/n/60:.0f} min",
                      file=sys.stderr)
    el = time.perf_counter() - t_start
    print(f"done: {n} pairs in {el/60:.1f} min ({el/max(n,1)*1000:.0f} ms/pair wall), "
          f"{reloads[0]} model reloads -> {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
