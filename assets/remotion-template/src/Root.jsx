import React from 'react';
import {Composition} from 'remotion';
import {EditorialDocumentary} from './EditorialDocumentary';
import {VerticalNewsroom} from './VerticalNewsroom';
import captions from './captions.json';
import story from './story.json';
import verticalStory from './vertical-story.json';

export const RemotionRoot = () => {
  return (
    <>
    <Composition
      id="EditorialDocumentary"
      component={EditorialDocumentary}
      durationInFrames={story.totalFrames}
      fps={story.fps}
      width={story.width}
      height={story.height}
      defaultProps={{story, captions}}
    />
    <Composition
      id="VerticalNewsroom"
      component={VerticalNewsroom}
      durationInFrames={verticalStory.totalFrames}
      fps={verticalStory.fps}
      width={verticalStory.width}
      height={verticalStory.height}
      defaultProps={{story: verticalStory, captions}}
    />
    </>
  );
};
