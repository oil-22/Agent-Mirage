"""Exercise the exact staged native parser and Controller request construction.

The callback stops before returning any reply. No model, synthetic verdict, GUI,
weight, GPU, network request or source-control semantic resampling is performed.
"""
from pathlib import Path
import ast
import base64
import hashlib
import json
import re
import sys
import time

HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'runtime-package'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((PACKAGE / 'manifest.json').read_bytes())
for name, expected in manifest['files'].items():
    assert sha(PACKAGE / name) == expected, name
sys.path[:0] = [str(PACKAGE), str(PACKAGE / 'release')]
from defense.core import Controller, Journal, Limits, PublicView, VisibleImage
from exploratory_action_scope import EXPLORATORY_ACTION_SCOPE, with_exploratory_action_scope
import image_evidence as contract

tree = ast.parse((PACKAGE / 'native-parser-source.py').read_text(encoding='utf8'))
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'parse')
namespace = {'json': json, 're': re}
exec(compile(ast.Module(body=[node], type_ignores=[]), 'native-parser-source.py', 'exec'), namespace)
plan = json.loads((PACKAGE / 'controls-plan.json').read_bytes())
out = HERE / ('exact-request-CPU-admission-' + str(time.time_ns()))
out.mkdir(exist_ok=False)

class StopBeforeInference(RuntimeError):
    pass

rows = []
for row in plan['judges']:
    path = PACKAGE / row['path']
    assert sha(path) == row['sha256']
    frozen = json.loads(path.read_bytes())
    public = frozen['view']
    candidate = frozen['candidate']
    native = namespace['parse'](candidate)
    proposal = {'name': native['type'], 'parsed': True, 'executor_fallback_wait': False,
                'payload': native, 'coordinate_space': 'normalized_1000'}
    assert native['type'] == ('wait' if row['id'] == 'E07' else 'click')
    view = PublicView(public['observation_id'], public['messages'],
                      tuple(VisibleImage(base64.b64decode(im['raw_base64']), im['role'])
                            for im in public['images']),
                      public['recent_action'], public['execution_feedback'], public['observed_at'])
    captured = []
    def stop(system, actual_view, actual_candidate):
        assert actual_candidate == candidate
        assert actual_view.messages == view.messages
        assert len(actual_view.images) == len(view.images) == 1
        assert actual_view.images[0].raw == view.images[0].raw
        captured.append(system)
        raise StopBeforeInference()
    controller = Controller(stop, Journal(out / (row['id'] + '-request-journal')),
                            'post_only', Limits(max_verifier_calls=2, max_format_retries=1),
                            sleeper=lambda _: None)
    try:
        controller.inspect('verify', view, candidate, proposal)
        raise AssertionError('CPU callback should stop before inference')
    except StopBeforeInference:
        pass
    assert len(captured) == 1
    old = captured[0]
    new = with_exploratory_action_scope(old, proposal)
    assert new == (old + '\n' + EXPLORATORY_ACTION_SCOPE if native['type'] == 'click' else old)
    assert old.startswith('You are') or len(old) > 1000
    (out / (row['id'] + '-original-system.txt')).write_text(old, encoding='utf8')
    (out / (row['id'] + '-new-system.txt')).write_text(new, encoding='utf8')
    rows.append({'id': row['id'], 'native': native,
                 'actual_full_image_sha256': hashlib.sha256(view.images[0].raw).hexdigest(),
                 'candidate_unchanged': True, 'full_public_messages_unchanged': True,
                 'old_system_sha256': hashlib.sha256(old.encode()).hexdigest(),
                 'new_system_sha256': hashlib.sha256(new.encode()).hexdigest(),
                 'only_click_scope_appended': native['type'] == 'click',
                 'model_called': False, 'reply_or_semantic_result_supplied': False})

aux = []
for row in plan['auxiliary']:
    path = PACKAGE / row['path']
    assert sha(path) == row['sha256']
    request = json.loads(path.read_bytes())
    raw = contract.validate_image_only_request(request)
    aux.append({'id': row['id'], 'image_sha256': hashlib.sha256(raw).hexdigest(),
                'fixed_prompt_sha256': request['prompt_sha256'],
                'native_request_valid': True})
assert aux[0]['image_sha256'] == aux[1]['image_sha256']
assert len({a['fixed_prompt_sha256'] for a in aux}) == 1
receipt = {'schema': 'exact-staged-parser-and-controller-request-CPU-v1',
           'passed': True, 'manifest_sha256': sha(PACKAGE / 'manifest.json'),
           'judge_cases': rows, 'prompt_conditions_per_case': 2,
           'auxiliary_request_contracts': aux,
           'WAIT_scope_and_native_candidate_unchanged': True,
           'no_fabricated_model_reply_or_GUI_result': True,
           'new_model_GPU_GUI_scorer_paid_calls': 0,
           'actual_GPU_cache_lifecycle_unproven': True,
           'semantic_pass_or_GUI_release_established': False}
with (out / 'receipt.json').open('x', encoding='utf8') as f:
    json.dump(receipt, f, ensure_ascii=False, indent=2)
    f.write('\n')
with (out / 'seal.json').open('x', encoding='utf8') as f:
    json.dump({p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()}, f, indent=2)
    f.write('\n')
print(json.dumps({'receipt': str(out / 'receipt.json'), 'sha256': sha(out / 'receipt.json'),
                  'passed': True, 'judge_cases': 8, 'model_GPU_GUI_calls': 0}))
