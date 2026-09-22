"""Build labeled (request, email) pairs from parsed productions.

  uv run python scripts/build_dataset.py

Reads  data/emails/*.emails.jsonl, data/emails/*.requests.jsonl
Writes data/dataset/pairs.jsonl  — one row per (request, email) instance:
         pair_id, request_id, email_id, label (1/0), kind, email_request_id
       data/dataset/summary.json

Labeling (SPEC §7):
  produced       label 1  email was produced in response to this request
  cross_request  label 0  email was produced for a *different* request from the
                          same agency; assumed non-responsive to this one
Synthetic rows (kind synthetic_*) are appended by a later step, not here.

Assumption to hand-check in phase 4: cross-request pairs are true negatives.
Look at the highest-scoring cross_request rows; if a model is confidently "yes"
and a human agrees, that is label noise, not model error.
"""
import json
import pathlib

EMAILS_DIR = pathlib.Path("data/emails")
OUT_DIR = pathlib.Path("data/dataset")

# Topical adjacency between requests (SPEC §7.3.1). Same agency for all; these
# note where cross-request negatives are "harder" because subject matter overlaps.
ADJACENT = {
    frozenset({"25-3152", "25-4697"}): "both PDS land-use / community planning matters",
}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    requests = [json.loads(l) for p in EMAILS_DIR.glob("*.requests.jsonl") for l in p.open()]
    emails = [json.loads(l) for p in EMAILS_DIR.glob("*.emails.jsonl") for l in p.open()]
    req_ids = [r["request_id"] for r in requests]

    pairs = []
    for e in emails:
        for rid in req_ids:
            if rid == e["request_id"]:
                label, kind = 1, "produced"
            else:
                label, kind = 0, "cross_request"
            pairs.append({
                "pair_id": f"{rid}|{e['id']}",
                "request_id": rid, "email_id": e["id"],
                "label": label, "kind": kind,
                "email_request_id": e["request_id"],
                "adjacent": ADJACENT.get(frozenset({rid, e["request_id"]})),
            })

    with (OUT_DIR / "pairs.jsonl").open("w") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")

    summary = {
        "requests": req_ids,
        "emails": len(emails),
        "emails_per_request": {rid: sum(e["request_id"] == rid for e in emails) for rid in req_ids},
        "pairs": len(pairs),
        "positives": sum(p["label"] for p in pairs),
        "negatives": sum(1 - p["label"] for p in pairs),
        "adjacent_negatives": sum(1 for p in pairs if p["adjacent"] and not p["label"]),
    }
    json.dump(summary, (OUT_DIR / "summary.json").open("w"), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
