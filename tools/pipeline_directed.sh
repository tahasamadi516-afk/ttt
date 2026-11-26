#!/bin/bash
# Video 01: directed voice (3 takes per line), swap it in as the voiceover, rebuild the video.
# Nothing is deleted: the previous voiceover folder is renamed to voice-e-plain.
set -e
cd /home/user/ttt
D=youtube/videos/01-who-was-that-guy
LOG=/tmp/claude-0/-home-user-ttt/fb6c52f0-53aa-5a50-b049-b34d024084f0/scratchpad
~/qwentts/.venv/bin/python youtube/voice-clone/direct_voice.py "$D/narration.txt" "$D/directions.json" "$D/voice-directed" --takes 3 > "$LOG/direct.log" 2>&1
if [ -d "$D/voice" ] && [ ! -d "$D/voice-e-plain" ]; then mv "$D/voice" "$D/voice-e-plain"; fi
cp -r "$D/voice-directed" "$D/voice"
python3 tools/build_video.py "$D" --jobs 3 > "$LOG/build-dir.log" 2>&1
echo finished > "$LOG/pipeline-dir.done"
