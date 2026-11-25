"""Independent local forensic checks. Never SSH, load weights or generate."""
import ast
import base64
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import tarfile
import traceback

HERE = Path(__file__).resolve().parent
COLLECTION = HERE / 'gpu-compact-four-terminal-collection-02'
ORIGINAL = COLLECTION / 'original'
FIRST = HERE / 'gpu-four-terminal-collection-01/original'
CPU = HERE / 'native-auxiliary-admission-compact02/cpu-native-compact-four-02/collected/admission-01'
FROZEN = HERE / 'compact-launcher-02/frozen-compact-gpu-02'
INPUTS = HERE / 'compact-four-image-inputs-02'
OUT = HERE / 'compact-four-independent-technical-audit-linked03'
HASHED = {}
IDS = ['S04', 'S10', 'S16', 'S19']


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(path):
    path = Path(path)
    before = path.stat()
    signature = (before.st_size, before.st_mtime_ns, before.st_ino)
    key = str(path.resolve())
    if key in HASHED and HASHED[key]['stat'] == signature:
        return HASHED[key]['sha256']
    accumulator = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            accumulator.update(block)
    after = path.stat()
    assert signature == (after.st_size, after.st_mtime_ns, after.st_ino), 'Artifact changed during independent hashing'
    HASHED[key] = {'stat': signature, 'bytes': before.st_size, 'sha256': accumulator.hexdigest()}
    return accumulator.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def verify_table(root, table):
    records = []
    for relative, expected in table.items():
        path = root / relative
        assert path.resolve().is_relative_to(root.resolve())
        assert sha(path) == expected, str(path)
        records.append({'path': relative, 'bytes': path.stat().st_size, 'sha256': expected})
    return records


def verify_seal(root, expected=None):
    if expected:
        assert sha(root / 'seal.json') == expected
    seal = read(root / 'seal.json')
    rows = seal['files'] if isinstance(seal.get('files'), list) else [{'path': k, 'sha256': v} for k, v in seal.items()]
    assert len({r['path'] for r in rows}) == len(rows)
    for row in rows:
        path = root / row['path']
        assert path.resolve().is_relative_to(root.resolve())
        assert sha(path) == row['sha256'], str(path)
        if 'bytes' in row:
            assert path.stat().st_size == row['bytes']
    return seal, len(rows)


def verify_chain(path):
    head = '0' * 64
    events = []
    for line in path.read_bytes().splitlines():
        event = json.loads(line)
        signature = event.pop('sha256')
        assert event.get('seq', event.get('index')) == len(events) and event.get('previous', event.get('previous_sha256')) == head
        assert digest(canonical(event)) == signature
        event['sha256'] = signature
        events.append(event)
        head = signature
    return events, {'events': len(events), 'head': head, 'raw_sha256': sha(path)}


def int64_values(path):
    raw = path.read_bytes()
    assert len(raw) % 8 == 0
    return list(struct.unpack('<' + 'q' * (len(raw) // 8), raw))


def identical_identity(left, right):
    return all(str(left[key]) == str(right[key]) for key in ['pid', 'uid', 'command', 'start_ticks'])


def audit():
    OUT.mkdir(exist_ok=False)
    collection_seal, collection_entries = verify_seal(COLLECTION, 'bf3f889fbbef396bf4fb85af57df6e872ec9026f798d506916bd75b602a01516')
    terminal_table = read(ORIGINAL / 'terminal-manifest.json')
    assert len(terminal_table) == 121
    assert {p.relative_to(ORIGINAL).as_posix() for p in ORIGINAL.rglob('*') if p.is_file()} == set(terminal_table) | {'terminal-manifest.json'}
    original_files = verify_table(ORIGINAL, terminal_table)
    # The archive and extracted originals are independently hashed above. Check
    # archive inventory without extracting or altering any original artifact.
    with tarfile.open(COLLECTION / 'original-terminal.tar', 'r:') as archive:
        members = {m.name.removeprefix('./'): m.size for m in archive.getmembers() if m.isfile()}
    assert set(members) == set(terminal_table) | {'terminal-manifest.json'}
    assert all((ORIGINAL / name).stat().st_size == size for name, size in members.items())
    seal, worker_files = verify_seal(ORIGINAL / 'worker')
    launcher_events, launcher_chain = verify_chain(ORIGINAL / 'journal.jsonl')
    worker_events, worker_chain = verify_chain(ORIGINAL / 'worker/journal.jsonl')
    assert launcher_chain['events'] == 4 and worker_chain['events'] == 25
    assert seal['journal_events'] == worker_chain['events'] and seal['journal_head'] == worker_chain['head']
    terminal = read(ORIGINAL / 'worker/terminal.json')
    assert worker_events[-1]['kind'] == 'terminal' and worker_events[-1]['data'] == terminal
    assert terminal['status'] == 'completed_four_first_attempts' and terminal['error'] is None
    assert terminal['attempted_request_ids'] == IDS
    assert [terminal[k] for k in ['attempted_requests', 'completed_requests', 'failed_incomplete_requests', 'unattempted']] == [4, 4, 0, 0]
    assert terminal['primary_actor_judge_calls'] == terminal['GUI_actions'] == terminal['scorer'] == terminal['paid_API'] == 0
    assert terminal['Mirage_reduction_established'] is False and terminal['four_card_joint_capacity_proven'] is False
    manifest = read(ORIGINAL / 'frozen-manifest.json')
    specification = read(ORIGINAL / 'launch-specification.json')
    for remote_name, local_name in [('frozen-manifest.json', 'gpu-manifest.json'), ('launch-specification.json', 'launch-specification.json')]:
        assert sha(ORIGINAL / remote_name) == sha(FROZEN / local_name)
    assert sha(ORIGINAL / 'worker/input-manifest.original.json') == sha(FROZEN / 'gpu-manifest.json')
    assert specification['manifest']['sha256'] == sha(ORIGINAL / 'frozen-manifest.json')
    assert specification['worker_source']['sha256'] == sha(ORIGINAL / 'source-snapshot/native_image_gpu_preflight.py')
    assert sha(ORIGINAL / 'source-snapshot/native_image_gpu_preflight.py') == '1fbd3b6e1b21f4c3468bbc4a08cf37baad780c47143cc40886ce32880d7606e8'
    assert specification['launcher_source_sha256'] == sha(ORIGINAL / 'source-snapshot/launch_once.py')
    assert specification['resource_gate_source_sha256'] == sha(ORIGINAL / 'source-snapshot/resource_gate.py')
    assert [r['request_id'] for r in manifest['requests']] == IDS
    old_functions = {n.name: ast.dump(n, include_attributes=False) for n in ast.parse((HERE / 'native_image_gpu_preflight.py').read_text(encoding='utf-8')).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    new_functions = {n.name: ast.dump(n, include_attributes=False) for n in ast.parse((ORIGINAL / 'source-snapshot/native_image_gpu_preflight.py').read_text(encoding='utf-8')).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    assert [k for k in old_functions if old_functions[k] != new_functions[k]] == ['validate_manifest', 'current_weight_identity']
    assert new_functions['run'] == old_functions['run']
    cpu_seal, cpu_files = verify_seal(CPU, manifest['cpu_proof']['seal_sha256'])
    assert cpu_files == 73 and read(CPU / 'terminal.json')['admitted_requests'] == 4
    verify_seal(INPUTS, '3473bf5a7a5a28c37ee14d329a72359d43bea3da531025a8d56d6e89d49c8706')
    contract_path = HERE / 'compact-evidence-02/image_evidence.py'
    assert sha(contract_path) == manifest['evidence_contract']['sha256'] == '081caa2595440dd1f813efaa4f960a78cd095b8448353d65a11f464593140676'
    module_spec = importlib.util.spec_from_file_location('technical_audit_contract_only', contract_path)
    contract = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(contract)  # stdlib; PIL only validates already received originals
    # Do not read PRIVATE labels. Verify their outer source-file byte bindings.
    labels = HERE / 'compact-launcher-02/source-first-labels-envelope-02'
    verify_seal(labels, manifest['source_labels']['seal_sha256'])
    assert sha(labels / 'source-seal.original.json') == '688f27b2fa0f28b31f3e3cf5632efe1316f3dcaee364407478fcf94d078485c1'
    for row in read(labels / 'source-seal.original.json')['entries']:
        assert sha(labels / row['path']) == row['sha256'] and (labels / row['path']).stat().st_size == row['bytes']
    # Reuse full original hash proof; never touch any deployed shard.
    reused = manifest['current_weight_identity_reuse']
    assert sha(FIRST / 'worker/current-weight-identity.json') == reused['identity_sha256']
    assert sha(FIRST / 'worker/seal.json') == reused['worker_seal_sha256']
    assert sha(FIRST / 'terminal-manifest.json') == reused['terminal_manifest_sha256']
    first_manifest = read(FIRST / 'terminal-manifest.json')
    first_seal = {r['path']: r['sha256'] for r in read(FIRST / 'worker/seal.json')['files']}
    assert first_manifest['worker/current-weight-identity.json'] == first_seal['current-weight-identity.json'] == reused['identity_sha256']
    assert first_manifest['worker/seal.json'] == reused['worker_seal_sha256']
    assert sha(FIRST / 'worker/terminal.json') == first_manifest['worker/terminal.json'] == first_seal['terminal.json']
    assert sha(FIRST / 'exit.json') == first_manifest['exit.json']
    first_terminal = read(FIRST / 'worker/terminal.json')
    first_exit = read(FIRST / 'exit.json')
    assert first_terminal['status'] == 'completed_four_first_attempts' and first_terminal['error'] is None
    assert first_exit['launcher_exit_code'] == first_exit['worker_exit_code'] == 0
    proof = read(FIRST / 'worker/current-weight-identity.json')
    current = read(ORIGINAL / 'worker/current-weight-identity.json')
    assert current['current_weight_identity_reuse'] == reused
    assert proof['official_LFS_current_shard_identity_verified'] is True and current['official_LFS_current_shard_identity_verified'] is True
    assert current['fresh_full_weight_hash_performed'] is False and current['weight_bytes_read_by_identity_check'] == 0
    assert current['after_load_stat_gate_required'] is True
    official = HERE / 'model-capability-review/native-small-metadata-linked02-1794046900308884400/qwen-fixed-api.json'
    assert sha(official) == manifest['official_base_api']['sha256'] == proof['official_pinned_base_api_sha256'] == current['official_pinned_base_api_sha256']
    api = read(official)
    assert api['id'] == manifest['base_model']['repo'] and api['sha'] == manifest['base_model']['revision']
    lfs = {r['rfilename']: r['lfs'] for r in api['siblings'] if r['rfilename'].endswith('.safetensors')}
    historical_path = Path('D:/MultiModel/attention-audit-20261031/model-sha256-3090.json')
    assert sha(historical_path) == manifest['prior_weight_identity']['sha256']
    historical = read(historical_path)['files']
    before = {r['filename']: r for r in proof['complete_current_shards']}
    after = {r['filename']: r for r in current['complete_current_shards']}
    declared = {r['filename']: r for r in manifest['weight_files']}
    index = read(ORIGINAL / 'worker/metadata--model.safetensors.index.json')
    assert len(before) == len(after) == len(declared) == 4
    assert set(before) == set(after) == set(declared) == set(index['weight_map'].values()) == set(lfs)
    for name in before:
        assert all(before[name][key] == after[name][key] for key in ['bytes', 'sha256', 'mtime_ns', 'inode'])
        assert before[name]['current_sha256'] == after[name]['reused_full_sha256'] == declared[name]['sha256'] == historical['Qwen3.5-9B/' + name]['sha256'] == lfs[name]['sha256']
        assert before[name]['bytes'] == declared[name]['bytes'] == historical['Qwen3.5-9B/' + name]['bytes'] == lfs[name]['size']
    assert sum(r['bytes'] for r in after.values()) == 19306310880
    assert proof['metadata'] == current['metadata'] == manifest['metadata_files']
    for row in current['metadata']:
        p = ORIGINAL / 'worker' / ('metadata--' + row['filename'])
        assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256']
    stat_events = [e['data'] for e in worker_events if e['kind'] == 'current_shard_stat_reuse']
    assert stat_events == current['complete_current_shards']
    loaded = read(ORIGINAL / 'worker/loaded.json')
    inventory = loaded['actual_cuda_tensors']
    assert len(inventory) == terminal['runtime']['actual_cuda_tensors'] == 763
    assert loaded['base_model'] == manifest['base_model'] and loaded['jev_relationship'] == manifest['jev_relationship']
    assert loaded['model_class'] == 'Qwen3_5ForConditionalGeneration'
    assert loaded['jev_relationship']['decision_adapter_loaded'] is False
    assert all(r['device'] == 'cuda:0' for r in inventory)
    assert all(r['dtype'] == 'torch.bfloat16' for r in inventory if r['kind'] == 'parameter' and r['dtype'].startswith(('torch.float', 'torch.bfloat')))
    assert loaded['actual_attention_backends'] == {'model': 'sdpa', 'text': 'sdpa', 'vision': 'sdpa'}
    assert loaded['runtime_change_from_official_vLLM'] is True and loaded['vLLM_bitwise_equivalence_claimed'] is False
    for name, row in loaded['runtime_sources'].items():
        assert sha(ORIGINAL / 'worker' / ('runtime-source--' + name + '.py')) == row['sha256']
    generation = read(ORIGINAL / 'worker/effective-generation.json')['config']
    for name in ['max_new_tokens', 'do_sample', 'temperature', 'top_p', 'top_k', 'num_beams', 'num_return_sequences', 'eos_token_id']:
        assert generation[name] == manifest['generation'][name]
    assert generation['forced_eos_token_id'] is None and generation['stop_strings'] is None
    exited = read(ORIGINAL / 'exit.json')
    assert exited['worker_exit_code'] == exited['launcher_exit_code'] == 0
    worker_identity = read(ORIGINAL / 'worker/claim.json')['identity']
    assert identical_identity(worker_identity, exited['worker_identity']) and identical_identity(loaded['identity'], exited['worker_identity'])
    assert worker_identity['uid'] == 1033 and worker_identity['ppid'] == exited['launcher_identity']['pid']
    claim = read(ORIGINAL / 'worker/claim.json')
    assert claim['manifest_sha256'] == sha(ORIGINAL / 'frozen-manifest.json')
    assert claim['worker_sha256'] == sha(ORIGINAL / 'source-snapshot/native_image_gpu_preflight.py')
    worker_launch = read(ORIGINAL / 'worker-launch.json')
    assert identical_identity(worker_launch['identity'], exited['worker_identity'])
    assert worker_launch['inherited_lock_FDs'] == list(range(3, 12)) and worker_launch['visible_GPU'] == '7'
    postexit = read(COLLECTION / 'remote-audit.json')
    assert postexit['exit'] == exited
    assert postexit['actual_original_processes'] == {'launcher_identity': None, 'worker_identity': None}
    assert postexit['time_unix'] > exited['ended_unix']
    resources = [read(ORIGINAL / name) for name in ['before-resources.json', 'immediate-pre-spawn-resources.json', 'after-resources.json']]
    resources.extend(e['data'] for e in worker_events if e['kind'] == 'actual_resource_check')
    for data in resources:
        assert data['actual_holder']['uid'] == 1033 and str(data['actual_holder']['start_ticks']) == '1159211789'
        for identity in data['actual_allowed_identities'].values():
            role = 'launcher_identity' if identity['pid'] == exited['launcher_identity']['pid'] else 'worker_identity'
            assert identical_identity(identity, exited[role])
        assert [r['index'] for r in data['cards']] == [4, 5, 6, 7]
        assert data['lease_sha256'] == specification['lease']['sha256']
        assert len(data['holder_fdinfo']) == len(data['inherited_fdinfo']) == 9
        for held, inherited in zip(data['holder_fdinfo'], data['inherited_fdinfo']):
            assert all(held[k] == inherited[k] for k in ['path', 'inode', 'device'])
            assert held['held_lock_lines'] and inherited['held_lock_lines']
            assert all('FLOCK  ADVISORY  WRITE 2568295 ' in line for line in held['held_lock_lines'] + inherited['held_lock_lines'])
        if data['require_empty']:
            assert not data['compute'] and all(card['free_mib'] >= 23000 for card in data['cards'])
        for process in data['compute']:
            assert identical_identity(process['actual_identity'], exited['worker_identity'])
            assert process['uuid'] == data['cards'][-1]['uuid']
    assert not resources[2]['compute']
    tokenizer = read(ORIGINAL / 'worker/metadata--tokenizer.json')
    assert tokenizer['decoder']['type'] == 'ByteLevel' and tokenizer['model']['type'] == 'BPE'
    tokens = {value: key for key, value in tokenizer['model']['vocab'].items()}
    specials = set()
    for row in tokenizer['added_tokens']:
        tokens[row['id']] = row['content']
        if row['special']:
            specials.add(row['id'])
    initial_bytes = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    byte_values = initial_bytes[:]
    codepoints = initial_bytes[:]
    for number in range(256):
        if number not in initial_bytes:
            byte_values.append(number)
            codepoints.append(256 + len(byte_values) - len(initial_bytes) - 1)
    decoder = {chr(codepoint): byte for byte, codepoint in zip(byte_values, codepoints)}
    def decode(ids, skip_special):
        encoded = ''.join(tokens[token] for token in ids if not (skip_special and token in specials))
        return bytes(decoder[character] for character in encoded).decode('utf-8', errors='replace')
    request_events = [e['data'] for e in worker_events if e['kind'] == 'inference_request']
    reply_events = [e['data'] for e in worker_events if e['kind'] == 'inference_terminal']
    assert len(request_events) == len(reply_events) == 4
    reports = []
    for i, source in enumerate(manifest['requests']):
        path = ORIGINAL / 'worker' / ('r%03d' % i)
        cpu_path = CPU / ('r%03d' % i)
        admission = read(cpu_path / 'admission.json')
        result = read(path / 'result.json')
        assert result == terminal['results'][i] == reply_events[i]
        assert result['request_id'] == admission['request_id'] == source['request_id'] == IDS[i]
        assert sha(path / 'request.original.json') == sha(INPUTS / (IDS[i] + '-request.json')) == source['sha256'] == result['request_sha256'] == admission['request_sha256']
        request = read(path / 'request.original.json')
        image = contract.validate_image_only_request(request)
        assert digest(image) == sha(path / 'received-original.image') == source['image_sha256'] == result['image_sha256'] == admission['image_sha256']
        assert request['prompt'] == contract.FIXED_PROMPT and request['prompt_sha256'] == admission['prompt_sha256']
        actual = read(path / 'actual-first-forward.json')
        assert set(actual) == set(admission['tensor_artifacts'])
        tensors = {}
        for name, expected in admission['tensor_artifacts'].items():
            observed = actual[name]
            assert all(observed[key] == expected[key] for key in ['shape', 'dtype', 'bytes', 'sha256'])
            actual_path = path / observed['file']
            prepared_path = path / ('prepared_' + name + '.tensor')
            native_path = cpu_path / expected['file']
            assert sha(actual_path) == sha(prepared_path) == sha(native_path) == expected['sha256']
            assert actual_path.stat().st_size == prepared_path.stat().st_size == native_path.stat().st_size == expected['bytes']
            tensors[name] = {'sha256': expected['sha256'], 'bytes': expected['bytes'], 'shape': expected['shape'], 'dtype': expected['dtype']}
        inputs = int64_values(path / 'actual_forward_input_ids.tensor')
        generated = read(path / 'generated_ids.json')[0]
        sequence = read(path / 'sequence_ids.json')[0]
        assert sequence == inputs + generated
        assert int64_values(path / 'generated_ids.tensor') == generated and int64_values(path / 'sequence_ids.tensor') == sequence
        assert len(inputs) == result['input_tokens'] == admission['input_tokens'] == 2616
        assert len(generated) == result['output_tokens'] < manifest['generation']['max_new_tokens']
        assert generated[-1] == result['last_token_id'] == 248046
        assert all(token not in manifest['generation']['eos_token_id'] for token in generated[:-1])
        assert contract.FIXED_PROMPT in decode(inputs, False)
        raw = (path / 'raw-output.txt').read_text(encoding='utf-8')
        assert decode(generated, True) == raw
        assert decode(generated, False) == (path / 'output-with-special-tokens.txt').read_text(encoding='utf-8')
        assert sha(path / 'raw-output.txt') == result['raw_output_sha256']
        trace = [json.loads(line) for line in (path / 'actual-forward-calls.jsonl').read_bytes().splitlines()]
        assert len(trace) == result['actual_forward_calls'] == len(generated)
        assert [row['forward_index'] for row in trace] == list(range(len(trace)))
        assert trace[0]['input_ids'] == [inputs]
        assert all(trace[j]['input_ids'] == [[generated[j - 1]]] for j in range(1, len(trace)))
        assert result['natural_eos'] is True and result['contract_valid'] is True and result['contract_error'] is None
        assert result['retry_performed'] is False and result['automatic_allow_or_block'] is False
        packet = read(path / 'evidence-packet.json')
        assert contract.actor_packet(request, raw, True) == packet
        assert packet['semantic_correctness_established'] is False and packet['inventory_is_exhaustive'] is False
        assert packet['auxiliary_model_count'] == 1 and packet['automatic_allow_or_block'] is False
        assert request_events[i]['request_id'] == source['request_id'] and request_events[i]['request_sha256'] == source['sha256']
        assert request_events[i]['image_sha256'] == source['image_sha256'] and request_events[i]['semantic_labels_supplied'] is False
        reports.append({'request_id': IDS[i], 'input_tokens': len(inputs), 'output_tokens': len(generated),
            'generation_seconds': result['generation_seconds'], 'natural_eos_token': generated[-1],
            'request_sha256': source['sha256'], 'image_sha256': source['image_sha256'],
            'full_native_CPU_prepared_actual_forward_hashes_equal': True, 'tensor_records': tensors,
            'native_sequence_prefix_and_cached_steps_checked': True, 'independent_ByteLevel_ID_decode_equal_raw_output': True,
            'contract_packet_reconstruction_equal': True, 'transport': packet['native_transport']['kind'],
            'text_count': len(packet['reading']['text_spans']), 'element_count': len(packet['reading']['elements']),
            'uncertainty_count': len(packet['reading']['uncertain_regions']),
            'semantic_accuracy_assessed_by_this_audit': False,
        })
    elapsed = exited['ended_unix'] - exited['started_unix']
    reserved = 4 * elapsed
    assert math.isclose(reserved, exited['four_GPU_reserved_seconds_during_launcher'], abs_tol=1e-9)
    assert exited['reservation_GPUs'] == [4, 5, 6, 7] and exited['compute_GPU_scope'] == [7]
    assert exited['primary_or_Flash_started'] is False and exited['GUI_actions'] == exited['scorer_calls'] == 0
    cost = {'input_tokens': sum(r['input_tokens'] for r in reports), 'output_tokens': sum(r['output_tokens'] for r in reports),
        'summed_generation_seconds': sum(r['generation_seconds'] for r in reports),
        'load_seconds': loaded['load_seconds'], 'launcher_elapsed_seconds': elapsed,
        'four_GPU_reserved_seconds_during_launcher': reserved,
        'maximum_allocated_bytes': max(r['peak_allocated_bytes'] for r in terminal['results']),
        'maximum_reserved_bytes': max(r['peak_reserved_bytes'] for r in terminal['results']),
        'whole_holder_reservation_outside_launcher_interval_measured': False,
        'currency_energy_or_end_to_end_cost_reduction_claimed': False}
    assert cost['input_tokens'] == 10464 and cost['output_tokens'] == 3240
    write_new(OUT / 'requests.json', reports)
    write_new(OUT / 'hash-verification.json', {'terminal_original_files': original_files,
        'collection_seal_entries': collection_entries, 'worker_seal_entries': worker_files, 'cpu_seal_entries': cpu_files,
        'hashes': {name: {'bytes': item['bytes'], 'sha256': item['sha256']} for name, item in HASHED.items()}})
    receipt = {'status': 'completed_independent_read_only_technical_audit',
        'original_terminal_manifest_sha256': sha(ORIGINAL / 'terminal-manifest.json'),
        'collection_seal_sha256': sha(COLLECTION / 'seal.json'), 'original_manifest_bound_files': 121,
        'manifest_self_excluded_from_121': True, 'all_original_tensor_bytes_independently_hashed': True,
        'launcher_chain': launcher_chain, 'worker_chain': worker_chain,
        'attempted_requests': 4, 'natural_EOS': 4, 'contract_valid_packets': 4, 'retries': 0,
        'model_revision_and_source_bindings_checked': True,
        'weight_identity': {'original_full_hash_proof_reused': True, 'current_size_mtime_inode_match_original_four_shards': True,
            'metadata_current_hashes_and_official_historical_full_SHA_agree': True,
            'fresh_full_weight_hash_performed': False, 'deployed_weight_bytes_read_by_this_audit': 0,
            'after_load_stat_gate_passed_by_successful_mandatory_source_control_flow': True,
            'separate_post_load_stat_snapshot_present': False,
            'GPU_tensor_inventory_device_dtype_checked': True, 'GPU_tensor_value_identity_cryptographically_proven': False},
        'postexit': {'exit_codes': [0, 0], 'same_UID_full_command_start_ticks_bound': True,
            'captured_proc_absence_receipt_verified': True, 'receipt_time_unix': postexit['time_unix'],
            'new_live_remote_observation_performed_by_this_audit': False,
            'nine_holder_and_inherited_lock_FDs_checked_at_all_resource_snapshots': True,
            'resource_snapshots_checked': len(resources)},
        'cost': cost,
        'limitations': ['technical completion and packet syntax are not semantic correctness or Mirage reduction',
            'single image-only shared original base in BF16/SDPA; no JEV decision adapter; no vLLM numerical equivalence',
            'one auxiliary computes on GPU7 while four GPUs remain reserved; joint main+aux capacity untested',
            'no main actor, full GUI, official score or paid API calls; normal-operation/false-block behavior untested',
            'audit independently checks original bytes and chains; it does not rerun inference or independently re-observe remote state'],
        'linked_prior_local_audit_failure': {'root': str(HERE / 'compact-four-independent-technical-audit-02'), 'reason': 'launcher uses index/previous_sha256; worker uses seq/previous; journal parser field dispatch only', 'original_experiment_failure': False},
        'root_technical_audit_receipt_or_conclusions_read': False,
        'semantic_label_bodies_read': False, 'original_images_visually_reviewed_by_this_audit': False,
        'new_model_GPU_GUI_scorer_network_requests': 0, 'original_files_modified': False,
        'primary_GUI_release_ready': False, 'Mirage_reduction_established': False,
    }
    write_new(OUT / 'receipt.json', receipt)
    (OUT / 'audit-source.py').write_bytes(Path(__file__).read_bytes())
    write_new(OUT / 'seal.json', {path.name: sha(path) for path in sorted(OUT.iterdir()) if path.is_file()})
    print(json.dumps({'status': receipt['status'], 'seal_sha256': sha(OUT / 'seal.json'), 'cost': cost,
        'verified_requests': 4, 'technical_findings': 'no failed assertions; semantic quality outside scope'}))


if __name__ == '__main__':
    try:
        audit()
    except BaseException:
        if OUT.is_dir():
            write_new(OUT / 'failure.json', {'traceback': traceback.format_exc(), 'new_model_GPU_GUI_network_requests': 0,
                'all_originals_read_only': True})
            (OUT / 'failed-audit-source.py').write_bytes(Path(__file__).read_bytes())
            write_new(OUT / 'failure-seal.json', {path.name: sha(path) for path in sorted(OUT.iterdir()) if path.is_file()})
        raise
