"""Fact-grounded report synthesis boundary and future LLM integration point."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class TextGenerator(Protocol):
    def generate(self, facts: dict[str, object]) -> str: ...


@dataclass
class ConstrainedChineseGenerator:
    """Deterministic safe generator used until the approved local model is connected."""

    def generate(self, facts: dict[str, object]) -> str:
        risk_level = str(facts["risk_level"])
        confidence = float(facts["confidence"])
        evidence = tuple(str(item) for item in facts["evidence"])
        evidence_text = "；".join(evidence[:4])
        if risk_level == "无法评估":
            return "当前有效数据不足，暂时无法形成可靠趋势判断。建议继续佩戴设备后再次评估。"
        advice = {
            "低": "当前变化较小，建议保持规律作息并继续观察。",
            "中": "建议优先休息、补充有效数据；如异常持续或伴随不适，请咨询专业人员。",
            "高": "本结果不构成诊断。建议尽快复测；如伴随明显不适，请及时联系专业人员。",
        }[risk_level]
        return f"本周期健康趋势提示等级为{risk_level}，模型置信度{confidence:.0%}。{evidence_text}。{advice}"
