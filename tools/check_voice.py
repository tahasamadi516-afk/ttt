#!/usr/bin/env python3
"""Check every voiced line against the script: did it say the right words, at a sane speed?

Run with the asr venv:  ~/asr/.venv/bin/python tools/check_voice.py <narration.txt> <voice_dir> [--report out.json]

Transcribes each line_NNN.wav with Whisper (small.en), compares it word by word with the script
line (censored [BLEEP] words are ignored), and flags lines whose word error rate is above 15%,
or whose speaking rate is outside a natural range. Prints the flagged line numbers on the last
line as "FLAGGED: 3,17" (or "FLAGGED: none"), so a pipeline can re-record them.
"""
import json
import re
import sys
from pathlib import Path

import soundfile as sf
from faster_whisper import WhisperModel

NUM = {"1": "one", "5": "five", "20": "twenty", "100": "hundred"}
# Contractions count as the same words as their long forms.
EXPAND = {"should've": "should have", "would've": "would have", "could've": "could have",
          "i'd": "i would", "we'd": "we would", "it'd": "it would", "you'd": "you would",
          "wanna": "want to", "gonna": "going to"}


def norm(text):
    text = text.lower().replace("[bleep]", " ").replace("’", "'")
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    text = " ".join(EXPAND.get(w, w) for w in text.split())
    words = [NUM.get(w, w) for w in text.split()]
    return [w.strip("'") for w in words if w.strip("'")]


def wer(ref, hyp):
    d = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        prev, d[0] = d[0], i
        for j, h in enumerate(hyp, 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r != h))
            prev, d[j] = d[j], cur
    return d[len(hyp)] / max(1, len(ref))


def script_lines(path):
    out = []
    for raw in Path(path).read_text().splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        s = re.sub(r"^@[a-z0-9.]+\s+", "", s)
        out.append(re.sub(r"\s*\|\|?\s*", " ", s))
    return out


def main():
    args = [a for i, a in enumerate(sys.argv[1:]) if not a.startswith("--") and sys.argv[i] != "--report"]
    src, vdir = args[0], Path(args[1])
    report_path = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    model = WhisperModel("small.en", device="cpu", compute_type="int8", cpu_threads=2)
    rows, flagged = [], []
    for i, line in enumerate(script_lines(src), 1):
        f = vdir / f"line_{i:03d}.wav"
        if not f.exists():
            continue
        segs, _ = model.transcribe(str(f), beam_size=5, language="en")
        heard = " ".join(s.text.strip() for s in segs)
        ref, hyp = norm(line), norm(heard)
        bleeps = line.count("[BLEEP]")
        if bleeps:   # Whisper may write a word or noise for the bleep tone: allow that many extras
            hyp = [w for w in hyp if w not in ("beep", "bleep", "fuck", "f")] or hyp
        hyp = [w for w in hyp if w not in ("ugh", "ah", "uh", "um", "hmm", "oh")] if not any(
            w in ref for w in ("ugh", "ah", "uh", "um", "hmm", "oh")) else hyp   # natural fillers are fine
        e = wer(ref, hyp)
        dur = sf.info(str(f)).duration
        rate = len(ref) / max(0.1, dur - 0.32 * bleeps)
        bad = e > 0.15 or rate > 3.8 or rate < 1.1
        rows.append({"line": i, "wer": round(e, 3), "words_per_sec": round(rate, 2), "flag": bad,
                     "script": line, "heard": heard})
        if bad:
            flagged.append(i)
        print(f"{'FLAG' if bad else ' ok '} {i:2d} wer={e:.2f} rate={rate:.1f}  heard: {heard[:90]}", flush=True)
    if report_path:
        Path(report_path).write_text(json.dumps(rows, indent=1))
    print("FLAGGED:", ",".join(map(str, flagged)) or "none")


if __name__ == "__main__":
    main()
