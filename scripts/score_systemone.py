"""Score (request, email) pairs with a System One decision model: Jev through TypeSafe's API (SPEC §14.1), or a
local decision model (e.g. d3) through Ollama's /v1/systemone endpoint.

  uv run python scripts/score_systemone.py --pairs data/golden/pairs.jsonl --extra-emails data/golden/emails.jsonl \
      --tag golden_jev-1.14.0_noul_p2 [--roster data/golden/roster_context.txt] [--limit N]
  uv run python scripts/score_systemone.py --base-url http://localhost:11434 --model d3-ctx8k:4b ... [--fresh]

One request per pair: state = {"cpra_request", "email"} (the email rendered exactly as score.py renders it),
one Noul question whose instructions carry prompt 2's screening rules. The score is the Noul value, the model's
probability that the answer is yes. TypeSafe's re-ranking cookbook uses the same shape for query-candidate pairs.
Neither endpoint reports server-side timing, so latency is wall time from this machine (network included for Jev).
Ollama's endpoint takes no runtime options: context and batch size come from the model's Modelfile, recorded in
run.json. Key (TypeSafe only): TYPESAFE_API_KEY from the environment or .env. Same row schema and resume rules as
score.py. Stdlib only.
"""
import argparse
import hashlib
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

import score
from score import MAX_BODY_CHARS, NAMED_RULE, PROMPT, RENDER, render_email

TYPESAFE = "https://api.typesafe.ai"
MODEL = "jev-1.14.0"  # pinned; jev-latest moves when a release ships
INSTRUCTIONS = (
    "`cpra_request` is a California Public Records Act (CPRA) request to a California county, and `email` is "
    "one email from the county's email system. Is `email` responsive to `cpra_request`, meaning it is a record "
    "the request is asking for? " + NAMED_RULE + "Do not consider whether the email might be exempt from "
    "disclosure; that is a separate question."
)


def api_key():
    if os.environ.get("TYPESAFE_API_KEY"):
        return os.environ["TYPESAFE_API_KEY"]
    env = pathlib.Path(__file__).resolve().parent.parent / ".env"
    for line in env.read_text().splitlines() if env.exists() else []:
        if line.startswith("TYPESAFE_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("TYPESAFE_API_KEY not set (environment or .env)")


def score_one(endpoint, key, model, instructions, request_text, email, keep_alive=None):
    text, truncated = render_email(email)
    body = {"model": model, "state": {"cpra_request": request_text, "email": text},
            "questions": {"responsive": {"type": "noul", "instructions": instructions}}}
    if keep_alive is not None:
        body["keep_alive"] = keep_alive
    headers = {"Content-Type": "application/json", **({"Authorization": f"Bearer {key}"} if key else {})}
    for attempt in range(6):
        req = urllib.request.Request(endpoint, data=json.dumps(body).encode(), headers=headers)
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=600 if not key else 60) as r:
                resp, rid = json.load(r), r.headers.get("x-typesafe-request-id")
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 529, 500, 502, 503) or attempt == 5:
                raise RuntimeError(f"HTTP {e.code}: {e.read()[:300]!r}")
            wait = float(e.headers.get("retry-after") or 2 ** attempt)
            print(f"  HTTP {e.code}; retrying in {wait:.0f}s", file=sys.stderr)
            time.sleep(wait)
        except (urllib.error.URLError, TimeoutError) as e:  # connection/TLS failures and timeouts
            if attempt == 5:
                raise
            print(f"  {e}; retrying in {2 ** attempt}s", file=sys.stderr)
            time.sleep(2 ** attempt)
    wall = time.perf_counter() - t0
    return {
        "score": resp["answers"]["responsive"]["noul"], "model_answered": resp.get("model"),
        "truncated": truncated, "prompt_tokens": resp.get("usage", {}).get("input_tokens"),
        "output_tokens": resp.get("usage", {}).get("output_tokens"),
        "wall_ms": wall * 1000, "retries": attempt, **({"request_id_typesafe": rid} if rid else {}),
    }


def ollama_info(model):
    """Settings the local endpoint can't take per request: Ollama version, digest, Modelfile parameters."""
    digest, details = score.model_digest(model)
    params = dict(l.split(None, 1) for l in score.post("/api/show", {"model": model}).get("parameters", "").splitlines()
                  if l.strip())
    num = lambda k: int(params[k]) if k in params else None
    return {"digest": digest, "details": details, "num_ctx": num("num_ctx"), "num_batch": num("num_batch"),
            "num_gpu": num("num_gpu"),
            "ollama_version": json.load(urllib.request.urlopen(f"{score.OLLAMA}/api/version"))["version"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--base-url", default=TYPESAFE, help="TypeSafe API (default) or a local Ollama server")
    ap.add_argument("--pairs", default="data/golden/pairs.jsonl")
    ap.add_argument("--emails-dir", default="data/emails", help="directory of *.emails.jsonl / *.requests.jsonl")
    ap.add_argument("--extra-emails", help="additional emails jsonl (e.g. data/golden/emails.jsonl)")
    ap.add_argument("--roster", help="text file appended to request 25-3152's text (roster ablation)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--tag", help="run directory name (default: model name)")
    ap.add_argument("--fresh", action="store_true", help="local only: unload the model after every request "
                                                         "(keep_alive 0), for a cached-vs-fresh identity check")
    a = ap.parse_args()

    local = a.base_url.rstrip("/") != TYPESAFE
    if a.fresh and not local:
        sys.exit("--fresh needs a local server")
    key = None if local else api_key()
    endpoint = a.base_url.rstrip("/") + "/v1/systemone"
    out_dir = pathlib.Path("runs") / (a.tag or a.model.replace(":", "_"))
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
    done = {r["pair_id"] for r in map(json.loads, out_path.open())} if out_path.exists() else set()
    todo = sorted((p for p in pairs if p["pair_id"] not in done), key=lambda p: (p["request_id"], p["email_id"]))
    if a.limit:
        todo = todo[:a.limit]

    json.dump({
        "model": a.model, "backend": "ollama" if local else "typesafe-api", "endpoint": endpoint, "mode": "noul",
        "prompt": PROMPT, "prompt_hash": hashlib.sha256(INSTRUCTIONS.encode()).hexdigest()[:16],
        "instructions": INSTRUCTIONS, "state_fields": ["cpra_request", "email"], "render": RENDER,
        "max_body_chars": MAX_BODY_CHARS, "concurrency": 1, "pairs": a.pairs, "extra_emails": a.extra_emails,
        "roster": a.roster, "fresh": a.fresh, **(ollama_info(a.model) if local else {}),
    }, (out_dir / "run.json").open("w"), indent=1)
    print(f"{a.model}: {len(done)} already scored, {len(todo)} to go", file=sys.stderr)
    keep_alive = 0 if a.fresh else None
    if local and todo and not a.fresh:  # warm-up so model load time doesn't land on the first row
        score_one(endpoint, key, a.model, INSTRUCTIONS, requests[todo[0]["request_id"]], emails[todo[0]["email_id"]])

    tokens, t_start = 0, time.time()
    with out_path.open("a") as f:
        for n, p in enumerate(todo, 1):
            try:
                s = score_one(endpoint, key, a.model, INSTRUCTIONS, requests[p["request_id"]], emails[p["email_id"]],
                              keep_alive)
            except Exception as e:  # recorded and skipped; rerun to retry (resume skips only scored rows)
                print(f"  {p['pair_id']}: {e}", file=sys.stderr)
                continue
            tokens += s["prompt_tokens"] or 0
            f.write(json.dumps({**{k: p[k] for k in ("pair_id", "request_id", "email_id", "label", "kind")}, **s}) + "\n")
            f.flush()
            if n % 50 == 0:
                print(f"  {n}/{len(todo)}  {tokens:,} input tokens  {(time.time() - t_start) / n:.2f} s/pair",
                      file=sys.stderr)
    print(f"done: {len(todo)} pairs, {tokens:,} input tokens -> {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
