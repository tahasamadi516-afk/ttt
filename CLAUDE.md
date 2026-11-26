# Project notes

## How to talk to me
Keep messages as short as possible while still complete. Casual, plain, talk like me.

## Goal
Make YouTube videos using the YouTube agent skills (yt-* skills: yt-plan, yt-script,
yt-package, yt-seo, yt-edit, yt-shorts, yt-chapters, yt-retention, yt-viral, yt-audit,
yt-comment). No videos have been made yet; the first one is being planned.

## Voice profile
Written: `youtube/voice.md` (copy to `~/.claude/youtube/voice.md` at session start; home is wiped between sessions).

## Tools available every session (installed by the environment setup script)
- graphify: code knowledge graph (run once the repo has real code)
- find-skills: search skills.sh for skills that fit a task
- yt-dlp: reads public YouTube video lists (youtube.com is allowed on the network)

## Documentary skill
`/documentary` (in `.claude/skills/documentary/`, checked into this repo) turns one idea
into a cinematic 3D documentary blueprint: case file, scene table, image prompts,
30-second video prompts, narration script and edit checklist. Prompts only; it never
generates media. Run `/documentary` with no idea to see the process.

## 3D animation skill
`3d-animation` (in `.claude/skills/3d-animation/`) is a step-by-step studio for ~30s
narrated 3D myth-busting shorts. Claude writes the script and all image/video prompts,
the user generates the images and clips, then Claude voices it (edge-tts) and cuts the
final MP4 (ffmpeg). Each video lives in `projects/<slug>/`.
- Needs: ffmpeg (preinstalled), `pip install edge-tts` (not in the setup script yet).
- edge-tts needs network access to `speech.platform.bing.com`, which this environment
  currently blocks. Only the final voice/cut step needs it.

## Motion design skill
`/motion-design` (in `.claude/skills/motion-design/`) turns one image into a paper-cut
stop-motion clip: 3 prompts (paper-cut image, 9-panel sheet, animation). Prompts only.
Style anchor image: `.claude/skills/motion-design/paper-cut-style.jpg`.
