from __future__ import annotations

import argparse
import json

from healthsynth.signal_processing import create_signal_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("header")
    parser.add_argument("annotation")
    parser.add_argument("--output", default="artifacts/signal-features/wrist-s1-walk.json")
    args = parser.parse_args()
    report = create_signal_report(args.header, args.annotation, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
