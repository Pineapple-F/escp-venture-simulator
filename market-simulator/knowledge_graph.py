"""Bounded, read-only graphs built from the disclosed historical snapshot.

Participation in a financing round is not evidence of ownership or control.
No simulation-account transaction or recommendation establishes an edge here.
"""
from collections import defaultdict
from hashlib import sha256
import json


def _key(*parts):
    return sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True,
                             default=str).encode('utf-8')).hexdigest()[:20]


class KnowledgeGraph:
    MAX_NODES = 40
    COMPANY_ROUNDS = 8
    INSTITUTION_ROUNDS = 12
    COMPANY_INSTITUTIONS = 12
    PEER_ROUNDS = 6
    PEOPLE = 6
    RISKS = 5

    def __init__(self, universe, institutions, profile_loader=None):
        self.as_of = universe['start']
        self.profile_loader = profile_loader
        self.companies = {str(c['id']): c for c in universe['companies']}
        self.rounds = {}
        # Filtering precedes every index and total, including institution counts.
        for row in sorted(universe.get('rounds', []),
                          key=lambda r: json.dumps(r, sort_keys=True, default=str)):
            if (row.get('id') and row.get('company') in self.companies
                    and row.get('available') and row['available'] <= self.as_of):
                self.rounds.setdefault(row['id'], row)
        self.company_rounds = defaultdict(list)
        for row in self.rounds.values():
            self.company_rounds[row['company']].append(row)
        for rows in self.company_rounds.values():
            rows.sort(key=self._round_order)
        self.institutions = {}
        self.institution_rounds = {}
        self.round_institutions = defaultdict(list)
        for iid, institution in sorted(institutions.items()):
            # Participation must point to a canonical, already-visible round.
            ids = {r['id'] for r in institution.get('rounds', [])
                   if r.get('id') in self.rounds
                   and r.get('company') == self.rounds[r['id']]['company']}
            if not ids:
                continue
            self.institutions[iid] = institution
            self.institution_rounds[iid] = sorted(
                (self.rounds[rid] for rid in ids), key=self._round_order)
            for rid in ids:
                self.round_institutions[rid].append(iid)
        for ids in self.round_institutions.values():
            ids.sort()
        self.company_risks = defaultdict(list)
        risks = {}
        for risk in universe.get('risks', []):
            if (risk.get('company') in self.companies and risk.get('date')
                    and risk['date'] <= self.as_of):
                key = (risk['company'], risk['date'], risk.get('type', 'unknown'))
                previous = risks.get(key)
                if previous is None or risk.get('records', 0) > previous.get('records', 0):
                    risks[key] = risk
        for risk in risks.values():
            self.company_risks[risk['company']].append(risk)
        for rows in self.company_risks.values():
            rows.sort(key=lambda r: (r['date'], r.get('type', '')), reverse=True)

    @staticmethod
    def _round_order(row):
        return (-int(row['available'].replace('-', '')), str(row['id']))

    def _company_node(self, cid):
        base = self.companies[cid]
        latest = next(iter(self.company_rounds.get(cid, [])), {})
        details = {'行业': latest.get('industry') or base.get('industry') or '未披露',
                   '地区': latest.get('region') or base.get('region') or '未披露',
                   '历史融资轮次': len(self.company_rounds.get(cid, []))}
        if base.get('established') and base['established'] <= self.as_of:
            details['成立日期'] = base['established']
        return dict(id='company:' + cid, type='company', entity_id=cid,
                    label=latest.get('name') or base.get('name') or cid, details=details)

    def _institution_node(self, iid):
        rounds = self.institution_rounds[iid]
        return dict(id='institution:' + iid, type='institution', entity_id=iid,
                    label=self.institutions[iid].get('name') or iid,
                    details={'已收录融资轮次': len(rounds),
                             '已收录被投企业': len({r['company'] for r in rounds}),
                             '关系含义': '历史融资参与，不代表股权、控制或当前持仓'})

    @staticmethod
    def _round_node(row):
        details = {'融资日期': row.get('date') or '未披露', '可用日期': row['available'],
                   '轮次': row.get('stage') or '未披露',
                   '整轮融资金额': row.get('amount') if row.get('amount') is not None else '未披露',
                   '币种': row.get('currency') or '未披露',
                   '金额口径': '整轮融资总额，不代表任何单个机构的出资额',
                   '来源记录': sorted(set(row.get('source_ids', []))),
                   '来源冲突': '存在，需核验' if row.get('conflict') else '未标记冲突'}
        if row.get('publication_proxy'):
            details['时间说明'] = '以融资事件日期代替公开日期，实际披露时间未核实'
        return dict(id='round:' + row['id'], type='round',
                    label=(row.get('stage') or '未披露轮次') + ' · ' +
                          (row.get('date') or row['available']), details=details)

    @staticmethod
    def _round_evidence(row):
        return ([dict(source='universe-v3.json / rounds（清洗合并融资记录）', record_id=row['id'])]
                + [dict(source='融资来源事件（合并前）', record_id=sid)
                   for sid in sorted(set(row.get('source_ids', [])))])

    @staticmethod
    def _participation_evidence(iid, row):
        # build_index preserves institution/round membership, but not the exact
        # event row for each institution. A merged round may have other investors'
        # source rows: those must not be attributed to this participation edge.
        return [dict(source='institutions.build_index / 机构—融资轮次关联（清洗投资事件表匹配）',
                     record_id=iid + ' / ' + row['id'])]

    def graph(self, entity_type, entity_id):
        if entity_type not in ('company', 'institution'):
            raise ValueError('图谱实体类型无效')
        entities = self.companies if entity_type == 'company' else self.institutions
        if entity_id not in entities:
            raise KeyError(entity_id)
        nodes, edges = {}, {}
        truncated = False
        notes = [f'依据截至 {self.as_of} 的已收录历史资料生成；未收录关系不代表不存在。',
                 '融资金额为整轮总额，不代表单个机构的出资额；参与融资不等于股权持有或控制。',
                 '本图展示历史资料，不包含模拟账户中的资金配置、接洽或融资操作。']

        def add_nodes(*items):
            nonlocal truncated
            if len(nodes.keys() | {item['id'] for item in items}) > self.MAX_NODES:
                truncated = True
                return False
            for item in items:
                nodes.setdefault(item['id'], item)
            return True

        def edge(source, target, kind, label, date, evidence):
            if source not in nodes or target not in nodes:
                return
            eid = 'edge:' + _key(source, target, kind)
            edges.setdefault(eid, dict(id=eid, source=source, target=target, type=kind,
                                       label=label, date=date, evidence=evidence))

        def financing(row, investor_ids):
            company_id, round_id = 'company:' + row['company'], 'round:' + row['id']
            if not add_nodes(self._company_node(row['company']), self._round_node(row)):
                return False
            evidence = self._round_evidence(row)
            edge(round_id, company_id, 'financing_of', '融资企业',
                 row.get('date') or row['available'], evidence)
            for iid in investor_ids:
                if add_nodes(self._institution_node(iid)):
                    edge('institution:' + iid, round_id, 'participated', '参与融资',
                         row.get('date') or row['available'],
                         self._participation_evidence(iid, row))
            return True

        root_id = entity_type + ':' + entity_id
        if entity_type == 'institution':
            add_nodes(self._institution_node(entity_id))
            rounds = self.institution_rounds[entity_id]
            totals = dict(rounds=len(rounds), companies=len({r['company'] for r in rounds}),
                          institutions=1, risks=0, people=0)
            truncated = len(rounds) > self.INSTITUTION_ROUNDS
            for row in rounds[:self.INSTITUTION_ROUNDS]:
                financing(row, [entity_id])
        else:
            add_nodes(self._company_node(entity_id))
            rounds = self.company_rounds.get(entity_id, [])
            investor_ids = sorted({iid for row in rounds
                                   for iid in self.round_institutions[row['id']]})
            risks = self.company_risks.get(entity_id, [])
            totals = dict(rounds=len(rounds), institutions=len(investor_ids),
                          companies=1, risks=len(risks), people=0)
            truncated = len(rounds) > self.COMPANY_ROUNDS
            visible_investors = set()
            for row in rounds[:self.COMPANY_ROUNDS]:
                admitted = []
                for iid in self.round_institutions[row['id']]:
                    if iid in visible_investors or len(visible_investors) < self.COMPANY_INSTITUTIONS:
                        admitted.append(iid)
                        visible_investors.add(iid)
                    else:
                        truncated = True
                financing(row, admitted)

            if self.profile_loader is not None:
                try:
                    profile = self.profile_loader(entity_id, self.as_of)
                    officers = {}
                    for person in profile.get('officers', []):
                        if person.get('start') and person['start'] > self.as_of:
                            continue
                        record = dict(person)
                        if record.get('end') and record['end'] > self.as_of:
                            record['end'] = None
                        officers[_key(entity_id, record)] = record
                    totals['people'] = len(officers)
                    truncated = truncated or len(officers) > self.PEOPLE
                    for person_key, person in sorted(officers.items())[:self.PEOPLE]:
                        pid = 'person:' + person_key
                        locator = '; '.join([entity_id, person.get('name') or '姓名未披露',
                                            person.get('position') or '职务未披露',
                                            person.get('start') or '起始时间未明确',
                                            person.get('end') or '离任时间未明确'])
                        details = {'职务': person.get('position') or '未披露',
                                   '起始日期': person.get('start') or '未明确',
                                   '离任日期': person.get('end') or '未明确',
                                   '记录状态': person.get('status') or '时间待核验',
                                   '身份说明': '本企业任职记录，未与其他企业的同名人员合并'}
                        if add_nodes(dict(id=pid, type='person',
                                          label=person.get('name') or '姓名未披露', details=details)):
                            edge(pid, root_id, 'holds_role', person.get('position') or '任职记录',
                                 person.get('start'),
                                 [dict(source='主要人员表（按企业、姓名、职务、时间定位）', record_id=locator)])
                    if profile.get('note'):
                        notes.append(profile['note'])
                except Exception:
                    notes.append('人员资料暂不可用；已展示可用的融资及风险关系，可稍后重试。')

            truncated = truncated or len(risks) > self.RISKS
            for risk in risks[:self.RISKS]:
                kind = risk.get('type', 'unknown')
                label = {'abnormal_listing': '列入经营异常',
                         'abnormal_removed': '移出经营异常'}.get(kind, '风险记录')
                rid = 'risk:' + _key(entity_id, risk['date'], kind)
                if add_nodes(dict(id=rid, type='risk', label=label,
                                  details={'日期': risk['date'], '记录类型': kind,
                                           '来源记录数': risk.get('records', 1),
                                           '状态说明': '历史事件，不代表当前经营状态'})):
                    edge(root_id, rid, 'risk_record', label, risk['date'],
                         [dict(source='universe-v3.json / risks（经营异常记录汇总）',
                               record_id='; '.join([entity_id, risk['date'], kind]))])
            if risks:
                notes.append('经营异常列入、移出分别显示为历史事件，不据此推断企业当前状态。')

            # Related companies require actual events of a shared institution.
            peer_rounds = {}
            for iid in sorted(visible_investors):
                available = [row for row in self.institution_rounds[iid]
                             if row['company'] != entity_id]
                if len(available) > 2:
                    truncated = True
                for row in available[:2]:
                    peer_rounds[row['id']] = row
            if len(peer_rounds) > self.PEER_ROUNDS:
                truncated = True
            for row in sorted(peer_rounds.values(), key=self._round_order)[:self.PEER_ROUNDS]:
                financing(row, [iid for iid in self.round_institutions[row['id']]
                                if iid in visible_investors and 'institution:' + iid in nodes])
            if peer_rounds:
                notes.append('其他企业通过共同融资参与机构关联，不表示企业之间存在直接投资或控制关系。')

        counts = {kind: sum(node['type'] == kind for node in nodes.values())
                  for kind in ('company', 'institution', 'round', 'person', 'risk')}
        if len(nodes) == 1:
            notes.append('当前资料未收录可展示的关联记录，可继续查看其他企业或机构。')
        if truncated:
            notes.append('为便于阅读，仅展示部分近期融资、人员、风险及关联企业；点击企业或机构可继续查看其图谱。')
        return dict(root_id=root_id, as_of=self.as_of,
                    nodes=sorted(nodes.values(), key=lambda node: (node['id'] != root_id, node['type'], node['id'])),
                    edges=sorted(edges.values(), key=lambda item: item['id']),
                    truncated=truncated, summary=dict(node_count=len(nodes), edge_count=len(edges),
                                                      counts=counts, totals=totals), notes=notes)
