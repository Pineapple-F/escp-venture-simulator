"""Full dated histories, dynamic collation, and explicit record attributes."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / 'research/enterprise_path_clean'
ATTR_BUCKETS = 32768


def bucket(text):
    return 1 + int.from_bytes(hashlib.blake2b(text.encode(), digest_size=8).digest(), 'little') % (ATTR_BUCKETS - 1)


def attribute_tokens(values):
    """Field-keyed categorical/numeric encoding; no learned vocabulary from future."""
    ids, weights = [], []
    for key, value in sorted(values.items()):
        if value is None or (isinstance(value, float) and not np.isfinite(value)):
            ids.append(bucket(key + '=MISSING')); weights.append(1.)
        elif isinstance(value, (int, float)):
            ids.extend([bucket(key + '=PRESENT'), bucket(key + '=NUMBER')])
            weights.extend([1., float(np.sign(value) * np.log1p(abs(value)))])
        else:
            # Exact field/value identity: simple categorical coding, not semantic text encoding.
            ids.append(bucket(key + '=' + str(value))); weights.append(1.)
    return np.asarray(ids, np.int64), np.asarray(weights, np.float32)


def parse_dates(series):
    s = series.astype('string').str.replace(r'\.0$', '', regex=True).str.slice(0, 10)
    compact = s.str.fullmatch(r'\d{8}', na=False)
    out = pd.to_datetime(s.where(~compact), errors='coerce', format='mixed')
    out.loc[compact] = pd.to_datetime(s[compact], format='%Y%m%d', errors='coerce')
    return out.where(out.dt.year.ge(1900) & out.dt.year.ne(1970))


class Histories:
    def __init__(self):
        self.records = pd.read_parquet(CLEAN / 'history_events.parquet')
        self.raw = {}
        # Use dates as already conservatively cleaned; some are availability proxies.
        self.records['attributes'] = [self.attributes(row) for row in self.records.itertuples()]
        extra = []
        for source, name in enumerate(('company_balance_sheet', 'company_income_statement', 'company_cashflow_statement'), 14):
            frame = self.table(name)
            publish, end = parse_dates(frame.publish_date), parse_dates(frame.end_date)
            valid = publish.notna() & end.notna() & end.le(publish)
            valid &= frame.company_id_anon.astype('string').str.fullmatch(r'co_[A-Za-z0-9_]+', na=False)
            for index in frame.index[valid]:
                row = frame.loc[index]
                attrs = {f'{name}.{key}': self.scalar(value) for key, value in row.items()
                         if 'pseudo' not in key and key != 'company_id_anon'}
                extra.append(dict(id=str(row.company_id_anon), day=publish[index], type=26+source-14,
                                  source=source, stage=-1., role=0., sources=str(source),
                                  uid=f'{name}:{index}', attributes=attrs))
        if extra:
            self.records = pd.concat([self.records, pd.DataFrame(extra)], ignore_index=True)
        self.records = self.records.sort_values(['id', 'day', 'type', 'source', 'uid']).reset_index(drop=True)
        self.groups = {cid: ix for cid, ix in self.records.groupby('id', sort=False).indices.items()}
        self.raw.clear()

    @staticmethod
    def scalar(value):
        if value is None or value is pd.NA:
            return None
        if isinstance(value, (np.integer, np.floating)):
            value = value.item()
        if isinstance(value, float) and not np.isfinite(value):
            return None
        return value if isinstance(value, (str, int, float, bool)) else str(value)

    def table(self, name):
        if name not in self.raw:
            self.raw[name] = pd.read_parquet(ROOT / 'data/data' / (name + '.parquet')).drop_duplicates().reset_index(drop=True)
        return self.raw[name]

    def attributes(self, row):
        identity = str(row.identity)
        attrs = {'identity': None if identity.startswith(('unknown:', 'change-field:')) or identity in ('state-event', 'nan', '<NA>') else identity,
                 'detail': self.scalar(row.detail)}
        name = row.uid.split(':')[0]
        fields = {
            'events_sample_cn': ['amount_usd', 'stage', 'role_or_dealtype', 'counterparty_id'],
            'investment_merged': ['round_raw', 'amount_str', 'amount_num', 'currency', 'estimated_amount', 'valuation', 'proportion', 'investor_key_anon', 'event_date', 'pub_date'],
            'rongzi': ['money', 'round', 'value', 'investor_key_anon', 'date', 'real_time'],
            'change': ['change_type', 'change_field'],
            'employee': ['position'], 'stock_executive': ['position'],
            'legal_person': ['legal_person_caption'], 'partner': ['stock_type'],
        }.get(name, [])
        if name == 'annual_report_base':
            fields = [c for c in self.table(name) if 'pseudo' not in c and c != 'company_id_anon'
                      and (pd.api.types.is_numeric_dtype(self.table(name)[c]) or c in ('report_date', 'report_year'))]
        if fields:
            original = self.table(name).iloc[int(row.uid.rsplit(':', 1)[1])]
            for key in fields:
                if key in original:
                    attrs[name + '.' + key] = self.scalar(original[key])
        return attrs

    def before(self, company, year):
        frame = self.records.iloc[self.groups.get(str(company), [])]
        cutoff = pd.Timestamp(year=int(year), month=12, day=31)
        return frame.loc[frame.day.le(cutoff)].copy()


class Dataset:
    def __init__(self, histories, split='train', targets=False):
        if split not in ('train', 'calibration', 'validation'):
            raise ValueError('Only train/calibration/validation are supported.')
        self.histories, self.targets = histories, targets
        fields = ['company', 'year', 'allowed']
        if targets:
            fields += ['future_type', 'future_time', 'future_count', 'initial', 'eligible']
        with np.load(CLEAN / 'cache' / (split + '.npz'), allow_pickle=False) as z:
            self.meta = {key: z[key] for key in fields}

    def __len__(self):
        return len(self.meta['company'])

    def __getitem__(self, index):
        company, year = self.meta['company'][index], int(self.meta['year'][index])
        frame = self.histories.before(company, year)
        cutoff = pd.Timestamp(year=year, month=12, day=31)
        days = frame.day.to_numpy(dtype='datetime64[D]')
        age = (np.datetime64(cutoff.date()) - days).astype(float) / 30.4375
        gap = np.r_[0., np.diff(days).astype(float)] / 30.4375 if len(days) else np.array([])
        cont = np.zeros((len(frame), 18), np.float32)
        cont[:, :4] = np.column_stack([np.log1p(age)/8, np.log1p(gap)/8,
                                      (frame.stage.to_numpy()+1)/12, frame.role.to_numpy()])
        cont[:, 4] = np.log(2.)  # One canonical record per node, no month grouping.
        for j, sources in enumerate(frame.sources):
            for source in str(sources).split('|'):
                if 1 <= int(source) <= 13:
                    cont[j, 4+int(source)] = 1.
        sample = dict(company=str(company), year=year, typ=frame.type.to_numpy(np.int64),
                      src=frame.source.to_numpy(np.int64), cont=cont,
                      attributes=[attribute_tokens(a) for a in frame.attributes],
                      allowed=self.meta['allowed'][index].astype(bool))
        if self.targets:
            sample['targets'] = {dest: self.meta[src][index] for dest, src in
                [('true_type','future_type'), ('true_time','future_time'), ('count','future_count'),
                 ('initial','initial'), ('eligible','eligible')]}
        return sample


def collate(samples):
    """Batch maximum length, no truncation. Attribute lists have no token cap."""
    batch, length = len(samples), max(1, max(len(s['typ']) for s in samples))
    history = dict(typ=torch.zeros((batch, length), dtype=torch.long),
                   src=torch.zeros((batch, length), dtype=torch.long),
                   cont=torch.zeros((batch, length, 18), dtype=torch.float32),
                   allowed=torch.as_tensor(np.stack([s['allowed'] for s in samples])))
    ids, weights, offsets = [], [], []
    for i, sample in enumerate(samples):
        n = len(sample['typ'])
        for key in ('typ', 'src', 'cont'):
            if n:
                history[key][i, -n:] = torch.as_tensor(np.array(sample[key], copy=True))
        for j in range(length):
            offsets.append(len(ids))
            if j >= length-n:
                a, w = sample['attributes'][j-(length-n)]
                ids.extend(a); weights.extend(w)
    history.update(attr_ids=torch.tensor(ids, dtype=torch.long),
                   attr_weights=torch.tensor(weights, dtype=torch.float32),
                   attr_offsets=torch.tensor(offsets, dtype=torch.long))
    if 'targets' not in samples[0]:
        return history
    return history, {key: torch.as_tensor(np.stack([s['targets'][key] for s in samples]))
                     for key in samples[0]['targets']}


if __name__ == '__main__':
    histories = Histories()
    report = {'representation': 'full canonical daily records plus dated financial reports',
              'history_rows': len(histories.records), 'splits': {},
              'attributes': 'field-keyed hash embeddings; exact categorical values, signed-log numeric values',
              'limitations': ['Missing original occurrence dates remain availability-date proxies.',
                              'Hash collisions possible; text is categorical, not semantically encoded.',
                              'Cross-source merged records retain primary-row content and union of sources.',
                              'Undated snapshots are excluded; no claim of complete real-world history.']}
    for split in ('train', 'calibration', 'validation'):
        data = Dataset(histories, split)
        # Count via sorted full day arrays, without constructing every tensor.
        counts = []
        for cid, year in zip(data.meta['company'], data.meta['year']):
            frame = histories.records.iloc[histories.groups.get(str(cid), [])]
            counts.append(int(frame.day.searchsorted(pd.Timestamp(year=int(year), month=12, day=31), side='right')))
        report['splits'][split] = dict(samples=len(data), total_nodes=sum(counts),
                                      max_nodes=max(counts), over_64=sum(n>64 for n in counts),
                                      empty=sum(n==0 for n in counts))
    path = Path(__file__).with_name('FULL_HISTORY_AUDIT.json')
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
