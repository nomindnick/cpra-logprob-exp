"""Generate the second cut's music bed with the ElevenLabs API (key from the environment).
Run from the repo root:  set -a; . ./.env; set +a; python3 explainer/video/v2/music.py [out.mp3]"""
import json, os, pathlib, sys, urllib.request, urllib.error
HERE = pathlib.Path(__file__).resolve().parent
KEY = os.environ["ELEVENLABS_API_KEY"]
MUSIC = ("Instrumental underscore for a two and a half minute explainer film about a data experiment, built to sit under narration. "
         "It opens sparse: a soft felt piano motif and a quiet pulsing analog synth. Every thirty seconds a layer joins: light dry "
         "percussion, then a warm bass, then gentle plucked arpeggios and soft strings, so the track builds steadily to a confident, "
         "hopeful peak around the two minute mark, then thins to the piano alone and resolves on a held final chord. "
         "Curious, precise, quietly optimistic. Steady 100 bpm. No vocals, no sudden hits, no long silences.")
out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "audio" / "music.mp3"
req = urllib.request.Request("https://api.elevenlabs.io/v1/music", data=json.dumps({"prompt": MUSIC, "music_length_ms": 150000}).encode(),
                             headers={"xi-api-key": KEY, "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=900) as r:
        data = r.read(); out.write_bytes(data); print(out.name, r.status, r.headers.get("content-type"), len(data), "bytes")
except urllib.error.HTTPError as e:
    print(out.name, "HTTP", e.code, e.read()[:600].decode("utf-8", "replace"))
