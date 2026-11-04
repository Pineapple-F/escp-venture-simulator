#!/usr/bin/env python3
"""Build calendar-cutoff website targets in the fixed-query HotPP format.

Inputs and target definitions come from the simulator's anonymous snapshot.
The most recent fully observable calendar year is held out for validation.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / 'model-runtime/research/enterprise_path_clean/history_events.parquet'
DATA = ROOT / 'model-runtime/data/data'
EVENTS = ['融资', '企业／机构股东进入', '股权结构变更', '注册资本变更', '注销']
QUERY, TARGET_FIRST, NUM_CLASSES = 29, 30, 35


def parse(values):
    return pd.to_datetime(values.astype('string').str.replace(r'\.0$', '', regex=True).str.slice(0, 10), errors='coerce', format='mixed')


def build(output):
    output.mkdir(parents=True, exist_ok=False)
    history = pd.read_parquet(HISTORY)
    history['day'] = pd.to_datetime(history['day'], errors='coerce')
    history = history.loc[history.id.notna() & history.day.notna() & history.type.between(1, 28)].copy()
    history['id'] = history.id.astype(str)
    history = history.sort_values(['id', 'day', 'type', 'source', 'uid'], kind='stable')
    change = pd.read_parquet(DATA / 'change.parquet').drop_duplicates()
    change = change.assign(id=change.company_id_anon.astype(str), day=parse(change.change_date))
    company = pd.read_parquet(DATA / 'company.parquet').drop_duplicates()
    cancel = pd.DataFrame({'id': company.companyid_anon.astype(str), 'day': parse(company.cancel_date)})
    targets = [history.loc[history.type.eq(1), ['id', 'day']],
               history.loc[history.type.eq(4) & history.detail.astype(str).str.contains('企业|法人|合伙|投资', regex=True), ['id', 'day']],
               change.loc[change.change_type.eq('股东信息变更'), ['id', 'day']],
               change.loc[change.change_type.fillna('').str.contains('注册资本'), ['id', 'day']],
               cancel]
    target_tables = []
    for i, frame in enumerate(targets):
        f = frame.dropna(subset=['id', 'day']).drop_duplicates().copy()
        f['label'] = TARGET_FIRST + i
        target_tables.append(f)
    future = pd.concat(target_tables, ignore_index=True).sort_values(['id', 'day', 'label'])
    by_id = {key: group for key, group in future.groupby('id', sort=False)}
    cancellation = {key: group.day.min() for key, group in cancel.dropna().groupby('id', sort=False)}
    schema = pa.schema([('id', pa.string()), ('company', pa.string()), ('cutoff', pa.string()),
                        ('timestamps', pa.list_(pa.float32())), ('labels', pa.list_(pa.int64())),
                        ('is_query', pa.list_(pa.bool_())), ('observation_end', pa.float32())])
    rows = {'train': [], 'val': [], 'test': []}
    for cid, group in history.groupby('id', sort=False):
        days = group.day.to_numpy(dtype='datetime64[D]')
        labels = group.type.to_numpy(np.int64)
        f = by_id.get(cid)
        if f is None:
            f = pd.DataFrame(columns=['day', 'label'])
        for year in range(2014, 2024):
            cutoff = pd.Timestamp(year=year, month=12, day=31)
            if cancellation.get(cid, pd.Timestamp.max) <= cutoff:
                continue
            n = int(np.searchsorted(days, np.datetime64(cutoff.date()), side='right'))
            if n < 3:
                continue
            past = group.iloc[:n]
            months = past.day.dt.to_period('M')
            if months.nunique() < 3 or (months.iloc[-1].ordinal - months.iloc[0].ordinal) < 6:
                continue
            start = max(0, n - 64)
            origin = days[start]
            past_days = days[start:n]
            end = cutoff + pd.Timedelta(days=365)
            matches = f.loc[f.day.gt(cutoff) & f.day.le(end)].drop_duplicates('label', keep='first')
            future_days = matches.day.to_numpy(dtype='datetime64[D]')
            all_days = np.concatenate([past_days, [np.datetime64(cutoff.date())], future_days])
            times = ((all_days - origin).astype('timedelta64[D]').astype(np.float64) / 365.25).astype(np.float32)
            all_labels = labels[start:n].tolist() + [QUERY] + matches.label.astype(int).tolist()
            query = [False] * (n - start) + [True] + [False] * len(matches)
            split = 'test' if year == 2023 else ('val' if year == 2022 else 'train')
            rows[split].append({'id': f'{cid}__{year}', 'company': cid, 'cutoff': cutoff.date().isoformat(),
                                'timestamps': times.tolist(), 'labels': all_labels, 'is_query': query,
                                # Daily records through day 365 cover the same discrete dates
                                # as the model's one-year window (365.25 days). A small
                                # float margin prevents roundoff from discarding the window.
                                'observation_end': float(times[n - start]) + 1.00001})
    summary = {'events': EVENTS, 'history_types': '1..28', 'query_label': QUERY,
               'target_labels': list(range(TARGET_FIRST, NUM_CLASSES)), 'horizon_days': 365,
               'split': 'train 2014-2021, validation 2022, test 2023; same companies may appear in different years',
               'max_history': 64, 'files': {}}
    for split, values in rows.items():
        path = output / (split + '.parquet')
        pq.write_table(pa.Table.from_pylist(values, schema=schema), path, compression='zstd')
        counts = [sum(x >= TARGET_FIRST for x in row['labels']) for row in values]
        summary['files'][split] = {'windows': len(values), 'companies': len({r['company'] for r in values}),
                                   'empty_fraction': float(np.mean(np.asarray(counts) == 0)),
                                   'positive_counts': [sum(TARGET_FIRST+i in r['labels'] for r in values) for i in range(5)],
                                   'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    build(parser.parse_args().output)
