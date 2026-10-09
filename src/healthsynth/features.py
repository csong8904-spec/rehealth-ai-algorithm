"""Feature extraction with explicit missingness and personal baselines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

from .config import FEATURE_NAMES


@dataclass(frozen=True)
class FeatureVector:
    values: np.ndarray
    evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, float]:
        return dict(zip(FEATURE_NAMES, self.values.tolist(), strict=True))


def _relative_change(current: float | None, baseline: float | None) -> tuple[float, bool]:
    if current is None or baseline is None or abs(baseline) < 1e-8:
        return 0.0, True
    return float((current - baseline) / abs(baseline)), False


def extract_features(
    valid_coverage: float,
    metrics: Mapping[str, float],
    baseline: Mapping[str, float],
) -> FeatureVector:
    coverage = float(np.clip(valid_coverage, 0.0, 1.0))
    hr_change, hr_missing = _relative_change(
        metrics.get("resting_heart_rate"), baseline.get("resting_heart_rate")
    )
    sleep_change, sleep_missing = _relative_change(
        metrics.get("sleep_duration_hours"), baseline.get("sleep_duration_hours")
    )
    activity_change, _ = _relative_change(
        metrics.get("daily_steps"), baseline.get("daily_steps")
    )
    spo2_change, spo2_missing = _relative_change(metrics.get("spo2"), baseline.get("spo2"))
    values = np.asarray(
        [
            coverage,
            np.clip(hr_change, -1.0, 1.0),
            np.clip(sleep_change, -1.0, 1.0),
            np.clip(activity_change, -1.0, 1.0),
            np.clip(spo2_change, -1.0, 1.0),
            float(hr_missing),
            float(sleep_missing),
            float(spo2_missing),
        ],
        dtype=np.float64,
    )
    evidence = (
        f"有效数据覆盖率{coverage:.0%}",
        f"静息心率相对个人基线变化{hr_change:+.1%}" if not hr_missing else "静息心率数据缺失",
        f"睡眠时长相对个人基线变化{sleep_change:+.1%}" if not sleep_missing else "睡眠数据缺失",
        f"活动量相对个人基线变化{activity_change:+.1%}",
        f"血氧相对个人基线变化{spo2_change:+.1%}" if not spo2_missing else "血氧数据缺失",
    )
    return FeatureVector(values=values, evidence=evidence)
