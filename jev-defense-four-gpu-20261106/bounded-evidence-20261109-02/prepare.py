from pathlib import Path
import ast
import hashlib
import json
import shutil
import zipfile
from ops import HERE,BASE,sha,save

def main():
    prior=BASE/'repair-evidence-20261109-01';package=HERE/'runtime-package'
    assert sha(prior/'review-completion-01/receipt.json')
    assert not package.exists();shutil.copytree(prior/'runtime-package',package,ignore=shutil.ignore_patterns('control-inputs','controls-plan.json','manifest.json','private.token','__pycache__','*.pyc'))
    vendor=package/'grammar-vendor';vendor.mkdir()
    wheels=HERE/'grammar-dependencies-01/wheels'
    for wheel in sorted(wheels.glob('*.whl')):
        with zipfile.ZipFile(wheel)as z:
            for n in z.namelist():assert(vendor/n).resolve().is_relative_to(vendor.resolve())
            z.extractall(vendor)
    for name in ['bounded_schema.py','intrinsic_count_guard.py']:
        shutil.copy2(HERE/name,package/name)
    # Supplemental guard goes next to the unchanged validator. It withholds the
    # entire packet, never clips the output or changes a numerical claim.
    shutil.copy2(HERE/'intrinsic_count_guard.py',package/'release/intrinsic_count_guard.py')
    p=package/'release/image_evidence.py';text=p.read_text(encoding='utf8')
    text=text.replace('single-image-neutral-evidence-v4-compact-quote-development','single-image-neutral-evidence-v5-schema-constrained-development')
    text += '''\n\n_unmodified_packet_with_transport=actor_packet
def actor_packet(request,raw_output,natural_eos):
    result=_unmodified_packet_with_transport(request,raw_output,natural_eos)
    from intrinsic_count_guard import check_intrinsic_counts
    check=check_intrinsic_counts(result['reading'])
    if check['reject']:
        raise EvidenceContractError('Internally inconsistent literal range; entire raw packet withheld, no corrected digits')
    result['intrinsic_count_check']=check
    return result
'''
    p.write_text(text,encoding='utf8',newline='\n')
    for p in package.rglob('*.py'):ast.parse(p.read_text(encoding='utf8'))
    save(HERE/'condition-and-tradeoffs.json',{'authorization':'User sustained goal and prior authorization to make improvements to image-only assistance',
        'parent_terminal_receipt_sha256':sha(prior/'review-completion-01/receipt.json'),
        'new_condition':'Auxiliary only: native generate with prefix_allowed_tokens_fn, structural JSON-schema mask; main decoding unchanged',
        'fixed_prompt_text_unchanged_from_repair01':True,'strict_original_evidence_validator_unchanged':True,
        'native_main_validator_origin_backend_and_controller_unchanged_from_repair01':True,
        'auxiliary_raw_logits_changed_by_structural_mask':True,'output_tokens_remain_2048':True,
        'no_truth_labels_or_task_context_to_schema':True,'no_candidate_or_GUI_advice_from_mask':True,
        'tradeoffs':['May change which fact is emitted, including introducing errors; no bitwise invariance claim',
                     'Constrained valid JSON does not establish accurate OCR, boxes, semantic truth or Mirage reduction',
                     'Schema does not replace original cross-reference/box/order validators',
                     'Impossible start/end/total ranges with explicit listing units cause complete withholding, never correction',
                     'Withholding can reduce auxiliary availability; normal-operation outcomes must be measured'],
        'dependencies_isolated_in_task_directory':True,'shared_Python_environment_modified':False,
        'libraries_wheel_sha256':{p.name:sha(p)for p in wheels.glob('*.whl')},
        'completed_A01_A06_R01_R08_not_requeued':True,'models_GUI_calls':0})
    print(json.dumps({'new_sources':str(package),'libraries_isolated':True,'model_calls':0}))

if __name__=='__main__':main()
