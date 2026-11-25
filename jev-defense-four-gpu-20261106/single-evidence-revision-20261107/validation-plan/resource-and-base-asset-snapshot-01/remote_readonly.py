"""Read-only remote base asset and GPU evidence; no model imports or remote writes."""
import os
import sys
import json
import time
import hashlib
import pathlib
import subprocess

HOST_ALIAS = 'HOST_ALIAS_PLACEHOLDER'

def digest(path):
    h = hashlib.sha256()
    with open(str(path), 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def small_json(path):
    with open(str(path), encoding='utf-8') as stream:
        return json.load(stream)


def stat_file(path, hash_small=False):
    p = pathlib.Path(path)
    before = p.stat()
    out = {'path': str(p), 'realpath': os.path.realpath(str(p)), 'bytes': before.st_size,
           'mtime_ns': before.st_mtime_ns, 'inode': before.st_ino, 'device': before.st_dev,
           'is_symlink': p.is_symlink()}
    if hash_small and before.st_size <= 40 * 1024 * 1024:
        out['sha256'] = digest(p)
    after = p.stat()
    out['stable_during_read'] = (before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino)
    return out


def proc(pid, with_fds=False):
    d = pathlib.Path('/proc') / str(pid)
    try:
        stat = (d / 'stat').read_text()
        suffix = stat[stat.rfind(')') + 2:].split()
        status = (d / 'status').read_text().splitlines()
        uid = next(x for x in status if x.startswith('Uid:')).split()[1:]
        out = {'pid': int(pid), 'uid_fields': [int(x) for x in uid], 'state': suffix[0],
               'start_ticks': int(suffix[19]), 'full_command': (d / 'cmdline').read_bytes().replace(b'\x00', b' ').decode(errors='replace').strip(),
               'exe': os.readlink(str(d / 'exe'))}
        if with_fds:
            out['lock_fds'] = []
            for f in (d / 'fd').iterdir():
                try:
                    target = os.readlink(str(f))
                    info = (d / 'fdinfo' / f.name).read_text()
                    held = [line for line in info.splitlines() if line.startswith('lock:')]
                    if held:
                        out['lock_fds'].append({'fd': int(f.name), 'target': target, 'fdinfo_held_locks': held,
                                                'target_stat': stat_file(f)})
                except (OSError, IOError) as exc:
                    out.setdefault('fd_read_errors', []).append({'fd': f.name, 'error_type': type(exc).__name__})
            out['actual_held_lock_FD_count'] = len(out['lock_fds'])
        return out
    except (OSError, IOError, ValueError, StopIteration) as exc:
        return {'pid': int(pid), 'actual_proc_read_failed': type(exc).__name__, 'detail': str(exc)}


def command(argv):
    p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=20)
    return {'argv': argv, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}


result = {'snapshot_time_unix': time.time(), 'hostname': os.uname().nodename, 'effective_uid': os.geteuid(),
          'read_only': True, 'model_imports': False, 'model_GUI_health_calls': 0,
          'GPU_lock_acquisitions': 0, 'remote_files_written': 0,
          'large_weight_bytes_hashed': 0, 'asset_roots': [], 'receipt_candidates': []}

model_paths = [
    '/home/researcher/models/Qwen3.5-9B', '/data/researcher/models/Qwen3.5-9B',
    '/opt/whz/llms/Qwen3.5-9B', '/opt/whz/models/Qwen3.5-9B',
    '/home/researcher/.cache/huggingface/hub/models--Qwen--Qwen3.5-9B/snapshots/c202236235762e1c871ad0ccb60c8ee5ba337b9a',
    '/data/researcher/.cache/huggingface/hub/models--Qwen--Qwen3.5-9B/snapshots/c202236235762e1c871ad0ccb60c8ee5ba337b9a',
]
for name in model_paths:
    p = pathlib.Path(name)
    row = {'path': name, 'exists': p.exists()}
    if p.is_dir():
        row['realpath'] = os.path.realpath(name)
        row['files'] = []
        for f in sorted(p.iterdir()):
            if f.is_file():
                is_weight = f.name.endswith(('.safetensors', '.bin', '.pt', '.pth', '.gguf'))
                row['files'].append(stat_file(f, hash_small=not is_weight))
        config = p / 'config.json'
        if config.is_file():
            d = small_json(config)
            row['config_summary'] = {k: d.get(k) for k in ['architectures', 'model_type', '_name_or_path', '_commit_hash', 'torch_dtype', 'dtype']}
            text = d.get('text_config', d)
            row['text_config_summary'] = {k: text.get(k) for k in ['num_hidden_layers', 'num_attention_heads', 'hidden_size', 'head_dim', 'dtype', 'torch_dtype', 'max_position_embeddings']}
        index = p / 'model.safetensors.index.json'
        if index.is_file():
            d = small_json(index)
            shards = sorted(set(d.get('weight_map', {}).values()))
            row['weight_index_summary'] = {'metadata': d.get('metadata'), 'shard_names': shards,
                                           'all_declared_shards_exist': all((p / x).is_file() for x in shards)}
        mdroot = p / '.cache/huggingface/download'
        if mdroot.is_dir():
            row['download_metadata'] = []
            for f in sorted(mdroot.glob('*.metadata')):
                if f.stat().st_size < 4096:
                    row['download_metadata'].append({'file': stat_file(f, hash_small=True), 'lines': f.read_text().splitlines()})
    result['asset_roots'].append(row)

scan_roots = []  # Existing identity receipts are already local; do not rescan old experiment trees.
for root in scan_roots:
    if not os.path.isdir(root):
        continue
    for here, dirs, files in os.walk(root):
        rel = os.path.relpath(here, root)
        depth = 0 if rel == '.' else len(rel.split(os.sep))
        dirs[:] = [x for x in dirs if x not in ['.git', '__pycache__', 'images', 'assets', 'raw', 'logits', 'tokens', 'requests', 'replies', 'captures']]
        if depth >= 3:
            dirs[:] = []
        for name in files:
            low = name.lower()
            selected = ('identity' in low or 'weight' in low) and low.endswith(('.json', '.md'))
            selected = selected or low in ['qwen9-scale-current.json', 'qwen9-scale-finalization.json', 'qwen9-preflight.json', 'runtime.json']
            if not selected:
                continue
            f = pathlib.Path(here) / name
            if f.stat().st_size > 4 * 1024 * 1024:
                continue
            row = stat_file(f, hash_small=True)
            if low.endswith('.json'):
                try:
                    d = small_json(f)
                    row['json_top_keys'] = list(d)[:40] if isinstance(d, dict) else None
                    row['small_public_identity_content'] = d if ('identity' in low or 'weight' in low or low == 'runtime.json') else None
                    if row['small_public_identity_content'] is None and isinstance(d, dict):
                        row['selected_public_fields'] = {k: v for k, v in d.items() if any(s in k.lower() for s in ['root', 'identity', 'model', 'receipt', 'revision', 'sha256']) and not any(s in k.lower() for s in ['token', 'auth', 'secret'])}
                except (ValueError, OSError) as exc:
                    row['json_error'] = type(exc).__name__
            result['receipt_candidates'].append(row)
            if len(result['receipt_candidates']) >= 240:
                result['receipt_scan_truncated_at'] = 240
                break
        if result.get('receipt_scan_truncated_at'):
            break
    if result.get('receipt_scan_truncated_at'):
        break

result['cpu_environment_metadata'] = []
env_paths = ['/opt/whz/conda-envs/webmall-vlm/bin/python', '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python']
result['environment_directory_names'] = {}
for env_root in ['/opt/whz/conda-envs', '/data/researcher/venvs', '/home/researcher/venvs']:
    if os.path.isdir(env_root):
        names = sorted(os.listdir(env_root))
        result['environment_directory_names'][env_root] = names
        for name in names:
            if any(x in name.lower() for x in ['flash', 'jev']):
                env_paths.append(os.path.join(env_root, name, 'bin/python'))
env_code = "import sys,json,importlib.metadata as m; names=['transformers','torch','tokenizers','pillow','numpy','accelerate','safetensors','vllm']; out={'executable':sys.executable,'version':sys.version,'versions':{}}; " \
           "exec('for n in names:\\n try: out[\"versions\"][n]=m.version(n)\\n except m.PackageNotFoundError: out[\"versions\"][n]=None'); print(json.dumps(out))"
for python_path in sorted(set(env_paths)):
    if os.path.isfile(python_path):
        row = {'python': stat_file(python_path), 'metadata_only_no_model_import': True}
        try:
            row['version_metadata_command'] = command([python_path, '-B', '-c', env_code])
        except Exception as exc:
            row['error'] = type(exc).__name__ + ': ' + str(exc)
        result['cpu_environment_metadata'].append(row)

if HOST_ALIAS in ['3090', '4090']:
    result['GPU_inventory'] = command(['nvidia-smi', '--query-gpu=index,uuid,name,memory.total,memory.used,memory.free', '--format=csv,noheader,nounits'])
    result['compute_inventory'] = command(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid,process_name,used_memory', '--format=csv,noheader,nounits'])
    pids = []
    for line in result['compute_inventory']['stdout'].splitlines():
        fields = [x.strip() for x in line.split(',')]
        if len(fields) > 1 and fields[1].isdigit():
            pids.append(int(fields[1]))
    result['actual_compute_processes'] = [proc(pid) for pid in sorted(set(pids))]
    if HOST_ALIAS == '3090':
        result['requested_holder_actual_identity_and_locks'] = proc(2568295, with_fds=True)
        try:
            result['proc_locks_holder_lines'] = [x for x in pathlib.Path('/proc/locks').read_text().splitlines() if ' 2568295 ' in x]
        except (OSError, IOError) as exc:
            result['proc_locks_error'] = type(exc).__name__

result['snapshot_completed_unix'] = time.time()
print(json.dumps(result, ensure_ascii=False, indent=2))
