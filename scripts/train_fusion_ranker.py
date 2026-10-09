"""Train and subject-isolated cross-validate the PPG-motion ranker."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from healthsynth.fusion_model import CandidateRanker, build_groups, decode_candidate_sequence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/raw/wrist-ppg-1.0.0")
    parser.add_argument("--model", default="artifacts/models/ppg_motion_ranker.json")
    parser.add_argument("--report", default="artifacts/benchmarks/ppg_motion_ranker_loso.json")
    parser.add_argument("--temporal-decoder", action="store_true")
    parser.add_argument("--adaptive-denoise", action="store_true")
    parser.add_argument("--group-softmax", action="store_true")
    args = parser.parse_args()
    groups = build_groups(args.data, adaptive_denoise=args.adaptive_denoise)
    subjects = sorted({group.subject for group in groups})
    predictions: list[dict[str, object]] = []
    for subject in subjects:
        train = [group for group in groups if group.subject != subject]
        test = [group for group in groups if group.subject == subject]
        ranker = (
            CandidateRanker.fit_group_softmax(train)
            if args.group_softmax
            else CandidateRanker.fit(train)
        )
        per_record_predictions: dict[str, list[float]] = defaultdict(list)
        per_record_targets: dict[str, list[float]] = defaultdict(list)
        per_record_margins: dict[str, list[float]] = defaultdict(list)
        per_record_harmonic_ambiguity: dict[str, list[float]] = defaultdict(list)
        if args.temporal_decoder:
            test_by_record: dict[str, list] = defaultdict(list)
            for group in test:
                test_by_record[group.record].append(group)
            evaluated = [
                (group, float(decoded_rate))
                for record_groups in test_by_record.values()
                for group, decoded_rate in zip(
                    record_groups, decode_candidate_sequence(record_groups, ranker)[0]
                )
            ]
        else:
            evaluated = [(group, ranker.predict_group(group)) for group in test]
        for group, decoded_rate in evaluated:
            scores = ranker.score(group.features)
            order = np.argsort(scores)
            selected_index = int(np.argmin(np.abs(group.candidate_rates - decoded_rate)))
            per_record_predictions[group.record].append(float(decoded_rate))
            per_record_targets[group.record].append(group.target_bpm)
            margin = float(scores[order[-1]] - scores[order[-2]]) if scores.size > 1 else float(scores[order[-1]])
            per_record_margins[group.record].append(margin)
            selected_rate = float(group.candidate_rates[selected_index])
            selected_score = float(scores[selected_index])
            ambiguous = any(
                other != selected_index
                and (
                    abs(float(group.candidate_rates[other]) - 2.0 * selected_rate) <= 7.5
                    or abs(2.0 * float(group.candidate_rates[other]) - selected_rate) <= 7.5
                )
                and float(scores[other]) >= 0.5 * selected_score
                for other in range(scores.size)
            )
            per_record_harmonic_ambiguity[group.record].append(float(ambiguous))
        for record in sorted(per_record_predictions):
            window_predictions = np.asarray(per_record_predictions[record], dtype=np.float64)
            prediction = float(np.median(window_predictions))
            target = float(np.median(per_record_targets[record]))
            deviation = np.abs(window_predictions - prediction)
            predictions.append(
                {
                    "subject": subject,
                    "record": record,
                    "predicted_bpm": prediction,
                    "target_bpm": target,
                    "absolute_error_bpm": abs(prediction - target),
                    "window_count": len(per_record_predictions[record]),
                    "prediction_mad_bpm": float(np.median(deviation)),
                    "consensus_fraction_10_bpm": float(np.mean(deviation <= 10.0)),
                    "median_score_margin": float(np.median(per_record_margins[record])),
                    "harmonic_ambiguity_fraction": float(np.mean(per_record_harmonic_ambiguity[record])),
                }
            )
    errors = np.asarray([row["absolute_error_bpm"] for row in predictions], dtype=np.float64)
    metrics = {
        "validation": (
            "leave-one-subject-out with label-free temporal decoding"
            if args.temporal_decoder
            else "leave-one-subject-out"
        ),
        "candidate_version": (
            "adaptive-denoise-group-softmax-v1"
            if args.adaptive_denoise and args.group_softmax
            else "group-softmax-v1"
            if args.group_softmax
            else
            "adaptive-denoise-temporal-v1"
            if args.adaptive_denoise and args.temporal_decoder
            else "adaptive-denoise-v1"
            if args.adaptive_denoise
            else "temporal-decoder-v1"
            if args.temporal_decoder
            else "ranker-baseline-v1"
        ),
        "subjects": len(subjects),
        "records": len(predictions),
        "windows": len(groups),
        "mean_absolute_error_bpm": float(errors.mean()),
        "median_absolute_error_bpm": float(np.median(errors)),
        "p90_absolute_error_bpm": float(np.quantile(errors, 0.9)),
        "within_10_bpm_fraction": float(np.mean(errors <= 10.0)),
    }
    metrics["release_gate_pass"] = bool(
        metrics["mean_absolute_error_bpm"] <= 10.0
        and metrics["p90_absolute_error_bpm"] <= 15.0
        and metrics["within_10_bpm_fraction"] >= 0.90
    )
    selective: list[dict[str, float]] = []
    for consensus_threshold in (0.50, 0.60, 0.70, 0.80, 0.90):
        accepted = [
            row for row in predictions if float(row["consensus_fraction_10_bpm"]) >= consensus_threshold
        ]
        if not accepted:
            continue
        accepted_errors = np.asarray([row["absolute_error_bpm"] for row in accepted], dtype=np.float64)
        selective.append(
            {
                "consensus_threshold": consensus_threshold,
                "coverage": len(accepted) / len(predictions),
                "accepted_records": len(accepted),
                "mean_absolute_error_bpm": float(accepted_errors.mean()),
                "p90_absolute_error_bpm": float(np.quantile(accepted_errors, 0.9)),
                "within_10_bpm_fraction": float(np.mean(accepted_errors <= 10.0)),
            }
        )
    metrics["selective_prediction"] = selective
    harmonic_selective: list[dict[str, float]] = []
    for ambiguity_max in (0.0, 0.10, 0.20, 0.30, 0.40):
        accepted = [
            row
            for row in predictions
            if float(row["harmonic_ambiguity_fraction"]) <= ambiguity_max
            and float(row["consensus_fraction_10_bpm"]) >= 0.50
        ]
        if not accepted:
            continue
        accepted_errors = np.asarray([row["absolute_error_bpm"] for row in accepted], dtype=np.float64)
        harmonic_selective.append(
            {
                "harmonic_ambiguity_max": ambiguity_max,
                "coverage": len(accepted) / len(predictions),
                "accepted_records": len(accepted),
                "mean_absolute_error_bpm": float(accepted_errors.mean()),
                "p90_absolute_error_bpm": float(np.quantile(accepted_errors, 0.9)),
                "within_10_bpm_fraction": float(np.mean(accepted_errors <= 10.0)),
            }
        )
    metrics["harmonic_aware_selective_prediction"] = harmonic_selective
    report = {"metrics": metrics, "records": predictions}
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    final_model = (
        CandidateRanker.fit_group_softmax(groups)
        if args.group_softmax
        else CandidateRanker.fit(groups)
    )
    final_model.save(
        args.model,
        metadata={
            "candidate_version": metrics["candidate_version"],
            "adaptive_denoise": args.adaptive_denoise,
            "temporal_decoder": args.temporal_decoder,
            "training_objective": "group-softmax" if args.group_softmax else "weighted-binary",
            "validation": metrics["validation"],
            "release_gate_pass": metrics["release_gate_pass"],
        },
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
