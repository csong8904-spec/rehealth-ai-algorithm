"""Reproducible synthetic-data training harness for pipeline verification."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .config import FEATURE_NAMES
from .model import RiskModel, binary_metrics


def generate_synthetic_dataset(users: int = 1200, seed: int = 20261007) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    coverage = rng.uniform(0.70, 1.00, users)
    hr = rng.normal(0.02, 0.12, users)
    sleep = rng.normal(-0.03, 0.18, users)
    activity = rng.normal(0.00, 0.25, users)
    spo2 = rng.normal(-0.002, 0.008, users)
    hr_missing = rng.binomial(1, 0.04, users)
    sleep_missing = rng.binomial(1, 0.10, users)
    spo2_missing = rng.binomial(1, 0.25, users)
    features = np.column_stack(
        [coverage, hr, sleep, activity, spo2, hr_missing, sleep_missing, spo2_missing]
    ).astype(np.float64)
    latent = (
        8.0 * np.maximum(hr, 0)
        + 4.5 * np.maximum(-sleep, 0)
        + 2.3 * np.maximum(-activity, 0)
        + 18.0 * np.maximum(-spo2, 0)
        + 0.7 * hr_missing
        + 0.4 * sleep_missing
        - 2.1
        + rng.normal(0, 0.45, users)
    )
    labels = (latent > 0).astype(np.float64)
    user_ids = np.arange(users)
    assert features.shape[1] == len(FEATURE_NAMES)
    return features, labels, user_ids


def train_and_evaluate(output_dir: Path) -> dict[str, object]:
    features, labels, user_ids = generate_synthetic_dataset()
    rng = np.random.default_rng(42)
    shuffled = rng.permutation(user_ids)
    train_end = int(len(shuffled) * 0.70)
    validation_end = int(len(shuffled) * 0.85)
    train_ids = shuffled[:train_end]
    validation_ids = shuffled[train_end:validation_end]
    test_ids = shuffled[validation_end:]

    model = RiskModel.initialize()
    losses = model.fit(features[train_ids], labels[train_ids])
    validation_metrics = binary_metrics(labels[validation_ids], model.predict_proba(features[validation_ids]))
    test_metrics = binary_metrics(labels[test_ids], model.predict_proba(features[test_ids]))

    output_dir.mkdir(parents=True, exist_ok=True)
    model.save(output_dir / "risk_model.json")
    report: dict[str, object] = {
        "data_class": "synthetic-pipeline-validation-only",
        "seed": 20261007,
        "split": {"train": len(train_ids), "validation": len(validation_ids), "test": len(test_ids)},
        "training": {"initial_loss": losses[0], "final_loss": losses[-1]},
        "validation": validation_metrics,
        "test": test_metrics,
        "limitations": [
            "该模型仅验证工程流程，不得用于真实用户或备案效果证明",
            "生产模型必须使用经授权的真实目标设备数据重新训练与验证",
        ],
    }
    (output_dir / "evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report
