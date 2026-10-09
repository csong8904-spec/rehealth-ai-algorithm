"""Command line entry points for training and demonstration."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .contracts import SensorSummary
from .service import ReHealthService
from .training import train_and_evaluate


def _train(args: argparse.Namespace) -> None:
    report = train_and_evaluate(Path(args.output))
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _demo(args: argparse.Namespace) -> None:
    service = ReHealthService.from_model_file(args.model)
    sample = SensorSummary(
        user_key="demo-user",
        period_start="2026-10-01",
        period_end="2026-10-07",
        valid_coverage=0.94,
        metrics={
            "resting_heart_rate": 75.0,
            "sleep_duration_hours": 5.9,
            "daily_steps": 5100.0,
            "spo2": 96.0,
        },
        baseline={
            "resting_heart_rate": 66.0,
            "sleep_duration_hours": 7.1,
            "daily_steps": 7200.0,
            "spo2": 97.0,
        },
    )
    print(json.dumps(asdict(service.generate_report(sample)), ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="ReHealth AI model utilities")
    subparsers = parser.add_subparsers(required=True)
    train = subparsers.add_parser("train-synthetic", help="Train a pipeline-validation model")
    train.add_argument("--output", default="artifacts")
    train.set_defaults(func=_train)
    demo = subparsers.add_parser("demo", help="Generate one bounded health report")
    demo.add_argument("--model", default="artifacts/risk_model.json")
    demo.set_defaults(func=_demo)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
