"""Verify the completed two-call technical attempt, never launch another call."""
import ast
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import time

HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'runtime-package'
COLLECTION = HERE / 'terminal-collection-1794213181071816100'
ROOT = COLLECTION / 'original'
sys.path[:0] = [str(PACKAGE), str(PACKAGE / 'release')]
from defense.core import Controller, Journal, Limits, PublicView, VisibleImage, ValidationError
import image_evidence as contract
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    with p.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')


for name, expected in json.loads((COLLECTION / 'seal.json').read_bytes()).items():
    assert sha(COLLECTION / name) == expected, name
collection = json.loads((COLLECTION / 'receipt.json').read_bytes())
assert collection['terminal_collection']
assert all(v['actual'].get('absent') is True for v in collection['actual_processes'].values())
for name, expected in collection['exported_files'].items():
    assert sha(ROOT / name) == expected, name
m = json.loads((PACKAGE / 'manifest.json').read_bytes())
assert sha(PACKAGE / 'manifest.json') == collection['manifest_sha256']
for name, expected in m['files'].items():
    assert sha(PACKAGE / name) == expected, name
terminal = json.loads((ROOT / 'worker/terminal.json').read_bytes())
exited = json.loads((ROOT / 'exit.json').read_bytes())
assert terminal['status'] == 'completed' and terminal['error'] is None
assert exited['worker_exit_code'] == exited['launcher_exit_code'] == 0
assert terminal['attempted'] == ['auxiliary/A01', 'judge/J01']
out = HERE / ('completed-audit-' + str(time.time_ns())); out.mkdir()
loaded = json.loads((ROOT / 'worker/loaded.json').read_bytes())
assert loaded['primary_CUDA']['devices'] == ['cuda:0', 'cuda:1', 'cuda:2', 'cuda:3']
assert loaded['auxiliary_CUDA']['devices'] == ['cuda:3']
assert loaded['jev_relationship']['decision_adapter_loaded'] is False
assert loaded['primary_generation_backend_sha256'] == '11b6cd7a45a31c614b385909b3f43cc1484168fc6c2d2b0796face8495d359eb'
placement = json.loads((ROOT / 'worker/new-placement.json').read_bytes())
assert placement['primary_layer_counts'] == [22, 23, 19]
assert placement['device_map']['model.visual'] == placement['device_map']['model.language_model.embed_tokens'] == 3
rows = []
for call in ['auxiliary/A01', 'judge/J01']:
    p = ROOT / 'worker' / call
    prepared = json.loads((p / 'prepared.json').read_bytes())
    first = json.loads((p / 'first-forward.json').read_bytes())
    assert set(prepared) == set(first)
    for name in prepared:
        assert all(prepared[name][key] == first[name][key] for key in ['shape', 'dtype', 'bytes', 'sha256'])
    actual = json.loads((p / 'actual-generation.json').read_bytes())
    cfg = json.loads((p / 'effective-generation.json').read_bytes())
    ids = actual['output_ids']; eos = cfg['eos_token_id']
    eos = [eos] if isinstance(eos, int) else eos
    assert ids[-1] in eos and actual['natural_EOS'] and len(ids) == actual['output_tokens']
    text = (p / 'raw-output.txt').read_text(encoding='utf8')
    response = json.loads((p / 'response.json').read_bytes())
    assert response['text'] == text
    row = {'call': call, 'input_tokens': actual['input_tokens'], 'output_tokens': len(ids),
           'natural_EOS': True, 'actual_input_ids_sha256': prepared['input_ids']['sha256'],
           'actual_first_forward_equal_native_CPU': True, 'memory': actual['memory'],
           'seconds_including_instrumentation': response['seconds_including_instrumentation'],
           'seal_sha256': sha(p / 'seal.json')}
    if call.startswith('auxiliary'):
        request = json.loads((p / 'request.json').read_bytes())
        assert contract.validate_image_only_request(request) == (PACKAGE / 'new-auxiliary-full.png').read_bytes()
        assert contract.actor_packet(request, text, True) == json.loads((p / 'packet.json').read_bytes())
        boundary = json.loads((p / 'stateless-input-boundary.json').read_bytes())
        lifecycle = json.loads((p / 'stateless-context-discarded.json').read_bytes())
        assert boundary['message_count'] == 1 and boundary['content_types'] == ['image', 'text']
        assert lifecycle['actual_first_forward_cache_length'] == 0
        assert lifecycle['all_observed_cache_objects_released'] and lifecycle['observed_cache_objects_still_alive'] == 0
        assert lifecycle['call_id'] == boundary['call_id']
        assert boundary['task_history_candidate_previous_auxiliary_content_supplied'] is False
        mask = json.loads((p / 'actual-mask-steps.json').read_bytes())
        assert mask['all_actual_selected_tokens_allowed']
        assert [x['selected_id'] for x in mask['steps']] == ids
        assert cfg['max_new_tokens'] == 2048
    else:
        original = PACKAGE / 'original0178'
        assert sha(p / 'payload.json') == sha(original / 'payload.json') == m['original_payload_sha256']
        original_prepared = json.loads((original / 'prepared.json').read_bytes())
        for name in prepared:
            assert all(prepared[name][key] == original_prepared[name][key] for key in ['shape', 'dtype', 'bytes', 'sha256'])
        assert cfg == json.loads((original / 'effective-generation.json').read_bytes())
        assert cfg['max_new_tokens'] == 4096
        assert json.loads((p / 'original-input-equality-before-first-forward.json').read_bytes())['passed']
        assert json.loads((p / 'original-generation-configuration-equality.json').read_bytes())['passed']
        native = json.loads((p / 'generation.json').read_bytes())
        assert native['generated_ids'] == ids and native['text'] == text
        raw_ids = b''.join(int(x).to_bytes(8, 'little', signed=True) for x in native['input_ids'])
        assert hashlib.sha256(raw_ids).hexdigest() == m['original_input_ids_sha256']
        row['original_full_request_input_and_generation_equal'] = True
    rows.append(row)

payload = json.loads((PACKAGE / 'original0178/payload.json').read_bytes())
public = payload['view']; candidate = payload['candidate']
view = PublicView(public['observation_id'], copy.deepcopy(public['messages']),
                  tuple(VisibleImage(base64.b64decode(im['raw_base64']), im['role']) for im in public['images']),
                  public['recent_action'], public['execution_feedback'], public['observed_at'])
tree = ast.parse((PACKAGE / 'native-parser-source.py').read_text(encoding='utf8'))
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'parse')
ns = {'json': json, 're': re}; exec(compile(ast.Module(body=[node], type_ignores=[]), 'native-parser-source', 'exec'), ns)
native = ns['parse'](candidate)
proposal = {'name': native['type'], 'parsed': True, 'executor_fallback_wait': False,
            'payload': native, 'coordinate_space': 'normalized_1000'}
reply = (ROOT / 'worker/judge/J01/raw-output.txt').read_text(encoding='utf8')
replay = {'calls': 0}
def recorded(system, actual_view, actual_candidate):
    assert actual_candidate == candidate
    replay['calls'] += 1
    replay['constructed_system_equal_original_wire'] = system == payload['system']
    return reply
controller = Controller(recorded, Journal(out / 'strict-original-validator-CPU-replay'), 'post_only',
                        Limits(max_verifier_calls=1, max_format_retries=0), sleeper=lambda _: None)
try:
    verdict = controller.inspect('verify', view, candidate, proposal)
    save(out / 'strict-contract-result.json', {'format_citation_contract_valid': True, 'verdict': verdict})
    strict_valid = True
except ValidationError as exc:
    save(out / 'strict-contract-result.json', {'format_citation_contract_valid': False, 'error': str(exc), 'no_model_retry': True})
    strict_valid = False
assert replay['calls'] == 1

result = {'schema': 'completed-exact-full-input-capacity13-audit-v1', 'passed': True,
          'time': time.time(), 'manifest_sha256': collection['manifest_sha256'],
          'collection_receipt_sha256': sha(COLLECTION / 'receipt.json'),
          'all_terminal_original_files_verified': len(collection['all_terminal_original_files']),
          'source_files_verified': collection['source_files_verified'],
          'worker_and_launcher_actually_absent': True, 'terminal_and_exit_codes_verified': True,
          'all_event_chains_verified': collection['chains'], 'actual_attempts': 2, 'natural_EOS_replies': 2,
          'actual_auxiliary_calls': 1, 'actual_judge_calls': 1, 'requests': rows,
          'original_failed_request_input_tokens': 20382, 'original_complete_images': 4,
          'original_legal_messages': 46, 'primary_layer_counts': [22, 23, 19],
          'primary_visual_and_embeddings_share_physical7_with_one_auxiliary': True,
          'all_models_GPU_resident_BF16_SDPA_no_CPU_inference': True,
          'CPU_strict_replay': replay, 'format_citation_contract_valid': strict_valid,
          'four_GPU_reserved_seconds_in_launcher_only': exited['four_GPU_reserved_seconds_in_launcher'],
          'minimum_recorded_postgeneration_free_MiB': min(r['free_bytes'] for r in rows[1]['memory']) / 1024 ** 2,
          'all_future_full_history_inputs_fit_established': False, 'GUI_trajectory_resumed_or_recovered': False,
          'defense_efficacy_established': False, 'semantic_pass': None,
          'new_model_GPU_GUI_scorer_paid_calls_in_this_audit': 0, 'goal': 'active'}
save(out / 'receipt.json', result)
save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
print(json.dumps({'audit': str(out / 'receipt.json'), 'sha256': sha(out / 'receipt.json'),
                  'technical_capacity_passed': True, 'strict_contract_valid': strict_valid,
                  'minimum_recorded_postgeneration_free_MiB': result['minimum_recorded_postgeneration_free_MiB']}, ensure_ascii=False))
