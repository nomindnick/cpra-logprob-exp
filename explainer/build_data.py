"""Builds explainer/data.js for the project explainer page from the golden set and the runs behind
the findings tables (docs/findings-golden.md, scripts/golden_report.py). Run from the repo root:
    uv run python explainer/build_data.py [--stats]
"""
import json, pathlib, re, statistics, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analyze import auroc, pr_curve, at_recall  # noqa: E402

CONFIGS = [  # key, label, family, size, run dir (roster run = dir + "_roster")
    ("lp4", "4b lp", "stock", "4b", "golden_qwen3.5_4b_logprob_p2db"),
    ("lp9", "9b lp", "stock", "9b", "golden_qwen3.5_9b_logprob_p2db"),
    ("lp27", "27b lp", "stock", "27b", "golden_qwen3.8_27b_logprob_p2"),
    ("d4", "d3-4b", "d3", "4b", "golden_d3-ctx8k_4b_noul_p2"),
    ("d9", "d3-9b", "d3", "9b", "golden_d3-ctx8k_9b_noul_p2"),
    ("d27", "d3-27b", "d3", "27b", "golden_d3-ctx8k_27b_noul_p2"),
    ("jev", "Jev", "jev", "api", "golden_jev-1.14.0_noul_p2"),
    ("js4", "4b json", "json", "4b", "golden_qwen3.5_4b_json_p2"),
    ("js9", "9b json", "json", "9b", "golden_qwen3.5_9b_json_p2"),
    ("js27", "27b json", "json", "27b", "golden_qwen3.8_27b_json_p2"),
    ("jr4", "4b jsonR", "jsonR", "4b", "golden_qwen3.5_4b_json_reason_p2"),
    ("jr9", "9b jsonR", "jsonR", "9b", "golden_qwen3.5_9b_json_reason_p2"),
    ("jr27", "27b jsonR", "jsonR", "27b", "golden_qwen3.8_27b_json_reason_p2"),
]


def load(tag):
    return {r["pair_id"]: r for r in map(json.loads, (ROOT / "runs" / tag / "scores.jsonl").open())}


def nrecip(e):
    n = 0
    for f in ("to", "cc", "bcc"):
        if e.get(f):
            n += len(re.findall(r"[\w.+-]+@[\w.-]+", e[f])) or 1
    return n


def clean(s, n):
    s = re.sub(r"[ \t\r\f\v]+", " ", s or "")
    s = re.sub(r"\n\s*\n+", "\n", s).strip()
    return s[:n] + ("…" if len(s) > n else "")


def main():
    stats = "--stats" in sys.argv
    pairs = [json.loads(l) for l in (ROOT / "data/golden/pairs.jsonl").open()]
    emails = {e["id"]: e for e in map(json.loads, (ROOT / "data/golden/emails.jsonl").open())}
    runs = {k: load(tag) for k, _, _, _, tag in CONFIGS}
    rost = {k: load(tag + "_roster") for k, _, _, _, tag in CONFIGS}

    out_pairs = []
    for p in pairs:
        e = emails[p["email_id"]]
        pid = p["pair_id"]
        row = {
            "id": p["email_id"].replace("sandiego:", ""),
            "req": p["request_id"], "kind": p["kind"], "label": p["label"], "recipe": p["recipe"],
            "real": p["kind"].startswith("real"),
            "subj": clean(e.get("subject"), 110), "from": clean(e.get("from"), 70),
            "date": (e.get("date") or "")[:10], "nrec": nrecip(e),
            "snip": clean(e.get("body"), 300),
            "s": {}, "r": {},
        }
        for k in runs:
            sc = runs[k].get(pid, {}).get("score")
            row["s"][k] = None if sc is None else round(sc, 5)
            if pid in rost[k]:
                sc = rost[k][pid].get("score")
                row["r"][k] = None if sc is None else round(sc, 5)
        lp = runs["lp27"][pid]
        row["top3"] = [[t, round(v, 4)] for t, v in lp.get("top3", [])]
        row["pyn"] = [round(lp["p_yes"], 5), round(lp["p_no"], 5)]
        out_pairs.append(row)

    cfgs = []
    for k, label, fam, size, tag in CONFIGS:
        rows = [r for r in runs[k].values() if r["pair_id"] in {p["pair_id"] for p in pairs}]
        med = statistics.median(r["wall_ms"] for r in rows)
        rrows = list(rost[k].values())
        rmed = statistics.median(r["wall_ms"] for r in rrows)
        cfgs.append({"key": k, "label": label, "family": fam, "size": size, "ms": round(med), "ms_roster": round(rmed)})

    if stats:
        lab = {p["pair_id"]: p["label"] for p in pairs}
        for k, label, *_ in CONFIGS:
            rows = [(r["score"], lab[pid]) for pid, r in runs[k].items() if pid in lab and r.get("score") is not None]
            s, l = zip(*rows)
            c = pr_curve(list(s), list(l)); t = at_recall(c, 0.98)
            cf = next(c_ for c_ in cfgs if c_["key"] == k)
            print(f"{label:10s} n={len(rows)} AUROC {auroc(list(s), list(l)):.3f} thr98 {t[0]:.4f} elim98 {t[3]*100:.0f}%  median {cf['ms']} ms  roster {cf['ms_roster']} ms")

    data = {"pairs": out_pairs, "configs": cfgs}
    js = "window.DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (ROOT / "explainer/data.js").write_text(js)
    print(f"wrote explainer/data.js: {len(js)/1024:.0f} KB, {len(out_pairs)} pairs")


if __name__ == "__main__":
    main()
