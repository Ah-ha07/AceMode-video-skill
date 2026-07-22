# Native aspect-ratio directing

Read this reference when delivering 9:16, delivering more than one ratio, or adapting an existing edit to a new ratio.

## Core contract

Share the factual research, locked narration, word timings, source ledger, and original media. Direct the composition separately for each ratio.

For multi-ratio delivery, keep:

```text
src/story-16x9.json
src/story-9x16.json
qa/cover-frame-16x9.png
qa/cover-frame-9x16.png
qa/opening-preview-16x9.mp4
qa/opening-preview-9x16.mp4
```

Never produce one ratio by scaling the complete composition of another. Cropping an individual source asset is normal; cropping or letterboxing a finished scene is not.

## Plan ratio-specific decisions

Declare the delivery profiles at the scene-plan root:

```json
{
  "deliveryProfiles": [
    {"id": "16x9", "aspectRatio": "16:9", "width": 1920, "height": 1080},
    {"id": "9x16", "aspectRatio": "9:16", "width": 1080, "height": 1920}
  ]
}
```

For a single ratio, use the normal beat layout fields. For multiple ratios, add `layoutByProfile` only where geometry, crop, evidence placement, or text hierarchy changes:

```json
{
  "layoutByProfile": {
    "16x9": {"layout": "stat-left", "focalAnchor": "center-right"},
    "9x16": {"layout": "portrait", "focalAnchor": "top-center"}
  }
}
```

Do not fork narration timing unless the user requests ratio-specific edits.

## Compose for the reading direction

### 16:9

- Use horizontal cause-and-effect, timelines, score rails, unequal splits, and document-plus-subject arrangements.
- Let dominant media occupy roughly 55–75% of the frame; use the remaining width for a clear editorial rail.
- Keep captions in a dedicated bottom band and keep action, faces, and evidence labels out of that band.
- Prefer lateral evidence-card motion, restrained camera pushes, and depth separation over vertical stacking.

### 9:16

- Build a vertical hierarchy: identity or claim near the top, dominant subject through the center, proof or data below it, captions in their own lower band.
- Use fewer simultaneous cards. One large proof card is stronger than shrinking a horizontal three-card layout.
- Re-crop source media around the face, hands, ball, product, or document detail that carries the beat.
- Prefer depth, scale, and short vertical travel; avoid long side-to-side movement that wastes portrait width.

## Record crop intent

Add normalized `focalPoint` coordinates to a ledger item when automated cropping could lose the subject:

```json
{
  "focalPoint": {"x": 0.62, "y": 0.38},
  "safeCrop": {
    "16:9": "keep trophy and both hands",
    "9:16": "keep face, trophy, and upper torso"
  }
}
```

Create aspect-specific derivatives when one crop cannot preserve the evidence. Keep every derivative linked to its licensed source.

## Re-direct the opening

Preserve the same opening claim and factual payoff across ratios, but redesign all of these:

- headline line breaks and maximum footprint;
- hero crop or cutout scale;
- evidence-card size and entry path;
- score/stat rail orientation;
- subject, headline, and caption collision zones.

Frame 0 must be a finished cover in every ratio. Check frames 0, 8, 18, 45, and 90 independently for each composition.

## Multi-ratio QA

- Compare both covers at 25% size; each needs one obvious focal point.
- Confirm no ratio contains letterboxing, stretched media, uniform scene scaling, or inherited empty space.
- Confirm the named subject remains identifiable and direct evidence remains legible.
- Check that a cutout does not accidentally duplicate the same person already visible at similar scale in the background.
- Review caption safety, title safety, action crops, and transition midpoints separately.
- Request user approval on the latest review package for every ratio before full-length rendering.
