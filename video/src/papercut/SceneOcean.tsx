import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {paperShadow, wavePath} from './paper';

const WAVES = ['#2f6f8f', '#2a5d7c', '#244c68', '#1d3b54', '#152a3d'];

const Wave: React.FC<{index: number}> = ({index}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const rise = spring({frame: frame - index * 4, fps, config: {damping: 16}});
  const phase = frame / (12 - index) + index * 1.3;
  return (
    <AbsoluteFill
      style={{filter: paperShadow, translate: `0px ${interpolate(rise, [0, 1], [500, 0])}px`}}
    >
      <svg width={width} height={height}>
        <path d={wavePath(width, height, 600 + index * 85, 22, 2 + index * 0.4, phase)} fill={WAVES[index]} />
      </svg>
    </AbsoluteFill>
  );
};

const Boat: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sail = spring({frame: frame - 20, fps, config: {damping: 8}});
  const bob = Math.sin(frame / 8) * 14;
  const rock = Math.sin(frame / 10) * 7;
  return (
    <div
      style={{
        position: 'absolute',
        left: interpolate(frame, [0, 120], [520, 820]),
        top: 470 + bob,
        filter: paperShadow,
        rotate: `${rock}deg`,
      }}
    >
      <svg width="320" height="260" viewBox="0 0 320 260">
        <g style={{transformOrigin: '160px 190px', transform: `scaleY(${sail})`}}>
          <path d="M165,20 L165,180 L280,180 Z" fill="#fffaf0" />
          <path d="M155,50 L155,180 L60,180 Z" fill="#f6c28b" />
        </g>
        <path d="M20,190 L300,190 L250,250 L70,250 Z" fill="#d0684f" />
      </svg>
    </div>
  );
};

const Caption: React.FC<{fontFamily: string}> = ({fontFamily}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const unfold = spring({frame: frame - 30, fps, config: {damping: 12}});
  return (
    <AbsoluteFill style={{alignItems: 'center', paddingTop: 130}}>
      <div
        style={{
          fontFamily,
          fontSize: 96,
          color: '#152a3d',
          background: '#fffaf0',
          padding: '18px 60px',
          borderRadius: 14,
          filter: paperShadow,
          // Unfolds like a paper banner flipping down.
          transformOrigin: 'top center',
          rotate: `x ${interpolate(unfold, [0, 1], [-90, 0])}deg`,
        }}
      >
        every frame is code
      </div>
    </AbsoluteFill>
  );
};

export const SceneOcean: React.FC<{fontFamily: string}> = ({fontFamily}) => (
  <AbsoluteFill style={{background: 'linear-gradient(#f9b98a, #f6d6b0 60%)', perspective: 1200}}>
    <Wave index={0} />
    <Boat />
    {WAVES.slice(1).map((_, i) => (
      <Wave key={i} index={i + 1} />
    ))}
    <Caption fontFamily={fontFamily} />
  </AbsoluteFill>
);
