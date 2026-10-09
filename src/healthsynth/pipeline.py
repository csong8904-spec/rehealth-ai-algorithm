"""Runnable contract prototype; trained neural components will replace the stubs."""

from __future__ import annotations

from .contracts import HealthReport, SensorSummary
from .safety import safe_fallback, validate_generated_text


class HealthSynthesisPipeline:
    """Produce a bounded, non-diagnostic report from validated summary data."""

    minimum_coverage = 0.70

    def run(self, sample: SensorSummary) -> HealthReport:
        quality = max(0.0, min(1.0, sample.valid_coverage))
        if quality < self.minimum_coverage:
            return HealthReport(
                data_quality_score=quality,
                anomaly_score=None,
                risk_level="无法评估",
                confidence=0.0,
                evidence=(f"有效数据覆盖率为{quality:.0%}",),
                report_text=safe_fallback(),
                safety_actions=("数据不足，已禁用风险结论",),
            )

        heart_rate = sample.metrics.get("resting_heart_rate")
        baseline = sample.baseline.get("resting_heart_rate")
        if heart_rate is None or baseline is None or baseline <= 0:
            return HealthReport(
                data_quality_score=quality,
                anomaly_score=None,
                risk_level="无法评估",
                confidence=0.0,
                evidence=("缺少静息心率或个人基线",),
                report_text=safe_fallback(),
                safety_actions=("关键指标缺失，已禁用风险结论",),
            )

        deviation = abs(heart_rate - baseline) / baseline
        risk_level = "低" if deviation < 0.08 else "中" if deviation < 0.18 else "高"
        confidence = min(0.95, quality * 0.9)
        direction = "升高" if heart_rate > baseline else "降低"
        evidence = (
            f"当前静息心率为{heart_rate:.1f}",
            f"个人基线为{baseline:.1f}",
            f"相对个人基线{direction}{deviation:.1%}",
        )
        text = (
            f"本周期静息心率较个人基线{direction}{deviation:.1%}，"
            f"当前健康趋势提示等级为{risk_level}。建议结合近期活动、睡眠和身体感受继续观察。"
        )
        is_safe, hits = validate_generated_text(text)
        actions: tuple[str, ...] = ()
        if not is_safe:
            text = safe_fallback()
            actions = (f"生成内容命中禁止表述：{','.join(hits)}",)

        return HealthReport(
            data_quality_score=quality,
            anomaly_score=min(1.0, deviation),
            risk_level=risk_level,
            confidence=confidence,
            evidence=evidence,
            report_text=text,
            safety_actions=actions,
        )

