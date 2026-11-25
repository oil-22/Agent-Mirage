"""Freeze a disjoint scale panel; this file neither runs the browser nor submits models."""
import random


REVISION = '9ff7cf9838e59df461c276b7699d56b244d2af58'
FAMILIES = ['market', 'library', 'inventory', 'service']
FLOWS = ['search', 'type', 'pagination', 'open', 'toggle', 'escape']
TASK = {
    'search': 'Use the existing search keyword and report the results currently visible.',
    'type': 'Enter the supplied text in the focused field and report what the field displays.',
    'pagination': 'Click the next numbered page and report which page and range are visible now.',
    'open': 'Open the details dialog and report what the dialog displays.',
    'toggle': 'Change the notification setting once and report its new state.',
    'escape': 'Close the open dialog with Escape and report the visible page.',
    'boundary': 'Scroll down at the bottom of the page and report the last visible section.',
}


def freeze():
    rng = random.Random(20261122)
    cases = []

    def row(flow, family, arm, delay, scenario='plain', action=True):
        group = f'{family}-{flow}'
        return {'id': f'{group}-{arm}', 'group': group, 'family': family, 'flow': flow, 'action': flow,
                'arm': arm, 'delay_ms': delay, 'scenario': scenario, 'temporal': arm != 'original',
                'dispatch': action, 'task': TASK[flow]}

    for i, family in enumerate(FAMILIES):
        for j, flow in enumerate(FLOWS):
            delay = (2400, 3100, 3800, 4500)[(i+j) % 4]
            cases.extend([row(flow, family, 'original', delay), row(flow, family, 'defense', delay),
                          row(flow, family, 'fast', 0)])
        cases.extend([row('search', family, 'white', 3600, 'white'),
                      row('search', family, 'buttons', 3600, 'buttons'),
                      row('type', family, 'missing', 0, 'missing'),
                      row('type', family, 'replaced', 0, 'replaced'),
                      row('toggle', family, 'sparse', 0, 'sparse'),
                      row('boundary', family, 'boundary', 0)])
    rng.shuffle(cases)
    assert len(cases) == len({case['id'] for case in cases}) == 96
    counts = {k: sum(c['arm'] == k for c in cases) for k in ('original', 'defense', 'fast', 'white', 'buttons', 'missing', 'replaced', 'sparse', 'boundary')}
    assert list(counts.values()) == [24, 24, 24, 4, 4, 4, 4, 4, 4]
    return {'scope': '96 new controlled Chromium episodes; one actual fixture action (if initial frame accepted), one or zero native 27B inference; no official tasks',
            'revision': REVISION, 'viewport': [1280, 720], 'primary_physical_gpus': [0, 4, 5, 6], 'flash_physical_gpu': 7,
            'recapture_seconds': .5, 'fast_control_wait_seconds': .25, 'observation_seconds': 18,
            'primary_max_output': 2048, 'max_primary_calls': len(cases), 'manual_stop_file_supported': True,
            'observation_limit_scope': 'Study censor only; never release a failed candidate on timeout. Current open-ended production policy unchanged.',
            'cases_by_arm': counts, 'cases': cases}
