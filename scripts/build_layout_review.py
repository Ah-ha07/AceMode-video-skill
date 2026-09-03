#!/usr/bin/env python3
"""Render and approve native-resolution layout checkpoints for every scene."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None
    import msvcrt


def read_json(path: Path) -> dict:
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


def source_tree_sha256(path: Path) -> str:
    records = [
        f"{item.relative_to(path).as_posix()}:{sha256(item)}"
        for item in sorted(value for value in path.rglob("*") if value.is_file())
    ]
    return hashlib.sha256("\n".join(records).encode("utf-8")).hexdigest()


def run(command: list[str], cwd: Path, verbose: bool) -> None:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        capture_output=not verbose,
    )
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


def scene_checkpoints(scene: dict) -> list[tuple[int, str]]:
    start = int(scene["from"])
    duration = int(scene["duration"])
    end = start + duration - 1
    return [
        (min(end, start + 12), "early-settled"),
        (min(end, start + duration // 2), "midpoint"),
        (end, "late-settled"),
    ]


def scene_for_frame(scenes: list[dict], frame: int) -> dict | None:
    for scene in scenes:
        start = int(scene["from"])
        if start <= frame < start + int(scene["duration"]):
            return scene
    return None


def validate_layout_manifest(
    value: dict,
    story: dict | None = None,
    project: Path | None = None,
    require_approval: bool = True,
) -> list[str]:
    errors: list[str] = []
    if value.get("schema_version") != 1:
        errors.append("layout review must use schema version 1")
    allowed_statuses = {"passed"} if require_approval else {"ready", "passed"}
    if value.get("status") not in allowed_statuses:
        errors.append(
            "layout review must be explicitly approved"
            if require_approval
            else "layout review status must be ready or passed"
        )
    if require_approval:
        for key in ("reviewer", "reviewed_at", "review_receipt"):
            if not str(value.get(key) or "").strip():
                errors.append(f"approved layout review requires {key}")

    frames = value.get("frames")
    if not isinstance(frames, list) or not frames:
        errors.append("layout review requires native-resolution frames")
        frames = []
    for index, item in enumerate(frames):
        if not isinstance(item, dict):
            errors.append(f"layout frame[{index}] must be an object")
            continue
        for key in ("scene_id", "frame", "path", "sha256"):
            if item.get(key) in (None, ""):
                errors.append(f"layout frame[{index}] requires {key}")
        if project and item.get("path"):
            path = (project / str(item["path"])).resolve()
            if not path.is_file():
                errors.append(f"missing layout frame: {path}")
            elif item.get("sha256") != sha256(path):
                errors.append(f"layout frame hash mismatch: {path}")

    if story:
        by_scene: dict[str, set[int]] = {}
        for item in frames:
            if isinstance(item, dict):
                by_scene.setdefault(str(item.get("scene_id") or ""), set()).add(int(item.get("frame") or 0))
        for scene in story.get("scenes") or []:
            scene_id = str(scene.get("id") or "")
            if len(by_scene.get(scene_id, set())) < 3:
                errors.append(f"layout review requires three distinct frames for scene {scene_id}")
        included = {int(item.get("frame") or 0) for item in frames if isinstance(item, dict)}
        for frame in story.get("layoutCheckFrames") or []:
            if int(frame) not in included:
                errors.append(f"layout review is missing explicit checkpoint frame {frame}")

    if project:
        source_dir = project / str(value.get("source_tree") or "src")
        if not source_dir.is_dir():
            errors.append(f"missing Remotion source tree: {source_dir}")
        elif value.get("source_tree_sha256") != source_tree_sha256(source_dir):
            errors.append("layout review does not match the current Remotion source tree")

    board = str(value.get("board") or "").strip()
    if not board:
        errors.append("layout review requires board path")
    elif project:
        board_path = (project / board).resolve()
        if not board_path.is_file():
            errors.append(f"missing layout board: {board_path}")
        elif value.get("board_sha256") != sha256(board_path):
            errors.append(f"layout board hash mismatch: {board_path}")
    return errors


def approve_manifest(manifest: Path, receipt: str, reviewer: str) -> None:
    value = read_json(manifest)
    if value.get("status") != "ready":
        raise SystemExit("Only a ready layout review can be approved")
    project = manifest.parent.parent
    story = read_json(project / str(value.get("story") or "src/story.json"))
    value["status"] = "passed"
    value["reviewer"] = reviewer
    value["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    value["review_receipt"] = receipt
    errors = validate_layout_manifest(value, story, project)
    if errors:
        raise SystemExit("Invalid layout review approval: " + "; ".join(errors))
    manifest.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, nargs="?")
    parser.add_argument("--story", default="src/story.json")
    parser.add_argument("--entry", default="src/index.jsx")
    parser.add_argument("--composition")
    parser.add_argument("--suffix", default="")
    parser.add_argument("--browser-executable")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--approve-manifest", type=Path)
    parser.add_argument("--review-receipt")
    parser.add_argument("--reviewer", default="user")
    args = parser.parse_args()

    if args.approve_manifest:
        if args.project or args.composition:
            raise SystemExit("Do not supply project/composition when approving a layout manifest")
        if not str(args.review_receipt or "").strip():
            raise SystemExit("--review-receipt is required when approving a layout manifest")
        manifest = args.approve_manifest.expanduser().resolve()
        approve_manifest(manifest, args.review_receipt, args.reviewer)
        print(manifest)
        return 0

    if not args.project or not args.composition:
        raise SystemExit("project and --composition are required when building a layout review")
    project = args.project.expanduser().resolve()
    story_path = project / args.story
    story = read_json(story_path)
    scenes = story.get("scenes") or []
    if not scenes:
        raise SystemExit("layout review requires at least one scene")
    local = project / "node_modules" / ".bin" / "remotion"
    if not local.is_file():
        raise SystemExit("Local Remotion CLI not found; run npm ci first")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required")

    total = int(story["totalFrames"])
    suffix = f"-{args.suffix.strip('-')}" if args.suffix.strip("-") else ""
    output_dir = project / "qa" / f"layout-frames{suffix}"
    output_dir.mkdir(parents=True, exist_ok=True)
    browser = ["--browser-executable", args.browser_executable, "--chrome-mode", "chrome-for-testing"] if args.browser_executable else []
    quiet = [] if args.verbose else ["--log=error"]

    selected: dict[int, dict] = {}
    for scene in scenes:
        for frame, reason in scene_checkpoints(scene):
            selected[frame] = {"scene": scene, "reason": reason}
    for raw_frame in story.get("layoutCheckFrames") or []:
        frame = min(max(int(raw_frame), 0), total - 1)
        scene = scene_for_frame(scenes, frame)
        if scene:
            selected[frame] = {"scene": scene, "reason": "explicit-checkpoint"}

    frames: list[dict] = []
    with browser_lock(project):
        for index, (frame, selection) in enumerate(sorted(selected.items())):
            scene = selection["scene"]
            scene_id = str(scene["id"])
            output = output_dir / f"{index:02d}-{scene_id}-f{frame:04d}.png"
            command = [str(local), "still", args.entry, args.composition, str(output), "--frame", str(frame), *browser, *quiet]
            run(command, project, args.verbose)
            frames.append(
                {
                    "scene_id": scene_id,
                    "frame": frame,
                    "reason": selection["reason"],
                    "path": str(output.relative_to(project)),
                    "sha256": sha256(output),
                    "required_landmarks": scene.get("layoutRequiredLandmarks") or [],
                }
            )

    board = project / "qa" / f"layout-board{suffix}.png"
    columns = 5 if int(story["width"]) < int(story["height"]) else 4
    rows = math.ceil(len(frames) / columns)
    cell_width = 270 if columns == 5 else 480
    run(
        [
            ffmpeg, "-loglevel", "error", "-y", "-framerate", "1", "-pattern_type", "glob",
            "-i", str(output_dir / "*.png"),
            "-vf", f"scale={cell_width}:-2,tile={columns}x{rows}:nb_frames={len(frames)}:padding=10:margin=10:color=white",
            "-frames:v", "1", "-update", "1", str(board),
        ],
        project,
        args.verbose,
    )

    value = {
        "schema_version": 1,
        "status": "ready",
        "composition": args.composition,
        "story": args.story,
        "story_sha256": sha256(story_path),
        "source_tree": "src",
        "source_tree_sha256": source_tree_sha256(project / "src"),
        "aspect_ratio": story.get("aspectRatio"),
        "native_frame_resolution": {"width": story.get("width"), "height": story.get("height")},
        "frames": frames,
        "board": str(board.relative_to(project)),
        "board_sha256": sha256(board),
        "required_checks": [
            "visual meaning matches the narration at that frame",
            "headline, labels, and evidence are readable on the target device",
            "evidence crops retain every declared landmark",
            "captions, safe zones, brand marks, and focal content do not overlap",
        ],
        "review_required": "Open the native PNGs, not only the scaled board. Presence is not readability.",
    }
    errors = validate_layout_manifest(value, story, project, require_approval=False)
    if errors:
        raise SystemExit("Invalid layout review: " + "; ".join(errors))
    manifest = project / "qa" / f"layout-review{suffix}.json"
    manifest.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
