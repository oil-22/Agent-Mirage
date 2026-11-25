"""New CPU check restoring only the original isolated grammar dependency path."""
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import time

assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')
DEPS = Path('/home/researcher/defense-resume-20261102-retry2/deps')
RELEASE = BASE / 'primary-release-01'
root = BASE / 'dependency-cpu-checks' / str(time.time_ns()); root.mkdir(parents=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
files = {str(p.relative_to(DEPS)): sha(p) for p in DEPS.rglob('*')
         if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
repair_path = DEPS.parent / 'dependency-repair.json'
repair = json.loads(repair_path.read_bytes())
integration_path = DEPS / 'lmformatenforcer/integrations/transformers.py'
assert repair['all_functions_and_classes_AST_identical'] is True
assert repair['no_generation_schema_or_validator_change'] is True
assert repair['after_sha256'] == sha(integration_path) == '223e56d56be3f60d14b270c6db6cfedd19000adefb22f9d3aeaf5925a6035f47'
sys.path[:0] = [str(DEPS), str(RELEASE)]
import torch
from transformers import AutoTokenizer
from transformers.tokenization_utils_base import PreTrainedTokenizerBase
from lmformatenforcer import JsonSchemaParser
import lmformatenforcer
import lmformatenforcer.integrations.transformers as integration
assert Path(lmformatenforcer.__file__).resolve().is_relative_to(DEPS.resolve())
assert Path(integration.__file__).resolve() == integration_path.resolve()
assert integration.PreTrainedTokenizerBase is PreTrainedTokenizerBase
assert not torch.cuda.is_initialized()
tokenizer = AutoTokenizer.from_pretrained('/data/llms/Qwen3.8-27B', local_files_only=True, trust_remote_code=True)
token_data = integration.build_token_enforcer_tokenizer_data(tokenizer)
wire_paths = list(BASE.glob('**/primary-capacity-frozen-02/request.json'))
assert len(wire_paths) == 1, [str(p) for p in wire_paths]
wire_path = wire_paths[0]; body = json.loads(wire_path.read_bytes())
assert sha(wire_path) == '921d1df12734b116f3a920e6caa769c9b148990c2efb6439febe9c47231e6a92'
from defense.core import PublicView, VisibleImage, canonical, digest
from defense.prompts import HISTORY_REPORT
from defense.schema import judge_schema
v = body['view']
view = PublicView(v['observation_id'], v['messages'],
    tuple(VisibleImage(base64.b64decode(x['raw_base64']), x['role']) for x in v['images']),
    v.get('recent_action', ''), v.get('execution_feedback', ''), v['observed_at'])
phase = 'history_report' if body['system'].startswith(HISTORY_REPORT) else None
schema = judge_schema(view, body.get('candidate'), phase=phase)
parser = JsonSchemaParser(schema)
allowed_fn = integration.build_transformers_prefix_allowed_tokens_fn(token_data, parser)
allowed = allowed_fn(0, torch.tensor([tokenizer.eos_token_id]))
assert allowed and all(type(value) is int and 0 <= value < len(tokenizer) for value in allowed)
assert not torch.cuda.is_initialized()
assert files == {str(p.relative_to(DEPS)): sha(p) for p in DEPS.rglob('*')
    if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
result = {'root': str(root), 'status': 'passed', 'dependency_root': str(DEPS),
    'dependency_files': files, 'repair_receipt': str(repair_path), 'repair_receipt_sha256': sha(repair_path),
    'integration_sha256': sha(integration_path), 'canonical_class_identical': True,
    'actual_lmformatenforcer_module': lmformatenforcer.__file__, 'actual_integration_module': integration.__file__,
    'tokenizer_class': type(tokenizer).__name__, 'vocabulary': len(tokenizer),
    'original_capacity_wire': str(wire_path), 'original_capacity_wire_sha256': sha(wire_path),
    'original_capacity_schema_sha256': digest(canonical(schema)),
    'initial_allowed_token_count': len(allowed), 'initial_allowed_ids': allowed,
    'all_dependency_bytes_stable': True, 'weights_loaded': False,
    'model_generation': False, 'GPU_allocations': 0, 'cuda_initialized': False,
    'GUI_actions': 0, 'package_installed_or_modified': False}
(root / 'receipt.json').write_text(json.dumps(result, indent=2))
(root / 'original-schema.json').write_text(json.dumps(schema, indent=2))
(root / 'dependency-repair.json').write_bytes(repair_path.read_bytes())
(root / 'integration.py').write_bytes(integration_path.read_bytes())
(root / 'seal.json').write_text(json.dumps({p.name: sha(p) for p in root.iterdir() if p.is_file()}, indent=2))
print(json.dumps({k: v for k, v in result.items() if k not in ('dependency_files', 'initial_allowed_ids')}))
