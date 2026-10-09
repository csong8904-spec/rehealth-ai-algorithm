"""Batch benchmark motion-suppressed PPG heart rate against ECG annotations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from healthsynth.signal_processing import create_signal_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/raw/wrist-ppg-1.0.0")
    parser.add_argument("--output", default="artifacts/benchmarks/wrist-ppg-v1.json")
    args = parser.parse_args()
    root = Path(args.data)
    records: list[dict[str, object]] = []
    for header in sorted(root.glob("*.hea")):
        annotation = header.with_suffix(".atr")
        if not annotation.exists():
            continue
        detail_path = Path(args.output).parent / "records" / f"{header.stem}.json"
        report = create_signal_report(header, annotation, detail_path)
        summary = dict(report["summary"])
        records.append(summary)
        print(
            f"{header.stem}: ppg={summary['motion_suppressed_ppg_heart_rate_bpm']:.2f} "
            f"ecg={summary['reference_ecg_heart_rate_bpm']:.2f} "
            f"error={summary['absolute_ppg_ecg_difference_bpm']:.2f}"
        )
    errors = np.asarray(
        [float(item["absolute_ppg_ecg_difference_bpm"]) for item in records], dtype=np.float64
    )
    mean_error = float(errors.mean())
    p90_error = float(np.quantile(errors, 0.9))
    within_ten = float(np.mean(errors <= 10.0))
    gate_pass = mean_error <= 10.0 and p90_error <= 15.0 and within_ten >= 0.90
    aggregate = {
        "dataset": "Wrist PPG During Exercise v1.0.0",
        "record_count": len(records),
        "mean_absolute_error_bpm": mean_error,
        "median_absolute_error_bpm": float(np.median(errors)),
        "p90_absolute_error_bpm": p90_error,
        "within_5_bpm_fraction": float(np.mean(errors <= 5.0)),
        "within_10_bpm_fraction": within_ten,
        "release_gate": {
            "pass": gate_pass,
            "requirements": {
                "mean_absolute_error_bpm_max": 10.0,
                "p90_absolute_error_bpm_max": 15.0,
                "within_10_bpm_fraction_min": 0.90
            }
        },
        "release_status": "research-validation-only" if gate_pass else "blocked-from-production",
        "records": records,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in aggregate.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
