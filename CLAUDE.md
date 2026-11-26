# Project notes

## Goal
Make YouTube videos using the YouTube agent skills (yt-* skills: yt-plan, yt-script,
yt-package, yt-seo, yt-edit, yt-shorts, yt-chapters, yt-retention, yt-viral, yt-audit,
yt-comment). No videos have been made yet; the first one is being planned.

## Voice profile
Lives in this repo at `youtube/voice.md`. At the start of each session, copy it to
`~/.claude/youtube/voice.md` (the home directory is wiped), because the yt-* skills read it there.

## Video style
See the "Video style" section in `youtube/voice.md`: self-mocking and fun, reactions must
match each line, a cappella only (no instrumental music, nothing corny).

## Character
`youtube/character/` holds the character sheet and description. Every video uses him.

## Tools available every session (installed by the environment setup script)
- graphify: code knowledge graph (run once the repo has real code)
- find-skills: search skills.sh for skills that fit a task
- yt-dlp: reads public YouTube video lists (youtube.com is allowed on the network)
