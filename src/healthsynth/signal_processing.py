"""Auditable PPG signal-quality and heart-rate feature extraction."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .wfdb_simple import read_digital_signal


@dataclass(frozen=True)
class SignalWindow:
    start_seconds: float
    end_seconds: float
    heart_rate_bpm: float | None
    spectral_confidence: float
    motion_index: float
    clipping_fraction: float
    flatline_fraction: float
    quality_score: float


def _standardize(values: np.ndarray) -> np.ndarray:
    centered = values.astype(np.float64) - np.median(values)
    scale = np.median(np.abs(centered)) * 1.4826
    if scale < 1e-8:
        return np.zeros_like(centered)
    return centered / scale


def _dominant_rate(
    values: np.ndarray,
    sample_rate_hz: float,
    noise_reference: np.ndarray | None = None,
) -> tuple[float | None, float]:
    if values.size < sample_rate_hz * 4 or np.std(values) < 1e-8:
        return None, 0.0
    standardized = _standardize(values)
    standardized -= np.linspace(standardized[0], standardized[-1], standardized.size)
    windowed = standardized * np.hanning(standardized.size)
    spectrum = np.abs(np.fft.rfft(windowed)) ** 2
    frequencies = np.fft.rfftfreq(windowed.size, d=1.0 / sample_rate_hz)
    band = (frequencies >= 0.7) & (frequencies <= 3.0)
    band_power = spectrum[band]
    if band_power.size == 0 or band_power.sum() <= 0:
        return None, 0.0
    adjusted_power = band_power
    if noise_reference is not None:
        reference = np.atleast_2d(noise_reference)
        if reference.shape[0] != values.size and reference.shape[1] == values.size:
            reference = reference.T
        if reference.shape[0] != values.size:
            raise ValueError("运动参考信号与PPG窗口长度不一致")
        motion_power = np.zeros_like(spectrum)
        for index in range(reference.shape[1]):
            axis = _standardize(reference[:, index]) * np.hanning(reference.shape[0])
            motion_power += np.abs(np.fft.rfft(axis)) ** 2
        motion_band = motion_power[band]
        motion_normalized = motion_band / max(float(motion_band.max()), 1e-8)
        ppg_normalized = band_power / max(float(band_power.max()), 1e-8)
        adjusted_power = ppg_normalized / (1.0 + 20.0 * motion_normalized)
    peak_index = int(np.argmax(adjusted_power))
    rate = float(frequencies[band][peak_index] * 60.0)
    confidence = float(adjusted_power[peak_index] / adjusted_power.sum())
    return rate, confidence


def _motion_index(accelerometer: np.ndarray) -> float:
    standardized = np.column_stack([_standardize(accelerometer[:, index]) for index in range(3)])
    differences = np.diff(standardized, axis=0)
    return float(np.sqrt(np.mean(differences**2))) if differences.size else 0.0


def extract_ppg_windows(
    header_path: str | Path,
    *,
    window_seconds: float = 8.0,
    stride_seconds: float = 4.0,
) -> tuple[dict[str, object], list[SignalWindow]]:
    header, signal = read_digital_signal(header_path)
    names = [channel.name for channel in header.channels]
    ppg_index = names.index("wrist_ppg")
    accelerometer_indices = [
        names.index("wrist_low_noise_accelerometer_x"),
        names.index("wrist_low_noise_accelerometer_y"),
        names.index("wrist_low_noise_accelerometer_z"),
    ]
    window_size = int(round(window_seconds * header.sample_rate_hz))
    stride_size = int(round(stride_seconds * header.sample_rate_hz))
    windows: list[SignalWindow] = []
    for start in range(0, header.samples - window_size + 1, stride_size):
        stop = start + window_size
        ppg = signal[start:stop, ppg_index]
        accelerometer = signal[start:stop, accelerometer_indices]
        rate, spectral_confidence = _dominant_rate(ppg, header.sample_rate_hz, accelerometer)
        clipping = float(np.mean((ppg == -32768) | (ppg == 32767)))
        flatline = float(np.mean(np.diff(ppg) == 0))
        motion = _motion_index(accelerometer)
        motion_penalty = min(1.0, motion / 2.5)
        artifact_penalty = min(1.0, clipping * 20.0 + flatline * 5.0)
        quality = float(np.clip(spectral_confidence * (1.0 - 0.55 * motion_penalty) * (1.0 - artifact_penalty), 0, 1))
        windows.append(
            SignalWindow(
                start_seconds=start / header.sample_rate_hz,
                end_seconds=stop / header.sample_rate_hz,
                heart_rate_bpm=rate,
                spectral_confidence=spectral_confidence,
                motion_index=motion,
                clipping_fraction=clipping,
                flatline_fraction=flatline,
                quality_score=quality,
            )
        )
    valid_rates = [w.heart_rate_bpm for w in windows if w.heart_rate_bpm is not None and w.quality_score >= 0.08]
    global_rate, global_confidence = _dominant_rate(
        signal[:, ppg_index], header.sample_rate_hz, signal[:, accelerometer_indices]
    )
    summary: dict[str, object] = {
        "record": header.record_name,
        "activity": header.comment,
        "window_seconds": window_seconds,
        "stride_seconds": stride_seconds,
        "window_count": len(windows),
        "usable_window_fraction": float(len(valid_rates) / len(windows)) if windows else 0.0,
        "median_window_heart_rate_bpm": float(np.median(valid_rates)) if valid_rates else None,
        "motion_suppressed_ppg_heart_rate_bpm": global_rate,
        "global_spectral_confidence": global_confidence,
        "median_quality_score": float(np.median([w.quality_score for w in windows])) if windows else 0.0,
        "heart_rate_reliable": bool(windows and np.median([w.quality_score for w in windows]) >= 0.35),
        "warning": "工程特征，不构成医疗级心率测量",
    }
    return summary, windows


def read_wfdb_annotations(path: str | Path) -> np.ndarray:
    """Read standard two-byte WFDB annotations and return event sample indices."""
    raw = Path(path).read_bytes()
    position = 0
    sample = 0
    events: list[int] = []
    index = 0
    while index + 1 < len(raw):
        first, second = raw[index], raw[index + 1]
        index += 2
        annotation_type = second >> 2
        interval = first | ((second & 0x03) << 8)
        if annotation_type == 0 and interval == 0:
            break
        if annotation_type == 59 and index + 3 < len(raw):
            interval = int.from_bytes(raw[index : index + 4], "little", signed=True)
            index += 4
            sample += interval
            continue
        if annotation_type == 63:
            index += interval + (interval % 2)
            continue
        if annotation_type in (60, 61, 62):
            continue
        sample += interval
        if 1 <= annotation_type <= 49:
            events.append(sample)
    return np.asarray(events, dtype=np.int64)


def create_signal_report(
    header_path: str | Path,
    annotation_path: str | Path,
    output_path: str | Path,
) -> dict[str, object]:
    summary, windows = extract_ppg_windows(header_path)
    header, _ = read_digital_signal(header_path)
    annotations = read_wfdb_annotations(annotation_path)
    intervals = np.diff(annotations) / header.sample_rate_hz
    plausible = intervals[(intervals >= 0.25) & (intervals <= 2.0)]
    reference_rate = float(60.0 / np.median(plausible)) if plausible.size else None
    ppg_rate = summary["motion_suppressed_ppg_heart_rate_bpm"]
    summary["annotation_count"] = int(annotations.size)
    summary["reference_ecg_heart_rate_bpm"] = reference_rate
    summary["absolute_ppg_ecg_difference_bpm"] = (
        abs(float(ppg_rate) - reference_rate) if ppg_rate is not None and reference_rate is not None else None
    )
    difference = summary["absolute_ppg_ecg_difference_bpm"]
    summary["reference_validation_pass"] = bool(difference is not None and float(difference) <= 10.0)
    if not summary["reference_validation_pass"]:
        summary["heart_rate_reliable"] = False
        summary["release_action"] = "阻断该记录的心率结论，并进入运动伪影模型改进队列"
    else:
        summary["heart_rate_reliable"] = True
        summary["release_action"] = "通过带ECG参考的离线基准验证；仍不得视为医疗级测量"
    payload = {
        "summary": summary,
        "windows": [asdict(window) for window in windows],
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
