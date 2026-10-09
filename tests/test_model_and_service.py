import tempfile
import unittest
from pathlib import Path

import numpy as np

from healthsynth import ReHealthService, SensorSummary
from healthsynth.features import extract_features
from healthsynth.model import RiskModel
from healthsynth.synthesis import TextGenerator


class UnsafeGenerator(TextGenerator):
    def generate(self, facts: dict[str, object]) -> str:
        return "你已经确诊，应立即服用某药。"


class ModelAndServiceTests(unittest.TestCase):
    def test_feature_extraction_tracks_missingness(self) -> None:
        result = extract_features(
            0.9,
            {"resting_heart_rate": 70.0, "daily_steps": 5000.0},
            {"resting_heart_rate": 65.0, "daily_steps": 6000.0},
        )
        self.assertEqual(result.values.shape, (8,))
        self.assertEqual(result.values[6], 1.0)
        self.assertEqual(result.values[7], 1.0)

    def test_model_round_trip(self) -> None:
        model = RiskModel.initialize()
        model.weights = np.arange(8, dtype=float) / 10
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.json"
            model.save(path)
            loaded = RiskModel.load(path)
        np.testing.assert_allclose(loaded.weights, model.weights)

    def test_unsafe_generation_is_replaced(self) -> None:
        model = RiskModel.initialize()
        service = ReHealthService(model, UnsafeGenerator())
        result = service.generate_report(
            SensorSummary(
                user_key="test",
                period_start="2026-10-01",
                period_end="2026-10-07",
                valid_coverage=0.95,
                metrics={"resting_heart_rate": 70.0, "daily_steps": 6000.0},
                baseline={"resting_heart_rate": 65.0, "daily_steps": 7000.0},
            )
        )
        self.assertNotIn("已经确诊", result.report_text)
        self.assertTrue(result.safety_actions)


if __name__ == "__main__":
    unittest.main()
