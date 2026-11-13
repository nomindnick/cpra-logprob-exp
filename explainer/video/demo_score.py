"""Score the invented demo emails used in the public video with the project's own scorer.

Every name, agency and email here is invented for the video (no produced record is shown publicly).
The prompt, settings and scoring code are the ones the golden-set runs used (scripts/score.py).
Run from the repo root:  uv run python explainer/video/demo_score.py
Writes explainer/video/demo_scores.json
"""
import json, sys, time, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import score  # noqa: E402

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3.8:27b"
REQUEST = ("All emails sent or received by county staff between January 1, 2024 and June 30, 2024 "
           "concerning the Mill Creek Bridge repair project, including contractor bids, the "
           "engineering assessment and the construction schedule.")
EMAILS = {
    "yes": {
        "from": "Dana Whitfield <dana.whitfield@aldercounty.example>",
        "to": "Marcus Lee <marcus.lee@aldercounty.example>",
        "date": "2024-03-14", "subject": "RE: Mill Creek Bridge - revised bid tabulation",
        "attachments": ["MillCreek_BidTab_rev2.xlsx"],
        "body": ("Marcus,\n\nThe revised bid tab for the Mill Creek Bridge repair is attached. After Addendum 2 "
                 "the low bid is $1.84M, about 6% under the engineer's estimate.\n\nCan you confirm the estimate "
                 "before the board packet goes out Thursday?\n\nThanks,\nDana\n\nDana Whitfield\n"
                 "Senior Civil Engineer, Public Works"),
    },
    "no": {
        "from": "Facilities Desk <facilities@aldercounty.example>",
        "to": "All Staff <allstaff@aldercounty.example>",
        "date": "2024-03-14", "subject": "North parking lot closed Saturday for restriping",
        "body": ("The north lot will be closed this Saturday for restriping. Please move your vehicle by "
                 "Friday at 6 pm. Cars left in the lot will be towed to the south structure.\n\nFacilities Desk"),
    },
    "near": {
        "from": "Priya Raman <priya.raman@aldercounty.example>",
        "to": "Parks Front Desk <parksdesk@aldercounty.example>",
        "date": "2024-04-02", "subject": "Mill Creek Park picnic shelter reservations",
        "body": ("Reservations for the Mill Creek Park picnic shelters open April 15. If callers ask, the "
                 "footbridge by shelter 3 is open and no repairs are planned there this season.\n\n"
                 "Priya Raman\nRecreation Coordinator, Parks"),
    },
    "date": {
        "from": "Dana Whitfield <dana.whitfield@aldercounty.example>",
        "to": "Marcus Lee <marcus.lee@aldercounty.example>",
        "date": "2023-09-08", "subject": "Mill Creek Bridge - inspection photos",
        "body": ("Marcus,\n\nPhotos from this morning's Mill Creek Bridge inspection are on the shared drive. "
                 "The east abutment spalling is worse than last year.\n\nDana"),
    },
}

out = {"model": MODEL, "request": REQUEST, "system": score.SYSTEM, "emails": {}}
score.score_one(MODEL, REQUEST, EMAILS["no"])  # load the model and warm the cache
for key, e in EMAILS.items():
    text, _ = score.render_email(e)
    lp = [score.score_one(MODEL, REQUEST, e) for _ in range(3)]
    js = [score.score_json(MODEL, REQUEST, e) for _ in range(2)]
    r = lp[-1]
    out["emails"][key] = {
        "email": e, "rendered": text,
        "lp": {k: r[k] for k in ("score", "p_yes", "p_no", "residual", "first_token", "top3", "prompt_tokens")},
        "lp_total_ms": [round(x["total_ms"]) for x in lp], "lp_wall_ms": [round(x["wall_ms"]) for x in lp],
        "json": {k: js[-1][k] for k in ("score", "verdict", "confidence", "raw", "gen_tokens")},
        "json_total_ms": [round(x["total_ms"]) for x in js], "json_wall_ms": [round(x["wall_ms"]) for x in js],
    }
    print(key, "lp score", r["score"], r["top3"], "ms", out["emails"][key]["lp_total_ms"],
          "| json", js[-1]["verdict"], js[-1]["confidence"], "ms", out["emails"][key]["json_total_ms"])
    print("   ", js[-1]["raw"][:300])
(ROOT / "explainer/video/demo_scores.json").write_text(json.dumps(out, indent=1))
