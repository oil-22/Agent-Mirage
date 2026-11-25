"""New finite no-GUI four-GPU services. Never runs an old queue or gate.

Run only via the task lease holder/launcher with inherited UUID locks. Primary and
native Flash use separate pinned environments and one shared inference mutex.
"""
import argparse
import base64
from contextlib import contextmanager
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import inspect
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

from four_gpu_contract import (FLASH, FLASH_REVISION, canonical, digest,
                               identity_matches, primary_device_map, request_fingerprint,
                               validate_actor, validate_admission,
                               validate_decision, validate_layout,
                               validate_probabilities, validate_resource_group,
                               validate_frozen_wire, validate_observation)


def save(path, value):
    with path.open('x', encoding='utf8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def sha(path):
    return digest(path.read_bytes())


def identity(pid):
    proc = Path('/proc') / str(pid)
    stat = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': int(pid), 'uid': proc.stat().st_uid,
            'command': (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode().strip(),
            'start_ticks': stat[19]}


def check_inherited_locks(lease):
    supplied = {int(s) for s in os.environ['MIRAGE_GPU_LOCK_FDS'].split(',')}
    expected = {r['fd'] for r in lease['lock_records']}
    if supplied != expected:
        raise RuntimeError('All task UUID locks must be inherited, not reacquired')
    for row in lease['lock_records']:
        fd = row['fd']
        if (os.fstat(fd).st_ino != row['inode']
                or os.readlink('/proc/self/fd/' + str(fd)) != row['path']
                or 'lock:' not in Path('/proc/self/fdinfo', str(fd)).read_text()):
            raise RuntimeError('Inherited lock identity/held status mismatch')
    if not identity_matches(identity(lease['holder']['pid']), lease['holder']):
        raise RuntimeError('Task lease holder identity changed')


def resource_admission(lease, group_root, commands):
    check_inherited_locks(lease)
    registrations = []
    actual = {}
    for path in sorted((group_root / 'processes').glob('*.json')):
        row = json.loads(path.read_bytes())
        if row['role'] not in commands or row['identity']['command'] != ' '.join(commands[row['role']]):
            raise RuntimeError('Worker registration does not match sealed command')
        # A dead peer is excluded only if its process is truly absent; a live PID
        # with different identity is an error, never an authorized stale flag.
        if not Path('/proc', str(row['identity']['pid'])).exists():
            continue
        actual[row['identity']['pid']] = identity(row['identity']['pid'])
        registrations.append(row)
    lines = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid',
                                     '--format=csv,noheader,nounits'], text=True).splitlines()
    compute = [{'uuid': line.split(',')[0].strip(), 'pid': int(line.split(',')[1])}
               for line in lines if line.strip()]
    return validate_resource_group(lease, registrations, actual, compute)


@contextmanager
def serial_inference(lease, group_root, commands):
    import fcntl
    # Each worker independently opens this file. Inheriting the same flock open
    # description would NOT serialize related processes.
    with Path(lease['inference_lock']).open('a') as mutex:
        fcntl.flock(mutex, fcntl.LOCK_EX)
        resource_admission(lease, group_root, commands)
        try:
            yield
        finally:
            fcntl.flock(mutex, fcntl.LOCK_UN)


def memory(torch):
    return [{'logical_device': i, 'allocated_bytes': torch.cuda.memory_allocated(i),
             'reserved_bytes': torch.cuda.memory_reserved(i),
             'peak_allocated_bytes': torch.cuda.max_memory_allocated(i),
             'peak_reserved_bytes': torch.cuda.max_memory_reserved(i),
             'free_bytes': torch.cuda.mem_get_info(i)[0],
             'total_bytes': torch.cuda.mem_get_info(i)[1]}
            for i in range(torch.cuda.device_count())]


def reset_memory(torch):
    for i in range(torch.cuda.device_count()):
        torch.cuda.synchronize(i)
        torch.cuda.reset_peak_memory_stats(i)


def tensor_record(torch, tensor, keep_values=False):
    value = tensor.detach().cpu().contiguous()
    result = {'shape': list(value.shape), 'dtype': str(value.dtype),
              'sha256': digest(value.view(torch.uint8).numpy().tobytes())}
    if keep_values:
        result['values'] = value.tolist()
    return result


def audited_forward(torch, module, capture, raw_readout=False):
    def pre_hook(_module, args, kwargs):
        row = {'time': time.time(), 'tensors': {}}
        for key, value in kwargs.items():
            if isinstance(value, torch.Tensor):
                row['tensors'][key] = tensor_record(torch, value,
                                                   key in {'input_ids', 'image_grid_thw', 'video_grid_thw'})
        capture.append(row)
    def output_hook(_module, args, output):
        if isinstance(output, torch.Tensor):
            capture.append({'raw_readout': tensor_record(torch, output, True)})
    return (module.register_forward_hook(output_hook) if raw_readout else
            module.register_forward_pre_hook(pre_hook, with_kwargs=True))


def audit_tensors(torch, modules, expected_devices):
    records = []
    for prefix, module in modules:
        for name, value in list(module.named_parameters()) + list(module.named_buffers()):
            if value.device.type != 'cuda':
                raise RuntimeError('CPU/disk/meta model tensor is prohibited')
            records.append({'name': prefix + '.' + name, 'device': str(value.device),
                            'dtype': str(value.dtype), 'elements': value.numel(),
                            'bytes': value.numel() * value.element_size()})
    devices = sorted({row['device'] for row in records})
    if not records or devices != expected_devices:
        raise RuntimeError('Actual tensor device placement mismatch')
    return {'devices': devices, 'tensor_count': len(records),
            'tensor_bytes_by_device': {device: sum(r['bytes'] for r in records if r['device'] == device)
                                       for device in devices},
            'dtype_elements': {dtype: sum(r['elements'] for r in records if r['dtype'] == dtype)
                               for dtype in sorted({r['dtype'] for r in records})}}


def verify_flash_checkpoint(config):
    """Bind actual local files to the completed download plus new stable stats.

    The download already read and hashed every byte. A linked identity receipt
    records the stable file state after completion; large weights are checked by
    that state without repeating the full download audit. Native Python source is
    small and is additionally hashed here before and after its actual import/load.
    """
    model = Path(config['flash_model']).resolve(strict=True)
    completion_path = Path(config['flash_identity_receipt'])
    stable_path = Path(config['flash_stable_identity_receipt'])
    if (sha(completion_path) != config['flash_identity_receipt_sha256'] or
            sha(stable_path) != config['flash_stable_identity_receipt_sha256']):
        raise RuntimeError('Flash checkpoint identity receipt differs from sealed config')
    completion = json.loads(completion_path.read_bytes())
    stable = json.loads(stable_path.read_bytes())
    if (completion.get('status') != 'complete' or
            completion.get('revision') != FLASH_REVISION or
            stable.get('status') != 'identity_bound' or
            stable.get('revision') != FLASH_REVISION or
            Path(completion['checkpoint']).resolve(strict=True) != model or
            Path(stable['checkpoint']).resolve(strict=True) != model or
            Path(stable['completion_receipt']).resolve(strict=True) != completion_path.resolve(strict=True) or
            stable['completion_receipt_sha256'] != config['flash_identity_receipt_sha256']):
        raise RuntimeError('Flash checkpoint/revision/completion chain is unbound')
    completed = {row['file']: row for row in completion['files']}
    recorded = {row['file']: row for row in stable['files']}
    if (len(completed) != len(completion['files']) or len(recorded) != len(stable['files']) or
            not completed or set(completed) != set(recorded)):
        raise RuntimeError('Flash file identity lists differ or contain duplicates')
    actual = {str(p.relative_to(model)).replace('\\', '/')
              for p in model.rglob('*') if p.is_file()}
    if actual != set(completed):
        raise RuntimeError('Flash actual checkpoint file set differs from complete identity')
    source_sha = {}
    for name, row in completed.items():
        relative = Path(name)
        path = model / relative
        if (relative.is_absolute() or '..' in relative.parts or path.is_symlink() or
                not path.resolve(strict=True).is_relative_to(model)):
            raise RuntimeError('Flash checkpoint file escapes its identity root')
        stamp = path.stat()
        expected = recorded[name]
        if (expected['sha256'] != row['sha256'] or expected['bytes'] != row['bytes'] or
                expected['stat'] != {'dev': stamp.st_dev, 'ino': stamp.st_ino,
                                     'size': stamp.st_size, 'mtime_ns': stamp.st_mtime_ns} or
                stamp.st_size != row['bytes']):
            raise RuntimeError('Flash checkpoint file changed after complete byte verification')
        if relative.suffix == '.py':
            source_sha[name] = sha(path)
            if source_sha[name] != row['sha256']:
                raise RuntimeError('Flash native source bytes differ from pinned identity')
    if 'source/src/pplx_decider/model.py' not in source_sha:
        raise RuntimeError('Flash native model source is absent from identity')
    return {'checkpoint': str(model), 'file_count': len(completed),
            'completion_sha256': sha(completion_path), 'stable_identity_sha256': sha(stable_path),
            'source_sha256': source_sha, 'large_file_check': 'post-completion stable dev/ino/size/mtime_ns'}


def validate_native_state_records(actual, expected):
    by_name = {row['name']: row for row in actual}
    wanted = {row['name']: row for row in expected}
    if (len(by_name) != len(actual) or len(wanted) != len(expected) or
            set(by_name) != set(wanted) or any(name.startswith('mtp.') for name in by_name)):
        raise RuntimeError('Actual native state differs from the meta-proven architecture/no-MTP set')
    for name, row in by_name.items():
        if (not row['device'].startswith('cuda:') or
                any(row[key] != wanted[name][key] for key in ('shape', 'dtype', 'bytes'))):
            raise RuntimeError('Actual CUDA native state shape/dtype/bytes differs: ' + name)
    return {'actual_state_tensor_count': len(actual),
            'actual_state_total_bytes': sum(row['bytes'] for row in actual),
            'actual_native_state_layout_sha256': digest(canonical(actual)),
            'native_MTP_not_instantiated': True}


def verify_primary_native_state(config, engine):
    path = Path(config['primary_native_layout_receipt'])
    if sha(path) != config['primary_native_layout_receipt_sha256']:
        raise RuntimeError('Native parameter-placement receipt differs from sealed config')
    bound = json.loads(path.read_bytes())
    if (Path(bound['model']).resolve() != Path(config['primary_model']).resolve() or
            bound['layout_sha256'] != sha(Path(config['layout'])) or
            not bound['within_proposed_parameter_budgets']):
        raise RuntimeError('Native placement receipt does not bind this model/layout')
    source = Path(inspect.getfile(type(engine.model)))
    if sha(source) != bound['native_source_sha256']:
        raise RuntimeError('Actual instantiated native class source differs from original meta proof')
    meta_root = Path(bound['meta_root'])
    for name, expected in json.loads((meta_root / 'seal.json').read_bytes()).items():
        if sha(meta_root / name) != expected:
            raise RuntimeError('Native meta proof file changed')
    if sha(meta_root / 'receipt.json') != bound['meta_receipt_sha256']:
        raise RuntimeError('Native meta receipt chain differs')
    expected = json.loads((meta_root / 'meta-state.json').read_bytes())
    actual = [{'name': name, 'shape': list(value.shape), 'dtype': str(value.dtype),
               'device': str(value.device), 'bytes': value.numel() * value.element_size()}
              for name, value in engine.model.state_dict().items()]
    return {**validate_native_state_records(actual, expected),
            'primary_native_layout_receipt_sha256': sha(path),
            'primary_native_class_source_sha256': sha(source),
            'checkpoint_MTP_unused_bytes': bound['checkpoint_unused_native_MTP_bytes']}


def verify_original_dependencies(config):
    path = Path(config['primary_dependency_receipt'])
    if sha(path) != config['primary_dependency_receipt_sha256']:
        raise RuntimeError('Original dependency CPU evidence differs from sealed config')
    proof = json.loads(path.read_bytes())
    if (proof.get('status') != 'passed' or not proof['canonical_class_identical'] or
            not proof['all_dependency_bytes_stable'] or proof['weights_loaded'] or
            proof['model_generation'] or proof['GPU_allocations'] != 0 or proof['package_installed_or_modified']):
        raise RuntimeError('Original grammar dependency restore lacks exact CPU identity proof')
    deps = Path(proof['dependency_root'])
    actual = {str(p.relative_to(deps)): sha(p) for p in deps.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    if actual != proof['dependency_files']:
        raise RuntimeError('Historical isolated dependency files changed')
    integration_path = deps / 'lmformatenforcer/integrations/transformers.py'
    if sha(integration_path) != '223e56d56be3f60d14b270c6db6cfedd19000adefb22f9d3aeaf5925a6035f47':
        raise RuntimeError('Original canonical tokenizer compatibility identity differs')
    sys.path.insert(0, str(deps))
    import lmformatenforcer.integrations.transformers as integration
    from transformers.tokenization_utils_base import PreTrainedTokenizerBase
    if (Path(integration.__file__).resolve() != integration_path.resolve() or
            integration.PreTrainedTokenizerBase is not PreTrainedTokenizerBase):
        raise RuntimeError('Actual original grammar dependency import is not bound')
    return {'primary_dependency_receipt_sha256': sha(path), 'dependency_root': str(deps),
            'integration_sha256': sha(integration_path), 'dependency_file_count': len(actual),
            'original_grammar_functions_and_schema_unchanged': True}


def load_primary(a, config, layout, root, torch):
    dependencies = verify_original_dependencies(config)
    sys.path.insert(0, config['primary_release'])
    import transformers
    from defense.core import digest as parent_digest
    from defense.qwen_backend import LocalQwen
    import defense.qwen_backend as parent_backend
    source = Path(parent_backend.__file__)
    if sha(source) != config['primary_backend_sha256']:
        raise RuntimeError('Primary parent backend differs from reviewed source')
    expected = json.loads(Path(config['primary_expected_runtime']).read_bytes())
    if torch.__version__ != expected['torch'] or transformers.__version__ != expected['transformers']:
        raise RuntimeError('Primary native environment version changed')
    budgets = validate_layout(layout)
    class AsymmetricQwen(LocalQwen):
        # Only this constructor is new. generate/judge remain inherited objects.
        def __init__(self):
            from transformers import AutoModelForImageTextToText, AutoProcessor
            self.torch = torch
            self.processor = AutoProcessor.from_pretrained(config['primary_model'],
                                      local_files_only=True, trust_remote_code=True)
            self.model = AutoModelForImageTextToText.from_pretrained(
                config['primary_model'], dtype=torch.bfloat16, attn_implementation='sdpa',
                device_map=primary_device_map(), max_memory=budgets, local_files_only=True,
                trust_remote_code=True).eval()
            if any(str(v) in {'cpu', 'disk', 'meta'} for v in self.model.hf_device_map.values()):
                raise RuntimeError('Primary model offload is prohibited')
            if self.model.config.text_config.num_hidden_layers != 64 or str(self.model.dtype) != 'torch.bfloat16':
                raise RuntimeError('Primary native architecture/precision mismatch')
            self.runtime = {'model_path': config['primary_model'], 'class': type(self.model).__name__,
                'dtype': str(self.model.dtype), 'backend': 'sdpa', 'placement': 'explicit_asymmetric_18_20_20_6',
                'device_map': {k: str(v) for k, v in self.model.hf_device_map.items()},
                'max_memory_per_device': budgets, 'torch': torch.__version__,
                'transformers': transformers.__version__, 'history_truncation': False,
                'image_preprocessing_changes': False,
                'metadata_sha256': {name: parent_digest((Path(config['primary_model']) / name).read_bytes())
                    for name in ['config.json', 'model.safetensors.index.json',
                                 'preprocessor_config.json', 'generation_config.json']}}
            if self.runtime['metadata_sha256'] != expected['metadata_sha256']:
                raise RuntimeError('Primary original metadata identity mismatch')
            save(root / 'runtime.json', self.runtime)
    if AsymmetricQwen.generate is not LocalQwen.generate or AsymmetricQwen.judge is not LocalQwen.judge:
        raise RuntimeError('Original main generation/judge methods were replaced')
    engine = AsymmetricQwen()
    native_state = verify_primary_native_state(config, engine)
    tensors = audit_tensors(torch, [('primary', engine.model)], ['cuda:0', 'cuda:1', 'cuda:2', 'cuda:3'])
    for i, limit in enumerate(layout['primary_max_memory_gib']):
        if tensors['tensor_bytes_by_device']['cuda:' + str(i)] > limit * 1024 ** 3:
            raise RuntimeError('Explicit primary tensor placement exceeds reviewed per-device budget')
    return engine, [(engine.model, False)], {'primary_parent_source_sha256': sha(source),
        'generate_and_judge_inherited_unchanged': True, **dependencies, **native_state, **tensors, **engine.runtime}


def load_flash(config, root, torch):
    before_identity = verify_flash_checkpoint(config)
    sys.path.insert(0, str(Path(config['flash_model']) / 'source/src'))
    import transformers
    from pplx_decider import Decider
    import pplx_decider.model as native_model
    if Path(native_model.__file__).resolve() != (Path(config['flash_model']) /
            'source/src/pplx_decider/model.py').resolve():
        raise RuntimeError('Actual Flash native import did not use the pinned checkpoint source')
    engine = Decider.from_pretrained(config['flash_model'], device='cuda:0', fast=False)
    for module in (engine.backbone, engine.readout):
        if any(value.is_floating_point() and value.dtype != torch.bfloat16
               for value in module.parameters()):
            raise RuntimeError('Flash native CUDA model parameters must remain BF16')
    tensors = audit_tensors(torch, [('backbone', engine.backbone), ('readout', engine.readout)], ['cuda:0'])
    after_identity = verify_flash_checkpoint(config)
    if before_identity != after_identity:
        raise RuntimeError('Flash file identity changed during native load')
    return engine, [(engine.backbone, False), (engine.readout, True)], {
        'model': FLASH, 'revision': FLASH_REVISION, 'torch': torch.__version__,
        'transformers': transformers.__version__, 'native_decider': True,
        'noncausal_full_attention': True, 'marker_readout': True,
        'fast': False, 'questions_per_request': 3, 'image_only_neutral_joint_observer': True,
        'shared_question_attention': True, 'checkpoint_identity': after_identity, **tensors}


def main(a):
    root = a.root
    root.mkdir(parents=True, exist_ok=False)
    (root / 'requests').mkdir()
    config = json.loads(a.config.read_bytes())
    lease = json.loads(a.lease.read_bytes())
    layout = json.loads(Path(config['layout']).read_bytes())
    validate_layout(layout)
    admission_bytes = a.admission.read_bytes()
    if digest(admission_bytes) != config['admission_sha256'][a.role]:
        raise RuntimeError('Finite request admission plan differs from sealed config')
    admission = json.loads(admission_bytes)
    allowed = validate_admission(admission)
    observer_contract = None
    if a.role == FLASH:
        if admission['mode'] not in {'image_observer_preflight', 'resident_only'} or not 0 <= admission['max_new_calls'] <= 60:
            raise RuntimeError('Only the new finite image-only neutral observer plan is admitted')
        if admission['mode'] == 'image_observer_preflight' and admission['max_new_calls'] < 1:
            raise RuntimeError('Observer preflight requires a positive frozen finite budget')
        path = Path(config['flash_observer_contract'])
        if sha(path) != config['flash_observer_contract_sha256']:
            raise RuntimeError('Neutral observer contract differs from the reviewed file')
        observer_contract = json.loads(path.read_bytes())
    commands = config['commands']
    actual_self = identity(os.getpid())
    if actual_self['uid'] != 1033 or actual_self['command'] != ' '.join(commands[a.role]):
        raise RuntimeError('Worker UID/full command does not match launch config')
    check_inherited_locks(lease)
    group = Path(config['group_root'])
    (group / 'processes').mkdir(exist_ok=True)
    save(group / 'processes' / (a.role + '.json'), {'role': a.role, 'identity': actual_self,
        'lease_sha256': sha(a.lease), 'worker_sha256': sha(Path(__file__))})
    save(root / 'process.json', {'role': a.role, 'identity': actual_self,
                               'CUDA_VISIBLE_DEVICES': os.environ.get('CUDA_VISIBLE_DEVICES'),
                               'lease_sha256': sha(a.lease), 'admission_sha256': digest(admission_bytes)})
    # A peer can fail while this worker is still loading. Install the graceful
    # signal before load so the launcher never uses default SIGUSR1 termination
    # on an in-progress owned model load; finish, then seal and stop below.
    stop = {'value': False}
    signal.signal(signal.SIGUSR1, lambda *_: stop.update(value=True))
    signal.signal(signal.SIGTERM, lambda *_: stop.update(value=True))
    expected_visible = '4,5,6,7' if a.role == 'primary' else '7'
    if os.environ.get('CUDA_VISIBLE_DEVICES') != expected_visible:
        raise RuntimeError('Worker has the wrong physical CUDA visibility')
    import torch
    from PIL import Image
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    captured = []
    with serial_inference(lease, group, commands):
        started = time.monotonic()
        engine, modules, audit = (load_primary(a, config, layout, root, torch)
                                 if a.role == 'primary' else load_flash(config, root, torch))
        audit.update(load_seconds=time.monotonic() - started, memory=memory(torch), role=a.role,
                     admission_sha256=digest(admission_bytes), GUI_actions=0)
        save(root / 'loaded.json', audit)
        hooks = [audited_forward(torch, module, captured, raw_readout)
                 for module, raw_readout in modules]
    # Native loads may install their own handlers. Rearm the Python graceful
    # handlers after load as well, and keep the file-based stop fallback below.
    signal.signal(signal.SIGUSR1, lambda *_: stop.update(value=True))
    signal.signal(signal.SIGTERM, lambda *_: stop.update(value=True))
    token = Path(config['token_file']).read_text().strip()
    if len(token) < 32:
        raise RuntimeError('Missing private transport token')
    calls = 0
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def reply(self, code, value):
            raw = canonical(value)
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        def auth(self):
            return hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token)
        def do_GET(self):
            if self.path not in {'/', '/health'}:
                return self.reply(404, {'error': 'not_found'})
            if not self.auth():
                return self.reply(403, {'error': 'unauthorized'})
            try:
                resources = resource_admission(lease, group, commands)
                return self.reply(200, {'phase': 'ready_preflight_only', 'role': a.role,
                    'pid': os.getpid(), 'uid': os.getuid(), 'calls': calls,
                    'max_new_calls': admission['max_new_calls'], 'GUI_actions': 0, **resources})
            except Exception:
                return self.reply(503, {'phase': 'resource_conflict', 'error': traceback.format_exc(),
                                        'model_calls': 0})
        def do_POST(self):
            if stop['value'] or (group / 'stop-requested.json').exists():
                return self.reply(503, {'error': 'owned_group_stopping', 'model_calls': 0})
            nonlocal calls
            if not self.auth():
                return self.reply(403, {'error': 'unauthorized'})
            if self.path not in ({'/observe'} if a.role == FLASH else {'/'}):
                return self.reply(404, {'error': 'not_found'})
            try:
                count = int(self.headers.get('Content-Length', '0'))
                if not 0 < count <= 64 * 1024 ** 2:
                    return self.reply(413, {'error': 'request_size_no_truncation'})
                raw = self.rfile.read(count)
                body = json.loads(raw)
                try:
                    fingerprint = validate_frozen_wire(raw, body, allowed)
                except ValueError:
                    return self.reply(403, {'error': 'wire_not_in_frozen_preflight', 'model_calls': 0})
                request = root / 'requests' / fingerprint
                if request.exists():
                    if (request / 'response.json').exists():
                        result = json.loads((request / 'response.json').read_bytes())
                        # Transport retry can change ID; return original receipt only
                        # when identical full wire body, otherwise caller must inspect.
                        if (request / 'request.json').read_bytes() == raw:
                            return self.reply(200, result)
                    return self.reply(409, {'error': 'terminal_or_pending_input_no_retry',
                                           'receipt': str(request), 'model_calls': 0})
                if calls >= admission['max_new_calls']:
                    return self.reply(429, {'error': 'finite_preflight_budget_exhausted', 'model_calls': 0})
                with serial_inference(lease, group, commands):
                    request.mkdir(exist_ok=False)
                    (request / 'request.json').write_bytes(raw)
                    calls += 1
                    captured.clear()
                    reset_memory(torch)
                    start = time.monotonic()
                    try:
                        if a.role == FLASH:
                            validate_observation(body, observer_contract)
                            image_raw = base64.b64decode(body['image_base64'], validate=True)
                            if digest(image_raw) != body['image_sha256']:
                                raise ValueError('Original image SHA mismatch')
                            (request / 'original.image').write_bytes(image_raw)
                            image = Image.open(io.BytesIO(image_raw))
                            image.load()
                            native = {'state': body['state'], 'questions': body['questions']}
                            save(request / 'native-request.json', {**native, 'images_sha256': [digest(image_raw)]})
                            result = engine.decide({**native, 'images': [image]})
                            save(request / 'native-result.json', result)
                            if list(result['answers']) != list(body['questions']):
                                raise RuntimeError('Native result does not preserve the three question identities')
                            for key, question in body['questions'].items():
                                evidence = result['answers'][key]
                                validate_probabilities(evidence['probabilities'], question['criteria'], evidence['choice'])
                            if sum('pixel_values' in row.get('tensors', {}) and
                                   'input_ids' in row.get('tensors', {}) for row in captured) != 1:
                                raise RuntimeError('Native actual pixel/input-ID forward absent')
                            readouts = [row['raw_readout'] for row in captured if 'raw_readout' in row]
                            if (len(readouts) != 1 or readouts[0]['shape'] != [3, 255]
                                    or result.get('usage', {}).get('sequences') != 1):
                                raise RuntimeError('Expected one joint forward with three native255-way marker readouts')
                            result = {'status': 'ok', 'model': FLASH, 'revision': FLASH_REVISION,
                                'request_id': body['request_id'], 'request_sha256': digest(raw),
                                'image_sha256': digest(image_raw), 'original_size': list(image.size),
                                'answers': result['answers'], 'usage': result['usage'], 'native_result': result,
                                'scope': 'one_original_frame_only', 'history_verified': False,
                                'generation_tokens': 0}
                        else:
                            from defense.core import PublicView, VisibleImage
                            if body['operation'] == 'actor':
                                validate_actor(body)
                                original = body['body']
                                result = {'text': engine.generate(original['messages'], 2048,
                                    request / 'generation.json', seed=42, original_body=original)}
                            elif body['operation'] == 'judge':
                                value = body['view']
                                view = PublicView(value['observation_id'], value['messages'],
                                    tuple(VisibleImage(base64.b64decode(x['raw_base64']), x['role'])
                                          for x in value['images']), value.get('recent_action', ''),
                                    value.get('execution_feedback', ''), value['observed_at'])
                                result = {'verdict': engine.judge(body['system'], view,
                                    body.get('candidate'), request / 'generation.json')}
                            else:
                                raise ValueError('Only frozen actor/judge operations admitted')
                            generation = json.loads((request / 'generation.json').read_bytes())
                            result.update(input_tokens=len(generation['input_ids']),
                                output_tokens=len(generation['generated_ids']), seconds=generation['seconds'])
                        for i in range(torch.cuda.device_count()):
                            torch.cuda.synchronize(i)
                        save(request / 'forward-trace.json', captured)
                        result.update(receipt=str(request), forward_trace_sha256=sha(request / 'forward-trace.json'),
                            seconds_including_audit=time.monotonic() - start,
                            per_device_memory=memory(torch), GUI_actions=0,
                            peak_allocated_bytes=max(x['peak_allocated_bytes'] for x in memory(torch)),
                            peak_reserved_bytes=max(x['peak_reserved_bytes'] for x in memory(torch)))
                        save(request / 'response.json', result)
                        save(request / 'seal.json', {p.name: sha(p) for p in request.iterdir() if p.is_file()})
                        self.reply(200, result)
                    except BaseException:
                        if not (request / 'forward-trace.json').exists():
                            save(request / 'forward-trace.json', captured)
                        failure = {'status': 'technical_failure', 'error': traceback.format_exc(),
                            'receipt': str(request), 'semantic_pass': None, 'per_device_memory': memory(torch),
                            'seconds_including_audit': time.monotonic() - start, 'GUI_actions': 0}
                        save(request / 'failure.json', failure)
                        save(request / 'seal.json', {p.name: sha(p) for p in request.iterdir() if p.is_file()})
                        self.reply(500, failure)
                    finally:
                        captured.clear()
                        # Returned output/caches are not retained by these serial
                        # request handlers. Release allocator cache between requests
                        # so the peer can use reserved headroom; inputs/precision stay.
                        import gc
                        gc.collect()
                        torch.cuda.empty_cache()
            except Exception:
                self.reply(503, {'status': 'preflight_rejected', 'error': traceback.format_exc(),
                                 'model_calls': 0})
    server = HTTPServer(('127.0.0.1', a.port), Handler)
    server.timeout = 1
    save(root / 'ready.json', {'port': a.port, 'phase': 'ready_preflight_only', 'time': time.time(),
                              'loaded_sha256': sha(root / 'loaded.json'), 'GUI_actions': 0})
    print(json.dumps({'role': a.role, 'phase': 'ready_preflight_only', 'pid': os.getpid(),
                      'port': a.port}), flush=True)
    try:
        while not stop['value'] and not (group / 'stop-requested.json').exists():
            server.handle_request()
    finally:
        server.server_close()
        for hook in hooks:
            hook.remove()
        save(root / 'stopped.json', {'time': time.time(), 'calls': calls, 'GUI_actions': 0})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', choices=['primary', FLASH], required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--lease', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--admission', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    try:
        main(args)
    except BaseException:
        # Fatal load failure is a terminal new attempt; launcher seals this output
        # after process exit. No automatic smaller-input/precision/placement retry.
        traceback.print_exc()
        raise SystemExit(1)
