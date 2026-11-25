"""One offline eight-case Flash probe, with a fresh exclusive GPU lease. No GUI or server."""

import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'run'
DEVICE = 7
HELD = []  # Keep the leases through CUDA process exit, even on a failure.


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def hash_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('xb') as handle:
        handle.write(canonical(value) + b'\n')


def load(path):
    return json.loads(path.read_bytes())


def card(uuid=None):
    args = ['nvidia-smi', '-i', uuid or str(DEVICE), '--format=csv,noheader,nounits']
    fields = subprocess.check_output(args + ['--query-gpu=index,uuid,memory.free'], text=True, timeout=20).strip().split(', ')
    index, identity, free = int(fields[0]), fields[1], int(fields[2])
    assert index == DEVICE and (uuid is None or identity == uuid)
    apps = subprocess.check_output(args + ['--query-compute-apps=gpu_uuid,pid,used_gpu_memory'], text=True, timeout=20)
    compute = []
    for line in apps.splitlines():
        if line.strip():
            current, pid, memory = line.strip().split(', ')
            assert current == identity
            compute.append({'pid': int(pid), 'mib': int(memory)})
    return {'index': index, 'uuid': identity, 'free_mib': free, 'compute': compute, 'at': time.time()}


def check_gpu(snapshot, loaded):
    assert {r['pid'] for r in snapshot['compute']} == ({os.getpid()} if loaded else set()), 'Unexpected compute on GPU 7'
    if not loaded:
        assert snapshot['free_mib'] >= 23000, 'This probe requires 23000 MiB of exclusive free memory'


def closure():
    from resource_guard import identity, sha

    terminal = load(OUT / 'terminal.json')
    proof = load(OUT / 'lease.json') if (OUT / 'lease.json').is_file() else None
    released = []
    if proof:
        owner = proof['process']
        try:
            now = identity(owner['pid'])
        except FileNotFoundError:
            now = {}
        assert (now.get('start_ticks'), now.get('uid'), now.get('command')) != (owner['start_ticks'], owner['uid'], owner['command'])
        after = card(proof['uuid'])
        assert owner['pid'] not in {r['pid'] for r in after['compute']}
        for entry in proof['locks']:
            with Path(entry['path']).open('rb') as fd:
                assert os.fstat(fd.fileno()).st_ino == entry['inode']
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(fd, fcntl.LOCK_UN)
            released.append(entry['path'])
    manifest = {p.relative_to(OUT).as_posix(): sha(p) for p in OUT.rglob('*') if p.is_file()}
    row = {'terminal': terminal, 'sealed_members': manifest, 'released_locks': released,
           'lease_process_exited': proof is not None, 'postexit_gpu': after if proof else None}
    save(ROOT / 'postexit-audit.json', row)
    return row


def probe():
    from resource_guard import checkpoint, identity, sha

    assert os.getuid() == 1033
    frozen = load(ROOT / 'manifest.json')
    for name, expected in frozen['files'].items():
        assert sha(ROOT / name) == expected, name
    assert frozen['max_new_native_calls'] == 8 and frozen['retries'] == 0
    OUT.mkdir(exist_ok=False)
    attempted, replies, error, peaks = 0, [], None, []
    try:
        plan, cpu, config = [load(ROOT / name) for name in ('plan.json', 'cpu-prepared.json', 'service-config.json')]
        assert config['physical_gpu'] == DEVICE and len(plan['cases']) == 8
        assert cpu['plan_sha256'] == sha(ROOT / 'plan.json') and cpu['new_model_calls'] == 0 and cpu['status'] == 'passed'
        assert config['revision'] == cpu['revision'] == plan['revision'] and config['model_dir'] == plan['checkpoint']
        cpu_rows = {r['case']: r for r in cpu['rows']}
        before = card(); check_gpu(before, False); gpu_uuid = before['uuid']
        paths = (Path('/home/researcher/.mirage-resource-locks') / (gpu_uuid + '.lock'),
                 Path('/home/researcher/defense-resume-20261102-retry2/resource-locks') / (gpu_uuid + '.lock'),
                 Path('/home/researcher/jev-defense-four-gpu-20261106/inference.lock'))
        locks = []
        for path in sorted(paths):
            handle = path.open('a'); HELD.append(handle)
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locks.append({'path': str(path), 'file_descriptor': handle.fileno(), 'inode': os.fstat(handle.fileno()).st_ino})
        owner = identity(os.getpid())

        def verify_ownership(loaded):
            for entry in locks:
                fd = entry['file_descriptor']
                assert os.fstat(fd).st_ino == entry['inode'] and os.readlink(f'/proc/self/fd/{fd}') == entry['path']
                assert f'WRITE {owner["pid"]}' in Path(f'/proc/self/fdinfo/{fd}').read_text()
            snapshot = card(gpu_uuid)
            check_gpu(snapshot, loaded)
            return snapshot

        after = verify_ownership(False)
        save(OUT / 'lease.json', {'process': owner, 'locks': locks, 'uuid': gpu_uuid, 'before': before, 'after': after})
        old_identity = checkpoint(config, ROOT)
        save(OUT / 'checkpoint-before.json', old_identity)
        os.environ.update(CUDA_VISIBLE_DEVICES=gpu_uuid, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
        import torch
        import transformers
        from temporal_request import QUESTION_ID, native_request

        assert torch.__version__ == cpu['torch'] and transformers.__version__ == cpu['transformers']
        assert torch.cuda.device_count() == 1
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        model = Path(config['model_dir'])
        sys.path.insert(0, str(model / 'source/src'))
        from pplx_decider import Decider
        from pplx_decider import model as module

        assert Path(module.__file__).resolve() == model / 'source/src/pplx_decider/model.py'
        started = time.monotonic()
        engine = Decider.from_pretrained(model, device='cuda:0', fast=False, cpu_threads=4)
        torch.cuda.synchronize()
        actual_load = time.monotonic() - started
        for m in (engine.backbone, engine.readout):
            assert all(str(v.device) == 'cuda:0' for v in [*m.parameters(), *m.buffers()])
            assert all(v.dtype == torch.bfloat16 for v in m.parameters() if v.is_floating_point())
        save(OUT / 'loaded.json', {'load_seconds': actual_load, 'revision': config['revision'], 'BF16': True,
                                  'native_sdpa': True, 'owned_compute': verify_ownership(True)})

        def tensor(v):
            cpu_tensor = v.detach().cpu().contiguous()
            return {'shape': list(cpu_tensor.shape), 'dtype': str(cpu_tensor.dtype),
                    'sha256': hash_bytes(cpu_tensor.view(torch.uint8).numpy().tobytes())}

        for row in plan['cases']:
            key = row['case']
            expected = cpu_rows[key]
            ids = [row['previous_image_sha256'], row['candidate_image_sha256']]
            pngs = [(ROOT / 'images' / (name + '.png')).read_bytes() for name in ids]
            assert [hash_bytes(raw) for raw in pngs] == ids == expected['ordered_images']
            request = native_request(pngs[0], row['executed_action'], pngs[1])
            assert hash_bytes(canonical(request)) == expected['native_request_sha256']
            trace, readout = [], []

            def pre(_module, _args, kwargs):
                assert kwargs.get('past_key_values') is None and kwargs.get('use_cache') is False
                actual = {k: tensor(v) for k, v in kwargs.items() if isinstance(v, torch.Tensor)}
                assert actual == expected['forward_inputs_if_run'], key
                trace.append(actual)

            def post(_module, _args, value):
                readout.append(value.detach().float().cpu().tolist())

            before_call = verify_ownership(True)
            start = time.monotonic()
            attempted += 1
            save(OUT / (key + '-start.json'), {'case': key, 'request_sha256': expected['native_request_sha256'],
                                             'owned_compute': before_call, 'call_number': attempted})
            h1 = engine.backbone.register_forward_pre_hook(pre, with_kwargs=True)
            h2 = engine.readout.register_forward_hook(post)
            torch.cuda.reset_peak_memory_stats()
            try:
                result = engine.decide(request)
                torch.cuda.synchronize()
            finally:
                h1.remove(); h2.remove()
                save(OUT / (key + '-native.json'), {'forward': trace, 'raw_readout': readout, 'no_kv': True})
            elapsed = time.monotonic() - start
            assert len(trace) == len(readout) == 1 and len(readout[0]) == 1
            assert result['usage'] == {'input_tokens': expected['input_tokens'], 'output_tokens': 0, 'sequences': 1}
            answer = result['answers'][QUESTION_ID]
            prob = answer['probabilities']
            assert set(prob) == {'YES', 'NO'} and math.isclose(sum(prob.values()), 1.0, abs_tol=1e-7)
            assert answer['choice'] == max(prob, key=prob.__getitem__)
            resource = verify_ownership(True)
            peak = torch.cuda.max_memory_allocated()
            peaks.append(peak)
            reply = {'case': key, 'request_sha256': expected['native_request_sha256'], 'images': ids,
                     'choice': answer['choice'], 'probabilities': prob, 'native_result': result,
                     'seconds_with_trace': elapsed, 'peak_allocated_bytes': peak, 'owned_compute_after': resource}
            save(OUT / (key + '-reply.json'), reply)
            replies.append(reply)
            print(f'{len(replies)}/8', key, flush=True)
        assert checkpoint(config, ROOT) == old_identity and attempted == len(replies) == 8
    except Exception:
        error = traceback.format_exc()
        print(error, file=sys.stderr, flush=True)
    finally:
        save(OUT / 'terminal.json', {'status': 'completed' if error is None else 'technical_failure', 'error': error,
                                    'attempted': attempted, 'replies': replies, 'allowed': 8, 'retries': 0,
                                    'max_peak_allocated_bytes': max(peaks, default=None),
                                    'main_model_calls': 0, 'GUI_actions': 0, 'official_scores': 0})
    return 0 if error is None else 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--audit']:
        print(json.dumps(closure(), ensure_ascii=False, indent=2))
    elif len(sys.argv) == 1:
        raise SystemExit(probe())
    else:
        raise SystemExit('Unknown argument')
