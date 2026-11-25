"""Index already reviewed Flash temporal decisions, without model calls or training."""

import hashlib
import json
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / 'jev-temporal-gate-20261122'
LIVE_ID = 'live-1795284570214603700'
OFFLINE_ID = 'shadow-1795283017165610600'
REVISION = '9ff7cf9838e59df461c276b7699d56b244d2af58'


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def verify(root, names, seal):
    for name in names:
        if sha(root / name) != seal[name]:
            raise ValueError(f'Sealed source changed: {root / name}')


def main():
    completion = load(PRIOR / 'completion-receipt.json')['evidence_files_sha256']
    live_index = f'validated-{LIVE_ID}.json'
    live_key = f'attempts/{LIVE_ID}/local-seal.json'
    verify(PRIOR, (live_index, live_key), completion)
    model_prompt = PRIOR / 'temporal_request.py'
    live = PRIOR / 'attempts' / LIVE_ID
    live_seal = load(live / 'local-seal.json')
    if sha(model_prompt) != live_seal['temporal_request.py']:
        raise ValueError('Current temporal request differs from the sealed live request builder')
    audit = load(PRIOR / live_index)
    assert all(audit['paired_recovery'].values())
    cases = defaultdict(list)
    for trajectory in audit['rows']:
        for decision in trajectory['flash']:
            if decision['kind'] != 'temporal':
                continue
            request = decision['request_id']
            result_key = f'run/flash/{request}/result.json'
            verify(live, (result_key,), live_seal)
            result = load(live / result_key)
            assert result['revision'] == REVISION
            assert result['ordered_images'] == decision['images'] and result['choice'] == decision['decision']
            name = trajectory['id']
            expected = {'early_before_render': 'NO', 'after_visible_render': 'YES'}[decision['phase']]
            wire_key = f'run/flash/{request}/wire.json'
            verify(live, (wire_key,), live_seal)
            wire = load(live / wire_key)
            executed = trajectory['dispatched_action']
            assert wire['body']['action'] == executed
            pre, cur = decision['images']
            bound = {'previous_image_sha256': pre, 'candidate_image_sha256': cur, 'executed_action': executed}
            uid = hashlib.sha256(canonical(bound)).hexdigest()
            cases[uid].append({'binding': bound, 'trajectory': name, 'capture_id': decision['capture_id'],
                               'request_id': request, 'capture_phase': decision['phase'], 'policy_label': expected,
                               'observed_choice': result['choice'], 'p_yes': result['probabilities']['YES']})

    groups = []
    for key, members in cases.items():
        labels = {r['policy_label'] for r in members}
        assert len(labels) == 1
        groups.append({'input_key': key, 'binding': members[0]['binding'], 'policy_label': labels.pop(),
                       'observations': [{k: v for k, v in r.items() if k not in ('binding', 'policy_label')} for r in members]})

    archive = PRIOR / 'attempts' / OFFLINE_ID
    archived_seal = archive / 'local-seal.json'
    seal = load(archived_seal)
    verify(archive, ('plan.json', 'run/terminal.json', 'temporal_request.py'), seal)
    assert seal['temporal_request.py'] == sha(model_prompt)
    archived_cases = {case['case']: case for case in load(archive / 'plan.json')['cases']}
    reviewed = {
        'search-genuine': ('YES', 'Visible results page'), 'search-early-replay': ('NO', 'Previous homepage replay'),
        'type-genuine': ('YES', 'The requested text is visible in City'), 'type-early-replay': ('NO', 'The field is still blank'),
        'type-other-change': ('NO', 'Focus/other UI differs, but City is still blank'),
        'pagination-genuine': ('YES', 'The actual last page is visible; original temporal false hold'),
        'pagination-early-replay': ('NO', 'Previous page replay'),
        'escape-genuine': (None, 'New capture with identical pixels; the inputs alone do not certify no-op or pending'),
    }
    archived = []
    for row in load(archive / 'run/terminal.json')['replies']:
        case = archived_cases[row['case']]
        label, note = reviewed[row['case']]
        assert row['images'] == [case['previous_image_sha256'], case['candidate_image_sha256']]
        archived.append({'case': row['case'], 'source_kind': case['kind'], 'ordered_image_sha256': row['images'],
                         'executed_action': case['executed_action'], 'policy_label': label, 'interpretation': note,
                         'observed_choice': row['choice'], 'p_yes': row['probabilities']['YES']})
    assert sum(map(len, cases.values())) == 8 and len(groups) == 4 and len(archived) == 8
    reference = {
        'purpose': 'Seen engineering regression only. Not for optimization, calibration, or independent effectiveness estimates.',
        'requests_are_not_independent_tasks': True,
        'training_use': False, 'threshold_selection_use': False, 'independent_test_use': False,
        'model_revision': REVISION, 'same_prompt_code_sha256': sha(model_prompt),
        'live': {'attempt': LIVE_ID, 'source_seal_sha256': sha(live / 'local-seal.json'), 'source_audit_sha256': sha(PRIOR / live_index),
                 'temporal_requests': 8, 'distinct_image_pair_and_action_inputs': 4, 'unique_input_groups': groups},
        'offline': {'attempt': OFFLINE_ID, 'source_seal_sha256': sha(archived_seal),
                    'source_distinct_trajectories': 1, 'requests': archived},
        'additional_model_calls': 0,
    }
    with (HERE / 'known-regression-reference.json').open('x', encoding='utf-8') as handle:
        json.dump(reference, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


if __name__ == '__main__':
    main()
