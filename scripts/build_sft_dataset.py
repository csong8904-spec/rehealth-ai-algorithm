"""Build auditable SFT JSONL examples without exposing real user data."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from healthsynth.llm import SYSTEM_POLICY


def target_text(level: str, confidence: float, hr: float, sleep: float) -> str:
    advice = {
        "低": "建议保持规律作息并继续观察。",
        "中": "建议优先保证休息并补充有效数据；若异常持续或伴随不适，请咨询专业人员。",
        "高": "建议尽快复测；如伴随明显不适，请及时联系专业人员。",
    }[level]
    return (
        f"本周期健康趋势提示等级为{level}，模型置信度{confidence:.0%}。"
        f"静息心率相对个人基线变化{hr:+.1%}，睡眠时长相对个人基线变化{sleep:+.1%}。"
        f"{advice}本报告由人工智能生成，仅供健康趋势参考，不构成医疗诊断。"
    )


def build_examples(count: int, seed: int) -> list[dict[str, object]]:
    rng = random.Random(seed)
    examples: list[dict[str, object]] = []
    for index in range(count):
        hr = rng.uniform(-0.12, 0.30)
        sleep = rng.uniform(-0.35, 0.15)
        score = max(0.0, min(1.0, 0.25 + max(hr, 0) * 2.0 + max(-sleep, 0) * 1.2))
        level = "低" if score < 0.35 else "中" if score < 0.70 else "高"
        confidence = rng.uniform(0.70, 0.94)
        facts = {
            "sample_id": f"synthetic-{index:06d}",
            "risk_level": level,
            "confidence": round(confidence, 4),
            "evidence": [
                f"静息心率相对个人基线变化{hr:+.1%}",
                f"睡眠时长相对个人基线变化{sleep:+.1%}",
            ],
            "allowed_advice": ["继续观察", "保证休息", "持续不适时咨询专业人员"],
        }
        examples.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_POLICY},
                    {"role": "user", "content": json.dumps(facts, ensure_ascii=False, sort_keys=True)},
                    {"role": "assistant", "content": target_text(level, confidence, hr, sleep)},
                ],
                "metadata": {"source": "synthetic-template", "review_status": "not-human-reviewed"},
            }
        )
    return examples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/sft/rehealth_sft.synthetic.jsonl")
    parser.add_argument("--count", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20261007)
    args = parser.parse_args()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for example in build_examples(args.count, args.seed):
            handle.write(json.dumps(example, ensure_ascii=False) + "\n")
    print(f"wrote {args.count} examples to {path}")


if __name__ == "__main__":
    main()
