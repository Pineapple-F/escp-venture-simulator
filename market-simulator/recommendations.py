"""CPU-only serving of frozen SGL embeddings; no fitting or graph propagation online."""
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

import numpy as np


class RecommendationUnavailable(RuntimeError):
    pass


def investment_subjects(source, cutoff):
    """Read real investor identities and disclosed history, including filtered-out users.

    Keep the full history for exclusion, even when an investee is outside the UI
    cohort. Count distinct counterparties, not duplicated financing event rows.
    """
    import duckdb
    with duckdb.connect() as db:
        rows = db.execute("""
            SELECT investor_key_anon, investor_name_pseudo, invested_company_id_anon,
                   event_id_anon, invested_company_name_pseudo,
                   cast(event_date AS DATE), cast(greatest(event_date, pub_date) AS DATE),
                   round_std, industry_type, city, pub_date IS NULL
            FROM read_parquet(?)
            WHERE investor_key_anon IS NOT NULL
              AND investor_name_pseudo IS NOT NULL AND trim(investor_name_pseudo) <> ''
              AND invested_company_id_anon IS NOT NULL
              AND event_date >= '1990-01-01' AND event_date < ?::DATE + INTERVAL 1 DAY
              AND (pub_date IS NULL OR pub_date < ?::DATE + INTERVAL 1 DAY)
              AND NOT coalesce(event_date_is_suspect, false)
              AND NOT coalesce(pub_date_is_suspect, false)
              AND NOT coalesce(has_source_conflict, false)
            ORDER BY investor_key_anon, investor_name_pseudo
        """, [str(Path(source) / 'investment_events.parquet'), cutoff, cutoff]).fetchall()
    investors = {}
    for iid, name, cid, eid, company_name, day, available, stage, industry, region, publication_proxy in rows:
        item = investors.setdefault(iid, {'id': iid, 'name': name, 'companies': set(), 'events': {}})
        item['companies'].add(cid)
        if eid:
            item['events'].setdefault((eid, cid), dict(
                id=eid, company=cid, name=company_name or cid, date=day.isoformat(),
                available=(available or day).isoformat(), stage=stage or '未披露',
                industry=industry or '未披露', region=region or '未披露',
                publication_proxy=bool(publication_proxy)))
    return investors


class InvestorRecommender:
    TOP_K = 10
    PAGE_SIZE = 30

    def __init__(self, assets, universe, subjects):
        self.assets = Path(assets)
        self.history_cutoff = universe['start']
        self.companies = {c['id']: dict(c) for c in universe['companies'] if not c.get('closed')}
        for row in sorted(universe.get('rounds', []), key=lambda r: (r['available'], r['id'])):
            if row['company'] in self.companies and row['available'] <= self.history_cutoff:
                self.companies[row['company']].update(
                    name=row.get('name'), industry=row.get('industry'),
                    region=row.get('region'), stage=row.get('stage'))
        self.subjects = subjects
        self.history = {iid: frozenset(row['companies']) for iid, row in subjects.items()}
        popularity = defaultdict(int)
        for history in self.history.values():
            for cid in history:
                if cid in self.companies:
                    popularity[cid] += 1
        self.popularity = dict(popularity)
        self.popular_ids = sorted(popularity, key=lambda cid: (-popularity[cid], cid))
        self.model_error = None
        self.user_index = {}
        self.manifest = {}
        try:
            self._load()
        except (OSError, ValueError, KeyError, TypeError) as error:
            # A broken artifact is an operational error, never an unknown investor.
            self.model_error = str(error)
        self.investor_rows = sorted((
            dict(id=iid, name=row['name'], trained=iid in self.user_index,
                 company_count=len(self.history[iid]))
            for iid, row in self.subjects.items()), key=lambda row: (row['name'], row['id']))

    def _load(self):
        self.manifest = json.loads((self.assets / 'manifest.json').read_text(encoding='utf-8'))
        m = self.manifest
        if m['schema_version'] != 1 or m['model'] != 'SGL':
            raise ValueError('Unsupported recommendation artifact')
        payload = self.assets / 'embeddings.npz'
        if sha256(payload.read_bytes()).hexdigest() != m['embeddings_sha256']:
            raise ValueError('Recommendation artifact checksum mismatch')
        with np.load(payload, allow_pickle=False) as arrays:
            users = np.array(arrays['user_embeddings'], dtype=np.float32, order='C')
            items = np.array(arrays['item_embeddings'], dtype=np.float32, order='C')
            self.seen_indptr = np.array(arrays['seen_indptr'], dtype=np.int64)
            self.seen_indices = np.array(arrays['seen_indices'], dtype=np.int64)
        self.user_ids = list(m['user_ids'])
        self.item_ids = list(m['item_ids'])
        if (users.ndim != 2 or items.ndim != 2 or users.shape[1] != items.shape[1]
                or len(users) != len(self.user_ids) or len(items) != len(self.item_ids)
                or len(set(self.user_ids)) != len(users) or len(set(self.item_ids)) != len(items)
                or not np.isfinite(users).all() or not np.isfinite(items).all()):
            raise ValueError('Invalid recommendation vectors or ID mapping')
        if (self.seen_indptr.shape != (len(users) + 1,)
                or self.seen_indptr[0] != 0 or self.seen_indptr[-1] != len(self.seen_indices)
                or np.any(np.diff(self.seen_indptr) < 0)
                or np.any(self.seen_indices < 0) or np.any(self.seen_indices >= len(items))):
            raise ValueError('Invalid recommendation history')
        # Sort eligible candidates by stable ID for deterministic equal-score ties.
        candidate_rows = sorted((i for i, cid in enumerate(self.item_ids)
                                 if cid in self.companies), key=lambda i: self.item_ids[i])
        self.candidate_ids = [self.item_ids[i] for i in candidate_rows]
        self.item_vectors = np.ascontiguousarray(items[candidate_rows])
        self.user_vectors = users
        self.user_index = {iid: i for i, iid in enumerate(self.user_ids)}
        for array in (self.user_vectors, self.item_vectors, self.seen_indptr, self.seen_indices):
            array.flags.writeable = False

    def investors(self, query='', page=1):
        if page < 1 or len(query) > 200:
            raise ValueError('投资方查询条件无效')
        keywords = query.strip().casefold().split()
        rows = [r for r in self.investor_rows
                if all(word in (r['name'] + ' ' + r['id']).casefold() for word in keywords)]
        pages = max(1, (len(rows) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        page = min(page, pages)
        return dict(items=rows[(page - 1) * self.PAGE_SIZE:page * self.PAGE_SIZE],
                    total=len(rows), page=page, pages=pages)

    def identity(self, investor_id):
        if not isinstance(investor_id, str) or investor_id not in self.subjects:
            raise ValueError('请从数据库中选择投资方')
        row = self.subjects[investor_id]
        return dict(id=investor_id, name=row['name'], trained=investor_id in self.user_index,
                    company_count=len(self.history[investor_id]))

    def preview(self, investor_id):
        """Public source-data preview; never bind an account or run a recommendation."""
        investor = self.identity(investor_id)
        events = list(self.subjects[investor_id].get('events', {}).values())
        dates = [row['date'] for row in events]
        def values(key):
            return sorted({row[key] for row in events if row.get(key) not in (None, '', '未披露')})
        return dict(investor=investor, graph=self.graph(investor_id), profile=dict(
            id=investor_id, name=investor['name'], company_count=investor['company_count'],
            event_count=len(events), first_investment=min(dates) if dates else None,
            last_investment=max(dates) if dates else None, industries=values('industry'),
            regions=values('region'), stages=values('stage'), as_of=self.history_cutoff))

    def graph(self, investor_id):
        """An investor's disclosed events, including companies outside the UI cohort.

        Training membership never limits historical identity or graph visibility.
        Event nodes are source event IDs, not invented ownership relationships.
        """
        investor = self.identity(investor_id)
        events = sorted(self.subjects[investor_id].get('events', {}).values(),
                        key=lambda row: (row['available'], row['id'], row['company']), reverse=True)
        root_id = 'institution:' + investor_id
        nodes = {root_id: dict(id=root_id, type='institution', entity_id=investor_id,
                              label=investor['name'], details={'已收录被投企业': investor['company_count'],
                                                              '已收录融资事件': len(events)})}
        edges = []
        for event in events[:12]:
            cid = 'company:' + event['company']
            rid = 'round:source:' + event['id'] + ':' + event['company']
            nodes.setdefault(cid, dict(id=cid, type='company', entity_id=event['company'],
                                      label=event['name'],
                                      available_in_workspace=event['company'] in self.companies,
                                      details={'行业': event['industry'], '地区': event['region']}))
            nodes[rid] = dict(id=rid, type='round', label=event['stage'] + ' · ' + event['date'],
                             details={'融资日期': event['date'], '可用日期': event['available'],
                                      '轮次': event['stage'], '来源记录': event['id']})
            if event.get('publication_proxy'):
                nodes[rid]['details']['时间说明']='缺少披露日，以事件日代替；实际披露时间未核实'
            evidence = [dict(source='investment_events.parquet / 已披露融资参与记录', record_id=event['id'])]
            edges.extend([
                dict(id=rid + ':investor', source=root_id, target=rid, type='participated',
                     label='参与融资', date=event['date'], evidence=evidence),
                dict(id=rid + ':company', source=rid, target=cid, type='financing_of',
                     label='融资企业', date=event['date'], evidence=evidence)])
        counts = {kind: sum(n['type'] == kind for n in nodes.values())
                  for kind in ('company', 'institution', 'round', 'person', 'risk')}
        notes = [f'展示截至 {self.history_cutoff} 的已披露投资历史；推荐结果不会成为投资关系。',
                 '参与融资不代表股权持有或控制；融资事件按来源记录展示。']
        if len(events) > 12:
            notes.append(f'共收录 {len(events)} 条融资事件，图中展示最近 12 条。')
        if not events:
            notes.append('当前没有可展示的融资事件，未补造关系。')
        return dict(root_id=root_id, investor=investor, as_of=self.history_cutoff,
                    nodes=list(nodes.values()), edges=edges, truncated=len(events) > 12,
                    summary=dict(node_count=len(nodes), edge_count=len(edges), counts=counts,
                                 totals=dict(rounds=len(events), companies=investor['company_count'],
                                             institutions=1, risks=0, people=0)), notes=notes)

    def recommend(self, investor_id):
        started = perf_counter()
        if investor_id not in self.subjects:
            raise KeyError(investor_id)
        if self.model_error:
            raise RecommendationUnavailable('推荐模型暂不可用，请稍后重试。')
        excluded = set(self.history[investor_id])
        uid = self.user_index.get(investor_id)
        if uid is not None:
            excluded.update(self.item_ids[i] for i in
                            self.seen_indices[self.seen_indptr[uid]:self.seen_indptr[uid + 1]])
            # einsum performs a single CPU pass, avoiding BLAS thread oversubscription
            # under concurrent HTTP requests. Exactly the trained SGL dot product.
            scores = np.einsum('ij,j->i', self.item_vectors, self.user_vectors[uid], optimize=False)
            eligible = np.fromiter((cid not in excluded for cid in self.candidate_ids), dtype=bool)
            scores[~eligible] = -np.inf
            order = np.argsort(-scores, kind='stable')[:self.TOP_K]
            ranked = [(self.candidate_ids[i], float(scores[i])) for i in order if eligible[i]]
            method = 'sgl'
            reason = '根据该投资方的历史投资关系，由已训练的 SGL 模型排序。'
            candidate_count = int(eligible.sum())
        else:
            candidates = [cid for cid in self.popular_ids if cid not in excluded]
            ranked = [(cid, float(self.popularity[cid])) for cid in candidates[:self.TOP_K]]
            method = 'mostpop'
            reason = '该投资方未进入 SGL 训练集，按历史投资方数量推荐热门企业。'
            candidate_count = len(candidates)
        items = []
        for rank, (cid, score) in enumerate(ranked, 1):
            c = self.companies[cid]
            items.append(dict(id=cid, name=c.get('name') or cid,
                              industry=c.get('industry') or '未披露', region=c.get('region') or '未披露',
                              stage=c.get('stage') or '未披露', score=score, rank=rank))
        subject = self.subjects[investor_id]
        return dict(investor={'id': investor_id, 'name': subject['name']}, method=method,
                    items=items, count=len(items), candidate_count=candidate_count,
                    reason=reason, model_version=self.manifest['model_version'],
                    history_cutoff=self.history_cutoff,
                    model_history_cutoff=(self.manifest.get('history_cutoff')
                                          or self.manifest.get('max_source_event_date')),
                    elapsed_ms=round((perf_counter() - started) * 1000, 3))
