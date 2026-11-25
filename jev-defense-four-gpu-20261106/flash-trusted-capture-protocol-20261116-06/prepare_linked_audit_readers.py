"""Preserve the I/O timeout and prepare linked audit-only continuations.

No model/GUI relaunch and no validator, tensor, probability or SHA check changes.
Only read batching, transport time allowance, and verified completed-read reuse.
"""
import ast
import json
import shutil
import time
from pathlib import Path

from remote_util import HERE, save, sha


def main():
    assert not (HERE / 'linked-audit-preparation-current.json').exists()
    failed = HERE / 'trajectory-audit-receipt16-T089-stale_replace-gate-1794809123623714200'
    command = HERE / 'current-turn-watcher/commands/1794809123547371800-audit_finished_trajectory'
    timeout_operation = HERE / 'operations/1794809142886616400-finished-trajectory-primary-008'
    assert not (failed / 'seal.json').exists()
    assert sha(failed / 'source.py') == sha(HERE / 'audit_finished_trajectory.py')
    assert json.loads((command / 'result.json').read_bytes())['return_code'] == 1
    assert json.loads((timeout_operation / 'failure.json').read_bytes())['type'] == 'TimeoutExpired'
    root = HERE / ('audit-IO-repair-' + str(time.time_ns()))
    root.mkdir()
    for label, source in [('failed-audit', failed), ('failed-command', command), ('failed-transport', timeout_operation)]:
        shutil.copytree(source, root / label)
    for name in ['audit_finished_trajectory.py', 'audit_completed_group.py', 'protocol_audit_components.py', 'remote_util.py']:
        (root / ('before-' + name)).write_bytes((HERE / name).read_bytes())
    original = (HERE / 'audit_finished_trajectory.py').read_text('utf8')
    new = original.replace("raw, operation = remote(host, code, 'finished-trajectory-' + name)",
                           "raw, operation = remote(host, code, 'finished-trajectory-linked-' + name, timeout=180)")
    cache = '''    original_result = REUSE_ROOT / (name + '.json')
    if name in {'Controller', 'trusted-source-receipts', 'request-bindings'} and original_result.exists():
        reused = verified_original_result(original_result)
        save(root / (name + '.json'), reused)
        return reused['result']
'''
    new = new.replace('    raw, operation = remote(host, code,', cache + '    raw, operation = remote(host, code,', 1)
    replacement = '''    mains, flashes = [], []
    old_primary = verified_original_result(REUSE_ROOT / 'primary-000.json')
    mains.extend(old_primary['result']['requests'])
    reused_names = {Path(v['folder']).name for v in mains}
    assert len(reused_names) == len(mains) == 8
    assert reused_names <= set(discovery['primary_names'])
    save(root / 'verified-completed-read-reuse.json', {'source': str(REUSE_ROOT), 'primary_requests': len(mains),
                                                     'request_ids': [v['request_id'] for v in mains],
                                                     'preservation_seal_sha256': PRESERVATION_SHA})
    discovery['primary_names'] = [v for v in discovery['primary_names'] if v not in reused_names]
'''
    assert new.count('    mains, flashes = [], []\n') == 1
    new = new.replace('    mains, flashes = [], []\n', replacement)
    new = new.replace('range(0, len(names), 8)', 'range(0, len(names), 1)').replace('names[i:i + 8]', 'names[i:i + 1]')
    new = new.replace("'group_still_running_at_audit': True", "'group_still_running_at_audit': False")
    new = new.replace("'whole_group_postexit_audit_pending': True, 'new_model_GUI_calls': 0", "'whole_group_postexit_audit_pending': True, 'linked_read_only_IO_repair': True, 'new_model_GUI_calls': 0")
    helper = '''
REUSE_ROOT = Path(__REUSE_ROOT__)
PRESERVATION_ROOT = Path(__PRESERVATION_ROOT__)
PRESERVATION_SHA = __PRESERVATION_SHA__

def verified_original_result(path):
    assert sha(PRESERVATION_ROOT / 'seal.json') == PRESERVATION_SHA
    preserved = json.loads((PRESERVATION_ROOT / 'seal.json').read_bytes())
    relative = 'failed-audit/' + path.name
    assert sha(path) == preserved[relative]
    cached = json.loads(path.read_bytes())
    operation = Path(cached['operation'])
    for name, expected in json.loads((operation / 'seal.json').read_bytes()).items():
        assert sha(operation / name) == expected
    assert json.loads((operation / 'receipt.json').read_bytes())['returncode'] == 0
    assert json.loads((operation / 'stdout.txt').read_bytes()) == cached['result']
    return cached

'''
    group_original = (HERE / 'audit_completed_group.py').read_text('utf8')
    group_new = group_original.replace("remote(host, code, 'new-trusted-capture-postexit-' + name)",
                                       "remote(host, code, 'new-trusted-capture-postexit-linked-' + name, timeout=180)")
    group_new = group_new.replace('range(0, len(names), 8)', 'range(0, len(names), 1)').replace('names[i:i + 8]', 'names[i:i + 1]')
    # Embedded source readers and every original assert remain unchanged.
    def assertions(source):
        return [ast.dump(n, include_attributes=False) for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Assert)]
    assert assertions(group_original) == assertions(group_new)
    save(root / 'change-review.json', {'failed_audit': str(failed), 'failed_command': str(command),
                                     'failed_transport': str(timeout_operation), 'failure': '55-second read-only SSH timeout',
                                     'original_successful_primary_reads_reused': 8, 'batch_size_before': 8,
                                     'batch_size_after': 1, 'transport_timeout_before': 55, 'transport_timeout_after': 180,
                                     'group_original_assert_ASTs_unchanged': True,
                                     'embedded_model_tensor_probability_and_SHA_readers_unchanged': True,
                                     'no_model_GUI_or_protocol_condition_change': True,
                                     'new_model_GUI_calls': 0})
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    helper = helper.replace('__REUSE_ROOT__', repr(str(failed))).replace('__PRESERVATION_ROOT__', repr(str(root))).replace('__PRESERVATION_SHA__', repr(sha(root / 'seal.json')))
    assert new.count("if __name__ == '__main__':") == 1
    new = new.replace("if __name__ == '__main__':", helper + "\nif __name__ == '__main__':")
    for name, content in [('audit_finished_trajectory_linked.py', new), ('audit_completed_group_linked.py', group_new)]:
        ast.parse(content)
        destination = HERE / name
        assert not destination.exists()
        destination.write_text(content, encoding='utf8')
    save(HERE / 'linked-audit-preparation-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
                                                       'trajectory_reader_sha256': sha(HERE / 'audit_finished_trajectory_linked.py'),
                                                       'group_reader_sha256': sha(HERE / 'audit_completed_group_linked.py'),
                                                       'new_model_GUI_calls': 0})
    print(json.dumps({'root': str(root), 'linked_readers_prepared': True, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
