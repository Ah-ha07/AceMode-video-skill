#!/usr/bin/env python3
"""Validate timing, native delivery, motion intent, local assets, and rights."""

from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path
from urllib.parse import urlparse


LAYOUTS = {"full-bleed", "stat-left", "stat-right", "portrait", "split", "poster", "cutout-portrait", "document-network", "archive-video"}
ACCENTS = {"red", "teal", "yellow"}
SUBJECT_TYPES = {"person", "event", "product", "paper", "company", "place"}
EVIDENCE_ROLES = {"direct", "context", "illustrative"}
ASPECT_RATIOS = {"16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1.0, "4:5": 4 / 5}
MOTION_BUDGETS = {"low", "medium", "high"}
FOCAL_ANCHORS = {
    "left",
    "center-left",
    "center",
    "center-right",
    "right",
    "top-left",
    "top-center",
    "top-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
    "full-frame",
}
INGEST_STATUSES = {"approved", "blocked"}
PUBLICATION_STATUSES = {
    "cleared",
    "attribution_required",
    "editorial_preview_only",
    "legal_review_required",
    "unknown",
    "blocked",
}
PUBLICATION_ALIASES = {
    "approved_with_attribution": "attribution_required",
    "approved_for_editorial_citation": "legal_review_required",
}
PUBLISHABLE_STATUSES = {"cleared", "attribution_required"}
REQUIRED = {
    "id",
    "from",
    "duration",
    "kicker",
    "headline",
    "meta",
    "stat",
    "statLabel",
    "caption",
    "primary",
    "secondary",
    "accent",
    "layout",
}
REQUIRED_V2 = {"emotion", "energy", "motionBudget", "readingWindowFrames", "focalAnchor"}


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read JSON {path}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("story", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument(
        "--publication",
        action="store_true",
        help="Fail on assets that are not cleared for publication",
    )
    args = parser.parse_args()

    story_path = args.story.expanduser().resolve()
    ledger_path = args.ledger.expanduser().resolve()
    project = story_path.parent.parent
    public = project / "public"
    story = read_json(story_path)
    ledger = read_json(ledger_path)
    errors: list[str] = []
    warnings: list[str] = []

    schema_version = story.get("schemaVersion", 1)
    if not isinstance(schema_version, int) or schema_version < 1:
        errors.append("schemaVersion must be a positive integer")
        schema_version = 1
    elif schema_version == 1:
        warnings.append(
            "legacy schema: aspect ratio, duration budget, motion curve, and "
            "publication-state fields are not fully enforced"
        )

    fps = story.get("fps")
    width = story.get("width")
    height = story.get("height")
    total = story.get("totalFrames")
    scenes = story.get("scenes")
    if fps not in {24, 25, 30, 50, 60}:
        errors.append(f"fps must be a standard delivery rate, got {fps!r}")
    if not isinstance(width, int) or width <= 0:
        errors.append("width must be a positive integer")
    if not isinstance(height, int) or height <= 0:
        errors.append("height must be a positive integer")
    if not isinstance(total, int) or total <= 0:
        errors.append("totalFrames must be a positive integer")

    aspect_ratio = story.get("aspectRatio")
    if schema_version >= 2 and aspect_ratio not in ASPECT_RATIOS:
        errors.append("version-2 story requires aspectRatio: 16:9, 9:16, 1:1, or 4:5")
    elif aspect_ratio in ASPECT_RATIOS and isinstance(width, int) and isinstance(height, int) and height > 0:
        if abs(width / height - ASPECT_RATIOS[aspect_ratio]) > 0.01:
            errors.append(
                f"aspectRatio {aspect_ratio} does not match dimensions {width}x{height}"
            )

    target_duration = story.get("targetDurationSeconds")
    duration_tolerance = story.get("durationToleranceSeconds")
    if schema_version >= 2:
        if not isinstance(target_duration, (int, float)) or target_duration <= 0:
            errors.append("version-2 story requires positive targetDurationSeconds")
        if not isinstance(duration_tolerance, (int, float)) or duration_tolerance < 0:
            errors.append("version-2 story requires non-negative durationToleranceSeconds")
    if (
        isinstance(fps, int)
        and fps > 0
        and isinstance(total, int)
        and total > 0
        and isinstance(target_duration, (int, float))
        and isinstance(duration_tolerance, (int, float))
        and duration_tolerance >= 0
    ):
        timeline_duration = total / fps
        delta = abs(timeline_duration - float(target_duration))
        if delta > float(duration_tolerance):
            errors.append(
                "timeline duration "
                f"{timeline_duration:.2f}s misses target {float(target_duration):.2f}s "
                f"by {delta:.2f}s (tolerance {float(duration_tolerance):.2f}s)"
            )
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes must be a non-empty array")
        scenes = []
    elif scenes[0].get("from") != 0:
        errors.append("first scene must start at frame 0")
    elif scenes[0].get("coverFrame") is not True:
        errors.append("first scene must set coverFrame: true")
    elif scenes[0].get("openingMotion") != "cover-impact":
        errors.append("first scene must set openingMotion: 'cover-impact'")
    elif len(str(scenes[0].get("headline", "")).replace(" ", "")) > 16:
        warnings.append("opening headline may be too long for a cover")

    ledger_items = ledger.get("assets", [])
    ledger_by_path = {item.get("localPath"): item for item in ledger_items if isinstance(item, dict)}
    checked_ledger_assets: set[str] = set()
    ids: set[str] = set()
    previous_end = 0
    energies: list[int] = []

    for index, scene in enumerate(scenes):
        missing = sorted(REQUIRED - set(scene))
        if missing:
            errors.append(f"scene[{index}] missing fields: {', '.join(missing)}")
            continue
        if schema_version >= 2:
            director_missing = sorted(REQUIRED_V2 - set(scene))
            if director_missing:
                errors.append(
                    f"scene[{index}] missing version-2 director fields: "
                    f"{', '.join(director_missing)}"
                )
        scene_id = str(scene["id"])
        if scene_id in ids:
            errors.append(f"duplicate scene id: {scene_id}")
        ids.add(scene_id)

        start = scene["from"]
        duration = scene["duration"]
        if not isinstance(start, int) or start < 0:
            errors.append(f"{scene_id}: from must be a non-negative integer")
            continue
        if not isinstance(duration, int) or duration <= 0:
            errors.append(f"{scene_id}: duration must be a positive integer")
            continue
        end = start + duration
        if isinstance(total, int) and end > total:
            errors.append(f"{scene_id}: ends at {end}, beyond totalFrames {total}")
        if index > 0:
            overlap = previous_end - start
            if overlap < -6:
                errors.append(f"{scene_id}: timing gap is {-overlap} frames")
            elif overlap > 24:
                warnings.append(f"{scene_id}: transition overlap is {overlap} frames")
        previous_end = end

        if scene["layout"] not in LAYOUTS:
            errors.append(f"{scene_id}: unsupported layout {scene['layout']!r}")
        if scene["accent"] not in ACCENTS:
            errors.append(f"{scene_id}: accent must be red, teal, or yellow")
        if schema_version >= 2:
            if not isinstance(scene.get("emotion"), str) or not scene.get("emotion", "").strip():
                errors.append(f"{scene_id}: emotion must be a non-empty string")
            energy = scene.get("energy")
            if not isinstance(energy, int) or isinstance(energy, bool) or energy not in range(1, 6):
                errors.append(f"{scene_id}: energy must be an integer from 1 to 5")
            else:
                energies.append(energy)
            if scene.get("motionBudget") not in MOTION_BUDGETS:
                errors.append(f"{scene_id}: motionBudget must be low, medium, or high")
            reading_window = scene.get("readingWindowFrames")
            if not isinstance(reading_window, int) or isinstance(reading_window, bool) or reading_window <= 0:
                errors.append(f"{scene_id}: readingWindowFrames must be a positive integer")
            elif reading_window > duration:
                errors.append(f"{scene_id}: readingWindowFrames exceeds scene duration")
            if scene.get("focalAnchor") not in FOCAL_ANCHORS:
                errors.append(f"{scene_id}: unsupported focalAnchor {scene.get('focalAnchor')!r}")
        for type_key in ("primaryType", "secondaryType"):
            if scene.get(type_key, "image") not in {"image", "video"}:
                errors.append(f"{scene_id}: {type_key} must be image or video")
        for start_key in ("primaryStartFrom", "secondaryStartFrom"):
            if start_key in scene:
                value = scene[start_key]
                if not isinstance(value, int) or value < 0:
                    errors.append(f"{scene_id}: {start_key} must be a non-negative integer")
        if scene.get("cutoutOutline") not in {None, True, False}:
            errors.append(f"{scene_id}: cutoutOutline must be boolean")
        if scene.get("cutoutOutlineColor") not in {None, *ACCENTS}:
            errors.append(f"{scene_id}: cutoutOutlineColor must be red, teal, or yellow")

        subject_type = scene.get("subjectType")
        if subject_type is not None:
            if subject_type not in SUBJECT_TYPES:
                errors.append(f"{scene_id}: unsupported subjectType {subject_type!r}")
            if not scene.get("subjectName"):
                errors.append(f"{scene_id}: subjectName is required when subjectType is set")
            if scene.get("evidenceRole") not in EVIDENCE_ROLES:
                errors.append(f"{scene_id}: evidenceRole must be direct, context, or illustrative")
            if subject_type == "person" and not scene.get("cutout"):
                warnings.append(f"{scene_id}: named person has no cutout")
            if subject_type == "event" and "video" not in {
                scene.get("primaryType", "image"),
                scene.get("secondaryType", "image"),
            }:
                warnings.append(f"{scene_id}: named event has no direct video; verify the fallback")
        if len(str(scene["headline"]).replace(" ", "")) > 20:
            warnings.append(f"{scene_id}: headline may be too long")
        if len(str(scene["caption"]).replace(" ", "")) > 28:
            warnings.append(f"{scene_id}: caption may overflow one line")

        asset_keys = ["primary", "secondary"]
        if scene.get("cutout"):
            asset_keys.append("cutout")
        for key in asset_keys:
            asset = str(scene[key])
            if urlparse(asset).scheme:
                errors.append(f"{scene_id}: {key} must be project-local, got URL")
                continue
            if not (public / asset).is_file():
                errors.append(f"{scene_id}: missing public/{asset}")
            item = ledger_by_path.get(asset)
            if not item:
                errors.append(f"{scene_id}: public/{asset} has no ledger entry")
            elif asset not in checked_ledger_assets:
                checked_ledger_assets.add(asset)
                for field in ("sourceUrl", "license", "attribution", "factualRole"):
                    if not item.get(field):
                        errors.append(f"ledger {asset}: missing {field}")

                if schema_version >= 2:
                    for field in (
                        "ingestStatus",
                        "publicationStatus",
                        "usageScope",
                        "replacementRequiredBeforePublish",
                    ):
                        if field not in item or item.get(field) in {None, ""}:
                            errors.append(f"ledger {asset}: missing {field}")

                    ingest_status = item.get("ingestStatus")
                    if ingest_status not in INGEST_STATUSES:
                        errors.append(
                            f"ledger {asset}: ingestStatus must be approved or blocked"
                        )
                    elif ingest_status != "approved":
                        errors.append(f"ledger {asset}: ingestStatus is not approved")

                    publication_raw = item.get("publicationStatus")
                    publication_status = PUBLICATION_ALIASES.get(
                        publication_raw, publication_raw
                    )
                    if publication_raw in PUBLICATION_ALIASES:
                        warnings.append(
                            f"ledger {asset}: normalize publicationStatus "
                            f"{publication_raw!r} to {publication_status!r}"
                        )
                    if publication_status not in PUBLICATION_STATUSES:
                        errors.append(
                            f"ledger {asset}: unsupported publicationStatus "
                            f"{publication_raw!r}"
                        )

                    replacement_required = item.get("replacementRequiredBeforePublish")
                    if not isinstance(replacement_required, bool):
                        errors.append(
                            f"ledger {asset}: replacementRequiredBeforePublish "
                            "must be boolean"
                        )
                    if publication_status in {
                        "editorial_preview_only",
                        "unknown",
                        "blocked",
                    } and replacement_required is not True:
                        errors.append(
                            f"ledger {asset}: {publication_status} requires "
                            "replacementRequiredBeforePublish: true"
                        )
                else:
                    ingest_status = item.get("ingestStatus", item.get("status"))
                    if not ingest_status:
                        errors.append(
                            f"ledger {asset}: missing legacy status or ingestStatus"
                        )
                    elif ingest_status != "approved":
                        errors.append(f"ledger {asset}: edit status is not approved")
                    publication_raw = item.get("publicationStatus")
                    publication_status = PUBLICATION_ALIASES.get(
                        publication_raw, publication_raw
                    )
                    replacement_required = item.get(
                        "replacementRequiredBeforePublish", False
                    )

                if args.publication:
                    if publication_status not in PUBLISHABLE_STATUSES:
                        errors.append(
                            f"ledger {asset}: publication blocked by "
                            f"publicationStatus {publication_raw!r}"
                        )
                    if replacement_required is True:
                        errors.append(
                            f"ledger {asset}: replacement is required before publication"
                        )
                elif publication_status not in {None, *PUBLISHABLE_STATUSES}:
                    warnings.append(
                        f"ledger {asset}: local edit allowed, but publication is "
                        f"not cleared ({publication_raw!r})"
                    )

        if scene.get("cutout"):
            cutout_suffix = Path(str(scene["cutout"])).suffix.lower()
            if cutout_suffix not in {".png", ".webp", ".svg"}:
                errors.append(f"{scene_id}: cutout must be PNG, WebP, or SVG with transparency")
            cutout_item = ledger_by_path.get(str(scene["cutout"]))
            background_items = [
                ledger_by_path.get(str(scene.get("primary"))),
                ledger_by_path.get(str(scene.get("secondary"))),
            ]
            background_ids = {
                item.get("id")
                for item in background_items
                if isinstance(item, dict) and item.get("id")
            }
            if (
                isinstance(cutout_item, dict)
                and cutout_item.get("derivativeOf") in background_ids
            ):
                warnings.append(
                    f"{scene_id}: cutout derives from a displayed background asset; "
                    "check for accidental duplicate-subject collision"
                )

    if scenes and isinstance(total, int) and previous_end != total:
        errors.append(f"last scene ends at {previous_end}; expected totalFrames {total}")

    if schema_version >= 2 and len(energies) >= 4:
        if len(set(energies)) == 1:
            warnings.append("all scene energy scores are identical; design a visible curve")
        if min(energies) >= 3:
            warnings.append("energy curve has no low-energy reading or reflection beat")
        high_run = 0
        longest_high_run = 0
        for energy in energies:
            high_run = high_run + 1 if energy >= 4 else 0
            longest_high_run = max(longest_high_run, high_run)
        if longest_high_run >= 4:
            warnings.append(
                f"energy curve contains {longest_high_run} consecutive high-energy beats"
            )

    audio = story.get("audio")
    if audio:
        audio_path = public / audio
        if not audio_path.is_file():
            errors.append(f"missing public/{audio}")
        elif (
            audio_path.suffix.lower() == ".wav"
            and isinstance(fps, int)
            and fps > 0
            and isinstance(total, int)
            and total > 0
        ):
            try:
                with wave.open(str(audio_path), "rb") as wav:
                    audio_duration = wav.getnframes() / wav.getframerate()
                timeline_duration = total / fps
                audio_delta = abs(timeline_duration - audio_duration)
                if audio_delta > 0.75:
                    message = (
                        f"narration duration {audio_duration:.2f}s and timeline "
                        f"{timeline_duration:.2f}s differ by {audio_delta:.2f}s"
                    )
                    if schema_version >= 2:
                        errors.append(message)
                    else:
                        warnings.append(message)
            except (wave.Error, ZeroDivisionError) as exc:
                warnings.append(f"could not measure WAV duration for public/{audio}: {exc}")

    for message in warnings:
        print(f"WARN: {message}")
    for message in errors:
        print(f"ERROR: {message}")
    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"OK: {len(scenes)} scene(s), {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
