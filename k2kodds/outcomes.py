""" Probability of each finish (1st, 2nd, 3rd) implied by the odds.

Odds are (1 - takeout) / probability, so 1 / odds is proportional to the probability the market gives.
Normalizing it removes the takeout. These are the market's view, not a prediction.
"""
from itertools import permutations

from .tickets import OddsError


def _parse_order(key):
    return tuple(int(n) for n in key.split('-'))


def outcomes_from_tierce(tierce_odds):
    """ {'1-2-3': 609.5, ...} (3連単) -> {(1, 2, 3): probability}. Orders without odds (None) are left out. """
    weights = {_parse_order(k): 1 / v for k, v in tierce_odds.items() if v}
    total = sum(weights.values())
    if not total:
        raise OddsError('No tierce odds to read probabilities from.')
    return {order: w / total for order, w in weights.items()}


def win_probabilities(win_odds):
    """ k2kparser win odds (list of {'horse_num', 'win', ...}) or {'1': 3.3} -> {horse: probability} """
    if isinstance(win_odds, dict):
        items = [(int(k), v) for k, v in win_odds.items()]
    else:
        items = [(h['horse_num'], h['win']) for h in win_odds]
    weights = {num: 1 / v for num, v in items if v}
    total = sum(weights.values())
    if not total:
        raise OddsError('No win odds to read probabilities from.')
    return {num: w / total for num, w in weights.items()}


def outcomes_from_win(win_odds):
    """ Harville model: P(a, b, c) = p_a * p_b / (1 - p_a) * p_c / (1 - p_a - p_b). """
    p = win_probabilities(win_odds)
    outcomes = {}
    for a, b, c in permutations(p, 3):
        outcomes[(a, b, c)] = p[a] * p[b] / (1 - p[a]) * p[c] / (1 - p[a] - p[b])
    return outcomes


def horse_probabilities(outcomes, horses=None):
    """ {horse: {'win': P(1st), 'top2': P(1st or 2nd), 'top3': P(in the first 3)}} """
    result = {}
    for order, prob in outcomes.items():
        for pos, horse in enumerate(order):
            if horses is not None and horse not in horses:
                continue
            r = result.setdefault(horse, {'win': 0.0, 'top2': 0.0, 'top3': 0.0})
            if pos == 0:
                r['win'] += prob
            if pos <= 1:
                r['top2'] += prob
            r['top3'] += prob
    return result
