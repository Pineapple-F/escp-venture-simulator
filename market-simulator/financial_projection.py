"""Historical peer estimates used to turn event forecasts into monthly values.

The estimator only reads financing observations that are already available at the
simulation cutoff.  It never treats an undisclosed valuation as zero and never
converts currencies.
"""
from collections import Counter, defaultdict
from statistics import median


def _usable_amount(row, currency):
    return (row.get('amount') if row.get('currency') == currency
            and row.get('amount') and not row.get('conflict') else None)


def _usable_valuation(row, currency):
    value = row.get('valuation')
    return (value if row.get('valuation_currency') == currency and value
            and value > 0 else None)


def _middle(values):
    values = [float(value) for value in values if value and value > 0]
    return median(values) if values else None


class FinancialProjection:
    """Estimate the value impact of the model's next-financing event."""

    def __init__(self, universe):
        self.cutoff = universe['start']
        self.by_company = defaultdict(list)
        self.transitions = []
        self.rounds = [row for row in universe['rounds']
                       if row.get('available', '9999-99-99') <= self.cutoff]
        for row in self.rounds:
            self.by_company[row['company']].append(row)
        for rows in self.by_company.values():
            rows.sort(key=lambda row: (row.get('date', ''), row.get('available', ''), row.get('id', '')))
            for current, following in zip(rows, rows[1:]):
                if not following.get('amount') or following.get('conflict'):
                    continue
                self.transitions.append({
                    'industry': following.get('industry') or current.get('industry') or '未披露',
                    'stage': current.get('stage') or '未披露',
                    'next_stage': following.get('stage') or '未披露',
                    'currency': following.get('currency'),
                    'next_amount': following.get('amount'),
                    'next_valuation': following.get('valuation')
                        if following.get('valuation_currency') == following.get('currency') else None,
                })

    def _transition_pool(self, industry, stage, currency):
        choices = [
            [row for row in self.transitions if row['currency'] == currency
             and row['industry'] == industry and row['stage'] == stage],
            [row for row in self.transitions if row['currency'] == currency
             and row['stage'] == stage],
            [row for row in self.transitions if row['currency'] == currency
             and row['industry'] == industry],
            [row for row in self.transitions if row['currency'] == currency],
        ]
        for level, rows in zip(('同行业同阶段', '同阶段', '同行业', '同币种'), choices):
            if len(rows) >= 5:
                return level, rows
        return ('同币种', choices[-1]) if choices[-1] else (None, [])

    def _valuation_ratio(self, industry, stage, currency):
        choices = [
            [row for row in self.rounds if row.get('industry') == industry and row.get('stage') == stage],
            [row for row in self.rounds if row.get('stage') == stage],
            self.rounds,
        ]
        for rows in choices:
            ratios = []
            for row in rows:
                amount = _usable_amount(row, currency)
                valuation = _usable_valuation(row, currency)
                if amount and valuation and valuation >= amount:
                    ratios.append(min(50.0, valuation / amount))
            if len(ratios) >= 5:
                return float(median(ratios)), len(ratios)
        return 5.0, 0

    def project(self, company, forecast, currency):
        event = next((item for item in forecast.get('events', []) if item.get('event') == '融资'), None)
        if not event:
            return {'available': False, 'predicted': False, 'reason': '没有融资事件预测'}
        history = self.by_company.get(company, [])
        latest = history[-1] if history else {}
        industry = latest.get('industry') or '未披露'
        stage = latest.get('stage') or '未披露'
        basis, peers = self._transition_pool(industry, stage, currency)
        next_amount = _middle(row['next_amount'] for row in peers)
        if next_amount is None:
            return {'available': False, 'predicted': bool(event.get('predicted')),
                    'month_index': event.get('month_index'), 'estimated_month': event.get('estimated_month'),
                    'currency': currency, 'reason': '没有同币种历史金额样本'}

        next_stages = [row['next_stage'] for row in peers if row.get('next_stage')]
        next_stage = Counter(next_stages).most_common(1)[0][0] if next_stages else stage
        current_ratio, current_ratio_n = self._valuation_ratio(industry, stage, currency)
        next_ratio, next_ratio_n = self._valuation_ratio(industry, next_stage, currency)
        latest_amount = _usable_amount(latest, currency)
        latest_valuation = _usable_valuation(latest, currency)
        peer_current_amounts = [_usable_amount(row, currency) for row in self.rounds
                                if row.get('stage') == stage and row.get('industry') == industry]
        current_amount = latest_amount or _middle(peer_current_amounts) or next_amount
        entry_value = latest_valuation or current_amount * current_ratio
        disclosed_next_values = [row['next_valuation'] for row in peers if row.get('next_valuation')]
        next_value = (_middle(disclosed_next_values) if len(disclosed_next_values) >= 5
                      else next_amount * next_ratio)
        next_value = max(next_amount, next_value)
        multiple = max(.5, min(5.0, next_value / entry_value)) if entry_value else 1.0
        return {
            'available': True,
            'predicted': bool(event.get('predicted')),
            'month_index': event.get('month_index'),
            'estimated_month': event.get('estimated_month'),
            'currency': currency,
            'current_stage': stage,
            'next_stage': next_stage,
            'predicted_amount': round(next_amount, 2),
            'entry_valuation': round(entry_value, 2),
            'predicted_post_valuation': round(next_value, 2),
            'value_multiple': round(multiple, 6),
            'basis': basis,
            'peer_count': len(peers),
            'valuation_sample_count': max(current_ratio_n, next_ratio_n, len(disclosed_next_values)),
        }
