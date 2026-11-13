"""Build the film's timeline from the narration alignments: where each segment and word falls.
Run from the repo root:  python3 explainer/video/timeline.py   -> explainer/video/timeline.js"""
import json, pathlib, subprocess
HERE = pathlib.Path(__file__).resolve().parent
N = json.loads((HERE / "narration.json").read_text())
LEAD, GAP, TAIL = 0.9, 0.55, 4.2
GAPS = {"s3": 0.9, "s4": 2.6, "s6": 0.7}   # a longer breath after these segments (s4: time to read the chart)
t = LEAD; segs = []
for s in N["segments"]:
    a = json.loads((HERE / "audio" / f"{s['id']}.align.json").read_text())
    ch, st, en = a["characters"], a["character_start_times_seconds"], a["character_end_times_seconds"]
    assert "".join(ch) == s["text"], s["id"]
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                         str(HERE / "audio" / f"{s['id']}.mp3")]))
    words = []; i = 0
    for w in s["text"].split(" "):
        j = i + len(w) - 1
        words.append({"w": w, "s": round(t + st[i], 3), "e": round(t + en[j], 3)})
        i = j + 2
    segs.append({"id": s["id"], "start": round(t, 3), "end": round(t + dur, 3), "text": s["text"], "words": words})
    t += dur + GAPS.get(s["id"], GAP)
total = round(segs[-1]["end"] + TAIL, 3)
(HERE / "timeline.js").write_text("window.TL = " + json.dumps({"fps": 30, "dur": total, "segs": segs}) + ";\n")
print("duration", total, "frames", round(total * 30))
for s in segs:
    print(s["id"], s["start"], s["end"], " | ".join(f"{w['w']}@{w['s']:.2f}" for w in s["words"]))
