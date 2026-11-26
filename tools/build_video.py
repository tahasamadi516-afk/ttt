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
    # Speaking speed: < 1 slows the voice down without changing its pitch (0.9 = 10% slower).
    tempo = float(d.get("voice_tempo", 1.0))
    build = vdir / ("build-preview" if preview else "build")
    (build / "shots").mkdir(parents=True, exist_ok=True)

    # 1. Timeline: when each narration line starts.
    t = LEAD_IN
    starts = []
    for ln in lines:
        starts.append(t)
        t += ln["duration"] / tempo + (d["break"] if ln.get("break_after") else d["gap"])
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

    # 2b. Auto-cut: no character/scene shot holds longer than ~2.8 s. Long shots are split into
    # pieces with different camera framings (wide / close-up on the face / medium), so the frame
    # changes every 2-3 seconds. Punchlines are pinned to absolute time so they stay up across cuts.
    max_len = plan["defaults"].get("max_shot", 2.8)
    CHAR_FRAMES = [None, {"scale": 1.32, "oy": 0.22}, {"scale": 1.12, "oy": 0.42}]
    SCENE_FRAMES = [None, {"scale": 1.18, "ox": 0.6, "oy": 0.5}, {"scale": 1.14, "ox": 0.4, "oy": 0.45}]
    cut = []
    for f0, f1, s in shots:
        dur = (f1 - f0) / FPS
        s = dict(s)
        if "punch" in s and "at_frac" in s["punch"]:
            s["punch"] = dict(s["punch"])
            s["punch"]["abs"] = f0 / FPS + dur * s["punch"].pop("at_frac")
        if s["kind"] not in ("char", "scene") or dur <= max_len * 1.15:
            cut.append((f0, f1, s))
            continue
        n = max(2, round(dur / 2.5))
        bounds = [round(f0 + (f1 - f0) * k / n) for k in range(n + 1)]
        frames = CHAR_FRAMES if s["kind"] == "char" else SCENE_FRAMES
        for k in range(n):
            sub = dict(s)
            sub["_offset"] = (bounds[k] - f0) / FPS
            fr = frames[k % len(frames)]
            if fr:
                fr = dict(fr)
                if s["kind"] == "char":
                    fr.setdefault("ox", s.get("x", 0.5))
                sub["frame"] = fr
            if k > 0:
                sub.pop("label", None)
                sub["zoom"] = 0
                sub["intro"] = "soft"
            cut.append((bounds[k], bounds[k + 1], sub))
    shots = cut

    # 3a. Voice track (built first: the talking motion reads its loudness): every line placed at its start, then the studio polish chain.
    vin, vf = [], []
    clean = vdir / "voice" / "clean"
    for i, ln in enumerate(lines):
        src = clean / ln["file"] if (clean / ln["file"]).exists() else vdir / "voice" / ln["file"]
        vin += ["-i", str(src)]
        ms = int(starts[i] * 1000)
        vf.append(f"[{i}:a]aresample=48000,atempo={tempo},adelay={ms}|{ms}[v{i}]")
    vf.append("".join(f"[v{i}]" for i in range(len(lines))) +
              f"amix=inputs={len(lines)}:normalize=0,apad=whole_dur={end_time:.3f},"
              "highpass=f=75,equalizer=f=250:t=q:w=1.4:g=-3,equalizer=f=4000:t=q:w=1:g=2,"
              "equalizer=f=10000:t=q:w=1:g=1.5,acompressor=threshold=-20dB:ratio=2.5:attack=10:release=150:makeup=3,"
              "deesser=i=0.25,loudnorm=I=-16:TP=-1.5:LRA=9[out]")
    sh(["ffmpeg", "-loglevel", "error", "-y", *vin, "-filter_complex", ";".join(vf), "-map", "[out]",
        "-ac", "2", "-ar", "48000", str(build / "voice.wav")])

    # 3b. Voice loudness per frame -> talking motion for the character.
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(build / "voice.wav"), "-ac", "1", "-ar", "48000",
                          "-f", "s16le", "-"], check=True, capture_output=True).stdout
    pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    hop = 48000 // FPS
    nfr = len(pcm) // hop
    rms = np.sqrt((pcm[: nfr * hop].reshape(nfr, hop) ** 2).mean(axis=1))
    env = np.clip((20 * np.log10(rms + 1e-6) + 45) / 30, 0, 1)   # -45 dB -> 0, -15 dB -> 1
    env = np.round(env, 2)

    # Sound-effect hits (shake the camera) as absolute times.
    HIT_SFX = {"impact", "thud", "thunder", "record-scratch"}
    hit_times = []
    for line, frac, name, vol in plan["sfx"]:
        if name in HIT_SFX:
            la, lb = line_start(line), line_start(line + 1)
            hit_times.append(la + (lb - la) * frac)

    # 3c. Render each shot (cached).
    def scene_args(s, f0=0, f1=0):
        k = s["kind"]
        t0, t1 = f0 / FPS, f1 / FPS
        local_hits = [round(h - t0, 3) for h in hit_times if t0 <= h < t1]
        extra = {"hits": local_hits, "intro": s.get("intro", "pop")}
        for key in ("punch", "label", "particles", "captions"):
            if key in s:
                extra[key] = dict(s[key]) if isinstance(s[key], dict) else s[key]
        if "punch" in extra and "abs" in extra["punch"]:       # punch pinned to absolute time
            at = extra["punch"].pop("abs") - t0
            if at >= t1 - t0:
                extra.pop("punch")                              # appears in a later piece
            else:
                extra["punch"]["at"] = round(at, 3)             # negative = already on screen
        off = s.get("_offset", 0.0)
        flashes = [round(f - off, 3) for f in s.get("flashes", []) if f >= off]
        if "frame" in s:
            extra["frame"] = s["frame"]
        if k == "char":
            bg = plan["bgs"].get(s.get("bg")) if s.get("bg") else None
            p = {"poses": [{"src": rel_from_scenes(f"youtube/assets/character/{s['pose']}.png"), "at": 0}],
                 "x": s.get("x", 0.5), "height": s.get("height", 0.92), "push": s.get("push", 0.05),
                 "tint": s.get("tint", "none"), "flashes": flashes, "zoom": s.get("zoom", 0),
                 "env": env[f0:f1].tolist(), **extra}
            if bg:
                p["bg"] = rel_from_scenes(bg)
            return "character.html", p
        if k == "scene":
            return "character.html", {"bg": rel_from_scenes(f"youtube/assets/backgrounds/{s['img']}.png"),
                                       "push": s.get("push", 0.08), "flashes": flashes,
                                       "zoom": s.get("zoom", 0), "tint": s.get("tint", "none"), **extra}
        if k == "title":
            return "title.html", {"lines": s["lines"], "accent": s.get("accent", []), "gap": s.get("gap", 0.18),
                                  "size": 150 * W // 1920, "start": 0.05}
        if k == "messages":
            return "messages.html", {k2: v for k2, v in s.items() if k2 not in ("kind", "at")}
        raise ValueError(k)

    def render(item):
        f0, f1, s = item
        scene, params = scene_args(s, f0, f1)
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

    # 5. Music beds and sound effects, mixed under the voice.
    ins, fx, labels = ["-i", str(build / "voice.wav")], [], ["[vmain]"]
    n = 1
    for c in plan["music"]:
        a, b = line_start(c["lines"][0]), line_start(c["lines"][1] + 1)
        dur = b - a
        ins += ["-stream_loop", "-1", "-i", str(ROOT / plan["tracks"][c["track"]])]
        out_fade = 0.08 if c["track"] == "dark" else 0.8  # dark = hard cut back to reality
        ms = int(a * 1000)
        fx.append(f"[{n}:a]aresample=48000,atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.3,"
                  f"afade=t=out:st={max(0, dur - out_fade):.3f}:d={out_fade},volume=0.30,adelay={ms}|{ms}[m{n}]")
        labels.append(f"[m{n}]")
        n += 1
    # A cappella bed under the whole video (very low), dipped out under the epic cues.
    # "beds": one mood per section [{"files": [...], "lines": [from, to]}], blended into each other;
    # or a single "bed": {"file": ...} for the whole video.
    beds = plan.get("beds")
    if not beds and plan.get("bed"):
        beds = [{"files": [plan["bed"]["file"]], "lines": [1, len(lines)], "volume": plan["bed"].get("volume", 0.12)}]
    bed_cfg = bool(beds)
    if beds:
        xf, blend = 3.0, 2.5   # loop crossfade inside a mood; blend between moods
        dips = "+".join(f"between(t,{line_start(c['lines'][0]) - 0.3:.2f},{line_start(c['lines'][1] + 1):.2f})"
                        for c in plan["music"]) or "0"
        seg_labels = []
        for si, bd in enumerate(beds):
            a0 = 0.0 if si == 0 else line_start(bd["lines"][0]) - blend / 2
            a1 = end_time if si == len(beds) - 1 else line_start(bd["lines"][1] + 1) + blend / 2
            dur = a1 - a0
            files = [str(ROOT / f) for f in bd["files"]]
            lens = [float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                   "-of", "csv=p=0", f])) for f in files]
            seq, total = [], 0.0
            while total < dur + xf:
                k = len(seq) % len(files)
                seq.append(files[k])
                total += lens[k] - xf
            loop = build / f"bed-{si}.wav"
            bin_ = sum((["-i", f] for f in seq), [])
            if len(seq) == 1:
                sh(["ffmpeg", "-loglevel", "error", "-y", *bin_, "-ar", "48000", "-ac", "2", str(loop)])
            else:
                chain, prev = [], "[0:a]"
                for k in range(1, len(seq)):
                    chain.append(f"{prev}[{k}:a]acrossfade=d={xf}[x{k}]")
                    prev = f"[x{k}]"
                sh(["ffmpeg", "-loglevel", "error", "-y", *bin_, "-filter_complex", ";".join(chain), "-map", prev,
                    "-ar", "48000", "-ac", "2", str(loop)])
            # Even out loudness between moods, then place the segment on the timeline.
            ins += ["-i", str(loop)]
            ms = int(a0 * 1000)
            fx.append(f"[{n}:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,loudnorm=I=-20:TP=-3,"
                      f"afade=t=in:d={2 if si == 0 else blend},afade=t=out:st={max(0, dur - (3 if si == len(beds) - 1 else blend)):.3f}:d={3 if si == len(beds) - 1 else blend},"
                      f"volume={bd.get('volume', 0.12)},adelay={ms}|{ms}[bs{si}]")
            seg_labels.append(f"[bs{si}]")
            n += 1
        fx.append("".join(seg_labels) + f"amix=inputs={len(seg_labels)}:normalize=0,"
                  f"atrim=0:{end_time:.3f},volume=0.15:enable='{dips}'[bed0]")
    for line, frac, name, vol in plan["sfx"]:
        a, b = line_start(line), line_start(line + 1)
        ms = int((a + (b - a) * frac) * 1000)
        ins += ["-i", str(ROOT / f"youtube/assets/sfx/{name}.wav")]
        fx.append(f"[{n}:a]aresample=48000,volume={vol * 0.22},adelay={ms}|{ms}[s{n}]")
        labels.append(f"[s{n}]")
        n += 1
    # Music and sfx bus, ducked whenever the voice is talking (sidechain).
    fx.insert(0, "[0:a]asplit=2[vmain][vkey]")
    bed = labels[1:]
    if bed:
        fx.append("".join(bed) + f"amix=inputs={len(bed)}:normalize=0[bed]")
        fx.append("[bed][vkey]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[duck]")
        tail = "[bed0]" if bed_cfg else ""
        fx.append(f"[vmain][duck]{tail}amix=inputs={3 if bed_cfg else 2}:normalize=0,alimiter=limit=0.95[out]")
    else:
        fx.append("[vmain]anull[out]")
    sh(["ffmpeg", "-loglevel", "error", "-y", *ins, "-filter_complex", ";".join(fx), "-map", "[out]",
        "-t", f"{end_time:.3f}", "-ac", "2", "-ar", "48000", str(build / "mix.wav")])

    # 6. Mux.
    final = vdir / ("preview.mp4" if preview else "final.mp4")
    # Easy-on-the-eyes grade: lifted blacks, softened whites, a little less contrast and saturation,
    # slightly warm. Applied once to the whole video.
    grade = plan["defaults"].get("grade", "eq=contrast=0.94:saturation=0.9:gamma=1.03,"
                                 "colorbalance=rm=0.02:bm=-0.02:rh=0.01:bh=-0.015,"
                                 "curves=all='0/0.035 0.5/0.51 1/0.95'")
    sh(["ffmpeg", "-loglevel", "error", "-y", "-i", str(build / "video.mp4"), "-i", str(build / "mix.wav"),
        "-vf", grade, "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)])
    print("wrote", final.relative_to(ROOT))


if __name__ == "__main__":
    main()
