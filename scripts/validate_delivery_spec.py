#!/usr/bin/env python3
"""Validate the locked delivery contract and its production artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ASPECTS = {"16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1.0, "4:5": 4 / 5}
SCOPES = {"internal", "public"}
TRANSITIONS = {"opaque-cut", "designed-overlap"}
PUBLISHABLE = {"cleared", "attribution_required", "approved_with_attribution"}


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"Expected a JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if spec.get("schema_version") != 1:
        errors.append("delivery spec requires schema_version: 1")
    if not str(spec.get("story_id") or "").strip():
        errors.append("delivery spec requires story_id")
    language = str(spec.get("language") or "")
    if not language or "-" not in language:
        errors.append("delivery spec requires a BCP-47 language such as en-US")
    target = spec.get("target_duration_seconds")
    if not isinstance(target, (int, float)) or isinstance(target, bool) or target <= 0:
        errors.append("delivery spec requires positive target_duration_seconds")
    if spec.get("delivery_scope") not in SCOPES:
        errors.append("delivery_scope must be internal or public")
    if spec.get("transition_mode") not in TRANSITIONS:
        errors.append("transition_mode must be opaque-cut or designed-overlap")

    profiles = spec.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        errors.append("delivery spec requires at least one profile")
        profiles = []
    ratios: set[str] = set()
    ids: set[str] = set()
    for index, profile in enumerate(profiles):
        if not isinstance(profile, dict):
            errors.append(f"profile[{index}] must be an object")
            continue
        profile_id = str(profile.get("id") or "")
        ratio = str(profile.get("aspect_ratio") or "")
        width = profile.get("width")
        height = profile.get("height")
        if not profile_id or profile_id in ids:
            errors.append(f"profile[{index}] requires a unique id")
        ids.add(profile_id)
        if ratio not in ASPECTS or ratio in ratios:
            errors.append(f"profile[{index}] requires a unique supported aspect_ratio")
        ratios.add(ratio)
        if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
            errors.append(f"profile[{index}] requires positive integer width and height")
        elif ratio in ASPECTS and abs(width / height - ASPECTS[ratio]) > 0.01:
            errors.append(f"profile[{index}] dimensions do not match {ratio}")
        if not str(profile.get("composition") or "").strip():
            errors.append(f"profile[{index}] requires composition")

    voice = spec.get("voice")
    if not isinstance(voice, dict):
        errors.append("delivery spec requires voice")
    else:
        for key in ("provider", "voice_id", "approval_basis", "approval_receipt"):
            if not str(voice.get(key) or "").strip():
                errors.append(f"voice.{key} is required")
        if voice.get("approval_basis") not in {"audition", "user-specified", "existing-approved"}:
            errors.append("voice.approval_basis is invalid")

    captions = spec.get("captions")
    if not isinstance(captions, dict) or captions.get("required") is not True:
        errors.append("captions.required must be true for narrated newsroom video")
    else:
        if captions.get("language") != language:
            errors.append("captions.language must match delivery language")
        if captions.get("timing_source") != "tts-manifest":
            errors.append("captions.timing_source must be tts-manifest")
        if captions.get("max_lines") not in {1, 2}:
            errors.append("captions.max_lines must be 1 or 2")

    brand = spec.get("brand")
    if not isinstance(brand, dict) or not isinstance(brand.get("enabled"), bool):
        errors.append("delivery spec requires brand.enabled boolean")
    elif brand.get("enabled"):
        if not str(brand.get("profile") or "").strip():
            errors.append("enabled brand requires profile")
        if not str(brand.get("approval_receipt") or "").strip():
            errors.append("enabled brand requires approval_receipt")
    if not str(spec.get("director_approval_receipt") or "").strip():
        errors.append("delivery spec requires director_approval_receipt")
    return errors


def validate_contract(
    spec_path: Path,
    story_paths: list[Path] | None = None,
    review_paths: list[Path] | None = None,
    voice_path: Path | None = None,
    caption_path: Path | None = None,
    ledger_path: Path | None = None,
    expected_story_id: str | None = None,
) -> tuple[list[str], list[str]]:
    spec_path = spec_path.expanduser().resolve()
    spec = read_json(spec_path)
    errors = validate_spec(spec)
    warnings: list[str] = []
    if expected_story_id and spec.get("story_id") != expected_story_id:
        errors.append("delivery spec belongs to another story")

    profiles = spec.get("profiles") if isinstance(spec.get("profiles"), list) else []
    by_ratio = {
        str(item.get("aspect_ratio")): item
        for item in profiles
        if isinstance(item, dict) and item.get("aspect_ratio")
    }
    seen_story_ratios: set[str] = set()
    for path in story_paths or []:
        story = read_json(path.expanduser().resolve())
        ratio = str(story.get("aspectRatio") or "")
        seen_story_ratios.add(ratio)
        profile = by_ratio.get(ratio)
        if not profile:
            errors.append(f"story ratio {ratio or '<missing>'} is not locked in delivery spec")
            continue
        if story.get("width") != profile.get("width") or story.get("height") != profile.get("height"):
            errors.append(f"story dimensions for {ratio} do not match delivery spec")
        if story.get("transitionMode", spec.get("transition_mode")) != spec.get("transition_mode"):
            errors.append(f"story transitionMode for {ratio} does not match delivery spec")
    if story_paths and seen_story_ratios != set(by_ratio):
        errors.append("registered render stories do not cover every delivery profile")

    review_ratios: set[str] = set()
    for path in review_paths or []:
        review = read_json(path.expanduser().resolve())
        ratio = str(review.get("aspectRatio") or "")
        review_ratios.add(ratio)
        profile = by_ratio.get(ratio)
        if not profile:
            errors.append(f"review ratio {ratio or '<missing>'} is not locked in delivery spec")
        elif review.get("composition") != profile.get("composition"):
            errors.append(f"review composition for {ratio} does not match delivery spec")
    if review_paths and review_ratios != set(by_ratio):
        errors.append("review packages do not cover every delivery profile")

    if voice_path:
        voice_path = voice_path.expanduser().resolve()
        voice = read_json(voice_path)
        configured = str((spec.get("voice") or {}).get("voice_id") or "")
        actual = str(voice.get("voiceId") or voice.get("voice_id") or "")
        configured_provider = str((spec.get("voice") or {}).get("provider") or "")
        actual_provider = str(voice.get("provider") or "")
        if not actual or actual != configured:
            errors.append("voice manifest voice ID does not match delivery spec")
        if not actual_provider or actual_provider != configured_provider:
            errors.append("voice manifest provider does not match delivery spec")
        duration = voice.get("duration")
        if isinstance(duration, (int, float)) and isinstance(spec.get("target_duration_seconds"), (int, float)):
            if abs(float(duration) - float(spec["target_duration_seconds"])) > 3:
                errors.append("measured voice duration misses the locked target by more than 3 seconds")

    if caption_path:
        caption_path = caption_path.expanduser().resolve()
        captions = read_json(caption_path)
        if captions.get("schema_version") != 1 or captions.get("timing_source") != "tts-manifest":
            errors.append("caption manifest must be schema version 1 and TTS-timed")
        if captions.get("language") != spec.get("language"):
            errors.append("caption manifest language does not match delivery spec")
        cues = captions.get("cues")
        if not isinstance(cues, list) or not cues:
            errors.append("caption manifest contains no cues")
        if voice_path and captions.get("source_voice_manifest_sha256") != sha256(voice_path):
            errors.append("caption manifest was not generated from the registered voice manifest")

    if ledger_path and spec.get("delivery_scope") == "public":
        ledger = read_json(ledger_path.expanduser().resolve())
        for asset in ledger.get("assets") or []:
            if not isinstance(asset, dict):
                continue
            if asset.get("publicationStatus") not in PUBLISHABLE or asset.get("replacementRequiredBeforePublish") is True:
                errors.append(f"public delivery is blocked by asset {asset.get('localPath') or asset.get('id')}")
    elif ledger_path and spec.get("delivery_scope") == "internal":
        ledger = read_json(ledger_path.expanduser().resolve())
        blocked = [
            asset for asset in ledger.get("assets") or []
            if isinstance(asset, dict)
            and (asset.get("publicationStatus") not in PUBLISHABLE or asset.get("replacementRequiredBeforePublish") is True)
        ]
        if blocked:
            warnings.append(f"internal delivery has {len(blocked)} publication blocker(s)")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--story-file", action="append", type=Path, default=[])
    parser.add_argument("--review-manifest", action="append", type=Path, default=[])
    parser.add_argument("--voice-manifest", type=Path)
    parser.add_argument("--caption-manifest", type=Path)
    parser.add_argument("--source-ledger", type=Path)
    parser.add_argument("--story-id")
    args = parser.parse_args()
    errors, warnings = validate_contract(
        args.spec,
        args.story_file,
        args.review_manifest,
        args.voice_manifest,
        args.caption_manifest,
        args.source_ledger,
        args.story_id,
    )
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"OK: {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
