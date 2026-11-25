"""Freeze a proposed source-quote decoder on CPU; no GPU/GUI launch or retry."""
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


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    with Path(path).open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def replace_once(value, before, after):
    assert value.count(before) == 1, before
    return value.replace(before, after, 1)


def function_ast(path, name):
    nodes = [n for n in ast.walk(ast.parse(Path(path).read_text(encoding='utf8')))
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    assert len(nodes) == 1, name
    return ast.dump(nodes[0], include_attributes=False)


def main():
    assert not (HERE / 'preparation-created.json').exists(), 'Never repeat sealed preparation'
    assert sha(PACKAGE / 'manifest.json') == EXPECTED
    manifest = read(PACKAGE / 'manifest.json')
    for name, expected in manifest['files'].items():
        assert sha(PACKAGE / name) == expected, name
    terminal = read(PREVIOUS / 'logical-terminal-fullhistory23-T000-stale_replace-noaux-collected.json')
    assert sha(Path(terminal['collection']) / 'seal.json') == terminal['seal_sha256']
    preservation = read(PREVIOUS / 'postexit-preservation-linked02-created.json')
    preserved = Path(preservation['root'])
    assert sha(preserved / 'seal.json') == preservation['seal_sha256']
    for name, expected in read(preserved / 'seal.json').items():
        assert sha(preserved / name) == expected, name
    target = HERE / ('source-bound-quote-CPU-' + str(time.time_ns()))
    target.mkdir()
    for name in ['prepare_once.py', 'source_quote_options.py', 'test_source_quote_options.py']:
        (target / name).write_bytes((HERE / name).read_bytes())
    release = target / 'proposed-release'
    for name in manifest['files']:
        if name.startswith('release/'):
            destination = release / name.removeprefix('release/')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((PACKAGE / name).read_bytes())
    (release / 'source_quote_options.py').write_bytes((HERE / 'source_quote_options.py').read_bytes())
    schema = release / 'defense/schema.py'
    value = schema.read_text(encoding='utf8')
    value = replace_once(value, "{None,'history_report'}", "{None,'history_report','exact_source_quote'}")
    value = replace_once(value, "    return obj({'claims':array(", "    result = obj({'claims':array(")
    ending = "        'acknowledges_visual_deficit':BOOL,'pure_wait':BOOL})"
    value = replace_once(value, ending, ending + "\n    if phase=='exact_source_quote':\n        from source_quote_options import bind_quote_schema\n        result=bind_quote_schema(result,candidate)\n    return result")
    schema.write_text(value, encoding='utf8')
    backend = release / 'defense/qwen_backend.py'
    value = backend.read_text(encoding='utf8')
    value = replace_once(value, 'from .schema import judge_schema',
        'from .schema import judge_schema\nfrom .prompts import VERIFY')
    value = replace_once(value, "phase='history_report'if system.startswith(HISTORY_REPORT)else None",
        "phase='history_report'if system.startswith(HISTORY_REPORT)else'exact_source_quote'if system.startswith(VERIFY)else None")
    backend.write_text(value, encoding='utf8')
    units = release / 'candidate_units.py'
    value = units.read_text(encoding='utf8')
    value = replace_once(value, 'def extraction_instructions(units):\n',
        'def extraction_instructions(units):\n    from source_quote_options import extraction_boundary\n')
    value = replace_once(value, "''' + json.dumps(units, ensure_ascii=False, separators=(',', ':'))",
        "''' + json.dumps(units, ensure_ascii=False, separators=(',', ':')) + extraction_boundary(units)")
    units.write_text(value, encoding='utf8')
    core = release / 'defense/core.py'
    value = replace_once(core.read_text(encoding='utf8'),
        "DEFENSE_VERSION='evidence-v4.0.12-STAGED-native-answer-source-20261110'",
        "DEFENSE_VERSION='evidence-v4.0.13-STAGED-source-quote-options-20261110'")
    core.write_text(value, encoding='utf8')
    changes = []
    for name, expected in manifest['files'].items():
        if not name.startswith('release/'):
            continue
        relative = name.removeprefix('release/')
        if sha(release / relative) != expected:
            changes.append(relative)
    assert sorted(changes) == ['candidate_units.py', 'defense/core.py', 'defense/qwen_backend.py', 'defense/schema.py']
    # Main native sampling, processor, generation defaults, decoding and output
    # budgets are unedited. Only its existing verifier grammar gets new choices.
    assert function_ast(backend, 'generate') == function_ast(PACKAGE / 'release/defense/qwen_backend.py', 'generate')
    assert function_ast(units, 'candidate_source_units') == function_ast(PACKAGE / 'release/candidate_units.py', 'candidate_source_units')
    assert function_ast(core, 'validate_verdict') == function_ast(PACKAGE / 'release/defense/core.py', 'validate_verdict')
    assert function_ast(core, 'inspect') == function_ast(PACKAGE / 'release/defense/core.py', 'inspect')
    assert function_ast(core, 'decide') == function_ast(PACKAGE / 'release/defense/core.py', 'decide')
    for file in release.rglob('*.py'):
        compile(file.read_text(encoding='utf8'), str(file), 'exec')
    save(target / 'source-authorities.json', dict(original_manifest_sha256=EXPECTED,
        original_terminal=terminal, original_postexit_preservation=preservation,
        original_runtime_not_modified=True, modified_release_files=changes,
        current_remaining_unstarted_tracks=28, original_tracks=32, original_pairs=16,
        no_old_failed_control_or_terminal_reexecution=True))
    result = subprocess.run([sys.executable, str(target / 'test_source_quote_options.py'),
        '--release', str(release), '--previous', str(PREVIOUS), '--preserved', str(preserved)],
        capture_output=True, text=True, encoding='utf8', timeout=45)
    (target / 'CPU.stdout.txt').write_text(result.stdout, encoding='utf8')
    (target / 'CPU.stderr.txt').write_text(result.stderr, encoding='utf8')
    if result.returncode:
        save(target / 'failure.json', dict(stage='CPU_source_quote_boundary', returncode=result.returncode,
            new_model_GUI_scorer_calls=0, original_experiment_not_changed=True))
        save(target / 'seal.json', {f.relative_to(target).as_posix(): sha(f) for f in target.rglob('*') if f.is_file()})
        raise RuntimeError(str(target) + '\n' + result.stderr[-2000:])
    save(target / 'condition-boundary.json', dict(stage='proposed_only', user_decision_received=False,
        actual_model_generation_or_GUI_not_run=True,
        change='Restrict verify claims[].text to exact mechanical source units from the unchanged candidate or native STOP answer; all verdict statuses and original validators stay active.',
        tradeoff='Cannot emit arbitrary within-sentence subquotes or merge several units into one claim; more claims may use more of the original4096-token verifier output budget. Source-valid quotes can still be wrong, misclassified, omitted or miscited.',
        original_images_complete_main_history_BF16_SDPA_actions_scoring_budgets_unchanged=True,
        native_generation_function_AST_unchanged_but_verifier_decoding_choices_changed=True,
        auxiliary_9B_fixed_v6_single_image_stateless_unchanged=True,
        no_new_model_GUI_or_paid_budget_in_this_preparation=True,
        four_completed_tracks_remain_immutable=True, remaining_original_unstarted_tracks=28))
    save(target / 'receipt.json', dict(time=time.time(), CPU_passed=True,
        original_source_authorities='source-authorities.json', modified_release_files=changes,
        native_generate_original_validator_Controller_and_recovery_function_AST_unchanged=True,
        proposed_only_not_deployed=True, real_model_negative_WAIT_semantic_preflight_not_run=True,
        formal_condition_decision_still_required=True, efficacy_established=False,
        new_model_GPU_GUI_scorer_paid_calls=0, goal='active'))
    save(target / 'seal.json', {f.relative_to(target).as_posix(): sha(f) for f in target.rglob('*') if f.is_file()})
    pointer = dict(root=str(target), receipt_sha256=sha(target / 'receipt.json'), seal_sha256=sha(target / 'seal.json'))
    save(HERE / 'preparation-created.json', pointer)
    print(json.dumps(pointer))


if __name__ == '__main__':
    main()
