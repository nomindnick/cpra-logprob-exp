"""Narration: one ElevenLabs text-to-speech call per segment, with character timestamps.
Run from the repo root:  python3 explainer/video/tts.py [segment ids...]
Reads ELEVENLABS_API_KEY from the environment. Writes audio/<id>.mp3 and audio/<id>.align.json."""
import base64, json, os, pathlib, sys, urllib.request, urllib.error
HERE = pathlib.Path(__file__).resolve().parent
N = json.loads((HERE / "narration.json").read_text())
KEY = os.environ["ELEVENLABS_API_KEY"]
segs = N["segments"]; want = set(sys.argv[1:])
for i, s in enumerate(segs):
    if want and s["id"] not in want:
        continue
    body = {"text": s["text"], "model_id": N["model_id"],
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0, "use_speaker_boost": True}}
    if i > 0: body["previous_text"] = segs[i - 1]["text"]
    if i + 1 < len(segs): body["next_text"] = segs[i + 1]["text"]
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{N['voice_id']}/with-timestamps?output_format=mp3_44100_128",
        data=json.dumps(body).encode(), headers={"xi-api-key": KEY, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        print(s["id"], "HTTP", e.code, e.read()[:300]); continue
    (HERE / "audio" / f"{s['id']}.mp3").write_bytes(base64.b64decode(d["audio_base64"]))
    (HERE / "audio" / f"{s['id']}.align.json").write_text(json.dumps(d["alignment"]))
    a = d["alignment"]
    print(s["id"], "chars", len(a["characters"]), "of", len(s["text"]), "speech ends", a["character_end_times_seconds"][-1])
