// Shared helpers for scenes. Every scene defines window.renderFrame(t), where t is seconds.

window.BRAND = {
  bg: '#262427',       // charcoal, like the character sheet background
  bgDeep: '#151315',
  ink: '#0c0b0c',
  text: '#f2eae2',     // warm off-white
  muted: '#9a918b',
  accent: '#d2492f',   // the reddish rim light on the character
  cold: '#5aa7ff',     // phone-screen blue
  font: "'Inter Display', 'Inter', sans-serif",  // use weight 900
  body: "'Inter', sans-serif",
};

window.P = Object.assign({}, window.SCENE_PARAMS || {});
window.param = (k, d) => (window.P[k] !== undefined ? window.P[k] : d);

window.clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
window.lerp = (a, b, k) => a + (b - a) * k;
// progress of t through [start, start+dur] as 0..1
window.prog = (t, start, dur) => clamp((t - start) / dur);
window.ease = {
  out: (k) => 1 - Math.pow(1 - k, 3),
  inOut: (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
  back: (k) => { const c = 1.9; return 1 + (c + 1) * Math.pow(k - 1, 3) + c * Math.pow(k - 1, 2); },
};
// deterministic pseudo-random (same every render)
window.rand = (i) => { const x = Math.sin(i * 12.9898 + 78.233) * 43758.5453; return x - Math.floor(x); };
// small deterministic camera shake
window.shake = (t, amt) => [Math.sin(t * 47) * amt * rand(Math.floor(t * 30)), Math.cos(t * 53) * amt * rand(Math.floor(t * 30) + 7)];

// Film grain overlay, drawn on a canvas with id="grain" if present.
window.drawGrain = (t, strength = 0.06) => {
  const c = document.getElementById('grain');
  if (!c) return;
  const ctx = c.getContext('2d');
  const w = (c.width = 480), h = (c.height = 270);
  const img = ctx.createImageData(w, h);
  let seed = Math.floor(t * 24) * 9973;
  for (let i = 0; i < img.data.length; i += 4) {
    seed = (seed * 16807) % 2147483647;
    const v = (seed / 2147483647) * 255;
    img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
    img.data[i + 3] = 255 * strength;
  }
  ctx.putImageData(img, 0, 0);
};

// Wait for every <img> to load before rendering (call from window.sceneReady).
window.imagesReady = () => Promise.all([...document.images].map((im) =>
  im.complete ? null : new Promise((r) => { im.onload = im.onerror = r; })));
