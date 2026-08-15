import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {TimedCaptions} from './TimedCaptions';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};
const fontFamily = 'Inter, PingFang SC, Noto Sans, Arial, sans-serif';

const VerticalMedia = ({scene, progress}) => {
  const frame = useCurrentFrame();
  return (
    <div style={{position: 'absolute', left: 58, top: 570, width: 964, height: 800, overflow: 'hidden', background: '#D9D5CB', border: '9px solid #FFFDF7', boxShadow: '0 26px 60px rgba(13,26,43,.2)', transform: `translateY(${interpolate(progress, [0, 1], [60, 0])}px)`, opacity: progress}}>
      {scene.primaryType === 'video' ? (
        <OffthreadVideo muted src={staticFile(scene.primary)} startFrom={scene.primaryStartFrom ?? 0} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${interpolate(frame, [0, 180], [1, 1.07], clamp)})`}} />
      ) : (
        <Img src={staticFile(scene.primary)} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${interpolate(frame, [0, 180], [1, 1.07], clamp)})`}} />
      )}
      <div style={{position: 'absolute', left: 20, bottom: 20, padding: '10px 14px', color: '#fff', background: 'rgba(13,26,43,.88)', fontFamily, fontSize: 23, fontWeight: 800, letterSpacing: 1}}>{scene.primaryLabel ?? scene.meta}</div>
    </div>
  );
};

const VerticalScene = ({scene, palette, brand}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: {damping: 22, stiffness: 130}, durationInFrames: 26});
  const settle = interpolate(enter, [0, 1], [.76, 1], clamp);
  const accent = palette[scene.accent];
  return (
    <AbsoluteFill style={{background: palette.paper, overflow: 'hidden'}}>
      <div style={{position: 'absolute', inset: 28, border: '2px solid rgba(13,26,43,.08)'}} />
      <div style={{position: 'absolute', right: -240, top: -200, width: 680, height: 680, borderRadius: '50%', border: `95px solid ${accent}16`}} />
      <div style={{position: 'absolute', left: 58, top: 76, padding: '12px 18px', color: '#fff', background: accent, fontFamily, fontSize: 24, fontWeight: 850, letterSpacing: 1.4, transform: `translateY(${interpolate(settle, [.76, 1], [12, 0])}px)`, opacity: settle}}>{scene.kicker}</div>
      <div style={{position: 'absolute', left: 58, top: 158, width: 930, color: palette.ink, fontFamily, fontSize: 76, fontWeight: 950, lineHeight: 1.05, letterSpacing: -3.4, transform: `translateY(${interpolate(settle, [.76, 1], [18, 0])}px)`, opacity: settle}}>{scene.headline}</div>
      <div style={{position: 'absolute', left: 58, top: 440, color: accent, fontFamily, fontSize: 110, lineHeight: .9, fontWeight: 950, letterSpacing: -5}}>{scene.stat}<div style={{marginTop: 12, color: palette.ink, fontSize: 21, letterSpacing: 1.8}}>{scene.statLabel}</div></div>
      <VerticalMedia scene={scene} progress={settle} />
      <div style={{position: 'absolute', left: 58, right: 58, top: 1404, display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: `${palette.ink}99`, fontFamily, fontSize: 21, fontWeight: 750, letterSpacing: 1.2}}><span>{scene.meta}</span><span>{brand?.enabled ? brand.wordmark : 'EDITORIAL MOTION STUDY'}</span></div>
      {scene.brandRole === 'close' && brand?.enabled ? <div style={{position: 'absolute', left: 58, right: 58, bottom: 360, padding: '28px', color: brand.colors?.cloud ?? '#F0F6FA', background: brand.colors?.navy ?? '#162D51', fontFamily, fontSize: 52, fontWeight: 900, textAlign: 'center'}}>{brand.promise}</div> : null}
    </AbsoluteFill>
  );
};

export const VerticalNewsroom = ({story, captions}) => (
  <AbsoluteFill style={{background: story.palette.paper}}>
    {story.scenes.map((scene, index) => (
      <Sequence key={scene.id} from={scene.from} durationInFrames={scene.duration} premountFor={30} style={{zIndex: index + 1}}>
        <VerticalScene scene={scene} palette={story.palette} brand={story.brand} />
      </Sequence>
    ))}
    <TimedCaptions manifest={captions} vertical />
    {story.audio ? <Audio src={staticFile(story.audio)} /> : null}
  </AbsoluteFill>
);
