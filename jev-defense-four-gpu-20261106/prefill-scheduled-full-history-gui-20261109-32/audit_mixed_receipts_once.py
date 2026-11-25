"""Read-only native + HTTP + GPU cycle + frozen observer/actor audit.

An enabled actor automatically includes its immediately preceding original
auxiliary request. An auxiliary selection requires its following sealed actor.
Pending/failed inference is never rerun or classified as a semantic zero here.
"""
import argparse
import json
from pathlib import Path
import re
import time

from orchestrate import HERE, PACKAGE, OUTPUT, GUIROOT, REMOTE_PACKAGE, COMMON, remote, save, sha
from publish_source_progress22_once import verify_folder


def main(evidence, requested):
    assert evidence.parent == HERE and evidence.name.startswith('actual-evidence-')
    assert requested and len(requested) == len(set(requested))
    assert all(re.fullmatch(r'\d{4,}', ident) for ident in requested)
    verify_folder(evidence)
    inspected = json.loads((evidence / '3090.json').read_bytes())
    indexed = {row['request']: row for row in inspected['sealed_requests']}
    assert set(requested) <= set(indexed), 'Only inspected sealed original replies may be selected'
    expected = {ident: indexed[ident]['seal_sha256'] for ident in requested}
    manifest_sha = sha(PACKAGE / 'manifest.json')
    manifest = json.loads((PACKAGE / 'manifest.json').read_bytes())
    for name, value in manifest['files'].items():
        assert sha(PACKAGE / name) == value, name
    aux_p = json.loads((HERE / 'auxiliary-receipt-audit-preparation-created.json').read_bytes())
    aux_root = Path(aux_p['root'])
    verify_folder(aux_root, aux_p['seal_sha256'])
    assert sha(aux_root / 'receipt.json') == aux_p['receipt_sha256']
    expected_generation = json.loads((aux_root / 'expected-generation.json').read_bytes())
    names = ['auxiliary_receipt_checks.py', 'mixed_exchange_checks.py', 'primary_receipt_checks.py',
             'mixed_journal_map.py', 'mixed_audit_selection.py', 'mixed_audit_service.py', 'mixed_audit_GUI.py']
    sources = {name: (HERE / name).read_text(encoding='utf8') for name in names}
    for name, source in sources.items():
        compile(source, name, 'exec')
    stamp = str(time.time_ns())
    out = HERE / ('mixed-receipt-audit-' + stamp)
    out.mkdir()
    for name in names + [Path(__file__).name]:
        (out / name).write_bytes((HERE / name).read_bytes())
    save(out / 'intent.json', dict(time=time.time(), selected_original_requests=requested,
        original_inspection=str(evidence), original_inspection_seal_sha256=sha(evidence / 'seal.json'),
        runtime_manifest_sha256=manifest_sha, new_model_GUI_scorer_calls=0, runtime_modified=False))
    try:
        code = ('ROOT=' + repr(OUTPUT) + '\nPACKAGE=' + repr(REMOTE_PACKAGE) + '\nMANIFEST_SHA=' + repr(manifest_sha)
            + '\nEXPECTED=' + repr(expected) + '\nSOURCES=' + repr(sources)
            + '\nAUX_EXPECTATION=' + repr(expected_generation) + '\n' + COMMON
            + '\nns={"__name__":"read_only_service_mixed_receipts"}\n'
            + 'exec(compile(SOURCES["mixed_audit_service.py"],"mixed-audit-service","exec"),ns)\n'
            + 'print(json.dumps(ns["collect"](ROOT,PACKAGE,MANIFEST_SHA,EXPECTED,SOURCES,AUX_EXPECTATION),ensure_ascii=False))\n')
        compile(code, 'service-read-only-mixed-receipts', 'exec')
        output, operation3090 = remote('3090', code, 'read-only-complete-mixed-native-receipts-' + '-'.join(requested), timeout=55)
        service = json.loads(output)
        save(out / '3090-native-bindings.json', service)
        assert service['passed'] and not service['CUDA_initialized'] and not service['model_weights_loaded']
        for ident, binding in service['bindings'].items():
            assert ident in indexed and binding['request_seal_sha256'] == indexed[ident]['seal_sha256']
        code = ('ROOT=' + repr(GUIROOT) + '\nMANIFEST_SHA=' + repr(manifest_sha)
            + '\nSERVICE=' + repr(service) + '\nSOURCES=' + repr(sources) + '\n' + COMMON
            + '\nns={"__name__":"read_only_GUI_mixed_receipts"}\n'
            + 'exec(compile(SOURCES["mixed_audit_GUI.py"],"mixed-audit-GUI","exec"),ns)\n'
            + 'print(json.dumps(ns["collect"](ROOT,MANIFEST_SHA,SERVICE,SOURCES),ensure_ascii=False))\n')
        compile(code, 'GUI-read-only-mixed-receipts', 'exec')
        output, operation4090 = remote('4090', code, 'read-only-complete-mixed-HTTP-insertion-' + '-'.join(requested), timeout=55)
        gui = json.loads(output)
        save(out / '4090-GUI-bindings.json', gui)
        assert gui['passed']
        enabled = any(row['operation'] == 'evidence' for row in service['reports'])
        assert not enabled or any(row['preceding_auxiliary_request'] for row in gui['actor_insertions'])
        result = dict(time=time.time(), passed=True, requested=requested,
            actual_original_requests_read_not_generated=list(service['bindings']),
            enabled_auxiliary_native_HTTP_GPU_cache_and_actor_insertion_audited=enabled,
            primary_native_IDs_generation_and_mapped_prefill_bound=True,
            actual_enabled_mixed_branch_observed=enabled,
            current_GPU_tensor_values_independently_hashed=False,
            structural_mask_choices_independently_recomputed=False,
            independent_image_semantics_or_whole_trajectory_Mirage_labels_added=False,
            semantic_correctness_or_defense_efficacy_established=False,
            native_calls_added_to_experiment_count=0, new_model_GUI_scorer_paid_calls=0,
            runtime_modified=False, operations={'3090': str(operation3090), '4090': str(operation4090)})
        save(out / 'receipt.json', result)
        save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
        pointer = dict(root=str(out), receipt_sha256=sha(out / 'receipt.json'), seal_sha256=sha(out / 'seal.json'))
        save(HERE / ('mixed-receipt-audit-created-' + stamp + '.json'), pointer)
        print(json.dumps(dict(pointer, passed=True, selected=list(service['bindings']),
            actual_enabled_branch_audited=enabled, new_model_GUI_calls=0), ensure_ascii=False))
    except BaseException as error:
        save(out / 'failure.json', dict(time=time.time(), error_type=type(error).__name__, error=str(error),
             runtime_modified=False, no_inference_or_GUI_retry_performed=True))
        save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--request', action='append', required=True)
    args = parser.parse_args()
    main(args.evidence.resolve(), args.request)
