import React from 'react';
import {Composition} from 'remotion';
import {EditorialDocumentary} from './EditorialDocumentary';
import story from './story.json';

export const RemotionRoot = () => {
  return (
    <Composition
      id="EditorialDocumentary"
      component={EditorialDocumentary}
      durationInFrames={story.totalFrames}
      fps={story.fps}
      width={story.width}
      height={story.height}
      defaultProps={{story}}
    />
  );
};
