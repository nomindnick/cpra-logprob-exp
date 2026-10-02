"""Assemble the golden set from pre-labels, adjudications and verified synthetic emails.

  uv run python scripts/build_golden.py

Reads  data/golden/work/prelabels.jsonl, synthetic.jsonl, acpg_roster.json
       data/golden/work/adjudications.json   (the human's calls from the adjudication page: R/N for
                                              real rows, K/F/D for flagged synthetic rows)
Writes data/golden/emails.jsonl   real + synthetic emails, each with kind/label/request
       data/golden/pairs.jsonl    one designed pair per email
       data/golden/roster_context.txt   roster paragraph for the 25-3152 ablation
       data/golden/summary.json
"""
import json, pathlib, re, collections, random

W = pathlib.Path("data/golden/work"); OUT = pathlib.Path("data/golden")
TARGET_POS, TARGET_NEG = 75, 60


def load_adjudications():
    """Return {item key: call}. Keys are "<request>~<email id>" for real rows, the synth id for synthetic rows.

    adjudications.json is the export of the adjudication page's "calls" collection
    ({key: {"call": "R"|"N"|"K"|"F"|"D"|null, "note": str}}); see scripts/adjudication_sheet.py.
    """
    f = W / "adjudications.json"
    if not f.exists():
        return {}
    return {k: v["call"].upper() for k, v in json.load(open(f)).items() if v.get("call")}


def main():
    OUT.mkdir(exist_ok=True)
    calls = load_adjudications()
    emails = {e["id"]: e for e in map(json.loads, open("data/emails/sandiego.emails.jsonl"))}
    pre = [json.loads(l) for l in open(W / "prelabels.jsonl")]
    rng = random.Random(5)
    rows = []
    for rid in ["24-409", "25-3152"]:
        pos, neg = [], []
        for r in pre:
            if r["request_id"] != rid:
                continue
            key = f"{rid}~{r['email_id']}"
            final = calls.get(key, r["prelabel"])
            if final == "?":
                continue
            adjudicated = key in calls
            if final == "R" and r["origin"] == "produced":
                pos.append((r, adjudicated))
            elif final == "N" and r["origin"] == "other_production":
                neg.append((r, adjudicated))
            elif final == "R" and r["origin"] == "other_production" and adjudicated:
                pos.append((r, adjudicated))  # human says responsive despite other origin
        # prefer adjudicated + high-confidence rows, then random
        pos.sort(key=lambda x: (not x[1], x[0]["confidence"] != "high", rng.random()))
        neg.sort(key=lambda x: (not x[1], x[0]["confidence"] != "high", rng.random()))
        for r, adj in pos[:TARGET_POS]:
            e = emails[r["email_id"]]
            rows.append({**{k: e[k] for k in ("id", "from", "to", "cc", "date", "subject", "attachments", "body")},
                         "request_id": rid, "kind": "real_positive", "recipe": None, "label": 1,
                         "origin": r["origin"], "adjudicated": adj, "rationale": r["rationale"]})
        for r, adj in neg[:TARGET_NEG]:
            e = emails[r["email_id"]]
            rows.append({**{k: e[k] for k in ("id", "from", "to", "cc", "date", "subject", "attachments", "body")},
                         "request_id": rid, "kind": "real_negative", "recipe": None, "label": 0,
                         "origin": r["origin"], "adjudicated": adj, "rationale": r["rationale"]})
    dropped = 0
    for s in map(json.loads, open(W / "synthetic.jsonl")):
        flagged = (s["verify_label_correct"] is False or s["verify_recipe_followed"] is False
                   or s["verify_style_tell"] == "obvious")
        call = calls.get(s["id"])
        label = s["label"]
        if flagged and call is None:
            dropped += 1; continue          # unadjudicated flag -> out
        if call == "D":
            dropped += 1; continue
        if call == "F":
            label = 1 - label
        rows.append({**{k: s[k] for k in ("id", "from", "to", "cc", "date", "subject", "attachments", "body")},
                     "request_id": s["request_id"], "kind": s["kind"], "recipe": s["recipe"], "label": label,
                     "origin": "synthetic", "adjudicated": call is not None, "rationale": s["why_label"],
                     "source_id": s["source_id"]})
    with (OUT / "emails.jsonl").open("w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (OUT / "pairs.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps({"pair_id": f"{r['request_id']}|{r['id']}", "request_id": r["request_id"],
                                "email_id": r["id"], "label": r["label"], "kind": r["kind"], "recipe": r["recipe"]}) + "\n")
    roster = json.load(open(W / "acpg_roster.json"))
    lines = ["Members of the Alpine Community Planning Group who served at any time from 1 January 2024 through 31 May 2025 (name; role; period; email addresses used):"]
    for m in roster["members"]:
        lines.append(f"- {m['name']}; {m.get('role','member')}; {m.get('period','')}; {', '.join(m.get('email_addresses', []))}")
    (OUT / "roster_context.txt").write_text("\n".join(lines) + "\n")
    summary = {"emails": len(rows), "adjudications_applied": len(calls), "synthetic_dropped": dropped,
               "by_request_kind": {f"{k[0]}/{k[1]}": v for k, v in sorted(collections.Counter((r["request_id"], r["kind"]) for r in rows).items())},
               "positives": sum(r["label"] for r in rows), "negatives": sum(1 - r["label"] for r in rows)}
    json.dump(summary, (OUT / "summary.json").open("w"), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
