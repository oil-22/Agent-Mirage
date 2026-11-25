"""Stage exact model and gate sources from the independently audited temporal run."""

import hashlib
import json
from pathlib import Path

from panel_plan import freeze

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'jev-temporal-gate-20261122' / 'attempts' / 'live-1795284570214603700'
EXACT = {
    'live_common.py', 'live_lease.py', 'receipt_protocol.py', 'gate_core.py',
    'temporal_request.py', 'wire_contract.py', 'resource_guard.py', 'seal_run.py',
    'flash-identity.json', 'service-config.json', 'gate-contract.json',
    'four-card-placement.json', 'primary-reference.json', 'actor-template.json',
    'runtime-provenance.json',
}
ADAPTED = {'capture_gui.py', 'live_capture.py', 'live_models.py', 'live_run.py'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'


def put(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(raw)


def main():
    seal_bytes = (OLD / 'local-seal.json').read_bytes()
    seal = json.loads(seal_bytes)
    assert all(sha((OLD / rel).read_bytes()) == digest for rel, digest in seal.items())
    validated = OLD.parent.parent / ('validated-' + OLD.name + '.json')
    result = json.loads(validated.read_bytes())
    assert result['real_main_responses'] == 7 and all(result['paired_recovery'].values())
    terminal = json.loads((OLD / 'run/terminal.json').read_bytes())
    assert terminal['status'] == 'completed_panel' and len(terminal['sessions']) == 7
    exact = EXACT | {p for p in seal if p.startswith('release/') and p.endswith('.py')}
    files = {rel: (OLD / rel).read_bytes() for rel in sorted(exact | ADAPTED)}
    plan = freeze()
    # Only the worker's primary-call ceiling changes. The Flash class and
    # Primary processor, system, native generation and forward checks are identical.
    previous = b"assert self.calls < len(self.plan['cases']) == 7"
    updated = b"assert self.calls < len(self.plan['cases']) == self.plan['max_primary_calls'] == 96"
    assert files['live_models.py'].count(previous) == 1
    files['live_models.py'] = files['live_models.py'].replace(previous, updated)
    files['live_plan.json'] = json_bytes(plan)
    for rel, raw in files.items():
        put(HERE / rel, raw)
    put(HERE / 'stage-provenance.json', json_bytes({
        'previous_name': OLD.name,
        'previous_local_seal_sha256': sha(seal_bytes),
        'previous_validated_result_sha256': sha(validated.read_bytes()),
        'exactly_copied': {p: seal[p] for p in sorted(exact)},
        'adapted_originals': {p: seal[p] for p in sorted(ADAPTED)},
        'live_models_current_sha256': sha(files['live_models.py']),
        'plan_sha256': sha(files['live_plan.json']),
        'plan_generator_sha256': sha((HERE / 'panel_plan.py').read_bytes()),
    }))
    print('Verified previous complete seal; froze', len(plan['cases']), 'new cases, SHA', sha(files['live_plan.json']))


if __name__ == '__main__':
    main()
