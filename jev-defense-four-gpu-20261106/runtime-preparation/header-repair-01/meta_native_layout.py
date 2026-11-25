"""Instantiate the original native class only on meta; never load any weights."""
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import time

assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
import torch
import transformers
from transformers import AutoConfig, AutoModelForImageTextToText
import transformers.models.qwen3_5.modeling_qwen3_5 as native

base = Path('/home/researcher/jev-defense-four-gpu-20261106')
root = base / 'native-meta-layout' / str(time.time_ns())
root.mkdir(parents=True)
source = Path(native.__file__)
source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_sha == '67cf849081143a998f0e189c551e4b5f532365a055805570747385e400372abb'
assert transformers.__version__ == '5.15.1' and torch.__version__ == '2.5.1+cu121'
assert not torch.cuda.is_initialized()
config = AutoConfig.from_pretrained('/data/llms/Qwen3.8-27B', local_files_only=True, trust_remote_code=True)
with torch.device('meta'):
    model = AutoModelForImageTextToText.from_config(config, dtype=torch.bfloat16,
        attn_implementation='sdpa', trust_remote_code=True)
assert type(model).__name__ == 'Qwen3_5ForConditionalGeneration'
state = model.state_dict()
assert state and all(value.device.type == 'meta' for value in state.values())
assert not any(name.startswith('mtp.') for name in state)
index = json.loads(Path('/data/llms/Qwen3.8-27B/model.safetensors.index.json').read_bytes())
unexpected = sorted(set(index['weight_map']) - set(state))
missing = sorted(set(state) - set(index['weight_map']))
assert not missing and unexpected and all(name.startswith('mtp.') for name in unexpected)
patterns = list(model._keys_to_ignore_on_load_unexpected)
assert any(pattern == '^mtp.*' for pattern in patterns)
assert all(any(re.search(pattern, name) for pattern in patterns) for name in unexpected)
assert not torch.cuda.is_initialized()
records = [{'name': name, 'shape': list(value.shape), 'dtype': str(value.dtype),
            'device': str(value.device), 'bytes': value.numel() * value.element_size()}
           for name, value in state.items()]
result = {'root': str(root), 'class': type(model).__name__, 'torch': torch.__version__,
    'transformers': transformers.__version__, 'native_source': str(source),
    'native_source_sha256': source_sha, 'model_module_source': inspect.getfile(type(model)),
    'native_ignored_unexpected_patterns': patterns,
    'meta_state_tensor_count': len(records), 'meta_state_total_bytes': sum(r['bytes'] for r in records),
    'missing_checkpoint_tensors': missing, 'checkpoint_only_native_ignored_tensors': unexpected,
    'all_state_tensors_meta': True, 'cuda_initialized': False,
    'GPU_allocations': 0, 'weight_tensor_payloads_loaded': 0, 'model_calls': 0, 'GUI_actions': 0}
(root / 'meta-state.json').write_text(json.dumps(records, indent=2))
(root / 'receipt.json').write_text(json.dumps(result, indent=2))
(root / 'native-source.py').write_bytes(source.read_bytes())
(root / 'seal.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
    for p in root.iterdir() if p.is_file()}, indent=2))
print(json.dumps(result))
