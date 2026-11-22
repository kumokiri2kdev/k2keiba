""" Compare strategies (ways of buying tickets) by hit probability and return. """
import heapq

from .outcomes import outcomes_from_tierce, outcomes_from_win, horse_probabilities
from .tickets import BET_TYPES, OddsError, expand, hit_keys

UNIT = 100                  # yen; tickets are bought in units of 100 yen
ALLOCATIONS = ('equal', 'payout')
WIDE_ODDS = ('min', 'max', 'mid')


def _odds_table(odds, bet_type, wide):
    """ k2kparser odds of one bet type -> {key: float or None} """
    data = odds.get(bet_type)
    if data is None:
        raise OddsError('No {} odds given.'.format(bet_type))
    if bet_type == 'win':
        if isinstance(data, dict):
            return dict(data)
        return {str(h['horse_num']): h['win'] for h in data}
    if bet_type == 'wide':
        table = {}
        for key, value in data.items():
            if not value or value.get('min') is None or value.get('max') is None:
                table[key] = None
            elif wide == 'mid':
                table[key] = round((value['min'] + value['max']) / 2, 1)
            else:
                table[key] = value[wide]
        return table
    return data


def _waku_of(odds):
    win = odds.get('win')
    if isinstance(win, list):
        return {h['horse_num']: h['waku'] for h in win if h.get('waku')}
    return None


def allocate(odds_list, budget, method='equal'):
    """ Split `budget` (yen) over tickets in units of 100 yen.

    equal:  the same amount on every ticket (the rest of the budget is left unused)
    payout: about the same payout whichever ticket wins (more on low odds); spends the whole budget
    :return: list of yen, one per ticket
    """
    n = len(odds_list)
    units = int(budget) // UNIT
    if n == 0:
        return []
    if units < n:
        raise OddsError('Budget {} yen is not enough for {} tickets (100 yen each at least).'.format(budget, n))
    if method == 'equal':
        return [units // n * UNIT] * n
    if method == 'payout':
        amounts = [1] * n
        heap = [(odds, i) for i, odds in enumerate(odds_list)]     # (payout of the ticket per its units, index)
        heapq.heapify(heap)
        for _ in range(units - n):
            _, i = heapq.heappop(heap)
            amounts[i] += 1
            heapq.heappush(heap, (amounts[i] * odds_list[i], i))
        return [a * UNIT for a in amounts]
    raise OddsError('Unknown allocation: {!r}. Use one of: {}'.format(method, ', '.join(ALLOCATIONS)))


def _tickets(strategy, odds, budget, allocation, wide, runners):
    """ -> (tickets, excluded). ticket: {'bet_type', 'combination', 'odds', 'amount'} """
    bets = strategy['bets'] if 'bets' in strategy else [strategy]
    if not bets:
        raise OddsError('Strategy {!r} has no bets.'.format(strategy.get('name')))

    tickets, excluded, seen = [], [], set()
    for bet in bets:
        bet_type = bet.get('bet_type')
        keys = expand(bet)
        table = _odds_table(odds, bet_type, wide)
        amount = bet.get('amount')
        if amount is not None and (amount <= 0 or amount % UNIT):
            raise OddsError('amount must be a positive multiple of 100: {!r}'.format(amount))
        for key in keys:
            if (bet_type, key) in seen:
                continue
            seen.add((bet_type, key))
            horses = [int(n) for n in key.split('-')]
            if bet_type != 'wakuren' and not set(horses) <= runners:
                excluded.append({'bet_type': bet_type, 'combination': key, 'reason': 'horse not running'})
            elif table.get(key) is None:
                excluded.append({'bet_type': bet_type, 'combination': key, 'reason': 'no odds (cancelled or not sold)'})
            else:
                tickets.append({'bet_type': bet_type, 'combination': key, 'odds': table[key], 'amount': amount})

    if not tickets:
        raise OddsError('Strategy {!r} has no ticket with odds.'.format(strategy.get('name')))

    free = [t for t in tickets if t['amount'] is None]
    fixed_total = sum(t['amount'] for t in tickets if t['amount'] is not None)
    if free:
        method = strategy.get('allocation', allocation)
        for t, yen in zip(free, allocate([t['odds'] for t in free], budget - fixed_total, method)):
            t['amount'] = yen
    for t in tickets:
        t['payout'] = t['amount'] // UNIT * round(t['odds'] * 100)
    return tickets, excluded


def _weighted_median(values):
    """ values: [(value, probability)] -> value at the middle of the probability """
    values = sorted(values)
    half = sum(p for _, p in values) / 2
    acc = 0.0
    for value, p in values:
        acc += p
        if acc >= half:
            return value
    return values[-1][0] if values else None


def _label(orders, all_orders_of_set):
    if len(orders) == all_orders_of_set and len(orders) > 1:
        return '{} (any order)'.format('-'.join(str(n) for n in sorted(orders[0])))
    texts = ['-'.join(str(n) for n in o) for o in orders]
    if len(texts) > 3:
        return '{} and {} more orders'.format(' / '.join(texts[:2]), len(texts) - 2)
    return ' / '.join(texts)


def compare(strategies, odds, budget=3000, allocation='equal', wide='min', outcomes=None, table_size=20):
    """ Compare strategies by hit probability and return.

    :param strategies: list of {'name': str, 'bets': [bet, ...], 'allocation': optional}.
        A bet is {'bet_type': 'win' | 'wakuren' | 'umaren' | 'wide' | 'umatan' | 'trio' | 'tierce',
        and one of 'formation' / 'box' / 'horses' / 'combinations' (see tickets.expand),
        optionally 'amount': yen per ticket (otherwise the budget is allocated)}.
        A strategy without 'bets' is taken as a single bet.
    :param odds: {bet_type: odds} in the shape of k2kparser's output. Every bet type used is needed;
        'tierce' (or 'win') is also used for the probabilities, 'win' (with waku) for wakuren.
    :param budget: yen per strategy
    :param allocation: 'equal' or 'payout' (see allocate)
    :param wide: which end of the wide odds range to use: 'min', 'max' or 'mid'
    :param outcomes: {(1st, 2nd, 3rd): probability}; default: from the tierce odds, or the win odds (Harville)
    :param table_size: max rows of the finish table
    :return: dict, see docs/k2kodds.md
    """
    if wide not in WIDE_ODDS:
        raise OddsError('wide must be one of: {}'.format(', '.join(WIDE_ODDS)))
    if not strategies:
        raise OddsError('No strategies given.')
    if outcomes is not None:
        source = 'given'
    elif odds.get('tierce'):
        outcomes, source = outcomes_from_tierce(odds['tierce']), 'tierce odds'
    elif odds.get('win'):
        outcomes, source = outcomes_from_win(odds['win']), 'win odds (Harville model)'
    else:
        raise OddsError('Need tierce or win odds for the probabilities.')

    names = [s.get('name') or 'strategy {}'.format(i + 1) for i, s in enumerate(strategies)]
    if len(set(names)) != len(names):
        raise OddsError('Strategy names must be unique: {}'.format(', '.join(names)))

    runners = {h for order in outcomes for h in order}
    waku_of = _waku_of(odds)

    evaluated = []
    for name, strategy in zip(names, strategies):
        tickets, excluded = _tickets(strategy, odds, budget, allocation, wide, runners)
        if any(t['bet_type'] == 'wakuren' for t in tickets) and not waku_of:
            raise OddsError('wakuren needs the win odds (with waku) to know the brackets.')
        evaluated.append({'name': name, 'tickets': tickets, 'excluded': excluded,
                          'pay': {(t['bet_type'], t['combination']): t['payout'] for t in tickets},
                          'spent': sum(t['amount'] for t in tickets)})

    # payout of every strategy for every finish
    rows = []
    for order, prob in outcomes.items():
        hits = hit_keys(order, waku_of)
        payouts = tuple(sum(s['pay'].get((bt, k), 0) for bt, keys in hits.items() for k in keys) for s in evaluated)
        rows.append((order, prob, payouts))

    result_strategies = []
    for idx, s in enumerate(evaluated):
        spent = s['spent']
        hit = [(payouts[idx], prob) for _, prob, payouts in rows if payouts[idx] > 0]
        hit_prob = sum(p for _, p in hit)
        out = {
            'name': s['name'],
            'points': len(s['tickets']),
            'spent': spent,
            'hit_probability': round(hit_prob, 4),
            'profit_probability': round(sum(p for v, p in hit if v > spent), 4),
            'torigami_probability': round(sum(p for v, p in hit if v < spent), 4),
            'market_return_rate': round(sum(v * p for v, p in hit) / spent, 3),
        }
        if hit:
            values = [v for v, _ in hit]
            median = _weighted_median(hit)
            out['payout_when_hit'] = {'min': min(values), 'median': median, 'max': max(values)}
            out['return_when_hit'] = {'min': round(min(values) / spent, 2), 'median': round(median / spent, 2),
                                      'max': round(max(values) / spent, 2)}
        if budget - spent > 0:
            out['unused_budget'] = budget - spent
        out['tickets'] = s['tickets']
        if s['excluded']:
            out['excluded'] = s['excluded']
        result_strategies.append(out)

    # finish table: finishes where some strategy pays, grouped when the payouts are the same
    orders_of_set = {}
    for order, _, _ in rows:
        key = frozenset(order)
        orders_of_set[key] = orders_of_set.get(key, 0) + 1
    groups = {}
    for order, prob, payouts in rows:
        if any(payouts):
            g = groups.setdefault((frozenset(order), payouts), {'orders': [], 'probability': 0.0})
            g['orders'].append(order)
            g['probability'] += prob
    table = sorted(groups.items(), key=lambda kv: -kv[1]['probability'])
    shown = table[:table_size]
    any_hit = sum(g['probability'] for _, g in table)

    used = {int(n) for s in evaluated for t in s['tickets'] if t['bet_type'] != 'wakuren'
            for n in t['combination'].split('-')}
    horses = {h: {k: round(v, 4) for k, v in p.items()}
              for h, p in sorted(horse_probabilities(outcomes, used).items())}

    return {
        'probability_source': source,
        'budget': budget,
        'strategies': result_strategies,
        'finishes': [{'finish': _label(sorted(g['orders'], key=lambda o: -outcomes[o]), orders_of_set[key[0]]),
                      'probability': round(g['probability'], 4),
                      'payouts': {s['name']: payout for s, payout in zip(evaluated, key[1])}}
                     for key, g in shown],
        'finishes_omitted': len(table) - len(shown),
        'omitted_probability': round(sum(g['probability'] for _, g in table[table_size:]), 4),
        'no_hit_probability': round(1 - any_hit, 4),
        'horses': horses,
    }
