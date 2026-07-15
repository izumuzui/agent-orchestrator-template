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
TASK_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
PROFILE_ID_PATTERN = re.compile(r"[A-Za-z0-9_@.-]+")


def task_id(value: str) -> str:
    if not TASK_ID_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError("invalid opaque task identifier")
    return value


def profile_id(value: str) -> str:
    if not PROFILE_ID_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError("invalid capability profile identifier")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append a terminal task event.")
    parser.add_argument("--task-id", required=True, type=task_id)
    parser.add_argument("--planner", default="none", type=profile_id)
    parser.add_argument("--writer", required=True, type=profile_id)
    parser.add_argument("--reviewer", default="none", type=profile_id)
    parser.add_argument(
        "--reviewer-relation",
        choices=("none", "fresh_same", "cross_provider"),
        default="none",
    )
    parser.add_argument(
        "--review-outcome",
        choices=("none", "accepted", "changes_required", "blocked"),
        default="none",
    )
    parser.add_argument("--review-rework-rounds", type=int, default=0)
    parser.add_argument("--implementation-retries", type=int, default=0)
    parser.add_argument("--verification-retries", type=int, default=0)
    parser.add_argument("--plan-corrections", type=int, default=0)
    parser.add_argument("--overall", required=True, choices=("passed", "failed", "blocked", "incomplete"))
    parser.add_argument("--passed", type=int, default=0)
    parser.add_argument("--failed", type=int, default=0)
    parser.add_argument("--skipped", type=int, default=0)
    parser.add_argument("--environment-blocked", type=int, default=0)
    parser.add_argument(
        "--fallback-reason",
        choices=("none", "quota", "rate_limit", "availability", "scope_reduced"),
        default="none",
    )
    parser.add_argument("--rate-limit-hits", type=int, default=0)
    parser.add_argument("--usage-status", choices=("missing", "approximate", "reported"), default="missing")
    parser.add_argument("--usage-value", type=int)
    parser.add_argument("--usage-unit", choices=("tokens", "percent", "turns"))
    parser.add_argument("--regression-of", type=task_id)
    parser.add_argument(
        "--intervention",
        action="append",
        choices=(
            "permission_approval",
            "scope_decision",
            "acceptance_clarification",
            "environment_recovery",
            "safety_stop",
        ),
        default=[],
    )
    args = parser.parse_args()
    counts = (
        args.review_rework_rounds,
        args.implementation_retries,
        args.verification_retries,
        args.plan_corrections,
        args.passed,
        args.failed,
        args.skipped,
        args.environment_blocked,
        args.rate_limit_hits,
    )
    if any(value < 0 for value in counts):
        parser.error("counts must be non-negative")
    if args.overall == "passed" and (args.failed or args.environment_blocked):
        parser.error("passed requires zero failed and environment-blocked checks")
    if args.overall == "passed" and args.review_outcome in {"changes_required", "blocked"}:
        parser.error("passed is incompatible with an unresolved review outcome")
    if args.failed and args.overall != "failed":
        parser.error("failed checks require overall=failed")
    if args.environment_blocked and not args.failed and args.overall != "blocked":
        parser.error("environment-blocked checks require overall=blocked")
    if args.usage_status == "missing" and (args.usage_value is not None or args.usage_unit is not None):
        parser.error("missing usage cannot have a value or unit")
    if args.usage_status != "missing" and (args.usage_value is None or args.usage_unit is None):
        parser.error("available usage requires both value and unit")
    if args.usage_value is not None and args.usage_value < 0:
        parser.error("usage value must be non-negative")
    return args


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    args = parse_args()
    os.umask(0o077)
    if not EVENT_PATH.exists():
        raise SystemExit("no routing journal exists; reserve routing first")

    with EVENT_PATH.open("r+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        events = [json.loads(line) for line in handle if line.strip()]
        reservations = [
            event
            for event in events
            if event.get("event") == "routing_reserved" and event.get("task_id") == args.task_id
        ]
        if len(reservations) != 1:
            raise SystemExit(f"expected one routing reservation for {args.task_id}")
        if any(
            event.get("event") == "task_completed" and event.get("task_id") == args.task_id
            for event in events
        ):
            raise SystemExit(f"task already completed: {args.task_id}")

        reservation = reservations[0]
        if reservation["review_required"]:
            if args.reviewer == "none" or args.reviewer_relation == "none":
                raise SystemExit("routing requires a reviewer")
            if args.review_outcome == "none":
                raise SystemExit("routing requires a review outcome")
            if args.overall == "passed" and args.review_outcome != "accepted":
                raise SystemExit("passed requires an accepted mandatory review")

        event = {
            "event": "task_completed",
            "ts": utc_now(),
            "task_id": args.task_id,
            "policy_version": reservation["policy_version"],
            "area_id": reservation["area_id"],
            "task_type": reservation["task_type"],
            "risk": reservation["risk"],
            "intended_pattern": reservation["intended_pattern"],
            "sentinel_counter_key": reservation["sentinel_counter_key"],
            "routing_sequence": reservation["routing_sequence"],
            "sentinel_sequence": reservation["sentinel_sequence"],
            "calibration": reservation["calibration"],
            "sentinel": reservation["sentinel"],
            "review_required": reservation["review_required"],
            "assignment": {
                "planner": args.planner,
                "writer": args.writer,
                "reviewer": args.reviewer,
            },
            "reviewer_relation": args.reviewer_relation,
            "review_outcome": args.review_outcome,
            "review_rework_rounds": args.review_rework_rounds,
            "retries": {
                "implementation": args.implementation_retries,
                "verification": args.verification_retries,
                "plan_correction": args.plan_corrections,
            },
            "verify": {
                "overall": args.overall,
                "passed": args.passed,
                "failed": args.failed,
                "skipped": args.skipped,
                "environment_blocked": args.environment_blocked,
            },
            "fallback_reason": args.fallback_reason,
            "rate_limit_hits": args.rate_limit_hits,
            "usage": {
                "status": args.usage_status,
                "value": args.usage_value,
                "unit": args.usage_unit,
            },
            "interventions": args.intervention,
            "regression_of": args.regression_of,
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
