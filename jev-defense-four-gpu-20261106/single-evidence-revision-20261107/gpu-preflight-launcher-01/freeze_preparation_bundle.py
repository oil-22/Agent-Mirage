"""Seal the local source/CPU/freeze preparation; no remote or model work."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


receipt = {
    'created_utc': datetime.now(timezone.utc).isoformat(), 'status': 'root_reviewed_local_freeze_not_staged_or_submitted',
    'current_source_directory': 'launcher-linked02', 'CPU_resource_boundary_tests': 31,
    'actual_remote_proc_FD_inheritance_gate_exercised': False,
    'resource_gate_SHA256': sha(HERE / 'launcher-linked02/resource_gate.py'),
    'launcher_SHA256': sha(HERE / 'launcher-linked02/launch_once.py'),
    'CPU_receipt_SHA256': sha(HERE / 'CPU-resource-contract-linked02/receipt.json'),
    'GPU_manifest_SHA256': sha(HERE / 'frozen-gpu-four-linked02-01/gpu-manifest.json'),
    'launch_spec_SHA256': sha(HERE / 'frozen-gpu-four-linked02-01/launch-specification.json'),
    'frozen_package_seal_SHA256': sha(HERE / 'frozen-gpu-four-linked02-01/seal.json'),
    'actual_first_attempt_cap': 4, 'automatic_format_retries': 0, 'overall_package_cap': 8,
    'remaining_format_allowance_auto_spend': False,
    'four_GPU_reservation_still_active': True, 'compute_scope_when_launched': [7],
    'model_GUI_health_scorer_network_stage_submit_process_or_lock_mutations_in_this_preparation': 0,
    'old_sources_receipts_and_local_preparation_failure_preserved': True,
    'full_12_control_plan_or_GUI_launch_ready': False,
    'new_real_GPU_model_result_or_Mirage_reduction_claim': False,
}
with (HERE / 'preparation-status.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
files = [{'file': str(p.relative_to(HERE)).replace('\\', '/'), 'sha256': sha(p), 'bytes': p.stat().st_size}
         for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name != 'preparation-seal.json']
with (HERE / 'preparation-seal.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump({'created_utc': datetime.now(timezone.utc).isoformat(), 'files': files}, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'preparation_status_SHA256': sha(HERE / 'preparation-status.json'),
                  'preparation_seal_SHA256': sha(HERE / 'preparation-seal.json'), 'files': len(files)}))
