# Research and rights discipline

## Evidence order

Prefer sources in this order:

1. official records, governing bodies, company filings, original datasets, direct transcripts;
2. reputable newsrooms and institutional archives;
3. licensed photo/video libraries;
4. Wikimedia Commons files with a clear file-page license;
5. generated illustration for non-evidentiary connective material.

Search snippets are discovery aids, not evidence. Save the page that states the fact or license.

## Asset rights

- `public domain`: record the basis and jurisdiction.
- `CC0`: no attribution required, but keep source provenance.
- `CC BY`: preserve the exact creator and license link.
- `CC BY-SA`: confirm share-alike compatibility with the intended distribution.
- `editorial use only`: do not use in advertising or branded promotion without a separate license.
- `official broadcast footage`: assume protected unless written permission or a platform license covers the use.
- `fair use/fair dealing`: treat as a legal review path, not an automatic production license.

## Separate edit approval from publication clearance

Use two independent fields in `source-ledger.json`:

- `ingestStatus`: `approved` or `blocked`; controls whether the local production may use the file.
- `publicationStatus`: `cleared`, `attribution_required`, `editorial_preview_only`, `legal_review_required`, `unknown`, or `blocked`; controls whether an export may be published.

Also record `usageScope` and `replacementRequiredBeforePublish`. A licensed editorial preview, source-page screenshot, or temporary watermarked image may be approved for local composition while still blocking publication. Do not rename that state to `approved` merely to make a validator pass.

Run normal story validation while composing. Run `validate_story.py ... --publication` before publication delivery. Publication mode must fail on preview-only, legal-review, unknown, blocked, or replacement-required media.

## Real-event integrity

Never label a generic clip as the actual event. Use one of these factual roles:

- `direct evidence`: the asset depicts the claimed event or person and provenance proves it;
- `context`: the asset accurately depicts the place, organization, or era but not the event;
- `illustrative only`: generated or generic imagery that cannot prove the claim.

Make direct evidence visually primary. Label archival/context footage when ambiguity would mislead.

For a real-person cutout, preserve the original licensed portrait and record the alpha PNG as a derivative of that exact source. Attribution and share-alike obligations survive background removal, cropping, color treatment, and animation.

Use `derivativeOf` to connect a cutout, crop, denoised still, or normalized clip to the original ledger item. Record ratio-specific focal points or safe-crop notes when automatic reframing could remove the evidentiary subject.

## Image generation boundary

Good uses: abstract map backgrounds, metaphorical transitions, texture, non-specific environments, concept diagrams.

For a historical reconstruction, exclude identifiable real faces unless the user supplied a reference and the depiction is clearly disclosed. Add `factualRole: illustrative only`, label it on-screen when viewers could mistake it for archival evidence, and never use it to prove a factual claim.

Bad uses: fake match footage, fabricated documents, invented product screenshots, real-person actions that never happened, text-heavy title cards with baked-in lettering.
