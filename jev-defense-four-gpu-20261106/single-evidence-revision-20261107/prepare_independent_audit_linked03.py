"""Repair only the local audit journal reader; preserve its failed source."""
import hashlib
from pathlib import Path

root = Path(__file__).resolve().parent
source = root / 'audit_compact_four_independent_technical02.py'
target = root / 'audit_compact_four_independent_technical_linked03.py'
text = source.read_text(encoding='utf-8')
assert hashlib.sha256(source.read_bytes()).hexdigest() == '115e16772703508e83b54209f481fce9c327278c273caae1b9b70f7555a4f609'
text = text.replace("OUT = HERE / 'compact-four-independent-technical-audit-02'", "OUT = HERE / 'compact-four-independent-technical-audit-linked03'")
text = text.replace("assert event['seq'] == len(events) and event['previous'] == head", "assert event.get('seq', event.get('index')) == len(events) and event.get('previous', event.get('previous_sha256')) == head")
text = text.replace("assert current['current_weight_identity_reuse'] == reused", "assert current['current_weight_identity_reuse'] == reused\n    assert proof['official_LFS_current_shard_identity_verified'] is True and current['official_LFS_current_shard_identity_verified'] is True")
text = text.replace("assert worker_identity['uid'] == 1033", "assert worker_identity['uid'] == 1033 and worker_identity['ppid'] == exited['launcher_identity']['pid']\n    claim = read(ORIGINAL / 'worker/claim.json')\n    assert claim['manifest_sha256'] == sha(ORIGINAL / 'frozen-manifest.json')\n    assert claim['worker_sha256'] == sha(ORIGINAL / 'source-snapshot/native_image_gpu_preflight.py')")
text = text.replace("assert data['actual_holder']['uid'] == 1033 and str(data['actual_holder']['start_ticks']) == '1159211789'", "assert data['actual_holder']['uid'] == 1033 and str(data['actual_holder']['start_ticks']) == '1159211789'\n        for identity in data['actual_allowed_identities'].values():\n            role = 'launcher_identity' if identity['pid'] == exited['launcher_identity']['pid'] else 'worker_identity'\n            assert identical_identity(identity, exited[role])")
text = text.replace("'root_technical_audit_receipt_or_conclusions_read': False,", "'linked_prior_local_audit_failure': {'root': str(HERE / 'compact-four-independent-technical-audit-02'), 'reason': 'launcher uses index/previous_sha256; worker uses seq/previous; journal parser field dispatch only', 'original_experiment_failure': False},\n        'root_technical_audit_receipt_or_conclusions_read': False,")
with target.open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(text)
print({'linked_audit_source_sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
