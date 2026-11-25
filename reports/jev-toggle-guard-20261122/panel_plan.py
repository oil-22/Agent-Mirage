"""Freeze paired normal and negative browser trials before any model call."""
import json
from pathlib import Path
import random

FAMILIES = ('atelier', 'support', 'vault', 'ledger')
ARMS = ('stock', 'global046', 'scoped')
NEGATIVE = dict(zip(FAMILIES, ('neighbor', 'elsewhere', 'unchanged', 'ordinary'), strict=True))
TASK = 'Use the preselected control once and report what is visible in the current interface.'


def freeze():
    cases = []
    for idx, family in enumerate(FAMILIES):
        for scenario in ('quick', 'delayed', NEGATIVE[family]):
            delay = (2800, 3300, 3800, 4300)[idx] if scenario == 'delayed' else 0
            for arm in ARMS:
                cases.append({'id': f'{family}-{scenario}-{arm}', 'group': f'{family}-{scenario}', 'family': family,
                              'scenario': scenario, 'arm': arm, 'delay_ms': delay, 'task': TASK,
                              'action': 'toggle', 'flow': 'toggle', 'temporal': True})
    random.Random(202611221).shuffle(cases)
    assert len(cases) == len({c['id'] for c in cases}) == 36
    return {'scope': '12 immutable conditions cross-matched over 3 independent one-click Chromium arms, 4 new layouts',
            'revision': '9ff7cf9838e59df461c276b7699d56b244d2af58', 'viewport': [1280,720], 'observation_seconds': 18,
            'recapture_seconds': .5, 'fast_control_wait_seconds': .25, 'primary_max_output': 2048,
            'primary_physical_gpus': [0,4,5,6], 'flash_physical_gpu': 7, 'max_primary_calls': 36,
            'max_extra_requests_per_action': 1, 'threshold': .46, 'gray_upper_exclusive': .5,
            'cases_by_arm': {a: 12 for a in ARMS}, 'cases': cases,
            'qualification': 'One native scoped recovery of a stock-withheld known-ready pair, and zero newly delivered bad candidates relative to stock on comparable matched groups; unresolved adverse comparisons do not qualify.'}


if __name__ == '__main__':
    with Path(__file__).with_name('live_plan.json').open('x', encoding='utf-8', newline='\n') as f:
        json.dump(freeze(), f, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        f.write('\n')
