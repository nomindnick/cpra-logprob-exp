"""Narration for the second cut: one ElevenLabs text-to-speech call per segment, with character timestamps.
Run from the repo root:  set -a; . ./.env; set +a; python3 explainer/video/v2/tts.py [--plain] [--out=dir] [segment ids...]
Writes audio/<id>.mp3 and audio/<id>.align.json. --plain leaves out the neighbouring-text hints."""
import base64, json, os, pathlib, sys, time, urllib.request, urllib.error
HERE = pathlib.Path(__file__).resolve().parent
N = json.loads((HERE / "narration.json").read_text())
KEY = os.environ["ELEVENLABS_API_KEY"]
args = sys.argv[1:]; plain = "--plain" in args; want = set(a for a in args if not a.startswith("--"))
OUT = HERE / next((a.split("=", 1)[1] for a in args if a.startswith("--out=")), "audio"); OUT.mkdir(exist_ok=True)
segs = N["segments"]
for i, s in enumerate(segs):
    if want and s["id"] not in want:
        continue
    body = {"text": s["text"], "model_id": N["model_id"]}
    if N.get("speed"): body["voice_settings"] = {"speed": N["speed"]}
    if not plain:
        if i > 0: body["previous_text"] = segs[i - 1]["text"]
        if i + 1 < len(segs): body["next_text"] = segs[i + 1]["text"]
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{N['voice_id']}/with-timestamps?output_format=mp3_44100_128",
        data=json.dumps(body).encode(), headers={"xi-api-key": KEY, "Content-Type": "application/json"})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        print(s["id"], "HTTP", e.code, e.read()[:300].decode("utf8", "replace")); continue
    except Exception as e:
        print(s["id"], "failed after", round(time.time() - t, 1), "s:", repr(e)[:200]); continue
    (OUT / f"{s['id']}.mp3").write_bytes(base64.b64decode(d["audio_base64"]))
    (OUT / f"{s['id']}.align.json").write_text(json.dumps(d["alignment"]))
    a = d["alignment"]
    print(s["id"], "chars", len(a["characters"]), "of", len(s["text"]), "speech ends", a["character_end_times_seconds"][-1], "in", round(time.time() - t, 1), "s",
          "| text matches" if "".join(a["characters"]) == s["text"] else "| TEXT DIFFERS")
