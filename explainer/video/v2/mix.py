"""Mix narration, sound effects and music onto the film's timeline, then mux with the silent picture.
Second cut. Run from the repo root:  python3 explainer/video/v2/mix.py [silent.mp4 out.mp4]
Levels are set from measurements (EBU R128), since nobody hears the mix while it is built."""
import json, math, pathlib, re, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
B = HERE / "build"; A = HERE / "audio"; FX = HERE.parent / "audio"     # narration and music here; effect clips from the first cut
TL = json.loads((HERE / "timeline.js").read_text().split("=", 1)[1].rstrip().rstrip(";"))
CUES = json.loads((B / "sfx.json").read_text())["sfx"]
DUR = TL["dur"]
VOICE_LUFS, FINAL_LUFS = -16.5, -15.5
# The bed builds: its level before ducking, in LUFS, at these times (straight lines between). The last two points are the title after the narration ends.
BED = [(0, -30.0), (60, -30.0), (100, -28.5), (134, -27.5), (141.2, -23.0), (146, -22.0)]
RAW = [-27.7, -25.0, -22.7, -19.0, -19.5, -18.9, -17.9, -17.7, -19.8, -19.2, -16.4, -15.3, -15.0, -16.1, -18.6]   # the track's measured loudness in ten-second windows
SFX_DB = {"whoosh": -14, "pop": -9, "chime": -3, "rise": -11, "scatter": -1.5, "thud": 16, "tick": 0, "type": -15}   # brings each clip's peak to about -12..-18 dBFS
SFX_LEN = {"tick": 0.075, "pop": 0.3, "whoosh": 0.8, "thud": 0.6, "chime": 1.4, "rise": 1.9, "scatter": 2.5}
SFX_START = {"tick": 0.385}                  # the tick clip holds six clicks; use the last one only
def run(args): return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-y"] + args, capture_output=True, text=True)
def lufs(f):
    err = run(["-i", str(f), "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"]).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1]), float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)[-1]), float(re.findall(r"LRA:\s+(-?[\d.]+) LU", err)[-1])
# 1. narration on the timeline
ins, fl = [], []
for i, s in enumerate(TL["segs"]):
    ins += ["-i", str(A / f"{s['id']}.mp3")]
    fl.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={round(s['start'] * 1000)}:all=1[v{i}]")
n = len(TL["segs"])
fl.append("".join(f"[v{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,highpass=f=70,apad,atrim=0:{DUR}[out]")
r = run(ins + ["-filter_complex", ";".join(fl), "-map", "[out]", str(B / "voice_raw.wav")]); assert r.returncode == 0, r.stderr[-800:]
vi, vp, _ = lufs(B / "voice_raw.wav"); vgain = VOICE_LUFS - vi
print(f"narration: {vi} LUFS, peak {vp} dBFS -> gain {vgain:+.1f} dB")
# 2. effects
ins, fl, k = [], [], 0
for c in CUES:
    name = c["name"]; ln = SFX_LEN.get(name)
    if c.get("len"): ln = c["len"]                     # typing passages carry their own length
    ins += ["-i", str(FX / f"sfx_{name}.mp3")]
    st0 = SFX_START.get(name, 0); fd = min(0.12, 0.4 * ln)
    db = SFX_DB[name] + 20 * math.log10(c["gain"])
    fl.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,atrim={st0}:{st0 + ln:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={ln - fd:.3f}:d={fd:.3f},volume={db:.1f}dB,adelay={round(c['t'] * 1000)}:all=1[e{k}]"); k += 1
fl.append("".join(f"[e{i}]" for i in range(k)) + f"amix=inputs={k}:normalize=0,apad,atrim=0:{DUR}[out]")
r = run(ins + ["-filter_complex", ";".join(fl), "-map", "[out]", str(B / "sfx.wav")]); assert r.returncode == 0, r.stderr[-800:]
print("effects:", k, "cues, track", lufs(B / "sfx.wav"))
# 3. music bed, ducked under the narration, and the final sum
def bed(t):
    for (a, x), (b, y) in zip(BED, BED[1:]):
        if t <= b: return x + (y - x) * (t - a) / (b - a)
    return BED[-1][1]
knots = [(0.0, bed(0) - RAW[0])] + [(5 + 10 * i, bed(5 + 10 * i) - r) for i, r in enumerate(RAW)] + [(DUR + 1, bed(DUR) - RAW[-1])]   # gain in dB
expr = f"{knots[-1][1]:.2f}"
for (a, x), (b, y) in reversed(list(zip(knots, knots[1:]))):
    expr = f"if(lt(t,{b}),{x:.2f}+({y - x:.2f})*(t-{a})/{b - a},{expr})"
mus = (f"[2:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{DUR},volume='pow(10,({expr})/20)':eval=frame,"
       f"afade=t=in:st=0:d=0.6,afade=t=out:st={DUR - 1.4:.3f}:d=1.4[m]")
graph = (f"[0:a]volume={vgain:.2f}dB,acompressor=threshold=-18dB:ratio=2.2:attack=6:release=140,alimiter=limit=0.8:level=false,asplit=2[v][vsc];"
         f"{mus};[m][vsc]sidechaincompress=threshold=0.04:ratio=3:attack=20:release=500[duck];"
         f"[v][duck][1:a]amix=inputs=3:normalize=0,alimiter=limit=0.84:level=false[out]")
r = run(["-i", str(B / "voice_raw.wav"), "-i", str(B / "sfx.wav"), "-i", str(A / "music.mp3"), "-filter_complex", graph, "-map", "[out]", str(B / "mix_pre.wav")])
assert r.returncode == 0, r.stderr[-800:]
mi, mp, ml = lufs(B / "mix_pre.wav"); g = FINAL_LUFS - mi
r = run(["-i", str(B / "mix_pre.wav"), "-af", f"volume={g:.2f}dB,alimiter=limit=0.84:level=false", str(B / "mix.wav")]); assert r.returncode == 0, r.stderr[-800:]
print(f"mix before trim: {mi} LUFS, peak {mp} dBFS, LRA {ml} -> gain {g:+.2f} dB; final:", lufs(B / "mix.wav"))
# music alone, as it sits in the mix (for a level check)
r = run(["-i", str(B / "voice_raw.wav"), "-i", str(B / "sfx.wav"), "-i", str(A / "music.mp3"), "-filter_complex", graph.replace("amix=inputs=3:normalize=0", "amix=inputs=3:normalize=0:weights=0 1 0"), "-map", "[out]", str(B / "music_ducked.wav")])
assert r.returncode == 0, r.stderr[-800:]
print("music as mixed:", lufs(B / "music_ducked.wav"))
# 4. mux
if len(sys.argv) > 2:
    r = run(["-i", sys.argv[1], "-i", str(B / "mix.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", sys.argv[2]])
    assert r.returncode == 0, r.stderr[-800:]; print("wrote", sys.argv[2])
