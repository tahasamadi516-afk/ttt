#!/bin/bash
# Video 01 final: directed voice -> check every line (Whisper) and re-record mistakes ->
# convert to the chosen voice -> check again (fall back to the directed take if conversion garbles
# a line) -> swap in -> build. Nothing is deleted.
cd /home/user/ttt
D=youtube/videos/01-who-was-that-guy
LOG=/tmp/claude-0/-home-user-ttt/fb6c52f0-53aa-5a50-b049-b34d024084f0/scratchpad
QW=~/qwentts/.venv/bin/python; AS=~/asr/.venv/bin/python; CB=~/chatterbox/.venv/bin/python
done_() { echo "$1" > "$LOG/pipeline-final.done"; exit 0; }
while pgrep -f direct_voice.py >/dev/null; do sleep 30; done
[ -f "$D/voice-directed/lines.json" ] || $QW youtube/voice-clone/direct_voice.py "$D/narration.txt" "$D/directions.json" "$D/voice-directed" --takes 3 >> "$LOG/direct.log" 2>&1
[ -f "$D/voice-directed/lines.json" ] || done_ "directed voice did not finish"
for round in 1 2; do
  F=$($AS tools/check_voice.py "$D/narration.txt" "$D/voice-directed" --report "$LOG/qc-directed-$round.json" 2>/dev/null | tee "$LOG/qc-directed-$round.log" | grep '^FLAGGED:' | cut -d' ' -f2)
  [ "$F" = "none" ] || [ -z "$F" ] && break
  $QW youtube/voice-clone/direct_voice.py "$D/narration.txt" "$D/directions.json" "$D/voice-directed" --takes 3 --only "$F" >> "$LOG/direct.log" 2>&1
done
$QW youtube/voice-clone/direct_voice.py "$D/narration.txt" "$D/directions.json" "$D/voice-directed" --only 999 >> "$LOG/direct.log" 2>&1   # refresh lines.json durations
$CB youtube/voice-clone/convert_voice.py "$D/voice-directed" "$D/voice-final" --keep 3,22 > "$LOG/convert.log" 2>&1 || done_ "convert failed"
F=$($AS tools/check_voice.py "$D/narration.txt" "$D/voice-final" --report "$LOG/qc-final.json" 2>/dev/null | tee "$LOG/qc-final.log" | grep '^FLAGGED:' | cut -d' ' -f2)
if [ -n "$F" ] && [ "$F" != "none" ]; then
  for n in ${F//,/ }; do cp "$D/voice-directed/$(printf 'line_%03d.wav' $n)" "$D/voice-final/"; done
  $CB youtube/voice-clone/convert_voice.py "$D/voice-directed" "$D/voice-final" --keep 3,22 >> "$LOG/convert.log" 2>&1
fi
if [ -d "$D/voice" ] && [ ! -d "$D/voice-e-plain" ]; then mv "$D/voice" "$D/voice-e-plain"; elif [ -d "$D/voice" ]; then mv "$D/voice" "$D/voice-old-$(date +%s)"; fi
cp -r "$D/voice-final" "$D/voice"
python3 tools/build_video.py "$D" --jobs 3 > "$LOG/build-final.log" 2>&1 && done_ finished || done_ "build failed"
