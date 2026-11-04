"""Website adapter for a validated, exported HotPP candidate-set predictor."""
import numpy as np
import torch

QUERY_LABEL = 29
TARGET_FIRST = 30
MAX_HISTORY = 64


class Predictor:
    def __init__(self, path, thresholds, time_calibration=None):
        self.model = torch.jit.load(str(path), map_location='cpu').eval()
        self.thresholds = np.asarray(thresholds, dtype=np.float32)
        if self.thresholds.shape != (5,) or not np.isfinite(self.thresholds).all():
            raise ValueError('invalid event thresholds')
        self.clock = time_calibration or [{'scale': 1.0, 'offset': 0.0} for _ in range(5)]
        if len(self.clock) != 5 or not all(np.isfinite(v['scale']) and np.isfinite(v['offset']) for v in self.clock):
            raise ValueError('invalid time calibration')

    def predict(self, sample):
        # The model was trained on event types present in history_events.parquet;
        # separately added financial statements were not part of that training.
        types = np.asarray(sample['typ'], dtype=np.int64)
        cont = np.asarray(sample['cont'], dtype=np.float32)
        keep = (types >= 1) & (types <= 25)
        types = types[keep][-MAX_HISTORY:]
        cont = cont[keep][-MAX_HISTORY:]
        if not len(types):
            raise ValueError('no supported past events')
        age_days = np.rint(np.expm1(cont[:, 0].astype(np.float64) * 8) * 30.4375).astype(np.int64)
        first_age = int(age_days[0])
        elapsed = (first_age - age_days) / 365.25
        query_time = first_age / 365.25
        n = len(types) + 1
        timestamps = torch.zeros((1, MAX_HISTORY + 1), dtype=torch.float32)
        labels = torch.zeros((1, MAX_HISTORY + 1), dtype=torch.long)
        timestamps[0, :n] = torch.from_numpy(np.r_[elapsed, query_time].astype(np.float32))
        labels[0, :n] = torch.from_numpy(np.r_[types, QUERY_LABEL])
        with torch.inference_mode():
            predicted_time, logits, presence = self.model(timestamps, labels, torch.tensor([n]))
            weighted = logits.softmax(-1)[0, :, TARGET_FIRST:TARGET_FIRST + 5] * presence[0, :, None]
            scores, index = weighted.max(dim=0)
            offsets = predicted_time[0].gather(0, index) - query_time
        scores = scores.numpy()
        # Website months are discrete calendar months following the cutoff.
        days = np.array([np.clip(value * spec['scale'] + spec['offset'], 1/365.25, 1)
                         for value, spec in zip(offsets.numpy(), self.clock)])
        months = np.clip(np.ceil(days * 12), 1, 12).astype(np.int64)
        return scores, months, n - 1
