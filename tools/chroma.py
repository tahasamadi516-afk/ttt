#!/usr/bin/env python3
"""Cut the character out of a green-screen image and save a transparent PNG.

Usage:
    python3 tools/chroma.py in.png out.png [--crop]

How it works: the key color is sampled from the image corners (the background is
generated as flat green, but it's never exactly #00FF00). A pixel's distance from
that color sets its alpha, with a soft edge band. Green spill on the edges is then
removed by clamping green to max(red, blue). --crop trims the empty transparent
border so the cutout is easy to place in a scene.
"""
import sys

import numpy as np
from PIL import Image, ImageFilter


def key(img: Image.Image, inner: float = 60.0, outer: float = 130.0) -> Image.Image:
    rgb = np.asarray(img.convert("RGB")).astype(np.float32)
    h, w, _ = rgb.shape
    s = max(4, min(h, w) // 40)
    corners = np.concatenate([
        rgb[:s, :s].reshape(-1, 3), rgb[:s, -s:].reshape(-1, 3),
        rgb[-s:, :s].reshape(-1, 3), rgb[-s:, -s:].reshape(-1, 3),
    ])
    bg = np.median(corners, axis=0)

    dist = np.linalg.norm(rgb - bg, axis=2)
    # Also count "green-dominant" pixels as background, to catch shading in the green.
    greenness = rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])
    dist = np.where(greenness > 90, np.minimum(dist, inner), dist)
    alpha = np.clip((dist - inner) / (outer - inner), 0, 1)

    # Despill: no pixel should be greener than its red/blue allow.
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    g = np.minimum(g, np.maximum(r, b) * 1.02)
    out = np.dstack([r, g, b, alpha * 255]).clip(0, 255).astype(np.uint8)

    im = Image.fromarray(out, "RGBA")
    # Shrink the matte by a pixel and soften it, to kill the green halo.
    a = im.getchannel("A").filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    im.putalpha(a)
    return im


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    im = key(Image.open(args[0]))
    if "--crop" in sys.argv:
        bbox = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
        if bbox:
            pad = 12
            im = im.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad),
                          min(im.width, bbox[2] + pad), min(im.height, bbox[3] + pad)))
    im.save(args[1])
    print(f"wrote {args[1]} {im.size}")


if __name__ == "__main__":
    main()
