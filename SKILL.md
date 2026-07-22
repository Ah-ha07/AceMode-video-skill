---
name: editorial-documentary-video
description: Create sourced, narration-driven editorial documentary videos in Remotion with native 16:9 or 9:16 direction, real archival photos and event footage, licensed person cutouts, animated outline treatments, cover-ready opening frames, high-impact first-three-second hooks, evidence cards, diagrams, and synced Chinese captions. Use when the user gives a topic, person, script, SRT, audio, article, or reference video and wants a polished biography, AI/history explainer, news feature, sports story, business, or technology mini-documentary rather than a talking head, slideshow, product promo, or fully generative cinematic film.
---

# Editorial Documentary Video

Build a reproducible documentary pipeline whose source of truth is narration timing plus a reviewed scene plan. Treat motion as the execution layer; research, beat selection, and asset matching are the quality bottlenecks.

## Route first

- Use this skill for 45-second to 6-minute narrated editorial stories built from real footage, photos, maps, documents, numbers, and captions.
- For a person-led history or biography, read [references/person-led-story.md](references/person-led-story.md) before research and scene planning.
- Use `motion-graphics` for a short unnarrated title/stat hit.
- Use `faceless-explainer` for abstract concept teaching that needs diagrams more than evidence media.
- Use `embedded-captions` or `graphic-overlays` when enhancing an existing finished talking-head video.
- Do not use this workflow for synthetic cinematic films, live data, or unlicensed broadcast-footage redistribution.

## Required output contract

Create all work under `videos/<topic-slug>/` and keep these artifacts:

```text
research.md
script.md
script.txt
audio/voiceover.wav
audio/tts-manifest.json
transcript.words.json
scene-plan.json
source-ledger.json
public/assets/
src/story.json                     # one delivery ratio
src/story-16x9.json                # use ratio suffixes for multi-ratio delivery
src/story-9x16.json
renders/final[-<ratio>].mp4
qa/cover-frame[-<ratio>].png
qa/opening-preview[-<ratio>].mp4
qa/review-board[-<ratio>].png
qa/review-package[-<ratio>].json
qa/render-report.json
```

Do not start layout code until `scene-plan.json` and `source-ledger.json` exist.

## Workflow

### 1. Establish the factual spine

Search in English and write `research.md` with primary sources, dates, disputed claims, and exact numbers. Separate verified facts from narrative interpretation. For current events, public figures, law, prices, schedules, or product details, browse before scripting.

Write a single-sentence story promise: why should the viewer stay until the end? Then structure the script as hook → context → escalation → turning point → resolution → meaning. Land a concrete fact or direct-evidence reveal by 3 seconds and establish the broader conflict within 8 seconds.

Extract every editorially important named person, launch, keynote, official demo, product, paper, and company mentioned in the narration. Give each one an evidence target before scene planning. A founder or public figure normally needs a licensed portrait or event still; a launch or official demo normally needs a licensed clip or a verified still sequence. Read [references/opening-and-evidence-motion.md](references/opening-and-evidence-motion.md) before sourcing or designing the opening.

### 2. Lock narration before visuals

Set `targetDurationSeconds` and `durationToleranceSeconds` in the scene plan before recording or sourcing visual assets. Record or synthesize the final narration, measure its real duration, then transcribe it with word timestamps. Never estimate final timing from character count. Preserve the original language; non-English Whisper models must not use an `.en` suffix.

For Chinese technology news and documentary narration, use this default voice unless the user explicitly requests another voice or provides final recorded narration:

```text
Provider: Volcengine / Doubao Speech V3
Resource: seed-tts-2.0
Voice: 大壹 2.0
Voice ID: zh_male_dayi_saturn_bigtts
Language: zh-CN
Base speed: 1.08
```

Keep the clean narration-only text in `script.txt`, with one semantic paragraph per line. Generate those lines separately so mistakes can be replaced without regenerating the whole voiceover. With `VOLCANO_APP_ID` and `VOLCANO_ACCESS_TOKEN` set, run:

```bash
node <SKILL_DIR>/scripts/synthesize_volcano_dayi.mjs \
  --input videos/<topic-slug>/script.txt \
  --output videos/<topic-slug>/audio/voiceover.wav \
  --manifest videos/<topic-slug>/audio/tts-manifest.json
```

The helper uses real Volcengine V3 sentence and word timestamps, preserves raw paragraph segments, concatenates them, and masters the final WAV to 48 kHz mono near -16 LUFS with a -1.5 dBTP ceiling. If credentials or the 2.0 entitlement are unavailable, stop and report the missing capability; never silently switch to MiniMax, a system voice, or a different Volcengine speaker.

If measured narration falls outside the agreed duration tolerance, revise the script before visual production or ask the user to approve a new target. Do not silently accept a large overrun and do not force narration into a preconceived duration. Prefer shortening the script or retiming the scene plan. If a final no-pitch-change adjustment is unavoidable, keep total post-speed at or below `1.15x`; record the exact factor in `audio/tts-manifest.json`.

Segment narration into semantic beats, normally 4–8 seconds each. Split on a visual idea change, not every sentence. A 3-minute piece usually needs roughly 22–30 beats.

### 3. Make the director table

Read [references/story-schema.md](references/story-schema.md), then write `scene-plan.json`. Each beat must declare:

- narration time range and transcript text;
- one communication job;
- emotion, energy level, motion budget, and minimum stable reading window;
- primary evidence asset and optional secondary asset;
- layout family;
- headline, stat, and caption copy;
- entrance, hold, camera motion, and transition;
- source-ledger IDs;
- fallback if the ideal asset cannot be licensed.

When a beat names a real person or event, also declare `subjectName`, `subjectType`, `evidenceRole`, and the exact still, cutout, or clip that will appear. Do not let an editorially important named entity remain text-only when usable evidence exists.

The first beat is a special `cover-to-story` beat. Frame 0 must already be a finished cover composition—not black, empty, blurred, or halfway through an entrance. In the next three seconds, evolve that same composition into the story with an evidence reveal, cutout outline motion, or official-footage insert. Do not place a disconnected title card before the story.

Draft an intentional energy curve before assigning scene motion. Read [references/emotion-motion-curve.md](references/emotion-motion-curve.md) and preserve contrast between peaks and breathing spaces; rich motion does not mean constant motion.

Do not assign layouts randomly. Read [references/style-grammar.md](references/style-grammar.md) and choose the layout that best explains the beat. For 9:16 delivery, multi-ratio delivery, or conversion from an existing ratio, also read [references/aspect-ratio-directing.md](references/aspect-ratio-directing.md). Share research, narration, and assets across ratios, but create a native scene plan and story file for each ratio. Never ship a crop-only, letterboxed, stretched, or uniformly scaled conversion.

### 4. Source before composing

Prefer owned, public-domain, Creative Commons, or commercially licensed media. For real people, real matches, products, charts, documents, and locations, use real evidence media. Use image generation only for abstract connective visuals, atmospheres, or explicitly illustrative scenes; never let generated imagery impersonate archival evidence.

Read [references/research-and-rights.md](references/research-and-rights.md). Record every asset in `source-ledger.json` before it enters the timeline. Separate `ingestStatus`, which controls whether an asset may enter a local edit, from `publicationStatus`, which controls whether the result may be published. A successful preview validation is not publication clearance. Download assets into `public/assets/`; do not render from volatile remote URLs.

When narration introduces a founder, executive, researcher, public figure, keynote, launch, or official demo, actively search for direct visual evidence instead of defaulting to generic B-roll. Prefer official press kits, official event recordings, licensed editorial media, Wikimedia Commons, or owned material. When a usable official clip exists, select a short meaningful excerpt and record its source plus in/out timestamps. If rights are unclear, use a licensed still, document, or screenshot and state the fallback in the scene plan.

When the story needs an isolated real person, use a properly licensed high-resolution portrait, remove its background locally, and keep the source file beside the alpha PNG. Build the outline in Remotion from the alpha asset; do not permanently bake a neon halo into the source image. When the story needs launch or machine footage, trim and normalize the clip before Remotion sees it. Read [references/asset-preprocessing.md](references/asset-preprocessing.md) for the exact gates.

### 5. Scaffold and build

Run:

```bash
python <SKILL_DIR>/scripts/scaffold_project.py videos/<topic-slug>
```

Replace `src/story.json` with the approved scene data, add narration under `public/audio/`, and add sourced media under `public/assets/`. For multiple ratios, create one composition and one story file per ratio while reusing shared media and timing where they remain valid. Keep the renderer data-driven: one scene component family, multiple layout variants, no per-topic fork unless the story requires a genuinely new visual grammar.

Use Remotion frame-driven animation only. No CSS transitions, CSS keyframes, timers, random values, or DOM-dependent timing. Use `Img`, `OffthreadVideo`, `Audio`, and `Sequence`; premount every sequence. Keep captions as live text, never baked into generated images.

Use the bundled `coverFrame`, `openingMotion`, `cutoutOutline`, clip start-frame, and footage-label fields for the opening and person/event beats. The default template keeps every cover-critical layer visible at frame 0, then adds deterministic outline, parallax, evidence-card, and accent-line motion.

### 6. Validate before rendering

Run the deterministic gate:

```bash
python <SKILL_DIR>/scripts/validate_story.py \
  videos/<topic-slug>/src/story.json \
  videos/<topic-slug>/source-ledger.json
```

Fix every error. Review warnings about long headlines, dense captions, timing gaps, weak asset diversity, or excessive transition overlap.

Before delivery for publication, run the stricter rights gate:

```bash
python <SKILL_DIR>/scripts/validate_story.py \
  videos/<topic-slug>/src/story.json \
  videos/<topic-slug>/source-ledger.json \
  --publication
```

Default validation may allow clearly labeled local-preview assets; publication validation must reject unresolved, preview-only, unknown, blocked, or replacement-required assets.

### 7. Stop for user approval

Do not start a full-length MP4, MOV, or final export until the user has reviewed the latest content package and explicitly approved rendering.

Before requesting approval, provide:

- the final narration script, measured duration, target, and tolerance;
- the scene plan or a concise beat-by-beat summary;
- a frame-0 cover, a three-second preview with narration, and a representative key-frame review board for every delivery ratio;
- the selected voice, sourced people/events, and any material factual or rights caveats.

Build the package without rendering the full timeline:

```bash
python <SKILL_DIR>/scripts/build_review_package.py \
  videos/<topic-slug> \
  --composition EditorialDocumentary \
  --story src/story.json
```

For multi-ratio delivery, run it once per composition with the matching `--story` and `--suffix`. The manifest records timeline duration, target tolerance, sampled frames, and publication blockers.

Ask a direct question such as: `内容和画面方向已经准备好，是否开始正式渲染？`

Approval must come after the latest review package. A general instruction to make a video earlier in the conversation is not render approval. If the script, voice, scene order, visual direction, or major assets change after approval, invalidate the approval and ask again before re-rendering.

Before approval, it is acceptable to run story validation, open Remotion Studio, and render a small number of still frames or a short low-resolution motion sample needed for review. Do not render the complete timeline merely to show progress.

Skip this gate only when the user explicitly says in the current request to render directly or not to ask for confirmation.

### 8. Render and inspect

From the project directory:

```bash
npm install
npm run cover
npm run render
ffmpeg -v error -i renders/editorial-documentary.mp4 -f null -
```

Create a 1 fps contact sheet and inspect the opening, every transition midpoint, every hero frame, and the final frame. Read [references/qa-gates.md](references/qa-gates.md). Repair the plan or layout, not just the symptom.

## Non-negotiable quality rules

- The narration controls timing; the template never stretches speech.
- Lock a target duration and tolerance before visual production; revise or reconfirm when measured narration misses the target.
- Full-length rendering requires explicit user approval after the latest script, scene plan, and representative visual preview are presented.
- Direct each delivery ratio natively. Reuse evidence and timing, not a finished layout.
- Default Chinese editorial narration is Volcengine `大壹 2.0` at base speed `1.08`; explicit user direction overrides this default.
- Never apply more than `1.15x` post-speed to narration. Shorten the script or retime visuals instead.
- Final narration delivery should be 48 kHz, near -16 LUFS integrated, and no higher than -1.5 dBTP.
- Every beat needs a visible information change within 2.5 seconds, but not every change is a cut.
- Frame 0 is a publication-ready cover: one dominant subject, one short headline, strong contrast, and no incomplete entrance state.
- The first three seconds must contain a cover-to-story transformation and at least one real evidence reveal; decorative motion alone does not count.
- Use 2–4 assets per beat only when they add evidence or contrast.
- Reserve 8% title-safe margins and a dedicated caption-safe band.
- Keep subtitles to one semantic clause and normally no more than 24 Chinese characters per page.
- Use one dominant visual, one supporting detail, and one text hierarchy. Avoid four equal cards.
- Avoid accidental duplicate-subject collisions: do not place a person cutout over a background crop that already shows the same person at similar scale unless the repetition has a clear editorial purpose.
- Vary layout purposefully across adjacent beats while preserving the same design system.
- Never claim a clip depicts an event unless the ledger proves it.
- Show an editorially important named person or event at or near first mention whenever licensed evidence is available; generic AI imagery is not an acceptable substitute.
- Keep evidence roles visible: direct evidence may be primary; generic footage and generated historical reconstructions must be labeled as context or illustrative.
- Animate a person cutout independently from the background; keep the face, hands, and microphone edges outside headline and caption zones.
- Use cutout outlines as a timed identity cue: 4–10 px editorial keyline, brief trace/pulse/sweep, then settle. Avoid permanent neon glow, frantic looping, or effects that damage facial edges.
- Do not publish a final video with unresolved factual, licensing, missing-asset, overflow, decode, or black-frame errors.
- Do not treat local edit approval or a successful render as publication clearance.

## Failure patterns

- If output feels like slides, the scene plan is too sentence-driven or assets are decorative. Rebuild beat jobs and evidence choices.
- If every scene looks the same, add an appropriate layout family; do not add random effects.
- If the opening looks like an ordinary slide, rebuild it as a cover-to-story composition with frame-0 hierarchy, a named subject or product, a real evidence insert, and a three-stage motion sequence.
- If a named founder or launch is spoken but only generic visuals appear, stop and source direct evidence or document the rights-based fallback.
- If pacing feels frantic, reduce simultaneous entrances and give the dominant asset a hold.
- If narration sounds rushed, regenerate or shorten the text; do not repair it with aggressive time compression.
- If text covers faces, change the layout or crop focal point; do not merely shrink everything.
- If a ratio conversion looks like a repurposed canvas, rebuild the dominant geometry, crop, text hierarchy, and evidence placement for that ratio.
- If every beat is high energy, redesign the emotion curve; attention depends on contrast and readable holds.
- If image generation introduces false specificity, replace it with a map, document, diagram, or licensed real asset.
