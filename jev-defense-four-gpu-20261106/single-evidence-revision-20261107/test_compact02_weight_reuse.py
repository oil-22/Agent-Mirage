"""Small CPU-only admission attacks; no actual weights/model/GPU/network."""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import traceback
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('compact02_worker', HERE / 'native_image_gpu_preflight_compact02.py')
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    Path(path).write_bytes(json.dumps(value, sort_keys=True).encode() + b'\n')


def file_sha(path):
    return digest(Path(path).read_bytes())


class Fixture:
    def __init__(self, root):
        self.root = root
        self.model = root / 'small-cpu-model'
        self.source = root / 'first-completed-proof'
        self.output = root / 'output'
        for path in [self.model, self.source / 'worker', self.output]:
            path.mkdir(parents=True)
        self.weights = []
        self.previous = []
        old = {'files': {}}
        self.api = {'id': worker.BASE_REPO, 'sha': worker.BASE_REVISION, 'siblings': []}
        for i in range(1, 5):
            name = 'model.safetensors-%05d-of-00004.safetensors' % i
            raw = ('CPU fixture shard %d only' % i).encode()
            path = self.model / name
            path.write_bytes(raw)
            row = {'filename': name, 'bytes': len(raw), 'sha256': digest(raw)}
            stat = path.stat()
            self.weights.append(row)
            self.previous.append(dict(row, current_sha256=row['sha256'], mtime_ns=stat.st_mtime_ns, inode=stat.st_ino))
            old['files']['Qwen3.5-9B/' + name] = {'bytes': len(raw), 'sha256': digest(raw)}
            self.api['siblings'].append({'rfilename': name, 'lfs': {'size': len(raw), 'sha256': digest(raw)}})
        names = ['chat_template.jinja', 'config.json', 'merges.txt', 'model.safetensors.index.json',
                 'preprocessor_config.json', 'tokenizer.json', 'tokenizer_config.json',
                 'video_preprocessor_config.json', 'vocab.json']
        self.metadata = []
        for name in names:
            raw = (json.dumps({'weight_map': {str(i): r['filename'] for i, r in enumerate(self.weights)}}).encode()
                   if name == 'model.safetensors.index.json' else ('CPU small metadata ' + name).encode())
            (self.model / name).write_bytes(raw)
            self.metadata.append({'filename': name, 'bytes': len(raw), 'sha256': digest(raw)})
        (self.model / 'README.md').write_text('CPU fixtures only', encoding='utf-8')
        self.old_path = root / 'historical.json'
        self.old = old
        self.api_path = root / 'official.json'
        dump(self.old_path, old)
        dump(self.api_path, self.api)
        self.proof = {'complete_current_shards': self.previous, 'metadata': self.metadata,
                      'official_LFS_current_shard_identity_verified': True,
                      'official_pinned_base_api_sha256': file_sha(self.api_path)}
        self.terminal = {'status': 'completed_four_first_attempts', 'error': None,
                         'attempted_request_ids': ['S01', 'S07', 'S13', 'S25'],
                         'attempted_requests': 4, 'completed_requests': 4,
                         'failed_incomplete_requests': 0, 'unattempted': 0}
        self.exited = {'worker_exit_code': 0, 'launcher_exit_code': 0}
        self.m = {'weight_files': copy.deepcopy(self.weights), 'metadata_files': copy.deepcopy(self.metadata),
                  'prior_weight_identity': {'path': str(self.old_path), 'sha256': file_sha(self.old_path)},
                  'official_base_api': {'path': str(self.api_path), 'sha256': file_sha(self.api_path)}}
        self.events = []
        self.journal = type('Journal', (), {'append': lambda _s, kind, value: self.events.append((kind, value))})()
        self.reseal()

    def reseal(self, seal_change=None, outer_change=None):
        dump(self.source / 'worker/current-weight-identity.json', self.proof)
        dump(self.source / 'worker/terminal.json', self.terminal)
        dump(self.source / 'exit.json', self.exited)
        identity_sha = file_sha(self.source / 'worker/current-weight-identity.json')
        terminal_sha = file_sha(self.source / 'worker/terminal.json')
        seal = {'files': [{'path': 'current-weight-identity.json', 'sha256': identity_sha},
                          {'path': 'terminal.json', 'sha256': terminal_sha}]}
        if seal_change:
            seal_change(seal)
        dump(self.source / 'worker/seal.json', seal)
        seal_sha = file_sha(self.source / 'worker/seal.json')
        outer = {'worker/seal.json': seal_sha, 'worker/current-weight-identity.json': identity_sha,
                 'worker/terminal.json': terminal_sha, 'exit.json': file_sha(self.source / 'exit.json')}
        if outer_change:
            outer_change(outer)
        dump(self.source / 'terminal-manifest.json', outer)
        self.m['current_weight_identity_reuse'] = {
            'identity_path': str(self.source / 'worker/current-weight-identity.json'), 'identity_sha256': identity_sha,
            'worker_seal_path': str(self.source / 'worker/seal.json'), 'worker_seal_sha256': seal_sha,
            'terminal_manifest_path': str(self.source / 'terminal-manifest.json'),
            'terminal_manifest_sha256': file_sha(self.source / 'terminal-manifest.json')}

    def api_update(self):
        dump(self.api_path, self.api)
        self.m['official_base_api']['sha256'] = file_sha(self.api_path)
        self.proof['official_pinned_base_api_sha256'] = file_sha(self.api_path)
        self.reseal()

    def old_update(self):
        dump(self.old_path, self.old)
        self.m['prior_weight_identity']['sha256'] = file_sha(self.old_path)


def execute(f):
    original_open = Path.open
    reads = []
    def guarded_open(path, *args, **kwargs):
        if path.suffix == '.safetensors':
            reads.append(str(path))
            raise AssertionError('Identity check attempted to open a shard')
        return original_open(path, *args, **kwargs)
    with patch.object(worker, 'MODEL_PATH', str(f.model)), patch.object(worker, 'WEIGHT_REUSE_SOURCE_ROOT', str(f.source)), patch.object(Path, 'open', guarded_open):
        result = worker.current_weight_identity(f.m, f.output, f.journal)
    assert not reads
    assert len(result) == 4 and len(f.events) == 4
    receipt = json.loads((f.output / 'current-weight-identity.json').read_bytes())
    assert receipt['weight_bytes_read_by_identity_check'] == 0
    assert receipt['fresh_full_weight_hash_performed'] is False
    assert receipt['after_load_stat_gate_required'] is True
    return result


def replace_inode(f):
    path = f.model / f.weights[0]['filename']
    original = path.stat()
    replacement = f.model / 'replacement.tmp'
    replacement.write_bytes(b'x' * original.st_size)
    os.utime(replacement, ns=(original.st_atime_ns, original.st_mtime_ns))
    replacement.replace(path)
    assert path.stat().st_ino != original.st_ino


def unstable_stat(f):
    original = Path.stat
    target = f.model / f.weights[0]['filename']
    observed = []
    def changing(path, *args, **kwargs):
        value = original(path, *args, **kwargs)
        if path == target:
            observed.append(1)
            if len(observed) >= 3:  # inventory is_file(), then two admission stats
                proxy = type('ChangedStat', (), {})()
                for field in ['st_size', 'st_mtime_ns', 'st_ino', 'st_mode']:
                    setattr(proxy, field, getattr(value, field))
                proxy.st_mtime_ns += 1
                return proxy
        return value
    with patch.object(Path, 'stat', changing):
        execute(f)


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    def case(name, mutate=None, error=None, custom=None):
        f = Fixture(output / ('case-%02d' % len(cases)))
        try:
            if mutate:
                mutate(f)
            (custom or execute)(f)
            if error:
                raise AssertionError('Mutation was unexpectedly admitted: ' + name)
            cases.append({'case': name, 'passed': True, 'outcome': 'admitted_without_shard_read'})
        except ValueError as exc:
            if not error or error not in str(exc):
                raise
            cases.append({'case': name, 'passed': True, 'outcome': 'rejected', 'reason': str(exc)})
    case('valid_reuse_never_opens_shard')
    case('reuse_unknown_field', lambda f: f.m['current_weight_identity_reuse'].update(extra=1), 'six-field')
    case('wrong_original_namespace', lambda f: f.m['current_weight_identity_reuse'].update(identity_path=str(f.root / 'other.json')), 'first completed')
    for label, relative in [('identity', 'worker/current-weight-identity.json'), ('seal', 'worker/seal.json'), ('outer', 'terminal-manifest.json')]:
        case('tampered_' + label, lambda f, rel=relative: (f.source / rel).write_bytes(b'{}\n'), 'Immutable proof changed')
    case('outer_wrong_identity', lambda f: f.reseal(outer_change=lambda x: x.update({'worker/current-weight-identity.json': '0' * 64})), 'Outer terminal')
    case('outer_wrong_worker_seal', lambda f: f.reseal(outer_change=lambda x: x.update({'worker/seal.json': '0' * 64})), 'Outer terminal')
    case('missing_identity_in_worker_seal', lambda f: f.reseal(seal_change=lambda x: x['files'].pop(0)), 'does not bind identity')
    case('worker_seal_wrong_terminal', lambda f: f.reseal(seal_change=lambda x: x['files'][1].update(sha256='0' * 64)), 'does not bind identity')
    case('worker_seal_duplicate_identity', lambda f: f.reseal(seal_change=lambda x: x['files'].append(copy.deepcopy(x['files'][0]))), 'duplicate entries')
    for label, update in [('failed_terminal', {'status': 'failed'}), ('terminal_error', {'error': {'reason': 'failed'}}),
                          ('incomplete_terminal', {'completed_requests': 3}), ('wrong_source_ids', {'attempted_request_ids': ['S04', 'S10', 'S16', 'S19']})]:
        def mutate(f, change=update):
            f.terminal.update(change)
            f.reseal()
        case(label, mutate, 'fully completed')
    for key in ['worker_exit_code', 'launcher_exit_code']:
        def mutate(f, key=key):
            f.exited[key] = 1
            f.reseal()
        case('nonzero_' + key, mutate, 'fully completed')
    def proof_update(key, value):
        def mutate(f):
            f.proof[key] = value
            f.reseal()
        return mutate
    case('unverified_original_official_identity', proof_update('official_LFS_current_shard_identity_verified', False), 'lacks the same official')
    case('different_original_official_API', proof_update('official_pinned_base_api_sha256', '0' * 64), 'lacks the same official')
    def wrong_revision(f):
        f.api['sha'] = 'wrong-revision'
        f.api_update()
    case('wrong_official_revision', wrong_revision, 'frozen base revision')
    def wrong_lfs(f):
        f.api['siblings'][0]['lfs']['sha256'] = '0' * 64
        f.api_update()
    case('official_LFS_hash_disagreement', wrong_lfs, 'Reused SHA identity differs')
    def wrong_historical(f):
        next(iter(f.old['files'].values()))['sha256'] = '0' * 64
        f.old_update()
    case('historical_hash_disagreement', wrong_historical, 'Reused SHA identity differs')
    def original_hash(f):
        f.previous[0]['current_sha256'] = '0' * 64
        f.reseal()
    case('original_current_hash_disagreement', original_hash, 'Reused SHA identity differs')
    case('missing_shard', lambda f: f.m['weight_files'].pop(), 'four unique')
    case('duplicate_shard', lambda f: f.m['weight_files'].__setitem__(1, copy.deepcopy(f.m['weight_files'][0])), 'four unique')
    def duplicate_proof(f):
        f.previous[1] = copy.deepcopy(f.previous[0])
        f.reseal()
    case('duplicate_original_shard', duplicate_proof, 'four unique')
    case('changed_size', lambda f: (f.model / f.weights[0]['filename']).write_bytes(b'different'), 'stat continuity')
    def mtime(f):
        path = f.model / f.weights[0]['filename']
        value = path.stat()
        os.utime(path, ns=(value.st_atime_ns, value.st_mtime_ns + 10000000))
    case('mtime_only_change', mtime, 'stat continuity')
    case('same_size_mtime_replaced_inode', replace_inode, 'stat continuity')
    case('stat_unstable_across_admission_reads', error='stat continuity', custom=unstable_stat)
    case('current_metadata_tamper', lambda f: (f.model / f.metadata[0]['filename']).write_bytes(b'tampered'), 'metadata mismatch')
    case('missing_native_metadata', lambda f: f.m['metadata_files'].pop(), 'nine unique')
    case('extra_generation_defaults', lambda f: (f.model / 'generation_config.json').write_bytes(b'{}'), 'file set changed')
    def index_change(f):
        path = f.model / 'model.safetensors.index.json'
        dump(path, {'weight_map': {'0': f.weights[0]['filename']}})
        row = next(x for x in f.metadata if x['filename'] == path.name)
        row.update(bytes=path.stat().st_size, sha256=file_sha(path))
        f.m['metadata_files'] = copy.deepcopy(f.metadata)
        f.reseal()
    case('index_missing_three_shards', index_change, 'inventories differ')
    def stop_marker(f):
        (f.output.parent / 'stop-requested.json').write_bytes(b'{}')
        try:
            execute(f)
        except RuntimeError as exc:
            assert 'Requested stop marker' in str(exc)
            return
        raise AssertionError('Stop marker did not prevent shard admission')
    case('stop_marker_before_shard_admission', custom=stop_marker)
    old = ast.parse((HERE / 'native_image_gpu_preflight.py').read_text(encoding='utf-8'))
    new = ast.parse((HERE / 'native_image_gpu_preflight_compact02.py').read_text(encoding='utf-8'))
    functions = lambda tree: {x.name: ast.dump(x, include_attributes=False) for x in tree.body if isinstance(x, (ast.FunctionDef, ast.ClassDef))}
    prior, current = functions(old), functions(new)
    changed = [name for name in prior if prior[name] != current[name]]
    assert changed == ['validate_manifest', 'current_weight_identity']
    assert prior['run'] == current['run']
    report = {'status': 'completed_CPU_weight_reuse_boundaries', 'cases': cases, 'passed': len(cases),
              'failed': 0, 'model_GPU_network_requests': 0, 'actual_deployed_weight_bytes_read': 0,
              'CPU_fixture_only': True, 'fixture_shard_content_reads_during_identity_check': 0,
              'changed_function_ASTs': changed, 'run_AST_unchanged': True,
              'worker_sha256': file_sha(HERE / 'native_image_gpu_preflight_compact02.py')}
    dump(output / 'report.json', report)
    for filename in ['native_image_gpu_preflight_compact02.py', 'test_compact02_weight_reuse.py', 'prepare_compact_gpu_worker02.py']:
        (output / filename).write_bytes((HERE / filename).read_bytes())
    dump(output / 'seal.json', {str(p.relative_to(output)): file_sha(p) for p in sorted(output.rglob('*')) if p.is_file()})
    print(json.dumps({'passed': len(cases), 'worker_sha256': report['worker_sha256'], 'seal_sha256': file_sha(output / 'seal.json')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args.output)
    except BaseException:
        if args.output.is_dir():
            dump(args.output / 'failure.json', {'traceback': traceback.format_exc(), 'model_GPU_network_requests': 0})
            dump(args.output / 'failure-seal.json', {str(p.relative_to(args.output)): file_sha(p) for p in sorted(args.output.rglob('*')) if p.is_file()})
        raise
