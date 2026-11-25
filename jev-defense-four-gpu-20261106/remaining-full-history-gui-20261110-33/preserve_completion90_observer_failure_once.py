"""Preserve a read-only observer's mistaken image metadata-key assumption."""
import json
from pathlib import Path
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def main():
    pointer = HERE / 'completion90-observer-failure-preservation-created.json'
    assert not pointer.exists()
    actual = json.loads((HERE / 'source14-completion-0090-source-created.json').read_bytes())
    source = Path(actual['root'])
    assert verify_seal(source) == actual['seal_sha256']
    root = HERE / ('completion90-observer-failure-preservation-' + str(time.time_ns()))
    root.mkdir()
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (root / 'recorded-failed-stdin-source.py').write_bytes((HERE / 'completion90-input-observer-failed-source.py').read_bytes())
    (root / 'captured-tool-failure-excerpt.txt').write_text(
        'Original exec_command chunk_id: c9912a\nExit code: 1\n'
        'CANDIDATE None\nMESSAGES_COUNT 1 MATCHES_REVIEWED_0079 False\n'
        'Traceback (most recent call last):\n'
        '  File "<stdin>", line 8, in <module>\n'
        "KeyError: 'sha256'\n", encoding='utf8')
    save(root / 'preservation.json', dict(schema='read-only-observer-failure-before-linked-repair-v1',
        time=time.time(), original_tool_chunk='c9912a', original_exit_code=1,
        exact_failure_type='KeyError', exact_missing_key='sha256',
        captured_excerpt_is_not_a_claim_of_complete_stdout_bytes=True,
        failed_stdin_source_recorded_from_tool_command_not_original_OS_stdin_byte_capture=True,
        complete_printed_system_preserved_in_original_payload=True,
        original_input_authority=actual, original_payload_sha256=sha(source / 'payload.json'),
        cause='Local observer assumed payload-image dictionaries expose metadata sha256. They carry raw_base64 instead. No model/source/input/validator failed or changed.',
        linked_repair_scope='Derive image SHA from preserved complete raw bytes and compare inventories;review the actual image-only completion input,not an assumed actor-history view.',
        original_requests_replies_images_and_model_receipts_retained=True,
        no_model_GUI_scorer_paid_calls=0, no_experiment_retry_or_budget_change=True))
    save(root / 'seal.json', {p.name:sha(p) for p in root.iterdir() if p.is_file()})
    result = dict(root=str(root), preservation_sha256=sha(root / 'preservation.json'), seal_sha256=sha(root / 'seal.json'))
    save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
