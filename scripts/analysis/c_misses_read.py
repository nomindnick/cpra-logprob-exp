"""Branch C3 reading material: every consensus miss and consensus false positive, printed in full.

  uv run python scripts/analysis/c_misses_read.py [--only misses|fps] [--pair PAIR_ID ...] > reading.txt

For each pair: kind, recipe, label, origin, adjudicated flag; each score model's score (main and roster
runs) against its own thr98; the JSON verdicts and the start of the 27b reasoning-first answer; the email
as stored (headers, attachment names, the whole body, with a marker where score.MAX_BODY_CHARS cuts it);
the stored rationale; the generator's and verifier's notes (synthetic emails); the Opus pre-label
(real emails); and the human adjudication call and note, if any. The request texts and the roster are
printed once at the top. Prints no statistics.
"""
import argparse
import json

from c_misses_common import (JSON_RUNS, MAX_BODY_CHARS, NAMES, emails, load, pairs, per_model,
                             reading_list, requests, short, who)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["misses", "fps"])
    ap.add_argument("--pair", nargs="*")
    ap.add_argument("--no-header", action="store_true", help="skip the request texts and roster")
    a = ap.parse_args()
    main_runs, roster_runs, js, js_roster, _ = load()
    P, E, R = pairs(), emails(), requests()
    pm, pr = per_model(main_runs), per_model(roster_runs)
    ms, fs = reading_list(main_runs, roster_runs)
    ids = a.pair or (ms if a.only == "misses" else fs if a.only == "fps" else ms + fs)
    syn = {s["id"]: s for s in map(json.loads, open("data/golden/work/synthetic.jsonl"))}
    pre = {(p["request_id"], p["email_id"]): p for p in map(json.loads, open("data/golden/work/prelabels.jsonl"))}
    adj = json.load(open("data/golden/work/adjudications.json"))
    S = {m: {x["pair_id"]: x for x in rows} for m, rows in main_runs.items()}
    SR = {m: {x["pair_id"]: x for x in rows} for m, rows in roster_runs.items()}
    J = {m: {x["pair_id"]: x for x in rows} for m, rows in js.items()}
    JR = {m: {x["pair_id"]: x for x in rows} for m, rows in js_roster.items()}

    if not a.no_header:
        for rid in ("24-409", "25-3152"):
            print(f"=================== REQUEST {rid} ===================\n{R[rid]['request_text']}\n")
        print("=================== ROSTER (appended to 25-3152 in the roster runs) ===================")
        print(open("data/golden/roster_context.txt").read())

    for pid in ids:
        p = P[pid]; e = E[p["email_id"]]
        tag = ("MISS" if pid in ms else "") + ("FP" if pid in fs else "")
        print(f"\n######## {tag} {short(pid)}  ({pid})")
        print(f"kind={p['kind']} recipe={p['recipe']} label={p['label']} origin={e.get('origin')} adjudicated={e.get('adjudicated')}")
        for lbl, runs, per in (("main", S, pm), ("roster", SR, pr)):
            if pid not in runs[NAMES[0]]:
                continue
            cells = []
            for m in NAMES:
                x = runs[m][pid]
                mark = "<thr98" if x["score"] < per[m]["thr98"] else ">=thr98"
                cells.append(f"{m} {x['score']:.3f} ({mark}, thr {per[m]['thr98']:.3f})")
            print(f"scores [{lbl}]: " + "; ".join(cells))
            print(f"  tokens {runs['27b lp'][pid]['prompt_tokens']} (27b lp), truncated {runs['27b lp'][pid]['truncated']}")
        for lbl, jj in (("main", J), ("roster", JR)):
            if pid not in jj["27b jsonR"] and pid not in jj["4b json"]:
                continue
            v = [f"{m} {'yes' if jj[m][pid]['verdict'] else 'no'} {jj[m][pid]['confidence']}" if pid in jj[m] else f"{m} (no score)"
                 for m, _ in JSON_RUNS]
            print(f"json verdicts [{lbl}]: " + "; ".join(v))
            if pid in jj["27b jsonR"]:
                print(f"  27b jsonR [{lbl}] raw: {jj['27b jsonR'][pid].get('raw', '')[:600]}")
        print(f"From: {e.get('from')}\nTo: {e.get('to')}\nCc: {e.get('cc')}\nBcc: {e.get('bcc')}\nDelivered-To: {e.get('delivered_to')}")
        print(f"Date: {e.get('date')}\nSubject: {e.get('subject')}\nAttachments: {e.get('attachments')}")
        body = e.get("body") or ""
        print(f"--- body ({len(body)} chars) ---")
        print(body[:MAX_BODY_CHARS])
        if len(body) > MAX_BODY_CHARS:
            print(f"\n[[[ ---- models see nothing past here (char {MAX_BODY_CHARS}) ---- ]]]\n{body[MAX_BODY_CHARS:]}")
        print("--- notes ---")
        print(f"rationale: {e.get('rationale')}")
        s = syn.get(p["email_id"])
        if s:
            print(f"generator why_label: {s.get('why_label')}")
            print(f"verifier: label_ok={s.get('verify_label_correct')} recipe_ok={s.get('verify_recipe_followed')} "
                  f"style_tell={s.get('verify_style_tell')} problem={s.get('verify_problem')}")
            print(f"source_id: {s.get('source_id')}")
        q = pre.get((p["request_id"], p["email_id"]))
        if q:
            print(f"Opus pre-label: {q.get('prelabel')} ({q.get('confidence')}): {q.get('rationale')} [{q.get('note')}]")
        for k in (f"{p['request_id']}~{p['email_id']}", p["email_id"]):
            if k in adj:
                print(f"human adjudication: {adj[k]}")
        print(f"main-set: missed@thr98 by {who(pm, 'miss98', pid)}; missed@0.5 by {who(pm, 'miss50', pid)}; "
              f"kept@thr98 by {who(pm, 'fp98', pid)}; kept@0.5 by {who(pm, 'fp50', pid)}")


if __name__ == "__main__":
    main()
