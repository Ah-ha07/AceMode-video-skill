#!/usr/bin/env python3
"""Validate the approved Visual Director treatment and review images."""

from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_CONCEPTS = {
    "audience memory": ("audience memory", "观众记忆"),
    "emotional arc": ("emotional arc", "情绪曲线"),
    "visual motif": ("visual motif", "视觉母题"),
    "color roles": ("color roles", "色彩角色"),
    "shot causality": ("shot causality", "镜头因果"),
    "reject rules": ("reject rules", "拒绝规则"),
}


def is_image(path: Path) -> bool:
    head = path.read_bytes()[:16]
    return (
        head.startswith(b"\x89PNG\r\n\x1a\n")
        or head.startswith(b"\xff\xd8\xff")
        or head.startswith((b"GIF87a", b"GIF89a"))
        or (head.startswith(b"RIFF") and head[8:12] == b"WEBP")
        or path.suffix.lower() == ".svg"
    )


def validate_pack(treatment: Path, board: Path, frames: list[Path]) -> list[str]:
    errors: list[str] = []
    treatment = treatment.expanduser().resolve()
    board = board.expanduser().resolve()
    frames = [path.expanduser().resolve() for path in frames]
    if not treatment.is_file():
        return [f"director treatment is missing: {treatment}"]
    text = treatment.read_text(encoding="utf-8").lower()
    if len(text.strip()) < 240:
        errors.append("director treatment is too short to be actionable")
    for label, variants in REQUIRED_CONCEPTS.items():
        if not any(variant.lower() in text for variant in variants):
            errors.append(f"director treatment is missing {label}")
    if not board.is_file() or not is_image(board):
        errors.append("director concept board is missing or not an image")
    if len(frames) < 3:
        errors.append("director pack requires at least three style frames")
    for path in frames:
        if not path.is_file() or not is_image(path):
            errors.append(f"director style frame is missing or invalid: {path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--treatment", type=Path, required=True)
    parser.add_argument("--board", type=Path, required=True)
    parser.add_argument("--frame", dest="frames", action="append", type=Path, required=True)
    args = parser.parse_args()
    errors = validate_pack(args.treatment, args.board, args.frames)
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1
    print(f"OK: {len(args.frames)} style frame(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
