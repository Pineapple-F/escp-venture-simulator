"""Website-specific input, time and output contract for HotPP inference."""
import importlib.util
import unittest
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('website_hotpp_inference', ROOT / 'model-runtime/hotpp_website/inference.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MockGraph:
    def __call__(self, timestamps, labels, lengths):
        self.timestamps, self.labels, self.lengths = timestamps, labels, lengths
        # One candidate with known labels and time, as returned by the export.
        logits = torch.zeros((1, 1, 35))
        return timestamps.gather(1, (lengths - 1)[:, None]) + 0.25, logits, torch.ones((1, 1))


class PredictorTest(unittest.TestCase):
    def setUp(self):
        self.predictor = object.__new__(module.Predictor)
        self.predictor.model = MockGraph()
        self.predictor.thresholds = np.full(5, 0.01)
        self.predictor.clock = [{'scale': 1.0, 'offset': 0.0} for _ in range(5)]

    def test_keeps_recent_supported_history_and_query(self):
        types = np.r_[np.full(70, 1), 26]
        age_days = np.r_[np.arange(70, 0, -1), 0]
        cont = np.zeros((71, 18), np.float32)
        cont[:, 0] = np.log1p(age_days / 30.4375) / 8
        scores, months, count = self.predictor.predict({'typ': types, 'cont': cont})
        self.assertEqual(count, 64)
        self.assertEqual(self.predictor.model.lengths.tolist(), [65])
        self.assertEqual(self.predictor.model.labels[0, 64].item(), module.QUERY_LABEL)
        np.testing.assert_allclose(scores, np.full(5, 1/35), rtol=1e-6)
        np.testing.assert_array_equal(months, np.full(5, 3))

    def test_applies_per_event_time_calibration(self):
        self.predictor.clock[0] = {'scale': 0., 'offset': .5}
        cont = np.zeros((1, 18), np.float32)
        _, months, _ = self.predictor.predict({'typ': np.array([8]), 'cont': cont})
        self.assertEqual(months.tolist(), [6, 3, 3, 3, 3])

    def test_rejects_history_without_supported_events(self):
        with self.assertRaisesRegex(ValueError, 'no supported'):
            self.predictor.predict({'typ': np.array([26]), 'cont': np.zeros((1, 18), np.float32)})


if __name__ == '__main__':
    unittest.main()
