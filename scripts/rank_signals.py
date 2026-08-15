#!/usr/bin/env python3
"""Rank AI/tech signal clusters using recency, engagement, spread, and editorial value."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PLATFORM_SATURATION = {
    "x": 5000.0,
    "twitter": 5000.0,
    "reddit": 1200.0,
    "hacker-news": 550.0,
    "hn": 550.0,
    "youtube": 9000.0,
    "github": 800.0,
    "other": 1200.0,
}

FLAG_PENALTIES = {
    "rumor": 18.0,
    "unverified": 18.0,
    "recycled": 25.0,
    "sponsored": 12.0,
    "misleading-metrics": 15.0,
    "duplicate": 100.0,
}

VERIFICATION_LABELS = {
    "verified": "已证实",
    "attributed": "当事人表述",
    "reported": "可靠报道",
    "community-observed": "社区观察",
    "unverified": "未证实",
}

TOPIC_WEIGHTS = {
    "productivity_leverage": 0.25,
    "workflow_clarity": 0.20,
    "practicality": 0.15,
    "audience_resonance": 0.15,
    "visual_evidence": 0.10,
    "novelty": 0.05,
    "search_demand": 0.05,
    "discussion_value": 0.03,
    "emotional_payoff": 0.02,
}

REQUIRED_V2_TEXT_FIELDS = (
    "audience_cn",
    "user_need_cn",
    "topic_thesis_cn",
    "visual_proof_cn",
)

REQUIRED_V3_TEXT_FIELDS = (
    *REQUIRED_V2_TEXT_FIELDS,
    "work_task_cn",
    "old_workflow_cn",
    "friction_cn",
    "ai_change_cn",
    "new_workflow_cn",
    "human_role_cn",
    "readiness_reason_cn",
    "next_action_cn",
)

READINESS_LEVELS = {
    "use-now": "现在可用",
    "try-now": "可以试用",
    "watch": "暂时观望",
    "future": "长期趋势",
}

LEGACY_TOPIC_DIMENSIONS = (
    "practicality",
    "audience_resonance",
    "novelty",
    "visual_evidence",
    "discussion_value",
    "search_demand",
    "emotional_payoff",
)

REQUIRED_V2_JUDGMENTS = (
    "authority",
    "evidence_quality",
    "impact",
    *LEGACY_TOPIC_DIMENSIONS,
)

REQUIRED_V3_JUDGMENTS = (
    "authority",
    "evidence_quality",
    "impact",
    *TOPIC_WEIGHTS,
)


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO timestamp: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def number(data: dict[str, Any], key: str) -> float:
    value = data.get(key, 0)
    if value is None:
        return 0.0
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0


def engagement_units(source: dict[str, Any]) -> float:
    platform = str(source.get("platform", "other")).lower()
    engagement = source.get("engagement") or {}
    if platform in {"x", "twitter"}:
        return (
            number(engagement, "likes")
            + 1.8 * number(engagement, "reposts")
            + 1.2 * number(engagement, "replies")
            + 0.02 * number(engagement, "views")
        )
    if platform == "reddit":
        return number(engagement, "upvotes") + 2.0 * number(engagement, "comments")
    if platform in {"hacker-news", "hn"}:
        return number(engagement, "points") + 2.0 * number(engagement, "comments")
    if platform == "youtube":
        return (
            number(engagement, "likes")
            + 2.0 * number(engagement, "comments")
            + 0.005 * number(engagement, "views")
        )
    if platform == "github":
        return (
            number(engagement, "stars")
            + 2.0 * number(engagement, "forks")
            + number(engagement, "comments")
        )
    return (
        number(engagement, "likes")
        + number(engagement, "upvotes")
        + 1.5 * number(engagement, "shares")
        + 1.5 * number(engagement, "comments")
        + 0.005 * number(engagement, "views")
    )


def normalized_engagement(source: dict[str, Any]) -> float | None:
    engagement = source.get("engagement")
    if not engagement:
        return None
    platform = str(source.get("platform", "other")).lower()
    saturation = PLATFORM_SATURATION.get(platform, PLATFORM_SATURATION["other"])
    units = engagement_units(source)
    return clamp(100.0 * (1.0 - math.exp(-units / saturation)))


def event_time(signal: dict[str, Any]) -> datetime | None:
    direct = parse_time(signal.get("event_time"))
    if direct:
        return direct
    source_times = [
        parse_time(source.get("published_at"))
        for source in signal.get("sources", [])
        if source.get("published_at")
    ]
    valid = [value for value in source_times if value is not None]
    return min(valid) if valid else None


def source_identity(source: dict[str, Any]) -> str:
    url = str(source.get("url", ""))
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return str(source.get("source_name") or host or source.get("platform") or "unknown").lower()


def judgment(signal: dict[str, Any], key: str, default: float = 50.0) -> float:
    judgments = signal.get("judgments") or {}
    try:
        return clamp(float(judgments.get(key, default)))
    except (TypeError, ValueError):
        return default


def topic_judgment(signal: dict[str, Any], key: str) -> float:
    """Read a topic judgment, falling back to legacy content_potential."""
    judgments = signal.get("judgments") or {}
    if key in judgments:
        return judgment(signal, key)
    return judgment(signal, "content_potential")


def topic_gate(
    topic_score: float,
    productivity_leverage: float,
    practicality: float,
    impact: float,
    workflow_clarity: float,
) -> tuple[bool, str]:
    if topic_score >= 60.0:
        return True, "选题分达到 60"
    if productivity_leverage >= 85.0 and workflow_clarity >= 65.0:
        return True, "生产力杠杆达到 85，且工作流变化清楚"
    if practicality >= 85.0 and workflow_clarity >= 65.0:
        return True, "现在可行动，且工作流变化清楚"
    if impact >= 90.0 and workflow_clarity >= 70.0:
        return True, "重大影响保护，且能解释具体工作变化"
    return False, "生产力收益、可行动性或工作流清晰度未达门槛"


def validate_signal(signal: dict[str, Any], schema_version: int) -> None:
    signal_id = signal.get("id", "<unknown>")
    required_text = (
        REQUIRED_V3_TEXT_FIELDS if schema_version >= 3 else REQUIRED_V2_TEXT_FIELDS
    )
    missing_text = [
        key for key in required_text if not str(signal.get(key) or "").strip()
    ]
    if missing_text:
        raise ValueError(
            f"Signal {signal_id} is missing required v{schema_version} text fields: "
            + ", ".join(missing_text)
        )

    if schema_version >= 3 and signal.get("readiness") not in READINESS_LEVELS:
        raise ValueError(
            f"Signal {signal_id} readiness must be one of: "
            + ", ".join(READINESS_LEVELS)
        )

    judgments = signal.get("judgments")
    if not isinstance(judgments, dict):
        raise ValueError(f"Signal {signal_id} must contain a judgments object")
    required_judgments = (
        REQUIRED_V3_JUDGMENTS if schema_version >= 3 else REQUIRED_V2_JUDGMENTS
    )
    missing_judgments = [key for key in required_judgments if key not in judgments]
    if missing_judgments:
        raise ValueError(
            f"Signal {signal_id} is missing required v{schema_version} judgments: "
            + ", ".join(missing_judgments)
        )
    for key in required_judgments:
        try:
            value = float(judgments[key])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Signal {signal_id} judgment {key} must be a number"
            ) from exc
        if not math.isfinite(value) or not 0.0 <= value <= 100.0:
            raise ValueError(
                f"Signal {signal_id} judgment {key} must be between 0 and 100"
            )


def score_signal(signal: dict[str, Any], now: datetime, window_hours: int) -> dict[str, Any] | None:
    occurred = event_time(signal)
    if not occurred:
        raise ValueError(f"Signal {signal.get('id', '<unknown>')} has no usable event time")

    age_hours = max(0.0, (now - occurred).total_seconds() / 3600.0)
    if age_hours > window_hours:
        return None

    recency = clamp(100.0 * math.pow(0.5, age_hours / 36.0))
    sources = signal.get("sources") or []
    engagement_scores = [
        score
        for source in sources
        if (score := normalized_engagement(source)) is not None
    ]
    if engagement_scores:
        engagement_scores.sort(reverse=True)
        platform_heat = 0.65 * engagement_scores[0] + 0.35 * (
            sum(engagement_scores[:3]) / len(engagement_scores[:3])
        )
    else:
        platform_heat = 0.0

    platforms = {
        str(source.get("platform", "other")).lower()
        for source in sources
        if source.get("platform")
    }
    identities = {source_identity(source) for source in sources}
    primary_bonus = 15.0 if any(bool(source.get("is_primary")) for source in sources) else 0.0
    spread = clamp(12.0 * len(identities) + 10.0 * len(platforms) + primary_bonus)

    velocity_scores: list[float] = []
    velocity_age = max(age_hours, 2.0)
    for source in sources:
        if not source.get("engagement"):
            continue
        platform = str(source.get("platform", "other")).lower()
        saturation = PLATFORM_SATURATION.get(platform, PLATFORM_SATURATION["other"])
        expected = saturation * velocity_age / 24.0
        velocity_scores.append(
            clamp(100.0 * (1.0 - math.exp(-engagement_units(source) / max(expected, 1.0))))
        )
    velocity = max(velocity_scores, default=0.0)

    hot_72h = clamp(0.50 * platform_heat + 0.25 * spread + 0.25 * recency)
    today_pulse = clamp(0.50 * velocity + 0.35 * recency + 0.15 * spread)

    authority = judgment(signal, "authority")
    evidence_quality = judgment(signal, "evidence_quality")
    impact = judgment(signal, "impact")
    credibility = 0.55 * authority + 0.45 * evidence_quality

    topic_dimensions = {
        key: topic_judgment(signal, key)
        for key in TOPIC_WEIGHTS
    }
    topic_score = sum(
        TOPIC_WEIGHTS[key] * value
        for key, value in topic_dimensions.items()
    )

    signal_score = clamp(
        0.40 * hot_72h
        + 0.20 * today_pulse
        + 0.20 * credibility
        + 0.20 * impact
    )

    flags = {str(flag).lower() for flag in signal.get("flags", [])}
    penalty = sum(FLAG_PENALTIES.get(flag, 0.0) for flag in flags)
    priority = clamp(
        0.55 * signal_score
        + 0.45 * topic_score
        - penalty
    )

    verification = str(signal.get("verification", "unverified")).lower()
    if verification == "unverified" or "unverified" in flags:
        priority = min(priority, 59.0)

    gate_passed, gate_reason = topic_gate(
        topic_score,
        topic_dimensions["productivity_leverage"],
        topic_dimensions["practicality"],
        impact,
        topic_dimensions["workflow_clarity"],
    )

    if not gate_passed:
        tier = "Watch"
    elif priority >= 82.0:
        tier = "S"
    elif priority >= 72.0:
        tier = "A"
    elif priority >= 62.0:
        tier = "B"
    else:
        tier = "Watch"

    result = dict(signal)
    result["age_hours"] = round(age_hours, 1)
    result["scores"] = {
        "priority": round(priority, 1),
        "hot_72h": round(hot_72h, 1),
        "today_pulse": round(today_pulse, 1),
        "platform_heat": round(platform_heat, 1),
        "spread": round(spread, 1),
        "recency": round(recency, 1),
        "credibility": round(credibility, 1),
        "signal_score": round(signal_score, 1),
        "topic_score": round(topic_score, 1),
        "impact": round(impact, 1),
        "penalty": round(penalty, 1),
    }
    result["scores"].update(
        {key: round(value, 1) for key, value in topic_dimensions.items()}
    )
    if "content_potential" in (signal.get("judgments") or {}):
        result["scores"]["content_potential"] = round(
            judgment(signal, "content_potential"), 1
        )
    result["topic_gate_passed"] = gate_passed
    result["topic_gate_reason"] = gate_reason
    result["tier"] = tier
    result["verification_label_cn"] = VERIFICATION_LABELS.get(verification, verification)
    result["readiness_label_cn"] = READINESS_LEVELS.get(
        str(signal.get("readiness") or ""), "未标注"
    )
    return result


def diversify(ranked: list[dict[str, Any]], top: int, max_per_entity: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for signal in ranked:
        entity = str(signal.get("entity") or "").strip().lower()
        if entity and counts.get(entity, 0) >= max_per_entity:
            deferred.append(signal)
            continue
        selected.append(signal)
        if entity:
            counts[entity] = counts.get(entity, 0) + 1
        if len(selected) == top:
            return selected
    for signal in deferred:
        if len(selected) == top:
            break
        selected.append(signal)
    return selected


def markdown_table(payload: dict[str, Any]) -> str:
    lines = [
        "| # | 级别 | 工作场景 | 改变哪一步 | 现在能否用 | 事件 | Priority | 信号分 | 选题分 |",
        "|---:|:---:|---|---|---|---|---:|---:|---:|",
    ]
    for index, signal in enumerate(payload["signals"], start=1):
        title = str(signal.get("title", "Untitled")).replace("|", "\\|")
        sources = signal.get("sources") or []
        primary = next((source for source in sources if source.get("is_primary")), None)
        source = primary or (sources[0] if sources else None)
        if source and source.get("url"):
            title = f"[{title}]({source['url']})"
        scores = signal["scores"]
        audience = str(signal.get("audience_cn") or "未填写").replace("|", "\\|")
        work_task = str(
            signal.get("work_task_cn") or signal.get("user_need_cn") or "未填写"
        ).replace("|", "\\|")
        old_step = str(
            signal.get("friction_cn") or signal.get("old_workflow_cn") or ""
        ).strip()
        new_step = str(
            signal.get("ai_change_cn") or signal.get("topic_thesis_cn") or "未填写"
        ).strip()
        change = f"{old_step} → {new_step}" if old_step else new_step
        change = change.replace("|", "\\|")
        readiness = str(signal.get("readiness_label_cn") or "未标注").replace(
            "|", "\\|"
        )
        lines.append(
            f"| {index} | {signal['tier']} | {audience}：{work_task} | {change} | "
            f"{readiness} | {title} | {scores['priority']:.1f} | "
            f"{scores['signal_score']:.1f} | {scores['topic_score']:.1f} |"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Candidate JSON file")
    parser.add_argument("--top", type=int, default=10, help="Number of ranked signals to emit")
    parser.add_argument(
        "--min-priority",
        type=float,
        default=62.0,
        help="Minimum priority for the main list (default: 62)",
    )
    parser.add_argument(
        "--watch",
        type=int,
        default=3,
        help="Number of below-threshold signals to keep in the watchlist",
    )
    parser.add_argument("--window-hours", type=int, help="Override input window_hours")
    parser.add_argument("--now", help="Override current time with an ISO timestamp")
    parser.add_argument("--max-per-entity", type=int, default=3)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path, help="Write output to this path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
        if now is None:
            raise ValueError("Could not determine current time")
        window_hours = int(args.window_hours or data.get("window_hours", 72))
        if window_hours <= 0:
            raise ValueError("window_hours must be greater than 0")
        schema_version = int(data.get("schema_version", 1))
        raw_signals = data.get("signals")
        if not isinstance(raw_signals, list):
            raise ValueError("Top-level 'signals' must be an array")

        scored: list[dict[str, Any]] = []
        stale = 0
        for signal in raw_signals:
            if not isinstance(signal, dict):
                raise ValueError("Each signal must be an object")
            if schema_version >= 2:
                validate_signal(signal, schema_version)
            result = score_signal(signal, now, window_hours)
            if result is None:
                stale += 1
            else:
                scored.append(result)
        scored.sort(
            key=lambda item: (
                item["scores"]["priority"],
                item["scores"]["today_pulse"],
                item["scores"]["hot_72h"],
            ),
            reverse=True,
        )
        main_candidates = [
            signal
            for signal in scored
            if signal["scores"]["priority"] >= args.min_priority
            and signal.get("verification") != "unverified"
            and signal["topic_gate_passed"]
        ]
        watch_candidates = [signal for signal in scored if signal not in main_candidates]
        selected = diversify(main_candidates, args.top, args.max_per_entity)
        payload = {
            "schema_version": schema_version,
            "generated_at": now.isoformat(),
            "window_hours": window_hours,
            "candidate_count": len(raw_signals),
            "in_window_count": len(scored),
            "stale_excluded": stale,
            "signals": selected,
            "watchlist": watch_candidates[: max(0, args.watch)],
        }
        output = (
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            if args.format == "json"
            else markdown_table(payload)
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"rank_signals.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
