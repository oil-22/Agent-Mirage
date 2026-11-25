"""Bind already fully checked SAME requests to the fresh whole-group raw seal.

Never reuses a different request or substitutes inputs. The unchanged original
launcher rehashes every raw file after model exit; its entire request map must
equal the union actually checked by the sealed per-trajectory tensor readers.
"""
import json
from pathlib import Path, PurePosixPath
from remote_util import HERE, save, sha


def strict_bind(mains, flashes, checked_map, final_map, primary_names, flash_names):
    request_map = {n: h for n, h in final_map.items()
                   if n.startswith(('primary/requests/', 'flash/service/requests/'))}
    assert checked_map == request_map, 'Every final raw request member hash must match the completed strict audit'
    assert len(mains) == len({v['request_id'] for v in mains}) == len(primary_names)
    assert len(flashes) == len({v['request_id'] for v in flashes}) == len(flash_names)
    assert {PurePosixPath(v['root']).name for v in mains} == set(primary_names)
    assert {v['request_id'] for v in flashes} == set(flash_names)
    for prefix, rows in [('primary/requests/', mains), ('flash/service/requests/', flashes)]:
        for row in rows:
            name = PurePosixPath(row['root']).name
            assert final_map[prefix + name + '/seal.json'] == row['seal_sha256']
            if prefix.startswith('primary'):
                assert row['actual_tensor_files_verified'] and row['exact_full_history_preserved'] and row['natural_EOS']
            else:
                assert row['actual_forward_tensor_bytes_verified'] and row['full_raw_head_probability_binding_verified']


def load(root, admission):
    preparation = json.loads((HERE / 'audit-preparation-current.json').read_bytes())
    preserved = Path(preparation['root'])
    assert sha(preserved / 'seal.json') == preparation['seal_sha256']
    for name, h in json.loads((preserved / 'seal.json').read_bytes()).items():
        assert sha(preserved / name) == h
    allowed_sources = {sha(preserved / 'audit_finished_trajectory.py')}
    assert sha(HERE / 'audit_finished_trajectory.py') in allowed_sources
    mains, flashes, checked, bindings, run_ids = [], [], {}, [], set()
    for audit in sorted(HERE.glob('trajectory-audit-*')):
        if not (audit / 'seal.json').exists():
            continue
        members = json.loads((audit / 'seal.json').read_bytes())
        assert set(members) == {p.relative_to(audit).as_posix() for p in audit.rglob('*') if p.is_file() and p != audit / 'seal.json'}
        for name, expected in members.items():
            assert sha(audit / name) == expected
        assert sha(audit / 'source.py') in allowed_sources
        summary = json.loads((audit / 'summary.json').read_bytes())
        assert summary['full_wire_tensors_original_history_EOS_probabilities_verified'] and summary['GUI_terminal_sealed']
        assert summary['run_id'] not in run_ids
        run_ids.add(summary['run_id'])
        discovery = json.loads((audit / 'request-bindings.json').read_bytes())['result']
        assert not (set(checked) & set(discovery['global']))
        checked.update(discovery['global'])
        results = json.loads((audit / 'request-results.json').read_bytes())
        assert len(results['primary']) == summary['primary_replies']
        assert len(results['Flash']) == summary['Flash_replies']
        mains.extend(results['primary']); flashes.extend(results['Flash'])
        bindings.append({'root': str(audit), 'seal_sha256': sha(audit / 'seal.json'),
                         'request_bindings_sha256': sha(audit / 'request-bindings.json'),
                         'raw_tensor_reader_sha256': sha(audit / 'source.py'),
                         'primary': len(results['primary']), 'Flash': len(results['Flash'])})
    assert len(run_ids) == 40
    strict_bind(mains, flashes, checked, admission['global'], admission['primary_names'], admission['Flash_names'])
    mains.sort(key=lambda v: v['root']); flashes.sort(key=lambda v: v['request_id'])
    save(root / 'same-request-raw-proof-reuse.json', {
        'trajectory_audits': bindings, 'exact_request_raw_members_bound': len(checked),
        'fresh_postexit_full_raw_seal_sha256': admission['global_seal_sha256'],
        'all_final_request_member_hashes_exactly_equal_previously_checked_raw_members': True,
        'original_raw_tensor_probability_EOS_history_readers_unchanged': True,
        'different_request_or_input_reuse_forbidden': True, 'new_model_GUI_calls': 0})
    return mains, flashes
