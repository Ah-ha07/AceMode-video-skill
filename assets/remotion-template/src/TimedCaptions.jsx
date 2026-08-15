import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};
const fontFamily = 'Inter, PingFang SC, Noto Sans, Arial, sans-serif';

export const TimedCaptions = ({manifest, vertical = false}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const nowMs = frame / fps * 1000;
  const cue = (manifest?.cues ?? []).find(
    (item) => nowMs >= item.startMs && nowMs < item.endMs,
  );
  if (!cue) return null;
  const cueFrame = Math.max(0, frame - Math.floor(cue.startMs / 1000 * fps));
  const remaining = Math.ceil(cue.endMs / 1000 * fps) - frame;
  const opacity = Math.min(
    interpolate(cueFrame, [0, 4], [0, 1], clamp),
    interpolate(remaining, [0, 4], [0, 1], clamp),
  );

  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        bottom: vertical ? 190 : 42,
        width: vertical ? 920 : 1320,
        transform: `translate(-50%, ${interpolate(opacity, [0, 1], [12, 0])}px)`,
        opacity,
        zIndex: 100,
        textAlign: 'center',
        pointerEvents: 'none',
      }}
    >
      <span
        style={{
          display: 'inline',
          padding: vertical ? '13px 20px 16px' : '10px 19px 12px',
          color: '#FFFDF7',
          background: 'rgba(10,16,26,.92)',
          boxDecorationBreak: 'clone',
          WebkitBoxDecorationBreak: 'clone',
          fontFamily,
          fontSize: vertical ? 47 : 30,
          fontWeight: 760,
          lineHeight: 1.34,
          letterSpacing: vertical ? -0.5 : 0,
          boxShadow: '0 8px 24px rgba(0,0,0,.2)',
        }}
      >
        {cue.text}
      </span>
    </div>
  );
};
