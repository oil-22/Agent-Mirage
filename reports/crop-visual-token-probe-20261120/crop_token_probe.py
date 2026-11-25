"""Read-only CPU replay of native 27B preprocessing; no model is constructed."""
import argparse
import ast
import base64
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1] / 'jev-defense-four-gpu-20261106'
REMOTE_PROJECT = '/home/researcher/jev-defense-four-gpu-20261106'
REMOTE_ARCHIVES = '/data/researcher/jev-defense-four-gpu-20261106'
ENV_PYTHON = '/opt/whz/conda-envs/webmall-vlm/bin/python'
BACKEND = 'release/defense/qwen_backend.py'
LINKED11 = 'flash-native-source-loop-20261116-linked11'
SCALE12 = 'flash-four-mode-scale10-20261116-12'
PACKAGES = {
    LINKED11: ('preparation-1794820110211682400', 'c6b18f57e714100a2449a4c18a8f04de9cde014d95c587b711e72630db143e70'),
    SCALE12: ('preparation-1794835402751575200', '874a87681734dbe6ca65e2e76f7512638860b40897e3b80fad08e9bbcd23122b'),
}
T114 = ('trajectory-audit-native16b-T114-stale_replace-gate-1794825040707335200',
        '01294d79f1a176696c96882ad62a2b9eb997c1a0421f49b5a5c1726f9e5f578a')
SAMPLES = [
    ('T125-d01', LINKED11, ('trajectory-audit-native16b-T125-clean_control-gate-1794826534465392600',
                             '2ae2940205eb3d47c3c81698b7dd69c3e5b26280e75ff04a392f63e5717b5136'), 'primary-000.json'),
    ('T114-d02', LINKED11, T114, 'primary-001.json'),
    ('T114-d20', LINKED11, T114, 'primary-019.json'),
    ('T017-d40', SCALE12, ('trajectory-audit-scale10-T017-silent_drop-gate-1794844191361804900',
                           '7e4a5934481209679c4b9ee1f14ab6720ef9d5e5d47314b624b8b1dd5b1f6d0b'), 'primary-039.json'),
]
ARMS = ('original', 'append_duplicate', 'append_zoom', 'append_raw_crop', 'replace_raw_crop', 'replace_zoom')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def require(condition, label):
    if not condition:
        raise RuntimeError(label)


def make_plan():
    packages, cases = {}, []
    for campaign, (preparation, manifest_sha) in PACKAGES.items():
        package = PROJECT / campaign / preparation / 'package'
        manifest_path = package / 'manifest.json'
        require(sha_file(manifest_path) == manifest_sha, campaign + ' local manifest SHA')
        member_shas = load(manifest_path)['files']
        for name in (BACKEND, 'primary-reference.json', 'primary_server.py'):
            require(sha_file(package / name) == member_shas[name], name + ' local source SHA')
        reference = load(package / 'primary-reference.json')
        require(reference['primary_backend_sha256'] == member_shas[BACKEND], 'primary backend binding')
        packages[campaign] = {
            'root': f'{REMOTE_PROJECT}/runtime-preparation/{campaign}',
            'manifest_sha256': manifest_sha, 'reference': reference,
            'source_sha256': {name: member_shas[name] for name in (BACKEND, 'primary-reference.json', 'primary_server.py')},
        }
    for name, campaign, (audit_root, audit_seal), member in SAMPLES:
        source = PROJECT / campaign / audit_root
        require(sha_file(source / 'seal.json') == audit_seal, name + ' local audit seal SHA')
        member_sha = sha_file(source / member)
        require(load(source / 'seal.json')[member] == member_sha, name + ' local audit member SHA')
        records = load(source / member)['result']['requests']
        require(len(records) == 1, name + ' one archived request')
        row = records[0]
        require(row['root'].startswith(f'{REMOTE_ARCHIVES}/{campaign}/model-attempt-01/primary/requests/'), name + ' archive path')
        require(row['actual_tensor_files_verified'] and row['exact_full_history_preserved'], name + ' original delivery audit')
        keys = ('root', 'request_id', 'run_id', 'decision', 'seal_sha256', 'wire_sha256', 'body_sha256',
                'input_tokens', 'current_image_sha256', 'all_image_sha256s', 'history_messages')
        cases.append({'case': name, 'campaign': campaign, 'local_audit': str(source / member),
                      'local_audit_seal_sha256': audit_seal, 'local_audit_member_sha256': member_sha,
                      **{key: row[key] for key in keys}})
    return {'probe_source_sha256': sha_file(Path(__file__)), 'packages': packages, 'cases': cases, 'arms': ARMS,
            'crop_rule': 'fixed middle half of width and height, floor multiples of one quarter; zoom via Pillow Lanczos back to original size',
            'placement': 'append immediately after the current delivered image, or replace it in diagnostic arms; do not add text or alter history'}


def preprocess_from(backend, image_class):
    """Take the checked native preprocessing statements; exclude all generation statements."""
    tree = ast.parse(backend.read_bytes(), filename=str(backend))
    engine = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'LocalQwen')
    method = next(n for n in engine.body if isinstance(n, ast.FunctionDef) and n.name == 'generate')
    end = next(i for i, s in enumerate(method.body) if isinstance(s, ast.Assign) and
               [n.id for n in s.targets if isinstance(n, ast.Name)] == ['inputs'])
    call = method.body[end].value
    require(isinstance(call, ast.Call) and ast.unparse(call.func) == 'self.processor.apply_chat_template', 'native preprocessing cutoff')
    method.name = 'preprocess'
    method.body = method.body[:end + 1] + [ast.Return(value=ast.Name(id='inputs', ctx=ast.Load()))]
    fragment = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
    namespace = {'Image': image_class, 'base64': base64, 'copy': copy, 'io': io}
    exec(compile(fragment, str(backend), 'exec'), namespace)
    return namespace['preprocess'], sha(ast.dump(fragment).encode('utf-8'))


def tensor_sha(t):
    raw = t.detach().contiguous().numpy()
    return sha(memoryview(raw).cast('B'))


def describe(inputs, image_id, start_id, end_id, patch, merge, current):
    ids = inputs['input_ids'][0].tolist()
    require(inputs['input_ids'].shape[0] == 1, 'single batch')
    require(inputs['attention_mask'][0].tolist() == [1] * len(ids), 'attention mask has no padding')
    start = [i for i, token in enumerate(ids) if token == start_id]
    end = [i for i, token in enumerate(ids) if token == end_id]
    grids = inputs['image_grid_thw'].tolist()
    require(len(start) == len(end) == len(grids) == current[-1] + 1, 'one vision span per image')
    pixels = inputs['pixel_values']
    spans, other, con = [], [], 0
    cursor = 0
    for l, r, grid in zip(start, end, grids):
        n = math.prod(grid)
        count = n // (merge * merge)
        require(cursor <= l < r and n % (merge * merge) == 0 and r - l - 1 == count, 'grid/vision span mismatch')
        require(ids[l + 1:r] == [image_id] * count, 'native image placeholder run')
        other.extend(ids[cursor:l])
        cursor = r + 1
        spans.append({'image_grid_thw': grid, 'processor_dim_wh': [grid[2] * patch, grid[1] * patch],
                      'visual_tokens': count, 'pixel_values_sha256': tensor_sha(pixels[con:con + n])})
        con += n
    other.extend(ids[cursor:])
    require(con == pixels.shape[0] and image_id not in other, 'complete pixel/token coverage')
    total_visual = sum(s['visual_tokens'] for s in spans)
    current_visual = sum(spans[i]['visual_tokens'] for i in current)
    return {'total_tokens': len(ids), 'visual_tokens_all': total_visual, 'visual_tokens_current': current_visual,
            'visual_tokens_history': total_visual - current_visual, 'visual_share_all_pct': total_visual * 100 / len(ids),
            'visual_share_current_pct': current_visual * 100 / len(ids), 'vision_boundary_tokens': len(start) + len(end),
            'other_tokens': len(other), 'other_ids_sha256': sha(canonical(other)), 'image_spans': spans}, other


def trial(case, engine, prepare, processor, config, Image):
    path, name = Path(case['root']), case['case']
    require(sha_file(path / 'seal.json') == case['seal_sha256'], name + ' remote request seal')
    seal = load(path / 'seal.json')
    for file in ('body.json', 'wire-request.bin', 'prepared.json', 'first-forward.json', 'actual-generation.json'):
        require(sha_file(path / file) == seal[file], name + ' ' + file + ' sealed file')
    body, wire = load(path / 'body.json'), load(path / 'wire-request.bin')
    require(wire['body'] == body and sha(canonical(body)) == case['body_sha256'], name + ' full body/wire binding')
    require(seal['wire-request.bin'] == case['wire_sha256'], name + ' historical wire SHA')
    require((wire['request_id'], wire['run_id'], wire['decision_index']) == (case['request_id'], case['run_id'], case['decision']), name + ' historical request identity')
    gen = load(path / 'actual-generation.json')
    require(gen['natural_EOS'] and gen['input_tokens'] == case['input_tokens'], name + ' historical generation input length')
    messages = body['messages']
    image_spots, image_bytes = [], []
    for i, msg in enumerate(messages):
        if isinstance(msg['content'], list):
            for j, block in enumerate(msg['content']):
                if block['type'] == 'image_url':
                    url = block['image_url']
                    url = url['url'] if isinstance(url, dict) else url
                    image_bytes.append(base64.b64decode(url.split(',', 1)[1], validate=True))
                    image_spots.append((i, j))
    require(len(messages) == case['history_messages'] and [sha(b) for b in image_bytes] == case['all_image_sha256s'], name + ' complete ordered history images')
    image_message, image_position = image_spots[-1]
    require(image_message == len(messages) - 1 and messages[-1]['role'] == 'user' and
            all(i != image_message for i, _ in image_spots[:-1]) and sha(image_bytes[-1]) == case['current_image_sha256'], name + ' unique current image')
    original = Image.open(io.BytesIO(image_bytes[-1])).convert('RGB')
    w, h = original.size
    box = (w // 4, h // 4, (3 * w) // 4, (3 * h) // 4)
    crop = original.crop(box)
    zoom = crop.resize(original.size, Image.Resampling.LANCZOS)

    def make_image_block(image):
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        return {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')}}

    original_block = messages[image_message]['content'][image_position]
    variants = {'original': None, 'append_duplicate': original_block, 'append_zoom': make_image_block(zoom),
                'append_raw_crop': make_image_block(crop), 'replace_raw_crop': make_image_block(crop), 'replace_zoom': make_image_block(zoom)}
    baseline_sealed, first = load(path / 'prepared.json'), load(path / 'first-forward.json')
    rows, baseline_other, base_checks = {}, None, {}
    original_count = len(image_spots)
    for arm, image_block in variants.items():
        modified = copy.deepcopy(body)
        content = modified['messages'][image_message]['content']
        indices = [original_count - 1]
        if arm.startswith('append_'):
            content.insert(image_position + 1, image_block)
            indices += [original_count]
        elif arm.startswith('replace_'):
            content[image_position] = image_block
        require(modified['messages'][:-1] == messages[:-1], name + ' input history message integrity')
        inputs = prepare(engine, modified['messages'], 2048, None, original_body=modified)
        require(all(t.device.type == 'cpu' for t in inputs.values()), 'CPU tensors only')
        row, other = describe(inputs, config['image_token_id'], config['vision_start_token_id'], config['vision_end_token_id'],
                              processor.image_processor.patch_size, processor.image_processor.merge_size, indices)
        row['current_image_grids'] = [row['image_spans'][i]['image_grid_thw'] for i in indices]
        row['input_ids_sha256'] = tensor_sha(inputs['input_ids'])
        if arm == 'original':
            require(row['total_tokens'] == case['input_tokens'] and set(inputs) == set(baseline_sealed) == set(first), name + ' baseline key/length match')
            baseline_other = other
            for k, t in inputs.items():
                a, b = baseline_sealed[k], first[k]
                actual = {'shape': list(t.shape), 'dtype': str(t.dtype), 'bytes': t.numel() * t.element_size(), 'sha256': tensor_sha(t)}
                require(all(a[q] == b[q] == value for q, value in actual.items()), name + ' baseline vs historical first forward ' + k)
                pa, pb = path / a['file'], path / b['file']
                require(sha_file(pa) == actual['sha256'] and seal[a['file']] == seal[b['file']] == actual['sha256'] and
                        (pa.samefile(pb) or sha_file(pb) == actual['sha256']), name + ' raw baseline tensor seal ' + k)
                base_checks[k] = actual
        else:
            require(other == baseline_other, name + ' equal non-vision IDs ' + arm)
            keep = original_count if arm.startswith('append_') else original_count - 1
            require(row['image_spans'][:keep] == rows['original']['image_spans'][:keep], name + ' exact unchanged native history/full image pixels ' + arm)
        rows[arm] = row
        del inputs
    require(rows['append_duplicate']['image_spans'][-1] == rows['original']['image_spans'][-1], name + ' duplicate pixels match')
    require(rows['append_duplicate']['total_tokens'] == rows['append_zoom']['total_tokens'] and
            rows['append_duplicate']['current_image_grids'] == rows['append_zoom']['current_image_grids'] and
            rows['append_duplicate']['image_spans'][-1]['pixel_values_sha256'] != rows['append_zoom']['image_spans'][-1]['pixel_values_sha256'], name + ' token-matched but different image control')
    for row in rows.values():
        row['delta_total_tokens'] = row['total_tokens'] - rows['original']['total_tokens']
        row['delta_current_visual_tokens'] = row['visual_tokens_current'] - rows['original']['visual_tokens_current']
        row['delta_current_visual_share_pp'] = row['visual_share_current_pct'] - rows['original']['visual_share_current_pct']
    return {**case, 'original_image_wh': list(original.size), 'crop_box_xyxy_exclusive_right_bottom': list(box),
            'raw_crop_wh': list(crop.size), 'zoom_wh': list(zoom.size),
            'raw_crop_rgb_sha256': sha(crop.tobytes()), 'zoom_rgb_sha256': sha(zoom.tobytes()),
            'baseline_exact_prepared_and_first_forward': base_checks, 'arms': rows}


def run_remote(plan):
    require(os.environ.get('CUDA_VISIBLE_DEVICES') == '' and os.environ.get('HF_HUB_OFFLINE') == '1', 'CPU-only/offline worker envelope')
    import PIL
    from PIL import Image
    import torch
    import transformers
    from transformers import AutoProcessor

    torch.set_num_threads(4)
    require(not torch.cuda.is_available() and torch.cuda.device_count() == 0, 'GPU must be invisible')
    references = [v['reference'] for v in plan['packages'].values()]
    ref = references[0]
    require(all(r == ref for r in references), 'same primary processor reference across campaigns')
    prepare, packages = {}, {}
    for tag, item in plan['packages'].items():
        root = Path(item['root'])
        require(sha_file(root / 'manifest.json') == item['manifest_sha256'], tag + ' actual run package manifest')
        for rel, digest in item['source_sha256'].items():
            require(sha_file(root / rel) == digest, tag + ' remote source ' + rel)
        prepare[tag], fragment_sha = preprocess_from(root / BACKEND, Image)
        packages[tag] = {**item, 'native_preprocess_ast_sha256': fragment_sha}
    runtime = Path(ref['primary_expected_runtime'])
    expected = load(runtime)
    model = Path(ref['primary_model'])
    require(expected['model_path'] == str(model) and torch.__version__ == expected['torch'] and transformers.__version__ == expected['transformers'], 'original native Python runtime identity')
    for k, v in expected['metadata_sha256'].items():
        require(sha_file(model / k) == v, 'primary checkpoint metadata ' + k)
    reference_metadata = Path(ref['primary_native_layout_receipt'])
    require(sha_file(reference_metadata) == ref['primary_native_layout_receipt_sha256'], 'original checkpoint metadata receipt')
    historical_meta = Path(load(reference_metadata)['meta_root'])
    meta_seal = load(historical_meta / 'seal.json')
    metadata = {}
    for name in ('config.json', 'preprocessor_config.json', 'processor_config.json', 'chat_template.jinja', 'tokenizer.json',
                 'tokenizer_config.json', 'added_tokens.json', 'special_tokens_map.json', 'merges.txt', 'vocab.json', 'video_preprocessor_config.json'):
        if (model / name).is_file():
            metadata[name] = sha_file(model / name)
            if name in meta_seal:
                require(meta_seal[name] == metadata[name], 'historical native model metadata ' + name)
    config = load(model / 'config.json')
    processor = AutoProcessor.from_pretrained(model, local_files_only=True, trust_remote_code=True)
    require(processor.image_token_id == config['image_token_id'], 'native image token id')
    engine = SimpleNamespace(processor=processor)
    started = time.time()
    results = []
    for case in plan['cases']:
        results.append(trial(case, engine, prepare[case['campaign']], processor, config, Image))
        print(f"{case['case']}: historical input tensors matched and {len(ARMS)} CPU conditions processed", file=sys.stderr, flush=True)
    print(json.dumps({'schema': 'native-27b-crop-token-probe-v1', 'probe_source_sha256': plan['probe_source_sha256'],
                      'model_path_as_deployed': str(model), 'runtime_receipt_sha256': sha_file(runtime),
                      'packages': packages, 'processor': type(processor).__name__, 'image_processor': type(processor.image_processor).__name__,
                      'torch': torch.__version__, 'transformers': transformers.__version__, 'pillow': PIL.__version__,
                      'resize_size': dict(processor.image_processor.size), 'model_metadata_sha256': metadata,
                      'patch_size': processor.image_processor.patch_size, 'merge_size': processor.image_processor.merge_size,
                      'special_token_ids': {k: config[k] for k in ('image_token_id', 'vision_start_token_id', 'vision_end_token_id')},
                      'crop_rule': plan['crop_rule'], 'placement': plan['placement'], 'arms': ARMS, 'cases': results,
                      'cpu_only': True, 'gpu_devices_visible': 0, 'weight_loads': 0, 'forward_calls': 0,
                      'gui_calls': 0, 'Flash_calls': 0, 'scoring_calls': 0, 'seconds_processor_trials': time.time() - started}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='run read-only CPU probe against existing 3090 archives via SSH')
    parser.add_argument('--linked-from', help='name of a preserved technical failure under this report directory')
    args = parser.parse_args()
    plan = make_plan()
    if args.linked_from:
        require(Path(args.linked_from).name == args.linked_from and args.linked_from.startswith('attempt-'), 'historical attempt name')
        prior = HERE / args.linked_from
        pins = load(prior / 'plan.json')
        require(sha_file(prior / 'probe-source.py') == pins['probe_source_sha256'], 'prior technical attempt source')
        plan['linked_technical_failure'] = {'directory': args.linked_from, 'seal_sha256': sha_file(prior / 'SHA256SUMS.txt')}
    if not args.run:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return
    attempt = HERE / f'attempt-{time.time_ns()}'
    attempt.mkdir()
    (attempt / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    source = Path(__file__).read_bytes()
    require(sha(source) == plan['probe_source_sha256'], 'probe source identity')
    (attempt / 'probe-source.py').write_bytes(source)
    payload = source + b'\nrun_remote(json.loads(' + repr(canonical(plan).decode('utf-8')).encode('utf-8') + b'))\n'
    command = ['ssh', '-p', '2223', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', 'researcher@192.0.2.11',
               f'env CUDA_VISIBLE_DEVICES= HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false '
               f'OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 {ENV_PYTHON} -B - --worker']
    try:
        process = subprocess.run(command, input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=420)
        code, stdout, stderr = process.returncode, process.stdout, process.stderr
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr = 124, exc.stdout or b'', exc.stderr or b''
    (attempt / 'stdout.log').write_bytes(stdout)
    (attempt / 'stderr.log').write_bytes(stderr)
    print(attempt)
    if code:
        print(stderr.decode('utf-8', errors='replace'), file=sys.stderr)
        raise SystemExit(code)
    data = json.loads(stdout)
    require(data['probe_source_sha256'] == plan['probe_source_sha256'], 'remote result source')
    require([row['case'] for row in data['cases']] == [row['case'] for row in plan['cases']], 'complete remote result rows')
    (attempt / 'result.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"{len(data['cases'])} historical requests x {len(data['arms'])} conditions; {data['seconds_processor_trials']:.2f}s CPU replay")


if __name__ == '__main__' and '--worker' not in sys.argv:
    main()
