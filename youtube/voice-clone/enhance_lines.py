"""Studio-clean every voiced line with Resemble Enhance (denoise + dereverb + bandwidth extension).

Run with the enhance venv (see setup.sh):
    ~/enhance/.venv/bin/python youtube/voice-clone/enhance_lines.py <voice_dir>
Reads voice_dir/lines.json, writes voice_dir/clean/line_NNN.wav (44.1 kHz).
Bleep regions are re-drawn as a clean tone afterwards, because the speech model smears them.
Skips lines already done, so it can resume.
"""
import json
import sys
from pathlib import Path

import torch
import torchaudio as ta
from resemble_enhance.enhancer.inference import enhance

vdir = Path(sys.argv[1])
out = vdir / "clean"
out.mkdir(exist_ok=True)
lines = json.loads((vdir / "lines.json").read_text())
for i, ln in enumerate(lines, 1):
    dst = out / ln["file"]
    if dst.exists():
        continue
    w, sr = ta.load(str(vdir / ln["file"]))
    y, nsr = enhance(w.mean(0), sr, "cpu", nfe=32, solver="midpoint", lambd=0.9, tau=0.5)
    for start, dur in ln.get("bleeps", []):
        a, n = int(start * nsr), int(dur * nsr)
        t = torch.arange(n) / nsr
        tone = 0.22 * torch.sin(2 * torch.pi * 1000 * t)
        f = int(nsr * 0.006)
        tone[:f] *= torch.linspace(0, 1, f)
        tone[-f:] *= torch.linspace(1, 0, f)
        y[a:a + n] = tone[: max(0, min(n, len(y) - a))]
    ta.save(str(dst), y.unsqueeze(0), nsr)
    print(f"[{i}/{len(lines)}] {dst.name}", flush=True)
print("done")
