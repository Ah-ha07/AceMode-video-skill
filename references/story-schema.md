# Story and scene-plan schema

## `scene-plan.json`

Use this planning shape before touching Remotion code:

```json
{
  "schemaVersion": 2,
  "storyPromise": "Why the viewer should stay",
  "targetDurationSeconds": 180,
  "durationToleranceSeconds": 5,
  "deliveryProfiles": [
    {"id": "16x9", "aspectRatio": "16:9", "width": 1920, "height": 1080}
  ],
  "openingContract": {
    "frameZeroIsCover": true,
    "motion": "cover-to-story",
    "evidenceVisibleBySeconds": 1.5,
    "firstPayoffBySeconds": 3
  },
  "beats": [
    {
      "id": "beat-01",
      "start": 0,
      "end": 6.2,
      "transcript": "Narration text",
      "job": "Establish the apparent impossibility",
      "emotion": "astonishment",
      "energy": 5,
      "motionBudget": "high",
      "readingWindowFrames": 42,
      "focalAnchor": "center-right",
      "layout": "full-bleed",
      "headline": "A short editorial headline",
      "meta": "SOURCE · DATE",
      "stat": "3–2",
      "caption": "One spoken clause",
      "primaryAssetId": "asset-001",
      "secondaryAssetIds": ["asset-002"],
      "subjectName": "Named person, launch, product, or event",
      "subjectType": "person",
      "evidenceRole": "direct",
      "entrance": "media-right-spring",
      "camera": "push-104",
      "transition": "crossfade-16f",
      "fallback": "Use a verified still plus score card"
    }
  ]
}
```

## `src/story.json`

The bundled template consumes this render shape:

```json
{
  "schemaVersion": 2,
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "aspectRatio": "16:9",
  "targetDurationSeconds": 16,
  "durationToleranceSeconds": 0.5,
  "totalFrames": 480,
  "audio": "audio/voiceover.wav",
  "palette": {
    "paper": "#F2EEE5",
    "ink": "#141414",
    "muted": "#6F726F",
    "red": "#E94443",
    "teal": "#2C9DA5",
    "yellow": "#E6B92B",
    "white": "#FFFDF7"
  },
  "scenes": [
    {
      "id": "beat-01",
      "from": 0,
      "duration": 170,
      "emotion": "astonishment",
      "energy": 5,
      "motionBudget": "high",
      "readingWindowFrames": 42,
      "focalAnchor": "center-right",
      "kicker": "Context label",
      "headline": "Editorial headline",
      "meta": "SOURCE · DATE",
      "stat": "10",
      "statLabel": "What the number means",
      "caption": "One spoken clause",
      "primary": "assets/primary.jpg",
      "secondary": "assets/secondary.jpg",
      "primaryType": "image",
      "secondaryType": "image",
      "primaryStartFrom": 0,
      "primaryLabel": "OFFICIAL FOOTAGE · SOURCE",
      "cutout": "assets/person-cutout.png",
      "cutoutSide": "right",
      "cutoutOutline": true,
      "cutoutOutlineColor": "teal",
      "subjectName": "Named person",
      "subjectType": "person",
      "evidenceRole": "direct",
      "coverFrame": true,
      "openingMotion": "cover-impact",
      "accent": "teal",
      "layout": "stat-left"
    }
  ]
}
```

For schema version 2, `aspectRatio`, `targetDurationSeconds`, and `durationToleranceSeconds` are required. The ratio must agree with `width` and `height`, and the timeline duration must stay within the declared tolerance. Use `16:9`, `9:16`, `1:1`, or `4:5`.

Every version-2 scene declares its emotional and motion intent. `energy` is an integer from 1 to 5; `motionBudget` is `low`, `medium`, or `high`; `readingWindowFrames` is the minimum stable reading interval; and `focalAnchor` describes the intended visual anchor. Read [emotion-motion-curve.md](emotion-motion-curve.md) before assigning these fields.

Scene `from` values may overlap by 12–20 frames for transitions. The final scene end must equal `totalFrames`. Use paths relative to `public/`, never URLs.

`primaryType` and `secondaryType` may be `image` or `video`; omit them for images. `cutout` is optional and must point to an RGBA PNG or transparent SVG derived from a ledgered source. Use `layout: cutout-portrait` when the cutout is the dominant identity device.

The first render scene must start at frame 0 and set `coverFrame: true` plus `openingMotion: "cover-impact"`. All cover-critical media, identity, and headline layers are visible on frame 0; captions may enter after the cover frame. Use `primaryStartFrom` and `secondaryStartFrom` to begin an official clip on a meaningful internal frame. Use `primaryLabel` or `secondaryLabel` to identify official footage, archive material, contextual B-roll, or reconstruction.

Whenever narration names an editorially important person, product launch, keynote, paper, or event, set `subjectName`, `subjectType`, and `evidenceRole`. For `subjectType: "person"`, prefer a ledgered `cutout` plus contextual primary or secondary evidence. For `subjectType: "event"`, prefer a direct-evidence video; use a still or document fallback only when the ledger explains why.

## `source-ledger.json`

```json
{
  "assets": [
    {
      "id": "asset-001",
      "localPath": "assets/primary.jpg",
      "sourceUrl": "https://example.org/source-page",
      "license": "CC BY 4.0",
      "attribution": "Creator, title, year",
      "factualRole": "Aerial view of the location",
      "ingestStatus": "approved",
      "publicationStatus": "attribution_required",
      "usageScope": "editorial web video with visible or end-card attribution",
      "replacementRequiredBeforePublish": false,
      "focalPoint": {"x": 0.62, "y": 0.38},
      "safeCrop": {
        "16:9": "keep subject and object",
        "9:16": "keep face, hands, and object"
      }
    }
  ]
}
```

`ingestStatus` answers whether the file may enter a local edit. `publicationStatus` answers whether the resulting video may be published. Valid version-2 publication states are `cleared`, `attribution_required`, `editorial_preview_only`, `legal_review_required`, `unknown`, and `blocked`. Set `replacementRequiredBeforePublish: true` for preview-only, unknown, blocked, or known temporary assets.

For a cutout, crop, color treatment, or normalized clip, add `derivativeOf` with the source asset ID. Background removal does not reset license or attribution obligations.

Generated assets must use `license: generated` and add `provider`, `model`, `prompt`, and `factualRole: illustrative only`.
