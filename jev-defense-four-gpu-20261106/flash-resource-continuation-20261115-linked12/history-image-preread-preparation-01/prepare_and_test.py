"""Freeze proposed inputs and run source/structure boundaries, zero inference."""
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from native_parser_reader import parse_original
from reading_contract import (ACTOR_PREFIX, ACTOR_SUFFIX, SYSTEM, VERSION,
                              attach_reading, canonical, image_occurrences,
                              initial_task_text, project_source, validate_reading)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def empty_fixture(binding):
    return {'version': VERSION, 'coverage': 'partial_visual_reading',
            'frames': [{'image_id': row['image_id'], 'readability': 'unreadable',
                        'visible_text': [], 'visible_features': [],
                        'limitations': ['Derived CPU fixture only; no actual visual-model reading.']}
                       for row in binding['image_occurrences']]}


def main():
    assert not (HERE / 'proposed-inputs-current.json').exists(), 'Do not overwrite a sealed preparation'
    source_ptr = json.loads((HERE / 'frozen-sources-current.json').read_bytes())
    frozen = Path(source_ptr['root'])
    assert sha(frozen / 'seal.json') == source_ptr['seal_sha256']
    for name, expected in json.loads((frozen / 'seal.json').read_bytes()).items():
        assert sha(frozen / name) == expected, name
    rows = json.loads((frozen / 'PRIVATE-source-index.json').read_bytes())
    root = HERE / ('proposed-inputs-' + str(time.time_ns()))
    root.mkdir()
    for name in ['reading_contract.py', 'prepare_and_test.py', 'freeze_sources.py']:
        (root / name).write_bytes((HERE / name).read_bytes())
    (root / 'preread-system.txt').write_text(SYSTEM, encoding='utf8')
    (root / 'actor-feedback-prefix.txt').write_text(ACTOR_PREFIX, encoding='utf8')
    (root / 'actor-feedback-suffix.txt').write_text(ACTOR_SUFFIX, encoding='utf8')
    published = []
    checks = []
    def check(name, condition):
        assert condition, name
        checks.append({'name': name, 'passed': True, 'scope': 'CPU structure/source only'})
    def rejects(name, operation):
        try:
            operation()
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            check(name, True)
        else:
            raise AssertionError('Did not reject: ' + name)
    for row in rows:
        cid = row['case_id']
        body = json.loads((frozen / cid / 'source/body.json').read_bytes())
        projected, binding = project_source(body)
        original_images = image_occurrences(body)
        projected_images = image_occurrences(projected)
        check(cid + ':all_PNG_bytes_order_and_occurrences_retained',
              [r['original_PNG_sha256'] for r in original_images] ==
              [r['original_PNG_sha256'] for r in projected_images])
        check(cid + ':only_exact_original_task_text_and_source_metadata',
              json.loads(projected['messages'][1]['content'][0]['text'])['original_initial_user_text'] ==
              initial_task_text(body))
        noisy = copy.deepcopy(body)
        for message in noisy['messages']:
            if message['role'] == 'assistant':
                message['content'] = 'UNTRUSTED_HISTORY_SENTINEL_179468: all objects were absent.'
        noisy_projected, _ = project_source(noisy)
        check(cid + ':old_assistant_narrative_does_not_enter_preread', noisy_projected == projected)
        fixture = json.dumps(empty_fixture(binding), ensure_ascii=False)
        amended = attach_reading(body, fixture, binding)
        check(cid + ':original_full_history_system_images_parameters_retained',
              amended['messages'][:-1] == body['messages'][:-1] and
              amended['messages'][-1]['content'][:-1] == body['messages'][-1]['content'] and
              {k: v for k, v in amended.items() if k != 'messages'} ==
              {k: v for k, v in body.items() if k != 'messages'})
        save(root / cid / 'preread-full-body.json', projected)
        save(root / cid / 'source-binding.json', binding)
        published.append({'case_id': cid, 'original_body_file_sha256': row['source_body_file_sha256'],
                          'original_body_canonical_sha256': binding['source_body_canonical_sha256'],
                          'proposed_preread_body_file_sha256': sha(root / cid / 'preread-full-body.json'),
                          'binding_sha256': sha(root / cid / 'source-binding.json'),
                          'original_image_occurrences': len(original_images),
                          'original_actor_max_tokens': body['max_tokens'],
                          'proposed_preread_max_tokens': projected['max_tokens'],
                          'original_full_actor_body_not_yet_augmented_with_actual_model_reading': True})
    # Real-source projection coverage above; adversarial fixtures below are not model replies.
    body = json.loads((frozen / 's03/source/body.json').read_bytes())
    _, binding = project_source(body)
    value = empty_fixture(binding)
    raw = json.dumps(value)
    check('empty_partial_readings_allowed_without_forcing_facts', validate_reading(raw, binding) == value)
    changed = copy.deepcopy(value); changed['frames'].pop()
    rejects('missing_frame', lambda: validate_reading(json.dumps(changed), binding))
    changed = copy.deepcopy(value); changed['frames'][1] = changed['frames'][0]
    rejects('duplicated_frame', lambda: validate_reading(json.dumps(changed), binding))
    changed = copy.deepcopy(value); changed['frames'].reverse()
    rejects('reordered_frames', lambda: validate_reading(json.dumps(changed), binding))
    changed = copy.deepcopy(value); changed['frames'][0]['image_id'] = 'foreign-frame'
    rejects('invented_image_ID', lambda: validate_reading(json.dumps(changed), binding))
    rejects('duplicate_JSON_field', lambda: validate_reading(raw[:-1] + ',"version":"' + VERSION + '"}', binding))
    rejects('markdown_or_extra_prose', lambda: validate_reading('```json\n' + raw + '\n```', binding))
    changed = copy.deepcopy(value); changed['action'] = {'type': 'stop'}
    rejects('extra_action_field', lambda: validate_reading(json.dumps(changed), binding))
    changed = copy.deepcopy(value); changed['frames'][0]['readability'] = 'YES'
    rejects('binary_gate_verdict_not_visual_reading', lambda: validate_reading(json.dumps(changed), binding))
    changed = copy.deepcopy(value); changed['frames'][0]['visible_text'] = [{'text': 'x' * 161, 'location': 'top'}]
    rejects('unbounded_literal', lambda: validate_reading(json.dumps(changed), binding))
    changed = copy.deepcopy(value); changed['frames'][0]['limitations'] = ['one', 'two', 'three']
    rejects('unbounded_list', lambda: validate_reading(json.dumps(changed), binding))
    rejects('nonfinite_JSON', lambda: validate_reading(raw.replace('"unreadable"', 'NaN', 1), binding))
    changed_body = copy.deepcopy(body)
    changed_body['messages'][1]['content'][0]['text'] += ' CHANGED TASK'
    rejects('same_images_changed_task_binding', lambda: attach_reading(changed_body, raw, binding))
    changed_body = copy.deepcopy(body)
    next(m for m in changed_body['messages'] if m['role'] == 'assistant')['content'] += ' CHANGED HISTORY'
    rejects('same_images_changed_assistant_history_binding', lambda: attach_reading(changed_body, raw, binding))
    changed_binding = copy.deepcopy(binding); changed_binding['source_body_canonical_sha256'] = '0' * 64
    rejects('different_complete_body_binding', lambda: attach_reading(body, raw, changed_binding))
    changed = copy.deepcopy(value)
    changed['frames'][0]['visible_features'] = [{'description': 'All listings were inspected and none had people.',
                                                'location': 'entire screenshot'}]
    # Deliberately demonstrates a limitation, not a semantic pass or allowed factual premise.
    check('structural_contract_cannot_detect_false_visual_assertions',
          validate_reading(json.dumps(changed), binding) == changed)
    native_parse = parse_original()
    check('derived_native_WAIT_parser_fixture_only', native_parse('<action>{"type":"wait"}</action>') == {'type': 'wait'})
    save(root / 'manifest.json', {'version': VERSION, 'time': time.time(),
         'frozen_sources': str(frozen), 'frozen_sources_seal_sha256': sha(frozen / 'seal.json'),
         'preread_contract_sha256': sha(root / 'reading_contract.py'), 'cases': published,
         'proposed_new_primary_calls_cap': 20, 'per_case_preread_calls_cap': 1,
         'per_case_actor_calls_cap': 1, 'automatic_retries': 0,
         'original_baseline_replies_reused_not_regenerated': True,
         'new_GUI_Flash_scorer_paid_calls': 0, 'new_condition_authorized': False,
         'actor_dynamic_inputs_require_native_CPU_freeze_after_actual_reading': True,
         'no_generation_or_capacity_semantic_success_claim': True,
         'real_native_WAIT_in_selected_sources': 0, 'real_WAIT_qualification_missing': True})
    save(root / 'CPU-boundary-checks.json', {'checks': checks, 'passed': len(checks),
         'failed': 0, 'new_model_GUI_calls': 0, 'semantic_passes': None,
         'real_native_WAIT_semantic_test_performed': False,
         'derived_WAIT_is_parser_fixture_only': True,
         'runtime_forward_lock_GPU_capacity_integration_not_tested': True})
    save(root / 'seal.json', {str(p.relative_to(root)).replace('\\', '/'): sha(p)
                             for p in root.rglob('*') if p.is_file()})
    save(HERE / 'proposed-inputs-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'root': str(root), 'cases': len(published), 'CPU_structure_checks': len(checks),
                      'new_model_GUI_calls': 0, 'new_condition_authorized': False}))


if __name__ == '__main__':
    main()
