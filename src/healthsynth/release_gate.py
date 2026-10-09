"""Fail-closed release gate for physiological signal models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReleaseThresholds:
    max_mean_absolute_error_bpm: float = 10.0
    max_p90_absolute_error_bpm: float = 15.0
    min_within_10_bpm_fraction: float = 0.90
    min_coverage: float = 0.50
    min_subjects: int = 20
    min_records: int = 100


def _metric_view(metrics: dict[str, Any], profile: str) -> dict[str, Any]:
    if profile == "full":
        return {**metrics, "coverage": 1.0}
    if profile == "harmonic-selective":
        candidates = metrics.get("harmonic_aware_selective_prediction", [])
        if not candidates:
            raise ValueError("benchmark has no harmonic-aware selective metrics")
        # Choose the highest-coverage candidate that meets the accuracy targets;
        # if none does, report the highest-coverage candidate and fail closed.
        accurate = [
            row
            for row in candidates
            if row["mean_absolute_error_bpm"] <= 10.0
            and row["p90_absolute_error_bpm"] <= 15.0
            and row["within_10_bpm_fraction"] >= 0.90
        ]
        return max(accurate or candidates, key=lambda row: row["coverage"])
    raise ValueError(f"unknown release profile: {profile}")


def evaluate_release(
    benchmark: dict[str, Any],
    *,
    profile: str = "full",
    thresholds: ReleaseThresholds | None = None,
) -> dict[str, Any]:
    thresholds = thresholds or ReleaseThresholds()
    metrics = benchmark.get("metrics", {})
    selected = _metric_view(metrics, profile)
    checks = {
        "mean_absolute_error_bpm": selected["mean_absolute_error_bpm"]
        <= thresholds.max_mean_absolute_error_bpm,
        "p90_absolute_error_bpm": selected["p90_absolute_error_bpm"]
        <= thresholds.max_p90_absolute_error_bpm,
        "within_10_bpm_fraction": selected["within_10_bpm_fraction"]
        >= thresholds.min_within_10_bpm_fraction,
        "coverage": selected["coverage"] >= thresholds.min_coverage,
        "subjects": metrics.get("subjects", 0) >= thresholds.min_subjects,
        "records": metrics.get("records", 0) >= thresholds.min_records,
    }
    passed = all(checks.values())
    return {
        "schema_version": "1.0",
        "decision": "approved" if passed else "blocked",
        "profile": profile,
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "thresholds": asdict(thresholds),
        "selected_metrics": selected,
        "checks": checks,
        "failed_checks": [name for name, ok in checks.items() if not ok],
    }


def evaluate_benchmark_file(
    benchmark_path: Path,
    decision_path: Path,
    *,
    profile: str = "full",
    activation_path: Path | None = None,
) -> dict[str, Any]:
    raw = benchmark_path.read_bytes()
    benchmark = json.loads(raw)
    decision = evaluate_release(benchmark, profile=profile)
    decision["benchmark_path"] = str(benchmark_path)
    decision["benchmark_sha256"] = sha256(raw).hexdigest()
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    decision_path.write_text(
        json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if activation_path is not None:
        if decision["decision"] != "approved":
            raise RuntimeError(
                "release blocked; activation manifest was not created: "
                + ", ".join(decision["failed_checks"])
            )
        activation = {
            "schema_version": "1.0",
            "status": "active",
            "benchmark_sha256": decision["benchmark_sha256"],
            "approved_at_utc": decision["evaluated_at_utc"],
            "profile": profile,
        }
        activation_path.parent.mkdir(parents=True, exist_ok=True)
        activation_path.write_text(
            json.dumps(activation, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return decision
