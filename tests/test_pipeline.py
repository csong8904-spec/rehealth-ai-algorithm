import unittest

from healthsynth import HealthSynthesisPipeline, SensorSummary


class PipelineTests(unittest.TestCase):
    def test_low_coverage_disables_risk_conclusion(self) -> None:
        result = HealthSynthesisPipeline().run(
            SensorSummary(
                user_key="anonymous-test-user",
                period_start="2026-10-01",
                period_end="2026-10-07",
                valid_coverage=0.4,
                metrics={"resting_heart_rate": 80.0},
                baseline={"resting_heart_rate": 65.0},
            )
        )
        self.assertEqual(result.risk_level, "无法评估")
        self.assertIsNone(result.anomaly_score)
        self.assertTrue(result.safety_actions)

    def test_report_is_grounded_in_supplied_metrics(self) -> None:
        result = HealthSynthesisPipeline().run(
            SensorSummary(
                user_key="anonymous-test-user",
                period_start="2026-10-01",
                period_end="2026-10-07",
                valid_coverage=0.95,
                metrics={"resting_heart_rate": 72.0},
                baseline={"resting_heart_rate": 65.0},
            )
        )
        self.assertEqual(result.risk_level, "中")
        self.assertTrue(any("72.0" in item for item in result.evidence))
        self.assertTrue(result.synthesis_label)


if __name__ == "__main__":
    unittest.main()

