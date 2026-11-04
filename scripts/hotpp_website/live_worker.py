"""Compatibility bridge to the exported HotPP model, not yet activated."""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts'))
sys.path.insert(0, str(REPO / 'model-runtime/hotpp_website'))
import live_model_worker as previous
from inference import Predictor
import numpy as np
import torch


class HotPPWorker(previous.Worker):
    def __init__(self):
        torch.set_num_threads(int(os.environ.get('MODEL_CPU_THREADS', '2')))
        root = Path(os.environ.get('HOTPP_WEBSITE_MODEL_DIR', REPO / 'model-runtime/hotpp_website'))
        calibration = json.loads((root / 'calibration.json').read_text())
        self.predictor = Predictor(root / 'model.pt', calibration['thresholds'], calibration.get('time_calibration'))
        self.thresholds = self.predictor.thresholds
        self.histories = previous.Histories()
        self.history_cutoff = None
        self.live_history_added = 0
        self.device = torch.device('cpu')
        self.lookup = type('LookupCounters', (), {'last_cached': 0, 'last_encoded': 0})()
        self.collator = lambda samples: samples

    def predict(self, samples, **kwargs):
        results = [self.predictor.predict(sample) for sample in samples]
        self._input_nodes = [r[2] for r in results]
        return np.stack([r[0] for r in results]), np.stack([r[1] for r in results])

    def sample(self, company, as_of):
        sample, trace = super().sample(company, as_of)
        if sample is not None and not np.any((sample['typ'] >= 1) & (sample['typ'] <= 25)):
            return None, None
        return sample, trace

    @staticmethod
    def metadata(result, input_nodes):
        result.pop('model', None)
        if result.get('mode') == 'live_full_history_inference':
            result['mode'] = 'live_recent_history_inference'
        result['all_history'] = False
        result['history_scope'] = 'recent_supported_events_up_to_64'
        result['model_input_nodes'] = input_nodes
        return result

    def run(self, *args, **kwargs):
        result = super().run(*args, **kwargs)
        return self.metadata(result, self._input_nodes[0]) if result.get('available') else result

    def run_many(self, *args, **kwargs):
        results = super().run_many(*args, **kwargs)
        counts = iter(self._input_nodes) if any(r.get('available') for r in results) else iter(())
        return [self.metadata(r, next(counts)) if r.get('available') else r for r in results]

    def run_custom(self, *args, **kwargs):
        result = super().run_custom(*args, **kwargs)
        return self.metadata(result, self._input_nodes[0]) if result.get('available') else result

    def run_scenario(self, *args, **kwargs):
        result = super().run_scenario(*args, **kwargs)
        return self.metadata(result, self._input_nodes[0]) if result.get('available') else result


if __name__ == '__main__':
    previous.Worker = HotPPWorker
    previous.main()
