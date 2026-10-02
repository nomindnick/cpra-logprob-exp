"""Build the golden-set adjudication sheet (markdown) and the browser adjudication page.

  uv run python scripts/adjudication_sheet.py

Reads  data/golden/work/prelabels.jsonl, synthetic.jsonl, acpg_roster.json, gen/job_*.json
       data/emails/sandiego.emails.jsonl, data/emails/sandiego.requests.jsonl
       scripts/adjudication_page.html   (page template; data goes in at /*__DATA__*/)
Writes data/golden/work/adjudication_items.json   one record per row to adjudicate
       docs/golden-adjudication.md               reference copy: scope, roster, every row in full
       docs/golden-adjudication.html             the page published as the adjudication artifact

Rows: every disagreement between pre-label and production origin, every '?', a random 20%
of agreements per request, and every synthetic email the verifier flagged. Calls made on the
page are exported to data/golden/work/adjudications.json, which build_golden.py reads.
"""
import json, pathlib, random, glob, datetime, re

W = pathlib.Path("data/golden/work")
SAMPLE_RATE, SEED = 0.20, 409

SCOPE = {
    "24-409": {
        "title": "Juli Beth Hinds / UCSD USP — County LUEG records",
        "window": ("2023-01-01", "2023-07-31"),
        "window_label": "Jan 1, 2023 – Jul 31, 2023 (refined scope of 5/17/24)",
        "items": [
            ["2", "Anything that includes Juli Beth Hinds, Dr. Amy Lerner, Urban Studies and Planning (USP), "
                  "Global Policy & Strategy (GPS), or UCSD in conjunction with any of those terms."],
            ["3", "Anything related to the Regional Water Equity Report (RWER) or the RDF "
                  "(the County's Regional Decarbonization Framework)."],
            ["4", "Anything referencing Hinds, Lerner, Geosyntec, USP, GPS, the RWER or the RDF (UCSD in conjunction "
                  "with any of those) sent to or from: Elise Ruiz; anyone at Murakawa Communications; anyone at Geosyntec "
                  "(incl. Ken Susillo, Megan Otto, Stephanie Zinn); anyone at the County (incl. Stephanie Gaines, "
                  "Crystal Benham, Todd Snyder, Sarah Agassi, Eden Brukman, Murtaza Baxamusa)."],
        ],
        "notes": "Item (1) of the refinement is the date window. The original request (Hinds; UCSD USP; Nathan "
                 "Fletcher; 1/1/2022 to 4/16/2024) was superseded by the 5/17/24 refinement.",
        "terms": [r"Juli\s*Beth\s*Hinds", r"\bHinds\b", r"Amy\s+Lerner", r"\bLerner\b", r"Urban\s+Studies(\s+and\s+Planning)?",
                  r"\bUSP\b", r"Global\s+Policy\s*(&|&amp;|and)\s*Strategy", r"\bGPS\b", r"\bUCSD\b", r"UC\s+San\s+Diego",
                  r"Water\s+Equity", r"\bRWER\b", r"\bRWEP\b", r"\bRDF\b", r"Decarboni[sz]ation\s+Framework", r"Geosyntec",
                  r"Murakawa", r"Elise\s+Ruiz", r"Susillo", r"Megan\s+(M\.\s+)?Otto", r"Stephanie\s+(Castle\s+)?Zinn",
                  r"Stephanie\s+Gaines", r"Crystal\s+Benham", r"Todd\s+Snyder", r"Sarah\s+Agh?assi", r"Eden\s+Brukman",
                  r"Baxamusa", r"Nathan\s+Fletcher"],
    },
    "25-3152": {
        "title": "Alpine Community Planning Group communications",
        "window": ("2024-01-01", "2025-05-31"),
        "window_label": "Jan 1, 2024 – May 31, 2025 (every item)",
        "items": [
            ["1", "All ACPG agendas and minutes."],
            ["2", "All communications between any ACPG member and another ACPG member."],
            ["3", "All communications between any ACPG member and another government agency, including the County."],
            ["4", "All communications between any ACPG member and any member of the public, including individuals or "
                  "entities with business before the group."],
        ],
        "notes": "Current and former members during the window count (see roster). The request is addressed to the "
                 "ACPG members; there is no subject-matter limit on items 2–4.",
        "terms": [],  # filled from the roster below
    },
}

RECIPE_NOTE = {}
for f in sorted(glob.glob(str(W / "gen/job_*.json"))):
    j = json.load(open(f))
    RECIPE_NOTE[f"{j['kind']}/{j['recipe']}"] = j["recipe_desc"]


def name_variants(name):
    """'Michael (Mike) M. Milligan' -> Michael M. Milligan, Michael Milligan, Mike Milligan, ..."""
    paren = re.findall(r"\(([^)]*)\)", name)
    base = re.sub(r"\s*\([^)]*\)", "", name).split()
    last = [t for t in base if t not in ("Jr.", "Sr.")][-1]
    out = {" ".join(base), f"{base[0]} {last}"}
    for p in paren:
        out.add(p if len(p.split()) > 1 else f"{p} {last}")
    return sorted(out)


def name_rx(n):
    return r"\b" + r"\s+".join(re.escape(t) for t in n.split()) + r"(?![\w])"


def window_status(rid, date):
    if not date:
        return "unknown"
    try:
        dd = datetime.date.fromisoformat(date[:10])
    except ValueError:  # 25-5982 PDF exports: "Friday, August 30, 2024 10:12 AM"
        dd = datetime.datetime.strptime(date, "%A, %B %d, %Y %I:%M %p").date()
    lo, hi = SCOPE[rid]["window"]
    day = datetime.timedelta(days=1)
    lo_d, hi_d = (datetime.date.fromisoformat(x) for x in (lo, hi))
    if lo_d - day <= dd <= lo_d or hi_d <= dd <= hi_d + day:
        return "edge"
    return "in" if lo_d <= dd <= hi_d else "out"


def email_view(e):
    return {k: e.get(k) for k in ("id", "from", "to", "cc", "date", "subject", "attachments", "body", "url")}


def main():
    emails = {e["id"]: e for e in map(json.loads, open("data/emails/sandiego.emails.jsonl"))}
    requests = {r["request_id"]: r for r in map(json.loads, open("data/emails/sandiego.requests.jsonl"))}
    roster = json.load(open(W / "acpg_roster.json"))["members"]
    pre = [json.loads(l) for l in open(W / "prelabels.jsonl")]
    synth = [json.loads(l) for l in open(W / "synthetic.jsonl")]

    terms = [r"Alpine\s+Community\s+Planning\s+Group", r"\bACPG\b", r"\bAlpine\s+CPG\b"]
    for m in roster:
        terms += [name_rx(v) for v in name_variants(m["name"])]
        terms += [a.replace(".", r"\.") for a in m.get("email_addresses", [])]
    terms += [r"\bLyon\b", r"\bSaldano\b", r"\bCossio\b", r"\bGaray\b", r"\bReimund\b", r"\bBorchard\b", r"\bMilligan\b"]
    SCOPE["25-3152"]["terms"] = terms

    rng = random.Random(SEED)
    items = []
    for rid in ["24-409", "25-3152"]:
        rows = [r for r in pre if r["request_id"] == rid]
        dis, agree = [], []
        for r in rows:
            p, o = r["prelabel"], r["origin"]
            if p == "?":
                dis.append((r, "Pre-labeler was unsure"))
            elif o == "produced" and p == "N":
                dis.append((r, f"The County produced it for {rid}; the pre-label says not responsive"))
            elif o == "other_production" and p == "R":
                dis.append((r, f"It came from another request's production; the pre-label says responsive to {rid}"))
            else:
                agree.append(r)
        k = round(SAMPLE_RATE * len(agree))
        spot = rng.sample(agree, k)
        for section, chosen in (("disagree", dis), ("spot", [(r, None) for r in spot])):
            chosen = sorted(chosen, key=lambda x: (emails[x[0]["email_id"]]["date"] or ""))
            for r, why in chosen:
                e = emails[r["email_id"]]
                items.append({
                    "key": f"{rid}~{r['email_id']}", "section": section, "request_id": rid, "kind": "real",
                    "origin": r["origin"], "origin_request": r["email_id"].split(":")[1],
                    "prelabel": r["prelabel"], "confidence": r["confidence"], "rationale": r["rationale"],
                    "note": r.get("note") or "", "why_listed": why,
                    "window": window_status(rid, e["date"]), "email": email_view(e),
                })
    for s in synth:
        flagged = (s["verify_label_correct"] is False or s["verify_recipe_followed"] is False
                   or s["verify_style_tell"] == "obvious")
        if not flagged:
            continue
        src = emails.get(s["source_id"])
        items.append({
            "key": s["id"], "section": "synth", "request_id": s["request_id"], "kind": s["kind"], "recipe": s["recipe"],
            "recipe_desc": RECIPE_NOTE.get(f"{s['kind']}/{s['recipe']}", ""), "label": s["label"],
            "why_label": s["why_label"], "verify_label_correct": s["verify_label_correct"],
            "verify_recipe_followed": s["verify_recipe_followed"], "verify_style_tell": s["verify_style_tell"],
            "verify_problem": s["verify_problem"], "window": window_status(s["request_id"], s["date"]),
            "email": email_view(s), "source": email_view(src) if src else None,
        })

    req_out = {}
    for rid, sc in SCOPE.items():
        req_out[rid] = {**sc, "request_date": requests[rid]["request_date"], "departments": requests[rid]["departments"],
                        "url": requests[rid]["url"], "full_text": requests[rid]["request_text"]}
    data = {"generated": datetime.date.today().isoformat(), "requests": req_out, "roster": roster, "items": items}
    json.dump(data, (W / "adjudication_items.json").open("w"), ensure_ascii=False, indent=1)

    write_markdown(data)
    tpl = pathlib.Path("scripts/adjudication_page.html").read_text()
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    pathlib.Path("docs/golden-adjudication.html").write_text(tpl.replace("/*__DATA__*/null", blob))
    counts = {s: sum(1 for i in items if i["section"] == s) for s in ("disagree", "spot", "synth")}
    print(json.dumps(counts))


def fence(text):
    text = (text or "").replace("```", "ʼʼʼ")
    return f"```text\n{text.strip()}\n```"


def write_markdown(data):
    L = ["# Golden set — adjudication sheet", "",
         f"Generated {data['generated']} by `scripts/adjudication_sheet.py`. Calls are made on the adjudication page "
         "(`docs/golden-adjudication.html`, published as an artifact) and exported to "
         "`data/golden/work/adjudications.json`, which `scripts/build_golden.py` reads. This file is the reference copy.",
         "", "**Real rows:** R = responsive to the request as written, N = not responsive. Responsiveness only; "
         "privilege and exemptions do not matter here.",
         "**Synthetic rows:** K = keep the intended label, F = flip it, D = drop the email from the set.", ""]
    for rid, r in data["requests"].items():
        L += [f"## Request {rid} — {r['title']}", "",
              f"Filed {r['request_date']} · {r['departments'] or 'department not listed'} · {r['url']}", "",
              f"**Window:** {r['window_label']}", ""]
        L += [f"- **Item {n}.** {t}" for n, t in r["items"]]
        L += ["", r["notes"], "", "<details><summary>Full request text</summary>", "", fence(r["full_text"]), "", "</details>", ""]
        if rid == "25-3152":
            L += ["### ACPG members during the window", "", "| name | role | period | addresses |", "|--|--|--|--|"]
            for m in data["roster"]:
                L.append(f"| {m['name']} | {m.get('role','')} | {m.get('period','')} | {', '.join(m.get('email_addresses', []))} |")
            L.append("")
    names = {"disagree": "Disagreements and unclear", "spot": "Random 20% of agreements (spot check)",
             "synth": "Synthetic emails flagged by the verifier"}
    for sec in ("disagree", "spot", "synth"):
        rows = [i for i in data["items"] if i["section"] == sec]
        L += [f"## {names[sec]} ({len(rows)})", ""]
        for n, i in enumerate(rows, 1):
            e = i["email"]
            L += [f"### {sec[0].upper()}{n} · {i['request_id']} · {e['subject'] or '(no subject)'}", "",
                  f"`{i['key']}`", ""]
            if sec == "synth":
                L += [f"- **Kind / recipe:** {i['kind']} / {i['recipe']} — {i['recipe_desc']}",
                      f"- **Intended label:** {'responsive (1)' if i['label'] else 'not responsive (0)'}",
                      f"- **Why (generator):** {i['why_label']}",
                      f"- **Verifier:** label ok = {i['verify_label_correct']}, recipe ok = {i['verify_recipe_followed']}, "
                      f"style tell = {i['verify_style_tell']}",
                      f"- **Verifier's problem:** {i['verify_problem']}"]
            else:
                L += [f"- **Listed because:** {i['why_listed'] or 'random spot check of an agreement'}",
                      f"- **Origin:** {'produced for ' + i['request_id'] if i['origin'] == 'produced' else 'other production (' + i['origin_request'] + ')'}",
                      f"- **Pre-label:** {i['prelabel']} ({i['confidence']}) — {i['rationale']}"]
                if i["note"]:
                    L.append(f"- **Note:** {i['note']}")
            L += [f"- **From:** {e['from']}", f"- **To:** {e['to']}"]
            if e.get("cc"):
                L.append(f"- **Cc:** {e['cc']}")
            L += [f"- **Date:** {e['date']} (window: {i['window']})",
                  f"- **Attachments:** {', '.join(e['attachments']) if e.get('attachments') else 'none'}"]
            if e.get("url"):
                L.append(f"- **Original:** {e['url']}")
            L += ["", fence(e["body"]), ""]
            if sec == "synth" and i.get("source"):
                L += ["<details><summary>Original email it was edited from</summary>", "", fence(i["source"]["body"]), "", "</details>", ""]
    pathlib.Path("docs/golden-adjudication.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
