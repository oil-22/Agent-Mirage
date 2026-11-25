"""One-time, local-only native 27B replay on four explicitly leased GPUs."""
import ast
import base64
import copy
import io
import itertools
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
import traceback
from types import SimpleNamespace

from crop_token_probe import (BACKEND, LINKED11, REMOTE_ARCHIVES, canonical, describe, load,
                              preprocess_from, require, sha, sha_file, tensor_sha)

ROOT = Path(__file__).resolve().parent
PUBLIC, CASES = ROOT / 'public', ROOT / 'cases'
PLAN = load(ROOT / 'plan.json')
GIB = 1024 ** 3
PHYSICAL = [4, 5, 6, 7]


def save(path, v):
    with path.open('xb') as f:
        f.write(canonical(v) + b'\n')
        f.flush()
        os.fsync(f.fileno())


def check_sources():
    require(os.getuid() == 1033, 'actual 3090 user')
    require(sha_file(Path(__file__)) == PLAN['worker_sha256'] and sha_file(ROOT / 'crop_token_probe.py') == PLAN['probe_sha256'] and
            sha_file(ROOT / 'PROTOCOL.md') == PLAN['protocol_sha256'], 'frozen replay package')
    require(PLAN['physical_gpus'] == PHYSICAL and PLAN['max_calls'] == 3 * len(PLAN['cases']) == 36 and PLAN['max_output'] == 2048, 'frozen budget')
    for item in PLAN['packages'].values():
        p = Path(item['root'])
        require(sha_file(p / 'manifest.json') == item['manifest_sha256'], 'native package manifest')
        for name, h in item['source_sha256'].items():
            require(sha_file(p / name) == h, name)
    pkg = Path(PLAN['packages'][LINKED11]['root'])
    ref = PLAN['packages'][LINKED11]['reference']
    meta = load(Path(ref['primary_expected_runtime']))
    model = Path(ref['primary_model'])
    for name, h in meta['metadata_sha256'].items():
        require(sha_file(model / name) == h, name)
    return pkg, model, meta


def native_devices(*, loaded):
    def smi(args):
        return [re.split(r',\s*', r.strip()) for r in subprocess.check_output(
            ['nvidia-smi', args, '--format=csv,noheader,nounits'], text=True, timeout=15).splitlines() if r.strip()]
    cards = {int(i): {'uuid': u, 'total_mib': int(total), 'free_mib': int(free)}
             for i, u, total, free in smi('--query-gpu=index,uuid,memory.total,memory.free')}
    compute = [{'uuid': u, 'pid': int(p), 'mib': int(m)} for u, p, m in smi('--query-compute-apps=gpu_uuid,pid,used_memory')]
    for i in PHYSICAL:
        pids = {r['pid'] for r in compute if r['uuid'] == cards[i]['uuid']}
        require(pids == ({os.getpid()} if loaded else set()), 'unowned compute or absent expected worker on GPU ' + str(i))
        if not loaded:
            require(cards[i]['free_mib'] >= 23000, 'not enough unallocated GPU memory ' + str(i))
    return {'gpu': cards, 'compute': compute, 'checked_at': time.time()}


def identity():
    proc = Path('/proc/self')
    return {'uid': os.getuid(), 'pid': os.getpid(), 'command': proc.joinpath('cmdline').read_bytes().replace(b'\0', b' ').decode().strip(),
            'start_ticks': proc.joinpath('stat').read_text().rsplit(') ', 1)[1].split()[19]}


def acquire():
    import fcntl
    before = native_devices(loaded=False)
    h = Path('/home/researcher')
    dirs = (h / '.mirage-resource-locks', h / 'defense-resume-20261102-retry2/resource-locks')
    paths = [dirs[0] / 'crop-visual-replay-20261120.lock', h / 'jev-defense-four-gpu-20261106/inference.lock']
    for j in PHYSICAL:
        paths += [d / (before['gpu'][j]['uuid'] + '.lock') for d in dirs]
    keep = []
    for name in sorted(paths):
        f = name.open('a')
        keep.append(f)
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    after = native_devices(loaded=False)
    uuids = [before['gpu'][i]['uuid'] for i in PHYSICAL]
    require(uuids == [after['gpu'][i]['uuid'] for i in PHYSICAL], 'GPU UUID continuity under locks')
    save(PUBLIC / 'lease.json', {'process': identity(), 'physical_gpu': PHYSICAL, 'uuid_order': uuids, 'before': before, 'after': after,
                                'lock_files': [{'path': f.name, 'fd': f.fileno(), 'inode': os.fstat(f.fileno()).st_ino} for f in keep]})
    os.environ['CUDA_VISIBLE_DEVICES'] = ','.join(uuids)
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True,garbage_collection_threshold:0.8'
    os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
    return keep


def describe_body(body):
    spots, images = [], []
    for i, msg in enumerate(body['messages']):
        if isinstance(msg['content'], list):
            for j, block in enumerate(msg['content']):
                if block['type'] == 'image_url':
                    url = block['image_url']
                    url = url['url'] if isinstance(url, dict) else url
                    require(url.startswith('data:image/png;base64,'), 'archived PNG-only capture')
                    images.append(base64.b64decode(url.split(',', 1)[1], validate=True))
                    spots.append((i, j))
    return spots, images


def prepare_cases(pkg, model, meta):
    import torch
    import transformers
    from transformers import AutoProcessor
    from PIL import Image
    require(os.environ.get('CUDA_VISIBLE_DEVICES') == '' and not torch.cuda.is_available(), 'CPU prepare GPU isolation')
    require(torch.__version__ == meta['torch'] and transformers.__version__ == meta['transformers'], 'native processor runtime')
    torch.set_num_threads(4)
    config = load(model / 'config.json')
    ids = [config[k] for k in ('image_token_id', 'vision_start_token_id', 'vision_end_token_id')]
    processor = AutoProcessor.from_pretrained(model, local_files_only=True, trust_remote_code=True)
    fn, ast_sha = preprocess_from(pkg / BACKEND, Image)
    CASES.mkdir(exist_ok=False)
    all_png = CASES / 'source-images'
    all_png.mkdir()
    inputs = ROOT / 'native-inputs'
    inputs.mkdir()
    summaries = []
    for case in PLAN['cases']:
        name, archived = case['case'], Path(case['root'])
        require(sha_file(archived / 'seal.json') == case['seal_sha256'], 'source request seal ' + name)
        seal = load(archived / 'seal.json')
        for file in ('body.json', 'wire-request.bin', 'prepared.json', 'first-forward.json', 'actual-generation.json', 'native-call.json'):
            require(sha_file(archived / file) == seal[file], name + ' ' + file)
        wire = load(archived / 'wire-request.bin')
        body = load(archived / 'body.json')
        require(wire['body'] == body and sha(canonical(body)) == case['body_sha256'] and seal['wire-request.bin'] == case['wire_sha256'], name + ' actual wire')
        require(wire['request_id'] == case['request_id'] and wire['run_id'] == case['run_id'] and wire['decision_index'] == case['decision'], name + ' archive wire identity')
        require(body['max_tokens'] == 2048 and body['temperature'] == 0 and body['chat_template_kwargs']['enable_thinking'] is False, name + ' native settings')
        spots, imgs = describe_body(body)
        require(len(body['messages']) == case['history_messages'] and [sha(z) for z in imgs] == case['all_image_sha256s'], name + ' ordered full history images')
        i, j = spots[-1]
        require(i == len(body['messages']) - 1 and body['messages'][i]['role'] == 'user' and all(a != i for a, _ in spots[:-1]), 'one current image, distinct from history')
        require(sha(imgs[-1]) == case['current_image_sha256'], name + ' actual current pixels')
        orig = Image.open(io.BytesIO(imgs[-1])).convert('RGB')
        require(orig.size == (1280, 720), 'frozen viewport geometry')
        roi = orig.crop((320, 180, 960, 540)).resize(orig.size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        roi.save(buf, format='PNG')
        roi_raw = buf.getvalue()
        for img in imgs + [roi_raw]:
            p = all_png / (sha(img) + '.png')
            if not p.exists():
                p.write_bytes(img)
        legal = copy.deepcopy(body['messages'])
        for (x, y), data in zip(spots, imgs):
            legal[x]['content'][y] = {'type': 'image', 'sha256': sha(data)}
        save(CASES / (name + '.json'), {'legal_messages': legal, 'current_image_sha256': sha(imgs[-1]), 'crop_sha256': sha(roi_raw),
                                       'crop_box': [320, 180, 960, 540], 'viewport_wh': [1280, 720]})
        first = load(archived / 'first-forward.json')
        rows, base, text_ids = {}, None, None
        for arm in PLAN['arms']:
            variant = copy.deepcopy(body)
            ordinal = [len(imgs) - 1]
            if arm != 'original':
                addition = (variant['messages'][i]['content'][j] if arm == 'append_duplicate' else
                            {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(roi_raw).decode('ascii')}})
                variant['messages'][i]['content'].insert(j + 1, addition)
                ordinal += [len(imgs)]
            actual = fn(SimpleNamespace(processor=processor), variant['messages'], 2048, None, original_body=variant)
            summary, words = describe(actual, *ids, processor.image_processor.patch_size, processor.image_processor.merge_size, ordinal)
            tensors = {k: {'shape': list(t.shape), 'dtype': str(t.dtype), 'sha256': tensor_sha(t)} for k, t in actual.items()}
            if arm == 'original':
                require(set(tensors) == set(first) and all(row == {k: first[field][k] for k in row}
                        for field, row in tensors.items()) and summary['total_tokens'] == case['input_tokens'], name + ' history matches all archived forward tensors')
                base, text_ids = summary, words
            else:
                require(text_ids == words and base['image_spans'] == summary['image_spans'][:-1], name + ' only appended view changes native inputs')
            filename = name + '-' + arm + '.json'
            save(inputs / filename, variant)
            rows[arm] = {'body_file': filename, 'body_sha256': sha_file(inputs / filename), 'tensors': tensors, 'summary': summary}
            del actual
        dup, zoom = (rows[a] for a in ('append_duplicate', 'append_zoom'))
        for key in ('input_ids', 'image_grid_thw', 'attention_mask', 'mm_token_type_ids'):
            require(dup['tensors'][key] == zoom['tensors'][key], name + ' exact token-matched comparison')
        require(dup['tensors']['pixel_values']['sha256'] != zoom['tensors']['pixel_values']['sha256'], name + ' matched-count visual contents differ')
        require(dup['summary']['image_spans'][-1] == base['image_spans'][-1] and
                dup['summary']['total_tokens'] == base['total_tokens'] + 882, name + ' exact duplicate and append increment')
        summaries.append({'case': name, 'arms': rows})
        print(f'CPU READY {name} original={base["total_tokens"]} added={zoom["summary"]["total_tokens"]}', flush=True)
    save(PUBLIC / 'cpu-prepared.json', {'plan_sha256': sha_file(ROOT / 'plan.json'), 'native_cpu_AST_sha256': ast_sha,
                                       'native_class': type(processor).__name__, 'cases': summaries, 'new_model_calls': 0})


def model_layout(model):
    parent = Path(REMOTE_ARCHIVES) / LINKED11 / 'model-attempt-01'
    archived = load(parent / 'postexit-seal.json')
    for field in ('primary/actual-state.json', 'primary/checkpoint-admission.json'):
        require(sha_file(parent / field) == archived[field], 'sealed 27B weight metadata ' + field)
    check = load(parent / 'primary/checkpoint-admission.json')['weight_stat_continuity']
    for record in check:
        stat = (model / record['file']).stat()
        # The model path is the same frozen deployed checkpoint. No full weight rehash.
        require((stat.st_size, stat.st_mtime_ns, stat.st_ino) == (record['bytes'], record['mtime_ns'], record['inode']), 'checkpoint continuous ' + record['file'])
    state = load(parent / 'primary/actual-state.json')
    policy = {'model.visual': 0, 'model.language_model.embed_tokens': 0, 'model.language_model.norm': 3,
              'model.language_model.rotary_emb': 3, 'lm_head': 3}
    layer = 'model.language_model.layers.'
    totals = [0] * 64
    constants = [0] * 4
    for r in state:
        if r['name'].startswith(layer):
            totals[int(r['name'][len(layer):].split('.')[0])] += r['bytes']
        else:
            constants[map_device(policy, r['name'])] += r['bytes']
    candidates = []
    for a, b, c in itertools.combinations(range(4, 64, 4), 3):
        if not (4 <= a <= 12 and 12 <= b - a <= 24 and 12 <= c - b <= 24 and 12 <= 64 - c <= 24):
            continue
        gates = (0, a, b, c, 64)
        sizes = [sum(totals[gates[j]:gates[j + 1]]) + v for j, v in enumerate(constants)]
        target = (8 * GIB, 15 * GIB, 15 * GIB, 15 * GIB)
        if any(s > 17 * GIB for s in sizes):
            continue
        candidates.append((sum(((s - t) / GIB) ** 2 for s, t in zip(sizes, target)), gates, sizes))
    _, gates, sizes = min(candidates)
    for device in range(4):
        for n in range(gates[device], gates[device + 1]):
            policy[layer + str(n)] = device
    return {'device_map': policy, 'weight_bytes': sizes, 'cuts': gates,
            'archived_state_sha256': archived['primary/actual-state.json']}, state


def map_device(policy, name):
    key, = [k for k in policy if name == k or name.startswith(k + '.')]
    return policy[key]


def install_memory(pkg, engine):
    # This copies exactly the already validated numerical kernels. Adapt only the
    # installer assertion that checks how many devices own MLP layers.
    import historical_memory
    node = ast.parse((pkg / 'historical_memory.py').read_bytes())
    fn = next(x for x in node.body if isinstance(x, ast.FunctionDef) and x.name == 'install')
    guard, = [x for x in fn.body if isinstance(x, ast.Assert) and 'v.gate_proj.weight.device' in ast.unparse(x.test)]
    bound, = [x for x in ast.walk(guard) if isinstance(x, ast.Call) and ast.unparse(x) == 'range(7)']
    bound.args = [ast.Constant(4)]
    patched = ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))
    ctx = vars(historical_memory).copy()
    exec(compile(patched, str(pkg / 'historical_memory.py'), 'exec'), ctx)
    return ctx['install'](SimpleNamespace(engine=engine), pkg, PUBLIC, save, sha_file,
                          lambda loaded: native_devices(loaded=loaded))


def run_model(pkg, model_path, meta):
    import inspect
    prepared = load(PUBLIC / 'cpu-prepared.json')
    require(prepared['plan_sha256'] == sha_file(ROOT / 'plan.json') and len(prepared['cases']) == len(PLAN['cases']), 'CPU-preflight-to-run binding')
    require([c['case'] for c in prepared['cases']] == [c['case'] for c in PLAN['cases']], 'frozen panel order')
    # Claim before trying GPU admission; no resurrection of an old or partial run.
    save(PUBLIC / 'run-claim.json', {'process': identity(), 'cpu_prepared_sha256': sha_file(PUBLIC / 'cpu-prepared.json')})
    policy, state = model_layout(model_path)
    save(PUBLIC / 'four-card-placement.json', policy)
    locks = acquire()
    global HELD
    HELD = locks  # Keep the lease until this CUDA process exits, including on error.
    import torch
    import transformers
    from transformers import AutoModelForImageTextToText, AutoProcessor
    require(torch.__version__ == meta['torch'] and transformers.__version__ == meta['transformers'], 'native pinned GPU runtime')
    require(torch.cuda.device_count() == len(PHYSICAL), 'exact CUDA visible devices')
    torch.set_num_threads(4)
    for j in range(4):
        torch.cuda.set_per_process_memory_fraction(0.87, j)
    source = load(pkg / 'manifest.json')['files']
    for rel, digest in source.items():
        if rel.startswith('release/') or rel.endswith('.py') or rel in ('parent-capacity.json', 'explicit-placement.json'):
            require(sha_file(pkg / rel) == digest, 'sealed executed dependency ' + rel)
    sys.path[:0] = [str(pkg / 'flash'), str(pkg / 'release'), str(pkg)]
    from defense.qwen_backend import LocalQwen
    started = time.time()
    print('LOADING original 27B BF16 weights, four owned GPUs', flush=True)
    model = AutoModelForImageTextToText.from_pretrained(model_path, dtype=torch.bfloat16, attn_implementation='sdpa',
                 device_map=policy['device_map'], max_memory={i: '20GiB' for i in range(4)}, local_files_only=True, trust_remote_code=True).eval()
    processor = AutoProcessor.from_pretrained(model_path, local_files_only=True, trust_remote_code=True)
    engine = LocalQwen.__new__(LocalQwen)
    engine.model, engine.processor, engine.torch = model, processor, torch
    expected = {r['name']: r for r in state}
    actual = model.state_dict()
    require(set(actual) == set(expected), 'original full state inventory')
    for name, val in actual.items():
        r = expected[name]
        require((list(val.shape), str(val.dtype), val.numel() * val.element_size()) == (r['shape'], r['dtype'], r['bytes']), 'actual state metadata ' + name)
        require(str(val.device) == 'cuda:' + str(map_device(policy['device_map'], name)), 'any CPU/disk or misplaced parameter is invalid: ' + name)
    del actual
    for name, buf in list(model.named_buffers()):
        device = 'cuda:' + str(map_device(policy['device_map'], name))
        if buf.device.type == 'cpu':
            owner_name, leaf = name.rsplit('.', 1)
            owner = model.get_submodule(owner_name)
            require(leaf in owner._non_persistent_buffers_set, 'no moving persistent state')
            moved = buf.to(device)
            require(torch.equal(moved.cpu(), buf), 'native nonpersistent buffer values')
            owner._buffers[leaf] = moved
        else:
            require(str(buf.device) == device, 'native buffer map ' + name)
    require(all(t.dtype == torch.bfloat16 for t in model.parameters() if t.is_floating_point()), 'original BF16 precision')
    require(sha_file(Path(inspect.getfile(type(model)))) == load(Path(PLAN['packages'][LINKED11]['reference']['primary_native_layout_receipt']))['native_source_sha256'], 'same native execution class')
    save(PUBLIC / 'loaded.json', {'status': 'loaded', 'process': identity(), 'original_native_model': type(model).__name__,
                                  'BF16': True, 'SDPA': True, 'state_entries': len(state), 'placement': policy,
                                  'load_seconds': time.time() - started, 'actual_compute': native_devices(loaded=True)})
    install_memory(pkg, engine)
    print('READY four-card native 27B, no offload', flush=True)
    raw_dir, blind_dir = ROOT / 'raw', PUBLIC / 'blind'
    raw_dir.mkdir(); blind_dir.mkdir()
    mapping, rows = {}, []
    for frozen, cpu in zip(PLAN['cases'], prepared['cases']):
        name = frozen['case']
        for arm in frozen['arm_order']:
            before = native_devices(loaded=True)
            entry = cpu['arms'][arm]
            body_path = ROOT / 'native-inputs' / entry['body_file']
            require(sha_file(body_path) == entry['body_sha256'], 'frozen real request body')
            body = load(body_path)
            target = raw_dir / f'{name}-{arm}'
            target.mkdir()
            save(target / 'start.json', {'case': name, 'arm': arm, 'body_sha256': entry['body_sha256'], 'at': time.time(), 'resource': before})
            first, calls = {}, [0]
            def hook(_module, _args, kwargs):
                calls[0] += 1
                if calls[0] == 1:
                    record = {key: {'shape': list(kwargs[key].shape), 'dtype': str(kwargs[key].dtype),
                                    'sha256': tensor_sha(kwargs[key].detach().cpu())} for key in entry['tensors']}
                    require(record == entry['tensors'], name + ' actual first forward differs from frozen tensors')
                    past = kwargs.get('past_key_values')
                    require(past is None or past.get_seq_length() == 0, 'new generation independent KV')
                    first.update(record)
                    save(target / 'first-forward.json', record)
            for j in range(4):
                torch.cuda.reset_peak_memory_stats(j)
            handle = model.register_forward_pre_hook(hook, with_kwargs=True)
            began = time.time()
            try:
                try:
                    engine.generate(body['messages'], 2048, target / 'actual-native-call.json', seed=42, original_body=body)
                except RuntimeError:
                    if not (target / 'actual-native-call.json').exists() or not load(target / 'actual-native-call.json')['hit_output_cap']:
                        raise
                rec = load(target / 'actual-native-call.json')
                require(first and rec['request_messages_sha256'] == sha(canonical(body['messages'])), 'real body and model input observed')
                require(sha(memoryview(torch.tensor(rec['input_ids'], dtype=torch.int64).numpy()).cast('B')) == first['input_ids']['sha256'], 'actual generated prefix identical')
                require(rec['generation_config']['max_new_tokens'] == 2048 and not rec['generation_config']['do_sample'], 'native decode configuration')
                _, eos = rec['generation_config']['do_sample'], rec['generation_config']['eos_token_id']
                eos = eos if isinstance(eos, list) else [eos]
                gen = rec['generated_ids']
                natural = bool(gen and gen[-1] in eos and not rec['hit_output_cap'])
                old = load(Path(frozen['root']) / 'actual-generation.json')
                blind = secrets.token_hex(8)
                mapping[blind] = {'case': name, 'arm': arm}
                metrics = {'case': name, 'arm': arm, 'input_tokens': len(rec['input_ids']), 'output_tokens': len(gen),
                           'natural_EOS': natural, 'actual_forward_calls': calls[0], 'seconds': time.time() - began,
                           'actual_native_call_sha256': sha_file(target / 'actual-native-call.json'),
                           'input_ids_equal_original_archive': first['input_ids']['sha256'] == cpu['arms']['original']['tensors']['input_ids']['sha256'],
                           'generation_ids_equal_original_archive': gen == old['output_ids'],
                           'peak_reserved_bytes': [torch.cuda.max_memory_reserved(j) for j in range(4)],
                           'peak_allocated_bytes': [torch.cuda.max_memory_allocated(j) for j in range(4)],
                           'resource_after': native_devices(loaded=True)}
                save(target / 'result.json', metrics)
                save(blind_dir / (blind + '.json'), {'case': name, 'candidate': rec['text'], 'natural_EOS': natural,
                                                    'candidate_sha256': sha(rec['text'].encode('utf-8'))})
                rows.append(metrics)
                save(ROOT / 'receipts' / f'{len(rows):03d}.json', metrics)
                print(f'REPLY {len(rows)}/{PLAN["max_calls"]} {name} EOS={int(natural)}', flush=True)
            except Exception:
                save(target / 'failure.json', {'trace': traceback.format_exc(), 'forward_attempts': calls[0]})
                save(PUBLIC / 'run-failure.json', {'case': name, 'arm': arm, 'trace': traceback.format_exc(), 'forward_attempts': calls[0]})
                raise
            finally:
                handle.remove()
                torch.cuda.empty_cache()
                # Store a review-order-independent mapping separately, never as model input.
                tmp = ROOT / '.blind-map.tmp'
                save(tmp, mapping)
                tmp.replace(ROOT / 'blind-map.json')
    save(PUBLIC / 'terminal.json', {'status': 'completed', 'calls': len(rows), 'natural_EOS': sum(r['natural_EOS'] for r in rows),
                                   'wall_seconds_since_lease': time.time() - load(PUBLIC / 'lease.json')['after']['checked_at'],
                                   'gpu_process_identity': identity(), 'GUI_calls': 0, 'Flash_calls': 0, 'score_calls': 0,
                                   'native_call_manifest_sha256': sha(canonical(rows))})


if __name__ == '__main__':
    p, mp, m = check_sources()
    PUBLIC.mkdir(exist_ok=True)
    if sys.argv[1:] == ['prepare']:
        prepare_cases(p, mp, m)
    elif sys.argv[1:] == ['run']:
        (ROOT / 'receipts').mkdir(exist_ok=False)
        run_model(p, mp, m)
    else:
        raise ValueError('Explicit prepare/run required')
