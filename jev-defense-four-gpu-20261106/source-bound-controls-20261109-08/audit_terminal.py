"""Audit full terminal bindings and replay unchanged strict contracts on CPU."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import time
from PIL import Image

HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'runtime-package'
COLLECTION = HERE / 'terminal-collection-1794212429798794800'
ROOT = COLLECTION / 'original'
sys.path[:0] = [str(PACKAGE), str(PACKAGE / 'release')]
from defense.core import Controller, Journal, Limits, PublicView, VisibleImage, ValidationError
from exploratory_action_scope import with_exploratory_action_scope
import image_evidence as contract
import ast
import re

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
canonical = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def save(p, value):
    with p.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')


receipt = json.loads((COLLECTION / 'receipt.json').read_bytes())
assert receipt['terminal_collection'] and receipt['new_model_GPU_GUI_scorer_paid_calls'] == 0
for name, expected in json.loads((COLLECTION / 'seal.json').read_bytes()).items():
    assert sha(COLLECTION / name) == expected, name
for name, expected in receipt['exported_files'].items():
    assert sha(ROOT / name) == expected, name
assert all(row['actual'].get('absent') is True for row in receipt['actual_processes'].values())
manifest = json.loads((PACKAGE / 'manifest.json').read_bytes())
assert sha(PACKAGE / 'manifest.json') == receipt['manifest_sha256']
for name, expected in manifest['files'].items():
    assert sha(PACKAGE / name) == expected, name
terminal = json.loads((ROOT / 'worker/terminal.json').read_bytes())
exit_record = json.loads((ROOT / 'exit.json').read_bytes())
assert terminal['status'] == 'completed' and terminal['error'] is None
assert exit_record['worker_exit_code'] == exit_record['launcher_exit_code'] == 0
out = HERE / ('terminal-audit-' + str(time.time_ns())); out.mkdir()
plan = json.loads((PACKAGE / 'controls-plan.json').read_bytes())
tree = ast.parse((PACKAGE / 'native-parser-source.py').read_text(encoding='utf8'))
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'parse')
ns = {'json': json, 're': re}
exec(compile(ast.Module(body=[node], type_ignores=[]), 'unchanged-native-parser', 'exec'), ns)
parse = ns['parse']
aux_rows = []; all_rows = []; totals = {'input': 0, 'output': 0, 'seconds_including_instrumentation': 0}
call_ids = []
for group in ['auxiliary', 'judges']:
    for target in sorted((ROOT / 'worker' / group).iterdir()):
        prepared = json.loads((target / 'prepared.json').read_bytes())
        first = json.loads((target / 'first-forward.json').read_bytes())
        assert set(first) == set(prepared)
        for name in prepared:
            assert all(prepared[name][k] == first[name][k] for k in ['shape', 'dtype', 'bytes', 'sha256'])
        actual = json.loads((target / 'actual-generation.json').read_bytes())
        generation = json.loads((target / 'effective-generation.json').read_bytes())
        ids = actual['output_ids']; eos = generation['eos_token_id']
        eos = [eos] if isinstance(eos, int) else eos
        assert len(ids) == actual['output_tokens'] and ids[-1] in eos and actual['natural_EOS']
        assert actual['actual_forward_calls'] > 0 and actual['input_tokens'] == prepared['input_ids']['shape'][1]
        response = json.loads((target / 'response.json').read_bytes())
        text = (target / 'raw-output.txt').read_text(encoding='utf8')
        assert response['raw_output' if group == 'auxiliary' else 'text'] == text
        row = {'type': group, 'request': target.name, 'input_tokens': actual['input_tokens'],
               'output_tokens': actual['output_tokens'], 'natural_EOS': True,
               'first_forward_full_tensor_shape_dtype_bytes_SHA_equal_native_CPU': True,
               'actual_input_ids_sha256': prepared['input_ids']['sha256'],
               'seal_sha256': sha(target / 'seal.json')}
        totals['input'] += actual['input_tokens']; totals['output'] += actual['output_tokens']
        if group == 'auxiliary':
            request = json.loads((target / 'request.json').read_bytes())
            frozen = json.loads((PACKAGE / ('control-inputs/' + target.name + '.json')).read_bytes())
            assert request == frozen
            raw = contract.validate_image_only_request(request)
            assert raw == (target / 'original.png').read_bytes()
            boundary = json.loads((target / 'stateless-input-boundary.json').read_bytes())
            lifecycle = json.loads((target / 'stateless-context-discarded.json').read_bytes())
            assert boundary['message_count'] == 1 and boundary['content_types'] == ['image', 'text']
            assert boundary['complete_image_sha256'] == request['image_sha256']
            assert boundary['fixed_prompt_sha256'] == request['prompt_sha256']
            assert boundary['task_history_candidate_previous_auxiliary_content_supplied'] is False
            with Image.open(target / 'original.png') as image:
                assert list(image.size) == boundary['size']
                assert hashlib.sha256(image.convert('RGB').tobytes()).hexdigest() == boundary['complete_RGB_sha256']
            assert lifecycle['call_id'] == boundary['call_id'] and lifecycle['call_id'] not in call_ids
            call_ids.append(lifecycle['call_id'])
            assert lifecycle['actual_first_forward_cache_length'] == 0
            assert lifecycle['all_observed_cache_objects_released']
            assert lifecycle['observed_cache_objects'] > 0 and lifecycle['observed_cache_objects_still_alive'] == 0
            assert lifecycle['untrackable_cache_types'] == [] and lifecycle['error_type'] is None
            assert lifecycle['main_model_or_main_context_referenced'] is False
            assert generation['max_new_tokens'] == 2048
            mask = json.loads((target / 'actual-mask-steps.json').read_bytes())
            assert mask['all_actual_selected_tokens_allowed']
            assert len(mask['steps']) == len(ids)
            assert [x['selected_id'] for x in mask['steps']] == ids
            assert all(x['selected_allowed'] for x in mask['steps'])
            assert json.loads((target / 'raw-UTF8-validation.json').read_bytes())['strict_native_UTF8_roundtrip']
            packet = contract.actor_packet(request, text, True)
            assert packet == json.loads((target / 'packet.json').read_bytes())
            row.update(actual_stateless_boundary_and_cache_release_verified=True,
                       format_contract_valid=True, semantic_pass=None,
                       original_image_sha256=request['image_sha256'])
            aux_rows.append(row)
            duration = next(r['seconds_including_instrumentation'] for r in terminal['completed']['auxiliary'] if r['id'] == target.name)
        else:
            native = json.loads((target / 'generation.json').read_bytes())
            assert native['generated_ids'] == ids and native['text'] == text
            packed_ids = b''.join(int(x).to_bytes(8, 'little', signed=True) for x in native['input_ids'])
            assert hashlib.sha256(packed_ids).hexdigest() == prepared['input_ids']['sha256']
            assert generation['max_new_tokens'] == 4096 and native['generation_config'] == generation
            duration = response['seconds_including_instrumentation']
        totals['seconds_including_instrumentation'] += duration
        all_rows.append(row)

paired = []
for case in plan['judges']:
    frozen = json.loads((PACKAGE / case['path']).read_bytes())
    public = frozen['view']; candidate = frozen['candidate']; native = parse(candidate)
    proposal = {'name': native['type'], 'parsed': True, 'executor_fallback_wait': False,
                'payload': native, 'coordinate_space': 'normalized_1000'}
    for condition in plan['conditions']:
        requests = []
        for target in sorted((ROOT / 'worker/judges').iterdir()):
            request = json.loads((target / 'request.json').read_bytes())
            if request['case'] == case['id'] and request['condition'] == condition:
                requests.append((target, request))
        assert 1 <= len(requests) <= 2
        calls = {'n': 0}
        view = PublicView(public['observation_id'], copy.deepcopy(public['messages']),
                          tuple(VisibleImage(base64.b64decode(im['raw_base64']), im['role']) for im in public['images']),
                          public['recent_action'], public['execution_feedback'], public['observed_at'])
        def replay(system, actual_view, actual_candidate):
            target, request = requests[calls['n']]; calls['n'] += 1
            assert actual_candidate == candidate == request['candidate']
            assert system == request['controller_system_before_condition']
            expected = with_exploratory_action_scope(system, proposal) if condition == plan['conditions'][1] else system
            assert expected == request['system']
            assert actual_view.data() == request['public']
            assert [im.raw for im in actual_view.images] == [base64.b64decode(im['raw_base64']) for im in request['images']]
            return (target / 'raw-output.txt').read_text(encoding='utf8')
        controller = Controller(replay, Journal(out / (case['id'] + '-' + condition)), 'post_only',
                                Limits(max_verifier_calls=2, max_format_retries=1), sleeper=lambda _: None)
        saved = json.loads((ROOT / 'worker' / (case['id'] + '-' + condition + '-result.json')).read_bytes())
        try:
            verdict = controller.inspect('verify', view, candidate, proposal)
            assert saved['format_citation_contract_valid'] and verdict == saved['verdict']
        except ValidationError as exc:
            assert saved['format_citation_contract_valid'] is False and str(exc) == saved['error']
        assert calls['n'] == len(requests) == saved['actual_judge_calls']
        paired.append({'id': case['id'], 'condition': condition,
                       'actual_calls': calls['n'], 'strict_CPU_replay_equal_original_terminal': True,
                       'format_citation_contract_valid': saved['format_citation_contract_valid'],
                       'original_error': saved.get('error'), 'semantic_pass': None})

assert len(aux_rows) == 3 and len(all_rows) == 26 and len(paired) == 16
assert len(terminal['attempted']['judge']) == len(terminal['completed']['judge']) == 23
result = {'schema': 'closed-controls08-full-bindings-audit-v1', 'passed': True,
          'time': time.time(), 'manifest_sha256': receipt['manifest_sha256'],
          'collection_receipt_sha256': sha(COLLECTION / 'receipt.json'),
          'all_terminal_original_files_verified': len(receipt['all_terminal_original_files']),
          'source_files_verified': receipt['source_files_verified'],
          'worker_and_launcher_actually_absent': True, 'terminal_and_exit_codes_verified': True,
          'all_event_chains_verified': receipt['chains'], 'actual_attempts': 26,
          'natural_EOS_replies': 26, 'actual_auxiliary_calls': 3, 'actual_judge_calls': 23,
          'auxiliary': aux_rows, 'requests': all_rows, 'paired_controls': paired,
          'format_citation_valid_conditions': sum(r['format_citation_contract_valid'] for r in paired),
          'not_semantic_passes': True, 'totals': totals,
          'seconds_include_instrumentation_not_walltime_currency_or_energy': True,
          'new_model_GPU_GUI_scorer_paid_calls_in_this_audit': 0,
          'full_GUI_release_or_defense_efficacy_established': False, 'goal': 'active'}
save(out / 'receipt.json', result)
save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
print(json.dumps({'audit': str(out / 'receipt.json'), 'sha256': sha(out / 'receipt.json'),
                  'passed': True, 'paired_conditions_format_valid': result['format_citation_valid_conditions'],
                  'totals': totals}, ensure_ascii=False))
