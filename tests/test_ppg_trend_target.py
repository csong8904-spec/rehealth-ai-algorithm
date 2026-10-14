import unittest
from datetime import date, timedelta

from healthsynth.ppg_trend_target import DailyPPGSummary, build_next_day_examples


class PPGTrendTargetTests(unittest.TestCase):
    def _record(self, offset: int, heart_rate: float, *, subject: str = "s1", quality: float = 0.9):
        return DailyPPGSummary(subject, date(2026, 1, 1) + timedelta(days=offset), heart_rate, 0.9, quality)

    def test_next_day_label_uses_prior_baseline_only(self):
        records = [self._record(day, 60) for day in range(7)]
        records.extend([self._record(7, 62), self._record(8, 75)])
        examples = build_next_day_examples(records)
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0].baseline_bpm, 60)
        self.assertEqual(examples[0].current_deviation_bpm, 2)
        self.assertEqual(examples[0].target_deviation_bpm, 15)
        self.assertEqual(examples[0].label, 1)

    def test_missing_next_day_does_not_make_label(self):
        records = [self._record(day, 60) for day in range(7)] + [self._record(7, 65), self._record(9, 90)]
        self.assertEqual(build_next_day_examples(records), ())

    def test_low_quality_target_is_excluded(self):
        records = [self._record(day, 60) for day in range(7)]
        records.extend([self._record(7, 62), self._record(8, 75, quality=0.2)])
        self.assertEqual(build_next_day_examples(records), ())

    def test_duplicate_subject_day_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_next_day_examples([self._record(0, 60), self._record(0, 61)])


if __name__ == "__main__":
    unittest.main()
