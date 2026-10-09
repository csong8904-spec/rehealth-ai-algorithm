import tempfile
import unittest
from pathlib import Path

from healthsynth.release_gate import ReleaseThresholds, evaluate_benchmark_file, evaluate_release


class ReleaseGateTests(unittest.TestCase):
    def test_blocks_current_quality_and_sample_size(self) -> None:
        benchmark = {
            "metrics": {
                "subjects": 8,
                "records": 18,
                "mean_absolute_error_bpm": 24.0,
                "p90_absolute_error_bpm": 69.0,
                "within_10_bpm_fraction": 0.61,
            }
        }
        decision = evaluate_release(benchmark)
        self.assertEqual(decision["decision"], "blocked")
        self.assertIn("subjects", decision["failed_checks"])

    def test_approves_metrics_that_meet_every_threshold(self) -> None:
        benchmark = {
            "metrics": {
                "subjects": 25,
                "records": 120,
                "mean_absolute_error_bpm": 5.0,
                "p90_absolute_error_bpm": 10.0,
                "within_10_bpm_fraction": 0.95,
            }
        }
        self.assertEqual(evaluate_release(benchmark)["decision"], "approved")

    def test_blocked_release_never_writes_activation_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            benchmark = root / "benchmark.json"
            benchmark.write_text(
                '{"metrics":{"subjects":1,"records":1,'
                '"mean_absolute_error_bpm":20,"p90_absolute_error_bpm":30,'
                '"within_10_bpm_fraction":0.1}}',
                encoding="utf-8",
            )
            activation = root / "activation.json"
            with self.assertRaises(RuntimeError):
                evaluate_benchmark_file(
                    benchmark,
                    root / "decision.json",
                    activation_path=activation,
                )
            self.assertFalse(activation.exists())
            self.assertTrue((root / "decision.json").exists())


if __name__ == "__main__":
    unittest.main()
