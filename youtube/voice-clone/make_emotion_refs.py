"""Make one reference clip per emotion for voice E, so each line can be cloned in the right mood.

Run with the qwentts venv:  ~/qwentts/.venv/bin/python youtube/voice-clone/make_emotion_refs.py [--takes 3]

For each emotion: VoiceDesign generates a few takes from E's description plus that emotion,
then each take's speaker embedding is compared with ref-voice-e.wav and the closest one is kept
(so he stays the same guy). Writes emotions/<name>.wav + .txt and emotions/scores.json.
Two passes (design, then score) so only one 1.7B model is in memory at a time.
"""
import gc
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

HERE = Path(__file__).parent
OUT = HERE / "emotions"
TAKES = int(sys.argv[sys.argv.index("--takes") + 1]) if "--takes" in sys.argv else 3
BASE = ("Male, early twenties, General American accent. Clear medium-deep voice, natural and grounded, "
        "like a real person talking to a friend. Speaks at a relaxed, unhurried pace with natural pauses. ")
EMOTIONS = {
    "calm": ("Calm, relaxed storytelling, low energy, not excited.",
             "So here's the thing. I was making breakfast this morning, just a normal day, and out of nowhere it all came back to me. Five months. Gone."),
    "dry": ("Dry, deadpan, sarcastic, flat delivery, unimpressed.",
            "Oh, great idea. Really. Jump right into another one. That'll fix everything. Amazing plan. Genius, honestly."),
    "frustrated": ("Frustrated and exasperated at himself, a bit louder, but controlled.",
                   "Why did I even care? I didn't like her. I didn't want any of it. And I still kept going back. What was I doing?"),
    "sad": ("Quiet, low, a little sad and reflective, slow.",
            "I used to train every single day. I had plans. Big ones. And somewhere along the way, I just stopped. I don't even know when."),
    "warm": ("Warm, gentle and sincere, soft and kind.",
             "Hey. You're going to be okay. You can start over. People do it all the time. Give it a little time, and be patient with yourself."),
    "amused": ("Lightly amused, chuckling at himself, relaxed smile in the voice.",
               "Honestly, looking back, it's kind of hilarious. I knew exactly what I was doing, and I just kept doing it anyway. Classic."),
    "serious": ("Serious, low and intense, dramatic but quiet, slow.",
                "It's like a drug. You know it's bad for you. You know exactly where it leads. And you reach for it anyway."),
    "shocked": ("Surprised and shocked, realization dawning, a little breathy.",
                "Wait. Hold on. Wait a minute. Do I do that too? Is that what I look like?"),
}


def main():
    torch.set_num_threads(4)
    OUT.mkdir(exist_ok=True)
    tmp = OUT / "_takes"
    tmp.mkdir(exist_ok=True)

    design = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", device_map="cpu",
                                           dtype=torch.float32, attn_implementation="sdpa")
    for name, (mood, text) in EMOTIONS.items():
        for k in range(TAKES):
            f = tmp / f"{name}_{k}.wav"
            if f.exists():
                continue
            w, sr = design.generate_voice_design(text=text, language="English", instruct=BASE + mood)
            sf.write(f, w[0], sr)
            print(f"designed {name} take {k}", flush=True)
    del design
    gc.collect()

    base = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cpu",
                                         dtype=torch.float32, attn_implementation="sdpa")

    def emb(path, text):
        it = base.create_voice_clone_prompt(ref_audio=str(path), ref_text=text, x_vector_only_mode=True)[0]
        v = np.asarray(it.ref_spk_embedding, dtype=np.float32)
        return v / (np.linalg.norm(v) + 1e-9)

    target = emb(HERE / "ref-voice-e.wav", (HERE / "ref-voice-e.txt").read_text().strip())
    scores = {}
    for name, (mood, text) in EMOTIONS.items():
        best, best_s = None, -1
        for k in range(TAKES):
            f = tmp / f"{name}_{k}.wav"
            s = float(emb(f, text) @ target)
            scores[f"{name}_{k}"] = round(s, 4)
            if s > best_s:
                best, best_s = f, s
        (OUT / f"{name}.wav").write_bytes(best.read_bytes())
        (OUT / f"{name}.txt").write_text(text + "\n")
        print(f"{name}: kept {best.name} (similarity to E {best_s:.3f})", flush=True)
    (OUT / "scores.json").write_text(json.dumps(scores, indent=1))


if __name__ == "__main__":
    main()
