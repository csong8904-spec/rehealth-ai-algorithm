import unittest

import numpy as np

from healthsynth.fusion_model import CandidateGroup, CandidateRanker, decode_candidate_sequence


class FusionModelTests(unittest.TestCase):
    def test_ranker_prefers_learned_candidate(self) -> None:
        groups = []
        for index in range(20):
            features = np.asarray([[0.4, 0.9], [0.7, 0.1]], dtype=float)
            groups.append(
                CandidateGroup(
                    record=f"s{index}_walk",
                    subject=f"s{index}",
                    target_bpm=72.0,
                    candidate_rates=np.asarray([72.0, 126.0]),
                    features=features,
                )
            )
        ranker = CandidateRanker.fit(groups, epochs=300)
        self.assertEqual(ranker.predict_group(groups[0]), 72.0)

    def test_temporal_decoder_suppresses_isolated_harmonic_jump(self) -> None:
        class FixedRanker:
            def score(self, features: np.ndarray) -> np.ndarray:
                return features[:, 0]

        groups = [
            CandidateGroup("s1_walk", "s1", 75.0, np.asarray([75.0, 150.0]), scores)
            for scores in (
                np.asarray([[0.80], [0.20]]),
                np.asarray([[0.45], [0.75]]),
                np.asarray([[0.82], [0.18]]),
            )
        ]
        decoded, _ = decode_candidate_sequence(groups, FixedRanker())
        np.testing.assert_allclose(decoded, np.asarray([75.0, 75.0, 75.0]))

    def test_group_softmax_ranks_the_window_candidates(self) -> None:
        groups = []
        for index in range(24):
            groups.append(
                CandidateGroup(
                    record=f"s{index}_walk",
                    subject=f"s{index}",
                    target_bpm=72.0,
                    candidate_rates=np.asarray([72.0, 144.0, 108.0]),
                    features=np.asarray([[1.0, 0.1], [0.1, 1.0], [0.2, 0.4]]),
                )
            )
        ranker = CandidateRanker.fit_group_softmax(groups, epochs=300)
        self.assertEqual(ranker.predict_group(groups[0]), 72.0)


if __name__ == "__main__":
    unittest.main()
