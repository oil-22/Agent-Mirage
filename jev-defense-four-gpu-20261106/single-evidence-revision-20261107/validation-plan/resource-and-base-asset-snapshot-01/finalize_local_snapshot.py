"""Compare captured metadata with old receipts, without rehashing remote weights."""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
OLD = Path(r'D:\MultiModel\attention-audit-20261031')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_new(name, data):
    with (HERE / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


old_manifest = load(OLD / 'artifact-manifest.json')
old_bindings = []
for name in ['model-sha256-3090.json', 'model-sha256-4090.json', 'model-transfer-verification.json']:
    p = OLD / name
    expected = old_manifest['artifacts'].get(name)
    assert expected is not None, 'Historical artifact manifest must contain receipt ' + name
    assert expected['sha256'] == sha(p) and expected['bytes'] == p.stat().st_size
    old_bindings.append({'path': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size,
                         'old_artifact_manifest_hash_and_size_match': True})
tables = {host: load(OLD / ('model-sha256-' + host + '.json'))['files'] for host in ['3090', '4090']}
transfer = load(OLD / 'model-transfer-verification.json')
assert transfer['all_sizes_and_sha256_match'] is True
comparisons = []
for host, path in [('3090', '/home/researcher/models/Qwen3.5-9B'), ('4090', '/data/researcher/models/Qwen3.5-9B')]:
    snapshot = load(HERE / (host + '-readonly.json'))
    model = next(x for x in snapshot['asset_roots'] if x['path'] == path)
    current = {Path(x['path']).name: x for x in model['files']}
    old = {k.split('/', 1)[1]: v for k, v in tables[host].items() if k.startswith('Qwen3.5-9B/')}
    rows = []
    for name, previous in old.items():
        now = current.get(name)
        assert now is not None, name
        weight = name.endswith('.safetensors')
        match = now['bytes'] == previous['bytes'] and (weight or now.get('sha256') == previous['sha256'])
        assert match and now['stable_during_read']
        other = tables['4090' if host == '3090' else '3090']['Qwen3.5-9B/' + name]
        assert previous == other == transfer['files']['Qwen3.5-9B/' + name]
        rows.append({'name': name, 'bytes': now['bytes'], 'historical_sha256': previous['sha256'],
                     'current_sha256': None if weight else now['sha256'],
                     'current_stat': {k: now[k] for k in ['mtime_ns', 'inode', 'device', 'stable_during_read']},
                     'match_kind': 'size_and_stable_current_stat_only_no_fresh_weight_SHA' if weight else 'current_SHA_and_size_match_historical_receipt',
                     'historical_mtime_inode_stat_available': any(k in previous for k in ['mtime', 'mtime_ns', 'inode', 'device', 'stat'])})
    assert len(rows) == 14
    assert sum(x['name'].endswith('.safetensors') for x in rows) == 4
    assert sum(x['bytes'] for x in rows if x['name'].endswith('.safetensors')) == 19306310880
    comparisons.append({'host': host, 'reusable_complete_asset_path': path, 'files': rows,
                        'four_shard_bytes': 19306310880, 'index_tensor_total_size': 19306216416,
                        'current_full_weight_cryptographic_identity_reverified': False,
                        'historical_weight_stat_comparable_to_now': False,
                        'metadata_SHA_currently_matches_historical': True,
                        'downloaded_adapter_or_JEV_weights_claimed': False})
gpu = load(HERE / '3090-readonly.json')
holder = gpu['requested_holder_actual_identity_and_locks']
assert holder['uid_fields'] == [1033] * 4
assert holder['start_ticks'] == 1159211789
assert holder['actual_held_lock_FD_count'] == 9
assert 'resource_control.py --root /home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01 --worker' in holder['full_command']
assert gpu['compute_inventory']['returncode'] == 0 and gpu['compute_inventory']['stdout'].strip() == ''
target_gpus = []
for line in gpu['GPU_inventory']['stdout'].splitlines():
    fields = [x.strip() for x in line.split(',')]
    if int(fields[0]) in [4, 5, 6, 7]:
        target_gpus.append({'index': int(fields[0]), 'uuid': fields[1], 'name': fields[2],
                            'total_MiB': int(fields[3]), 'used_MiB': int(fields[4]), 'free_MiB': int(fields[5])})
assert len(target_gpus) == 4
report = {
    'created_utc': datetime.now(timezone.utc).isoformat(), 'type': 'read_only_resource_and_existing_base_asset_audit',
    'historical_receipts': old_bindings,
    'historical_artifact_manifest': {'path': str(OLD / 'artifact-manifest.json'), 'sha256': sha(OLD / 'artifact-manifest.json')},
    'asset_comparisons': comparisons,
    'incomplete_alternate_3090_path': {'path': '/opt/whz/llms/Qwen3.5-9B', 'top_level_files': 5,
                                       'has_all_declared_shards': False, 'do_not_use_as_complete_base': True},
    '3090_current_target_GPU_evidence': target_gpus,
    '3090_current_holder_identity': {k: holder[k] for k in ['pid', 'uid_fields', 'start_ticks', 'full_command', 'actual_held_lock_FD_count']},
    'target_compute_empty_at_snapshot': True,
    'four_GPU_reservation_released': False, 'snapshot_is_new_launch_permission': False,
    'CPU_environment_metadata_only': {
        '3090_python': '/opt/whz/conda-envs/webmall-vlm/bin/python',
        '4090_python': '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python',
        'common': {'python': '3.11.16', 'transformers': '5.15.1', 'torch': '2.5.1+cu121',
                   'tokenizers': '0.22.2', 'pillow': '12.3.0', 'numpy': '2.4.6', 'safetensors': '0.8.0', 'vllm': None},
        'accelerate': {'3090': '1.14.0', '4090': '1.15.0'},
        'processor_constructed': False, 'native_CPU_input_proof_completed': False,
        'shared_environment_installed_or_upgraded': False,
    },
    'scientific_limits': [
        'Existing receipts cryptographically bind historical copies of four weight shards, not current GPU tensors.',
        'Old receipts have only bytes and SHA256, no comparable historical mtime/inode/stat; current weights were not rehashed.',
        'Current metadata SHA and current size/stable stat support asset reuse preparation, not fresh full-weight identity.',
        'Config/index identity is consistent with fixed official base metadata; it does not prove every current weight byte official.',
        '19306216416 is index tensor storage including MTP, not instantiated model memory or prefill capacity.',
        'Existing base is Qwen3.5-9B; this audit does not claim JEV adapter download/load.',
        'Transformers BF16/SDPA candidate path differs from native S2/vLLM; no numerical equivalence established.',
        'GPU4–7 remain reserved by the original holder; four-card reservation time must still be counted even if future compute uses GPU7 only.',
    ],
    'model_GUI_health_scorer_download_load_remote_write_lock_acquisition_process_mutation_count': 0,
}
write_new('report.json', report)
text = '''# 现有9B基座与资源只读核查

3090完整基座为 `/home/researcher/models/Qwen3.5-9B`，4090为 `/data/researcher/models/Qwen3.5-9B`。各14文件，10份小元数据当前SHA与旧身份回执一致；4权重分片合计19,306,310,880字节、当前尺寸与旧回执一致，读取stat期间稳定。本次不重哈希大权重，旧回执只有bytes/SHA，无历史mtime/inode可比较；不能称为当前全权重身份再证明。旧三份回执均命中旧artifact-manifest原SHA。3090另一个`/opt/whz/llms/Qwen3.5-9B`仅5文件、缺权重与tokenizer，不能用作完整基座。

3090快照GPU4–7均无compute进程、各24,253MiB free；holder2568295真实UID1033/start_ticks1159211789/原完整命令，实际9个FD持FLOCK，四卡预留尚未释放。空闲不是新launch准入，也未触碰GPU0–3或外人任务。所有具体UUID、FD/inode和时间见原快照。

3090 `/opt/whz/conda-envs/webmall-vlm/bin/python` 与4090 `/data/researcher/venvs/qwen35-9b-full-20261019/bin/python`均为Python3.11.16，transformers5.15.1/torch2.5.1+cu121/tokenizers0.22.2/Pillow12.3.0/numpy2.4.6/safetensors0.8.0；accelerate分别1.14.0/1.15.0，均无vLLM。本次只读包metadata，未import模型、构造processor输入、装载权重或建立GPU上下文；没有共享环境安装/升级。原生S2/vLLM与拟用Transformers BF16/SDPA的差异须另列，不称数值等价。

本包0模型/GUI/health/scorer/下载/远端写入/占锁/进程更改。现有base可作为新JEV加载准备资产，但JEV权重、原生CPU输入与GPU预检仍须独立完成。若仅GPU7计算，原四卡预留时间仍按四卡记录。
'''
with (HERE / 'README.md').open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(text)
files = ['remote_readonly.py', 'collect_readonly.py', 'finalize_local_snapshot.py', '3090-readonly.json',
         '4090-readonly.json', '3090-invocation.json', '4090-invocation.json', 'report.json', 'README.md']
write_new('seal.json', {'created_utc': datetime.now(timezone.utc).isoformat(),
                         'files': [{'file': x, 'sha256': sha(HERE / x), 'bytes': (HERE / x).stat().st_size} for x in files]})
print(json.dumps({'report_sha256': sha(HERE / 'report.json'), 'seal_sha256': sha(HERE / 'seal.json'),
                  'files_sealed': len(files), 'old_receipts_verified_against_old_manifest': len(old_bindings)}))
