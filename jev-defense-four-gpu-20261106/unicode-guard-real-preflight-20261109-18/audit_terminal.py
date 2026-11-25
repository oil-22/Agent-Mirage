"""Audit six sealed masked generations, complete tensors and stateless boundaries."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
import time
from PIL import Image

HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'runtime-package'
sys.path[:0] = [str(PACKAGE), str(PACKAGE / 'release')]
import image_evidence as contract

sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
digest = lambda raw: hashlib.sha256(raw).hexdigest()
canonical = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
read = lambda path: json.loads(Path(path).read_bytes())


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main(collection):
    original = collection / 'original'
    root = original / 'worker'
    receipt = read(collection / 'receipt.json')
    assert receipt['terminal_collection'] and receipt['new_model_GPU_GUI_scorer_paid_calls'] == 0
    for name, expected in read(collection / 'seal.json').items():
        assert sha(collection / name) == expected, name
    for name, expected in receipt['exported_files'].items():
        assert sha(original / name) == expected, name
    assert all(row['actual'].get('absent') is True for row in receipt['actual_processes'].values())
    manifest = read(PACKAGE / 'manifest.json')
    plan = read(PACKAGE / 'controls-plan.json')
    assert sha(PACKAGE / 'manifest.json') == receipt['manifest_sha256']
    for name, expected in manifest['files'].items():
        assert sha(PACKAGE / name) == expected, name
    expected_ids = [row['id'] for row in plan['auxiliary']]
    assert len(expected_ids) == 6 and plan['actors'] == [] and plan['judges'] == []
    terminal = read(root / 'terminal.json')
    exit_record = read(original / 'exit.json')
    assert terminal['status'] == 'completed' and terminal['error'] is None
    assert exit_record['worker_exit_code'] == exit_record['launcher_exit_code'] == 0
    assert terminal['attempted'] == {'auxiliary': expected_ids, 'actor': [], 'judge': []}
    assert len(terminal['completed']['auxiliary']) == 6
    assert terminal['completed']['actor'] == terminal['completed']['judge'] == []
    loaded = read(root / 'loaded.json')
    assert loaded['single_auxiliary']['repo'] == 'Qwen/Qwen3.5-9B'
    assert loaded['single_auxiliary']['revision'] == 'c202236235762e1c871ad0ccb60c8ee5ba337b9a'
    assert loaded['jev_relationship']['decision_adapter_loaded'] is False
    assert loaded['auxiliary_CUDA']['devices'] == ['cuda:3']
    assert set(loaded['primary_CUDA']['devices']) == {'cuda:0', 'cuda:1', 'cuda:2', 'cuda:3'}
    assert loaded['auxiliary_CUDA']['dtype_elements']['torch.bfloat16'] > 0
    assert loaded['primary_generation_backend_sha256'] == '11b6cd7a45a31c614b385909b3f43cc1484168fc6c2d2b0796face8495d359eb'
    old = HERE.parent / 'balanced-visual-evidence-20261109-16/runtime-package'
    for name in ['model_runtime.py', 'release/defense/core.py', 'release/defense/qwen_backend.py',
                 'stateless_boundary.py', 'image_evidence.py', 'bounded_schema.py', 'native_format_bridge.py']:
        assert sha(PACKAGE / name) == sha(old / name), name
    def native_calls(path):
        return [ast.dump(node, include_attributes=False) for node in ast.walk(ast.parse(path.read_text(encoding='utf8')))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ['generate', 'apply_chat_template']]
    assert native_calls(PACKAGE / 'bounded_auxiliary.py') == native_calls(old / 'bounded_auxiliary.py')
    cpu = read(HERE / 'CPU-admission.json')['value']['proof']
    cpu_tensors = {row['case']: row['tensors'] for row in cpu['auxiliary_inputs']}
    rows = []
    totals = {'input_tokens': 0, 'output_tokens': 0, 'summed_seconds_including_instrumentation': 0.0}
    call_ids = set()
    for source in plan['auxiliary']:
        target = root / 'auxiliary' / source['id']
        for name, expected in read(target / 'seal.json').items():
            assert receipt['all_terminal_original_files'][(target / name).relative_to(original).as_posix()] == expected
        prepared = read(target / 'prepared.json')
        forward = read(target / 'first-forward.json')
        assert set(prepared) == set(forward) == set(cpu_tensors[source['id']])
        for name in prepared:
            for key in ['shape', 'dtype', 'bytes', 'sha256']:
                assert prepared[name][key] == forward[name][key] == cpu_tensors[source['id']][name][key]
            for record in [prepared[name], forward[name]]:
                name = (target / record['file']).relative_to(original).as_posix()
                assert receipt['all_terminal_original_files'][name] == record['sha256'], name
        actual = read(target / 'actual-generation.json')
        generation = read(target / 'effective-generation.json')
        ids = actual['output_ids']
        eos = generation['eos_token_id']
        eos = [eos] if isinstance(eos, int) else eos
        assert len(ids) == actual['output_tokens'] == actual['actual_forward_calls']
        assert actual['natural_EOS'] and ids[-1] in eos
        assert actual['input_tokens'] == prepared['input_ids']['shape'][1]
        assert generation['max_new_tokens'] == 2048 and generation['do_sample'] is False
        text = (target / 'raw-output.txt').read_text(encoding='utf8')
        response = read(target / 'response.json')
        assert response['text'] == text and response['natural_EOS']
        request = read(target / 'request.json')
        assert request == read(PACKAGE / source['path'])
        raw = contract.validate_image_only_request(request)
        assert raw == (target / 'original.png').read_bytes()
        assert digest(raw) == source['image_sha256'] == request['image_sha256']
        boundary = read(target / 'stateless-input-boundary.json')
        life = read(target / 'stateless-context-discarded.json')
        assert boundary['message_count'] == 1 and boundary['content_types'] == ['image', 'text']
        assert boundary['task_history_candidate_previous_auxiliary_content_supplied'] is False
        assert boundary['complete_image_sha256'] == request['image_sha256']
        assert boundary['fixed_prompt_sha256'] == request['prompt_sha256'] == manifest['fixed_prompt_sha256']
        with Image.open(target / 'original.png') as image:
            assert list(image.size) == boundary['size'] == [1280, 720]
            assert digest(image.convert('RGB').tobytes()) == boundary['complete_RGB_sha256']
        assert life['call_id'] == boundary['call_id'] and life['call_id'] not in call_ids
        call_ids.add(life['call_id'])
        assert life['actual_first_forward_cache_length'] == 0
        assert life['all_observed_cache_objects_released'] and life['observed_cache_objects_still_alive'] == 0
        assert life['observed_cache_objects'] > 0 and life['untrackable_cache_types'] == []
        assert life['error_type'] is None and life['main_model_or_main_context_referenced'] is False
        mask = read(target / 'actual-mask-steps.json')
        assert mask['all_actual_selected_tokens_allowed'] and len(mask['steps']) == len(ids)
        prefix_ids = read(target / 'sequence_ids.json')
        # The runtime additionally seals each selected prefix hash and choice set.
        for token, step in zip(ids, mask['steps']):
            assert token == step['selected_id'] and step['selected_allowed']
        guard = read(target / 'unicode-length-guard.json')
        assert guard['source_sha256'] == sha(PACKAGE / 'unicode_length_guard.py')
        assert guard['subset_only'] and guard['strict_final_validator_unchanged']
        assert guard['native_selected_tokens_not_rewritten'] and guard['final_decoded_length_state_complete_before_EOS']
        assert guard['calls'] == len(ids)
        assert read(target / 'raw-UTF8-validation.json')['strict_native_UTF8_roundtrip']
        packet = contract.actor_packet(request, text, True)
        assert packet == read(target / 'packet.json')
        assert packet['automatic_allow_or_block'] is False and packet['semantic_correctness_established'] is False
        parsed = json.loads(text)
        rows.append({'case': source['id'], 'natural_EOS': True, 'input_tokens': actual['input_tokens'],
                     'output_tokens': len(ids), 'format_contract_valid': True, 'semantic_pass': None,
                     'actual_prepared_forward_CPU_tensors_and_remote_binary_SHA_equal': True,
                     'single_complete_image_fixed_prompt_empty_first_KV_and_released_context_verified': True,
                     'actual_mask_steps': len(mask['steps']), 'filtered_choices_sum': guard['filtered_choices_sum'],
                     'summary_characters': len(parsed['frame']['summary']),
                     'raw_output_sha256': sha(target / 'raw-output.txt'), 'image_sha256': request['image_sha256'],
                     'seal_sha256': sha(target / 'seal.json')})
        totals['input_tokens'] += actual['input_tokens']
        totals['output_tokens'] += len(ids)
        totals['summed_seconds_including_instrumentation'] += response['seconds_including_instrumentation']
    result = {'schema': 'unicode18-complete-technical-audit-v1', 'time': time.time(), 'passed': True,
              'terminal_collection': str(collection), 'collection_receipt_sha256': sha(collection / 'receipt.json'),
              'manifest_sha256': receipt['manifest_sha256'], 'all_original_files_verified': len(receipt['all_terminal_original_files']),
              'source_files_verified': receipt['source_files_verified'], 'chains': receipt['chains'],
              'actual_auxiliary_calls': 6, 'natural_EOS': 6, 'format_retries': 0, 'format_contract_valid': 6,
              'actor_judge_GUI_scorer_paid_calls': 0, 'strict_validator_and_main_generation_unchanged': True,
              'actual_auxiliary_identity': loaded['single_auxiliary'], 'decision_adapter_loaded': False,
              'all_calls': rows, 'totals': totals,
              'four_GPU_reserved_seconds_in_launcher': exit_record['four_GPU_reserved_seconds_in_launcher'],
              'holder_reservation_outside_launcher_excluded': True,
              'model_seconds_include_instrumentation_not_walltime_currency_energy': True,
              'new_model_calls_in_audit': 0, 'full_GUI_or_trajectory_reduction_established': False}
    out = HERE / ('terminal-audit-' + str(time.time_ns()))
    out.mkdir()
    save(out / 'receipt.json', result)
    save(out / 'seal.json', {q.relative_to(out).as_posix(): sha(q) for q in out.rglob('*') if q.is_file()})
    print(json.dumps({'audit': str(out), 'receipt_sha256': sha(out / 'receipt.json'), 'calls': 6,
                      'format_contract_valid': 6, 'totals': totals}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--collection', type=Path, required=True)
    main(parser.parse_args().collection)
