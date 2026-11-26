"""Make every directed line sound like the same person: convert its voice texture to voice E.

Run with the chatterbox venv:
    ~/chatterbox/.venv/bin/python youtube/voice-clone/convert_voice.py <in_voice_dir> <out_voice_dir> [--target ref-voice-e.wav]

Directed lines (direct_voice.py) each get their own performance, so the voice drifts a little
from line to line. Chatterbox voice conversion keeps each line's words, timing and emotion and
re-voices it with the target speaker, so all lines share one voice. Bleeps are re-drawn
afterwards as a clean tone (the converter smears them). Copies line_NNN.json and lines.json,
updating durations. Resumable. Note: Chatterbox adds an inaudible AI watermark (Perth) to its output.
"""
import json
import shutil
import sys
from pathlib import Path

import torch
import torchaudio as ta

_load = torch.load
torch.load = lambda *a, **k: _load(*a, **{**k, "map_location": torch.device("cpu")})  # CPU-only machine
from chatterbox.vc import ChatterboxVC  # noqa: E402

HERE = Path(__file__).parent


def main():
    argv = sys.argv[1:]
    target = Path(argv[argv.index("--target") + 1]) if "--target" in argv else HERE / "ref-voice-e.wav"
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and not (i and argv[i - 1] == "--target")]
    src, dst = Path(args[0]), Path(args[1])
    dst.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    m = ChatterboxVC.from_pretrained(device="cpu")
    lines = json.loads((src / "lines.json").read_text())
    for i, ln in enumerate(lines, 1):
        out = dst / ln["file"]
        meta_src = src / f"line_{i:03d}.json"
        if meta_src.exists():
            shutil.copy(meta_src, dst / meta_src.name)
        if out.exists():
            continue
        w = m.generate(str(src / ln["file"]), target_voice_path=str(target))
        sr = m.sr
        for start, dur in ln.get("bleeps", []):
            a, n = int(start * sr), int(dur * sr)
            t = torch.arange(n) / sr
            tone = 0.22 * torch.sin(2 * torch.pi * 1000 * t)
            f = int(sr * 0.006)
            tone[:f] *= torch.linspace(0, 1, f)
            tone[-f:] *= torch.linspace(1, 0, f)
            end = min(w.shape[1], a + n)
            if a < end:
                w[0, a:end] = tone[: end - a]
        ta.save(str(out), w, sr)
        print(f"[{i}/{len(lines)}] {out.name}", flush=True)
    for ln in lines:
        info = ta.info(str(dst / ln["file"]))
        ln["duration"] = round(info.num_frames / info.sample_rate, 3)
        ln["voice"] = str(ln.get("voice", "")) + "+vc:E"
    (dst / "lines.json").write_text(json.dumps(lines, indent=1))
    print("done:", dst / "lines.json")


if __name__ == "__main__":
    main()
