# Video toolkit

Code-made visuals for the channel. Everything renders here in the container
(Chromium + ffmpeg), so it costs no OpenArt credits.

## Pieces

| File | What it does |
|---|---|
| `render.mjs` | Renders any scene in `scenes/` to an MP4, frame by frame (exact timing). `--alpha` gives a transparent .mov for layering. |
| `chroma.py` | Cuts the character out of an OpenArt green-screen image into a transparent PNG. |
| `scenes/lib.js` | Brand colors, easing, film grain, and shake helpers used by every scene. |
| `scenes/title.html` | Kinetic text: words slam in one by one, with accent-colored words. |
| `scenes/messages.html` | A phone filling up with incoming messages, plus a count-up ("20 MESSAGES"). |
| `scenes/character.html` | The character on a background: breathing, slow push-in, pose swaps on cue, captions. |

## Examples

```bash
# kinetic title
node tools/render.mjs tools/scenes/title.html out/title.mp4 --duration 3 \
  --params '{"lines":["WHO WAS","THAT GUY?"],"accent":["GUY?"]}'

# message pile-up
node tools/render.mjs tools/scenes/messages.html out/msgs.mp4 --duration 6

# character in the kitchen, swapping to a shrug at 3s
node tools/render.mjs tools/scenes/character.html out/kitchen.mp4 --duration 6 --params '{
  "bg": "../../youtube/assets/backgrounds/bg-kitchen-morning.png", "x": 0.32,
  "poses": [{"src": "../../youtube/assets/character/talking.png", "at": 0},
            {"src": "../../youtube/assets/character/shrug.png", "at": 3}],
  "captions": [{"text": "bro. Who was that guy?", "at": 3.1, "dur": 2.9}]}'

# new OpenArt pose -> cutout
python3 tools/chroma.py youtube/assets/raw/new.png youtube/assets/character/new.png --crop
```

Rendering takes about 5 seconds of compute per second of 1080p video.

## Adding a new scene

Make an HTML file in `scenes/` that loads `lib.js`, reads its options with
`param(name, default)`, and defines `window.renderFrame(t)` to draw the frame at
`t` seconds. If the scene loads images, define `window.sceneReady = () => imagesReady()`.
Never use CSS animations or timers, because only `renderFrame(t)` controls time.

Fonts: Inter / Inter Display (weight 900 for titles) are installed here. Font
downloads from GitHub are blocked on this network.
