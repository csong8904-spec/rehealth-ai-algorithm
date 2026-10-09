import unittest

import numpy as np

from healthsynth.motion_denoising import remove_motion_artifacts


class MotionDenoisingTests(unittest.TestCase):
    def test_reduces_acceleration_correlated_noise(self) -> None:
        sample_rate = 128
        time = np.arange(sample_rate * 16) / sample_rate
        pulse = np.sin(2 * np.pi * 1.2 * time)
        motion = np.sin(2 * np.pi * 2.0 * time)
        accelerometer = np.column_stack((motion, 0.5 * motion, -motion))
        contaminated = pulse + 2.5 * motion
        cleaned = remove_motion_artifacts(contaminated, accelerometer)
        before = abs(float(np.corrcoef(contaminated, motion)[0, 1]))
        after = abs(float(np.corrcoef(cleaned, motion)[0, 1]))
        self.assertLess(after, before * 0.2)
        self.assertGreater(abs(float(np.corrcoef(cleaned, pulse)[0, 1])), 0.8)

    def test_rejects_mismatched_time_axes(self) -> None:
        with self.assertRaises(ValueError):
            remove_motion_artifacts(np.ones(64), np.ones((32, 3)))


if __name__ == "__main__":
    unittest.main()
