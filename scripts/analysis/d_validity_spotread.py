"""D2 spot-read: a fixed random sample of real negatives, hard negatives and synthetic positives, with my notes.

  uv run python scripts/analysis/d_validity_spotread.py [--full | --notes]

Sample (random.Random(11), drawn per group from data/golden/emails.jsonl in pair_id order):
  10 real negatives (5 per request), 10 hard negatives (one per recipe per request),
  10 synthetic positives (2 close calls, 2 privileged... per request: see GROUPS).
Prints, for each: the headers the models see, the first 600 characters of the body, and for synthetic emails the
lines the edit added relative to its source email (difflib, first 12). --full prints whole bodies (up to 8,000
characters, the model's cap).

NOTES holds my reading of each sampled email (judgment, written after reading this output). The script prints
them next to each email and tallies the realism codes:
  real    reads like an ordinary email of this kind
  tell    plausible, but with a detail that reads as generated or contrived (named in the note)
  contrived  the scenario or wording would be unusual in a real mailbox
Stdlib only, deterministic.
"""
import argparse
import collections
import difflib
import json
import random
import sys

sys.path.insert(0, "scripts/analysis")
from d_validity_common import emails  # noqa: E402

GROUPS = [  # (label, kind, recipe or None, request, how many)
    ("real negative", "real_negative", None, "24-409", 5),
    ("real negative", "real_negative", None, "25-3152", 5),
] + [("hard negative", "hard_negative", rc, rid, 1)
     for rc in ("forwarded_no_content", "keyword_in_signature_or_newsletter", "keyword_unrelated_sense",
                "same_people_different_subject", "same_subject_wrong_date")
     for rid in ("24-409", "25-3152")] + [
    ("synthetic positive", "close_call_positive", None, "24-409", 2),
    ("synthetic positive", "close_call_positive", None, "25-3152", 2),
    ("synthetic positive", "privileged_positive", None, "24-409", 2),
    ("synthetic positive", "privileged_positive", None, "25-3152", 1),
    ("synthetic positive", "exempt_other_positive", None, "24-409", 1),
    ("synthetic positive", "exempt_other_positive", None, "25-3152", 2),
]

# pair_id -> (code, note). Filled in after reading the printed sample; judgment, not measurement.
NOTES = {
    # real negatives
    "24-409|sandiego:25-3152:48517858": ("real", "County staff invite to a 2024 cannabis-program stakeholder meeting. Ordinary "
                                         "email; 2024 date and no 24-409 term, so a 24-409 search would never return it."),
    "24-409|sandiego:25-5982:55059062": ("real", "Advocacy mailing-list forward (2025, per the body). Unrelated topic, no date "
                                         "header, no 24-409 term."),
    "24-409|sandiego:25-3152:48518074": ("real", "Construction-estimate spam bcc'd to the ACPG chair. Trivially non-responsive "
                                         "to 24-409."),
    "24-409|sandiego:25-5982:55058924": ("real", "2025 CAIR banquet sponsorship thread from another custodian search. Off "
                                         "topic, out of window."),
    "24-409|sandiego:25-5982:55059129": ("real", "2025 equity-office report comments. Off topic, out of window."),
    "25-3152|sandiego:25-4697:52663416": ("real", "Internal PDS graphics request on another project (Sept 2025). No ACPG "
                                          "member, after the window."),
    "25-3152|sandiego:24-409:33733067": ("real", "Internal County thread (April 2023) about community-group contacts. No "
                                         "ACPG member, before the window."),
    "25-3152|sandiego:24-409:33733023": ("real", "Food-system nonprofit to County staff, Feb 2023. No ACPG member, before "
                                         "the window."),
    "25-3152|sandiego:24-409:33733134": ("real", "Internal flood-control scheduling, March 2023. No ACPG member, before the "
                                         "window."),
    "25-3152|sandiego:25-4697:52663454": ("real", "Internal PDS docketing note, Sept 2025. No ACPG member, after the window."),
    # hard negatives
    "24-409|synth:24-409:06:07": ("real", "'See below' forward of a software-subscription notice to Elise Ruiz. Convincing, "
                                  "but it has no 24-409 term, so only a sweep of Ruiz's whole mailbox would return it."),
    "25-3152|synth:25-3152:18:03": ("real", "Staff FYI forward of a Parks notice sent to another planning group. Convincing; "
                                    "no ACPG member on it, so a member-address search would not return it."),
    "24-409|synth:24-409:05:02": ("real", "GovDelivery stormwater bulletin; a named County PM appears only as the 'sent to' "
                                  "address. Convincing bulk notice; no 24-409 term in the content."),
    "25-3152|synth:25-3152:17:08": ("real", "Community-center weekly newsletter to a member of the public; the ACPG meeting is "
                                    "one line in the events list. Convincing."),
    "24-409|synth:24-409:07:07": ("real", "The real water-equity planning thread rewritten as a 'Tree Equity' forum with the "
                                  "same consultant and staff. Convincing; a genuine near miss for a reader."),
    "25-3152|synth:25-3152:19:09": ("real", "Body identical to a real 25-3152-production email (a scoping letter to another "
                                    "planning group); 'synthetic' only in its label."),
    "24-409|synth:24-409:03:01": ("tell", "Named consultant and County PM chatting about a parking-lot closure. Plausible, but "
                                  "the thread repeats a near-identical 'no dates posted yet' message, which reads as "
                                  "generated. The verifier called it responsive (Geosyntec in the address); the owner kept "
                                  "it negative."),
    "25-3152|synth:25-3152:15:02": ("real", "Misaddressed vendor lease emails to the chair. Realistic; responsive under the "
                                    "request's literal 'any member and the public' wording, negative only under the owner's "
                                    "purely-personal call (findings-golden §9). The label is a legal judgment."),
    "24-409|synth:24-409:04:07": ("real", "The real RWER kickoff thread with every date moved to 2025. Convincing; a "
                                  "date-limited search would exclude it before review."),
    "25-3152|synth:25-3152:16:04": ("real", "Real member-public thread moved back one year (two quoted 'wrote' lines and the "
                                    "header date). Convincing; a date-limited search would exclude it."),
    # synthetic positives
    "24-409|synth:24-409:00:04": ("real", "One natural sentence ('hold off on anything RWER') added to a real consultant "
                                  "thread; 'RWER' removed from the subject. Reads as real."),
    "24-409|synth:24-409:00:02": ("real", "One sentence changed to mention reviewing the RWER. Reads as real."),
    "25-3152|synth:25-3152:13:07": ("real", "County staff answering the chair's personal building-records question, plus a "
                                    "one-line agenda note. Plausible; responsive from the headers alone (staff to a "
                                    "member), so the 'marginal mention' adds nothing for this request."),
    "25-3152|synth:25-3152:14:02": ("real", "Real APG report with one thank-you line added; the line sits past the 8,000-"
                                    "character cap, so the model sees only the chair as one of many recipients."),
    "24-409|synth:24-409:08:01": ("tell", "New Deputy County Counsel email under a privilege banner that names UCSD, "
                                  "Geosyntec, 'JB' and Dr. Lerner in one paragraph. Plausible, but denser in request terms "
                                  "than most real emails."),
    "24-409|synth:24-409:09:02": ("tell", "Staff forwarding numbered County Counsel advice on the RWER flyer, Murakawa's "
                                  "registrant list and GovDelivery. Tidy and on-topic in a way that reads as written to "
                                  "order."),
    "25-3152|synth:25-3152:21:04": ("tell", "County Counsel memo to the chair citing Gov. Code 54956 and 47 U.S.C. 332 under "
                                    "a privilege / work-product banner. Fluent and polished; plausible but likely easier "
                                    "than a real privileged email."),
    "24-409|synth:24-409:11:09": ("real", "One sentence about reduced hours after surgery added to a real RWER thread. Reads "
                                  "as real; otherwise a copy of a real positive."),
    "25-3152|synth:25-3152:22:05": ("real", "A few sentences about a ranger complaint added to a real member-public email. "
                                    "Reads as real."),
    "25-3152|synth:25-3152:22:00": ("real", "One 'still a working draft' caveat added to a real County-to-chair email. Reads "
                                    "as real."),
}


def sample():
    E = emails(); rng = random.Random(11); out = []
    for lab, kind, rc, rid, n in GROUPS:
        pool = sorted(p for p, e in E.items() if e["kind"] == kind and e["request_id"] == rid
                      and (rc is None or e["recipe"] == rc))
        out += [(lab, p) for p in rng.sample(pool, n)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--notes", action="store_true", help="print only a table of the sampled emails, my notes and the tally")
    a = ap.parse_args()
    E = emails()
    if a.notes:
        tally = collections.Counter()
        print("| group | pair | kind / recipe | date | subject | code | note |")
        print("|---|---|---|---|---|---|---|")
        for lab, p in sample():
            e = E[p]; code, note = NOTES.get(p, ("—", "—")); tally[(lab, code)] += 1
            subj = (e.get("subject") or "").replace("|", "/")[:70]
            print(f"| {lab} | `{p.replace('|', ' · ')}` | {e['kind']}{' / ' + e['recipe'] if e['recipe'] else ''} | "
                  f"{(e.get('date') or '—')[:25]} | {subj} | {code} | {note} |")
        print()
        print("| group | real | tell | contrived |")
        print("|---|---|---|---|")
        for lab in ("real negative", "hard negative", "synthetic positive"):
            print(f"| {lab} | {tally[(lab, 'real')]} | {tally[(lab, 'tell')]} | {tally[(lab, 'contrived')]} |")
        print()
        return
    syn = {s["id"]: s for s in map(json.loads, open("data/golden/work/synthetic.jsonl"))}
    src = {e["id"]: e for e in map(json.loads, open("data/emails/sandiego.emails.jsonl"))}
    tally = collections.Counter()
    print("# D2 spot-read sample\n")
    for lab, p in sample():
        e = E[p]
        print(f"## {lab} · {p} · {e['kind']}{' / ' + e['recipe'] if e['recipe'] else ''}\n")
        for k in ("from", "to", "cc", "bcc", "date", "subject"):
            if e.get(k):
                v = e[k] if len(e[k]) < 300 else e[k][:300] + " …"
                print(f"- {k}: {v}")
        if e.get("attachments"):
            print(f"- attachments: {', '.join(e['attachments'])[:300]}")
        print(f"- body chars: {len(e['body'] or '')}; rationale: {(e.get('rationale') or '')[:400]}")
        body = (e["body"] or "")[:8000 if a.full else 600]
        print("\n```text\n" + body + "\n```\n")
        if e["origin"] == "synthetic":
            s = syn[e["id"]]; o = src.get(s["source_id"])
            print(f"- source {s['source_id']}: subject {(o or {}).get('subject')!r}, date {(o or {}).get('date')}")
            print(f"- verifier: label ok {s['verify_label_correct']}, recipe ok {s['verify_recipe_followed']}, "
                  f"style tell {s['verify_style_tell']}")
            if o:
                added = [l[1:] for l in difflib.ndiff((o["body"] or "").splitlines(), (e["body"] or "").splitlines())
                         if l.startswith("+ ") and l[2:].strip()]
                print(f"- lines added by the edit ({len(added)}; first 12):")
                for l in added[:12]:
                    print(f"    + {l.strip()[:220]}")
            print()
        if p in NOTES:
            code, note = NOTES[p]; tally[(lab, code)] += 1
            print(f"**My note ({code}):** {note}\n")
    if NOTES:
        print("## Tally of my realism codes\n")
        print("| group | real | tell | contrived |")
        print("|---|---|---|---|")
        for lab in ("real negative", "hard negative", "synthetic positive"):
            print(f"| {lab} | {tally[(lab, 'real')]} | {tally[(lab, 'tell')]} | {tally[(lab, 'contrived')]} |")
        print()


if __name__ == "__main__":
    main()
