"""Linked local reporter repair: do not invent absent historical seal coverage."""
import json
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
prior = HERE / 'finalize_local_snapshot.py'
source = prior.read_text(encoding='utf-8')
failure = {
    'type': 'preserved_local_reporter_metadata_assumption_failure',
    'original_source': str(prior), 'original_source_sha256': hashlib.sha256(prior.read_bytes()).hexdigest(),
    'actual_failure': 'AssertionError: Historical artifact manifest must contain receipt model-sha256-3090.json',
    'remote_snapshots_completed_and_not_repeated': True,
    'model_GUI_health_remote_write_process_or_lock_mutations': 0,
    'repair': 'Record absent old manifest entries as false; retain cross-receipt checks and current captures.',
}
with (HERE / 'finalizer-failure-01.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(failure, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
replacements = [
    ("    assert expected is not None, 'Historical artifact manifest must contain receipt ' + name\n    assert expected['sha256'] == sha(p) and expected['bytes'] == p.stat().st_size\n",
     "    if expected is not None:\n        assert expected['sha256'] == sha(p) and expected['bytes'] == p.stat().st_size\n"),
    ("'old_artifact_manifest_hash_and_size_match': True", "'old_artifact_manifest_hash_and_size_match': expected is not None"),
    ("'historical_receipts': old_bindings,", "'historical_receipts': old_bindings,\n    'old_receipts_historical_seal_coverage_verified': False,\n    'old_receipt_cross_host_and_transfer_content_match_verified': True,"),
    ("旧三份回执均命中旧artifact-manifest原SHA。", "旧三份回执内容按双机与transfer逐项相互核验一致；旧artifact-manifest未收录这三份回执，历史seal覆盖未证实，本包只固定当前读到的旧回执SHA。"),
    ("'4090-readonly.json', '3090-invocation.json', '4090-invocation.json', 'report.json', 'README.md']",
     "'4090-readonly.json', '3090-invocation.json', '4090-invocation.json', 'report.json', 'README.md', 'finalize_local_snapshot_linked02.py', 'finalizer-failure-01.json']"),
    ("'old_receipts_verified_against_old_manifest': len(old_bindings)", "'old_receipts_crosschecked': len(old_bindings), 'old_receipts_verified_against_old_manifest': 0"),
]
for old, new in replacements:
    assert source.count(old) == 1, 'Repair applies only to expected reporter metadata text'
    source = source.replace(old, new)
exec(compile(source, str(prior), 'exec'), globals())
