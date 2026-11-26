"""Voice a narration file in the channel voice "E" (Qwen3-TTS clone of ref-voice-e.wav), with bleeps.

Run with the qwentts venv (see setup.sh):
    ~/qwentts/.venv/bin/python youtube/voice-clone/narrate_qwen.py <narration.txt> <out_dir> [--only 3,7]

Same narration.txt format and output (line_NNN.wav + lines.json with bleep positions) as the
other narrators, so build_video.py works unchanged. Lines are voiced whole so the delivery stays
natural; "@sad" etc. picks the emotion reference (emotions/sad.wav) for that line; [BLEEP] splits a line into pieces with a bleep tone between them.
Clips already generated are skipped, so it can resume after an interruption.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

HERE = Path(__file__).parent
REF_WAV, REF_TXT = HERE / "ref-voice-e.wav", HERE / "ref-voice-e.txt"


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
        emo = "calm"
        m = re.match(r"^@([a-z]+)\s+(.*)$", s)
        if m:
            emo, s = m.group(1), m.group(2)
        s = re.sub(r"^@(\d*\.?\d+)\s+", "", s)          # numeric expressiveness tags are not used here
        s = re.sub(r"\s*\|\|?\s*", " ", s).strip()        # nor manual pause marks: delivery is natural
        lines.append({"text": s, "emotion": emo, "break_after": False})
    return lines


def main():
    argv = sys.argv[1:]
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and not (i and argv[i - 1] == "--only")]
    only = {int(x) for x in argv[argv.index("--only") + 1].split(",")} if "--only" in argv else None
    src, out_dir = args[0], Path(args[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    m = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cpu",
                                      dtype=torch.float32, attn_implementation="sdpa")
    # One clone prompt per emotion (emotions/<name>.wav from make_emotion_refs.py); falls back to E.
    prompts = {}
    for wav in sorted((HERE / "emotions").glob("*.wav")):
        prompts[wav.stem] = m.create_voice_clone_prompt(ref_audio=str(wav), ref_text=wav.with_suffix(".txt").read_text().strip(),
                                                        x_vector_only_mode=False)
    default = m.create_voice_clone_prompt(ref_audio=str(REF_WAV), ref_text=REF_TXT.read_text().strip(),
                                          x_vector_only_mode=False)
    sr = None
    lines = parse(src)

    def say(text, emo="calm"):
        nonlocal sr
        w, sr = m.generate_voice_clone(text=text, language="English", voice_clone_prompt=prompts.get(emo, default))
        a = np.asarray(w[0], dtype=np.float32)
        idx = np.nonzero(np.abs(a) > 0.008)[0]
        if len(idx):
            pad = int(sr * 0.05)
            a = a[max(0, idx[0] - pad): idx[-1] + pad]
        return a

    for i, ln in enumerate(lines, 1):
        f, meta = out_dir / f"line_{i:03d}.wav", out_dir / f"line_{i:03d}.json"
        ln["file"] = f.name
        if (only and i not in only) or (not only and f.exists() and meta.exists()):
            continue
        parts, bleeps = [], []
        pieces = ln["text"].split("[BLEEP]")
        for j, piece in enumerate(pieces):
            piece = piece.strip()
            if piece and re.search(r"\w", piece):
                parts.append(say(piece, ln["emotion"]))
            if j < len(pieces) - 1:
                parts.append(np.zeros(int(sr * 0.04), np.float32))
                start = sum(len(p) for p in parts) / sr
                t = np.arange(int(sr * 0.32)) / sr
                tone = (0.22 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
                fd = int(sr * 0.006)
                tone[:fd] *= np.linspace(0, 1, fd)
                tone[-fd:] *= np.linspace(1, 0, fd)
                bleeps.append([round(start, 4), 0.32])
                parts += [tone, np.zeros(int(sr * 0.06), np.float32)]
        wav = np.concatenate(parts)
        sf.write(f, wav, sr)
        meta.write_text(json.dumps({"bleeps": bleeps}))
        print(f"[{i}/{len(lines)}] {f.name} ({len(wav) / sr:.1f}s)", flush=True)

    for i, ln in enumerate(lines, 1):
        f, meta = out_dir / ln["file"], out_dir / f"line_{i:03d}.json"
        if f.exists():
            info = sf.info(str(f))
            ln["duration"] = round(info.frames / info.samplerate, 3)
            ln["bleeps"] = json.loads(meta.read_text())["bleeps"] if meta.exists() else []
            ln["voice"] = f"qwen3:E:{ln['emotion']}"
    (out_dir / "lines.json").write_text(json.dumps(lines, indent=1))
    print("done:", out_dir / "lines.json")


if __name__ == "__main__":
    main()
