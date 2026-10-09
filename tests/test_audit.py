import json
import tempfile
import unittest
from pathlib import Path

from healthsynth.audit import HashChainAuditLog


class AuditTests(unittest.TestCase):
    def test_hash_chain_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            audit = HashChainAuditLog(path, salt="test-only-secret-salt")
            for level in ("低", "中"):
                audit.append(
                    user_key="user-1",
                    input_summary={"metric_names": ["heart_rate"]},
                    result_summary={"risk_level": level},
                    risk_level=level,
                    safety_actions=(),
                )
            self.assertTrue(audit.verify())
            rows = path.read_text(encoding="utf-8").splitlines()
            payload = json.loads(rows[0])
            payload["risk_level"] = "高"
            rows[0] = json.dumps(payload, ensure_ascii=False)
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            self.assertFalse(audit.verify())


if __name__ == "__main__":
    unittest.main()
