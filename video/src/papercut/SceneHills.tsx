import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {paperShadow, wavePath} from './paper';

const HILLS = [
  {color: '#f6c28b', baseY: 520, amp: 40, freq: 1.2, phase: 0.4},
  {color: '#e8956b', baseY: 610, amp: 55, freq: 1.6, phase: 2.1},
  {color: '#d0684f', baseY: 700, amp: 45, freq: 2.1, phase: 4.0},
  {color: '#9c4a4a', baseY: 790, amp: 50, freq: 1.4, phase: 1.2},
  {color: '#5e3348', baseY: 890, amp: 35, freq: 2.6, phase: 3.3},
];

const Hill: React.FC<{index: number}> = ({index}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const h = HILLS[index];
  const enter = spring({frame: frame - index * 5, fps, config: {damping: 14, mass: 0.8}});
  // Front layers drift faster than back layers: parallax.
  const drift = frame * (0.4 + index * 0.35);
  return (
    <AbsoluteFill
      style={{
        filter: paperShadow,
        translate: `${-drift}px ${interpolate(enter, [0, 1], [700, 0])}px`,
      }}
    >
      <svg width={width + 400} height={height}>
        <path d={wavePath(width + 400, height, h.baseY, h.amp, h.freq, h.phase)} fill={h.color} />
      </svg>
    </AbsoluteFill>
  );
};

const Sun: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame: frame - 18, fps, config: {damping: 9}});
  return (
    <div
      style={{
        position: 'absolute',
        left: 1340,
        top: 150,
        width: 260,
        height: 260,
        borderRadius: '50%',
        background: '#fff3c4',
        boxShadow: '0 0 0 28px rgba(255,243,196,0.35), 0 0 0 60px rgba(255,243,196,0.15)',
        filter: paperShadow,
        scale: String(pop),
        rotate: `${interpolate(frame, [0, 150], [0, 40])}deg`,
      }}
    />
  );
};

const Cloud: React.FC<{y: number; speed: number; delay: number; size: number}> = ({
  y,
  speed,
  delay,
  size,
}) => {
  const frame = useCurrentFrame();
  const x = -300 + (frame - delay) * speed;
  return (
    <div style={{position: 'absolute', top: y, left: x, filter: paperShadow, scale: String(size)}}>
      <svg width="300" height="120" viewBox="0 0 300 120">
        <path
          d="M30,100 Q0,100 10,75 Q20,50 55,60 Q60,20 105,25 Q140,0 175,30 Q215,15 235,50 Q290,50 285,85 Q285,100 255,100 Z"
          fill="#fffaf0"
        />
      </svg>
    </div>
  );
};

const Letter: React.FC<{char: string; index: number; fontFamily: string}> = ({
  char,
  index,
  fontFamily,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const drop = spring({frame: frame - 25 - index * 3, fps, config: {damping: 10, stiffness: 120}});
  const wobble = Math.sin((frame + index * 9) / 9) * 3;
  return (
    <span
      style={{
        display: 'inline-block',
        fontFamily,
        fontSize: 190,
        color: '#fffaf0',
        // Stacked hard shadows read as layers of cut card.
        textShadow: '0 6px 0 #e8956b, 0 12px 0 #9c4a4a, 0 22px 18px rgba(40,20,10,0.4)',
        translate: `0px ${interpolate(drop, [0, 1], [-700, 0])}px`,
        rotate: `${interpolate(drop, [0, 1], [index % 2 ? 25 : -25, 0]) + wobble}deg`,
        margin: char === ' ' ? '0 30px' : '0 4px',
      }}
    >
      {char}
    </span>
  );
};

export const SceneHills: React.FC<{fontFamily: string}> = ({fontFamily}) => (
  <AbsoluteFill style={{background: 'linear-gradient(#8fd3e8, #fde2c4)'}}>
    <Sun />
    <Cloud y={120} speed={3.2} delay={0} size={1} />
    <Cloud y={260} speed={2.2} delay={-180} size={0.7} />
    <Cloud y={60} speed={1.6} delay={-500} size={0.55} />
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', paddingBottom: 260}}>
      <div>
        {'PAPER CUT'.split('').map((c, i) => (
          <Letter key={i} char={c} index={i} fontFamily={fontFamily} />
        ))}
      </div>
    </AbsoluteFill>
    {HILLS.map((_, i) => (
      <Hill key={i} index={i} />
    ))}
  </AbsoluteFill>
);
