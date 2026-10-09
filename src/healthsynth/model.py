"""Small auditable risk model used to validate the end-to-end pipeline."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import ALGORITHM_NAME, ALGORITHM_VERSION, FEATURE_NAMES, FEATURE_SCHEMA_VERSION


def _sigmoid(value: np.ndarray) -> np.ndarray:
    clipped = np.clip(value, -30.0, 30.0)
    return 1.0 / (1.0 + np.exp(-clipped))


@dataclass
class RiskModel:
    weights: np.ndarray
    bias: float
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def initialize(cls) -> "RiskModel":
        width = len(FEATURE_NAMES)
        return cls(np.zeros(width), 0.0, np.zeros(width), np.ones(width))

    def fit(
        self,
        features: np.ndarray,
        labels: np.ndarray,
        *,
        learning_rate: float = 0.04,
        epochs: int = 800,
        l2: float = 0.01,
    ) -> list[float]:
        self.mean = features.mean(axis=0)
        self.scale = features.std(axis=0)
        self.scale[self.scale < 1e-8] = 1.0
        normalized = (features - self.mean) / self.scale
        history: list[float] = []
        for _ in range(epochs):
            probabilities = _sigmoid(normalized @ self.weights + self.bias)
            error = probabilities - labels
            grad_weights = normalized.T @ error / len(labels) + l2 * self.weights
            grad_bias = float(error.mean())
            self.weights -= learning_rate * grad_weights
            self.bias -= learning_rate * grad_bias
            eps = 1e-8
            loss = -np.mean(labels * np.log(probabilities + eps) + (1 - labels) * np.log(1 - probabilities + eps))
            history.append(float(loss + 0.5 * l2 * np.sum(self.weights**2)))
        return history

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        matrix = np.atleast_2d(features).astype(np.float64)
        normalized = (matrix - self.mean) / self.scale
        return _sigmoid(normalized @ self.weights + self.bias)

    def save(self, path: Path) -> None:
        payload = {
            "algorithm_name": ALGORITHM_NAME,
            "algorithm_version": ALGORITHM_VERSION,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "feature_names": list(FEATURE_NAMES),
            "weights": self.weights.tolist(),
            "bias": self.bias,
            "mean": self.mean.tolist(),
            "scale": self.scale.tolist(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "RiskModel":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if tuple(payload["feature_names"]) != FEATURE_NAMES:
            raise ValueError("模型特征协议与运行时不兼容")
        return cls(
            weights=np.asarray(payload["weights"], dtype=np.float64),
            bias=float(payload["bias"]),
            mean=np.asarray(payload["mean"], dtype=np.float64),
            scale=np.asarray(payload["scale"], dtype=np.float64),
        )


def binary_metrics(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    labels = labels.astype(int)
    probabilities = probabilities.astype(float)
    predictions = (probabilities >= 0.5).astype(int)
    order = np.argsort(probabilities)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(probabilities) + 1)
    positive = labels == 1
    negative = ~positive
    if positive.any() and negative.any():
        auc = (ranks[positive].sum() - positive.sum() * (positive.sum() + 1) / 2) / (
            positive.sum() * negative.sum()
        )
    else:
        auc = math.nan
    return {
        "accuracy": float((predictions == labels).mean()),
        "auroc": float(auc),
        "brier_score": float(np.mean((probabilities - labels) ** 2)),
        "positive_rate": float(labels.mean()),
    }
