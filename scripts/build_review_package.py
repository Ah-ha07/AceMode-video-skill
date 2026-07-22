#!/usr/bin/env python3
"""Render a compact pre-approval package without rendering the full timeline."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path


PUBLISHABLE = {
    "cleared",
    "attribution_required",
    "approved_with_attribution",
}


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read JSON {path}: {exc}") from exc


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def remotion_command(project: Path) -> list[str]:
    local = project / "node_modules" / ".bin" / "remotion"
    if local.is_file():
        return [str(local)]
    if shutil.which("npx"):
        return ["npx", "remotion"]
    raise SystemExit("Remotion CLI not found; install project dependencies first")


def representative_frames(story: dict, maximum_scene_frames: int) -> list[int]:
    total = int(story["totalFrames"])
    opening = [0, 8, 18, 45, 90]
    scenes = story.get("scenes", [])
    if len(scenes) > maximum_scene_frames:
        selected_indices = {
            round(index * (len(scenes) - 1) / (maximum_scene_frames - 1))
            for index in range(maximum_scene_frames)
        }
        selected = [scenes[index] for index in sorted(selected_indices)]
    else:
        selected = scenes

    scene_frames = [
        int(scene["from"]) + max(0, int(scene["duration"]) // 2)
        for scene in selected
        if isinstance(scene, dict)
        and isinstance(scene.get("from"), int)
        and isinstance(scene.get("duration"), int)
    ]
    candidates = opening + scene_frames + [total - 1]
    return sorted({min(max(frame, 0), total - 1) for frame in candidates})


def rights_blockers(ledger: dict) -> list[dict]:
    blockers: list[dict] = []
    for item in ledger.get("assets", []):
        if not isinstance(item, dict):
            continue
        publication = item.get("publicationStatus")
        replacement = item.get("replacementRequiredBeforePublish")
        if publication not in PUBLISHABLE or replacement is True:
            blockers.append(
                {
                    "id": item.get("id"),
                    "localPath": item.get("localPath"),
                    "publicationStatus": publication or "missing",
                    "replacementRequiredBeforePublish": replacement,
                }
            )
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--entry", default="src/index.jsx")
    parser.add_argument("--composition", default="EditorialDocumentary")
    parser.add_argument("--story", default="src/story.json")
    parser.add_argument("--ledger", default="source-ledger.json")
    parser.add_argument("--suffix", default="")
    parser.add_argument("--max-scene-frames", type=int, default=10)
    parser.add_argument("--review-scale", type=float, default=0.5)
    parser.add_argument("--skip-opening-video", action="store_true")
    args = parser.parse_args()

    project = args.project.expanduser().resolve()
    story_path = project / args.story
    ledger_path = project / args.ledger
    story = read_json(story_path)
    ledger = read_json(ledger_path)
    total = story.get("totalFrames")
    fps = story.get("fps")
    width = story.get("width")
    height = story.get("height")
    if not all(isinstance(value, int) and value > 0 for value in (total, fps, width, height)):
        raise SystemExit("Story requires positive integer totalFrames, fps, width, and height")
    if args.max_scene_frames < 2:
        raise SystemExit("--max-scene-frames must be at least 2")
    if not 0.1 <= args.review_scale <= 1:
        raise SystemExit("--review-scale must be between 0.1 and 1")

    suffix = f"-{args.suffix.strip('-')}" if args.suffix.strip("-") else ""
    qa = project / "qa"
    frames_dir = qa / f"review-frames{suffix}"
    qa.mkdir(exist_ok=True)
    frames_dir.mkdir(exist_ok=True)

    cover = qa / f"cover-frame{suffix}.png"
    opening = qa / f"opening-preview{suffix}.mp4"
    board = qa / f"review-board{suffix}.png"
    manifest = qa / f"review-package{suffix}.json"
    remotion = remotion_command(project)

    run(
        remotion
        + [
            "still",
            args.entry,
            args.composition,
            str(cover),
            "--frame",
            "0",
        ],
        project,
    )

    opening_end = min(total - 1, max(0, int(round(fps * 3)) - 1))
    if not args.skip_opening_video:
        run(
            remotion
            + [
                "render",
                args.entry,
                args.composition,
                str(opening),
                "--frames",
                f"0-{opening_end}",
                "--codec",
                "h264",
                "--crf",
                "22",
                "--scale",
                str(args.review_scale),
            ],
            project,
        )

    frames = representative_frames(story, args.max_scene_frames)
    for index, frame in enumerate(frames):
        output = frames_dir / f"frame-{index:02d}.png"
        run(
            remotion
            + [
                "still",
                args.entry,
                args.composition,
                str(output),
                "--frame",
                str(frame),
                "--scale",
                str(args.review_scale),
            ],
            project,
        )

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required to assemble the review board")
    columns = 4 if width >= height else 5
    rows = math.ceil(len(frames) / columns)
    cell_width = 480 if width >= height else 270
    tile_filter = (
        f"scale={cell_width}:-2,"
        f"tile={columns}x{rows}:nb_frames={len(frames)}:"
        "padding=12:margin=12:color=white"
    )
    run(
        [
            ffmpeg,
            "-y",
            "-framerate",
            "1",
            "-start_number",
            "0",
            "-i",
            str(frames_dir / "frame-%02d.png"),
            "-vf",
            tile_filter,
            "-frames:v",
            "1",
            "-update",
            "1",
            str(board),
        ],
        project,
    )

    package = {
        "composition": args.composition,
        "story": args.story,
        "aspectRatio": story.get("aspectRatio"),
        "dimensions": {"width": width, "height": height},
        "timelineDurationSeconds": round(total / fps, 3),
        "targetDurationSeconds": story.get("targetDurationSeconds"),
        "durationToleranceSeconds": story.get("durationToleranceSeconds"),
        "cover": str(cover.relative_to(project)),
        "openingPreview": (
            None if args.skip_opening_video else str(opening.relative_to(project))
        ),
        "reviewBoard": str(board.relative_to(project)),
        "reviewFrames": frames,
        "publicationBlockers": rights_blockers(ledger),
    }
    manifest.write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
