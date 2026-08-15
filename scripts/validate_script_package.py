#!/usr/bin/env python3
"""Validate the editorial handoff from a ranked signal to a locked narration."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


AI_CHEESE_PIE_CLOSING = (
    "我是AI芝士派，关注我，带你挖掘更多好用的AI工具，下期见！"
)
ACEMODE_PERSONA = "acemode-productivity-editor-v1"
AI_CHEESE_PIE_PERSONA = "ai-cheese-pie-v1"
LEGACY_ROLES = {"hook", "fact", "proof", "demo", "insight", "closing"}
PRODUCTIVITY_ROLES = {
    "hook",
    "old-workflow",
    "change",
    "news",
    "proof",
    "new-workflow",
    "boundary",
    "action",
    "closing",
}
REQUIRED_PRODUCTIVITY_ROLES = {
    "hook",
    "old-workflow",
    "news",
    "new-workflow",
    "boundary",
    "action",
    "closing",
}
PRODUCTIVITY_FRAME_FIELDS = (
    "audience_cn",
    "work_task_cn",
    "old_workflow_cn",
    "friction_cn",
    "ai_change_cn",
    "new_workflow_cn",
    "human_role_cn",
    "readiness_reason_cn",
    "next_action_cn",
)
READINESS_LEVELS = {"use-now", "try-now", "watch", "future"}
ALLOWED_CLAIM_KINDS = {"fact", "number", "quote", "observation", "inference"}
ALLOWED_VERIFICATION = {
    "verified",
    "attributed",
    "reported",
    "community-observed",
    "unverified",
}
FORBIDDEN_PHRASES = (
    "99%的人都不知道",
    "震惊",
    "千万别错过",
    "再不用就晚了",
    "彻底取代所有人",
)
TECH_FIRST_HOOK = re.compile(
    r"^(?:OpenAI|Anthropic|Google|Meta|微软|谷歌|苹果|英伟达|[A-Za-z0-9._-]+)"
    r".{0,12}(?:发布|推出|上线|更新|升级)|^.{0,10}(?:模型|参数).{0,8}(?:发布|推出|升级)"
)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"Expected a JSON object: {path}")
    return value


def compact_text(value: str) -> str:
    return re.sub(r"\s+", "", value)


def validate_package(
    package: dict[str, Any],
    ledger: dict[str, Any],
    selected_signal: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    schema_version = package.get("schema_version")
    if schema_version not in {1, 2}:
        errors.append("script package requires schema_version 1 or 2")
    is_productivity_v2 = schema_version == 2
    signal_id = str(package.get("source_signal_id") or "").strip()
    if not signal_id:
        errors.append("source_signal_id is required")
    if selected_signal and signal_id != str(selected_signal.get("id") or ""):
        errors.append("source_signal_id does not match selected-signal.json")

    persona_id = package.get("persona_id")
    if is_productivity_v2:
        if persona_id not in {ACEMODE_PERSONA, AI_CHEESE_PIE_PERSONA}:
            errors.append(
                "v2 persona_id must be acemode-productivity-editor-v1 or ai-cheese-pie-v1"
            )
        if not str(package.get("story_promise_cn") or "").strip():
            errors.append("v2 story_promise_cn is required")
        frame = package.get("productivity_frame")
        if not isinstance(frame, dict):
            errors.append("v2 productivity_frame must be an object")
            frame = {}
        for field in PRODUCTIVITY_FRAME_FIELDS:
            if not str(frame.get(field) or "").strip():
                errors.append(f"productivity_frame.{field} is required")
        if frame.get("readiness") not in READINESS_LEVELS:
            errors.append(
                "productivity_frame.readiness must be use-now, try-now, watch, or future"
            )
    elif persona_id != AI_CHEESE_PIE_PERSONA:
        errors.append("v1 persona_id must be ai-cheese-pie-v1")
    duration = package.get("target_duration_seconds")
    if not isinstance(duration, (int, float)) or isinstance(duration, bool):
        errors.append("target_duration_seconds must be a number")
    elif not 20 <= float(duration) <= 360:
        errors.append("target_duration_seconds must be between 20 and 360")

    titles = package.get("titles_cn")
    if not isinstance(titles, list) or len(titles) != 5:
        errors.append("titles_cn must contain exactly 5 titles")
        titles = []
    for index, title in enumerate(titles):
        if not isinstance(title, str) or not title.strip():
            errors.append(f"titles_cn[{index}] must be non-empty text")
            continue
        if len(compact_text(title)) > 20:
            errors.append(f"titles_cn[{index}] exceeds 20 characters")

    narration = package.get("narration_cn")
    if not isinstance(narration, str) or not narration.strip():
        errors.append("narration_cn is required")
        narration = ""
    for phrase in FORBIDDEN_PHRASES:
        if phrase in narration or any(phrase in str(title) for title in titles):
            errors.append(f"forbidden clickbait phrase: {phrase}")
    if re.search(r"[（(【\[].{0,30}(画面|镜头|字幕|B-?roll)", narration, re.I):
        errors.append("narration_cn contains a visual/stage direction")
    closing = str(package.get("closing_text_cn") or "").strip()
    if not closing:
        errors.append("closing_text_cn is required")
    if persona_id == AI_CHEESE_PIE_PERSONA and closing != AI_CHEESE_PIE_CLOSING:
        errors.append("closing_text_cn does not match the AI芝士派 fixed ending")
    if narration and not compact_text(narration).endswith(compact_text(closing)):
        errors.append("narration_cn must end with closing_text_cn")

    if ledger.get("schema_version") != 1:
        errors.append("claim ledger requires schema_version: 1")
    if str(ledger.get("source_signal_id") or "") != signal_id:
        errors.append("claim ledger source_signal_id does not match script package")

    radar_urls = {
        str(source.get("url"))
        for source in (selected_signal or {}).get("sources", [])
        if isinstance(source, dict) and source.get("url")
    }
    sources = ledger.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("claim ledger sources must be a non-empty array")
        sources = []
    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"sources[{index}] must be an object")
            continue
        source_id = str(source.get("id") or "").strip()
        if not source_id:
            errors.append(f"sources[{index}] requires id")
        elif source_id in source_ids:
            errors.append(f"duplicate source id: {source_id}")
        source_ids.add(source_id)
        url = str(source.get("url") or "")
        if urlparse(url).scheme not in {"http", "https"}:
            errors.append(f"source {source_id or index} requires an http(s) URL")
        if not str(source.get("supports_cn") or "").strip():
            errors.append(f"source {source_id or index} requires supports_cn")
        if source.get("verification") not in ALLOWED_VERIFICATION:
            errors.append(f"source {source_id or index} has invalid verification")
        from_radar = source.get("from_radar")
        if not isinstance(from_radar, bool):
            errors.append(f"source {source_id or index} requires boolean from_radar")
        elif from_radar and selected_signal and url not in radar_urls:
            errors.append(f"source {source_id or index} claims radar provenance but URL is absent")

    claims = ledger.get("claims")
    if not isinstance(claims, list) or not claims:
        errors.append("claim ledger claims must be a non-empty array")
        claims = []
    claim_ids: set[str] = set()
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append(f"claims[{index}] must be an object")
            continue
        claim_id = str(claim.get("id") or "").strip()
        if not claim_id:
            errors.append(f"claims[{index}] requires id")
        elif claim_id in claim_ids:
            errors.append(f"duplicate claim id: {claim_id}")
        claim_ids.add(claim_id)
        if not str(claim.get("text_cn") or "").strip():
            errors.append(f"claim {claim_id or index} requires text_cn")
        if claim.get("kind") not in ALLOWED_CLAIM_KINDS:
            errors.append(f"claim {claim_id or index} has invalid kind")
        refs = claim.get("source_ids")
        if not isinstance(refs, list) or not refs:
            errors.append(f"claim {claim_id or index} requires source_ids")
        else:
            missing = [str(ref) for ref in refs if str(ref) not in source_ids]
            if missing:
                errors.append(
                    f"claim {claim_id or index} references unknown sources: {', '.join(missing)}"
                )
        if not isinstance(claim.get("recheck_before_production"), bool):
            errors.append(
                f"claim {claim_id or index} requires boolean recheck_before_production"
            )
        if claim.get("kind") == "inference" and not str(
            claim.get("boundary_cn") or ""
        ).strip():
            errors.append(f"inference claim {claim_id or index} requires boundary_cn")

    segments = package.get("segments")
    if not isinstance(segments, list) or not segments:
        errors.append("segments must be a non-empty array")
        segments = []
    segment_ids: set[str] = set()
    used_claims: set[str] = set()
    segment_texts: list[str] = []
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            errors.append(f"segments[{index}] must be an object")
            continue
        segment_id = str(segment.get("id") or "").strip()
        if not segment_id:
            errors.append(f"segments[{index}] requires id")
        elif segment_id in segment_ids:
            errors.append(f"duplicate segment id: {segment_id}")
        segment_ids.add(segment_id)
        role = segment.get("role")
        allowed_roles = PRODUCTIVITY_ROLES if is_productivity_v2 else LEGACY_ROLES
        if role not in allowed_roles:
            errors.append(f"segment {segment_id or index} has invalid role")
        text = str(segment.get("text_cn") or "").strip()
        if not text:
            errors.append(f"segment {segment_id or index} requires text_cn")
        segment_texts.append(text)
        refs = segment.get("claim_refs")
        if not isinstance(refs, list):
            errors.append(f"segment {segment_id or index} claim_refs must be an array")
            refs = []
        unknown = [str(ref) for ref in refs if str(ref) not in claim_ids]
        if unknown:
            errors.append(
                f"segment {segment_id or index} references unknown claims: {', '.join(unknown)}"
            )
        used_claims.update(str(ref) for ref in refs)
        if role != "closing" and not refs:
            errors.append(f"non-closing segment {segment_id or index} requires claim_refs")
        if role == "closing" and text != closing:
            errors.append("closing segment text must equal closing_text_cn")

    if narration and compact_text(narration) != compact_text("\n".join(segment_texts)):
        errors.append("narration_cn must exactly match the ordered segment text")
    unused = sorted(claim_ids - used_claims)
    if unused:
        warnings.append(f"unused claims: {', '.join(unused)}")
    if segments and segments[0].get("role") != "hook":
        warnings.append("first segment should be the hook")
    if segments and segments[-1].get("role") != "closing":
        errors.append("last segment must be the closing")
    if is_productivity_v2:
        present_roles = {
            str(segment.get("role"))
            for segment in segments
            if isinstance(segment, dict)
        }
        missing_roles = sorted(REQUIRED_PRODUCTIVITY_ROLES - present_roles)
        if missing_roles:
            errors.append(
                "v2 segments are missing required roles: " + ", ".join(missing_roles)
            )
        ordered_roles = [
            "hook",
            "old-workflow",
            "news",
            "new-workflow",
            "boundary",
            "action",
            "closing",
        ]
        positions = {
            role: next(
                (
                    index
                    for index, segment in enumerate(segments)
                    if isinstance(segment, dict) and segment.get("role") == role
                ),
                None,
            )
            for role in ordered_roles
        }
        found_positions = [positions[role] for role in ordered_roles]
        if all(position is not None for position in found_positions) and found_positions != sorted(
            found_positions
        ):
            errors.append(
                "v2 workflow roles must follow hook → old-workflow → news → new-workflow → boundary → action → closing"
            )
    hook = str(segments[0].get("text_cn") or "") if segments else ""
    if is_productivity_v2 and TECH_FIRST_HOOK.search(hook.strip()):
        errors.append(
            "v2 hook starts with a company, model, parameter, or release; start from the work situation and practical impact"
        )
    if len(compact_text(hook)) > 70:
        warnings.append("hook may be too long for the first three seconds")

    if isinstance(duration, (int, float)) and duration > 0 and narration:
        spoken_chars = len(re.sub(r"[\s，。！？、；：,.!?;:]", "", narration))
        estimated_seconds = spoken_chars / 4.2
        if abs(estimated_seconds - float(duration)) > max(8.0, float(duration) * 0.3):
            warnings.append(
                f"rough text estimate {estimated_seconds:.1f}s differs from target {float(duration):.1f}s; audio duration is authoritative"
            )

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--selected", type=Path)
    args = parser.parse_args()

    package = read_json(args.package.expanduser().resolve())
    ledger = read_json(args.ledger.expanduser().resolve())
    selected = read_json(args.selected.expanduser().resolve()) if args.selected else None
    errors, warnings = validate_package(package, ledger, selected)
    for message in warnings:
        print(f"WARN: {message}")
    for message in errors:
        print(f"ERROR: {message}")
    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"OK: script package ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
