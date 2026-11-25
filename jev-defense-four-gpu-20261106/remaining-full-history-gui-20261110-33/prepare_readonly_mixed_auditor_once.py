"""Reuse strict native/HTTP/cache checks; bind mapping to the new31 zero counters."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'prefill-scheduled-full-history-gui-20261109-32'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    pointer = HERE / 'readonly-mixed-auditor-preparation-created.json'
    assert not pointer.exists()
    names = ['auxiliary_receipt_checks.py', 'mixed_exchange_checks.py', 'primary_receipt_checks.py',
             'mixed_journal_map.py', 'mixed_audit_selection.py', 'mixed_audit_service.py', 'mixed_audit_GUI.py']
    unchanged = {}
    for name in names:
        source = (OLD / name).read_bytes()
        assert not (HERE / name).exists()
        (HERE / name).write_bytes(source)
        unchanged[name] = sha(OLD / name)
    source = (OLD / 'mixed_audit_service.py').read_text(encoding='utf8')
    before = "    mapping = mapper.map_requests(events, read(package / 'plan.json')['queue'],\n                                  read(package / 'carryover/state.json')['initial_transport_counts'])"
    after = """    plan = read(package / 'plan.json')
    predecessor = read(package / 'predecessor.json')
    require(manifest['tracks'] == 31 and manifest['total_original_tracks'] == 32, 'Wrong remaining queue')
    require(sha(package / 'predecessor.json') == manifest['predecessor_sha256'], 'Predecessor authority differs')
    require(sha(package / 'plan.json') == predecessor['unchanged_full_plan_sha256'], 'Original full32 plan differs')
    require(predecessor['excluded_run_ids'] == [plan['queue'][0]['run_id']] == ['fullhistory23-T000-clean-noaux'], 'Only sealed terminal may be excluded')
    require(sha(package / 'predecessor/original-technical-failure.json') == predecessor['original_terminal_sha256'], 'Original terminal bytes differ')
    mapping = mapper.map_requests(events, plan['queue'][1:], {'actor': 0, 'judge': 0, 'evidence': 0})"""
    assert source.count(before) == 1
    adapted = source.replace(before, after)
    assert adapted.replace(after, before) == source
    compile(adapted, 'readonly-source-bound-remaining31-mixed-audit', 'exec')
    (HERE / 'mixed_audit_service.py').write_text(adapted, encoding='utf8')
    pointer_data = json.loads((OLD / 'auxiliary-receipt-audit-preparation-created.json').read_bytes())
    assert not (HERE / 'auxiliary-receipt-audit-preparation-created.json').exists()
    (HERE / 'auxiliary-receipt-audit-preparation-created.json').write_bytes((OLD / 'auxiliary-receipt-audit-preparation-created.json').read_bytes())
    root = HERE / ('readonly-mixed-auditor-preparation-' + str(time.time_ns()))
    root.mkdir()
    receipt = dict(time=time.time(), frozen_old_auditor_source_sha256=unchanged,
        changed_auditor_source_sha256=sha(HERE / 'mixed_audit_service.py'),
        only_change_to_existing_auditor='Frozen original32 tail31 and fresh0/0/0 passed to unchanged mapper; require original plan/predecessor/terminal SHA',
        strict_native_tensors_IDs_generation_tokenizer_UTF8_cache_GPU_and_HTTP_insertion_checks_unchanged=True,
        original_auxiliary_CPU_and_metadata_preparation_reused=pointer_data,
        synthetic_controls_not_repeated=True, runtime_modified=False, new_model_GUI_scorer_calls=0)
    (root / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
    (root / 'preparation-source.py').write_bytes(Path(__file__).read_bytes())
    (root / 'seal.json').write_text(json.dumps({p.name: sha(p) for p in root.iterdir() if p.is_file()}, indent=2), encoding='utf8')
    record = dict(root=str(root), receipt_sha256=sha(root / 'receipt.json'), seal_sha256=sha(root / 'seal.json'))
    pointer.write_text(json.dumps(record, indent=2), encoding='utf8')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
