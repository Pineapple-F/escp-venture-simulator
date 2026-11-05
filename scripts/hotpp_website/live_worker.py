"""Compatibility bridge to the exported HotPP model."""
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
        results = [self.predictor.predict(sample, sample['as_of']) for sample in samples]
        self._input_nodes = [r[2] for r in results]
        self._predicted_months = [r[1] for r in results]
        return np.stack([r[0] for r in results]), np.stack([r[1] for r in results])

    def sample(self, company, as_of):
        sample, trace = super().sample(company, as_of)
        if sample is not None and not np.any((sample['typ'] >= 1) & (sample['typ'] <= 25)):
            return None, None
        if sample is not None:
            sample['as_of'] = as_of
        return sample, trace

    def sample_custom(self, events, as_of):
        sample, trace = super().sample_custom(events, as_of)
        if sample is not None:
            sample['as_of'] = as_of
        return sample, trace

    def sample_scenario(self, company, events, as_of, reference_cutoff):
        sample, trace = super().sample_scenario(company, events, as_of, reference_cutoff)
        if sample is not None:
            sample['as_of'] = as_of
            trace['history_start'] = min(trace['history_start'], *(event['date'] for event in events))
        return sample, trace

    @staticmethod
    def metadata(result, input_nodes, predicted_months):
        result.pop('model', None)
        if result.get('mode') == 'live_full_history_inference':
            result['mode'] = 'live_recent_history_inference'
        result['all_history'] = False
        result['history_scope'] = 'recent_supported_events_up_to_64'
        result['model_input_nodes'] = input_nodes
        cutoff = previous.date.fromisoformat(result['as_of'])
        for event, month in zip(result['events'], predicted_months):
            if event['predicted']:
                event['month_index'] = int(month)
                year, calendar_month = previous.add_month(cutoff.year, cutoff.month, int(month))
                event['estimated_month'] = f'{year:04d}-{calendar_month:02d}'
        return result

    def run(self, *args, **kwargs):
        result = super().run(*args, **kwargs)
        return self.metadata(result, self._input_nodes[0], self._predicted_months[0]) if result.get('available') else result

    def run_many(self, *args, **kwargs):
        results = super().run_many(*args, **kwargs)
        predictions = iter(zip(self._input_nodes, self._predicted_months)) if any(r.get('available') for r in results) else iter(())
        return [self.metadata(r, *next(predictions)) if r.get('available') else r for r in results]

    def run_custom(self, *args, **kwargs):
        result = super().run_custom(*args, **kwargs)
        return self.metadata(result, self._input_nodes[0], self._predicted_months[0]) if result.get('available') else result

    def run_scenario(self, *args, **kwargs):
        result = super().run_scenario(*args, **kwargs)
        return self.metadata(result, self._input_nodes[0], self._predicted_months[0]) if result.get('available') else result


if __name__ == '__main__':
    previous.Worker = HotPPWorker
    previous.main()
