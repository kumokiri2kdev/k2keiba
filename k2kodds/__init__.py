""" k2kodds: compare ways of buying tickets for a race by hit probability and return.

No dependency on k2kparser or the network: the inputs are odds dicts in the shape of k2kparser's output
(docs/output.md), e.g. {'tierce': {'1-2-3': 609.5, ...}, 'umaren': {'1-2': 55.9, ...}, 'win': [...]}.

    from k2kodds import compare
    result = compare(strategies, odds, budget=3000)

The probability of each finish (1st-2nd-3rd) is read from the market: the tierce (3連単) odds, or the win odds
with the Harville model when tierce odds are not given. See compare() for the details.
"""
from .outcomes import outcomes_from_tierce, outcomes_from_win, horse_probabilities
from .tickets import BET_TYPES, expand, OddsError
from .compare import compare, allocate

__all__ = ['compare', 'allocate', 'expand', 'outcomes_from_tierce', 'outcomes_from_win', 'horse_probabilities',
           'BET_TYPES', 'OddsError']
