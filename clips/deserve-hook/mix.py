# Mix: Kokoro voice + earshot paper foley, placed on the page's events. Run with the lemo .venv python.
import json, sys, os, numpy as np, soundfile as sf
from scipy.signal import resample_poly
SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
ev = json.load(open(os.path.join(HERE, 'events.json')))
DUR = ev['dur']
buf = np.zeros((int(DUR * SR) + SR, 2))
voice = np.zeros_like(buf)

def load(path, gain=1.0, speed=1.0):
    x, sr = sf.read(path, always_2d=True); x = x.mean(1)
    if sr != SR: x = resample_poly(x, SR, sr)
    if speed != 1.0: x = np.interp(np.arange(0, len(x), speed), np.arange(len(x)), x)   # pitch + length together
    return x * gain

def put(b, x, at, gain=1.0, pan=0.0):
    i = int(max(0, at) * SR); n = min(len(x), len(b) - i)
    if n <= 0: return
    l, r = np.sqrt((1 - pan) / 2) * 1.414, np.sqrt((1 + pan) / 2) * 1.414
    b[i:i + n, 0] += x[:n] * gain * l; b[i:i + n, 1] += x[:n] * gain * r

# voice lines start where the captions start
starts = {'l1': 0.5, 'l2': 2.9, 'l3': 5.2, 'l4': 9.5}
for k, t0 in starts.items():
    x = load(os.path.join(HERE, 'voice', k + '.wav'))
    put(voice, x / np.abs(x).max() * .8, t0)
voice_env = np.abs(voice).max(1)
# duck: smooth envelope of the voice, used to pull foley down under speech
win = int(.12 * SR); k = np.ones(win) / win
duck = 1 - .45 * np.clip(np.convolve(voice_env > .02, k, 'same'), 0, 1)

S = lambda n, **kw: load(os.path.join(HERE, 'sfx', n), **kw)
snd = {'paper': S('paper-slide.wav'), 'snip': S('snip.wav'), 'stamp': S('stamp.wav'), 'whoosh': S('whoosh.wav'),
       'chime': S('chime.wav'), 'rise': S('rise.wav'), 'heart': S('heartbeat.wav'), 'thud2': S('thud2.wav')}
snd_thud = {i: S('thud.wav', speed=.9 + .045 * i) for i in range(6)}
PEAK = {'snip': 1.04, 'stamp': 0.0, 'chime': .20, 'rise': 2.45, 'paper': .11, 'whoosh': .24}
fx = np.zeros_like(buf)
for e in ev['ev']:
    t, ty = e['t'], e['type']
    if ty == 'thud':
        put(fx, snd_thud[e['i']], t, .9, pan=-.3 + e['i'] * .1); put(fx, snd['thud2'], t, .5)
    elif ty == 'rise': put(fx, snd['rise'], 8.72 - PEAK['rise'], .55)
    elif ty == 'heart':
        for rep in range(2 if t < 5 else 1): put(fx, snd['heart'], t + rep * 3.3, .35)
    else:
        g = {'paper': .55, 'snip': .8, 'stamp': 1.0, 'whoosh': .8, 'chime': .6}[ty]
        put(fx, snd[ty], t - PEAK.get(ty, 0) * (0 if ty == 'stamp' else 1) , g)
fx *= duck[:, None]
out = voice * .9 + fx * .75
out = np.tanh(out * 1.1) / np.tanh(1.1)
out = out[:int(DUR * SR)]
fade = int(.5 * SR); out[-fade:] *= np.linspace(1, 0, fade)[:, None]
out *= .89 / max(np.abs(out).max(), 1e-6)
sf.write(os.path.join(HERE, 'out', 'mix.wav'), out, SR)
print('mix', out.shape[0] / SR, 's, peak', np.abs(out).max())
