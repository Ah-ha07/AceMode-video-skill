# Story and scene-plan schema

## 目录

- [`scene-plan.json`](#scene-planjson)
- [`src/story.json`](#srcstoryjson)
- [`source-ledger.json`](#source-ledgerjson)

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
  "transitionMode": "opaque-cut",
  "targetDurationSeconds": 16,
  "durationToleranceSeconds": 0.5,
  "totalFrames": 480,
  "audio": "audio/voiceover.wav",
  "brand": {
    "profile": "acemode",
    "enabled": false,
    "wordmark": "AceMode",
    "logoAsset": null,
    "communityLabel": "AI 实践者效率社区",
    "promise": "10X faster, log off earlier",
    "publisherBug": "ACE MODE / AI SIGNALS",
    "requiresBrandReview": true,
    "colors": {
      "navy": "#162D51",
      "midnight": "#0D1A2B",
      "cloud": "#F0F6FA",
      "signalCyan": "#2EE6D6"
    }
  },
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

For schema version 2, `aspectRatio`, `transitionMode`, `targetDurationSeconds`, and `durationToleranceSeconds` are required. The ratio must agree with `width` and `height`, and the timeline duration must stay within the declared tolerance. Use `16:9`, `9:16`, `1:1`, or `4:5`. Use `opaque-cut` by default; choose `designed-overlap` only when the delivery spec and transition review explicitly approve it.

Every version-2 scene declares its emotional and motion intent. `energy` is an integer from 1 to 5; `motionBudget` is `low`, `medium`, or `high`; `readingWindowFrames` is the minimum stable reading interval; and `focalAnchor` describes the intended visual anchor. Read [emotion-motion-curve.md](emotion-motion-curve.md) before assigning these fields.

With `opaque-cut`, every scene begins exactly where the previous scene ends and each scene paints a fully opaque frame. `designed-overlap` may overlap only by an intentional, reviewed amount. The final scene end must equal `totalFrames`. Use paths relative to `public/`, never URLs.

`primaryType` and `secondaryType` may be `image` or `video`; omit them for images. `cutout` is optional and must point to an RGBA PNG or transparent SVG derived from a ledgered source. Use `layout: cutout-portrait` when the cutout is the dominant identity device.

The first render scene must start at frame 0 and set `coverFrame: true` plus `openingMotion: "cover-impact"`. All cover-critical media, identity, and headline layers are visible on frame 0. Scene `caption` remains a short beat summary for planning/backward compatibility; spoken captions come only from the top-level TTS-timed `captions.json` manifest and render once above all scenes. Use `primaryStartFrom` and `secondaryStartFrom` to begin an official clip on a meaningful internal frame. Use `primaryLabel` or `secondaryLabel` to identify official footage, archive material, contextual B-roll, or reconstruction.

Use the optional top-level `brand` block only for publisher identity. Keep `enabled: false` by default. When the user explicitly approves AceMode publishing identity, read [acemode-brand.md](acemode-brand.md), set `profile: "acemode"`, enable it, and use the official wordmark path in `logoAsset` when it exists. Keep `requiresBrandReview: true` while using a text fallback. Branding must not silently alter narration. Set `brandRole: "close"` on the final scene when it should carry the larger closing wordmark.

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
