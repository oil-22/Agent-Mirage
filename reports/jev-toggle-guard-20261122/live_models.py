"""New isolated native Flash and 27B inference workers; no reusable context or launches."""

import base64
import inspect
import io
import math
import os
from pathlib import Path
import re
import sys
import time

from live_common import canonical, hash_bytes, load, process, save, serve, sha, verify_input
from live_lease import admit, worker_lease
from toggle_prompt import QUESTION as TOGGLE_QUESTION, targeted_request

ROOT = Path(__file__).resolve().parent


def png(url):
    assert url.startswith('data:image/png;base64,')
    raw = base64.b64decode(url.split(',', 1)[1], validate=True)
    assert raw.startswith(b'\x89PNG\r\n\x1a\n')
    return raw


def tensor(v, torch, copy_values=False):
    v = v.detach().cpu().contiguous()
    row = {'shape': list(v.shape), 'dtype': str(v.dtype), 'sha256': hash_bytes(v.view(torch.uint8).numpy().tobytes())}
    if copy_values:
        row['values'] = v.tolist()
    return row


def state_proof(root, modelpath, policy):
    parent = Path(load(root / 'runtime-provenance.json')['previous_model_attempt'])
    source = load(parent / 'postexit-seal.json')
    assert source['primary/actual-state.json'] == policy['archived_state_sha256']
    for k in ('primary/actual-state.json', 'primary/checkpoint-admission.json'):
        assert sha(parent / k) == source[k]
    stats = load(parent / 'primary/checkpoint-admission.json')['weight_stat_continuity']
    for row in stats:
        s = (modelpath / row['file']).stat()
        assert (s.st_size, s.st_mtime_ns, s.st_ino) == (row['bytes'], row['mtime_ns'], row['inode']), row['file']
    return {row['name']: row for row in load(parent / 'primary/actual-state.json')}, source, stats


class Primary:
    def __init__(self, out, lease, plan):
        save(out / 'admission.json', admit(lease, 'primary', loaded=False))
        import torch
        import transformers
        from transformers import AutoModelForImageTextToText, AutoProcessor

        sys.path.insert(0, str(ROOT / 'release'))
        from defense.qwen_backend import LocalQwen

        self.torch, self.out, self.lease, self.plan = torch, out, lease, plan
        self.calls = 0
        ref = load(ROOT / 'primary-reference.json')
        modelpath = Path(ref['primary_model'])
        runtime = load(ref['primary_expected_runtime'])
        assert sha(ROOT / 'release/defense/qwen_backend.py') == ref['primary_backend_sha256']
        assert sha(ref['primary_native_layout_receipt']) == ref['primary_native_layout_receipt_sha256']
        assert torch.__version__ == runtime['torch'] and transformers.__version__ == runtime['transformers']
        for name, expected in runtime['metadata_sha256'].items():
            assert sha(modelpath / name) == expected
        policy = load(ROOT / 'four-card-placement.json')
        assert policy['cuts'] == [0, 8, 28, 48, 64] and torch.cuda.device_count() == 4
        expected, seal, stamps = state_proof(ROOT, modelpath, policy)
        save(out / 'checkpoint.json', {'parent_state_sha256': policy['archived_state_sha256'], 'weight_stat_continuity': stamps,
                                       'parent_admission_sha256': seal['primary/checkpoint-admission.json'], 'metadata': runtime['metadata_sha256']})
        started = time.monotonic()
        torch.set_num_threads(4)
        for j in range(4):
            torch.cuda.set_per_process_memory_fraction(.87, j)
        model = AutoModelForImageTextToText.from_pretrained(modelpath, dtype=torch.bfloat16, attn_implementation='sdpa',
                    device_map=policy['device_map'], max_memory={j: '20GiB' for j in range(4)},
                    local_files_only=True, trust_remote_code=True).eval()
        processor = AutoProcessor.from_pretrained(modelpath, local_files_only=True, trust_remote_code=True)
        assert type(model).__name__ == runtime['class']
        assert sha(Path(inspect.getfile(type(model)))) == load(ref['primary_native_layout_receipt'])['native_source_sha256']
        assert model.config.text_config.num_hidden_layers == 64 and model.config._attn_implementation == 'sdpa'

        def place(name):
            d, = (value for prefix, value in policy['device_map'].items() if name == prefix or name.startswith(prefix + '.'))
            return 'cuda:' + str(d)

        observed = []
        state = model.state_dict()
        assert set(state) == set(expected)
        for name, t in state.items():
            data = {'name': name, 'shape': list(t.shape), 'dtype': str(t.dtype), 'bytes': t.element_size()*t.numel(),
                    'device': str(t.device)}
            assert all(data[k] == expected[name][k] for k in ('shape', 'dtype', 'bytes')) and data['device'] == place(name)
            observed.append(data)
        save(out / 'actual-state.json', observed)
        del state
        for name, buf in list(model.named_buffers()):
            target = place(name)
            if buf.device.type == 'cpu':
                scope, prop = name.rsplit('.', 1)
                owner = model.get_submodule(scope)
                assert prop in owner._non_persistent_buffers_set
                moved = buf.to(target)
                assert torch.equal(moved.cpu(), buf)
                owner._buffers[prop] = moved
            else:
                assert str(buf.device) == target
        assert all(v.dtype == torch.bfloat16 for v in model.parameters() if v.is_floating_point())
        self.engine = LocalQwen.__new__(LocalQwen)
        self.engine.model, self.engine.processor, self.engine.torch = model, processor, torch
        self.template = load(ROOT / 'actor-template.json')
        self.loaded = {'role': 'primary', 'model': str(modelpath), 'process': process(), 'actual_cls': type(model).__name__,
                       'load_seconds': time.monotonic()-started, 'torch': torch.__version__, 'transformers': transformers.__version__,
                       'BF16': True, 'SDPA': True, 'state_entries': len(observed), 'placement': policy,
                       'compute': admit(lease, 'primary', loaded=True)}
        save(out / 'loaded.json', self.loaded)

    def request(self, data):
        assert set(data) == {'request_id', 'body', 'images'} and re.fullmatch('[0-9a-f]{32}', data['request_id'])
        assert self.calls < len(self.plan['cases']) == self.plan['max_primary_calls'] == 36
        body = data['body']
        assert set(body) == set(self.template)
        assert all(v == self.template[k] for k, v in body.items() if k != 'messages')
        assert body['messages'][0] == self.template['messages'][0]
        assert [row['role'] for row in body['messages']] == ['system', 'user', 'assistant', 'user']
        assert body['max_tokens'] == self.plan['primary_max_output'] == 2048
        images = [hash_bytes(png(p['image_url']['url'])) for row in body['messages'] if isinstance(row['content'], list)
                  for p in row['content'] if p['type'] == 'image_url']
        assert images == data['images'] and len(images) == 2
        dest = self.out / data['request_id']; dest.mkdir()
        save(dest / 'wire.json', data)
        admission = admit(self.lease, 'primary', loaded=True)
        torch, engine = self.torch, self.engine
        model = engine.model
        from PIL import Image
        converted = []
        # Independently preprocess the exact received body as a reference, then
        # compare the actual native generation's first forward tensors with it.
        for row in body['messages']:
            blocks = row['content'] if isinstance(row['content'], list) else [{'type': 'text', 'text': row['content']}]
            content = []
            for p in blocks:
                if p['type'] == 'image_url':
                    image = Image.open(io.BytesIO(png(p['image_url']['url']))).convert('RGB')
                    content.append({'type': 'image', 'image': image})
                else:
                    assert p['type'] == 'text'
                    content.append(p)
            converted.append({'role': row['role'], 'content': content})
        expected = engine.processor.apply_chat_template(converted, add_generation_prompt=True, tokenize=True,
                    return_dict=True, return_tensors='pt', tools=None, **body['chat_template_kwargs'])
        cpu = {k: tensor(v, torch, k == 'image_grid_thw') for k, v in expected.items()}
        assert cpu['image_grid_thw']['shape'] == [2, 3] and cpu['input_ids']['shape'][0] == 1
        del expected
        save(dest / 'expected-inputs.json', cpu)
        first, count = {}, 0

        def hook(_module, _args, kw):
            nonlocal count
            count += 1
            if count == 1:
                previous = kw.get('past_key_values')
                assert previous is None or previous.get_seq_length() == 0, 'Cross-request KV detected'
                first.update({k: tensor(kw[k], torch, k == 'image_grid_thw') for k in cpu})
                save(dest / 'first-forward.json', first)
                assert first == cpu

        save(dest / 'start.json', {'owned_compute': admission, 'at_ns': time.monotonic_ns()})
        for j in range(4):
            torch.cuda.reset_peak_memory_stats(j)
        h = model.register_forward_pre_hook(hook, with_kwargs=True)
        self.calls += 1
        try:
            try:
                engine.generate(body['messages'], 2048, dest / 'native-generation.json', seed=42, original_body=body)
            except RuntimeError:
                assert (dest / 'native-generation.json').is_file() and load(dest / 'native-generation.json')['hit_output_cap']
        finally:
            h.remove()
        rec = load(dest / 'native-generation.json')
        assert first and rec['request_messages_sha256'] == hash_bytes(canonical(body['messages']))
        assert tensor(torch.tensor([rec['input_ids']], dtype=torch.int64), torch) == first['input_ids']
        eos = rec['generation_config']['eos_token_id']
        eos = [eos] if isinstance(eos, int) else eos
        assert rec['generation_config']['max_new_tokens'] == 2048 and rec['generation_config']['do_sample'] is False
        result = {'request_id': data['request_id'], 'messages_sha256': rec['request_messages_sha256'],
                  'body_sha256': hash_bytes(canonical(body)), 'wire_sha256': sha(dest / 'wire.json'),
                  'ordered_images': images, 'current_image_sha256': images[-1], 'first_forward': first,
                  'forward_count': count, 'natural_eos': bool(rec['generated_ids'] and rec['generated_ids'][-1] in eos and not rec['hit_output_cap']),
                  'input_tokens': len(rec['input_ids']), 'output_tokens': len(rec['generated_ids']), 'seconds': rec['seconds'],
                  'peak_bytes_per_logical_device': [torch.cuda.max_memory_allocated(j) for j in range(4)],
                  'reply_sha256': sha(dest / 'native-generation.json'), 'text': rec['text'], 'output_cap': rec['hit_output_cap']}
        save(dest / 'result.json', result)
        return result


class Flash:
    def __init__(self, out, lease, plan):
        save(out / 'admission.json', admit(lease, 'flash', loaded=False))
        import torch
        import transformers
        from PIL import Image
        from resource_guard import checkpoint
        from wire_contract import decode_request, native_request as original
        from temporal_request import native_request as temporal, QUESTION_ID, png_size

        self.torch, self.Image, self.out, self.lease, self.plan = torch, Image, out, lease, plan
        self.decode, self.original, self.temporal = decode_request, original, temporal
        self.question, self.png_size = QUESTION_ID, png_size
        self.config, self.contract = load(ROOT / 'service-config.json'), load(ROOT / 'gate-contract.json')
        assert self.config['revision'] == self.contract['revision'] == plan['revision']
        before = checkpoint(self.config, ROOT)
        save(out / 'checkpoint-before.json', before)
        assert torch.__version__.split('+')[0] == '2.14.0' and transformers.__version__ == '5.17.0'
        assert torch.cuda.device_count() == 1
        torch.set_num_threads(4)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        folder = Path(self.config['model_dir'])
        sys.path.insert(0, str(folder / 'source/src'))
        from pplx_decider import Decider, protocol
        assert Path(inspect.getfile(Decider)).resolve() == folder / 'source/src/pplx_decider/model.py'
        self.protocol = protocol
        start = time.monotonic()
        self.engine = Decider.from_pretrained(folder, device='cuda:0', fast=False, cpu_threads=4)
        torch.cuda.synchronize()
        for m in (self.engine.backbone, self.engine.readout):
            assert all(str(t.device) == 'cuda:0' for t in [*m.parameters(), *m.buffers()])
            assert all(t.dtype == torch.bfloat16 for t in m.parameters() if t.is_floating_point())
        assert checkpoint(self.config, ROOT) == before
        self.loaded = {'role': 'flash', 'revision': self.config['revision'], 'process': process(), 'device': 'cuda:0',
                       'BF16': True, 'native_sdpa': True, 'fast': False, 'load_seconds': time.monotonic()-start,
                       'torch': torch.__version__, 'transformers': transformers.__version__, 'compute': admit(lease, 'flash', loaded=True)}
        save(out / 'loaded.json', self.loaded)

    def request(self, data):
        assert set(data) == {'request_id', 'kind', 'body'} and re.fullmatch('[0-9a-f]{32}', data['request_id'])
        key, mode, body = data['request_id'], data['kind'], data['body']
        out = self.out / key; out.mkdir()
        save(out / 'wire.json', data)
        if mode == 'quality':
            wire, raw = self.decode(canonical(body))
            assert key == wire['request_id']
            req = self.original(self.contract, self.Image.open(io.BytesIO(raw)))
            question = 'usable'
            raws = [raw]
        else:
            assert mode in ('temporal','toggle_check') and set(body) == {'previous', 'action', 'current'}
            raws = [png(body[k]) for k in ('previous', 'current')]
            if mode == 'temporal':
                req = self.temporal(raws[0], body['action'], raws[1]); question = self.question
            else:
                req = targeted_request(raws[0], body['action'], raws[1]); question = TOGGLE_QUESTION
        assert all(self.png_size(raw) == tuple(self.plan['viewport']) for raw in raws)
        img_hashes = [hash_bytes(raw) for raw in raws]
        trace_req = {**req, 'images': [{'sha256': k} for k in img_hashes]}
        save(out / 'native-request.json', trace_req)
        admission = admit(self.lease, 'flash', loaded=True)
        torch, engine = self.torch, self.engine
        (packed,) = engine.encoder.plan(req, engine.max_length)
        # Encoded.counts describes answer choices per question, not images.
        assert packed.counts == (2,) and packed.keys == (question,) and packed.markers.numel() == 1
        assert tuple(packed.image_grid_thw.shape) == (len(raws), 3)
        chunks = list(map(math.prod, packed.image_grid_thw.tolist()))
        pieces = packed.pixel_values.split(chunks, dim=0)
        pixel_slices = []
        for i, part in enumerate(pieces):
            (single,) = engine.encoder.plan({**req, 'images': [req['images'][i]]}, engine.max_length)
            assert torch.equal(part, single.pixel_values) and torch.equal(packed.image_grid_thw[i], single.image_grid_thw[0])
            pixel_slices.append(tensor(part, torch))
        expected = {k: tensor(v, torch, k in ('input_ids', 'image_grid_thw')) for k, v in
                    self.protocol.left_pad([packed], engine.encoder.pad_id).items()}
        save(out / 'expected-inputs.json', {'tensors': expected, 'ordered_pixel_slices': pixel_slices})
        forward, raw_readouts = [], []

        def pre(_module, _args, kw):
            assert kw.get('past_key_values') is None and kw.get('use_cache') is False
            actual = {k: tensor(v, torch, k in ('input_ids', 'image_grid_thw')) for k, v in kw.items() if isinstance(v, torch.Tensor)}
            forward.append(actual)
            assert actual == expected

        def post(_module, _args, val):
            raw_readouts.append(val.detach().float().cpu().tolist())

        save(out / 'start.json', {'owned_compute': admission, 'at_ns': time.monotonic_ns()})
        torch.cuda.reset_peak_memory_stats()
        h1 = engine.backbone.register_forward_pre_hook(pre, with_kwargs=True)
        h2 = engine.readout.register_forward_hook(post)
        start = time.monotonic()
        try:
            native = engine.decide(req)
            torch.cuda.synchronize()
        finally:
            h1.remove(); h2.remove()
            save(out / 'actual-forward.json', {'tensors_per_forward': forward, 'native_readout': raw_readouts, 'past_key_values': None, 'use_cache': False})
        elapsed = time.monotonic() - start
        assert len(forward) == len(raw_readouts) == 1
        answer = native['answers'][question]
        assert set(answer['probabilities']) == {'YES', 'NO'} and answer['choice'] == max(answer['probabilities'], key=answer['probabilities'].__getitem__)
        assert native['usage'] == {'input_tokens': packed.length, 'output_tokens': 0, 'sequences': 1}
        result = {'request_id': key, 'kind': mode, 'ordered_images': img_hashes, 'choice': answer['choice'],
                  'probabilities': answer['probabilities'], 'native_result': native, 'revision': self.config['revision'],
                  'quality_contract_sha256': sha(ROOT / 'gate-contract.json') if mode == 'quality' else None,
                  'wire_sha256': sha(out / 'wire.json'), 'native_request_sha256': sha(out / 'native-request.json'),
                  'forward_sha256': sha(out / 'actual-forward.json'), 'native_seconds_with_trace': elapsed,
                  'peak_allocated_bytes': torch.cuda.max_memory_allocated()}
        save(out / 'result.json', result)
        return result


if __name__ == '__main__':
    mode, = sys.argv[1:]
    assert os.getuid() == 1033 and verify_input(ROOT)['mode'] == 'live'
    run = ROOT / 'run'
    lease = worker_lease(run)
    out = run / mode
    out.mkdir()
    plan = load(ROOT / 'live_plan.json')
    service = {'primary': Primary, 'flash': Flash}[mode](out, lease, plan)
    serve({'ready': lambda _: service.loaded, 'infer': service.request})
