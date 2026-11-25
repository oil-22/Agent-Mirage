"""New runtime integrating the source-bound private grammar and stateless calls."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
original = BASE / 'full-gui-bounded-evidence-20261109-03' / 'runtime-package'
private = BASE / 'auxiliary-grammar-isolation-20261109-06' / 'isolated-runtime-source-linked02'
output = HERE / 'integrated-runtime-linked03'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
private_seal = json.loads((private / 'source-seal.json').read_bytes())
for name, expected in private_seal.items():
    assert sha(private / name) == expected, name
shutil.copytree(original, output, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
for source in private.iterdir():
    if source.name == 'source-seal.json':
        continue
    destination = output / source.name
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    else:
        shutil.copyfile(source, destination)

shutil.copyfile(HERE / 'stateless_boundary_v2.py', output / 'stateless_boundary.py')
shutil.copyfile(HERE / 'source' / 'evidence_observer.py', output / 'release' / 'evidence_observer.py')
shutil.copyfile(HERE / 'source' / 'gui_transport.py', output / 'gui_transport.py')
bounded = output / 'bounded_auxiliary.py'
text = bounded.read_text(encoding='utf8')
needle = 'def generate(model,processor,generation,torch,audit,data,raw,target):'
assert text.count(needle) == 1
text = text.replace(needle, 'def _generate_one_call(model,processor,generation,torch,audit,data,raw,target):')
text += '''
    finally:
        # Drop per-call tensors and PIL/context references before the outer
        # boundary checks weak references to the native generation cache.
        for message in messages:
            for block in message.get('content', []):
                if block.get('type') == 'image':
                    block['image'].close()
        messages.clear()
        inputs = output = prefix = None


def generate(model,processor,generation,torch,audit,data,raw,target):
    from stateless_boundary import StatelessAuxiliaryBoundary
    with StatelessAuxiliaryBoundary(model,processor,raw,contract.FIXED_PROMPT,target):
        result = _generate_one_call(model,processor,generation,torch,audit,data,raw,target)
    return result
'''
compile(text, str(bounded), 'exec')
bounded.write_text(text, encoding='utf8', newline='\n')

def generation_calls(path):
    return [ast.dump(node, include_attributes=False) for node in ast.walk(ast.parse(path.read_text(encoding='utf8')))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'generate']

assert generation_calls(private / 'bounded_auxiliary.py') == generation_calls(bounded)
changed = []
for source in original.rglob('*'):
    if not source.is_file() or '__pycache__' in source.parts or source.suffix == '.pyc':
        continue
    name = source.relative_to(original)
    if sha(source) != sha(output / name):
        changed.append(name.as_posix())
for required in ['model_runtime.py', 'gpu_server.py', 'release/image_evidence.py',
                 'release/defense/core.py', 'release/defense/schema.py']:
    assert sha(original / required) == sha(output / required), required
for path in output.rglob('*.py'):
    compile(path.read_text(encoding='utf8'), str(path), 'exec')
with (output / 'integrated-source-seal.json').open('x', encoding='utf8') as stream:
    json.dump({p.relative_to(output).as_posix(): sha(p) for p in output.rglob('*')
               if p.is_file() and '__pycache__' not in p.parts and p.name != 'integrated-source-seal.json'}, stream, indent=2)
    stream.write('\n')
receipt = {
    'time': time.time(), 'source': str(output),
    'source_seal_sha256': sha(output / 'integrated-source-seal.json'),
    'previous_private_grammar_seal_sha256': sha(private / 'source-seal.json'),
    'changed_relative_to_prior_GUI_package': changed,
    'main_native_load_generate_and_strict_validator_sources_unchanged': True,
    'auxiliary_native_generate_call_AST_unchanged': True,
    'one_complete_image_fixed_prompt_only': True,
    'same_image_response_memoization_removed': True,
    'per_call_first_forward_empty_cache_and_post_call_release_instrumented': True,
    'auxiliary_cap': 60,
    'new_model_GUI_scorer_calls': 0,
    'live_runtime_modified': False,
    'actual_GPU_boundary_and_semantic_efficacy_pending': True,
    'tradeoff': 'No reply reuse adds auxiliary calls/latency within the same60cap. '
                'Actual cache audit failure makes the auxiliary unavailable; no input clipping, extra retry or truth/action override.',
}
with (HERE / 'integrated-runtime-preparation-linked03.json').open('x', encoding='utf8') as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'runtime': str(output), 'source_seal_sha256': receipt['source_seal_sha256'],
                  'main_generation_unchanged': True, 'new_model_GUI_calls': 0}))
