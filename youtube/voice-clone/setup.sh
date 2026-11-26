#!/bin/bash
# Installs the Chatterbox voice-cloning tool into ~/chatterbox (CPU, a few minutes, ~4 GB).
# Needs these hosts allowed in the environment: huggingface.co, *.hf.co (already added).
set -e
V=~/chatterbox/.venv
if ! { [ -x $V/bin/python ] && $V/bin/python -c "import chatterbox" 2>/dev/null; }; then
  mkdir -p ~/chatterbox && cd ~/chatterbox
  uv venv --python 3.11 .venv
  uv pip install --python .venv/bin/python chatterbox-tts "setuptools<81"
fi
echo "installed. Use: $V/bin/python <repo>/youtube/voice-clone/clone.py ref.wav out.wav \"text\""

# Resemble Enhance (studio cleanup: denoise + dereverb), own venv so it can't break chatterbox.
# Weights come from Hugging Face (allowed); GitHub-hosted models like DeepFilterNet are blocked here.
E=~/enhance/.venv
if ! [ -x $E/bin/python ] || ! $E/bin/python -c "import resemble_enhance" 2>/dev/null; then
  mkdir -p ~/enhance && (cd ~/enhance && uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python resemble-enhance)
fi
echo "enhancer: $E/bin/python <repo>/youtube/voice-clone/enhance_lines.py <voice_dir>"

# Kokoro TTS: the channel voice is Kokoro "am_puck" (picked by the creator).
# espeak-ng is its fallback for unknown words; the spaCy English model comes from Hugging Face
# (its usual GitHub download is blocked here). The HF wheel is 3.7.1 despite its filename.
command -v espeak-ng >/dev/null || apt-get install -y -q espeak-ng
K=~/kokoro/.venv
if ! [ -x $K/bin/python ] || ! $K/bin/python -c "import kokoro, en_core_web_sm" 2>/dev/null; then
  mkdir -p ~/kokoro && (cd ~/kokoro && uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python "kokoro>=0.9" soundfile)
  W=/tmp/en_core_web_sm-3.7.1-py3-none-any.whl
  curl -sSfL -o $W https://huggingface.co/spacy/en_core_web_sm/resolve/main/en_core_web_sm-any-py3-none-any.whl
  uv pip install --python $K/bin/python $W
fi
echo "channel voice: $K/bin/python <repo>/youtube/voice-clone/narrate_kokoro.py <narration.txt> <voice_dir>"
