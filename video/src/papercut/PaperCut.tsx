import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {TransitionSeries, springTiming} from '@remotion/transitions';
import {wipe} from '@remotion/transitions/wipe';
import {flip} from '@remotion/transitions/flip';
import {loadFont} from '@remotion/google-fonts/LilitaOne';
import {Grain, Vignette} from './paper';
import {SceneHills} from './SceneHills';
import {SceneOcean} from './SceneOcean';
import {SceneOutro} from './SceneOutro';

const {fontFamily} = loadFont();

// Scene lengths minus the two 20-frame transitions = 330 frames (11s at 30fps).
export const PAPERCUT_DURATION = 150 + 120 + 100 - 20 - 20;

export const PaperCut: React.FC = () => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill>
      <TransitionSeries>
        <TransitionSeries.Sequence name="Hills" durationInFrames={5 * fps}>
          <SceneHills fontFamily={fontFamily} />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={wipe({direction: 'from-top-left'})}
          timing={springTiming({config: {damping: 200}, durationInFrames: 20})}
        />
        <TransitionSeries.Sequence name="Ocean" durationInFrames={4 * fps}>
          <SceneOcean fontFamily={fontFamily} />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={flip({direction: 'from-right'})}
          timing={springTiming({config: {damping: 200}, durationInFrames: 20})}
        />
        <TransitionSeries.Sequence name="Outro" durationInFrames={100}>
          <SceneOutro fontFamily={fontFamily} />
        </TransitionSeries.Sequence>
      </TransitionSeries>
      <Grain />
      <Vignette />
    </AbsoluteFill>
  );
};
