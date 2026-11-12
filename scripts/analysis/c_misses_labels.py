"""Branch C3 and C5: the reading of every consensus miss and consensus false positive, and how much each
candidate label would move the headline if it were flipped.

  uv run python scripts/analysis/c_misses_labels.py

Prints:
  C3a  one row per consensus item: what it is, why it has its label, the analyst's judgment of the label
       (right / arguable / likely wrong) and the model error type. The text columns are the analyst's
       reading (coded in JUDGMENTS below, after reading c_misses_read.py's output in full); the count
       columns are computed.
  C3b  tallies of judgments and error types.
  C3c  every 24-409 email with Geosyntec only in its addresses (no listed term in the subject or the visible
       body), with its label and the human call: a consistency check on one label question.
  C5a  re-check list: the candidates judged arguable or likely wrong, ordered by the mean change in elim@98
       across the 7 models if that one label were flipped (per-model change in elim@98 and AUROC).
  C5b  the same for label questions that cover a group of emails, flipped together (and, for RDF, dropped).
  C5c  every consensus item, flipped one at a time (appendix).
Nothing is written to data/. elim@98 and thr98 are recomputed on the flipped labels (pooled, in-sample).
"""
import json
import re

from c_misses_common import (ACPG_RE, ADDR_RE, MAX_BODY_CHARS, NAMES, TERMS_24409, auc, elim98, emails, in_window,
                             load, n_recipients, pairs, per_model, reading_list, short, table, who)

R, A, W = "right", "arguable", "likely wrong"
# error types (model side)
MANY = "member is one of many recipients"
AUTO = "automated notice to a member"
ONE = "topic carried by one acronym or one line"
CAP = "hook only past the 8,000-char body cap"
DATE = "date outside the request window"
NAMED = "named correspondent, no listed term (24-409 item 4 needs both)"
GEO = "named correspondent; Geosyntec only in the addresses"
FOOT = "term only in a footer, signature or link list"
SENSE = "term in an unrelated sense, or a near-name"
NONMEM = "non-member taken for a member"
FWD = "forward or auto-reply with no content"
PERS = "purely-personal exception not applied"

# short id -> (what it is, why it has its label, judgment, error type, note)
JUDGMENTS = {
    # ---- consensus misses (label 1) ----
    "24-409 real 33733472": ("OSEJ staff thread on the Governor's energy plan; one message gives a section-by-section 'alignment with RDF' summary.",
                             "County production; item 3 (related to the RDF); in window.", R, ONE,
                             "The subject never names a request term; RDF appears only as an acronym in the body."),
    "24-409 syn 00:03": ("Rain-barrel flyer thread; one added line says Elise may have a contact list 'from the RWER outreach'.",
                         "Item 4: from Gaines (named) and refers to the RWER; in window. Marginal by design.", R, ONE, ""),
    "24-409 syn 02:01": ("Climate Action Research Grant thread with UCSD's Lawrence Frank; the 'UC San Diego - Dept of Urban Studies and Planning' signature lies past the body cap.",
                         "Item 2 via the signature; the owner kept it (findings §9) to count a miss the system would really make.", R, CAP,
                         "No model sees the hook; the visible text has UCSD only in addresses and a Zoom URL."),
    "25-3152 real 48517463": ("Lakeside CPG chair's reply-all 'Excellent report Robin!' on an APG report about SANDAG; ACPG chair Lyon is one of many Cc's.",
                              "County production; items 3/4 read literally (a member received it); owner confirmed R.", R, MANY,
                              "Narrower reading possible: Lyon is a passive recipient and nothing concerns ACPG business."),
    "25-3152 real 48517567": ("Lakeside chair's 'Great news!!' reply-all on a forwarded SANDAG legislative update; Lyon one of many Cc's.",
                              "County production; items 3/4; owner confirmed R.", R, MANY, "Same narrower-reading question."),
    "25-3152 real 48517588": ("Lakeside chair asks 'Is this meeting still today?' on a County hold for the CPG chairs' meeting; Lyon first in a long Cc line.",
                              "County production; item 3 (County staff on the thread). Not human-adjudicated (Opus R, high).", R, MANY, ""),
    "25-3152 real 48517769": ("Lakeside chair's 'I plan to attend' on a County DPW Traffic Advisory Committee agenda thread; Lyon one of many Cc's.",
                              "County production; items 3/4; owner confirmed R.", R, MANY, ""),
    "25-3152 real 48517957": ("Fallbrook PG chair forwards her BESS meeting comments to all CPG chairs; 'Travis Lyon (Alpine)' one of many Cc's.",
                              "County production; items 3/4. Not human-adjudicated (Opus R, high).", R, MANY, ""),
    "25-3152 real 48518005": ("Fallbrook PG chair sends her cannabis DEIR comment draft to the countywide planning-group chairs, Lyon among them.",
                              "County production; items 3/4. Not human-adjudicated (Opus R, high).", R, MANY, ""),
    "25-3152 real 48518202": ("Automated password-reset email from the Clerk of the Board's eFile (Form 700) system to Lyon.",
                              "County production; item 3 read literally (County to a member); owner confirmed R.", R, AUTO,
                              "Trivial content; relates to his filing duty as a member."),
    "25-3152 syn 20:06": ("Synthetic copy of 48517588 with County Counsel's privileged Form 700 advice quoted.",
                          "Item 3; privilege does not affect responsiveness.", R, MANY, ""),
    # ---- consensus false positives, 24-409 (label 0) ----
    "24-409 syn 03:01": ("Megan Otto (Geosyntec) thanks Gaines for a heads-up about a County parking-lot closure.",
                         "Geosyntec only in the addresses. Owner call 2026-11-08: responsive (item 4, read literally).", R, GEO,
                         "Kept (K) until 2026-11-08, then flipped for consistency with 03:04, 03:07, 06:01 and 06:03 (C3c)."),
    "24-409 syn 03:02": ("OSEJ team plans a welcome lunch for a new hire; quotes Brukman's all-staff announcement (Aghassi, Baxamusa, Snyder, Ruiz copied).",
                         "County staff only; no listed term.", R, NAMED, ""),
    "24-409 syn 03:05": ("Gaines and a colleague promote the LUEG summer picnic flyer (from Elise Ruiz).",
                         "County staff only; no listed term.", R, NAMED, ""),
    "24-409 syn 03:09": ("Megan Otto (Geosyntec) organizes a team volunteer shift at a food bank; Zinn (Geosyntec), Gaines and Ruiz reply.",
                         "Geosyntec only in the addresses. Owner call 2026-11-08: responsive (item 4, read literally).", R, GEO,
                         "Kept (K) until 2026-11-08, then flipped for consistency with the four earlier flips (C3c)."),
    "24-409 syn 04:00": ("Ruiz tells Geosyntec that its staff will present for UCSD at the Water Assembly.",
                         "On topic but after both the refined (1/1-7/31/2023) and original (2022 to 4/16/2024) windows.", R, DATE, ""),
    "24-409 syn 04:02": ("Lynch and Baxamusa on the UCSD climate grant and RDF.",
                         "Outside both windows.", R, DATE, ""),
    "24-409 syn 04:03": ("Geosyntec RWER Task 3.B deliverable to Gaines.",
                         "Outside the refined window. Inside the original window, but the original request does not cover RWER.", R, DATE, ""),
    "24-409 syn 04:04": ("OSEJ/RDF steering-committee follow-ups (Murakawa, RWER).",
                         "Outside the refined window; the original request's subjects (Hinds, UCSD USP, Fletcher) are absent.", R, DATE, ""),
    "24-409 syn 04:05": ("Board-office staff help promote the Water Equity assembly.", "Outside both windows.", R, DATE, ""),
    "24-409 syn 04:06": ("Ruiz forwards Geosyntec's RWER interview agenda to Gaines.",
                         "Outside the refined window; the original request does not cover RWER.", R, DATE,
                         "The 27b jsonR answer applied the original request's 2022 window."),
    "24-409 syn 04:07": ("RWER interview scheduling between Geosyntec and County agriculture staff.", "Outside both windows.", R, DATE, ""),
    "24-409 syn 04:08": ("RWER standing-meeting action items between Geosyntec and Ruiz.",
                         "Outside the refined window; mentions UCSD studies but not the USP department.", R, DATE, ""),
    "24-409 syn 04:09": ("Earlier message of the same RWER thread.", "Same as 04:08.", R, DATE, ""),
    "24-409 syn 05:00": ("Zoom webinar confirmation to Ruiz from ULI; 'UC San Diego' only in an academic-partner footer.",
                         "Items 2/4 count UCSD only together with Hinds, Lerner, USP or GPS.", R, FOOT, ""),
    "24-409 syn 05:05": ("SharePoint notice that Brukman commented on an intern onboarding checklist, sent to Ruiz.",
                         "Named people only; no listed term.", R, NAMED, ""),
    "24-409 syn 05:06": ("IAP2 newsletter forwarded to Ruiz; 'UC San Diego Extended Studies' in the footer.", "UCSD alone is not enough.", R, FOOT, ""),
    "24-409 syn 05:07": ("Gaines forwards a Creek to Bay cleanup blast; UC San Diego in the sponsor footer.", "UCSD alone is not enough.", R, FOOT, ""),
    "24-409 syn 06:04": ("Ruiz forwards an IT 'SharePoint access' notice to Gaines and Benham with 'FYI'.", "Named people only; no listed term.", R, FWD, ""),
    "24-409 syn 06:06": ("Ruiz's out-of-office auto-reply to a County colleague ('IRWM contact list').",
                         "No listed term and no Geosyntec address (unlike flipped 06:01, sent to Geosyntec).", R, FWD, ""),
    "24-409 syn 06:09": ("Lynch tells Baxamusa she will call him; subject 'Climate Action Research Grant'.", "Named people only; no listed term.", R, FWD, ""),
    "24-409 syn 07:00": ("LeSar consultant schedules a Regional Fair Housing interview; Ruiz copied.", "'Regional ... Report' and 'equity' are not the RWER.", R, SENSE, ""),
    "24-409 syn 07:01": ("OSEJ Zero Waste steering agenda: 'RDF proposal' means refuse-derived fuel; Appel, Baxamusa, Ruiz.",
                         "Not the Regional Decarbonization Framework. Owner call 2026-11-11: not responsive (the requester's evident intent).", R, SENSE,
                         "07:09, the same RDF sense, was dropped 2026-10-31 and reinstated as a hard negative 2026-11-11."),
    "24-409 syn 07:09": ("Fallbrook Climate Action Team invites Ruiz to present; asks about 'RDF (refuse derived fuel)'.",
                         "Not the Regional Decarbonization Framework. Owner call 2026-11-11: not responsive.", R, SENSE, ""),
    "24-409 syn 07:02": ("Heat-mapping volunteer flyer; 'GPS-linked temperature sensors'; Gaines, Ruiz.", "The request defines GPS as global policy & strategy. Owner call 2026-11-11: not responsive.", R, SENSE, ""),
    "24-409 syn 07:03": ("Meeting invite on collecting GPS coordinates for outfalls; from Gaines.", "Same: GPS in its navigation sense. Owner call 2026-11-11: not responsive.", R, SENSE, ""),
    "24-409 syn 07:04": ("Murakawa event logistics naming 'Dr. Steven Lerner' as a speaker; Baxamusa, Ruiz.", "A different Lerner from Dr. Amy Lerner.", R, SENSE,
                         "A string search for 'Lerner' would hit it."),
    "24-409 syn 07:06": ("Board-office staff help promote a Tree Equity forum (to Ruiz).", "'Equity' alone is not the RWER.", R, SENSE, ""),
    "24-409 syn 07:07": ("Murakawa's poll question for a Tree Equity forum; Ruiz, Gaines.", "No listed term; Murakawa as a correspondent is not enough.", R, SENSE, ""),
    "24-409 syn 07:08": ("County staff on a CASQA abstract about Regional Water Quality Equivalency (WQE).", "A different program from the RWER.", R, SENSE, ""),
    # ---- consensus false positives, 25-3152 (label 0) ----
    "25-3152 syn 15:01": ("Lyon schedules a TV interview about his family's home-insurance non-renewal; signs as ACPG Chair.",
                          "Owner call 2026-11-08: responsive. Copying the ACPG Chair brings it in.", R, PERS,
                          "Purely personal by extension 2026-10-31 to 2026-11-08; he writes to the press under his official title."),
    "25-3152 syn 15:02": ("md7 writes to Lyon about a rooftop cell-site lease on a building he does not own; he says 'wrong Travis'.",
                          "Owner call 2026-11-08: responsive.", R, PERS,
                          "Purely personal by extension 2026-10-31 to 2026-11-08; misdirected business mail from md7, an applicant before the group."),
    "25-3152 syn 15:03": ("Two members arrange a fishing trip.", "Owner: purely personal (San Jose).", R, PERS, ""),
    "25-3152 syn 15:04": ("Lyon's Mother's Day brunch reservation sent to the wrong Martha (a County planner).",
                          "Owner: purely personal.", R, PERS, "The verifier called the synthetic implausible (applicant's consultants copied)."),
    "25-3152 syn 15:05": ("SDG&E service-order confirmation for Lyon's home panel upgrade.", "Owner: purely personal (decided directly).", R, PERS, ""),
    "25-3152 syn 15:06": ("Lyon warns a County planner and an applicant's representative that his ACPG account was hacked; signs as Chair.",
                          "Owner call 2026-11-08: responsive.", R, PERS,
                          "Purely personal by extension 2026-10-31 to 2026-11-08; concerns the account he uses for group business."),
    "25-3152 syn 15:08": ("Lyon cancels a backyard BBQ at his house (bcc list).", "Owner: purely personal.", R, PERS, ""),
    "25-3152 syn 15:09": ("Lyon sends his daughter's Girl Scout cookie order form to all members.", "Owner: purely personal (decided directly).", R, PERS, ""),
    "25-3152 syn 16:00": ("Member of the public asks Lyon for ACPG Loveland support letters.", "Before 1/1/2024.", R, DATE, ""),
    "25-3152 syn 16:01": ("A member sends Lyon her apology for missing a meeting.", "After 5/31/2025.", R, DATE, ""),
    "25-3152 syn 16:02": ("Member replies to Lyon's forward of an MUP scoping letter.", "After 5/31/2025.", R, DATE, ""),
    "25-3152 syn 16:04": ("Loveland support-letter follow-up to Lyon.", "Before 1/1/2024.", R, DATE, ""),
    "25-3152 syn 16:05": ("Nonprofit intern asks Lyon to present at an ACPG meeting.", "After 5/31/2025.", R, DATE, ""),
    "25-3152 syn 16:06": ("County hold for a CPG chairs' meeting, Lyon a recipient.", "After 5/31/2025.", R, DATE, ""),
    "25-3152 syn 16:07": ("Loveland 'Sunrise to Sunset' thread copying three members.", "Before 1/1/2024.", R, DATE, ""),
    "25-3152 syn 16:08": ("County PDS to Lyon on ACPG vacancies and roster.", "After 5/31/2025.", R, DATE, ""),
    "25-3152 syn 17:00": ("State Water Board consultant writes to the Descanso and Pine Valley groups; ACPG only in a link list.",
                          "No ACPG member is a party; not an agenda or minutes.", R, FOOT, ""),
    "25-3152 syn 17:01": ("Nonprofit intern writes to three other planning groups; ACPG named in her signature footer.", "No member is a party.", R, FOOT,
                          "The 27b jsonR answer took svcpg4@gmail.com (Spring Valley) for the ACPG address."),
    "25-3152 syn 17:02": ("PDS scoping-letter notice to the applicant (md7); ACPG only in the Board Policy I-1 boilerplate.", "No member is a party.", R, FOOT, ""),
    "25-3152 syn 17:05": ("Campo PG list reply on remote attendance; ACPG in a resources link list (Lyon removed from the Cc).", "No member is a party.", R, FOOT, ""),
    "25-3152 syn 17:06": ("APG sends draft standing rules to other groups; 'Alpine CPG Standing Rules' in a reference list.", "No member is a party.", R, FOOT, ""),
    "25-3152 syn 18:03": ("County-to-County FYI forward of a Parks fee notice sent to the Pine Valley group.", "No member is a party.", R, FWD, ""),
    "25-3152 syn 18:07": ("Curt Dean (Alpine Design Review Board) forwards a PDS MUP notice to md7.", "Dean is not on the ACPG roster.", R, NONMEM,
                          "The 27b jsonR answer called Dean 'a known ACPG member'."),
    "25-3152 syn 18:08": ("County planner's out-of-office reply; subject quotes 'ACPG Regular Meeting Agenda'.", "Not an agenda; no member is a party.", R, FWD, ""),
    "25-3152 syn 19:00": ("APG (Association of Planning Groups) draft minutes between two non-members.", "APG is not the ACPG.", R, SENSE, ""),
    "25-3152 syn 19:01": ("County planner sends the Alpine ODS checklist to Curt Dean of the Alpine Design Review Board.", "The DRB is a separate body.", R, SENSE, ""),
    "25-3152 syn 19:02": ("Member of the public to County staff, copying Patrick Brown (Julian), not member Kim Brown.", "No member is a party.", R, NONMEM,
                          "The 27b jsonR answer called the sender 'a known ACPG member'."),
    "25-3152 syn 19:03": ("Member of the public writes to the APG chair about speaking at APG.", "APG is not the ACPG; no member is a party.", R, SENSE, ""),
    "25-3152 syn 19:08": ("Curt Dean self-forwards the County's Design Review Board presentation.", "The DRB is a separate body.", R, SENSE, ""),
}

# label questions that cover a group (C5b); ids are short ids
GROUPS = [
    # Decided by the owner 2026-11-08 and 2026-11-11; "flip" reverses the current label, so each row shows what the
    # other answer would have done.
    ("Q1 Geosyntec only in the addresses: 03:01, 03:09 back to non-responsive (owner: responsive, 2026-11-08)",
     ["24-409 syn 03:01", "24-409 syn 03:09"], "flip"),
    ("Q2 RDF = refuse-derived fuel: 07:01 and 07:09 to responsive (owner: not responsive, 2026-11-11)", ["24-409 syn 07:01", "24-409 syn 07:09"], "flip"),
    ("Q2' RDF = refuse-derived fuel: 07:01 and 07:09 dropped (07:09 was dropped until 2026-11-11)", ["24-409 syn 07:01", "24-409 syn 07:09"], "drop"),
    ("Q3 15:01, 15:02, 15:06 back to purely personal (owner: responsive, 2026-11-08)", ["25-3152 syn 15:01", "25-3152 syn 15:02", "25-3152 syn 15:06"], "flip"),
    ("Q4 the six emails still 'purely personal' (15:03, 15:04, 15:05, 15:07, 15:08, 15:09) to responsive",
     [f"25-3152 syn 15:0{i}" for i in (3, 4, 5, 7, 8, 9)], "flip"),
    ("Q5 one member among many recipients: the 7 such consensus misses to non-responsive (owner: responsive, 2026-11-08)",
     ["25-3152 real 48517463", "25-3152 real 48517567", "25-3152 real 48517588", "25-3152 real 48517769",
      "25-3152 real 48517957", "25-3152 real 48518005", "25-3152 syn 20:06"], "flip"),
]


from golden_counts import NFLIP, NN, NP, NR, N_ALL, N_NEG, N_POS  # noqa: E402,F401  (current golden-set counts)


def first_term(e, rid):
    """Character offset in the body of the first listed 24-409 term (addresses and URLs blanked out, same length),
    or of the first ACPG mention for 25-3152; '—' if none. The models see characters 0 to 7,999."""
    body = ADDR_RE.sub(lambda m: " " * len(m.group(0)), e.get("body") or "")
    pats = TERMS_24409 if rid == "24-409" else [ACPG_RE.pattern]
    hits = [m.start() for t in pats for m in [re.search(t, body)] if m]
    return f"{min(hits):,}" if hits else "—"


def modified(rows, ids, how):
    if how == "drop":
        return [r for r in rows if r["pair_id"] not in ids]
    return [{**r, "label": 1 - r["label"]} if r["pair_id"] in ids else r for r in rows]


def deltas(runs, ids, how):
    out = {}
    for m, rows in runs.items():
        if not any(r["pair_id"] in ids for r in rows):
            out[m] = None
            continue
        new = modified(rows, ids, how)
        out[m] = (elim98(new) - elim98(rows), auc(new) - auc(rows))
    return out


def fmt_pp(x):
    return "—" if x is None else f"{100 * x:+.1f}"


def main():
    main_runs, roster_runs, js, _, _ = load()
    P, E = pairs(), emails()
    pm, pr = per_model(main_runs), per_model(roster_runs)
    S = {m: {x["pair_id"]: x for x in rows} for m, rows in main_runs.items()}
    ms, fs = reading_list(main_runs, roster_runs)
    by_short = {short(p): p for p in ms + fs}
    missing = sorted(set(by_short) - set(JUDGMENTS)); extra = sorted(set(JUDGMENTS) - set(by_short))
    assert not missing, missing  # extra = judged earlier, no longer on the reading list after a relabel
    adj = json.load(open("data/golden/work/adjudications.json"))
    call = lambda p: (adj.get(P[p]["email_id"]) or adj.get(f"{P[p]['request_id']}~{P[p]['email_id']}") or {}).get("call", "")

    print("# Branch C: label reading and label-flip sensitivity\n")
    if extra:
        print("Judged earlier but no longer consensus items (relabeled by the owner on 2026-11-08): "
              + ", ".join(extra) + ".\n")
    # ---- C3a ----
    for title, ids, keys in (("C3a-1. Consensus misses (label: responsive)", ms, ("miss98", "miss50")),
                             ("C3a-2. Consensus false positives (label: not responsive)", fs, ("fp98", "fp50"))):
        print(f"## {title}\n")
        print("Models = how many of the 7 miss it (misses) or keep it (false positives) at thr98 / at 0.5, main set; "
              "'+roster' = the same for the roster runs (25-3152 only). Human call: R/N = real row confirmed responsive/"
              "not; K = synthetic label kept; F = flipped; blank = no human check. Date, in window (the refined 24-409 window "
              "1/1-7/31/2023 or the 25-3152 window 1/1/2024-5/31/2025), recipients (distinct To/Cc/Bcc addresses) and first "
              "hook (body offset of the first listed 24-409 term, or of the first ACPG mention for 25-3152; the models "
              "see offsets below 8,000) are computed. The text columns are the analyst's reading.\n")
        out = []
        for p in sorted(ids, key=lambda p: (p.split("|")[0], JUDGMENTS[short(p)][3], p)):
            what, why, verdict, err, note = JUDGMENTS[short(p)]
            e = E[P[p]["email_id"]]
            ros = f"{len(who(pr, keys[0], p))} / {len(who(pr, keys[1], p))}" if p.startswith("25-3152") else "—"
            win = in_window(e, P[p]["request_id"])
            out.append([short(p), P[p]["kind"].replace("_positive", "").replace("hard_negative", "hn") +
                        (f"/{P[p]['recipe']}" if P[p]["kind"].startswith("hard") else ""),
                        f"{len(who(pm, keys[0], p))} / {len(who(pm, keys[1], p))}", ros, call(p),
                        (e.get("date") or "")[:10], "yes" if win else "no", n_recipients(e), first_term(e, P[p]["request_id"]),
                        what, why, verdict, err, note])
        table(["pair", "kind/recipe", "models (thr98 / 0.5)", "+roster", "human call", "date", "in window", "recipients",
               "first hook at char", "what it is", "why this label", "label judgment", "model error type", "note"], out)

    # ---- C3b ----
    print("## C3b. Tallies\n")
    out = []
    for grp, ids in (("consensus misses", ms), ("consensus false positives", fs)):
        for v in (R, A, W):
            n = sum(JUDGMENTS[short(p)][2] == v for p in ids)
            if n:
                out.append([grp, "label " + v, f"{n}/{len(ids)}"])
        errs = sorted({JUDGMENTS[short(p)][3] for p in ids})
        for e in errs:
            k = [p for p in ids if JUDGMENTS[short(p)][3] == e]
            out.append([grp, e, f"{len(k)}/{len(ids)} (24-409 {sum(p.startswith('24-409') for p in k)}, 25-3152 {sum(p.startswith('25-3152') for p in k)})"])
    table(["group", "category", "count"], out)

    # ---- C3c ----
    print("## C3c. 24-409 emails with Geosyntec only in the addresses\n")
    print(f"Mechanical filter over all {sum(p.startswith('24-409') for p in P)} 24-409 pairs: 'geosyntec' appears in an e-mail address (headers or quoted "
          "headers in the body), and once addresses and URLs are removed, no listed 24-409 term (Hinds, Lerner, USP, "
          "GPS, Urban Studies, Global Policy, UCSD, RWER, Water Equity, RDF, Decarbonization Framework, Geosyntec, "
          "Murakawa, Fletcher) appears in the subject or the first 8,000 body characters.\n")
    out = []
    for p in sorted(P):
        if not p.startswith("24-409"):
            continue
        e = E[P[p]["email_id"]]
        head = " ".join(str(e.get(k) or "") for k in ("from", "to", "cc", "bcc"))
        vis = (e.get("subject") or "") + "\n" + (e.get("body") or "")[:MAX_BODY_CHARS]
        addrs = " ".join(ADDR_RE.findall(head + " " + vis))
        if re.search(r"(?i)geosyntec", addrs) and not any(re.search(t, ADDR_RE.sub(" ", vis)) for t in TERMS_24409):
            out.append([short(p), P[p]["label"], P[p]["kind"], call(p) or "—", (e.get("date") or "")[:10],
                        (e.get("subject") or "")[:55].replace("|", "/"), f"{sum(S[m][p]['score'] >= 0.5 for m in NAMES)}/7"])
    table(["pair", "label", "kind", "human call", "date", "subject", "models saying yes at 0.5"], out)

    # ---- C5 ----
    cand = [p for p in ms + fs if JUDGMENTS[short(p)][2] != R]
    def row(ids, how, label):
        d = deltas(main_runs, set(ids), how)
        dr = deltas(roster_runs, set(ids), how)
        e = [d[m][0] for m in NAMES]
        a = [d[m][1] for m in NAMES]
        er = [dr[m][0] for m in NAMES if dr[m] is not None]
        return [label] + [fmt_pp(x) for x in e] + [fmt_pp(sum(e) / len(e)), f"{sum(a) / len(a):+.4f}",
                                                    f"{min(a):+.4f} to {max(a):+.4f}",
                                                    fmt_pp(sum(er) / len(er)) if er else "—"], (abs(sum(e) / len(e)), abs(sum(a) / len(a)))
    hdr = ["candidate"] + [f"Δelim@98 {m}" for m in NAMES] + ["mean Δelim@98", "mean ΔAUROC", "ΔAUROC range",
                                                               "mean Δelim@98 +roster"]
    print("## C5a. Re-check list: single labels judged arguable or likely wrong\n")
    print("Each row flips one label and recomputes every model's thr98, elim@98 (percentage points) and AUROC on all "
          f"{N_ALL} pairs. '+roster' = the same flip on the 25-3152 roster runs ({NR['25-3152']} pairs). Ordered by |mean Δelim@98|, then "
          "|mean ΔAUROC|. Δelim@98 is in percentage points.\n")
    rows = [row([p], "flip", f"{short(p)} ({JUDGMENTS[short(p)][2]}; label {P[p]['label']} → {1 - P[p]['label']})") for p in cand]
    table(hdr, [r for r, _ in sorted(rows, key=lambda t: (-t[1][0], -t[1][1]))])

    print("## C5b. Label questions that cover several emails, changed together\n")
    out = []
    for lbl, sids, how in GROUPS:
        ids = [next(p for p in P if short(p) == s) for s in sids]
        out.append(row(ids, how, f"{lbl} (n={len(ids)})"))
    table(hdr, [r for r, _ in out])

    print("## C5c. Appendix: every consensus item flipped on its own\n")
    print("Rows for the 11 consensus misses first, then the 57 consensus false positives; each group ordered as in C5a.\n")
    for grp in (ms, fs):
        rows = [row([p], "flip", f"{short(p)} ({JUDGMENTS[short(p)][2]})") for p in grp]
        table(hdr, [r for r, _ in sorted(rows, key=lambda t: (-t[1][0], -t[1][1]))])
    for lbl, grp in (("consensus misses", ms), ("consensus false positives", fs)):
        mean_e, per_m, mean_a = [], [], []
        for p in grp:
            d = deltas(main_runs, {p}, "flip")
            e = [d[m][0] for m in NAMES]
            mean_e.append(sum(e) / len(e)); per_m += e; mean_a.append(sum(d[m][1] for m in NAMES) / len(NAMES))
        print(f"- {lbl} (n={len(grp)}), one flip each: mean Δelim@98 from {fmt_pp(min(mean_e))} to {fmt_pp(max(mean_e))} pp; "
              f"single-model Δelim@98 from {fmt_pp(min(per_m))} to {fmt_pp(max(per_m))} pp; mean ΔAUROC from "
              f"{min(mean_a):+.4f} to {max(mean_a):+.4f}.")
    print()
    base = {m: (elim98(main_runs[m]), auc(main_runs[m])) for m in NAMES}
    print("Baseline (current labels): " + "; ".join(f"{m} elim@98 {100 * base[m][0]:.1f}%, AUROC {base[m][1]:.4f}" for m in NAMES) + ".\n")


if __name__ == "__main__":
    main()
