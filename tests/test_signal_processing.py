import tempfile
import unittest
from pathlib import Path

import numpy as np

from healthsynth.signal_processing import _dominant_rate, read_wfdb_annotations


class SignalProcessingTests(unittest.TestCase):
    def test_dominant_rate_on_clean_ppg_wave(self) -> None:
        sample_rate = 100.0
        time = np.arange(0, 20, 1 / sample_rate)
        waveform = np.sin(2 * np.pi * 1.2 * time) + 0.15 * np.sin(2 * np.pi * 2.4 * time)
        rate, confidence = _dominant_rate(waveform, sample_rate)
        self.assertIsNotNone(rate)
        self.assertAlmostEqual(float(rate), 72.0, delta=2.0)
        self.assertGreater(confidence, 0.5)

    def test_annotation_skip_uses_signed_offset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.atr"
            path.write_bytes(bytes([0, 59 << 2]) + (-1).to_bytes(4, "little", signed=True) + bytes([1, 1 << 2, 0, 0]))
            annotations = read_wfdb_annotations(path)
            self.assertEqual(annotations.tolist(), [0])


if __name__ == "__main__":
    unittest.main()
