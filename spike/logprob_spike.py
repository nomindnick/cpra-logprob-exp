"""Phase 1 spike: can we read a yes/no responsiveness score from the first
assistant token via Ollama, and does it behave sensibly on hand-written emails?

Also times the 2025-style JSON-generation approach on the same inputs (H1).

Usage: python spike/logprob_spike.py [model]   (default qwen3.5:4b)
"""
import json
import math
import sys
import time
import urllib.request

OLLAMA = "http://localhost:11434/api/chat"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3.5:4b"

SYSTEM = (
    "You are a public records analyst for a California city. You will be shown a "
    "California Public Records Act (CPRA) request and one email from the city's "
    "email system. Decide whether the email is responsive to the request, meaning "
    "it is a record the request is asking for. Do not consider whether the email "
    "might be exempt from disclosure; that is a separate question. "
    "Answer with a single word: yes or no."
)

REQUEST = (
    "All emails sent or received by Public Works Department staff between "
    "January 1, 2026 and June 30, 2026 concerning the Elm Street Bridge "
    "rehabilitation project, including communications with the contractor "
    "(Bayside Construction) regarding change orders, schedule, and payment."
)

# (id, expected label, kind, email text)
EMAILS = [
    ("pos-01", 1, "clear positive",
     "From: j.park@city.gov\nTo: pw-staff@city.gov\nDate: 2026-03-04\n"
     "Subject: Elm St Bridge - Bayside change order #3\n\n"
     "Team, Bayside submitted change order 3 for the deck resurfacing scope. "
     "Adds $84,200 and 12 working days. Please review and get comments to me by Friday."),
    ("pos-02", 1, "clear positive",
     "From: m.ruiz@baysideconstruction.com\nTo: j.park@city.gov\nDate: 2026-02-11\n"
     "Subject: RE: Elm Street Bridge - revised schedule\n\n"
     "Jin, attached is the revised baseline schedule reflecting the delayed steel "
     "delivery. Substantial completion moves to Aug 14. Let me know if the City objects."),
    ("pos-03", 1, "indirect positive (no keyword 'Elm')",
     "From: a.chen@city.gov\nTo: j.park@city.gov\nDate: 2026-05-20\n"
     "Subject: pay app 6\n\n"
     "Jin - Bayside's pay application 6 is in. Retention is being held at 5%. "
     "I need your sign-off on the bridge deck quantities before I release it to Finance."),
    ("pos-04", 1, "exemption-flavored positive (privileged)",
     "From: d.okafor@city.gov (City Attorney)\nTo: j.park@city.gov\nDate: 2026-04-02\n"
     "Subject: CONFIDENTIAL - ATTORNEY-CLIENT PRIVILEGED - Elm St Bridge claim\n\n"
     "Jin, regarding Bayside's delay claim on the Elm Street Bridge project: my advice "
     "is that the City's position on the steel delivery is defensible under section 8.3 "
     "of the contract. Do not forward this email outside the department."),
    ("pos-05", 1, "short positive",
     "From: j.park@city.gov\nTo: m.ruiz@baysideconstruction.com\nDate: 2026-06-15\n"
     "Subject: Elm bridge - traffic control plan\n\n"
     "Marco, the TCP for the eastbound closure is approved. Go ahead."),
    ("neg-01", 0, "cross-request style negative (different project)",
     "From: j.park@city.gov\nTo: pw-staff@city.gov\nDate: 2026-03-18\n"
     "Subject: Oak Avenue sidewalk repair - bid opening\n\n"
     "Bid opening for the Oak Avenue sidewalk project is Thursday at 2pm in the "
     "council chambers. Three bids expected."),
    ("neg-02", 0, "hard negative: same people, different subject",
     "From: m.ruiz@baysideconstruction.com\nTo: j.park@city.gov\nDate: 2026-04-22\n"
     "Subject: golf Saturday?\n\n"
     "Jin - still on for 8am tee time Saturday? Marco"),
    ("neg-03", 0, "hard negative: same project, wrong time window",
     "From: j.park@city.gov\nTo: pw-staff@city.gov\nDate: 2025-09-30\n"
     "Subject: Elm Street Bridge - Bayside awarded\n\n"
     "Council awarded the Elm Street Bridge rehabilitation contract to Bayside "
     "Construction last night. Notice to proceed expected in November."),
    ("neg-04", 0, "hard negative: keyword in signature/newsletter",
     "From: hr@city.gov\nTo: all-staff@city.gov\nDate: 2026-02-01\n"
     "Subject: February wellness newsletter\n\n"
     "This month: step challenge, flu shots, and a reminder that the Elm Street "
     "parking lot is closed for bridge construction staging. Use the Oak Ave lot."),
    ("neg-05", 0, "hard negative: keyword used in unrelated sense",
     "From: r.tan@city.gov\nTo: it-help@city.gov\nDate: 2026-05-05\n"
     "Subject: network bridge dropping\n\n"
     "The wireless bridge between the Elm St yard and the corp yard keeps dropping. "
     "Can someone from IT look at it this week?"),
]

VARIANTS_YES = {"yes", " yes", "Yes", " Yes", "YES", " YES"}
VARIANTS_NO = {"no", " no", "No", " No", "NO", " NO"}


def chat(messages, **extra):
    body = {"model": MODEL, "stream": False, "messages": messages, **extra}
    req = urllib.request.Request(OLLAMA, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as r:
        out = json.load(r)
    out["_wall_s"] = time.perf_counter() - t0
    return out


def user_prompt(email):
    return (f"CPRA request:\n{REQUEST}\n\nEmail:\n{email}\n\n"
            "Is this email responsive to the request? Answer yes or no.")


def score(email):
    r = chat(
        [{"role": "system", "content": SYSTEM},
         {"role": "user", "content": user_prompt(email)}],
        think=False, logprobs=True, top_logprobs=20,
        options={"num_predict": 1, "temperature": 0},
    )
    top = r["logprobs"][0]["top_logprobs"]
    p = {t["token"]: math.exp(t["logprob"]) for t in top}
    p_yes = sum(v for k, v in p.items() if k in VARIANTS_YES)
    p_no = sum(v for k, v in p.items() if k in VARIANTS_NO)
    residual = 1.0 - p_yes - p_no  # includes mass outside top-20
    return {
        "score": p_yes / (p_yes + p_no) if p_yes + p_no else float("nan"),
        "p_yes": p_yes, "p_no": p_no, "residual": residual,
        "first_token": r["message"]["content"],
        "top3": [(t["token"], round(math.exp(t["logprob"]), 4)) for t in top[:3]],
        "prompt_tokens": r.get("prompt_eval_count"),
        "prefill_ms": r.get("prompt_eval_duration", 0) / 1e6,
        "decode_ms": r.get("eval_duration", 0) / 1e6,
        "total_ms": r.get("total_duration", 0) / 1e6,
        "wall_ms": r["_wall_s"] * 1000,
    }


def json_baseline(email):
    """The 2025 approach: generate a JSON verdict with confidence and reasoning."""
    sys_json = SYSTEM.replace(
        "Answer with a single word: yes or no.",
        'Respond only with JSON: {"responsive": true|false, "confidence": 0-1, '
        '"reasoning": "<2-3 sentences>"}')
    r = chat(
        [{"role": "system", "content": sys_json},
         {"role": "user", "content": user_prompt(email).replace(
             "Answer yes or no.", "Respond in JSON.")}],
        think=False, format="json",
        options={"num_predict": 300, "temperature": 0},
    )
    try:
        verdict = json.loads(r["message"]["content"]).get("responsive")
    except Exception:
        verdict = None
    return {
        "verdict": verdict,
        "gen_tokens": r.get("eval_count"),
        "prefill_ms": r.get("prompt_eval_duration", 0) / 1e6,
        "decode_ms": r.get("eval_duration", 0) / 1e6,
        "total_ms": r.get("total_duration", 0) / 1e6,
    }


def main():
    print(f"model: {MODEL}\n")
    # warm-up so model load time doesn't land on the first measurement
    score(EMAILS[0][3])

    print("== logprob scoring ==")
    print(f"{'id':7} {'lbl':>3} {'score':>6} {'p_yes':>6} {'p_no':>6} {'resid':>6} "
          f"{'tok':>4} {'pre_ms':>7} {'dec_ms':>7} {'tot_ms':>7}  kind / top3")
    rows = []
    for eid, label, kind, email in EMAILS:
        s = score(email)
        rows.append((eid, label, s))
        print(f"{eid:7} {label:>3} {s['score']:6.3f} {s['p_yes']:6.3f} {s['p_no']:6.3f} "
              f"{s['residual']:6.3f} {s['prompt_tokens']:>4} {s['prefill_ms']:7.0f} "
              f"{s['decode_ms']:7.0f} {s['total_ms']:7.0f}  {kind} | {s['top3']}")

    errs = [(e, l, s["score"]) for e, l, s in rows if (s["score"] >= 0.5) != bool(l)]
    print(f"\nthreshold 0.5 -> {len(rows) - len(errs)}/{len(rows)} correct; "
          f"errors: {errs or 'none'}")
    ranked = sorted(rows, key=lambda r: -r[2]["score"])
    print("ranked by score:", " > ".join(f"{e}({s['score']:.2f})" for e, _, s in ranked))
    lp_tot = sum(s["total_ms"] for _, _, s in rows) / len(rows)

    print("\n== JSON generation baseline (same emails) ==")
    print(f"{'id':7} {'lbl':>3} {'verdict':>7} {'gen':>4} {'pre_ms':>7} {'dec_ms':>7} {'tot_ms':>7}")
    jrows = []
    for eid, label, kind, email in EMAILS:
        j = json_baseline(email)
        jrows.append(j)
        print(f"{eid:7} {label:>3} {str(j['verdict']):>7} {j['gen_tokens']:>4} "
              f"{j['prefill_ms']:7.0f} {j['decode_ms']:7.0f} {j['total_ms']:7.0f}")
    js_tot = sum(j["total_ms"] for j in jrows) / len(jrows)
    print(f"\nmean total ms: logprob {lp_tot:.0f}  vs  json {js_tot:.0f}  "
          f"({js_tot / lp_tot:.1f}x)")


if __name__ == "__main__":
    main()
