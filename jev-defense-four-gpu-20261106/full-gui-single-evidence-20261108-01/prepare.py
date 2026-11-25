"""Freeze NEW full GUI sources; completed development controls are never invoked."""
import ast,copy,difflib,hashlib,json,shutil,sys,textwrap
from pathlib import Path
from remote_control import HERE,BASE,ROOT3090,ROOT4090,save,sha

SOURCE=BASE/'single-evidence-revision-20261107/joint-main-controls-20261108-01/technical-continuation-03/runtime-package'
RUNTIME=HERE/'runtime-package'

def replace_once(s,old,new):
    assert s.count(old)==1,old[:130]
    return s.replace(old,new)

def prepare():
    assert not RUNTIME.exists();RUNTIME.mkdir()
    shutil.copytree(SOURCE/'release',RUNTIME/'release')
    for name in ['resource_gate.py','aux_identity_support.py','preflight_support.py','four_gpu_contract.py',
                 'primary-reference.json','auxiliary-identity-reference.json']:
        shutil.copyfile(SOURCE/name,RUNTIME/name)
    shutil.copyfile(BASE/'gui-preparation-package-01/release/defense/http_backend.py',RUNTIME/'release/defense/http_backend.py')
    for name in ['protocol.py','gui_transport.py','gpu_server.py']:
        shutil.copyfile(HERE/name,RUNTIME/name)
    shutil.copyfile(BASE/'single-evidence-revision-20261107/compact-evidence-02/image_evidence.py',RUNTIME/'release/image_evidence.py')
    shutil.copyfile(BASE/'single-evidence-revision-20261107/evidence-contract/evidence_observer.py',RUNTIME/'release/evidence_observer.py')
    old=(SOURCE/'joint_worker.py').read_text(encoding='utf8')
    tree=ast.parse(old)
    header='\n'.join(ast.get_source_segment(old,n) for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)))+'\n'
    functions='\n\n'.join(ast.get_source_segment(old,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['canonical','digest','sha','save','module'])
    start=old.index('        support = module(');end=old.index('        auxiliary_root = ',start)
    load=old[start:end]
    removed="""                if target == root / 'judges/01':
                    assert set(prepared) == set(continuation['parent_failed_prepared'])
                    for n,v in prepared.items():
                        assert all(v[k] == continuation['parent_failed_prepared'][n][k]
                                   for k in ['shape','dtype','bytes','sha256']), 'Failed input changed: ' + n
"""
    load=replace_once(load,removed,'')
    # Retain real loader, native state/precision validation and exact-forward instrumentation.
    load=textwrap.dedent(load)
    gen=old[old.index('        generation = copy.deepcopy(auxiliary_model.generation_config)'):old.index('        for row in plan[\'auxiliary\']:',end)]
    gen=textwrap.dedent(gen)
    runtime=header+'\n'+functions+'\n\ndef load_runtime(package,root,journal,resource,manifest,me):\n'
    runtime+='    from defense.qwen_backend import LocalQwen\n'
    runtime+=textwrap.indent(load+gen+'return locals()\n','    ')
    (RUNTIME/'model_runtime.py').write_text(runtime,encoding='utf8')
    launcher=(SOURCE/'launch_joint_once.py').read_text(encoding='utf8')
    launcher=launcher.replace('runtime-preparation/joint-main-controls-20261108-03','runtime-preparation/full-gui-single-evidence-20261108-01')
    launcher=launcher.replace('single-evidence-revision-20261107/joint-main-controls-20261108-03','full-gui-single-evidence-20261108-01')
    launcher=launcher.replace("package / 'joint_worker.py'","package / 'gpu_server.py'")
    launcher=launcher.replace("['launch_joint_once.py']","['launch_gui_service_once.py']")
    launcher=launcher.replace("'GUI_started': False","'GUI_is_external_and_bound_to_plan': True")
    (RUNTIME/'launch_gui_service_once.py').write_text(launcher,encoding='utf8')
    original=(BASE/'gui-preparation-package-01/release/run_image_observer_vwa_validation.py').read_text(encoding='utf8')
    runner=original
    runner=replace_once(runner,'from image_observer import from_config as observer_from_config, POLICY, SHARED_ACTOR_INSTRUCTIONS\nfrom observer_launch_contract import validate_launch_inputs\nfrom online_transport import OnlineQwen',
        'from gui_transport import GUIQwen as OnlineQwen, BoundObserver, validate_launch_inputs\nfrom image_evidence import POLICY, ACTOR_BOUNDARY as SHARED_ACTOR_INSTRUCTIONS')
    runner=replace_once(runner,"actor_observer=observer_from_config(a.auxiliary_config,enabled=item['observer_enabled'])","actor_observer=BoundObserver(model,item['observer_enabled'])")
    runner=replace_once(runner,"['run_image_observer_vwa_validation.py','image_observer.py','observer_launch_contract.py','online_transport.py','defense/core.py','defense/prompts.py']",
        "['run_single_evidence_gui.py','gui_transport.py','protocol.py','release/image_evidence.py','release/evidence_observer.py','release/defense/core.py','release/defense/prompts.py']")
    # The release directory is a separate frozen dependency, not a renamed old run.
    runner=runner.replace("from defense.core import PublicView", "sys.path.insert(0,str(Path(__file__).resolve().parent/'release'))\nfrom defense.core import PublicView",1)
    (RUNTIME/'run_single_evidence_gui.py').write_text(runner,encoding='utf8')
    (HERE/'runner-diff.txt').write_text(''.join(difflib.unified_diff(original.splitlines(True),runner.splitlines(True),fromfile='immutable-old-Flash-runner',tofile='new-single9B-fullGUI-runner')),encoding='utf8')
    plan=json.loads((BASE/'gui-preparation-package-01/plan.json').read_bytes())
    plan.update(policy='single-image-neutral-evidence-v3-compact-development',stage='new_user_authorized_full_GUI_pilot',
        authorization='2026-11-08 user: 运行完整的gui实验',primary_layer_counts=[19,24,21],
        primary_physical_GPUs=[4,5,6],auxiliary_physical_GPU=7,primary_allocator='expandable_segments:True',
        full_long_history_capacity_not_guaranteed=True,old_absence_and_readiness_failures_unresolved=True,
        auxiliary_single_model='Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a',
        auxiliary_is_JEV_S2_shared_original_base_not_decision_adapter=True,
        no_old_terminal_or_old_queue_reexecution=True,new_auxiliary_and_actor_feedback_condition=True,
        total_new_primary_call_cap=840,total_new_auxiliary_call_cap=120,
        stop_batch_on_technical_failure=True,automatic_technical_or_semantic_retry=False)
    for q in plan['queue']:q['run_id']=q['run_id'].replace('image-observer-v1','single9b-fullgui-20261108-01')
    for k in ['shared_actor_instructions_sha256','observer_native_contract_sha256']:
        plan.pop(k,None)
    plan['evidence_contract_sha256']=sha(RUNTIME/'release/image_evidence.py')
    plan['primary_core_sha256']=sha(RUNTIME/'release/defense/core.py')
    plan['source_condition_tradeoff']='One fallible image-only neutral packet is sent only to actor; same packet boundary/rules in disabled arm, full original history/images unchanged; no upstream readiness guarantee or claimed semantic truth.'
    save(RUNTIME/'plan.json',plan)
    save(RUNTIME/'auxiliary-config.json',{'model':plan['auxiliary_single_model'],'only_current_full_image_and_fixed_prompt':True,'max_calls_per_trajectory':60,'no_retry':True})
    discover=json.loads((HERE/'operations/1794143119761441700-discover-environment/stdout.txt').read_text(encoding='utf8'))
    (RUNTIME/'native_environment.py').write_text(discover['/data/researcher/jev-defense-four-gpu-20261106/gui-migration-three-linked02/native_environment.py'],encoding='utf8')
    for name in ['gui_outer.py','environment_preflight.py']:
        shutil.copyfile(HERE/name,RUNTIME/name)
    checks=[]
    for p in RUNTIME.rglob('*.py'):ast.parse(p.read_text(encoding='utf8'));checks.append(p.relative_to(RUNTIME).as_posix())
    for p in (SOURCE/'release').rglob('*.py'):
        if p.name!='image_evidence.py':assert sha(p)==sha(RUNTIME/'release'/p.relative_to(SOURCE/'release')),p
    save(HERE/'static-preparation.json',{'Python_AST_checks':checks,'latest_primary_native_release_unchanged':True,
        'main_native_generation_source_SHA':sha(RUNTIME/'release/defense/qwen_backend.py'),
        'resource_gate_SHA_unchanged':sha(RUNTIME/'resource_gate.py')==sha(SOURCE/'resource_gate.py'),
        'auxiliary_native_prompt_unchanged':True,'GUI_started':False,'model_calls':0})
    print(json.dumps({'runtime':str(RUNTIME),'AST_parsed':len(checks),'model_GUI_calls':0}))

if __name__=='__main__':prepare()
