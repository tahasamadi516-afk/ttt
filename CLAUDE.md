# Project notes

## Goal
Make YouTube videos using the YouTube agent skills (yt-* skills: yt-plan, yt-script,
yt-package, yt-seo, yt-edit, yt-shorts, yt-chapters, yt-retention, yt-viral, yt-audit,
yt-comment). No videos have been made yet; the first one is being planned.

## Reminder: voice profile not written yet
Most yt-* skills read `~/.claude/youtube/voice.md` (the creator's voice profile). It
does not exist yet. The user has not made a video, so there are no transcripts to build it from.

When we start actually making a video (before writing the first script, title or
description), remind the user and ask them the questions to fill it in:
- Who the videos are for (one specific viewer)
- How they talk (or a sample of them talking)
- Words they never use / words they do use
- Claims they will not make
- Their format

Save the finished profile in this repo as `youtube/voice.md` (the home directory is
wiped between cloud sessions), then copy it to `~/.claude/youtube/voice.md` and
remove this reminder.

## Tools available every session (installed by the environment setup script)
- graphify: code knowledge graph (run once the repo has real code)
- find-skills: search skills.sh for skills that fit a task
- yt-dlp: reads public YouTube video lists (youtube.com is allowed on the network)

## Documentary skill
`/documentary` (in `.claude/skills/documentary/`, checked into this repo) turns one idea
into a cinematic 3D documentary blueprint: case file, scene table, image prompts,
30-second video prompts, narration script and edit checklist. Prompts only; it never
generates media. Run `/documentary` with no idea to see the process.
