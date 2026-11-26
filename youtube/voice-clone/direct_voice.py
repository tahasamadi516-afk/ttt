"""Directed voice: every line performed from its own acting note, in voice E, best of N takes.

Run with the qwentts venv:
    ~/qwentts/.venv/bin/python youtube/voice-clone/direct_voice.py <narration.txt> <directions.json> <out_dir>
        [--takes 3] [--only 3,18]

For each line: Qwen3-TTS VoiceDesign performs it from PERSONA + that line's note, N times.
Each take's speaker embedding (Qwen3-TTS 0.6B Base) is compared with ref-voice-e.wav and the
closest take is kept, so every line has its own performance but he stays the same guy.
[BLEEP] splits a line into pieces with a bleep tone between them (each piece is cast the same way).
Output matches the other narrators: line_NNN.wav (+ .json with bleeps and scores) and lines.json.
Resumable: finished lines are skipped.
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
PERSONA = ("Male, early twenties, General American accent. Clear medium-deep voice, natural and grounded, "
           "like a real person talking to a friend, not a radio host. Relaxed, unhurried pace with natural "
           "pauses; never rushed and never over-excited. Delivery for this line: ")


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
        s = re.sub(r"^@[a-z]+\s+", "", s)
        s = re.sub(r"^@(\d*\.?\d+)\s+", "", s)
        s = re.sub(r"\s*\|\|?\s*", " ", s).strip()
        lines.append({"text": s, "break_after": False})
    return lines


def main():
    argv = sys.argv[1:]
    takes_n = int(argv[argv.index("--takes") + 1]) if "--takes" in argv else 3
    only = {int(x) for x in argv[argv.index("--only") + 1].split(",")} if "--only" in argv else None
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and not (i and argv[i - 1] in ("--takes", "--only"))]
    src, dirs_path, out_dir = args[0], Path(args[1]), Path(args[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    notes = json.loads(dirs_path.read_text())
    torch.set_num_threads(4)

    design = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", device_map="cpu",
                                           dtype=torch.float32, attn_implementation="sdpa")
    judge = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-0.6B-Base", device_map="cpu",
                                          dtype=torch.float32, attn_implementation="sdpa")

    def emb(audio, sr):
        it = judge.create_voice_clone_prompt(ref_audio=(audio, sr), ref_text="", x_vector_only_mode=True)[0]
        v = np.asarray(it.ref_spk_embedding, dtype=np.float32)
        return v / (np.linalg.norm(v) + 1e-9)

    ref, ref_sr = sf.read(str(HERE / "ref-voice-e.wav"), dtype="float32")
    target = emb(ref, ref_sr)

    def trim(a, sr):
        idx = np.nonzero(np.abs(a) > 0.008)[0]
        if not len(idx):
            return a
        pad = int(sr * 0.06)
        return a[max(0, idx[0] - pad): idx[-1] + pad]

    def cast(text, note):
        best, best_s, sr = None, -2.0, 24000
        for _ in range(takes_n):
            w, sr = design.generate_voice_design(text=text, language="English", instruct=PERSONA + note)
            a = trim(np.asarray(w[0], dtype=np.float32), sr)
            s = float(emb(a, sr) @ target)
            if s > best_s:
                best, best_s = a, s
        return best, best_s, sr

    lines = parse(src)
    for i, ln in enumerate(lines, 1):
        f, meta = out_dir / f"line_{i:03d}.wav", out_dir / f"line_{i:03d}.json"
        ln["file"] = f.name
        if (only and i not in only) or (not only and f.exists() and meta.exists()):
            continue
        note = notes.get(str(i), "Natural and calm.")
        parts, bleeps, scores, sr = [], [], [], 24000
        pieces = ln["text"].split("[BLEEP]")
        for j, piece in enumerate(pieces):
            piece = piece.strip()
            if piece and re.search(r"\w", piece):
                a, s, sr = cast(piece, note)
                parts.append(a)
                scores.append(round(s, 4))
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
        meta.write_text(json.dumps({"bleeps": bleeps, "similarity": scores, "note": note}))
        print(f"[{i}/{len(lines)}] {f.name} ({len(wav) / sr:.1f}s, similarity {scores})", flush=True)

    for i, ln in enumerate(lines, 1):
        f, meta = out_dir / ln["file"], out_dir / f"line_{i:03d}.json"
        if f.exists():
            info = sf.info(str(f))
            ln["duration"] = round(info.frames / info.samplerate, 3)
            m = json.loads(meta.read_text()) if meta.exists() else {}
            ln["bleeps"] = m.get("bleeps", [])
            ln["voice"] = "qwen3:E:directed"
    (out_dir / "lines.json").write_text(json.dumps(lines, indent=1))
    print("done:", out_dir / "lines.json")


if __name__ == "__main__":
    main()
