#!/bin/bash
# Installs the Chatterbox voice-cloning tool into ~/chatterbox (CPU, a few minutes, ~4 GB).
# Needs these hosts allowed in the environment: huggingface.co, *.hf.co (already added).
set -e
V=~/chatterbox/.venv
[ -x $V/bin/python ] && $V/bin/python -c "import chatterbox" 2>/dev/null && { echo "chatterbox ready"; exit 0; }
mkdir -p ~/chatterbox && cd ~/chatterbox
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python chatterbox-tts "setuptools<81"
echo "installed. Use: $V/bin/python <repo>/youtube/voice-clone/clone.py ref.wav out.wav \"text\""
