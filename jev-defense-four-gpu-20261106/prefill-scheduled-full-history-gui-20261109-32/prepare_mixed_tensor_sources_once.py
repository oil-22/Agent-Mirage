"""Derive native buffer-aware expected tensor metadata on meta devices only."""
import json
from pathlib import Path
import time

from orchestrate import HERE, PACKAGE, REMOTE_PACKAGE, OUTPUT, COMMON, remote, save, sha


def main():
    pointer = HERE / 'mixed-tensor-source-preparation-created.json'
    assert not pointer.exists()
    old = HERE.parent / 'unicode-guard-real-preflight-20261109-18/terminal-collection-1794218465768999100'
    old_seal = json.loads((old / 'seal.json').read_bytes())
    old_loaded = old / 'original/worker/loaded.json'
    assert sha(old_loaded) == old_seal['original/worker/loaded.json']
    old_proof = json.loads(old_loaded.read_bytes())
    out = HERE / ('mixed-tensor-source-preparation-' + str(time.time_ns()))
    out.mkdir()
    for name in ['mixed_audit_service.py', 'prepare_mixed_tensor_sources_once.py']:
        (out / name).write_bytes((HERE / name).read_bytes())
    save(out / 'old-native-proof-source.json', dict(path=str(old_loaded), sha256=sha(old_loaded),
         parent_collection_seal_sha256=sha(old / 'seal.json'), auxiliary_CUDA=old_proof['auxiliary_CUDA'],
         same_fixed_model=old_proof['single_auxiliary'], not_new_GPU_inference=True))
    try:
        code = ('ROOT=' + repr(OUTPUT) + '\nPACKAGE=' + repr(REMOTE_PACKAGE)
            + '\nMANIFEST_SHA=' + repr(sha(PACKAGE / 'manifest.json'))
            + '\nHELPER=' + repr((HERE / 'mixed_audit_service.py').read_text(encoding='utf8'))
            + '\nOLD=' + repr(old_proof) + '\n' + COMMON + r'''
import sys
r=Path(ROOT);package=Path(PACKAGE)
assert os.getuid()==1033 and sha(package/'manifest.json')==MANIFEST_SHA
manifest=json.loads((package/'manifest.json').read_bytes())
for name,expected in manifest['files'].items():assert sha(package/name)==expected,name
reference=json.loads((package/'primary-reference.json').read_bytes())
aux=json.loads((package/'auxiliary-identity-reference.json').read_bytes())
assert aux['base_model']==OLD['single_auxiliary']
for item in aux['metadata_files']:assert sha(Path(aux['base_model']['local_path'])/item['filename'])==item['sha256']
device_map=json.loads((r/'worker/new-placement.json').read_bytes())['device_map']
ns={'__name__':'read_only_meta_tensor_source_preparation'}
exec(compile(HELPER,'meta-tensor-expected-sources','exec'),ns)
proofs,sources=ns['expected_tensors'](package,r,reference,Path(aux['base_model']['local_path']),device_map,sha)
assert proofs[0]==OLD['auxiliary_CUDA'],'Native meta proof differs from sealed original actual auxiliary CUDA tensor metadata'
import torch
assert not torch.cuda.is_initialized()
print(json.dumps({'passed':True,'expected_tensor_proofs':proofs,'sources':sources,
 'auxiliary_meta_matches_old_actual_CUDA_proof':True,'primary_meta_matches_current_loaded_CUDA_proof':True,
 'native_float32_nonpersistent_buffers_preserved':True,'CUDA_initialized':False,'model_weights_loaded':False,
 'new_model_GUI_scorer_calls':0,'not_actual_new_auxiliary_GPU_cycle':True},ensure_ascii=False))
''')
        compile(code, 'read-only-native-meta-tensor-sources', 'exec')
        output, operation = remote('3090', code, 'read-only-native-meta-buffer-aware-tensor-sources', timeout=55)
        value = json.loads(output)
        assert value['passed'] and not value['CUDA_initialized'] and not value['model_weights_loaded']
        save(out / 'source-bound-result.json', value)
        save(out / 'receipt.json', dict(time=time.time(), passed=True, remote_operation=str(operation),
             original_wrapper_copy_preserved_in_prior_sealed_controls=True,
             primary_state_dict_alone_does_not_cover_3_native_nonpersistent_buffers=True,
             native_float32_buffer_elements_per_model=82, current32_runtime_modified=False,
             actual_enabled_mixed_branch_audited=False, new_model_GUI_scorer_calls=0,
             semantic_correctness_or_defense_efficacy_established=False))
        save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
        result = dict(root=str(out), receipt_sha256=sha(out / 'receipt.json'), seal_sha256=sha(out / 'seal.json'))
        save(pointer, result)
        print(json.dumps(dict(result, passed=True, native_buffers_preserved=True, new_model_GUI_calls=0)))
    except BaseException as error:
        save(out / 'failure.json', dict(time=time.time(), error_type=type(error).__name__, error=str(error),
             runtime_modified=False, new_model_GUI_calls=0))
        save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
        raise


if __name__ == '__main__':
    main()
