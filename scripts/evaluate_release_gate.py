from __future__ import annotations

import argparse
from pathlib import Path

from healthsynth.release_gate import evaluate_benchmark_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the fail-closed model release gate")
    parser.add_argument("benchmark", type=Path)
    parser.add_argument("--profile", choices=("full", "harmonic-selective"), default="full")
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--activation", type=Path)
    args = parser.parse_args()

    try:
        result = evaluate_benchmark_file(
            args.benchmark,
            args.decision,
            profile=args.profile,
            activation_path=args.activation,
        )
    except RuntimeError as exc:
        print(exc)
        return 2
    print(f"release decision: {result['decision']}")
    return 0 if result["decision"] == "approved" else 2


if __name__ == "__main__":
    raise SystemExit(main())
