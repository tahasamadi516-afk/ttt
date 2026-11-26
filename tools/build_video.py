#!/usr/bin/env python3
"""Assemble a full video from a voiceover, an edit plan, scenes, music and sound effects.

Usage:
    python3 tools/build_video.py youtube/videos/01-who-was-that-guy [--jobs 3] [--preview]

The video folder needs:
  voice/lines.json   from youtube/voice-clone/narrate.py (one clip per narration line)
  edit.json          the edit plan (which shot covers which lines, music, sfx)
Writes:
  build/shots/*.mp4  rendered shots (cached by content, so re-runs only redo changes)
  build/voice.wav, build/mix.wav, final.mp4
--preview renders at 960x540 for a fast check.
"""
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
LEAD_IN = 0.4


def sh(cmd):
    subprocess.run(cmd, check=True)


def rel_from_scenes(p):
    """Path as seen from tools/scenes/ (where the scene HTML lives)."""
    return "../../" + str(p)


def main():
    vdir = (ROOT / sys.argv[1]).resolve()
    jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 3
    preview = "--preview" in sys.argv
    W, H = (960, 540) if preview else (1920, 1080)
    plan = json.loads((vdir / "edit.json").read_text())
    lines = json.loads((vdir / "voice" / "lines.json").read_text())
    d = plan["defaults"]
    build = vdir / ("build-preview" if preview else "build")
    (build / "shots").mkdir(parents=True, exist_ok=True)

    # 1. Timeline: when each narration line starts.
    t = LEAD_IN
    starts = []
    for ln in lines:
        starts.append(t)
        t += ln["duration"] + (d["break"] if ln.get("break_after") else d["gap"])
    end_time = t + d["tail"]
    starts.append(end_time)  # sentinel

    def line_start(n):
        return starts[n - 1]

    # 2. Shots with absolute frame ranges.
    shots = []
    edits = plan["edits"]
    for i, e in enumerate(edits):
        a = 0.0 if i == 0 else line_start(e["lines"][0])
        b = line_start(edits[i + 1]["lines"][0]) if i + 1 < len(edits) else end_time
        ss = e["shots"]
        for j, s in enumerate(ss):
            f0 = a + (b - a) * s.get("at", 0.0)
            f1 = a + (b - a) * ss[j + 1]["at"] if j + 1 < len(ss) else b
            shots.append((round(f0 * FPS), round(f1 * FPS), s))

    # 3. Render each shot (cached).
    def scene_args(s):
        k = s["kind"]
        if k == "char":
            bg = plan["bgs"].get(s.get("bg")) if s.get("bg") else None
            p = {"poses": [{"src": rel_from_scenes(f"youtube/assets/character/{s['pose']}.png"), "at": 0}],
                 "x": s.get("x", 0.5), "height": s.get("height", 0.92), "push": s.get("push", 0.05),
                 "tint": s.get("tint", "none"), "flashes": s.get("flashes", []), "zoom": s.get("zoom", 0)}
            if bg:
                p["bg"] = rel_from_scenes(bg)
            return "character.html", p
        if k == "scene":
            return "character.html", {"bg": rel_from_scenes(f"youtube/assets/backgrounds/{s['img']}.png"),
                                       "push": s.get("push", 0.08), "flashes": s.get("flashes", []),
                                       "zoom": s.get("zoom", 0)}
        if k == "title":
            return "title.html", {"lines": s["lines"], "accent": s.get("accent", []), "gap": s.get("gap", 0.18),
                                  "size": 150 * W // 1920, "start": 0.05}
        if k == "messages":
            return "messages.html", {k2: v for k2, v in s.items() if k2 not in ("kind", "at")}
        raise ValueError(k)

    def render(item):
        f0, f1, s = item
        scene, params = scene_args(s)
        dur = (f1 - f0) / FPS
        key = hashlib.sha1(json.dumps([scene, params, f1 - f0, W], sort_keys=True).encode()).hexdigest()[:16]
        out = build / "shots" / f"{key}.mp4"
        if not out.exists():
            tmp = out.with_suffix(".tmp.mp4")
            sh(["node", str(ROOT / "tools/render.mjs"), str(ROOT / "tools/scenes" / scene), str(tmp),
                "--duration", f"{dur:.6f}", "--fps", str(FPS), "--width", str(W), "--height", str(H),
                "--params", json.dumps(params)])
            tmp.rename(out)
        return out

    print(f"{len(shots)} shots, {end_time:.1f}s total; rendering with {jobs} jobs")
    with ThreadPoolExecutor(jobs) as ex:
        outs = list(ex.map(render, shots))
    listf = build / "shots.txt"
    listf.write_text("".join(f"file '{o}'\n" for o in outs))
    sh(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listf),
        "-c", "copy", str(build / "video.mp4")])

    # 4. Voice track: every line placed at its start, then the studio polish chain.
    vin, vf = [], []
    for i, ln in enumerate(lines):
        vin += ["-i", str(vdir / "voice" / ln["file"])]
        ms = int(starts[i] * 1000)
        vf.append(f"[{i}:a]aresample=48000,adelay={ms}|{ms}[v{i}]")
    vf.append("".join(f"[v{i}]" for i in range(len(lines))) +
              f"amix=inputs={len(lines)}:normalize=0,apad=whole_dur={end_time:.3f},"
              "highpass=f=80,equalizer=f=140:t=q:w=1:g=2.5,equalizer=f=300:t=q:w=1.2:g=-2,"
              "equalizer=f=3500:t=q:w=1:g=2,acompressor=threshold=-22dB:ratio=3:attack=8:release=120:makeup=4,"
              "deesser=i=0.3,loudnorm=I=-16:TP=-2[out]")
    sh(["ffmpeg", "-loglevel", "error", "-y", *vin, "-filter_complex", ";".join(vf), "-map", "[out]",
        "-ac", "2", "-ar", "48000", str(build / "voice.wav")])

    # 5. Music beds and sound effects, mixed under the voice.
    ins, fx, labels = ["-i", str(build / "voice.wav")], [], ["[0:a]"]
    n = 1
    for c in plan["music"]:
        a, b = line_start(c["lines"][0]), line_start(c["lines"][1] + 1)
        dur = b - a
        ins += ["-stream_loop", "-1", "-i", str(ROOT / plan["tracks"][c["track"]])]
        out_fade = 0.08 if c["track"] == "dark" else 0.8  # dark = hard cut back to reality
        ms = int(a * 1000)
        fx.append(f"[{n}:a]aresample=48000,atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.3,"
                  f"afade=t=out:st={max(0, dur - out_fade):.3f}:d={out_fade},volume=0.55,adelay={ms}|{ms}[m{n}]")
        labels.append(f"[m{n}]")
        n += 1
    for line, frac, name, vol in plan["sfx"]:
        a, b = line_start(line), line_start(line + 1)
        ms = int((a + (b - a) * frac) * 1000)
        ins += ["-i", str(ROOT / f"youtube/assets/sfx/{name}.wav")]
        fx.append(f"[{n}:a]aresample=48000,volume={vol * 0.6},adelay={ms}|{ms}[s{n}]")
        labels.append(f"[s{n}]")
        n += 1
    fx.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.95[out]")
    sh(["ffmpeg", "-loglevel", "error", "-y", *ins, "-filter_complex", ";".join(fx), "-map", "[out]",
        "-t", f"{end_time:.3f}", "-ac", "2", "-ar", "48000", str(build / "mix.wav")])

    # 6. Mux.
    final = vdir / ("preview.mp4" if preview else "final.mp4")
    sh(["ffmpeg", "-loglevel", "error", "-y", "-i", str(build / "video.mp4"), "-i", str(build / "mix.wav"),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)])
    print("wrote", final.relative_to(ROOT))


if __name__ == "__main__":
    main()
