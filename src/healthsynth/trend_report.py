"""Conservative, inspectable health-trend facts for report synthesis.

This module deliberately does not predict disease, triage emergencies, or use
the research PPG risk model. Its outputs are observations, not diagnoses.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class MetricSpec:
    label: str
    unit: str
    minimum: float
    maximum: float
    min_change: float


METRICS: dict[str, MetricSpec] = {
    "resting_heart_rate": MetricSpec("静息心率", "bpm", 30, 220, 5),
    "sleep_duration_hours": MetricSpec("睡眠时长", "小时", 0, 24, 0.5),
    "daily_steps": MetricSpec("日均步数", "步", 0, 100000, 500),
}
MINIMUM_COVERAGE = 0.7


@dataclass(frozen=True)
class TrendFact:
    metric: str
    label: str
    current: float
    baseline: float
    unit: str
    direction: str
    difference: float


@dataclass(frozen=True)
class TrendReport:
    status: str
    coverage: float
    facts: tuple[TrendFact, ...]
    text: str
    limitations: tuple[str, ...]
    synthesis_label: str = "本内容由人工智能生成，仅供健康趋势参考，不构成医疗诊断或治疗建议。"


def _checked_number(value: object, spec: MetricSpec) -> float:
    if isinstance(value, bool):
        raise ValueError("布尔值不能作为健康指标")
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{spec.label}必须是数字") from exc
    if not isfinite(number) or not spec.minimum <= number <= spec.maximum:
        raise ValueError(f"{spec.label}超出支持范围")
    return number


def make_trend_report(
    current: Mapping[str, object],
    baseline: Mapping[str, object],
    *,
    coverage: float,
) -> TrendReport:
    """Compare validated period aggregates with the same person's baseline.

    Missing or low-quality data abstains. Thresholds indicate a *noticeable
    numerical change*, never a medical abnormality or risk level.
    """
    try:
        coverage = float(coverage) if not isinstance(coverage, bool) else float("nan")
    except (TypeError, ValueError) as exc:
        raise ValueError("有效覆盖率必须在 0 到 1 之间") from exc
    if not isfinite(coverage) or not 0 <= coverage <= 1:
        raise ValueError("有效覆盖率必须在 0 到 1 之间")
    if coverage < MINIMUM_COVERAGE:
        return TrendReport(
            "insufficient_data", coverage, (),
            "有效数据覆盖不足，无法形成可靠的个人趋势报告。请补充数据后重试。",
            ("有效数据覆盖率低于 70%",),
        )
    facts: list[TrendFact] = []
    for key, spec in METRICS.items():
        if key not in current or key not in baseline:
            continue
        now = _checked_number(current[key], spec)
        reference = _checked_number(baseline[key], spec)
        difference = now - reference
        direction = "上升" if difference >= spec.min_change else "下降" if difference <= -spec.min_change else "相近"
        facts.append(TrendFact(key, spec.label, now, reference, spec.unit, direction, difference))
    if not facts:
        return TrendReport(
            "insufficient_data", coverage, (),
            "缺少可比较的本期指标和个人基线，无法形成趋势报告。",
            ("至少需要一项同时具备本期值与个人基线的支持指标",),
        )
    observations = [
        f"{fact.label}本期{fact.current:g}{fact.unit}，个人基线{fact.baseline:g}{fact.unit}，数值{fact.direction}"
        for fact in facts
    ]
    text = "；".join(observations) + "。这些是数值变化，不代表疾病风险或临床异常；测量条件、设备差异和日常活动可能影响结果。"
    return TrendReport(
        "generated", coverage, tuple(facts), text,
        ("仅比较输入的周期汇总值与个人基线", "不提供诊断、用药、急救或治疗决策"),
    )
