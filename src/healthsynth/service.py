"""End-to-end inference service independent from any web framework."""

from __future__ import annotations

from pathlib import Path

from .config import HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD, MINIMUM_COVERAGE
from .contracts import HealthReport, SensorSummary
from .features import extract_features
from .model import RiskModel
from .safety import safe_fallback, validate_generated_text
from .synthesis import ConstrainedChineseGenerator, TextGenerator


class ReHealthService:
    def __init__(self, model: RiskModel, generator: TextGenerator | None = None) -> None:
        self.model = model
        self.generator = generator or ConstrainedChineseGenerator()

    @classmethod
    def from_model_file(cls, path: str | Path) -> "ReHealthService":
        return cls(RiskModel.load(Path(path)))

    def generate_report(self, sample: SensorSummary) -> HealthReport:
        features = extract_features(sample.valid_coverage, sample.metrics, sample.baseline)
        quality = float(features.values[0])
        if quality < MINIMUM_COVERAGE:
            return HealthReport(
                data_quality_score=quality,
                anomaly_score=None,
                risk_level="无法评估",
                confidence=0.0,
                evidence=features.evidence,
                report_text=safe_fallback(),
                safety_actions=("有效覆盖率不足，已阻断风险结论",),
            )
        probability = float(self.model.predict_proba(features.values)[0])
        level = "低" if probability < MEDIUM_RISK_THRESHOLD else "中" if probability < HIGH_RISK_THRESHOLD else "高"
        confidence = max(probability, 1.0 - probability) * quality
        facts: dict[str, object] = {
            "risk_level": level,
            "confidence": confidence,
            "evidence": features.evidence,
        }
        report_text = self.generator.generate(facts)
        is_safe, hits = validate_generated_text(report_text)
        actions: tuple[str, ...] = ()
        if not is_safe:
            report_text = safe_fallback()
            actions = (f"命中禁止表述：{','.join(hits)}",)
        return HealthReport(
            data_quality_score=quality,
            anomaly_score=probability,
            risk_level=level,
            confidence=confidence,
            evidence=features.evidence,
            report_text=report_text,
            safety_actions=actions,
        )
