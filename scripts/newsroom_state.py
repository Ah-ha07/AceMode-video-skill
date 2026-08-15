#!/usr/bin/env python3
"""Persist and enforce AceMode Newsroom approval gates across chat turns."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_transition_review import validate_transition_manifest
from caption_pipeline import validate_manifest as validate_caption_manifest
from validate_delivery_spec import validate_contract
from validate_director_pack import validate_pack as validate_director_pack
from validate_script_package import validate_package
from voice_audition import validate_manifest as validate_voice_audition


MANIFEST = "project.json"
VALID_STATES = {
    "SELECTED",
    "SCRIPT_DRAFT",
    "SCRIPT_APPROVED",
    "PREVIEW_READY",
    "RENDER_APPROVED",
    "COMPLETED_INTERNAL",
    "COMPLETED",
}


def utc_now(value: str | None = None) -> str:
    if value:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise SystemExit(f"Invalid ISO timestamp: {value}") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def parse_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"Expected a JSON object: {path}")
    return value


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_records(records: list[dict[str, str]]) -> str:
    payload = "\n".join(f"{item['path']}:{item['sha256']}" for item in records)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def tree_record(path: Path, root: Path, role: str) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise SystemExit(f"Missing {role} directory: {resolved}")
    files: list[dict[str, str]] = []
    for item in sorted(value for value in resolved.rglob("*") if value.is_file()):
        files.append({"path": relative_to_project(item, root), "sha256": sha256(item)})
    if not files:
        raise SystemExit(f"Refusing to register empty {role} directory: {resolved}")
    payload = "\n".join(f"{item['path']}:{item['sha256']}" for item in files)
    return {
        "role": role,
        "path": relative_to_project(resolved, root),
        "kind": "tree",
        "file_count": len(files),
        "files": files,
        "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    }


def validate_remotion_source_closure(path: Path) -> None:
    root = path.expanduser().resolve()
    pattern = re.compile(
        r"(?:from\s+|import\s*\(|import\s+|require\s*\()\s*['\"](\.{1,2}/[^'\"]+)['\"]"
    )
    extensions = ("", ".js", ".jsx", ".ts", ".tsx", ".json")
    for source in root.rglob("*"):
        if not source.is_file() or source.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx"}:
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in pattern.finditer(text):
            target = (source.parent / match.group(1)).resolve()
            candidates = [Path(str(target) + extension) for extension in extensions]
            candidates.extend(target / f"index{extension}" for extension in extensions[1:])
            resolved = next((item for item in candidates if item.is_file()), None)
            if resolved is None:
                raise SystemExit(f"Unresolved local Remotion import in {source}: {match.group(1)}")
            try:
                resolved.relative_to(root)
            except ValueError as exc:
                raise SystemExit(
                    f"Remotion source imports an unregistered file outside src/: {resolved}"
                ) from exc


def safe_id(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._")
    return normalized[:72] or "story"


def project_path(project: Path) -> Path:
    return project.expanduser().resolve() / MANIFEST


def load_project(project: Path) -> tuple[Path, dict[str, Any]]:
    root = project.expanduser().resolve()
    manifest = project_path(root)
    value = read_json(manifest)
    if value.get("schema_version") != 1 or value.get("skill") != "acemode-newsroom":
        raise SystemExit(f"Unsupported newsroom manifest: {manifest}")
    return root, value


def save_project(root: Path, project: dict[str, Any], at: str) -> None:
    project["updated_at"] = at
    atomic_json(root / MANIFEST, project)


def relative_to_project(path: Path, root: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return str(resolved.relative_to(root))
    except ValueError as exc:
        raise SystemExit(f"Artifact must be inside the newsroom project: {resolved}") from exc


def copy_file(source: Path, destination: Path) -> None:
    source = source.expanduser().resolve()
    destination = destination.resolve()
    if not source.is_file():
        raise SystemExit(f"Missing file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source != destination:
        shutil.copy2(source, destination)


def record_event(project: dict[str, Any], at: str, event: str, story_id: str | None = None, **data: Any) -> None:
    item: dict[str, Any] = {"at": at, "event": event}
    if story_id:
        item["story_id"] = story_id
    item.update(data)
    project.setdefault("history", []).append(item)


def resolve_story(project: dict[str, Any], selector: str) -> tuple[str, dict[str, Any]]:
    stories = project.get("stories") or {}
    if selector in stories:
        return selector, stories[selector]
    for story_id, story in stories.items():
        if selector in {
            str(story.get("radar_rank")),
            str(story.get("source_signal_id")),
        }:
            return story_id, story
    raise SystemExit(f"Unknown story selector: {selector}")


def story_dir(root: Path, story: dict[str, Any]) -> Path:
    return root / str(story["directory"])


def require_selected_signal(root: Path, story: dict[str, Any]) -> Path:
    path = root / str(story.get("selected_signal_path") or "")
    expected = story.get("selected_signal_sha256")
    if not path.is_file() or not expected:
        raise SystemExit("Selected signal snapshot is missing")
    if sha256(path) != expected:
        raise SystemExit("Selected signal changed after selection; restore the snapshot or start a new project")
    return path


def clear_after_script(story: dict[str, Any]) -> None:
    story.pop("source_recheck", None)
    story.pop("preview", None)
    story.pop("render_approval", None)
    story.pop("final", None)


def clear_after_recheck(story: dict[str, Any]) -> None:
    story.pop("preview", None)
    story.pop("render_approval", None)
    story.pop("final", None)


def current_script_hash(root: Path, story: dict[str, Any]) -> str:
    script = story.get("script") or {}
    paths = [
        script.get("package_path"),
        script.get("claim_ledger_path"),
        script.get("narration_path"),
        script.get("readable_path"),
    ]
    if not all(isinstance(path, str) and path for path in paths):
        raise SystemExit("Story has no registered script bundle")
    records = []
    for path in paths:
        artifact = root / str(path)
        if not artifact.is_file():
            raise SystemExit(f"Registered script artifact is missing: {artifact}")
        records.append({"path": str(path), "sha256": sha256(artifact)})
    return hash_records(records)


def require_approved_script(root: Path, story: dict[str, Any]) -> str:
    script = story.get("script") or {}
    approved_hash = script.get("approved_hash")
    if not approved_hash:
        raise SystemExit("Script has not been explicitly approved")
    actual = current_script_hash(root, story)
    if actual != approved_hash:
        raise SystemExit("Script artifacts changed after approval; register and approve them again")
    return actual


def require_fresh_recheck(root: Path, story: dict[str, Any]) -> None:
    script = story.get("script") or {}
    recheck = story.get("source_recheck") or {}
    if recheck.get("result") != "unchanged":
        raise SystemExit("Run a source recheck after script approval before video production")
    manifest = root / str(recheck.get("manifest_path") or "")
    if not manifest.is_file() or sha256(manifest) != recheck.get("manifest_sha256"):
        raise SystemExit("Source recheck manifest changed or is missing; run the recheck again")
    if parse_time(str(recheck["checked_at"])) < parse_time(str(script["approved_at"])):
        raise SystemExit("Source recheck predates script approval; recheck again")


def validate_recheck_manifest(root: Path, story: dict[str, Any], path: Path) -> tuple[str, str]:
    manifest = read_json(path)
    if manifest.get("schema_version") != 1:
        raise SystemExit("Source recheck manifest requires schema_version: 1")
    if str(manifest.get("source_signal_id") or "") != story.get("source_signal_id"):
        raise SystemExit("Source recheck manifest belongs to another signal")
    ledger = read_json(root / str(story["script"]["claim_ledger_path"]))
    required = {
        str(claim["id"]): {str(item) for item in claim.get("source_ids") or []}
        for claim in ledger.get("claims") or []
        if isinstance(claim, dict)
        and claim.get("id")
        and claim.get("recheck_before_production") is True
    }
    checks = manifest.get("checks")
    if not isinstance(checks, list):
        raise SystemExit("Source recheck manifest checks must be an array")
    by_claim: dict[str, dict[str, Any]] = {}
    overall = "unchanged"
    latest: datetime | None = None
    for check in checks:
        if not isinstance(check, dict):
            raise SystemExit("Each source recheck must be an object")
        claim_id = str(check.get("claim_id") or "")
        if claim_id in by_claim:
            raise SystemExit(f"Duplicate source recheck for claim: {claim_id}")
        if claim_id not in required:
            raise SystemExit(f"Unexpected source recheck claim: {claim_id}")
        source_ids = {str(item) for item in check.get("source_ids") or []}
        if not required[claim_id].issubset(source_ids):
            raise SystemExit(f"Source recheck for {claim_id} does not cover all claim sources")
        result = check.get("result")
        if result not in {"unchanged", "material-change"}:
            raise SystemExit(f"Source recheck for {claim_id} has invalid result")
        if not str(check.get("notes_cn") or "").strip():
            raise SystemExit(f"Source recheck for {claim_id} requires notes_cn")
        checked_at = str(check.get("checked_at") or "")
        try:
            checked = parse_time(checked_at)
        except (ValueError, TypeError) as exc:
            raise SystemExit(f"Source recheck for {claim_id} has invalid checked_at") from exc
        approved_at = parse_time(str(story.get("script", {}).get("approved_at") or ""))
        if checked < approved_at:
            raise SystemExit(f"Source recheck for {claim_id} predates script approval")
        latest = checked if latest is None or checked > latest else latest
        if result == "material-change":
            overall = "material-change"
        by_claim[claim_id] = check
    missing = sorted(set(required) - set(by_claim))
    if missing:
        raise SystemExit(f"Source recheck is missing claims: {', '.join(missing)}")
    checked_at = (latest or datetime.now(timezone.utc)).isoformat()
    return overall, checked_at


def is_image(path: Path) -> bool:
    head = path.read_bytes()[:16]
    return (
        head.startswith(b"\x89PNG\r\n\x1a\n")
        or head.startswith(b"\xff\xd8\xff")
        or head.startswith((b"GIF87a", b"GIF89a"))
        or (head.startswith(b"RIFF") and head[8:12] == b"WEBP")
        or path.suffix.lower() == ".svg"
    )


def ffprobe(path: Path) -> dict[str, Any]:
    executable = shutil.which("ffprobe")
    if not executable:
        raise SystemExit("ffprobe is required to validate video artifacts")
    completed = subprocess.run(
        [
            executable,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise SystemExit(f"Not a decodable media file: {path}: {completed.stderr.strip()}")
    return json.loads(completed.stdout)


def audit_project(root: Path, project: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    radar = project.get("radar") or {}
    if radar.get("status") == "READY":
        radar_path = root / str(radar.get("signals_path") or "")
        if not radar_path.is_file():
            errors.append("radar signals snapshot is missing")
        elif sha256(radar_path) != radar.get("snapshot_sha256"):
            errors.append("radar signals snapshot hash mismatch")
    for story_id, story in (project.get("stories") or {}).items():
        try:
            require_selected_signal(root, story)
        except SystemExit as exc:
            errors.append(f"{story_id}: {exc}")
        script = story.get("script") or {}
        if script:
            try:
                actual = current_script_hash(root, story)
                if actual != script.get("bundle_sha256"):
                    errors.append(f"{story_id}: registered script bundle hash mismatch")
                if script.get("approved_hash") and actual != script.get("approved_hash"):
                    errors.append(f"{story_id}: approved script bundle hash mismatch")
            except SystemExit as exc:
                errors.append(f"{story_id}: {exc}")
        recheck = story.get("source_recheck") or {}
        if recheck:
            path = root / str(recheck.get("manifest_path") or "")
            if not path.is_file() or sha256(path) != recheck.get("manifest_sha256"):
                errors.append(f"{story_id}: source recheck manifest hash mismatch or file missing")
        preview = story.get("preview") or {}
        if preview:
            try:
                actual = verify_artifact_records(root, preview.get("artifacts") or [])
                if actual != preview.get("bundle_sha256"):
                    errors.append(f"{story_id}: preview bundle hash mismatch")
            except SystemExit as exc:
                errors.append(f"{story_id}: {exc}")
        final = story.get("final") or {}
        if final:
            render = root / str(final.get("render_path") or "")
            report = root / str(final.get("qa_report_path") or "")
            cost = root / str(final.get("cost_manifest_path")) if final.get("cost_manifest_path") else None
            if not render.is_file() or sha256(render) != final.get("sha256"):
                errors.append(f"{story_id}: final render hash mismatch or file missing")
            if not report.is_file() or sha256(report) != final.get("qa_report_sha256"):
                errors.append(f"{story_id}: final QA report hash mismatch or file missing")
            if cost is not None and (not cost.is_file() or sha256(cost) != final.get("cost_manifest_sha256")):
                errors.append(f"{story_id}: cost manifest hash mismatch or file missing")
    return {"ok": not errors, "errors": errors}


def verify_artifact_records(root: Path, records: list[dict[str, str]]) -> str:
    current: list[dict[str, str]] = []
    for item in records:
        if item.get("kind") == "tree":
            actual = tree_record(root / item["path"], root, str(item.get("role") or "tree"))
            if actual["sha256"] != item["sha256"] or actual["files"] != item.get("files"):
                raise SystemExit(f"Preview/production directory changed after review: {root / item['path']}")
            current.append({"path": item["path"], "sha256": actual["sha256"]})
            continue
        path = root / item["path"]
        if not path.is_file():
            raise SystemExit(f"Approved preview artifact is missing: {path}")
        value = sha256(path)
        if value != item["sha256"]:
            raise SystemExit(f"Preview/production artifact changed after review: {path}")
        current.append({"path": item["path"], "sha256": value})
    return hash_records(current)


def require_registered_artifact(root: Path, story: dict[str, Any], role: str, path: Path) -> None:
    relative = relative_to_project(path, root)
    matches = [
        item
        for item in (story.get("preview") or {}).get("artifacts") or []
        if item.get("role") == role and item.get("path") == relative
    ]
    if len(matches) != 1 or sha256(path) != matches[0].get("sha256"):
        raise SystemExit(f"Final QA input is not the approved {role} artifact: {path}")


def registered_artifact(root: Path, story: dict[str, Any], role: str) -> Path:
    matches = [
        item
        for item in (story.get("preview") or {}).get("artifacts") or []
        if item.get("role") == role
    ]
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one approved {role} artifact")
    path = root / str(matches[0]["path"])
    if not path.is_file() or sha256(path) != matches[0].get("sha256"):
        raise SystemExit(f"Approved {role} artifact changed or is missing: {path}")
    return path


def command_init(args: argparse.Namespace) -> None:
    root = args.project.expanduser().resolve()
    manifest = root / MANIFEST
    if manifest.exists():
        raise SystemExit(f"Refusing to overwrite existing newsroom project: {manifest}")
    root.mkdir(parents=True, exist_ok=True)
    at = utc_now(args.at)
    value = {
        "schema_version": 1,
        "skill": "acemode-newsroom",
        "project_id": args.project_id or safe_id(root.name),
        "title": args.title,
        "created_at": at,
        "updated_at": at,
        "radar": {"status": "EMPTY"},
        "stories": {},
        "history": [],
    }
    record_event(value, at, "PROJECT_CREATED")
    atomic_json(manifest, value)
    print(manifest)


def command_import_radar(args: argparse.Namespace) -> None:
    root, project = load_project(args.project)
    if project.get("radar", {}).get("status") == "READY":
        raise SystemExit("Radar snapshot already exists; create a new newsroom project for a new run")
    payload = read_json(args.signals.expanduser().resolve())
    signals = payload.get("signals")
    if not isinstance(signals, list) or not signals:
        raise SystemExit("signals.json contains no ranked main-list signals")
    seen: set[str] = set()
    for rank, signal in enumerate(signals, start=1):
        if not isinstance(signal, dict) or not str(signal.get("id") or "").strip():
            raise SystemExit(f"Rank {rank} has no stable signal id")
        signal_id = str(signal["id"])
        if signal_id in seen:
            raise SystemExit(f"Duplicate signal id: {signal_id}")
        seen.add(signal_id)
        signal["rank"] = rank
    radar_dir = root / "radar"
    radar_dir.mkdir(exist_ok=True)
    signals_path = radar_dir / "signals.json"
    candidates_path = radar_dir / "candidates.json"
    brief_path = radar_dir / "brief.md"
    atomic_json(signals_path, payload)
    if args.candidates:
        copy_file(args.candidates, candidates_path)
    copy_file(args.brief, brief_path)
    at = utc_now(args.at)
    project["radar"] = {
        "status": "READY",
        "generated_at": payload.get("generated_at"),
        "window_hours": payload.get("window_hours"),
        "signals_path": "radar/signals.json",
        "candidates_path": "radar/candidates.json" if args.candidates else None,
        "brief_path": "radar/brief.md",
        "snapshot_sha256": sha256(signals_path),
        "main_count": len(signals),
        "watchlist_count": len(payload.get("watchlist") or []),
    }
    record_event(project, at, "RADAR_IMPORTED", main_count=len(signals))
    save_project(root, project, at)
    print(signals_path)


def parse_ranks(values: list[str]) -> list[int]:
    ranks: list[int] = []
    for value in values:
        for item in value.split(","):
            try:
                rank = int(item)
            except ValueError as exc:
                raise SystemExit(f"Invalid rank: {item}") from exc
            if rank < 1 or rank in ranks:
                raise SystemExit(f"Rank must be positive and unique: {rank}")
            ranks.append(rank)
    return ranks


def command_select(args: argparse.Namespace) -> None:
    root, project = load_project(args.project)
    radar = project.get("radar") or {}
    if radar.get("status") != "READY":
        raise SystemExit("Import a radar snapshot before selecting stories")
    radar_path = root / str(radar["signals_path"])
    if sha256(radar_path) != radar.get("snapshot_sha256"):
        raise SystemExit("Radar snapshot changed after import; restore it or create a new newsroom project")
    payload = read_json(radar_path)
    signals = payload.get("signals") or []
    at = utc_now(args.at)
    selected_ids: list[str] = []
    for rank in parse_ranks(args.ranks):
        if rank > len(signals):
            raise SystemExit(f"Rank {rank} is outside the saved main list")
        signal = signals[rank - 1]
        signal_id = str(signal["id"])
        story_id = f"{rank:02d}-{safe_id(signal_id)}"
        existing = project.setdefault("stories", {}).get(story_id)
        if existing:
            selected_ids.append(story_id)
            continue
        directory = f"stories/{story_id}"
        target = root / directory
        target.mkdir(parents=True, exist_ok=True)
        atomic_json(target / "selected-signal.json", signal)
        project["stories"][story_id] = {
            "story_id": story_id,
            "source_signal_id": signal_id,
            "radar_rank": rank,
            "title": signal.get("title"),
            "directory": directory,
            "selected_signal_path": f"{directory}/selected-signal.json",
            "selected_signal_sha256": sha256(target / "selected-signal.json"),
            "status": "SELECTED",
            "selected_at": at,
        }
        record_event(project, at, "STORY_SELECTED", story_id, radar_rank=rank)
        selected_ids.append(story_id)
    save_project(root, project, at)
    print(json.dumps({"selected": selected_ids}, ensure_ascii=False))


def command_register_script(args: argparse.Namespace) -> None:
    root, project = load_project(args.project)
    story_id, story = resolve_story(project, args.story)
    target = story_dir(root, story)
    package = read_json(args.package.expanduser().resolve())
    ledger = read_json(args.ledger.expanduser().resolve())
    selected_signal = read_json(require_selected_signal(root, story))
    if str(package.get("source_signal_id") or "") != story.get("source_signal_id"):
        raise SystemExit("Script package does not belong to the selected signal")
    errors, warnings = validate_package(package, ledger, selected_signal)
    for message in warnings:
        print(f"WARN: {message}")
    if errors:
        for message in errors:
            print(f"ERROR: {message}")
        raise SystemExit(f"Refusing to register invalid script: {len(errors)} error(s)")
    package_path = target / "script-package.json"
    ledger_path = target / "claim-ledger.json"
    copy_file(args.package, package_path)
    copy_file(args.ledger, ledger_path)
    narration = str(package.get("narration_cn") or "").strip()
    if not narration:
        raise SystemExit("Script package narration_cn is empty")
    (target / "script.txt").write_text(narration + "\n", encoding="utf-8")
    titles = package.get("titles_cn") or []
    markdown = [f"# {story.get('title') or story_id}", ""]
    frame = package.get("productivity_frame")
    if isinstance(frame, dict):
        readiness_labels = {
            "use-now": "现在可用",
            "try-now": "可以试用",
            "watch": "暂时观望",
            "future": "长期趋势",
        }
        markdown.extend(
            [
                "## 这对工作有什么实际影响",
                "",
                f"- 适用人群：{frame.get('audience_cn', '')}",
                f"- 日常任务：{frame.get('work_task_cn', '')}",
                f"- 原来怎么做：{frame.get('old_workflow_cn', '')}",
                f"- 真正卡点：{frame.get('friction_cn', '')}",
                f"- AI 改变哪一步：{frame.get('ai_change_cn', '')}",
                f"- 现在怎么做：{frame.get('new_workflow_cn', '')}",
                f"- 人仍要负责：{frame.get('human_role_cn', '')}",
                "- 可用程度："
                f"{readiness_labels.get(str(frame.get('readiness') or ''), '未标注')}；"
                f"{frame.get('readiness_reason_cn', '')}",
                f"- 下一步：{frame.get('next_action_cn', '')}",
                "",
            ]
        )
    markdown.extend(["## 备选标题", ""])
    markdown.extend(f"- {title}" for title in titles)
    markdown.extend(["", "## 口播稿", "", narration, ""])
    (target / "script.md").write_text("\n".join(markdown), encoding="utf-8")
    bundle_hash = current_script_hash(
        root,
        {
            "script": {
                "package_path": f"{story['directory']}/script-package.json",
                "claim_ledger_path": f"{story['directory']}/claim-ledger.json",
                "narration_path": f"{story['directory']}/script.txt",
                "readable_path": f"{story['directory']}/script.md",
            }
        },
    )
    at = utc_now(args.at)
    story["script"] = {
        "package_path": f"{story['directory']}/script-package.json",
        "claim_ledger_path": f"{story['directory']}/claim-ledger.json",
        "narration_path": f"{story['directory']}/script.txt",
        "readable_path": f"{story['directory']}/script.md",
        "bundle_sha256": bundle_hash,
        "registered_at": at,
    }
    clear_after_script(story)
    story["status"] = "SCRIPT_DRAFT"
    record_event(project, at, "SCRIPT_REGISTERED", story_id, bundle_sha256=bundle_hash)
    save_project(root, project, at)
    print(target / "script.md")


def command_approve_script(args: argparse.Namespace) -> None:
    root, project = load_project(args.project)
    story_id, story = resolve_story(project, args.story)
    if story.get("status") != "SCRIPT_DRAFT":
        raise SystemExit("Register a validated script before approval")
    selected = read_json(require_selected_signal(root, story))
    bundle_hash = current_script_hash(root, story)
    if bundle_hash != story.get("script", {}).get("bundle_sha256"):
        raise SystemExit("Registered script artifacts changed; register and present the revised draft again")
    package = read_json(root / str(story["script"]["package_path"]))
    ledger = read_json(root / str(story["script"]["claim_ledger_path"]))
    errors, warnings = validate_package(package, ledger, selected)
    for message in warnings:
        print(f"WARN: {message}")
    if errors:
        raise SystemExit("Registered script no longer validates: " + "; ".join(errors))
    presentation = story.get("script", {}).get("presentation") or {}
    if presentation.get("bundle_sha256") != bundle_hash:
        raise SystemExit("Present the current full script to the user before recording approval")
    at = utc_now(args.at)
    story["script"]["approved_hash"] = bundle_hash
    story["script"]["approved_at"] = at
    story["script"]["approved_by"] = args.by
    clear_after_script(story)
    story["status"] = "SCRIPT_APPROVED"
    record_event(project, at, "SCRIPT_APPROVED", story_id, bundle_sha256=bundle_hash)
    save_project(root, project, at)
    print(json.dumps({"story_id": story_id, "status": story["status"]}))


def command_present_script(args: argparse.Namespace) -> None:
    root, project = load_project(args.project)
    story_id, story = resolve_story(project, args.story)
    if story.get("status") != "SCRIPT_DRAFT":
        raise SystemExit("Only the current draft can be presented for script approval")
    require_selected_signal(root, story)
    bundle_hash = current_script_hash(root, story)
    if bundle_hash != story.get("script", {}).get("bundle_sha256"):
        raise SystemExit("Script artifacts changed; register the draft again before presentation")
    at = utc_now(args.at)
    story["script"]["presentation"] = {
        "bundle_sha256": bundle_hash,
        "presented_at": at,
        "receipt": args.receipt,
    }
    record_event(project, at, "SCRIPT_PRESENTED", story_id, receipt=args.receipt)
    save_project(root, project, at)
    print(json.dumps({"story_id": story_id, "presented_hash": bundle_hash}))


def command_recheck(args: argparse.Namespace) -> None:
    root, project = load_project(args.project)
    story_id, story = resolve_story(project, args.story)
    if not story.get("script", {}).get("approved_hash"):
        raise SystemExit("Approve the script before the production source recheck")
    require_approved_script(root, story)
    source_manifest = args.manifest.expanduser().resolve()
    result, checked_at = validate_recheck_manifest(root, story, source_manifest)
    at = utc_now(args.at)
    target = story_dir(root, story) / "source-recheck.json"
    copy_file(source_manifest, target)
    story["source_recheck"] = {
        "result": result,
        "checked_at": checked_at,
        "manifest_path": relative_to_project(target, root),
        "manifest_sha256": sha256(target),
    }
    if result == "material-change":
        story["script"].pop("approved_hash", None)
        story["script"].pop("approved_at", None)
        story["script"].pop("approved_by", None)
        clear_after_recheck(story)
        story["status"] = "SCRIPT_DRAFT"
        event = "SOURCE_CHANGE_INVALIDATED_SCRIPT"
    else:
        clear_after_recheck(story)
        story["status"] = "SCRIPT_APPROVED"
        event = "SOURCE_RECHECK_PASSED"
    record_event(project, at, event, story_id, manifest_path=relative_to_project(target, root))
    save_project(root, project, at)
    print(json.dumps({"story_id": story_id, "status": story["status"]}))


def validate_preview_inputs(args: argparse.Namespace, story_id: str) -> None:
    scene_plan = read_json(args.scene_plan.expanduser().resolve())
    read_json(args.source_ledger.expanduser().resolve())
    voice = read_json(args.voice_manifest.expanduser().resolve())
    if not isinstance(voice.get("duration"), (int, float)) or voice.get("duration", 0) <= 0:
        raise SystemExit("Voice manifest requires a positive measured duration")

    captions = read_json(args.caption_manifest.expanduser().resolve())
    caption_errors, caption_warnings = validate_caption_manifest(captions, voice)
    for message in caption_warnings:
        print(f"WARN: {message}")
    if caption_errors:
        raise SystemExit("Invalid timed captions: " + "; ".join(caption_errors))

    audition = read_json(args.voice_audition.expanduser().resolve())
    audition_errors = validate_voice_audition(audition)
    if audition_errors:
        raise SystemExit("Invalid voice audition: " + "; ".join(audition_errors))
    approved_candidate = next(
        (
            item
            for item in audition.get("candidates") or []
            if isinstance(item, dict)
            and item.get("id") == (audition.get("approval") or {}).get("candidate_id")
        ),
        None,
    )
    manifest_voice_id = str(voice.get("voiceId") or voice.get("voice_id") or "")
    if approved_candidate and str(approved_candidate.get("voice_id") or "") != manifest_voice_id:
        raise SystemExit("Synthesized voice does not match the approved audition candidate")
    if approved_candidate and str(approved_candidate.get("provider") or "") != str(voice.get("provider") or ""):
        raise SystemExit("Synthesized voice provider does not match the approved audition candidate")
    delivery_spec = read_json(args.delivery_spec.expanduser().resolve())
    if (audition.get("approval") or {}).get("receipt") != (delivery_spec.get("voice") or {}).get("approval_receipt"):
        raise SystemExit("Voice audition approval receipt does not match delivery spec")

    director_errors = validate_director_pack(
        args.director_treatment,
        args.director_board,
        args.director_frames,
    )
    if director_errors:
        raise SystemExit("Invalid Visual Director pack: " + "; ".join(director_errors))

    counts = {
        "story files": len(args.story_files),
        "review manifests": len(args.review_manifests),
        "covers": len(args.covers),
        "opening previews": len(args.openings),
        "review boards": len(args.boards),
        "transition reviews": len(args.transition_reviews),
        "transition boards": len(args.transition_boards),
    }
    if len(set(counts.values())) != 1:
        raise SystemExit(
            "Each delivery profile requires one story, review manifest, cover, opening, "
            "review board, transition review, and transition board: " + json.dumps(counts)
        )

    stories = [read_json(path.expanduser().resolve()) for path in args.story_files]
    reviews = [read_json(path.expanduser().resolve()) for path in args.review_manifests]
    story_ratios = [str(item.get("aspectRatio") or "") for item in stories]
    if any(not ratio for ratio in story_ratios) or len(set(story_ratios)) != len(story_ratios):
        raise SystemExit("Render stories require unique aspectRatio values")
    profiles = scene_plan.get("deliveryProfiles")
    planned_ratios = {
        str(item.get("aspectRatio"))
        for item in profiles or []
        if isinstance(item, dict) and item.get("aspectRatio")
    }
    if not set(story_ratios).issubset(planned_ratios):
        raise SystemExit("scene-plan deliveryProfiles do not cover every render story ratio")

    passed_covers = {path.expanduser().resolve() for path in args.covers}
    passed_openings = {path.expanduser().resolve() for path in args.openings}
    passed_boards = {path.expanduser().resolve() for path in args.boards}
    review_ratios: list[str] = []
    for path, review, story_value in zip(args.review_manifests, reviews, stories):
        review_ratios.append(str(review.get("aspectRatio") or ""))
        if review.get("aspectRatio") != story_value.get("aspectRatio"):
            raise SystemExit(f"Review/story profile ordering mismatch: {path}")
        video_root = path.expanduser().resolve().parent.parent
        expected = {
            "cover": (video_root / str(review.get("cover") or "")).resolve(),
            "opening": (video_root / str(review.get("openingPreview") or "")).resolve(),
            "board": (video_root / str(review.get("reviewBoard") or "")).resolve(),
        }
        if expected["cover"] not in passed_covers:
            raise SystemExit(f"Review manifest cover was not registered: {expected['cover']}")
        if expected["opening"] not in passed_openings:
            raise SystemExit(f"Review manifest opening was not registered: {expected['opening']}")
        if expected["board"] not in passed_boards:
            raise SystemExit(f"Review manifest board was not registered: {expected['board']}")
        if not isinstance(review.get("timelineDurationSeconds"), (int, float)):
            raise SystemExit(f"Review manifest has no measured timeline duration: {path}")
        if "publicationBlockers" not in review:
            raise SystemExit(f"Review manifest has no publicationBlockers field: {path}")
    if set(review_ratios) != set(story_ratios):
        raise SystemExit("Review manifest ratios do not match render story ratios")

    passed_transition_boards = {path.expanduser().resolve() for path in args.transition_boards}
    transition_ratios: list[str] = []
    for index, (path, transition, story_value) in enumerate(zip(
        args.transition_reviews,
        [read_json(item.expanduser().resolve()) for item in args.transition_reviews],
        stories,
    )):
        errors = validate_transition_manifest(transition, story_value)
        if errors:
            raise SystemExit(f"Invalid transition review {path}: " + "; ".join(errors))
        story_path = args.story_files[len(transition_ratios)].expanduser().resolve()
        if transition.get("story_sha256") != sha256(story_path):
            raise SystemExit(f"Transition review does not match render story: {path}")
        if transition.get("composition") != reviews[index].get("composition"):
            raise SystemExit(f"Transition review composition does not match review package: {path}")
        board = (path.expanduser().resolve().parent.parent / str(transition["board"])).resolve()
        if board not in passed_transition_boards:
            raise SystemExit(f"Transition review board was not registered: {board}")
        transition_ratios.append(str(story_value.get("aspectRatio") or ""))

    for path in args.covers + args.boards:
        resolved = path.expanduser().resolve()
        if not is_image(resolved):
            raise SystemExit(f"Not a recognized image artifact: {resolved}")
    for path in args.transition_boards:
        resolved = path.expanduser().resolve()
        if not is_image(resolved):
            raise SystemExit(f"Not a recognized transition board: {resolved}")
    for path in args.openings:
        probe = ffprobe(path.expanduser().resolve())
        if not any(stream.get("codec_type") == "video" for stream in probe.get("streams") or []):
            raise SystemExit(f"Opening preview has no video stream: {path}")

    registered_assets = {path.expanduser().resolve() for path in args.assets}
    for path, story_value in zip(args.story_files, stories):
        public = path.expanduser().resolve().parent.parent / "public"
        referenced = set()
        audio = story_value.get("audio")
        if audio:
            referenced.add((public / str(audio)).resolve())
        for scene in story_value.get("scenes") or []:
            if not isinstance(scene, dict):
                continue
            for key in ("primary", "secondary", "cutout"):
                if scene.get(key):
                    referenced.add((public / str(scene[key])).resolve())
        missing = sorted(str(item) for item in referenced - registered_assets)
        if missing:
            raise SystemExit("Story assets were not registered: " + ", ".join(missing))

    contract_errors, contract_warnings = validate_contract(
        args.delivery_spec,
        args.story_files,
        args.review_manifests,
        args.voice_manifest,
        args.caption_manifest,
        args.source_ledger,
        story_id,
    )
    for message in contract_warnings:
        print(f"WARN: {message}")
    if contract_errors:
        raise SystemExit("Delivery contract mismatch: " + "; ".join(contract_errors))


def command_mark_preview(args: argparse.Namespace) -> None:
    root, project = load_project(args.project)
    story_id, story = resolve_story(project, args.story)
    script_hash = require_approved_script(root, story)
    require_fresh_recheck(root, story)
    require_selected_signal(root, story)
    validate_preview_inputs(args, story_id)
    validate_remotion_source_closure(args.remotion_src_dir)
    grouped: list[tuple[str, list[Path]]] = [
        ("scene-plan", [args.scene_plan]),
        ("delivery-spec", [args.delivery_spec]),
        ("source-ledger", [args.source_ledger]),
        ("voice-manifest", [args.voice_manifest]),
        ("caption-manifest", [args.caption_manifest]),
        ("voice-audition", [args.voice_audition]),
        ("director-treatment", [args.director_treatment]),
        ("director-board", [args.director_board]),
        ("director-frame", args.director_frames),
        ("source-recheck", [root / str(story["source_recheck"]["manifest_path"])]),
        ("review-manifest", args.review_manifests),
        ("transition-review", args.transition_reviews),
        ("transition-board", args.transition_boards),
        ("render-story", args.story_files),
        ("render-config", args.render_configs),
        ("source-asset", args.assets),
        ("cover", args.covers),
        ("opening-preview", args.openings),
        ("review-board", args.boards),
        ("extra", args.files or []),
    ]
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for role, values in grouped:
        for value in values:
            path = value.expanduser().resolve()
            if not path.is_file():
                raise SystemExit(f"Missing {role} artifact: {path}")
            relative = relative_to_project(path, root)
            if relative in seen:
                raise SystemExit(f"Duplicate preview/production artifact: {relative}")
            seen.add(relative)
            records.append({"role": role, "path": relative, "sha256": sha256(path)})
    tree_roles = [("remotion-source-tree", args.remotion_src_dir)]
    for role, directory in tree_roles:
        record = tree_record(directory, root, role)
        if record["path"] in seen:
            raise SystemExit(f"Duplicate preview/production artifact: {record['path']}")
        seen.add(record["path"])
        records.append(record)
    at = utc_now(args.at)
    story["preview"] = {
        "registered_at": at,
        "artifacts": records,
        "bundle_sha256": hash_records(records),
        "script_sha256": script_hash,
    }
    story.pop("render_approval", None)
    story.pop("final", None)
    story["status"] = "PREVIEW_READY"
    record_event(project, at, "PREVIEW_READY", story_id, artifact_count=len(records))
    save_project(root, project, at)
    print(json.dumps({"story_id": story_id, "status": story["status"]}))


def command_present_preview(args: argparse.Namespace) -> None:
    root, project = load_project(args.project)
    story_id, story = resolve_story(project, args.story)
    if story.get("status") != "PREVIEW_READY":
        raise SystemExit("Only the latest ready preview can be presented for render approval")
    require_approved_script(root, story)
    require_fresh_recheck(root, story)
    preview = story.get("preview") or {}
    bundle_hash = verify_artifact_records(root, preview.get("artifacts") or [])
    if bundle_hash != preview.get("bundle_sha256"):
        raise SystemExit("Preview artifacts changed; register a new preview package")
    at = utc_now(args.at)
    preview["presentation"] = {
        "bundle_sha256": bundle_hash,
        "presented_at": at,
        "receipt": args.receipt,
    }
    record_event(project, at, "PREVIEW_PRESENTED", story_id, receipt=args.receipt)
    save_project(root, project, at)
    print(json.dumps({"story_id": story_id, "presented_hash": bundle_hash}))


def command_approve_render(args: argparse.Namespace) -> None:
    root, project = load_project(args.project)
    story_id, story = resolve_story(project, args.story)
    if story.get("status") != "PREVIEW_READY":
        raise SystemExit("The latest review package is not ready for approval")
    script_hash = require_approved_script(root, story)
    require_fresh_recheck(root, story)
    preview = story.get("preview") or {}
    preview_hash = verify_artifact_records(root, preview.get("artifacts") or [])
    if preview_hash != preview.get("bundle_sha256"):
        raise SystemExit("Preview artifact bundle no longer matches the reviewed version")
    presentation = preview.get("presentation") or {}
    if presentation.get("bundle_sha256") != preview_hash:
        raise SystemExit("Present the latest review package to the user before render approval")
    at = utc_now(args.at)
    story["render_approval"] = {
        "approved_at": at,
        "approved_by": args.by,
        "script_sha256": script_hash,
        "preview_sha256": preview_hash,
    }
    story["status"] = "RENDER_APPROVED"
    record_event(project, at, "FULL_RENDER_APPROVED", story_id)
    save_project(root, project, at)
    print(json.dumps({"story_id": story_id, "status": story["status"]}))


def validate_cost_manifest(path: Path, render: Path) -> dict[str, Any]:
    value = read_json(path)
    if value.get("schema_version") != 1:
        raise SystemExit("Cost manifest requires schema_version: 1")
    llm = value.get("llm") or {}
    if llm.get("status") not in {"measured", "unavailable"}:
        raise SystemExit("Cost manifest must record measured or unavailable LLM usage")
    if llm.get("status") == "unavailable" and not str(llm.get("unavailable_reason") or "").strip():
        raise SystemExit("Unavailable token usage requires an explicit reason")
    render_usage = value.get("render") or {}
    if render_usage.get("llm_tokens") != 0:
        raise SystemExit("Cost manifest must distinguish local rendering from LLM token usage")
    recorded_render = Path(str(render_usage.get("path") or "")).expanduser().resolve()
    if recorded_render != render:
        raise SystemExit("Cost manifest belongs to another final render")
    if render_usage.get("sha256") != sha256(render):
        raise SystemExit("Cost manifest was not measured from the current final render")
    return value


def complete_story(args: argparse.Namespace, scope: str) -> None:
    root, project = load_project(args.project)
    story_id, story = resolve_story(project, args.story)
    if story.get("status") != "RENDER_APPROVED":
        raise SystemExit("Full render has not been explicitly approved")
    script_hash = require_approved_script(root, story)
    preview = story.get("preview") or {}
    preview_hash = verify_artifact_records(root, preview.get("artifacts") or [])
    approval = story.get("render_approval") or {}
    if script_hash != approval.get("script_sha256") or preview_hash != approval.get("preview_sha256"):
        raise SystemExit("Approved inputs changed; obtain a new render approval")
    render = args.render.expanduser().resolve()
    if not render.is_file():
        raise SystemExit(f"Missing final render: {render}")
    probe = ffprobe(render)
    if not any(stream.get("codec_type") == "video" for stream in probe.get("streams") or []):
        raise SystemExit("Final render has no video stream")
    if not any(stream.get("codec_type") == "audio" for stream in probe.get("streams") or []):
        raise SystemExit("Final render has no audio stream")
    story_file = args.story_file.expanduser().resolve()
    source_ledger = args.source_ledger.expanduser().resolve()
    visual_review = args.visual_review.expanduser().resolve()
    qa_report = args.qa_report.expanduser().resolve()
    for path in (story_file, source_ledger, visual_review):
        if not path.is_file():
            raise SystemExit(f"Missing final QA input: {path}")
    require_registered_artifact(root, story, "render-story", story_file)
    require_registered_artifact(root, story, "source-ledger", source_ledger)
    delivery_spec = read_json(registered_artifact(root, story, "delivery-spec"))
    if delivery_spec.get("delivery_scope") != scope:
        raise SystemExit(
            f"Delivery spec is locked for {delivery_spec.get('delivery_scope')}; "
            f"cannot complete it as {scope}"
        )
    relative_to_project(qa_report, root)
    verifier = Path(__file__).resolve().parent / "verify_final_video.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(verifier),
            str(render),
            str(story_file),
            str(source_ledger),
            "--story-id",
            story_id,
            "--visual-review",
            str(visual_review),
            "--output",
            str(qa_report),
            "--scope",
            scope,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise SystemExit("Final video verification failed:\n" + completed.stdout + completed.stderr)
    report = read_json(qa_report)
    if report.get("schema_version") != 1 or report.get("status") != "passed":
        raise SystemExit("Final QA report must be schema version 1 with status: passed")
    if report.get("story_id") != story_id:
        raise SystemExit("Final QA report belongs to another story")
    if report.get("final_video_sha256") != sha256(render):
        raise SystemExit("Final QA report does not match the final render")
    if report.get("delivery_scope") != scope or report.get("full_decode") != "passed":
        raise SystemExit("Final QA report must match delivery scope and pass full decode")
    if scope == "public" and report.get("publication_validation") != "passed":
        raise SystemExit("Public final QA must pass publication validation")
    if scope == "internal" and report.get("publication_validation") not in {"passed", "blocked"}:
        raise SystemExit("Internal final QA must record publication readiness")
    visual = report.get("visual_review") or {}
    required_visual = {
        "opening_reviewed",
        "transitions_reviewed",
        "final_frame_reviewed",
        "captions_reviewed",
        "caption_timing_reviewed",
        "audio_gaps_reviewed",
        "transition_midpoints_reviewed",
        "safe_areas_reviewed",
        "rights_attributions_reviewed",
    }
    if any(visual.get(key) is not True for key in required_visual):
        raise SystemExit("Final QA report is missing a required visual review pass")
    render_relative = relative_to_project(render, root)
    report_relative = relative_to_project(qa_report, root)
    cost_manifest = args.cost_manifest.expanduser().resolve()
    if not cost_manifest.is_file():
        raise SystemExit(f"Missing cost manifest: {cost_manifest}")
    relative_to_project(cost_manifest, root)
    validate_cost_manifest(cost_manifest, render)
    at = utc_now(args.at)
    story["final"] = {
        "delivery_scope": scope,
        "render_path": render_relative,
        "sha256": sha256(render),
        "qa_report_path": report_relative,
        "qa_report_sha256": sha256(qa_report),
        "cost_manifest_path": relative_to_project(cost_manifest, root),
        "cost_manifest_sha256": sha256(cost_manifest),
        "completed_at": at,
    }
    story["status"] = "COMPLETED" if scope == "public" else "COMPLETED_INTERNAL"
    event = "STORY_COMPLETED" if scope == "public" else "STORY_COMPLETED_INTERNAL"
    record_event(project, at, event, story_id, render_path=render_relative)
    save_project(root, project, at)
    print(render)


def command_complete(args: argparse.Namespace) -> None:
    complete_story(args, "public")


def command_complete_internal(args: argparse.Namespace) -> None:
    complete_story(args, "internal")


def command_status(args: argparse.Namespace) -> None:
    root, project = load_project(args.project)
    integrity = audit_project(root, project)
    if args.story:
        story_id, story = resolve_story(project, args.story)
        story_errors = [item for item in integrity["errors"] if item.startswith(f"{story_id}:")]
        if args.summary:
            final = story.get("final") or {}
            print(
                json.dumps(
                    {
                        "story_id": story_id,
                        "rank": story.get("radar_rank"),
                        "title": story.get("title"),
                        "status": story.get("status"),
                        "delivery_scope": final.get("delivery_scope"),
                        "final_render": final.get("render_path"),
                        "integrity": {"ok": not story_errors, "errors": story_errors},
                    },
                    ensure_ascii=False,
                )
            )
            return
        print(
            json.dumps(
                {"story_id": story_id, **story, "integrity": {"ok": not story_errors, "errors": story_errors}},
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if args.summary:
        stories = []
        for story_id, story in (project.get("stories") or {}).items():
            final = story.get("final") or {}
            stories.append(
                {
                    "story_id": story_id,
                    "rank": story.get("radar_rank"),
                    "title": story.get("title"),
                    "status": story.get("status"),
                    "delivery_scope": final.get("delivery_scope"),
                    "final_render": final.get("render_path"),
                }
            )
        print(
            json.dumps(
                {
                    "project_id": project.get("project_id"),
                    "title": project.get("title"),
                    "radar_status": (project.get("radar") or {}).get("status"),
                    "stories": stories,
                    "integrity": integrity,
                },
                ensure_ascii=False,
            )
        )
        return
    print(json.dumps({**project, "integrity": integrity}, ensure_ascii=False, indent=2))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    subparsers = result.add_subparsers(dest="command", required=True)

    command = subparsers.add_parser("init")
    command.add_argument("project", type=Path)
    command.add_argument("--title", required=True)
    command.add_argument("--project-id")
    command.add_argument("--at")
    command.set_defaults(handler=command_init)

    command = subparsers.add_parser("import-radar")
    command.add_argument("project", type=Path)
    command.add_argument("signals", type=Path)
    command.add_argument("--candidates", type=Path)
    command.add_argument("--brief", type=Path, required=True)
    command.add_argument("--at")
    command.set_defaults(handler=command_import_radar)

    command = subparsers.add_parser("select")
    command.add_argument("project", type=Path)
    command.add_argument("ranks", nargs="+")
    command.add_argument("--at")
    command.set_defaults(handler=command_select)

    command = subparsers.add_parser("register-script")
    command.add_argument("project", type=Path)
    command.add_argument("story")
    command.add_argument("--package", type=Path, required=True)
    command.add_argument("--ledger", type=Path, required=True)
    command.add_argument("--at")
    command.set_defaults(handler=command_register_script)

    command = subparsers.add_parser("present-script")
    command.add_argument("project", type=Path)
    command.add_argument("story")
    command.add_argument("--receipt", required=True)
    command.add_argument("--at")
    command.set_defaults(handler=command_present_script)

    command = subparsers.add_parser("approve-script")
    command.add_argument("project", type=Path)
    command.add_argument("story")
    command.add_argument("--by", default="user")
    command.add_argument("--at")
    command.set_defaults(handler=command_approve_script)

    command = subparsers.add_parser("recheck")
    command.add_argument("project", type=Path)
    command.add_argument("story")
    command.add_argument("--manifest", type=Path, required=True)
    command.add_argument("--at")
    command.set_defaults(handler=command_recheck)

    command = subparsers.add_parser("mark-preview")
    command.add_argument("project", type=Path)
    command.add_argument("story")
    command.add_argument("--scene-plan", type=Path, required=True)
    command.add_argument("--delivery-spec", type=Path, required=True)
    command.add_argument("--source-ledger", type=Path, required=True)
    command.add_argument("--voice-manifest", type=Path, required=True)
    command.add_argument("--caption-manifest", type=Path, required=True)
    command.add_argument("--voice-audition", type=Path, required=True)
    command.add_argument("--director-treatment", type=Path, required=True)
    command.add_argument("--director-board", type=Path, required=True)
    command.add_argument(
        "--director-frame",
        dest="director_frames",
        action="append",
        type=Path,
        required=True,
    )
    command.add_argument(
        "--review-manifest",
        dest="review_manifests",
        action="append",
        type=Path,
        required=True,
    )
    command.add_argument("--story-file", dest="story_files", action="append", type=Path, required=True)
    command.add_argument("--remotion-src-dir", type=Path, required=True)
    command.add_argument(
        "--render-config",
        dest="render_configs",
        action="append",
        type=Path,
        required=True,
    )
    command.add_argument("--asset", dest="assets", action="append", type=Path, required=True)
    command.add_argument("--cover", dest="covers", action="append", type=Path, required=True)
    command.add_argument("--opening", dest="openings", action="append", type=Path, required=True)
    command.add_argument("--board", dest="boards", action="append", type=Path, required=True)
    command.add_argument(
        "--transition-review",
        dest="transition_reviews",
        action="append",
        type=Path,
        required=True,
    )
    command.add_argument(
        "--transition-board",
        dest="transition_boards",
        action="append",
        type=Path,
        required=True,
    )
    command.add_argument("--file", dest="files", action="append", type=Path)
    command.add_argument("--at")
    command.set_defaults(handler=command_mark_preview)

    command = subparsers.add_parser("present-preview")
    command.add_argument("project", type=Path)
    command.add_argument("story")
    command.add_argument("--receipt", required=True)
    command.add_argument("--at")
    command.set_defaults(handler=command_present_preview)

    command = subparsers.add_parser("approve-render")
    command.add_argument("project", type=Path)
    command.add_argument("story")
    command.add_argument("--by", default="user")
    command.add_argument("--at")
    command.set_defaults(handler=command_approve_render)

    for name, handler in (
        ("complete", command_complete),
        ("complete-internal", command_complete_internal),
    ):
        command = subparsers.add_parser(name)
        command.add_argument("project", type=Path)
        command.add_argument("story")
        command.add_argument("--render", type=Path, required=True)
        command.add_argument("--story-file", type=Path, required=True)
        command.add_argument("--source-ledger", type=Path, required=True)
        command.add_argument("--visual-review", type=Path, required=True)
        command.add_argument("--qa-report", type=Path, required=True)
        command.add_argument("--cost-manifest", type=Path, required=True)
        command.add_argument("--at")
        command.set_defaults(handler=handler)

    command = subparsers.add_parser("status")
    command.add_argument("project", type=Path)
    command.add_argument("--story")
    command.add_argument("--summary", action="store_true")
    command.set_defaults(handler=command_status)
    return result


def main() -> int:
    args = parser().parse_args()
    args.handler(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
