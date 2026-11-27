import React from 'react';
import {AbsoluteFill} from 'remotion';

// Builds a closed SVG path: a wavy top edge filled down to the bottom.
export const wavePath = (
  width: number,
  height: number,
  baseY: number,
  amp: number,
  freq: number,
  phase: number,
) => {
  const steps = 64;
  let d = `M0,${height} L0,${baseY + Math.sin(phase) * amp}`;
  for (let i = 1; i <= steps; i++) {
    const x = (i / steps) * width;
    const y =
      baseY +
      Math.sin((i / steps) * Math.PI * 2 * freq + phase) * amp +
      Math.sin((i / steps) * Math.PI * 2 * freq * 2.3 + phase * 1.7) * amp * 0.25;
    d += ` L${x.toFixed(1)},${y.toFixed(1)}`;
  }
  return d + ` L${width},${height} Z`;
};

// Paper layers cast a soft shadow on the layer behind them.
export const paperShadow = 'drop-shadow(0px 10px 12px rgba(40, 20, 10, 0.35))';

// Static paper grain laid over everything, so flat colours read as card stock.
export const Grain: React.FC = () => (
  <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'multiply', opacity: 0.35}}>
    <svg width="100%" height="100%">
      <filter id="grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" seed="7" />
        <feColorMatrix
          type="matrix"
          values="0 0 0 0 0.55  0 0 0 0 0.5  0 0 0 0 0.45  0 0 0 -1.4 1.1"
        />
      </filter>
      <rect width="100%" height="100%" filter="url(#grain)" />
    </svg>
  </AbsoluteFill>
);

// Darkens the corners, like light falling on a paper diorama.
export const Vignette: React.FC = () => (
  <AbsoluteFill
    style={{
      pointerEvents: 'none',
      background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(30,15,5,0.45) 100%)',
    }}
  />
);
