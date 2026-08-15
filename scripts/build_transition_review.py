#!/usr/bin/env python3
"""Render before/cut/after frames for every Remotion scene boundary."""

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
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read JSON {path}: {exc}") from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def validate_transition_manifest(
    value: dict,
    story: dict | None = None,
    require_approval: bool = True,
) -> list[str]:
    errors: list[str] = []
    if value.get("schema_version") != 1:
        errors.append("transition review must use schema version 1")
    allowed_statuses = {"passed"} if require_approval else {"ready", "passed"}
    if value.get("status") not in allowed_statuses:
        errors.append(
            "transition review must be explicitly approved"
            if require_approval
            else "transition review status must be ready or passed"
        )
    if require_approval:
        for key in ("reviewer", "reviewed_at", "review_receipt"):
            if not str(value.get(key) or "").strip():
                errors.append(f"approved transition review requires {key}")
    boundaries = value.get("boundaries")
    if not isinstance(boundaries, list):
        errors.append("transition review requires boundaries")
        boundaries = []
    for index, item in enumerate(boundaries):
        if not isinstance(item, dict) or len(item.get("frames") or []) != 3:
            errors.append(f"transition boundary[{index}] requires before/cut/after frames")
    if story:
        expected = max(0, len(story.get("scenes") or []) - 1)
        if len(boundaries) != expected:
            errors.append(f"transition review covers {len(boundaries)} boundaries; expected {expected}")
    if not str(value.get("board") or "").strip():
        errors.append("transition review requires board path")
    return errors


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
            raise SystemExit("Do not supply project/composition when approving a transition manifest")
        if not str(args.review_receipt or "").strip():
            raise SystemExit("--review-receipt is required when approving a transition manifest")
        manifest = args.approve_manifest.expanduser().resolve()
        value = read_json(manifest)
        if value.get("status") != "ready":
            raise SystemExit("Only a ready transition review can be approved")
        value["status"] = "passed"
        value["reviewer"] = args.reviewer
        value["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        value["review_receipt"] = args.review_receipt
        errors = validate_transition_manifest(value)
        if errors:
            raise SystemExit("Invalid transition review approval: " + "; ".join(errors))
        manifest.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(manifest)
        return 0
    if not args.project or not args.composition:
        raise SystemExit("project and --composition are required when building a transition review")
    project = args.project.expanduser().resolve()
    story_path = project / args.story
    story = read_json(story_path)
    scenes = story.get("scenes") or []
    if len(scenes) < 2:
        raise SystemExit("transition review requires at least two scenes")
    local = project / "node_modules" / ".bin" / "remotion"
    if not local.is_file():
        raise SystemExit("Local Remotion CLI not found; run npm ci first")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required")
    suffix = f"-{args.suffix.strip('-')}" if args.suffix.strip("-") else ""
    output_dir = project / "qa" / f"transition-frames{suffix}"
    output_dir.mkdir(parents=True, exist_ok=True)
    browser = ["--browser-executable", args.browser_executable, "--chrome-mode", "chrome-for-testing"] if args.browser_executable else []
    quiet = [] if args.verbose else ["--log=error"]
    boundaries: list[dict] = []
    with browser_lock(project):
        for index, scene in enumerate(scenes[1:], start=1):
            frame = int(scene["from"])
            selected = [max(0, frame - 1), frame, min(int(story["totalFrames"]) - 1, frame + 1)]
            outputs: list[str] = []
            for slot, selected_frame in enumerate(selected):
                output = output_dir / f"boundary-{index:02d}-{slot}.png"
                command = [str(local), "still", args.entry, args.composition, str(output), "--frame", str(selected_frame), *browser, *quiet]
                run(command, project, args.verbose)
                outputs.append(str(output.relative_to(project)))
            boundaries.append({"from_scene": scenes[index - 1]["id"], "to_scene": scene["id"], "cut_frame": frame, "frames": outputs})
    board = project / "qa" / f"transition-board{suffix}.png"
    columns = 3
    rows = math.ceil(len(boundaries) * 3 / columns)
    run(
        [ffmpeg, "-loglevel", "error", "-y", "-framerate", "1", "-start_number", "0", "-pattern_type", "glob", "-i", str(output_dir / "*.png"), "-vf", f"scale=270:-2,tile={columns}x{rows}:padding=10:margin=10:color=white", "-frames:v", "1", "-update", "1", str(board)],
        project,
        args.verbose,
    )
    value = {
        "schema_version": 1,
        "status": "ready",
        "composition": args.composition,
        "story": args.story,
        "story_sha256": sha256(story_path),
        "transition_mode": story.get("transitionMode", "opaque-cut"),
        "boundaries": boundaries,
        "board": str(board.relative_to(project)),
        "review_required": "Review every three-frame row for double headlines, captions, or transparent scene remnants.",
    }
    errors = validate_transition_manifest(value, story, require_approval=False)
    if errors:
        raise SystemExit("Invalid transition review: " + "; ".join(errors))
    manifest = project / "qa" / f"transition-review{suffix}.json"
    manifest.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
