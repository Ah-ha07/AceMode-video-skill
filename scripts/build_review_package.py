#!/usr/bin/env python3
"""Render a compact pre-approval package without rendering the full timeline."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None
    import msvcrt


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


def run(command: list[str], cwd: Path, verbose: bool = False) -> None:
    options = {"cwd": cwd, "check": False, "text": True, "capture_output": not verbose}
    if Path(command[0]).name == "remotion":
        with browser_lock(cwd):
            completed = subprocess.run(command, **options)
    else:
        completed = subprocess.run(command, **options)
    if completed.returncode != 0:
        raise SystemExit(
            f"Command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout or ''}{completed.stderr or ''}"
        )


@contextmanager
def browser_lock(project: Path) -> Iterator[None]:
    lock_path = project / "qa" / ".remotion-browser.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w+b") as stream:
        if fcntl is not None:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield
            return
        stream.write(b"0")
        stream.flush()
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def remotion_command(project: Path) -> list[str]:
    local = project / "node_modules" / ".bin" / "remotion"
    if local.is_file():
        return [str(local)]
    raise SystemExit("Local Remotion CLI not found; run npm ci in the video project first")


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
    parser.add_argument(
        "--browser-executable",
        help="Use an existing Chrome/Chromium executable instead of downloading one",
    )
    parser.add_argument(
        "--chrome-mode",
        choices=("headless-shell", "chrome-for-testing"),
        help=(
            "Remotion browser mode. Defaults to chrome-for-testing when "
            "--browser-executable is provided"
        ),
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Opening-preview render concurrency (default: 1)",
    )
    parser.add_argument("--verbose", action="store_true")
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
    if args.concurrency < 1:
        raise SystemExit("--concurrency must be at least 1")

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
    browser_args = (
        ["--browser-executable", args.browser_executable]
        if args.browser_executable
        else []
    )
    chrome_mode = args.chrome_mode or (
        "chrome-for-testing" if args.browser_executable else None
    )
    if chrome_mode:
        browser_args += ["--chrome-mode", chrome_mode]
    log_args = [] if args.verbose else ["--log=error"]

    run(
        remotion
        + [
            "still",
            args.entry,
            args.composition,
            str(cover),
            "--frame",
            "0",
        ]
        + browser_args
        + log_args,
        project,
        args.verbose,
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
                "--concurrency",
                str(args.concurrency),
            ]
            + browser_args
            + log_args,
            project,
            args.verbose,
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
            ]
            + browser_args
            + log_args,
            project,
            args.verbose,
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
            "-loglevel",
            "error",
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
        args.verbose,
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
