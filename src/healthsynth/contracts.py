"""Stable data contracts for the model and service layers."""

from dataclasses import dataclass, field
from typing import Mapping, Sequence


@dataclass(frozen=True)
class SensorSummary:
    user_key: str
    period_start: str
    period_end: str
    valid_coverage: float
    metrics: Mapping[str, float]
    baseline: Mapping[str, float]


@dataclass(frozen=True)
class HealthReport:
    data_quality_score: float
    anomaly_score: float | None
    risk_level: str
    confidence: float
    evidence: Sequence[str]
    report_text: str
    synthesis_label: str = "本内容由人工智能生成，仅用于健康趋势参考，不构成医疗诊断。"
    safety_actions: Sequence[str] = field(default_factory=tuple)

