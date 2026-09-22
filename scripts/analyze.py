"""Compute SPEC §6 metrics from a scoring run.

  uv run python scripts/analyze.py runs/qwen3.5_4b [--dedupe]

Prints a report and writes runs/<tag>/metrics.json. Stdlib only.

Metrics: AUROC, AUPRC, recall/precision sweep, non-responsive eliminated at
98% and 99% recall (the headline), reliability table (score decile vs observed
positive rate), per-request recall, per-negative-kind breakdown, latency
(prefill/decode/total; by prompt-token bucket), truncation rate.
--dedupe collapses emails with identical body_sha256 within a request so an
email pulled from several mailboxes counts once.
"""
import argparse
import json
import pathlib
import statistics
import sys


def auroc(scores, labels):
    # rank-based (Mann-Whitney), ties get average rank
    pairs = sorted(zip(scores, labels))
    n_pos = sum(labels); n_neg = len(labels) - n_pos
    if not n_pos or not n_neg:
        return None
    rank_sum = 0.0; i = 0
    while i < len(pairs):
        j = i
        while j < len(pairs) and pairs[j][0] == pairs[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2  # ranks i+1..j
        rank_sum += avg_rank * sum(l for _, l in pairs[i:j])
        i = j
    return (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def pr_curve(scores, labels):
    """Returns list of (threshold, recall, precision, neg_eliminated) sorted by threshold desc."""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    n_pos = sum(labels); n_neg = len(labels) - n_pos
    tp = fp = 0; out = []
    i = 0
    while i < len(order):
        thr = scores[order[i]]
        while i < len(order) and scores[order[i]] == thr:
            if labels[order[i]]: tp += 1
            else: fp += 1
            i += 1
        out.append((thr, tp / n_pos, tp / (tp + fp), (n_neg - fp) / n_neg))
    return out


def auprc(curve):
    # average precision: sum over recall steps of precision
    ap = 0.0; prev_r = 0.0
    for _, r, p, _ in curve:
        ap += (r - prev_r) * p; prev_r = r
    return ap


def at_recall(curve, target):
    """Highest threshold whose recall >= target; returns (thr, recall, precision, eliminated)."""
    for row in curve:
        if row[1] >= target:
            return row
    return curve[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--dedupe", action="store_true")
    a = ap.parse_args()
    run = pathlib.Path(a.run_dir)
    rows = [json.loads(l) for l in (run / "scores.jsonl").open()]
    errors = [r for r in rows if "error" in r or r.get("score") is None]
    rows = [r for r in rows if "error" not in r and r.get("score") is not None]

    if a.dedupe:
        emails = {e["id"]: e for p in pathlib.Path("data/emails").glob("*.emails.jsonl")
                  for e in map(json.loads, p.open())}
        seen = set(); kept = []
        for r in rows:
            key = (r["request_id"], emails[r["email_id"]]["body_sha256"])
            if key in seen: continue
            seen.add(key); kept.append(r)
        rows = kept

    scores = [r["score"] for r in rows]; labels = [r["label"] for r in rows]
    if not sum(labels) or sum(labels) == len(labels):
        sys.exit(f"{run.name}: {len(rows)} rows but need both positives and negatives (partial run?)")
    curve = pr_curve(scores, labels)
    m = {
        "run": run.name, "n": len(rows), "errors": len(errors),
        "positives": sum(labels), "negatives": len(labels) - sum(labels),
        "auroc": auroc(scores, labels), "auprc": auprc(curve),
        "at_recall": {},
        "threshold_0.5": None, "reliability": [], "per_request_recall_at_thr": {},
        "per_kind": {}, "latency": {}, "truncated_rate": sum(r["truncated"] for r in rows) / len(rows),
        "residual_median": statistics.median(r["residual"] for r in rows),
    }
    for t in (0.95, 0.98, 0.99, 1.0):
        thr, rec, prec, elim = at_recall(curve, t)
        m["at_recall"][str(t)] = {"threshold": thr, "recall": rec, "precision": prec, "neg_eliminated": elim}
    tp = sum(1 for s, l in zip(scores, labels) if s >= 0.5 and l)
    fp = sum(1 for s, l in zip(scores, labels) if s >= 0.5 and not l)
    fn = sum(labels) - tp; tn = len(labels) - sum(labels) - fp
    m["threshold_0.5"] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                          "recall": tp / (tp + fn), "precision": tp / (tp + fp) if tp + fp else None,
                          "neg_eliminated": tn / (tn + fp)}
    # reliability: deciles of score
    for d in range(10):
        lo, hi = d / 10, (d + 1) / 10
        b = [l for s, l in zip(scores, labels) if lo <= s < hi or (d == 9 and s == 1.0)]
        m["reliability"].append({"bucket": f"{lo:.1f}-{hi:.1f}", "n": len(b),
                                 "pos_rate": sum(b) / len(b) if b else None})
    thr98 = m["at_recall"]["0.98"]["threshold"]
    for rid in sorted({r["request_id"] for r in rows}):
        pos = [r for r in rows if r["request_id"] == rid and r["label"]]
        neg = [r for r in rows if r["request_id"] == rid and not r["label"]]
        m["per_request_recall_at_thr"][rid] = {
            "n_pos": len(pos), "recall_at_0.5": sum(r["score"] >= 0.5 for r in pos) / len(pos),
            "recall_at_thr98": sum(r["score"] >= thr98 for r in pos) / len(pos),
            "n_neg": len(neg), "neg_eliminated_at_thr98": sum(r["score"] < thr98 for r in neg) / len(neg) if neg else None,
            "median_pos_score": statistics.median(r["score"] for r in pos),
        }
    for kind in sorted({r["kind"] for r in rows}):
        k = [r for r in rows if r["kind"] == kind]
        m["per_kind"][kind] = {"n": len(k), "median_score": statistics.median(r["score"] for r in k),
                               "frac_above_thr98": sum(r["score"] >= thr98 for r in k) / len(k)}
    def q(xs, p): xs = sorted(xs); return xs[min(len(xs) - 1, int(p * len(xs)))]
    lat = {}
    for f in ("prefill_ms", "decode_ms", "total_ms", "wall_ms", "prompt_tokens"):
        xs = [r[f] for r in rows if r.get(f) is not None]
        lat[f] = {"median": statistics.median(xs), "p90": q(xs, .9), "mean": statistics.mean(xs)}
    lat["prefill_tok_per_s"] = sum(r["prompt_tokens"] for r in rows) / (sum(r["prefill_ms"] for r in rows) / 1000)
    buckets = {}
    for r in rows:
        b = f"{(r['prompt_tokens'] // 1000) * 1000}-{(r['prompt_tokens'] // 1000 + 1) * 1000}"
        buckets.setdefault(b, []).append(r["total_ms"])
    lat["total_ms_by_prompt_tokens"] = {b: {"n": len(v), "median": statistics.median(v)} for b, v in sorted(buckets.items(), key=lambda kv: int(kv[0].split("-")[0]))}
    m["latency"] = lat
    json.dump(m, (run / ("metrics.dedupe.json" if a.dedupe else "metrics.json")).open("w"), indent=1)

    # ---- report ----
    print(f"== {run.name}  n={m['n']} (+{m['positives']} / -{m['negatives']})  errors={m['errors']}"
          f"{'  [deduped]' if a.dedupe else ''}")
    print(f"AUROC {m['auroc']:.4f}   AUPRC {m['auprc']:.4f}   truncated {m['truncated_rate']:.1%}   residual median {m['residual_median']:.4f}")
    print("\nrecall target -> threshold, precision, non-responsive eliminated")
    for t, v in m["at_recall"].items():
        print(f"  {float(t):.0%}: thr {v['threshold']:.3f}  prec {v['precision']:.3f}  eliminated {v['neg_eliminated']:.1%}")
    t5 = m["threshold_0.5"]
    print(f"  @0.5: recall {t5['recall']:.3f}  prec {t5['precision']:.3f}  eliminated {t5['neg_eliminated']:.1%}  (tp {t5['tp']} fp {t5['fp']} fn {t5['fn']} tn {t5['tn']})")
    print("\nreliability (score bucket: n, observed positive rate)")
    for b in m["reliability"]:
        print(f"  {b['bucket']}: n={b['n']:5d}  pos {b['pos_rate']:.3f}" if b["n"] else f"  {b['bucket']}: n=0")
    print(f"\nper request (thr98={thr98:.3f})")
    for rid, v in m["per_request_recall_at_thr"].items():
        print(f"  {rid}: pos {v['n_pos']:4d} recall@0.5 {v['recall_at_0.5']:.3f} recall@thr98 {v['recall_at_thr98']:.3f} median {v['median_pos_score']:.3f} | neg {v['n_neg']:4d} eliminated@thr98 {v['neg_eliminated_at_thr98']:.3f}")
    print("\nper kind"); [print(f"  {k}: n={v['n']} median {v['median_score']:.3f} above thr98 {v['frac_above_thr98']:.3f}") for k, v in m["per_kind"].items()]
    print(f"\nlatency: total median {lat['total_ms']['median']:.0f} ms (p90 {lat['total_ms']['p90']:.0f}), prefill median {lat['prefill_ms']['median']:.0f}, "
          f"decode median {lat['decode_ms']['median']:.0f}, prompt tokens median {lat['prompt_tokens']['median']:.0f}, prefill {lat['prefill_tok_per_s']:.0f} tok/s")
    for b, v in lat["total_ms_by_prompt_tokens"].items():
        print(f"  {b} tok: n={v['n']:5d} median {v['median']:.0f} ms")


if __name__ == "__main__":
    main()
