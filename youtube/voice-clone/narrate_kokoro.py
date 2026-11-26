"""Voice a narration file with a Kokoro voice (the channel voice: am_puck), with bleeps.

Run with the kokoro venv (see setup.sh):
    ~/kokoro/.venv/bin/python youtube/voice-clone/narrate_kokoro.py <narration.txt> <out_dir> [--voice am_puck]

Same narration.txt format and same output (line_NNN.wav + lines.json with bleep positions)
as narrate.py, so build_video.py works with either. Kokoro has no emotion dial, so the
"@0.7" expressiveness tag is mapped to speaking speed: rants a bit faster, sincere
lines a bit slower.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

sys.path.insert(0, str(Path(__file__).parent))
SR = 24000


def parse(path):
    lines = []
    for raw in Path(path).read_text().splitlines():
        s = raw.strip()
        if s.startswith("#"):
            continue
        if not s:
            if lines:
                lines[-1]["break_after"] = True
            continue
        ex = 0.5
        m = re.match(r"^@(\d*\.?\d+)\s+(.*)$", s)
        if m:
            ex, s = float(m.group(1)), m.group(2)
        lines.append({"text": s, "exaggeration": ex, "break_after": False})
    return lines


def bleep(dur=0.32):
    t = np.arange(int(SR * dur)) / SR
    tone = 0.22 * np.sin(2 * np.pi * 1000 * t)
    f = int(SR * 0.006)
    tone[:f] *= np.linspace(0, 1, f)
    tone[-f:] *= np.linspace(1, 0, f)
    return tone.astype(np.float32)


def silence(sec):
    return np.zeros(int(SR * sec), dtype=np.float32)


def trim(a, thresh=0.01):
    idx = np.nonzero(np.abs(a) > thresh)[0]
    if len(idx) == 0:
        return a
    pad = int(SR * 0.04)
    return a[max(0, idx[0] - pad): idx[-1] + pad]


def main():
    argv = sys.argv[1:]
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and not (i and argv[i - 1] == "--voice")]
    voice = argv[argv.index("--voice") + 1] if "--voice" in argv else "am_puck"
    src, out_dir = args[0], Path(args[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    pipe = KPipeline(lang_code="a")
    lines = parse(src)
    for i, ln in enumerate(lines, 1):
        speed = round(1.0 + (ln["exaggeration"] - 0.5) * 0.3, 3)
        parts, bleeps = [], []
        pieces = ln["text"].split("[BLEEP]")
        for j, piece in enumerate(pieces):
            piece = piece.strip()
            if piece and re.search(r"\w", piece):
                audio = np.concatenate([np.asarray(a) for _, _, a in pipe(piece, voice=voice, speed=speed)])
                parts.append(trim(audio.astype(np.float32)))
            if j < len(pieces) - 1:
                parts.append(silence(0.04))
                bleeps.append([round(sum(len(p) for p in parts) / SR, 4), 0.32])
                parts += [bleep(), silence(0.06)]
        wav = np.concatenate(parts)
        f = out_dir / f"line_{i:03d}.wav"
        sf.write(f, wav, SR)
        ln.update(file=f.name, bleeps=bleeps, duration=round(len(wav) / SR, 3), voice=voice, speed=speed)
        print(f"[{i}/{len(lines)}] {f.name} ({ln['duration']}s)", flush=True)
    (out_dir / "lines.json").write_text(json.dumps(lines, indent=1))
    print("done:", out_dir / "lines.json")


if __name__ == "__main__":
    main()
