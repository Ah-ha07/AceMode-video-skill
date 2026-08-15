#!/usr/bin/env python3
"""Run publication, decode, media, and signed visual-review checks for a final video."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VISUAL_CHECKS = (
    "opening_reviewed",
    "transitions_reviewed",
    "final_frame_reviewed",
    "captions_reviewed",
    "caption_timing_reviewed",
    "audio_gaps_reviewed",
    "transition_midpoints_reviewed",
    "safe_areas_reviewed",
    "rights_attributions_reviewed",
)


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


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def loudness_measurement(ffmpeg: str, video: Path) -> dict[str, Any]:
    result = run(
        [ffmpeg, "-hide_banner", "-nostats", "-i", str(video), "-af", "loudnorm=print_format=json", "-f", "null", "-"]
    )
    matches = re.findall(r"\{[^{]*\"input_i\"[\s\S]*?\}", result.stderr)
    if not matches:
        return {"status": "unavailable", "diagnostic": result.stderr[-500:]}
    try:
        return {"status": "measured", **json.loads(matches[-1])}
    except json.JSONDecodeError:
        return {"status": "unavailable", "diagnostic": matches[-1][-500:]}


def detect_ranges(ffmpeg: str, video: Path, filter_value: str, pattern: str) -> list[dict[str, float]]:
    result = run([ffmpeg, "-hide_banner", "-nostats", "-i", str(video), "-vf" if "blackdetect" in filter_value else "-af", filter_value, "-f", "null", "-"])
    ranges: list[dict[str, float]] = []
    for match in re.finditer(pattern, result.stderr, re.DOTALL):
        ranges.append({
            "start": round(float(match.group(1)), 3),
            "end": round(float(match.group(2)), 3),
            "duration": round(float(match.group(3)), 3),
        })
    return ranges


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("story", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--story-id", required=True)
    parser.add_argument("--visual-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scope", choices=("internal", "public"), default="public")
    args = parser.parse_args()

    video = args.video.expanduser().resolve()
    story_path = args.story.expanduser().resolve()
    ledger = args.ledger.expanduser().resolve()
    visual_path = args.visual_review.expanduser().resolve()
    output = args.output.expanduser().resolve()
    for path in (video, story_path, ledger, visual_path):
        if not path.is_file():
            raise SystemExit(f"Missing input: {path}")
    story = read_json(story_path)
    visual = read_json(visual_path)
    if visual.get("schema_version") != 1 or not str(visual.get("reviewer") or "").strip():
        raise SystemExit("Visual review requires schema_version: 1 and reviewer")
    if not str(visual.get("reviewed_at") or "").strip():
        raise SystemExit("Visual review requires reviewed_at")
    missing = [key for key in VISUAL_CHECKS if visual.get(key) is not True]
    if missing:
        raise SystemExit("Visual review has not passed: " + ", ".join(missing))

    skill_dir = Path(__file__).resolve().parent.parent
    edit_validation = run(
        [
            sys.executable,
            str(skill_dir / "scripts" / "validate_story.py"),
            str(story_path),
            str(ledger),
        ]
    )
    if edit_validation.returncode != 0:
        raise SystemExit("Edit validation failed:\n" + edit_validation.stdout + edit_validation.stderr)
    publication = run(
        [
            sys.executable,
            str(skill_dir / "scripts" / "validate_story.py"),
            str(story_path),
            str(ledger),
            "--publication",
        ]
    )
    if args.scope == "public" and publication.returncode != 0:
        raise SystemExit("Publication validation failed:\n" + publication.stdout + publication.stderr)

    ffprobe = shutil.which("ffprobe")
    ffmpeg = shutil.which("ffmpeg")
    if not ffprobe or not ffmpeg:
        raise SystemExit("ffprobe and ffmpeg are required")
    probe_result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(video),
        ]
    )
    if probe_result.returncode != 0:
        raise SystemExit("ffprobe failed:\n" + probe_result.stderr)
    probe = json.loads(probe_result.stdout)
    streams = probe.get("streams") or []
    video_stream = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if not video_stream or not audio_stream:
        raise SystemExit("Final delivery requires both video and audio streams")
    if video_stream.get("width") != story.get("width") or video_stream.get("height") != story.get("height"):
        raise SystemExit("Final video dimensions do not match story.json")
    duration = float((probe.get("format") or {}).get("duration") or 0)
    expected = float(story.get("totalFrames") or 0) / float(story.get("fps") or 1)
    if abs(duration - expected) > 1.0:
        raise SystemExit(f"Final duration {duration:.3f}s differs from story timeline {expected:.3f}s")

    decode = run([ffmpeg, "-v", "error", "-i", str(video), "-f", "null", "-"])
    if decode.returncode != 0:
        raise SystemExit("Full FFmpeg decode failed:\n" + decode.stderr)

    silence_ranges = detect_ranges(
        ffmpeg,
        video,
        "silencedetect=noise=-45dB:d=0.8",
        r"silence_start:\s*([0-9.]+).*?silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)",
    )
    black_ranges = detect_ranges(
        ffmpeg,
        video,
        "blackdetect=d=0.25:pix_th=0.10:pic_th=0.98",
        r"black_start:([0-9.]+)\s+black_end:([0-9.]+)\s+black_duration:([0-9.]+)",
    )
    loudness = loudness_measurement(ffmpeg, video)
    if any(item["duration"] >= max(0.5, duration - 0.25) for item in silence_ranges):
        raise SystemExit("Narration track appears silent throughout the final video")
    if loudness.get("status") == "measured":
        try:
            if float(loudness.get("input_i", "-inf")) < -55:
                raise SystemExit("Final audio is effectively silent")
        except (TypeError, ValueError):
            raise SystemExit("Could not interpret final integrated loudness")
    publication_status = "passed" if publication.returncode == 0 else "blocked"
    report = {
        "schema_version": 1,
        "status": "passed",
        "story_id": args.story_id,
        "delivery_scope": args.scope,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "final_video_path": str(video),
        "final_video_sha256": sha256(video),
        "story_sha256": sha256(story_path),
        "source_ledger_sha256": sha256(ledger),
        "edit_validation": "passed",
        "edit_validator_output": edit_validation.stdout.strip(),
        "publication_validation": publication_status,
        "publication_validator_output": (publication.stdout + publication.stderr).strip(),
        "full_decode": "passed",
        "media_probe": {
            "duration_seconds": duration,
            "video_codec": video_stream.get("codec_name"),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "audio_codec": audio_stream.get("codec_name"),
            "audio_sample_rate": audio_stream.get("sample_rate"),
        },
        "technical_measurements": {
            "silence_ranges_over_0_8s": silence_ranges,
            "black_ranges_over_0_25s": black_ranges,
            "integrated_loudness": loudness,
        },
        "visual_review": {key: visual[key] for key in VISUAL_CHECKS},
        "reviewer": visual["reviewer"],
        "reviewed_at": visual["reviewed_at"],
        "notes": visual.get("notes"),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
