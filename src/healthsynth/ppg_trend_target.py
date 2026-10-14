"""Research label builder for a PPG-derived next-day physiological trend target.

Labels describe a numerical change in resting heart rate, not disease. The
builder never reads future observations into features or the personal baseline.
No predictive model is trained or approved by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import isfinite
from statistics import median
from typing import Sequence


@dataclass(frozen=True)
class DailyPPGSummary:
    subject_id: str
    day: date
    resting_heart_rate_bpm: float
    valid_coverage: float
    signal_quality: float


@dataclass(frozen=True)
class NextDayTrendExample:
    subject_id: str
    feature_day: date
    baseline_bpm: float
    current_bpm: float
    current_deviation_bpm: float
    target_day: date
    target_deviation_bpm: float
    label: int


def _valid(record: DailyPPGSummary, min_coverage: float, min_quality: float) -> bool:
    return (
        bool(record.subject_id)
        and isfinite(record.resting_heart_rate_bpm)
        and 30 <= record.resting_heart_rate_bpm <= 220
        and isfinite(record.valid_coverage)
        and min_coverage <= record.valid_coverage <= 1
        and isfinite(record.signal_quality)
        and min_quality <= record.signal_quality <= 1
    )


def build_next_day_examples(
    records: Sequence[DailyPPGSummary],
    *,
    baseline_days: int = 14,
    min_baseline_days: int = 7,
    deviation_threshold_bpm: float = 10.0,
    min_coverage: float = 0.7,
    min_quality: float = 0.7,
) -> tuple[NextDayTrendExample, ...]:
    """Create leakage-free *research* labels from authorized daily summaries.

    For each feature day, the baseline is the median of valid preceding days
    only. The following calendar day supplies the label only. Thresholds are
    configurable study definitions, not medical alarm thresholds.
    """
    if baseline_days < 1 or not 1 <= min_baseline_days <= baseline_days:
        raise ValueError("invalid baseline window")
    if not isfinite(deviation_threshold_bpm) or deviation_threshold_bpm <= 0:
        raise ValueError("invalid deviation threshold")
    if not 0 <= min_coverage <= 1 or not 0 <= min_quality <= 1:
        raise ValueError("invalid quality thresholds")
    grouped: dict[str, dict[date, DailyPPGSummary]] = {}
    for record in records:
        if not _valid(record, min_coverage, min_quality):
            continue
        days = grouped.setdefault(record.subject_id, {})
        if record.day in days:
            raise ValueError("duplicate subject/day record")
        days[record.day] = record
    examples: list[NextDayTrendExample] = []
    for subject_id, days in sorted(grouped.items()):
        for feature_day, current in sorted(days.items()):
            target_day = feature_day + timedelta(days=1)
            target = days.get(target_day)
            if target is None:
                continue
            history = [
                prior.resting_heart_rate_bpm
                for day, prior in days.items()
                if feature_day - timedelta(days=baseline_days) <= day < feature_day
            ]
            if len(history) < min_baseline_days:
                continue
            baseline = float(median(history))
            target_deviation = target.resting_heart_rate_bpm - baseline
            examples.append(
                NextDayTrendExample(
                    subject_id=subject_id,
                    feature_day=feature_day,
                    baseline_bpm=baseline,
                    current_bpm=current.resting_heart_rate_bpm,
                    current_deviation_bpm=current.resting_heart_rate_bpm - baseline,
                    target_day=target_day,
                    target_deviation_bpm=target_deviation,
                    label=int(abs(target_deviation) >= deviation_threshold_bpm),
                )
            )
    return tuple(examples)
