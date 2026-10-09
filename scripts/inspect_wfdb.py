from __future__ import annotations

import argparse
import json

from healthsynth.wfdb_simple import summarize_record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("header")
    parser.add_argument("--output", default="artifacts/data-quality/wrist-s1-walk.json")
    args = parser.parse_args()
    print(json.dumps(summarize_record(args.header, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
