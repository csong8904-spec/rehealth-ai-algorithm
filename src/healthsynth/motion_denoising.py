"""Motion-reference denoising for wrist PPG waveforms."""

from __future__ import annotations

import numpy as np

from .signal_processing import _standardize


def remove_motion_artifacts(
    ppg: np.ndarray,
    accelerometer: np.ndarray,
    *,
    lag_samples: tuple[int, ...] = (-8, -4, 0, 4, 8),
    ridge: float = 0.25,
) -> np.ndarray:
    """Remove the acceleration-correlated component with ridge projection.

    This is fitted independently inside each inference window and has no access
    to ECG labels or future records. Lagged acceleration captures sensor-motion
    coupling that is slightly offset from the optical channel.
    """
    values = _standardize(np.asarray(ppg, dtype=float))
    motion = np.asarray(accelerometer, dtype=float)
    if values.ndim != 1 or motion.ndim != 2 or motion.shape[0] != values.size:
        raise ValueError("PPG and accelerometer must share a one-dimensional time axis")
    if motion.shape[1] < 1 or values.size < 32:
        return values.copy()

    columns = [np.ones(values.size), np.linspace(-1.0, 1.0, values.size)]
    for axis in range(motion.shape[1]):
        standardized = _standardize(motion[:, axis])
        for lag in lag_samples:
            shifted = np.roll(standardized, lag)
            if lag > 0:
                shifted[:lag] = standardized[0]
            elif lag < 0:
                shifted[lag:] = standardized[-1]
            columns.append(shifted)
    design = np.column_stack(columns)
    gram = design.T @ design
    penalty = np.eye(gram.shape[0]) * ridge
    penalty[:2, :2] = 0.0
    coefficients = np.linalg.solve(gram + penalty, design.T @ values)
    residual = values - design @ coefficients
    return _standardize(residual)
