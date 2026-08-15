# Emotion and motion curve

Read this reference before assigning entrances, camera motion, and transitions. The goal is controlled attention, not maximum movement.

## Plan the curve first

Write one emotional word and one energy score for every beat. Read the scores in sequence before choosing effects.

Use these scene fields:

```json
{
  "emotion": "triumph",
  "energy": 5,
  "motionBudget": "high",
  "readingWindowFrames": 42,
  "focalAnchor": "center-right"
}
```

`energy` is an integer from 1 to 5:

1. still, intimate, reflective;
2. measured context or consequence;
3. active explanation and evidence;
4. escalation, contrast, or discovery;
5. hook, decisive reveal, victory, or rupture.

Use `motionBudget` to limit simultaneous motion channels:

- `low`: one active channel, such as camera drift or typography;
- `medium`: two active channels, such as media plus evidence card;
- `high`: at most three coordinated channels, reserved for a short peak.

Motion channels are camera, hero object/person, typography, evidence insert, data graphic, and transition. A high-energy scene does not authorize every channel at once.

## Build contrast

Use peaks and valleys. After one or two energy-4/5 beats, create a readable hold or lower-energy beat unless the story demands a continuous climax. Avoid a flat sequence where every scene uses the same speed, spring, and transition.

Useful documentary phrases include:

```text
HOOK 5 → PROOF 4 → CONTEXT 2 → DISCOVERY 3 → TURN 4 → CONSEQUENCE 2 → MEANING 1
```

```text
VICTORY 5 → ORIGIN 2 → EXPANSION 3 → COMMERCIAL PEAK 4 → HUMAN QUESTION 1
```

Choose the curve from the argument, not from a genre preset.

## Protect reading time

Every beat needs a stable interval in which the dominant media, headline, and evidence relationship can be understood. Set `readingWindowFrames` explicitly:

- 36–54 frames for a simple hero statement at 30fps;
- 54–90 frames for a document, chart, map, or multi-step causal explanation;
- longer when viewers must read source text.

Do not count a period of continuous zooming, card reshuffling, or text replacement as a stable reading window.

## Direct entrances

Give every movement a communication job:

- reveal identity;
- expose proof;
- show chronology;
- compare two states;
- convert a number into meaning;
- transfer attention into the next beat.

Use a clear visual order such as hero → headline → proof. Timed captions follow narration independently at composition root. During an energy peak, shorten the delay between visual stages; during a reflective beat, lengthen the hold rather than slowing every animation into mush.

## Shape the first three seconds

The opening normally follows:

1. frame 0: complete cover and proof cue;
2. frames 2–18: one impact movement;
3. frames 12–45: direct evidence reveal;
4. frames 36–90: first factual payoff and conversion into the story.

Use one hero movement, one evidence movement, and one typography movement. If the opening still feels weak, strengthen the claim, proof, silhouette, or contrast before adding more effects.

## QA the curve

- Scrub the timeline without audio; the energy pattern should still be visible.
- Listen without video; narration emphasis should align with the visual peaks.
- Reject four or more consecutive high-energy beats unless there is a documented climax.
- Check that each peak has one dominant focal point.
- Check that reflective beats remain designed frames rather than dead or empty screens.
- Remove any looping outline, floating card, or idle effect that competes with the current spoken clause.
