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
