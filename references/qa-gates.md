# QA gates

## Story

- Frame 0 works as a standalone cover and the cover evolves into the story rather than cutting to a separate generic title card.
- The first three seconds contain a meaningful evidence reveal and the opening factual payoff; the broader conflict is clear within 8 seconds.
- Measured narration duration stays inside the agreed target tolerance, or the user explicitly approved the revised target before visual production.
- Every beat has one communication job and follows logically from the previous beat.
- Names, dates, scores, quotations, and numbers match research sources.

## Visual relevance

- Every dominant asset directly supports the spoken clause.
- No generic B-roll appears where a real evidence asset is available.
- Editorially important named people and events receive direct visual evidence at or near first mention, or the scene plan records a rights-based fallback.
- Founder cutouts preserve face, hair, hands, glasses, and microphones, and the animated outline remains clean at its widest frame.
- Launch and official-demo clips match the named event, have ledgered source-time ranges, and carry an accurate footage-role label.
- Adjacent scenes vary in layout or media behavior for a reason.
- Faces, ball/action, maps, and document text remain inside their crop at hero frames.
- A foreground cutout does not accidentally duplicate the same person already visible at similar scale in the background.
- Person cutouts have a real alpha channel, transparent corners, no obvious halo, and no missing face/hair/hand regions.
- Generic footage and generated reconstructions carry an accurate visual-role label when context could be mistaken for direct evidence.

## Delivery ratio

- Every requested ratio has its own composition, story file, cover, opening preview, and review board.
- No scene is a uniformly scaled, stretched, letterboxed, or crop-only conversion of another finished composition.
- Headline wrapping, dominant geometry, focal crop, proof-card placement, and caption band are native to the ratio.
- Multi-ratio versions preserve the same factual claim and evidence role even when the visual crop or layout differs.

## Motion

- No CSS keyframes or nondeterministic animation.
- Entrances establish a clear order; elements do not all move together.
- Frame 0 has no fade-in dependency: cover-critical headline, subject, and proof media are already visible.
- Opening motion has three readable stages—cover, impact, evidence—without sacrificing mobile-scale legibility.
- Cutout outline motion pulses or sweeps once and settles; it does not loop continuously.
- Each scene has a stable reading window.
- Scene energy and motion-budget fields form a deliberate curve with readable valleys, not an uninterrupted sequence of peaks.
- Default `opaque-cut` scenes are contiguous and each scene paints a fully opaque frame. Use overlap only when delivery spec explicitly chooses `designed-overlap` and the transition board proves the composite is intentional.
- Captions render once at composition root from the TTS-timed manifest; scene boundaries cannot create a second caption layer.

## Typography

- Chinese captions normally stay within 24 characters and one line at 1920×1080.
- Headline stays within three lines and does not collide with media.
- Numbers use tabular figures and retain their unit/meaning label.

## Technical

- Story validator exits zero.
- Publication delivery also passes `validate_story.py ... --publication`.
- Render is 1920×1080, 30fps unless the delivery spec says otherwise.
- Final audio targets roughly -16 LUFS for web video with true peak no higher than -1.5 dBTP.
- FFmpeg decodes the full file with no errors.
- No unintended black frame, missing asset, silent narration gap, or frozen motion longer than the planned hold.
- Every MP4 asset decodes independently, and all source clips are normalized to a predictable frame rate and pixel format before final rendering.
- Contact sheet and transition midpoint frames have been reviewed.
- Every scene boundary has before/cut/after frames in an explicitly reviewed transition manifest; no double headline, stale caption, transparent remnant, or one-frame black flash remains. Rendering the board alone leaves it `ready`, not `passed`.

## Approval package

- The user received the measured narration duration, target, and tolerance.
- The user received frame 0, a three-second preview with narration, and a representative key-frame board for every ratio.
- Material factual uncertainty, preview-only media, legal-review items, attribution requirements, and replacement requirements were disclosed.
- Approval was obtained after the latest material change and before full-length rendering.
