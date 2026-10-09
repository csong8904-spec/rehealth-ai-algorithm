"""Trainable PPG-motion candidate ranker with subject-isolated evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .signal_processing import _standardize, read_wfdb_annotations
from .motion_denoising import remove_motion_artifacts
from .wfdb_simple import read_digital_signal


@dataclass(frozen=True)
class CandidateGroup:
    record: str
    subject: str
    target_bpm: float
    candidate_rates: np.ndarray
    features: np.ndarray


def _activity_features(record: str) -> tuple[float, float, float]:
    return (float("walk" in record), float("run" in record), float("bike" in record))


def _spectra(
    ppg: np.ndarray,
    accelerometer: np.ndarray,
    sample_rate: float,
    *,
    adaptive_denoise: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if adaptive_denoise:
        ppg = remove_motion_artifacts(ppg, accelerometer)
    window = np.hanning(ppg.size)
    frequencies = np.fft.rfftfreq(ppg.size, 1.0 / sample_rate)
    ppg_power = np.abs(np.fft.rfft(_standardize(ppg) * window)) ** 2
    motion_power = np.zeros_like(ppg_power)
    for axis in range(accelerometer.shape[1]):
        motion_power += np.abs(np.fft.rfft(_standardize(accelerometer[:, axis]) * window)) ** 2
    band = (frequencies >= 0.7) & (frequencies <= 3.0)
    return frequencies[band] * 60.0, ppg_power[band], motion_power[band]


def _candidate_indices(rates: np.ndarray, score: np.ndarray, count: int = 8) -> list[int]:
    chosen: list[int] = []
    for index in np.argsort(score)[::-1]:
        if all(abs(rates[index] - rates[other]) >= 4.0 for other in chosen):
            chosen.append(int(index))
        if len(chosen) == count:
            break
    return chosen


def build_groups(
    root: str | Path,
    *,
    window_seconds: float = 16.0,
    stride_seconds: float = 8.0,
    adaptive_denoise: bool = False,
) -> list[CandidateGroup]:
    groups: list[CandidateGroup] = []
    for header_path in sorted(Path(root).glob("*.hea")):
        header, signal = read_digital_signal(header_path)
        names = [channel.name for channel in header.channels]
        ppg_index = names.index("wrist_ppg")
        accelerometer_indices = [
            names.index("wrist_low_noise_accelerometer_x"),
            names.index("wrist_low_noise_accelerometer_y"),
            names.index("wrist_low_noise_accelerometer_z"),
        ]
        annotations = read_wfdb_annotations(header_path.with_suffix(".atr"))
        window_size = int(window_seconds * header.sample_rate_hz)
        stride_size = int(stride_seconds * header.sample_rate_hz)
        activity = _activity_features(header.record_name)
        for start in range(0, header.samples - window_size + 1, stride_size):
            stop = start + window_size
            events = annotations[(annotations >= start) & (annotations < stop)]
            intervals = np.diff(events) / header.sample_rate_hz
            intervals = intervals[(intervals >= 0.25) & (intervals <= 2.0)]
            if intervals.size < 4:
                continue
            target = float(60.0 / np.median(intervals))
            ppg = signal[start:stop, ppg_index]
            accelerometer = signal[start:stop, accelerometer_indices]
            rates, ppg_power, motion_power = _spectra(
                ppg,
                accelerometer,
                header.sample_rate_hz,
                adaptive_denoise=adaptive_denoise,
            )
            ppg_normalized = ppg_power / max(float(ppg_power.max()), 1e-8)
            motion_normalized = motion_power / max(float(motion_power.max()), 1e-8)
            adjusted = ppg_normalized / (1.0 + 50.0 * motion_normalized)
            candidates = _candidate_indices(rates, adjusted)
            cadence = float(rates[int(np.argmax(motion_normalized))])
            rows: list[list[float]] = []
            for rank, index in enumerate(candidates):
                rate = float(rates[index])
                half_index = int(np.argmin(np.abs(rates - rate / 2.0)))
                double_index = int(np.argmin(np.abs(rates - rate * 2.0)))
                rows.append(
                    [
                        rate / 180.0,
                        float(ppg_normalized[index]),
                        float(motion_normalized[index]),
                        float(adjusted[index]),
                        float(ppg_normalized[half_index]),
                        float(ppg_normalized[double_index]),
                        abs(rate - cadence) / 180.0,
                        cadence / 180.0,
                        rank / max(1, len(candidates) - 1),
                        *activity,
                    ]
                )
            groups.append(
                CandidateGroup(
                    record=header.record_name,
                    subject=header.record_name.split("_")[0],
                    target_bpm=target,
                    candidate_rates=rates[candidates],
                    features=np.asarray(rows, dtype=np.float64),
                )
            )
    return groups


@dataclass
class CandidateRanker:
    weights: np.ndarray
    bias: float
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, groups: list[CandidateGroup], epochs: int = 1200) -> "CandidateRanker":
        features = np.vstack([group.features for group in groups])
        labels = np.concatenate(
            [
                np.eye(len(group.candidate_rates), dtype=np.float64)[
                    int(np.argmin(np.abs(group.candidate_rates - group.target_bpm)))
                ]
                for group in groups
            ]
        )
        mean = features.mean(axis=0)
        scale = features.std(axis=0)
        scale[scale < 1e-8] = 1.0
        normalized = (features - mean) / scale
        weights = np.zeros(features.shape[1], dtype=np.float64)
        bias = 0.0
        positive_weight = max(1.0, float((labels == 0).sum() / max(1, (labels == 1).sum())))
        for _ in range(epochs):
            logits = np.clip(normalized @ weights + bias, -25.0, 25.0)
            probabilities = 1.0 / (1.0 + np.exp(-logits))
            sample_weights = np.where(labels == 1, positive_weight, 1.0)
            error = (probabilities - labels) * sample_weights
            weights -= 0.025 * (normalized.T @ error / sample_weights.sum() + 0.02 * weights)
            bias -= 0.025 * float(error.sum() / sample_weights.sum())
        return cls(weights, bias, mean, scale)

    @classmethod
    def fit_group_softmax(
        cls,
        groups: list[CandidateGroup],
        epochs: int = 1200,
        learning_rate: float = 0.04,
    ) -> "CandidateRanker":
        """Fit a listwise ranker where candidates compete inside each window."""
        features = np.vstack([group.features for group in groups])
        mean = features.mean(axis=0)
        scale = features.std(axis=0)
        scale[scale < 1e-8] = 1.0
        normalized_groups = [(group.features - mean) / scale for group in groups]
        labels = [
            int(np.argmin(np.abs(group.candidate_rates - group.target_bpm))) for group in groups
        ]
        weights = np.zeros(features.shape[1], dtype=np.float64)
        buckets: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        for candidate_count in sorted({item.shape[0] for item in normalized_groups}):
            indices = [
                index
                for index, item in enumerate(normalized_groups)
                if item.shape[0] == candidate_count
            ]
            buckets[candidate_count] = (
                np.stack([normalized_groups[index] for index in indices]),
                np.asarray([labels[index] for index in indices], dtype=int),
            )
        for _ in range(epochs):
            gradient = np.zeros_like(weights)
            for normalized, bucket_labels in buckets.values():
                logits = np.clip(normalized @ weights, -25.0, 25.0)
                logits -= logits.max(axis=1, keepdims=True)
                probabilities = np.exp(logits)
                probabilities /= probabilities.sum(axis=1, keepdims=True)
                probabilities[np.arange(probabilities.shape[0]), bucket_labels] -= 1.0
                gradient += np.einsum("nkf,nk->f", normalized, probabilities)
            gradient = gradient / len(groups) + 0.02 * weights
            weights -= learning_rate * gradient
        return cls(weights, 0.0, mean, scale)

    def score(self, features: np.ndarray) -> np.ndarray:
        normalized = (features - self.mean) / self.scale
        logits = np.clip(normalized @ self.weights + self.bias, -25.0, 25.0)
        return 1.0 / (1.0 + np.exp(-logits))

    def predict_group(self, group: CandidateGroup) -> float:
        return float(group.candidate_rates[int(np.argmax(self.score(group.features)))])

    def save(self, path: str | Path, *, metadata: dict[str, object] | None = None) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "model_type": "ppg-motion-candidate-ranker",
                    "weights": self.weights.tolist(),
                    "bias": self.bias,
                    "mean": self.mean.tolist(),
                    "scale": self.scale.tolist(),
                    "metadata": metadata or {},
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def decode_candidate_sequence(
    groups: list[CandidateGroup],
    ranker: CandidateRanker,
    *,
    transition_scale_bpm: float = 18.0,
    harmonic_jump_penalty: float = 1.25,
    double_rate_penalty: float = 0.65,
) -> tuple[np.ndarray, np.ndarray]:
    """Decode a record jointly so isolated motion harmonics cannot dominate.

    The decoder only sees PPG/accelerometer-derived candidates and ranker scores.
    ECG annotations remain evaluation labels and are never used by this function.
    """
    if not groups:
        return np.asarray([], dtype=float), np.asarray([], dtype=float)
    emissions: list[np.ndarray] = []
    for group in groups:
        scores = np.clip(ranker.score(group.features), 1e-6, 1.0 - 1e-6)
        log_odds = np.log(scores / (1.0 - scores))
        adjusted = log_odds.copy()
        for index, rate in enumerate(group.candidate_rates):
            half_matches = np.where(np.abs(group.candidate_rates - rate / 2.0) <= 7.5)[0]
            if half_matches.size:
                half_score = float(np.max(scores[half_matches]))
                ratio = half_score / max(float(scores[index]), 1e-6)
                adjusted[index] -= double_rate_penalty * min(1.0, ratio)
        emissions.append(adjusted)

    costs = emissions[0].copy()
    backpointers: list[np.ndarray] = []
    for step in range(1, len(groups)):
        previous_rates = groups[step - 1].candidate_rates
        current_rates = groups[step].candidate_rates
        next_costs = np.full(current_rates.size, -np.inf)
        pointers = np.zeros(current_rates.size, dtype=int)
        for current_index, current_rate in enumerate(current_rates):
            changes = np.abs(previous_rates - current_rate)
            transition = -changes / transition_scale_bpm
            harmonic_jump = (
                (np.abs(previous_rates - 2.0 * current_rate) <= 7.5)
                | (np.abs(2.0 * previous_rates - current_rate) <= 7.5)
            )
            transition -= harmonic_jump_penalty * harmonic_jump
            alternatives = costs + transition
            pointers[current_index] = int(np.argmax(alternatives))
            next_costs[current_index] = alternatives[pointers[current_index]] + emissions[step][current_index]
        costs = next_costs
        backpointers.append(pointers)

    chosen = [int(np.argmax(costs))]
    for pointers in reversed(backpointers):
        chosen.append(int(pointers[chosen[-1]]))
    chosen.reverse()
    rates = np.asarray(
        [group.candidate_rates[index] for group, index in zip(groups, chosen)], dtype=float
    )
    margins = np.asarray(
        [
            float(np.partition(emission, -1)[-1] - np.partition(emission, -2)[-2])
            if emission.size > 1
            else float(emission[0])
            for emission in emissions
        ],
        dtype=float,
    )
    return rates, margins
