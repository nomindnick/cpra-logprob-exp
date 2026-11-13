"""Mix narration, sound effects and music onto the film's timeline, then mux with the silent picture.
Run from the repo root:  python3 explainer/video/mix.py [silent.mp4 out.mp4]
Levels are set from measurements (EBU R128), since nobody hears the mix while it is built."""
import json, math, pathlib, re, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
B = HERE / "build"; A = HERE / "audio"
TL = json.loads((HERE / "timeline.js").read_text().split("=", 1)[1].rstrip().rstrip(";"))
CUES = json.loads((B / "sfx.json").read_text())["sfx"]
DUR = TL["dur"]
VOICE_LUFS, FINAL_LUFS = -16.5, -15.5
MUSIC_DB, MUSIC_INTRO_DB = -14.0, 5.0        # bed level; lift for the track's quiet first 15 seconds
SFX_DB = {"whoosh": -14, "pop": -9, "chime": -3, "rise": -11, "scatter": -1.5, "thud": 16, "tick": 0, "type": -15}   # brings each clip's peak to about -12..-18 dBFS
SFX_LEN = {"tick": 0.075, "pop": 0.3, "whoosh": 0.8, "thud": 0.6, "chime": 1.4, "rise": 1.9, "scatter": 2.5}
SFX_START = {"tick": 0.385}                  # the tick clip holds six clicks; use the last one only
TYPE_LEN = [1.5, 4.15]                       # the two typing passages
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
ins, fl, k = [], [], 0; ntype = 0
for c in CUES:
    name = c["name"]; ln = SFX_LEN.get(name)
    if name == "type": ln = TYPE_LEN[min(ntype, len(TYPE_LEN) - 1)]; ntype += 1
    ins += ["-i", str(A / f"sfx_{name}.mp3")]
    st0 = SFX_START.get(name, 0); fd = min(0.12, 0.4 * ln)
    db = SFX_DB[name] + 20 * math.log10(c["gain"])
    fl.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,atrim={st0}:{st0 + ln:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={ln - fd:.3f}:d={fd:.3f},volume={db:.1f}dB,adelay={round(c['t'] * 1000)}:all=1[e{k}]"); k += 1
fl.append("".join(f"[e{i}]" for i in range(k)) + f"amix=inputs={k}:normalize=0,apad,atrim=0:{DUR}[out]")
r = run(ins + ["-filter_complex", ";".join(fl), "-map", "[out]", str(B / "sfx.wav")]); assert r.returncode == 0, r.stderr[-800:]
print("effects:", k, "cues, track", lufs(B / "sfx.wav"))
# 3. music bed, ducked under the narration, and the final sum
intro = 10 ** (MUSIC_INTRO_DB / 20)
mus = (f"[2:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{DUR},"
       f"volume='if(lt(t,14),{intro:.3f},if(lt(t,20),{intro:.3f}-(t-14)/6*{intro - 1:.3f},1))':eval=frame,volume={MUSIC_DB}dB,"
       f"afade=t=in:st=0:d=0.6,afade=t=out:st={DUR - 2.2:.3f}:d=2.2[m]")
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
