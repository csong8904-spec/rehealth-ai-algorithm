"""Download and verify Wrist PPG During Exercise v1.0.0 from PhysioNet S3."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


S3_ROOT = "https://physionet-open.s3.amazonaws.com"
PREFIX = "wrist/1.0.0/"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def list_keys() -> list[str]:
    url = f"{S3_ROOT}/?list-type=2&prefix={PREFIX}"
    with urllib.request.urlopen(url, timeout=60) as response:
        root = ET.fromstring(response.read())
    namespace = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    return [node.text for node in root.findall("s3:Contents/s3:Key", namespace) if node.text]


def download(key: str, destination: Path) -> str:
    target = destination / Path(key).name
    if target.exists() and target.stat().st_size > 0:
        return f"skip {target.name}"
    temporary = target.with_suffix(target.suffix + ".part")
    urllib.request.urlretrieve(f"{S3_ROOT}/{key}", temporary)
    temporary.replace(target)
    return f"download {target.name}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/raw/wrist-ppg-1.0.0")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    destination = Path(args.output)
    destination.mkdir(parents=True, exist_ok=True)
    keys = list_keys()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        for message in executor.map(lambda key: download(key, destination), keys):
            print(message)

    checksums: dict[str, str] = {}
    for line in (destination / "SHA256SUMS.txt").read_text(encoding="ascii").splitlines():
        expected, filename = line.split(maxsplit=1)
        checksums[filename.strip()] = expected.lower()
    failures: list[str] = []
    for filename, expected in checksums.items():
        path = destination / filename
        if not path.exists() or sha256(path) != expected:
            failures.append(filename)
    if failures:
        raise SystemExit(f"checksum failures: {failures}")
    print(f"verified {len(checksums)} files")


if __name__ == "__main__":
    main()
