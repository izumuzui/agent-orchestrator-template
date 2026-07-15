#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVENT_PATH = ROOT / ".agent-state" / "metrics" / "task-events.jsonl"
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
TASK_TYPES = {"feature", "bugfix", "refactor", "review", "ops", "docs"}
PATTERNS = {"P0", "P1", "P2", "P3", "P3+P0", "P3+P1", "P3+P2"}


def bounded_id(value: str) -> str:
    if not ID_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError("use only letters, numbers, underscore, and hyphen")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atomically reserve routing before implementation.")
    parser.add_argument("--task-id", required=True, type=bounded_id)
    parser.add_argument("--policy-version", required=True, type=bounded_id)
    parser.add_argument("--area-id", required=True, type=bounded_id)
    parser.add_argument("--task-type", required=True, choices=sorted(TASK_TYPES))
    parser.add_argument("--risk", required=True, choices=("low", "medium", "high"))
    parser.add_argument("--intended-pattern", required=True, choices=sorted(PATTERNS))
    parser.add_argument("--non-trivial", action="store_true")
    parser.add_argument(
        "--review-override",
        choices=("none", "escaped_defect", "policy"),
        default="none",
    )
    parser.add_argument("--calibration-size", type=int, default=10)
    parser.add_argument("--sentinel-interval", type=int, default=5)
    args = parser.parse_args()
    if args.calibration_size < 1 or args.sentinel_interval < 1:
        parser.error("calibration size and sentinel interval must be positive")
    return args


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    args = parse_args()
    os.umask(0o077)
    EVENT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with EVENT_PATH.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        events = [json.loads(line) for line in handle if line.strip()]

        if any(event.get("task_id") == args.task_id for event in events):
            raise SystemExit(f"task already recorded: {args.task_id}")

        counter_key = f"{args.area_id}:{args.task_type}"
        matching = [
            event
            for event in events
            if event.get("event") == "routing_reserved"
            and event.get("policy_version") == args.policy_version
            and event.get("sentinel_counter_key") == counter_key
        ]
        routing_sequence = max((int(event["routing_sequence"]) for event in matching), default=0) + 1

        previous_non_trivial = sum(
            1
            for event in events
            if event.get("event") == "routing_reserved"
            and event.get("policy_version") == args.policy_version
            and event.get("non_trivial") is True
        )
        calibration = args.non_trivial and previous_non_trivial < args.calibration_size
        calibration_complete = previous_non_trivial >= args.calibration_size
        low_risk_after_calibration = [
            event
            for event in matching
            if event.get("risk") == "low" and event.get("calibration") is False
        ]
        sentinel_sequence = (
            len(low_risk_after_calibration) + 1
            if calibration_complete and args.risk == "low"
            else None
        )
        sentinel = sentinel_sequence is not None and sentinel_sequence % args.sentinel_interval == 0

        reasons: list[str] = []
        if calibration:
            reasons.append("calibration")
        if args.risk in {"medium", "high"}:
            reasons.append(f"risk_{args.risk}")
        if sentinel:
            reasons.append("sentinel")
        if args.review_override != "none":
            reasons.append(args.review_override)

        event = {
            "event": "routing_reserved",
            "ts": utc_now(),
            "task_id": args.task_id,
            "policy_version": args.policy_version,
            "area_id": args.area_id,
            "task_type": args.task_type,
            "risk": args.risk,
            "intended_pattern": args.intended_pattern,
            "sentinel_counter_key": counter_key,
            "routing_sequence": routing_sequence,
            "sentinel_sequence": sentinel_sequence,
            "non_trivial": args.non_trivial,
            "calibration": calibration,
            "sentinel": sentinel,
            "review_required": bool(reasons),
            "review_reason": reasons or ["none"],
        }
        handle.seek(0, os.SEEK_END)
        handle.write(json.dumps(event, ensure_ascii=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
