from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "rank_signals.py"
SPEC = importlib.util.spec_from_file_location("rank_signals", SCRIPT)
assert SPEC and SPEC.loader
rank_signals = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rank_signals)

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)


def make_signal(
    signal_id: str = "signal",
    *,
    judgments: dict[str, float] | None = None,
    verification: str = "verified",
    flags: list[str] | None = None,
    event_time: str = "2026-08-05T10:00:00Z",
) -> dict:
    return {
        "id": signal_id,
        "event_key": f"event-{signal_id}",
        "entity": signal_id,
        "title": f"Event {signal_id}",
        "type": "official-release",
        "event_time": event_time,
        "audience_cn": "正在评估 AI 工具的独立开发者",
        "user_need_cn": "判断是否迁移工作流",
        "work_task_cn": "把需求和代码改动整理成可审查的提交",
        "old_workflow_cn": "人工搜索文件、修改代码、运行检查并整理说明",
        "friction_cn": "时间耗在重复搜索和整理，失败后还要重新定位",
        "ai_change_cn": "AI 可以执行部分搜索、修改与检查，并保留过程",
        "new_workflow_cn": "人定义验收标准，AI 执行，人复核差异和结果",
        "human_role_cn": "决定目标、审查代码并对合并结果负责",
        "readiness": "try-now",
        "readiness_reason_cn": "现在可以在低风险仓库试用，但仍要人工审查",
        "next_action_cn": "先选一个有测试的小修复做同任务对比",
        "topic_thesis_cn": "迁移不应只看演示速度",
        "visual_proof_cn": "用同一任务的并排对比证明",
        "verification": verification,
        "judgments": judgments
        or {
            "authority": 90,
            "evidence_quality": 90,
            "impact": 80,
            "productivity_leverage": 80,
            "workflow_clarity": 80,
            "practicality": 80,
            "audience_resonance": 80,
            "novelty": 80,
            "visual_evidence": 80,
            "discussion_value": 80,
            "search_demand": 80,
            "emotional_payoff": 80,
        },
        "flags": flags or [],
        "sources": [
            {
                "platform": "x",
                "source_name": "Original author",
                "url": f"https://x.com/example/status/{signal_id}",
                "published_at": event_time,
                "is_primary": True,
                "engagement": {
                    "likes": 8000,
                    "reposts": 1200,
                    "replies": 500,
                    "views": 900000,
                },
            },
            {
                "platform": "reddit",
                "source_name": "r/LocalLLaMA",
                "url": f"https://reddit.com/r/LocalLLaMA/{signal_id}",
                "published_at": event_time,
                "is_primary": False,
                "engagement": {"upvotes": 2200, "comments": 500},
            },
        ],
    }


class TopicScoringTests(unittest.TestCase):
    def test_topic_weights_sum_to_one(self) -> None:
        self.assertAlmostEqual(sum(rank_signals.TOPIC_WEIGHTS.values()), 1.0)

    def test_topic_dimensions_have_deterministic_weights(self) -> None:
        judgments = {
            "authority": 90,
            "evidence_quality": 90,
            "impact": 80,
            "productivity_leverage": 100,
            "workflow_clarity": 0,
            "practicality": 0,
            "audience_resonance": 0,
            "novelty": 0,
            "visual_evidence": 0,
            "discussion_value": 0,
            "search_demand": 0,
            "emotional_payoff": 0,
        }
        scored = rank_signals.score_signal(make_signal(judgments=judgments), NOW, 72)
        assert scored
        self.assertEqual(scored["scores"]["topic_score"], 25.0)

    def test_better_topic_fit_raises_priority_without_changing_signal_score(self) -> None:
        high = make_signal("high")
        low_judgments = dict(high["judgments"])
        for key in rank_signals.TOPIC_WEIGHTS:
            low_judgments[key] = 20
        low = make_signal("low", judgments=low_judgments)

        high_score = rank_signals.score_signal(high, NOW, 72)
        low_score = rank_signals.score_signal(low, NOW, 72)
        assert high_score and low_score
        self.assertEqual(
            high_score["scores"]["signal_score"],
            low_score["scores"]["signal_score"],
        )
        self.assertGreater(
            high_score["scores"]["priority"],
            low_score["scores"]["priority"],
        )

    def test_topic_gate_requires_a_clear_workflow_for_overrides(self) -> None:
        self.assertEqual(rank_signals.topic_gate(59, 84, 84, 89, 89)[0], False)
        self.assertEqual(rank_signals.topic_gate(59, 85, 50, 89, 65)[0], True)
        self.assertEqual(rank_signals.topic_gate(59, 50, 85, 89, 65)[0], True)
        self.assertEqual(rank_signals.topic_gate(59, 50, 50, 90, 70)[0], True)
        self.assertEqual(rank_signals.topic_gate(59, 95, 95, 95, 40)[0], False)

    def test_v1_content_potential_remains_compatible(self) -> None:
        legacy = make_signal(
            judgments={
                "authority": 90,
                "evidence_quality": 90,
                "impact": 80,
                "novelty": 73,
                "content_potential": 73,
            }
        )
        scored = rank_signals.score_signal(legacy, NOW, 72)
        assert scored
        self.assertEqual(scored["scores"]["topic_score"], 73.0)
        self.assertEqual(scored["scores"]["content_potential"], 73.0)
        self.assertTrue(scored["topic_gate_passed"])

    def test_unverified_signal_is_capped_and_excluded_from_main_list(self) -> None:
        scored = rank_signals.score_signal(
            make_signal(verification="unverified"), NOW, 72
        )
        assert scored
        self.assertLessEqual(scored["scores"]["priority"], 59.0)


class CliTests(unittest.TestCase):
    def test_v3_cli_rejects_missing_productivity_fields(self) -> None:
        incomplete = make_signal("incomplete")
        incomplete.pop("new_workflow_cn")
        payload = {"schema_version": 3, "window_hours": 72, "signals": [incomplete]}

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "candidates.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(input_path), "--now", NOW.isoformat()],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("new_workflow_cn", completed.stderr)

    def test_v3_cli_rejects_invalid_readiness(self) -> None:
        invalid = make_signal("invalid-readiness")
        invalid["readiness"] = "available-soon"
        payload = {"schema_version": 3, "window_hours": 72, "signals": [invalid]}

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "candidates.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(input_path), "--now", NOW.isoformat()],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("readiness must be one of", completed.stderr)

    def test_cli_separates_main_list_watchlist_and_stale_events(self) -> None:
        low_topic = make_signal("low-topic")
        low_topic["judgments"].update({key: 20 for key in rank_signals.TOPIC_WEIGHTS})
        low_topic["judgments"]["impact"] = 89

        stale = make_signal("stale", event_time="2026-08-01T10:00:00Z")
        payload = {
            "schema_version": 3,
            "window_hours": 72,
            "signals": [make_signal("main"), low_topic, stale],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "candidates.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(input_path),
                    "--now",
                    NOW.isoformat(),
                    "--format",
                    "json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        output = json.loads(completed.stdout)
        self.assertEqual(output["schema_version"], 3)
        self.assertEqual(output["stale_excluded"], 1)
        self.assertEqual([item["id"] for item in output["signals"]], ["main"])
        self.assertIn("low-topic", [item["id"] for item in output["watchlist"]])


if __name__ == "__main__":
    unittest.main()
