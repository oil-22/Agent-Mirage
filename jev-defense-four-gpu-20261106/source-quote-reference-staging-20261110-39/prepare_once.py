"""Prepare and test a proposed source-reference wire condition, never deploy."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'remaining29-full-history-gui-20261110-37'
PACKAGE = PREVIOUS / 'runtime-package'
EXPECTED = '368b0a594822f5e294fcd21927aa924a18a80f23249f160857b5de7090c1c02d'
sys.path.insert(0, str(PREVIOUS))
from join_source_reviews import verify_seal


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    with Path(path).open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def replace_once(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after, 1)


def function_ast(path, name):
    found = [n for n in ast.walk(ast.parse(Path(path).read_text(encoding='utf8')))
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    assert len(found) == 1, name
    return ast.dump(found[0], include_attributes=False)


def main():
    assert not (HERE / 'preparation-created.json').exists(), 'Inspect the sealed attempt, never repeat'
    assert sha(PACKAGE / 'manifest.json') == EXPECTED
    manifest = read(PACKAGE / 'manifest.json')
    for name, expected in manifest['files'].items():
        assert sha(PACKAGE / name) == expected, name
    old = read(HERE.parent / 'source-quote-grammar-staging-20261110-38/preparation-created.json')
    old_root = Path(old['root'])
    assert verify_seal(old_root) == old['seal_sha256']
    assert sha(old_root / 'receipt.json') == old['receipt_sha256']
    preservation = read(PREVIOUS / 'postexit-preservation-linked02-created.json')
    preserved = Path(preservation['root'])
    assert verify_seal(preserved) == preservation['seal_sha256']
    target = HERE / ('source-reference-CPU-' + str(time.time_ns()))
    target.mkdir()
    for name in ['prepare_once.py', 'source_quote_references.py', 'test_source_quote_references.py']:
        (target / name).write_bytes((HERE / name).read_bytes())
    release = target / 'proposed-release'
    for name in manifest['files']:
        if name.startswith('release/'):
            path = release / name.removeprefix('release/')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((PACKAGE / name).read_bytes())
    (release / 'source_quote_options.py').write_bytes((old_root / 'source_quote_options.py').read_bytes())
    (release / 'source_quote_references.py').write_bytes((target / 'source_quote_references.py').read_bytes())
    schema = release / 'defense/schema.py'
    text = schema.read_text(encoding='utf8')
    text = replace_once(text, "{None,'history_report'}", "{None,'history_report','exact_source_reference'}")
    text = replace_once(text, "    return obj({'claims':array(", "    result = obj({'claims':array(")
    ending = "        'acknowledges_visual_deficit':BOOL,'pure_wait':BOOL})"
    text = replace_once(text, ending, ending + "\n    if phase=='exact_source_reference':\n        from source_quote_references import bind_reference_schema\n        result=bind_reference_schema(result,candidate)\n    return result")
    schema.write_text(text, encoding='utf8')
    backend = release / 'defense/qwen_backend.py'
    text = backend.read_text(encoding='utf8')
    text = replace_once(text, 'from .schema import judge_schema',
        'from .schema import judge_schema\nfrom .prompts import VERIFY')
    text = replace_once(text, "phase='history_report'if system.startswith(HISTORY_REPORT)else None",
        "phase='history_report'if system.startswith(HISTORY_REPORT)else'exact_source_reference'if system.startswith(VERIFY)else None")
    backend.write_text(text, encoding='utf8')
    units = release / 'candidate_units.py'
    text = units.read_text(encoding='utf8')
    text = replace_once(text, 'def extraction_instructions(units):\n',
        'def extraction_instructions(units):\n    from source_quote_references import extraction_boundary\n')
    text = replace_once(text, "''' + json.dumps(units, ensure_ascii=False, separators=(',', ':'))",
        "''' + json.dumps(units, ensure_ascii=False, separators=(',', ':')) + extraction_boundary(units)")
    units.write_text(text, encoding='utf8')
    core = release / 'defense/core.py'
    text = core.read_text(encoding='utf8')
    text = replace_once(text, 'from decoded_answer_source import check_with_exact_answer_source',
        'from decoded_answer_source import check_with_exact_answer_source\nfrom source_quote_references import resolve_references, QuoteReferenceError')
    text = replace_once(text, "DEFENSE_VERSION='evidence-v4.0.12-STAGED-native-answer-source-20261110'",
        "DEFENSE_VERSION='evidence-v4.0.14-STAGED-source-reference-wire-20261110'")
    boundary = "                if not isinstance(value,dict):raise ValidationError('Judge did not return JSON object')"
    insertion = """
                if phase=='verify':
                    try:value,source_binding=resolve_references(value,candidate)
                    except QuoteReferenceError as error:
                        raise ValidationError('Exact candidate quote reference invalid: '+str(error))from error
                    self.log.append('candidate_quote_reference_resolved',source_binding)"""
    text = replace_once(text, boundary, boundary + insertion)
    core.write_text(text, encoding='utf8')
    modified = [name.removeprefix('release/') for name, value in manifest['files'].items()
                if name.startswith('release/') and sha(release / name.removeprefix('release/')) != value]
    assert sorted(modified) == ['candidate_units.py', 'defense/core.py', 'defense/qwen_backend.py', 'defense/schema.py']
    unchanged_functions = [('defense/qwen_backend.py', 'generate'), ('candidate_units.py', 'candidate_source_units')]
    for name in ['validate_evidence', 'validate_verdict', 'validate_screen', 'validate_point',
                 'validate_alignment', 'validate_history_relation', 'decide', 'reference_view',
                 'check_current_focus', 'check_current_point', 'check_target_alignment', 'resolve_history_reports']:
        unchanged_functions.append(('defense/core.py', name))
    for filename, name in unchanged_functions:
        assert function_ast(release / filename, name) == function_ast(PACKAGE / 'release' / filename, name), name
    # Removing the one declared resolution block must reproduce the entire old
    # inspect() AST, including its original bounded retry handling and budget.
    normalized = text.replace(insertion, '', 1)
    old_inspect = function_ast(PACKAGE / 'release/defense/core.py', 'inspect')
    nodes = [n for n in ast.walk(ast.parse(normalized)) if isinstance(n, ast.FunctionDef) and n.name == 'inspect']
    assert len(nodes) == 1 and ast.dump(nodes[0], include_attributes=False) == old_inspect
    for file in release.rglob('*.py'):
        compile(file.read_text(encoding='utf8'), str(file), 'exec')
    save(target / 'source-authorities.json', dict(original_manifest_sha256=EXPECTED,
        sealed_enumeration_source=old, original_postexit_preservation=preservation,
        unchanged_functions=unchanged_functions, inspect_only_change='resolve a copy of verify wire references inside original bounded try/retry',
        modified_release_files=modified, unchanged_auxiliary_fixed_v6_and_single_image_boundary=True,
        full_original_scope=dict(tracks=32, pairs=16, selected_tasks=8), remaining_unstarted=28))
    result = subprocess.run([sys.executable, str(target / 'test_source_quote_references.py'),
        '--release', str(release), '--previous', str(PREVIOUS), '--preserved', str(preserved)],
        capture_output=True, text=True, encoding='utf8', timeout=55)
    (target / 'CPU.stdout.txt').write_text(result.stdout, encoding='utf8')
    (target / 'CPU.stderr.txt').write_text(result.stderr, encoding='utf8')
    if result.returncode:
        save(target / 'failure.json', dict(stage='CPU_source_reference_boundary', returncode=result.returncode,
            new_model_GUI_scorer_calls=0, original_experiment_not_changed=True))
        save(target / 'seal.json', {p.relative_to(target).as_posix(): sha(p) for p in target.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
        raise RuntimeError(str(target) + '\n' + result.stderr[-2500:])
    condition = dict(stage='proposed_only', user_decision_received=False,
        change='Main verify wire claims[].quote_id replaces free text; exact source units resolve on a copy before every unchanged original validator.',
        tradeoff='Verifier prompt adds the full ID-to-source table and decoding chooses a source ID instead of freely quoting text. Whole mechanical units may contain several clauses; arbitrary subquotes or merged units are unavailable. This can change extraction, statuses, capacity or behavior despite unchanged per-call output limits. IDs guarantee provenance only, not complete extraction or truth.',
        raw_model_wire_reply_preserved_and_different_from_resolved_copy=True,
        no_source_option_truth_labels=True, native_generation_function_AST_unchanged=True,
        verifier_prompt_wire_and_decoding_condition_changed=True,
        original_images_complete_main_history_BF16_SDPA_native_actions_scoring_and_budgets_unchanged=True,
        four_completed_tracks_immutable=True, remaining_original_unstarted_tracks=28,
        real_model_negative_WAIT_semantic_and_capacity_controls_not_run=True)
    save(target / 'condition-boundary.json', condition)
    save(target / 'receipt.json', dict(time=time.time(), CPU_passed=True,
        proposed_only_not_deployed=True, controls_log='CPU.stderr.txt',
        modified_release_files=modified, new_release_files=['source_quote_options.py', 'source_quote_references.py'],
        original_validators_native_generation_decide_and_budgets_AST_unchanged=True,
        no_real_model_semantic_pass=True, formal_condition_decision_still_required=True,
        new_model_GPU_GUI_scorer_paid_calls=0, efficacy_established=False, goal='active'))
    save(target / 'seal.json', {p.relative_to(target).as_posix(): sha(p) for p in target.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    pointer = dict(root=str(target), receipt_sha256=sha(target / 'receipt.json'), seal_sha256=sha(target / 'seal.json'))
    save(HERE / 'preparation-created.json', pointer)
    print(json.dumps(pointer))


if __name__ == '__main__':
    main()
