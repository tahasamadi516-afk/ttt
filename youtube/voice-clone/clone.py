import sys, torch, torchaudio as ta
_l = torch.load
torch.load = lambda *a, **k: _l(*a, **{**k, 'map_location': torch.device('cpu')})   # CPU-only machine
from chatterbox.tts import ChatterboxTTS
ref, out, text = sys.argv[1], sys.argv[2], sys.argv[3]
m = ChatterboxTTS.from_pretrained(device='cpu')
w = m.generate(text, audio_prompt_path=ref, exaggeration=0.5, cfg_weight=0.5)
ta.save(out, w, m.sr); print('saved', out, w.shape[-1] / m.sr, 's')
