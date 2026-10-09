"""Minimal reader for interleaved WFDB format-16 records used in the pilot dataset."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


GAIN_PATTERN = re.compile(r"^(?P<gain>[-+0-9.]+)(?:\((?P<baseline>[-+0-9]+)\))?/(?P<unit>.+)$")


@dataclass(frozen=True)
class Channel:
    name: str
    gain: float
    baseline: int
    unit: str


@dataclass(frozen=True)
class RecordHeader:
    record_name: str
    channels: tuple[Channel, ...]
    sample_rate_hz: float
    samples: int
    comment: str


def read_header(path: str | Path) -> RecordHeader:
    header_path = Path(path)
    lines = header_path.read_text(encoding="ascii").splitlines()
    first = lines[0].split()
    record_name, channel_count, sample_rate, sample_count = first[:4]
    channels: list[Channel] = []
    comments: list[str] = []
    for line in lines[1:]:
        if line.startswith("#"):
            comments.append(line[1:].strip())
            continue
        parts = line.split()
        if len(parts) < 9 or parts[1] != "16":
            raise ValueError(f"仅支持单文件交错WFDB format 16：{line}")
        gain_match = GAIN_PATTERN.match(parts[2])
        if not gain_match:
            raise ValueError(f"无法解析增益字段：{parts[2]}")
        channels.append(
            Channel(
                name=parts[-1],
                gain=float(gain_match.group("gain")),
                baseline=int(gain_match.group("baseline") or 0),
                unit=gain_match.group("unit"),
            )
        )
    if len(channels) != int(channel_count):
        raise ValueError("头文件通道数不一致")
    return RecordHeader(
        record_name=record_name,
        channels=tuple(channels),
        sample_rate_hz=float(sample_rate),
        samples=int(sample_count),
        comment="; ".join(comments),
    )


def read_digital_signal(header_path: str | Path) -> tuple[RecordHeader, np.ndarray]:
    header = read_header(header_path)
    data_path = Path(header_path).with_suffix(".dat")
    expected_values = header.samples * len(header.channels)
    values = np.fromfile(data_path, dtype="<i2")
    if values.size != expected_values:
        raise ValueError(f"数据长度不匹配：期望{expected_values}，实际{values.size}")
    return header, values.reshape(header.samples, len(header.channels))


def summarize_record(header_path: str | Path, output_path: str | Path | None = None) -> dict[str, object]:
    header, signal = read_digital_signal(header_path)
    channel_summaries: list[dict[str, object]] = []
    for index, channel in enumerate(header.channels):
        values = signal[:, index].astype(np.float64)
        differences = np.diff(values)
        channel_summaries.append(
            {
                "name": channel.name,
                "unit": channel.unit,
                "raw_min": float(values.min()),
                "raw_max": float(values.max()),
                "raw_mean": float(values.mean()),
                "raw_std": float(values.std()),
                "flatline_fraction": float(np.mean(differences == 0)),
                "clipping_fraction": float(np.mean((values == -32768) | (values == 32767))),
            }
        )
    summary: dict[str, object] = {
        "record": header.record_name,
        "activity": header.comment,
        "sample_rate_hz": header.sample_rate_hz,
        "samples": header.samples,
        "duration_seconds": header.samples / header.sample_rate_hz,
        "channel_count": len(header.channels),
        "channels": channel_summaries,
        "source_class": "public-licensed-real-signal",
    }
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
