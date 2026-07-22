import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  Easing,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

const clamp = {
  extrapolateLeft: 'clamp',
  extrapolateRight: 'clamp',
};

const fontFamily = 'PingFang SC, Hiragino Sans GB, Noto Sans CJK SC, Arial, sans-serif';

const PaperBackground = ({palette}) => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: palette.paper,
        backgroundImage:
          'radial-gradient(circle at 10% 10%, rgba(255,255,255,.75), transparent 30%), radial-gradient(circle at 86% 86%, rgba(233,68,67,.08), transparent 24%), repeating-linear-gradient(0deg, rgba(20,20,20,.018) 0, rgba(20,20,20,.018) 1px, transparent 1px, transparent 5px)',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 28,
          border: '1px solid rgba(20,20,20,.08)',
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 590,
          height: 590,
          borderRadius: '50%',
          border: `70px solid ${palette.red}18`,
          right: -330,
          bottom: -380,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 58,
          bottom: 38,
          fontFamily,
          fontSize: 14,
          letterSpacing: 3,
          color: `${palette.ink}60`,
        }}
      >
        EDITORIAL MOTION STUDY · 01
      </div>
    </AbsoluteFill>
  );
};

const AccentLabel = ({children, color, progress}) => {
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        minHeight: 34,
        padding: '0 12px',
        color: '#fff',
        background: color,
        fontFamily,
        fontSize: 15,
        fontWeight: 800,
        letterSpacing: 1.2,
        transform: `translateY(${interpolate(progress, [0, 1], [16, 0])}px)`,
        opacity: progress,
      }}
    >
      {children}
    </div>
  );
};

const MediaCard = ({
  src,
  mediaType = 'image',
  progress,
  x,
  y,
  width,
  height,
  rotate = 0,
  zoom = 1.05,
  zIndex = 2,
  startFrom = 0,
  label,
  coverMode = false,
}) => {
  const frame = useCurrentFrame();
  const imageScale = interpolate(frame, [0, 150], [1, zoom], clamp);
  const enterX = interpolate(progress, [0, 1], [80, 0]);
  const enterY = interpolate(progress, [0, 1], [24, 0]);
  const coverImpact = coverMode
    ? interpolate(frame, [0, 5, 18, 42], [1, 1, 1.025, 1], clamp)
    : 1;

  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width,
        height,
        zIndex,
        overflow: 'hidden',
        background: '#ddd7ca',
        border: '10px solid rgba(255,253,247,.96)',
        boxShadow: '0 18px 45px rgba(52,42,27,.18), 0 2px 0 rgba(20,20,20,.1)',
        transform: `translate(${enterX}px, ${enterY}px) rotate(${rotate}deg) scale(${interpolate(progress, [0, 1], [.94, 1]) * coverImpact})`,
        opacity: progress,
      }}
    >
      {mediaType === 'video' ? (
        <OffthreadVideo
          muted
          src={staticFile(src)}
          startFrom={startFrom}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: `scale(${imageScale})`,
          }}
        />
      ) : (
        <Img
          src={staticFile(src)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: `scale(${imageScale})`,
          }}
        />
      )}
      {label ? (
        <div
          style={{
            position: 'absolute',
            left: 14,
            bottom: 14,
            zIndex: 4,
            padding: '6px 9px',
            color: '#fff',
            background: 'rgba(16,16,16,.82)',
            fontFamily,
            fontSize: 13,
            fontWeight: 800,
            letterSpacing: 1.2,
          }}
        >
          {label}
        </div>
      ) : null}
    </div>
  );
};

const PersonCutout = ({
  src,
  side = 'right',
  progress,
  outline = false,
  outlineColor = '#2C9DA5',
  coverMode = false,
}) => {
  if (!src) return null;
  const frame = useCurrentFrame();
  const x = side === 'left' ? 95 : 1120;
  const direction = side === 'left' ? -90 : 90;
  const resolvedProgress = coverMode ? 1 : progress;
  const outlineWidth = 7;
  const outlineOpacity = coverMode
    ? interpolate(frame, [0, 4, 16, 34, 70], [.55, 1, .82, .42, .28], clamp)
    : interpolate(progress, [0, .35, 1], [0, .9, .3], clamp);
  const baseTransform = `translate(${interpolate(resolvedProgress, [0, 1], [direction, 0])}px, ${interpolate(resolvedProgress, [0, 1], [64, Math.sin(frame / 24) * 3])}px) scale(${interpolate(resolvedProgress, [0, 1], [.94, 1])})`;
  const outlineFilter = [
    `drop-shadow(${outlineWidth}px 0 0 ${outlineColor})`,
    `drop-shadow(-${outlineWidth}px 0 0 ${outlineColor})`,
    `drop-shadow(0 ${outlineWidth}px 0 ${outlineColor})`,
    `drop-shadow(0 -${outlineWidth}px 0 ${outlineColor})`,
  ].join(' ');

  return (
    <>
      {outline ? (
        <Img
          src={staticFile(src)}
          style={{
            position: 'absolute',
            left: x,
            top: 105,
            height: 900,
            zIndex: 13,
            transformOrigin: '50% 100%',
            transform: `${baseTransform} scale(${1 + outlineOpacity * .012})`,
            opacity: outlineOpacity,
            filter: outlineFilter,
          }}
        />
      ) : null}
      <Img
        src={staticFile(src)}
        style={{
          position: 'absolute',
          left: x,
          top: 105,
          height: 900,
          zIndex: 14,
          transformOrigin: '50% 100%',
          transform: baseTransform,
          opacity: resolvedProgress,
          filter: 'drop-shadow(0 24px 25px rgba(25,24,20,.2))',
        }}
      />
    </>
  );
};

const OpeningImpact = ({enabled, accent}) => {
  const frame = useCurrentFrame();
  if (!enabled) return null;
  const sweep = interpolate(frame, [2, 18], [0, 1], clamp);
  const settle = interpolate(frame, [30, 62], [1, 0], clamp);
  const opacity = sweep * settle;

  return (
    <>
      <div
        style={{
          position: 'absolute',
          left: 54,
          top: 118,
          width: 820,
          height: 8,
          zIndex: 16,
          background: accent,
          transformOrigin: '0 50%',
          transform: `scaleX(${sweep})`,
          opacity,
        }}
      />
      <div
        style={{
          position: 'absolute',
          right: 72,
          bottom: 128,
          width: 470,
          height: 3,
          zIndex: 16,
          background: accent,
          transformOrigin: '100% 50%',
          transform: `scaleX(${interpolate(frame, [8, 26], [0, 1], clamp)})`,
          opacity: settle,
        }}
      />
    </>
  );
};

const Caption = ({text, palette, progress}) => {
  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        bottom: 36,
        transform: `translate(-50%, ${interpolate(progress, [0, 1], [18, 0])}px)`,
        opacity: progress,
        zIndex: 20,
        padding: '11px 22px 12px',
        color: palette.white,
        background: 'rgba(16,16,16,.9)',
        fontFamily,
        fontSize: 28,
        fontWeight: 650,
        letterSpacing: .5,
        lineHeight: 1.25,
        whiteSpace: 'nowrap',
        boxShadow: '0 6px 16px rgba(0,0,0,.12)',
      }}
    >
      {text}
    </div>
  );
};

const Scene = ({scene, palette}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const accent = palette[scene.accent];
  const coverMode = scene.coverFrame === true;

  const sceneOpacity = coverMode
    ? interpolate(frame, [scene.duration - 18, scene.duration], [1, 0], clamp)
    : interpolate(
        frame,
        [0, 14, scene.duration - 18, scene.duration],
        [0, 1, 1, 0],
        clamp,
      );
  const primaryIn = spring({
    frame: frame - 2,
    fps,
    config: {damping: 22, stiffness: 120, mass: .9},
    durationInFrames: 28,
  });
  const textIn = spring({
    frame: frame - 10,
    fps,
    config: {damping: 200},
    durationInFrames: 24,
  });
  const statIn = spring({
    frame: frame - 22,
    fps,
    config: {damping: 18, stiffness: 160, mass: .8},
    durationInFrames: 25,
  });
  const captionIn = spring({
    frame: frame - 34,
    fps,
    config: {damping: 200},
    durationInFrames: 18,
  });
  const captionOut = interpolate(
    frame,
    [scene.duration - 30, scene.duration - 14],
    [1, 0],
    clamp,
  );
  const primaryProgress = coverMode ? 1 : primaryIn;
  const textProgress = coverMode ? 1 : textIn;
  const statProgress = coverMode ? 1 : statIn;

  const layouts = {
    'stat-left': {
      textX: 72, textY: 54, textW: 520,
      primaryX: 500, primaryY: 115, primaryW: 1335, primaryH: 785, primaryR: -0.4,
      statX: 88, statY: 310,
      secondaryX: 88, secondaryY: 575, secondaryW: 330, secondaryH: 205, secondaryR: -2,
      lineX: 470, lineY: 870,
    },
    'stat-right': {
      textX: 1190, textY: 54, textW: 650,
      primaryX: 72, primaryY: 182, primaryW: 1080, primaryH: 730, primaryR: -0.8,
      statX: 1400, statY: 720,
      secondaryX: 1510, secondaryY: 835, secondaryW: 330, secondaryH: 205, secondaryR: 1.8,
      lineX: 1840, lineY: 180,
    },
    poster: {
      textX: 72, textY: 54, textW: 700,
      primaryX: 610, primaryY: 165, primaryW: 1160, primaryH: 700, primaryR: 0.4,
      statX: 88, statY: 310,
      secondaryX: 85, secondaryY: 745, secondaryW: 430, secondaryH: 210, secondaryR: -2,
      lineX: 470, lineY: 870,
    },
    'full-bleed': {
      textX: 94, textY: 78, textW: 600,
      primaryX: 64, primaryY: 64, primaryW: 1792, primaryH: 900, primaryR: 0,
      statX: 1570, statY: 120,
      secondaryX: 1420, secondaryY: 715, secondaryW: 360, secondaryH: 210, secondaryR: 1.4,
      lineX: 1812, lineY: 160,
    },
    portrait: {
      textX: 72, textY: 72, textW: 510,
      primaryX: 590, primaryY: 80, primaryW: 850, primaryH: 875, primaryR: -0.5,
      statX: 1490, statY: 190,
      secondaryX: 1480, secondaryY: 655, secondaryW: 350, secondaryH: 230, secondaryR: 1.6,
      lineX: 1450, lineY: 120,
    },
    split: {
      textX: 72, textY: 54, textW: 670,
      primaryX: 70, primaryY: 190, primaryW: 1060, primaryH: 710, primaryR: -0.5,
      statX: 1390, statY: 760,
      secondaryX: 1165, secondaryY: 250, secondaryW: 670, secondaryH: 470, secondaryR: 0.8,
      lineX: 1825, lineY: 780,
    },
    'cutout-portrait': {
      textX: 72, textY: 72, textW: 720,
      primaryX: 760, primaryY: 130, primaryW: 1060, primaryH: 720, primaryR: .6,
      statX: 88, statY: 390,
      secondaryX: 85, secondaryY: 720, secondaryW: 420, secondaryH: 220, secondaryR: -1.6,
      lineX: 535, lineY: 820,
    },
    'document-network': {
      textX: 72, textY: 54, textW: 700,
      primaryX: 760, primaryY: 155, primaryW: 1060, primaryH: 730, primaryR: .4,
      statX: 95, statY: 350,
      secondaryX: 90, secondaryY: 680, secondaryW: 560, secondaryH: 270, secondaryR: -1.4,
      lineX: 710, lineY: 830,
    },
    'archive-video': {
      textX: 94, textY: 78, textW: 620,
      primaryX: 64, primaryY: 64, primaryW: 1792, primaryH: 900, primaryR: 0,
      statX: 1570, statY: 120,
      secondaryX: 1420, secondaryY: 715, secondaryW: 360, secondaryH: 210, secondaryR: 1.4,
      lineX: 1812, lineY: 160,
    },
  };
  const metrics = layouts[scene.layout] ?? layouts['stat-left'];
  const isPoster = scene.layout === 'poster';
  const isFullBleed = scene.layout === 'full-bleed';
  const statDirection = metrics.statX > 960 ? 35 : -35;

  return (
    <AbsoluteFill style={{opacity: sceneOpacity}}>
      <div
        style={{
          position: 'absolute',
          left: metrics.textX,
          top: metrics.textY,
          width: metrics.textW,
          zIndex: 10,
          padding: isFullBleed ? '18px 20px 20px' : 0,
          background: isFullBleed ? `${palette.paper}EE` : 'transparent',
          boxShadow: isFullBleed ? '0 14px 34px rgba(20,20,20,.14)' : 'none',
          transform: `translateY(${interpolate(textProgress, [0, 1], [34, 0])}px)`,
          opacity: textProgress,
        }}
      >
        <AccentLabel color={accent} progress={textProgress}>{scene.kicker}</AccentLabel>
        <div
          style={{
            marginTop: 14,
            maxWidth: metrics.textW,
            color: palette.ink,
            fontFamily,
            fontSize: isPoster ? 68 : isFullBleed ? 58 : 52,
            fontWeight: 900,
            lineHeight: 1.08,
            letterSpacing: -2.4,
          }}
        >
          {scene.headline}
        </div>
        <div
          style={{
            display: 'inline-block',
            marginTop: 14,
            padding: '6px 10px',
            color: palette.white,
            background: palette.ink,
            fontFamily,
            fontSize: 14,
            fontWeight: 750,
            letterSpacing: 1.8,
          }}
        >
          {scene.meta}
        </div>
      </div>

      <MediaCard
        src={scene.primary}
        mediaType={scene.primaryType}
        progress={primaryProgress}
        x={metrics.primaryX}
        y={metrics.primaryY}
        width={metrics.primaryW}
        height={metrics.primaryH}
        rotate={metrics.primaryR}
        zoom={scene.layout === 'stat-right' ? 1.065 : 1.045}
        startFrom={scene.primaryStartFrom}
        label={scene.primaryLabel}
        coverMode={coverMode}
      />

      <div
        style={{
          position: 'absolute',
          left: metrics.statX,
          top: metrics.statY,
          zIndex: 12,
          color: accent,
          fontFamily,
          fontSize: isPoster ? 128 : 104,
          fontWeight: 950,
          lineHeight: .85,
          letterSpacing: -5,
          fontVariantNumeric: 'tabular-nums',
          transform: `translateX(${interpolate(statProgress, [0, 1], [statDirection, 0])}px) scale(${interpolate(statProgress, [0, 1], [.85, 1])})`,
          opacity: statProgress,
        }}
      >
        {scene.stat}
        <div
          style={{
            marginTop: 16,
            color: palette.ink,
            fontSize: 16,
            fontWeight: 800,
            letterSpacing: 1.6,
          }}
        >
          {scene.statLabel}
        </div>
      </div>

      <MediaCard
        src={scene.secondary}
        mediaType={scene.secondaryType}
        progress={statProgress}
        x={metrics.secondaryX}
        y={metrics.secondaryY}
        width={metrics.secondaryW}
        height={metrics.secondaryH}
        rotate={metrics.secondaryR}
        zoom={1.08}
        zIndex={11}
        startFrom={scene.secondaryStartFrom}
        label={scene.secondaryLabel}
        coverMode={coverMode}
      />

      <PersonCutout
        src={scene.cutout}
        side={scene.cutoutSide}
        progress={statProgress}
        outline={scene.cutoutOutline}
        outlineColor={palette[scene.cutoutOutlineColor] ?? accent}
        coverMode={coverMode}
      />

      <OpeningImpact
        enabled={coverMode && scene.openingMotion === 'cover-impact'}
        accent={accent}
      />

      <div
        style={{
          position: 'absolute',
          left: metrics.lineX,
          top: metrics.lineY,
          width: 3,
          height: interpolate(statProgress, [0, 1], [0, 116]),
          background: accent,
          zIndex: 13,
        }}
      />
      <Caption text={scene.caption} palette={palette} progress={captionIn * captionOut} />
    </AbsoluteFill>
  );
};

export const EditorialDocumentary = ({story}) => {
  return (
    <AbsoluteFill style={{background: story.palette.paper}}>
      <PaperBackground palette={story.palette} />
      {story.scenes.map((scene) => (
        <Sequence
          key={scene.id}
          from={scene.from}
          durationInFrames={scene.duration}
          premountFor={30}
        >
          <Scene scene={scene} palette={story.palette} />
        </Sequence>
      ))}
      {story.audio ? <Audio src={staticFile(story.audio)} /> : null}
    </AbsoluteFill>
  );
};
