# Asset preprocessing gates

## Person cutout

Prefer a portrait with clear shoulders or full body, high subject/background separation, and at least 1600 px on the long edge. Preserve the downloaded source.

When HyperFrames is available:

```bash
npx hyperframes remove-background public/assets/person-source.jpg \
  -o public/assets/person-cutout.png
```

Validate:

```bash
file public/assets/person-cutout.png
identify -verbose public/assets/person-cutout.png | rg 'Geometry|Type:|Alpha:'
```

Require RGBA, transparent corners, plausible subject coverage, and clean hair/hand/microphone edges. Composite a preview over the actual paper color before approving it.

Also preview the alpha PNG with the intended 4–10 px outline treatment. Reject sources whose hair, glasses, hands, microphone, or clothing produce a distracting halo. Keep the outline as a separate Remotion layer so its color, pulse, sweep, and timing remain editable.

## Video normalization

Trim outside Remotion and remove unused source audio:

```bash
ffmpeg -y -ss <start> -t <duration> -i source.mp4 \
  -vf 'scale=1920:-2,fps=30' -an \
  -c:v libx264 -crf 20 -pix_fmt yuv420p \
  public/assets/clip.mp4
```

Choose the internal start time so the first rendered frame already contains meaningful action. Avoid visible loops. Verify each normalized clip with a full FFmpeg decode.

For a keynote, launch, official demo, or founder interview, save the original source URL and selected source-time range in the ledger. Prefer a 1.5–5 second excerpt with a clear action or reveal. Remove source audio unless it is explicitly part of the editorial plan. Label the rendered clip `OFFICIAL FOOTAGE`, `ARCHIVE`, `CONTEXT`, or `RECONSTRUCTION` according to its evidence role.

## Generated historical environments

Generate only the environment or anonymous figures, reserve negative space for typography, exclude readable text and logos, and specify the period equipment. Keep explanatory diagrams and all exact words code-native in Remotion.

Record the prompt, provider, date, and `factualRole: illustrative only` in the ledger. Add an on-screen `ORIGINAL RECONSTRUCTION` or equivalent label when it could be confused with archival material.

## Audio lock

Synthesize or record narration first, normalize it, then transcribe the final processed file. Time captions and scenes from that processed waveform, not from the pre-speed-change file.
