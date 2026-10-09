from __future__ import annotations

import argparse
import json
from pathlib import Path

from healthsynth.red_team import run_safety_evaluation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluations/safety-red-team.json"))
    args = parser.parse_args()
    result = run_safety_evaluation()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("cases", "passed", "pass_rate", "gate_pass")}, ensure_ascii=False))
    return 0 if result["gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
