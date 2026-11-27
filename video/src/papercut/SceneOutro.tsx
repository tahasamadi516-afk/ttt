import React from 'react';
import {AbsoluteFill, interpolate, random, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {paperShadow} from './paper';

const COLORS = ['#f6c28b', '#e8956b', '#d0684f', '#8fd3e8', '#fffaf0', '#5e3348'];

// random() is seeded, so every render of every frame lands the same confetti.
const Confetti: React.FC<{i: number}> = ({i}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const x = random(`x${i}`) * width;
  const speed = 4 + random(`s${i}`) * 6;
  const start = -100 - random(`y${i}`) * 900;
  const y = start + frame * speed;
  const spin = frame * (2 + random(`r${i}`) * 8);
  const flip = Math.cos((frame + i * 7) / 6);
  return (
    <div
      style={{
        position: 'absolute',
        left: x + Math.sin((frame + i * 13) / 15) * 40,
        top: y % (height + 200),
        width: 26,
        height: 40,
        background: COLORS[i % COLORS.length],
        borderRadius: 3,
        filter: paperShadow,
        rotate: `${spin}deg`,
        scale: `${flip} 1`,
      }}
    />
  );
};

const Rings: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
      {[0, 1, 2, 3, 4].map((i) => {
        const s = spring({frame: frame - i * 4, fps, config: {damping: 12}});
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              width: 1500 - i * 250,
              height: 1500 - i * 250,
              borderRadius: '50%',
              background: COLORS[(i + 2) % COLORS.length],
              filter: paperShadow,
              scale: String(s),
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

const Title: React.FC<{fontFamily: string}> = ({fontFamily}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame: frame - 22, fps, config: {damping: 8, stiffness: 140}});
  const sub = spring({frame: frame - 36, fps, config: {damping: 14}});
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', fontFamily}}>
      <div
        style={{
          fontSize: 210,
          color: '#fffaf0',
          textShadow: '0 7px 0 #d0684f, 0 14px 0 #5e3348, 0 26px 20px rgba(40,20,10,0.45)',
          scale: String(pop),
          rotate: `${interpolate(pop, [0, 1], [-12, -3])}deg`,
        }}
      >
        Remotion
      </div>
      <div
        style={{
          fontSize: 58,
          color: '#5e3348',
          marginTop: 20,
          opacity: sub,
          translate: `0px ${interpolate(sub, [0, 1], [40, 0])}px`,
        }}
      >
        React → MP4
      </div>
    </AbsoluteFill>
  );
};

export const SceneOutro: React.FC<{fontFamily: string}> = ({fontFamily}) => (
  <AbsoluteFill style={{background: '#fde2c4', overflow: 'hidden'}}>
    <Rings />
    {Array.from({length: 60}).map((_, i) => (
      <Confetti key={i} i={i} />
    ))}
    <Title fontFamily={fontFamily} />
  </AbsoluteFill>
);
