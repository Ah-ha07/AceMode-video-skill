#!/usr/bin/env python3
"""Create and approve an auditable TTS voice audition manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"Expected a JSON object: {path}")
    return value


def parse_candidate(value: str) -> dict[str, str]:
    parts = value.split(",", 3)
    if len(parts) != 4 or any(not part.strip() for part in parts):
        raise argparse.ArgumentTypeError("candidate must be id,provider,voice_id,audio_path")
    candidate_id, provider, voice_id, raw_path = (part.strip() for part in parts)
    path = Path(raw_path).expanduser().resolve()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"candidate audio is missing: {path}")
    return {"id": candidate_id, "provider": provider, "voice_id": voice_id, "audio_path": str(path), "sha256": sha256(path)}


def validate_manifest(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("schema_version") != 1:
        errors.append("voice audition requires schema_version: 1")
    candidates = value.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        errors.append("voice audition requires candidates")
        candidates = []
    ids = [str(item.get("id") or "") for item in candidates if isinstance(item, dict)]
    if len(ids) != len(set(ids)) or any(not item for item in ids):
        errors.append("voice audition candidate IDs must be non-empty and unique")
    approval = value.get("approval")
    if not isinstance(approval, dict):
        errors.append("voice audition has not been approved")
    else:
        if approval.get("candidate_id") not in ids:
            errors.append("approved candidate is not in the audition")
        if not str(approval.get("receipt") or "").strip():
            errors.append("voice audition approval requires receipt")
    return errors


def command_create(args: argparse.Namespace) -> int:
    sample = args.sample_text.expanduser().resolve()
    if not sample.is_file() or not sample.read_text(encoding="utf-8").strip():
        raise SystemExit("sample text is missing or empty")
    value = {
        "schema_version": 1,
        "language": args.language,
        "sample_text_path": str(sample),
        "sample_text_sha256": sha256(sample),
        "candidates": args.candidates,
        "approval": None,
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


def command_approve(args: argparse.Namespace) -> int:
    source = args.manifest.expanduser().resolve()
    value = read_json(source)
    ids = {str(item.get("id")) for item in value.get("candidates") or [] if isinstance(item, dict)}
    if args.candidate not in ids:
        raise SystemExit(f"Unknown audition candidate: {args.candidate}")
    value["approval"] = {
        "candidate_id": args.candidate,
        "approved_by": args.by,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "receipt": args.receipt,
    }
    errors = validate_manifest(value)
    if errors:
        raise SystemExit("Invalid voice audition: " + "; ".join(errors))
    output = args.output.expanduser().resolve() if args.output else source
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


def command_validate(args: argparse.Namespace) -> int:
    errors = validate_manifest(read_json(args.manifest.expanduser().resolve()))
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1
    print("OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("create")
    command.add_argument("--sample-text", type=Path, required=True)
    command.add_argument("--language", required=True)
    command.add_argument("--candidate", dest="candidates", action="append", type=parse_candidate, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.set_defaults(handler=command_create)
    command = subparsers.add_parser("approve")
    command.add_argument("manifest", type=Path)
    command.add_argument("--candidate", required=True)
    command.add_argument("--receipt", required=True)
    command.add_argument("--by", default="user")
    command.add_argument("--output", type=Path)
    command.set_defaults(handler=command_approve)
    command = subparsers.add_parser("validate")
    command.add_argument("manifest", type=Path)
    command.set_defaults(handler=command_validate)
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
