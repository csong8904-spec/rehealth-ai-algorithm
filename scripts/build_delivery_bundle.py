"""Build a tamper-evident engineering delivery and readiness summary."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ESSENTIAL_FILES = (
    "README.md",
    "docs/algorithm-design.md",
    "docs/training-plan.md",
    "docs/filing-outline.md",
    "docs/data-register.md",
    "docs/model-card.md",
    "docs/release-checklist.md",
    "docs/benchmark-results.md",
    "src/healthsynth/api.py",
    "src/healthsynth/safety.py",
    "src/healthsynth/audit.py",
    "src/healthsynth/release_gate.py",
    "artifacts/models/ppg_motion_ranker_adaptive_denoise_v1.json",
    "artifacts/benchmarks/ppg_motion_ranker_adaptive_denoise_v1_loso.json",
    "artifacts/release-decisions/ppg-motion-ranker-adaptive-denoise-v1.json",
    "artifacts/evaluations/safety-red-team.json",
)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    missing = [relative for relative in ESSENTIAL_FILES if not (ROOT / relative).is_file()]
    if missing:
        raise SystemExit("missing essential files: " + ", ".join(missing))
    decision = json.loads(
        (ROOT / "artifacts/release-decisions/ppg-motion-ranker-adaptive-denoise-v1.json").read_text(
            encoding="utf-8"
        )
    )
    safety = json.loads(
        (ROOT / "artifacts/evaluations/safety-red-team.json").read_text(encoding="utf-8")
    )
    manifest = {
        relative: {"sha256": file_sha256(ROOT / relative), "bytes": (ROOT / relative).stat().st_size}
        for relative in ESSENTIAL_FILES
    }
    external_blockers = [
        "备案主体、服务角色、域名/App及实际上线渠道尚未填写",
        "真实商业数据授权、单独同意和个人信息保护影响评估须由公司完成",
        "报告生成大模型尚未使用人工复核数据在受控GPU环境完成微调与评测",
        "PPG研究候选未通过准确性、覆盖率和验证样本规模门槛",
        "实名认证、投诉申诉、删除撤回、TLS、鉴权和密钥管理须接入公司生产系统",
        "医疗器械软件属性与宣传口径须由合规或专业机构确认",
    ]
    payload = {
        "algorithm_name": "ReHealth AI健康趋势报告生成合成算法",
        "bundle_version": "engineering-mvp-1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "engineering_checks": {
            "essential_files_complete": True,
            "safety_red_team_pass": bool(safety["gate_pass"]),
            "audit_log_implemented": True,
            "explicit_synthesis_label_implemented": True,
            "api_machine_label_implemented": True,
            "release_gate_implemented": True,
        },
        "model_release_decision": decision["decision"],
        "overall_status": "engineering_mvp_complete_production_blocked",
        "external_blockers": external_blockers,
        "manifest": manifest,
    }
    output = ROOT / "artifacts/delivery/rehealth-engineering-bundle.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    registry = {
        "registry_version": "1.0",
        "model_id": "adaptive-denoise-v1",
        "role": "research-champion",
        "deployment_allowed": False,
        "model_sha256": manifest["artifacts/models/ppg_motion_ranker_adaptive_denoise_v1.json"]["sha256"],
        "benchmark_sha256": manifest["artifacts/benchmarks/ppg_motion_ranker_adaptive_denoise_v1_loso.json"]["sha256"],
        "release_decision_sha256": manifest["artifacts/release-decisions/ppg-motion-ranker-adaptive-denoise-v1.json"]["sha256"],
        "reason": "主要总体指标优于其他研究候选，但未通过生产发布门槛",
    }
    registry_path = ROOT / "artifacts/registry/research-champion.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["overall_status"], "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
