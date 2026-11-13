"""Generate the film's sound effects and music bed with the ElevenLabs API (key from the environment).
Run from the repo root:  set -a; . ./.env; set +a; python3 explainer/video/sfx.py [names...|music]"""
import json, os, pathlib, sys, urllib.request, urllib.error
HERE = pathlib.Path(__file__).resolve().parent
KEY = os.environ["ELEVENLABS_API_KEY"]
SFX = {  # name: (prompt, seconds, prompt_influence)
    "whoosh":  ("Short soft airy whoosh, a gentle interface transition swish, clean and dry, no music", 1.0, 0.6),
    "scatter": ("A large stack of paper sheets riffling and fluttering down onto a desk, light and dry, close microphone, no voices", 2.6, 0.5),
    "tick":    ("One single soft dry click, like a small mechanical counter ticking once", 0.5, 0.7),
    "pop":     ("One soft rounded interface pop, gentle and short, like a small bubble, dry", 0.5, 0.7),
    "type":    ("Steady fast typing on a quiet laptop keyboard, soft key presses, close and dry, no voices, no music", 4.5, 0.6),
    "thud":    ("Single deep muffled bass drum hit, one soft low thump impact, short and dry", 0.8, 0.6),
    "chime":   ("One gentle warm two-note chime, a soft bell confirmation tone, bright and pleasant, short tail", 1.6, 0.6),
    "rise":    ("A soft airy shimmer swelling upward, a gentle rising whoosh of sparkling tones, smooth, no drums", 2.0, 0.6),
}
MUSIC = ("Minimal, warm instrumental underscore for a short explainer video about a data experiment. Soft felt piano motif over a gentle "
         "pulsing analog synth and light, dry percussion. Curious, calm, quietly confident. No vocals. Steady 96 bpm, even dynamics "
         "suitable for sitting under narration, with a gentle resolving ending.")
def post(path, body, out):
    req = urllib.request.Request("https://api.elevenlabs.io" + path, data=json.dumps(body).encode(),
                                 headers={"xi-api-key": KEY, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            data = r.read(); out.write_bytes(data); print(out.name, r.status, r.headers.get("content-type"), len(data), "bytes")
    except urllib.error.HTTPError as e:
        print(out.name, "HTTP", e.code, e.read()[:400].decode("utf-8", "replace"))
want = sys.argv[1:] or list(SFX) + ["music"]
for name in want:
    if name == "music":
        post("/v1/music", {"prompt": MUSIC, "music_length_ms": 85000}, HERE / "audio" / "music.mp3")
    else:
        p, d, inf = SFX[name]
        post("/v1/sound-generation", {"text": p, "duration_seconds": d, "prompt_influence": inf}, HERE / "audio" / f"sfx_{name}.mp3")
