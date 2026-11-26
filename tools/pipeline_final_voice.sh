#!/bin/bash
# Video 01 final voice: wait for the directed voice, convert every line to the chosen voice
# (ref-voice-final.wav; lines 3 and 22 kept as-is), swap it in, rebuild the video. Nothing is deleted.
cd /home/user/ttt
D=youtube/videos/01-who-was-that-guy
LOG=/tmp/claude-0/-home-user-ttt/fb6c52f0-53aa-5a50-b049-b34d024084f0/scratchpad
while pgrep -f direct_voice.py >/dev/null; do sleep 30; done
if [ ! -f "$D/voice-directed/lines.json" ]; then echo "directed voice did not finish" > "$LOG/pipeline-final.done"; exit 1; fi
~/chatterbox/.venv/bin/python youtube/voice-clone/convert_voice.py "$D/voice-directed" "$D/voice-final" --keep 3,22 > "$LOG/convert.log" 2>&1 || { echo "convert failed" > "$LOG/pipeline-final.done"; exit 1; }
if [ -d "$D/voice" ] && [ ! -d "$D/voice-e-plain" ]; then mv "$D/voice" "$D/voice-e-plain"; elif [ -d "$D/voice" ]; then mv "$D/voice" "$D/voice-old-$(date +%s)"; fi
cp -r "$D/voice-final" "$D/voice"
python3 tools/build_video.py "$D" --jobs 3 > "$LOG/build-final.log" 2>&1 && echo finished > "$LOG/pipeline-final.done" || echo "build failed" > "$LOG/pipeline-final.done"
