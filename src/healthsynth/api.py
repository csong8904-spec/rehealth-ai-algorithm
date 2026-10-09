"""Dependency-free local JSON API for controlled deployment tests."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .audit import HashChainAuditLog
from .contracts import SensorSummary
from .service import ReHealthService


class ReHealthHandler(BaseHTTPRequestHandler):
    service: ReHealthService
    audit: HashChainAuditLog
    max_body_bytes = 64 * 1024

    def _respond(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-AI-Generated", "true")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self._respond(200, {"status": "ok"})
        else:
            self._respond(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/reports":
            self._respond(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > self.max_body_bytes:
                raise ValueError("请求体大小不符合要求")
            payload = json.loads(self.rfile.read(length))
            sample = SensorSummary(
                user_key=str(payload["user_key"]),
                period_start=str(payload["period_start"]),
                period_end=str(payload["period_end"]),
                valid_coverage=float(payload["valid_coverage"]),
                metrics={str(k): float(v) for k, v in payload["metrics"].items()},
                baseline={str(k): float(v) for k, v in payload["baseline"].items()},
            )
            result = self.service.generate_report(sample)
            response = asdict(result)
            self.audit.append(
                user_key=sample.user_key,
                input_summary={
                    "period_start": sample.period_start,
                    "period_end": sample.period_end,
                    "valid_coverage": sample.valid_coverage,
                    "metric_names": sorted(sample.metrics),
                },
                result_summary={
                    "risk_level": result.risk_level,
                    "confidence": result.confidence,
                    "safety_actions": result.safety_actions,
                },
                risk_level=result.risk_level,
                safety_actions=tuple(result.safety_actions),
            )
            self._respond(200, response)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._respond(400, {"error": "invalid_request", "message": str(exc)})

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="artifacts/risk_model.json")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--audit-log", default="artifacts/audit/inference.jsonl")
    parser.add_argument("--audit-salt", required=True)
    args = parser.parse_args()
    ReHealthHandler.service = ReHealthService.from_model_file(args.model)
    ReHealthHandler.audit = HashChainAuditLog(Path(args.audit_log), salt=args.audit_salt)
    server = ThreadingHTTPServer((args.host, args.port), ReHealthHandler)
    print(f"ReHealth AI API listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
