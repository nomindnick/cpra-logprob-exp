"""Transcribe audio with a local speech-recognition model, to check the spoken words against
the script (the audio is otherwise unheard during the build).
Run:  uv run --with faster-whisper python explainer/video/asr_check.py <audio files...>"""
import subprocess, sys
import numpy as np
from faster_whisper import WhisperModel
m = WhisperModel("small.en", device="cpu", compute_type="int8")
for f in sys.argv[1:]:
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    segs, info = m.transcribe(np.frombuffer(pcm, dtype=np.float32), beam_size=5)
    print(f.split("/")[-1], "|", " ".join(s.text.strip() for s in segs))
