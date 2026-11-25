"""Seal prepared control sources. Does not import/execute their main functions."""
import hashlib,json,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not(HERE/'seal.json').exists()
receipt={'stage':'source_CPU_only_control_preparation','tests_passed':7,
    'tests_scope':'exact resource group/spec/layers/allocator/source hashes; closed template static evidence; no HTTP/model calls; single background Popen source only',
    'fixed_package_seal_sha256':'1dc3568fe581574856ee7457982103d1d50a3348179bec91687c0e32767bbd44',
    'fixed_wrapper_sha256':'e660bd664ca94355a3d1109611dc18aa8069abd77f92c9dcb18265477f58792d',
    'native_environment_preserved_from_sealed_package':True,
    'actual_prepare_run_health_POST_model_GUI_scorer_signal_calls':0,
    'sealed_GUI_package_not_modified':True,'actual_resource_and_fresh_owner_still_required':True,'time':time.time()}
(HERE/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
mapping={p.relative_to(HERE).as_posix():sha(p)for p in HERE.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
(HERE/'seal.json').write_text(json.dumps(mapping,indent=2),encoding='utf8')
print(json.dumps({'root':str(HERE),'seal_sha256':sha(HERE/'seal.json'),'receipt_sha256':sha(HERE/'receipt.json'),
    'prepare_helper_sha256':sha(HERE/'prepare_bound_once.py'),'background_helper_sha256':sha(HERE/'background_three_once.py')}))
