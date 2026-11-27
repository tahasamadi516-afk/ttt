import {Composition} from 'remotion';
import {Hello} from './Hello';
import {PaperCut, PAPERCUT_DURATION} from './papercut/PaperCut';

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="PaperCut"
      component={PaperCut}
      durationInFrames={PAPERCUT_DURATION}
      fps={30}
      width={1920}
      height={1080}
    />
    <Composition
      id="Hello"
      component={Hello}
      durationInFrames={90}
      fps={30}
      width={1920}
      height={1080}
    />
  </>
);
