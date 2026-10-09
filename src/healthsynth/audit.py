"""Append-only, hash-chained inference audit records without raw health values."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from .config import ALGORITHM_NAME, ALGORITHM_VERSION


@dataclass(frozen=True)
class AuditRecord:
    timestamp_utc: str
    algorithm_name: str
    algorithm_version: str
    pseudonymous_user_hash: str
    input_digest: str
    result_digest: str
    risk_level: str
    safety_actions: tuple[str, ...]
    previous_record_hash: str
    record_hash: str


class HashChainAuditLog:
    def __init__(self, path: str | Path, *, salt: str) -> None:
        if len(salt) < 16:
            raise ValueError("审计盐值至少16个字符，且必须由密钥管理系统提供")
        self.path = Path(path)
        self.salt = salt

    @staticmethod
    def _canonical(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def _digest(self, value: object) -> str:
        return hashlib.sha256((self.salt + self._canonical(value)).encode("utf-8")).hexdigest()

    def _previous_hash(self) -> str:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return "GENESIS"
        with self.path.open("rb") as handle:
            handle.seek(0, 2)
            position = handle.tell() - 1
            while position > 0:
                handle.seek(position)
                if handle.read(1) == b"\n" and position < handle.seek(0, 2) - 1:
                    break
                position -= 1
            handle.seek(position + 1 if position > 0 else 0)
            line = handle.readline().decode("utf-8")
        return str(json.loads(line)["record_hash"])

    def append(
        self,
        *,
        user_key: str,
        input_summary: Mapping[str, object],
        result_summary: Mapping[str, object],
        risk_level: str,
        safety_actions: tuple[str, ...],
    ) -> AuditRecord:
        previous = self._previous_hash()
        unsigned = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "algorithm_name": ALGORITHM_NAME,
            "algorithm_version": ALGORITHM_VERSION,
            "pseudonymous_user_hash": self._digest(user_key),
            "input_digest": self._digest(input_summary),
            "result_digest": self._digest(result_summary),
            "risk_level": risk_level,
            "safety_actions": safety_actions,
            "previous_record_hash": previous,
        }
        record = AuditRecord(**unsigned, record_hash=self._digest(unsigned))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(self._canonical(asdict(record)) + "\n")
        return record

    def verify(self) -> bool:
        previous = "GENESIS"
        if not self.path.exists():
            return True
        for line in self.path.read_text(encoding="utf-8").splitlines():
            payload = json.loads(line)
            record_hash = payload.pop("record_hash")
            if payload["previous_record_hash"] != previous or self._digest(payload) != record_hash:
                return False
            previous = record_hash
        return True
