"""Freeze a six-call independent native generation check of the length guard."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
OLD=BASE/'balanced-visual-evidence-20261109-16/runtime-package'
PACKAGE=HERE/'runtime-package'
GUARD=BASE/'unicode-length-guard-20261109-17'
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path,value):
    with path.open('x',encoding='utf8')as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')


def main():
    source=HERE/'sources'
    for name,expected in json.loads((source/'seal.json').read_bytes()).items():assert sha(source/name)==expected,name
    cpu=GUARD/'native-CPU-inspection-1794217355774954300/original/attempt-02/receipt.json'
    cpu_result=json.loads(cpu.read_bytes());assert cpu_result['passed']and cpu_result['native_case_count']==9
    assert cpu_result['source_sha256']==sha(GUARD/'unicode_length_guard.py')
    assert not PACKAGE.exists();PACKAGE.mkdir()
    parent=json.loads((OLD/'manifest.json').read_bytes())
    for name,expected in parent['files'].items():
        assert sha(OLD/name)==expected,name
        if name.startswith('inputs/')or name in ['controls-plan.json','worker.py','launch_balanced_once.py']:continue
        target=PACKAGE/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OLD/name,target)
    shutil.copyfile(GUARD/'unicode_length_guard.py',PACKAGE/'unicode_length_guard.py')
    decoder=(OLD/'bounded_auxiliary.py').read_text(encoding='utf8')
    old='    prefix=new_prefix_filter(data);checks=[]\n'
    new='    from unicode_length_guard import UnicodeLengthPrefixFilter\n    prefix=UnicodeLengthPrefixFilter(data,new_prefix_filter(data),SCHEMA);checks=[]\n'
    assert decoder.count(old)==1;decoder=decoder.replace(old,new)
    needle="        save(target/'actual-mask-steps.json',"
    assert decoder.count(needle)==1
    decoder=decoder.replace(needle,"        save(target/'unicode-length-guard.json',{'source_sha256':sha(Path(__file__).parent/'unicode_length_guard.py'),'subset_only':True,'calls':prefix.calls,'filtered_choices_sum':prefix.filtered,'final_decoded_length_state_complete_before_EOS':prefix.state.complete(),'strict_final_validator_unchanged':True,'native_selected_tokens_not_rewritten':True})\n"+needle)
    (PACKAGE/'bounded_auxiliary.py').write_text(decoder,encoding='utf8',newline='\n')
    # The native model.generate call and stateless lifecycle function are unchanged.
    calls=lambda text:[ast.dump(node,include_attributes=False)for node in ast.walk(ast.parse(text))if isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)and node.func.attr in ['generate','apply_chat_template']]
    assert calls(decoder)==calls((OLD/'bounded_auxiliary.py').read_text(encoding='utf8'))
    module=importlib.util.spec_from_file_location('new18_image_contract',PACKAGE/'release/image_evidence.py')
    contract=importlib.util.module_from_spec(module);module.loader.exec_module(contract)
    inputs=PACKAGE/'inputs';inputs.mkdir();rows=[]
    for row in json.loads((source/'provenance.json').read_bytes())['complete_screenshots']:
        raw=(source/'public'/row['file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256']
        request=contract.build_image_only_request(raw,'Qwen/Qwen3.5-9B','c202236235762e1c871ad0ccb60c8ee5ba337b9a')
        target=inputs/(row['id']+'.json');save(target,request)
        rows.append({'id':row['id'],'path':'inputs/'+target.name,'sha256':sha(target),'image_sha256':row['sha256']})
    limits={'auxiliary':6,'actor':0,'judge':0,'format_retries_per_judge_control':0,
            'GUI':0,'scorer':0,'paid_API':0,'auxiliary_retries':0,'actor_retries':0}
    save(PACKAGE/'controls-plan.json',{'schema':'unicode-guard-native-real-six-new-inputs-v1','auxiliary':rows,'actors':[],'judges':[],
         'limits':limits,'same_fixed_generic_prompt_as16':True,'private_geometry_in_model_package':False,
         'complete_new_offline_fixtures_not_benchmark_trajectories':True,'no_completed_source_control_rerun':True,
         'condition_change':'Subset-only Unicode decoded-character filter around original auxiliary byte grammar; same final validator, model, complete image, fixed prompt, original2048cap and stateless call.',
         'tradeoff':'Mask narrows choices to original character limits and adds CPU decoding overhead. It does not certify reading correctness, page counts, focus or history. All four GPUs remain reserved and counted while the unchanged joint load is present.',
         'new_primary_or_GUI_or_scorer_calls':0,'no_automatic_retry_or_cap_expansion':True})
    worker=(OLD/'worker.py').read_text(encoding='utf8')
    start=worker.index('LIMITS = ');end=worker.index('\n\n\n',start)
    worker=worker[:start]+'LIMITS = '+repr(limits)+worker[end:]
    worker=worker.replace("len(plan['auxiliary'])==7 and len(plan['actors'])==4 and len(plan['judges'])==11","len(plan['auxiliary'])==6 and len(plan['actors'])==0 and len(plan['judges'])==0")
    begin=worker.index("        template=json.loads((package/'actor-template.json').read_bytes())")
    finish=worker.index("        status('completed')",begin)
    worker=worker[:begin]+worker[finish:]
    (PACKAGE/'worker.py').write_text(worker,encoding='utf8',newline='\n')
    launcher=(OLD/'launch_balanced_once.py').read_text(encoding='utf8').replace('balanced-visual-evidence-20261109-16',HERE.name)
    (PACKAGE/'launch_balanced_once.py').write_text(launcher,encoding='utf8',newline='\n')
    unchanged=['model_runtime.py','stateless_boundary.py','release/image_evidence.py','release/defense/core.py',
               'release/defense/qwen_backend.py','bounded_schema.py','native_format_bridge.py','resource_gate.py']
    for name in unchanged:assert sha(PACKAGE/name)==parent['files'][name],name
    save(HERE/'PRIVATE-source-first-review.json',{'time':time.time(),'all_six_complete_images_actually_viewed_before_outputs':True,
        'reviewer':'root; source author also reviewer, not blind/independent human','never_in_model_package':True,
        'expectations':['T01 visibly blue box drawing, two controls; no identity or photo inference.',
                        'T02 literal41-50 of95,10per page and selected5; shortcuts3..7 do not mean total7.',
                        'T03 visiblecopper in input and current-filter line; no OS focus or past execution proof.',
                        'T04 visible modal covers part of underlying Compact view; do not fill hidden control.',
                        'T05 Chinese project notes state current铜制台灯 and数量12, plusdraft; not executed task completion.',
                        'T06 three rows, twoReady and oneNeeds review; no selected row styling or import success proof.']})
    manifest={key:value for key,value in parent.items()if key!='files'}
    manifest.update(schema='unicode-length-guard-six-call-native-preflight-v1',output='/home/researcher/jev-defense-four-gpu-20261106/'+HERE.name,
        limits=limits,parent_balanced16_manifest_sha256=sha(OLD/'manifest.json'),
        source_provenance_sha256=sha(source/'provenance.json'),private_source_review_sha256=sha(HERE/'PRIVATE-source-first-review.json'),
        unicode_guard_source_sha256=sha(PACKAGE/'unicode_length_guard.py'),native_CPU9_receipt_sha256=sha(cpu),
        unicode_native_CPU_evidence_only_no_GPU_repair_claim_before_run=True,
        unchanged_runtime_files={name:sha(PACKAGE/name)for name in unchanged},
        no_primary_model_or_GUI_calls_in_this_six_call_preflight=True,
        files={p.relative_to(PACKAGE).as_posix():sha(p)for p in sorted(PACKAGE.rglob('*'))if p.is_file()})
    for path in PACKAGE.rglob('*.py'):compile(path.read_text(encoding='utf8'),str(path),'exec')
    save(PACKAGE/'manifest.json',manifest)
    save(HERE/'preparation.json',{'time':time.time(),'manifest_sha256':sha(PACKAGE/'manifest.json'),'source_files':len(manifest['files']),
         'new_model_GPU_GUI_calls':0,'limits':limits,'GPU_launch_requires_fresh_nine_locks_empty_4_to_7_and_native_CPU_input_admission':True})
    print(json.dumps({'package':str(PACKAGE),'manifest_sha256':sha(PACKAGE/'manifest.json'),'limits':limits,'source_files':len(manifest['files'])}))


if __name__=='__main__':main()
