"""Finish zero-call preparation after inherited config name collision."""
from pathlib import Path
import ast
import json
import shutil
import time
from prepare import HERE,BASE,PARENT,REPAIR,BOUNDED,RUNTIME,sha,save

def main():
    preserve=HERE/'preparation-failure-preservation-01';preserve.mkdir(exist_ok=False)
    for name in ['prepare.py']:
        shutil.copy2(HERE/name,preserve/name)
    shutil.copy2(RUNTIME/'auxiliary-config.json',preserve/'inherited-auxiliary-config.json')
    save(preserve/'receipt.json',{'observed_failure':'FileExistsError saving inherited auxiliary-config.json with exclusive-create',
        'occurred_before_staging_models_or_GUI':True,'model_GUI_calls':0,
        'prepared_source_SHA':{p.relative_to(RUNTIME).as_posix():sha(p)for p in RUNTIME.rglob('*')if p.is_file()},
        'repair':'Keep new main/server sources; update only copied config metadata, then finish remaining preparation',
        'observed_in_exec_command_exit':1})
    # This is an unsealed, unstaged preparation copy; original is sealed above.
    auxiliary={'model':json.loads((RUNTIME/'plan.json').read_bytes())['auxiliary_single_model'],
        'only_current_full_image_and_fixed_prompt':True,'max_calls_per_trajectory':60,'no_retry':True,
        'auxiliary_structural_mask':True,'element_text_refs_always_empty':True}
    (RUNTIME/'auxiliary-config.json').write_text(json.dumps(auxiliary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    schema=RUNTIME/'bounded_schema.py';text=schema.read_text(encoding='utf8')
    old="'text_refs':array(enum(['t1','t2','t3','t4','t5','t6']),6)"
    assert text.count(old)==1
    (preserve/'prior-bounded_schema.py').write_bytes(schema.read_bytes())
    schema.write_text(text.replace(old,"'text_refs':array(enum(['t1','t2','t3','t4','t5','t6']),0)"),encoding='utf8',newline='\n')
    # The preexisting validator and decoded outputs are never changed. Masking
    # narrows this new condition to the originally legal empty association list.
    plan=json.loads((RUNTIME/'plan.json').read_bytes())
    plan['element_text_refs_always_empty']=True
    plan['source_condition_tradeoff']+=' This pilot suppresses all text-to-element associations at generation (text_refs=[]), retaining independently boxed literal text and elements; fewer relations may omit useful evidence. No output rewriting, corrected OCR, truth labels or semantic retry.'
    (RUNTIME/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for p in RUNTIME.rglob('*.py'):ast.parse(p.read_text(encoding='utf8'),filename=str(p))
    for name in ['defense/schema.py','claim_origin.py','defense/qwen_backend.py','evidence_observer.py']:
        assert(REPAIR/'runtime-package/release'/name).read_bytes()==(RUNTIME/'release'/name).read_bytes(),name
    remote=(PARENT/'remote_control.py').read_text(encoding='utf8').replace('full-gui-single-evidence-20261108-01',HERE.name)
    with(HERE/'remote_control.py').open('x',encoding='utf8')as f:f.write(remote)
    staging=(PARENT/'stage_and_launch.py').read_text(encoding='utf8').replace('full-gui-single-evidence-20261108-01',HERE.name)
    staging=staging.replace("    assert not (RUNTIME/'manifest.json').exists()", "    assert not (RUNTIME/'manifest.json').exists()\n    review=BASE/'bounded-evidence-20261109-02/review-completion-01/receipt.json'\n    assert json.loads(review.read_bytes())['followup_GUI_development_with_references_disabled_authorized'] is True\n    assert json.loads((HERE/'no-reference-mask-CPU-result.json').read_bytes())['passed'] is True")
    staging=staging.replace("    raw,target=remote('4090',code,'original-actor-template')\n    v=json.loads(raw);(RUNTIME/'actor-template.json').write_bytes(base64.b64decode(v['actor_template_base64']))\n    assert sha(RUNTIME/'actor-template.json')==v['sha256']", "    assert (RUNTIME/'actor-template.json').read_bytes()==(BASE/'full-gui-single-evidence-20261108-01/runtime-package/actor-template.json').read_bytes()")
    staging=staging.replace("'source_condition_tradeoffs':'One fallible image-only auxiliary; no task/history/candidate to it. Exact latest original main validator. No full long-history fit or semantic efficacy guarantee.'", "'source_condition_tradeoffs':json.loads((RUNTIME/'plan.json').read_bytes())['source_condition_tradeoff'],\n        'source_control_negative_review_sha256':sha(review),\n        'new_mask_CPU_receipt_sha256':sha(HERE/'no-reference-mask-CPU-result.json')")
    staging=staging.replace("'authorization':'User explicitly requested 运行完整的gui实验 on 2026-11-08'", "'authorization':'User sustained goal: 做实验做到防御有效果为止; new finite matched GUI development'" )
    with(HERE/'stage_and_launch.py').open('x',encoding='utf8')as f:f.write(staging)
    inspector=(PARENT/'inspect_gui.py').read_text(encoding='utf8').replace('full-gui-single-evidence-20261108-01',HERE.name)
    with(HERE/'inspect_gui.py').open('x',encoding='utf8')as f:f.write(inspector)
    save(HERE/'preparation.json',{'new_finite_GUI_trajectories':4,'main_generation_calls_source_unchanged':True,
        'full_original_history_images_actions_BF16_and_budgets_retained':True,'completed_old_runs_not_resumed':True,
        'models_GUI_scorer_paid_calls':0,'cannot_stage_until_new_negative_control_review_and_targeted_CPU_check':True,
        'repair_source_receipt_sha256':sha(REPAIR/'review-completion-01/receipt.json'),
        'auxiliary_condition_sha256':sha(BOUNDED/'condition-and-tradeoffs.json'),
        'new_auxiliary_condition':'Structural mask plus no text-element association claims; all text_refs=[]',
        'known_risks':['new condition real generation untested before GUI','literal OCR and boxes can still be wrong','withheld output may reduce assistance','joint long-history capacity unproven']})
    print(json.dumps({'new_GUI_preparation_complete':True,'models_GUI_calls':0,'known_negative_preserved':True}))

if __name__=='__main__':main()
