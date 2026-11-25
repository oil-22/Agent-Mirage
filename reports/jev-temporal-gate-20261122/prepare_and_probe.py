"""Freeze action-linked replay controls and check only the native Flash CPU encoder."""

import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile
import time


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
PROJECT = WORKSPACE / 'jev-defense-four-gpu-20261106' / 'flash-native-source-loop-20261116-linked11'
PACKAGE = PROJECT / 'preparation-1794820110211682400' / 'package' / 'flash'
ARCHIVE = HERE.parent / 'crop-visual-replay-20261120' / 'attempt-1795150772352391100' / 'cases' / 'source-images'
REVISION = '9ff7cf9838e59df461c276b7699d56b244d2af58'
RUN_ID = 'native16b-T114-stale_replace-gate'
SSH = ['ssh', '-p', '2223', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', 'researcher@192.0.2.11']


def read(path):
    return json.loads(path.read_bytes())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def freeze():
    (source,) = PROJECT.glob(f'trajectory-audit-{RUN_ID}-*')
    seal = read(source / 'seal.json')
    required = ('Controller.json', 'summary.json', 'trusted-source-receipts.json')
    assert all(sha((source / name).read_bytes()) == seal[name] for name in required)
    summary = read(source / 'summary.json')
    binding = summary['binding']
    controller = read(source / 'Controller.json')['result']
    source_receipts = read(source / 'trusted-source-receipts.json')['result']
    assert summary['run_id'] == RUN_ID and summary['GUI_terminal_sealed']
    assert binding['terminal_sha256'] == controller['terminal_sha256']
    assert all(binding['chain'][k] == controller['chain'][k] for k in ('head', 'events', 'sha256'))
    assert source_receipts['signatures_challenges_persistent_ledgers_and_same_live_source_verified']
    assert source_receipts['all_raw_delivered_images_bound']
    actions = {e['data']['step']: e for e in controller['events'] if e['kind'] == 'native_environment_action'}
    accepted = {r['source_action_sequence']: r for r in source_receipts['rows'] if r['receipt_decision'] == 'YES'}
    assert len(accepted) == sum(r['receipt_decision'] == 'YES' for r in source_receipts['rows'])

    cases, images = [], {}
    for step, name in [(1, 'search'), (3, 'type'), (13, 'pagination'), (8, 'escape')]:
        prior, later = accepted[step - 1], accepted[step]
        row = binding['rows'][step - 1]
        data = actions[step]['data']
        assert prior['raw_sha256'] == prior['delivered_sha256'] == row['image_sha256']
        assert later['raw_sha256'] == later['delivered_sha256'] == data['current_capture_sha256']
        assert binding['rows'][step]['image_sha256'] == later['raw_sha256']
        assert data == row['actual_native_action'] and row['candidate_dispatched'] and data['ok']
        assert prior['capture_id'] != later['capture_id'] and prior['challenge'] != later['challenge']
        start, end = prior['raw_sha256'], later['raw_sha256']
        assert (start == end) == (name == 'escape')
        shared = {'previous_image_sha256': start, 'executed_action': data['payload'],
                  'action_event_seq': actions[step]['seq'], 'source_action_sequence': step,
                  'trusted_previous_capture_id': prior['capture_id']}
        cases.append({**shared, 'case': name + '-genuine', 'candidate_image_sha256': end,
                      'genuine_capture_id': later['capture_id'], 'kind': 'archived_post_action_capture',
                      'evaluation_axis': 'same_pixels_new_capture_no_visible_effect' if name == 'escape' else 'visible_action_outcome'})
        compare = {start, end}
        if name != 'escape':
            cases.append({**shared, 'case': name + '-early-replay', 'candidate_image_sha256': start,
                          'genuine_capture_id': None, 'kind': 'offline_replay_of_pre_action_pixels',
                          'evaluation_axis': 'prior_state_after_action'})
        if name == 'type':
            unrelated = accepted[1]['raw_sha256']  # Readable search page, but City is blank and not focused.
            assert unrelated not in compare
            cases.append({**shared, 'case': 'type-other-change', 'candidate_image_sha256': unrelated,
                          'genuine_capture_id': None, 'kind': 'offline_comparison_with_a_different_screen',
                          'evaluation_axis': 'changed_pixels_without_visible_typed_text'})
            compare.add(unrelated)
        for key in compare:
            img = (ARCHIVE / (key + '.png')).read_bytes()
            assert sha(img) == key
            images['images/' + key + '.png'] = img

    model = read(PACKAGE / 'service-config.json')
    identity_p = PACKAGE / 'flash-identity.json'
    identity = read(identity_p)
    assert model['revision'] == identity['revision'] == REVISION
    assert sha(identity_p.read_bytes()) == model['stable_identity_sha256']
    assert identity['checkpoint'] == model['model_dir']
    inputs = {'config.json', 'joint_config.json', 'decision_config.json', 'processor_config.json',
              'chat_template.jinja', 'tokenizer.json', 'tokenizer_config.json'}
    meta = {r['file']: r['sha256'] for r in identity['files']
            if r['file'] in inputs or r['file'].startswith('source/src/pplx_decider/')}
    assert inputs <= meta.keys() and len(cases) == 8 and len(images) == 7
    plan = {'revision': REVISION, 'checkpoint': model['model_dir'], 'pinned_source_sha256': meta,
            'source_run': RUN_ID, 'source_audit': str(source), 'source_audit_seal_sha256': sha((source / 'seal.json').read_bytes()),
            'source_verified_members': {key: seal[key] for key in required}, 'cases': cases,
            'quality_gate_unchanged': True, 'scope': 'New isolated CPU input preflight; no inference or GUI'}
    files = {**images, 'plan.json': dump(plan), 'cpu_native.py': (HERE / 'cpu_native.py').read_bytes(),
             'temporal_request.py': (HERE / 'temporal_request.py').read_bytes()}
    return model['python'], files


def main():
    python, files = freeze()
    name = f'cpu-probe-{time.time_ns()}'
    home = HERE / 'attempts' / name
    home.mkdir(exist_ok=False, parents=True)
    remote = '/data/researcher/jev-temporal-gate-20261122/' + name
    (home / 'plan.json').write_bytes(files['plan.json'])
    (home / 'remote-root.txt').write_text(remote + '\n', encoding='ascii')
    (home / 'input-manifest.json').write_bytes(dump({k: sha(v) for k, v in files.items()}))
    print(name, 'frozen plan', sha(files['plan.json']), flush=True)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w') as tar:
        for k, v in files.items():
            entry = tarfile.TarInfo(k)
            entry.size, entry.mode = len(v), 0o600
            tar.addfile(entry, io.BytesIO(v))
    command = (f'umask 077; mkdir -p /data/researcher/jev-temporal-gate-20261122 && mkdir {remote} '
               f'&& tar -xf - -C {remote} && cd {remote} '
               f'&& {shlex.quote(python)} -B -u cpu_native.py > cpu-result.json 2> cpu-stderr.log; '
               'result=$?; if [ "$result" -ne 0 ]; then cat cpu-stderr.log >&2; exit "$result"; fi; cat cpu-result.json')
    try:
        p = subprocess.run(SSH + [command], input=buf.getvalue(), capture_output=True, timeout=100)
        (home / 'stdout.json').write_bytes(p.stdout)
        (home / 'stderr.log').write_bytes(p.stderr)
        if p.returncode:
            print(p.stderr.decode('utf-8', errors='replace'), flush=True)
            raise SystemExit(p.returncode)
        result = json.loads(p.stdout)
        assert result['status'] == 'passed' and result['plan_sha256'] == sha(files['plan.json'])
        ranges = [r['input_tokens'] for r in result['rows']]
        assert len(ranges) == 8 and result['new_model_calls'] == result['GPU_allocations'] == result['GUI_calls'] == 0
        print('Native CPU input passed:', len(ranges), 'cases encoded,', min(ranges), 'to', max(ranges), 'input tokens, 0 model calls')
    except subprocess.TimeoutExpired as error:
        (home / 'stdout.json').write_bytes(error.stdout or b'')
        (home / 'stderr.log').write_bytes(error.stderr or b'')
        raise
    finally:
        (home / 'seal.json').write_bytes(dump({p.name: sha(p.read_bytes()) for p in sorted(home.iterdir()) if p.is_file()}))


if __name__ == '__main__':
    main()
