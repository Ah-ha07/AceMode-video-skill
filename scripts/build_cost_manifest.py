#!/usr/bin/env python3
"""Write a provider-neutral production cost and usage manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"Expected a JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe_duration(path: Path) -> float | None:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return round(float(result.stdout.strip()), 3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-provider", default="unknown")
    parser.add_argument("--model", default="unknown")
    parser.add_argument("--input-tokens", type=int)
    parser.add_argument("--cached-input-tokens", type=int)
    parser.add_argument("--output-tokens", type=int)
    parser.add_argument("--reasoning-output-tokens", type=int)
    parser.add_argument("--tokens-unavailable-reason")
    parser.add_argument("--script", type=Path)
    parser.add_argument("--tts-manifest", type=Path)
    parser.add_argument("--render", type=Path)
    parser.add_argument("--render-frames", type=int)
    parser.add_argument("--render-wall-seconds", type=float)
    args = parser.parse_args()
    token_values = [args.input_tokens, args.cached_input_tokens, args.output_tokens]
    if any(value is not None for value in token_values) and not all(value is not None for value in token_values):
        raise SystemExit("input, cached input, and output tokens must be supplied together")
    if all(value is None for value in token_values) and not args.tokens_unavailable_reason:
        raise SystemExit("supply token usage or --tokens-unavailable-reason")
    if any(value is not None and value < 0 for value in [*token_values, args.reasoning_output_tokens]):
        raise SystemExit("token usage cannot be negative")
    if args.input_tokens is not None and args.cached_input_tokens > args.input_tokens:
        raise SystemExit("cached input tokens cannot exceed input tokens")
    script = args.script.expanduser().resolve() if args.script else None
    tts_path = args.tts_manifest.expanduser().resolve() if args.tts_manifest else None
    render = args.render.expanduser().resolve() if args.render else None
    tts = read_json(tts_path) if tts_path else None
    value = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "llm": {
            "provider": args.model_provider,
            "model": args.model,
            "status": "measured" if args.input_tokens is not None else "unavailable",
            "input_tokens": args.input_tokens,
            "cached_input_tokens": args.cached_input_tokens,
            "non_cached_input_tokens": (args.input_tokens - args.cached_input_tokens) if args.input_tokens is not None else None,
            "output_tokens": args.output_tokens,
            "reasoning_output_tokens": args.reasoning_output_tokens,
            "unavailable_reason": args.tokens_unavailable_reason,
        },
        "script": {
            "path": str(script) if script else None,
            "sha256": sha256(script) if script and script.is_file() else None,
            "characters": len(script.read_text(encoding="utf-8")) if script and script.is_file() else None,
            "words": len(script.read_text(encoding="utf-8").split()) if script and script.is_file() else None,
        },
        "tts": {
            "manifest_path": str(tts_path) if tts_path else None,
            "manifest_sha256": sha256(tts_path) if tts_path and tts_path.is_file() else None,
            "provider": (tts or {}).get("provider"),
            "voice_id": (tts or {}).get("voiceId", (tts or {}).get("voice_id")),
            "duration_seconds": (tts or {}).get("duration"),
            "segment_count": len((tts or {}).get("segments") or []),
        },
        "render": {
            "path": str(render) if render else None,
            "sha256": sha256(render) if render and render.is_file() else None,
            "duration_seconds": probe_duration(render) if render and render.is_file() else None,
            "frames": args.render_frames,
            "wall_seconds": args.render_wall_seconds,
            "llm_tokens": 0,
        },
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
