"""Voice a whole narration file in the cloned voice, one clip per line, with bleeps.

Run with the chatterbox venv (see setup.sh):
    ~/chatterbox/.venv/bin/python youtube/voice-clone/narrate.py <narration.txt> <out_dir> [--only 3,7]

narration.txt format (see youtube/videos/*/narration.txt):
  - one line = one clip, saved as out_dir/line_NNN.wav
  - [BLEEP] marks a censored word; a bleep tone goes there
  - a line starting with "@0.7 " sets expressiveness for that line (default 0.5)
  - a blank line = a paragraph break (a longer pause in the full mix)
  - lines starting with # are comments
Writes out_dir/lines.json (text, file, duration, paragraph break after) for the editor.
Already-generated clips are skipped, so it can resume; --only regenerates given line numbers.
"""
import json
import re
import sys
from pathlib import Path

import torch
import torchaudio as ta

_load = torch.load
torch.load = lambda *a, **k: _load(*a, **{**k, "map_location": torch.device("cpu")})  # CPU-only machine
from chatterbox.tts import ChatterboxTTS  # noqa: E402

REF = Path(__file__).with_name("ref.wav")
MAX_CHARS = 220  # long inputs make the model drift; split at sentence ends


def parse(path):
    lines, para = [], False
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


def chunks(text):
    """Split text into pieces no longer than MAX_CHARS, at sentence boundaries."""
    sents = re.split(r"(?<=[.!?])\s+", text)
    out, cur = [], ""
    for s in sents:
        if cur and len(cur) + len(s) + 1 > MAX_CHARS:
            out.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        out.append(cur)
    return out


def bleep(sr, dur=0.32):
    t = torch.arange(int(sr * dur)) / sr
    tone = 0.22 * torch.sin(2 * torch.pi * 1000 * t)
    fade = int(sr * 0.006)
    env = torch.ones_like(tone)
    env[:fade] = torch.linspace(0, 1, fade)
    env[-fade:] = torch.linspace(1, 0, fade)
    return (tone * env).unsqueeze(0)


def silence(sr, sec):
    return torch.zeros(1, int(sr * sec))


def trim(w, sr, thresh=0.01):
    """Cut leading/trailing near-silence the model adds, keeping 40 ms."""
    a = w.abs().squeeze(0)
    idx = torch.nonzero(a > thresh)
    if len(idx) == 0:
        return w
    pad = int(sr * 0.04)
    return w[:, max(0, idx[0].item() - pad): idx[-1].item() + pad]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    src, out_dir = args[0], Path(args[1])
    only = None
    if "--only" in sys.argv:
        only = {int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")}
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = parse(src)
    model = ChatterboxTTS.from_pretrained(device="cpu")
    sr = model.sr
    for i, ln in enumerate(lines, 1):
        f = out_dir / f"line_{i:03d}.wav"
        ln["file"] = f.name
        if f.exists() and not (only and i in only):
            continue
        if only and i not in only:
            continue
        parts = []
        pieces = ln["text"].split("[BLEEP]")
        for j, piece in enumerate(pieces):
            piece = piece.strip()
            if piece and re.search(r"\w", piece):
                for c in chunks(piece):
                    w = model.generate(c, audio_prompt_path=str(REF),
                                       exaggeration=ln["exaggeration"], cfg_weight=0.5)
                    parts += [trim(w, sr), silence(sr, 0.12)]
                if parts:
                    parts.pop()  # no gap before the bleep
            if j < len(pieces) - 1:
                parts += [silence(sr, 0.04), bleep(sr), silence(sr, 0.06)]
        ta.save(str(f), torch.cat(parts, dim=1), sr)
        print(f"[{i}/{len(lines)}] {f.name}: {ln['text'][:60]}", flush=True)
    for ln in lines:
        f = out_dir / ln["file"]
        if f.exists():
            info = ta.info(str(f))
            ln["duration"] = round(info.num_frames / info.sample_rate, 3)
    (out_dir / "lines.json").write_text(json.dumps(lines, indent=1))
    print("done:", out_dir / "lines.json")


if __name__ == "__main__":
    main()
