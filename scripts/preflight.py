#!/usr/bin/env python3
"""Check the local runtime needed by AceMode Newsroom stages."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


def keychain(service: str) -> bool:
    security = shutil.which("security")
    if not security:
        return False
    result = subprocess.run(
        [security, "find-generic-password", "-a", os.environ.get("USER", ""), "-s", service, "-w"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("radar", "script", "video"), default="video")
    parser.add_argument("--with-tts", action="store_true")
    parser.add_argument("--video-project", type=Path)
    parser.add_argument("--browser-executable", type=Path)
    parser.add_argument(
        "--allow-browser-download",
        action="store_true",
        help="Allow preflight to accept Remotion's later managed browser download",
    )
    args = parser.parse_args()

    required = ["python3"]
    if args.stage == "video":
        required.extend(["node", "npm", "ffmpeg", "ffprobe"])
    commands = {name: shutil.which(name) for name in required}
    missing = [name for name, path in commands.items() if not path]
    remotion = None
    if args.stage == "video" and args.video_project:
        video_project = args.video_project.expanduser().resolve()
        cli = video_project / "node_modules" / ".bin" / "remotion"
        lockfile = video_project / "package-lock.json"
        requested_browser = args.browser_executable or (
            Path(os.environ["REMOTION_BROWSER_EXECUTABLE"])
            if os.environ.get("REMOTION_BROWSER_EXECUTABLE")
            else None
        )
        discovered_browsers = [
            Path(value)
            for value in (
                shutil.which("google-chrome"),
                shutil.which("chromium"),
                shutil.which("chromium-browser"),
                shutil.which("msedge"),
            )
            if value
        ]
        candidates = (
            [requested_browser]
            if requested_browser
            else [
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
                *discovered_browsers,
            ]
        )
        browser = next((str(path.expanduser().resolve()) for path in candidates if path and path.expanduser().is_file()), None)
        remotion = {
            "project": str(video_project),
            "local_cli": str(cli) if cli.is_file() else None,
            "lockfile": str(lockfile) if lockfile.is_file() else None,
            "browser_executable": browser,
            "browser_download_allowed": args.allow_browser_download,
        }
        if not cli.is_file():
            missing.append("project-local Remotion CLI (run npm ci)")
        if not lockfile.is_file():
            missing.append("package-lock.json")
        if requested_browser and not requested_browser.expanduser().is_file():
            missing.append(f"requested browser executable: {requested_browser}")
        elif not browser and not args.allow_browser_download:
            missing.append("Chrome/Chromium executable or --allow-browser-download")
    tts = None
    if args.with_tts:
        app_id = bool(os.environ.get("VOLCANO_APP_ID")) or keychain("codex-volcano-app-id")
        token = bool(os.environ.get("VOLCANO_ACCESS_TOKEN")) or keychain("codex-volcano-access-token")
        tts = {"app_id_available": app_id, "access_token_available": token}
        if not app_id or not token:
            missing.append("Volcengine TTS credentials")
    result = {"ok": not missing, "stage": args.stage, "commands": commands, "remotion": remotion, "tts": tts, "missing": missing}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
