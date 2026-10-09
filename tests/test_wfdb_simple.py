import tempfile
import unittest
from pathlib import Path

import numpy as np

from healthsynth.wfdb_simple import read_digital_signal, summarize_record


class WfdbSimpleTests(unittest.TestCase):
    def test_reads_interleaved_format_16(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            header = root / "sample.hea"
            header.write_text(
                "sample 2 10 3\n"
                "sample.dat 16 100(0)/mV 0 0 0 0 0 ecg\n"
                "sample.dat 16 20(-10)/a.u. 0 0 0 0 0 ppg\n"
                "#test activity\n",
                encoding="ascii",
            )
            np.asarray([[1, 2], [3, 4], [5, 6]], dtype="<i2").tofile(root / "sample.dat")
            parsed, values = read_digital_signal(header)
            self.assertEqual(parsed.samples, 3)
            self.assertEqual(parsed.channels[1].name, "ppg")
            self.assertEqual(values.tolist(), [[1, 2], [3, 4], [5, 6]])
            summary = summarize_record(header)
            self.assertEqual(summary["duration_seconds"], 0.3)


if __name__ == "__main__":
    unittest.main()
