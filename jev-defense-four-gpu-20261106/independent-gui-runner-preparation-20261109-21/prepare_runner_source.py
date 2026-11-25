"""Prepare a new32-track runner from frozen native code; never launches it."""
import ast
import hashlib
import json
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
OLD=BASE/'full-gui-bounded-evidence-20261109-03/runtime-package'
PROSPECTIVE=BASE/'independent-evaluation-preparation-20261109-04/prospective-plan.json'
BINDINGS=BASE/'independent-native-bindings-20261109-19/source-bindings-1794217976714587500/receipt.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())


def replace_once(source,old,new):
    assert source.count(old)==1,old[:180]
    return source.replace(old,new)


def main():
    target=HERE/'prepared-source';assert not target.exists()
    proposal=read(PROSPECTIVE);bindings=read(BINDINGS)
    assert [t['task_id']for t in proposal['selected_tasks']]==[0,3,17,58,89,94,114,125]
    assert [t['task_id']for t in bindings['tasks']]==[t['task_id']for t in proposal['selected_tasks']]
    tasks=[];queue=[]
    for ordinal,task in enumerate(proposal['selected_tasks']):
        tasks.append({**task,'pilot_task_id':'classifieds_'+str(task['task_id'])})
        conditions=['clean','stale_replace']if ordinal%2==0 else['stale_replace','clean']
        for condition in conditions:
            # Alternate arm order within each task and across task/condition pairs.
            arms=[False,True]if(ordinal+(condition=='stale_replace'))%2==0 else[True,False]
            for enabled in arms:
                queue.append({'run_id':'T%03d-%s-%s'%(task['task_id'],condition,'aux'if enabled else'noaux'),
                              'dataset':'vwa','task_id':task['task_id'],'condition':condition,
                              'arm':'joint','observer_enabled':enabled})
    oldplan=read(OLD/'plan.json')
    plan={**oldplan,'tasks':{'vwa':tasks},'queue':queue,
          'prospective_plan_sha256':sha(PROSPECTIVE),'native_bindings_sha256':sha(BINDINGS),
          'phase':'source_preparation_only','launch_ready':False,
          'history_condition':'All actual accepted actor request messages/images/auxiliary data and native replies retained identically in both arms; original within-decision Controller recovery unchanged.',
          'source_exposure':'Initial pages viewed for native admission, no task outcomes or private reference URLs used.',
          'remaining_admission':['Source-bound normal-operation/negative/WAIT controls',
                                 'Full accepted-history GPU capacity under original output caps',
                                 'Repair/protocol freeze and new service manifest',
                                 'Once-only live service/scorer transport checks']}
    runner=(OLD/'run_single_evidence_gui.py').read_text(encoding='utf8')
    runner=replace_once(runner,'from image_evidence import POLICY, ACTOR_BOUNDARY as SHARED_ACTOR_INSTRUCTIONS',
        'from image_evidence import POLICY, ACTOR_BOUNDARY as SHARED_ACTOR_INSTRUCTIONS\nfrom complete_actor_history import CompleteAcceptedActorHistory')
    runner=replace_once(runner,"['root','plan','token-file','runtime','native-task','actor-template','auxiliary-config','readiness']",
        "['root','plan','token-file','runtime','native-bindings','actor-template','auxiliary-config','readiness']")
    runner=replace_once(runner,"plan=json.loads(a.plan.read_text());task=plan['tasks']['vwa'][0];assert task['pilot_task_id']=='classifieds_112' and task['image']is None",
        "plan=json.loads(a.plan.read_text());tasks={t['task_id']:t for t in plan['tasks']['vwa']};assert sorted(tasks)==[0,3,17,58,89,94,114,125] and all(t['image']is None for t in tasks.values())\n bindings=json.loads(a.native_bindings.read_bytes());native_tasks={t['task_id']:t for t in bindings['tasks']};assert sorted(native_tasks)==sorted(tasks)")
    runner=replace_once(runner,"queue=[q for q in plan['queue']if q['dataset']=='vwa'];assert len(queue)==4 and {q['condition']for q in queue}=={'clean','stale_replace'} and all(q['arm']=='joint'for q in queue) and {(q['observer_enabled'],q['condition'])for q in queue}=={(False,'clean'),(True,'clean'),(False,'stale_replace'),(True,'stale_replace')}",
        "queue=[q for q in plan['queue']if q['dataset']=='vwa'];assert len(queue)==32 and all(q['arm']=='joint'for q in queue)\n for task_id in tasks:\n  subset=[q for q in queue if q['task_id']==task_id]\n  assert len(subset)==4 and {(q['observer_enabled'],q['condition'])for q in subset}=={(False,'clean'),(True,'clean'),(False,'stale_replace'),(True,'stale_replace')}")
    start=runner.index(' original_config=a.native_task;raw=original_config.read_bytes()')
    end=runner.index(' # Independent about:blank native screenshot',start)
    runner=runner[:start]+runner[end:]
    runner=replace_once(runner," for item in queue:\n  if stopping['requested']:",
        " for item in queue:\n  task=tasks[item['task_id']];binding=native_tasks[item['task_id']]\n  original_config=Path(binding['original_private_path']);raw=original_config.read_bytes()\n  assert digest(raw)==binding['original_private_SHA']==task['source_config_sha256']\n  cfg=json.loads(raw.decode().replace('192.0.2.10:19980','192.0.2.10:29980'))\n  assert cfg['intent']==task['intent'] and cfg['require_reset']is False and cfg['eval']['eval_types']==['url_match']\n  cfg['storage_state']=str(auth/'classifieds_state.json')\n  if stopping['requested']:")
    runner=replace_once(runner,"history=[];last_image=None;previous=None;fired=False;", "transcript=CompleteAcceptedActorHistory(SYSTEM);last_image=None;previous=None;fired=False;")
    runner=replace_once(runner,"msgs=[{'role':'system','content':SYSTEM}]+copy.deepcopy(history)+[{'role':'user','content':blocks}]", "msgs=transcript.current_messages(blocks)")
    runner=replace_once(runner,'     return model.actor(body)',
        "     output=model.actor(body)\n     transcript.record_actual_reply(body,output)\n     return output")
    old="    if controller.last_corrections:history.append({'role':'user','content':'Evidence verification correction retained: '+json.dumps(controller.last_corrections,ensure_ascii=False)})\n    history.extend([{'role':'user','content':'Task: '+task['intent']+'\\nPrevious observation request.'},{'role':'assistant','content':result['candidate']}])"
    runner=replace_once(runner,old,"    log.append('accepted_actor_history_retained',transcript.commit_accepted(result))")
    runner=replace_once(runner,"'protocol.py','release/image_evidence.py'", "'protocol.py','complete_actor_history.py','release/image_evidence.py'")
    assert 'classifieds_112'not in runner and 'Previous observation request.'not in runner
    assert 'a.native_task'not in runner and 'history.extend('not in runner
    ast.parse(runner)
    transport=(OLD/'gui_transport.py').read_text(encoding='utf8')
    transport=replace_once(transport,"self.failures=[v for v in self.observer.terminals.values() if v['status']=='preserved_technical_or_contract_failure_no_retry']",
        'self.failures=copy.deepcopy(self.observer.failures)')
    transport=replace_once(transport,"assert a.plan==package/'plan.json' and a.actor_template==package/'actor-template.json'",
        "assert a.plan==package/'plan.json' and a.actor_template==package/'actor-template.json'\n    assert a.native_bindings==package/'native-bindings-public.json'\n    assert hashlib.sha256(a.native_bindings.read_bytes()).hexdigest()==m['native_bindings_sha256']")
    ast.parse(transport)
    target.mkdir()
    (target/'run_independent_gui.py').write_text(runner,encoding='utf8')
    (target/'gui_transport.py').write_text(transport,encoding='utf8')
    (target/'complete_actor_history.py').write_bytes((HERE/'complete_actor_history.py').read_bytes())
    (target/'protocol.py').write_bytes((OLD/'protocol.py').read_bytes())
    (target/'native-bindings-public.json').write_bytes(BINDINGS.read_bytes())
    (target/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    changes={'time':time.time(),'old_runner_sha256':sha(OLD/'run_single_evidence_gui.py'),
             'new_runner_sha256':sha(target/'run_independent_gui.py'),'prospective_tracks':32,
             'native_tasks':[t['task_id']for t in tasks],'counterbalanced_order_frozen_before_task_outcomes':True,
             'history_fix':'Preserve actual accepted request/reply including complete native image blocks, existing correction messages and auxiliary data. Both matched arms use this rule.',
             'previous_runner_gap':'Old runner wrote Task/Previous observation request text placeholders to actor history; old reference_bank supplies selected old frames to verifier only. Prior old-G results are unchanged.',
             'transport_metadata_fix':'Latest stateless observer exposes failures list, no terminals memoization map; only accounting access changed.',
             'strict_Controller_native_model_generation_parser_actions_unchanged':True,
             'limits':proposal['limits'],'one_image_fixed_generic_prompt_auxiliary_boundary_unchanged':True,
             'no_model_GUI_scorer_calls':True,'launch_ready':False,
             'remaining_admission':plan['remaining_admission']}
    # tasks is a list; retain explicit public IDs without reading evaluator answers.
    changes['native_tasks']=[t['task_id']for t in tasks]
    (target/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (target/'seal.json').write_text(json.dumps({p.name:sha(p)for p in target.iterdir()if p.is_file()},indent=2)+'\n',encoding='utf8')
    print(json.dumps({'prepared':str(target),'seal_sha256':sha(target/'seal.json'),'tracks':32,'launch_ready':False,'model_GUI_calls':0}))


if __name__=='__main__':
    main()
