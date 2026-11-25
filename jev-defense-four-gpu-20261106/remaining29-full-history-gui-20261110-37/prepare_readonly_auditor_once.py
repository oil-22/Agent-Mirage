"""Bind existing strict receipt checks to the exact new remaining29 queue."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import time


HERE = Path(__file__).resolve().parent
N = HERE.parent / 'remaining-full-history-gui-20261110-33'
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    assert not (HERE / 'readonly-auditor-preparation-created.json').exists()
    names = ['auxiliary_receipt_checks.py', 'mixed_exchange_checks.py', 'primary_receipt_checks.py',
             'mixed_journal_map.py', 'mixed_audit_selection.py', 'mixed_audit_service.py', 'mixed_audit_GUI.py',
             'audit_mixed_receipts_once.py', 'collect_source_first_packets.py', 'seal_source_review.py',
             'join_source_reviews.py', 'read_source_packet.py', 'source_review_console_safe.py',
             'auxiliary-receipt-audit-preparation-created.json']
    copied = {}
    for name in names:
        assert not (HERE / name).exists()
        shutil.copyfile(N / name, HERE / name)
        copied[name] = sha(N / name)
    path = HERE / 'mixed_audit_service.py'
    source = path.read_text(encoding='utf-8')
    start = source.index("    plan = read(package / 'plan.json')\n")
    stop = source.index('    selected = selector.select_completed_requests', start)
    old = source[start:stop]
    assert "manifest['tracks'] == 31" in old and "plan['queue'][1:]" in old
    new = '''    plan = read(package / 'plan.json')
    continuation = read(package / 'continuation.json')
    require(manifest['tracks'] == 29 and manifest['total_original_tracks'] == 32, 'Wrong remaining queue')
    require(sha(package / 'continuation.json') == manifest['continuation_sha256'], 'Continuation source differs')
    require(sha(package / 'plan.json') == continuation['unchanged_full32_plan_sha256'], 'Original full32 plan differs')
    require(continuation['excluded_run_ids'] == [row['run_id'] for row in plan['queue'][:3]] ==
            ['fullhistory23-T000-clean-noaux', 'fullhistory23-T000-clean-aux', 'fullhistory23-T000-stale_replace-aux'], 'Three immutable terminal exclusions differ')
    for row in continuation['terminal_copies']:
        require(sha(package / row['copy']) == row['sha256'], 'Original terminal bytes differ')
    queue = [row for row in plan['queue'] if row['run_id'] not in continuation['excluded_run_ids']]
    require([row['run_id'] for row in queue] == continuation['remaining_run_ids'] and len(queue) == 29, 'Original remaining order differs')
    require(sha(package / 'completed-request-exclusions.json') == continuation['completed_request_exclusions_sha256'], 'Completed request exclusions differ')
    require(manifest['source_condition_choice'] == 'adopt_exact_decoded_native_STOP_answer_source' and manifest['source_condition_decision_received'] is True, 'Actual human source choice differs')
    require(sha(package / 'human-source-condition-decision.json') == manifest['human_decision_receipt_sha256'], 'Human choice receipt differs')
    mapping = mapper.map_requests(events, queue, {'actor': 0, 'judge': 0, 'evidence': 0})
'''
    updated = source[:start] + new + source[stop:]
    assert updated.replace(new, old, 1) == source
    compile(updated, str(path), 'exec')
    path.write_text(updated, encoding='utf-8', newline='\n')
    root = HERE / ('readonly-auditor-preparation-' + str(time.time_ns()))
    root.mkdir()
    shutil.copyfile(__file__, root / 'prepare_readonly_auditor_once.py')
    (root / 'old-queue-binding.txt').write_text(old, encoding='utf-8')
    (root / 'new-queue-binding.txt').write_text(new, encoding='utf-8')
    for name in names:
        shutil.copyfile(HERE / name, root / name)
        if name != 'mixed_audit_service.py':
            assert sha(HERE / name) == copied[name]
    receipt = {'time': time.time(), 'source_auditors': copied,
               'only_auditor_change': 'Original32 minus three immutable terminals,exact29 zero counters and362 request exclusions/human source-decision receipt; all actual native/HTTP/KV/ID/tensor/EOS checks unchanged',
               'runtime_changed': False, 'model_or_synthetic_controls_rerun': False,
               'new_model_GPU_GUI_scorer_paid_calls': 0}
    with (root / 'receipt.json').open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2); stream.write('\n')
    with (root / 'seal.json').open('x', encoding='utf-8') as stream:
        json.dump({p.name: sha(p) for p in root.iterdir() if p.is_file()}, stream, indent=2); stream.write('\n')
    pointer = {'root': str(root), 'receipt_sha256': sha(root / 'receipt.json'), 'seal_sha256': sha(root / 'seal.json')}
    with (HERE / 'readonly-auditor-preparation-created.json').open('x', encoding='utf-8') as stream:
        json.dump(pointer, stream, indent=2); stream.write('\n')
    print(json.dumps(pointer, ensure_ascii=True))


if __name__ == '__main__':
    main()
