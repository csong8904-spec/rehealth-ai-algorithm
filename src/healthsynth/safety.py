"""Output-boundary controls for the report generator prototype."""

from __future__ import annotations

import re


PROHIBITED_PHRASES = (
    "已经确诊",
    "保证治愈",
    "无需就医",
    "立即服用",
    "停止服药",
)

PROHIBITED_PATTERNS = (
    ("疾病确诊", re.compile(r"(?:你|用户|患者)?(?:已|已经|可以)?(?:确诊|诊断为|患有)(?!风险)")),
    ("处方或用药指令", re.compile(r"(?:服用|停用|加量|减量|换用).{0,12}(?:药|片|胶囊|毫克|mg)")),
    ("疗效保证", re.compile(r"(?:保证|一定|百分之百).{0,10}(?:治愈|康复|有效)")),
    ("替代就医", re.compile(r"(?:无需|不用|不必).{0,6}(?:就医|看医生|复诊)")),
    ("急救决策", re.compile(r"(?:无需急救|可以排除急症|肯定不是急症)")),
)


def validate_generated_text(text: str) -> tuple[bool, tuple[str, ...]]:
    phrase_hits = [phrase for phrase in PROHIBITED_PHRASES if phrase in text]
    pattern_hits = [label for label, pattern in PROHIBITED_PATTERNS if pattern.search(text)]
    hits = tuple(dict.fromkeys([*phrase_hits, *pattern_hits]))
    return not hits, hits


def safe_fallback() -> str:
    return "当前数据不足以形成可靠趋势判断。建议继续佩戴设备并在身体不适时咨询专业人员。"

