#!/usr/bin/env python3
"""Generate and validate readable caption cues from authoritative TTS timing."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


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


def milliseconds(value: Any, unit: str) -> int:
    number = float(value)
    if unit == "milliseconds":
        return round(number)
    return round(number * 1000)


def sentence_records(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    unit = str(manifest.get("timingUnit") or manifest.get("timing_unit") or "seconds")
    if unit not in {"seconds", "milliseconds"}:
        raise SystemExit("voice manifest timingUnit must be seconds or milliseconds")
    for segment in manifest.get("segments") or []:
        if not isinstance(segment, dict):
            continue
        sentences = segment.get("sentences")
        if not isinstance(sentences, list):
            continue
        for sentence in sentences:
            if not isinstance(sentence, dict):
                continue
            text = str(sentence.get("text") or "").strip()
            start = sentence.get("startTime", sentence.get("start"))
            end = sentence.get("endTime", sentence.get("end"))
            if text and start is not None and end is not None:
                records.append({"text": text, "start": milliseconds(start, unit), "end": milliseconds(end, unit), "words": sentence.get("words") or [], "unit": unit})
    return sorted(records, key=lambda item: item["start"])


def split_display_words(text: str, max_words: int, max_chars: int) -> list[list[str]]:
    words = text.split()
    chunks: list[list[str]] = []
    current: list[str] = []
    for word in words:
        candidate = current + [word]
        if current and (len(candidate) > max_words or len(" ".join(candidate)) > max_chars):
            chunks.append(current)
            current = [word]
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def raw_word_times(words: list[Any], unit: str) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for word in words:
        if not isinstance(word, dict):
            continue
        start = word.get("startTime", word.get("start"))
        end = word.get("endTime", word.get("end"))
        if start is None or end is None:
            continue
        result.append((milliseconds(start, unit), milliseconds(end, unit)))
    return result


def generate_cues(manifest: dict[str, Any], max_words: int, max_chars: int) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    for sentence in sentence_records(manifest):
        chunks = split_display_words(sentence["text"], max_words, max_chars)
        display_count = sum(len(chunk) for chunk in chunks)
        raw = raw_word_times(sentence["words"], sentence["unit"])
        consumed = 0
        for index, chunk in enumerate(chunks):
            start_ratio = consumed / max(display_count, 1)
            consumed += len(chunk)
            end_ratio = consumed / max(display_count, 1)
            if raw:
                start_index = min(len(raw) - 1, int(start_ratio * len(raw)))
                end_index = min(len(raw) - 1, max(start_index, int(end_ratio * len(raw) - 1e-9)))
                start_ms = raw[start_index][0]
                end_ms = raw[end_index][1]
            else:
                span = sentence["end"] - sentence["start"]
                start_ms = round(sentence["start"] + span * start_ratio)
                end_ms = round(sentence["start"] + span * end_ratio)
            if index == 0:
                start_ms = sentence["start"]
            if index == len(chunks) - 1:
                end_ms = sentence["end"]
            cues.append(
                {
                    "text": " ".join(chunk),
                    "startMs": start_ms,
                    "endMs": max(start_ms + 1, end_ms),
                    "timestampMs": None,
                    "confidence": 1.0,
                }
            )
    return cues


def validate_manifest(value: dict[str, Any], voice: dict[str, Any] | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if value.get("schema_version") != 1:
        errors.append("caption manifest requires schema_version: 1")
    if value.get("timing_source") != "tts-manifest":
        errors.append("caption timing_source must be tts-manifest")
    if not str(value.get("language") or "").strip():
        errors.append("caption manifest requires language")
    cues = value.get("cues")
    if not isinstance(cues, list) or not cues:
        errors.append("caption manifest requires non-empty cues")
        cues = []
    previous_end = 0
    for index, cue in enumerate(cues):
        if not isinstance(cue, dict):
            errors.append(f"cue[{index}] must be an object")
            continue
        text = str(cue.get("text") or "").strip()
        start = cue.get("startMs")
        end = cue.get("endMs")
        if not text:
            errors.append(f"cue[{index}] has empty text")
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
            errors.append(f"cue[{index}] has invalid timing")
            continue
        if start < previous_end:
            errors.append(f"cue[{index}] overlaps the previous cue")
        previous_end = end
        duration = end - start
        if duration < 350:
            errors.append(f"cue[{index}] is shorter than 350ms")
        if duration > 4500:
            warnings.append(f"cue[{index}] is longer than 4.5s")
        if len(text) > 84:
            errors.append(f"cue[{index}] exceeds two-line mobile caption budget")
        cps = len(re.sub(r"\s+", "", text)) / (duration / 1000)
        if cps > 24:
            warnings.append(f"cue[{index}] reading speed is {cps:.1f} characters/s")
    if value.get("cue_count") != len(cues):
        errors.append("cue_count does not match cues")
    if voice:
        duration = voice.get("duration")
        if isinstance(duration, (int, float)) and cues and cues[-1].get("endMs", 0) > float(duration) * 1000 + 100:
            errors.append("captions extend beyond measured voice duration")
    return errors, warnings


def command_generate(args: argparse.Namespace) -> int:
    voice_path = args.voice_manifest.expanduser().resolve()
    voice = read_json(voice_path)
    cues = generate_cues(voice, args.max_words, args.max_chars)
    value = {
        "schema_version": 1,
        "language": args.language or voice.get("language") or "en-US",
        "timing_source": "tts-manifest",
        "source_voice_manifest_sha256": sha256(voice_path),
        "cue_count": len(cues),
        "cues": cues,
    }
    errors, warnings = validate_manifest(value, voice)
    if errors:
        raise SystemExit("Generated captions failed validation: " + "; ".join(errors))
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "cue_count": len(cues), "warnings": warnings}, ensure_ascii=False))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    value = read_json(args.caption_manifest.expanduser().resolve())
    voice = read_json(args.voice_manifest.expanduser().resolve()) if args.voice_manifest else None
    errors, warnings = validate_manifest(value, voice)
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1
    print(f"OK: {len(value.get('cues') or [])} cue(s), {len(warnings)} warning(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("generate")
    command.add_argument("voice_manifest", type=Path)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--language")
    command.add_argument("--max-words", type=int, default=9)
    command.add_argument("--max-chars", type=int, default=52)
    command.set_defaults(handler=command_generate)
    command = subparsers.add_parser("validate")
    command.add_argument("caption_manifest", type=Path)
    command.add_argument("--voice-manifest", type=Path)
    command.set_defaults(handler=command_validate)
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
