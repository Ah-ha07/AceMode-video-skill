from __future__ import annotations

import json
import base64
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "scripts" / "newsroom_state.py"
VALIDATOR = ROOT / "scripts" / "validate_script_package.py"
CAPTIONS = ROOT / "scripts" / "caption_pipeline.py"
STORY_VALIDATOR = ROOT / "scripts" / "validate_story.py"
TRANSITIONS = ROOT / "scripts" / "build_transition_review.py"
CLOSING = "这里是 AceMode，帮你把新工具变成真正能用的生产力。"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signal() -> dict:
    return {
        "id": "model-release",
        "rank": 1,
        "event_key": "company-model-release-date",
        "entity": "Example AI",
        "title": "Example AI releases a model",
        "event_time": "2026-08-12T08:00:00Z",
        "verification": "verified",
        "audience_cn": "需要维护代码的小团队",
        "work_task_cn": "完成一个有测试保护的小修复",
        "old_workflow_cn": "人工搜索、修改、运行测试并整理说明",
        "friction_cn": "重复定位和整理挤占了审查时间",
        "ai_change_cn": "AI 可以执行搜索、修改与测试并保留过程",
        "new_workflow_cn": "人定标准，AI 执行，人审查差异和结果",
        "human_role_cn": "决定目标并对合并结果负责",
        "readiness": "try-now",
        "readiness_reason_cn": "可用于低风险任务，但仍需审查",
        "next_action_cn": "先在有测试的小修复上做对比",
        "sources": [
            {
                "platform": "official",
                "source_name": "Example AI",
                "url": "https://example.com/model-release",
                "supports_cn": "证实模型发布和官方范围。",
                "is_primary": True,
            }
        ],
    }


def package(hook: str = "如果你维护一个小项目，最耗时间的往往不是改代码，而是反复找文件和跑检查。") -> dict:
    old_workflow = "过去你要自己搜索文件、修改代码、运行测试，再整理提交说明。"
    fact = "官方已经发布新模型，并展示了连续搜索、修改和检查的能力。"
    new_workflow = "新的分工是人先写清验收标准，AI 执行重复步骤，人再审查差异和测试结果。"
    boundary = "它现在适合在有测试保护的低风险任务中试用，最终合并仍由人负责。"
    action = "先选一个做过的小修复，用同一任务比较时间、错误和返工。"
    return {
        "schema_version": 2,
        "source_signal_id": "model-release",
        "radar_rank": 1,
        "persona_id": "acemode-productivity-editor-v1",
        "target_duration_seconds": 55,
        "story_promise_cn": "帮助开发者判断是否值得迁移。",
        "productivity_frame": {
            "audience_cn": "需要维护代码的小团队",
            "work_task_cn": "完成一个有测试保护的小修复",
            "old_workflow_cn": "人工搜索、修改、运行测试并整理说明",
            "friction_cn": "重复定位和整理挤占了审查时间",
            "ai_change_cn": "AI 可以执行搜索、修改与测试并保留过程",
            "new_workflow_cn": "人定标准，AI 执行，人审查差异和结果",
            "human_role_cn": "决定目标、审查代码并对合并结果负责",
            "readiness": "try-now",
            "readiness_reason_cn": "可用于有测试的低风险任务，但仍需人工审查",
            "next_action_cn": "先在一个做过的小修复上做同任务对比",
        },
        "titles_cn": ["迁移别只看跑分", "新模型值不值得换", "失败恢复才是关键", "一次更新两种判断", "先别急着迁移模型"],
        "segments": [
            {"id": "seg-01", "role": "hook", "text_cn": hook, "claim_refs": ["claim-01"]},
            {"id": "seg-02", "role": "old-workflow", "text_cn": old_workflow, "claim_refs": ["claim-01"]},
            {"id": "seg-03", "role": "news", "text_cn": fact, "claim_refs": ["claim-01"]},
            {"id": "seg-04", "role": "new-workflow", "text_cn": new_workflow, "claim_refs": ["claim-01"]},
            {"id": "seg-05", "role": "boundary", "text_cn": boundary, "claim_refs": ["claim-01"]},
            {"id": "seg-06", "role": "action", "text_cn": action, "claim_refs": ["claim-01"]},
            {"id": "seg-07", "role": "closing", "text_cn": CLOSING, "claim_refs": []},
        ],
        "narration_cn": "\n".join([hook, old_workflow, fact, new_workflow, boundary, action, CLOSING]),
        "closing_text_cn": CLOSING,
    }


def ledger() -> dict:
    return {
        "schema_version": 1,
        "source_signal_id": "model-release",
        "sources": [
            {
                "id": "src-01",
                "url": "https://example.com/model-release",
                "source_name": "Example AI",
                "supports_cn": "证实模型发布和官方范围。",
                "verification": "verified",
                "from_radar": True,
            }
        ],
        "claims": [
            {
                "id": "claim-01",
                "text_cn": "Example AI 发布了新模型。",
                "kind": "fact",
                "source_ids": ["src-01"],
                "boundary_cn": "官方发布不等于独立实测。",
                "recheck_before_production": True,
            }
        ],
    }


def preview_arguments(story: Path) -> list[str]:
    video = story / "video"
    primary = video / "public" / "assets" / "primary.svg"
    secondary = video / "public" / "assets" / "secondary.svg"
    for path in (primary, secondary):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg' width='320' height='180'/>", encoding="utf-8")
    scene_plan = video / "scene-plan.json"
    write_json(
        scene_plan,
        {
            "schemaVersion": 2,
            "deliveryProfiles": [{"id": "16x9", "aspectRatio": "16:9", "width": 320, "height": 180}],
        },
    )
    source_ledger = video / "source-ledger.json"
    write_json(
        source_ledger,
        {
            "assets": [
                {
                    "id": "asset-1",
                    "localPath": "assets/primary.svg",
                    "sourceUrl": "https://example.com/primary",
                    "license": "CC0",
                    "attribution": "Example",
                    "factualRole": "Direct evidence fixture",
                    "ingestStatus": "approved",
                    "publicationStatus": "cleared",
                    "usageScope": "test",
                    "replacementRequiredBeforePublish": False,
                },
                {
                    "id": "asset-2",
                    "localPath": "assets/secondary.svg",
                    "sourceUrl": "https://example.com/secondary",
                    "license": "CC0",
                    "attribution": "Example",
                    "factualRole": "Context fixture",
                    "ingestStatus": "approved",
                    "publicationStatus": "cleared",
                    "usageScope": "test",
                    "replacementRequiredBeforePublish": False,
                },
            ]
        },
    )
    voice = video / "audio" / "tts-manifest.json"
    write_json(
        voice,
        {
            "provider": "volcano",
            "voiceId": "voice-sophie",
            "language": "en-US",
            "duration": 1.0,
            "timingUnit": "seconds",
            "segments": [
                {
                    "sentences": [
                        {"text": "Work faster.", "startTime": 0.0, "endTime": 1.0}
                    ]
                }
            ],
        },
    )
    captions = video / "src" / "captions.json"
    write_json(
        captions,
        {
            "schema_version": 1,
            "language": "en-US",
            "timing_source": "tts-manifest",
            "source_voice_manifest_sha256": sha256(voice),
            "cue_count": 1,
            "cues": [{"text": "Work faster.", "startMs": 0, "endMs": 1000}],
        },
    )
    story_file = video / "src" / "story.json"
    write_json(
        story_file,
        {
            "schemaVersion": 2,
            "fps": 30,
            "width": 320,
            "height": 180,
            "aspectRatio": "16:9",
            "transitionMode": "opaque-cut",
            "targetDurationSeconds": 1,
            "durationToleranceSeconds": 0,
            "totalFrames": 30,
            "audio": None,
            "scenes": [
                {
                    "id": "scene-1",
                    "from": 0,
                    "duration": 30,
                    "kicker": "TEST",
                    "headline": "测试",
                    "meta": "SOURCE",
                    "stat": "1",
                    "statLabel": "TEST",
                    "caption": "测试字幕",
                    "primary": "assets/primary.svg",
                    "secondary": "assets/secondary.svg",
                    "accent": "teal",
                    "layout": "stat-left",
                    "emotion": "focus",
                    "energy": 3,
                    "motionBudget": "medium",
                    "readingWindowFrames": 20,
                    "focalAnchor": "center",
                    "coverFrame": True,
                    "openingMotion": "cover-impact",
                }
            ],
        },
    )
    remotion = video / "src" / "EditorialDocumentary.jsx"
    remotion.write_text("export const Fixture = () => null;\n", encoding="utf-8")
    package_json = video / "package.json"
    package_lock = video / "package-lock.json"
    write_json(package_json, {"name": "fixture", "version": "1.0.0"})
    write_json(package_lock, {"name": "fixture", "lockfileVersion": 3, "packages": {}})
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
    cover = video / "qa" / "cover.png"
    board = video / "qa" / "board.png"
    for path in (cover, board):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png)
    opening = video / "qa" / "opening.mp4"
    opening.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=320x180:r=30:d=0.2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", str(opening)],
        check=True,
    )
    review = video / "qa" / "review-package.json"
    write_json(
        review,
        {
            "composition": "EditorialDocumentary",
            "aspectRatio": "16:9",
            "timelineDurationSeconds": 1,
            "cover": "qa/cover.png",
            "openingPreview": "qa/opening.mp4",
            "reviewBoard": "qa/board.png",
            "publicationBlockers": [],
        },
    )
    delivery_spec = video / "delivery-spec.json"
    write_json(
        delivery_spec,
        {
            "schema_version": 1,
            "story_id": "01-model-release",
            "language": "en-US",
            "target_duration_seconds": 1,
            "delivery_scope": "public",
            "transition_mode": "opaque-cut",
            "profiles": [
                {"id": "16x9", "aspect_ratio": "16:9", "width": 320, "height": 180, "composition": "EditorialDocumentary"}
            ],
            "voice": {"provider": "volcano", "voice_id": "voice-sophie", "approval_basis": "audition", "approval_receipt": "voice-approved"},
            "captions": {"required": True, "language": "en-US", "timing_source": "tts-manifest", "max_lines": 2},
            "brand": {"enabled": False, "profile": None, "approval_receipt": None},
            "director_approval_receipt": "director-approved",
        },
    )
    voice_audition = video / "audio" / "voice-audition.json"
    write_json(
        voice_audition,
        {
            "schema_version": 1,
            "candidates": [{"id": "sophie", "provider": "volcano", "voice_id": "voice-sophie", "audio_path": str(opening), "sha256": sha256(opening)}],
            "approval": {"candidate_id": "sophie", "receipt": "voice-approved", "approved_by": "user"},
        },
    )
    director_treatment = video / "director" / "treatment.md"
    director_treatment.parent.mkdir(parents=True, exist_ok=True)
    director_treatment.write_text(
        "audience memory: remember the workflow change, not a model name. "
        "emotional arc: friction, recognition, agency. visual motif: a paper path becoming a clean system. "
        "color roles: teal means action, red means friction, yellow means decision. "
        "shot causality: every image proves the sentence before it. reject rules: no decorative dashboards, no duplicate headlines, no unexplained stock footage. "
        "The opening begins inside an ordinary task and the ending gives one small action the viewer can try today.",
        encoding="utf-8",
    )
    director_board = video / "director" / "concept-board.png"
    director_frames = [video / "director" / f"style-frame-{index}.png" for index in range(1, 4)]
    for path in [director_board, *director_frames]:
        path.write_bytes(png)
    transition_board = video / "qa" / "transition-board.png"
    transition_board.write_bytes(png)
    transition_review = video / "qa" / "transition-review.json"
    write_json(
        transition_review,
        {
            "schema_version": 1,
            "status": "passed",
            "composition": "EditorialDocumentary",
            "story": "src/story.json",
            "story_sha256": sha256(story_file),
            "transition_mode": "opaque-cut",
            "boundaries": [],
            "board": "qa/transition-board.png",
            "reviewer": "test",
            "reviewed_at": "2026-08-12T10:05:30Z",
            "review_receipt": "transition-approved",
        },
    )
    return [
        "--scene-plan", str(scene_plan),
        "--delivery-spec", str(delivery_spec),
        "--source-ledger", str(source_ledger),
        "--voice-manifest", str(voice),
        "--caption-manifest", str(captions),
        "--voice-audition", str(voice_audition),
        "--director-treatment", str(director_treatment),
        "--director-board", str(director_board),
        *[item for path in director_frames for item in ("--director-frame", str(path))],
        "--review-manifest", str(review),
        "--transition-review", str(transition_review),
        "--transition-board", str(transition_board),
        "--story-file", str(story_file),
        "--remotion-src-dir", str(video / "src"),
        "--render-config", str(package_json),
        "--render-config", str(package_lock),
        "--asset", str(primary),
        "--asset", str(secondary),
        "--cover", str(cover),
        "--opening", str(opening),
        "--board", str(board),
    ]


def write_recheck(story: Path, result: str) -> Path:
    path = story / f"recheck-{result}.json"
    write_json(
        path,
        {
            "schema_version": 1,
            "source_signal_id": "model-release",
            "checks": [
                {
                    "claim_id": "claim-01",
                    "source_ids": ["src-01"],
                    "checked_at": "2026-08-12T10:05:00Z",
                    "result": result,
                    "notes_cn": "官方来源已逐项复核。",
                }
            ],
        },
    )
    return path


def make_final_video(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=320x180:r=30:d=1",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1", "-t", "1", "-shortest",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-y", str(path),
        ],
        check=True,
    )


def write_cost_manifest(video: Path, render: Path) -> Path:
    path = video / "qa" / "cost-manifest.json"
    write_json(
        path,
        {
            "schema_version": 1,
            "llm": {
                "status": "unavailable",
                "provider": "test",
                "model": "test",
                "unavailable_reason": "unit test runner does not expose token accounting",
            },
            "render": {"path": str(render.resolve()), "sha256": sha256(render), "llm_tokens": 0},
        },
    )
    return path


def visual_review_value() -> dict:
    return {
        "schema_version": 1,
        "reviewer": "test",
        "reviewed_at": "2026-08-12T10:07:30Z",
        "opening_reviewed": True,
        "transitions_reviewed": True,
        "final_frame_reviewed": True,
        "captions_reviewed": True,
        "caption_timing_reviewed": True,
        "audio_gaps_reviewed": True,
        "transition_midpoints_reviewed": True,
        "safe_areas_reviewed": True,
        "rights_attributions_reviewed": True,
    }


class NewsroomWorkflowTests(unittest.TestCase):
    def run_state(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(STATE), *args],
            check=check,
            capture_output=True,
            text=True,
        )

    def set_up_selected_story(self, temp: Path) -> tuple[Path, Path]:
        project = temp / "newsroom" / "2026-08-12" / "1000-test"
        self.run_state("init", str(project), "--title", "Test", "--at", "2026-08-12T10:00:00Z")
        signals = temp / "signals.json"
        brief = temp / "brief.md"
        write_json(
            signals,
            {
                "schema_version": 3,
                "generated_at": "2026-08-12T10:00:00Z",
                "window_hours": 72,
                "signals": [signal()],
                "watchlist": [],
            },
        )
        brief.write_text("# Brief\n", encoding="utf-8")
        self.run_state(
            "import-radar",
            str(project),
            str(signals),
            "--brief",
            str(brief),
            "--at",
            "2026-08-12T10:01:00Z",
        )
        self.run_state("select", str(project), "1", "--at", "2026-08-12T10:02:00Z")
        story = project / "stories" / "01-model-release"
        return project, story

    def register(self, project: Path, story: Path, hook: str = "如果你维护一个小项目，最耗时间的往往不是改代码，而是反复找文件和跑检查。") -> None:
        write_json(story / "draft-package.json", package(hook))
        write_json(story / "draft-ledger.json", ledger())
        self.run_state(
            "register-script",
            str(project),
            "1",
            "--package",
            str(story / "draft-package.json"),
            "--ledger",
            str(story / "draft-ledger.json"),
            "--at",
            "2026-08-12T10:03:00Z",
        )

    def approve_script(self, project: Path) -> None:
        self.run_state(
            "present-script",
            str(project),
            "1",
            "--receipt",
            "test-turn-script",
            "--at",
            "2026-08-12T10:03:30Z",
        )
        self.run_state(
            "approve-script", str(project), "1", "--at", "2026-08-12T10:04:00Z"
        )

    def recheck(self, project: Path, story: Path, result: str) -> None:
        self.run_state(
            "recheck",
            str(project),
            "1",
            "--manifest",
            str(write_recheck(story, result)),
            "--at",
            "2026-08-12T10:05:00Z",
        )

    def present_and_approve_preview(self, project: Path) -> None:
        self.run_state(
            "present-preview",
            str(project),
            "1",
            "--receipt",
            "test-turn-preview",
            "--at",
            "2026-08-12T10:06:30Z",
        )
        self.run_state(
            "approve-render", str(project), "1", "--at", "2026-08-12T10:07:00Z"
        )

    def test_happy_path_requires_two_approvals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            project, story = self.set_up_selected_story(Path(temp_name))
            self.register(project, story)
            readable = (story / "script.md").read_text(encoding="utf-8")
            self.assertIn("## 这对工作有什么实际影响", readable)
            self.assertIn("可用程度：可以试用", readable)
            self.assertIn("人仍要负责", readable)
            self.approve_script(project)

            video = story / "video"
            preview_args = preview_arguments(story)
            blocked = self.run_state(
                "mark-preview", str(project), "1", *preview_args, check=False
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("source recheck", blocked.stderr)

            self.recheck(project, story, "unchanged")
            self.run_state(
                "mark-preview",
                str(project),
                "1",
                *preview_args,
                "--at",
                "2026-08-12T10:06:00Z",
            )
            self.present_and_approve_preview(project)
            render = video / "renders" / "final.mp4"
            make_final_video(render)
            visual_review = video / "qa" / "visual-review.json"
            write_json(
                visual_review,
                {
                    "schema_version": 1,
                    "reviewer": "test",
                    "reviewed_at": "2026-08-12T10:07:30Z",
                    "opening_reviewed": True,
                    "transitions_reviewed": True,
                    "final_frame_reviewed": True,
                    "captions_reviewed": True,
                    "caption_timing_reviewed": True,
                    "audio_gaps_reviewed": True,
                    "transition_midpoints_reviewed": True,
                    "safe_areas_reviewed": True,
                    "rights_attributions_reviewed": True,
                },
            )
            self.run_state(
                "complete",
                str(project),
                "1",
                "--render",
                str(render),
                "--story-file",
                str(video / "src" / "story.json"),
                "--source-ledger",
                str(video / "source-ledger.json"),
                "--visual-review",
                str(visual_review),
                "--qa-report",
                str(video / "qa" / "final-delivery.json"),
                "--cost-manifest",
                str(write_cost_manifest(video, render)),
                "--at",
                "2026-08-12T10:08:00Z",
            )
            manifest = json.loads((project / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["stories"]["01-model-release"]["status"], "COMPLETED")

    def test_material_source_change_invalidates_script_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            project, story = self.set_up_selected_story(Path(temp_name))
            self.register(project, story)
            self.approve_script(project)
            self.recheck(project, story, "material-change")
            manifest = json.loads((project / "project.json").read_text(encoding="utf-8"))
            saved = manifest["stories"]["01-model-release"]
            self.assertEqual(saved["status"], "SCRIPT_DRAFT")
            self.assertNotIn("approved_hash", saved["script"])

    def test_script_text_change_after_approval_blocks_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            project, story = self.set_up_selected_story(Path(temp_name))
            self.register(project, story)
            self.approve_script(project)
            self.recheck(project, story, "unchanged")
            (story / "script.txt").write_text("silent mutation\n", encoding="utf-8")
            preview_args = preview_arguments(story)
            result = self.run_state(
                "mark-preview", str(project), "1", *preview_args, check=False
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("changed after approval", result.stderr)

    def test_preview_change_after_render_approval_blocks_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            project, story = self.set_up_selected_story(Path(temp_name))
            self.register(project, story)
            self.approve_script(project)
            self.recheck(project, story, "unchanged")
            preview_args = preview_arguments(story)
            self.run_state(
                "mark-preview",
                str(project),
                "1",
                *preview_args,
                "--at",
                "2026-08-12T10:06:00Z",
            )
            self.present_and_approve_preview(project)
            (story / "video" / "qa" / "cover.png").write_bytes(b"changed cover")
            render = story / "video" / "renders" / "final.mp4"
            render.parent.mkdir(parents=True, exist_ok=True)
            render.write_bytes(b"fake final")
            result = self.run_state(
                "complete",
                str(project),
                "1",
                "--render",
                str(render),
                "--story-file",
                str(story / "video" / "src" / "story.json"),
                "--source-ledger",
                str(story / "video" / "source-ledger.json"),
                "--visual-review",
                str(story / "video" / "qa" / "visual-review.json"),
                "--qa-report",
                str(story / "video" / "qa" / "final-delivery.json"),
                "--cost-manifest",
                str(write_cost_manifest(story / "video", render)),
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("changed after review", result.stderr)

    def test_radar_snapshot_change_blocks_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            temp = Path(temp_name)
            project = temp / "project"
            self.run_state("init", str(project), "--title", "Test")
            signals = temp / "signals.json"
            brief = temp / "brief.md"
            brief.write_text("# Brief\n", encoding="utf-8")
            payload = {"schema_version": 3, "window_hours": 72, "signals": [signal()]}
            write_json(signals, payload)
            self.run_state("import-radar", str(project), str(signals), "--brief", str(brief))
            saved = project / "radar" / "signals.json"
            payload["signals"][0]["id"] = "tampered"
            write_json(saved, payload)
            result = self.run_state("select", str(project), "1", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Radar snapshot changed", result.stderr)

    def test_script_presentation_and_readable_hash_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            project, story = self.set_up_selected_story(Path(temp_name))
            self.register(project, story)
            missing_presentation = self.run_state(
                "approve-script", str(project), "1", check=False
            )
            self.assertNotEqual(missing_presentation.returncode, 0)
            self.assertIn("Present the current full script", missing_presentation.stderr)
            self.run_state(
                "present-script", str(project), "1", "--receipt", "test-turn"
            )
            (story / "script.md").write_text("different display copy\n", encoding="utf-8")
            drifted = self.run_state("approve-script", str(project), "1", check=False)
            self.assertNotEqual(drifted.returncode, 0)
            self.assertIn("register and present", drifted.stderr)

    def test_preview_presentation_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            project, story = self.set_up_selected_story(Path(temp_name))
            self.register(project, story)
            self.approve_script(project)
            self.recheck(project, story, "unchanged")
            args = preview_arguments(story)
            self.run_state("mark-preview", str(project), "1", *args)
            result = self.run_state("approve-render", str(project), "1", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Present the latest review package", result.stderr)

    def test_unreviewed_transition_board_blocks_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            project, story = self.set_up_selected_story(Path(temp_name))
            self.register(project, story)
            self.approve_script(project)
            self.recheck(project, story, "unchanged")
            args = preview_arguments(story)
            manifest_path = story / "video" / "qa" / "transition-review.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["status"] = "ready"
            manifest.pop("review_receipt")
            write_json(manifest_path, manifest)
            result = self.run_state("mark-preview", str(project), "1", *args, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("explicitly approved", result.stderr)

    def test_status_reports_integrity_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            project, story = self.set_up_selected_story(Path(temp_name))
            self.register(project, story)
            (story / "script.md").write_text("tampered\n", encoding="utf-8")
            result = self.run_state("status", str(project))
            payload = json.loads(result.stdout)
            self.assertFalse(payload["integrity"]["ok"])
            self.assertIn("script bundle hash mismatch", " ".join(payload["integrity"]["errors"]))

    def test_unlisted_remotion_dependency_change_blocks_render_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            project, story = self.set_up_selected_story(Path(temp_name))
            self.register(project, story)
            self.approve_script(project)
            self.recheck(project, story, "unchanged")
            preview_args = preview_arguments(story)
            src = story / "video" / "src"
            ratio = src / "ratio-config.json"
            write_json(ratio, {"aspectRatio": "16:9"})
            (src / "EditorialDocumentary.jsx").write_text(
                "import ratio from './ratio-config.json';\nexport const Fixture = () => ratio;\n",
                encoding="utf-8",
            )
            self.run_state("mark-preview", str(project), "1", *preview_args)
            self.run_state(
                "present-preview", str(project), "1", "--receipt", "test-turn"
            )
            write_json(ratio, {"aspectRatio": "9:16"})
            result = self.run_state("approve-render", str(project), "1", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("directory changed after review", result.stderr)

    def test_approve_script_cannot_reseal_silent_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            project, story = self.set_up_selected_story(Path(temp_name))
            self.register(project, story)
            self.approve_script(project)
            (story / "script.txt").write_text("silent mutation\n", encoding="utf-8")
            result = self.run_state("approve-script", str(project), "1", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Register a validated script", result.stderr)

    def test_fake_final_video_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            project, story = self.set_up_selected_story(Path(temp_name))
            self.register(project, story)
            self.approve_script(project)
            self.recheck(project, story, "unchanged")
            preview_args = preview_arguments(story)
            self.run_state("mark-preview", str(project), "1", *preview_args)
            self.present_and_approve_preview(project)
            video = story / "video"
            render = video / "renders" / "final.mp4"
            render.parent.mkdir(parents=True, exist_ok=True)
            render.write_text("not a video", encoding="utf-8")
            visual = video / "qa" / "visual-review.json"
            write_json(visual, {"schema_version": 1})
            result = self.run_state(
                "complete",
                str(project),
                "1",
                "--render",
                str(render),
                "--story-file",
                str(video / "src" / "story.json"),
                "--source-ledger",
                str(video / "source-ledger.json"),
                "--visual-review",
                str(visual),
                "--qa-report",
                str(video / "qa" / "final-delivery.json"),
                "--cost-manifest",
                str(write_cost_manifest(video, render)),
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Not a decodable media file", result.stderr)

    def test_internal_completion_preserves_publication_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            project, story = self.set_up_selected_story(Path(temp_name))
            self.register(project, story)
            self.approve_script(project)
            self.recheck(project, story, "unchanged")
            args = preview_arguments(story)
            video = story / "video"
            spec = json.loads((video / "delivery-spec.json").read_text(encoding="utf-8"))
            spec["delivery_scope"] = "internal"
            write_json(video / "delivery-spec.json", spec)
            source_ledger = json.loads((video / "source-ledger.json").read_text(encoding="utf-8"))
            source_ledger["assets"][0]["publicationStatus"] = "editorial_preview_only"
            source_ledger["assets"][0]["replacementRequiredBeforePublish"] = True
            write_json(video / "source-ledger.json", source_ledger)
            self.run_state("mark-preview", str(project), "1", *args)
            self.present_and_approve_preview(project)
            render = video / "renders" / "internal.mp4"
            make_final_video(render)
            visual = video / "qa" / "visual-review.json"
            write_json(visual, visual_review_value())
            public_attempt = self.run_state(
                "complete",
                str(project),
                "1",
                "--render",
                str(render),
                "--story-file",
                str(video / "src" / "story.json"),
                "--source-ledger",
                str(video / "source-ledger.json"),
                "--visual-review",
                str(visual),
                "--qa-report",
                str(video / "qa" / "public-qa.json"),
                "--cost-manifest",
                str(write_cost_manifest(video, render)),
                check=False,
            )
            self.assertNotEqual(public_attempt.returncode, 0)
            self.assertIn("locked for internal", public_attempt.stderr)
            self.run_state(
                "complete-internal",
                str(project),
                "1",
                "--render",
                str(render),
                "--story-file",
                str(video / "src" / "story.json"),
                "--source-ledger",
                str(video / "source-ledger.json"),
                "--visual-review",
                str(visual),
                "--qa-report",
                str(video / "qa" / "internal-qa.json"),
                "--cost-manifest",
                str(video / "qa" / "cost-manifest.json"),
            )
            status = json.loads(self.run_state("status", str(project), "--story", "1", "--summary").stdout)
            self.assertEqual(status["status"], "COMPLETED_INTERNAL")
            self.assertEqual(status["delivery_scope"], "internal")
            report = json.loads((video / "qa" / "internal-qa.json").read_text(encoding="utf-8"))
            self.assertEqual(report["publication_validation"], "blocked")

    def test_silent_audio_track_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            project, story = self.set_up_selected_story(Path(temp_name))
            self.register(project, story)
            self.approve_script(project)
            self.recheck(project, story, "unchanged")
            args = preview_arguments(story)
            self.run_state("mark-preview", str(project), "1", *args)
            self.present_and_approve_preview(project)
            video = story / "video"
            render = video / "renders" / "silent.mp4"
            render.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    "ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=320x180:r=30:d=1",
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "1", "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-y", str(render),
                ],
                check=True,
            )
            visual = video / "qa" / "visual-review.json"
            write_json(visual, visual_review_value())
            result = self.run_state(
                "complete",
                str(project),
                "1",
                "--render", str(render),
                "--story-file", str(video / "src" / "story.json"),
                "--source-ledger", str(video / "source-ledger.json"),
                "--visual-review", str(visual),
                "--qa-report", str(video / "qa" / "silent-qa.json"),
                "--cost-manifest", str(write_cost_manifest(video, render)),
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("silent", result.stderr.lower())

    def test_status_summary_is_compact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            project, _ = self.set_up_selected_story(Path(temp_name))
            result = self.run_state("status", str(project), "--summary")
            payload = json.loads(result.stdout)
            self.assertIn("stories", payload)
            self.assertNotIn("history", payload)
            self.assertLess(len(result.stdout), 1500)


class ProductionContractTests(unittest.TestCase):
    def test_transition_review_requires_explicit_review_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            manifest = Path(temp_name) / "transition.json"
            write_json(
                manifest,
                {
                    "schema_version": 1,
                    "status": "ready",
                    "boundaries": [],
                    "board": "qa/transition-board.png",
                },
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(TRANSITIONS),
                    "--approve-manifest",
                    str(manifest),
                    "--review-receipt",
                    "review-turn-1",
                    "--reviewer",
                    "test",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            value = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(value["status"], "passed")
            self.assertEqual(value["review_receipt"], "review-turn-1")

    def test_caption_pipeline_respects_explicit_millisecond_unit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            temp = Path(temp_name)
            voice = temp / "voice.json"
            output = temp / "captions.json"
            write_json(
                voice,
                {
                    "duration": 1.0,
                    "language": "en-US",
                    "timingUnit": "milliseconds",
                    "segments": [{"sentences": [{"text": "AI helps now", "startTime": 100, "endTime": 900}]}],
                },
            )
            result = subprocess.run(
                [sys.executable, str(CAPTIONS), "generate", str(voice), "--output", str(output)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            cue = json.loads(output.read_text(encoding="utf-8"))["cues"][0]
            self.assertEqual((cue["startMs"], cue["endMs"]), (100, 900))

    def test_bundled_horizontal_and_vertical_stories_validate(self) -> None:
        template = ROOT / "assets" / "remotion-template"
        for name in ("story.json", "vertical-story.json"):
            result = subprocess.run(
                [sys.executable, str(STORY_VALIDATOR), str(template / "src" / name), str(template / "source-ledger.json")],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class ScriptValidatorTests(unittest.TestCase):
    def run_validator(self, package_value: dict, ledger_value: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_name:
            temp = Path(temp_name)
            package_path = temp / "package.json"
            ledger_path = temp / "ledger.json"
            selected_path = temp / "selected.json"
            write_json(package_path, package_value)
            write_json(ledger_path, ledger_value)
            write_json(selected_path, signal())
            return subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    str(package_path),
                    str(ledger_path),
                    "--selected",
                    str(selected_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_valid_package_passes(self) -> None:
        result = self.run_validator(package(), ledger())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stage_direction_and_fake_radar_provenance_fail(self) -> None:
        invalid_package = package("（画面：产品演示）这次更新很重要。")
        invalid_ledger = ledger()
        invalid_ledger["sources"][0]["url"] = "https://example.com/not-in-radar"
        result = self.run_validator(invalid_package, invalid_ledger)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("visual/stage direction", result.stdout)
        self.assertIn("radar provenance", result.stdout)

    def test_v2_requires_complete_productivity_frame(self) -> None:
        invalid_package = package()
        invalid_package["productivity_frame"].pop("human_role_cn")
        result = self.run_validator(invalid_package, ledger())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("productivity_frame.human_role_cn is required", result.stdout)

    def test_v2_rejects_technical_release_first_hook(self) -> None:
        invalid_package = package("OpenAI 发布了一个参数更强的新模型。")
        result = self.run_validator(invalid_package, ledger())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("start from the work situation", result.stdout)


if __name__ == "__main__":
    unittest.main()
