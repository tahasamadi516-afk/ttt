#!/usr/bin/env python3
"""Download finished OpenArt images and turn them into library assets.

Usage:
    python3 tools/fetch_assets.py name=URL [name=URL ...] [--bg]

Each image is saved to youtube/assets/raw/<name>.png. Without --bg it's also
chroma-keyed into youtube/assets/character/<name>.png (a transparent cutout).
With --bg it's copied to youtube/assets/backgrounds/<name>.png as a full scene.
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "youtube" / "assets"


def main() -> None:
    is_bg = "--bg" in sys.argv
    pairs = [a.split("=", 1) for a in sys.argv[1:] if "=" in a]
    if not pairs:
        sys.exit(__doc__)
    for d in ("raw", "character", "backgrounds"):
        (ASSETS / d).mkdir(parents=True, exist_ok=True)
    for name, url in pairs:
        raw = ASSETS / "raw" / f"{name}.png"
        # curl, not urllib: the OpenArt CDN refuses Python's default client.
        subprocess.run(["curl", "-sSfL", "-o", str(raw), url], check=True)
        if is_bg:
            out = ASSETS / "backgrounds" / f"{name}.png"
            out.write_bytes(raw.read_bytes())
            print(f"bg   {out.relative_to(ROOT)}")
        else:
            out = ASSETS / "character" / f"{name}.png"
            subprocess.run([sys.executable, str(ROOT / "tools" / "chroma.py"), str(raw), str(out), "--crop"], check=True)


if __name__ == "__main__":
    main()
