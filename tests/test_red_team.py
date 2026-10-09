import unittest

from healthsynth.red_team import run_safety_evaluation
from healthsynth.safety import validate_generated_text


class RedTeamTests(unittest.TestCase):
    def test_complete_red_team_suite_passes(self) -> None:
        result = run_safety_evaluation()
        self.assertTrue(result["gate_pass"])
        self.assertEqual(result["cases"], 10)

    def test_non_diagnostic_disclaimer_is_not_false_positive(self) -> None:
        safe, _ = validate_generated_text("仅供参考，不构成诊断。")
        self.assertTrue(safe)


if __name__ == "__main__":
    unittest.main()
