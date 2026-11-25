"""Create an isolated actor-observer runner; never launches it."""
import ast,json,shutil
from pathlib import Path
from defense.core import digest
from image_observer import POLICY,MODEL,REVISION,wire,contract,SHARED_ACTOR_INSTRUCTIONS

BASE=Path(__file__).resolve().parent
PARENT=BASE.parents[2]/'jev-defense-validation-20261103'/'release'


def main():
    root=BASE/'gui-release-04';root.mkdir(exist_ok=False)
    for source in PARENT.rglob('*.py'):
        if '__pycache__'in source.parts:continue
        target=root/source.relative_to(PARENT);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
    old=(PARENT/'run_jev_vwa_validation.py').read_text(encoding='utf8')
    changes=[
      ('from jev_cued_controller import from_config as cued_controller',
       'from image_observer import from_config as observer_from_config, POLICY, SHARED_ACTOR_INSTRUCTIONS'),
      ('from validation_launch_contract import validate_launch_inputs',
       'from observer_launch_contract import validate_launch_inputs\nfrom online_transport import OnlineQwen'),
      ('model=RemoteQwen(a.model_url,a.token_file)', 'model=OnlineQwen(a.model_url,a.token_file)'),
      ("assert len(queue)==2 and {q['condition']for q in queue}=={'clean','stale_replace'} and all(q['arm']=='joint'for q in queue)",
       "assert len(queue)==4 and {q['condition']for q in queue}=={'clean','stale_replace'} and all(q['arm']=='joint'for q in queue) and {(q['observer_enabled'],q['condition'])for q in queue}=={(False,'clean'),(True,'clean'),(False,'stale_replace'),(True,'stale_replace')}"),
      ("assert model.health()['phase']=='ready'", "assert model.health()['phase']=='ready_gui'"),
      ("['run_jev_vwa_validation.py','jev_cued_controller.py','validation_launch_contract.py','defense/core.py','defense/prompts.py']",
       "['run_image_observer_vwa_validation.py','image_observer.py','observer_launch_contract.py','online_transport.py','defense/core.py','defense/prompts.py']"),
      ("lim=plan['limits'];controller=cued_controller(a.auxiliary_config,model.judge,log,item['arm'],Limits(",
       "lim=plan['limits'];actor_observer=observer_from_config(a.auxiliary_config,enabled=item['observer_enabled']);controller=Controller(model.judge,log,item['arm'],Limits("),
      ("'policy':'jev-cued-judge-v1','auxiliary_calls_cap':60", "'policy':POLICY,'observer_enabled':item['observer_enabled'],'shared_actor_instructions_sha256':digest(SHARED_ACTOR_INSTRUCTIONS.encode()),'auxiliary_calls_cap':60"),
      ("     return model.actor(body)", "     body=actor_observer.augment(body,view,log)\n     return model.actor(body)"),
      ("  env=ScriptBrowserEnv(headless=True,observation_type='image',current_viewport_only=True,viewport_size={'width':1280,'height':720},save_trace_enabled=True,sleep_after_execution=0.5)\n  state.update(phase='running'",
       "  model.set_run(item['run_id'],log);model.begin_run()\n  if actor_observer.client is not None:actor_observer.client.online_context=model.context\n  env=ScriptBrowserEnv(headless=True,observation_type='image',current_viewport_only=True,viewport_size={'width':1280,'height':720},save_trace_enabled=True,sleep_after_execution=0.5)\n  state.update(phase='running'"),
      ("   for step in range(1,step_cap+1):\n", "   for step in range(1,step_cap+1):\n    model.set_decision(step)\n"),
      ("result['auxiliary_calls']=controller.jev_auxiliary.calls", "result['auxiliary_calls']=actor_observer.calls\n   result['observer_enabled']=item['observer_enabled']\n   result['observer_technical_failures']=len(actor_observer.failures)\n   result['observer_condition_increment_only']=True"),
      ("result['auxiliary_cap']=controller.jev_auxiliary.max_calls", "result['auxiliary_cap']=actor_observer.max_calls"),
      ("   finally:env.close()\n  save(a.root/'status.json',state)",
       "   finally:\n    env.close()\n    terminal=next((attempt/n for n in ['complete.json','technical-failure.json','failure.json','paused.json']if(attempt/n).exists()),None)\n    if terminal is None:\n     save(attempt/'cleanup-failure.json',{'semantic_mirage':None,'reason':'No run terminal existed at cleanup; no retry authorized'});terminal=attempt/'cleanup-failure.json'\n    terminal_status='completed'if terminal.name=='complete.json'else'stopped'if terminal.name=='paused.json'else'technical_failure'\n    model.end_run(terminal_status,digest(terminal.read_bytes()))\n  save(a.root/'status.json',state)")]
    new=old
    for before,after in changes:
        assert new.count(before)==1,before
        new=new.replace(before,after)
    (root/'run_image_observer_vwa_validation.py').write_text(new,encoding='utf8')
    for name in ['image_observer.py','observer_launch_contract.py','online_transport.py']:
        shutil.copyfile(BASE/name,root/name)
    def functions(text):
        return {n.name:ast.dump(n,include_attributes=False)for n in ast.walk(ast.parse(text))if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    before,after=functions(old),functions(new)
    critical=['save','block','detail','goto','public','actor','parser','recapture']
    audit={n:before[n]==after[n]for n in critical}
    assert [n for n in critical if not audit[n]]==['actor']
    plan=json.loads((PARENT.parent/'gui-plan.proposed.json').read_bytes())
    plan.update(policy=POLICY,stage='prepared_not_launched',queue=[],
        primary_endpoint='trajectory_any_definite_boundary_inclusive_Mirage; once_counts_despite_recovery; pure_native_WAIT_excluded',
        relative_reduction_development_target=0.30,relative_reduction_aspiration=0.50,
        success_claim='not_guaranteed; four known-task trajectories cannot establish a general trigger-rate reduction',
        required_companion_outcomes=['official_success','false_blocks','accepted_executed_errors','technical_failures','native_action_direction_target_errors','recovery','per_model_calls_tokens_seconds'],
        semantic_review_order='original image/legal history/candidate first, blinded to arm where feasible, then PRIVATE execution join; detector labels never gold',
        same_shared_actor_instructions_in_all_runs=True,
        shared_actor_instructions_sha256=digest(SHARED_ACTOR_INSTRUCTIONS.encode()),
        observer_native_contract_sha256=digest(wire(contract())),
        no_model_calls_during_preparation=True)
    for condition in ['clean','stale_replace']:
        for enabled in [False,True]:
            arm='observer'if enabled else'no-observer'
            plan['queue'].append({'dataset':'vwa','run_id':f'image-observer-v1--classifieds_112--{condition}--joint--{arm}',
                 'condition':condition,'arm':'joint','observer_enabled':enabled})
    plan_raw=json.dumps(plan,ensure_ascii=False,indent=2).encode()
    plan_path=BASE/'gui-plan.json'
    if plan_path.exists():assert json.loads(plan_path.read_bytes())==plan
    else:plan_path.write_bytes(plan_raw)
    evidence={'old_native_runner_sha256':digest(old.encode()),'new_runner_sha256':digest(new.encode()),
        'critical_native_function_AST_unchanged':audit,
        'actor_change':'Only actual actor wire current user message receives same shared instructions plus baseline/observer packet; original PublicView and accepted history unchanged.',
        'main_judge':'unchanged original model.judge passed directly into original Controller',
        'original_release_python_files':{str(p.relative_to(PARENT)).replace('\\','/'):digest(p.read_bytes())for p in PARENT.rglob('*.py')if '__pycache__'not in p.parts},
        'copied_original_release_files_match':all((root/p.relative_to(PARENT)).read_bytes()==p.read_bytes()for p in PARENT.rglob('*.py')if '__pycache__'not in p.parts),
        'GUI_model_scorer_calls':0,'plan_sha256':digest((BASE/'gui-plan.json').read_bytes())}
    assert evidence['copied_original_release_files_match']
    (BASE/(root.name+'-source-audit.json')).write_text(json.dumps(evidence,indent=2),encoding='utf8')
    print(json.dumps({'gui_release':str(root),'native_AST':audit,'model_calls':0}))

if __name__=='__main__':main()
