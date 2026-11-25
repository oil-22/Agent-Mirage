"""Linked read-only retry: primary output text lives in native-call.json."""
import json
from pathlib import Path
import sys
import time

from collect_main_trace_once import HERE, BASE, remote, save, sha, verify


def main():
    assert not (HERE / 'collected.json').exists(), 'Do not repeat a completed collector'
    failure = json.loads((HERE / 'read-failure-preserved.json').read_bytes())
    preserved = Path(failure['root'])
    verify(preserved, failure['seal_sha256'])
    assert sha(preserved / 'receipt.json') == failure['receipt_sha256']
    prior = json.loads((preserved / 'prior-native-bindings.json').read_bytes())
    for pointer in prior['authorities'].values():
        verify(Path(pointer['root']), pointer['seal_sha256'])
    source = (preserved / 'operation-source.py').read_text(encoding='utf8')
    # Change only the diagnostic reader's primary reply filename/field. The failed
    # collector and failed source remain immutable, and no experiment is rerun.
    assert source.count("'raw-output.txt'") == 3
    source = source.replace("'raw-output.txt'", "'native-call.json'")
    old = "'raw_output':(p/'native-call.json').read_text(encoding='utf8'),"
    assert source.count(old) == 1
    source = source.replace(old, "'raw_output':json.loads((p/'native-call.json').read_bytes())['text'],")
    source = source.replace("'original_raw_output_sha256':files['native-call.json']", "'original_native_call_file_sha256':files['native-call.json']")
    old = "assert payload['operation']=='judge'"
    assert source.count(old) == 1
    source = source.replace(old, old + "\n assert sha(p/'response.json')==files['response.json']\n assert json.loads((p/'response.json').read_bytes())['verdict']==json.loads((p/'native-call.json').read_bytes())['text']")
    compile(source, 'linked02-read-native-primary-output-text', 'exec')
    out = HERE / ('original-checker-trace-linked02-' + str(time.time_ns()))
    out.mkdir()
    (out / 'linked02-remote-source.py').write_text(source, encoding='utf8')
    raw, operation = remote('3090', source, 'five-completed-checker-entailment-sources-readonly-linked02', timeout=55)
    actual = json.loads(raw)
    assert {row['request'] for row in actual['rows']} == {'0068', '0079', '0096', '0098', '0099'}
    for row in actual['rows']:
        original = prior['rows'][row['request']]
        assert row['raw_output'] == original['binding']['response']['verdict']
        assert row['canonical_payload_sha256'] == original['binding']['payload_sha256']
        assert row['original_wire_sha256'] == original['binding']['wire_sha256']
        assert row['request_seal_sha256'] == original['request_seal_sha256']
    save(out / 'actual-original-source-projection.json', dict(actual, remote_operation=str(operation)))
    save(out / 'prior-native-bindings.json', prior)
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out / 'receipt.json', dict(time=time.time(), failed_read_preservation=failure,
        repair='Only metadata-reader filename and text field changed; original raw primary text equals original HTTP verdict',
        original_model_and_GUI_requests_replies_budgets_unchanged=True,
        new_model_GUI_capture_action_scorer_paid_calls=0))
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    result = dict(root=str(out), native_bindings_sha256=sha(out / 'prior-native-bindings.json'),
        actual_projection_sha256=sha(out / 'actual-original-source-projection.json'),
        seal_sha256=sha(out / 'seal.json'), original_checker_requests=5,
        initial_read_failure_preserved=failure, new_model_GUI_capture_action_scorer_paid_calls=0)
    save(HERE / 'collected.json', result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf8')
    main()
