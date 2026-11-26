"""Voice a narration file with Orpheus TTS (expressive, free for commercial use, runs on CPU).

Run with the chatterbox venv (it has torch, llama-cpp-python and snac; see setup.sh):
    ~/chatterbox/.venv/bin/python youtube/voice-clone/narrate_orpheus.py <narration.txt> <out_dir>
        [--voice leo] [--only 3,7] [--model ~/orpheus/orpheus-q4km.gguf]

Same narration.txt format and output (line_NNN.wav + lines.json) as the other narrators:
  " | " beat, " || " long pause, [BLEEP], "@0.7" expressiveness, blank line = paragraph.
Orpheus also understands emotion tags written into the text:
  <laugh> <chuckle> <sigh> <groan> <gasp> <yawn> <cough> <sniffle>
"@" expressiveness maps to sampling temperature (more expressive = a bit wilder delivery).
Clips already generated are skipped, so it can resume.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from llama_cpp import Llama
from snac import SNAC

SR = 24000
START, BOS, EOT, END_HUMAN = 128259, 128000, 128009, 128260
SPEECH_START, SPEECH_END, CODE_BASE = 128257, 128258, 128266


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


def trim(a, thresh=0.008):
    idx = np.nonzero(np.abs(a) > thresh)[0]
    if len(idx) == 0:
        return a
    pad = int(SR * 0.05)
    return a[max(0, idx[0] - pad): idx[-1] + pad]


class Orpheus:
    def __init__(self, model_path, voice):
        self.llm = Llama(model_path=str(model_path), n_ctx=4096, n_threads=4, verbose=False)
        self.snac = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval()
        self.voice = voice

    def say(self, text, temp=0.6, max_tokens=2400):
        prompt = [START, BOS] + self.llm.tokenize(f"{self.voice}: {text}".encode(), add_bos=False, special=True) \
            + [EOT, END_HUMAN]
        codes, started = [], False
        for tok in self.llm.generate(prompt, temp=temp, top_p=0.9, repeat_penalty=1.1, reset=True):
            if tok == SPEECH_END or tok == EOT or len(codes) >= max_tokens:
                break
            if tok == SPEECH_START:
                started = True
                continue
            if started and tok >= CODE_BASE:
                codes.append(tok - CODE_BASE - (len(codes) % 7) * 4096)
        n = len(codes) // 7
        if n == 0:
            return np.zeros(0, dtype=np.float32)
        c = codes[: n * 7]
        l0, l1, l2 = [], [], []
        for j in range(n):
            i = 7 * j
            l0.append(c[i])
            l1 += [c[i + 1], c[i + 4]]
            l2 += [c[i + 2], c[i + 3], c[i + 5], c[i + 6]]
        layers = [torch.tensor(x).clamp(0, 4095).unsqueeze(0) for x in (l0, l1, l2)]
        with torch.inference_mode():
            audio = self.snac.decode(layers)
        return audio.squeeze().numpy().astype(np.float32)


def main():
    argv = sys.argv[1:]
    takes = ("--voice", "--only", "--model")
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and not (i and argv[i - 1] in takes)]
    voice = argv[argv.index("--voice") + 1] if "--voice" in argv else "leo"
    model = Path(argv[argv.index("--model") + 1] if "--model" in argv else Path.home() / "orpheus/orpheus-q4km.gguf")
    only = {int(x) for x in argv[argv.index("--only") + 1].split(",")} if "--only" in argv else None
    src, out_dir = args[0], Path(args[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    tts = Orpheus(model, voice)
    lines = parse(src)
    for i, ln in enumerate(lines, 1):
        f = out_dir / f"line_{i:03d}.wav"
        meta = out_dir / f"line_{i:03d}.json"
        ln["file"] = f.name
        if (only and i not in only) or (not only and f.exists() and meta.exists()):
            continue
        temp = round(0.5 + (ln["exaggeration"] - 0.5) * 0.4, 3)
        parts, bleeps = [], []
        for tok in [t.strip() for t in re.split(r"(\[BLEEP\]|\|\||\|)", ln["text"]) if t.strip()]:
            if tok == "||":
                parts.append(silence(0.85))
            elif tok == "|":
                parts.append(silence(0.4))
            elif tok == "[BLEEP]":
                parts.append(silence(0.04))
                bleeps.append([round(sum(len(p) for p in parts) / SR, 4), 0.32])
                parts += [bleep(), silence(0.06)]
            elif re.search(r"\w", tok):
                parts.append(trim(tts.say(tok, temp=temp)))
        wav = np.concatenate(parts) if parts else silence(0.5)
        sf.write(f, wav, SR)
        meta.write_text(json.dumps({"bleeps": bleeps, "temp": temp}))
        print(f"[{i}/{len(lines)}] {f.name} ({len(wav) / SR:.1f}s)", flush=True)
    for i, ln in enumerate(lines, 1):
        f, meta = out_dir / ln["file"], out_dir / f"line_{i:03d}.json"
        if f.exists():
            ln["duration"] = round(sf.info(str(f)).frames / SR, 3)
            ln["bleeps"] = json.loads(meta.read_text())["bleeps"] if meta.exists() else []
            ln["voice"] = f"orpheus:{voice}"
    (out_dir / "lines.json").write_text(json.dumps(lines, indent=1))
    print("done:", out_dir / "lines.json")


if __name__ == "__main__":
    main()
