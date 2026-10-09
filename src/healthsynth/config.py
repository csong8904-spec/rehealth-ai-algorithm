"""Versioned production defaults. Changes require model re-validation."""

ALGORITHM_NAME = "ReHealth AI健康趋势报告生成合成算法"
ALGORITHM_VERSION = "0.1.0"
FEATURE_SCHEMA_VERSION = "1.0"
MINIMUM_COVERAGE = 0.70
MEDIUM_RISK_THRESHOLD = 0.35
HIGH_RISK_THRESHOLD = 0.70

FEATURE_NAMES = (
    "valid_coverage",
    "resting_hr_relative_change",
    "sleep_duration_relative_change",
    "activity_relative_change",
    "spo2_relative_change",
    "resting_hr_missing",
    "sleep_missing",
    "spo2_missing",
)
