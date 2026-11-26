# Reusable asset library

Made in OpenArt (Nano Banana 2, image-to-image from `youtube/character/character-sheet.png`)
and saved there in **Personal Project → Character Assets**. Reuse these in every video,
and generate new ones only when a video needs a pose or place that isn't here yet.

## Character cutouts (`character/`, transparent PNG, waist-up unless noted)

| File | Pose | Good for |
|---|---|---|
| `talking.png` | hand on chest, mid-sentence | default narration, explaining |
| `phone.png` | looking down at phone, blue glow | scrolling, texting, "hooked" moments |
| `facepalm.png` | hand over face | "stupid idiot", regret, cringe |
| `shrug.png` | palms up, confused | "who was that guy?", "prove what?" |
| `pointing.png` | points at viewer | calling the viewer out, "put the phone down" |
| `arms-crossed-full.png` | full body, arms crossed | confident, "even 1% I'm not accepting" |
| `shocked.png` | eyes wide, frozen | flashbacks, sudden realization |
| `deadpan.png` | flat, bored stare | "I don't care if you exist", punchline after a fake smile |
| `smirk.png` | raised brow, half smile | "yeah right", sarcasm |
| `hands-on-head.png` | grabbing his hair, groaning | exasperated at himself |
| `puppy-face.png` | teary begging, hands clasped | mocking his own neediness |
| `rant.png` | arms thrown out, shouting | "good enough for what?!" |
| `chin-stroke.png` | smug "hmm, interesting" | fake-genius self-roast |
| `awkward-laugh.png` | cringe grin, rubbing neck | guilty, "that's a little crazy" |
| `thumbs-up.png` | fake smile + thumbs up | "beautiful, amazing" sarcasm |
| `pinch.png` | "just a tiny bit" fingers | "five percent, barely noticeable" |
| `side-eye.png` | suspicious side glance | distracted asides, "or am I?" |
| `laughing.png` | head back, big laugh | genuine fun with the audience |
| `smile.png` | warm sincere smile | heartfelt moments, endings |
| `wave.png` | goofy wave, wink | outros, "bye" |
| `intense.png` | close-up, burning focus | goals, ambition, discipline |
| `cooking.png` | spatula, sleepy morning | everyday-life openings |

## Backgrounds (`backgrounds/`, 16:9)

| File | Scene |
|---|---|
| `bg-kitchen-morning.png` | apartment kitchen, morning light |
| `bg-bedroom-night.png` | dark bedroom at night, blue window light, dumbbells |

## Full scenes with him in them (`backgrounds/`, 16:9)

Use these as-is with the camera push in `character.html` (`"bg"` only, no `poses`).

**Epic-music jokes** (dramatic a cappella plays, played straight):
`epic-throne-phone` (throne, phone like a relic) · `epic-courtyard-sword` (sword training at sunset) ·
`epic-heaven-wakeup` (light beams, revelation) · `epic-cathedral-realization` (lightning, shock) ·
`epic-scriptorium-phone` (reading a phone like a scroll) · `epic-mirror-reflection` (mirror shows a dating app) ·
`epic-dagger-pillow` (politely declining a dagger) · `epic-heaven-reborn` (rising at sunrise)

## How new assets are made

Prompt recipe for a new pose (keep everything except the pose line the same):

> The exact same character from the reference character sheet: lean young man, messy
> dark curly hair over his forehead, sharp jaw, strong brows, olive-tan skin, oversized
> black t-shirt with dropped shoulders, loose black pants. Waist-up shot, **<POSE AND
> EXPRESSION>**. Same art style as the reference: semi-realistic comic/anime line art,
> clean dark outlines, warm dark palette, subtle reddish rim light on the edges.
> Background: one perfectly flat, solid chroma-key green (#00FF00), no shadows, no
> gradient, nothing else. Character fully inside the frame.

Settings: 3:4, 2K, with the character sheet as the reference. Costs about 27 credits per image.
Then run `python3 tools/chroma.py raw.png character/name.png --crop`.

The green-screen originals stay in OpenArt and in `raw/` (raw/ is not committed).
