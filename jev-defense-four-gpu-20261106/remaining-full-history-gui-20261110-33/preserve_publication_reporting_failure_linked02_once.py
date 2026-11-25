"""Preserve a local-only report KeyError and prepare its one-key linked repair."""
import json
from pathlib import Path
import time

from orchestrate import HERE, BASE, save, sha
from join_source_reviews import verify_seal


def main():
    pointer = HERE / 'publication-reporting-linked02-created.json'
    assert not pointer.exists()
    failed = HERE / 'publish_two_actions_diagnosis_once.py'
    evidence = HERE / 'actual-evidence-1794253672868036700'
    verify_seal(evidence)
    assert 'batch/status.json' in json.loads((evidence / '4090.json').read_bytes())
    assert 'batch/state.json' not in json.loads((evidence / '4090.json').read_bytes())
    # The failed lookup precedes directory creation and every head mutation.
    assert not list(HERE.glob('two-actions-summary-diagnosis-publication-*'))
    earlier = json.loads((HERE / 'first-enabled-chain-publication-created.json').read_bytes())
    previous_root = Path(earlier['root'])
    assert verify_seal(previous_root) == earlier['seal_sha256']
    assert (BASE / 'full-gui-current.json').read_bytes() == (previous_root / 'status.json').read_bytes()
    root = HERE / ('publication-reporting-failure-preservation-' + str(time.time_ns()))
    root.mkdir()
    (root / failed.name).write_bytes(failed.read_bytes())
    for name in ['3090.json', '4090.json', 'seal.json']:
        (root / ('input-evidence-' + name)).write_bytes((evidence / name).read_bytes())
    for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']:
        (root / ('unmodified-head-' + name)).write_bytes((BASE / name).read_bytes())
    observed = '''Traceback (most recent call last):
  File "D:\\MultiModel\\jev-defense-four-gpu-20261106\\remaining-full-history-gui-20261110-33\\publish_two_actions_diagnosis_once.py", line 161, in <module>
    main(parser.parse_args().evidence.resolve())
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\\MultiModel\\jev-defense-four-gpu-20261106\\remaining-full-history-gui-20261110-33\\publish_two_actions_diagnosis_once.py", line 83, in main
    new31_GUI_state=gui['batch/state.json']['value'],
                    ~~~^^^^^^^^^^^^^^^^^^^^
KeyError: 'batch/state.json'
'''
    (root / 'observed-combined-tool-output-transcription.txt').write_text(observed, encoding='utf8')
    save(root / 'failure.json', dict(time=time.time(), type='KeyError', field='batch/state.json',
        actual_source_field='batch/status.json', exit_code=1, tool_chunk_id='3da7ee',
        input_evidence=str(evidence), input_evidence_seal_sha256=sha(evidence / 'seal.json'),
        failed_source_sha256=sha(failed), local_reporting_only=True,
        raw_stdout_stderr_not_separately_captured=True, observed_tool_output_transcribed=True,
        no_model_GUI_scorer_calls_from_failed_reporter=True,
        failure_before_output_directory_and_head_mutations=True,
        existing_live_remote_experiment_not_interrupted=True,
        original_auxiliary_replies_labels_and_budgets_unchanged=True))
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    source = failed.read_text(encoding='utf8')
    before = "new31_GUI_state=gui['batch/state.json']['value']"
    after = "new31_GUI_state=gui['batch/status.json']['value']"
    assert source.count(before) == 1
    repaired = source.replace(before, after)
    assert repaired.replace(after, before) == source
    linked = HERE / 'publish_two_actions_diagnosis_linked02.py'
    assert not linked.exists()
    with linked.open('x', encoding='utf8') as stream:
        stream.write(repaired)
    compile(linked.read_text(encoding='utf8'), str(linked), 'exec')
    result = dict(failure_preservation=str(root), failure_seal_sha256=sha(root / 'seal.json'),
                  failed_source_sha256=sha(failed), linked_source=str(linked), linked_source_sha256=sha(linked),
                  only_changed_expression=dict(before=before, after=after),
                  runtime_models_inputs_labels_budgets_unchanged=True, new_model_GUI_scorer_calls=0)
    save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
