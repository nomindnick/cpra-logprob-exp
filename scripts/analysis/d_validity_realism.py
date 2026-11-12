"""D2: what the real negatives, hard negatives and synthetic positives are, and how they differ.

  uv run python scripts/analysis/d_validity_realism.py

Descriptive, from data/golden/emails.jsonl, data/golden/work/synthetic.jsonl, data/golden/work/prelabels.jsonl,
data/golden/work/adjudication_items.json + adjudications.json, data/golden/work/gen/job_*.json and the full
productions in data/emails/sandiego.emails.jsonl. Scores only in D2-8 (the seven score runs).

"Keyword-search hit" is a proxy built here, not the county's search (which isn't published):
  24-409: any of the refinement's terms (Hinds, Lerner, urban studies, USP, global policy, GPS, UCSD /
          UC San Diego, water equity, RWER, RDF, decarbonization framework, Geosyntec, Murakawa), acronyms
          case-sensitive, in the subject, body, attachment names or address headers;
  25-3152: the group's name (Alpine Community Planning Group, ACPG, Alpine CPG / planning group, alpinecpg) or
          any roster member's name or email address (data/golden/work/acpg_roster.json), same fields.
"In window" = the email's date falls in the request's date window (24-409: 2023-01-01..2023-07-31;
25-3152: 2024-01-01..2025-05-31).

Prints D2-0 (real candidates), D2-1 (generation recipe catalogue), D2-2 (where the real negatives come from), D2-3 (features by kind),
D2-4 (keyword-hit pool in the other productions), D2-5 (verifier verdicts on kept synthetic emails),
D2-6 (how the labels were checked), D2-7 (how big the synthetic edits are), D2-8 (do synthetic emails score
differently from real ones of the same label). Stdlib only, deterministic.
"""
import collections
import difflib
import glob
import json
import re
import statistics
import sys

sys.path.insert(0, "scripts/analysis")
from d_validity_common import SCORE_RUNS, emails, in_window, iso_date, load, pairs, table  # noqa: E402

sys.path.insert(0, "scripts")
from analyze import auroc  # noqa: E402

KINDS = ["real_positive", "close_call_positive", "privileged_positive", "exempt_other_positive",
         "hard_negative_flipped", "real_negative", "hard_negative"]


def term_patterns():
    t24 = [r"\bhinds\b", r"\blerner\b", r"urban studies", r"global policy", r"\buc san diego\b", r"water equity",
           r"decarboni[sz]ation framework", r"geosyntec", r"murakawa"]
    acr24 = [r"\bUSP\b", r"\bGPS\b", r"\bUCSD\b", r"\bRWER\b", r"\bRDF\b"]
    pats = {"24-409": [re.compile(p, re.I) for p in t24] + [re.compile(p) for p in acr24]}
    roster = json.load(open("data/golden/work/acpg_roster.json"))["members"]
    p25 = [re.compile(r"alpine community planning group", re.I), re.compile(r"\bACPG\b"),
           re.compile(r"alpine\s+(cpg|planning group)", re.I), re.compile(r"alpinecpg", re.I)]
    for m in roster:
        toks = m["name"].replace(" Jr.", "").replace(",", "").split()
        first, last = toks[0], toks[-1]
        p25.append(re.compile(re.escape(m["name"]), re.I))
        p25.append(re.compile(rf"\b{re.escape(first)}\s+{re.escape(last)}\b", re.I))
        p25.append(re.compile(rf"\b{re.escape(last)},\s*{re.escape(first)}\b", re.I))
        for addr in m.get("email_addresses", []):
            p25.append(re.compile(re.escape(addr), re.I))
    pats["25-3152"] = p25
    return pats


PATS = term_patterns()


def text_fields(e, headers=True):
    parts = [e.get("subject") or "", e.get("body") or "", " ".join(e.get("attachments") or [])]
    if headers:
        parts += [e.get(k) or "" for k in ("from", "to", "cc", "bcc", "delivered_to")]
    return "\n".join(parts)


def hit(e, rid, headers=True):
    t = text_fields(e, headers)
    return any(p.search(t) for p in PATS[rid])


def recipients(e):
    return sum((e.get(k) or "").count("@") for k in ("to", "cc", "bcc"))


def pct(k, n):
    return f"{k}/{n} ({k / n:.0%})" if n else "—"


def main():
    E = emails(); P = pairs()
    print("# D2. Real vs synthetic emails\n")

    print("## D2-0. Real candidates: pre-labeled vs kept (data/golden/work/candidate_plan.json, prelabels.jsonl)\n")
    plan = json.load(open("data/golden/work/candidate_plan.json"))
    prl = [json.loads(l) for l in open("data/golden/work/prelabels.jsonl")]
    out = []
    for rid in ("24-409", "25-3152"):
        out.append([rid, len(plan[rid]["positive_candidates"]), len(plan[rid]["negative_candidates"]),
                    sum(p["request_id"] == rid for p in prl),
                    sum(e["request_id"] == rid and e["kind"] == "real_positive" for e in E.values()),
                    sum(e["request_id"] == rid and e["kind"] == "real_negative" for e in E.values())])
    table(["request", "produced candidates", "other-production candidates", "pre-labeled by Opus", "kept as real+",
           "kept as real−"], out)

    print("## D2-1. Synthetic generation jobs (data/golden/work/gen/job_*.json): what each recipe asked for\n")
    jobs = collections.defaultdict(lambda: {"count": 0, "requests": set(), "desc": ""})
    for f in sorted(glob.glob("data/golden/work/gen/job_*.json")):
        j = json.load(open(f))
        k = (j["kind"], j["recipe"])
        jobs[k]["count"] += j["count"]; jobs[k]["requests"].add(j["request_id"]); jobs[k]["desc"] = j["recipe_desc"]
    kept = collections.Counter((e["kind"].replace("_flipped", ""), e["recipe"]) for e in E.values() if e["origin"] == "synthetic")
    table(["kind / recipe", "asked for (both requests)", "kept in golden set", "recipe description (verbatim)"],
          [[f"{k[0]} / {k[1]}", v["count"], kept[k], v["desc"]] for k, v in sorted(jobs.items())])
    syn = [json.loads(l) for l in open("data/golden/work/synthetic.jsonl")]
    summ = json.load(open("data/golden/summary.json"))
    print(f"Generated: {len(syn)}; dropped by build_golden.py (flagged and not kept, or D): {summ['synthetic_dropped']}; "
          f"in the golden set: {sum(e['origin'] == 'synthetic' for e in E.values())} "
          f"(of which flipped to responsive by the human: {sum(e['kind'] == 'hard_negative_flipped' for e in E.values())})\n")

    print("## D2-2. Where the real negatives come from (the production each email was released under)\n")
    out = []
    for rid in ("24-409", "25-3152"):
        c = collections.Counter(e["id"].split(":")[1] for e in E.values() if e["request_id"] == rid and e["kind"] == "real_negative")
        for src, n in sorted(c.items(), key=lambda kv: -kv[1]):
            xs = [e for e in E.values() if e["request_id"] == rid and e["kind"] == "real_negative" and e["id"].split(":")[1] == src]
            ds = sorted(d for d in (iso_date(e.get("date")) for e in xs) if d)
            out.append([rid, src, n, f"{ds[0]} .. {ds[-1]}", sum(in_window(e, rid) is None for e in xs),
                        pct(sum(bool(in_window(e, rid)) for e in xs), n), pct(sum(hit(e, rid) for e in xs), n),
                        pct(sum(bool(in_window(e, rid)) and hit(e, rid) for e in xs), n),
                        pct(sum(bool(re.search(r"\balpine\b", text_fields(e), re.I)) for e in xs), n)])
    table(["scored against", "produced for", "n", "date range", "date unknown", "in the target's date window",
           "keyword-search hit (proxy)", "in window + keyword hit", "mentions 'Alpine' anywhere"], out)
    rn = [e for e in E.values() if e["kind"] == "real_negative"]
    print(f"- Opus pre-label rationale for the real negatives cites the date window ('window', 'predates', "
          f"'outside the', 'before the', 'after the'): "
          f"{pct(sum(bool(re.search(r'window|predates|outside the|before the|after the', e.get('rationale') or '', re.I)) for e in rn), len(rn))}")
    for rid in ("24-409", "25-3152"):
        xs = [e for e in E.values() if e["request_id"] == rid and e["kind"] == "real_positive"]
        ds = sorted(d for d in (iso_date(e.get("date")) for e in xs) if d)
        print(f"- {rid} real positives: dates {ds[0]} .. {ds[-1]}; window {' .. '.join(__import__('d_validity_common').WINDOWS[rid])}")
    print()

    print("## D2-3. Email features by kind (both requests; per request in the second table)\n")
    hdr = ["kind", "n", "median body chars", "body > 8,000 chars (truncated)", "has attachments", "median recipients",
           "quoted thread", "in date window", "keyword hit (any field)", "keyword hit (subject/body/attachments only)"]

    def feat_rows(group):
        out = []
        for k in KINDS:
            xs = [e for e in E.values() if e["kind"] == k and e["request_id"] in group]
            if not xs:
                continue
            n = len(xs)
            out.append([k, n, f"{statistics.median(len(e['body'] or '') for e in xs):.0f}",
                        pct(sum(len(e["body"] or "") > 8000 for e in xs), n),
                        pct(sum(bool(e.get("attachments")) for e in xs), n),
                        f"{statistics.median(recipients(e) for e in xs):.0f}",
                        pct(sum(bool(re.search(r"^\s*>?\s*From:", e["body"] or "", re.M)) for e in xs), n),
                        pct(sum(bool(in_window(e, e["request_id"])) for e in xs), n),
                        pct(sum(hit(e, e["request_id"]) for e in xs), n),
                        pct(sum(hit(e, e["request_id"], headers=False) for e in xs), n)])
        return out
    table(hdr, feat_rows({"24-409", "25-3152"}))
    for rid in ("24-409", "25-3152"):
        print(f"### {rid}\n")
        table(hdr, feat_rows({rid}))

    print("Hard negatives by recipe (in window / keyword hit, any field):\n")
    out = []
    for rid in ("24-409", "25-3152"):
        for rc in sorted({e["recipe"] for e in E.values() if e["kind"] == "hard_negative"}):
            xs = [e for e in E.values() if e["request_id"] == rid and e["kind"] == "hard_negative" and e["recipe"] == rc]
            out.append([rid, rc, len(xs), pct(sum(bool(in_window(e, rid)) for e in xs), len(xs)),
                        pct(sum(hit(e, rid) for e in xs), len(xs)),
                        pct(sum(bool(in_window(e, rid)) and hit(e, rid) for e in xs), len(xs))])
    table(["request", "recipe", "n", "in window", "keyword hit", "in window + keyword hit"], out)
    xs = [e for e in E.values() if e["kind"] == "hard_negative"]
    print(f"All hard negatives, in window + keyword hit: {pct(sum(bool(in_window(e, e['request_id'])) and hit(e, e['request_id']) for e in xs), len(xs))}\n")

    print("## D2-4. The real keyword-hit pool: emails in the OTHER productions that hit the target's proxy and are in its window\n")
    print("These are real emails a keyword search for the target request could return although another request "
          "produced them. They are unlabeled (some could be responsive); they are the material a real-negative "
          "hard set could be built from.\n")
    allm = [json.loads(l) for l in open("data/emails/sandiego.emails.jsonl")]
    golden_ids = {(e["request_id"], e["id"]) for e in E.values()}
    out = []
    for rid in ("24-409", "25-3152"):
        for src in ("24-409", "25-3152", "25-4697", "25-5982"):
            if src == rid:
                continue
            xs = [e for e in allm if e["request_id"] == src]
            w = [e for e in xs if in_window(e, rid)]
            h = [e for e in w if hit(e, rid)]
            uniq = len({e["body_sha256"] for e in h})
            used = sum((rid, e["id"]) in golden_ids for e in h)
            out.append([rid, src, len(xs), len(w), len(h), uniq, used])
    table(["target request", "production", "emails", "in target window", "in window + keyword hit",
           "distinct bodies among those", "already a golden real negative"], out)

    print("### D2-4b. Produced emails judged not responsive (over-production), left out of the golden set\n")
    print("Final call = the human's call where one exists, else the Opus pre-label. build_golden.py keeps negatives "
          "only from other productions, so these real in-window near misses are not in the set.\n")
    pre_all = [json.loads(l) for l in open("data/golden/work/prelabels.jsonl")]
    calls_all = {k: v.get("call") for k, v in json.load(open("data/golden/work/adjudications.json")).items() if v.get("call")}
    out = []
    for rid in ("24-409", "25-3152"):
        xs = [p for p in pre_all if p["request_id"] == rid and p["origin"] == "produced"]
        fin = collections.Counter(calls_all.get(f"{rid}~{p['email_id']}", p["prelabel"]) for p in xs)
        out.append([rid, len(xs), fin["R"], fin["N"], fin["?"]])
    table(["request", "produced emails pre-labeled", "final R", "final N (over-produced)", "final ? (unclear, dropped)"], out)

    print("## D2-5. Verifier verdicts on the synthetic emails kept in the golden set\n")
    S = {s["id"]: s for s in syn}
    out = []
    for k in ["close_call_positive", "privileged_positive", "exempt_other_positive", "hard_negative", "hard_negative_flipped"]:
        xs = [S[e["id"]] for e in E.values() if e["kind"] == k]
        if not xs:
            continue
        st = collections.Counter(x["verify_style_tell"] for x in xs)
        out.append([k, len(xs), st["none"], st["mild"], st["obvious"],
                    sum(x["verify_label_correct"] is False for x in xs), sum(x["verify_recipe_followed"] is False for x in xs),
                    sum(e["adjudicated"] for e in E.values() if e["kind"] == k)])
    out.append(["all synthetic"] + [sum(r[i] for r in out) for i in range(1, 8)])
    table(["kind", "kept", "style tell: none", "mild", "obvious", "verifier: label wrong", "verifier: recipe not followed",
           "human-adjudicated"], out)

    print("## D2-6. How the labels were checked\n")
    items = json.load(open("data/golden/work/adjudication_items.json"))["items"]
    calls = {k: v.get("call") for k, v in json.load(open("data/golden/work/adjudications.json")).items()}
    pre = {f"{p['request_id']}~{p['email_id']}": p for p in map(json.loads, open("data/golden/work/prelabels.jsonl"))}
    out = []
    for sec in ("spot", "disagree", "synth", "recheck"):
        its = [i for i in items if i["section"] == sec]
        c = collections.Counter(calls.get(i["key"]) for i in its)
        agree = ""
        if sec == "spot":
            agree = f"{sum(calls.get(i['key']) == pre[i['key']]['prelabel'] for i in its if i['key'] in pre)}/{len(its)} calls equal the Opus pre-label"
        out.append([sec, len(its), ", ".join(f"{k}×{v}" for k, v in sorted(c.items(), key=lambda kv: str(kv[0]))), agree])
    table(["adjudication-page section", "items", "human calls", "note"], out)
    out = []
    for k in KINDS:
        xs = [e for e in E.values() if e["kind"] == k]
        out.append([k, len(xs), pct(sum(e["adjudicated"] for e in xs), len(xs))])
    table(["kind", "n", "human-adjudicated (any section)"], out)
    sel = [pre[f"{e['request_id']}~{e['id']}"] for e in E.values() if e["origin"] in ("produced", "other_production")]
    c = collections.Counter((p["origin"], p["confidence"]) for p in sel)
    allc = collections.Counter((p["origin"], p["confidence"]) for p in pre.values())
    table(["origin", "pre-label confidence", "in golden set", f"in the {len(pre)} pre-labeled candidates"],
          [[o, cf, c[(o, cf)], allc[(o, cf)]] for o, cf in sorted(allc)])

    print("## D2-7. Size of the synthetic edits: similarity of each synthetic body to its source email's body\n")
    print("difflib.SequenceMatcher ratio on the first 8,000 characters (what the models see); 1.0 = identical.\n")
    allm_by_id = {e["id"]: e for e in allm}
    out = []
    reuse = collections.Counter()
    rel_count = collections.Counter()
    for k in ["close_call_positive", "privileged_positive", "exempt_other_positive", "hard_negative", "hard_negative_flipped"]:
        xs = [e for e in E.values() if e["kind"] == k]
        ratios, same_subj, same_from, src_in_set, ident = [], 0, 0, 0, 0
        for e in xs:
            s = S[e["id"]]; src = allm_by_id.get(s["source_id"])
            reuse[s["source_id"]] += 1
            if src is None:
                continue
            a = (src["body"] or "")[:8000]; b = (e["body"] or "")[:8000]
            ratios.append(difflib.SequenceMatcher(None, a, b, autojunk=False).quick_ratio() if len(a) + len(b) > 20000
                          else difflib.SequenceMatcher(None, a, b, autojunk=False).ratio())
            ident += a == b
            same_subj += (src.get("subject") or "") == (e.get("subject") or "")
            same_from += (src.get("from") or "") == (e.get("from") or "")
            rel = [x["kind"] + ("" if x["request_id"] == e["request_id"] else " (other request)")
                   for x in E.values() if x["id"] == s["source_id"] and x["origin"] != "synthetic"]
            src_in_set += bool(rel)
            for r_ in rel:
                rel_count[(k, r_)] += 1
        qs = sorted(ratios)
        out.append([k, len(xs), f"{statistics.median(qs):.2f}", f"{qs[len(qs) // 4]:.2f}–{qs[(3 * len(qs)) // 4]:.2f}",
                    pct(ident, len(xs)), pct(same_subj, len(xs)), pct(same_from, len(xs)), pct(src_in_set, len(xs))])
    table(["kind", "n", "median similarity to source", "interquartile range", "visible body identical to source",
           "same subject as source", "same sender", "source email is also a real row in the set"], out)
    print("What the source email is, where it is also a real row in the golden set:\n")
    table(["synthetic kind", "source is a ...", "n"], [[k, r_, n] for (k, r_), n in sorted(rel_count.items())])
    print(f"Distinct source emails behind the {sum(reuse.values())} kept synthetic emails: {len(reuse)}; "
          f"sources used more than once: {sum(v > 1 for v in reuse.values())}\n")

    print("## D2-8. Do synthetic emails score differently from real emails of the same label?\n")
    print("P(synthetic > real) = AUROC with synthetic as the 'positive' class: the probability that a random synthetic "
          "email outscores a random real one of the same label (0.5 = no difference; ties count half).\n")
    out = []
    for name, tag in SCORE_RUNS:
        rows, _ = load(tag, P)
        rp = [r["score"] for r in rows if r["kind"] == "real_positive"]
        sp = [r["score"] for r in rows if r["label"] and r["kind"] != "real_positive"]
        rn = [r["score"] for r in rows if r["kind"] == "real_negative"]
        hn = [r["score"] for r in rows if r["kind"] == "hard_negative"]
        out.append([name, f"{statistics.median(rp):.3f}", f"{statistics.median(sp):.3f}",
                    f"{auroc(sp + rp, [1] * len(sp) + [0] * len(rp)):.2f}",
                    f"{statistics.median(rn):.3f}", f"{statistics.median(hn):.3f}",
                    f"{auroc(hn + rn, [1] * len(hn) + [0] * len(rn)):.2f}"])
    table(["run", "median real+", "median synthetic+", "P(synthetic+ > real+)", "median real−", "median hard−",
           "P(hard− > real−)"], out)
    print("By synthetic positive kind: P(kind > real+)\n")
    sk = ["close_call_positive", "privileged_positive", "exempt_other_positive", "hard_negative_flipped"]
    out = []
    for name, tag in SCORE_RUNS:
        rows, _ = load(tag, P)
        rp = [r["score"] for r in rows if r["kind"] == "real_positive"]
        row = [name]
        for k in sk:
            xs = [r["score"] for r in rows if r["kind"] == k]
            row.append(f"{auroc(xs + rp, [1] * len(xs) + [0] * len(rp)):.2f}")
        out.append(row)
    table(["run"] + [f"{k} (n={sum(1 for x in P.values() if x['kind'] == k)})" for k in sk], out)


if __name__ == "__main__":
    main()
